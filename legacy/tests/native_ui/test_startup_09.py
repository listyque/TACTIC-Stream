"""Regression for the reported Api NameError and trusted class configuration."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'src/client'))
from pyasm.common import Common, Container
from tactic.core.widget_config import WidgetConfig, WidgetConfigView
spec=importlib.util.spec_from_file_location('context_registry_test',ROOT/'src/pyasm/web/context_registry.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)

class Startup09(unittest.TestCase):
 def test_original_and_fixed_real_registration_in_clean_process(self):
  result=subprocess.run([sys.executable,'-W','ignore',str(ROOT/'tests/native_ui/check_startup_contexts_09.py')],capture_output=True,text=True,timeout=40)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn('Original default context Api instantiated',result.stdout)
  self.assertIn('Site-specific XML-RPC tooling',result.stdout)
 def test_project_attribute_assignment(self):
  root=SimpleNamespace();p=registry.attach_project(root,'project-01',SimpleNamespace,'site_1');self.assertIs(registry.get_project(root,'project-01','site_1'),p)
 def test_names_are_data_not_code(self):
  for value in ('x;print(1)','x.y','../x','__dict__','',None):
   with self.subTest(value=value),self.assertRaises(ValueError):registry.route_segment(value)
 def test_context_directory_and_unknown_base(self):
  self.assertEqual(registry.load_contexts('/does/not/exist','sites','x'),{})
  with self.assertRaises(ValueError):registry.load_contexts('/does/not/exist','attacker','x')
 def test_import_and_constructor_errors_propagate(self):
  with tempfile.TemporaryDirectory() as tmp:
   Path(tmp,'Api.py').write_text('unused')
   with patch.object(registry.importlib,'import_module',side_effect=ModuleNotFoundError('inner dependency')):
    with self.assertRaisesRegex(ModuleNotFoundError,'inner dependency'):registry.load_contexts(tmp,'sites','x')
   with patch.object(registry.importlib,'import_module',return_value=SimpleNamespace()):
    with self.assertRaisesRegex(ImportError,'must export Api'):registry.load_contexts(tmp,'sites','x')
   with patch.object(registry.importlib,'import_module',return_value=SimpleNamespace(Api=lambda:(_ for _ in ()).throw(RuntimeError('ctor')))):
    with self.assertRaisesRegex(RuntimeError,'ctor'):registry.load_contexts(tmp,'sites','x')
 def test_classes_from_several_exec_calls_are_not_needed(self):
  with tempfile.TemporaryDirectory() as tmp:
   for name in ('Api','XMLRPC','UploadServer','__init__'):Path(tmp,name+'.py').write_text('unused')
   with patch.object(registry.importlib,'import_module',side_effect=lambda name:SimpleNamespace(**{name.rsplit('.',1)[-1]:SimpleNamespace})):
    self.assertEqual(list(registry.load_contexts(tmp,'sites','x')),['Api','UploadServer','XMLRPC'])
 def test_probe_bat_invokes_new_flag_utf8(self):
  sys.path.insert(0,str(ROOT/'tools/local'))
  import control
  a=control.parse(['check','startup']);c=control.effective(a,{'format':1},ROOT);v=control.plan_command(a,c,ROOT).argv
  self.assertIn('--check-startup',v);self.assertIn('utf8',v)
 def test_no_exec_eval_in_current_context_registration(self):
  import ast
  t=ast.parse((ROOT/'src/pyasm/web/cherrypy30_startup.py').read_text());m=next(n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='register_project')
  self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('exec','eval') for n in ast.walk(m)))

class ClassResolution09(unittest.TestCase):
 def setUp(self):
  Container.create();self.mod=ModuleType('config_test_mod09')
  class Layout:
   @staticmethod
   def get_default_display_handler(name):return 'native-test.'+name
   @staticmethod
   def has_config():return True
   @staticmethod
   def get_default_action():return 'OriginalSpecialAction'
  self.mod.Layout=Layout;self.patch=patch.dict(sys.modules,{'config_test_mod09':self.mod});self.patch.start()
 def tearDown(self):self.patch.stop()
 def test_resolve_without_constructor(self):self.assertIs(Common.resolve_class('config_test_mod09.Layout'),self.mod.Layout)
 def test_no_eval_expression_allowed(self):
  for path in ('os.system("echo bad")','os..path','','x; x',None):
   with self.subTest(path=path),self.assertRaises(ValueError):Common.resolve_class(path)
 def test_missing_module_exception_preserved(self):
  with self.assertRaises(ModuleNotFoundError):Common.resolve_class('impossible_module_09.Layout')
 def test_missing_class_exception_preserved(self):
  with self.assertRaises(AttributeError):Common.resolve_class('config_test_mod09.Absent')
 def test_plugin_loader_contract(self):
  plugin=ModuleType('tactic.plugins');plugin.import_plugin=lambda name:SimpleNamespace(inside=SimpleNamespace(Layout=self.mod.Layout))
  with patch.dict(sys.modules,{'tactic.plugins':plugin}):self.assertIs(Common.resolve_class('tactic.plugins.demo.inside.Layout'),self.mod.Layout)
 def test_short_name_resolution_order(self):
  with patch('importlib.import_module',side_effect=lambda n:SimpleNamespace(Foo=n)):
   self.assertEqual(Common.resolve_class('Foo'),'pyasm.widget')
 def test_default_display_and_edit_use_original_class(self):
  c=WidgetConfigView(search_type=None,view='table',configs=[WidgetConfig.get(xml='<config><table><element name="cost"/></table></config>',view='table')])
  with patch.object(c,'get_layout_handler',return_value='config_test_mod09.Layout'):
   self.assertEqual(c.get_display_handler('cost'),'native-test.cost');self.assertEqual(c.get_edit_handler('cost'),'native-test.cost')
 def test_dynamic_has_config_uses_imported_class_on_python313(self):
  c=WidgetConfig.get(xml='<config><table><element name="nested"><display class="config_test_mod09.Layout"><config><element name="name"/></config></display></element></table></config>',view='table')
  self.assertIn('config_xml',c.get_display_options('nested'))
 def test_original_default_action_not_silently_lost(self):self.assertEqual(Common.resolve_class('config_test_mod09.Layout').get_default_action(),'OriginalSpecialAction')
if __name__=='__main__':unittest.main()
