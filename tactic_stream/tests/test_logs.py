"""Journal classes and XML/staging reads against the real original kernel."""
import ast
from contextlib import redirect_stdout
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest

import test_read_parity as read_tests
from pyasm.common.common import Common, Container
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SObject, request_context
from pyasm.security.authenticator import hash_password
from pyasm.search.sobject_log import SObjectLog, RetireLog
from pyasm.search.storage import Store
from pyasm.search.transaction import Transaction
from pyasm.search.transaction_log import TransactionLog
from pyasm.common.lxml_wrapper import XmlException
from tools.capture_legacy import journal_schema
from tools.log_probe import run_log_case


def log_fixture(store):
    xml = '<transaction><column>Тест &amp; значение</column></transaction>'
    rows = [
        (1, 'T_OLD', 'admin', 'one', 'undo', '2026-09-28 12:00:00', None),
        (2, 'T_REDO_OLD', 'admin', 'one', 'redo', '2026-10-01 12:00:00', None),
        (3, 'T_REDO_NEW', 'admin', 'one', 'redo', '2026-10-03 12:00:00', None),
        (4, 'T_UNDO_NEW', 'admin', 'one', 'undo', '2026-10-04 12:00:00', None),
        (5, 'T_OTHER', 'artist', 'one', 'undo', '2026-10-05 12:00:00', None),
        (6, 'T_TWO', 'admin', 'two', 'undo', '2026-10-06 12:00:00', None),
        (7, 'T_START', 'admin', 'one', 'undo', '2026-10-07 12:00:00', 'start'),
        (8, 'T_SYSTEM', 'admin', 'admin', 'undo', '2026-10-08 12:00:00', None),
    ]
    rows += [(100 + index, f'BULK_{index:03d}', 'admin', 'bulk', 'undo', '2025-01-01 12:00:00', None) for index in range(105)]
    with store.connection(write=True) as db:
        db.executemany('INSERT INTO transaction_log (id,code,login,namespace,type,timestamp,state,"transaction",title,ticket) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       [(*row, xml, 'Тест журнала', 'private-fixture-ticket') for row in rows])
        db.executemany('INSERT INTO retire_log (id,code,search_type,search_id,login,timestamp,search_code) VALUES (?,?,?,?,?,?,?)', [
            (1, 'R_ONE', 'contract/entity?project=one', '1', 'admin', '2026-10-01 12:00:00', 'A'),
            (2, 'R_TWO', 'contract/entity?project=two', '1', 'admin', '2026-10-01 12:00:00', 'A'),
            (3, 'R_CODE', 'contract/entity?project=one', None, 'admin', '2026-10-01 12:00:00', 'A'),
            (4, 'R_BASE', 'contract/entity', '1', 'admin', '2026-10-01 12:00:00', 'A'),
        ])
        db.execute('INSERT INTO sobject_log (id,code,search_type,search_id,login,timestamp,transaction_log_id) VALUES (1,?,?,?,?,?,1)',
                   ('S_ONE', 'contract/entity?project=one', 1, 'admin', '2026-10-01 12:00:00'))
        db.executemany('INSERT INTO change_timestamp (id,code,search_type,search_code,changed_on,changed_by) VALUES (?,?,?,?,?,?)', [
            (1, 'CT_FULL', 'contract/entity?project=one', 'A', '{"name":"2020-01-01"}', '{"name":"artist"}'),
            (2, 'CT_BASE', 'contract/entity', 'A', '{}', '{}'),
            (3, 'CT_NULL', 'contract/entity', None, '{}', '{}'),
        ])


def log_cases():
    cases = []
    def step(method, *args, **kwargs):
        return {'method': method, 'args': list(args), 'kwargs': kwargs}
    def add(name, steps, **options):
        cases.append({'name': name, 'method': 'journal_reads', 'steps': steps, **options})
    for project in ('one', 'two', 'admin', 'sthpw'):
        add('history_' + project, [step('get_last'), step('get_last', 'undo'), step('get_last', 'redo'), step('get_next_redo')], project=project)
    for user in (None, 'admin', 'artist', 'missing'):
        for namespace in (None, 'one', 'two', 'bulk', 'missing'):
            add('history_filter_' + str(user) + '_' + str(namespace), [step('get', user, namespace), step('get', user, namespace, 'NONE')])
    add('code_prefix', [step('code_key')])
    for owner, code in (('transaction', 'T_START'), ('sobject', 'S_ONE'), ('retire', 'R_ONE')):
        add('cached_code_' + owner, [step('get_by_code', code), step('get_by_code', code), step('get_by_code', code, show_retired=False), step('get_by_code', code, show_retired=False)], owner=owner)
        add('cached_id_' + owner, [step('get_by_id', 1), step('get_by_id', 1), step('get_by_id', 1, show_retired=False), step('get_by_id', 1, show_retired=False)], owner=owner)
        add('cached_miss_' + owner, [step('get_by_code', 'missing'), step('get_by_code', 'missing'), step('get_by_id', 9999), step('get_by_id', 9999)], owner=owner)
    for project in ('one', 'two'):
        for code in ('A', 'B'):
            add('retire_' + project + code, [step('retire_by_entity', code)], project=project)
    add('remote_start_noop', [step('trigger_remote_sync', 'T_START'), step('trigger_remote_undo', 'T_START')])
    for search_type in ('contract/entity?project=one', 'contract/entity'):
        for code in ('A', 'missing', None, 0):
            for insert in (False, True):
                add('change_' + search_type + str(code) + str(insert), [step('get_change_timestamp', search_type, code, insert), step('get_change_timestamp', search_type, code, not insert)])
    add('change_pending_reset', [step('get_change_timestamp', 'contract/entity?project=one', 'A'),
        step('set_cached_json', 'changed_on', {'amount': 'CHANGED'}), step('get_change_timestamp', 'contract/entity?project=one', 'A'),
        step('reset_transaction'), step('get_change_timestamp', 'contract/entity?project=one', 'A')])
    for value in (None, '', '<transaction/>', '<transaction><column>one &amp; two</column></transaction>',
                  '<transaction>\n  <column>\n    text\n  </column>\n</transaction>', '<transaction><column><![CDATA[a&b]]></column></transaction>'):
        add('xml_' + repr(value), [step('get_xml_value'), step('get_xml_value')], xml_value=value)
    add('xml_preserve_whitespace', [step('get_xml_value', remove_blank_text=False)], xml_value='<transaction>\n <column>value</column>\n</transaction>')
    add('xml_root_override', [step('get_xml_value', root='transaction')], xml_value='')
    add('xml_no_cache_write', [step('get_xml_value'), step('change_xml_value', '<transaction><column>new</column></transaction>'), step('get_xml_value')], xml_value='<transaction><column>old</column></transaction>')
    add('xml_cache_prefilled', [step('prefill_xml_cache', '<transaction><column>cached</column></transaction>'), step('get_xml_value')], xml_value='<transaction><column>raw</column></transaction>')
    xml = '<transaction><column>Сжатый XML</column></transaction>'
    add('xml_compressed', [step('get_xml_value')], xml_value=Common.compress_transaction(xml))
    for index, text in enumerate(('', 'Тест & < >', xml, 'x' * 11000)):
        add('compression_' + str(index), [step('compress_transaction', text), step('decompress_transaction', Common.compress_transaction(text))], compare_compressed_payload=True)
    return cases


class LogReadsParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        log_fixture(cls.store)
        cls.cases = log_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_log_case(case)

    def test_imports_inheritance_registry_and_source_signatures(self):
        from pyasm.search import TransactionLog as Imported
        from pyasm.search.transaction_log import TransactionLog as ModuleImported
        from pyasm.search.sobject_log import RetireLog as RetireImported
        self.assertIs(Imported, TransactionLog)
        self.assertIs(ModuleImported, TransactionLog)
        self.assertIs(RetireImported, RetireLog)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            for owner in (TransactionLog, SObjectLog, RetireLog):
                self.assertTrue(issubclass(owner, SObject))
            self.assertIsInstance(Search(TransactionLog.SEARCH_TYPE).get_sobject(), TransactionLog)
            # Keep the seed registry's generic SObject for sthpw/sobject_log.
            self.assertIs(type(Search(SObjectLog.SEARCH_TYPE).get_sobject()), SObject)
        for filename, owner in (('search/search.py', SObject), ('search/transaction.py', Transaction),
                                ('search/transaction_log.py', TransactionLog), ('search/sobject_log.py', SObjectLog),
                                ('search/sobject_log.py', RetireLog), ('common/common.py', Common)):
            tree = ast.parse((read_tests.LEGACY / 'src/pyasm' / filename).read_text(encoding='utf-8'))
            original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == owner.__name__)
            selected = {'get_by_id', 'get_by_code', 'get_xml_root', 'get_xml_value'} if owner is SObject else {'get_change_timestamp'} if owner is Transaction else {'compress_transaction', 'decompress_transaction'} if owner is Common else owner.__dict__
            for node in original.body:
                if not isinstance(node, ast.FunctionDef) or node.name not in selected:
                    continue
                expected = [arg.arg for arg in node.args.args]
                if expected and expected[0] == 'cls': expected = expected[1:]
                with self.subTest(owner=owner.__name__, method=node.name):
                    actual = inspect.signature(getattr(owner, node.name))
                    self.assertEqual(list(actual.parameters), expected)
                    self.assertEqual([parameter.default for parameter in actual.parameters.values() if parameter.default is not inspect.Parameter.empty],
                                     [ast.literal_eval(default) for default in node.args.defaults])

    def test_unported_writes_intervals_and_remote_queues_fail_before_changes(self):
        before = {path: path.read_bytes() for path in self.store.data_dir.glob('db/*.db')}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            log = TransactionLog.get_by_code('T_OLD')
            original_data = log.get_data()
            for operation in (lambda: TransactionLog.create('Command', '<transaction/>', 'Description'),
                              lambda: TransactionLog.create_sobject_log(log), TransactionLog.delete_all_redo,
                              log.undo, log.redo, log.trigger_remote_sync, log.trigger_remote_undo,
                              lambda: TransactionLog.get(time_interval='1 day'), lambda: RetireLog.get_by_interval('1 day'),
                              lambda: RetireLog.create('contract/entity', search_id=1),
                              lambda: SObjectLog.create(Search.get_by_code('contract/entity', 'A'), log, 'update')):
                with self.assertRaises(UnsupportedContract):
                    operation()
            self.assertEqual(log.get_data(), original_data)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_malformed_xml_fallback_and_unsupported_xml_are_explicit(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            obj = Search.get_by_code('contract/entity', 'A')
            obj.set_value('metadata', '<broken')
            with self.assertLogs('pyasm.search.search', level='WARNING'):
                self.assertEqual(obj.get_xml_value('metadata', root='transaction').to_string(), '<transaction/>\n')
            obj.set_value('metadata', '<!DOCTYPE transaction [<!ENTITY x "expanded">]><transaction>&x;</transaction>')
            with self.assertRaises(XmlException):
                obj.get_xml_value('metadata')
            obj.set_value('metadata', '<transaction><!-- comment --></transaction>')
            self.assertIn('comment', obj.get_xml_value('metadata').to_string())
            obj.set_value('metadata', '<transaction xmlns="namespace"/>')
            with self.assertRaises(UnsupportedContract):
                obj.get_xml_value('metadata')

    def test_public_api_does_not_expose_journal_tickets_or_raw_security_changes(self):
        ticket = {'ticket': self.ticket, 'project': 'one', 'language': 'python'}
        for search_type in ('sthpw/transaction_log', 'sthpw/sobject_log'):
            with self.assertRaises(UnsupportedContract):
                self.api.dispatch('query', (ticket, search_type))
            with self.assertRaises(UnsupportedContract):
                self.api.dispatch('get_by_search_key', (ticket, search_type + '|1'))
        rows = ast.literal_eval(self.api.dispatch('query', (ticket, 'sthpw/retire_log')))
        self.assertEqual(len(rows), 4)


class JournalUpgrade(unittest.TestCase):
    def test_owned_09_upgrade_is_atomic_repeatable_and_matches_original_definitions(self):
        resource = read_tests.ROOT / 'src/tactic_stream/compatibility/journal_upgrade.json'
        metadata = json.loads(resource.read_text(encoding='utf-8'))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(metadata, journal_schema(read_tests.LEGACY))
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-upgrade-password'))
            with store.connection(write=True) as db:
                initial_tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                for name in metadata['tables']:
                    db.execute('DROP TABLE "' + name + '"')
                    db.execute('DELETE FROM search_object WHERE search_type=?', ('sthpw/' + name,))
                account = dict(db.execute('SELECT * FROM login').fetchone())
            self.assertTrue(store.upgrade())
            with store.connection() as db:
                self.assertEqual(dict(db.execute('SELECT * FROM login').fetchone()), account)
                self.assertEqual({row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}, initial_tables)
                for migration in metadata['columns']:
                    self.assertIn(migration['column'], {row['name'] for row in db.execute('PRAGMA table_info("' + migration['table'] + '")')})
            before = store.database_path('sthpw').read_bytes()
            self.assertFalse(store.upgrade())
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE sobject_log')
                db.execute("UPDATE search_object SET class_name='custom.TransactionLog' WHERE search_type='sthpw/transaction_log'")
            before = store.database_path('sthpw').read_bytes()
            with self.assertRaises(ValueError):
                store.upgrade()
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)
