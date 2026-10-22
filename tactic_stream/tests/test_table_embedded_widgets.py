"""L02 configured cells reuse native note/task writes and format original messages."""

import ast
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pyasm.command import Command
from pyasm.common import Config, UserException
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from pyasm.widget import WidgetConfig
from pyasm.widget.discussion_wdg import DiscussionWdg
from pyasm.widget.task_wdg import SObjectTaskTableElement, TaskParentSpacingTableElement
from tactic.ui.app.message_wdg import MessageTableElementWdg
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.table_cells import describe_cell, read_table_cells

LEGACY = Path(__file__).resolve().parents[2] / 'legacy/src'


def write(operation):
    command = Command()
    command.execute = operation
    command.get_transaction().set_sync(False)
    return Command.execute_cmd(command)


class Dom:
    def __init__(self, text=''):
        self.children = [text] if text else []
        self.attributes = {}

    def add(self, value):
        self.children.append(value)
        return value

    def add_row(self):
        return self

    def add_cell(self, value=None):
        return self.add(Dom(value))

    def add_style(self, *args):
        pass

    add_styles = add_style

    def add_attr(self, key, value):
        self.attributes[key] = value

    set_attr = add_attr
    set_id = add_style

    def text(self):
        return ''.join(value.text() if isinstance(value, Dom) else str(value)
                       for value in self.children)


def original_method(path, class_name, method_name, namespace):
    tree = ast.parse((LEGACY / path).read_text(encoding='utf-8-sig'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                  and node.name == method_name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), path, 'exec'), namespace)
    return namespace[method_name]


class EmbeddedTableWidgets(unittest.TestCase):
    def setUp(self):
        self.enterContext(request_context(RequestContext(None, 'admin')))

    def test_message_projection_matches_original_formatting_and_never_runs_markup(self):
        original = original_method('tactic/ui/app/message_wdg.py', 'FormatMessageWdg',
            'get_display', dict(Table=Dom, DivWdg=Dom, HtmlElement=Dom,
                               jsonloads=json.loads,
                               Project=SimpleNamespace(extract_base_search_type=lambda name: name)))
        cases = [
            ('', 'Ordinary message', 'Ordinary message', None),
            ('chat', 'Two\nlines', 'Two\nlines', None),
            ('sobject', {'search_type': 'sthpw/note', 'update_data': {'note': 'Review'}, 'sobject': {}}, 'Review', None),
            ('sobject', {'search_type': 'sthpw/task', 'update_data': {'process': 'model'}, 'sobject': {}}, 'model', None),
            ('sobject', {'search_type': 'sthpw/snapshot', 'sobject': {'process': 'publish'}}, 'publish', None),
            ('progress', {'message': 'Uploading', 'progress': 25}, 'Uploading', 25),
            ('', {'description': 'Saved result'}, 'Saved result', None),
        ]
        for category, payload, body, percent in cases:
            data = dict(category=category, message=json.dumps(payload) if isinstance(payload, dict) else payload,
                        login='artist', code='M1', timestamp='2030-01-01')
            record = SimpleNamespace(get_value=lambda key, **kw: data.get(key, ''),
                get_search_type=lambda: 'sthpw/message', get=lambda key: data.get(key))
            widget = MessageTableElementWdg()
            widget.set_sobject(record)
            cell = widget.get_cell_value()
            old = original(SimpleNamespace(sobjects=[record], kwargs={'show_preview': False}))
            self.assertEqual(cell['text'], body)
            self.assertIn(body.replace('\n', ''), re.sub('<[^>]*>', '', old.text()).replace('\n', ''))
            self.assertEqual(cell['progress'], percent)
            self.assertEqual(cell['author'], 'artist')
        data['message'] = '<img src=x onerror="window.unexpected=true">'
        self.assertEqual(widget.get_cell_value()['text'], data['message'])
        for payload in ('{not JSON}', '{"progress": NaN}'):
            data.update(category='progress', message=payload)
            with self.assertRaises(ValueError):
                widget.get_cell_value()

    def test_parent_context_matches_original_display(self):
        original = original_method('pyasm/widget/task_wdg.py', 'TaskParentSpacingTableElement',
                                   'get_display', dict(DivWdg=Dom))
        for context in ('model', 'model/high/res', ''):
            record = SimpleNamespace(get_value=lambda name: context, get_id=lambda: 1)
            widget = TaskParentSpacingTableElement(name='context')
            widget.set_sobject(record)
            self.assertEqual(widget.get_cell_value()['text'], original(widget).text())
            self.assertEqual(widget.get_cell_value()['tooltip'], context)

    def test_four_registered_classes_reject_unhandled_options(self):
        for cls, kind in ((DiscussionWdg, 'notes'), (SObjectTaskTableElement, 'tasks'),
                          (TaskParentSpacingTableElement, 'text'), (MessageTableElementWdg, 'message')):
            name = cls.__module__ + '.' + cls.__name__
            self.assertIsInstance(WidgetConfig.create_widget(name), cls)
            element = dict(name='computed', display=dict(handler=name, options={}), action=dict(handler=''))
            descriptor = describe_cell(element, {})
            self.assertEqual(descriptor['kind'], kind)
            self.assertTrue(descriptor['supported'] and descriptor['server'])
            element['display']['options']['script_path'] = 'never/execute'
            self.assertFalse(describe_cell(element, {})['supported'])


