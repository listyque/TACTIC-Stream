import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, DbContainer, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tactic.core.schema_commands import SearchTypeCreatorCmd
from tools.snapshot_probe import run_snapshot_case


class SchemaTemplate(read_tests.ReadParity):
    filter_test_search_type = 'contract/schema_asset'
    test_expressions_and_sql_remain_explicitly_unsupported = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import schema_api_contract, schema_template_contract
        with cls.store.connection(write=True) as db:
            schema_api_contract.install_fixture(db)
            schema_template_contract.install_fixture(db)
        cls.cases = [dict(method='schema_template_contract', name=mode, operation=mode, project='one') for mode in ('copy', 'pipeline', 'pipeline_escaped', 'views', 'views_no_format')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case['operation'].startswith('views'):
            for view in ('definition', 'project_view'):
                self.assertEqual(len(result['sidebar'][view][3]), 1)
                # Source cases share their fixture; compare this creator's own element.
                name = 'tmpl_' + case['operation'] + '_list'
                source = original['sidebar'][view][3]
                active = [element for node in source for element in node[3] if element[1].get('name') == name]
                self.assertTrue(active)
                self.assertGreater(len(source), 1)  # Source duplicates the view on every append.
                self.assertTrue(all(element == result['sidebar'][view][3][0][3][0] for element in active))
            if case['operation'] == 'views_no_format':
                for view in ('definition', 'table'):
                    self.assertFalse(any(node[1]['name'] == 'amount' for node in original['configs'][view][3][0][3]))
                    self.assertTrue(any(node[1]['name'] == 'amount' for node in result['configs'][view][3][0][3]))
                self.assertEqual(result['configs']['edit'], original['configs']['edit'])
            else:
                self.assertEqual(result['configs'], original['configs'])
            return
        if case['operation'] == 'pipeline':
            self.assertEqual(original.pop('processes'), [])
            self.assertEqual(result.pop('processes'), [['model', 1, {'version': 2}], ['review', 2, {'version': 2}]])
            self.assertEqual(result, original)
            return
        if case['operation'] == 'pipeline_escaped':
            self.assertEqual(original, dict(code='one/tmpl_pipeline_escaped', names=[], processes=[]))
            self.assertEqual(result['names'], ['model', 'Review & approve'])
            self.assertEqual(result['processes'], [['model', 1, {'version': 2}], ['Review & approve', 2, {'version': 2}]])
            return
        self.assertEqual(original['error'], 'TypeError')
        self.assertIn('TableUndo.log', original['message'])
        self.assertTrue(result['schema'])
        self.assertEqual(result['source'], ['TEMPLATE_ROW'])
        self.assertEqual(result['rows'], [[index + 1, 'tmpl_original', 7, False, True, {'from': 'template', 'index': index}] for index in range(2)])
        self.assertIn('tmpl_original_value', result['columns'])

    def test_template_rollback_constraints_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/search_object', 'sthpw/schema', 'config/naming', 'config/widget_config', 'sthpw/sobject_list')
                before = {kind: [obj.get_sobject_dict() for obj in Search(kind).get_sobjects()] for kind in kinds}
                with self.assertRaisesRegex(ValueError, 'late template failure'):
                    run_snapshot_case(dict(method='schema_template_contract', fail=True))
                self.assertEqual({kind: [obj.get_sobject_dict() for obj in Search(kind).get_sobjects()] for kind in kinds}, before)
                self.assertNotIn('tmpl_copy', store.tables('sthpw'))
                result = run_snapshot_case(dict(method='schema_template_contract'))
                from pyasm.search import TransactionLog
                command_id = TransactionLog.get_last('undo').get_id()
                ticket = {'ticket': self.ticket, 'project': 'one'}
                for data in (dict(code='COPY1'), dict(code='BAD', tmpl_original_value=-1), dict(code='NULL', tmpl_original_value=None)):
                    with self.assertRaises(Exception):
                        api.dispatch('insert', (ticket, 'contract/tmpl_copy', data))
                sql = DbContainer.get(Project.get().get_project_db_resource())
                definition = sql.get_database_impl().get_table_definition(sql, 'tmpl_copy')
                self.assertEqual(len(definition['extras']), 1)
                self.assertIn("'tmpl_original'", definition['statement'])
                self.assertIn('tmpl_original_value', definition['statement'])
                self.assertIn('"tmpl_copy"', definition['extras'][0])
                # Schema create and inserted objects belong to one journaled command.
                api.dispatch('undo', (ticket, None, command_id))
                self.assertNotIn('tmpl_copy', store.tables('sthpw'))
                api.dispatch('redo', (ticket, None, command_id))
                self.assertEqual([obj.get_code() for obj in Search('contract/tmpl_copy').get_sobjects()], ['COPY1', 'COPY2'])
                self.assertEqual(Search('contract/tmpl_original').get_count(), 1)
                for template in ('contract/missing', 'contract/tmpl_original?project=two'):
                    creator = SearchTypeCreatorCmd(search_type_name='contract/forbidden_copy', copy_from_template=template)
                    creator.get_transaction().set_sync(False)
                    with self.assertRaises(Exception):
                        Command.execute_cmd(creator)
                    self.assertNotIn('forbidden_copy', store.tables('sthpw'))
