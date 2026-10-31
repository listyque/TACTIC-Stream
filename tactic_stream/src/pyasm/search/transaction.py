"""Original Transaction lifecycle and in-memory XML journal.

Adapted from pyasm/search/transaction.py; see LICENSE.TACTIC/source_manifest.json.
Automatic journal/change timestamps participate in the owned sthpw transaction.
FileUndo participates in rollback and durable replay; remote queues remain unported.
"""
import os
import stat
import shutil
import uuid
import json
from copy import deepcopy

from pyasm.common.common import Base, Common, Container
from pyasm.common.environment import Environment
from pyasm.common.errors import UnsupportedContract
from pyasm.common.lxml_wrapper import Xml


class TransactionException(Exception):
    pass


class PartialCommitException(TransactionException):
    """An existing database committed before a later database failed."""


class Transaction(Base):
    KEY = "Transaction:transaction"

    def __init__(self):
        self._reset()
        self.command_class = ""
        self.title = ""
        self.record_flag = self.sync_flag = True
        self.notify_updates = True
        self.notify_excluded_types = set()

    def _reset(self):
        self.counter = 0
        self.transaction_objs = []
        self.databases = {}
        self.created_databases = {}
        self.committed_databases = []
        self.transaction_log = None
        self.change_timestamps = {}
        self.update_objects = {}
        self.file_nodes = set()
        self.file_journal = None
        self.file_identity = None
        self.write_resource = None
        self.commit_started = False
        self.description = ""
        self.xml = Xml()
        self.xml.create_doc("transaction")

    def set_record(self, record_flag):
        self.record_flag = record_flag

    def set_sync(self, sync_flag):
        self.sync_flag = sync_flag

    def set_description(self, description):
        self.description = description

    def add_description(self, description):
        if self.description:
            self.description += "\n%s" % description
        else:
            self.description += "%s" % description

    def set_title(self, title):
        self.title = title

    def set_command_class(self, command_class):
        self.command_class = command_class

    def is_in_transaction(self):
        return self.counter != 0

    def start(self):
        if self.counter == 0:
            self._reset()
        self.counter += 1

    def register(self, transaction_obj):
        if self.counter == 0:
            return
        transaction_obj.start()
        self.transaction_objs.append(transaction_obj)

    def register_database(self, database):
        if self.counter == 0:
            return
        db_name = database.get_database_name()
        if db_name in self.databases:
            if self.databases[db_name] is not database:
                raise UnsupportedContract('Multiple connections for the same database in one Transaction are not migrated')
            return
        database.start()
        self.databases[db_name] = database
        self.transaction_objs.append(database)

    def get_databases(self):
        return self.databases

    def require_single_database(self, resource):
        """Opt-in atomic domain: reject another writer before its first mutation."""
        key = resource._get_connection_key()
        if self.write_resource is not None and self.write_resource != key:
            raise TransactionException('Atomic command cannot span databases')
        if self.write_resource is None and not self.can_write_resource(resource):
            raise TransactionException('Atomic command requires a registered database resource')
        from xml.etree import ElementTree
        if self.transaction_log is not None or self.change_timestamps or len(ElementTree.fromstring(self.xml.get_xml())):
            raise TransactionException('Atomic command requires a clean transaction journal')
        for sql in self.databases.values():
            if getattr(sql, '_has_writes', False) and sql.get_db_resource()._get_connection_key() != key:
                raise TransactionException('Atomic command cannot span databases')
        self.write_resource = key

    def check_write_resource(self, resource):
        if self.write_resource is not None and resource._get_connection_key() != self.write_resource:
            raise TransactionException('Atomic command cannot span databases')

    def register_created_database(self, resource):
        self.created_databases[resource._get_connection_key()] = resource

    def can_write_resource(self, resource):
        from pyasm.search.search import _context
        from pyasm.search.sql import DbResource
        key = resource._get_connection_key()
        if self.write_resource is not None:
            self.check_write_resource(resource)
            return True  # Ownership was checked at binding; row/column ACL still runs per SObject.
        context = _context.get()
        if key == context.store.get_db_resource()._get_connection_key() or key in self.created_databases:
            return True
        # An existing project must actually own the configured resource. A name
        # supplied to Sql alone does not authorize writes to another database.
        parameter = context.store.get_db_resource().get_database_impl().get_parameter()
        with context.store.connection() as db:
            owners = db.execute('SELECT db_resource FROM project WHERE COALESCE(NULLIF("database",\'\'),code)=' + parameter +
                                ' AND (s_status IS NULL OR s_status<>\'retired\')', (resource.get_database(),)).fetchall()
        return any((DbResource.get_by_code(owner['db_resource'], resource.get_database()) if owner['db_resource'] else
                    DbResource.get_default(resource.get_database()))._get_connection_key() == key for owner in owners)

    def _has_multiple_writers(self):
        return sum(bool(getattr(sql, '_has_writes', False)) for sql in self.databases.values()) > 1

    def _commit_databases(self):
        if self.file_journal:
            self.file_journal.prepare(list(self.databases.values()))
        # TACTIC commits each database separately. Publish the system journal
        # last and report an already committed database if a later commit fails.
        if not self.created_databases and not self._has_multiple_writers():
            for database in self.databases.values():
                self.commit_started = True
                database.commit()
            return
        from pyasm.search.search import _context
        system = _context.get().store.get_db_resource()._get_connection_key()
        databases = sorted(self.databases.values(), key=lambda sql:
                           -1 if not getattr(sql, '_has_writes', False) else
                           2 if sql.get_db_resource()._get_connection_key() == system else
                           0 if sql.get_db_resource()._get_connection_key() in self.created_databases else 1)
        for database in databases:
            wrote = getattr(database, '_has_writes', False)
            self.commit_started = True
            try:
                database.commit()
            except Exception as error:
                if self.committed_databases:
                    raise PartialCommitException('Commit failed for database [%s]; already committed: %s. '
                                                 'Inspect these databases before retrying; rollback cannot undo committed rows.' %
                                                 (database.get_database_name(), ', '.join(self.committed_databases))) from error
                raise
            if wrote and database.get_db_resource()._get_connection_key() not in self.created_databases:
                self.committed_databases.append(database.get_database_name())

    def get_database(self, db_name):
        return self.databases.get(db_name)

    def commit_all(self):
        self.counter = 1
        self.commit()

    def commit(self):
        if self.counter == 1 and any(Xml.get_attribute(node, 'state') == 'pending'
                                     for node in self.xml.get_nodes('transaction/file')):
            self.rollback()
            raise TransactionException('Cannot commit an incomplete file operation')
        if self.counter == 1 and self.record_flag and (len(self.xml.get_root_node()) or self.change_timestamps):
            # Keep the transaction active: journal writes must join it before
            # data commits, unlike the original post-commit logging path.
            try:
                for obj in self.transaction_objs:
                    if obj not in self.databases.values():
                        obj.commit()
                if len(self.xml.get_root_node()):
                    self.commit_log()
                else:
                    # Chat is excluded from Undo; its live cursors still belong to this commit.
                    self.update_change_timestamps(None)
                self._commit_databases()
            except Exception:
                self.rollback()
                raise
            from pyasm.search.update_events import publish_transaction
            publish_transaction(self)
            if self.file_journal:
                self.file_journal.close(resolved=True)
            self._reset()
            return
        self.counter -= 1
        if self.counter < 0:
            raise TransactionException("Transaction counter below zero")
        if self.counter > 0:
            return
        coordinated = bool(self.created_databases) or self._has_multiple_writers()
        if coordinated:
            # Creation cleanup and its authorization need the active owner.
            self.counter = 1
        try:
            if self.file_journal and not coordinated:
                self.file_journal.prepare(list(self.databases.values()))
            for transaction_obj in self.transaction_objs:
                if not coordinated or transaction_obj not in self.databases.values():
                    if transaction_obj in self.databases.values():
                        self.commit_started = True
                    transaction_obj.commit()
            if coordinated:
                self._commit_databases()
        except Exception:
            # A no-journal transaction still owns its SQLite writes and caches.
            self.counter = 1
            self.rollback()
            raise
        from pyasm.search.update_events import publish_transaction
        publish_transaction(self)
        if self.file_journal:
            self.file_journal.close(resolved=True)
        self._reset()

    def abort(self):
        return self.rollback()

    def rollback(self):
        if self.counter <= 0:
            raise TransactionException("Transaction start/rollback mismatch")
        journal_database = self.databases.get('sthpw')
        journal_connection = getattr(journal_database, 'conn', None)
        journal_written = (getattr(journal_connection, 'total_changes', 0) > 0 or
                           any(getattr(sql, '_has_writes', False) for sql in self.databases.values()))
        failures = []
        partial = bool(self.committed_databases)
        if self.file_journal:
            self.file_journal.claim()
        if self.file_journal and self.commit_started and self.file_journal.resources:
            from pyasm.search.file_recovery import commit_states
            from pyasm.search.search import _context
            try:
                partial |= any(commit_states(_context.get().store, self.file_journal.resources, self.file_journal.token))
            except Exception:
                self.file_journal.close()
                raise TransactionException('File commit outcome unavailable; backups and journal retained')
        # Private upload rollback must finish while its database row lock is held.
        rollback_objs = sorted(self.transaction_objs,
                               key=lambda obj: not getattr(obj, 'rollback_before_database', False))
        for transaction_obj in rollback_objs:
            if partial and transaction_obj not in self.databases.values():
                continue  # Command hooks can reverse effects already committed.
            try:
                transaction_obj.rollback()
            except Exception as error:
                # A broken command hook must not prevent closing/dropping the
                # new database and rolling back the other SQL participants.
                failures.append(error)
        from pyasm.search.search import _context
        if _context.get(None) is None:
            # Original Transaction also accepts standalone database participants.
            if failures:
                raise TransactionException('Rollback cleanup failed: %s' % failures[0]) from failures[0]
            self._reset()
            return
        if journal_written:
            from pyasm.search.search import SObject
            for search_type in ['sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp', 'sthpw/sobject_list']:
                # Rolled-back rows must not remain queryable through identity caches.
                Container.put(SObject._get_cached_key(search_type), {})
            from pyasm.security.security import _clear_account_cache
            for search_type in SObject.SECURITY_TYPES + SObject.BUSINESS_TYPES:
                SObject.get_cache_dict(search_type=search_type).clear()
            SObject._clear_process_cache()
            for key in list(Container.get_instance().get_data()):
                if isinstance(key, str) and key.startswith('Workflow|process_state|'):
                    Container.remove(key)
            _clear_account_cache()
        Container.clear_dict("Expression:keys")
        Container.clear_dict('DatabaseImpl:column_info')
        Container.clear_dict('DatabaseImpl:table_info')
        Container.clear_dict('SearchType:search_object_data')
        Container.clear_dict('SObjectConnection:cache')
        from pyasm.search.search import _context
        _context.get().schemas.clear()
        # Generic rows/DDL can also have been cached before a late failure.
        for node in self.xml.get_nodes('transaction/sobject'):
            search_type = Xml.get_attribute(node, 'search_type')
            if search_type:
                from pyasm.search.search import SObject
                SObject.get_cache_dict(search_type=search_type.split('?')[0]).clear()
                SObject._clear_config_cache(search_type.split('?')[0])
        for resource in list(self.created_databases.values()):
            try:
                for database in self.databases.values():
                    if database.get_db_resource()._get_connection_key() == resource._get_connection_key():
                        database.close()
                resource.get_database_impl()._drop_created_database(resource)
                pool = Container.get('DbContainer::thread_pool') or {}
                pool.pop(resource._get_connection_key(), None)
                self.created_databases.pop(resource._get_connection_key())
            except Exception as error:
                failures.append(error)
        nodes = self.file_journal.nodes if self.file_journal else self.xml.get_nodes('transaction/file')
        for index in reversed(range(len(nodes))):
            node = nodes[index]
            if partial:
                break  # Preserve files referenced by already committed records.
            if self.file_journal and index in self.file_journal.completed:
                continue
            if not Xml.get_attribute(node, 'type'):
                continue  # A rejected malformed journal node performed no FileUndo operation.
            previous = Container.get('FileUndo:rollback')
            Container.put('FileUndo:rollback', node if self.file_journal or node in self.file_nodes else None)
            try:
                FileUndo.undo(node, Environment.get_ticket() or '')
                if self.file_journal:
                    self.file_journal.undone(index)
            except Exception as error:
                failures.append(error)
            finally:
                Container.put('FileUndo:rollback', previous)
        if failures:
            # Retain the journal/cache for diagnosis; never claim a successful rollback.
            if self.file_journal:
                self.file_journal.close()
            raise TransactionException('Rollback cleanup failed: %s' % failures[0]) from failures[0]
        if self.file_journal:
            self.file_journal.close(resolved=not partial)
            if partial and not self.committed_databases:
                raise PartialCommitException('File transaction has committed database effects; journal and files retained for recovery')
        self._reset()

    def get_change_timestamps(self):
        return self.change_timestamps

    def get_transaction_log_sobj(self):
        return self.transaction_log

    def get_xml(self):
        return self.xml

    def get_transaction_log(self):
        return self.get_xml()

    def get_file_log(self):
        xml = Xml()
        xml.create_doc("transaction")
        for node in self.xml.get_nodes('transaction/file'):
            Xml.append_child(xml.get_root_node(), deepcopy(node))
        return xml

    def create_log_node(self, node_name):
        if node_name not in ('sobject', 'file', 'table', 'alter'):
            raise UnsupportedContract("Only local SObject, file and schema journal nodes are migrated")
        return self.xml.create_element(node_name, node=self.xml.get_root_node())

    def set_transaction(self, transaction_log):
        self.xml = Xml("<transaction/>")
        self.transaction_log = transaction_log

    @classmethod
    def resume_by_id(cls, transaction_log_id):
        from .transaction_log import TransactionLog
        log = TransactionLog.get_by_id(transaction_log_id)
        if not log:
            raise TransactionException('Transaction [%s] does not exist' % transaction_log_id)
        return cls.resume(log)

    @classmethod
    def resume(cls, transaction_log):
        if not transaction_log:
            raise TransactionException('A transaction log is required')
        if Environment.get_user_name() != transaction_log.get_value('login'):
            raise TransactionException('Transaction does not belong to the current user')
        transaction = cls.get(create=True)
        transaction.set_description(transaction_log.get_value('description'))
        transaction.set_title(transaction_log.get_value('title'))
        transaction.set_command_class(transaction_log.get_value('command'))
        transaction.set_transaction(transaction_log)
        return transaction

    def commit_log(self):
        from pyasm.common.common import Common
        from pyasm.common.environment import Environment
        from pyasm.search.transaction_log import TransactionLog
        if Transaction.get() is not self or not self.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('Automatic journal requires active Transaction and Environment Security')
        if not self.description:
            self.description = 'No description available'
        if self.command_class:
            try:
                if not Common.resolve_class(self.command_class).is_undoable():
                    return
            except (AttributeError, NameError):
                pass
        if self.transaction_log is not None:
            # Original appended XML by splitting serializer-specific lines.
            # Merge actual nodes, retaining compressed logs and XML escaping.
            log = self.transaction_log
            if log.get_value('login') != Environment.get_user_name():
                raise TransactionException('Transaction does not belong to the current user')
            previous = log.get_value('transaction')
            if previous.startswith('zlib:'):
                previous = Common.decompress_transaction(previous)
            xml = Xml(previous)
            if xml.get_root_node().tag != 'transaction':
                raise TransactionException('Expected transaction XML root')
            for node in list(self.xml.get_root_node()):
                Xml.append_child(xml.get_root_node(), deepcopy(node))
            value = xml.to_string()
            log.set_value('transaction', Common.compress_transaction(value) if len(value) > 10 * 1024 else value)
            log.set_value('description', self.description)
            log.commit(triggers=False, log_transaction=False)
            self.update_change_timestamps(log)
            if self.sync_flag:
                log.trigger_remote_sync()
            return log
        # Original per-database commits are retained; no distributed atomicity.
        for database in self.databases.values():
            if not self.can_write_resource(database.get_db_resource()) and getattr(database, '_has_writes', False):
                raise UnsupportedContract('Automatic journal across writable databases is not migrated')
        data = self.xml.to_string()
        self.transaction_log = TransactionLog.create(self.command_class, data, self.description, self.title)
        # Low-level create only indexes small logs; automatic Commands also finish large logs.
        if len(data) > 10 * 1024:
            TransactionLog.create_sobject_log(self.transaction_log, data)
        self.update_change_timestamps(self.transaction_log)
        if self.sync_flag:
            self.transaction_log.trigger_remote_sync()
        return self.transaction_log

    def get_change_timestamp(self, search_type, search_code, is_insert=False):
        from pyasm.search.search import Search, SearchType
        key = '%s|%s' % (search_type, search_code)
        log = self.change_timestamps.get(key)
        if log is not None:
            return log
        log = None
        if not is_insert:
            search = Search('sthpw/change_timestamp')
            search.add_filter('search_type', search_type)
            search.add_filter('search_code', search_code)
            log = search.get_sobject()
        if not log:
            log = SearchType.create('sthpw/change_timestamp')
            log.set_value('search_type', search_type)
            log.set_value('search_code', search_code)
            log.set_value('changed_on', {})
            log.set_value('changed_by', {})
        self.change_timestamps[key] = log
        return log

    def update_change_timestamps(self, transaction_log):
        from pyasm.common.environment import Environment
        if Transaction.get() is not self or not self.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('Change timestamps require active Transaction and Environment Security')
        from pyasm.security.access_manager import Sudo
        from pyasm.common.spt_date import SPTDate
        from pyasm.biz.preference import PrefSetting
        from pyasm.biz.project import Project
        from pyasm.search.search import Search, SObject
        from pyasm.search.sql import DbContainer
        sudo = Sudo()
        try:
            from datetime import datetime, timezone as datetime_timezone
            timestamp = transaction_log.get_value('timestamp') if transaction_log else datetime.now(datetime_timezone.utc)
            timezone = PrefSetting.get_value_by_key('timezone')
            timestamp = SPTDate.convert_to_local(timestamp) if timezone in ('local', '') else SPTDate.convert_to_timezone(timestamp, timezone)
            if timestamp and not isinstance(timestamp, str):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            code = transaction_log.get_value('code') if transaction_log else ''
            project_code = Project.get_project_code()
            sql = DbContainer.get(Project.get_db_resource_by_search_type('sthpw/change_timestamp'))
            sequential = sql.get_database_impl().has_table_triggers(sql, 'change_timestamp')
            from itertools import islice
            staged_rows = iter(self.change_timestamps.values())
            while batch := list(islice(staged_rows, 250)):
                existing, by_type = {}, {}
                for staged in batch:
                    by_type.setdefault(staged.get_value('search_type'), []).append(staged.get_value('search_code'))
                for search_type, codes in (() if sequential else by_type.items()):
                    search = Search('sthpw/change_timestamp')
                    search.add_filter('search_type', search_type)
                    search.add_filters('search_code', codes)
                    for row in search.get_sobjects():
                        existing.setdefault((row.get_value('search_type'), row.get_value('search_code')), row)
                pending = []
                for staged in batch:
                    new_changed_on = staged.get_json_value('changed_on', {})
                    new_changed_by = staged.get_json_value('changed_by', {})
                    stored = existing.get((staged.get_value('search_type'), staged.get_value('search_code')))
                    if sequential:
                        search = Search('sthpw/change_timestamp')
                        search.add_filter('search_type', staged.get_value('search_type'))
                        search.add_filter('search_code', staged.get_value('search_code'))
                        stored = search.get_sobject()
                    change_timestamp = stored if stored is not None else staged
                    changed_on = change_timestamp.get_json_value('changed_on', {})
                    changed_by = change_timestamp.get_json_value('changed_by', {})
                    for column, value in new_changed_on.items():
                        if value == 'CHANGED':
                            changed_on[column] = timestamp
                            if column in new_changed_by:
                                changed_by[column] = new_changed_by[column]
                    change_timestamp.set_json_value('changed_on', changed_on)
                    if stored is not None and new_changed_by:
                        change_timestamp.set_json_value('changed_by', changed_by)
                    change_timestamp.set_value('transaction_code', code)
                    change_timestamp.set_value('project_code', project_code)
                    change_timestamp.set_now('timestamp')
                    # A failed timestamp must fail the transaction, including earlier batches.
                    if sequential:
                        change_timestamp.commit(triggers='ingest', log_transaction=False, cache=False)
                    else:
                        pending.append(change_timestamp)
                SObject.commit_multiple(pending, triggers='ingest', log_transaction=False, cache=False)
        finally:
            sudo.exit()

    @staticmethod
    def get(create=False, force=False):
        transaction = None
        if not force:
            transactions = Container.get_seq(Transaction.KEY)
            if transactions:
                transaction = transactions[-1]
        if force:
            transaction = Transaction()
            transaction.start()
            Container.append_seq(Transaction.KEY, transaction)
        elif create:
            if transaction:
                transaction.start()
            else:
                transaction = Transaction()
                transaction.start()
                Container.append_seq(Transaction.KEY, transaction)
        return transaction


