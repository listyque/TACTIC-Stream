"""Strict native-state envelopes; persistence is exercised on original server."""
from pathlib import Path
import copy,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from tactic.ui_api.ui_state_service import validate_state,storage_key
from tactic.ui_api.project_service import project_fields
from tactic.ui_api.contracts import ApiError
FIELDS=[{'name':'name','label':'Name','kind':'text','storage':'name','filterable':True,'sortable':True},
 {'name':'start','label':'Start','kind':'date','storage':'start','filterable':True,'sortable':True},
 {'name':'end','label':'End','kind':'date','storage':'end','filterable':True,'sortable':True}]
SPEC={'fields':FIELDS,'default_sort':[]}
TABS={'children':[{'name':'one','removable':False},{'name':'two','removable':True}], 'container':{'allow_drag':True}}
class StateTests(unittest.TestCase):
 def bad(self,scope,value,spec=SPEC):
  with self.assertRaises(ApiError):validate_state(scope,value,spec)
 def test_namespace_does_not_reuse_legacy_key(self):self.assertTrue(storage_key('geometry','x').startswith('native:ui:v1:'))
 def test_target_hash_distinguishes_widgets(self):self.assertNotEqual(storage_key('geometry','x'),storage_key('geometry','y'))
 def test_scope_hash_distinguishes_purpose(self):self.assertNotEqual(storage_key('query','x'),storage_key('geometry','x'))
 def test_bad_scopes_are_client_errors(self):
  for s in ([],{},None,'password',''):
   with self.subTest(scope=s),self.assertRaises(ApiError):storage_key(s,'x')
 def test_long_target_rejected(self):
  with self.assertRaises(ApiError):storage_key('query','a'*4001)
 def test_workspace_empty_valid(self):self.assertEqual(validate_state('workspace',{}),{'ids':[],'active':''})
 def test_workspace_active_must_exist(self):self.bad('workspace',{'ids':['x'],'active':'y'})
 def test_workspace_cap(self):self.bad('workspace',{'ids':[str(i) for i in range(33)]})
 def test_workspace_duplicates(self):self.bad('workspace',{'ids':['x','x']})
 def test_workspace_cannot_include_record_drafts(self):self.bad('workspace',{'ids':[],'drafts':{'password':'x'}})
 def test_workspace_ids_are_opaque(self):self.assertEqual(validate_state('workspace',{'ids':['x/y?z=1'],'active':'x/y?z=1'})['active'],'x/y?z=1')
 def test_appearance_exact(self):self.assertEqual(validate_state('appearance',{'theme':'dark'}),{'theme':'dark'})
 def test_appearance_rejects_arbitrary_css(self):self.bad('appearance',{'theme':'javascript:bad'})
 def test_navigation_only_configured_folder(self):self.bad('navigation',{'folders':{'other':True}},{'folders':{'known'}})
 def test_navigation_values_are_boolean(self):self.bad('navigation',{'folders':{'known':'false'}},{'folders':{'known'}})
 def test_navigation_roundtrip(self):self.assertEqual(validate_state('navigation',{'folders':{'known':False}},{'folders':{'known'}})['folders'],{'known':False})
 def test_geometry_defaults(self):self.assertEqual(validate_state('geometry',{},SPEC)['density'],'comfortable')
 def test_geometry_width_limits(self):
  for width in (True,0,1201,float('nan'),float('inf')):
   with self.subTest(width=width):self.bad('geometry',{'widths':{'name':width}})
 def test_geometry_unknown_column(self):self.bad('geometry',{'hidden':['secret']})
 def test_geometry_cannot_hide_secret_editor(self):self.bad('geometry',{'hidden':['secret']},{'fields':FIELDS+[{'name':'secret','write_only':True}]})
 def test_geometry_does_not_mutate_source(self):
  original=copy.deepcopy(SPEC);validate_state('geometry',{'order':['end','name'],'widths':{'name':250}},SPEC);self.assertEqual(SPEC,original)
 def test_geometry_rejects_group_nonstring(self):
  for value in (False,0,{},[]):
   with self.subTest(value=value):self.bad('geometry',{'groupField':value})
 def test_geometry_no_arbitrary_root(self):self.bad('geometry',{'values':{'name':'new'}})
 def test_tabs_source_names_preserved(self):self.assertEqual(validate_state('tabs',{'order':['two','one'],'selected':'two'},TABS)['order'],['two','one'])
 def test_tabs_protected_cannot_close(self):self.bad('tabs',{'closed':['one']},TABS)
 def test_tabs_closed_not_selected(self):self.bad('tabs',{'closed':['two'],'selected':'two'},TABS)
 def test_tabs_hidden_not_accessible(self):self.bad('tabs',{'order':['hidden']},TABS)
 def test_tabs_duplicate_names_fail_closed(self):self.bad('tabs',{},dict(TABS,children=[TABS['children'][0]]*2))
 def test_tabs_allow_drag_false(self):self.bad('tabs',{'order':['two','one']},dict(TABS,container={'allow_drag':False}))
 def test_tabs_titles_plain_unicode(self):self.assertEqual(validate_state('tabs',{'titles':{'one':'Свой заголовок'}},TABS)['titles']['one'],'Свой заголовок')
 def test_tabs_malformed_selection_is_client_error(self):self.bad('tabs',{'selected':[]},TABS)
 def timeline(self,**kw):return dict(mode='calendar',start='2026-10-01',end='2026-11-11',month='2026-10',zoom=30,startField='start',endField='end',includeUndated=False,**kw)
 def test_timeline_roundtrip(self):self.assertEqual(validate_state('timeline',self.timeline(),SPEC)['start'],'2026-10-01')
 def test_timeline_range(self):v=self.timeline();v['end']='2030-01-01';self.bad('timeline',v)
 def test_timeline_wrong_dates(self):v=self.timeline();v['month']=None;self.bad('timeline',v)
 def test_timeline_hidden_fields(self):v=self.timeline();v['startField']='name';self.bad('timeline',v)
 def test_timeline_does_not_store_results(self):v=self.timeline();v['items']=[];self.bad('timeline',v)
 def test_query_no_sql(self):self.bad('query',{'sql':'select * from login'})
 def test_query_unknown_filter(self):self.bad('query',{'filters':[{'field':'secret','op':'eq','value':'x'}]})
 def test_query_quick_invalid_type(self):self.bad('query',{'quickField':[]})
 def test_query_keeps_unicode(self):self.assertEqual(validate_state('query',{'quickText':'Проверка'},SPEC)['quickText'],'Проверка')
 def test_query_zero_offset(self):self.assertEqual(validate_state('query',{'offset':0,'limit':50},SPEC)['offset'],0)
 def test_size_cap(self):self.bad('workspace',{'ids':['x'*70000]})
class ProjectFieldsTests(unittest.TestCase):
 def data(self,**kw):return dict(code='new_project',title='Новый проект',type='default',description='Строка\nОписание',**kw)
 def test_original_strings_preserved(self):self.assertEqual(project_fields(self.data())['description'],'Строка\nОписание')
 def test_reserved_and_unsafe_codes(self):
  for code in ('admin','default','sthpw','unittest','template','public','../bad','bad-code','Foo','1project','x'*31,None):
   with self.subTest(code=code),self.assertRaises(ApiError):project_fields(dict(self.data(),code=code))
 def test_empty_title(self):
  with self.assertRaises(ApiError):project_fields(dict(self.data(),title=' '))
 def test_null_in_description(self):
  with self.assertRaises(ApiError):project_fields(dict(self.data(),description='\0'))
 def test_no_database_path_or_class_input(self):
  with self.assertRaises(ApiError):project_fields(dict(self.data(),database='/tmp/anything'))
 def test_backwards_default_type(self):v=self.data();del v['type'];self.assertEqual(project_fields(v)['type'],'default')
if __name__=='__main__':unittest.main()
