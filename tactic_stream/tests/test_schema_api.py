import json
import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search import Search, DbContainer
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.common.errors import SecurityException, UnsupportedContract
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


class SchemaApiParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import schema_api_contract
        with cls.store.connection(write=True) as db:
            schema_api_contract.install_fixture(db)
        cls.cases = [dict(method='schema_api_contract', project='one', name='connections_instances_core_DDL')]

    def test_unported_filter_dependencies_and_sql_are_rejected(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            for filters in (['name = 1'], [['other_table.code', 'A']], [['name', '@@', 'secret']]):
                with self.assertRaises(UnsupportedContract):
                    Search('contract/schema_asset').add_op_filters(filters)

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('classes'), ['NameError', 'NameError'])
        self.assertEqual(result.pop('classes'), [True, False])
        self.assertEqual(original.pop('connection_lookup_count'), 0)
        self.assertEqual(result.pop('connection_lookup_count'), 1)
        self.assertEqual(original.pop('lookup_types'), ['contract/schema_asset', 'contract/schema_asset?project=one'])
        self.assertEqual(result.pop('lookup_types'), ['contract/schema_asset?project=one'] * 2)
        self.assertEqual(result, original)

    def test_schema_command_rollback_and_generic_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/connection', 'contract/schema_instance', 'sthpw/sobject_list',
                         'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'schema API rollback'):
                    run_snapshot_case(dict(method='schema_api_contract', fail=True))
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                self.assertNotIn('schema_ddl', DbContainer.get('sthpw').get_database_impl().get_table_info(DbContainer.get('sthpw').get_db_resource())
                                 if store.get_db_resource().get_vendor() == 'PostgreSQL' else store.tables('sthpw'))

    def test_connection_contexts_cache_and_missing_targets_do_not_delete_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                from pyasm.biz import SObjectConnection, Project
                from pyasm.command import Command
                from pyasm.search import SearchType
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                command = Command()
                def execute():
                    command.get_transaction().set_sync(False)
                    first = Search.get_by_code('contract/schema_asset', 'ASSET')
                    second = Search.get_by_code('contract/schema_tag', 'TAG')
                    self.assertEqual(SObjectConnection.get_connected_sobjects(first, context='alpha')[1], [])
                    SObjectConnection.create(first, second, context='alpha')
                    self.assertEqual(SObjectConnection.get_connected_sobject(first, context='alpha').get_code(), 'TAG')
                    SObjectConnection.create(first, second, context='beta')
                    self.assertEqual(len(SObjectConnection.get_connections([first], context='beta')), 1)
                    SObjectConnection.create(first, Project.get(), context='gamma')
                    self.assertEqual(len(SObjectConnection.get_sobjects(SObjectConnection.get_connections([first]))), 2)
                    # A mixed target list used to delete broken connections during reads.
                    SObjectConnection.create(Project.get(), first, context='missing', direction='src')
                    connection = SearchType.create('sthpw/connection')
                    connection.set_value('src_search_type', second.get_search_type())
                    connection.set_value('src_search_id', 9999)
                    connection.set_value('dst_search_type', first.get_search_type())
                    connection.set_value('dst_search_id', first.get_id())
                    connection.set_value('context', 'missing')
                    connection.commit()
                    before = Search('sthpw/connection').get_count()
                    connections, targets = SObjectConnection.get_connected_sobjects(first, context='missing')
                    self.assertEqual((len(connections), len(targets)), (2, 1))
                    self.assertEqual(Search('sthpw/connection').get_count(), before)
                    # Clear the target, not the broken connection, and repeat a read.
                    second.delete()
                    self.assertEqual(SObjectConnection.get_connected_sobjects(first, context='alpha')[1], [])
                command.execute = execute
                Command.execute_cmd(command)

    def test_search_type_creation_columns_records_and_failure_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'admin', 'language': 'python'}
            def call(method, *args):
                return api.dispatch(method, (ticket, *args))
            created = call('create_search_type', 'contract/created_schema', 'Created', 'Описание', True)
            self.assertEqual((created['search_type'], created['database']), ('contract/created_schema', '{project}'))
            self.assertTrue(call('add_column_to_search_type', 'contract/created_schema', 'extra', 'varchar(80)'))
            self.assertFalse(call('add_column_to_search_type', 'contract/created_schema', 'extra', 'varchar(80)'))
            record = call('insert', 'contract/created_schema', {'code': 'CREATED', 'name': 'Объект', 'extra': 'OK'})
            self.assertEqual(record['extra'], 'OK')
            self.assertIn('pipeline_code', call('get_column_names', 'contract/created_schema'))
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.assertEqual(Search('sthpw/sobject_list').get_count(), 1)
                api.auth.bind_security('admin', self.ticket)
                from pyasm.command import Command, ColumnAddCmd
                add = ColumnAddCmd('contract/created_schema', 'priority', 'Number')
                add.get_transaction().set_sync(False)
                Command.execute_cmd(add)
                self.assertIn('priority', Search('contract/created_schema').get_columns())
                command = Command()
                def execute():
                    api.create_search_type(ticket, 'contract/rolled_schema', 'Rolled')
                    api.insert(ticket, 'contract/rolled_schema', {'code': 'ROLLBACK'})
                    api.add_column_to_search_type(ticket, 'contract/rolled_schema', 'late', 'integer')
                    raise ValueError('late DDL failure')
                command.execute = execute
                with self.assertRaisesRegex(ValueError, 'late DDL failure'):
                    Command.execute_cmd(command)
                self.assertNotIn('rolled_schema', store.tables('sthpw'))
                registry = Search('sthpw/search_object')
                registry.add_filter('search_type', 'contract/rolled_schema')
                self.assertEqual(registry.get_count(), 0)
            for data_type in ('text; DROP TABLE login', 'varchar(2) DEFAULT evil()', 'text /* comment */'):
                with self.assertRaises(ValueError):
                    call('add_column_to_search_type', 'contract/created_schema', 'invalid', data_type)
            self.assertNotIn('invalid', call('get_column_names', 'contract/created_schema'))
            with self.assertRaises(Exception):
                call('create_search_type', 'contract/created_schema', 'Duplicate')
            self.assertEqual(call('get_by_search_key', record['__search_key__'])['extra'], 'OK')
            self.assertFalse(call('class_exists', 'os;raise RuntimeError.x'))
            with request_context(RequestContext(store, 'anonymous', 'admin')):
                with self.assertRaises((SecurityException, UnsupportedContract)):
                    DbContainer.get('sthpw').add_column('created_schema', 'denied', 'text')

