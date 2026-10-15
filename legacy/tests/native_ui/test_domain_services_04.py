"""Call production services; DB/model collaborators are isolated protocol spies.
These are not end-to-end PostgreSQL/SQLite TACTIC tests.
"""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.ui_api.task_service import TaskService
from tactic.ui_api.relationship_service import RelationshipService
from tactic.ui_api.history_service import HistoryService
from tactic.ui_api.contracts import ApiError, revision
from test_task_form_04 import Obj, Pipeline

class ServiceBase:
 allow_writes=True
 def _project(self):return 'fixture'
 def _serialize(self,obj,spec):return {'key':obj.get_search_key(),'values':obj.get_sobject_dict(),'revision':revision(obj.get_sobject_dict())}
 def _write(self,callback):
  if not self.allow_writes:raise ApiError(403,'read_only','disabled')
  return callback()
 def _object(self,stype,key):
  obj=self.objects.get(key)
  if obj is None or obj.get_base_search_type()!=stype:raise ApiError(403,'scope','wrong object')
  return obj
 def require_type(self,stype):
  if stype not in {'fixture/item','fixture/tag','fixture/item_in_tag','sthpw/login'}:raise ApiError(403,'type','wrong type')
 def view(self,stype,view):return self.spec
 def open_target(self,key):
  if key!='target':raise ApiError(403,'target','wrong target')
  return {'id':'target','kind':'table','search_type':'fixture/item','spec':self.spec}

class Tasks(TaskService,ServiceBase):pass
class Relations(RelationshipService,ServiceBase):pass
class Histories(HistoryService,ServiceBase):pass

