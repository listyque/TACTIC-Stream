"""0.3 regression: real pure transformers and service boundaries, not a DB emulator.
Graph command tests replace DB collaborators only. No live PostgreSQL claim.
"""
import ast
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

R = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(R/'src'), str(R/'src/client')]
from tactic.core.graph_model import apply_graph_edits, graph_spec, normalize_workflow_settings
from tactic.core.view_edits import patch_view
from tactic.core.config_model import parse_xml, view_node
from tactic.ui_api.graph_service import GraphService
from tactic.ui_api.record_service import checked_file_path, related_id, decode_related_id
from tactic.ui_api.contracts import ApiError
from tactic.ui_api.extended_backend import ExtendedBackend

PIPE = '<pipeline custom="A &amp; B"><!--retain--><process name="first" type="manual" xpos="10" custom="preserve"><plugin config="yes"/></process><process name="second" type="approval"/><connect from="first" to="second" from_attr="success" extra="keep"/><extension mode="x"/></pipeline>'
VIEW = '<config custom="keep"><!--root--><table mode="x"><element name="name" title="Name" extra="keep"><display class="TextWdg"><width>120</width><custom><nested k="v"/></custom></display><action class="DatabaseAction"/></element><!--slot--><element name="separator"/><element name="separator"/><element name="amount"/></table><edit><element name="description"/></edit></config>'

