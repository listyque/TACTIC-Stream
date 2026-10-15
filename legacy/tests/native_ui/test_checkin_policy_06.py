"""Source-declared check-in customizations are not silently bypassed."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from tactic.core.checkin_policy import checkin_constraints
from tactic.ui_api.upload_service import UploadService
from tactic.ui_api.contracts import ApiError

class Query:
 def __init__(self,rows):self.rows=rows;self.filters=[];self.limit=None
 def add_filter(self,k,v):self.filters.append((k,v))
 def add_filters(self,k,v):self.filters.append((k,v))
 def set_limit(self,n):self.limit=n
 def get_sobjects(self):return self.rows[:self.limit]
def row(**values):return SimpleNamespace(get_value=lambda name,**kw:values.get(name))

class PolicyTests(unittest.TestCase):
 def resolve(self,options=None,callbacks=None,process=None,pipeline=None):
  q=Query([row(**x) for x in (callbacks or [])]);p=Query([row(**x) for x in (process or [])]);self.queries=[]
  def query(stype,**kw):self.queries.append((stype,kw));return q if stype=='config/client_trigger' else p
  with patch('tactic.core.checkin_policy.Search',query),patch('tactic.core.checkin_policy.Pipeline') as pl:
   pl.get_by_code.return_value=row(project_code='library') if pipeline!='missing' else None
   result=checkin_constraints('fixture/item','publish',pipeline,options or {})
  self.q,self.p=q,p;return result
 def test_plain_original_file_checkin_allowed(self):self.assertEqual(self.resolve(),[])
 def test_explicit_default_class_allowed(self):self.assertEqual(self.resolve({'checkin_cls':'pyasm.checkin.FileCheckin','checkin_type':'strict'}),[])
 def test_each_custom_widget_option_blocked(self):
  for name in ('validate_script_path','checkin_script_path','checkin_script','checkin_options_view','checkin_cls','checkin_type','snapshot_type','file_type'):
   with self.subTest(name=name):self.assertIn('widget:'+name,self.resolve({name:'custom'}))
 def test_revision_is_not_silently_changed_to_new_version(self):self.assertIn('widget:revision/level',self.resolve({'is_revision':True}))
 def test_level_is_not_silently_ignored(self):self.assertIn('widget:revision/level',self.resolve({'level_key':'level'}))
 def test_original_client_event_names_are_used(self):
  self.resolve();self.assertEqual(set(self.q.filters[0][1]),{'CheckinWdg|validate_script_path|fixture/item','CheckinWdg|validate_script_path|fixture/item|publish','CheckinWdg|checkin_script_path|fixture/item','CheckinWdg|checkin_script_path|fixture/item|publish'})
 def test_custom_client_callback_is_not_executed(self):self.assertIn('client_trigger:checkin/validation',self.resolve(callbacks=[{'callback':'dangerous_script()'}]))
 def test_empty_callback_is_no_override(self):self.assertEqual(self.resolve(callbacks=[{'callback':''}]),[])
 def test_excessive_callbacks_fail_closed(self):self.assertIn('client_trigger:too_many',self.resolve(callbacks=[{'callback':''}]*1001))
 def test_original_pipeline_project_selects_process_config(self):
  self.resolve(pipeline='p');self.assertEqual(self.queries[-1],('config/process',{'project_code':'library'}));self.assertEqual(self.p.filters,[('pipeline_code','p'),('process','publish')])
 def test_process_validation_script_is_detected(self):self.assertIn('process:checkin_validate_script_path',self.resolve(pipeline='p',process=[{'checkin_validate_script_path':'validate'}]))
 def test_custom_option_panel_is_detected(self):self.assertIn('process:checkin_options_view',self.resolve(pipeline='p',process=[{'checkin_options_view':'custom'}]))
 def test_repo_transfer_semantics_not_assumed(self):
  for key in ('repo_type','transfer_mode'):
   with self.subTest(key=key):self.assertIn('process:'+key,self.resolve(pipeline='p',process=[{key:'special'}]))
 def test_missing_pipeline_is_not_unrestricted(self):self.assertIn('pipeline:not_found',self.resolve(pipeline='missing'))
 def test_ambiguous_process_fail_closed(self):self.assertIn('process:ambiguous',self.resolve(pipeline='p',process=[{},{}]))
 def test_policy_projection_uses_context_root_and_object_pipeline(self):
  svc=UploadService();obj=row(pipeline_code='pipeline-from-object')
  with patch('tactic.core.checkin_policy.checkin_constraints',return_value=[]) as c:svc._checkin_policy({'search_type':'fixture/item','options':{}},obj,'publish/main');self.assertEqual(c.call_args.args[:3],('fixture/item','publish','pipeline-from-object'))
 def test_policy_projection_honors_original_process_option(self):
  with patch('tactic.core.checkin_policy.checkin_constraints',return_value=[]) as c:
   UploadService()._checkin_policy({'search_type':'fixture/item','options':{'process':'model','pipeline_code':'explicit-pipeline'}},row(pipeline_code='object-pipeline'),'publish/main')
   self.assertEqual(c.call_args.args[:3],('fixture/item','model','explicit-pipeline'))
 def test_policy_error_does_not_leak_script_body(self):
  with patch('tactic.core.checkin_policy.checkin_constraints',return_value=['widget:checkin_script']):
   with self.assertRaises(ApiError) as e:UploadService()._checkin_policy({'search_type':'fixture/item','options':{'checkin_script':'secret code'}},row(),'publish')
  self.assertEqual(e.exception.status,501);self.assertNotIn('secret',str(e.exception.details))
 def test_invalid_context_before_policy_queries(self):
  for c in (None,[],123,'../publish','/publish','',True):
   with self.subTest(c=c),patch('tactic.core.checkin_policy.checkin_constraints') as policy:
    with self.assertRaises(ApiError):UploadService()._checkin_policy({'search_type':'x/y'},row(),c)
    policy.assert_not_called()

class LegacyUploadGuardTests(unittest.TestCase):
 def backend(self):
  class Legacy:
   def upload(self,*args):return {'delegated':args}
  class Native(UploadService,Legacy):
   def _object(self,stype,key):return row()
  n=Native();n.active_target={'kind':'table','search_type':'fixture/item','options':{}};return n
 def test_old_endpoint_does_not_bypass_guard(self):
  n=self.backend()
  with patch.object(n,'_checkin_policy',side_effect=ApiError(501,'checkin_custom_policy','blocked')):
   with self.assertRaises(ApiError):n.upload('fixture/item','key','name',b'data','publish')
 def test_plain_old_endpoint_delegates_original_backend(self):
  n=self.backend()
  with patch.object(n,'_checkin_policy') as policy:
   result=n.upload('fixture/item','key','name',b'data','publish');self.assertEqual(result['delegated'][-1],'publish');policy.assert_called_once()
 def test_old_endpoint_requires_matching_view(self):
  n=self.backend()
  with self.assertRaises(ApiError):n.upload('secret/type','key','name',b'data','publish')


class StagedPolicyIntegrationTests(unittest.TestCase):
 """Real disk store + production UploadService, fake command to count DB calls."""
 def setUp(self):
  import tempfile
  from tactic.ui_api.upload_store import UploadStore
  self.tmp=tempfile.TemporaryDirectory();self.store=UploadStore(self.tmp.name)
  test=self
  class Backend(UploadService):
   site='';allow_uploads=True
   blocked=False;calls=0;checks=0
   def open_target(self,target):return {'id':'view','kind':'table','search_type':'fixture/item','options':{}}
   def _object(self,stype,key):return SimpleNamespace(get_search_key=lambda:'item-1')
   def _project(self):return 'fixture'
   def _upload_owner(self):return 'alice'
   def _upload_store(self):return test.store
   def _checkin_policy(self,opened,obj,context):
    self.checks+=1
    if self.blocked:raise ApiError(501,'checkin_custom_policy','custom validation not ported')
   def _finish_staged_upload(self,key,path,state):
    self.calls+=1;return {'snapshot':{'code':'S-'+str(self.calls)},'sha256':state['sha256']}
  self.backend=Backend();self.data={'target':'view','key':'item-1'}
 def tearDown(self):self.tmp.cleanup()
 def create(self):
  import hashlib
  content=b'original file'
  sha=lambda b:hashlib.sha256(b).hexdigest()
  job=self.backend.upload_operation('POST','/uploads',{**self.data,'filename':'original.bin','size':len(content),'fingerprint':sha(hashlib.sha256(content).digest()),'context':'publish','request_id':'request-1234'})
  self.backend.upload_operation('PATCH','/upload-chunk',{**self.data,'upload_id':job['id'],'offset':0,'sha256':sha(content)},content)
  return {**self.data,'upload_id':job['id']}
 def test_changed_policy_after_staging_leaves_ready_no_command(self):
  args=self.create();self.backend.blocked=True
  with self.assertRaises(ApiError) as e:self.backend.upload_operation('POST','/upload-finish',args)
  self.assertEqual(e.exception.status,501);self.assertEqual(self.backend.calls,0)
  self.assertEqual(self.backend.upload_operation('GET','/upload-status',args)['state'],'ready')
 def test_policy_rechecked_before_original_command(self):
  args=self.create();self.assertEqual(self.backend.checks,1)
  self.assertEqual(self.backend.upload_operation('POST','/upload-finish',args)['state'],'complete')
  self.assertEqual(self.backend.checks,2);self.assertEqual(self.backend.calls,1)
 def test_completed_receipt_does_not_rerun_after_policy_changed(self):
  args=self.create();a=self.backend.upload_operation('POST','/upload-finish',args)
  self.backend.blocked=True;b=self.backend.upload_operation('POST','/upload-finish',args)
  self.assertEqual(a,b);self.assertEqual(self.backend.calls,1);self.assertEqual(self.backend.checks,2)
 def test_turned_off_uploads_still_allow_reading_queue(self):
  args=self.create();self.backend.allow_uploads=False
  self.assertEqual(self.backend.upload_operation('GET','/upload-status',args)['state'],'ready')
  with self.assertRaises(ApiError) as e:self.backend.upload_operation('POST','/upload-finish',args)
  self.assertEqual(e.exception.status,403);self.assertEqual(self.backend.calls,0)
 def test_blocked_create_does_not_allocate_staging(self):
  self.backend.blocked=True
  with self.assertRaises(ApiError):self.create()
  self.assertEqual(list(Path(self.tmp.name).glob('*/state.json')),[])
