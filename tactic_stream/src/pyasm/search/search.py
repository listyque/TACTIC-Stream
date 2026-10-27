"""TACTIC Search, SearchType and base SObject on native database resources.

The registry remains sthpw/search_object. There is no parallel asset/task model.
Objects stage values in memory; selected system and generic configured-system
types persist through native Command, ACLs, triggers and the transaction journal.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
import json
import logging
import re
import sqlite3
import uuid

from dateutil import parser

from pyasm.common.spt_date import SPTDate
from pyasm.common.lxml_wrapper import Xml
from pyasm.common.common import Base, Common, Container, jsondumps
from pyasm.common.errors import TacticException, UnsupportedContract
from pyasm.search.keys import SearchKey, breakup_search_type, build_search_type
from pyasm.search.storage import Store, identifier


class SearchException(TacticException):
    pass


class SObjectException(TacticException):
    pass


class SObjectValueException(SObjectException):
    pass


@dataclass(frozen=True)
class RequestContext:
    store: Store
    login: str
    project: str = "admin"
    language: str = "python"
    schemas: dict = field(default_factory=dict)
    schema_loading: set = field(default_factory=set)
    container: Container = field(default_factory=Container)
    read_connections: dict = field(default_factory=dict)


_context: ContextVar[RequestContext] = ContextVar("tactic_stream_request")


@contextmanager
def request_context(context: RequestContext):
    previous = _context.get(None)
    token = _context.set(context)
    try:
        yield context
    finally:
        try:
            if previous is not context:
                from pyasm.search.sql import DbContainer
                # Closing native connections discards unfinished writes.
                try:
                    DbContainer.close_all()
                finally:
                    for db in context.read_connections.values():
                        db.close()
                    context.read_connections.clear()
        finally:
            _context.reset(token)


class SObject:
    SEARCH_TYPE = "pyasm.search.SObject"

    SECURITY_TYPES = ('sthpw/login', 'sthpw/login_group', 'sthpw/login_in_group', 'sthpw/ticket')
    BUSINESS_TYPES = ('sthpw/transaction_state', 'sthpw/project', 'sthpw/project_type', 'sthpw/milestone', 'sthpw/task', 'sthpw/note', 'sthpw/work_hour', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log', 'config/process_state', 'config/custom_script', 'sthpw/custom_script', 'config/process', 'sthpw/snapshot', 'sthpw/file', 'sthpw/pref_setting', 'sthpw/retire_log', 'sthpw/pipeline', 'sthpw/connection', 'sthpw/search_object', 'sthpw/schema', 'config/naming', 'sthpw/sobject_list', 'config/plugin', 'config/plugin_content', 'config/url', 'config/widget_config', 'config/prod_setting', 'config/trigger', 'config/client_trigger', 'sthpw/trigger', 'config/pipeline', 'config/custom_property', 'config/ingest_rule', 'config/ingest_session', 'config/translation', 'sthpw/notification', 'sthpw/notification_log', 'sthpw/notification_login', 'sthpw/subscription', 'sthpw/interaction', 'sthpw/wdg_settings', 'sthpw/queue', 'sthpw/exception_log', 'sthpw/debug_log')

    def __init__(self, search_type, columns=None, result=None, remote=False, fast_data=None):
        if remote:
            raise UnsupportedContract("Remote SObjects are not migrated")
        context = _context.get()
        if fast_data:
            self.search_type_obj = fast_data['search_type_obj']
            self.full_search_type = fast_data['full_search_type']
            self.database = fast_data['database']
            self.db_resource = fast_data['db_resource']
        else:
            if isinstance(search_type, SearchType):
                self.search_type_obj = search_type
                search_type = search_type.get_base_key()
            elif search_type == 'sthpw/search_object':
                self.search_type_obj = self
            else:
                self.search_type_obj = SearchType.get(search_type)
            from pyasm.biz.project import Project
            self.full_search_type = Project.get_full_search_type(search_type)
            if self.full_search_type == 'sthpw/virtual':
                self.database = self.search_type_obj.get_database()
            else:
                _, self.database, _ = context.store.resolve(self.full_search_type, context.project)
            self.db_resource = Project.get_db_resource_by_search_type(self.full_search_type)
        if columns and fast_data:
            self.data = fast_data['data'][fast_data['count']]
            for name in fast_data.get('datetime_cols') or []:
                value = self.data.get(name)
                if value:
                    self.data[name] = str(value) if name in fast_data.get('time_cols', ()) else str(SPTDate.convert(value, is_gmt=True))
            for name in fast_data.get('boolean_cols') or []:
                self.data[name] = self.data.get(name) not in ('false', '', 0, None)
        elif isinstance(columns, dict) and result is None:
            # Internal metadata loaders may also supply row dictionaries.
            self.data = columns.copy()
        elif not columns:
            self.data = {self.get_id_col(): -1}
        else:
            self.data = {name: str(value) if isinstance(value, (datetime, time)) else value
                         for name, value in zip(columns, result)}
        self.update_data, self.quoted_flag = {}, {}
        self.prev_data, self.prev_update_data = {}, {}
        self.has_updates = False
        self.new_id = -1
        self.force_insert = self._skip_invalid_column = False
        self.update_description = None
        self.last_statement = None
        self.metadata = {}
        self.errors = []

    @classmethod
    def add_static_triggers(cls, search_type):
        '''for any kinds of insert run TaskCreatorTrigger to auto-create tasks where applicable'''
        from pyasm.command import Trigger
        event = "insert|%s" % search_type
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event, temp=True)
        trigger.set_value("mode", "same process,same transaction", temp=True)
        trigger.set_value("class_name", "tactic.command.TaskCreatorTrigger", temp=True)
        Trigger.append_static_trigger(trigger)

    def get(self, name, **kwargs):
        return self.get_value(name, **kwargs)

    def get_data(self, merged=True):
        if not merged:
            return self.data
        data = self.data.copy()
        data.update(self.update_data)
        return data

    def set_data(self, data):
        self.data = data.copy()

    def set_update_data(self, data):
        self.update_data = data.copy()

    def get_value(self, name, no_exception=False, auto_convert=True):
        if not name:
            return None
        parts = name.split("->>") if "->>" in name else name.split("->")
        name = parts[0]
        if self.has_updates and name in self.update_data:
            value = self.update_data[name]
            if len(parts) > 1:
                value = value or {}
                return value.get(parts[1]) if len(parts) == 2 else value.get(parts[1]).get(parts[2])
            # Pending values bypass the stored-data conversion and dictionary copy.
            return value
        if name not in self.data:
            if no_exception or (name != self.get_id_col() and self.get_id() == -1):
                return ""
            raise SObjectValueException(f"Column [{name}] does not exist in search_object type [{self.get_search_type()}]")
        value = self.data[name]
        if value and len(parts) > 1:
            value = value.get(parts[1]) if len(parts) == 2 else value.get(parts[1]).get(parts[2])
        if value and isinstance(value, (datetime, time)):
            return str(value)
        if value is None and auto_convert:
            data_type = SearchType.get_column_type(self.full_search_type, name)
            return 0 if data_type in ("integer", "float", "numeric", "decimal", "double precision") else ""
        return value.copy() if value and isinstance(value, dict) else value

    def get_attr_value(self, name):
        # Original column-backed SObjectAttr.get_value delegates to get_value.
        return self.get_value(name)

    def has_auto_current(self):
        '''determines whether new snapshots for this sobject are automatically
        set as the current.  This is true for most sobjects, however, some
        have the current explicitly set'''
        return True

    def has_value(self, name):
        name = name.split("->>")[0] if "->>" in name else name.split("->")[0]
        return name in self.update_data or name in self.data

    def column_exists(self, column):
        return SearchType.column_exists(self.full_search_type, column)

    def get_column_type(self, name):
        return SearchType.get_column_type(self.full_search_type, name)

    def skip_invalid_column(self):
        self._skip_invalid_column = True

    def validate_set_value(self, name, value):
        pass

    def process_value(self, name, value, column_type):
        quoted = True
        if column_type == "timestamp":
            quoted = False
            if isinstance(value, str):
                try:
                    value = parser.parse(value)
                except ValueError:
                    pass
            if isinstance(value, datetime):
                if value.tzinfo:
                    value = value.astimezone(timezone.utc)
                quoted = True
        elif value == "NULL":
            quoted = False
        elif column_type == "boolean":
            value = 1 if value in ("true", "True", 1, "1", True) else 0
            quoted = False
        return {"value": value, "quoted": quoted}

    def set_value(self, name, value, quoted=True, temp=False, no_exception=False, allow_none=False):
        self.validate_set_value(name, value)
        if name.find("->") != -1:
            parts = name.split("->")
            return self.set_data_value(parts[0], parts[1], value)
        if self._skip_invalid_column and not SearchType.column_exists(self.full_search_type, name):
            return
        if temp:
            self._set_value(name, value, quoted=quoted)
            return
        if not name:
            raise SObjectException(f"Name is None for value [{value}]")
        if value is None and not allow_none:
            if no_exception:
                return
            raise SObjectException(f"Value for [{name}] is None")
        column_type = SearchType.get_column_type(self.full_search_type, name)
        if isinstance(value, (list, tuple)):
            if not value:
                return
            value = value[0]
        info = self.process_value(name, value, column_type) if value is not None else None
        if info:
            value, quoted = info["value"], info["quoted"]
        from pyasm.common.environment import Environment
        from pyasm.biz.project import Project
        security = Environment.get_security()
        if security is not None:
            key = {'search_type': self.search_type_obj.get_base_key(), 'column': name,
                   'project': '*' if isinstance(self, Project) else Project.get_project_code()}
            if self.get_base_search_type() in ('sthpw/task', 'sthpw/note'):
                key['project'] = self.get_value('project_code', no_exception=True) or Project.get_project_code()
            elif self.get_base_search_type() == 'config/process_state':
                key['project'] = self.get_project_code()
            elif self.get_base_search_type() in ('sthpw/message', 'sthpw/message_log') and Container.get('Workflow:message_source'):
                key['project'] = Container.get('Workflow:message_source')[0].get_project_code()
            elif self.get_base_search_type() == 'sthpw/note' and Container.get('Workflow:note_source') is not None:
                key['project'] = Container.get('Workflow:note_source').get_project_code()
            elif not self.get_base_search_type().startswith(('sthpw/', 'config/')):
                key['project'] = self.get_project_code()
            if not security.check_access("sobject_column", key, "edit"):
                from pyasm.common.errors import SecurityException
                raise SecurityException("Column [%s] not editable for search type [%s]" % (name, self.get_search_type()))
        else:
            # Private/trusted bootstrap contexts still require an active admin.
            from pyasm.security.authenticator import Authenticator
            context = _context.get()
            with context.store.connection() as db:
                if not Authenticator._admin(db, context.login, context.store.get_db_resource().get_database_impl().get_parameter()):
                    raise UnsupportedContract("Staging non-admin edits requires Environment Security")
        column_info = SearchType.get_column_info(self.full_search_type).get(name) or {}
        if allow_none and value is None and column_info.get("nullable") is False:
            raise SObjectException(f"Column [{name}] does not allow NULL")
        if value is None or value == "":
            if column_info.get("data_type") == "timestamp":
                value = None
            elif column_info.get("data_type") in ("integer", "bigint", "float", "numeric", "decimal", "double precision"):
                if column_info.get("nullable"):
                    value = None
                else:
                    return
            elif column_info.get("nullable"):
                value = None
        elif column_info.get("data_type") in ("timestamp", "datetime", "datetime2"):
            try:
                value = str(parser.parse(value))
            except (ValueError, TypeError, OverflowError):
                pass
        self._set_value(name, value, quoted=quoted)

    def _set_value(self, name, value, quoted=True):
        if name in self.update_data or name not in self.data or value != self.data[name] or isinstance(value, dict):
            self.update_data[name] = value
            self.quoted_flag[name] = quoted
        self.has_updates = True

    def set_data_value(self, column, name, value, quoted=True):
        if isinstance(value, str):
            try:
                try:
                    integer = int(value)
                except ValueError:
                    integer = ""
                number = float(value)
                value = integer if integer == number else number
            except ValueError:
                pass
        data = self.get_json_value(column, default={}).copy()
        data[name] = value
        self.set_value(column, data)

    def get_json_value(self, name, default=None, no_exception=False):
        value = self.get_value(name, no_exception=no_exception)
        if isinstance(value, dict):
            return value.copy()
        if not isinstance(value, str):
            return value
        if value.startswith("zlib:"):
            value = Common.decompress_transaction(value)
        if not value.strip():
            return default
        try:
            return json.loads(value)
        except ValueError:
            return value

    def set_json_value(self, name, value):
        if value is None or SearchType.get_column_type(self.full_search_type, name) == "json":
            self.set_value(name, value)
            return
        data = jsondumps(value)
        if len(data) > 10 * 1024:
            data = Common.compress_transaction(data)
        self.set_value(name, data)

    def get_xml_root(self, name):
        return name

    def get_xml_value(self, name, root=None, strip_cdata=True, remove_blank_text=True):
        from pyasm.common.lxml_wrapper import Xml, XmlException
        cache = Container.get('SObject:xml_cache')
        if cache is None:
            cache = {}
            Container.put('SObject:xml_cache', cache)
        search_key = self.get_search_key()
        cached = cache.get('%s|%s' % (search_key, name))
        if cached is not None:
            return cached
        root = root or self.get_xml_root(name)
        value = self.get_value(name)
        if value is None:
            value = ''
        if value.startswith('zlib:'):
            value = Common.decompress_transaction(value)
        # Reject declarations before the original malformed-XML fallback.
        if '<!DOCTYPE' in value or '<!ENTITY' in value:
            raise XmlException('DTD/entities are not accepted')
        xml = Xml(strip_cdata=strip_cdata)
        try:
            xml.read_string(value or '<%s/>' % root, remove_blank_text=remove_blank_text)
        except XmlException as exc:
            xml.read_string('<%s/>' % root)
            # The legacy UI warning queue is absent; report failures in the log.
            logging.getLogger(__name__).warning('Xml read error for [%s]: %s', search_key, exc)
        # Original reads pre-filled cache entries, but does not cache this result.
        return xml

    def get_metadata_xml(self):
        # The original name remains, although current TACTIC metadata uses JSON.
        if not self.metadata:
            self.metadata = self.get_json_value("metadata") or {}
        return self.metadata

    def get_metadata(self):
        self.metadata = self.get_json_value("metadata") or {}
        return self.metadata

    def get_metadata_value(self, name):
        value = self.metadata.get(name)
        return "" if value is None else value

    def get_metadata_dict(self):
        return self.get_metadata_xml()

    def set_metadata_value(self, name, value):
        metadata = self.get_metadata_xml()
        if isinstance(metadata, str):
            metadata = {}
        metadata[name] = value
        self.set_json_value("metadata", metadata)

    def add_metadata(self, data, replace=False):
        '''takes a whole dictionary of values and sets them'''
        if not isinstance(data, dict):
            raise ValueError('Metadata must be a dictionary')
        if replace:
            self.metadata = dict(data)
            self.set_json_value('metadata', self.metadata)
        else:
            for name, value in data.items():
                self.set_metadata_value(name, value)

    def get_seq_value(self, name, delimiter=","):
        value = self.get_value(name)
        return [] if value == "" else value.split(delimiter)

    def get_dict_value(self, name, delimiter=","):
        return {value: "" for value in self.get_seq_value(name, delimiter)}

    def get_datetime_value(self, name):
        value = self.get_value(name)
        return value if isinstance(value, datetime) else parser.parse(value) if value else None

    def get_datetime_display(self, name, format):
        value = self.get_value(name)
        return parser.parse(value).strftime(format) if value else ""

    def get_columns(self):
        return SearchType.get_columns(self.get_search_type())

    # Directory structure functions
    def get_repo_handler(self, snapshot):
        '''Projects can define which repo handler is used.
        This gives the ability to use different styles and or 3rd party
        repositories such as Perforce or Subversion'''
        from pyasm.biz import Project
        repo_handler = Project.get_project_repo_handler()
        repo_handler.set_snapshot(snapshot)
        repo_handler.set_sobject(self)
        return repo_handler

    def get_repo(self, snapshot):
        '''get the repo for this specific snapshot'''
        repo_handler = self.get_repo_handler(snapshot)
        return repo_handler.get_repo()


    def get_web_dir(self,snapshot=None,file_type=None, file_object=None):
        '''The http sobject directory from the client point of view.
        The details are handled by the project class'''
        from pyasm.biz import Project
        dir = Project.get_project_web_dir(self,snapshot,file_type,file_object=file_object)
        return dir

    def get_lib_dir(self,snapshot=None,file_type=None, create=False, file_object=None, dir_naming=None):
        '''The nfs sobject directory from the server point of view.
        The details are handled by the project class'''
        from pyasm.biz import Project
        dir = Project.get_project_lib_dir(self,snapshot,file_type, create=create, file_object=file_object, dir_naming=dir_naming)
        return dir

    def get_env_dir(self,snapshot=None,file_type=None):
        '''This retrieves the unexpanded directory:
        $TACTIC_ASSET_DIR/bar/shot/...
        '''
        from pyasm.biz import Project
        dir = Project.get_project_env_dir(self,snapshot,file_type)
        return dir



    def get_remote_web_dir(self, snapshot=None, file_type=None):
        '''get_web_dir with the full http link.
        All web directories are, by default, relative links.  This function
        will force a full link, including the http://<server> part'''
        from pyasm.biz import Project
        dir = Project.get_project_remote_web_dir(self,snapshot,file_type)
        return dir


    def get_client_lib_dir(self, snapshot=None, file_type=None, create=False, file_object=None, dir_naming=None):
        '''The asset directory from the client point of view.  This is only
        valid if this directory is visible to the client'''
        # for now assume the same directory as the server
        from pyasm.biz import Project
        dir = Project.get_project_client_lib_dir(self,snapshot,file_type,\
                create=create, file_object=file_object, dir_naming=dir_naming)
        return dir


    def get_local_dir(self, snapshot=None):
        '''finds the local directory on the client to download files to'''
        from pyasm.common import Config
        base_dir = Config.get_value("checkin","win32_local_base_dir")
        return "%s/download" % (base_dir)



    def get_local_repo_dir(self, snapshot=None, file_type=None, file_object=None):
        '''the local sync of the Tactic repository'''
        from pyasm.biz import Project
        dir = Project.get_project_local_repo_dir(self,snapshot,file_type, file_object=file_object)
        return dir


    def get_sandbox_dir(self, snapshot=None, file_type=None):
        '''the local sandbox(work area) designated by Tactic'''
        from pyasm.biz import Project
        dir = Project.get_project_sandbox_dir(self,snapshot,file_type)
        return dir

    def get_relative_dir(self, snapshot=None, file_type=None, create=False, file_object=None, dir_naming=None):
        '''the relative direcory without any base'''
        from pyasm.biz import Project
        dir = Project.get_project_relative_dir(self,snapshot,file_type, create=create, file_object=file_object, dir_naming=dir_naming)
        return dir



    def get_column_info(self, column=None):
        info = SearchType.get_column_info(self.get_search_type())
        return info if not column else info.get(column) or {}

    def get_id_col(self):
        return "id"

    def get_code_col(self):
        return "code"

    def get_id(self):
        return self.get_value(self.get_id_col(), no_exception=True)

    def get_code(self):
        return self.get_value("code") if self.has_value("code") else str(self.get_id())

    def get_display_value(self, long=False):
        from pyasm.biz import Schema
        schema = Schema.get()
        base_search_type = self.get_base_search_type()
        attrs = schema.get_attrs_by_search_type(base_search_type)

        display = attrs.get("display")
        if display:
            # evaluate the expression
            from pyasm.biz import ExpressionParser
            parser = ExpressionParser()
            result = parser.eval(display, self, single=True)
            return result
        else:
            return self.get_name(long=long)

    def get_name(self, long=False):
        name = self.get_value("name") if self.has_value("name") else ""
        if long:
            code = self.get_code()
            if name:
                return f"{name} ({code})"
            search_id = self.get_id()
            return f"{code} ({search_id})" if code != search_id else code
        return name or self.get_code()

    def get_description(self):
        return self.get_value("description") if self.has_value("description") else self.get_code()

    def get_primary_key(self):
        return 'id'

    def get_primary_key_value(self):
        return self.get_value(self.get_primary_key())

    def is_insert(self):
        return self.get_id() in (-1, "-1", "")

    def set_id(self, value):
        self.new_id = value

    def set_force_insert(self, force=True):
        self.force_insert = force

    def get_prev_value(self, name):
        return self.prev_data.get(name)

    def get_prev_update_data(self):
        return self.prev_update_data

    def get_update_description(self):
        return self.update_description

    def get_search_type(self):
        return self.full_search_type

    def get_search_type_obj(self):
        return self.search_type_obj

    def get_database(self):
        return self.database

    def get_database_type(self):
        return self.db_resource.get_database_type()

    def get_db_resource(self):
        return self.db_resource

    def get_database_impl(self):
        return self.get_db_resource().get_database_impl()

    def get_sql(self):
        return self.get_db_resource().get_sql()

    def get_last_statement(self):
        return self.last_statement





    def get_table(self):
        return self.get_search_type_obj().get_table()

    @classmethod
    def get_icon_context(cls, context=None):
        '''gives various widgets (namely the ThumbWdg) an indication of
        which context of this asset provides an appropriate icon'''
        if context:
            return context
        else:
            return 'icon'

    def get_base_search_type(self):
        return SearchKey.extract_base_search_type(self.full_search_type)

    def get_project_code(self):
        from pyasm.biz.project import Project
        return SearchKey.extract_project(self.full_search_type) or Project.get_project_code()

    def get_search_key(self, use_id=False):
        return SearchKey.get_by_sobject(self, use_id=use_id)

    def get_project(self):
        from pyasm.biz import Project
        project_code = self.get_project_code()
        return Project.get_by_code(project_code)

    def get_schema(self):
        from pyasm.biz.schema import Schema
        return Schema.get_by_sobject(self)

    def set_sobject_value(self, sobject, type=None):
        from pyasm.biz.schema import Schema
        schema = Schema.get()
        # Original set_sobject_value does not filter relationships by the optional type.
        attrs = schema.get_relationship_attrs(self.get_base_search_type(), sobject.get_base_search_type())
        attrs = schema.resolve_relationship_attrs(attrs, self.get_search_type(), sobject.get_search_type())
        relationship = attrs.get("relationship")
        if relationship in ("search_type", "search_code", "search_id"):
            self.set_value("search_type", sobject.get_search_type())
            if SearchType.column_exists(self.full_search_type, "search_id"):
                search_id = sobject.get_id()
                self.set_value("search_id" if isinstance(search_id, int) else "search_code", search_id)
            if SearchType.column_exists(self.full_search_type, "search_code") and SearchType.column_exists(sobject.get_search_type(), "code"):
                self.set_value("search_code", sobject.get_value("code"))
        elif relationship == "code":
            forward = attrs.get("to") != self.get_base_search_type()
            self.set_value(attrs.get("from_col") if forward else attrs.get("to_col"),
                           sobject.get_value(attrs.get("to_col") if forward else attrs.get("from_col")))
        elif relationship == "general":
            return
        else:
            raise SearchException(f"Relationship [{relationship}] is not supported")

    def set_parent(self, sobject, relationship=None):
        schema = self.get_schema()
        if isinstance(sobject, str):
            key = sobject
            sobject = SearchKey.get_by_search_key(key)
            if not sobject:
                raise SearchException(f"Parent [{key}] not found")
        search_type, related_type = self.get_base_search_type(), sobject.get_base_search_type()
        relationship = relationship or schema.get_relationship(self.get_search_type(), sobject.get_search_type())
        if relationship in ("search_type", "search_code", "search_id"):
            self.set_sobject_value(sobject, type="hierarchy")
        elif relationship in ("foreign_key", "code", "id"):
            attrs = schema.get_relationship_attrs(search_type, related_type, path=None)
            forward = attrs.get("to") != search_type
            self.set_value(attrs.get("from_col") if forward else attrs.get("to_col"),
                           sobject.get_value(attrs.get("to_col") if forward else attrs.get("from_col")))
        elif relationship == "parent_code":
            self.set_value("parent_code", sobject.get_code())
        elif relationship == "search_key":
            self.set_value("search_key", sobject.get_search_key())
        else:
            raise SearchException(f"Parent relationship [{relationship}] is not supported")

    def get_collection_type(self):
        return SearchType.get_collection_type(self.get_base_search_type())

    def get_collections(self):
        collection_type = SearchType.build_search_type(self.get_collection_type(), self.get_project_code())
        search = Search(collection_type)
        search.add_column('parent_code')
        search.add_filter('search_code', self.get_code())
        collections = Search(self.get_search_type())
        collections.add_search_filter('code', search)
        return collections.get_sobjects()

    def add_to_collection(self, collection):
        from pyasm.command import Trigger
        if collection.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise SearchException('SObject [%s] is not a collection' % collection.get_code())
        if self.get_base_search_type() != collection.get_base_search_type() or self.get_project_code() != collection.get_project_code() or self.get_db_resource().get_key() != collection.get_db_resource().get_key():
            raise SearchException('Collection and member must belong to the same SearchType and database')
        if self.get_id() == -1 or collection.get_id() == -1 or not self.get_code() or not collection.get_code():
            raise SearchException('Collection and member must be saved and have codes')
        collection_type = SearchType.build_search_type(self.get_collection_type(), self.get_project_code())
        search_code, parent_code = self.get_code(), collection.get_code()
        sql = self.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(collection_type).get_table())
        targets = Search(self.get_search_type())
        targets.add_filters('id', [self.get_id(), collection.get_id()])
        saved = {obj.get_id(): obj for obj in targets.get_sobjects()}
        if any(obj.get_id() not in saved or obj.get_code() != saved[obj.get_id()].get_code() for obj in (self, collection)) or saved[collection.get_id()].get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise SearchException('Collection or member no longer exists or changed')
        search = Search(collection_type)
        search.add_filter('search_code', search_code)
        search.add_filter('parent_code', parent_code)
        if search.get_sobject():
            return
        # The original SObject path bypassed the command's cycle check.
        statement = sql.get_database_impl().get_child_codes_cte(collection_type, self.get_search_type(), search_code)
        if search_code == parent_code or any(row[0] == parent_code for row in sql.do_query(statement)):
            raise SearchException('Circular collection relationship')
        item = SearchType.create(collection_type)
        item.set_value('search_code', search_code)
        item.set_value('parent_code', parent_code)
        item.commit()
        output = {'mode': 'add', 'search_key': self.get_search_key(), 'id': self.get_id(),
                  'search_type': self.get_search_type(), 'collection': collection.get_sobject_dict(),
                  'sobject': self.get_sobject_dict()}
        Trigger.call(self, 'collection|%s' % self.get_base_search_type(), output, project_code=self.get_project_code())

    def add_relationship(self, sobject, relationship=None):
        return self.set_parent(sobject, relationship=relationship)

    def connect(self, sobjects=[], context="reference"):
        if not isinstance(sobjects, list):
            sobjects = [sobjects]
        from pyasm.biz import SObjectConnection
        for sobject in sobjects:
            if isinstance(sobject, str):
                sobject = Search.get_by_search_key(sobject)
            if not sobject:
                raise SearchException('Connected SObject does not exist')
            SObjectConnection.create(self, sobject, context=context)

    def get_connections(self, context="reference"):
        from pyasm.biz import SObjectConnection
        connections, sobjects = SObjectConnection.get_connected_sobjects(self, context=context)
        return sobjects

    def add_related_sobject(self, sobject, src_path=None):
        if isinstance(sobject, str):
            sobject = SearchKey.get_by_search_key(sobject)
        schema = self.get_schema()
        search_type, related_type = self.get_base_search_type(), sobject.get_base_search_type()
        attrs = schema.get_relationship_attrs(search_type, related_type, path=src_path)
        relationship = attrs.get("relationship")
        if relationship == "search_type":
            attrs = schema.resolve_relationship_attrs(attrs, search_type, related_type)
            relationship = attrs['relationship']
        if relationship == "search_code":
            self.set_value("search_type", sobject.get_search_type())
            self.set_value("search_code", sobject.get_code())
            self.set_value("search_id", sobject.get_id())
        elif relationship == "search_id":
            self.set_value("search_type", sobject.get_search_type())
            self.set_value("search_id", sobject.get_id())
        else:
            forward = attrs.get("to") != search_type
            self.set_value(attrs.get("from_col") if forward else attrs.get("to_col"),
                           sobject.get_value(attrs.get("to_col") if forward else attrs.get("from_col")))

    def add_related_connection(self, src_sobject, dst_sobject, src_path=None):
        self.add_related_sobject(src_sobject, src_path=src_path)
        self.add_related_sobject(dst_sobject)

    def set_user(self, user=None):
        self.set_value("login", _context.get().login if user is None else user)

    def set_project(self, project_code=None):
        self.set_value("project_code", project_code or _context.get().project)

    def is_retired(self):
        return self.get_value("s_status", no_exception=True) == "retired"

    def get_foreign_key(self):
        return SearchType.get_foreign_key(self.get_base_search_type())

    def get_related_sobject(self, related_type, filters=[], show_retired=False):
        search = Search(related_type)
        search.set_show_retired(show_retired)
        search.add_op_filters(filters)
        search.add_relationship_filter(self)
        return search.get_sobject()

    def get_related_sobjects(self, related_type, filters=[], path=None, show_retired=False):
        from pyasm.biz.schema import Schema
        attrs = Schema.get(project_code=self.get_project_code()).get_relationship_attrs(self.get_base_search_type(), related_type)
        if attrs.get("relationship") == "many_to_many":
            raise UnsupportedContract("Many-to-many relationships are not migrated yet")
        search = Search(related_type)
        search.set_show_retired(show_retired)
        search.add_op_filters(filters)
        search.add_relationship_filter(self, path=path)
        return search.get_sobjects()

    def get_parent_search_key(self):
        search_type = self.get_value("search_type")
        search_code = self.get_value("search_code", no_exception=True)
        column, identity = ("code", search_code) if search_code else ("id", self.get_value("search_id"))
        return SearchKey.build_search_key(search_type, identity, column=column)

    def get_parent(self, parent_type=None, columns=[], show_retired=False):
        # The original columns argument is deprecated and ignored.
        if not parent_type:
            schema = self.get_schema()
            parent_type = schema.get_parent_type(self.get_base_search_type())
        if parent_type == "*":
            attrs = schema.get_relationship_attrs("*", self.get_base_search_type())
            prefix = attrs.get("prefix", "")
            prefix = prefix + "_" if prefix else ""
            search_type = self.get_value(prefix + "search_type", no_exception=True)
            if not search_type:
                return None
            attrs = schema.resolve_relationship_attrs(attrs, self.get_search_type(), search_type)
            relationship = attrs.get("relationship")
            # Original wildcard lookup includes retired parents, regardless of this flag.
            if relationship == "search_code":
                identity = self.get_value(prefix + "search_code")
                if SearchType.column_exists(search_type, "code"):
                    return Search.get_by_code(search_type, identity)
                return Search.get_by_id(search_type, identity)
            if relationship == "search_id":
                return Search.get_by_id(search_type, self.get_value(prefix + "search_id"))
            return None
        if parent_type:
            return self.get_related_sobject(parent_type, show_retired=show_retired)
        return None

    def get_reference(self, search_type):
        return self.get_parent(search_type)

    def get_all_children_search(self, child_type):
        search = Search(child_type)
        return self.children_alter_search(search, child_type)

    def children_alter_search(self, search, child_type):
        schema = self.get_schema()
        relationship = schema.get_relationship(self.get_base_search_type(), child_type)
        if relationship in ("search_type", "search_code"):
            search.add_filter("search_type", self.get_search_type())
            search.add_filter("search_id" if relationship == "search_type" else "search_code",
                              self.get_id() if relationship == "search_type" else self.get_code())
        elif relationship == "search_key":
            search.add_filter("search_key", self.get_search_key())
        elif relationship == "parent_code":
            search.add_filter("parent_code", self.get_code())
        elif relationship in ("code", "id"):
            attrs = schema.get_relationship_attrs(child_type, self.get_base_search_type())
            column = attrs.get("from_col") if relationship == "id" or attrs["from"] in (child_type, "*") else attrs.get("to_col")
            search.add_filter(column or self.get_foreign_key(), self.get_id() if relationship == "id" else self.get_code())
        elif relationship == "general":
            search.add_relationship_filter(self)
        elif relationship == "instance":
            search.add_relationship_filter(self)
        elif relationship == "many_to_many":
            raise UnsupportedContract("Many-to-many relationship mode is not migrated")
        else:
            column = self.get_foreign_key()
            search.add_filter("asset_library" if column == "asset_library_code" else column, self.get_code())
        return search

    def get_all_children(self, child_type):
        return self.get_all_children_search(child_type).get_sobjects()

    def get_child(self, child_type):
        children = self.get_all_children(child_type)
        return children[0] if children else None

    @staticmethod
    def get_values(sobjects, attr_name, unique=False, no_exception=False):
        values = [obj.get_value(attr_name, no_exception=no_exception) for obj in sobjects or []]
        return sorted(set(values)) if unique else values

    def get_sobject_dict(self, columns=None, use_id=False, language="python", mode="normal"):
        if mode == "fast":
            raw = self.get_data()
            data = {name: raw[name] for name in columns if name in raw} if columns else raw
        elif mode == "normal":
            if self.get_base_search_type() == 'sthpw/virtual':
                columns = set(self.data) | set(self.update_data)
            data = {}
            for name in columns or SearchType.get_columns(self.full_search_type):
                value = self.get_metadata_dict() if name == "metadata" else self.get_value(name, no_exception=True)
                data[name] = None if language == "c#" and value == "" else value
        else:
            raise UnsupportedContract("Unsupported SObject serialization mode")
        data.update(__search_key__=self.get_search_key(use_id), __search_type__=self.get_base_search_type())
        return data

    def validate(self):
        return True

    def handle_commit_security(self):
        from pyasm.common.environment import Environment
        from pyasm.security.access_manager import Sudo
        security = Environment.get_security()
        if security is not None:
            if security.is_admin() or Sudo.is_sudo():
                return True
            return self.get_base_search_type() not in ['config/custom_script']
        from pyasm.security.authenticator import Authenticator
        context = _context.get()
        with context.store.connection() as db:
            if Authenticator._admin(db, context.login, context.store.get_db_resource().get_database_impl().get_parameter()):
                return True
        raise UnsupportedContract("SObject commit security is migrated only for active admin")

    @staticmethod
    def alter_search(search):
        '''allow the sobject to alter the search'''
        pass

    def store_version(self):
        # The original versioning flag is hardcoded False.
        pass

    def get_defaults(self):
        from pyasm.biz.prod_setting import ProjectSetting
        defaults = {}
        autofill = ProjectSetting.get_value_by_key('autofill_pipeline_code')
        if autofill != 'false' and self.get_base_search_type() != "sthpw/task" and SearchType.column_exists(self.get_search_type(), "pipeline_code"):
            from pyasm.biz.pipeline import Pipeline
            pipelines = Pipeline.get_by_search_type(self.get_base_search_type())
            if pipelines:
                defaults['pipeline_code'] = pipelines[0].get_code()
        return defaults

    def get_code_key(self):
        from pyasm.biz.prod_setting import ProjectSetting
        prefix = ProjectSetting.get_value_by_key('code_prefix', self.get_base_search_type())
        if prefix.startswith('{') and prefix.endswith('}'):
            raise UnsupportedContract("Expression-based code prefixes are not migrated")
        return prefix or self.get_table().upper()

    def set_random_code(self):
        search_code = self.generate_code()
        self.set_value("code", search_code)
        return search_code

    def generate_code(self, id=None):
        from pyasm.biz.prod_setting import ProjectSetting
        parts = [self.get_code_key()]
        # Owned local configuration has no install.server prefix.
        if id is None or ProjectSetting.get_value_by_key('code_format', self.get_base_search_type()) == 'random':
            parts.append(Common.generate_random_key(digits=10))
        else:
            try:
                padding = 8 if self.get_base_search_type() in (
                    'sthpw/file', 'sthpw/snapshot', 'sthpw/transaction_log',
                    'sthpw/ticket', 'sthpw/task', 'sthpw/sync_job', 'sthpw/sync_log') else 5
                int(id)
                parts.append(('%%0.%dd' % padding) % id)
            except Exception:
                parts.append(str(id))
        return ''.join(parts)

    def set_defaults(self):
        for name, value in self.get_defaults().items():
            if value is not None and (not self.has_value(name) or self.get_value(name) is None):
                self.set_value(name, value)
        if SearchType.column_exists(self.full_search_type, "timestamp") and not self.get_value("timestamp", no_exception=True):
            from pyasm.search.sql import DbContainer
            sql = DbContainer.get(self.get_db_resource())
            self.set_value("timestamp", sql.get_timestamp_now(), quoted=False)

    @staticmethod
    def is_day_column(col):
        return col.endswith("day")

    def get_statement(self):
        return self.commit(return_sql=True)

    def set_auto_code(self):
        unique_id = uuid.uuid1()
        self.set_value('code', '%s_%s' % (self.get_code_key(), unique_id))

    @classmethod
    def create_new(cls):
        return SearchType.create(cls.SEARCH_TYPE)

    def on_insert(self):
        pass

    def on_update(self):
        pass

    def on_delete(self):
        pass

    def build_update_description(self, is_insert=True):
        action = "Inserted" if is_insert else "Updated"
        title = self.get_search_type_obj().get_value("title", no_exception=True)
        code, name = self.get_code(), self.get_name()
        if code == name:
            return "%s %s: %s" % (action, title, code)
        return "%s %s: %s %s" % (action, title, code, name)

    def set_now(self, column="timestamp"):
        from pyasm.search.sql import DbContainer
        sql = DbContainer.get(self.db_resource)
        self.set_value(column, sql.get_timestamp_now(), quoted=False)

    def _get_self_instance_search(self, instance_type, sobject=None):
        if not instance_type:
            raise ValueError('No instance_type defined')
        schema = self.get_schema()
        owner_edge, member_edge = schema._get_self_instance_edges(instance_type, self.get_base_search_type())
        search = Search(build_search_type(instance_type, self.get_project_code()))
        if search.null_filter:
            from pyasm.common.errors import SecurityException
            raise SecurityException('Instance search type is not accessible: ' + instance_type)
        for obj, edge in ((self, owner_edge), (sobject, member_edge)):
            if obj is None:
                continue
            if (obj.get_search_type() != self.get_search_type()
                    or obj.get_db_resource().get_key() != search.get_db_resource().get_key()):
                raise UnsupportedContract('Self-instance endpoints require one type, project and database resource')
            if obj.get_id() == -1:
                raise ValueError('Self-instance endpoints must be saved')
            saved = Search(obj.get_search_type())
            saved.add_id_filter(obj.get_id())
            keys = saved._get_sobject_values(edge['to_col'])
            if not keys:
                raise LookupError('Self-instance endpoint no longer exists or is not accessible')
            value = obj.get_value(edge['to_col'])
            if value in ('', None) or value != keys[0]:
                raise ValueError('Self-instance endpoint key is empty or changed')
            search.add_filter(edge['from_col'], value)
        return search

    def add_instance(self, sobject):
        search_type1 = self.get_base_search_type()
        search_type2 = sobject.get_base_search_type()

        from pyasm.biz import Schema
        schema = self.get_schema() if search_type1 == search_type2 else Schema.get()
        attrs = schema.get_relationship_attrs(search_type1, search_type2)
        relationship = attrs.get("relationship")
        if relationship != "instance":
            raise SearchException("Not an instance relationship")

        # get the instance
        instance_type = attrs.get("instance_type")

        if search_type1 == search_type2:
            search = self._get_self_instance_search(instance_type, sobject)
            instance = SearchType.create(search.get_search_type())
            # The source overwrote one endpoint by resolving the same path twice.
            instance.add_related_sobject(self, src_path='child')
            instance.add_related_sobject(sobject, src_path='parent')
        else:
            instance = SearchType.create(instance_type)
            instance.add_related_sobject(self)
            instance.add_related_sobject(sobject)
        instance.commit()

        return instance

    def get_instances(self, search_type2):

        search_type1 = self.get_base_search_type()

        from pyasm.biz import Schema
        same_type = search_type1 == SearchKey.extract_base_search_type(search_type2)
        schema = self.get_schema() if same_type else Schema.get()
        attrs = schema.get_relationship_attrs(search_type1, search_type2)
        relationship = attrs.get("relationship")
        if relationship != "instance":
            raise SearchException("Not an instance relationship")

        # get the instance
        instance_type = attrs.get("instance_type")

        if same_type:
            from pyasm.biz import Project
            if Project.get_full_search_type(search_type2, project_code=self.get_project_code()) != self.get_search_type():
                raise UnsupportedContract('Self-instance endpoints require one type, project and database resource')
            return self._get_self_instance_search(instance_type).get_sobjects()

        expression = "@SOBJECT(%s)" % (instance_type)
        instances = Search.eval(expression, self)

        return instances

    def remove_instance(self, sobject):
        search_type1 = self.get_base_search_type()
        search_type2 = sobject.get_base_search_type()

        from pyasm.biz import Schema
        schema = self.get_schema() if search_type1 == search_type2 else Schema.get()
        attrs = schema.get_relationship_attrs(search_type1, search_type2)
        relationship = attrs.get("relationship")
        if relationship != "instance":
            raise SearchException("Not an instance relationship")

        instance_type = attrs.get("instance_type")

        if search_type1 == search_type2:
            for instance in self._get_self_instance_search(instance_type, sobject).get_sobjects():
                instance.delete()
        else:
            expression = "@SOBJECT(%s)" % (instance_type)
            from_instances = Search.eval(expression, self)
            to_instances = Search.eval(expression, sobject)
            for from_instance in from_instances:
                from_search_key = from_instance.get_search_key()
                for to_instance in to_instances:
                    if from_search_key == to_instance.get_search_key():
                        to_instance.delete()

        # NOTE: need to clear the expression cache.  This may be a little
        # too heavy, but it is assumed that this operation does not
        # happen too often
        from pyasm.biz import ExpressionParser
        ExpressionParser.clear_cache()

    def _check_repository_write(self, access=None):
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException
        from pyasm.search.transaction import FileUndo
        FileUndo._check_access()
        scope = Container.get('Checkin:writing')
        parent = scope.get('parent') if scope else None
        if parent is None:
            raise SecurityException('Repository metadata requires its check-in parent')
        replay_node = scope.get('replay_node')
        if replay_node is not None and (replay_node.get('search_type') != self.get_base_search_type() or
                replay_node.get('search_code') != self.get_code()):
            raise SecurityException('Repository replay only permits its validated current journal record')
        parent._check_business_write('edit')
        anchors = {'search_type': parent.get_search_type(), 'search_code': parent.get_code(), 'search_id': parent.get_id()}
        if any(str(self.get_value(name, no_exception=True) or '') not in ('', str(expected))
               for name, expected in anchors.items()):
            raise SecurityException('Repository record belongs to another object')
        if self.get_value('search_type') != anchors['search_type'] or self.get_value('search_code') != anchors['search_code']:
            raise SecurityException('Repository record requires its exact parent identity')
        project = parent.get_value('project_code', no_exception=True) or parent.get_project_code()
        if self.get_value('project_code') != project:
            raise SecurityException('Repository record requires its own project')
        security = Environment.get_security()
        inserting = self.force_insert or self.get_id() in (-1, '-1', '')
        if not inserting:
            current = Search(self.get_search_type())
            current.add_id_filter(self.get_id())
            current = current.get_sobject()
            if current is None or any(str(self.get_value(name, no_exception=True)) != str(current.get_value(name, no_exception=True))
                    for name in (*anchors, 'project_code')):
                raise SecurityException('Repository ownership cannot be changed')
            if current.get_value('code') and self.get_value('code') != current.get_value('code'):
                raise SecurityException('Repository code cannot be changed')
            if (scope.get('replay_node') is None and current.get_value('snapshot_code', no_exception=True) and
                    self.get_value('snapshot_code', no_exception=True) != current.get_value('snapshot_code')):
                raise SecurityException('File snapshot cannot be changed')
        if self.get_base_search_type() == 'sthpw/snapshot':
            if self.get_value('project_code') != project or (inserting and self.get_value('login') != _context.get().login):
                raise SecurityException('Snapshot requires its own project and authenticated author')
        elif self.get_value('snapshot_code'):
            snapshot = Search.get_by_code('sthpw/snapshot', self.get_value('snapshot_code'))
            if snapshot is None or any(str(snapshot.get_value(name, no_exception=True) or '') not in ('', str(expected))
                    for name, expected in anchors.items()):
                raise SecurityException('File requires a snapshot of its own parent')
        base = self.get_base_search_type()
        # Chat/profile uploads use their validated owner scope and native edit grant.
        attachment = Container.get('Chat:attachment') or (Container.get('UserProfile:writing') or {}).get('avatar')
        operation = 'edit' if attachment and access != 'delete' else access or ('insert' if inserting else 'edit')
        if not security.check_access('search_type', [{'code': base}, {'code': base, 'project': project},
                {'code': '*'}, {'code': '*', 'project': project}], operation, default='deny'):
            raise SecurityException('Repository search type access denied: ' + base)
        for name in self.update_data if operation != 'delete' else ():
            if not security.check_access('sobject_column', {'search_type': base, 'column': name, 'project': project}, 'edit'):
                raise SecurityException('Repository column is not editable: ' + name)
        return project

    def _check_business_write(self, access=None):
        from pyasm.security.authenticator import Authenticator
        from pyasm.common.errors import SecurityException
        context = _context.get()
        system = context.store.get_db_resource()
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction() or not transaction.can_write_resource(self.get_db_resource()):
            raise UnsupportedContract('Business writes require an active system or registered-project transaction')
        base = self.get_base_search_type()
        if base == 'sthpw/queue' and Container.get('CheckinQueue:writing') is self:
            from pyasm.common import Environment
            from tactic.command.checkin_queue_cmd import JOB_COMMAND, QUEUE, BATCH_QUEUE
            security = Environment.get_security()
            if (access == 'delete' or security is None or not security.is_logged_in()
                    or security.get_user_name() != context.login or self.get_value('login') != context.login
                    or self.get_value('project_code') != context.project
                    or self.get_value('command') != JOB_COMMAND or self.get_value('queue') not in (QUEUE, BATCH_QUEUE)):
                raise SecurityException('Check-in queue writes must retain their authenticated owner and fixed command')
            from tactic_stream.server.navigation_links import check_project
            check_project(context.project)
            return
        if base in ('sthpw/snapshot', 'sthpw/file') and Container.get('Checkin:writing'):
            with context.store.connection() as db:
                admin = Authenticator._admin(db, context.login, system.get_database_impl().get_parameter())
            if not admin:
                self._check_repository_write(access)
                return
        from pyasm.security import Sudo
        if base == 'sthpw/sobject_list' and Sudo.is_sudo():
            return
        workflow = Container.get('Workflow:writing')
        if Container.get('Workflow:replay'):
            from pyasm.command.workflow import _check_replay_effect
            if base in ('config/process_state', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log'):
                _check_replay_effect(self, access)
                return
        if workflow and workflow[0] is self:
            from pyasm.command.workflow import _check_effect
            _check_effect(self, access)
            return
        log_scope = {'sthpw/status_log': 'StatusLog:writing', 'sthpw/retire_log': 'RetireLog:writing', 'sthpw/notification_log': 'NotificationLog:writing', 'sthpw/notification_login': 'NotificationLog:writing'}.get(base, 'Diagnostics:writing')
        if base in ('sthpw/notification_log', 'sthpw/notification_login') and Container.get('NotificationLog:writing') is self:
            from pyasm.common import Environment
            security = Environment.get_security()
            inserting = self.get_id() in (-1, '-1', '')
            if ((access not in (None, 'insert') if inserting else
                    access not in (None, 'edit') or set(self.update_data) != {'code'}) or
                    security is None or not security.is_logged_in() or
                    security.get_user_name() != context.login):
                raise SecurityException('Notification logs may only be inserted by an authenticated trigger execution')
            return
        if base in ('sthpw/exception_log', 'sthpw/debug_log', 'sthpw/status_log', 'sthpw/retire_log') and Container.get(log_scope) is self:
            from pyasm.common import Environment
            security = Environment.get_security()
            inserting = self.get_id() in (-1, '-1', '')
            if ((access not in (None, 'insert') if inserting else
                    access not in (None, 'edit') or set(self.update_data) != {'code'}) or
                    security is None or not security.is_logged_in() or
                    security.get_user_name() != context.login or self.get_value('login') != context.login):
                raise SecurityException('Internal logs may only insert their own row and assign its generated code')
            return
        parent_write = False
        if base in ('sthpw/task', 'sthpw/note'):
            with context.store.connection() as db:
                parent_write = not Authenticator._admin(db, context.login, system.get_database_impl().get_parameter())
        if parent_write or not base.startswith(('sthpw/', 'config/')):
            from pyasm.common import Environment
            security = Environment.get_security()
            if security is None or not security.is_logged_in() or security.get_user_name() != context.login:
                raise SecurityException('Business writes require the authenticated request identity')
            from pyasm.biz import Project
            project = (self.get_value('project_code') or Project.get_project_code()) if parent_write else self.get_project_code()
            if not security.check_access('project', [{'code': '*'}, {'code': project}], 'allow', default='deny'):
                raise SecurityException('Project write access denied: ' + project)
            access = access or ('insert' if self.force_insert or self.get_id() in (-1, '-1', '') else 'edit')
            keys = [{'code': base}, {'code': base, 'project': project},
                    {'code': '*'}, {'code': '*', 'project': project}]
            if not security.check_access('search_type', keys, access, default='deny'):
                raise SecurityException('Search type %s access denied: %s' % (access, base))
            if access != 'insert' and self.get_id() not in (-1, '-1', ''):
                current = Search(self.get_search_type())
                current.add_id_filter(self.get_id())
                current = current.get_sobject()
                if not current:
                    raise SecurityException('Object is missing or outside the current read policy')
                if parent_write:
                    # ponytail: reparenting needs dependency/thread propagation before opening it.
                    for name in ('project_code', 'search_type', 'search_code', 'search_id') + (('login', 'parent_id') if base == 'sthpw/note' else ()):
                        if str(self.get_value(name, no_exception=True) or '') != str(current.get_value(name, no_exception=True) or ''):
                            raise UnsupportedContract('Changing task/note ownership requires dependency propagation')
            if parent_write:
                parent = self.get_parent()
                if (parent is None or parent.get_base_search_type().startswith(('sthpw/', 'config/')) or
                        parent.get_project_code() != project):
                    raise SecurityException('Task/note requires a visible parent in its own project')
                for name, expected in (('search_code', parent.get_code()), ('search_id', parent.get_id())):
                    if str(self.get_value(name, no_exception=True) or '') not in ('', str(expected)):
                        raise SecurityException('Task/note parent identities do not match')
                parent._check_business_write('edit')
                if base == 'sthpw/note':
                    if self.get_value('login') != context.login:
                        raise SecurityException('Note writes require their authenticated author')
                    parent_id = self.get_value('parent_id', no_exception=True)
                    if parent_id not in (None, '', 0, '0'):
                        thread = Search.get_by_id(base, parent_id)
                        if thread is None or any(str(thread.get_value(name, no_exception=True) or '') != str(self.get_value(name, no_exception=True) or '')
                                for name in ('project_code', 'search_type', 'search_code', 'search_id')):
                            raise SecurityException('Note reply requires a visible thread on the same parent')
                    if access == 'delete':
                        # Integrity checks must see private replies too, without exposing their contents.
                        sudo = Sudo()
                        try:
                            replies = Search(base); replies.add_filter('parent_id', self.get_id()); replies.set_limit(1)
                            if replies.get_sobject() is not None:
                                raise UnsupportedContract('Delete note replies before their parent')
                        finally:
                            sudo.exit()
            for name in self.update_data if access != 'delete' else ():
                key = {'search_type': base, 'column': name, 'project': project}
                if not security.check_access('sobject_column', key, 'edit'):
                    raise SecurityException('Column [%s] not editable for search type [%s]' % (name, self.get_search_type()))
            return
        attachment = Container.get('Chat:attachment')
        profile = Container.get('UserProfile:writing')
        if profile:
            base = self.get_base_search_type()
            if base == 'sthpw/login' and self.get_value('login') == profile['login']:
                return
            if profile['manage'] and base in ('sthpw/login_group', 'sthpw/login_in_group'):
                return
            if profile['avatar'] and base in ('sthpw/snapshot', 'sthpw/file'):
                user = Search('sthpw/login'); user.add_filter('login', profile['login']); user = user.get_sobject()
                if self.get_value('search_type') == 'sthpw/login' and user and self.get_value('search_code') == user.get_code():
                    return
                raise SecurityException('Avatar record belongs to another user')
            if base in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp'):
                return
        if attachment and self.get_base_search_type() in ('sthpw/snapshot', 'sthpw/file'):
            if self.get_value('search_type') != 'sthpw/message' or self.get_value('search_code') != attachment['message_code']:
                raise SecurityException('Repository record belongs to another chat')
        if (attachment and self.get_base_search_type() in ('sthpw/snapshot', 'sthpw/file')) or (Container.get('Chat:writing') and self.get_base_search_type() in (
                'sthpw/message', 'sthpw/message_log', 'sthpw/subscription', 'sthpw/connection')):
            from pyasm.common import Environment
            security = Environment.get_security()
            base = self.get_base_search_type()
            if security is None or not security.check_access('search_type',
                    [{'code': base}, {'code': base, 'project': 'sthpw'},
                     {'code': '*'}, {'code': '*', 'project': 'sthpw'}], 'edit', default='deny'):
                raise SecurityException('Chat record write access denied')
            return
        with context.store.connection() as db:
            if not Authenticator._admin(db, context.login, system.get_database_impl().get_parameter()):
                raise SecurityException('Business writes currently require administrator access')

    def commit(self, triggers=True, log_transaction=True, cache=True, return_sql=False):
        prepared = self._prepare_commit(triggers, log_transaction, cache, return_sql)
        if prepared is None or return_sql:
            return prepared
        update, is_insert, search_id, triggers = prepared
        resource = update.db_resource
        from pyasm.search.sql import DbContainer
        sql = DbContainer.get(resource)
        if not sql._admin_sql:
            sql._do_security_dml(update.table, update.data,
                                 None if is_insert else self.get_id_col(), self.get_id(), update.unquoted_cols,
                                 sobject=self)
        else:
            sql._do_update(self.last_statement,
                           native_table=sql._native_metadata_table(update.table, update.data, update.unquoted_cols))
        Container.increment('Search:sql_commit')
        if is_insert:
            impl = sql.get_database_impl()
            if impl.has_sequences():
                if search_id == -1:
                    sequence = impl.get_sequence_name(SearchType.TABLE if isinstance(self, SearchType) else self.search_type_obj)
                    search_id = int(sql.get_value(impl.get_currval_select(sequence, db_resource=resource)))
            else:
                search_id = sql.last_row_id
        self._finish_commit(is_insert, search_id, triggers, log_transaction, cache)

    @classmethod
    def _can_batch_checkin_files(cls):
        from pyasm.biz.file import File
        return (cls is File and bool(Container.get('Checkin:writing')) and
                all(getattr(File, name) is getattr(SObject, name) for name in
                    ('commit', 'validate', 'store_version', 'on_insert', 'on_update',
                     'set_defaults', 'get_defaults', 'generate_code', 'get_code_key', '_prepare_commit', '_finish_commit')))

    @staticmethod
    def commit_multiple(sobjects, triggers=True, log_transaction=True, cache=True, values=None):
        """Save bounded batches through the same checks and journal as commit()."""
        from pyasm.search.sql import DbContainer
        from pyasm.security.access_manager import Sudo
        for offset in range(0, len(sobjects), 250):
            batch = sobjects[offset:offset + 250]
            first = batch[0]
            new_files = (triggers == 'none' and first._can_batch_checkin_files() and
                         all(sobject.get_id() == -1 and not sobject.get_code() for sobject in batch))
            identity_column = 'file_name' if new_files else 'code'
            # shortcut: duplicate input names and custom hooks stay sequential; batching needs an unambiguous identity.
            eligible = (len(batch) > 1 and triggers in ('none', 'ingest') and
                        not {'code', 'id'}.intersection(values or {}) and
                        all(sobject.get_search_type() == first.get_search_type() and
                            (sobject.get_code() or new_files) and not sobject.force_insert and sobject.new_id == -1 and
                            'commit' not in sobject.__dict__ and
                            ((triggers == 'none' and sobject._can_batch_checkin_files() and
                              (new_files or sobject.get_id() != -1) and 'id' not in sobject.update_data and
                              ('code' not in sobject.update_data or
                               (set(sobject.update_data) == {'code'} and not sobject.data.get('code'))) and
                              all(name not in sobject.__dict__ for name in
                                  ('commit', 'validate', 'store_version', 'on_insert', 'on_update',
                                   'set_defaults', 'get_defaults', 'generate_code', 'get_code_key', '_prepare_commit', '_finish_commit'))) or
                             (triggers == 'ingest' and type(sobject) is SObject and
                              sobject.get_base_search_type() == 'sthpw/change_timestamp'))
                            for sobject in batch) and
                        len({sobject.get_value(identity_column) for sobject in batch}) == len(batch) and
                        (new_files or triggers == 'ingest' or len({sobject.get_id() for sobject in batch}) == len(batch)))
            sql = DbContainer.get(first.get_db_resource()) if eligible else None
            if not eligible or sql.get_database_impl().has_table_triggers(sql, first.get_table()):
                for sobject in batch:
                    for name, value in (values or {}).items():
                        sobject.set_value(name, value)
                    sobject.commit(triggers=triggers, log_transaction=log_transaction, cache=cache)
                continue
            pending = []
            for sobject in batch:
                for name, value in (values or {}).items():
                    sobject.set_value(name, value)
                prepared = sobject._prepare_commit(triggers, log_transaction, cache)
                if prepared is not None:
                    pending.append((sobject, prepared))
            if not pending:
                continue
            inserted = sql.do_update_multiple([item[1][0] for item in pending], [item[0] for item in pending])
            identities = [inserted[sobject.get_value(identity_column)] if is_insert else search_id
                          for sobject, (_, is_insert, search_id, _) in pending]
            sudo = Sudo()
            try:
                search = Search(first.get_search_type())
                search.set_show_retired(True)
                search.set_security_filter()
                search.add_filters(first.get_id_col(), identities)
                stored = {sobject.get_id(): sobject for sobject in search.get_sobjects()}
            finally:
                sudo.exit()
            generated_codes = [] if new_files else None
            for (sobject, (_, is_insert, search_id, mode)), identity in zip(pending, identities):
                row = stored.get(identity)
                if row is None or row.get_value(identity_column) != sobject.get_value(identity_column):
                    raise SObjectException('Batch write failed to reload its own SObject')
                Container.increment('Search:sql_commit')
                sobject._finish_commit(is_insert, row.get_id(), mode, log_transaction, cache,
                                       stored=row, generated_codes=generated_codes)
            if generated_codes:
                SObject.commit_multiple(generated_codes, triggers='none', log_transaction=False, cache=cache)

    def _prepare_commit(self, triggers=True, log_transaction=True, cache=True, return_sql=False):
        if self.get_base_search_type() == 'sthpw/virtual':
            raise UnsupportedContract('Virtual SObjects have no persistent table')
        if not return_sql:
            from pyasm.search.transaction import Transaction
            from pyasm.common.environment import Environment
            transaction = Transaction.get()
            base = self.get_base_search_type()
            if base in self.SECURITY_TYPES:
                from pyasm.security.security import _require_admin, _security_transaction
                _require_admin()
                if transaction is None or not transaction.is_in_transaction():
                    with _security_transaction():
                        return self.commit(triggers, log_transaction, cache, return_sql)
                if base in ('sthpw/login', 'sthpw/login_group') and self.get_id() != -1:
                    identity = 'login' if base == 'sthpw/login' else 'login_group'
                    if identity in self.update_data and self.update_data[identity] != self.data.get(identity):
                        raise UnsupportedContract('Changing account identities requires dependency propagation')
            elif base in self.BUSINESS_TYPES or not base.startswith(('sthpw/', 'config/')):
                self._check_business_write()
                if base == 'sthpw/snapshot':
                    from pyasm.common import Xml
                    self._lock_versions()
                    Xml(self.get_value('snapshot'))
                    # A complete file journal restores versionless records/bytes itself.
                    if (self.get_value('version') not in (-1, 0) and self.get_id() != -1 and triggers != 'none' and
                            not Container.get('Checkin:replay_complete') and
                            (Container.get('Checkin:writing') or {}).get('replay_node') is None):
                        for field, mode in (('is_latest', 'latest'), ('is_current', 'current')):
                            if self.update_data.get(field) == True:
                                self.update_versionless(mode)
            elif base not in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp'):
                raise UnsupportedContract("Domain SObject writes require the remaining Command/Transaction/Trigger path")
            if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
                raise UnsupportedContract("Journal writes require an active Transaction and Environment Security")
        from pyasm.search.sql import DbContainer, Insert, Update
        search_id = self.get_id()
        is_insert = bool(self.force_insert or search_id == -1)
        if search_id in ('-1', ''):
            search_id = -1
            self.set_id(-1)
            is_insert = True
        if not self.handle_commit_security():
            from pyasm.common.errors import SecurityException
            raise SecurityException("Security: Action not permitted")
        if is_insert:
            self.set_defaults()
        else:
            self.store_version()
        if not return_sql and self.get_base_search_type() == 'sthpw/task' and self.get_value('pipeline_code', no_exception=True) not in (None, '', 'task', 'approval', 'dependency', 'progress', 'milestone', 'snapshot'):
            from pyasm.biz import Pipeline
            pipeline_code = self.get_value('pipeline_code')
            status_pipeline = Pipeline.get_by_code(pipeline_code)
            if status_pipeline is None or not status_pipeline.get_processes():
                raise UnsupportedContract('Task status pipeline does not exist: %s' % pipeline_code)
        if triggers == True:
            triggers = "all"
        elif triggers == False:
            triggers = "integral"
        assert triggers in ("all", "integral", "ingest", "none")
        update = Insert() if is_insert else Update()
        resource = self.get_db_resource()
        update.set_database(resource)
        update.set_table(SearchType.TABLE if isinstance(self, SearchType) else self.get_table())
        if not is_insert:
            update.add_filter(self.get_id_col(), self.get_id())
        if self.new_id != -1:
            self.set_value("id", self.new_id)
            search_id = self.new_id
            self.new_id = -1
        if is_insert and triggers == "ingest" and not self.update_data.get("code") and SearchType.column_exists(self.full_search_type, "code"):
            self.set_value("code", Common.generate_random_key())
        if is_insert and not self.update_data and SearchType.column_exists(self.full_search_type, "code"):
            self.set_value("code", "NULL", quoted=False)
        self.validate()
        # Match the original connection registration before converting values.
        DbContainer.get(resource)
        column_types = SearchType.get_column_types(self.full_search_type)
        for name, value in self.update_data.items():
            quoted = self.quoted_flag.get(name)
            changed = isinstance(value, datetime) and bool(value)
            if isinstance(value, dict):
                value = jsondumps(value)
            if column_types.get(name) in ("timestamp", "datetime", "datetime2"):
                if value and not self.is_day_column(name):
                    value = SPTDate.add_gmt_timezone(value)
                if value and not isinstance(value, str):
                    value = value.strftime('%Y-%m-%d %H:%M:%S.%f %z' if value.microsecond else '%Y-%m-%d %H:%M:%S %z')
                changed = True
            if changed:
                self.update_data[name] = value
            update.set_value(name, value, quoted=quoted)
        statement = update.get_statement()
        if not statement:
            return
        self.last_statement = statement
        if return_sql:
            return statement
        return update, is_insert, search_id, triggers

    def _finish_commit(self, is_insert, search_id, triggers, log_transaction, cache, stored=None, generated_codes=None):
        if triggers == 'ingest':
            self.set_id(search_id)
            return
        from pyasm.security.access_manager import Sudo
        if stored is None:
            sudo = Sudo()
            try:
                search = Search(self.full_search_type)
                search.set_show_retired(True)
                search.set_security_filter()
                search.add_id_filter(search_id)
                stored = search.get_sobject()
            finally:
                sudo.exit()
        if stored is None:
            raise SObjectException("Insert/Update of [%s] failed. The entry with id [%s] cannot be found.\n%s" % (self.get_search_type(), search_id, self.last_statement))
        for name in self.update_data:
            if not self.quoted_flag.get(name):
                self.update_data[name] = stored.get_value(name)
        prev_code = None
        if not is_insert and self.update_data.get('code') and self.data.get('code') and self.update_data['code'] != self.data['code']:
            prev_code = self.data['code']
        code = None
        if SearchType.column_exists(self.full_search_type, 'code'):
            code = stored.get_value('code', no_exception=True) or self.generate_code(search_id)
        if getattr(self, 'track_change_timestamps', True) and (self.get_base_search_type() == 'sthpw/sobject_log' or self.get_base_search_type() in self.SECURITY_TYPES + self.BUSINESS_TYPES or not self.get_base_search_type().startswith(('sthpw/', 'config/'))) and code:
            # Original change-timestamp staging also applies to SObjectLog.
            from pyasm.search.transaction import Transaction
            transaction = Transaction.get()
            key = '%s|%s' % (self.get_search_type(), code)
            log = transaction.change_timestamps.get(key)
            if log is None:
                log = SearchType.create('sthpw/change_timestamp')
                log.set_auto_code()
                log.set_value('search_type', self.get_search_type())
                log.set_value('search_code', code)
                transaction.change_timestamps[key] = log
            if not is_insert:
                changed_on = log.get_json_value('changed_on', {})
                changed_by = log.get_json_value('changed_by', {})
                from pyasm.common.environment import Environment
                for name in self.update_data:
                    changed_on[name], changed_by[name] = 'CHANGED', Environment.get_user_name()
                log.set_json_value('changed_on', changed_on)
                log.set_json_value('changed_by', changed_by)
        if log_transaction:
            SObjectUndo.log_undo(self, code, search_id, is_insert, prev_code=prev_code)
        trigger_update_data = self.update_data.copy()
        trigger_prev_data = {name: self.data.get(name) for name in trigger_update_data}
        self.prev_data, self.prev_update_data = self.data, self.update_data
        self.data = stored.data
        from pyasm.search.update_events import capture_change
        capture_change(self)
        if self.get_base_search_type() == 'sthpw/file' and 'metadata' in trigger_update_data and Container.get('is_undo') != True:
            # Handler supplies group metadata after inplace registration; reclaim all owned members.
            from tactic_stream.server.file_presentation import metadata_paths
            from pyasm.search.transaction import FileUndo
            FileUndo.reclaim(str(path) for path in metadata_paths(self))
        Container.clear_dict("Expression:keys")
        Container.clear_dict('SObjectConnection:cache')
        if self.get_base_search_type() == 'sthpw/search_object':
            Container.clear_dict('SearchType:search_object_data')
        if self.get_base_search_type() == 'sthpw/schema':
            _context.get().schemas.clear()
            self.init()
        self.update_data = {}
        self.has_updates = False
        if self.get_base_search_type() == 'sthpw/snapshot':
            self.clear_cache()
        if self.get_base_search_type() in ('sthpw/pipeline', 'config/pipeline'):
            Container.clear_dict('Pipeline:xml')
            Container.put('Task::status_colors', None)
            self.set_pipeline(self.get_value('pipeline'), cache=False)
        if self.get_base_search_type() == 'config/process':
            self._clear_process_cache()
        self._clear_config_cache(self.get_base_search_type())
        self.update_description = self.build_update_description(is_insert)
        if SearchType.column_exists(self.full_search_type, 'code') and not stored.get_value('code', no_exception=True):
            stored.set_value('code', code)
            if generated_codes is not None:
                # Keep the insertion journal unchanged; authorize code assignment as its original edit.
                generated_codes.append(stored)
                self.data = self.data.copy()
                self.data['code'] = code
            else:
                log_scope = {'sthpw/status_log': 'StatusLog:writing', 'sthpw/retire_log': 'RetireLog:writing', 'sthpw/notification_log': 'NotificationLog:writing', 'sthpw/notification_login': 'NotificationLog:writing'}.get(self.get_base_search_type(), 'Diagnostics:writing')
                internal_log = Container.get(log_scope) is self
                workflow = Container.get('Workflow:writing')
                internal_workflow = workflow and workflow[0] is self
                if internal_workflow:
                    Container.put('Workflow:writing', (stored, workflow[1]))
                if internal_log:
                    Container.put(log_scope, stored)
                try:
                    stored.commit(triggers='none', log_transaction=False)
                finally:
                    if internal_log:
                        Container.put(log_scope, self)
                    if internal_workflow:
                        Container.put('Workflow:writing', workflow)
                self.data['code'] = code
        if self.get_base_search_type() in self.SECURITY_TYPES:
            if self.get_base_search_type() == 'sthpw/login' and not is_insert and (
                    'password' in trigger_update_data or self.is_retired()):
                search = Search('sthpw/ticket', sudo=True)
                search.add_filter('login', self.get_login())
                for ticket in search.get_sobjects():
                    ticket.delete(triggers=False)
            from pyasm.security.security import _clear_account_cache
            _clear_account_cache()
        if (not self.get_base_search_type().startswith(('sthpw/', 'config/')) or self.get_base_search_type() in self.SECURITY_TYPES[:-1] + ('sthpw/task', 'sthpw/note', 'sthpw/milestone', 'sthpw/work_hour', 'config/process_state', 'config/process', 'sthpw/snapshot', 'sthpw/file', 'sthpw/pref_setting', 'sthpw/retire_log', 'sthpw/pipeline', 'sthpw/connection', 'sthpw/search_object', 'sthpw/schema', 'config/naming', 'sthpw/sobject_list', 'config/widget_config', 'config/prod_setting', 'config/trigger', 'config/client_trigger', 'sthpw/trigger', 'config/pipeline', 'config/custom_property', 'config/ingest_rule', 'config/ingest_session', 'config/translation', 'sthpw/notification', 'sthpw/notification_log', 'sthpw/notification_login', 'sthpw/subscription', 'sthpw/interaction', 'sthpw/wdg_settings', 'sthpw/queue', 'sthpw/exception_log', 'sthpw/debug_log')) and triggers != 'none' and Container.get('is_undo') != True:
            mode = 'insert' if is_insert else 'update'
            output = {'is_insert': is_insert, 'mode': mode, 'id': self.get_id(),
                      'search_code': self.get_code(), 'search_type': self.get_search_type(),
                      'search_key': self.get_search_key(), 'update_data': trigger_update_data,
                      'prev_data': trigger_prev_data, 'sobject': self.get_sobject_dict()}
            process = self.get_value('process', no_exception=True)
            parent_type = self.get_value('search_type').split('?')[0] if self.get_base_search_type() in ('sthpw/task', 'sthpw/note', 'sthpw/work_hour', 'sthpw/snapshot') else self.get_base_search_type()
            self._call_triggers(trigger_update_data, mode, output, process, parent_type, triggers)
            events = self.get_search_type_obj().get_value('message_event', no_exception=True)
            if events and any(event in (mode, 'change') for event in events.split('|')):
                raise UnsupportedContract('Message subscriptions and delivery are not migrated')
        # System journal and ticket types skip _call_triggers/_add_message.
        # Source caching is outside that type check, but inside this mode check.
        if triggers != 'none' and Container.get('is_undo') != True and cache:
            key = SearchKey.build_search_key(self.get_search_type(), search_id, column='id', project_code=self.get_project_code())
            self.cache_sobject(key, self)
            if self.get_code():
                key = SearchKey.build_search_key(self.get_search_type(), self.get_code(), column='code', project_code=self.get_project_code())
                self.cache_sobject(key, self)
        if prev_code and triggers == 'all':
            self._update_code_dependencies(prev_code)
        self.on_insert() if is_insert else self.on_update()

    def _update_code_dependencies(self, old_code):
        """Original dependency propagation; always restore the object's new code."""
        search_type = self.get_base_search_type()
        related_types = ['sthpw/snapshot', 'sthpw/note', 'sthpw/task']
        if search_type in related_types:
            return
        new_code = self.data['code']
        self.data['code'] = old_code
        try:
            for related_type in related_types:
                related_sobjects = self.get_related_sobjects(related_type)
                for related_sobject in related_sobjects:
                    if related_sobject.get_value('search_type', no_exception=True) != self.get_search_type():
                        continue
                    related_sobject.set_value('search_code', new_code)
                    related_sobject.commit()
            from pyasm.biz import Schema
            schema = Schema.get()
            for related_type in schema.get_related_search_types(search_type):
                if related_type == '*':
                    continue
                attrs = schema.get_relationship_attrs(search_type, related_type)
                if attrs.get('relationship') == 'code':
                    if related_type == attrs.get('from'):
                        if attrs.get('to_col') != 'code':
                            continue
                    elif attrs.get('from_col') != 'code':
                        continue
                if self.get_related_sobjects(related_type):
                    raise TacticException('There are related items in [%s].  Please change these first' % related_type)
        finally:
            self.data['code'] = new_code

    def retire(self):
        '''retires the asset.  This is prefered to deleting because
        deletion is a loss of work and is permanently removed from ever
        existing'''
        events = self.search_type_obj.get_value('message_event', no_exception=True)
        if events and any(event in ('retire', 'change') for event in events.split('|')):
            raise UnsupportedContract('Message subscriptions and delivery are not migrated')
        retire_col = self.search_type_obj.get_retire_col()
        if not SearchType.column_exists(self.full_search_type, retire_col):
            raise SObjectException('Search type has no retirement column')
        self.set_value(retire_col,"retired")
        self.commit()

        from .sobject_log import RetireLog
        RetireLog.create(self.get_search_type(), search_code=self.get_code(), search_id=self.get_id() if not self.get_code() else None )

        # remember the data
        data = self.data.copy()

        # call a retire event
        from pyasm.command import Trigger
        output = {}
        output["is_retire"] = True
        output["mode"] = "retire"
        output["search_key"] = SearchKey.build_by_sobject(self)
        output["id"] = self.get_id()
        output["search_type"] = self.get_search_type()
        output["data"] = data
        output["sobject"] = self.get_sobject_dict()

        from pyasm.biz import Project
        project_code = Project.get_project_code()
        Trigger.call(self, "retire", output, project_code=project_code)
        Trigger.call(self, "retire|%s" % self.get_base_search_type(), output, project_code=project_code)
        Trigger.call(self, "change", output, project_code=project_code)
        Trigger.call(self, "change|%s" % self.get_base_search_type(), output, project_code=project_code)

        # add message
        # Message event preflight above rejects unported delivery before mutation.

    def reactivate(self):
        '''reactivate a retired asset'''
        retire_col = self.search_type_obj.get_retire_col()
        if not SearchType.column_exists(self.full_search_type, retire_col):
            raise SObjectException('Search type has no retirement column')
        self.set_value(retire_col, "NULL", quoted=0)
        self.commit()

    def clone(self, recursive=True, related_types=[], parent=None, extra_data={}):
        '''copy an sobject'''
        if self.get_base_search_type() in ('sthpw/file', 'sthpw/snapshot'):
            raise UnsupportedContract('Repository objects require the dedicated copy/check-in path')
        search_type = self.get_search_type()
        clone = SearchType.create(search_type)
        #clone.update_data = self.data.copy()

        for name, value in self.data.items():
            if value == None or name == 'code':
                continue

            if isinstance(value, list) or isinstance(value, dict):
                clone.set_json_value(name, value)
            else:
                clone.set_value(name, value)

        clone.update_data.pop('id', None)
        clone.set_id(-1)

        if parent:
            clone.set_parent(parent)

        for name, value in extra_data.items():
            clone.set_value(name, value)

        clone.commit(triggers=False)

        # copy recursively
        if related_types:
            for related_type in related_types:
                # if related type is the search type, then skip
                if related_type == search_type:
                    continue

                related_sobjects = self.get_related_sobjects(related_type)

                for related_sobject in related_sobjects:
                    related_sobject.clone(parent=clone)

        return clone

    def delete(self, log=True, triggers=True, return_sql=False):
        if self.get_base_search_type() == 'sthpw/virtual':
            raise UnsupportedContract('Virtual SObjects have no persistent table')
        if not return_sql:
            from pyasm.search.transaction import Transaction
            from pyasm.common.environment import Environment
            transaction = Transaction.get()
            if self.get_base_search_type() in self.SECURITY_TYPES:
                from pyasm.security.security import _require_admin, _security_transaction
                _require_admin()
                if transaction is None or not transaction.is_in_transaction():
                    with _security_transaction():
                        return self.delete(log, triggers, return_sql)
                if self.get_base_search_type() in ('sthpw/login', 'sthpw/login_group'):
                    identity = 'login' if self.get_base_search_type() == 'sthpw/login' else 'login_group'
                    search = Search('sthpw/login_in_group', sudo=True)
                    search.add_filter(identity, self.get_value(identity))
                    for membership in search.get_sobjects():
                        membership.delete(log=log, triggers=triggers)
                    if identity == 'login':
                        search = Search('sthpw/ticket', sudo=True)
                        search.add_filter('login', self.get_login())
                        for ticket in search.get_sobjects():
                            ticket.delete(log=log, triggers=False)
            elif self.get_base_search_type() in self.BUSINESS_TYPES or not self.get_base_search_type().startswith(('sthpw/', 'config/')):
                self._check_business_write(access='delete')
                if self.get_base_search_type() == 'sthpw/snapshot':
                    self._lock_versions()
            elif self.get_base_search_type() not in ('sthpw/transaction_log', 'sthpw/sobject_list'):
                raise UnsupportedContract("Domain SObject writes require the remaining Command/Transaction/Trigger path")
            if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
                raise UnsupportedContract("Journal deletes require an active Transaction and Environment Security")
        from pyasm.common.environment import Environment
        from pyasm.search.sql import DbContainer
        search_id = self.get_id()
        if search_id == -1:
            return
        security = Environment.get_security()
        if security is None:
            if not self.handle_commit_security():
                raise UnsupportedContract("Preparing deletes requires Environment Security")
        else:
            base = self.get_base_search_type()
            project = self.get_project_code()
            if base in ['sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file', 'sthpw/work_hour']:
                project = self.get_value('project_code')
                default = 'allow'
            elif not base.startswith(('sthpw/', 'config/')):
                default = 'deny'
            else:
                default = None
            if default is not None:
                keys = [{'code': base}, {'code': base, 'project': project},
                        {'code': '*'}, {'code': '*', 'project': project}]
                if not security.check_access('search_type', keys, 'delete', default=default):
                    raise SObjectException('[%s] is not allowed to delete item in [%s]. You may need to adjust the access rules for the group.' % (Environment.get_user_name(), base))
        if not return_sql and self.get_base_search_type() == 'config/process':
            from pyasm.biz.pipeline import Pipeline
            Pipeline._delete_process_dependencies(self)
        sql = DbContainer.get(self.get_db_resource())
        # Quote string identities rather than interpolating them into SQL.
        identity = sql.quote(search_id) if isinstance(search_id, str) else str(search_id)
        table = SearchType.TABLE if isinstance(self, SearchType) else self.get_table()
        statement = 'DELETE FROM %s WHERE %s = %s' % (identifier(table), identifier(self.get_id_col()), identity)
        if not return_sql:
            if not sql._admin_sql:
                sql._do_security_dml(table, id_col=self.get_id_col(), search_id=search_id, sobject=self)
            else:
                sql._do_update(statement, native_table=table)
        if log:
            SObjectUndo.log_undo_for_delete(self)
        if return_sql:
            return statement
        from pyasm.search.update_events import capture_change
        capture_change(self)
        Container.clear_dict("Expression:keys")
        Container.clear_dict('SObjectConnection:cache')
        if self.get_base_search_type() == 'sthpw/search_object':
            Container.clear_dict('SearchType:search_object_data')
        if self.get_base_search_type() == 'sthpw/schema':
            _context.get().schemas.clear()
            self.init()
        # Evict all retired-mode variants: a deleted row cannot stay visible
        # merely because it was fetched by code/id earlier in the request.
        cache = SObject.get_cache_dict(search_type=self.get_base_search_type())
        keys = [self.get_search_key(), self.get_search_key(use_id=True)]
        for key in list(cache):
            if any(key == identity or key == identity + ':False' for identity in keys):
                cache.pop(key)
        if triggers and Container.get('is_undo') != True:
            from pyasm.command.trigger import Trigger
            output = {'is_delete': True, 'mode': 'delete', 'search_key': self.get_search_key(),
                      'id': search_id, 'search_type': self.get_search_type(), 'data': self.data.copy(),
                      'sobject': self.get_sobject_dict()}
            for event in ['delete', 'delete|' + self.get_base_search_type(), 'change', 'change|' + self.get_base_search_type()]:
                Trigger.call(self, event, output, project_code=_context.get().project if '|' in event else None)
        if self.get_base_search_type() != 'sthpw/sobject_list':
            search = Search('sthpw/sobject_list')
            search.add_filter('search_type', self.get_base_search_type())
            search.add_filter('search_code', self.get_code())
            indexed = search.get_sobject()
            if indexed:
                indexed.delete(log=log)
        self.on_delete()
        self._clear_config_cache(self.get_base_search_type())
        if self.get_base_search_type() == 'sthpw/snapshot':
            self.clear_cache()
        if self.get_base_search_type() == 'config/process':
            self._clear_process_cache()
        if self.get_base_search_type() == 'config/process_state':
            for key in list(Container.get_instance().get_data()):
                if isinstance(key, str) and key.startswith('Workflow|process_state|'):
                    Container.remove(key)
        if self.get_base_search_type() in self.SECURITY_TYPES:
            from pyasm.security.security import _clear_account_cache
            _clear_account_cache()

    def check_access(self, required_access, default="allow"):
        # Original base method; custom SObject subclasses may override it.
        return True

    @staticmethod
    def _get_cached_key(key):
        return "%s::cached_obj" % key

    @staticmethod
    def _clear_config_cache(base):
        if base == 'sthpw/wdg_settings':
            for key in list(Container.get_instance().get_data()):
                if isinstance(key, str) and key.startswith('sthpw/wdg_settings:'):
                    Container.remove(key)
        if base in ('config/widget_config', 'config/prod_setting', 'config/pipeline', 'config/custom_script'):
            suffix = SObject._get_cached_key(base)
            for key in list(Container.get_instance().get_data()):
                if key == suffix or key.endswith('::' + suffix):
                    Container.clear_dict(key)
            Container.clear_dict('SObject:xml_cache')
        if base == 'config/widget_config':
            Container.remove('CustomProcessConfig:configs')
            for key in list(Container.get_instance().get_data()):
                if isinstance(key, str) and key.startswith('WidgetConfigView:'):
                    Container.remove(key)
        if base == 'config/pipeline':
            Container.clear_dict('Pipeline:xml')
            Container.put('Task::status_colors', None)
        if base in ('config/trigger', 'sthpw/trigger', 'sthpw/notification'):
            from pyasm.command import Trigger
            Trigger.clear_db_cache()

    @staticmethod
    def _clear_process_cache():
        Container.increment('Pipeline:process_generation')
        Container.remove('NodeHandler::proces')

    @classmethod
    def get_cache_dict(cls, sobject=None, search_type=None):
        if sobject and not isinstance(sobject, list):
            key = SObject._get_cached_key(sobject.get_base_search_type())
        else:
            key = SObject._get_cached_key(search_type or cls.SEARCH_TYPE)
        if not key.startswith('sthpw/'):
            key = "%s::%s" % (_context.get().project, key)
        cache = Container.get(key)
        if cache is None:
            cache = {}
            Container.put(key, cache)
        return cache

    @classmethod
    def cache_sobject(cls, key, sobject, search_type=None):
        cache = cls.get_cache_dict(sobject=sobject, search_type=search_type)
        cache[key] = '__NONE__' if sobject is None or sobject == [] else sobject

    @classmethod
    def get_cached_obj(cls, key, search_type=None):
        return cls.get_cache_dict(search_type=search_type).get(key)

    @classmethod
    def _get_cached_for_read(cls, key, search_type=None):
        from pyasm.common.environment import Environment
        security = Environment.get_security()
        # Other callers still build a Search to apply the current row policy.
        if security is None or not security.is_admin():
            return None
        full_type = search_type or cls.SEARCH_TYPE
        Search._check_resource_access(full_type)
        base = SearchKey.extract_base_search_type(full_type)
        cached = cls.get_cached_obj(key, search_type=base if search_type else None)
        if cached is not None and not base.startswith('sthpw/'):
            from pyasm.biz.project import Project
            Project.get_db_resource_by_search_type(Project.get_full_search_type(
                full_type, project_code=_context.get().project))
        return cached

    @classmethod
    def clear_cache(cls, search_key=None, key=None):
        # Original clear_cache omits the project prefix used by get_cache_dict.
        cached_key = SObject._get_cached_key(cls.SEARCH_TYPE)
        cache = Container.get(cached_key)
        if search_key or key:
            if cache:
                cache[search_key or key] = None
        else:
            Container.put(cached_key, {})

    @classmethod
    def get_by_search(cls, search, key, is_multi=False):
        from pyasm.common.environment import Environment
        security = Environment.get_security()
        # A Sudo-loaded object must not bypass the caller's current ACL via
        # the identity cache. Keep pending state only after verifying access.
        if security is not None and not security.is_admin() and search.get_count() == 0:
            return [] if is_multi else None
        search_type = search.get_base_search_type() if cls.__name__ == 'SObject' else None
        cached = cls.get_cached_obj(key, search_type=search_type)
        if cached:
            return ([] if is_multi else None) if cached == '__NONE__' else cached
        result = search.get_sobjects() if is_multi else search.get_sobject()
        cls.cache_sobject(key, result, search_type=search_type)
        return result

    @classmethod
    def get_by_id(cls, id, show_retired=True):
        key = SearchKey.build_search_key(cls.SEARCH_TYPE, id, column='id', project_code=_context.get().project)
        if show_retired == False:
            key += ':False'
        cached = cls._get_cached_for_read(key)
        if cached is not None:
            return None if cached == '__NONE__' else cached
        search = Search(cls.SEARCH_TYPE)
        search.set_show_retired(show_retired)
        search.add_id_filter(id)
        key = SearchKey.build_search_key(search.get_search_type(), id, column='id', project_code=search.project_code)
        if show_retired == False:
            key += ':False'
        return cls.get_by_search(search, key)

    @classmethod
    def get_by_code(cls, code, show_retired=True):
        key = SearchKey.build_search_key(cls.SEARCH_TYPE, code, column='code', project_code=_context.get().project)
        if show_retired == False:
            key += ':False'
        cached = cls._get_cached_for_read(key)
        if cached is not None:
            return None if cached == '__NONE__' else cached
        search = Search(cls.SEARCH_TYPE)
        search.set_show_retired(show_retired)
        search.add_filter('code', code)
        key = SearchKey.build_search_key(search.get_search_type(), code, column='code', project_code=search.project_code)
        if show_retired == False:
            key += ':False'
        return cls.get_by_search(search, key)


    def _call_triggers(self, trigger_update_data, mode, output, process, parent_type, triggers):
        is_undo = Container.get('is_undo')
        if triggers == 'integral' or is_undo == True:
            integral_only = True
        else:
            integral_only = False
        from pyasm.command.trigger import Trigger
        search_type = self.get_base_search_type()
        events = [mode, '%s|%s' % (mode, search_type), 'change', 'change|%s' % search_type]
        from pyasm.biz.project import Project
        project_code = Project.get_project_code()
        for column in trigger_update_data.keys():
            if column == 'timestamp':
                continue
            events.append('%s|%s|%s' % (mode, search_type, column))
            events.append('change|%s|%s' % (search_type, column))
        process_context_valid = False
        process_code = None
        for event in events:
            key = {'event': event}
            called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code)
            if parent_type:
                key = {'event': event}
                key['search_type'] = parent_type
                called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code) or called
            if process:
                key = {'event': event}
                key['process'] = process
                called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code) or called
            if process and parent_type:
                key = {'event': event}
                key['process'] = process
                key['search_type'] = parent_type
                called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code) or called
            # Any invoked trigger can change rows, rights or context without committing.
            if called:
                process_context_valid = False
            if process and self.get_base_search_type() in ['sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/work_hour']:
                if not process_context_valid:
                    process_code = None
                    process_sobj = None
                    parent = self.get_parent()
                    pipeline_code = None
                    if parent:
                        pipeline_code = parent.get_value('pipeline_code', no_exception=True)
                    if pipeline_code:
                        try:
                            search = Search('config/process')
                        except LookupError as exc:
                            if not str(exc).startswith('Unregistered SearchType:'):
                                raise
                            if isinstance(parent, SObject) and parent.get_base_search_type() == 'sthpw/task' and pipeline_code in ('task', 'approval', 'dependency', 'progress', 'milestone', 'snapshot'):
                                continue
                            raise UnsupportedContract('Process-bound triggers require project process definitions') from exc
                        search.add_filter('process', process)
                        search.add_filter('pipeline_code', pipeline_code)
                        process_sobj = search.get_sobject()
                        if process_sobj:
                            process_code = process_sobj.get_code()
                    # Custom getters may deliberately return a different value per call.
                    process_context_valid = (getattr(self.get_parent, '__func__', None) is SObject.get_parent
                        and getattr(self.get_value, '__func__', None) is SObject.get_value
                        and getattr(self.get_schema, '__func__', None) is SObject.get_schema
                        and getattr(self.get_related_sobject, '__func__', None) is SObject.get_related_sobject
                        and (parent is None or getattr(parent.get_value, '__func__', None) is SObject.get_value)
                        and (process_sobj is None or (getattr(process_sobj.get_code, '__func__', None) is SObject.get_code
                            and getattr(process_sobj.get_value, '__func__', None) is SObject.get_value)))
                if process_code:
                    key = {'event': event}
                    key['process'] = process_code
                    called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code)
                    if parent_type:
                        key = {'event': event}
                        key['process'] = process_code
                        key['search_type'] = parent_type
                        called = Trigger.call_by_key(key, self, output, integral_only=integral_only, project_code=project_code) or called
                    if called:
                        process_context_valid = False

