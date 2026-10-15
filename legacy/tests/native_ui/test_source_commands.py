"""Tests of moved ORIGINAL classes with DB/command collaborators replaced.

These prove extraction/adaptation semantics, not live PostgreSQL integration.
"""
import sys,unittest,types
from pathlib import Path
from unittest.mock import patch,Mock
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from pyasm.common import Container,UserException
from tactic.core.widget_config import WidgetConfig
from tactic.core.sidebar_config import SidebarConfig
from tactic.core.config_model import ConfigModel,SidebarProjection
from tactic.core.native_edit import NativeEditCmd,ExplicitDatabaseAction
from tactic.core.edit_commands import EditCmd
from pyasm.command.edit_wdg_action import DatabaseAction,DefaultValueDatabaseAction

class SourceSidebarTests(unittest.TestCase):
 def setUp(self):Container.create()
 def setup_loader(self,rows=None):
  import tactic.core.sidebar_config as module
  queries=[];rows=rows or {}
  class Search:
   def __init__(self,*a):self.filters={};self.order=None;queries.append(self)
   def add_filter(self,k,v):self.filters[k]=v
   def column_exists(self,n):return True
   def add_order_by(self,s):self.order=s
   def get_sobject(self):return rows.get((self.filters.get('view'),self.filters.get('login')))
  project=Mock();project.get_base_type.return_value='admin';project.is_admin.return_value=True
  patches=[patch.object(module,'Search',Search),patch.object(module.Project,'get',return_value=project),patch.object(module.Environment,'get_user_name',return_value='fixture'),patch.object(module.WidgetDbConfig,'get_by_search',side_effect=lambda s,k:s.get_sobject())]
  for p in patches:p.start();self.addCleanup(p.stop)
  return queries
 def test_original_loader_reads_real_internal_xml(self):
  self.setup_loader();m=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg','admin_views'));self.assertEqual(m.names(),['create_project','global_admin','project_admin','separator','project_essentials'])
 def test_original_loader_uses_db_priority_and_preserves_normal_query_shape(self):
  w=WidgetConfig.get(xml='<config><admin_views><element name="users"/></admin_views></config>',view='admin_views');q=self.setup_loader({('admin_views',None):w});m=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg','admin_views'));self.assertEqual(m.names(),['users']);self.assertEqual(q[0].order,'priority desc');self.assertNotIn('login',q[0].filters);self.assertEqual(m.handler('users'),'LinkWdg')
 def test_personal_definition_precedes_shared_definition(self):
  make=lambda title:WidgetConfig.get(xml='<config><definition><element name="users" title="'+title+'"/></definition></config>',view='definition')
  self.setup_loader({('definition','fixture'):make('Personal'),('definition',None):make('Shared')});m=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg','admin_views',personal=True));self.assertEqual(m.describe('users')['title'],'Personal')
 def test_existing_links_keep_identity_after_order_change(self):
  def projection(xml):
   self.setup_loader({('admin_views',None):WidgetConfig.get(xml=xml,view='admin_views')});p=SidebarProjection(lambda v,personal:ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg',v,personal=personal)),lambda n:True,'admin','fixture');p.build(['admin_views']);return {v['name']:k for k,v in p.targets.items()}
  a=projection('<config><admin_views><element name="users"/><element name="projects"/></admin_views></config>')
  b=projection('<config><admin_views><element name="projects"/><element name="users"/></admin_views></config>');self.assertEqual(a,b)

class NativeValueTests(unittest.TestCase):
 def test_zero_is_not_converted_to_null(self):
  a=ExplicitDatabaseAction();self.assertEqual(a.convert_value('integer',0),0);self.assertEqual(a.convert_value('float',0.0),0.0)
 def test_legacy_zero_behavior_not_globally_changed(self):self.assertIsNone(DatabaseAction().convert_value('integer',0))
 def test_explicit_null_sets_correct_column_without_committing(self):
  a=ExplicitDatabaseAction();a.explicit_value=None;a.name='alias';a.set_option('column','name');a.sobject=Mock();a.execute();a.sobject.set_value.assert_called_once_with('name',None,allow_none=True);a.sobject.commit.assert_not_called()
 def test_required_null_is_rejected(self):
  a=ExplicitDatabaseAction();a.explicit_value=None;a.name='name';a.set_option('empty','false')
  with self.assertRaises(UserException):a.check()
 def test_only_plain_actions_are_adapted(self):
  plain=DatabaseAction();plain.name='a';default=DefaultValueDatabaseAction();default.name='b';absent=DatabaseAction();absent.name='c';custom=type('CustomAction',(DatabaseAction,),{})();custom.name='d'
  cmd=object.__new__(NativeEditCmd);cmd.data={'a':0,'b':0,'d':0}
  with patch.object(EditCmd,'_get_action_handlers',return_value=[plain,default,absent,custom]):result=cmd._get_action_handlers()
  self.assertIs(type(result[0]),ExplicitDatabaseAction);self.assertIs(result[1],default);self.assertIs(result[2],absent);self.assertIs(result[3],custom)
 def test_wrapper_file_reexports_correct_class(self):
  # Check the compatibility shim itself, not import-time legacy package init.
  import runpy
  scope=runpy.run_path(str(R/'src/tactic/ui/panel/edit_cmd.py'))
  self.assertIs(scope['EditCmd'],EditCmd)

class CoreInitTests(unittest.TestCase):
 def test_business_registration_order_and_modes(self):
  import tactic.core.bootstrap as m
  calls=[]
  class TriggerRecord:
   def __init__(self):self.values={}
   def set_value(self,k,v):self.values[k]=v
  with patch.object(m.SearchType,'create',side_effect=lambda n:TriggerRecord()),patch.object(m.Trigger,'append_static_trigger',side_effect=lambda t,startup:calls.append(('trigger',t.values,startup))),patch('pyasm.command.workflow.Workflow.init',side_effect=lambda **kw:calls.append(('workflow',kw))),patch('pyasm.biz.Snapshot.add_integral_trigger',side_effect=lambda:calls.append(('snapshot',))):m.CoreInit().execute()
  self.assertEqual([c[0] for c in calls],['trigger','trigger','workflow','trigger','snapshot'])
  self.assertEqual([c[1]['event'] for c in calls if c[0]=='trigger'],['change|sthpw/task|status','change|config/process_state|status','insert|sthpw/login'])
  self.assertTrue(all(c[1]['mode']=='same process,same transaction' and c[2] for c in calls if c[0]=='trigger'))

if __name__=='__main__':unittest.main()