class GraphTransformerTests(unittest.TestCase):
 def apply(self, ops): return apply_graph_edits(PIPE, 'pipeline', ops)
 def test_noop_preserves_extensions(self):
  root=parse_xml(self.apply([])['xml']);self.assertEqual(root.get('custom'),'A & B');self.assertEqual(root.find('extension').get('mode'),'x');self.assertEqual(root.find('process/plugin').get('config'),'yes')
 def test_move_preserves_unmentioned_attrs(self):
  root=parse_xml(self.apply([{'op':'update_node','name':'first','attributes':{'xpos':25,'ypos':-4}}])['xml']);self.assertEqual(root.find('process').get('custom'),'preserve');self.assertEqual(float(root.find('process').get('xpos')),25)
 def test_rename_updates_edges_and_returns_original_identity(self):
  result=self.apply([{'op':'rename_node','name':'first','new_name':'renamed'}]);self.assertEqual(result['renamed'],{'first':'renamed'});self.assertEqual(parse_xml(result['xml']).find('connect').get('from'),'renamed')
 def test_chained_rename_preserves_original_identity(self):
  result=self.apply([{'op':'rename_node','name':'first','new_name':'middle'},{'op':'rename_node','name':'middle','new_name':'last'}]);self.assertEqual(result['renamed'],{'first':'last'})
 def test_remove_renamed_returns_original_identity(self):
  result=self.apply([{'op':'rename_node','name':'first','new_name':'middle'},{'op':'remove_node','name':'middle'}]);self.assertEqual(result['removed'],['first']);self.assertEqual(result['renamed'],{})
 def test_add_then_remove_has_no_original_history(self):
  result=self.apply([{'op':'add_node','name':'new'},{'op':'remove_node','name':'new'}]);self.assertEqual(result['removed'],[])
 def test_add_then_rename_does_not_rename_existing_process(self):
  result=self.apply([{'op':'add_node','name':'new'},{'op':'rename_node','name':'new','new_name':'last'}]);self.assertEqual(result['renamed'],{})
 def test_rename_collision_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'rename_node','name':'first','new_name':'second'}])
 def test_remove_node_only_removes_its_edges(self):
  root=parse_xml(self.apply([{'op':'remove_node','name':'first'}])['xml']);self.assertEqual([n.get('name') for n in root.findall('process')],['second']);self.assertEqual(root.findall('connect'),[]);self.assertIsNotNone(root.find('extension'))
 def test_custom_node_preserved_when_moved(self):
  text=PIPE.replace('type="manual"','type="custom.plugin"');result=apply_graph_edits(text,'pipeline',[{'op':'update_node','name':'first','attributes':{'xpos':33}}]);self.assertEqual(parse_xml(result['xml']).find('process').get('type'),'custom.plugin')
 def test_new_custom_type_is_not_instantiated(self):
  with self.assertRaises(ValueError):self.apply([{'op':'add_node','name':'third','attributes':{'type':'custom.plugin'}}])
 def test_empty_name_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'add_node','name':' '}])
 def test_nan_coordinate_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update_node','name':'first','attributes':{'xpos':float('nan')}}])
 def test_infinite_coordinate_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update_node','name':'first','attributes':{'ypos':'Infinity'}}])
 def test_bool_coordinate_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update_node','name':'first','attributes':{'xpos':True}}])
 def test_setting_cannot_be_smuggled_as_xml_attribute(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update_node','name':'first','attributes':{'settings':'{}'}}])
 def test_unknown_operation_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'execute_python'}])
 def test_json_array_size_bounded(self):
  with self.assertRaises(ValueError):self.apply([{}]*501)
 def test_edge_index_bool_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'remove_edge','index':True}])
 def test_port_update_preserves_extra_attrs(self):
  root=parse_xml(self.apply([{'op':'update_edge','index':0,'attributes':{'from_attr':'fail','to_attr':'input'}}])['xml']);edge=root.find('connect');self.assertEqual(edge.get('extra'),'keep');self.assertEqual(edge.get('from_attr'),'fail')
 def test_multiple_edges_use_sequential_indices(self):
  result=self.apply([{'op':'add_edge','from':'second','to':'first'},{'op':'remove_edge','index':0}]);edge=parse_xml(result['xml']).find('connect');self.assertEqual(edge.get('from'),'second')
 def test_unknown_edge_endpoint_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'add_edge','from':'first','to':'missing'}])
 def test_schema_does_not_rename_types(self):
  with self.assertRaises(ValueError):apply_graph_edits('<schema><search_type name="p/a"/></schema>','schema',[{'op':'rename_node','name':'p/a','new_name':'p/b'}])
 def test_schema_instance_connection(self):
  text='<schema><search_type name="p/a"/><search_type name="p/b"/></schema>'
  root=parse_xml(apply_graph_edits(text,'schema',[{'op':'add_edge','from':'p/a','to':'p/b','attributes':{'relationship':'instance','instance_type':'p/a_in_b','from_col':'a_code','to_col':'b_code'}}])['xml']);self.assertEqual(root.find('connect').get('instance_type'),'p/a_in_b')
 def test_schema_inherited_endpoints_preserved(self):
  text='<schema><search_type name="p/a"/><connect from="p/a" to="sthpw/task" relationship="search_type"/></schema>';self.assertEqual(len(graph_spec(apply_graph_edits(text,'schema',[])['xml'],'schema')['edges']),1)
 def test_wrong_root_rejected(self):
  with self.assertRaises(ValueError):apply_graph_edits('<config/>','pipeline',[])
 def test_duplicate_source_node_rejected(self):
  with self.assertRaises(ValueError):apply_graph_edits('<pipeline><process name="x"/><process name="x"/></pipeline>','pipeline',[])
 def test_dtd_rejected(self):
  with self.assertRaises(ValueError):graph_spec('<!DOCTYPE pipeline [<!ENTITY a "x">]><pipeline/>','pipeline')
 def test_coordinates_bad_source_render_with_fallback(self):
  spec=graph_spec(PIPE.replace('xpos="10"','xpos="nan"'),'pipeline');self.assertEqual(spec['nodes'][0]['x'],60)

