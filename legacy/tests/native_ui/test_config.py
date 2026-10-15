"""Configuration semantics, using real shipped TACTIC XML as fixtures."""
import sys, unittest, json, math, copy
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'src'))
from tactic.core.config_model import (ConfigSource,ConfigModel,SidebarProjection,parse_xml,view_node,reorder_view,patch_pipeline_positions,target_spec)
from tactic.core.field_policy import field_access,sidebar_allowed

def source(xml,view='table',origin='test'):return ConfigSource(xml,view,origin)
def model(xml,view='table'):return ConfigModel(view,[source(xml,view)])

class LayerTests(unittest.TestCase):
 def test_first_view_owns_order(self):
  m=ConfigModel('table',[source('<config><table><element name="b"/></table></config>'),source('<config><table><element name="a"/></table></config>')]);self.assertEqual(m.names(),['b'])
 def test_empty_view_overrides_inheritance(self):
  m=ConfigModel('table',[source('<config><table/></config>'),source('<config><table><element name="a"/></table></config>')]);self.assertEqual(m.names(),[])
 def test_missing_view_falls_through(self):
  m=ConfigModel('table',[source('<config><other/></config>'),source('<config><table><element name="a"/></table></config>')]);self.assertEqual(m.names(),['a'])
 def test_definitions_do_not_add_columns(self):
  m=ConfigModel('table',[source('<config><definition><element name="hidden"/></definition></config>','definition'),source('<config><table><element name="a"/></table></config>')]);self.assertEqual(m.names(),['a'])
 def test_definition_view_first_nonempty(self):
  m=ConfigModel('definition',[source('<config><definition/></config>','definition'),source('<config><definition><element name="a"/></definition></config>','definition')]);self.assertEqual(m.names(),['a'])
 def test_attributes_merge_first_wins(self):
  m=ConfigModel('table',[source('<config><table title="Top"><element name="a" width="20"/></table></config>'),source('<config><definition layout="table"><element name="a" width="90" title="Inherited"/></definition></config>','definition')]);self.assertEqual(m.attributes('a'),{'name':'a','width':'20','title':'Inherited'});self.assertEqual(m.attributes()['title'],'Top')
 def test_options_are_not_deep_merged(self):
  m=ConfigModel('table',[source('<config><table><element name="a"><display><view>first</view></display></element></table></config>'),source('<config><definition><element name="a"><display class="Fake"><search_type>p/a</search_type></display></element></definition></config>','definition')]);self.assertEqual(m.handler('a'),'Fake');self.assertEqual(m.options('a'),{'view':'first'})
 def test_empty_options_fall_through(self):
  m=ConfigModel('table',[source('<config><table><element name="a"><display class="Top"/></element></table></config>'),source('<config><definition><element name="a"><display><view>fallback</view></display></element></definition></config>','definition')]);self.assertEqual(m.options('a'),{'view':'fallback'})
 def test_alias_and_action_independent(self):
  m=ConfigModel('table',[source('<config><table><element name="a"><display widget="text"/><action class="DatabaseAction"><empty>false</empty></action></element></table></config>')],{'text':'TextWdg'});self.assertEqual(m.handler('a'),'TextWdg');self.assertEqual(m.handler('a','action'),'DatabaseAction');self.assertEqual(m.options('a','action'),{'empty':'false'})
 def test_view_with_at_is_exact(self):
  m=model('<config><view name="@panel"><element name="a"/></view></config>','@panel');self.assertEqual(m.names(),['a']);self.assertIsNone(view_node(m.sources[0].root,"@panel' or 1=1"))
 def test_nested_config_is_data_not_code(self):
  m=model('<config><table><element name="a"><display><config><tab title="X"/></config></display></element></table></config>');self.assertEqual(m.options('a')['config'],{'tab':''})  # original generic recursive options, not invented XML string
 def test_entities_disabled(self):
  for s in ['<!DOCTYPE config [<!ENTITY x "x">]><config/>','<!DOCTYPE config SYSTEM "file:///etc/passwd"><config/>']:
   with self.assertRaises(ValueError):parse_xml(s)
 def test_oversized_xml(self):
  with self.assertRaises(ValueError):parse_xml('<config>'+(' '*(4*1024*1024))+'</config>')
 def test_revision_changes_for_definition(self):
  a=model('<config><table><element name="a" title="A"/></table></config>');b=model('<config><table><element name="a" title="B"/></table></config>');self.assertNotEqual(a.fingerprint(),b.fingerprint())
 def test_unknown_widget_not_silently_table(self):
  self.assertEqual(target_spec('company.CustomWdg',{'search_type':'p/a'})['kind'],'unsupported')
 def test_existing_view_panel_is_table(self):
  self.assertEqual(target_spec('LinkWdg',{'class_name':'tactic.ui.panel.ViewPanelWdg','search_type':'p/a','view':'special'})['view'],'special')