# Copyright (c) 2005, Southpaw Technology; see LICENSE.TACTIC.
class TableUndo:
    def log(search_type, database, table):
        # build the sobject xml action description
        transaction = Transaction.get()
        if not transaction:
            print("WARNING: no transaction found")
            return

        sobject_node = transaction.create_log_node("table")
        Xml.set_attribute(sobject_node,"search_type", search_type)
        Xml.set_attribute(sobject_node,"table",table)
        Xml.set_attribute(sobject_node,"database",database)
        Xml.set_attribute(sobject_node,"action", "create")

        from .search import SearchType


        column_info = SearchType.get_column_info(search_type)
        xml = transaction.get_xml()

        #print("column_info: ", column_info)
        #column_info:  {u'code': {'data_type': 'varchar', 'nullable': True}, u'description': {'data_type': 'text', 'nullable': True}, u'timestamp': {'data_type': 'timestamp', 'nullable': True}, u's_status': {'data_type': 'varchar', 'nullable': True}, u'keywords': {'data_type': 'text', 'nullable': True}, u'login': {'data_type': 'varchar', 'nullable': True}, u'id': {'data_type': 'integer', 'nullable': False}, u'name': {'data_type': 'varchar', 'nullable': True}}
        for column, data in column_info.items():
            column_node = xml.create_element("column")
            xml.append_child(sobject_node, column_node)
            xml.set_attribute(column_node,"name",column)

            # make some assumptions about id
            if column == 'id':
                data_type = 'serial'
                xml.set_attribute(column_node,"primary_key","true")
            elif column == 'code':
                data_type = data.get("data_type")
                xml.set_attribute(column_node,"unique","true")
            else:
                data_type = data.get("data_type")
            xml.set_attribute(column_node,"data_type",data_type)


            if data.get('nullable'):
                nullable = "true"
            else:
                nullable = "false"
            xml.set_attribute(column_node,"nullable",nullable)
        from pyasm.biz import Project
        resource = Project.get_db_resource_by_search_type(search_type)
        Xml.set_attribute(sobject_node, 'schema', resource.get_schema() or 'public')
        TableUndo._snapshot(sobject_node, data=False)
    log = staticmethod(log)

    @staticmethod
    def _sql(node):
        from .sql import DbContainer, DbResource
        resource = DbResource.get_default(Xml.get_attribute(node, 'database'),
                                          schema=Xml.get_attribute(node, 'schema') or 'public')
        sql = DbContainer.get(resource)
        sql.check_schema_write()
        vendor = Xml.get_attribute(node, 'vendor')
        if vendor and vendor != resource.get_vendor():
            raise UnsupportedContract('Schema journals cannot be replayed across database vendors')
        return sql

    @staticmethod
    def _save(node, name, backup):
        previous = node.find(name)
        if previous is not None:
            Xml.remove_child(node, previous)
        xml = Transaction.get().get_xml()
        Xml.append_child(node, xml.create_text_element(name, json.dumps(backup, ensure_ascii=False)))

    @staticmethod
    def _load(node, name='backup'):
        child = node.find(name)
        if child is None or not child.text:
            raise UnsupportedContract('Historical schema journal has no complete backup; migration is required')
        return json.loads(child.text)

    @staticmethod
    def _snapshot(node, data=True):
        sql = TableUndo._sql(node)
        backup = sql.get_database_impl().snapshot_table(sql, Xml.get_attribute(node, 'table'), data)
        Xml.set_attribute(node, 'vendor', sql.get_db_resource().get_vendor())
        Xml.set_attribute(node, 'schema', sql.get_db_resource().get_schema() or 'public')
        TableUndo._save(node, 'backup', backup)

    @staticmethod
    def undo(node):
        from .storage import identifier
        sql = TableUndo._sql(node)
        table = Xml.get_attribute(node, 'table')
        TableUndo._snapshot(node)
        sql.do_update('DROP TABLE ' + identifier(table))
        sql.clear_table_cache()

    @staticmethod
    def redo(node):
        sql = TableUndo._sql(node)
        sql.get_database_impl().restore_table(sql, Xml.get_attribute(node, 'table'), TableUndo._load(node))