class WorkflowSettingsTests(unittest.TestCase):
 def test_nested_merge_preserves_extensions(self):
  old={'a':{'x':1,'y':2},'plugin':{'v':3}};result=GraphService._merge_settings(old,{'a':{'x':4}});self.assertEqual(result,{'a':{'x':4,'y':2},'plugin':{'v':3}});self.assertEqual(old['a']['x'],1)
 def test_patch_validation_returns_independent_copy(self):
  v={'progress':{'related_search_type':'p/a'}};result=normalize_workflow_settings(v);result['progress']['x']=1;self.assertNotIn('x',v['progress'])
 def test_nested_script_rejected(self):
  with self.assertRaises(ValueError):normalize_workflow_settings({'default':{'script':'print(1)'}})
 def test_callback_rejected(self):
  with self.assertRaises(ValueError):normalize_workflow_settings({'_cbk_classes':[]})
 def test_trigger_identity_cannot_be_injected(self):
  with self.assertRaises(ValueError):normalize_workflow_settings({'progress':{'trigger_code':'someone_elses_trigger'}})
 def test_deep_patch_rejected(self):
  v={};current=v
  for _ in range(20):current['a']={};current=current['a']
  with self.assertRaises(ValueError):normalize_workflow_settings(v)
 def test_nan_settings_rejected(self):
  with self.assertRaises(ValueError):normalize_workflow_settings({'value':float('nan')})
 def test_array_root_rejected(self):
  with self.assertRaises(ValueError):normalize_workflow_settings([])

class ViewPatchTests(unittest.TestCase):
 def apply(self, ops):return parse_xml(patch_view(VIEW,'table',ops))
 def test_other_views_survive(self):self.assertEqual(self.apply([{'op':'remove','index':3}]).find('edit/element').get('name'),'description')
 def test_duplicate_separators_reorder_by_index(self):
  root=self.apply([{'op':'reorder','order':[3,1,0,2]}]);self.assertEqual([n.get('name') for n in root.find('table') if n.tag=='element'],['amount','separator','name','separator'])
 def test_partial_attribute_patch_keeps_unknowns(self):
  root=self.apply([{'op':'update','index':0,'attributes':{'title':'Имя'}}]);self.assertEqual(root.find('table/element').get('extra'),'keep');self.assertEqual(root.find('table/element').get('title'),'Имя')
 def test_handler_options_keep_unmodified_nodes(self):
  root=self.apply([{'op':'update','index':0,'display':{'options':{'width':'200'}}}]);self.assertEqual(root.find('table/element/display/custom/nested').get('k'),'v');self.assertEqual(root.findtext('table/element/display/width'),'200');self.assertEqual(root.find('table/element/action').get('class'),'DatabaseAction')
 def test_nested_option_not_flattened(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update','index':0,'display':{'options':{'custom':'gone'}}}])
 def test_option_null_removes_override(self):self.assertIsNone(self.apply([{'op':'update','index':0,'display':{'options':{'width':None}}}]).find('table/element/display/width'))
 def test_attribute_null_restores_inheritance(self):self.assertIsNone(self.apply([{'op':'update','index':0,'attributes':{'title':None}}]).find('table/element').get('title'))
 def test_invalid_attributes_shape(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update','index':0,'attributes':[]}])
 def test_invalid_options_shape(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update','index':0,'display':{'options':[]}}])
 def test_duplicate_new_element_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'add','name':'name'}])
 def test_invalid_order_duplicates_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'reorder','order':[0,1,1,3]}])
 def test_invalid_order_boolean_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'reorder','order':[False,1,2,3]}])
 def test_invalid_class_expression_rejected(self):
  with self.assertRaises(ValueError):self.apply([{'op':'update','index':0,'display':{'class':'eval(x)'}}])
 def test_at_view_names(self):
  raw='<config><view name="custom@table"><element name="a"/></view></config>';root=parse_xml(patch_view(raw,'custom@table',[{'op':'update','index':0,'attributes':{'width':'140'}}]));self.assertEqual(root.find('view/element').get('width'),'140')
 def test_add_operation_preserves_definition_inheritance(self):self.assertIsNone(self.apply([{'op':'add','name':'created'}]).find('table/element[@name="created"]/display'))

class FileBoundaryTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'repo').mkdir();(self.root/'repo/a.txt').write_text('test');(self.root/'private.txt').write_text('private')
 def test_registered_path_in_repo(self):self.assertEqual(checked_file_path(self.root/'repo/a.txt',[self.root/'repo']),self.root/'repo/a.txt')
 def test_parent_escape_rejected(self):
  with self.assertRaises(ApiError) as cm:checked_file_path(self.root/'repo/../private.txt',[self.root/'repo'])
  self.assertEqual(cm.exception.status,403)
 def test_missing_path_is_404(self):
  with self.assertRaises(ApiError) as cm:checked_file_path(self.root/'repo/missing',[self.root/'repo'])
  self.assertEqual(cm.exception.status,404)
 def test_no_roots_denies(self):
  with self.assertRaises(ApiError):checked_file_path(self.root/'repo/a.txt',[])
 def test_symlink_escape_denied(self):
  try:(self.root/'repo/link').symlink_to(self.root/'private.txt')
  except OSError:self.skipTest('Symlinks unavailable')
  with self.assertRaises(ApiError):checked_file_path(self.root/'repo/link',[self.root/'repo'])
 def test_prefix_sibling_is_not_repo(self):
  (self.root/'repo-else').mkdir();(self.root/'repo-else/a').write_text('x')
  with self.assertRaises(ApiError):checked_file_path(self.root/'repo-else/a',[self.root/'repo'])
 def test_related_key_keeps_full_project_identity(self):
  value='p/item?project=one&code=BIG123';encoded=related_id('root/id',value,'p/child').split('/~related/')[1];self.assertEqual(decode_related_id(encoded),[value,'p/child'])
 def test_related_invalid_encoding_denied(self):
  with self.assertRaises(ApiError):decode_related_id('not-valid-json')
 def test_related_overlong_denied(self):
  with self.assertRaises(ApiError):decode_related_id('x'*3501)

class ServiceGuardTests(unittest.TestCase):
 def setUp(self):
  self.b=ExtendedBackend({'allow_writes':True});self.b._project=lambda:'fixture';self.b._write=lambda fn:fn()
  p=patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:True));p.start();self.addCleanup(p.stop)
 def test_graph_invalid_kind_rejected(self):
  with self.assertRaises(ApiError) as cm:self.b.graph_operation('GET',{'kind':'arbitrary'})
  self.assertEqual(cm.exception.status,400)
 def test_builtin_schema_write_rejected(self):
  self.b._project=lambda:'admin';self.b._object=lambda *a:Mock(get_code=lambda:'sthpw',get_value=lambda n,*a,**kw:'<schema/>')
  with self.assertRaises(ApiError) as cm:self.b.graph_operation('PATCH',{'kind':'schema','key':'x'})
  self.assertEqual(cm.exception.code,'builtin_schema')
 def test_bad_graph_create_code_rejected(self):
  with self.assertRaises(ApiError):self.b.graph_operation('POST',{'kind':'pipeline','code':'x;DROP'})
 def test_graph_nonadmin_cannot_read(self):
  with patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:False)):
   with self.assertRaises(ApiError):self.b.graph_operation('GET',{'kind':'pipeline'})
 def test_bulk_invalid_unhashable_key_is_400(self):
  self.b.open_target=lambda *a:{'kind':'table','search_type':'p/a'}
  with self.assertRaises(ApiError) as cm:self.b.record_operation('PATCH','/bulk-records',{'records':[{'key':[]}]})
  self.assertEqual(cm.exception.status,400)
 def test_bulk_duplicate_keys_rejected(self):
  self.b.open_target=lambda *a:{'kind':'table','search_type':'p/a'}
  with self.assertRaises(ApiError):self.b.record_operation('PATCH','/bulk-records',{'records':[{'key':'x'},{'key':'x'}]})
 def test_bulk_conflict_no_commands_run(self):
  self.b.open_target=lambda *a:{'kind':'table','search_type':'p/a'};self.b._object=lambda *a:Mock();self.b.form=lambda *a:{'record':{'revision':'new'},'spec':{'fields':[]}}
  with patch('tactic.core.native_edit.NativeEditCmd') as cmd:
   with self.assertRaises(ApiError) as cm:self.b.record_operation('PATCH','/bulk-records',{'records':[{'key':'x','revision':'old','values':{}}]})
   cmd.assert_not_called()
  self.assertEqual(cm.exception.status,409)
 def test_api_admin_action_must_match_configured_target(self):
  self.b.open_target=lambda *a:{'kind':'pipeline'}
  with self.assertRaises(ApiError) as cm:self.b.admin_operation('POST','/users',{'target':'x'})
  self.assertEqual(cm.exception.code,'target_denied')
 def test_security_builtin_admin_protected(self):
  self.b.open_target=lambda *a:{'kind':'security'};self.b._object=lambda *a:Mock(get_value=lambda n:'admin' if n=='login_group' else '<rules/>')
  with self.assertRaises(ApiError) as cm:self.b.admin_operation('PATCH','/security',{'target':'x','key':'x','xml':'<rules/>'})
  self.assertEqual(cm.exception.code,'admin_group')