class RoundTripTests(unittest.TestCase):
 XML='<config custom="keep"><table layout="X"><!-- keep --><element name="a" x="1"><display><custom>keep</custom></display></element><extension flag="1"/><element name="separator"/><element name="separator"/></table><definition><element name="other"/></definition></config>'
 def test_reorder_preserves_unknown_nodes(self):
  t=reorder_view(self.XML,'table',[2,0,1]);r=parse_xml(t);self.assertEqual(r.get('custom'),'keep');self.assertEqual([e.get('name') for e in r.findall('table/element')],['separator','a','separator']);self.assertIsNotNone(r.find('table/extension'));self.assertIsNotNone(r.find('definition/element'));self.assertIn('<!-- keep -->',t)
 def test_reorder_requires_permutation(self):
  for bad in ([0,0,1],[0,1],['0',1,2],[False,1,2],None):
   with self.assertRaises(ValueError):reorder_view(self.XML,'table',bad)
 def test_reorder_empty_view(self):self.assertIn('<table',reorder_view('<config><table/></config>','table',[]))
 def test_pipeline_preserves_unknowns_and_escaped_values(self):
  s='<pipeline color="#123"><!-- note --><process name="a" xpos="1" ypos="2" type="custom" custom="A &amp; B"><config foo="bar"/></process><process name="b"/><connect from="a" to="b" custom="yes"/></pipeline>'
  t=patch_pipeline_positions(s,{'a':{'x':5.5,'y':-3}});r=parse_xml(t);a=r.find('process');self.assertEqual(a.get('xpos'),'5.5');self.assertEqual(a.get('ypos'),'-3');self.assertEqual(a.get('custom'),'A & B');self.assertIsNone(a.get('x'));self.assertIsNotNone(a.find('config'));self.assertEqual(r.find('connect').get('custom'),'yes');self.assertIn('<!-- note -->',t)
 def test_pipeline_rejects_unknown_process(self):
  with self.assertRaises(ValueError):patch_pipeline_positions('<pipeline><process name="a"/></pipeline>',{'x':{'x':1,'y':2}})
 def test_pipeline_rejects_invalid_coordinates(self):
  for x in (float('nan'),float('inf'),True,'1',100001):
   with self.assertRaises(ValueError):patch_pipeline_positions('<pipeline><process name="a"/></pipeline>',{'a':{'x':x,'y':0}})
 def test_duplicate_process_rejected(self):
  with self.assertRaises(ValueError):patch_pipeline_positions('<pipeline><process name="a"/><process name="a"/></pipeline>',{})

