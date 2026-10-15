import shutil
import sys
import tempfile
import ast
import importlib.util
import json
from unittest.mock import patch
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class WorkflowForm(read_tests.ReadParity):
    filter_test_search_type = 'contract/work_item'
    test_expressions_and_sql_remain_explicitly_unsupported = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import workflow_form_contract
        with cls.store.connection(write=True) as db:
            workflow_form_contract.install_fixture(db)
        cls.cases = [dict(method='workflow_form_contract', name=mode, operation=mode, project='one') for mode in ('metadata', 'edit', 'process_name')]

    def new_result(self, case):
        import workflow_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return workflow_form_contract.run(case)

    def assert_case_result(self, case, result, original):
        if case['operation'] == 'process_name':
            source_process = next(field for field in original['task'] if field['name'] == 'process')
            native_process = next(field for field in result['task'] if field['name'] == 'process')
            self.assertEqual(source_process['choices'], ['', 'edit|process'])
            self.assertEqual(native_process['choices'], ['', 'edit|process', 'review'])
            source_process['choices'] = native_process['choices']
            source_process['labels'] = native_process['labels']
        self.assertEqual(result, original)
        pipeline = result['item'][0]
        self.assertEqual(set(pipeline['choices']), {'', 'form_main', 'form_global'})
        assigned = next(field for field in result['task'] if field['name'] == 'assigned')
        if case['operation'] != 'process_name':
            self.assertEqual(assigned['choices'], ['', 'alice'])
        if case['operation'] == 'edit':
            self.assertEqual(result['saved']['context'], 'model/new')
            self.assertEqual(result['cleared']['context'], 'model')
            self.assertEqual(result['error'], 'UserException')
            self.assertEqual(result['after_error'], result['cleared'])

    def test_original_xmlrpc_client_and_handler_task_form(self):
        from test_transport import Transport
        from test_foundation import LEGACY
        import workflow_form_contract
        class FixtureServer(Transport):
            pass
        FixtureServer.setUpClass()
        self.addCleanup(FixtureServer.tearDownClass)
        with FixtureServer.store.connection(write=True) as db:
            db.execute("DELETE FROM schema WHERE code='one' OR project_code='one'")
            workflow_form_contract.install_fixture(db)
            db.execute("INSERT INTO plain_item (code,name) VALUES ('PLAIN','Plain parent')")
        spec = importlib.util.spec_from_file_location('workflow_source_client', LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(FixtureServer.url)
        client.set_project('one')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        # This module is test-only; supply the same source body through existing script API.
        source = (Path(__file__).parent / 'scripts/workflow_form_contract.py').read_text(encoding='utf-8')
        client.execute_python_script('', kwargs={'code': source + '\nreturn run({"operation": "metadata"})'})
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key='contract/work_task?project=one&code=TASK',
            view='workflow_form_test', element_names=['status']), values={'edit|status': 'In Progress'})
        handler = Path('D:/code/th_codex/thlib/tactic_query.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(handler).body if isinstance(node, ast.FunctionDef) and node.name == 'query_EditWdg')
        code = ast.get_source_segment(handler, function) + '\nreturn query_EditWdg(args=kwargs["form_args"], search_type=kwargs["kind"])'
        kind = 'contract/work_task'
        result = json.loads(client.execute_python_script('', kwargs=dict(code=code, kind=kind,
            form_args=dict(search_type=kind, search_key=kind + '?project=one&code=TASK', view='workflow_form_test')))['info'])
        status = next(item for item in result['InputWidgets'] if item['name'] == 'status')
        self.assertEqual(status['task_pipelines'], ['task'])
        self.assertEqual(status['__display_values__'], ['In Progress'])
        obj = client.get_by_code(kind, 'TASK')
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=obj['__search_key__'], view='workflow_form_test',
            element_names=['context', 'subcontext']), values={'edit|context': 'review', 'edit|subcontext': 'client'})
        self.assertEqual(client.get_by_code(kind, 'TASK')['context'], 'review/client')

        # Real Handler task-field catalog: default insert XML, including empty selects.
        client.set_project('admin')
        kind = 'sthpw/task'
        for parent_key in (None, 'sthpw/login?code=admin',
                           'contract/plain_item?project=one&code=PLAIN',
                           'contract/work_item?project=one&code=PARENT'):
            with self.subTest(parent_key=parent_key):
                result = json.loads(client.execute_python_script('', kwargs=dict(code=code, kind=kind,
                    form_args=dict(mode='insert', input_prefix='insert', search_key='', parent_key=parent_key,
                                   search_type=kind, view='insert')))['info'])
                self.assertEqual(result['EditWdg']['mode'], 'insert')
                fields = {item['name']: item for item in result['InputWidgets']}
                self.assertEqual(fields['priority']['values'], ['', '5', '4', '3', '2', '1'])
                for name in ('assigned', 'supervisor'):
                    if name not in fields:
                        continue  # Original EditWdg omits the column already fixed by this parent relation.
                    self.assertIn('admin', fields[name]['__display_values__']['values'])
                    self.assertEqual(len(fields[name]['__display_values__']['values']),
                                     len(fields[name]['__display_values__']['labels']))
                if parent_key and 'work_item' in parent_key:
                    self.assertEqual(fields['process']['pipeline_codes'], ['form_main'])
                else:
                    self.assertEqual(fields['process']['pipeline_codes'], [])
        client.set_project('one')
        result = json.loads(client.execute_python_script('', kwargs=dict(code=code, kind='contract/work_item',
            form_args=dict(mode='insert', search_type='contract/work_item', view='workflow_form_test')))['info'])
        pipeline = next(field for field in result['InputWidgets'] if field['name'] == 'pipeline_code')
        self.assertIn('form_main', pipeline['__display_values__']['values'])
        from tactic_stream.server.interface import read_form
        from tactic_stream.server.api import Api
        with request_context(RequestContext(FixtureServer.store, 'admin', 'admin')):
            Api(FixtureServer.store).auth.bind_security('admin', client.ticket['ticket'])
            form = read_form(kind, 'insert')
            self.assertNotIn('process', [field['name'] for field in form['fields']])

    def test_status_choices_preserve_current_value_and_check_access(self):
        from pyasm.common import Environment
        from pyasm.common.errors import UnsupportedContract
        from pyasm.widget import WidgetConfig
        from tactic.ui.input import ProcessInputWdg
        from tactic.ui.panel import EditWdg
        import workflow_form_contract
        self.assertIsInstance(WidgetConfig.create_widget('ProcessInputWdg'), ProcessInputWdg)
        with self.assertRaises(UnsupportedContract):
            WidgetConfig.create_widget('CalendarInputWdg')
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                workflow_form_contract.run({'operation': 'metadata'})
                widget = EditWdg(search_type='contract/work_task', search_key='contract/work_task?project=one&code=TASK', view='workflow_form_test')
                status = next(item for item in widget.get_widgets() if item.name == 'status')
                security = Environment.get_security()
                check_access = security.check_access
                def check(group, code, *args, **kwargs):
                    if group == 'process_select':
                        return False
                    if group == 'process':
                        return any(key['process'] == 'Complete' for key in code)
                    return check_access(group, code, *args, **kwargs)
                with patch.object(security, 'check_access', check):
                    labels, values = status.get_input().get_select_values()
                self.assertEqual(values, ['', 'Pending', 'Complete'])
