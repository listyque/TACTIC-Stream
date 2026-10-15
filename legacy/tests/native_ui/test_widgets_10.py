"""Widget foundations: production services, source precedence, no real user DB."""
import ast
import copy
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.core.config_model import ConfigModel, ConfigSource, target_spec
from tactic.core.widget_containers import tab_model, tab_items, default_values, resolve_edit, edit_base_model
from tactic.core.context_menus import menu_items
from tactic.ui_api.contracts import ApiError
from tactic.ui_api.widget_service import WidgetService
from tactic.ui_api.extended_backend import ExtendedBackend

RAW='<config><tab><element name="a" title="Alpha"><display widget="table_layout"><search_type>fixture/item</search_type></display></element><element name="hidden" display="false"/><element name="b" title="Beta" load="true"><display class="tactic.ui.panel.EditWdg"><search_type>fixture/item</search_type><search_key>{@GET(.key)}</search_key></display></element></tab></config>'

def model(opts=None,include=None,db=None,saved=None):
 return tab_model(opts or {'config_xml':RAW},lambda n:(include or {})[n],lambda v:(db or {}).get(v),lambda k:saved)

def parent(opts=None):return {'id':'root','options':opts or {'config_xml':RAW}}

class TabTests(unittest.TestCase):
 def test_order_from_original_inline(self):self.assertEqual(model()[1],['a','hidden','b'])
 def test_original_alias_resolves(self):
  m,n,_=model();self.assertEqual(tab_items(parent(),m,n,lambda e,s:'fixture/item?code=1')[0]['kind'],'table')
 def test_explicit_order(self):self.assertEqual(model({'config_xml':RAW,'element_names':'b,a'})[1],['b','a'])
 def test_saved_state_owns_order_when_enabled(self):self.assertEqual(model({'config_xml':RAW,'save_state':True,'element_names':'b,a'})[1],['a','hidden','b'])
 def test_boolean_save_key(self):self.assertEqual(model({'config_xml':RAW,'save_state':'true'})[2],'save_state|main_tab')
 def test_inline_not_reordered_by_saved(self):
  m,n,_=model({'config_xml':RAW,'save_state':'x'},saved='<config><tab><element name="b" title="changed"/><element name="c"/></tab></config>')
  self.assertEqual(n,['a','hidden','b','c']);self.assertEqual(m.describe('b')['title'],'Beta')
 def test_saved_without_inline(self):self.assertEqual(model({'save_state':'x'},saved='<config><tab><element name="only"/></tab></config>')[1],['only'])
 def test_last_include_wins(self):
  a='<config><custom><element name="a"/></custom></config>';b=a.replace('"a"','"b"');self.assertEqual(model({'view':'custom','include':'a|b'},include={'a':a,'b':b})[1],['b'])
 def test_last_missing_include_falls_back_to_db(self):
  a='<config><custom><element name="a"/></custom></config>';b='<config><other/></config>';d=a.replace('"a"','"db"')
  self.assertEqual(model({'view':'custom','include':'a|b'},include={'a':a,'b':b},db={'custom':d})[1],['db'])
 def test_unknown_named_view_empty(self):self.assertEqual(model({'view':'unknown'})[1],[])
 def test_default_untitled(self):self.assertEqual(model({'view':'tab'})[1],['untitled'])
 def test_explicit_empty_stays_empty(self):self.assertEqual(model({'config_xml':'<config><tab/></config>'})[1],[])
 def test_hidden_indices_not_renumbered(self):
  m,n,_=model();items=tab_items(parent(),m,n,lambda e,s:'fixture/item?code=1');self.assertEqual([i['id'] for i in items],['root/~tab/0','root/~tab/2'])
 def test_selected_is_original_name(self):
  m,n,_=model();items=tab_items(parent({'selected':'b'}),m,n,lambda e,s:'fixture/item?code=1');self.assertEqual([i['name'] for i in items if i['selected']],['b'])
 def test_preload_attribute(self):
  m,n,_=model();self.assertTrue(tab_items(parent(),m,n,lambda e,s:'fixture/item?code=1')[1]['preload'])
 def test_is_visible_is_not_display(self):
  m,n,_=model({'config_xml':RAW.replace('display="false"','is_visible="false"')});self.assertEqual(len(tab_items(parent(),m,n,lambda e,s:'x')),3)
 def test_show_remove_false(self):
  m,n,_=model();self.assertFalse(any(c['removable'] for c in tab_items(parent({'show_remove':'false'}),m,n,lambda e,s:'x')))
 def test_protected_names(self):
  m,n,_=model();items=tab_items(parent({'show_remove_tabs':'a'}),m,n,lambda e,s:'x');self.assertFalse(items[0]['removable']);self.assertTrue(items[1]['removable'])
 def test_state_bound_expression(self):
  seen=[];m,n,_=model();items=tab_items(parent({'state':{'x':0},'search_key':'fixed'}),m,n,lambda e,s:seen.append(s) or 'fixed');self.assertEqual(seen,[{'x':0,'search_key':'fixed'}]);self.assertEqual(items[-1]['options']['search_key'],'fixed')
 def test_expression_without_provider_rejected(self):
  m,n,_=model()
  with self.assertRaises(ValueError):tab_items(parent(),m,n)
 def test_oversized_container_rejected(self):
  with self.assertRaises(ValueError):model({'config_xml':RAW,'element_names':[str(i) for i in range(65)]})
 def test_external_xml_not_loaded(self):
  with self.assertRaises(ValueError):model({'config_xml':'<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><config><tab/></config>'})
 def test_hidden_direct_api_route_rejected(self):
  b=ExtendedBackend({'allow_writes':False});p=parent();p.update(kind='tabs',view='tab',handler='tactic.ui.container.TabWdg',title='Tabs')
  b._tree=lambda:([],{'root':p});b._tab_model=lambda t:model();b.view=lambda *a,**kw:{'fields':[]}
  with patch('pyasm.search.Search.eval',return_value='fixture/item?code=1'):
   self.assertEqual(b.open_target('root/~tab/0')['kind'],'table')
   with self.assertRaises(ApiError) as cm:b.open_target('root/~tab/1')
   self.assertEqual(cm.exception.status,403)
 def test_depth_limit(self):
  with self.assertRaises(ApiError):ExtendedBackend({}).open_target('root'+'/~tab/0'*9)