class TableDropUndo(Base):
    @staticmethod
    def log(search_type, database, table):
        node = Transaction.get().create_log_node('table')
        for name, value in dict(action='drop', search_type=search_type, database=database, table=table).items():
            Xml.set_attribute(node, name, value)
        from pyasm.biz import Project
        resource = Project.get_db_resource_by_search_type(search_type)
        Xml.set_attribute(node, 'schema', resource.get_schema() or 'public')
        TableUndo._snapshot(node)

    @staticmethod
    def undo(node):
        TableUndo.redo(node)

    @staticmethod
    def redo(node):
        TableUndo.undo(node)


class AlterTableUndo(Base):
    @staticmethod
    def log_drop(database, table, column):
        from pyasm.search.sql import DbContainer, SqlException
        sql = DbContainer.get(database)
        sql.check_schema_write()
        col_type = sql.get_column_types(table).get(column)
        if not col_type:
            raise SqlException('Column Type is unknown. log_drop() needs to be called before a column is dropped.')
        node = Transaction.get().create_log_node('alter')
        for name, value in dict(action='drop', database=sql.get_database_name(), table=table,
                                column=column, type=col_type).items():
            Xml.set_attribute(node, name, value)
        Xml.set_attribute(node, 'schema', sql.get_db_resource().get_schema() or 'public')
        TableUndo._snapshot(node)

    def log_add(db_resource,table,column,type):
        database = db_resource if isinstance(db_resource, str) else db_resource.get_database()

        # build the sobject xml action description
        transaction = Transaction.get()
        sobject_node = transaction.create_log_node("alter")

        Xml.set_attribute(sobject_node,"action", 'add')

        Xml.set_attribute(sobject_node, 'database', database)
        Xml.set_attribute(sobject_node,"table",table)
        Xml.set_attribute(sobject_node,"column",column)
        Xml.set_attribute(sobject_node,"type",type)
        if not isinstance(db_resource, str):
            Xml.set_attribute(sobject_node, 'schema', db_resource.get_schema() or 'public')
        TableUndo._snapshot(sobject_node)
    log_add = staticmethod(log_add)

    @staticmethod
    def undo(node):
        if Xml.get_attribute(node, 'action') == 'add':
            AlterTableUndo._drop_column(node)
        elif Xml.get_attribute(node, 'action') == 'drop':
            AlterTableUndo._add_column(node)
        else:
            raise UnsupportedContract('Column type modification replay is not migrated')

    @staticmethod
    def redo(node):
        if Xml.get_attribute(node, 'action') == 'add':
            AlterTableUndo._add_column(node)
        elif Xml.get_attribute(node, 'action') == 'drop':
            AlterTableUndo._drop_column(node)
        else:
            raise UnsupportedContract('Column type modification replay is not migrated')

    @staticmethod
    def _drop_column(node):
        sql = TableUndo._sql(node)
        TableUndo._snapshot(node)
        sql.drop_column(Xml.get_attribute(node, 'table'), Xml.get_attribute(node, 'column'))
        TableUndo._save(node, 'remaining', sql.get_database_impl().get_table_definition(sql, Xml.get_attribute(node, 'table')))

    @staticmethod
    def _add_column(node):
        from .storage import identifier
        sql = TableUndo._sql(node)
        impl = sql.get_database_impl()
        table, column = Xml.get_attribute(node, 'table'), Xml.get_attribute(node, 'column')
        backup = TableUndo._load(node)
        current = impl.snapshot_table(sql, table)
        definition = {key: value for key, value in current.items() if key not in ('vendor', 'rows', 'sequence')}
        if definition != TableUndo._load(node, 'remaining'):
            raise TransactionException('Table schema changed after column removal: ' + table)
        names = [item['name'] for item in backup['columns']]
        present = [item['name'] for item in current['columns']]
        if 'id' not in present:
            raise UnsupportedContract('Column value restoration requires SObject id')
        saved = {row[names.index('id')]: row[names.index(column)] for row in backup['rows']}
        if len(saved) != len(backup['rows']) or len({row[present.index('id')] for row in current['rows']}) != len(current['rows']):
            raise UnsupportedContract('Column value restoration requires unique SObject ids')
        rows = []
        dropped = backup['columns'][names.index(column)]
        for row in current['rows']:
            values = dict(zip(present, row))
            row_id = values['id']
            if row_id in saved:
                values[column] = saved[row_id]
            elif dropped['default'] is None and not dropped['nullable']:
                raise UnsupportedContract('Cannot restore a required column without values for new rows')
            rows.append(values)
        backup['rows'] = rows
        backup['sequence'] = max(backup['sequence'], current['sequence'])
        sql.do_update('DROP TABLE ' + identifier(table))
        impl.restore_table(sql, table, backup)


