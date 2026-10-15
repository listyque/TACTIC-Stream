"""Native administration invariants; no user DB, no fake permission evaluator."""
import ast,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'src'))
from tactic.ui_api.security_service import rule_match,matrix_cell,CATEGORIES,SecurityService
from tactic.core.sidebar_edits import patch_sidebar,load_xml,find_view
from tactic.core.config_model import ConfigModel,ConfigSource,target_spec
from tactic.ui_api.contracts import ApiError

class ExtractedCommands(unittest.TestCase):
 def test_original_class_bodies_preserved(self):
  tree=ast.parse((R/'src/tactic/core/admin_commands_017.py').read_text())
  classes={n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
  for item in json.loads((R/'tests/native_ui/source-provenance-017.json').read_text()):
   with self.subTest(name=item['class']):
    body=ast.dump(classes[item['class']],include_attributes=False)
    self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),item['ast_sha256'])
 def test_old_paths_reexport_same_class(self):
  for item in json.loads((R/'tests/native_ui/source-provenance-017.json').read_text()):
   tree=ast.parse((R/item['source']).read_text())
   self.assertTrue(any(isinstance(n,ast.ImportFrom) and n.module=='tactic.core.admin_commands_017' and any(a.name==item['class'] for a in n.names) for n in tree.body))
 def test_original_menu_catalog(self):
  tree=ast.parse((R/'src/tactic/ui/startup/security_wdg.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GearMenuSecurityWdg')
  fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_all_menu_names')
  node=next(n for n in ast.walk(fn) if isinstance(n,ast.Dict))
  self.assertEqual(ast.literal_eval(node),json.loads((R/'src/tactic/core/security_menu_names.json').read_text()))

class MatrixSemantics(unittest.TestCase):
 def setUp(self):self.row={'value':'entry','pipeline':'pipe','submenu':'View'};self.project='work'
 def cell(self,cat='link',rules=(),level='none',group_project='',protected=False,row=None):return matrix_cell(cat,row or self.row,list(rules),self.project,level,group_project,protected)
 def rule(self,cat='link',**extra):return dict(rule_match(cat,self.row,self.project),access='allow',**extra)
 def test_no_rule_not_checked(self):self.assertFalse(self.cell()['checked']);self.assertFalse(self.cell()['read_only'])
 def test_explicit_allow(self):self.assertTrue(self.cell(rules=[self.rule()])['checked']);self.assertFalse(self.cell(rules=[self.rule()])['read_only'])
 def test_deny_is_not_checked_as_allow(self):r=self.rule();r['access']='deny';c=self.cell(rules=[r]);self.assertFalse(c['checked']);self.assertTrue(c['read_only'])
 def test_conditional_rule_readonly(self):self.assertTrue(self.cell(rules=[self.rule(condition='custom')])['read_only'])
 def test_duplicate_rule_readonly(self):self.assertTrue(self.cell(rules=[self.rule(),self.rule()])['read_only'])
 def test_foreign_link_rule_not_current_grant(self):r=self.rule();r['project']='other';self.assertFalse(self.cell(rules=[r])['checked'])
 def test_foreign_stype_rule_is_locked_not_removed(self):r=self.rule('search_type');r['project']='other';self.assertTrue(self.cell('search_type',[r])['read_only'])
 def test_foreign_process_rule_locked(self):r=self.rule('process');r['project']='other';self.assertTrue(self.cell('process',[r])['read_only'])
 def test_foreign_task_pipeline_locked(self):r=self.rule('task');r['pipeline']='other';self.assertTrue(self.cell('task',[r])['read_only'])
 def test_menu_same_label_other_submenu_locked(self):r=self.rule('gear_menu');r['submenu']='Other';self.assertTrue(self.cell('gear_menu',[r])['read_only'])
 def test_wildcard_inherited(self):r=self.rule();r['element']='*';c=self.cell(rules=[r]);self.assertTrue(c['checked']);self.assertTrue(c['inherited']);self.assertTrue(c['read_only'])
 def test_wildcard_does_not_hide_existing_explicit_rule(self):r=self.rule();r['element']='*';c=self.cell(rules=[r,self.rule()]);self.assertTrue(c['explicit']);self.assertFalse(c['read_only'])
 def test_admin_protected(self):self.assertTrue(self.cell(protected=True)['read_only'])
 def test_original_link_high_auto(self):self.assertTrue(self.cell(level='high')['inherited']);self.assertFalse(self.cell(level='medium')['inherited'])
 def test_original_project_level_bound(self):self.assertTrue(self.cell('project',level='min',group_project='entry')['inherited']);self.assertFalse(self.cell('project',level='high',group_project='other')['inherited'])
 def test_original_stype_min_auto(self):self.assertTrue(self.cell('search_type',level='min')['inherited'])
 def test_original_process_low_auto(self):self.assertTrue(self.cell('process',level='low')['inherited']);self.assertFalse(self.cell('process',level='min')['inherited'])
 def test_original_task_low_auto(self):self.assertTrue(self.cell('task',level='low')['inherited'])
 def test_task_rules_have_pipeline_not_project(self):r=rule_match('task',self.row,self.project);self.assertEqual(r['pipeline'],'pipe');self.assertNotIn('project',r)
 def test_process_all_has_original_pipeline_star(self):self.assertEqual(rule_match('process',{'value':'*'},self.project),{'group':'process','process':'*','project':'work','pipeline':'*'})
 def test_process_rules_have_project_not_pipeline(self):r=rule_match('process',self.row,self.project);self.assertEqual(r['project'],'work');self.assertNotIn('pipeline',r)
 def test_rules_not_mutated(self):r=self.rule();old=dict(r);self.cell(rules=[r]);self.assertEqual(r,old)
 def test_no_cross_project_wildcard(self):r=self.rule();r.update(element='*',project='other');self.assertFalse(self.cell(rules=[r])['checked'])

RAW='''<config><!-- keep --><project_view custom="yes"><element name="a" title="Alpha"><display class="LinkWdg"><search_type>work/item</search_type><view>table</view><opaque><![CDATA[x < y && z]]></opaque></display></element><unknown keep="1"/><element name="separator"/><element name="b"/><element name="separator"/></project_view><definition><element name="b"><display class="custom.Special"><hello>stay</hello></display></element></definition><other q="kept"/></config>'''
class SidebarPreservation(unittest.TestCase):
 def go(self,ops,raw=RAW):return patch_sidebar(raw,'project_view',ops,{'b':{'handler':'custom.Special','options':{'hello':'stay'}}})[0]
 def names(self,raw):return [e.get('name') for e in find_view(load_xml(raw),'project_view') if e.tag=='element']
 def test_title_only_preserves_everything_else(self):s=self.go([{'op':'edit','index':0,'attributes':{'title':'Новый'}}]);self.assertIn('<![CDATA[x < y && z]]>',s);self.assertIn('<!-- keep -->',s);self.assertIn('<unknown keep="1"/>',s);self.assertIn('<other q="kept"/>',s);self.assertIn('custom="yes"',s)
 def test_remove_only_reference_not_definition(self):s=self.go([{'op':'remove','index':2}]);self.assertEqual(self.names(s),['a','separator','separator']);self.assertIn('<element name="b"><display class="custom.Special">',s)
 def test_remove_everything_leaves_empty_view(self):s=self.go([{'op':'remove','index':0}]*4);self.assertEqual(self.names(s),[]);self.assertIn('<unknown keep="1"/>',s)
 def test_separator_occurrences_survive_reorder(self):s=self.go([{'op':'reorder','order':[3,2,1,0]}]);self.assertEqual(self.names(s),['separator','b','separator','a'])
 def test_unknown_node_keeps_its_slot(self):s=self.go([{'op':'reorder','order':[3,2,1,0]}]);n=find_view(load_xml(s),'project_view');self.assertEqual(n[1].tag,'unknown')
 def test_duplicate_order_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'reorder','order':[0,0,2,3]}])
 def test_bool_not_accepted_as_index(self):
  with self.assertRaises(ValueError):self.go([{'op':'remove','index':True}])
 def test_invalid_index_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'edit','index':4}])
 def test_custom_handler_not_overwritten(self):
  with self.assertRaises(ValueError):self.go([{'op':'edit','index':2,'options':{}}])
 def test_unknown_attributes_preserved(self):self.assertIn('custom="yes"',self.go([{'op':'edit','index':0,'attributes':{'icon':'book'}}]))
 def test_new_link_escapes_text(self):s=self.go([{'op':'add','name':'c','options':{'title':'<script>bad</script>'}}]);self.assertIn('&lt;script&gt;',s)
 def test_native_options_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'add','name':'c','options':{'native_fixed_group':'x'}}])
 def test_callback_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'add','name':'c','options':{'cbjs_action':'evil()'}}])
 def test_duplicate_link_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'add','name':'a'}])
 def test_duplicate_separator_allowed(self):self.assertEqual(self.names(self.go([{'op':'add','kind':'separator','name':'separator'}])).count('separator'),3)
 def test_folder_returns_creation_plan(self):s,f=patch_sidebar(RAW,'project_view',[{'op':'add','kind':'folder','name':'folder','options':{'view':'new_folder'}}],{});self.assertEqual(f,['new_folder'])
 def test_duplicate_folder_target_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'add','kind':'folder','name':'x','options':{'view':'new_folder'}},{'op':'add','kind':'folder','name':'y','options':{'view':'new_folder'}}])
 def test_folder_cannot_refer_to_itself(self):
  with self.assertRaises(ValueError):self.go([{'op':'add','kind':'folder','name':'x','options':{'view':'project_view'}}])
 def test_folder_rebinding_is_not_silent(self):
  raw='<config><project_view><element name="x"><display class="FolderWdg"><view>old</view></display></element></project_view></config>'
  with self.assertRaises(ValueError):self.go([{'op':'edit','index':0,'options':{'view':'project_view'}}],raw)
 def test_entities_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'remove','index':0}],'<!DOCTYPE config SYSTEM "file:///etc/passwd"><config/>')
 def test_unknown_operation_rejected(self):
  with self.assertRaises(ValueError):self.go([{'op':'delete_everything'}])
 def test_new_nested_options_remain_xml(self):s=self.go([{'op':'add','name':'c','options':{'settings':{'show_insert':False}}}]);self.assertIn('<settings><show_insert>false</show_insert></settings>',s)
 def test_remove_attribute(self):s=self.go([{'op':'edit','index':0,'attributes':{'title':None}}]);self.assertNotIn('title="Alpha"',s)
 def test_edit_does_not_rename_identity(self):
  with self.assertRaises(ValueError):self.go([{'op':'edit','index':0,'attributes':{'name':'other'}}])
 def test_buffer_sequence_tracks_updated_indices(self):s=self.go([{'op':'remove','index':1},{'op':'edit','index':1,'attributes':{'title':'B'}}]);self.assertIn('name="b" title="B"',s)