class SidebarTests(unittest.TestCase):
 def fixture(self,extra=None,allowed=lambda n:True):
  files=[R/'src/tactic/ui/config/admin-conf.xml',R/'src/tactic/ui/config/DEFAULT-conf.xml'];texts=[(p.read_text(),p.name) for p in files]
  def load(view,personal=False):
   layers=[]
   if extra and view in extra:layers.append(source(extra[view],view,'config/widget_config:test'))
   for v in (view,'definition'):
    for text,origin in texts:
     if view_node(parse_xml(text),v) is not None:layers.append(source(text,v,origin))
   return ConfigModel(view,layers)
  p=SidebarProjection(load,allowed,'admin','admin');return p,p.build(['admin_views'])
 def test_real_admin_xml_order(self):
  p,tree=self.fixture();r=parse_xml((R/'src/tactic/ui/config/admin-conf.xml').read_text());expected=[n.get('name') for n in r.find('admin_views')];self.assertEqual([n['name'] for n in tree[0]['children']],expected)
 def test_original_folders_resolve_to_real_targets(self):
  p,tree=self.fixture();self.assertGreater(len(p.targets),30);users=next(t for t in p.targets.values() if t['name']=='users');self.assertEqual(users['search_type'],'sthpw/login');self.assertEqual(users['view'],'table')
 def test_database_override_replaces_original_order(self):
  p,tree=self.fixture({'admin_views':'<config><admin_views><element name="users"/><element name="project_admin"/></admin_views></config>'});self.assertEqual([n['name'] for n in tree[0]['children']],['users','project_admin'])
 def test_access_removes_target_server_side(self):
  p,tree=self.fixture(allowed=lambda n:n!='users');self.assertFalse(any(t['name']=='users' for t in p.targets.values()))
 def test_unknown_remains_in_menu_as_unsupported(self):
  p,_=self.fixture();self.assertTrue(any(t['kind']=='unsupported' for t in p.targets.values()))
 def test_cycle_stops_recursion(self):
  def load(v,p):return model('<config><loop><element name="again"><display class="FolderWdg"><view>loop</view></display></element></loop></config>','loop')
  p=SidebarProjection(load,lambda n:True,'p','u');self.assertEqual(p.build(['loop'])[0]['children'][0]['children'][0]['kind'],'diagnostic')
 def test_personal_flag_propagates(self):
  calls=[]
  def load(v,p):calls.append((v,p));return model('<config><my_view_alex><element name="f"><display class="FolderWdg"><view>folder</view></display></element></my_view_alex><folder><element name="x"/></folder></config>',v)
  SidebarProjection(load,lambda n:True,'p','alex').build(['my_view_alex']);self.assertEqual(calls,[('my_view_alex',True),('folder',True)])
 def test_hidden_link_not_registered(self):
  def load(v,p):return model('<config><x><element name="secret" is_visible="false"/></x></config>','x')
  p=SidebarProjection(load,lambda n:True,'p','u');p.build(['x']);self.assertEqual(p.targets,{})

class PermissionTests(unittest.TestCase):
 def security(self,version=2,answer=True):
  class Security:
   def __init__(self):self.calls=[]
   def get_version(self):return version
   def check_access(self,*args,**kwargs):self.calls.append((args,kwargs));return answer
  return Security()
 def test_v1_sidebar_category(self):
  s=self.security(1);sidebar_allowed(s,'p','u','x');self.assertEqual(s.calls[0][0][:3],('side_bar','x','view'))
 def test_v2_personal_default(self):
  s=self.security();sidebar_allowed(s,'p','u','u.custom');self.assertEqual(s.calls[0][1]['default'],'view')
 def test_v2_shared_deny_default(self):
  s=self.security();sidebar_allowed(s,'p','u','global');self.assertEqual(s.calls[0][1]['default'],'deny')
 def test_hidden_field(self):self.assertEqual(field_access(self.security(),'p','p/x','salary',{'hidden':'true'}),(False,False))
 def test_denied_view_never_editable(self):self.assertEqual(field_access(self.security(answer=False),'p','p/x','salary',{}),(False,False))
 def test_access_default_from_config(self):
  s=self.security();field_access(s,'p','p/x','name',{'access':'view'});self.assertEqual(s.calls[0][1]['default'],'view')

if __name__=='__main__':unittest.main()
