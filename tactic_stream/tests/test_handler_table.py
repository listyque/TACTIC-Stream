"""Working Handler table cells, native inline edits and saved view metadata."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.command import Command, DatabaseAction
from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.ui.table.table_edit import TableCellEditCmd
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.table_cells import WIDGETS, read_table_cells, describe_cell
from tactic_stream.server.widget_configuration import read_widget_configuration

TYPE = 'sthpw/login_group'
XML = '''<config><table layout="TableLayoutWdg">
<element name="login_group" width="145"/><element name="description" width="160"/>
<element name="is_default"/>
<element name="preview"><display class="ThumbWdg"><detail>false</detail><icon_size>100%</icon_size></display></element>
<element name="details"><display class="tactic.ui.table.SObjectDetailElementWdg"/></element>
<element name="notes"><display class="tactic.ui.widget.DiscussionElementWdg"><allow_email>true</allow_email><note_format>full</note_format></display></element>
<element name="checkin"><display class="tactic.ui.table.CheckinButtonElementWdg"><process>publish</process><mode>upload</mode></display></element>
<element name="tasks"><display class="tactic.ui.table.TaskElementWdg"><layout>panel</layout><show_filler_tasks>true</show_filler_tasks></display></element>
<element name="folder"><display class="tactic.ui.table.ExplorerElementWdg"><mode>repository</mode></display></element>
<element name="files"><display class="tactic.ui.table.SObjectFilesElementWdg"/></element>
<element name="metadata"><display class="tactic.ui.table.MetadataElementWdg"/></element>
<element name="delete"><display class="tactic.ui.table.DeleteElementWdg"/></element>
</table></config>'''


def write(operation):
    command = Command(); command.execute = operation; command.get_transaction().set_sync(False)
    return Command.execute_cmd(command)


class HandlerTable(unittest.TestCase):
    def test_all_handler_registered_aliases(self):
        expected = json.loads((Path(__file__).parent/'fixtures/table_widget_aliases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(expected), len(set(expected)))
        self.assertFalse(set(expected) - set(WIDGETS))
        from pyasm.widget import WidgetConfig
        with request_context(RequestContext(None, 'admin')):
            for alias in expected:
                self.assertIsNotNone(WidgetConfig.create_widget(alias), alias)
        path = Path('D:/code/th_codex/thlib/ui/qml/tactic_frame/features/table/widgets.json')
        if path.exists():
            catalog = json.loads(path.read_text(encoding='utf-8'))
            names = [alias for entry in catalog for alias in entry['aliases'] if alias]
            self.assertEqual(sorted(names), sorted(expected))

    def test_native_cells_edits_conflicts_rollback_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH':'','TACTIC_TMP_CONFIG_PATH':''}):
            Config.reload_config()
            store = Store(Path(directory) / 'data'); store.initialize(hash_password('table-test-password'))
            api = Api(store); ticket = api.get_ticket('admin', 'table-test-password')
            try:
                with request_context(RequestContext(store, login='admin', project='admin')):
                    api.auth.bind_security('admin', ticket)
                    records = []
                    for code in ('A', 'B'):
                        obj = SearchType.create(TYPE); obj.set_value('login_group', 'TABLE_' + code); obj.set_value('description', code)
                        write(obj.commit); records.append(obj)
                    config = SearchType.create('config/widget_config'); config.set_value('search_type', TYPE); config.set_value('view','table'); config.set_value('config',XML); write(config.commit)
                    inputs = SearchType.create('config/widget_config'); inputs.set_value('search_type',TYPE); inputs.set_value('view','edit_definition')
                    inputs.set_value('config','<config><edit_definition><element name="is_default"><display class="CheckboxWdg"/><action class="DatabaseAction"/></element></edit_definition></config>');write(inputs.commit)
                    keys = [record.get_search_key() for record in records]
                    interface = read_interface(TYPE)
                    self.assertTrue(all(element['cell']['supported'] for element in interface['table']['elements']),
                        [element for element in interface['table']['elements'] if not element['cell']['supported']])
                    cells = read_table_cells(TYPE, 'table', keys)
                    for key in keys:
                        self.assertFalse(any(cell.get('error') for cell in cells[key].values()), cells[key])
                        self.assertEqual(cells[key]['checkin']['process'], 'publish')
                        self.assertEqual(cells[key]['details']['targetSearchKey'].split('?')[0], TYPE)
                        self.assertTrue(cells[key]['delete']['available'])
                    for action in ('details','checkin','folder','files','metadata','delete'):
                        self.assertFalse(next(element for element in interface['table']['elements'] if element['name'] == action)['cell']['sortable'])
                    scope = dict(search_type=TYPE, view='table', column='description', search_keys=keys)
                    def edit(**values):
                        return write(lambda: TableCellEditCmd(**scope, **values).execute())
                    plan = edit()
                    self.assertEqual(plan['field']['values'], ['A'])
                    result = edit(action='save', plans=plan['plans'], value='Updated')
                    self.assertEqual(len(result['search_keys']), 2)
                    self.assertEqual([record['description'] for record in result['records']], ['Updated','Updated'])
                    self.assertEqual([Search.get_by_search_key(key).get_value('description') for key in keys], ['Updated','Updated'])
                    bool_scope = {**scope, 'column':'is_default'}
                    boolean = write(lambda:TableCellEditCmd(**bool_scope).execute())
                    write(lambda:TableCellEditCmd(**bool_scope,action='save',plans=boolean['plans'],value=True).execute())
                    self.assertEqual(write(lambda:TableCellEditCmd(**bool_scope,action='check',plans=boolean['plans'],value=True).execute())['state'], 'saved')
                    self.assertEqual(edit(action='check', plans=plan['plans'], value='Updated')['state'], 'saved')
                    with self.assertRaisesRegex(ValueError, 'changed'):
                        edit(action='save', plans=plan['plans'], value='Stale')
                    prepared = edit()
                    original_execute, calls = DatabaseAction.execute, []
                    def fail_second(action):
                        calls.append(action)
                        if len(calls) == 2:
                            raise ValueError('late native action failure')
                        return original_execute(action)
                    with patch.object(DatabaseAction, 'execute', fail_second):
                        with self.assertRaisesRegex(ValueError, 'late native'):
                            edit(action='save', plans=prepared['plans'], value='Rolled back')
                    self.assertEqual(len(calls), 2)
                    self.assertEqual([Search.get_by_search_key(key).get_value('description') for key in keys], ['Updated','Updated'])
                    with self.assertRaisesRegex(ValueError, 'read-only'):
                        write(lambda: TableCellEditCmd(**{**scope,'column':'id'}).execute())
                    with self.assertRaisesRegex(ValueError, 'another type|does not belong'):
                        write(lambda: TableCellEditCmd(**{**scope,'search_keys':['sthpw/project?code=admin']}).execute())
                    metadata = read_widget_configuration(TYPE)
                    self.assertTrue(any(row['view'] == 'table' and row['current'] for row in metadata['table_views']))
                    candidate = dict(name='description', display=dict(handler='',options={'script_path':'do/not/run'}),action=dict(handler=''))
                    self.assertFalse(describe_cell(candidate, interface['columns'])['supported'])
                    config.set_value('config', XML.replace('</table>','<element name="description_time"><display class="tactic.ui.common.SimpleTableElementWdg"><column>description</column></display></element></table>'));write(config.commit)
                    inputs.set_value('config','<config><edit_definition><element name="description_time"><display class="tactic.ui.widget.TimeInputWdg"/><action class="TimeAction"><column>description</column></action></element></edit_definition></config>');write(inputs.commit)
                    for key in keys:
                        record = Search.get_by_search_key(key);record.set_value('description','2030-04-05 12:30:00');write(record.commit)
                    time_scope = {**scope,'column':'description_time'}
                    prepared = write(lambda:TableCellEditCmd(**time_scope).execute())
                    write(lambda:TableCellEditCmd(**time_scope,action='save',plans=prepared['plans'],value='17:45').execute())
                    self.assertEqual(write(lambda:TableCellEditCmd(**time_scope,action='check',plans=prepared['plans'],value='17:45').execute())['state'],'saved')
                with request_context(RequestContext(store, login='anonymous', project='admin')):
                    with self.assertRaises(SecurityException):
                        TableCellEditCmd(**scope).execute()
            finally:
                Config.reload_config()


if __name__ == '__main__':
    unittest.main()