class SearchType(SObject):
    def get_record_read_options(self):
        """Registered record classes declare their dedicated read API."""
        from pyasm.common.errors import UnsupportedContract
        from pyasm.common import Environment
        try:
            record_class = Common.resolve_class(self.get_value('class_name') or 'pyasm.search.SObject')
        except UnsupportedContract as error:
            return dict(available=False, reason=str(error))
        options = dict(getattr(record_class, 'record_read', {}))
        if options:
            options['available'] = not options.get('admin_only') or Environment.get_security().is_admin()
        return options

    SEARCH_TYPE = "sthpw/search_object"
    DATABASE = "sthpw"
    TABLE = "search_object"
    build_search_type = staticmethod(build_search_type)
    breakup_search_type = staticmethod(breakup_search_type)

    def __init__(self, search_type, columns=None, result=None, fast_data=None):
        super().__init__(search_type, columns, result, fast_data=fast_data)
        self.base_key = self.get_value("search_type") or self.SEARCH_TYPE

    @classmethod
    def get(cls, key, use_mapping=True, no_exception=False):
        virtual = cls.get_virtual(key)
        if virtual is not None:
            return virtual
        if key == 'sthpw/virtual':
            columns = ['id', 'table_name', 'title', 'search_type', 'class_name', 'namespace', 'database']
            result = ['0', 'unknown', 'Virtual', 'sthpw/virtual', 'pyasm.search.SObject', 'sthpw', 'sthpw']
            return cls.create('sthpw/search_object', columns, result)
        context = _context.get()
        base = SearchKey.extract_base_search_type(key)
        cache = Container.get('SearchType:search_object_data')
        if cache is None:
            cache = {}
            Container.put('SearchType:search_object_data', cache)
        try:
            row, database, table = context.store.resolve(key, context.project)
        except LookupError as exc:
            if not str(exc).startswith('Unregistered SearchType:'):
                raise
            if not no_exception:
                raise SearchException('Search type [%s] not registered' % base) from exc
            cls.add_triggers(base)
            return None
        metadata = cache.get(base)
        if metadata is None:
            metadata = cls('sthpw/search_object', row)
            cache[base] = metadata
        cls.add_triggers(base)
        return metadata

    @classmethod
    def create(cls, search_type, columns=None, result=None):
        class_path = 'pyasm.search.SearchType' if search_type == 'sthpw/search_object' else cls.get(search_type).get_class()
        return cls.fast_create_from_class_path(class_path, search_type, columns, result)

    @classmethod
    def get_virtual(cls, key):
        # look at the virtual stypes first
        virtual_key = "SearchType:virtual_stypes"
        virtual_stypes = Container.get(virtual_key)
        if virtual_stypes == None:
            virtual_stypes = {}
            Container.put(virtual_key, virtual_stypes)
        search_type = virtual_stypes.get(key)
        return search_type


    @classmethod
    def set_virtual(cls, key, search_type):
        # set the virtual stype
        virtual_key = "SearchType:virtual_stypes"
        virtual_stypes = Container.get(virtual_key)
        if virtual_stypes == None:
            virtual_stypes = {}
            Container.put(virtual_key, virtual_stypes)
        virtual_stypes[key] = search_type


    @classmethod
    def add_triggers(cls, base):
        # Add some triggers.  These will only be added when a search type
        # is accessed for the first time.
        # 
        triggers = Container.get("SearchType::triggers")
        if triggers == None:
            triggers = {}
            Container.put("SearchType::triggers", triggers)


        if triggers.get(base):
            return

        base_triggers = {}
        triggers[base] = base_triggers
        if base == 'config/process_state':
            from pyasm.command import Trigger
            trigger = SearchType.create('sthpw/trigger')
            trigger.set_value('event', 'change|config/process_state|status', temp=True)
            trigger.set_value('class_name', 'tactic.core.bootstrap.StatusLogTrigger', temp=True)
            trigger.set_value('mode', 'same process,same transaction', temp=True)
            if not any(item.get_value('class_name') == 'tactic.core.bootstrap.StatusLogTrigger'
                       for item in Trigger.get_static_triggers_by_event('change|config/process_state|status')):
                Trigger.append_static_trigger(trigger)
        if base == 'sthpw/task':
            if base_triggers.get(base) == None:
                #exec("from pyasm.biz import Task")
                from pyasm.biz import Task
                Task.add_static_triggers()
                base_triggers[base] = True

        if not base.startswith("sthpw/") and base_triggers.get("task_insert") == None:
            SObject.add_static_triggers(base)
            base_triggers["task_insert"] = True


        if not base.startswith("sthpw/") and not base.startswith("config/"):
            # global search trigger.  Add all automatically
            if not base_triggers.get('global_search'): 
                from pyasm.command import Trigger
                event = "change|%s" % base
                trigger = SearchType.create("sthpw/trigger")
                trigger.set_value("event", event, temp=True)
                trigger.set_value("mode", "same process,same transaction", temp=True)
                trigger.set_value("class_name", "tactic.command.GlobalSearchTrigger", temp=True)
                Trigger.append_static_trigger(trigger)
                base_triggers["global_search"] = True

            if not base_triggers.get('folder_trigger'): 
                event = "insert|%s" % base
                trigger = SearchType.create("sthpw/trigger")
                trigger.set_value("event", event, temp=True)
                trigger.set_value("mode", "same process,same transaction", temp=True)
                trigger.set_value("class_name", "tactic.command.FolderTrigger", temp=True)

                Trigger.append_static_trigger(trigger)
                base_triggers["folder_trigger"] = True






        elif base == 'sthpw/login_group':
            if not base_triggers.get('login_group_sync'): 
                from pyasm.command import Trigger
                event = "change|%s" % base
                trigger = SearchType.create("sthpw/trigger")
                trigger.set_value("event", event, temp=True)
                trigger.set_value("mode", "same process,same transaction", temp=True)
                trigger.set_value("class_name", "tactic.command.LoginGroupTrigger", temp=True)
                Trigger.append_static_trigger(trigger)
                base_triggers["login_group_sync"] = True

        elif base == 'sthpw/snapshot':
            if not base_triggers.get('snapshot_latest_trigger'):
                from pyasm.biz import Snapshot
                Snapshot.add_integral_trigger()
            base_triggers["snapshot_latest_trigger"] = True


    @classmethod
    def fast_create_from_class_path(cls, class_name, search_type, columns, result, module_name=None, fast_data=None):

        if not module_name:
            (module_name, class_name) = Common.breakup_class_path(class_name)

        # Resolve once per result batch, not once per row. A new search sees
        # changes to the registry/module; nothing is cached between requests.
        classes = fast_data.setdefault('_object_classes', {}) if fast_data is not None else {}
        class_path = module_name + "." + class_name
        object_class = classes.get(class_path)
        if object_class is None:
            object_class = classes[class_path] = Common.resolve_class(class_path)

        try:
            # Custom constructors receive the original fast_data contract, without our resolver cache.
            constructor_data = ({key: value for key, value in fast_data.items() if key != '_object_classes'}
                                if fast_data is not None else None)
            object = object_class(search_type, columns, result, fast_data=constructor_data)
        except Exception:
            # Original retries after any constructor exception, not only TypeError.
            logging.warning("Retrying class [%s] without fast_data", class_name)
            object = object_class(search_type, columns, result)

        return object


    def get_table(self):
        return self.get_value("table_name").replace("{public}.", "").replace("public.", "")

    def get_database(self, use_cache=True):
        from pyasm.biz.project import Project
        value = self.get_value("database")
        return Project.get_project_code() if value == "{project}" else value

    def get_class(self):
        # Class paths come from the trusted server registry, never from RPC arguments.
        return self.get_value("class_name") or "pyasm.search.SObject"

    def get_retire_col(self):
        return "s_status"

    def get_base_key(self):
        return self.base_key

    def get_defaults(self):
        return {"code": self.get_value("search_type")}

    def get_title(self):
        title = self.get_value("title")
        if title:
            return title
        parts = self.get_base_key().split("/")
        title = (parts[1] if len(parts) > 1 else self.get_table()).strip()
        if "_" in title:
            return title.replace("_", " ").title()
        return re.sub(" +", " ", re.sub(r"([A-Z])", r" \1", title).strip()).title()

    @classmethod
    def get_column_info(cls, search_type):
        if search_type == 'sthpw/virtual':
            return {}
        from pyasm.biz.project import Project
        context = _context.get()
        key = (context.project, search_type)
        cache = Container.get_full_dict('SearchType:column_info')
        if key in cache:
            return cache[key]
        _, database, table = context.store.resolve(search_type, context.project)
        info = context.store.columns(Project.get_db_resource_by_search_type(search_type), table)
        cache[key] = info
        return info

    @classmethod
    def clear_column_cache(cls, search_type):
        '''Clear SearchType and database column metadata, as in the original core.'''
        from pyasm.biz import Project
        context = _context.get()
        Container.get_full_dict('SearchType:column_info').pop((context.project, search_type), None)
        resource = Project.get_db_resource_by_search_type(search_type)
        table = cls.get(search_type).get_table()
        cache = Container.get('DatabaseImpl:column_info') or {}
        cache.pop('%s:%s' % (resource, table), None)
        cache.pop((resource._get_connection_key(), table), None)

    def get_search_type_id_col(self):
        id_col = self.data.get("id_column")
        if not id_col:
            return "id"
        else:
            return id_col

    @classmethod
    def get_columns(cls, search_type, show_hidden=True):
        return [name for name in cls.get_column_info(search_type) if not name.startswith("_tmp")]

    @classmethod
    def get_column_type(cls, search_type, column):
        return cls.get_column_info(search_type).get(column, {}).get("data_type")

    @classmethod
    def get_column_types(cls, search_type):
        return {name: info["data_type"] for name, info in cls.get_column_info(search_type).items()}

    @classmethod
    def get_tactic_type(cls, search_type, column):
        '''These are the tactic types (as opposed to the database types).'''
        column_info = cls.get_column_info(search_type).get(column)
        if not column_info:
            return 'string'
        # SQLite may report upper-case names; TACTIC's type mapping is lower-case.
        type = column_info.get('data_type').lower()
        size = column_info.get('size') or 256
        # SQLite keeps declaration parameters; source database introspection separates them.
        declaration = re.fullmatch(r'([a-z ]+)\((\d+)(?:,\s*\d+)?\)', type)
        if declaration:
            type, declared_size = declaration.groups()
            type = type.strip()
            size = int(declared_size)
        if type == 'varchar' and size > 256:
            type = 'text'
        elif type.startswith('time'):
            type = 'time'
        elif type.startswith('datetime'):
            type = 'datetime'
        elif type in ('double precision', 'numeric', 'decimal'):
            type = 'float'
        elif type in ('character', 'char'):
            type = 'character'
        return type

    @classmethod
    def get_tactic_types(cls, search_type):
        return {column: cls.get_tactic_type(search_type, column)
                for column in cls.get_column_types(search_type)}

    @classmethod
    def get_db_resource_by_search_type(cls, search_type):
        from pyasm.biz import Project
        # Same owner as native SQL routing, including fixed/shared databases.
        return Project.get_db_resource_by_search_type(search_type)

    @classmethod
    def get_sql_by_search_type(cls, search_type):
        # Original SearchType routing through the owning project's native resource.
        from pyasm.biz import Project
        from pyasm.search.sql import DbContainer
        db_resource = Project.get_db_resource_by_search_type(search_type)
        return DbContainer.get(db_resource)

    @classmethod
    def get_database_impl_by_search_type(cls, search_type):
        from pyasm.biz import Project
        return Project.get_db_resource_by_search_type(search_type).get_database_impl()

    @classmethod
    def column_exists(cls, search_type, column):
        if isinstance(search_type, SObject):
            search_type = search_type.get_search_type()
        column_info = cls.get_column_info(search_type)
        if column.find("->"):
            column = column.split("->")[0]
        return column_info.get(column) is not None

    @classmethod
    def get_foreign_key(cls, search_type):
        column = "code" if cls.column_exists(search_type, "code") else "id"
        return cls.get(search_type).get_table() + "_" + column

    @classmethod
    def get_related_types(cls, search_type, direction="children"):
        from pyasm.biz.project import Project
        from pyasm.biz.schema import Schema
        project = SearchKey.extract_project(search_type)
        if not project:
            database = cls.get(search_type).get_value("database")
            project = Project.get_project_code() if database == "{project}" else database
        schema = Schema.get(project_code=project)
        result = schema.get_related_search_types(search_type, direction)
        parent = schema.get_parent_type(search_type)
        if search_type in ("sthpw/task", "sthpw/note", "sthpw/snapshot"):
            for name in ("sthpw/project", "sthpw/login", "config/process"):
                if name in result:
                    result.remove(name)
        if direction == "children" and parent in result:
            result.remove(parent)
        result.extend(("sthpw/note", "sthpw/task", "sthpw/snapshot"))
        if "sthpw/work_hour" not in result:
            result.append("sthpw/work_hour")
        return result

    @classmethod
    def get_collection_type(cls, search_type):
        namespace, table = SearchKey.extract_base_search_type(search_type).split('/')
        return '%s/%s_in_%s' % (namespace, table, table)