class EditTests(unittest.TestCase):
 def test_edit_short_handler_kind(self):self.assertEqual(target_spec('EditWdg',{'search_type':'fixture/item'},{} )['kind'],'form')
 def test_default_direct_view_edit(self):self.assertEqual(target_spec('tactic.ui.panel.EditWdg',{},{} )['view'],'edit')
 def test_json_defaults(self):self.assertEqual(default_values('{"a":0,"b":null}'),{'a':0,'b':None})
 def test_python_literal_defaults(self):self.assertEqual(default_values("{'x': False, 's': 'Привет'}"),{'x':False,'s':'Привет'})
 def test_defaults_copied(self):
  a={'x':[1]};b=default_values(a);b['x'].append(2);self.assertEqual(a,{'x':[1]})
 def test_defaults_not_code(self):
  with self.assertRaises((ValueError,SyntaxError)):default_values("__import__('os').getcwd()")
 def test_defaults_non_object(self):
  with self.assertRaises(ValueError):default_values('[1,2]')
 def test_defaults_nonfinite(self):
  with self.assertRaises(ValueError):default_values({'x':float('nan')})
 def test_defaults_nonstring_key(self):
  with self.assertRaises(ValueError):default_values({1:'a'})
 def test_inline_form_definitions(self):
  base=ConfigModel('edit',[ConfigSource('<config><edit><element name="old"/></edit><edit_definition/></config>','edit')])
  resolved=resolve_edit(base,{'config_xml':'<config><edit><element name="x" title="Own"/></edit><tab><element name="y"/></tab></config>'})
  self.assertEqual(resolved.names(),['x']);self.assertEqual(resolved.describe('x')['title'],'Own')
 def test_inline_tab_fallback(self):
  b=ConfigModel('edit',[]);self.assertEqual(resolve_edit(b,{'config_xml':'<config><tab><element name="x"/></tab></config>'}).names(),['x'])
 def test_explicit_field_order_uses_existing_defs(self):
  b=ConfigModel('edit',[ConfigSource('<config><edit><element name="x" title="X"/><element name="y"/></edit></config>','edit')]);r=resolve_edit(b,{'element_names':'y,x'});self.assertEqual(r.names(),['y','x']);self.assertEqual(r.describe('x')['title'],'X')
 def test_custom_layout_not_silently_discarded(self):
  with self.assertRaises(ValueError):resolve_edit(ConfigModel('edit',[]),{'layout_view':'custom'})
 def test_custom_edit_resolution_matches_original_method(self):
  # Execute ORIGINAL get_config method body with DB/file collaborators replaced.
  src=ast.parse((R/'src/tactic/ui/panel/edit_wdg.py').read_text());cls=next(n for n in src.body if isinstance(n,ast.ClassDef) and n.name=='EditWdg');fn=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_config'));fn.decorator_list=[]
  for existing in (True,False):
   for mode in ('edit','insert'):
    db=types.SimpleNamespace(get_by_search_type=lambda st,v:('db:'+v) if v!='custom' or existing else None)
    class View:
     def __init__(self,st,v,c,layout):self.configs=c
     @staticmethod
     def get_configs_from_file(st,v):return ['file:'+v]
    ns={'WidgetDbConfig':db,'WidgetConfigView':View};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'original.EditWdg.get_config','exec'),ns)
    expected=ns['get_config'](types.SimpleNamespace(search_type='fixture/item',view='custom',mode=mode)).configs
    with patch('pyasm.search.WidgetDbConfig',db),patch('tactic.core.widget_config.WidgetConfigView',View),patch.object(ConfigModel,'from_tactic',side_effect=lambda v:v.configs):
     self.assertEqual(edit_base_model('fixture/item','custom',mode),expected)

