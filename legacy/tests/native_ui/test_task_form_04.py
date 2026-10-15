"""Real task-conf.xml and production provider code; only DB collaborators mocked."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.core.config_model import ConfigModel, ConfigSource
from tactic.ui_api.extended_backend import ExtendedBackend
from tactic.ui_api.contracts import ApiError, revision, clean_values

class Obj:
 def __init__(self,values,stype='sthpw/task',parent=None):self.values=values;self.stype=stype;self.parent=parent
 def get_value(self,name,*a,**kw):return self.values.get(name,'')
 def get_code(self):return self.values.get('code','')
 def get_id(self):return self.values.get('id',1)
 def get_search_key(self):return self.stype+'?code='+self.get_code()
 def get_base_search_type(self):return self.stype
 def get_search_type(self):return self.stype+'?project=fixture'
 def get_project_code(self):return 'fixture'
 def get_sobject_dict(self):return dict(self.values)
 def get_parent(self):return self.parent
 def has_value(self,name):return name in self.values
 def get_pipeline(self):
  from pyasm.biz import Pipeline
  return Pipeline.get_by_code(self.values.get('pipeline_code') or 'task')
 def is_retired(self):return self.values.get('s_status')=='retired'

class Pipeline:
 def __init__(self,code,names):self.code=code;self.names=names;self.attrs={}
 def get_code(self):return self.code
 def get_process_names(self):return list(self.names)
 def get_processes(self,*a,**kw):return [Mock(get_name=lambda n=n:n,get_color=lambda:'#888888',is_from_sub_pipeline=lambda:False,get_type=lambda:'manual') for n in self.names]
 def get_output_contexts(self,name):return [name,name+'/review']
 def get_process_attrs(self,name):return self.attrs.get(name,{})

class TaskFormTests(unittest.TestCase):
 def setUp(self):
  self.backend=ExtendedBackend({'allow_writes':True})
  self.backend._project=lambda:'fixture';self.backend.require_type=lambda st:None
  self.raw=(R/'src/config2/search_type/widget/sthpw/task-conf.xml').read_text()
  self.parent=Obj({'code':'ITEM1','pipeline_code':'production'},'fixture/item')
  self.obj=Obj({'id':1,'code':'TASK1','project_code':'fixture','process':'model','context':'model/review','pipeline_code':'task','status':'Open','assigned':'alice','supervisor':'bob','milestone_code':'MS1','description':'Work','bid_start_date':'2026-09-01','bid_end_date':'2026-09-03'},parent=self.parent)
  self.original=copy.deepcopy(self.obj.values)
  self.backend._object=lambda st,key:self.obj
  self.model=lambda st,view:ConfigModel(view,[ConfigSource(self.raw,view,'original task-conf.xml'),ConfigSource(self.raw,'edit_definition' if view in ('edit','insert','single_process') else 'definition','original definitions'),ConfigSource(self.raw,'definition','original definition')])
  self.backend._model=self.model
  self.backend._edit_base_model=lambda st,view,mode:self.model(st,view)  # custom-view DB/file collaborator; production precedence has separate tests
  self.backend._column_config_sources=lambda: []  # isolated DB collaborator, no global custom columns in this fixture
  self.columns={n:{'data_type':'varchar'} for n in ['id','code','search_code','project_code','process','context','description','milestone_code','assigned','supervisor','bid_start_date','bid_end_date','bid_duration','actual_duration','actual_quantity','priority','pipeline_code','status']}
  self.columns['bid_duration']['data_type']='integer'
  self.columns['bid_start_date']['data_type']='timestamp';self.columns['bid_end_date']['data_type']='timestamp'
  self.backend._stub=lambda:Mock(get_column_info=lambda st:self.columns)
  self.pipeline=Pipeline('task',['Open','Waiting','Closed']);self.other=Pipeline('alternate',['Todo','Done']);self.production=Pipeline('production',['model','review'])
  self.production.attrs={'model':{'assigned_login_group':'modelers'},'review':{'assigned_login_group':'reviewers'}}
  self.searches=[]
  outer=self
  class Search:
   def __init__(self,stype):self.stype=stype;self.filters=[];self.ops=[];self.order=[];self.limit=None;outer.searches.append(self)
   def add_filter(self,name,value,**kw):self.filters.append((name,value,kw))
   def add_filters(self,name,values,**kw):self.filters.append((name,list(values),kw))
   def add_op(self,op):self.ops.append(op)
   def add_order_by(self,col,**kw):self.order.append(col)
   def set_limit(self,n):self.limit=n
   def get_sobjects(self):
    if self.stype=='sthpw/login_in_group':return [Obj({'login':'alice' if self.filters[0][1]=='modelers' else 'bob'})]
    if self.stype=='sthpw/login':
     users=[Obj({'login':'alice','display_name':'Alice','first_name':'Alice','last_name':'Example'}),Obj({'login':'bob','display_name':'Bob','first_name':'Bob','last_name':'Example'})]
     for name,value,_ in self.filters:
      if name=='login':users=[u for u in users if u.get_value('login') in value]
     return users
    if self.stype=='sthpw/pipeline':return [Obj({'code':'task'}),Obj({'code':'alternate'})]
    if self.stype=='sthpw/milestone':return [Obj({'code':'MS1'})]
    return []
  self.patches=[patch('pyasm.search.Search',Search),patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in self.columns),patch('pyasm.common.Environment.get_security',return_value=Mock(check_access=lambda *a,**kw:True,is_admin=lambda:True)),patch('pyasm.biz.Pipeline.get_by_code',side_effect=lambda c:{'task':self.pipeline,'alternate':self.other,'production':self.production}.get(c)),patch('pyasm.biz.Pipeline.get_by_sobject',return_value=self.production)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def form(self,**kwargs):return self.backend.form('sthpw/task',self.obj.get_search_key(),**kwargs)
 def fields(self,form=None):return {f['name']:f for f in (form or self.form())['spec']['fields']}
 def values(self,field,form=None):return [o['value'] for o in self.fields(form)[field]['options']]
 def test_original_edit_names_are_preserved(self):self.assertEqual([f['name'] for f in self.form()['spec']['fields']],self.model('sthpw/task','edit').names())
 def test_original_status_select_is_writable(self):
  f=self.fields()['status'];self.assertEqual(f['handler'],'tactic.ui.widget.TaskStatusSelectWdg');self.assertFalse(f['read_only']);self.assertEqual(self.values('status'),['','Open','Waiting','Closed'])
 def test_original_process_and_context_choices(self):self.assertEqual(self.values('process'),['','model','review']);self.assertEqual(self.values('context'),['','model','model/review','review','review/review'])
 def test_virtual_subcontext_uses_original_action(self):
  form=self.form();f=self.fields(form)['subcontext'];self.assertFalse(f['storage']);self.assertFalse(f['read_only']);self.assertEqual(form['record']['values']['subcontext'],'review');self.assertEqual(f['action'],'tactic.ui.input.SubContextAction')
 def test_date_retains_original_action(self):self.assertEqual(self.fields()['bid_end_date']['action'],'TaskDateAction');self.assertFalse(self.fields()['bid_end_date']['read_only']);self.assertEqual(self.fields()['bid_start_date']['action'],'')
 def test_original_group_scope_for_assigned(self):self.assertEqual(self.values('assigned'),['','alice']);self.assertEqual(self.values('supervisor'),['','alice','bob'])
 def test_two_exact_stock_lookup_expressions(self):
  self.assertEqual(self.values('pipeline_code'),['','task','alternate']);self.assertEqual(self.values('milestone_code'),['','MS1']);q=next(q for q in self.searches if q.stype=='sthpw/pipeline');self.assertEqual(q.ops,['begin','or']);self.assertIn(('project_code',None,{}),q.filters);self.assertIn(('project_code','fixture',{}),q.filters);self.assertIn(('search_type','sthpw/task',{}),q.filters)
 def test_unknown_values_expression_is_not_free_text(self):
  self.raw=self.raw.replace("@GET(sthpw/milestone['project_code',$PROJECT]['project_code','is','NULL']['or'].code)",'@GET(sthpw/login.login)');self.assertTrue(self.fields()['milestone_code']['read_only'])
 def test_preview_new_pipeline_recomputes_choices_without_writes(self):
  base=self.form();new=self.form(choice_overrides={'pipeline_code':'alternate'});self.assertEqual(self.values('status',new),['','Todo','Done']);self.assertEqual(new['record']['revision'],base['record']['revision']);self.assertEqual(self.obj.values,self.original)
 def test_preview_new_process_recomputes_login_group(self):
  new=self.form(choice_overrides={'process':'review'});self.assertEqual(self.values('assigned',new),['','bob']);self.assertEqual(self.obj.values,self.original)
 def test_pipeline_change_requires_new_valid_status(self):
  new=self.backend.prepare_form('sthpw/task',self.obj.get_search_key(),{'pipeline_code':'alternate'});self.assertIn('dependency_notice',new)
  new=self.backend.prepare_form('sthpw/task',self.obj.get_search_key(),{'pipeline_code':'alternate','status':'Todo'});self.assertNotIn('dependency_notice',new)
  with self.assertRaises(ApiError):self.backend.prepare_form('sthpw/task',self.obj.get_search_key(),{'pipeline_code':'alternate','status':'Open'})
 def test_invalid_pipeline_not_accepted_by_preview(self):
  with self.assertRaises(ApiError):self.backend.prepare_form('sthpw/task',self.obj.get_search_key(),{'pipeline_code':'arbitrary'})
 def test_invalid_new_group_assignee_rejected(self):
  new=self.backend.prepare_form('sthpw/task',self.obj.get_search_key(),{'process':'review','assigned':'alice'})
  with self.assertRaises(ApiError):clean_values({'assigned':'alice'},new['spec']['fields'])
 def test_readonly_source_option_not_overridden(self):
  self.raw=self.raw.replace('<display class="tactic.ui.widget.TaskStatusSelectWdg">','<display class="tactic.ui.widget.TaskStatusSelectWdg"><read_only>true</read_only>');self.assertTrue(self.fields()['status']['read_only'])
 def test_active_custom_edit_view_preserved(self):
  self.backend.active_target={'search_type':'sthpw/task','options':{'edit_view':'single_process'}};self.assertEqual(self.form()['spec']['view'],'single_process')
 def test_write_disabled_keeps_all_fields_readonly(self):
  self.backend.allow_writes=False;self.assertTrue(all(f['read_only'] for f in self.form()['spec']['fields']))
 def test_parent_virtual_field_not_claimed_supported(self):self.assertFalse(self.fields()['parent']['supported']);self.assertTrue(self.fields()['parent']['read_only'])
 def test_original_my_task_work_hours_column_is_native(self):
  fields={f['name']:f for f in self.backend.view('sthpw/task','my_task')['fields']}
  self.assertEqual(fields['work_hours']['renderer'],'work-hours');self.assertTrue(fields['work_hours']['supported']);self.assertFalse(fields['work_hours']['storage']);self.assertTrue(fields['work_hours']['read_only'])
 def test_preview_endpoint_rejects_wrong_revision(self):
  self.backend.open_target=lambda key:{'kind':'table','search_type':'sthpw/task'}
  with self.assertRaises(ApiError) as caught:self.backend.form_preview({'target':'task','key':self.obj.get_search_key(),'revision':'wrong','values':{'process':'review'}})
  self.assertEqual(caught.exception.status,409)

if __name__=='__main__':unittest.main()
