"""Request-local connection reuse and native batch result contracts."""
import ast
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from test_foundation import fixture
from pyasm.common.errors import UnsupportedContract
from pyasm.search import Search, SObject, Sql
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class CustomKeyObject(SObject):
    def get_search_key(self, use_id=False):
        return 'custom:' + str(self.get_id())


class EnginePerformance(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name))
        self.store.initialize(hash_password('private-performance-test'))
        fixture(self.store)
        self.api = Api(self.store)
        self.token = self.api.get_ticket('admin', 'private-performance-test')

    def test_identity_reader_reuses_connection_but_rechecks_retirement_and_groups(self):
        path = self.store.database_path('sthpw')
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("INSERT INTO login(code,login) VALUES('artist','artist')")
        with request_context(RequestContext(self.store, 'artist', 'one')) as context:
            first = Sql(self.store.get_db_resource('one')).connect()
            self.assertFalse(first._admin_sql)
            reader = context.read_connections['sthpw']
            with self.store.connection() as db:
                self.assertIs(db, reader)
                self.assertEqual(db.execute("SELECT split_part('a/b','/',2) AS value").fetchone()['value'], 'b')
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute('DELETE FROM login')
            # A committed account change from another client must be visible immediately.
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('grant','artist','admin')")
            second = Sql(self.store.get_db_resource('two')).connect()
            self.assertTrue(second._admin_sql)
            self.assertIs(context.read_connections['sthpw'], reader)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("DELETE FROM login_in_group WHERE login='artist'")
            third = Sql(self.store.get_db_resource('two')).connect()
            self.assertFalse(third._admin_sql)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE login SET s_status='retired' WHERE login='artist'")
            with self.assertRaises(UnsupportedContract):
                Sql(self.store.get_db_resource('sthpw')).connect()
        with self.assertRaises(sqlite3.ProgrammingError):
            reader.execute('SELECT 1')

    def test_query_batch_keys_preserve_project_code_id_and_custom_overrides(self):
        for project in ('one', 'two'):
            ticket = {'ticket': self.token, 'project': project}
            with request_context(RequestContext(self.store, 'admin', project)):
                self.api.auth.bind_security('admin', self.token)
                expected = [obj.get_search_key() for obj in Search('contract/entity').get_sobjects()]
            result = ast.literal_eval(self.api.dispatch('query', (ticket, 'contract/entity')))
            self.assertEqual([row['__search_key__'] for row in result], expected)
            self.assertTrue(any('&id=' in key for key in expected))
            projected = ast.literal_eval(self.api.dispatch('query', (ticket, 'contract/entity'), {'columns': ['name']}))
            self.assertEqual([row['__search_key__'] for row in projected], expected)
        with self.store.connection(write=True) as db:
            db.execute("UPDATE search_object SET class_name='test_engine_performance.CustomKeyObject' WHERE search_type='contract/entity'")
        result = ast.literal_eval(self.api.dispatch('query', (ticket, 'contract/entity')))
        self.assertEqual([row['__search_key__'] for row in result], ['custom:' + str(row['id']) for row in result])

    def test_failed_connect_closes_owned_identity_reader_with_request(self):
        with patch('pyasm.search.sql.sqlite3.connect', wraps=sqlite3.connect) as connect:
            with self.assertRaises(UnsupportedContract):
                with request_context(RequestContext(self.store, 'missing', 'one')) as context:
                    try:
                        Sql(self.store.get_db_resource('one')).connect()
                    finally:
                        reader = context.read_connections['sthpw']
            self.assertEqual(connect.call_count, 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            reader.execute('SELECT 1')

    def test_resolving_another_form_of_cached_type_does_not_enter_a_read_scope(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            first = self.store.resolve('contract/entity', 'one')
            with patch.object(self.store, 'connection', side_effect=AssertionError('Unnecessary read scope')):
                alternate = self.store.resolve('contract/entity?project=one', 'one')
            self.assertEqual(first, alternate)
            alternate[0]['table_name'] = 'changed_by_caller'
            self.assertEqual(self.store.resolve('contract/entity?project=one', 'one')[2], 'entity')
            self.assertEqual(self.store.resolve('contract/entity?project=two', 'one')[1], 'two')

    def test_reader_initialization_error_does_not_leak_connection(self):
        from pyasm.search.database_impl import SqliteImpl
        with self.assertRaisesRegex(ValueError, 'reader setup failed'):
            with request_context(RequestContext(self.store, 'admin', 'one')) as context:
                with patch.object(SqliteImpl, 'configure_connection', side_effect=ValueError('reader setup failed')):
                    try:
                        Sql(self.store.get_db_resource('one')).connect()
                    finally:
                        reader = context.read_connections['sthpw']
        with self.assertRaises(sqlite3.ProgrammingError):
            reader.execute('SELECT 1')