class LocalLaunchSourceTests(unittest.TestCase):
 def test_batch_files_crlf_and_quoted_project_path(self):
  files=list(R.glob('*.bat'));self.assertEqual(sorted(p.name for p in files),['MANAGE_TACTIC.bat','SETUP_ENV.bat','START_TACTIC.bat'])
  for p in files:
   raw=p.read_bytes();self.assertIn(b'\r\n',raw);self.assertIn(b'%~dp0',raw);self.assertIn(b'DisableDelayedExpansion',raw)
 def test_launcher_does_not_import_test_fixture(self):
  text=(R/'tools/local/launch.py').read_text();tree=ast.parse(text)
  names=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)];self.assertFalse(any('fixture' in str(n) for n in names));self.assertIn('pyasm.web.cherrypy30_startup',names)
 def test_download_manifest_pins_python_hash(self):
  data=json.loads((R/'tools/local/runtime-manifest.json').read_text());self.assertEqual(len(data['python']['sha256']),64);self.assertTrue(data['python']['url'].startswith('https://www.python.org/ftp/python/'))
 def test_script_does_not_silently_override_unknown_runtime(self):
  text=(R/'tools/local/setup_env.ps1').read_text(encoding='utf-8-sig');self.assertIn('Unknown runtime',text);self.assertIn('Get-FileHash',text);self.assertIn('Get-AuthenticodeSignature',text);self.assertIn('--only-binary=:all:',text)
 def test_sqlite_upgrade_imports_are_python3_relative(self):self.assertIn('from .sql_convert import *',(R/'src/pyasm/search/upgrade/sqlite/__init__.py').read_text())
 def test_upgrade_no_removed_imp_module(self):
  tree=ast.parse((R/'src/pyasm/search/upgrade/upgrade_db.py').read_text());self.assertFalse(any(isinstance(n,ast.Import) and any(x.name=='imp' for x in n.names) for n in ast.walk(tree)))
 def test_original_date_string_regression(self):
  from pyasm.common import SPTDate
  self.assertEqual(SPTDate.convert('2026-09-30T12:30:00+00:00'),datetime(2026,9,30,12,30))
 def test_original_date_only_noon_preserved(self):
  from pyasm.common import SPTDate
  self.assertEqual(SPTDate.convert(date(2026,9,30)),datetime(2026,9,30,12))
 def test_invalid_date_type_rejected(self):
  from pyasm.common import SPTDate
  with self.assertRaises(TypeError):SPTDate.convert(12)
 def test_windows_kronos_exports_no_missing_fork_names(self):
  import os
  fake=Mock();fake.path=os.path # Only hasattr(os, 'fork') is tested in this module.
  class NoFork:
   def __getattr__(self,name):
    if name=='fork':raise AttributeError(name)
    return getattr(os,name)
  scope={'__name__':'kronos_without_fork'}
  with patch.dict(sys.modules,{'os':NoFork()}):exec(compile((R/'src/pyasm/command/kronos.py').read_text(),'kronos.py','exec'),scope)
  self.assertTrue(all(n in scope for n in scope['__all__']));self.assertNotIn('ForkedIntervalTask',scope['__all__'])

if __name__=='__main__':unittest.main()