class TaskServiceTests(unittest.TestCase):
 def setUp(self):
  self.b=Tasks();self.b.spec={'view':'single_process','fields':[{'name':'status','label':'Status','kind':'select','storage':True,'read_only':False,'options':[{'value':'Open'},{'value':'Closed'}]},{'name':'description','kind':'text','storage':True,'read_only':False}]}
  self.parent=Obj({'code':'ITEM1','pipeline_code':'production'},'fixture/item');self.task=Obj({'id':1,'code':'TASK1','status':'Open','description':'old'},parent=self.parent)
  self.b.objects={o.get_search_key():o for o in (self.parent,self.task)}
  self.b.form=lambda st,key:{'spec':self.b.spec,'record':self.b._serialize(self.task,self.b.spec)}
  self.b.prepare_form=lambda st,key,values:self.b.form(st,key)
  self.search=Mock();self.search.get_sobject.return_value=self.task;self.search.get_sobjects.return_value=[self.task];self.search.get_count.return_value=1
  self.b._task_search=lambda p:self.search
  self.pipeline=Pipeline('production',['model','review']);self.pipeline.get_sobject_dict=lambda:{'code':'production'};self.pipeline.get_process_sobjects=lambda:{'model':Obj({'code':'PROCESS1','process':'model'})}
  self.b._initial_pipeline=lambda p:self.pipeline
  self.data={'target':'target','key':self.parent.get_search_key()}
  self.preview=lambda:self.b.task_operation('GET','/task-generate',dict(self.data))
 def request(self,path='/task-generate',method='POST',**kw):return self.b.task_operation(method,path,{**self.data,**kw})
 def test_generation_preview_reflects_actual_pipeline(self):
  result=self.preview();self.assertEqual(result['pipeline'],'production');self.assertEqual([p['name'] for p in result['processes']],['model','review']);self.assertEqual(result['existing'],1)
 def test_original_generator_receives_validated_selection(self):
  preview=self.preview()
  with patch('pyasm.biz.Task.add_initial_tasks',return_value=[self.task]) as create:
   result=self.request(revision=preview['revision'],processes=['model'],confirm='GENERATE',start_date='2026-09-30')
  create.assert_called_once_with(self.parent,processes=['model'],start_date='2026-09-30',skip_duplicate=True);self.assertEqual(result['keys'],[self.task.get_search_key()])
 def test_default_generation_stays_original_empty_process_branch(self):
  with patch('pyasm.biz.Task.add_initial_tasks',return_value=[]) as create:self.request(revision=self.preview()['revision'],confirm='GENERATE')
  self.assertEqual(create.call_args.kwargs['processes'],[])
 def test_unknown_process_rejected_before_generator(self):
  with patch('pyasm.biz.Task.add_initial_tasks') as create:
   with self.assertRaises(ApiError):self.request(processes=['evil'],confirm='GENERATE')
   create.assert_not_called()
 def test_duplicate_selection_rejected(self):
  with self.assertRaises(ApiError):self.request(processes=['model','model'],confirm='GENERATE')
 def test_date_validation(self):
  for date in ('tomorrow','2026-13-32',1):
   with self.subTest(date=date):
    with self.assertRaises(ApiError):self.request(start_date=date,confirm='GENERATE')
 def test_confirmation_required(self):
  with self.assertRaises(ApiError) as e:self.request(revision=self.preview()['revision'])
  self.assertEqual(e.exception.code,'confirmation')
 def test_stale_task_set_prevents_generation(self):
  old=self.preview()['revision'];self.task.values['description']='changed'
  with patch('pyasm.biz.Task.add_initial_tasks') as create:
   with self.assertRaises(ApiError) as e:self.request(revision=old,confirm='GENERATE')
   create.assert_not_called()
  self.assertEqual(e.exception.status,409)
 def test_process_configuration_in_revision(self):
  old=self.preview()['revision'];self.pipeline.get_process_sobjects=lambda:{'model':Obj({'code':'PROCESS1','process':'model','workflow':'changed'})};self.assertNotEqual(self.preview()['revision'],old)
 def test_change_between_preview_and_command_detected(self):
  original=self.b._generation_state
  self.b._write=lambda callback:(setattr(self.pipeline,'get_sobject_dict',lambda:{'code':'changed'}),callback())[1]
  with patch('pyasm.biz.Task.add_initial_tasks') as create:
   with self.assertRaises(ApiError):self.request(revision=original(self.parent)[2],confirm='GENERATE')
   create.assert_not_called()
 def test_readonly_blocks_generator(self):
  self.b.allow_writes=False
  with patch('pyasm.biz.Task.add_initial_tasks') as create:
   with self.assertRaises(ApiError):self.request(revision=self.preview()['revision'],confirm='GENERATE')
   create.assert_not_called()
 def test_retired_parent_cannot_generate(self):
  self.parent.values['s_status']='retired'
  with self.assertRaises(ApiError):self.preview()
 def test_system_parent_cannot_generate(self):
  self.parent.stype='sthpw/login'
  self.b._task_parent=lambda data:({},self.parent)
  with self.assertRaises(ApiError):self.preview()
 def test_foreign_project_cannot_generate(self):
  self.parent.get_project_code=lambda:'other'
  with self.assertRaises(ApiError):self.preview()
 def test_task_must_belong_to_parent(self):
  self.search.get_sobject.return_value=None
  with self.assertRaises(ApiError) as e:self.request('/task-form','GET',task=self.task.get_search_key())
  self.assertEqual(e.exception.code,'task_scope')
 def test_task_edit_preserves_original_form_view_and_command(self):
  cmd=Mock();cmd.get_sobject.return_value=self.task
  with patch('tactic.core.native_edit.NativeEditCmd',return_value=cmd) as cls:
   self.request('/task-change','PATCH',task=self.task.get_search_key(),revision=revision(self.task.values),values={'status':'Closed'})
  self.assertEqual(cls.call_args.kwargs,{'sobject':self.task,'view':'single_process','data':{'status':'Closed'},'input_prefix':'__NONE__'});cmd.execute.assert_called_once()
 def test_task_edit_rejects_status_outside_original_choices(self):
  with patch('tactic.core.native_edit.NativeEditCmd') as cls:
   with self.assertRaises(ApiError):self.request('/task-change','PATCH',task=self.task.get_search_key(),revision=revision(self.task.values),values={'status':'invented'})
   cls.assert_not_called()
 def test_task_edit_checks_revision(self):
  with patch('tactic.core.native_edit.NativeEditCmd') as cls:
   with self.assertRaises(ApiError) as e:self.request('/task-change','PATCH',task=self.task.get_search_key(),revision='old',values={'status':'Closed'})
   cls.assert_not_called()
  self.assertEqual(e.exception.status,409)
 def test_task_preview_does_not_write(self):
  self.b._write=Mock(side_effect=AssertionError('write'))
  result=self.request('/task-form-preview','POST',task=self.task.get_search_key(),revision=revision(self.task.values),values={'process':'model'});self.assertEqual(result['spec']['view'],'single_process');self.b._write.assert_not_called()
 def test_task_preview_rejects_arbitrary_mutation_fields(self):
  with self.assertRaises(ApiError):self.request('/task-form-preview','POST',task=self.task.get_search_key(),revision=revision(self.task.values),values={'status':'Closed'})

