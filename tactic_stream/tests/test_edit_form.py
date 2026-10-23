import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case
from tactic_stream.server.api import Api


class EditForm(read_tests.ReadParity):
    test_expressions_and_sql_remain_explicitly_unsupported = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import edit_form_contract
        with cls.store.connection(write=True) as db:
            edit_form_contract.install_fixture(db)
        cls.cases = [dict(method='edit_form_contract', name=mode, operation=mode, project='one')
                     for mode in ('metadata', 'edit')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def test_defaults_actions_and_bulk_rollback(self):
        from pyasm.command import DatabaseAction
        from pyasm.common import UserException
        from pyasm.search import Search, SearchType
        from tactic.ui.panel import EditWdg
        import edit_form_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            token = api.get_ticket('admin', 'private-test-password')
            ticket = dict(ticket=token, project='one')
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', token)
                edit_form_contract.run(dict(operation='metadata'))
                kind, view = 'contract/edit_entity', 'contract_edit_metadata'
                widget = EditWdg(search_type=kind, view=view, default={'name': 'Default', 'amount': 0, 'active': False})
                widget.explicit_display()
                self.assertEqual({item.name: item.get_values() for item in widget.get_widgets()}['amount'], [0])
                self.assertEqual({item.name: item.get_values() for item in widget.get_widgets()}['active'], [False])
                from pyasm.widget import CheckboxWdg
                self.assertEqual(CheckboxWdg('active', default=False).get_values(), [False])
                self.assertEqual(SearchType.get_tactic_type(kind, 'amount'), 'integer')
                inline = '<config><contract_edit_metadata><element name="name" title="A &amp; B"><display class="pyasm.widget.TextWdg"/></element></contract_edit_metadata></config>'
                self.assertEqual(EditWdg(search_type=kind, view=view, config_xml=inline).element_titles, ['A & B'])
                from pyasm.widget import SelectWdg
                select = SelectWdg(values='b|a', labels='B|A', extra_values='c|d', extra_labels='C|D')
                self.assertEqual(select.get_select_values(), (['B', 'A', 'C', 'D'], ['b', 'a', 'c', 'd']))
                select = SelectWdg(query=kind + '|code|name')
                self.assertEqual(select.get_select_values(), (['Original'], ['A']))
                select = SelectWdg(values_expr='@GET(contract/edit_entity.code)', labels_expr='@GET(contract/edit_entity.name)')
                self.assertEqual(select.get_select_values(), (['Original'], ['A']))
                select = SelectWdg(query=kind + '|get_code()|get_name()')
                self.assertEqual(select.get_select_values(), (['Original'], ['A']))
                from pyasm.common.errors import UnsupportedContract
                for bad_query in (kind + '|code|delete()', kind + '|_private()|name', kind + '|eval(1)|name'):
                    with self.assertRaises(UnsupportedContract):
                        SelectWdg(query=bad_query).get_select_values()
                from tactic.ui.filter import FilterData
                from pyasm.common import Container
                from pyasm.widget import TextWdg
                from pyasm.search import Transaction
                from pyasm.web import Web, WebContainer, WidgetSettings
                FilterData.get().set_data([{'prefix': 'main_body', 'status_filter': 'approved'}])
                persist_input = TextWdg('status_filter')
                persist_input.set_persist_on_submit('main_body')
                WebContainer.set_web(Web({}))
                self.assertEqual(persist_input.get_values(for_display=True), ['approved'])
                tx = Transaction.get(create=True)
                try:
                    db_input = TextWdg('saved_field')
                    db_input.set_persistence(db_input)
                    WebContainer.set_web(Web({'saved_field': 'persisted_val', 'is_form_submitted': 'yes'}))
                    self.assertEqual(db_input.get_values(), ['persisted_val'])
                    self.assertEqual(WidgetSettings.get_key_values(db_input.get_key()), ['persisted_val'])
                    db_input2 = TextWdg('saved_field')
                    db_input2.set_persistence(db_input)
                    WebContainer.set_web(Web({}))
                    self.assertEqual(db_input2.get_values(), ['persisted_val'])
                finally:
                    tx.rollback()
                    Container.put('FilterData', None)
                from pyasm.command import UniqueValueAction
                unique = UniqueValueAction()
                unique.set_name('code')
                unique.set_data('A')
                unique.set_sobject(Search.get_by_code(kind, 'A'))
                self.assertTrue(unique.check())
                from pyasm.web import Web, WebContainer
                outer_web = Web({'outer': 'preserved'})
                WebContainer.set_web(outer_web)
                with self.assertRaises(Exception):
                    api.execute_cmd(ticket, 'tactic.ui.panel.EditCmd',
                                    args=dict(multiplier=-1), values={'outer': 'inner'})
                self.assertIs(WebContainer.get_web(), outer_web)
                self.assertEqual(outer_web.get_form_value('outer'), 'preserved')
                action = DatabaseAction()
                # The exact source method drops numeric zero; keep this intentional bug fix explicit.
                import ast
                import six
                source = ast.parse((read_tests.LEGACY / 'src/pyasm/command/edit_wdg_action.py').read_text(encoding='utf-8'))
                original_class = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'DatabaseAction')
                method = next(node for node in original_class.body if isinstance(node, ast.FunctionDef) and node.name == 'convert_value')
                namespace = dict(six=six, UserException=UserException)
                exec(compile(ast.Module(body=[method], type_ignores=[]), '<source DatabaseAction>', 'exec'), namespace)
                self.assertIsNone(namespace['convert_value'](action, 'integer', 0))
                self.assertEqual(action.convert_value('integer', '$1,234'), 1234)
                self.assertEqual(action.convert_value('integer', 0), 0)
                self.assertEqual(action.convert_value('float', 0.0), 0.0)
                with self.assertRaises(UserException):
                    action.convert_value('integer', 'bad')
            keys = []
            for name in ('First', 'Second'):
                result = api.dispatch('execute_cmd', (ticket, 'tactic.ui.panel.EditCmd'),
                    dict(args=dict(view=view, data={'name': name, 'amount': 0}), values=dict(search_type=kind, search_id='-1')))
                keys.append(result['info']['search_key'])
                self.assertEqual(result['info']['sobject']['amount'], 0)
            args = dict(search_keys=keys, view=view, element_names=['name'], input_prefix='__NONE__',
                        update_data='[{"name":"Changed"},{"name":""}]', extra_data='[{},{}]', extra_action='[{},{}]')
            with self.assertRaises(UserException):
                api.dispatch('execute_cmd', (ticket, 'tactic.ui.panel.EditMultipleCmd'), dict(args=args))
            self.assertEqual([api.dispatch('get_by_search_key', (ticket, key))['name'] for key in keys],
                             ['First', 'Second'])
            args['update_data'] = '[{"name":"One"},{"name":"Two"}]'
            result = api.dispatch('execute_cmd', (ticket, 'tactic.ui.panel.EditMultipleCmd'), dict(args=args))
            self.assertEqual([api.dispatch('get_by_search_key', (ticket, key))['name']
                              for key in result['info']['search_keys']], ['One', 'Two'])
