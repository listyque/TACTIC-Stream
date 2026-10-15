"""System journal persistence against the real legacy runtime, on private DBs."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile

import test_read_parity as read_tests
from pyasm.common import Environment
from pyasm.security import Security
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SearchType, request_context
from pyasm.search.storage import Store
from pyasm.search.transaction import Transaction
from tools.capture_legacy import persistence_schema
from tools.journal_write_probe import run_journal_write_case


def journal_cases():
    cases = []
    def add(xml='<transaction/>', **kwargs):
        cases.append({'method': 'journal_write_contract', 'name': 'write_' + str(len(cases)), 'xml': xml, **kwargs})
    add()
    for flags in [{}, {'state': 'start'}, {'keywords': 'one two'}, {'update_log': True},
                  {'id_override': True}, {'change_code': True}, {'force_insert': True}, {'redo': True}, {'fail': True}]:
        add(**flags)
    for identity in ['search_code="A"', 'search_id="1"', 'search_code="missing"']:
        for action in ['insert', 'update', 'delete']:
            add('<transaction><sobject search_type="contract/entity?project=one" %s action="%s"/></transaction>' % (identity, action))
    for flags in [{}, {'index_again': True}, {'redo': True}, {'fail': True}]:
        add('<transaction><sobject search_type="contract/entity?project=one" search_code="A" action="update"/><sobject search_type="contract/entity?project=one" search_code="A" action="insert"/></transaction>', **flags)
    add('<transaction><sobject search_type="contract/entity?project=one" search_code="A" action="delete"/><sobject search_type="contract/entity?project=one" search_code="A" action="insert"/></transaction>')
    add('<transaction><sobject search_type="contract/entity?project=one" search_code="A" action="update"/><sobject search_type="sthpw/project" search_code="one" action="update"/></transaction>')
    add('<transaction><sobject search_type="sthpw/transaction_log" search_code="missing" action="insert"/></transaction>')
    for length in [10239, 10240, 10241, 15000]:
        prefix = '<transaction><sobject search_type="contract/entity?project=one" search_code="A" action="update"><column name="name" to="'
        suffix = '"/></sobject></transaction>'
        add(prefix + 'x' * (length - len(prefix) - len(suffix)) + suffix)
    add(redo=True, operation='delete_redo')
    for operation in ['delete_redo', 'create']:
        add(redo=True, cached_redo=True, operation=operation, bugfix='deleted_cache')
    return cases


class JournalWriteParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = journal_cases()

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='tactic-stream-journal-write-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', case.get('project', 'one'))):
                return run_journal_write_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('fail'):
            self.assertEqual(original['error'], 'ValueError')
            self.assertEqual(original['message'], 'rollback after journal write')
            self.assertEqual(result['transaction_log'], [])
            self.assertEqual(result['sobject_log'], [])
            self.assertTrue(original['rolled_back_cached_log'])
            original['rolled_back_cached_log'] = False
        elif case.get('keywords'):
            self.assertEqual(original['error'], 'SqlException')
            self.assertIn('no column named keywords', original['message'])
            expected = dict(original)
            expected.update(error='UnsupportedContract', message='TransactionLog keywords require a schema column not present in the original seed')
            self.assertEqual(result, expected)
            return
        else:
            self.assertNotIn('error', original)
            self.assertNotIn('error', result)
        if case.get('bugfix') == 'deleted_cache':
            self.assertTrue(original['result']['cached_redo'])
            original['result']['cached_redo'] = False
        super().assert_case_result(case, result, original)

    def test_persistence_schema_is_original_atomic_and_repeatable(self):
        metadata = json.loads((read_tests.ROOT / 'src/tactic_stream/compatibility/persistence_upgrade.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata, persistence_schema(read_tests.LEGACY))
        with tempfile.TemporaryDirectory(prefix='tactic-stream-index-upgrade-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE sobject_list')
                db.execute("DELETE FROM search_object WHERE search_type='sthpw/sobject_list'")
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with store.connection(write=True) as db:
                db.execute('DROP TABLE sobject_list')
                db.execute("UPDATE search_object SET class_name='CustomIndex' WHERE search_type='sthpw/sobject_list'")
            before = store.database_path('sthpw').read_bytes()
            with self.assertRaises(ValueError):
                store.upgrade()
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)

    def test_journal_fields_and_domain_writes_join_the_transaction(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            tx = Transaction.get(create=True)
            security = Security()
            Environment.set_security(security)
            security._is_logged_in = 1
            security._login = Search.get_by_code('sthpw/login', 'admin')
            obj = Search.get_by_code('contract/entity', 'A')
            tx.set_sync(False)
            original = obj.get_value('name')
            obj.set_value('name', 'Transactional edit')
            obj.commit()
            obj.delete()
            tx.commit_log()
            log = SearchType.create('sthpw/transaction_log')
            log.set_user()
            log.set_value('description', 'pending')
            log.commit(triggers=False)
            datetime.fromisoformat(log.get_value('timestamp'))
            self.assertTrue(log.get_code().startswith('TRANSACTION'))
            tx.rollback()
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM transaction_log').fetchone()[0], 0)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.assertEqual(Search.get_by_code('contract/entity', 'A').get_value('name'), original)

    def test_unsupported_journal_payloads_refuse_before_redo_changes(self):
        from pyasm.search.transaction_log import TransactionLog
        from pyasm.search.sql import DbContainer
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = Security()
            Environment.set_security(security)
            security._is_logged_in = 1
            security._login = Search.get_by_code('sthpw/login', 'admin')
            tx = Transaction.get(create=True)
            sql = DbContainer.get('sthpw')
            sql.do_update("INSERT INTO transaction_log (code,login,type) VALUES ('REDO','admin','redo')")
            before = sql.get_value('SELECT count(*) FROM transaction_log')
            for xml, kwargs in [('<transaction><file/></transaction>', {}),
                                ('<transaction><sobject site="other"/></transaction>', {}),
                                ('<transaction/>', {'keywords': 'test'})]:
                with self.subTest(xml=xml, kwargs=kwargs), self.assertRaises(UnsupportedContract):
                    TransactionLog.create('Command', xml, 'Description', **kwargs)
                self.assertEqual(sql.get_value('SELECT count(*) FROM transaction_log'), before)
                self.assertEqual(sql.get_value("SELECT count(*) FROM transaction_log WHERE code='REDO'"), 1)
            tx.rollback()
