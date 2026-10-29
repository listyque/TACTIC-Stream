"""L07a uses native records and commands, with revisions and current-user scope."""

import ast
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_foundation import fixture, LEGACY
from test_table_embedded_widgets import write
from pyasm.biz import PrefSetting
from pyasm.command import Trigger
from pyasm.common import Config
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from pyasm.widget.table_element_wdg import UpdateWdg
from tactic.command.notification_cmd import NotificationTestCmd
from tactic.ui.table.preference_wdg import PreferenceEditWdg, SetPreferenceCmd
from tactic_stream.server.api import Api
from tactic_stream.server.table_cells import describe_cell, read_table_cells
from tactic_stream.server.interface import read_interface


class TableServices(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {'TACTIC_CONFIG_PATH':'', 'TACTIC_TMP_CONFIG_PATH':''}))
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(directory) / 'data')
        self.store.initialize(hash_password('service-cell-fixture'))
        fixture(self.store)
        self.api = Api(self.store)
        ticket = self.api.get_ticket('admin','service-cell-fixture')
        self.enterContext(request_context(RequestContext(self.store, login='admin', project='one')))
        self.api.auth.bind_security('admin', ticket)

    def test_all_service_aliases_have_typed_projection_and_reject_unknown_options(self):
        names = ['MyTacticSummaryWdg','UpdateWdg','tactic.ui.input.LoginTableElementWdg',
                 'tactic.ui.panel.SecurityManagerButtonWdg','tactic.ui.table.PreferenceEditWdg',
                 'tactic.ui.table.ProjectTemplateUpdateWdg','tactic.ui.table.NotificationTriggerElementWdg']
        for handler in names:
            with self.subTest(handler=handler):
                element = dict(name='value',display=dict(handler=handler,options={}),action=dict(handler='',options={}))
                descriptor = describe_cell(element,{})
                self.assertTrue(descriptor['supported'])
                self.assertTrue(descriptor['server'])
                element['display']['options']['not_a_real_option']='true'
                self.assertFalse(describe_cell(element,{})['supported'])

    def test_stock_task_edit_flag_does_not_disable_real_task_cells(self):
        from pathlib import Path
        from xml.etree import ElementTree as ET
        from tactic_stream.server.interface import describe_view
        from pyasm.widget import WidgetConfig, WidgetConfigView
        source = Path(__file__).resolve().parents[1] / 'src/tactic_stream/config/search_type/widget/prod/DEFAULT-conf.xml'
        definition = ET.fromstring(source.read_text(encoding='utf-8')).find('default_definition')
        names = ('task_pipeline_panels', 'task_pipeline_vertical', 'task_pipeline_report', 'task_status_edit')
        root = ET.Element('config')
        node = ET.SubElement(root, 'definition')
        for name in names:
            node.append(definition.find("element[@name='%s']" % name))
        xml = ET.tostring(root, encoding='unicode')
        config = WidgetConfig.get(view='definition', xml=xml, use_cache=False)
        elements = describe_view(WidgetConfigView('contract/entity', 'definition', [config]))['elements']
        for element in elements:
            self.assertTrue(describe_cell(element, {})['supported'], element['name'])
            invalid = dict(element, display=dict(element['display'], options=dict(element['display']['options'], edit='arbitrary')))
            self.assertFalse(describe_cell(invalid, {})['supported'])
            unknown = dict(element, display=dict(element['display'], options=dict(element['display']['options'], unknown_task_option='true')))
            self.assertFalse(describe_cell(unknown, {})['supported'])
        def configure():
            for view, content in [('definition', xml), ('table', '<config><table>' + ''.join('<element name="%s"/>' % name for name in names) + '</table></config>')]:
                row = SearchType.create('config/widget_config')
                row.set_value('search_type', 'contract/entity')
                row.set_value('view', view)
                row.set_value('config', content)
                row.commit()
            return Task.create(Search.get_by_code('contract/entity', 'A'), 'model', triggers=False)
        from pyasm.biz import Task
        task = write(configure)
        parent = Search.get_by_code('contract/entity', 'A')
        cells = read_table_cells('contract/entity', 'table', [parent.get_search_key()])[parent.get_search_key()]
        for name in names:
            self.assertNotIn('error', cells[name])
            self.assertEqual(cells[name]['tasks'][0]['taskCode'], task.get_code())

    def test_standard_database_action_keeps_expression_readable_and_checks_target(self):
        element = dict(name='alias', display=dict(handler='tactic.ui.table.ExpressionElementWdg',
            options=dict(expression='@GET(contract/entity.name)')),
            action=dict(handler='pyasm.command.DatabaseAction', options=dict(column='name')))
        columns = SearchType.get_column_info('contract/entity')
        self.assertTrue(describe_cell(element, columns)['supported'])
        for action in (dict(handler='untrusted.CustomAction', options=dict(column='name')),
                       dict(handler='pyasm.command.DatabaseAction', options=dict(column='missing')),
                       dict(handler='pyasm.command.DatabaseAction', options=dict(column='name', script='anything'))):
            self.assertFalse(describe_cell(dict(element, action=action), columns)['supported'])

    def test_summary_counts_current_login_and_project_using_actual_timestamp_storage(self):
        from pyasm.widget.my_tactic_summary_wdg import MyTacticSummaryWdg
        with self.store.connection(write=True) as db:
            db.executemany('INSERT INTO notification_login(login,project_code,type) VALUES (?,?,?)',
                           [('admin','one','email'),('someone','one','email'),('admin','two','email')])
        widget = MyTacticSummaryWdg()
        widget.set_sobject(Search.get_by_code('sthpw/project','one'))
        entries = widget.get_cell_value()['entries']
        received = [row for row in entries if row['title']=='Notifications received']
        self.assertEqual([row['value'] for row in received],['1','1','1'])
        cells = read_table_cells('sthpw/project','mytactic',[widget.get_current_sobject().get_search_key()])
        self.assertNotIn('error',next(iter(cells.values()))['summary'])

    def test_preference_view_uses_current_user_value_not_the_preference_definition(self):
        with self.store.connection(write=True) as db:
            db.execute('INSERT INTO pref_list(code,"key",title,type,options) VALUES (?,?,?,?,?)',
                       ('QUALITY','fixture_quality','Quality','sequence','draft|final'))
        obj = Search('sthpw/pref_list').get_sobject()
        widget = PreferenceEditWdg(name='value')
        widget.set_sobject(obj)
        cell = widget.get_cell_value()
        self.assertEqual(cell['text'],'')
        self.assertEqual([item['value'] for item in cell['preferenceOptions']],['draft','final'])
        self.assertEqual(cell['preferenceKey'],'fixture_quality')
        write(lambda: SetPreferenceCmd(key='fixture_quality',value='final',expected_revision=cell['expectedRevision']).execute())
        self.assertEqual(widget.get_cell_value()['text'],'final')
        with self.assertRaisesRegex(ValueError,'changed'):
            write(lambda: SetPreferenceCmd(key='fixture_quality',value='draft',expected_revision=cell['expectedRevision']).execute())
        self.assertEqual(write(lambda: SetPreferenceCmd(key='fixture_quality',value='final',action='check').execute())['state'],'saved')
        fresh = widget.get_cell_value()
        write(lambda: SetPreferenceCmd(key='fixture_quality',value='',expected_revision=fresh['expectedRevision']).execute())
        self.assertEqual(PrefSetting.get_value_by_key('fixture_quality'),'')
        definition = read_interface('sthpw/pref_list','user')
        value = next(item for item in definition['table']['elements'] if item['name']=='value')
        self.assertTrue(value['cell']['supported'])
        projected = read_table_cells('sthpw/pref_list','user',[obj.get_search_key()])
        self.assertEqual(projected[obj.get_search_key()]['value']['preferenceKey'],'fixture_quality')

    def test_update_keeps_flags_custom_edit_view_and_retired_state(self):
        obj = Search.get_by_code('contract/entity','A')
        if obj is None:
            obj = SearchType.create('contract/entity')
            obj.set_value('code','SERVICE_ROW')
            write(obj.commit)
        widget = UpdateWdg(name='update',delete='true',edit_view='edit_service')
        widget.set_sobject(obj)
        cell = widget.get_cell_value()
        self.assertEqual([action['name'] for action in cell['actions']],['edit','retire','delete'])
        self.assertEqual(cell['actions'][0]['view'],'edit_service')
        self.assertTrue(cell['expectedRevision'])
        widget.set_option('edit','false')
        widget.set_option('retire','false')
        self.assertEqual([action['name'] for action in widget.get_cell_value()['actions']],['delete'])
        write(obj.retire)
        widget.set_option('retire','true')
        self.assertEqual(widget.get_cell_value()['actions'][0]['name'],'reactivate')
        write(obj.reactivate)

    def test_notification_test_matches_original_event_and_does_not_save_dummy_object(self):
        text = (LEGACY/'src/tactic/command/notification_cmd.py').read_text(encoding='utf-8')
        cls = next(node for node in ast.parse(text).body if isinstance(node,ast.ClassDef) and node.name=='NotificationTestCmd')
        method = next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='execute')
        from pyasm.common import Environment, TacticException
        from pyasm.biz import Project
        from pyasm.search import SearchKey
        namespace = dict(Environment=Environment,TacticException=TacticException,Project=Project,
                         SearchKey=SearchKey,SearchType=SearchType,Trigger=Trigger)
        exec(compile(ast.Module(body=[method],type_ignores=[]),'original-notification-test','exec'),namespace)
        data = {'__search_key__':'sthpw/notification?id=1','id':1,'event':'update|contract/entity','process':''}
        count = Search('contract/entity').get_count()
        outputs = []
        def called(obj,event,**options):
            outputs.append((obj.get_data().copy(),event,options))
            return [SimpleNamespace(get_description=lambda:'Fixture notification handler')]
        with patch.object(Trigger,'call',side_effect=called):
            command = NotificationTestCmd(sobject_dict=data)
            namespace['execute'](command)
            modern = NotificationTestCmd(sobject_dict=data)
            write(modern.execute)
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(Search('contract/entity').get_count(),count)
        self.assertIn('Fixture notification handler',modern.get_description())
        with patch.object(Trigger,'call',return_value=[]):
            with self.assertRaisesRegex(TacticException,'No notification trigger'):
                write(lambda: NotificationTestCmd(sobject_dict=data).execute())