class FormBindingTests(unittest.TestCase):
 def setUp(self):self.b=WidgetService();self.opened={'kind':'form','form_binding':{'key':'fixture/item?code=1','mode':'edit'}}
 def test_same_record_allowed(self):self.b.check_form_binding(self.opened,{'key':'fixture/item?code=1'},'PATCH','/record')
 def test_foreign_record_rejected(self):
  with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{'key':'fixture/item?code=2'},'PATCH','/record')
 def test_missing_bound_key_rejected(self):
  with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{},'PATCH','/record')
 def test_metadata_not_requiring_record(self):
  for route in ('/view','/resolved-view'):self.b.check_form_binding(self.opened,{},'GET',route)
 def test_form_not_table(self):
  for route in ('/query','/timeline','/export-csv'):
   with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{'key':'fixture/item?code=1'},'POST',route)
 def test_view_readonly(self):
  self.opened['form_binding']['mode']='view'
  with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{'key':'fixture/item?code=1'},'PATCH','/record')
 def test_insert_cannot_update(self):
  self.opened['form_binding']={'key':None,'mode':'insert'}
  with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{},'PATCH','/record')
 def test_edit_cannot_create(self):
  with self.assertRaises(ApiError):self.b.check_form_binding(self.opened,{'key':'fixture/item?code=1'},'POST','/record')
 def test_table_contract_unaffected(self):self.b.check_form_binding({'kind':'table'},{},'POST','/query')
 def test_mutable_insert_defaults_cleaned(self):
  b=WidgetService();opened={'kind':'form','search_type':'fixture/item','form_binding':{'key':None,'mode':'insert'},'options':{}}
  b.open_target=lambda t:opened;b.prepare_form=lambda *a:{'spec':{'fields':[{'name':'x','read_only':False,'kind':'integer','nullable':True}],'capabilities':{'create':True}},'defaults':{'x':0}};b.create=lambda st,values,spec:values
  self.assertEqual(b.embedded_form('POST',{'target':'root','values':{}}),{'x':0})
 def test_binding_resolved_from_server_search_key(self):
  obj=Mock();obj.get_base_search_type.return_value='fixture/item';obj.get_search_key.return_value='fixture/item?code=1'
  b=WidgetService();b.require_type=lambda st:None;b._object=lambda st,k:obj
  with patch('pyasm.search.Search.get_by_search_key',return_value=obj):
   target=b.bind_form_target({'kind':'form','search_type':'fixture/item','options':{'search_key':'fixture/item?code=1'}})
  self.assertEqual(target['form_binding'],{'key':'fixture/item?code=1','mode':'edit'})
 def test_binding_type_disagreement_denied(self):
  obj=Mock();obj.get_base_search_type.return_value='sthpw/login'
  with patch('pyasm.search.Search.get_by_search_key',return_value=obj):
   with self.assertRaises(ApiError):WidgetService().bind_form_target({'search_type':'fixture/item','options':{'search_key':'sthpw/login?code=x'}})
 def test_missing_object_no_insert_fallback(self):
  with patch('pyasm.search.Search.get_by_search_key',return_value=None):
   with self.assertRaises(ApiError):WidgetService().bind_form_target({'search_type':'fixture/item','options':{'search_key':'fixture/item?code=gone'}})

