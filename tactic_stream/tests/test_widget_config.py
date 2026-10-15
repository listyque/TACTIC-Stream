import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.common import Xml, XmlException
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class WidgetConfigParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='widget_config_contract', name='xml_view_metadata', project='admin')]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        # Original wraps every descendant config twice and loses the inner elements.
        self.assertEqual(original.pop('nested_inline_names'), [])
        self.assertEqual(result.pop('nested_inline_names'), ['code'])
        super().assert_case_result(case, result, original)

    def test_file_and_view_cache_boundaries(self):
        from pyasm.widget import WidgetConfig, WidgetConfigView
        with tempfile.TemporaryDirectory() as directory, request_context(RequestContext(self.store, 'admin', 'admin')):
            path = Path(directory) / 'config.xml'
            path.write_text('<config><table><element name="one"/></table></config>', encoding='utf-8')
            first = WidgetConfig.get(view='table', file_path=str(path))
            path.write_text('<config><table><element name="two"/></table></config>', encoding='utf-8')
            second = WidgetConfig.get(view='table', file_path=str(path), use_cache=False)
            self.assertEqual(first.get_element_names(), ['one'])
            self.assertEqual(second.get_element_names(), ['two'])
            imported = second.import_element_node('two')
            Xml.set_attribute(imported, 'name', 'copy')
            self.assertEqual(second.get_element_names(), ['two'])
            left, right = WidgetConfigView('sthpw/note', 'table'), WidgetConfigView('sthpw/note', 'table')
            left.add_config(first)
            self.assertEqual(right.get_configs(), [])
            path.write_text('<!DOCTYPE config [<!ENTITY unsafe "data">]><config/>', encoding='utf-8')
            with self.assertRaises(XmlException):
                Xml(file_path=str(path))

    def test_saved_changes_invalidate_derived_views(self):
        from tactic_stream.server.api import Api
        from pyasm.security.authenticator import hash_password
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-widget-check'))
            api = Api(store)
            ticket = {'ticket': api.get_ticket('admin', 'private-widget-check'), 'project': 'admin'}
            code = '''
from pyasm.widget import WidgetConfigView
record = server.insert('config/widget_config', {'search_type':'sthpw/note', 'view':'table', 'config':'<config><table><element name="one"/></table></config>'})
first = WidgetConfigView.get_by_search_type('sthpw/note', 'table')
server.update(record['__search_key__'], {'config':'<config><table><element name="two"/></table></config>'})
second = WidgetConfigView.get_by_search_type('sthpw/note', 'table')
return [first.get_element_names(), second.get_element_names()]
'''
            self.assertEqual(api.dispatch('execute_python_script', (ticket, '', {'code': code}))['info'], [['one'], ['two']])

    def test_table_configuration_and_column_state(self):
        import ast
        from pyasm.common import Common
        from pyasm.common.errors import UnsupportedContract
        from pyasm.search import Search
        from pyasm.widget import WidgetConfig, WidgetConfigView
        from tactic.ui.panel import TableLayoutWdg
        with request_context(RequestContext(self.store, 'admin', 'one')):
            config = WidgetConfig.get(view='table', xml='<config><table><element name="code"/><element name="name"/></table></config>')
            widget = TableLayoutWdg(search_type='contract/entity', config=WidgetConfigView('contract/entity', 'table', [config]))
            self.assertEqual([item.get_name() for item in widget.get_widgets()], ['code', 'name'])
            rows = [Search.get_by_code('contract/entity', code) for code in ('A', 'B')]
            widget.set_sobjects(rows)
            column = widget.get_widget('name')
            column.set_current_index(1)
            self.assertEqual(column.get_text_value(), "O'Reilly")
            for path in ('tactic.ui.panel.TableLayoutWdg', 'tactic.ui.panel.FastTableLayoutWdg',
                         'tactic.ui.panel.table_layout_wdg.TableLayoutWdg'):
                self.assertEqual(Common.resolve_class(path).get_default_display_handler('name'), 'tactic.ui.common.SimpleTableElementWdg')
            with self.assertRaisesRegex(UnsupportedContract, 'HTML table rendering'):
                widget.get_display()
            # Document the original bug separately: explicit falsey values were lost.
            tree = ast.parse((read_tests.LEGACY / 'src/pyasm/widget/table_element_wdg.py').read_text(encoding='utf-8'))
            original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BaseTableElementWdg')
            method = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == 'get_value')
            namespace = {}
            exec(compile(ast.Module(body=[method], type_ignores=[]), '<original table get_value>', 'exec'), namespace)
            for value in (0, False, ''):
                column.set_value(value)
                self.assertEqual(namespace['get_value'](column), "O'Reilly")
                self.assertEqual(column.get_text_value(), value)
            from pyasm.common import SetupException
            from unittest.mock import patch
            from pyasm.search import SearchKey
            keys = ['contract/entity?project=one&amp;code=B', 'contract/entity?project=one&code=A',
                    'contract/entity?project=one&code=B', 'contract/entity?project=one&code=missing']
            with patch.object(Search, 'get_by_code', wraps=Search.get_by_code) as batch:
                self.assertEqual([obj.get_code() for obj in Search.get_by_search_keys(keys, keep_order=True)], ['B', 'A'])
                self.assertEqual(sum(call.args[0] == 'contract/entity?project=one' for call in batch.call_args_list), 1)
            self.assertEqual(SearchKey.get_by_search_keys([]), [])
            ids = ['contract/entity?project=one&id=2', 'contract/entity?project=one&id=1']
            self.assertEqual([obj.get_id() for obj in Search.get_by_search_keys(','.join(ids), keep_order=True)], [2, 1])
            with self.assertRaises(SetupException):
                Search.get_by_search_keys([keys[1], ids[0]])
            objects = Search.get_by_search_keys([keys[1], 'contract/entity?project=two&code=A'], keep_order=True)
            self.assertEqual([obj.get_project_code() for obj in objects], ['one', 'two'])