class EmbeddedTableLifecycle(unittest.TestCase):
    def test_native_configured_note_task_lifecycle_and_scopes(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,
                {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory) / 'data')
            store.initialize(hash_password('embedded-table-fixture'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'embedded-table-fixture')
            try:
                with request_context(RequestContext(store, login='admin', project='admin')):
                    api.auth.bind_security('admin', ticket)
                    from tactic.core.schema_commands import SearchTypeCreatorCmd
                    write(lambda: SearchTypeCreatorCmd(search_type_name='contract/l02_parent',
                        sobject_pipeline=True, process=['publish']).execute())
                    objects = []
                    for name in ('L02_ONE', 'L02_TWO'):
                        obj = SearchType.create('contract/l02_parent')
                        obj.set_value('code', name)
                        write(obj.commit)
                        objects.append(obj)
                    config = SearchType.create('config/widget_config')
                    config.set_value('search_type', 'contract/l02_parent')
                    config.set_value('view', 'table')
                    config.set_value('config', '''<config><table layout="TableLayoutWdg">
                      <element name="notes"><display class="DiscussionWdg"><include_submission>false</include_submission></display></element>
                      <element name="tasks"><display class="pyasm.widget.SObjectTaskTableElement"><supe>true</supe><bid_edit>false</bid_edit><simple_date>true</simple_date><width>280</width></display></element>
                      </table></config>''')
                    write(config.commit)
                    definition = read_interface('contract/l02_parent')
                    self.assertTrue(all(el['cell']['supported'] for el in definition['table']['elements']))
                    target = objects[0]
                    from tactic.ui.widget.discussion_wdg import DiscussionAddNoteCmd, DiscussionReadCmd, DiscussionChangeNoteCmd
                    add_note = DiscussionAddNoteCmd(search_key=target.get_search_key(),
                        process='publish', note='Embedded note')
                    write(add_note.execute)
                    note = add_note.info['note']
                    read = write(lambda: DiscussionReadCmd(search_key=target.get_search_key()).execute())
                    record = read['notes'][0]
                    write(lambda: DiscussionChangeNoteCmd(search_key=target.get_search_key(), action='edit',
                        id=note['id'], body='Updated embedded note', expected_revision=record['revision']).execute())
                    foreign = SearchType.create('sthpw/note')
                    for name, value in dict(search_type='contract/l02_parent', search_code=target.get_code(),
                            search_id=target.get_id(), project_code='other_project', process='publish',
                            context='publish', login='admin', note='Other project with the same parent code').items():
                        foreign.set_value(name, value)
                    write(foreign.commit)
                    task = SearchType.create('sthpw/task')
                    for name, value in dict(search_type=target.get_search_type(), search_id=target.get_id(),
                            search_code=target.get_code(), project_code='admin', process='publish', context='publish',
                            status='Pending', bid_start_date='2030-01-01', bid_end_date='2030-01-03').items():
                        task.set_value(name, value)
                    write(task.commit)
                    keys = [obj.get_search_key() for obj in objects]
                    cells = read_table_cells('contract/l02_parent', 'table', keys)
                    self.assertEqual(cells[keys[0]]['notes']['count'], 1)
                    self.assertEqual(cells[keys[1]]['notes']['count'], 0)
                    row = cells[keys[0]]['tasks']
                    self.assertNotIn('error', row)
                    self.assertEqual(row['widthHint'], 280)
                    self.assertTrue(row['tasks'])
                    self.assertEqual(row['tasks'][0]['taskCode'], task.get_code())
                    self.assertTrue(row['tasks'][0]['editAssigned'])
                    self.assertFalse(row['tasks'][0]['editDates'])
                    self.assertEqual(cells[keys[1]]['tasks']['tasks'], [])
                    from tactic.ui.table.task_inspector import TaskTableEditCmd
                    source = dict(search_key=target.get_search_key(), task_key=task.get_search_key(),
                                  process='publish', context='publish')
                    plans = write(lambda: TaskTableEditCmd(source=source).execute())['plans']
                    plans[0]['data'] = dict(status='Waiting')
                    write(lambda: TaskTableEditCmd(action='save', plans=plans).execute())
                    self.assertEqual(Search.get_by_id('sthpw/task', task.get_id()).get_value('status'), 'Waiting')
                    with self.assertRaisesRegex(UserException, 'changed'):
                        write(lambda: TaskTableEditCmd(action='save', plans=plans).execute())
                    selected = SObjectTaskTableElement(process_filter='scope_process')
                    selected.set_sobjects(objects)
                    selected.state['scope_process'] = ['model']
                    self.assertEqual(selected.get_tasks(), [])
                    with patch('pyasm.biz.ProjectSetting.get_seq_by_key', return_value=['publish', 'review']), \
                            patch('pyasm.biz.ProjectSetting.get_by_key', return_value=None):
                        discussion = DiscussionWdg(setting='fixture_contexts')
                        discussion.set_sobject(target)
                        choices = discussion.get_cell_value()['processes']
                        self.assertEqual({item['process']: item['count'] for item in choices},
                                         {'publish': 1, 'review': 0})
                    with self.assertRaisesRegex(ValueError, 'another type|project'):
                        read_table_cells('contract/l02_parent', 'table', ['sthpw/project?code=admin'])
                    previous = Search.get_by_id('sthpw/note', note['id']).get_value('note')
                    def failing():
                        obj = Search.get_by_id('sthpw/note', note['id'])
                        obj.set_value('note', 'Must roll back')
                        obj.commit()
                        raise ValueError('Late embedded write failure')
                    with self.assertRaisesRegex(ValueError, 'Late embedded'):
                        write(failing)
                    self.assertEqual(Search.get_by_id('sthpw/note', note['id']).get_value('note'), previous)
                    unsupported = DiscussionWdg(include_submission='true')
                    unsupported.set_sobject(target)
                    with self.assertRaisesRegex(UnsupportedContract, 'excluded pyasm.prod'):
                        unsupported.preprocess()
                with request_context(RequestContext(store, login='anonymous', project='admin')):
                    with self.assertRaises(SecurityException):
                        read_table_cells('contract/l02_parent', 'table', keys)
            finally:
                Config.reload_config()


class EmbeddedTableTransport(unittest.TestCase):
    def test_unchanged_handler_procedure_reads_all_four_cells_over_xmlrpc(self):
        import test_transport
        test_transport.Transport.setUpClass()
        self.addCleanup(test_transport.Transport.tearDownClass)
        self.url = test_transport.Transport.url
        proxy = test_transport.Transport.proxy(self)
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
        parent = proxy.insert(auth, 'contract/entity', dict(code='L02_RPC', name='Embedded cells'))
        key = parent['__search_key__']
        proxy.execute_cmd(auth, 'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
                          dict(search_key=key, process='publish', note='RPC note'))
        task = proxy.insert(auth, 'sthpw/task', dict(process='publish', context='publish/detail',
                            status='Pending'), {}, key)
        message = proxy.insert(auth, 'sthpw/message_log', dict(project_code='one', login='admin',
            category='progress', message=json.dumps(dict(message='RPC upload', progress=37))))
        source_path = Path('D:/grav/Tactic Stream/TH/thlib/tactic_query.py')
        text = source_path.read_text(encoding='utf-8-sig')
        function = next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)

        def read(kind, key, elements):
            view = 'l02_embedded'
            xml = f'<config><{view}>{elements}</{view}></config>'
            proxy.insert(auth, 'config/widget_config', dict(search_type=kind, view=view, config=xml))
            code = source + '\nreturn query_table_layout(kwargs["kind"], search_keys=[kwargs["key"]], view="l02_embedded", project_code="one")'
            return json.loads(proxy.execute_python_script(auth, '', dict(code=code, kind=kind, key=key))['info'])

        result = read('contract/entity', key, '''
            <element name="notes"><display class="pyasm.widget.DiscussionWdg"/></element>
            <element name="tasks"><display class="pyasm.widget.SObjectTaskTableElement"><supe>true</supe><bid_edit>false</bid_edit></display></element>''')
        self.assertEqual(result['rows'][key]['notes']['count'], 1)
        task_cell = result['rows'][key]['tasks']
        self.assertFalse(task_cell['error'])
        self.assertEqual(task_cell['tasks'][0]['taskCode'], task['code'])
        self.assertTrue(task_cell['tasks'][0]['editAssigned'])
        self.assertFalse(task_cell['tasks'][0]['editDates'])
        result = read('sthpw/task', task['__search_key__'], '<element name="context"><display class="pyasm.widget.TaskParentSpacingTableElement"/></element>')
        self.assertEqual(result['rows'][task['__search_key__']]['context']['text'], 'publish')
        result = read('sthpw/message_log', message['__search_key__'], '<element name="message"><display class="tactic.ui.app.MessageTableElementWdg"/></element>')
        cell = result['rows'][message['__search_key__']]['message']
        self.assertFalse(cell['error'])
        self.assertEqual((cell['text'], cell['progress']), ('RPC upload', 37))


if __name__ == '__main__':
    unittest.main()