class MenuTests(unittest.TestCase):
 def get(self,scope,id,**ctx):return next(a for a in menu_items(scope,ctx) if a.get('id')==id)
 def test_row_edit_disabled_without_right(self):self.assertFalse(self.get('row','edit',can_edit=False)['enabled'])
 def test_row_delete_not_reinterpreted_as_retire(self):self.assertFalse(self.get('row','delete',can_delete=True)['enabled'])
 def test_retired_label(self):self.assertEqual(self.get('row','state',can_retire=True,retired=True)['legacy_label'],'Reactivate')
 def test_header_exact_sort_direction(self):self.assertTrue(self.get('column','sort_asc',sortable=True)['enabled'])
 def test_nonstorage_not_sortable(self):self.assertFalse(self.get('column','sort_desc',sortable=False)['enabled'])
 def test_local_group_not_claimed_server_group(self):self.assertFalse(self.get('column','legacy_group')['enabled']);self.assertTrue(self.get('column','group_page',storage=True)['enabled'])
 def test_definition_admin_permission(self):self.assertFalse(self.get('sidebar','definition',admin=False)['enabled'])
 def test_source_remove_link_not_arbitrary_delete(self):self.assertFalse(self.get('sidebar','remove_link',admin=True)['enabled'])
 def test_nonremovable_tab_no_close(self):self.assertNotIn('close',[a.get('id') for a in menu_items('tab',{'removable':False})])
 def test_tear_off_not_claimed(self):self.assertFalse(self.get('tab','tear_off')['enabled'])
 def test_readonly_field_no_reset(self):self.assertFalse(self.get('form-field','reset_field',editable=False)['enabled'])
 def test_not_nullable_no_null(self):self.assertFalse(self.get('form-field','null_field',editable=True,nullable=False)['enabled'])
 def test_no_executable_callbacks(self):
  for scope in ('row','column','sidebar','tab','form-field','widget'):
   self.assertNotIn('cbjs_action',json.dumps(menu_items(scope,{})))
 def test_unknown_scope_rejected(self):
  with self.assertRaises(ValueError):menu_items('anything',{})

if __name__=='__main__':unittest.main()
