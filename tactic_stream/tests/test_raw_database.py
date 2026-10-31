"""Physical table CRUD, optimistic conflicts, rollback and administrator boundary."""
import copy
import builtins
import json
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from runpy import run_path
from types import SimpleNamespace
from unittest.mock import patch

from pyasm.common import Config, Environment, SecurityException
from pyasm.search import DbContainer, DbResource
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.raw_database import raw_database_operation, raw_database_request


class RawDatabaseTests(unittest.TestCase):
    def procedure_sources(self):
        handler = run_path(str(Path(__file__).resolve().parents[3]
                               / 'TH/thlib/ui/admin/raw_database_api.py'))
        return {
            'handler': inspect.getsource(handler['raw_database_request']),
            'stream': inspect.getsource(raw_database_request),
        }

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''})
        self.environment.start(); self.addCleanup(self.environment.stop)
        Config.reload_config()
        self.store = Store(Path(self.directory.name) / 'db')
        self.store.initialize(hash_password('raw-admin'))
        with self.store.connection(write=True) as db:
            db.execute('CREATE TABLE raw_sample (id INTEGER PRIMARY KEY, text TEXT DEFAULT \'default\', number INTEGER, password TEXT, derived TEXT GENERATED ALWAYS AS (text || number) VIRTUAL)')
            db.execute('INSERT INTO raw_sample (text,number,password) VALUES (?,?,?)', ('original', 42, 'private'))
            db.execute('CREATE TABLE raw_composite (a TEXT, b INTEGER, value TEXT, PRIMARY KEY(a,b)) WITHOUT ROWID')
            db.execute("INSERT INTO raw_composite VALUES ('one', 2, 'old')")
            db.execute('CREATE TABLE raw_no_key (value TEXT)')
            db.execute("INSERT INTO raw_no_key VALUES ('same'), ('same')")
            db.execute('CREATE TABLE raw_secret_key (token TEXT PRIMARY KEY, data JSON)')
            db.execute('INSERT INTO raw_secret_key VALUES (?,?)', ('private-token', '{"password":"embedded-private","label":"keep"}'))
        api = Api(self.store)
        self.ticket = api.get_ticket('admin', 'raw-admin')
        self.context = request_context(RequestContext(self.store, 'admin', 'admin'))
        self.context.__enter__(); self.addCleanup(self.context.__exit__, None, None, None)
        api.auth.bind_security('admin', self.ticket)

    def request(self, action, table='raw_sample', **parameters):
        return raw_database_operation(action, dict(project='admin', identity=json.dumps(['sthpw', table]), **parameters))

    def test_catalog_edit_insert_delete_export_and_drop(self):
        catalog = self.request('list')['catalog']
        self.assertTrue(any(row['identity'] == json.dumps(['sthpw', 'raw_sample']) for row in catalog))
        loaded = self.request('load')
        self.assertEqual(loaded['document']['rows'][0]['values']['password'], '[redacted]')
        self.assertNotIn('private', json.dumps(loaded))
        draft = copy.deepcopy(loaded['document'])
        draft['rows'][0]['values']['text'] = "quote ' backslash \\ newline\nЮникод"
        draft['rows'].append(dict(key=None, values={'number': None}))
        saved = self.request('save', document=draft, expected_revision=loaded['revision'])
        self.assertEqual(saved['metadata']['total'], 2)
        self.assertEqual(saved['document']['rows'][0]['values']['text'], draft['rows'][0]['values']['text'])
        self.assertEqual(saved['document']['rows'][1]['values']['text'], 'default')
        exported = self.request('export')['metadata']['csv']
        self.assertIn('Юникод', exported); self.assertNotIn('private', exported)
        draft = saved['document']; draft['rows'][0]['deleted'] = True
        deleted = self.request('save', document=draft, expected_revision=saved['revision'])
        self.assertEqual(deleted['metadata']['total'], 1)
        with self.assertRaisesRegex(ValueError, 'confirm DROP'):
            self.request('drop', expected_revision=deleted['revision'], confirmation='raw_sample')
        dropped = self.request('drop', expected_revision=deleted['revision'], confirmation='sthpw / raw_sample')
        self.assertFalse(any('raw_sample' in row['identity'] for row in dropped['catalog']))

    def test_conflicts_roll_back_entire_batch(self):
        loaded = self.request('load')
        first = copy.deepcopy(loaded['document'])
        first['rows'][0]['values']['text'] = 'committed'
        self.request('save', document=first, expected_revision=loaded['revision'])
        with self.assertRaisesRegex(ValueError, 'row changed'):
            self.request('save', document=loaded['document'], expected_revision=loaded['revision'])
        fresh = self.request('load')
        draft = copy.deepcopy(fresh['document'])
        draft['rows'][0]['values']['text'] = 'must rollback'
        draft['rows'].append(dict(key=None, values={'id': draft['rows'][0]['key'][0]}))
        with self.assertRaises(Exception):
            self.request('save', document=draft, expected_revision=fresh['revision'])
        self.assertEqual(self.request('load')['document']['rows'][0]['values']['text'], 'committed')
        draft = copy.deepcopy(fresh['document']); draft['rows'][0]['values']['password'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'read-only'):
            self.request('save', document=draft, expected_revision=fresh['revision'])

    def test_sparse_save_ignores_background_changes_to_untouched_rows(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO raw_sample (text,number) VALUES ('background',8)")
        loaded = self.request('load')
        with self.store.connection(write=True) as db:
            db.execute("UPDATE raw_sample SET text='background changed' WHERE id=2")
        draft = copy.deepcopy(loaded['document'])
        draft['rows'][0]['values']['text'] = 'edited'
        with self.assertRaisesRegex(ValueError, 'row changed'):
            self.request('save', document=draft, expected_revision=loaded['revision'])
        self.assertEqual(self.request('load')['document']['rows'][0]['values']['text'], 'original')
        draft['rows'] = [dict(key=draft['rows'][0]['key'], revision=draft['rows'][0]['revision'],
                              deleted=False, values={'text': 'edited'})]
        saved = self.request('save', document=draft, expected_revision=loaded['revision'])
        self.assertEqual([row['values']['text'] for row in saved['document']['rows']],
                         ['edited', 'background changed'])
        with self.store.connection(write=True) as db:
            db.execute("UPDATE raw_sample SET number=99 WHERE id=1")
        draft['rows'][0].update(revision=saved['document']['rows'][0]['revision'], values={'text': 'stale edit'})
        with self.assertRaisesRegex(ValueError, 'row changed'):
            self.request('save', document=draft, expected_revision=saved['revision'])
        self.assertEqual(self.request('load')['document']['rows'][0]['values']['text'], 'edited')

    def test_composite_and_missing_primary_keys_target_one_row(self):
        loaded = self.request('load', 'raw_composite')
        self.assertEqual(loaded['document']['rows'][0]['key'], ['one', 2])
        loaded['document']['rows'][0]['values']['value'] = 'new'
        saved = self.request('save', 'raw_composite', document=loaded['document'], expected_revision=loaded['revision'])
        self.assertEqual(saved['document']['rows'][0]['values']['value'], 'new')
        loaded = self.request('load', 'raw_no_key')
        loaded['document']['rows'][0]['deleted'] = True
        saved = self.request('save', 'raw_no_key', document=loaded['document'], expected_revision=loaded['revision'])
        self.assertEqual(saved['metadata']['total'], 1)

    def test_identifiers_and_admin_boundary(self):
        with self.assertRaisesRegex(ValueError, 'no longer exists'):
            self.request('load', 'raw_sample"; DROP TABLE login; --')
        from pyasm.security import Login
        Login.create('raw_reader', 'reader-password')
        api = Api(self.store); ticket = api.get_ticket('raw_reader', 'reader-password')
        with request_context(RequestContext(self.store, 'raw_reader', 'admin')):
            api.auth.bind_security('raw_reader', ticket)
            for action in ('list', 'load', 'save', 'drop', 'export'):
                with self.assertRaises(SecurityException):
                    self.request(action)

    def test_secret_primary_keys_and_nested_json_never_leave_server(self):
        loaded = self.request('load', 'raw_secret_key')
        serialized = json.dumps(loaded)
        self.assertNotIn('private-token', serialized)
        self.assertNotIn('embedded-private', serialized)
        self.assertEqual(loaded['document']['rows'][0]['key'], [1])
        self.assertIn('data', loaded['document']['rows'][0]['readonly'])
        loaded['document']['rows'][0]['values']['data'] = '{}'
        with self.assertRaisesRegex(ValueError, 'read-only'):
            self.request('save', 'raw_secret_key', document=loaded['document'], expected_revision=loaded['revision'])

    def test_handler_source_runs_through_native_python_procedure_transport(self):
        for name, source in self.procedure_sources().items():
            with self.subTest(procedure=name):
                code = source + '\nreturn raw_database_request(**kwargs["parameters"])'
                api = Api(self.store)
                auth = dict(ticket=self.ticket, project='admin', language='python')
                def call(action, **values):
                    parameters = dict(action=action, project_code='admin', identity=json.dumps(['sthpw', 'raw_sample']), **values)
                    return api.dispatch('execute_python_script', (auth, '', dict(code=code, parameters=parameters)))['info']
                loaded = call('load')
                loaded['document']['rows'][0]['values']['text'] = name + ' remote edit'
                saved = call('save', document=loaded['document'], expected_revision=loaded['revision'])
                self.assertEqual(saved['document']['rows'][0]['values']['text'], name + ' remote edit')

    def test_procedures_work_without_stream_errors_module_and_keep_admin_guard(self):
        def legacy_import(name, *args, **kwargs):
            if name == 'pyasm.common.errors':
                raise ModuleNotFoundError("No module named 'pyasm.common.errors'")
            return builtins.__import__(name, *args, **kwargs)

        for name, source in self.procedure_sources().items():
            with self.subTest(procedure=name):
                scope = {'__builtins__': {**vars(builtins), '__import__': legacy_import}}
                exec(source, scope)
                procedure = scope['raw_database_request']
                catalog = procedure('list')['catalog']
                identity = json.dumps(['sthpw', 'raw_sample'])
                self.assertIn(identity, [row['identity'] for row in catalog])
                loaded = procedure('load', identity=identity)
                self.assertEqual(loaded['document']['rows'][0]['values']['password'], '[redacted]')
                with patch.object(Environment, 'get_security', return_value=SimpleNamespace(is_admin=lambda: False)):
                    with self.assertRaises(SecurityException):
                        procedure('list')

    def test_pagination_null_empty_and_large_integer_precision(self):
        with self.store.connection(write=True) as db:
            db.executemany('INSERT INTO raw_no_key VALUES (?)', [(str(number),) for number in range(55)])
        page = self.request('load', 'raw_no_key', item_offset=50)
        self.assertEqual(page['metadata']['total'], 57)
        self.assertEqual(page['document']['offset'], 50)
        self.assertEqual(len(page['document']['rows']), 7)
        loaded = self.request('load')
        loaded['document']['rows'][0]['values']['text'] = ''
        loaded['document']['rows'][0]['values']['number'] = '9223372036854775807'
        saved = self.request('save', document=loaded['document'], expected_revision=loaded['revision'])
        self.assertEqual(saved['document']['rows'][0]['values']['text'], '')
        self.assertEqual(saved['document']['rows'][0]['values']['number'], '9223372036854775807')
        saved['document']['rows'][0]['values']['text'] = None
        saved = self.request('save', document=saved['document'], expected_revision=saved['revision'])
        self.assertIsNone(saved['document']['rows'][0]['values']['text'])


if __name__ == '__main__':
    unittest.main()