class RelationshipTests(unittest.TestCase):
 def setUp(self):
  self.b=Relations();self.b.spec={'view':'table','fields':[{'name':'name','kind':'text','storage':True}]};self.source=Obj({'code':'ITEM1'},'fixture/item');self.other=Obj({'code':'TAG1','name':'Tag'},'fixture/tag');self.junction=Obj({'code':'LINK1'},'fixture/item_in_tag');self.source_links=[];self.other_links=[]
  self.source.get_instances=lambda st:list(self.source_links);self.other.get_instances=lambda st:list(self.other_links)
  self.source.add_instance=Mock(return_value=self.junction);self.source.remove_instance=Mock();self.other.delete=Mock(side_effect=AssertionError('never delete object'));self.source.delete=Mock(side_effect=AssertionError('never delete source'))
  self.b.objects={o.get_search_key():o for o in (self.source,self.other)}
  self.schema=Mock();self.schema.get_related_search_types.return_value=['fixture/tag'];self.attrs={'relationship':'instance','instance_type':'fixture/item_in_tag'};self.schema.get_relationship_attrs.return_value=self.attrs
  p=patch('pyasm.biz.Schema.get',return_value=self.schema);p.start();self.addCleanup(p.stop)
  self.data={'target':'target','key':self.source.get_search_key(),'related_type':'fixture/tag'}
 def request(self,method='GET',path='/relationship',**kw):return self.b.relationship_operation(method,path,{**self.data,**kw})
 def args(self):return {'revision':self.request()['revision'],'other_key':self.other.get_search_key(),'other_revision':revision(self.other.values)}
 def linked(self):self.source_links[:]=[self.junction];self.other_links[:]=[self.junction]
 def test_descriptor_uses_declared_instance_table(self):
  d=self.request();self.assertEqual(d['instance_type'],'fixture/item_in_tag');self.assertEqual(d['count'],0);self.assertTrue(d['can_write'])
 def test_add_calls_original_sobject_instance(self):
  with patch('pyasm.biz.ExpressionParser.clear_cache') as clear:result=self.request('POST',**self.args())
  self.source.add_instance.assert_called_once_with(self.other);clear.assert_called_once();self.assertFalse(result['direct_object_delete'])
 def test_duplicate_link_is_not_created(self):
  self.linked()
  with self.assertRaises(ApiError) as e:self.request('POST',**self.args())
  self.assertEqual(e.exception.code,'already_linked');self.source.add_instance.assert_not_called()
 def test_unlink_calls_original_remove_only(self):
  self.linked();result=self.request('DELETE',confirm_count=1,**self.args());self.source.remove_instance.assert_called_once_with(self.other);self.other.delete.assert_not_called();self.source.delete.assert_not_called();self.assertEqual(result['unlinked'],1)
 def test_duplicate_junctions_require_exact_count(self):
  self.linked();second=Obj({'code':'LINK2'},'fixture/item_in_tag');self.source_links.append(second);self.other_links.append(second)
  with self.assertRaises(ApiError) as e:self.request('DELETE',confirm_count=1,**self.args())
  self.assertEqual(e.exception.code,'link_count');self.source.remove_instance.assert_not_called();self.assertEqual(self.request('DELETE',confirm_count=2,**self.args())['unlinked'],2)
 def test_membership_revision_changes_block_write(self):
  data=self.args();self.linked()
  with self.assertRaises(ApiError) as e:self.request('POST',**data)
  self.assertEqual(e.exception.status,409);self.source.add_instance.assert_not_called()
 def test_other_revision_checked(self):
  data=self.args();self.other.values['name']='changed'
  with self.assertRaises(ApiError):self.request('POST',**data)
  self.source.add_instance.assert_not_called()
 def test_disabled_schema_not_writable(self):
  self.attrs['disabled']='true'
  with self.assertRaises(ApiError):self.request()
 def test_non_instance_not_invented_as_junction(self):
  self.attrs['relationship']='code'
  with self.assertRaises(ApiError):self.request()
 def test_undeclared_relation_rejected(self):
  self.schema.get_related_search_types.return_value=[]
  with self.assertRaises(ApiError):self.request()
 def test_readonly_disabled(self):
  self.b.allow_writes=False;self.assertFalse(self.request()['can_write'])
  with self.assertRaises(ApiError):self.request('POST',**self.args())
 def test_archived_target_cannot_link(self):
  self.other.values['s_status']='retired'
  with self.assertRaises(ApiError):self.request('POST',**self.args())
 def test_cross_project_target_cannot_link(self):
  self.other.get_project_code=lambda:'other'
  with self.assertRaises(ApiError):self.request('POST',**self.args())
 def test_candidates_batch_original_relation_resolution(self):
  from pyasm.search.database_impl import PostgresImpl
  self.linked();search=Mock();search.get_database_impl.return_value=PostgresImpl();search.get_count.return_value=1;search.get_sobjects.return_value=[self.other];factory=Mock(return_value=search);factory.get_related_by_sobjects.return_value={self.other.get_search_key():[self.junction]}
  with patch('pyasm.search.Search',factory):result=self.request('POST','/relation-candidates',keyword='a.b',limit=30,offset=0)
  factory.get_related_by_sobjects.assert_called_once_with([self.other],'fixture/item_in_tag');search.add_regex_filter.assert_called_once_with('name',r'a\.b',op='EQI');self.assertEqual(result['items'][0]['links'],1)