class FileUndo:
    '''encapsulates common file manipulations that can be undone'''


    @staticmethod
    def _replay_intent(kind, src, dst='', extra=None):
        transaction = Transaction.get()
        if not transaction or not transaction.is_in_transaction() or Container.get('FileUndo:rollback') is not None:
            return False
        if transaction.file_journal is None:
            from pyasm.search.file_recovery import FileJournal
            from pyasm.search.search import _context
            transaction.file_journal = FileJournal(_context.get().store)
        node = Xml().create_element('file')
        for name, value in dict(extra or {}, type=kind, src=FileUndo._stored_path(src), dst=FileUndo._stored_path(dst), state='pending').items():
            Xml.set_attribute(node, name, value)
        transaction.file_journal.add(node)
        return True

    @staticmethod
    def _replay_io(operation, *args, **kwargs):
        functions = {'move': shutil.move, 'copy': shutil.copy, 'copyfile': shutil.copyfile,
                     'copytree': shutil.copytree, 'makedirs': os.makedirs, 'rmdir': os.rmdir,
                     'unlink': os.unlink, 'rmtree': shutil.rmtree, 'link': os.link, 'symlink': os.symlink}
        if operation in ('move', 'copy', 'copyfile', 'copytree', 'link', 'symlink'):
            FileUndo._replay_intent('move' if operation == 'move' else 'copy', args[0], args[1])
        elif operation == 'makedirs' and not os.path.exists(args[0]):
            parents, parent = [], os.path.dirname(os.path.abspath(args[0]))
            while not os.path.exists(parent):
                parents.append(parent)
                parent = os.path.dirname(parent)
            FileUndo._replay_intent('mkdir', args[0], extra={'parents': json.dumps(parents)})
        elif operation == 'rmdir' and os.path.isdir(args[0]):
            FileUndo._replay_intent('rmdir', args[0])
        elif operation in ('unlink', 'rmtree') and os.path.lexists(args[0]):
            transaction = Transaction.get()
            if transaction and transaction.is_in_transaction() and Container.get('FileUndo:rollback') is None:
                backup = FileUndo._cache_path(args[0])
                FileUndo._replay_intent('remove', args[0], backup)
                return shutil.move(args[0], backup)
        return functions[operation](*args, **kwargs)

    @staticmethod
    def _check_access(require_transaction=True):
        from pyasm.common.errors import SecurityException
        from pyasm.search.search import _context
        from pyasm.security.authenticator import Authenticator
        context = _context.get(None)
        security = Environment.get_security()
        attachment = Container.get('Chat:attachment')
        profile = Container.get('UserProfile:writing')
        if profile and profile['avatar']: attachment = profile
        checkin = Container.get('Checkin:writing')
        if context is None or security is None or not (security.is_admin() or attachment or checkin):
            raise SecurityException('File operations require authenticated administrator access')
        resource = context.store.get_db_resource()
        transaction = Transaction.get()
        identity = (context.login, id(security), Container.get('FileUndo:identity-revision'))
        cached = transaction.file_identity if transaction is not None and transaction.is_in_transaction() else None
        if cached is None or cached[0] != identity:
            with context.store.connection() as db:
                admin = Authenticator._admin(db, context.login, resource.get_database_impl().get_parameter())
                marker = resource.get_database_impl().get_parameter()
                active = bool(db.execute("SELECT 1 FROM login WHERE login=" + marker +
                    " AND (s_status IS NULL OR s_status!='retired')", (context.login,)).fetchone())
            if transaction is not None and transaction.is_in_transaction():
                transaction.file_identity = (identity, admin, active)
        else:
            _, admin, active = cached
        if not attachment and not admin:
            if (not checkin or not active or not security.is_logged_in() or
                    security.get_user_name() != context.login):
                raise SecurityException('File operations require the authenticated active request identity')
            parent = checkin.get('parent')
            if parent is not None:
                parent._check_business_write('edit')
            elif not checkin.get('ticket_upload') and not security.check_access('project', [{'code': '*'}, {'code': context.project}], 'allow', default='deny'):
                raise SecurityException('Upload project access denied')
        if require_transaction and (transaction is None or not transaction.is_in_transaction()):
            raise UnsupportedContract('File operations require an active Command transaction')
        if not Container.get('FileUndo:recovered'):
            from pyasm.search.file_recovery import recover_files
            recover_files(context.store)
            Container.put('FileUndo:recovered', True)
        return transaction

    @staticmethod
    def _stored_path(path):
        if not path:
            return ''
        path = os.path.abspath(path)
        base = os.path.abspath(Environment.get_asset_dir())
        try:
            if os.path.commonpath([base, path]) == base:
                return os.path.relpath(path, base).replace(os.sep, '/')
        except ValueError:
            pass  # Different Windows drives remain absolute.
        return path.replace(os.sep, '/')

    @staticmethod
    def _resolve_path(path):
        return os.path.normpath(path if os.path.isabs(path) else os.path.join(Environment.get_asset_dir(), path)) if path else ''

    @staticmethod
    def _cache_path(src, ticket=''):
        # Keep undo payloads outside temp/cache: dump creation journals mkdir
        # there, and undo must be able to remove it after moving the dump away.
        directory = os.path.join(Environment.get_tmp_dir(), 'undo', uuid.uuid4().hex)
        os.makedirs(directory)
        return os.path.join(directory, os.path.basename(src))

    @staticmethod
    def _check_source(src, dst):
        try:
            info = os.lstat(src)
        except OSError:
            raise FileNotFoundError(src) from None
        if stat.S_ISREG(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            source_parent = os.path.abspath(os.path.dirname(src) or '.')
            source = os.path.join(Environment._directory(source_parent), os.path.basename(src))
        else:
            source = os.path.realpath(src)
        source = os.path.normcase(source)
        parent = os.path.abspath(os.path.dirname(dst) or '.')
        destination = os.path.normcase(os.path.join(Environment._directory(parent), os.path.basename(dst)))
        try:
            nested = os.path.isdir(src) and os.path.commonpath([source, destination]) == source
        except ValueError:
            nested = False
        if source == destination or nested:
            raise ValueError('Cannot copy or move a path onto itself or inside itself')

    def mkdir(src):
        FileUndo._check_access()
        src = os.path.abspath(src)
        if os.path.isdir(src):
            return
        # Infrastructure must exist before recording newly created parents;
        # later undo backups must not become children of a parent to remove.
        os.makedirs(os.path.join(Environment.get_tmp_dir(), 'undo'), exist_ok=True)
        if os.path.isdir(src):
            return
        parents = []
        parent = os.path.dirname(src)
        while not os.path.exists(parent):
            parents.append(parent)
            parent = os.path.dirname(parent)
        node = FileUndo._add_to_transaction_log('mkdir', src, '', {'parents': parents})
        os.makedirs(src)
        Xml.set_attribute(node, 'state', 'done')
 
    mkdir = staticmethod(mkdir)


    def rmdir(src):
        FileUndo._check_access()
        if not os.path.lexists(src):
            return
        node = FileUndo._add_to_transaction_log('rmdir', os.path.abspath(src), '')
        os.rmdir(src)
        Xml.set_attribute(node, 'state', 'done')
 
    rmdir = staticmethod(rmdir)



    def remove(src):
        FileUndo._check_access()
        if not os.path.lexists(src):
            return
        src = os.path.abspath(src)
        tmp_file = FileUndo._cache_path(src)
        node = FileUndo._add_to_transaction_log('remove', src, tmp_file)
        shutil.move(src, tmp_file)
        Xml.set_attribute(node, 'state', 'done')

    remove = staticmethod(remove)


    def create(orig, src=None, io_action=True, extra={}):
        FileUndo._check_access()
        orig = os.path.abspath(orig)
        src = os.path.abspath(src or orig)
        extra = dict(extra, orig=FileUndo._stored_path(orig),
                     source_move='true' if io_action is True and orig != src else 'false')
        if io_action and orig != src:
            FileUndo._check_source(orig, src)
            if os.path.lexists(src):
                FileUndo.remove(src)
        node = FileUndo._add_to_transaction_log('create', src, '', extra)
        if io_action and orig != src:
            if io_action == 'copy':
                if os.path.isdir(orig):
                    shutil.copytree(orig, src)
                else:
                    shutil.copy(orig, src)
            else:
                shutil.move(orig, src)
        Xml.set_attribute(node, 'state', 'done')
    create = staticmethod(create)
       


    def copy(src, dst):
        FileUndo._check_access()
        src, dst = os.path.abspath(src), os.path.abspath(dst)
        FileUndo._check_source(src, dst)
        if os.path.lexists(dst):
            FileUndo.remove(dst)
        node = FileUndo._add_to_transaction_log('copy', src, dst)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)
        Xml.set_attribute(node, 'state', 'done')
    copy = staticmethod(copy)



    def move(src, dst):
        FileUndo._check_access()
        src, dst = os.path.abspath(src), os.path.abspath(dst)
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
        FileUndo._check_source(src, dst)
        if os.path.lexists(dst):
            FileUndo.remove(dst)
        node = FileUndo._add_to_transaction_log('move', src, dst)
        shutil.move(src, dst)
        Xml.set_attribute(node, 'state', 'done')
    move = staticmethod(move)

    @staticmethod
    def reclaim(paths):
        """Restore inplace sources removed by this same Command, with replayable moves."""
        removed = Transaction.get().get_xml().get_nodes('transaction/file')
        for path in paths:
            if os.path.lexists(path):
                continue
            for node in reversed(removed):
                if Xml.get_attribute(node, 'type') != 'remove' or Xml.get_attribute(node, 'state') != 'done':
                    continue
                original = FileUndo._resolve_path(Xml.get_attribute(node, 'src'))
                backup = FileUndo._resolve_path(Xml.get_attribute(node, 'dst'))
                if os.path.normcase(os.path.abspath(original)) == os.path.normcase(os.path.abspath(path)) and os.path.lexists(backup):
                    FileUndo.move(backup, path)
                    break

    def symlink(src,dst,mode='symlink'):
        """Create a versionless link or copy, retaining replaced paths for rollback."""
        FileUndo._check_access()
        if mode not in ('symlink', 'hardlink', 'copy'):
            raise ValueError('Versionless mode must be symlink, hardlink or copy')
        src, dst = os.path.abspath(src), os.path.abspath(dst)
        FileUndo._check_source(src, dst)
        FileUndo.mkdir(os.path.dirname(dst))
        link_path = os.path.join(os.path.dirname(dst), '.' + os.path.basename(dst) + '.link')
        extra = {'mode': mode,
                 'link': FileUndo._stored_path(link_path)}
        if os.path.islink(dst):
            extra['prev'] = FileUndo._stored_path(os.path.join(os.path.dirname(dst), os.readlink(dst)))
        elif os.path.isfile(link_path):
            with open(link_path, encoding='utf-8') as stream:
                extra['prev'] = FileUndo._stored_path(stream.readline())
        for path in (dst, link_path):
            if os.path.lexists(path):
                FileUndo.remove(path)
        node = FileUndo._add_to_transaction_log('symlink', src, dst, extra)
        if extra['mode'] in ('copy', 'hardlink'):
            with open(link_path, 'w', encoding='utf-8') as stream:
                stream.write(src)
            if extra['mode'] == 'hardlink':
                os.link(src, dst)
            elif os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copyfile(src, dst)
        else:
            os.symlink(os.path.relpath(src, os.path.dirname(dst)), dst,
                       target_is_directory=os.path.isdir(src))
        Xml.set_attribute(node, 'state', 'done')

    symlink = staticmethod(symlink)


    def _add_to_transaction_log(type, src, dst, extra={}):
        transaction = FileUndo._check_access()
        attachment = Container.get('Chat:attachment')
        profile = Container.get('UserProfile:writing')
        if profile and profile['avatar']: attachment = profile
        if attachment:
            from pathlib import Path
            from pyasm.common.errors import SecurityException
            for value in (src, dst, extra.get('orig')):
                if value and not any(Path(value).resolve().is_relative_to(Path(root).resolve()) for root in attachment['paths']):
                    raise SecurityException('File operation is outside this avatar upload' if profile and profile['avatar'] else 'File operation is outside this chat upload')
        # Validate XML before any disk operation. A failed IO stays pending;
        # commit rejects it even if a caller catches the original exception.
        xml = transaction.get_xml()
        node = xml.create_element('file')
        for name, value in dict(extra, type=type, src=FileUndo._stored_path(src),
                                dst=FileUndo._stored_path(dst), state='pending').items():
            Xml.set_attribute(node, name, value)
        Xml.append_child(xml.get_root_node(), node)
        transaction.file_nodes.add(node)
        if transaction.file_journal is None:
            from pyasm.search.file_recovery import FileJournal
            from pyasm.search.search import _context
            transaction.file_journal = FileJournal(_context.get().store)
        transaction.file_journal.add(node)
        return node

    _add_to_transaction_log = staticmethod(_add_to_transaction_log)
      



    def undo(node, ticket=""):
        # Rollback must restore its own validated IO even after its parent row disappears.
        if Container.get('FileUndo:rollback') is not node:
            scope = Container.get('Checkin:writing') or {}
            if scope.get('replay_node') is not None and scope['replay_node'] is not node:
                from pyasm.common.errors import SecurityException
                raise SecurityException('File replay only permits its validated current journal node')
            FileUndo._check_access(require_transaction=False)
        if Xml.get_attribute(node, 'undone') == 'true':
            return

        #if not ticket:
        #    ticket = "NO_TICKET"

        type = Xml.get_attribute(node,"type")
        if type not in ('move', 'copy', 'remove', 'mkdir', 'rmdir', 'create', 'symlink'):
            raise UnsupportedContract('FileUndo operation is not migrated: %s' % type)
        if type == 'symlink' and not Xml.get_attribute(node, 'state'):
            raise UnsupportedContract('Historical versionless journals require backup migration')
        src = Xml.get_attribute(node,"src")
        dst = Xml.get_attribute(node,"dst")

        src, dst = FileUndo._resolve_path(src), FileUndo._resolve_path(dst)


        try:
            if type == "move":
                # move the file back
                dirname = os.path.dirname(src)
                if not os.path.exists(dirname):
                    FileUndo._replay_io('makedirs', dirname)

                if os.path.lexists(dst):
                    if os.path.lexists(src):
                        if Xml.get_attribute(node, 'state') == 'pending':
                            if os.path.isdir(dst) and not os.path.islink(dst):
                                FileUndo._replay_io('rmtree', dst)
                            else:
                                FileUndo._replay_io('unlink', dst)
                        else:
                            raise TransactionException('Undo would overwrite existing source: %s' % src)
                    else:
                        FileUndo._replay_io('move', dst,src)

            elif type == "copy":
                if os.path.lexists(dst):
                    cache_path = Xml.get_attribute(node, 'undo_cache') or FileUndo._cache_path(dst, ticket)
                    if os.path.lexists(cache_path):
                        raise TransactionException('Undo cache path already exists: %s' % cache_path)
                    Xml.set_attribute(node, 'undo_cache', cache_path)
                    FileUndo._replay_io('move', dst, cache_path)
                else:
                    Environment.add_warning("Cannot delete", "Cannote remove nonexistent file/dir [%s]" % dst)
            elif type == "remove":
                if os.path.lexists(dst):
                    if os.path.lexists(src):
                        raise TransactionException('Undo would overwrite existing path: %s' % src)
                    FileUndo._replay_io('makedirs', os.path.dirname(src), exist_ok=True)
                    FileUndo._replay_io('move', dst,src)
            elif type == "mkdir":
                import json
                parents = json.loads(Xml.get_attribute(node, 'parents') or '[]')
                paths = [src] + parents
                # Refuse before removing the leaf if a later parent has
                # acquired unrelated contents since the original operation.
                removed = {os.path.normcase(os.path.abspath(path)) for path in paths}
                for path in paths:
                    if os.path.isdir(path):
                        with os.scandir(path) as entries:
                            if any(os.path.normcase(os.path.abspath(entry.path)) not in removed for entry in entries):
                                raise TransactionException('Undo directory contains unrelated files: %s' % path)
                for path in paths:
                    if os.path.isdir(path):
                        FileUndo._replay_io('rmdir', path)

            elif type == "rmdir":
                # add the directory back
                if not os.path.exists(src):
                    FileUndo._replay_io('makedirs', src)

            elif type == "create":
                if os.path.lexists(src):
                    cache_path = Xml.get_attribute(node, 'cache')
                    if not cache_path:
                        cache_path = FileUndo._cache_path(src, ticket)
                        Xml.set_attribute(node, 'cache', cache_path)
                    if os.path.lexists(cache_path):
                        if Xml.get_attribute(node, 'state') != 'pending':
                            raise TransactionException('Undo cache path already exists: %s' % cache_path)
                        # Failed redo can leave partial bytes while the complete cache survives.
                        if os.path.isdir(src) and not os.path.islink(src):
                            FileUndo._replay_io('rmtree', src)
                        else:
                            FileUndo._replay_io('unlink', src)
                    else:
                        # Never delete the only copy when a cache move fails.
                        FileUndo._replay_io('move', src, cache_path)

            elif type == "symlink":
                # Replaced aliases and .link files have their own remove nodes.
                link_path = FileUndo._resolve_path(Xml.get_attribute(node, 'link'))
                moves = []
                for path, attribute in ((dst, 'undo_cache'), (link_path, 'undo_link_cache')):
                    if path and os.path.lexists(path):
                        cache_path = Xml.get_attribute(node, attribute) or FileUndo._cache_path(path, ticket)
                        if os.path.lexists(cache_path):
                            raise TransactionException('Undo cache path already exists: %s' % cache_path)
                        Xml.set_attribute(node, attribute, cache_path)
                        moves.append((path, cache_path))
                completed = []
                try:
                    for path, cache_path in moves:
                        FileUndo._replay_io('move', path, cache_path)
                        completed.append((path, cache_path))
                except OSError:
                    for path, cache_path in reversed(completed):
                        FileUndo._replay_io('move', cache_path, path)
                    raise


        except IOError as e:
            raise TransactionException("Failed to undo %s %s: %s" % (type, src, e)) from e
        except OSError as e:
            raise TransactionException("Failed to undo due to OS Error during %s. %s" % (type, e.__str__()))
        except Exception as e:
            print("Error: %s" %e)
            raise

        Xml.set_attribute(node, 'undone', 'true')

    undo = staticmethod(undo)



    def redo(node, ticket="", base_dir=''):
        if Container.get('FileUndo:rollback') is not node:
            scope = Container.get('Checkin:writing') or {}
            if scope.get('replay_node') is not None and scope['replay_node'] is not node:
                from pyasm.common.errors import SecurityException
                raise SecurityException('File replay only permits its validated current journal node')
            FileUndo._check_access(require_transaction=False)
        '''interpret transaction log and perform the actions in it'''

        #if not ticket:
        #    ticket = "NO_TICKET"

        type = Xml.get_attribute(node,"type")
        if type not in ('move', 'copy', 'remove', 'mkdir', 'rmdir', 'create', 'symlink'):
            raise UnsupportedContract('FileUndo operation is not migrated: %s' % type)
        if type == 'symlink' and not Xml.get_attribute(node, 'state'):
            raise UnsupportedContract('Historical versionless journals require backup migration')
        src = Xml.get_attribute(node,"src")
        dst = Xml.get_attribute(node,"dst")

        asset_dir = Environment.get_asset_dir()
        src, dst = FileUndo._resolve_path(src), FileUndo._resolve_path(dst)


        if type == "move":
            # move the file
            if os.path.lexists(dst):
                raise TransactionException('Redo would overwrite existing path: %s' % dst)
            FileUndo._replay_io('move', src,dst)
        elif type == "copy":
            if os.path.lexists(dst):
                raise TransactionException('Redo would overwrite existing path: %s' % dst)
            cache_path = Xml.get_attribute(node, 'undo_cache')
            if cache_path and os.path.lexists(cache_path):
                FileUndo._replay_io('move', cache_path, dst)
            elif os.path.isdir(src):
                FileUndo._replay_io('copytree', src, dst)
            else:
                FileUndo._replay_io('copyfile', src, dst)
        elif type == "remove":
            if os.path.lexists(dst):
                raise TransactionException('Redo would overwrite existing path: %s' % dst)
            FileUndo._replay_io('move', src,dst)
        elif type == "rmdir":
            FileUndo._replay_io('rmdir', src)
        elif type == "mkdir":
            # recreate directory
            if not os.path.exists(src):
                FileUndo._replay_io('makedirs', src)
        elif type == "create":
            
            tmp_dir = Environment.get_tmp_dir()

            # first check the upload, then the cache
            filename = os.path.basename(src)

            # find the location of the file

            # if this is from reruning a transaction from another server
            # then the file will be in the transaction folder???
            # when to use rel_path?
            if base_dir:
                rel_path = Xml.get_attribute(node,"rel_path")
                orig = "%s/%s" % (base_dir, rel_path)
                src = "%s/%s" % (asset_dir, rel_path)
                src_dir = os.path.dirname(src)
            else:
                # if the transaction was undo, then the file will be in the
                # cache folder
                orig = Xml.get_attribute(node, 'cache') or "%s/cache/%s/%s" % (tmp_dir, ticket, filename)
                if not os.path.lexists(orig):
                    orig = "%s/upload/%s/%s" % (tmp_dir, ticket, filename)

                src_dir = os.path.dirname(src)


            if not os.path.exists(orig):
                raise FileNotFoundError(orig)
            if os.path.lexists(src):
                raise TransactionException('Redo would overwrite existing path: %s' % src)

            if not os.path.exists(src_dir):
                FileUndo._replay_io('makedirs', src_dir)

            if base_dir:
                FileUndo._replay_io('copy', orig, src)
            else:
                FileUndo._replay_io('move', orig, src)

            #dirname = os.path.dirname(src)
            #if not os.path.exists(dirname):
            #    FileUndo._replay_io('makedirs', dirname)
            #FileUndo._replay_io('move', "%s/%s" % (tmp_dir,filename), src)
        elif type == "symlink":
            link_path = FileUndo._resolve_path(Xml.get_attribute(node, 'link'))
            for path in (dst, link_path):
                if path and os.path.lexists(path):
                    raise TransactionException('Redo would overwrite existing path: %s' % path)
            FileUndo._replay_io('makedirs', os.path.dirname(dst), exist_ok=True)
            cache_path = Xml.get_attribute(node, 'undo_cache')
            if cache_path and os.path.lexists(cache_path):
                if os.path.lexists(dst):
                    raise TransactionException('Redo would overwrite existing path: %s' % dst)
                FileUndo._replay_io('move', cache_path, dst)
                link_path = FileUndo._resolve_path(Xml.get_attribute(node, 'link'))
                link_cache = Xml.get_attribute(node, 'undo_link_cache')
                if link_cache and os.path.lexists(link_cache):
                    FileUndo._replay_io('move', link_cache, link_path)
                Xml.set_attribute(node, 'undone', 'false')
                return
            mode = Xml.get_attribute(node, 'mode')
            if mode in ('copy', 'hardlink'):
                link_path = FileUndo._resolve_path(Xml.get_attribute(node, 'link'))
                FileUndo._replay_intent('copy', '', link_path)
                with open(link_path, 'w', encoding='utf-8') as stream:
                    stream.write(src)
                if mode == 'hardlink':
                    FileUndo._replay_io('link', src, dst)
                elif os.path.isdir(src):
                    FileUndo._replay_io('copytree', src, dst)
                else:
                    FileUndo._replay_io('copyfile', src, dst)
            else:
                FileUndo._replay_io('symlink', os.path.relpath(src, os.path.dirname(dst)), dst,
                           target_is_directory=os.path.isdir(src))

        Xml.set_attribute(node, 'undone', 'false')

    redo = staticmethod(redo)


