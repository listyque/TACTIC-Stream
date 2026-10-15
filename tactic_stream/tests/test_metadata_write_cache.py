"""Structural metadata stays cached only across known, trigger-free native writes."""
from pathlib import Path
import tempfile
import unittest

from test_foundation import fixture
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import DbContainer, Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class MetadataWriteCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))
        self.store.initialize(hash_password('private-test-password'))
        fixture(self.store)
        self.api = Api(self.store)
        ticket = self.api.get_ticket('admin', 'private-test-password')
        context = request_context(RequestContext(self.store, 'admin', 'one'))
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.api.auth.bind_security('admin', ticket)

    def test_native_writes_reuse_structural_metadata_and_keep_fresh_rows(self):
        def execute():
            obj = Search.get_by_code('contract/entity', 'A')
            info = SearchType.get_column_info('contract/entity')
            system = DbContainer.get('sthpw')
            project = obj.get_sql()
            statements = []
            system.get_connection().set_trace_callback(statements.append)
            project.get_connection().set_trace_callback(statements.append)
            try:
                for amount in (10, 20):
                    obj.set_value('amount', amount)
                    obj.commit(triggers=False)
                    self.assertIs(SearchType.get_column_info('contract/entity'), info)
                    self.assertEqual(Search.get_by_code('contract/entity', 'A').get_value('amount'), amount)
                    statements.clear()
                    for _ in range(10):
                        self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('one', 'entity'))
                        self.assertIs(SearchType.get_column_info('contract/entity'), info)
                    self.assertEqual(statements, [])
                obj.delete(log=False)
                self.assertIs(SearchType.get_column_info('contract/entity'), info)
                self.assertIsNone(Search.get_by_code('contract/entity', 'A'))
            finally:
                system.get_connection().set_trace_callback(None)
                project.get_connection().set_trace_callback(None)
        command = Command()
        command.get_transaction().set_sync(False)
        command.execute = execute
        Command.execute_cmd(command)

    def test_native_registry_and_project_writes_invalidate_and_rollback(self):
        def execute():
            self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('one', 'entity'))
            info = SearchType.get_column_info('contract/entity')
            project = Project.get_by_code('one')
            project.set_value('database', 'two')
            project.commit(triggers=False)
            self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('two', 'entity'))
            self.assertIsNot(SearchType.get_column_info('contract/entity'), info)
            search = Search('sthpw/search_object')
            search.add_filter('search_type', 'contract/entity')
            registry = search.get_sobject()
            registry.set_value('table_name', 'spt_process')
            registry.commit(triggers=False)
            self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('two', 'spt_process'))
            self.assertNotIn('amount', SearchType.get_column_info('contract/entity'))
            raise ValueError('late structural failure')
        command = Command()
        command.get_transaction().set_sync(False)
        command.execute = execute
        with self.assertRaisesRegex(ValueError, 'late structural failure'):
            Command.execute_cmd(command)
        self.assertEqual(self.store.resolve('contract/entity', 'one')[1:], ('one', 'entity'))
        self.assertIn('amount', SearchType.get_column_info('contract/entity'))

    def test_custom_native_sql_expression_invalidates_and_rolls_back(self):
        def execute():
            system = DbContainer.get('sthpw')
            def change_route():
                system.get_connection().execute("UPDATE search_object SET table_name='spt_process' "
                                                "WHERE search_type='contract/entity'")
                return 'Expression changes registry'
            system.get_connection().create_function('cache_route_expression', 0, change_route)
            self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'entity')
            self.assertIn('amount', SearchType.get_column_info('contract/entity'))
            log = SearchType.create('sthpw/debug_log')
            system._do_security_dml(log.get_table(),
                data=dict(code='METADATA_EXPRESSION', message='cache_route_expression()', login='admin'),
                unquoted=('message',), sobject=log)
            self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'spt_process')
            self.assertNotIn('amount', SearchType.get_column_info('contract/entity'))
            raise ValueError('late expression failure')
        command = Command()
        command.get_transaction().set_sync(False)
        command.execute = execute
        with self.assertRaisesRegex(ValueError, 'late expression failure'):
            Command.execute_cmd(command)
        self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'entity')
        self.assertIn('amount', SearchType.get_column_info('contract/entity'))

    def test_sql_triggers_invalidate_registry_changes_and_rollback(self):
        for temporary in ('', 'TEMP '):
            with self.subTest(temporary=bool(temporary)):
                def execute():
                    system = DbContainer.get('sthpw')
                    def warm_metadata():
                        self.store.resolve('contract/entity', 'one')
                        SearchType.get_column_info('contract/entity')
                        return 0
                    system.get_connection().create_function('cache_metadata_probe', 0, warm_metadata)
                    system.do_update("CREATE %sTRIGGER metadata_probe AFTER INSERT ON debug_log "
                        "BEGIN SELECT cache_metadata_probe(); UPDATE search_object SET table_name='spt_process' "
                        "WHERE search_type='contract/entity'; END" % temporary)
                    self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'entity')
                    self.assertIn('amount', SearchType.get_column_info('contract/entity'))
                    log = SearchType.create('sthpw/debug_log')
                    log.set_value('message', 'Trigger changes registry')
                    log.set_value('login', 'admin')
                    log.commit(triggers=False)
                    self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'spt_process')
                    self.assertNotIn('amount', SearchType.get_column_info('contract/entity'))
                    raise ValueError('late SQL trigger failure')
                command = Command()
                command.get_transaction().set_sync(False)
                command.execute = execute
                with self.assertRaisesRegex(ValueError, 'late SQL trigger failure'):
                    Command.execute_cmd(command)
                self.assertEqual(self.store.resolve('contract/entity', 'one')[2], 'entity')
                self.assertIn('amount', SearchType.get_column_info('contract/entity'))