class AdminRouting(unittest.TestCase):
 def test_stock_user_panel(self):self.assertEqual(target_spec('tactic.ui.startup.project_config_wdg.UserPanelWdg',{})['kind'],'users')
 def test_stock_group_assignment(self):self.assertEqual(target_spec('tactic.ui.startup.UserSecurityWdg',{})['kind'],'group-assignment')
 def test_stock_user_group_popup(self):self.assertEqual(target_spec('tactic.ui.startup.GroupAssignWdg',{})['kind'],'group-assignment')
 def test_stock_groups(self):self.assertEqual(target_spec('tactic.ui.startup.SecurityGroupListWdg',{})['kind'],'groups')
 def test_stock_categories(self):
  for c in ('Project','Link','GearMenu','SearchType','Process','Task'):
   self.assertEqual(target_spec('tactic.ui.startup.'+c+'SecurityWdg',{})['kind'],'security')
 def test_foreign_basename_not_matched(self):self.assertEqual(target_spec('evil.SecurityWdg',{})['kind'],'unsupported')
 def test_search_type_tool(self):self.assertEqual(target_spec('tactic.ui.app.SearchTypeToolWdg',{})['kind'],'search-types')
 def test_manage_sidebar(self):self.assertEqual(target_spec('tactic.ui.panel.ManageViewPanelWdg',{})['kind'],'sidebar-editor')

