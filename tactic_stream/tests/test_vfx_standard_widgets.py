"""Standard VFX declarations use the native form, cell and instance-link owners."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_form, read_interface
from tactic_stream.server.table_cells import describe_cell, read_table_cells
from tactic.ui.panel import EditCmd
from tactic.ui.table.drop_element_wdg import DropElementEditCmd, edit_drop_links
from tactic.ui.table.nested_scope import nested_cell
from test_table_embedded_widgets import write
from test_vfx_relationships import exercise


class VfxStandardWidgets(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.store = Store(Path(directory))
        self.store.initialize(hash_password('plugin-test-password'))
        exercise(self.store, 'standard_vfx')
        self.api = Api(self.store)
        ticket = self.api.get_ticket('admin', 'plugin-test-password')
        self.auth = dict(ticket=ticket, project='standard_vfx_ok')
        self.enterContext(request_context(RequestContext(self.store, 'admin', 'standard_vfx_ok')))
        self.api.auth.bind_security('admin', ticket)

    def column(self, stype, view, name):
        return next(item for item in read_interface(stype, view)['table']['elements'] if item['name'] == name)

    def handler_read(self, function, **kwargs):
        source = (Path(__file__).resolve().parents[3] / 'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == function)
        script = ast.get_source_segment(source, node) + '\nreturn ' + function + '(' + ','.join(
            key + '=' + repr(value) for key, value in kwargs.items()) + ')'
        result = self.api.dispatch('execute_python_script', (self.auth, '', dict(code=script)))['info']
        return json.loads(result) if isinstance(result, str) else result

    def test_text_inputs_read_and_save_actual_vfx_forms(self):
        for stype in ('vfx/art_reference', 'vfx/layer'):
            record = Search(stype).get_sobject()
            form = read_form(stype, search_key=record.get_search_key())
            field = next(field for field in form['fields'] if field['name'] == 'name')
            self.assertEqual(field['class_name'], 'tactic.ui.input.text_input_wdg.TextInputWdg')
            native = self.handler_read('query_EditWdg', search_type=stype, project='standard_vfx_ok',
                                       args=dict(view='edit', search_key=record.get_search_key()))
            self.assertTrue(any(field['class_name'] == 'tactic.ui.input.text_input_wdg.TextInputWdg'
                                for field in native['InputWidgets']))
            write(lambda: EditCmd(search_key=record.get_search_key(), data={'name': 'Changed'}).execute())
            self.assertEqual(Search.get_by_search_key(record.get_search_key()).get_value('name'), 'Changed')
            self.assertIn('name', [field['name'] for field in read_form(stype, 'insert')['fields']])

    def test_wiki_description_is_safe_multiline_text_and_has_an_inline_editor(self):
        record = SearchType.create('vfx/plate')
        record.set_value('description', '<img src=x onerror=alert(1)>\nSecond line')
        write(record.commit)
        column = self.column('vfx/plate', 'table', 'description')
        self.assertTrue(column['cell']['supported'])
        self.assertTrue(column['cell']['editable'])
        cell = read_table_cells('vfx/plate', 'table', [record.get_search_key()])[record.get_search_key()]['description']
        self.assertNotIn('error', cell)
        self.assertEqual(cell['text'], record.get_value('description'))
        self.assertTrue(cell['multiline'])
        native = self.handler_read('query_table_layout', search_type='vfx/plate', view='table',
                                   project_code='standard_vfx_ok', search_keys=[record.get_search_key()])
        self.assertEqual(native['rows'][record.get_search_key()]['description']['text'], cell['text'])
        self.assertTrue(native['rows'][record.get_search_key()]['description']['multiline'])

    def test_camera_template_selector_uses_vfx_shots_and_keeps_upload(self):
        record = Search('vfx/camera').get_sobject()
        form = read_form('vfx/camera', search_key=record.get_search_key())
        fields = {field['name']: field for field in form['fields']}
        self.assertEqual(fields['shot_code']['options']['query'], 'vfx/shot|code|code')
        self.assertIn('SH010', fields['shot_code']['choices'])
        self.assertEqual(fields['files']['input']['type'], 'file')
        self.assertEqual(fields['files']['action']['handler'], 'UploadAction')

    def test_review_hidden_table_accepts_its_original_full_width(self):
        record = SearchType.create('vfx/review')
        write(record.commit)
        column = self.column('vfx/review', 'review_tracking', 'submission')
        self.assertTrue(column['cell']['supported'])
        options = column['display']['options']
        cell = nested_cell(record.get_search_key(), options)
        self.assertEqual(cell['nestedTable']['searchType'], 'vfx/submission')
        self.assertEqual(cell['nestedTable']['view'], 'review_submission_list')
        native = self.handler_read('query_table_layout', search_type='vfx/review', view='review_tracking',
                                   project_code='standard_vfx_ok', search_keys=[record.get_search_key()])
        self.assertEqual(native['rows'][record.get_search_key()]['submission']['nestedTable'], cell['nestedTable'])
        column['display']['options'] = dict(options, width='broken')
        self.assertFalse(describe_cell(column, {})['supported'])
        with self.assertRaisesRegex(ValueError, 'width'):
            nested_cell(record.get_search_key(), column['display']['options'])

    def test_original_drop_action_reaches_guarded_instance_link_command(self):
        for stype, view, instance in (
            ('vfx/shot', 'planner_shot', 'vfx/asset_in_shot'),
            ('vfx/sequence', 'planner_sequence', 'vfx/asset_in_sequence'),
        ):
            column = self.column(stype, view, 'asset_drop')
            self.assertTrue(column['cell']['supported'], column)
            parent = Search(stype).get_sobject()
            asset = Search('vfx/asset').get_sobject()
            args = dict(search_type=stype, view=view, column='asset_drop', parent_key=parent.get_search_key())
            prepared = edit_drop_links(**args)
            write(lambda: DropElementEditCmd(**args, action='save', target_keys=[asset.get_search_key()],
                                            expected_revision=prepared['expected_revision']).execute())
            self.assertEqual(len(parent.get_related_sobjects(instance)), 1)
            native = self.handler_read('query_table_layout', search_type=stype, view=view,
                                       project_code='standard_vfx_ok', search_keys=[parent.get_search_key()])
            self.assertFalse(native['rows'][parent.get_search_key()]['asset_drop']['error'])
            self.assertEqual(len(native['rows'][parent.get_search_key()]['asset_drop']['links']), 1)
            fresh = edit_drop_links(**args)
            with self.assertRaisesRegex(ValueError, 'changed'):
                write(lambda: DropElementEditCmd(**args, action='save', target_keys=[],
                                                expected_revision='stale').execute())
            self.assertEqual(len(parent.get_related_sobjects(instance)), 1)
            write(lambda: DropElementEditCmd(**args, action='save', target_keys=[],
                                            expected_revision=fresh['expected_revision']).execute())
            self.assertEqual(parent.get_related_sobjects(instance), [])
            column['action']['options']['instance_type'] = 'vfx/wrong_type'
            self.assertFalse(describe_cell(column, {})['supported'])

    def test_shot_sheet_task_notes_keep_parent_and_process(self):
        task = Search('sthpw/task').get_sobject()
        column = self.column('sthpw/task', 'shot_sheet_wdg_tasks', 'notes')
        self.assertTrue(column['cell']['supported'], column)
        cell = read_table_cells('sthpw/task', 'shot_sheet_wdg_tasks', [task.get_search_key()])[task.get_search_key()]['notes']
        self.assertNotIn('error', cell)
        self.assertEqual(cell['search_key'], task.get_parent().get_search_key())
        self.assertEqual(cell['process'], task.get_value('process'))
        native = self.handler_read('query_table_layout', search_type='sthpw/task', view='shot_sheet_wdg_tasks',
                                   project_code='standard_vfx_ok', search_keys=[task.get_search_key()])
        self.assertEqual(native['rows'][task.get_search_key()]['notes']['search_key'], cell['search_key'])
        self.assertEqual(native['rows'][task.get_search_key()]['notes']['process'], cell['process'])
        from tactic.ui.widget.discussion_wdg import DiscussionElementWdg
        with patch.object(DiscussionElementWdg, 'get_cell_value', None):
            fallback = self.handler_read('query_table_layout', search_type='sthpw/task', view='shot_sheet_wdg_tasks',
                                         project_code='standard_vfx_ok', search_keys=[task.get_search_key()])
        self.assertEqual(fallback['rows'][task.get_search_key()]['notes']['search_key'], cell['search_key'])
        self.assertEqual(fallback['rows'][task.get_search_key()]['notes']['process'], cell['process'])


if __name__ == '__main__':
    unittest.main()
