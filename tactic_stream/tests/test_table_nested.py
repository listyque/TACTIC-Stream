"""Nested tables preserve parent scope, ordering, pagination and stored views."""
import unittest
import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Task
from pyasm.search import Search
from pyasm.search import SearchType
from tactic.ui.table.nested_scope import nested_cell, read_nested_scope
from tactic.ui.table.hidden_row_element_wdg import HiddenRowElementWdg
from tactic.ui.table.nested_table import NestedTableReadCmd
from tactic_stream.server.table_cells import describe_cell


class NestedTables(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def test_bidding_currency_works_in_c_locale_for_cells_summaries_and_expressions(self):
        import locale
        from unittest.mock import patch
        from pyasm.common import FormatValue
        from tactic.ui.table.format_element_wdg import FormatElementWdg
        parent = Search.get_by_code('contract/entity', 'A')
        task = write(lambda: Task.create(parent, 'model', triggers=False))
        for value, expected in [(1250.75, '$1,250'), (0, '$0'), (-1250.75, '-$1,250')]:
            task.set_value('bid_cost', value)
            widget = FormatElementWdg(name='bid_cost', type='currency', format='-$1,234', total_summary='total')
            widget.set_sobject(task)
            with patch('locale.localeconv', return_value={'frac_digits': locale.CHAR_MAX}):
                self.assertEqual(widget.get_text_value(), expected)
                self.assertEqual(widget.evaluate_summary([task]), expected)
                self.assertEqual(FormatValue().get_format_value(value, '-$1,234'), expected)

    def test_bidding_computed_column_is_visible_to_its_display_expression_without_writes(self):
        from tactic.ui.table.expression_element_wdg import ExpressionElementWdg
        parent = Search.get_by_code('contract/entity', 'A')
        write(lambda: Task.create(parent, 'model', triggers=False))
        task = Search('sthpw/task').get_sobject()
        write(lambda: (task.set_value('bid_cost', 1250.50), task.commit()))
        parent.set_value('description', 'Unsaved draft')
        before = parent.get_data(), parent.update_data.copy()
        widget = ExpressionElementWdg(name='total_cost', expression='@SUM(sthpw/task.bid_cost)',
            display_expression='${@GET(.total_cost, %0.2f)}')
        widget.set_sobjects([parent]); widget.preprocess(); widget.set_current_index(0)
        self.assertEqual(widget.get_cell_value()['text'], '$1250.50')
        self.assertEqual((parent.get_data(), parent.update_data), before)
        self.assertNotIn('total_cost', parent.get_data())

    def test_bidding_named_views_saved_filter_and_order_stay_scoped(self):
        import json
        from tactic_stream.server.interface import read_form
        parent = Search.get_by_code('contract/entity', 'A')
        other = Search.get_by_code('contract/entity', 'B')
        def create():
            tasks = [Task.create(owner, 'model', context=str(i), triggers=False)
                     for i, owner in enumerate([parent, parent, other])]
            for task, cost in zip(tasks, [10, 20, 30]):
                task.set_value('bid_cost', cost); task.commit()
            values = [dict(prefix='main_body', main_body_column='bid_cost', main_body_relation='>',
                           main_body_value=0, main_body_enabled='on'),
                      dict(prefix='group', order='bid_cost desc')]
            config = SearchType.create('config/widget_config')
            config.set_value('search_type', 'sthpw/task')
            config.set_value('view', 'link_search:bidding')
            config.set_value('config', '<config><filter><values>' + json.dumps(values) + '</values></filter></config>')
            config.commit()
            edit = SearchType.create('config/widget_config')
            edit.set_value('search_type', 'sthpw/task'); edit.set_value('view', 'bidding_edit')
            edit.set_value('config', '<config><bidding_edit><element name="description"/><element name="bid_cost"/></bidding_edit></config>')
            edit.commit()
        write(create)
        options = dict(search_type='sthpw/task', view='table', search_view='link_search:bidding',
                       edit_view='bidding_edit', insert_view='bidding_edit', mode='insert')
        element = dict(name='tasks', display=dict(handler='HiddenRowToggleWdg', options=options), action=dict(handler='', options={}))
        self.assertTrue(describe_cell(element, {})['supported'])
        scope = nested_cell(parent.get_search_key(), options)['nestedTable']
        self.assertEqual(scope['insertView'], 'bidding_edit')
        self.assertEqual(scope['editView'], 'bidding_edit')
        result = read_nested_scope(scope['parentKey'], scope['searchType'], search_view=scope['searchView'])
        self.assertEqual([row['bid_cost'] for row in result['records']], [20, 10])
        form = read_form('sthpw/task', 'bidding_edit', parent_key=parent.get_search_key())
        self.assertEqual(form['mode'], 'insert')
        self.assertEqual([field['name'] for field in form['fields']], ['description', 'bid_cost'])

    def test_checkin_history_uses_the_owned_snapshot_table(self):
        parent = Search.get_by_code('contract/entity', 'A')
        cell = nested_cell(parent.get_search_key(), dict(dynamic_class='tactic.ui.widget.SObjectCheckinHistoryWdg'))
        scope = cell['nestedTable']
        self.assertEqual(scope['searchType'], 'sthpw/snapshot')
        self.assertEqual(scope['view'], 'checkin_history')
        self.assertFalse(scope['insert'])
        self.assertEqual(read_nested_scope(scope['parentKey'], scope['searchType'])['records'], [])

    def test_same_type_scope_selects_current_record_instead_of_every_record(self):
        parent = Search.get_by_code('contract/entity', 'A')
        result = read_nested_scope(parent.get_search_key(), 'contract/entity')
        self.assertEqual([row['code'] for row in result['records']], ['A'])

    def test_task_scope_paginates_without_leaking_other_parents(self):
        parent = Search.get_by_code('contract/entity', 'A')
        other = Search.get_by_code('contract/entity', 'B')
        write(lambda: [Task.create(parent, 'model', context='model/' + str(i), triggers=False) for i in range(3)])
        write(lambda: Task.create(other, 'model', triggers=False))
        first = read_nested_scope(parent.get_search_key(), 'sthpw/task', limit=2)
        second = read_nested_scope(parent.get_search_key(), 'sthpw/task', offset=2, limit=2)
        self.assertTrue(first['hasNext'])
        self.assertFalse(second['hasNext'])
        self.assertEqual(len(first['records']) + len(second['records']), 3)
        self.assertTrue(all(row['search_code'] == 'A' for row in first['records'] + second['records']))

    def test_unknown_class_and_unscoped_expression_fail_explicitly(self):
        parent = Search.get_by_code('contract/entity', 'A')
        with self.assertRaisesRegex(ValueError, 'not a migrated table'):
            nested_cell(parent.get_search_key(), {'dynamic_class': 'pyasm.prod.web.AssetHistoryWdg'})
        for expr in ('@GET(sthpw/task.code)', '@SOBJECT(sthpw/task) @PYTHON(1)', '@SOBJECT(@PYTHON(1))'):
            with self.subTest(expression=expr), self.assertRaisesRegex(ValueError, '@SOBJECT'):
                read_nested_scope(parent.get_search_key(), 'sthpw/task', expression=expr)

    def test_project_filter_sort_and_page_validation(self):
        parent = Search.get_by_code('contract/entity', 'A')
        for kwargs in ({'offset': -1}, {'limit': True}, {'limit': 101}, {'order_by': ['password desc']},
                       {'filters': [['name', 'or 1=1', 'x']]}, {'view': '../../edit'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                read_nested_scope(parent.get_search_key(), 'contract/entity', **kwargs)
        result = read_nested_scope(parent.get_search_key(), 'contract/entity', filters=[['code', '=', 'B']])
        self.assertEqual(result['records'], [])

    def test_login_scope_does_not_send_password_material_to_the_ui(self):
        login = Search('sthpw/login').get_sobject()
        result = read_nested_scope(login.get_search_key(), 'sthpw/login')
        self.assertEqual(len(result['records']), 1)
        self.assertNotIn('password', result['records'][0])

    def test_hidden_widget_is_a_computed_commands_cell(self):
        element = dict(name='nested', display=dict(handler='tactic.ui.table.HiddenRowElementWdg', options={
            'search_type': 'sthpw/task', 'view': 'table', 'show_insert': 'false'}), action=dict(handler='', options={}))
        descriptor = describe_cell(element, {})
        self.assertTrue(descriptor['supported'])
        self.assertEqual(descriptor['kind'], 'commands')
        parent = Search.get_by_code('contract/entity', 'A')
        widget = HiddenRowElementWdg(name='nested', **element['display']['options'])
        widget.set_sobject(parent)
        cell = widget.get_cell_value()
        self.assertEqual(cell['nestedTable']['parentKey'], parent.get_search_key())
        self.assertFalse(cell['nestedTable']['insert'])

    def test_transport_returns_normal_interface_and_typed_cells(self):
        parent = Search.get_by_code('contract/entity', 'A')
        command = NestedTableReadCmd(parent_key=parent.get_search_key(), search_type='contract/entity')
        result = command.execute()
        self.assertEqual(result['definition']['search_type'], 'contract/entity')
        self.assertIn(parent.get_search_key(), result['cells'])
        envelope = self.api.execute_cmd('', 'tactic.ui.table.NestedTableReadCmd',
            dict(parent_key=parent.get_search_key(), search_type='contract/entity'))
        self.assertEqual(envelope['status'], 'OK')
        self.assertEqual(envelope['info']['definition']['search_type'], 'contract/entity')

    def test_original_cg_tasks_parent_layout_reads_its_parent_table(self):
        import ast
        from pathlib import Path
        definitions = Path(__file__).resolve().parents[2] / 'cg/config_widget_config.spt'
        layout = None
        for block in definitions.read_text(encoding='utf-8-sig').split('#-- Start Entry --#'):
            if not block.strip():
                continue
            fields = {ast.literal_eval(node.args[0]): ast.literal_eval(node.args[1])
                for node in ast.walk(ast.parse(block)) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'set_value' and len(node.args) == 2}
            if fields.get('view') == 'columns.tasks_parent':
                layout = fields
                break
        self.assertIsNotNone(layout)
        def create():
            config = SearchType.create('config/widget_config')
            for key in ('view', 'config', 'category'):
                config.set_value(key, layout[key])
            config.commit()
            return Task.create(Search.get_by_code('contract/entity','A'), 'model', triggers=False)
        task = write(create)
        cell = nested_cell(task.get_search_key(), dict(dynamic_class='tactic.ui.table.CustomLayoutElementWdg',
            include_mako='true', view='columns/tasks_parent'))
        self.assertEqual(cell['nestedTable']['searchType'].split('?')[0], 'contract/entity')
        result = read_nested_scope(cell['nestedTable']['parentKey'], cell['nestedTable']['searchType'])
        self.assertEqual([row['code'] for row in result['records']], ['A'])

    def test_used_display_flags_and_initial_render_hint_are_validated(self):
        parent = Search.get_by_code('contract/entity', 'A')
        value=nested_cell(parent.get_search_key(),dict(show_select='false',show_shelf='false',
            show_search='false',show_search_limit='false',show_gear='false',init_load_num='500'))['nestedTable']
        self.assertFalse(value['selection'])
        self.assertFalse(value['shelf'])
        self.assertFalse(value['search'])
        self.assertFalse(value['searchLimit'])
        self.assertFalse(value['gear'])
        self.assertTrue(nested_cell(parent.get_search_key(),dict(show_gear='true'))['nestedTable']['gear'])
        for options in (dict(init_load_num='no'),dict(show_shelf='yes'),dict(show_gear='yes')):
            with self.subTest(options=options),self.assertRaises(ValueError):
                nested_cell(parent.get_search_key(),options)

    def test_hidden_row_toggle_row_add_and_aux_data_elements(self):
        from types import SimpleNamespace
        from pyasm.widget.table_element_wdg import AuxDataWdg, HiddenRowToggleWdg
        from tactic.ui.table.hidden_row_element_wdg import RowAddElementWdg
        parent = Search.get_by_code('contract/entity', 'A')
        toggle = HiddenRowToggleWdg(name='toggle', search_type='sthpw/task')
        toggle.set_sobject(parent)
        self.assertEqual(toggle.get_cell_value()['nestedTable']['searchType'], 'sthpw/task')
        row_add = RowAddElementWdg(name='tasks')
        row_add.set_sobject(parent)
        self.assertEqual(row_add.get_cell_value()['nestedTable']['searchType'], 'sthpw/task')
        custom_add = RowAddElementWdg(name='notes', search_type='sthpw/note')
        custom_add.set_sobject(parent)
        self.assertEqual(custom_add.get_cell_value()['nestedTable']['searchType'], 'sthpw/note')
        aux = AuxDataWdg(name='summary')
        aux.set_parent_wdg(SimpleNamespace(aux_data=[{'summary': 42}]))
        aux.set_current_index(0)
        self.assertEqual(aux.get_text_value(), '42')
        self.assertEqual(aux.get_cell_value(), {'text': '42'})