class FileUndoReplay:
    """File replay participant: a later SQL failure reverses completed IO."""

    def __init__(self, undo, ticket, base_dir='', nodes=()):
        self.undo = undo
        self.ticket = ticket
        self.base_dir = base_dir
        self.nodes = []
        self.source_paths = {}
        created = set()
        for node in nodes:
            if node.tag != 'file':
                continue
            kind = Xml.get_attribute(node, 'type')
            src = FileUndo._resolve_path(Xml.get_attribute(node, 'src'))
            dst = FileUndo._resolve_path(Xml.get_attribute(node, 'dst'))
            orig = FileUndo._resolve_path(Xml.get_attribute(node, 'orig'))
            # Uploaded bytes can be consumed by a later repository create.
            # Undo must return them before replaying the earlier upload/move.
            if kind == 'create' and orig in created and orig != src and Xml.get_attribute(node, 'source_move') != 'false':
                self.source_paths[node] = orig
            created.add(dst if kind in ('move', 'copy', 'symlink') else src)

    def start(self):
        pass

    def commit(self):
        pass

    def apply(self, node):
        FileUndo._check_access()
        kind = Xml.get_attribute(node, 'type')
        src = FileUndo._resolve_path(Xml.get_attribute(node, 'src'))
        dst = FileUndo._resolve_path(Xml.get_attribute(node, 'dst'))
        if not self.undo and self.base_dir and kind == 'create':
            rel_path = Xml.get_attribute(node, 'rel_path')
            if not rel_path:
                raise ValueError('Transferred repository creates require rel_path')
            src = os.path.join(Environment.get_asset_dir(), rel_path)
            Xml.set_attribute(node, 'src', FileUndo._stored_path(src))
        if self.undo:
            if Xml.get_attribute(node, 'undone') == 'true':
                return
            path = dst if kind in ('move', 'copy', 'remove', 'symlink') else src
            if kind != 'rmdir' and not os.path.lexists(path):
                raise TransactionException('Cannot undo missing path: %s' % path)
            if kind == 'rmdir' and os.path.lexists(src):
                raise TransactionException('Undo would overwrite existing directory: %s' % src)
            if node in self.source_paths:
                Xml.set_attribute(node, 'cache', self.source_paths[node])
            FileUndo.undo(node, self.ticket)
            self.nodes.append(deepcopy(node))
        else:
            path = dst if kind in ('move', 'copy', 'remove', 'symlink') else src
            if kind != 'rmdir' and os.path.lexists(path):
                raise TransactionException('Redo would overwrite existing path: %s' % path)
            if kind == 'symlink':
                link_path = FileUndo._resolve_path(Xml.get_attribute(node, 'link'))
                if link_path and os.path.lexists(link_path):
                    raise TransactionException('Redo would overwrite existing path: %s' % link_path)
            # Keep attempted IO too: copyfile may leave a partial destination.
            pending = deepcopy(node)
            Xml.set_attribute(pending, 'state', 'pending')
            Xml.set_attribute(pending, 'undone', 'false')
            self.nodes.append(pending)
            FileUndo.redo(node, self.ticket, self.base_dir)
            self.nodes[-1] = deepcopy(node)

    def rollback(self):
        if Transaction.get().file_journal:
            return  # The outer transaction compensates every physical replay intent in reverse order.
        failures = []
        for node in reversed(self.nodes):
            # Compensation owns these exact attempted nodes after the check-in scope closes.
            previous = Container.get('FileUndo:rollback')
            Container.put('FileUndo:rollback', node)
            try:
                if self.undo:
                    FileUndo.redo(node, self.ticket)
                else:
                    FileUndo.undo(node, self.ticket)
            except Exception as error:
                failures.append(error)
            finally:
                Container.put('FileUndo:rollback', previous)
        if failures:
            raise TransactionException('File replay rollback failed: %s' % failures[0]) from failures[0]
