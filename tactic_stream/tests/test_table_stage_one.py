"""Stage 1 task cells and real stored CG layouts use actual temporary TACTIC data."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import test_table_services as services_fixture
from test_table_embedded_widgets import write
from pyasm.biz import Pipeline, Task
from pyasm.common import SecurityException
from pyasm.search import Search
from pyasm.widget.parallel_status import ParallelStatusWdg, ParallelStatusEditWdg
from tactic.ui.table.subcontext_wdg import ProcessElementWdg
from tactic.ui.widget.misc_input_wdg import TaskStatusElementWdg
from tactic.ui.table.task_element_wdg import WorkElementWdg
from tactic.ui.table.sobject_detail_wdg import SObjectTaskStatusElementWdg
from tactic.ui.table.custom_layout_element_wdg import read_custom_layout
from tactic.ui.table.service_documents import read_group_summary
from tactic_stream.server.table_cells import describe_cell, read_table_cells

ROOT=Path(__file__).resolve().parents[2]

class StageOneCells(unittest.TestCase):
    setUp=services_fixture.TableServices.setUp

    def configure_tasks(self):
        with self.store.connection('one',write=True) as database:
            database.execute('ALTER TABLE entity ADD COLUMN pipeline_code text')
            database.execute("UPDATE entity SET pipeline_code='PARALLEL' WHERE code='A'")
        def create():
            Pipeline.create('Statuses','','sthpw/task','<pipeline><process name="Ready" color="#ff0000"/><process name="Working" color="#aabbcc"/><process name="Done"/></pipeline>',code='STATUSES')
            Pipeline.create('Parallel','','contract/entity','<pipeline><process name="model"/><process name="rig"/></pipeline>',code='PARALLEL')
            parent=Search.get_by_code('contract/entity','A')
            return [Task.create(parent,'model',assigned='admin',status=status,pipeline_code='STATUSES',triggers=False,
                end_date='2000-01-01' if status=='Working' else None) for status in ('Ready','Working','Done')]
        return Search.get_by_code('contract/entity','A'),write(create)

    def test_parallel_process_status_and_work_project_real_tasks(self):
        parent,tasks=self.configure_tasks()
        widget=ParallelStatusWdg(name='parallel',bar_height='3',label_format='abbr')
        widget.set_sobjects([parent]);widget.preprocess();widget.set_current_index(0)
        cell=widget.get_cell_value()
        self.assertEqual([group['process'] for group in cell['groups']],['PARALLEL/model','PARALLEL/rig'])
        self.assertEqual([bar['percent'] for bar in cell['groups'][0]['bars']],[33,66,100])
        self.assertEqual(cell['groups'][0]['bars'][1]['color'],'#f00')
        self.assertEqual(cell['groups'][0]['completion'],199/3)
        self.assertEqual(cell['groups'][0]['label'],'mod')
        self.assertEqual(cell['steps'],3)
        self.assertEqual(cell['barHeight'],3)
        process=ProcessElementWdg(name='process');process.set_sobject(tasks[0])
        self.assertEqual(process.get_cell_value(),dict(text='model',parentPipeline='PARALLEL'))
        status=TaskStatusElementWdg(name='status');status.set_sobject(tasks[1])
        self.assertEqual(status.get_cell_value()['statusColor'],'#aabbcc')
        self.assertEqual(status.get_cell_value()['statusPipeline'],'STATUSES')
        for cls,action in ((ParallelStatusEditWdg,'add-task'),(SObjectTaskStatusElementWdg,'task-details'),(WorkElementWdg,'work')):
            widget=cls();widget.set_sobject(tasks[0] if cls is not ParallelStatusEditWdg else parent)
            value=widget.get_cell_value()
            self.assertEqual(value['targetSearchKey'],parent.get_search_key())
            self.assertEqual(value['actions'][0]['name'],action)
        work=WorkElementWdg(transfer_mode='upload');work.set_sobject(tasks[0])
        self.assertEqual(work.get_cell_value()['taskCode'],tasks[0].get_code())
        self.assertEqual(work.get_cell_value()['process'],'model')
        widget=ParallelStatusWdg(bar_height='0');widget.set_sobjects([parent]);widget.preprocess();widget.set_current_index(0)
        with self.assertRaisesRegex(ValueError,'between 1 and 32'):widget.get_cell_value()

    def test_status_assigned_scope_is_enforced_before_form_mutation(self):
        _,tasks=self.configure_tasks()
        widget=TaskStatusElementWdg(name='status',edit_scope='assigned');widget.set_sobject(tasks[0])
        with patch('tactic.ui.widget.misc_input_wdg.Environment.get_security',return_value=SimpleNamespace(is_admin=lambda:False)),patch('tactic.ui.widget.misc_input_wdg.Environment.get_user_name',return_value='artist'):
            with self.assertRaises(SecurityException):widget.assert_editable()
        with patch('tactic.ui.widget.misc_input_wdg.Environment.get_security',return_value=SimpleNamespace(is_admin=lambda:False)),patch('tactic.ui.widget.misc_input_wdg.Environment.get_user_name',return_value='admin'):
            widget.assert_editable()

    def load_cg_layout(self,view):
        source=(ROOT/'cg/config_widget_config.spt').read_text(encoding='utf-8')
        for block in source.split('#-- Start Entry --#'):
            if not block.strip():continue
            values={}
            for node in ast.parse(block).body:
                if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='set_value':
                    values[ast.literal_eval(node.value.args[0])]=ast.literal_eval(node.value.args[1])
            if values.get('view')==view and values.get('category')=='CustomLayoutWdg':
                with self.store.connection('one',write=True) as database:
                    database.execute('INSERT INTO spt_widget_config(code,category,view,config) VALUES(?,?,?,?)',(values['code'],values['category'],view,values['config']))
                return
        self.fail('CG layout not found: '+view)

    def test_cg_slash_view_resolves_dotted_definition_and_keeps_edit_link_action(self):
        self.load_cg_layout('episodes.columns.script')
        with self.store.connection('one',write=True) as database:
            database.execute('ALTER TABLE entity ADD COLUMN script text')
            database.execute("UPDATE entity SET script='https://docs.google.com/document/d/fixture/edit#heading' WHERE code='A'")
        key=Search.get_by_code('contract/entity','A').get_search_key()
        cell=read_custom_layout(key,'episodes/columns/script')
        self.assertEqual(cell['layoutView'],'episodes.columns.script')
        self.assertTrue(any(node['kind']=='link' and node['href'].startswith('https://docs.google.com/') for node in cell['layoutNodes']))
        edit=next(node for node in cell['layoutNodes'] if node['kind']=='action')
        self.assertIn('tactic.ui.panel.EditWdg',edit['javascript'])
        self.assertIn('bvr.kwargs.search_key',edit['javascript'])
        self.assertTrue(any(node.get('translate') for node in cell['layoutNodes']))
        with self.store.connection('one',write=True) as database:database.execute("UPDATE entity SET script='' WHERE code='A'")
        empty=read_custom_layout(key,'episodes/columns/script')
        self.assertFalse(any(node.get('href','').startswith('http') for node in empty['layoutNodes']))
        self.assertTrue(any(node['kind']=='action' for node in empty['layoutNodes']))
        with self.assertRaisesRegex(ValueError,'not configured'):read_custom_layout(key,'missing/layout')

    def test_summary_lists_actual_group_rules_and_rejects_non_login_target(self):
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES('crew','crew','<rules/>')")
            database.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('crew-admin','admin','crew')")
        user=Search.get_by_code('sthpw/login','admin')
        model=read_group_summary(user.get_search_key())
        section=next(item for item in model['sections'] if item['title']=='crew')
        self.assertEqual(section['text'],'<rules/>')
        self.assertNotIn('password',str(model))
        with self.assertRaises(ValueError):read_group_summary(Search.get_by_code('contract/entity','A').get_search_key())


    def test_configured_edit_ignore_hides_only_requested_fields(self):
        from tactic_stream.server.interface import read_form
        key=Search.get_by_code('contract/entity','A').get_search_key()
        complete=read_form('contract/entity','edit',key)
        self.assertIn('name',[field['name'] for field in complete['fields']])
        reduced=read_form('contract/entity','edit',key,ignore=['name'])
        self.assertEqual([field['name'] for field in reduced['fields']],
                         [field['name'] for field in complete['fields'] if field['name']!='name'])
        with self.assertRaisesRegex(ValueError,'ignored form fields'):
            read_form('contract/entity','edit',key,ignore={'name':True})

    def test_table_retire_and_reactivate_use_original_revision_without_retry(self):
        from pyasm.widget.table_element_wdg import UpdateWdg
        from tactic.ui.table.record_actions import TableObjectStatusCmd
        obj=Search.get_by_code('contract/entity','A')
        widget=UpdateWdg();widget.set_sobject(obj)
        revision=widget.get_cell_value()['expectedRevision']
        write(lambda:TableObjectStatusCmd(search_key=obj.get_search_key(),action='retire',expected_revision=revision).execute())
        current=Search.get_by_search_key(obj.get_search_key())
        self.assertEqual(current.get_value('s_status'),'retired')
        with self.assertRaisesRegex(ValueError,'changed'):
            write(lambda:TableObjectStatusCmd(search_key=obj.get_search_key(),action='reactivate',expected_revision=revision).execute())
        widget.set_sobject(current)
        write(lambda:TableObjectStatusCmd(search_key=obj.get_search_key(),action='reactivate',expected_revision=widget.get_cell_value()['expectedRevision']).execute())
        self.assertNotEqual(Search.get_by_search_key(obj.get_search_key()).get_value('s_status'),'retired')

    def test_layout_reads_reject_writes_imports_private_objects_and_io(self):
        key=Search.get_by_code('contract/entity','A').get_search_key()
        for code in ('from pyasm.search import Search',"search('contract/entity').get_sobject().delete()",
                     "open('should-not-exist','w')",'x=sobject.__class__',"sobject['code']='changed'",'str=search.get_by_search_key',
                     'if False: context=0',"x=context.get('open')",'str=sobject.get'):
            with self.subTest(code=code),self.assertRaisesRegex(ValueError,'data-only Mako'):
                read_custom_layout(key,html='<% '+code+' %>text')
        self.assertEqual(Search.get_by_search_key(key).get_value('code'),'A')