class MissingException(TacticException):
    pass


class SObjectUndo:
    """Original SObject journal and reverse/replay operations."""

    @staticmethod
    def log_undo(sobject, search_code, search_id, is_insert, prev_code=None):
        from pyasm.search.transaction import Transaction
        from pyasm.common.lxml_wrapper import Xml
        search_type = sobject.get_search_type()
        if search_type in ("sthpw/command_log", "sthpw/wdg_settings", "sthpw/transaction_log",
                           "sthpw/change_timestamp", "sthpw/ticket", "sthpw/sync_job", "sthpw/sync_log",
                           "sthpw/sync_server", "sthpw/cache", "sthpw/queue"):
            return
        workflow = Container.get('Workflow:writing')
        if search_type in ('sthpw/message', 'sthpw/message_log') and not (workflow and workflow[0] is sobject):
            return
        old_data, new_data = sobject.data, sobject.update_data
        if not is_insert and not new_data:
            return
        transaction = Transaction.get()
        if not transaction:
            return
        xml = transaction.get_transaction_log()
        if workflow and workflow[0] is sobject:
            Xml.set_attribute(xml.get_root_node(), 'workflow_replay', 'complete')
        sobject_node = transaction.create_log_node("sobject")
        Xml.set_attribute(sobject_node, "search_type", search_type)
        column_types = SearchType.get_column_types(search_type)
        Xml.set_attribute(sobject_node, "search_code" if search_code else "search_id", search_code or search_id)
        if sobject.get_base_search_type() in ('sthpw/note', 'sthpw/task', 'config/process_state'):
            Xml.set_attribute(sobject_node, 'search_id', search_id)
        if prev_code:
            Xml.set_attribute(sobject_node, "prev_search_code", prev_code)
        Xml.set_attribute(sobject_node, "action", "insert" if is_insert else "update")
        for key, value in new_data.items():
            node = xml.create_element("column")
            Xml.set_attribute(node, "name", key)
            if is_insert:
                if value is None:
                    value = ""
                elif column_types.get(key) == "timestamp":
                    value = str(SPTDate.add_gmt_timezone(value))
                elif column_types.get(key) == "boolean":
                    value = "true" if value in (True, "true", 1, "1") else "false"
                Xml.set_attribute(node, "to", value)
            else:
                from_data = old_data.get(key)
                if from_data is None:
                    from_data = ""
                if value is None:
                    value = ""
                elif isinstance(value, str):
                    # Original strings bypass timestamp/boolean normalization here.
                    pass
                elif column_types.get(key) == "timestamp":
                    value = str(SPTDate.add_gmt_timezone(value))
                    from_data = str(SPTDate.add_gmt_timezone(from_data))
                elif column_types.get(key) == "boolean":
                    value = "true" if value in (True, "true") else "false"
                    from_data = "true" if from_data in (True, "true") else "false"
                Xml.set_attribute(node, "from", from_data)
                Xml.set_attribute(node, "to", value)
            xml.append_child(sobject_node, node)

    @staticmethod
    def log_undo_for_delete(sobject):
        from pyasm.search.transaction import Transaction
        from pyasm.common.lxml_wrapper import Xml
        search_type = sobject.get_search_type()
        if search_type in ("sthpw/command_log", "sthpw/change_timestamp", "sthpw/sync_job", "sthpw/sync_log",
                           "sthpw/sync_server", "sthpw/transaction_log", "sthpw/ticket", "sthpw/cache",
                           "sthpw/queue", "sthpw/message", "sthpw/message_log"):
            return
        transaction = Transaction.get()
        if not transaction:
            return
        xml = transaction.get_transaction_log()
        node = transaction.create_log_node("sobject")
        Xml.set_attribute(node, "search_type", search_type)
        code = sobject.get_value("code", no_exception=True)
        Xml.set_attribute(node, "search_code" if code else "search_id", code or sobject.get_id())
        Xml.set_attribute(node, "action", "delete")
        # SqliteImpl.get_temp_column_name() is empty; no temporary column is removed.
        for key, value in sobject.data.items():
            column = xml.create_element("column")
            Xml.set_attribute(column, "name", key)
            Xml.set_attribute(column, "from", "" if value is None else value)
            xml.append_child(node, column)

    @staticmethod
    def undo(node):
        '''function that acutally does the undo'''
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException

        search_type = Xml.get_attribute(node,"search_type")
        search_id = Xml.get_attribute(node,"search_id")
        search_code = Xml.get_attribute(node,"search_code")

        # ensure that this is a proper search id
        if search_id:
            try:
                search_id = int(search_id)
            except ValueError as e:
                # try to extract from quotes: example '15'
                if search_id.startswith("'") and search_id.endswith("'"):
                    try:
                        search_id = int(search_id.strip("'"))
                    except ValueError as e:
                        print("ERROR: undo error: ", e.__str__())
                        return

        # get the sobject
        search = Search(search_type)
        if search_code:
            search.add_filter("code", search_code)
        else:
            search.add_filter("id", search_id)
        sobject = search.get_sobject()

        # NOTE:
        # If the sobject is none, that means that the system thought it
        # exists but it actually didn't.  The only know reason for this
        # would be that a commit failed due to referential integrity
        # violation.  This is not reported until commit time.
        # This will at least allow backout of that error
        action = Xml.get_attribute(node,"action")


        if action == "delete":
            # if the sobject still exists, we have an inconsistency
            if sobject:
                print("WARNING: deleted sobject still exists [%s, %s]" % (search_type, search_code))

            # recreate the sobject
            sobject = SearchType.create(search_type)

            columns = Xml.xpath(node,"column")
           
            tmp_col_name = sobject.get_database_impl().get_temp_column_name()
          
            for column in columns:
                name = Xml.get_attribute(column,"name")
                # id and code are set outside of the columns.  They
                # recorded only for information purposes.  Should they
                # even be recorded at all?
                if name in ['code', 'id', tmp_col_name]:
                    continue

                value = Xml.get_attribute(column,"from")
                sobject.set_value(name,value)
            if len(columns) > 0:
                if search_code:
                    sobject.set_value("code", search_code)
                    if search_type.split('?')[0] in ('sthpw/note', 'sthpw/task', 'config/process_state'):
                        identity = next((column.get('from') for column in columns if column.get('name') == 'id'), None)
                        if identity:
                            sobject.set_id(int(identity))
                else:
                    sobject.set_id(search_id)

                sobject.set_force_insert()
                sobject.commit()


        # if no sobject exists, then don't bother updating.
        # TODO: there are some operations where the object might not exist
        # but in general it should and there should probably be more enforcement
        # on this
        if sobject == None:
            if not Environment.get_security().is_admin():
                raise SecurityException('Undo object is missing or outside the current read policy: %s %s' % (search_type, search_code or search_id))
            return


        if action == "insert":
            if search_type.split('?')[0] in ('sthpw/note', 'sthpw/task', 'config/process_state'):
                Xml.set_attribute(node, 'search_id', sobject.get_id())
            # on an insert simply delete
            sobject.delete(log=False)
        elif action == "update":
            # revert to the old values
            columns = Xml.xpath(node,"column")
            for column in columns:
                name = Xml.get_attribute(column,"name")
                value = Xml.get_attribute(column,"from")
                sobject.set_value(name,value)

            if len(columns) > 0:
                sobject.commit()


    @staticmethod
    def redo(node, no_exception=True):
        #no_exception=False
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException

        import time
        start = time.time()

        from dateutil import parser
        from pyasm.search.database_impl import DatabaseImpl
        search_type = Xml.get_attribute(node,"search_type")
        action = Xml.get_attribute(node,"action")

        column_types = SearchType.get_column_types(search_type)

        # if the code was changed, we have to use the prev search code
        search_code = Xml.get_attribute(node,"prev_search_code")
        if not search_code:
            search_code = Xml.get_attribute(node,"search_code")

        # Use of this is deprecated as of 4.0
        search_id = Xml.get_attribute(node,"search_id")


        # get the transaction time if it was supplied
        transaction_time = Xml.get_attribute(node, "timestamp")
        if transaction_time:
            transaction_time = parser.parse(transaction_time)
            # Source changed_on values use the user's preferred wall clock,
            # while the journal timestamp is GMT. Compare in that same clock.
            from pyasm.biz import PrefSetting
            preferred = PrefSetting.get_value_by_key('timezone')
            transaction_time = (SPTDate.convert_to_local(transaction_time) if preferred in ('local', '')
                                else SPTDate.convert_to_timezone(transaction_time, preferred))

        # get the changed_timestamps for this sobject
        # if this in an insert, then the change_timestamp entry cannot exist
        # so skip
        if search_code and action != "insert":
            search = Search("sthpw/change_timestamp")
            search.add_filter("search_type", search_type)
            search.add_filter("search_code", search_code)
            change_log = search.get_sobject()
        else:
            change_log = None

        if not change_log:
            changed_on = {}
        else:
            changed_on = change_log.get_json_value("changed_on", {})


        search_type_obj = SearchType.get(search_type)


        database_type = DatabaseImpl.get().get_database_type()
        if action == "insert":
            # create a new sobject
            sobject = SearchType.create(search_type)

            columns = Xml.xpath(node,"column")
            for column in columns:
                name = Xml.get_attribute(column,"name")

                if not SearchType.column_exists(search_type, name):
                    msg = "Column [%s] does not exist in search_type [%s]" % (name, sobject.get_search_type() )
                    if no_exception:
                        print("WARNING: %s" % msg)
                        continue
                    else:
                        raise MissingException(msg)

                value = Xml.get_attribute(column,"to")
                quoted = True
                # only SQL server can't interpret GETDATE() function as a string
                
                column_type = column_types.get(name)
                if database_type == 'SQLServer':
                    if column_type == 'datetime2' and value =='GETDATE()':
                        quoted = False
                elif database_type == 'Sqlite':
                    if column_type == 'timestamp' and value in ["CURRENT_TIMESTAMP", "datetime('now')"]:
                        quoted = False
                elif database_type == 'MySQL':
                    if column_type in ['timestamp', 'datetime'] and value in ["CURRENT_TIMESTAMP", "UTC_TIMESTAMP()"]:
                        quoted = False


                if column_type == 'timestamp':
                    try:
                        if value == "now()":
                            value = SPTDate.now()
                        else:
                            value = SPTDate.convert(value, is_gmt=True)
                    except:
                        print("WARNING: could not parse timestamp [%s]" % value)

                elif column_type == 'boolean':
                    if value == 'true':
                        value = True
                    else:
                        value = False



                sobject.set_value(name,value, quoted=quoted)
            if search_code:
                sobject.set_value("code", search_code)
                if search_type.split('?')[0] in ('sthpw/note', 'sthpw/task', 'config/process_state') and node.get('search_id'):
                    sobject.set_id(int(node.get('search_id')))
                    sobject.set_force_insert()
            else:
                sobject.set_id(search_id)

            sobject.commit()

        elif action == "update":

            # get the sobject
            if search_code:
                sobject = Search.get_by_code(search_type, search_code)
            else:
                sobject = Search.get_by_id(search_type, search_id)
            if not sobject:
                msg = "sobject [%s, code=%s] does not exist when trying to update in redo" % (search_type, search_code)
                if not Environment.get_security().is_admin():
                    raise SecurityException('Redo object is missing or outside the current read policy')
                if no_exception:
                    print("WARNING: %s" % msg)
                    return
                else:
                    raise MissingException(msg)
                    

            # set to the new values
            columns = Xml.xpath(node,"column")
            for column in columns:
                name = Xml.get_attribute(column,"name")
                value = Xml.get_attribute(column,"to")

                # if the col was changed later than this transaction
                # then skip
                col_changed = changed_on.get(name)
                if col_changed and transaction_time:
                    # need to convert to timestamps
                    # if the date is mangled, then change the data
                    try:
                        col_changed = parser.parse(col_changed)
                        compared_time = transaction_time if col_changed.tzinfo else transaction_time.replace(tzinfo=None)
                        if col_changed > compared_time:
                            print("Column [%s] was changed after this transaction ... skipping" % name)
                            print("Transaction time: ", transaction_time)
                            print("Column modification time: ", col_changed)
                            continue
                    except:
                        print("WARNING: modification date mangled for column [%s]... skipping" % name)

                if not SearchType.column_exists(search_type, name):
                    msg = "WARNING: Column [%s] does not exist in search_type [%s]" % (name, sobject.get_search_type() )
                    if no_exception:
                        print("WARNING: %s" % msg)
                        continue
                    else:
                        raise MissingException(msg)


                quoted = True
                # only SQL server can't interpret GETDATE() function as a string
                column_type = column_types.get(name)
                if column_type == 'datetime2' and value =='GETDATE()':
                    quoted = False

                elif column_type == 'timestamp' and value:
                    # Journal values already use the database GMT clock.
                    value = SPTDate.convert(value, is_gmt=True)
                elif column_type == 'boolean':
                    if value == 'true':
                        value = True
                    else:
                        value = False

                sobject.set_value(name,value, quoted=quoted)


            if len(columns) > 0:
                sobject.commit()


        elif action == "delete":
            # get the sobject
            if search_code:
                sobject = Search.get_by_code(search_type, search_code)
            else:
                # Deprecated
                sobject = Search.get_by_id(search_type, search_id)
                search_code = search_id

            if sobject == None:
                error = "Error trying to delete sobject [%s, %s] that does not exist." % (search_type, search_code)
                if not Environment.get_security().is_admin():
                    raise SecurityException('Redo object is missing or outside the current read policy')
                if no_exception:
                    print("WARNING: %s" % error)
                else:
                    raise MissingException(error)
            else:
                sobject.delete(log=False)



