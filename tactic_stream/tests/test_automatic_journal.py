"""Automatic journal and timestamp contracts on private original/native DBs."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import test_read_parity as read_tests
from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.search import DbContainer, Search, SearchType, Transaction
from pyasm.security import Security
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.automatic_journal_probe import run_automatic_journal_case
from tools.capture_legacy import preference_schema


def automatic_cases():
    result = []
    for flags in [{}, {'empty': True}, {'description': 'Описание', 'title': 'Title'},
                  {'nested': True}, {'record': False}, {'undoable': False, 'bugfix': 'undoable'},
                  {'update': True}, {'update': True, 'existing_timestamp': True, 'bugfix': 'changed_by'},
                  {'fail': 'log'}, {'fail': 'timestamp'}, {'project': 'one', 'sync': False}]:
        result.append({'method': 'automatic_journal_contract', 'name': 'auto_' + str(len(result)), 'project': 'admin', **flags})
    for timezone in ['UTC', 'Europe/Moscow', 'Asia/Tokyo', 'local', '', 'not/a/timezone']:
        result.append(dict(method='automatic_journal_contract', name='zone_' + timezone, project='one', direct=True, timezone=timezone))
    result.append(dict(method='automatic_journal_contract', name='existing_direct', project='one', direct=True, existing_direct=True, bugfix='changed_by_direct'))
    result.append(dict(method='preference_contract', name='preferences', project='one'))
    return result


class AutomaticJournalParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = automatic_cases()

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='tactic-stream-auto-journal-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', case.get('project', 'admin'))):
                return run_automatic_journal_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('timezone') == 'not/a/timezone':
            # Source silently uses the machine timezone for an unknown name.
            self.assertNotIn('error', original)
            self.assertEqual(len(original['change_timestamp']), 1)
            self.assertEqual(result['error'], 'ValueError')
            self.assertIn('Unknown time zone', result['message'])
            self.assertEqual(result['change_timestamp'], [])
            self.assertEqual(result['counter'], 0)
            return
        if case.get('fail'):
            if case['fail'] == 'log':
                self.assertEqual(original['error'], 'SqlException')
                self.assertEqual(original['stack'], 1)
            else:
                self.assertNotIn('error', original)
                self.assertEqual(len(original['transaction_log']), 1)
            self.assertEqual(len(original['sobject_log']), 1)
            self.assertEqual(result['error'], 'SqlException')
            self.assertIn('blocked write', result['message'])
            for table in ['transaction_log', 'sobject_log', 'sobject_list', 'change_timestamp']:
                self.assertEqual(result[table], [])
            self.assertEqual(result['counter'], 0)
            self.assertEqual(result['stack'], 0)
            self.assertTrue(result['admin'])
            return
        self.assertNotIn('error', original)
        self.assertNotIn('error', result)
        if case.get('bugfix') == 'undoable':
            self.assertEqual(len(original['transaction_log']), 1)
            self.assertEqual(len(original['change_timestamp']), 1)
            self.assertEqual(result['transaction_log'], [])
            self.assertEqual(result['change_timestamp'], [])
            original['transaction_log'] = []
            original['change_timestamp'] = []
        if case.get('bugfix') == 'changed_by':
            before = json.loads(original['change_timestamp'][0]['changed_by'])
            self.assertEqual(before, {'old': 'other', 'action': 'other'})
            before['action'] = 'admin'
            original['change_timestamp'][0]['changed_by'] = json.dumps(before)
        if case.get('bugfix') == 'changed_by_direct':
            self.assertEqual(original['change_timestamp'][0]['changed_by'], '{"old":"other"}')
            original['change_timestamp'][0]['changed_by'] = json.dumps({'old': 'other', 'name': 'admin'})
        super().assert_case_result(case, result, original)
        if case['method'] == 'preference_contract':
            self.assertEqual(result['values'], ['UTC', 'Asia/Tokyo', 'Europe/Moscow', '', 'UTC|local'])
            self.assertEqual(result['cache'], [True, 'UTC', 'local'])
        elif case.get('direct'):
            self.assertEqual(len(result['change_timestamp']), 1)
            fields = json.loads(result['change_timestamp'][0]['changed_on'])
            if case.get('timezone') in ['UTC', 'Europe/Moscow', 'Asia/Tokyo']:
                hour = {'UTC': '12', 'Europe/Moscow': '15', 'Asia/Tokyo': '21'}[case['timezone']]
                self.assertEqual(fields['name'], '2026-01-15 ' + hour + ':00:00')
        elif case.get('empty') or case.get('record') is False or case.get('undoable') is False:
            self.assertEqual(result['transaction_log'], [])
            self.assertEqual(result['change_timestamp'], [])
        else:
            self.assertEqual(len(result['transaction_log']), 1)
            self.assertTrue(result['change_timestamp'])

    def security(self):
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        return security

    def test_preference_module_and_schema_are_original_atomic_and_repeatable(self):
        new = read_tests.ROOT / 'src/pyasm/biz/preference.py'
        original = read_tests.LEGACY / 'src/pyasm/biz/preference.py'
        self.assertEqual(hashlib.sha256(new.read_bytes()).digest(), hashlib.sha256(original.read_bytes()).digest())
        metadata = json.loads((read_tests.ROOT / 'src/tactic_stream/compatibility/preference_upgrade.json').read_text(encoding='utf-8'))
        self.assertEqual({name: value for name, value in metadata.items() if name != 'indexes'},
                         preference_schema(read_tests.LEGACY))
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with store.connection(write=True) as db:
                for name in metadata['tables']:
                    db.execute('DROP TABLE "' + name + '"')
                    db.execute('DELETE FROM search_object WHERE search_type=?', ('sthpw/' + name,))
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with store.connection(write=True) as db:
                db.execute('DROP TABLE pref_list')
                db.execute("UPDATE search_object SET class_name='custom.Preference' WHERE search_type='sthpw/pref_setting'")
            before = store.database_path('sthpw').read_bytes()
            with self.assertRaises(ValueError):
                store.upgrade()
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)

    def test_invalid_append_and_unported_sync_and_other_database_roll_back(self):
        for operation in ['append', 'sync', 'database']:
            with self.subTest(operation=operation), request_context(RequestContext(self.store, 'admin', 'one')):
                self.security()
                class Writer(Command):
                    def execute(inner):
                        tx = inner.get_transaction()
                        if operation == 'append':
                            tx.set_transaction(SearchType.create('sthpw/transaction_log'))
                        if operation == 'database':
                            Search('contract/entity').get_sql().do_update("UPDATE entity SET name='pending' WHERE code='A'")
                        node = tx.create_log_node('sobject')
                        tx.xml.set_attribute(node, 'search_type', 'contract/entity?project=one')
                        tx.xml.set_attribute(node, 'search_code', 'A')
                        tx.xml.set_attribute(node, 'action', 'update')
                from pyasm.search import TransactionException
                with self.assertRaises(TransactionException if operation == 'append' else UnsupportedContract):
                    Command.execute_cmd(Writer())
                self.assertEqual(Transaction.get().counter, 0)
                self.assertEqual(Container.get_seq(Command.TOP_CMD_KEY), [])
                self.assertEqual(Search('sthpw/transaction_log').get_count(), 0)
                self.assertEqual(Search('sthpw/sobject_log').get_count(), 0)
                self.assertEqual(Search.get_by_code('contract/entity', 'A').get_value('name'), 'Первый')

    def test_generated_timestamp_and_code_and_callback_failure(self):
        for fail in [False, True]:
            with self.subTest(fail=fail), request_context(RequestContext(self.store, 'admin', 'admin')):
                self.security()
                class Writer(Command):
                    def execute(inner):
                        obj = SearchType.create('sthpw/sobject_log')
                        obj.set_user()
                        obj.set_value('search_type', 'contract/entity?project=one')
                        obj.set_value('search_code', 'A')
                        obj.set_value('search_id', 1)
                        obj.set_value('action', 'updated')
                        obj.commit()
                    def commit(inner):
                        if fail:
                            raise ValueError('failed commit hook')
                if fail:
                    with self.assertRaisesRegex(ValueError, 'failed commit hook'):
                        Command.execute_cmd(Writer())
                    self.assertEqual(Container.get_seq(Command.TOP_CMD_KEY), [])
                    self.assertEqual(Search('sthpw/sobject_log').get_count(), 0)
                    self.assertEqual(Search('sthpw/transaction_log').get_count(), 0)
                else:
                    Command.execute_cmd(Writer())
                    log = Search('sthpw/transaction_log').get_sobject()
                    datetime.fromisoformat(log.get_value('timestamp'))
                    change = Search('sthpw/change_timestamp').get_sobject()
                    self.assertRegex(change.get_code(), r'^CHANGE_TIMESTAMP_[0-9a-f-]{36}$')
                    datetime.fromisoformat(change.get_value('timestamp'))
            if not fail:
                with self.store.connection(write=True) as db:
                    for table in ['sobject_log', 'transaction_log', 'change_timestamp']:
                        db.execute('DELETE FROM ' + table)

    def test_commit_failure_and_unported_file_journal_still_roll_back_sql(self):
        for failure in ['constraint', 'file']:
            with self.subTest(failure=failure), request_context(RequestContext(self.store, 'admin', 'admin')):
                self.security()
                sql = DbContainer.get('sthpw')
                sql.do_update('PRAGMA foreign_keys=ON')
                sql.do_update('CREATE TEMP TABLE parent (id INTEGER PRIMARY KEY)')
                sql.do_update('CREATE TEMP TABLE child (parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)')
                class Writer(Command):
                    def execute(inner):
                        DbContainer.get('sthpw').do_update('INSERT INTO child VALUES (1)')
                        tx = inner.get_transaction()
                        node = tx.xml.create_element('file' if failure == 'file' else 'sobject', node=tx.xml.get_root_node())
                        if failure != 'file':
                            tx.xml.set_attribute(node, 'search_type', 'contract/entity?project=one')
                            tx.xml.set_attribute(node, 'search_code', 'A')
                            tx.xml.set_attribute(node, 'action', 'update')
                from pyasm.search.sql import SqlException
                with self.assertRaises(UnsupportedContract if failure == 'file' else SqlException):
                    Command.execute_cmd(Writer())
                self.assertFalse(sql.conn.in_transaction)
                self.assertEqual(sql.get_value('SELECT count(*) FROM child'), 0)
                self.assertEqual(Search('sthpw/transaction_log').get_count(), 0)
                self.assertEqual(Search('sthpw/sobject_log').get_count(), 0)
                self.assertEqual(Transaction.get().counter, 0)
                self.assertEqual(Container.get_seq(Command.TOP_CMD_KEY), [])