if __name__=='__main__':unittest.main()

class ProdSettingSiteTests(unittest.TestCase):
    """Execute the source get_by_key with controlled collaborators, not a duplicate algorithm."""
    def run_lookup(self, site_value, project='work', failure=False):
        import types, sys
        from unittest.mock import patch
        path=R/'src/pyasm/prod/biz/prod_setting.py'
        tree=ast.parse(path.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProdSetting')
        fun=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_by_key')
        fun.decorator_list=[];module=ast.Module(body=[fun],type_ignores=[]);ast.fix_missing_locations(module)
        calls=[]
        class FakeSite:
            @staticmethod
            def get_site():return site_value
            @staticmethod
            def set_site(value):calls.append(('push',value))
            @staticmethod
            def pop_site():calls.append(('pop',))
        class FakeSearch:
            def __init__(self,*args,**kwargs):pass
            def add_filter(self,*args):pass
        class Model:
            SEARCH_TYPE='config/prod_setting'
            @staticmethod
            def get_by_search(search,key):
                if failure:raise ValueError('probe')
                return 'original result'
        scope={'Search':FakeSearch,'ProdSetting':Model,'Project':types.SimpleNamespace(get_project_code=lambda:project,get_project_name=lambda:project)}
        exec(compile(module,str(path),'exec'),scope)
        with patch.dict(sys.modules,{'pyasm.security':types.SimpleNamespace(Site=FakeSite)}):
            try:result=scope['get_by_key'](Model,'set_persistent_search')
            except ValueError:
                if not failure:raise
                result='raised'
        return result,calls
    def test_unnamed_site_neither_pushes_nor_pops_security_frame(self):
        self.assertEqual(self.run_lookup(''),('original result',[]))
    def test_named_site_balances_original_context(self):
        self.assertEqual(self.run_lookup('studio'),('original result',[('push','studio'),('pop',)]))
    def test_named_site_pops_even_when_query_fails(self):
        self.assertEqual(self.run_lookup('studio',failure=True),('raised',[('push','studio'),('pop',)]))
    def test_admin_shortcut_still_balances_named_context(self):
        self.assertEqual(self.run_lookup('studio',project='admin'),(None,[('push','studio'),('pop',)]))