class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.b=Histories();self.b.spec={'view':'table'};self.obj=Obj({'code':'ITEM1','s_status':None},'fixture/item');self.b.objects={self.obj.get_search_key():self.obj};self.obj.retire=Mock(side_effect=lambda:self.obj.values.update(s_status='retired'));self.obj.reactivate=Mock(side_effect=lambda:self.obj.values.update(s_status=None))
  self.patches=[patch('pyasm.search.SearchType.get',return_value=Mock(get_retire_col=lambda:'s_status')),patch('pyasm.search.SearchType.column_exists',return_value=True)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def request(self,method='GET',path='/record-state',**kw):return self.b.history_operation(method,path,{'target':'target','key':self.obj.get_search_key(),**kw})
 def test_retire_uses_original_model_not_raw_update(self):
  result=self.request('POST',action='retire',confirm='RETIRE',revision=revision(self.obj.values));self.obj.retire.assert_called_once();self.assertTrue(result['retired']);self.assertFalse(result['deleted'])
 def test_reactivate_uses_original_model(self):
  self.obj.values['s_status']='retired';result=self.request('POST',action='reactivate',confirm='REACTIVATE',revision=revision(self.obj.values));self.obj.reactivate.assert_called_once();self.assertFalse(result['retired'])
 def test_confirmation_required(self):
  with self.assertRaises(ApiError):self.request('POST',action='retire',revision=revision(self.obj.values))
  self.obj.retire.assert_not_called()
 def test_stale_revision_rejected(self):
  with self.assertRaises(ApiError) as e:self.request('POST',action='retire',confirm='RETIRE',revision='old')
  self.assertEqual(e.exception.status,409);self.obj.retire.assert_not_called()
 def test_state_conflict_does_not_duplicate_retire_events(self):
  self.obj.values['s_status']='retired'
  with self.assertRaises(ApiError):self.request('POST',action='retire',confirm='RETIRE',revision=revision(self.obj.values))
  self.obj.retire.assert_not_called()
 def test_system_type_not_archived(self):self.assertFalse(self.b._can_retire('sthpw/login'))
 def test_readonly_not_archived(self):
  self.b.allow_writes=False
  with self.assertRaises(ApiError):self.request('POST',action='retire',confirm='RETIRE',revision=revision(self.obj.values))
 def test_history_rejects_arbitrary_table(self):
  with self.assertRaises(ApiError):self.request('GET','/history',source='sthpw/ticket')
 def test_changes_use_parent_relationship_and_allowlisted_fields(self):
  log=Obj({'code':'LOG1','login':'alice','timestamp':'today','action':'update','transaction_log_id':1,'password':'secret'},'sthpw/sobject_log');search=Mock();search.get_sobjects.return_value=[log];search.get_count.return_value=1
  with patch('pyasm.search.Search',return_value=search) as cls:result=self.request('GET','/history',source='changes')
  cls.assert_called_once_with('sthpw/sobject_log');search.add_relationship_filter.assert_called_once_with(self.obj);self.assertNotIn('password',result['items'][0])
 def test_retire_log_without_identifier_fails_closed(self):
  with patch('pyasm.search.Search',return_value=Mock()),patch('pyasm.search.SearchType.column_exists',return_value=False):
   with self.assertRaises(ApiError) as e:self.request('GET','/history',source='retire')
  self.assertEqual(e.exception.code,'history_schema')
 def test_non_task_status_log_not_fabricated(self):self.assertEqual(self.request('GET','/history',source='status')['items'],[])

if __name__=='__main__':unittest.main()