class Search(Base):
    def __init__(self, search_type, project_code=None, sudo=False):
        from pyasm.biz.project import Project, ProjectType
        from pyasm.biz.schema import Schema
        context = _context.get()
        if sudo:
            from pyasm.common.environment import Environment
            if Environment.get_security() is None:
                raise UnsupportedContract("Search sudo requires Environment Security")
        if isinstance(search_type, SearchType):
            search_type = search_type.get_base_key()
        elif isinstance(search_type, type) and issubclass(search_type, SObject):
            search_type = search_type.SEARCH_TYPE
        self._check_resource_access(search_type)
        project_code = project_code or context.project
        self.definition, self.database, self.table = context.store.resolve(search_type, project_code)
        self.search_type_obj = SearchType.get(search_type)
        self.sobject_class = None  # Loaded only when constructing rows, as in TACTIC.
        self.store = context.store
        self.search_type = Project.get_full_search_type(search_type, project_code=project_code)
        self.db_resource = Project.get_db_resource_by_search_type(self.search_type)
        self.project_code = "sthpw" if self.search_type.startswith("sthpw/") else breakup_search_type(self.search_type).get("project") or self.database
        self.columns = SearchType.get_column_info(self.search_type)
        from pyasm.search.sql import Select
        self.select = Select()
        self.select._search_owned = self
        self.select.db_resource = self.db_resource
        self.select.impl = self.db_resource.get_database_impl()
        self.select.tables.append(self.table)
        self.filters, self.parameters = self.select.wheres, []
        self.order_bys = self.select.order_bys
        self.order_columns = set()
        self.selected_columns = self.select.columns
        self.joins, self.join_sources = self.select.joins, set()
        self.join_columns = {self.table: self.columns}
        self.order_by = True
        self.retired_filter = False
        self.distinct = self.null_filter = self.is_search_done = False
        self.sobjects = []
        self.limit = self.offset = None
        self.show_retired = False
        self.security_filter = False
        self.custom_filter = False
        self.raw_where = False
        from pyasm.common.environment import Environment
        security = Environment.get_security()
        if security is not None:
            if not sudo:
                self.check_security()
            base = self.get_base_search_type()
            if search_type in ['sthpw/task', 'sthpw/note', 'sthpw/work_hour']:
                project, default = Project.get_project_code(), 'allow'
            elif not base.startswith(('sthpw/', 'config/')):
                project, default = self.project_code, 'deny'
            else:
                default = None
            if default is not None:
                keys = [{'code': base}, {'code': base, 'project': project},
                        {'code': '*'}, {'code': '*', 'project': project}]
                if not security.check_access('search_type', keys, 'view', default=default):
                    self.set_null_filter()

    def check_security(self):
        from pyasm.common.environment import Environment
        from pyasm.security.access_manager import Sudo
        security = Environment.get_security()
        if security is None:
            return
        if Environment.get_user_name() == 'admin' or Sudo.is_sudo():
            return
        base = self.get_base_search_type()
        if base in {'sthpw/login', 'sthpw/login_in_group', 'sthpw/login_group',
                    'sthpw/transaction_log', 'sthpw/change_timestamp', 'sthpw/exception_log', 'sthpw/ticket'}:
            if not security.check_access('search_type', base, 'view'):
                raise Exception('Search Permission Denied [%s]' % base)

    @staticmethod
    def _check_resource_access(search_type):
        policy = Container.get('Expression:check_record_access')
        if policy:
            policy(SearchKey.extract_base_search_type(search_type))
        if SearchKey.extract_base_search_type(search_type) != 'sthpw/db_resource':
            return
        # Connection passwords are server secrets, including joined script reads.
        from pyasm.security.authenticator import Authenticator
        from pyasm.common.errors import SecurityException
        context = _context.get()
        with context.store.connection() as db:
            if not Authenticator._admin(db, context.login, context.store.get_db_resource().get_database_impl().get_parameter()):
                raise SecurityException('Database resources require administrator access')

    def copy(self):
        from copy import deepcopy
        # Original copy starts with a fresh Search; recheck the current ACL.
        search = Search(self.search_type, project_code=self.project_code)
        denied = search.null_filter
        search.select = deepcopy(self.select, {id(self): search,
            id(self.select.impl): self.select.impl, id(self.db_resource): self.db_resource,
            id(self.select.sql): self.select.sql})
        search.filters = search.select.wheres
        search.joins = search.select.joins
        search.order_bys = search.select.order_bys
        search.selected_columns = search.select.columns
        for name in ("parameters", "order_columns",
                     "join_sources", "join_columns", "order_by",
                     "retired_filter", "distinct", "null_filter", "limit",
                     "offset", "show_retired", "raw_where"):
            setattr(search, name, deepcopy(getattr(self, name)))
        search.null_filter = denied or self.null_filter
        return search

    def set_security_filter(self):
        self.security_filter = True

    def add_user_filter(self, user=None, column=None, table=''):
        from pyasm.common import Environment
        user = Environment.get_user_name() if user is None else user
        self.add_filter(column or 'login', user, table=table or self.table)

    def add_enum_order_by(self, column, values, table=None):
        if not values:
            return
        from pyasm.search.sql import Sql
        expression = 'CASE %s %s ELSE %d END' % (self._column(column, table or ''),
            ' '.join('WHEN %s THEN %d' % (Sql.quote(value), index) for index, value in enumerate(values, 1)), len(values) + 1)
        self.order_bys.append(expression)

    def get_search_type(self):
        return self.search_type

    get_full_search_type = get_search_type

    def get_base_search_type(self):
        return SearchKey.extract_base_search_type(self.search_type)

    def get_database(self):
        return self.database

    def get_db_resource(self):
        return self.db_resource

    def get_sql(self):
        return self.get_db_resource().get_sql()

    def get_select(self):
        '''returns the select object'''
        return self.select

    def get_database_impl(self):
        return self.get_db_resource().get_database_impl()

    def get_database_type(self):
        return self.get_db_resource().get_database_type()

    def get_project_code(self):
        return self.project_code

    def get_id_col(self):
        return "id"

    def get_table(self):
        return self.table

    def get_search_type_obj(self):
        return SearchType.get(self.search_type)

    def get_columns(self, table=None, show_hidden=False):
        return list(self.store.columns(self.db_resource, table)) if table else list(self.columns)

    def _placeholder(self):
        return self.db_resource.get_database_impl().get_parameter()

    def _same_database(self, resource):
        return self.db_resource._get_connection_key() == resource._get_connection_key()

    def column_exists(self, column):
        return column.split("->", 1)[0] in self.columns

    def _column(self, name, table=""):
        if isinstance(name, str) and "." in name:
            qualifier, name = name.split(".", 1)
            if table and qualifier != table:
                raise ValueError("Conflicting column table qualifiers")
            table = qualifier
        table = table or self.table
        if table not in self.join_columns:
            raise UnsupportedContract("Table has not been joined: " + str(table))
        if name not in self.join_columns[table]:
            raise UnsupportedContract("Unknown column or SQL expression: " + str(name))
        return identifier(table) + "." + identifier(name)

    def add_filter(self, name, value, op="=", quoted=None, table=""):
        if value == "__ALL__":
            return
        column = self._column(name, table)
        op = op.lower().strip()
        if op not in ("=", "!=", "<>", "<", ">", "<=", ">=", "like", "not like", "is", "is not", "in", "not in"):
            raise UnsupportedContract("Unsupported filter operator: " + op)
        if value is None or isinstance(value, list) and not value:
            # Original Select ignores the operator for a Python None value.
            self.filters.append(column + " IS NULL")
            return
        if op in ("in", "not in"):
            self.add_filters(name, value, table, op)
            return
        if isinstance(value, (list, tuple)):
            value = value[0]
        source_table, column_name = name.split(".", 1) if "." in name else (table or self.table, name)
        data_type = self.join_columns[source_table][column_name]["data_type"]
        # Day columns are wall-clock dates in SObject.commit, not UTC instants.
        if data_type in ("timestamp", "datetime", "datetime2"):
            if isinstance(value, str):
                impl = self.db_resource.get_database_impl()
                expression = impl.get_timestamp_filter(value) if quoted in (None, False) or value.lower() == 'now' else None
                if expression is not None:
                    if not SObject.is_day_column(column_name) and op in ('=', '!=', '<>', '<', '>', '<=', '>='):
                        column, expression = impl.get_datetime_filter(column, expression, expression=True)
                    self.filters.append(f"{column} {op.upper()} {expression}")
                    return
                try:
                    value = parser.parse(value)
                except ValueError:
                    pass
            if isinstance(value, datetime):
                value = str(value.replace(tzinfo=None) if SObject.is_day_column(column_name) else SPTDate.convert_to_local(value))
        if quoted is None:
            if value == "NULL":
                quoted = False
            elif data_type == "boolean":
                value = self.db_resource.get_database_impl().process_value(name, value, data_type)['value']
                quoted = False
            else:
                quoted = True
        if quoted == "column":
            self.filters.append(f"{column} {op.upper()} {self._column(value)}")
        elif value == "NULL" and not quoted:
            self.filters.append(f"{column} {op.upper()} NULL")
        else:
            if data_type in ('timestamp', 'datetime', 'datetime2') and not SObject.is_day_column(column_name) and op in ('=', '!=', '<>', '<', '>', '<=', '>='):
                column, value = self.db_resource.get_database_impl().get_datetime_filter(column, value)
            self.filters.append(f"{column} {op.upper()} {self._placeholder()}")
            self.parameters.append(str(value) if quoted else value)

    def add_null_filter(self, name):
        self.add_filter(name, "NULL", quoted=False, op="is")

    def add_empty_filter(self, name):
        self.add_op('begin')
        self.add_filter(name, 'NULL', quoted=False, op='is')
        self.add_filter(name, '', op='=')
        self.add_op('or')

    def add_filters(self, name, values, table="", op="in"):
        column = self._column(name, table)
        if op not in ("in", "not in"):
            raise UnsupportedContract("Unsupported list filter operator: " + op)
        if not values or values == [""]:
            # Even empty NOT IN matches no persisted rows in the original Select.
            self.filters.append(self._column("id") + " IS NULL")
            return
        if not isinstance(values, (list, tuple)):
            raise ValueError("List filter values must be a list or tuple")
        self.filters.append(f"{column} {op.upper()} ({','.join(self._placeholder() for _ in values)})")
        self.parameters.extend(values)

    def add_id_filter(self, value):
        self.add_filter(self.get_id_col(), value if isinstance(value, int) else str(value))
        # Original explicit identity filters include retired rows.
        self.set_show_retired(True)

    def add_code_filter(self, value):
        self.add_filter('code', value)
        self.set_show_retired(True)

    def add_project_filter(self, project_code=None, show_unset=True):
        from pyasm.biz.project import Project
        project_code = project_code or Project.get_project_code()
        column = self._column('project_code')
        conditions = []
        if isinstance(project_code, list):
            codes = project_code
        else:
            codes = [project_code]
            if show_unset:
                conditions.append(column + ' IS NULL')
        for code in codes:
            conditions.append('(%s = %s OR %s LIKE %s)' % (column, self._placeholder(), column, self._placeholder()))
            self.parameters.extend([code, '%%||%s||%%' % code])
        # Original list filters have no outer group: preserve their OR precedence.
        expression = ' OR '.join(conditions)
        self.filters.append(expression if isinstance(project_code, list) else '(' + expression + ')')

    def add_sobject_filter(self, sobject, prefix="", op=None):
        '''convenience function to add a filter for the given sobject'''
        self.add_filter("%ssearch_type" % prefix, sobject.get_search_type() )

        if SearchType.column_exists(sobject.get_search_type(), "code") and \
            SearchType.column_exists(self.get_search_type(), "%ssearch_code" % prefix):
            search_code = sobject.get_value("code")
            if not op:
                op = '='
            self.add_filter("%ssearch_code" % prefix, search_code, op=op )
        else:
            if not op:
                op = '='
            sobject_id = sobject.get_id()
            if isinstance(sobject_id, int):
                self.add_filter("%ssearch_id" % prefix, sobject.get_id(), op=op )
            else:
                self.add_filter("%ssearch_code" % prefix, sobject.get_id(), op=op )

    def add_sobjects_filter(self, sobjects, prefix="", op='in'):
        '''convenience function to add a filter for the given sobjects'''

        if not sobjects:
            return

        search_type = sobjects[0].get_search_type()
        self.add_filter("%ssearch_type" % prefix, search_type )

        # assume they are of the same type
        sobject = sobjects[0]
        if self.column_exists("%ssearch_code" % prefix):
            search_codes = [x.get_value("code") for x in sobjects if x]
            self.add_filters("%ssearch_code" % prefix, search_codes, op=op )
        else:
            search_ids = [str(x.get_id()) for x in sobjects if x]
            self.add_filters("%ssearch_id" % prefix, search_ids, op=op )

    def add_parent_filter(self, parent, relationship=None):
        from pyasm.biz.schema import Schema
        if not parent:
            self.add_id_filter(0)
            return
        if isinstance(parent, str):
            parent = Search.get_by_search_key(parent)
        if parent is None:
            raise LookupError("Parent SObject does not exist")
        parent_type, search_type = parent.get_search_type(), self.get_search_type()
        if parent_type == search_type:
            self.add_relationship_filter(parent)
            return
        schema = Schema.get(project_code=self.project_code)
        relationship = relationship or schema.get_relationship(parent_type, search_type)
        attrs = schema.get_relationship_attrs(parent_type, search_type)
        if not relationship:
            raise LookupError("Search types are not related")
        if relationship in ("code", "id"):
            self.add_relationship_filter(parent)
        elif relationship == "parent_code":
            self.add_filter("parent_code", parent.get_code())
        elif relationship in ("search_type", "search_code", "search_id"):
            prefix = attrs.get("prefix", "")
            prefix = prefix + "_" if prefix else ""
            from pyasm.biz import Project
            base = parent.get_base_search_type()
            # The original cache masks these two spellings until it is cleared.
            # Match references to the same system-project parent after rollback,
            # without merging objects belonging to ordinary project databases.
            if parent.get_project_code() in ('admin', 'sthpw') and Project.get_full_search_type(base, project_code=parent.get_project_code()) == base:
                self.add_filters(prefix + "search_type", [base, base + '?project=admin', base + '?project=sthpw'])
            else:
                self.add_filter(prefix + "search_type", parent_type)
            if self.column_exists(prefix + "search_code") and SearchType.column_exists(parent_type, 'code'):
                self.add_filter(prefix + "search_code", parent.get_code())
            else:
                self.add_filter(prefix + "search_id", parent.get_id())
        elif relationship in ("instance", "general"):
            self.add_relationship_filter(parent)
        else:
            raise UnsupportedContract("Unsupported parent relationship: " + str(relationship))

    def _get_relationship_attrs(self, schema, related_type, path=None, type=None):
        attrs = schema.get_relationship_attrs(self.get_search_type(), related_type, path=path, type=type)
        if not attrs and path and self.get_base_search_type() == SearchKey.extract_base_search_type(related_type):
            default = schema.get_relationship_attrs(self.get_search_type(), related_type, type=type)
            if default.get('relationship') == 'instance':
                if path not in ('parent', 'child'):
                    raise LookupError('Self-instance relationship path is not defined: ' + str(path))
                attrs = default
        return attrs

    def _add_instance_relationship(self, schema, attrs, related_type, path=None):
        instance_type = attrs.get('instance_type')
        if not instance_type:
            raise ValueError('No instance_type defined')
        if self.get_base_search_type() == SearchKey.extract_base_search_type(related_type):
            # Handler joins the child endpoint through parent, and filters the owner through child.
            result_path = path if path in ('parent', 'child') else 'parent'
            owner_edge, member_edge = schema._get_self_instance_edges(instance_type, related_type)
            result_edge, source_edge = (member_edge, owner_edge) if result_path == 'parent' else (owner_edge, member_edge)
            self._check_resource_access(instance_type)
            instance = Search(build_search_type(instance_type, self.project_code))
            if instance.null_filter:
                from pyasm.common.errors import SecurityException
                raise SecurityException('Joined search type is not accessible: ' + instance_type)
            if not self._same_database(instance.get_db_resource()):
                raise UnsupportedContract('Cross-resource instance relationships are not migrated')
            alias = '_instance_' + str(len(self.joins))
            while alias in self.join_columns:
                alias += '_'
            for edge in (result_edge, source_edge):
                instance._column(edge['from_col'])
                self._column(edge['to_col'])
            self.join_columns[alias] = instance.columns
            self.join_sources.add(alias)
            self.select.join_tables.add(alias)
            self.joins.append('LEFT OUTER JOIN %s AS %s ON %s = %s' % (
                identifier(instance.table), identifier(alias),
                self._column(result_edge['to_col']), self._column(result_edge['from_col'], alias)))
            related_alias = alias + '_related'
            while related_alias in self.join_columns:
                related_alias += '_'
            self.join_columns[related_alias] = self.columns
            self.join_sources.add(related_alias)
            self.select.join_tables.add(related_alias)
            self.joins.append('LEFT OUTER JOIN %s AS %s ON %s = %s' % (
                identifier(self.table), identifier(related_alias),
                self._column(source_edge['from_col'], alias), self._column(source_edge['to_col'], related_alias)))
            table, column, source = related_alias, source_edge['to_col'], source_edge['to_col']
        else:
            self.add_join(instance_type, self.get_search_type())
            self.add_join(related_type, instance_type)
            table = SearchType.get(related_type).get_table()
            column = attrs['to_col'] if attrs['from'] == self.get_base_search_type() else attrs['from_col']
            source = column
        self.add_column('*', table=self.table)
        self.add_column(column, table=table, as_column='_related_code')
        return table, column, source

    def add_relationship_filter(self, sobject, path=None):
        from pyasm.biz.schema import Schema
        search_type, related_type = self.get_search_type(), sobject.get_search_type()
        project = sobject.get_project_code() if self.project_code == "sthpw" else self.project_code
        schema = Schema.get(project_code=project)
        attrs = self._get_relationship_attrs(schema, related_type, path)
        if search_type == related_type and attrs.get('relationship') not in ('instance', 'general'):
            self.add_id_filter(sobject.get_id())
            return
        if not attrs:
            raise LookupError("Search types are not related")
        if attrs.get("disabled"):
            self.set_null_filter()
            return
        forward = attrs["from"] in (self.get_base_search_type(), "*")
        relationship = attrs.get("relationship")
        if relationship == "search_type":
            attrs = schema.resolve_relationship_attrs(attrs, search_type, related_type)
            relationship = attrs['relationship']
        if relationship in ("id", "code"):
            column, source = (attrs.get("from_col"), attrs.get("to_col")) if forward else (attrs.get("to_col"), attrs.get("from_col"))
            value = sobject.get_value(source)
            if value:
                self.add_filter(column, value)
            else:
                self.set_null_filter()
        elif relationship in ("search_id", "search_code"):
            prefix = attrs.get("prefix", "")
            prefix = prefix + "_" if prefix else ""
            column = "search_id" if relationship == "search_id" else "search_code"
            if forward:
                self.add_filter(prefix + "search_type", sobject.get_search_type())
                self.add_filter(prefix + column, sobject.get_id() if relationship == "search_id" else sobject.get_code())
            else:
                # Original reverse single-object lookup does not use the prefix.
                self.add_filter("id" if relationship == "search_id" else "code", sobject.get_value(column))
        elif relationship == "general":
            self.add_relationship_filters([sobject], path=path)
        elif relationship == "instance":
            if not self._same_database(sobject.get_db_resource()):
                raise UnsupportedContract("Cross-resource instance relationships are not migrated")
            related_table, column, source = self._add_instance_relationship(schema, attrs, related_type, path)
            value = sobject.get_value(source)
            if not value:
                self.set_null_filter()
                return
            # Source filters the wrong table in reverse, and the wrong column for unequal keys.
            self.add_filter(column, value, table=related_table)
        else:
            raise UnsupportedContract("Relationship is not migrated: " + str(relationship))

    def _add_parent_type_filter(self, parent, prefix=''):
        search_type = parent.get_search_type()
        base = parent.get_base_search_type()
        full = SearchType.build_search_type(search_type, parent.get_project_code())
        if not prefix and self.get_base_search_type() in ('sthpw/note', 'sthpw/task') and full != base:
            # Native scripts can persist a bare type; its logical project must still match.
            self.add_op('begin')
            self.add_filter('search_type', full)
            self.add_op('begin')
            self.add_filter('search_type', base)
            self.add_filter('project_code', parent.get_project_code())
            self.add_op('and')
            self.add_op('or')
        else:
            self.add_filter(prefix + 'search_type', search_type)

    def add_relationship_filters(self, sobjects, op='in', path=None, type=None):
        from pyasm.biz.schema import Schema
        if not sobjects:
            self.set_null_filter()
            return
        first = sobjects[0]
        search_type, related_type = self.get_base_search_type(), first.get_base_search_type()
        project = first.get_project_code() if self.project_code == "sthpw" else self.project_code
        schema = Schema.get(project_code=project)
        attrs = self._get_relationship_attrs(schema, first.get_search_type(), path=path, type=type)
        relationship = attrs.get("relationship")
        if search_type == related_type and not attrs:
            column = "code" if SearchType.column_exists(search_type, "code") else "id"
            self.add_filters(column, [obj.get_value(column) for obj in sobjects], op=op)
            return
        if not attrs:
            raise LookupError("Search types are not related")
        if attrs.get("disabled"):
            self.set_null_filter()
            return
        forward = attrs["from"] == search_type
        if relationship in ("code", "id"):
            column, source = (attrs.get("from_col"), attrs.get("to_col")) if forward else (attrs.get("to_col"), attrs.get("from_col"))
            self.add_filters(column, [obj.get_value(source) for obj in sobjects], op=op)
        elif relationship in ("search_type", "search_code", "search_id"):
            prefix = attrs.get("prefix", "")
            prefix = prefix + "_" if prefix else ""
            if forward:
                if not attrs.get("to_col"):
                    attrs = schema.resolve_relationship_attrs(attrs, self.get_search_type(), first.get_search_type())
                from_col, to_col = attrs["from_col"], attrs["to_col"]
                if any(obj.get_search_type() != first.get_search_type() for obj in sobjects):
                    if op != "in":
                        raise ValueError("Multiple search types require an IN relationship filter")
                    self.add_op("begin")
                    for obj in sobjects:
                        self.add_op("begin")
                        self._add_parent_type_filter(obj)
                        self.add_filter(from_col, obj.get_value(to_col))
                        self.add_op("and")
                    self.add_op("or")
                else:
                    values = [obj.get_value(to_col) for obj in sobjects]
                    self._add_parent_type_filter(first, prefix)
                    self.add_filters(from_col if isinstance(values[0], int) else prefix + "search_code", values, op=op)
            else:
                column = prefix + ("search_code" if SearchType.column_exists(related_type, prefix + "search_code") else "search_id")
                target = "code" if column.endswith("search_code") else "id"
                values = [obj.get_value(column) for obj in sobjects if obj.get_value(prefix + "search_type") == self.get_search_type()]
                self.add_filters(target, list(dict.fromkeys(value for value in values if value)), op=op)
        elif relationship == "general":
            from pyasm.biz.sobject_connection import SObjectConnection
            target = 'src' if forward else 'dst'
            links = SObjectConnection.get_connections(sobjects, direction=target)
            ids = [link.get_value(target + '_search_id') for link in links
                   if link.get_value(target + '_search_type') == self.get_search_type()]
            self.add_filters(self.get_id_col(), list(dict.fromkeys(ids)), op=op)
        elif relationship == "instance":
            if any(obj.get_search_type() != first.get_search_type()
                   or not self._same_database(obj.get_db_resource()) for obj in sobjects):
                raise UnsupportedContract("Instance lists require one source type on the same database resource")
            related_table, column, source = self._add_instance_relationship(schema, attrs, first.get_search_type(), path)
            # The original instance branch ignores the supplied list and operator.
            self.add_filters(column, SObject.get_values(sobjects, source), table=related_table, op=op)
        else:
            raise UnsupportedContract("Relationship is not migrated: " + str(relationship))

    def add_join(self, to_search_type, from_search_type=None, path=None, join=None):
        from pyasm.biz.schema import Schema
        to_search_type = SearchType.get(to_search_type).get_base_key()
        from_search_type = SearchType.get(from_search_type).get_base_key() if from_search_type else self.get_base_search_type()
        if to_search_type == from_search_type:
            return
        attrs = Schema.get(project_code=self.project_code).get_relationship_attrs(from_search_type, to_search_type, path=path)
        if not attrs:
            return
        source_table = SearchType.get(from_search_type).get_table()
        target_table = SearchType.get(to_search_type).get_table()
        if source_table not in self.join_columns:
            raise ValueError("Join source must already belong to this search")
        self._check_resource_access(to_search_type)
        from pyasm.common import Environment
        security = Environment.get_security()
        if to_search_type == 'sthpw/note' and (security is None or not security.check_access('builtin', 'view_private_notes', 'view', default='deny')):
            raise UnsupportedContract('Joining private notes requires the remaining joined object access policy')
        target = Search(build_search_type(to_search_type, self.project_code))
        if target.null_filter:
            from pyasm.common.errors import SecurityException
            raise SecurityException('Joined search type is not accessible: ' + to_search_type)
        if not self._same_database(target.get_db_resource()):
            raise UnsupportedContract('Joins between separate database resources are not supported')
        if target_table in self.join_columns:
            # Preserve first-join-wins for a repeated target, including other paths.
            return
        join = (join or "LEFT OUTER").upper()
        if join not in ("LEFT OUTER", "INNER", "RIGHT OUTER"):
            raise ValueError("Invalid join type")
        target_columns = target.columns
        relationship = attrs.get("relationship")
        if relationship == "search_type":
            relationship = Schema.get(project_code=self.project_code).resolve_search_type_relationship(attrs, from_search_type, to_search_type)
        forward = attrs.get("from") in (from_search_type, '*')
        if relationship in ("search_code", "search_id"):
            prefix = attrs.get('prefix', '')
            prefix = prefix + '_' if prefix else ''
            child_col = prefix + relationship
            parent_col = 'code' if relationship == 'search_code' else 'id'
            source_col, target_col = (child_col, parent_col) if forward else (parent_col, child_col)
            child_table = source_table if forward else target_table
            parent_type = to_search_type if forward else from_search_type
            from pyasm.biz.project import Project
            parent_type = Project.get_full_search_type(parent_type, project_code=self.project_code)
            type_column = prefix + 'search_type'
            child_columns = self.join_columns[source_table] if forward else target_columns
            if type_column not in child_columns:
                raise UnsupportedContract('Joined object reference has no search_type column')
        else:
            source_col, target_col = (attrs.get("from_col"), attrs.get("to_col")) if forward else (attrs.get("to_col"), attrs.get("from_col"))
        if not source_col:
            source_col = target_table + "_id"
            if source_col in self.join_columns[source_table]:
                target_col = "id"
            else:
                source_col, target_col = "id", source_table + "_id"
        target_col = target_col or "id"
        if source_col not in self.join_columns[source_table] or target_col not in target_columns:
            raise UnsupportedContract("Joined relationship refers to a missing column")
        self.join_columns[target_table] = target_columns
        self.join_sources.add(target_table)
        self.joins.append(f"{join} JOIN {identifier(target_table)} ON {self._column(source_col, source_table)} = {self._column(target_col, target_table)}")
        self.select.join_tables.add(target_table)
        if relationship in ("search_code", "search_id"):
            # Original uses the main search type here, even when it is the child.
            self.add_filter(type_column, parent_type, table=child_table)

    def add_search_filter(self, name, search, op='in', table=''):
        if op not in ("in", "not in"):
            raise ValueError("Expected IN or NOT IN")
        if not self._same_database(search.get_db_resource()):
            # Original cross-database fallback ignores both op and table.
            source = search.selected_columns[0]
            values = SObject.get_values(search.get_sobjects(), source, unique=True)
            self.add_filters(name, values)
        else:
            # Capture the subquery now, before subsequent changes to the search.
            column = self._column(name, table)
            sql, parameters = search._statement(default_order=False, apply_retired=False)
            self.filters.append(f"{column} {op.upper()} ({sql})")
            self.parameters.extend(parameters)

    def add_relationship_search_filter(self, search, op='in', delay_null=False, use_multidb=None, path=None):
        from pyasm.biz.schema import Schema
        if not search:
            self.set_null_filter()
            return False
        if op not in ("in", "not in"):
            raise ValueError("Expected IN or NOT IN")
        search.order_by = False
        search_type, related_type = self.get_base_search_type(), search.get_base_search_type()
        project = search.project_code if self.project_code == "sthpw" else self.project_code
        schema = Schema.get(project_code=project)
        attrs = self._get_relationship_attrs(schema, search.get_search_type(), path=path)
        if not path and search_type == related_type and attrs.get('relationship') not in ('instance', 'general'):
            search.add_column("id")
            self.add_search_filter("id", search, op, table=self.table)
            return True
        if not attrs:
            raise LookupError("Search types are not related")
        relationship = attrs.get("relationship")
        forward = attrs["from"] == search_type
        if relationship == 'general':
            self.add_relationship_filters(search.get_sobjects(), op=op, path=path)
            return True
        if relationship in ("code", "id"):
            column, source = (attrs["from_col"], attrs["to_col"]) if forward else (attrs["to_col"], attrs["from_col"])
            search.add_column(source)
            self.add_search_filter(column, search, op, table=self.table)
        elif relationship in ("search_type", "search_code", "search_id"):
            if relationship == "search_type":
                relationship = schema.resolve_search_type_relationship(attrs, search_type, related_type)
            has_code = relationship == "search_code"
            parent_col, child_col = ("code", "search_code") if has_code else ("id", "search_id")
            can_join = self._same_database(search.get_db_resource())
            if can_join and use_multidb is not None:
                can_join = use_multidb
            if can_join:
                self.add_op("begin")
                if forward:
                    self.add_filter("search_type", search.get_search_type())
                    search.add_column(parent_col, distinct=True)
                    self.add_search_filter(child_col, search, op=op)
                else:
                    search.add_filter("search_type", self.get_search_type())
                    search.add_column(child_col, distinct=True)
                    self.add_search_filter(parent_col, search, op=op)
                self.add_op("and")
            elif forward:
                values = search.get_sobject_codes() if has_code else search.get_sobject_ids()
                if delay_null and not values:
                    return False
                self.add_op("begin")
                self.add_filter("search_type", search.get_search_type())
                self.add_filters(child_col, values)
                self.add_op("and")
            else:
                search.add_column(child_col, distinct=True)
                search.add_filter("search_type", self.get_search_type())
                search.retired_filter = not search.show_retired and "s_status" in search.columns
                sql, parameters = search._statement(default_order=False, apply_retired=False)
                # Execute the source search on its resource, not a same-named local table.
                from pyasm.search.sql import Sql
                sql = Sql._bound_query(sql, parameters, search._placeholder())
                with self.store.connection(search.get_db_resource()) as db:
                    rows = db.execute(sql, parameters).fetchall()
                values = [next(iter(row.values())) if isinstance(row, dict) else row[0] for row in rows]
                values = [value for value in values if value]
                if delay_null and not values:
                    return False
                if not rows:
                    self.add_filter(parent_col, "NULL", quoted=False)
                else:
                    self.add_filters(parent_col, values, op=op)
        elif relationship == "instance":
            if not self._same_database(search.get_db_resource()):
                raise UnsupportedContract("Cross-resource instance relationships are not migrated")
            related_table, column, source = self._add_instance_relationship(schema, attrs, search.get_search_type(), path)
            values = search._get_sobject_values(source)
            self.add_filters(column, values, table=related_table, op=op)
        else:
            raise UnsupportedContract("Relationship is not migrated: " + str(relationship))
        return True

    def add_op(self, op, idx=None):
        if op not in ("begin", "and", "or"):
            raise ValueError("Expected begin, and or or")
        if idx is None:
            self.filters.append(op)
        else:
            self.filters.insert(idx, op)

    def add_where(self, value):
        if value in ("begin", "and", "or"):
            self.add_op(value)
        elif value:
            from tactic.command.python_cmd import check_script_execution
            check_script_execution(require_transaction=False)
            self.filters.append(value)
            self.raw_where = True

    @staticmethod
    def is_expr(value):
        return re.search(r"^(@|\$\w|{@|{\$\w)", str(value))

    def add_regex_filter(self, name, regex, op="EQI"):
        expression, value = self.db_resource.get_database_impl().get_bound_regex_filter(self._column(name), regex, op)
        self.filters.append(expression)
        self.parameters.append(value)

    def add_op_filters(self, filters):
        if isinstance(filters, str):
            filters = json.loads(filters.replace("&gt;", ">").replace("&lt;", "<"))
        for item in filters:
            if not item:
                continue
            if isinstance(item, str) or len(item) == 1:
                value = item if isinstance(item, str) else item[0]
                if value not in ('begin', 'and', 'or'):
                    raise UnsupportedContract('Raw SQL API filters are not supported')
                self.add_where(value)
                continue
            if not isinstance(item, (list, tuple)) or len(item) not in (2, 3, 4):
                raise ValueError("Expected a two, three or four argument filter")
            name = item[0]
            if len(item) == 2:
                value = item[1]
                if name.startswith("@"):
                    if name == "@ORDER_BY":
                        self.add_order_by(value)
                    elif name == "@LIMIT":
                        self.set_limit(value)
                    elif name == "@OFFSET":
                        self.set_offset(value)
                    elif name == "@UNIQUE":
                        self.add_column(value, distinct=True)
                elif isinstance(value, str):
                    if self.is_expr(value):
                        value = Search.eval(value, single=True)
                    self.add_filter(name, value)
                elif isinstance(value, (int, float, bool)):
                    self.add_filter(name, value)
                else:
                    self.add_filters(name, value)
            elif len(item) == 4:
                if item[1] in ("in between", "between"):
                    self.add_date_range_filter(name, item[2], item[3])
            else:
                _, op, value = item
                if name is None or op is None:
                    continue
                if op in ("is empty", "is not empty"):
                    self.add_filter(name, "NULL", op="is" if op == "is empty" else "is not", quoted=False)
                    continue
                if value in (None, ""):
                    continue
                op = op.replace("lte", "<=").replace("gte", ">=").replace("lt", "<").replace("gt", ">")
                if self.is_expr(value):
                    value = Search.eval(value, single=True)
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    value = Search.eval(value, single=True)
                if op == "is not":
                    self.add_op("begin")
                    self.add_filter(name, value, "!=")
                    self.add_filter(name, None)
                    self.add_op("or")
                elif op == "contains":
                    self.add_regex_filter(name, value)
                elif op == "does not contain":
                    self.add_op("begin")
                    self.add_regex_filter(name, value, "NEQI")
                    self.add_filter(name, None)
                    self.add_op("or")
                elif op in ("starts with", "ends with", "does not start with", "does not end with"):
                    value = str(value) + "%" if "start" in op else "%" + str(value)
                    self.add_filter(name, value, "not like" if op.startswith("does not") else "like")
                elif op in ("in", "not in"):
                    values = value.split("|") if isinstance(value, str) else value
                    self.add_filters(name, [value for value in values if value], op=op)
                elif op in ("EQ", "NEQ", "EQI", "NEQI"):
                    self.add_regex_filter(name, value, op)
                elif op == "is on":
                    self.add_day_filter(name, value)
                else:
                    op = {"is after": ">=", "is before": "<=", "is": "="}.get(op, op)
                    if value == "NULL":
                        self.add_filter(name, value, "is", quoted=False)
                    else:
                        self.add_filter(name, value, op, quoted=not isinstance(value, (int, float)))

    def add_date_range_filter(self, name, start_date, end_date, table=""):
        if not start_date and not end_date:
            self.set_null_filter()
            return
        if start_date and end_date:
            self.add_op("begin")
        for value, op in ((start_date, ">="), (end_date, "<")):
            if not value:
                continue
            value = parser.parse(value) if isinstance(value, str) else value
            value = datetime(value.year, value.month, value.day)
            if op == "<":
                value += timedelta(days=1)
            self.add_filter(name, value, op, table=table)
        if start_date and end_date:
            self.add_op("and")

    def add_day_filter(self, name, value):
        try:
            day = datetime.strptime(str(value).split(" ", 1)[0], "%Y-%m-%d")
        except ValueError as exc:
            raise UnsupportedContract("Day filters require a YYYY-MM-DD date") from exc
        self.add_filter(name, day.strftime("%Y-%m-%d"), ">=")
        self.add_filter(name, (day + timedelta(days=1)).strftime("%Y-%m-%d"), "<")

    def add_order_by(self, value, direction="", join="LEFT OUTER"):
        if "," in value:
            for expression in value.split(","):
                self.add_order_by(expression, direction, join)
            return
        words = value.split()
        if len(words) not in (1, 2):
            raise UnsupportedContract("Unsupported order expression")
        column = words[0]
        direction = words[1] if len(words) == 2 else direction
        if direction.lower() not in ("", "asc", "desc"):
            raise UnsupportedContract("Unsupported sort direction")
        if column in self.order_columns:
            return
        parts = [part for part in column.split(".") if part]
        if "connect" in parts:
            return
        # Original Search ignores absent sort columns on the main search type.
        if len(parts) == 1 and not self.column_exists(column):
            return False
        table = self.table
        previous_type = self.get_base_search_type()
        for next_type in parts[:-1]:
            path = None
            if ":" in next_type:
                path, next_type = next_type.split(':', 1)
            if "/" not in next_type:
                next_type = SearchType.get(previous_type).get_value("namespace") + "/" + next_type
            if next_type != previous_type:
                from pyasm.biz.project import Project
                resource = Project.get_db_resource_by_search_type(build_search_type(next_type, self.project_code))
                if not self._same_database(resource):
                    return False
                # Original parses the path but forgets to pass it to add_join.
                self.add_join(next_type, previous_type, path=path, join=join)
            table = SearchType.get(next_type).get_table()
            previous_type = next_type
        order = self._column(parts[-1], table)
        if direction:
            order += " " + direction.upper()
        self.order_columns.add(column)
        if order not in self.order_bys:
            self.order_bys.append(order)
        return True

    def add_column(self, column, distinct=False, table=None, as_column=None, quoted=True):
        table = table or self.table
        if quoted and self.select.quoted_mode != 'none' and column != "*":
            self._column(column, table)
        elif table not in self.join_columns:
            raise UnsupportedContract("Table has not been joined")
        if as_column:
            identifier(as_column)
        self.select.add_column(column, distinct, table, as_column, quoted)
        if distinct:
            self.distinct = True

    def add_group_by(self, column):
        self.select.add_group_by(column)

    def add_group_aggregate_filter(self, group_cols, column='id', aggregate='max'):
        """Native correlated aggregate: select the maximum/minimum row per group."""
        if not group_cols:
            return
        group_cols = [group_cols] if isinstance(group_cols, str) else group_cols
        if not isinstance(aggregate, str) or aggregate.lower() not in ('max', 'min', 'sum', 'avg', 'count'):
            raise ValueError('Invalid aggregate function')
        outer = self._column(column)
        conditions = []
        for name in group_cols:
            conditions.append(f'xxx.{identifier(name)} = {self._column(name)}')
        self.filters.append(f'{outer} = (SELECT {aggregate.upper()}({identifier(column)}) '
                            f'FROM {identifier(self.table)} AS xxx WHERE {" AND ".join(conditions)})')

    def add_having(self, filter):
        self.select.add_having(filter)

    def set_limit(self, limit):
        if type(limit) is not int or limit < 0:
            raise ValueError("Limit must be a non-negative integer")
        self.limit = limit
        self.select.set_limit(limit)

    def add_limit(self, limit):
        '''deprecated: use set_limit()'''
        self.set_limit(limit)

    def set_offset(self, offset):
        if type(offset) is not int or offset < 0:
            raise ValueError("Offset must be a non-negative integer")
        self.offset = offset
        self.select.set_offset(offset)

    def set_show_retired(self, value=True):
        self.show_retired = value

    def set_null_filter(self):
        self.null_filter = True

    def _where(self, columns=None, apply_retired=True):
        if self.select.filters or self.select._statement or self.select.tables != [self.table]:
            raise UnsupportedContract('Replacing Search tables or loading raw Select filters is not migrated')
        items = self.filters.copy()
        if self.null_filter:
            items.append('1 = 0')
        columns = self.columns if columns is None else columns
        if apply_retired:
            self.retired_filter = "s_status" in columns and not self.show_retired
        if self.retired_filter:
            column = self._column("s_status")
            items.append(f"({column} IS NULL OR {column} != 'retired')")
        if not items:
            return ""
        # Select.process_wheres uses postfix group operators, not infix SQL tokens.
        if items[0] != "begin":
            items.insert(0, "begin")
        if items[-1] not in ("and", "or"):
            items.append("and")
        if items.count("begin") > items.count("and") + items.count("or"):
            items.append("and")
        groups = [[]]
        for item in items:
            if item == "begin":
                groups.append([])
            elif item in ("and", "or"):
                group = groups.pop() if len(groups) > 1 else groups[0]
                expression = (" " + item.upper() + " ").join(group)
                if len(group) > 1:
                    expression = "(" + expression + ")"
                if len(groups) == 1 and group is groups[0]:
                    groups[0] = [expression] if expression else []
                elif expression:
                    groups[-1].append(expression)
            elif item:
                groups[-1].append(item)
        while len(groups) > 1:
            expression = " AND ".join(groups.pop())
            if expression:
                groups[-1].append(expression)
        expression = " AND ".join(groups[0])
        return " WHERE " + expression if expression else ""

    def _apply_security_filter(self):
        from pyasm.common import Environment
        if not self.custom_filter:
            klass = Common.resolve_class(self.search_type_obj.get_class())
            klass.alter_search(self)
            self.custom_filter = True
        if not self.security_filter:
            security = Environment.get_security()
            if security is not None:
                security.alter_search(self)

    def get_count(self, no_exception=False):
        if self.null_filter:
            return 0
        self._apply_security_filter()
        errors = (sqlite3.Error,)
        if self.db_resource.get_vendor() == 'PostgreSQL':
            errors = self.get_sql()._errors
        try:
            with self.store.connection(self.db_resource) as db:
                sql, parameters = self._statement(default_order=False, count=True)
                from pyasm.search.sql import Sql
                sql = Sql._bound_query(sql, parameters, self._placeholder())
                row = db.execute(sql, parameters).fetchone()
                return next(iter(row.values())) if isinstance(row, dict) else row[0]
        except errors:
            if no_exception:
                return -1
            raise

    def get_group_counts(self, columns):
        """Count native visible rows per physical column tuple, ignoring paging/order."""
        columns = list(dict.fromkeys(columns))
        if not columns:
            raise ValueError('Grouped counts require columns')
        expressions = [self._column(column) for column in columns]
        if self.null_filter:
            return []
        sql, parameters = self._statement(default_order=False, count=True)
        prefix = 'SELECT COUNT(*)'
        selected = [expression + ' AS ' + identifier('group_%d' % index)
                    for index, expression in enumerate(expressions)]
        sql = 'SELECT ' + ','.join([*selected, 'COUNT(*) AS "__count__"']) + sql[len(prefix):]
        sql += ' GROUP BY ' + ','.join(expressions)
        from pyasm.search.sql import Sql
        sql = Sql._bound_query(sql, parameters, self._placeholder())
        with self.store.connection(self.db_resource) as db:
            rows = db.execute(sql, parameters).fetchall()
        return [tuple(row.values()) if isinstance(row, dict) else tuple(row) for row in rows]

    def _statement(self, default_order=True, apply_retired=True, count=False):
        self._apply_security_filter()
        if self.select.db_resource and not self._same_database(self.select.db_resource):
            raise UnsupportedContract('Execute a Search Select on its own database resource')
        if (self.raw_where or self.select.quoted_mode == 'none' or self.select.havings
                or self.select.order_by_columns or None in self.select.column_tables
                or any(group not in self.columns for group in self.select.group_bys)):
            # Native SQL expressions keep the existing trusted-script boundary.
            from tactic.command.python_cmd import check_script_execution
            check_script_execution(require_transaction=False)
        selections = []
        for name, table, alias in zip(self.select.columns, self.select.column_tables, self.select.as_columns):
            if table is None or self.select.quoted_mode == 'none':
                expression = name
            else:
                expression = identifier(table) + ".*" if name == "*" else self._column(name, table)
            if alias:
                expression += " AS " + identifier(alias)
            selections.append(expression)
        selected = 'COUNT(*)' if count else ",".join(selections) or identifier(self.table) + ".*"
        selected_names = self.select.get_columns()
        where_columns = selected_names or self.columns
        if count or not default_order or "*" in where_columns:
            where_columns = self.columns
        # Original object reads apply retirement only when s_status was selected.
        distinct = not count and (self.distinct or self.select.distinct)
        sql = f"SELECT {'DISTINCT ' if distinct else ''}{selected} FROM {identifier(self.table)}"
        where = self._where(where_columns, apply_retired=apply_retired)
        queue_parameters = []
        if self.get_base_search_type() == 'sthpw/queue' or self.database == 'sthpw' and 'queue' in self.join_sources:
            from pyasm.common import Environment
            security = Environment.get_security()
            if security is not None and not security.is_admin():
                from tactic.command.checkin_queue_cmd import JOB_COMMAND
                # Keep ownership outside caller-supplied OR groups, including joined reads.
                command, login = self._column('command', 'queue'), self._column('login', 'queue')
                guard = f'({command} IS NULL OR {command} != {self._placeholder()} OR {login} = {self._placeholder()})'
                where = ' WHERE (' + where[7:] + ') AND ' + guard if where else ' WHERE ' + guard
                queue_parameters = [JOB_COMMAND, Environment.get_user_name()]
        sql += "".join(" " + join for join in self.joins) + where
        order_bys = self.select.order_bys.copy()
        if default_order and self.order_by:
            if self.get_base_search_type() in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/snapshot'):
                if 'timestamp' not in self.order_columns:
                    order_bys.append(self._column('timestamp') + ' DESC')
            elif "code" in where_columns and self._column("code") not in order_bys:
                order_bys.append(self._column("code"))
        if self.select.group_bys and not count:
            # Native Select includes sorting columns in GROUP BY.
            groups = self.select.group_bys + [order.rsplit(' ', 1)[0]
                if order.upper().endswith((' ASC', ' DESC')) else order for order in order_bys]
            sql += ' GROUP BY ' + ','.join(identifier(group) if group in self.columns else group for group in dict.fromkeys(groups))
        if self.select.havings and not count:
            sql += ' HAVING ' + ' AND '.join(self.select.havings)
        if order_bys and not distinct and not count:
            # Keep object ordering identical on SQLite and PostgreSQL, including NULLs.
            sql += " ORDER BY " + ",".join(order + (' NULLS LAST' if order.upper().endswith(' DESC') else ' NULLS FIRST')
                                         for order in order_bys)
        parameters = self.parameters.copy() + queue_parameters
        # PostgresImpl.get_page, inherited by SqliteImpl, ignores offset without limit.
        if self.select.limit is not None and not count:
            sql += ' LIMIT %s OFFSET %s' % (self._placeholder(), self._placeholder())
            parameters.extend((self.select.limit, self.select.offset or 0))
        return sql, parameters

    @classmethod
    def eval(cls, expression, sobjects=None, mode=None, single=False, list=False, vars={}, dictionary=False, env_sobjects={}, show_retired=False, state={}, extra_filters={}, search=None):
        from pyasm.biz import ExpressionParser
        parser = ExpressionParser()
        return parser.eval(expression, sobjects=sobjects, mode=mode, single=single, list=list, dictionary=dictionary, vars=vars, env_sobjects=env_sobjects, show_retired=show_retired, state=state, extra_filters=extra_filters, search=search)

    def get_statement(self):
        return self.select.get_statement()

    def get_sobjects(self, redo=False, statement=None):
        if statement:
            raise UnsupportedContract("Raw SQL search statements are not supported")
        if self.null_filter:
            return []
        if self.is_search_done and not redo:
            return self.sobjects
        sql, parameters = self._statement()
        from pyasm.search.sql import Sql
        sql = Sql._bound_query(sql, parameters, self._placeholder())
        with self.store.connection(self.db_resource) as db:
            rows = db.execute(sql, parameters).fetchall()
        self.sobjects = []
        if rows:
            columns = list(rows[0].keys())
            fast_data = {
                'full_search_type': self.search_type, 'search_type_obj': self.search_type_obj,
                'database': self.database, 'db_resource': self.get_db_resource(),
                'datetime_cols': [name for name, info in self.columns.items()
                                  if info['data_type'] in ('timestamp', 'time', 'date', 'datetime2')],
                'time_cols': {name for name, info in self.columns.items() if info['data_type'] == 'time'},
                'boolean_cols': [name for name, info in self.columns.items() if info['data_type'] == 'boolean'],
                'skipped_cols': [], 'data': [dict(row) for row in rows],
            }
            class_path = self.search_type_obj.get_class()
            for index, row in enumerate(rows):
                fast_data['count'] = index
                self.sobjects.append(SearchType.fast_create_from_class_path(
                    class_path, self.search_type_obj, columns, tuple(row), fast_data=fast_data))
        self.is_search_done = True
        return self.sobjects

    def get_sobject(self, redo=False):
        self.set_limit(1)
        rows = self.get_sobjects(redo=redo)
        return rows[0] if rows else None

    @staticmethod
    def get_by_code(search_type, code, show_retired=True):
        if not search_type or not code:
            return None
        if not isinstance(code, list):
            key = SearchKey.build_search_key(search_type, code, column='code', project_code=_context.get().project)
            cached = SObject._get_cached_for_read(key, search_type=search_type)
            if cached is not None:
                return None if cached == '__NONE__' else cached
        search = Search(search_type)
        search.set_show_retired(show_retired)
        if isinstance(code, list):
            search.add_filters("code", code)
            return search.get_sobjects()
        search.add_filter("code", code)
        key = SearchKey.build_search_key(search_type, code, column='code', project_code=search.project_code)
        return SObject.get_by_search(search, key)

    @staticmethod
    def get_by_id(search_type, search_id, show_retired=True):
        if not search_type or search_id in (None, ""):
            return None
        if not isinstance(search_id, list):
            key = SearchKey.build_search_key(search_type, search_id, column='id', project_code=_context.get().project)
            cached = SObject._get_cached_for_read(key, search_type=search_type)
            if cached is not None:
                return None if cached == '__NONE__' else cached
        search = Search(search_type)
        search.set_show_retired(show_retired)
        if isinstance(search_id, list):
            search.add_filters(search.get_id_col(), search_id)
            return search.get_sobjects()
        search.add_id_filter(search_id)
        key = SearchKey.build_search_key(search_type, search_id, column='id', project_code=search.project_code)
        return SObject.get_by_search(search, key)

    @staticmethod
    def get_by_search_key(search_key):
        if not search_key:
            return None
        if not isinstance(search_key, str):
            raise ValueError("A string search key is required")
        while "&amp;" in search_key:
            search_key = search_key.replace("&amp;", "&")
        if "|" in search_key and not re.search(r'[?&](?:code|id)=', search_key.split('|', 1)[0]):
            search_type, identity = search_key.split("|", 1)
            return Search.get_by_id(search_type, identity)
        base, parts = SearchKey._get_data(search_key)
        if not base.startswith("sthpw/") and not parts.get("project"):
            raise ValueError("Project-scoped search keys must include their project")
        search_type = parts.get("search_type") or base
        column = "code" if parts.get("code") else "id"
        identity = parts.get(column)
        if identity is None or str(identity) == "-1":
            raise UnsupportedContract("New-object or incomplete search keys are not migrated")
        # Original SearchKey uses the caller's complete key for identity lookup.
        # Rebuilding it via get_by_code can substitute the physical database for
        # project and miss an object already staged in this request.
        search = Search(search_type)
        if column == 'code':
            search.add_filter('code', identity)
        else:
            search.add_id_filter(identity)
        search.set_show_retired(True)
        return SObject.get_by_search(search, search_key)

    @staticmethod
    def get_by_search_keys(search_keys, keep_order=False):
        return SearchKey.get_by_search_keys(search_keys, keep_order=keep_order)

    def _get_sobject_values(self, column):
        from pyasm.search.sql import Sql
        self.add_column(column)
        self._apply_security_filter()
        source = self.copy()
        source.custom_filter = self.custom_filter
        # Append the actual base column even if an existing projection aliases its name.
        source.select.columns.append(column)
        source.select.column_tables.append(source.table)
        source.select.as_columns.append(None)
        sql, parameters = source._statement(default_order=False)
        self.retired_filter = source.retired_filter
        sql = Sql._bound_query(sql, parameters, source._placeholder())
        with self.store.connection(source.db_resource) as db:
            return [row[column] if isinstance(row, dict) else row[-1] for row in db.execute(sql, parameters)]

    def get_sobject_codes(self):
        return self._get_sobject_values("code")

    def get_sobject_ids(self):
        return self._get_sobject_values("id")

    @classmethod
    def get_sobject_dicts(cls, sobjects, columns=None):
        return [obj.get_sobject_dict(columns=columns, mode="fast") for obj in sobjects]

    @classmethod
    def get_related_by_sobjects(cls, sobjects, related_type, filters=[], path=None, show_retired=False):
        from pyasm.biz.schema import Schema
        if not sobjects or not sobjects[0]:
            return {}
        search_type = sobjects[0].get_base_search_type()
        schema = Schema.get(project_code=sobjects[0].get_project_code())
        search = Search(related_type)
        search.set_show_retired(show_retired)
        search.add_op_filters(filters)
        search.add_relationship_filters(sobjects, path=path)
        related_sobjects = search.get_sobjects()
        related_type = SearchKey.extract_base_search_type(related_type)
        attrs = search._get_relationship_attrs(schema, search_type, path=path)
        if related_type == search_type and not attrs:
            return {}
        relationship = attrs.get("relationship")
        if relationship == 'search_type':
            attrs = schema.resolve_relationship_attrs(attrs, related_type, search_type)
            relationship = attrs['relationship']
        forward = related_type == attrs.get("from")
        if relationship == 'general':
            from pyasm.biz.sobject_connection import SObjectConnection
            source, target = ('dst', 'src') if forward else ('src', 'dst')
            owners = {(obj.get_search_type(), str(obj.get_id())): obj.get_search_key() for obj in sobjects}
            related = {(obj.get_search_type(), str(obj.get_id())): obj for obj in related_sobjects}
            result = {obj.get_search_key(): [] for obj in sobjects}
            for link in SObjectConnection.get_connections(sobjects, direction=target):
                owner = owners.get((link.get_value(source + '_search_type'), str(link.get_value(source + '_search_id'))))
                obj = related.get((link.get_value(target + '_search_type'), str(link.get_value(target + '_search_id'))))
                if owner and obj and obj not in result[owner]:
                    result[owner].append(obj)
            return result
        prefix = attrs.get("prefix", "")
        prefix = prefix + "_" if prefix else ""
        grouped = {}
        for obj in related_sobjects:
            if relationship == "search_type":
                relationship = schema.resolve_search_type_relationship(attrs, search_type, related_type)
            if relationship in ("code", "id"):
                key = obj.get_value(attrs.get("from_col") if forward else attrs.get("to_col"))
            elif relationship == "instance":
                key = obj.get_value("_related_code")
            elif relationship in ("search_code", "search_id"):
                column = "code" if relationship == "search_code" else "id"
                search_type = obj.get_value(prefix + "search_type") if forward else obj.get_search_type()
                value = obj.get_value(prefix + "search_" + column) if forward else obj.get_value(column)
                key = f"{search_type}&{column}={value}"
            else:
                raise UnsupportedContract("Relationship is not migrated: " + str(relationship))
            grouped.setdefault(key, []).append(obj)
        result = {}
        for obj in sobjects:
            if relationship in ("code", "id", "instance"):
                if relationship == 'instance' and related_type == search_type:
                    source_path = 'parent' if path == 'child' else 'child'
                    edge = schema.get_relationship_attrs(attrs['instance_type'], search_type, path=source_path)
                    key = obj.get_value(edge['to_col'])
                else:
                    key = obj.get_value(attrs.get("to_col") if forward else attrs.get("from_col"))
            elif relationship in ("search_type", "search_code", "search_id"):
                if relationship == "search_type":
                    relationship = schema.resolve_search_type_relationship(attrs, search_type, related_type)
                column = "code" if relationship == "search_code" else "id"
                key_type = obj.get_search_type() if forward else obj.get_value(prefix + "search_type")
                value = obj.get_value(column) if forward else obj.get_value(prefix + "search_" + column)
                key = f"{key_type}&{column}={value}"
            else:
                raise UnsupportedContract("Relationship is not migrated: " + str(relationship))
            result[obj.get_search_key()] = grouped.get(key, [])
        return result


class SObjectFactory(Base):
    '''DEPRECATED: use SearchType'''
    def create(search_type, columns=None, result=None):
        '''creation function for all sobject'''
        # super complicated dynamically importing a module
        # and instantiating the appropriate class
        class_path = None
        if search_type == "sthpw/search_object":
            class_path = "pyasm.search.SearchType"
        else:
            search_type_obj = SearchType.get(search_type)
            class_path = search_type_obj.get_class()

        sobject = Common.create_from_class_path(class_path, \
            [search_type,columns,result])
        return sobject
    create = staticmethod(create)
