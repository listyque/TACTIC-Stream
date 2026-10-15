"""0.7 configuration contracts and differential real upstream resolver tests."""
import ast,copy,hashlib,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client'),str(R/'tools/native_ui')]
from tactic.core.config_model import ConfigModel,ConfigSource
from tactic.core.view_resolution import resolve_table,configured_sort,table_options
from tactic.core.widget_config import WidgetConfig,WidgetConfigView
from tactic.core.table_settings import TableSettingsMixin
from pyasm.common import Container
from audit_config_parity import audit
from column_test_store_07 import XML,INLINE,CODE_XML,model

class TableResolutionTests(unittest.TestCase):
 def setUp(self):Container.create();self.base=model();self.extra=ConfigSource('<config><custom><element name="extra"><display class="KnownCustom"/></element></custom></config>','custom','global-column')
 def original(self,layers,view='table'):
  return WidgetConfigView(search_type=None,view=view,configs=[WidgetConfig.get(xml=xml,view=v) for xml,v in layers])
 def test_plain_branch_matches_original(self):
  conf=self.original([(XML,'table'),(XML,'definition'),(self.extra.text,'custom')]);m=resolve_table(self.base,{},[self.extra]);self.assertEqual(m.names(),conf.get_element_names());self.assertEqual(m.handler('extra'),conf.get_display_handler('extra'))
 def test_inline_branch_precedes_names_and_code(self):
  loader=Mock(side_effect=AssertionError('Code must not run'));m=resolve_table(self.base,{'config_xml':INLINE,'config_code':'OTHER','element_names':'url'},[self.extra],loader)
  c=self.original([(INLINE,'table'),(XML,'table'),(XML,'definition')]);self.assertEqual(m.names(),c.get_element_names());self.assertEqual(m.options('amount'),c.get_display_options('amount'));self.assertNotIn(self.extra,m.sources);loader.assert_not_called()
 def test_inline_empty_view_is_not_fallback(self):self.assertEqual(resolve_table(self.base,{'config_xml':'<config><table/></config>'}).names(),[])
 def test_inline_missing_view_uses_original_order(self):self.assertEqual(resolve_table(self.base,{'config_xml':'<config><other/></config>'}).names(),self.base.names())
 def test_inline_wrapper_unwrapped_safely(self):self.assertEqual(resolve_table(self.base,{'config_xml':'<config_xml>'+INLINE+'</config_xml>'}).names(),['name','amount','code'])
 def test_inline_attributes_override_and_inherit(self):
  m=resolve_table(self.base,{'config_xml':INLINE});self.assertEqual(m.describe('name')['title'],'Имя из inline');self.assertEqual(m.describe('name')['attributes']['width'],'260');self.assertEqual(m.options('ratio')['format'],'-12.95%')
 def test_inline_does_not_mutate_base(self):
  before=self.base.fingerprint();resolve_table(self.base,{'config_xml':INLINE});self.assertEqual(before,self.base.fingerprint())
 def test_code_uses_only_stored_view(self):
  code=ConfigModel('card',[ConfigSource(CODE_XML,'card','code')]);m=resolve_table(self.base,{'config_code':'C','element_names':'name'},[self.extra],lambda c:code);self.assertIs(m,code);self.assertEqual(m.names(),['code']);self.assertEqual(len(m.sources),1)
 def test_missing_code_loader_fails(self):
  with self.assertRaises(ValueError):resolve_table(self.base,{'config_code':'C'})
 def test_invalid_code_not_executable(self):
  for value in ('../secret','C()','x;import os',{'bad':1},'x'*201):
   with self.subTest(value=value),self.assertRaises(ValueError):resolve_table(self.base,{'config_code':value},code_loader=lambda c:None)
 def test_element_names_reorders_not_definitions(self):
  m=resolve_table(self.base,{'element_names':'ratio, name, extra'},[self.extra]);self.assertEqual(m.names(),['ratio','name','extra']);self.assertEqual(m.options('ratio')['format'],'-12.95%');self.assertEqual(m.handler('extra'),'KnownCustom')
 def test_names_xml_is_escaped_not_injected(self):
  m=resolve_table(self.base,{'element_names':['x"/><element name="injected']});self.assertEqual(m.names(),['x"/><element name="injected'])
 def test_names_limit(self):
  with self.assertRaises(ValueError):resolve_table(self.base,{'element_names':['x']*501})
 def test_duplicate_definitions_keep_original_handler(self):
  xml='<config><table><element name="x" title="first"/><element name="x"><display class="D"><a> second </a></display></element></table></config>';m=ConfigModel('table',[ConfigSource(xml,'table')]);c=self.original([(xml,'table')]);self.assertEqual(m.handler('x'),c.get_display_handler('x'));self.assertEqual(m.options('x'),c.get_display_options('x'));self.assertEqual(m.attributes('x'),c.get_element_attributes('x'))
 def test_scalar_whitespace_not_stripped(self):
  xml='<config><table><element name="x"><display><a>  exact\n </a></display></element></table></config>';self.assertEqual(ConfigModel('table',[ConfigSource(xml,'table')]).options('x')['a'],'  exact\n ')
 def test_nested_options_use_dict_not_xml_string(self):
  xml='<config><table><element name="x"><display><state><search_type>prod/shot</search_type></state></display></element></table></config>';m=ConfigModel('table',[ConfigSource(xml,'table')]);self.assertEqual(m.options('x'),self.original([(xml,'table')]).get_display_options('x'))
 def test_stock_table_inline_config_conversion(self):
  xml='<config><table><element name="x"><display class="tactic.ui.panel.TableLayoutWdg"><config><element name="code"/></config></display></element></table></config>';m=ConfigModel('table',[ConfigSource(xml,'table')]);self.assertEqual(m.options('x'),self.original([(xml,'table')]).get_display_options('x'));self.assertIn('<table>',m.options('x')['config_xml'])
 def test_original_settings_extraction_ast(self):
  ref=ast.parse((R/'tests/native_ui/reference_07/base_table_layout_wdg_06.py.txt').read_text());old=next(n for n in ast.walk(ref) if isinstance(n,ast.FunctionDef) and n.name=='get_setting');new=ast.parse((R/'src/tactic/core/table_settings.py').read_text());fun=next(n for n in ast.walk(new) if isinstance(n,ast.FunctionDef) and n.name=='get_setting');self.assertEqual(ast.dump(old),ast.dump(fun))
 def test_settings_pipe_and_explicit_override(self):
  f=table_options({'settings':'search|insert','show_column_manager':'true'});self.assertTrue(f['show_search']);self.assertTrue(f['show_column_manager']);self.assertFalse(f['show_layout_switcher']);self.assertFalse(f['show_search_limit'])
 def test_original_default_setting_flags(self):
  opts={'show_search_limit':False,'show_keyword_search':'false'};f=table_options(opts)
  for name in ('search_limit','keyword_search','column_manager','search','layout_switcher'):self.assertEqual(f['show_'+name],bool(TableSettingsMixin.get_setting(SimpleNamespace(kwargs=opts),name)))
 def test_explicit_display_flags_and_tile(self):
  f=table_options({'show_header':'false','show_select':False,'show_shelf':'false','show_context_menu':'none','native_layout':'cards'});self.assertEqual(f['initial_mode'],'cards');self.assertFalse(f['show_header']);self.assertFalse(f['show_select']);self.assertFalse(f['show_shelf']);self.assertFalse(f['show_context_menu'])
 def test_bounded_configured_page_size(self):
  self.assertEqual(table_options({'search_limit':'20'})['page_size'],20);self.assertEqual(table_options({})['page_size'],100);self.assertTrue(table_options({'search_limit':'-1'})['limit_notice']);self.assertEqual(table_options({'search_limit':'300'})['page_size'],200)
 def test_all_shipped_xml_metadata_differential(self):
  report=audit();self.assertEqual(report['files'],80);self.assertGreaterEqual(report['views'],480);self.assertEqual(report['differences'],[]);self.assertEqual(report['errors'],[])

class OptionWriteTests(unittest.TestCase):
 def test_nested_settings_roundtrip(self):
  import xml.etree.ElementTree as ET
  from tactic.core.config_options import append_option,options_from_node
  n=ET.Element('display');options={'settings':{'search':'false','column_manager':'true'},'state':{'x':{'text':'  & <test>  '}},'config_xml':'<config><table/></config>'}
  for k,v in options.items():append_option(n,k,v)
  self.assertEqual(options_from_node(ET.fromstring(ET.tostring(n))),options)
 def test_unsafe_option_key_rejected(self):
  import xml.etree.ElementTree as ET
  from tactic.core.config_options import append_option
  with self.assertRaises(ValueError):append_option(ET.Element('display'),'bad/><x',1)
 def test_array_option_not_silently_rewritten(self):
  import xml.etree.ElementTree as ET
  from tactic.core.config_options import append_option
  with self.assertRaises(ValueError):append_option(ET.Element('display'),'nested',[1,2])

if __name__=='__main__':unittest.main()
