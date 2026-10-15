"""Targeted original XML updates, identity/authorization and console lifecycle."""
from pathlib import Path
import json, sys, unittest
from unittest.mock import patch
from types import SimpleNamespace
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.core import design_document as d
from tactic.core.config_model import target_spec
from tactic.ui_api import action_log as log
from tactic.ui_api.ui_state_service import validate_state,storage_key
from tactic.ui_api.contracts import ApiError
XML='''<config keep="root"><!-- keep comment --><test flag="x"><unknown a="1"><![CDATA[ unknown & <> ]]></unknown><kwargs><![CDATA[{"key":"value"}]]></kwargs><mako><![CDATA[<% x = "&" %>]]></mako><html id="main">leading &amp; text<div title="A &amp; B">Привет</div><style type="text/css"><![CDATA[.x {color:red}]]></style></html><behavior type="load"><![CDATA[var a = 1 < 2;]]></behavior></test><other id="keep"><![CDATA[private <unparsed> & preserved]]></other></config>'''
class Documents018(unittest.TestCase):
 def node(self,text,name='test'):return d.find_view(d.parse(text),name)
 def test_parts_match_original_sections(self):
  p=d.layout_parts(XML,'test');self.assertIn('<div',p['html']);self.assertNotIn('<style',p['html']);self.assertEqual(p['style'],'.x {color:red}');self.assertIn('<![CDATA[',p['behavior'])
 def test_html_leading_text_remains_escaped_fragment(self):self.assertIn('leading &amp; text',d.layout_parts(XML,'test')['html'])
 def test_html_part_can_roundtrip(self):self.assertEqual(self.node(d.patch_layout(XML,'test',{'html':d.layout_parts(XML,'test')['html']})).find('html').text,'leading & text')
 def test_css_edit_does_not_mutate_mako(self):self.assertEqual(d.serialize(self.node(XML).find('mako')),d.serialize(self.node(d.patch_layout(XML,'test',{'style':'.new{}'})).find('mako')))
 def test_css_edit_preserves_neighbor_cdata(self):self.assertEqual(d.serialize(self.node(XML,'other')),d.serialize(self.node(d.patch_layout(XML,'test',{'style':'b{}'}),'other')))
 def test_unknown_nodes_untouched(self):self.assertEqual(d.serialize(self.node(XML).find('unknown')),d.serialize(self.node(d.patch_layout(XML,'test',{'html':'<p>x</p>'})).find('unknown')))
 def test_comment_preserved(self):self.assertIn('<!-- keep comment -->',d.patch_layout(XML,'test',{'style':'b{}'}))
 def test_style_stays_inside_html(self):
  node=self.node(d.patch_layout(XML,'test',{'html':'<p>new</p>','style':'b { color:blue }'}));self.assertEqual(node.find('html/style').text,'b { color:blue }');self.assertIsNone(node.find('style'))
 def test_html_attributes_preserved(self):self.assertEqual(self.node(d.patch_layout(XML,'test',{'html':'<p/>'})).find('html').get('id'),'main')
 def test_multiple_styles_refuse_lossy_merge(self):
  with self.assertRaises(ValueError):d.layout_parts('<config><x><html><style/><style/></html></x></config>','x')
 def test_styles_in_html_section_refused(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'html':'<style>a</style>'})
 def test_style_closing_tag_refused(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'style':'</style><script>bad</script>'})
 def test_kwargs_literal_dictionary_allowed(self):self.assertIn('a',d.layout_parts(d.patch_layout(XML,'test',{'kwargs':"{'a': 'b'}"}),'test')['kwargs'])
 def test_kwargs_no_evaluation(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'kwargs':"__import__('os').system('echo BAD')"})
 def test_kwargs_root_must_be_dictionary(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'kwargs':'[]'})
 def test_behavior_multiple_blocks(self):
  x='<behavior type="load"><![CDATA[x++]]></behavior><behavior type="click"><![CDATA[y++]]></behavior>'
  self.assertEqual(d.layout_parts(d.patch_layout(XML,'test',{'behavior':x}),'test')['behavior'],x)
 def test_behavior_cannot_insert_unrelated_element(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'behavior':'<mako>bad</mako>'})
 def test_callbacks_preserve_other_views(self):
  x=d.patch_layout(XML,'test',{'callback':'<callback name="x"><![CDATA[a < b]]></callback>'});self.assertIn('<![CDATA[a < b]]>',x);self.assertIn('<other id="keep">',x)
 def test_copy_changes_only_selected_view_name(self):
  x=d.copy_view(XML,'test','<config><existing/></config>','copy');self.assertIsNotNone(self.node(x,'existing'));self.assertIsNone(self.node(x,'other'));self.assertEqual(self.node(x,'copy').get('flag'),'x')
 def test_copy_view_name_attribute(self):self.assertIsNotNone(self.node(d.copy_view(XML,'test','<config/>','a@b'),'a@b'))
 def test_copy_refuses_duplicate(self):
  with self.assertRaises(ValueError):d.copy_view(XML,'test','<config><copy/></config>','copy')
 def test_remove_keeps_neighbor(self):self.assertEqual(d.serialize(self.node(XML,'other')),d.serialize(self.node(d.remove_view(XML,'test'),'other')))
 def test_duplicate_view_rejected(self):
  with self.assertRaises(ValueError):d.layout_parts('<config><test/><view name="test"/></config>','test')
 def test_xml_entity_refused(self):
  with self.assertRaises(ValueError):d.parse('<!DOCTYPE config [<!ENTITY e SYSTEM "file:///etc/passwd">]><config>&e;</config>')
 def test_wrong_root_refused(self):
  with self.assertRaises(ValueError):d.parse('<html/>')
 def test_nul_refused(self):
  with self.assertRaises(ValueError):d.parse('<config>\0</config>')
 def test_size_bounded(self):
  with self.assertRaises(ValueError):d.bounded('a'*(d.MAX_BYTES+1))
 def test_section_unknown_refused(self):
  with self.assertRaises(ValueError):d.patch_layout(XML,'test',{'arbitrary':'x'})
 def test_view_name_no_path(self):
  for name in ('../file','<tag>','x/y','x()','',None):
   with self.subTest(name=name),self.assertRaises(ValueError):d.view_name(name)
 def test_no_style_preserves_html(self):self.assertEqual(d.layout_parts('<config><x><html><p>Text</p></html></x></config>','x')['html'],'<p>Text</p>')
 def test_empty_html(self):self.assertEqual(d.layout_parts('<config><x><html/></x></config>','x')['html'],'')
 def test_xhtml_ampersand_roundtrip(self):
  xml='<config><x><html><p>A &amp; B</p></html></x></config>';parts=d.layout_parts(xml,'x');self.assertEqual(d.layout_parts(d.patch_layout(xml,'x',{'html':parts['html']}),'x'),parts)
 def test_mako_cdata_with_cdata_terminator(self):
  result=d.patch_layout(XML,'test',{'mako':'value = "]]><"'});self.assertEqual(d.layout_parts(result,'test')['mako'],'value = "]]><"')

class StateAndRouting018(unittest.TestCase):
 def test_stype_state_has_native_storage_scope(self):self.assertTrue(storage_key('stype-editor','abc').startswith('native:ui:v1:stype-editor:'))
 def test_stype_selection_validated(self):self.assertEqual(validate_state('stype-editor',{'selected':'p/a','tab':'views'},{'types':['p/a']}),{'selected':'p/a','tab':'views'})
 def test_stype_unknown_type_denied(self):
  with self.assertRaises(ApiError):validate_state('stype-editor',{'selected':'p/b','tab':'columns'},{'types':['p/a']})
 def test_stype_drafts_not_persistable(self):
  with self.assertRaises(ApiError):validate_state('stype-editor',{'selected':'p/a','tab':'columns','script':'secret'},{'types':['p/a']})
 def test_layout_and_views_are_not_generic_config(self):
  for cls,kind in [('tactic.ui.tools.CustomLayoutEditWdg','layout-editor'),('tactic.ui.manager.ViewManagerWdg','views-manager'),('CustomLayoutWdg','custom-layout')]:self.assertEqual(target_spec(cls,{})['kind'],kind)
 def test_short_and_full_handlers_match(self):self.assertEqual(target_spec('ViewManagerWdg',{})['kind'],target_spec('tactic.ui.manager.ViewManagerWdg',{})['kind'])

class ConsoleLifecycle018(unittest.TestCase):
 def setUp(self):
  self.events=[];self.patches=[patch.object(log,'emit',side_effect=lambda e:self.events.append(dict(e))),patch.object(log,'ensure_monitor'),patch.object(log,'MODE','actions')]
  for p in self.patches:p.start()
 def tearDown(self):
  log.PENDING.clear()
  for p in reversed(self.patches):p.stop()
 def trace(self,route='/layout-document',method='PATCH'):
  t=log.RequestTrace(SimpleNamespace(path=route,method=method,headers={}), 'abc123').begin();self.addCleanup(lambda:log.TRACE.set(None));return t
 def test_start_before_finish(self):
  t=self.trace();t.identity(SimpleNamespace(login='admin',site=''));t.parameters({'project':'p','target':'layout','xml':'PRIVATE'});self.assertEqual(self.events[-1]['phase'],'start');t.finish(200,{});self.assertEqual(self.events[-1]['phase'],'end')
 def test_slow_request_has_progress(self):
  t=self.trace();t.parameters({'project':'p'});t.progress(t.started+6);self.assertEqual(self.events[-1]['phase'],'running');t.finish(200,{})
 def test_progress_has_actual_command_name(self):
  t=self.trace();t.parameters({});log.command_started(SimpleNamespace());t.progress(t.started+6);self.assertIn('SimpleNamespace',self.events[-1]['commands'][0]);t.finish(200,{})
 def test_fast_request_has_no_false_heartbeat(self):
  t=self.trace();t.parameters({});t.progress(t.started+.1);self.assertEqual(len(self.events),1);t.finish(200,{})
 def test_cleanup_on_error(self):
  t=self.trace();t.parameters({});t.finish(500,{},'ValueError');self.assertNotIn(id(t),log.PENDING);self.assertIsNone(log.TRACE.get());self.assertEqual(self.events[-1]['state'],'failed')
 def test_quiet_state_get_has_no_spam(self):
  t=self.trace('/ui-state','GET');t.parameters({});t.progress(t.started+10);t.finish(200,{});self.assertFalse(self.events)
 def test_quiet_error_is_visible(self):
  t=self.trace('/ui-state','GET');t.parameters({});t.finish(500,{},'ValueError');self.assertEqual(len(self.events),1)
 def test_sensitive_request_bodies_omitted(self):
  t=self.trace();t.parameters({'xml':'SECRET XML','script':'SECRET SCRIPT','text':'SECRET CSV','password':'SECRET PASS','values':{'description':'PRIVATE VALUE'}});t.finish(200,{'xml':'PRIVATE RESULT'});text=json.dumps(self.events);self.assertNotIn('SECRET',text);self.assertNotIn('PRIVATE',text)
 def test_exception_logs_location_not_message_or_locals(self):
  t=self.trace();t.parameters({})
  try:raise ValueError('MY SECRET MESSAGE')
  except ValueError as e:t.exception(e)
  t.finish(500,{},'ValueError');self.assertIn('error_frames',self.events[-1]);self.assertNotIn('MY SECRET',json.dumps(self.events))
 def test_command_timer_in_final_record(self):
  t=self.trace();t.parameters({});cmd=SimpleNamespace(execute=lambda:42);self.assertEqual(log.execute_traced(cmd),42);t.finish(200,{});self.assertGreaterEqual(self.events[-1]['command_ms'],0)
 def test_human_differentiates_running_and_completed(self):
  t=self.trace();t.parameters({});t.progress(t.started+6);t.finish(200,{});self.assertIn('RUNNING',log.human(self.events[-2]));self.assertIn('END',log.human(self.events[-1]))
if __name__=='__main__':unittest.main()

class LayoutChildren018(unittest.TestCase):
 def render(self,xml,name='page'):
  from tactic.ui_api.design_service import DesignService
  from tactic.core.config_model import ConfigModel,ConfigSource
  class Service(DesignService):
   def _design_record(self,key,layout):return SimpleNamespace(get_value=lambda k: {'config':xml,'view':name}[k])
   def require_type(self,stype):
    if stype!='p/item':raise ApiError(403,'type','Unknown type')
   def _model(self,stype,view):return ConfigModel('reference',[ConfigSource('<config><reference><element name="table"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>p/item</search_type></display></element></reference></config>','reference','test')])
  return Service().layout_screen({'id':'target','options':{'native_layout_key':'key'}})['children']
 def test_unnamed_inline_gets_stable_slot_name(self):
  c=self.render('<config><page><html><element><display class="tactic.ui.panel.TableLayoutWdg"><search_type>p/item</search_type></display></element></html></page></config>')[0];self.assertEqual(c['name'],'element0');self.assertEqual(c['kind'],'table')
 def test_named_element_uses_same_view_definition(self):
  c=self.render('<config><page><element name="items"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>p/item</search_type></display></element><html><element name="items"/></html></page></config>')[0];self.assertEqual(c['kind'],'table');self.assertEqual(c['search_type'],'p/item')
 def test_short_display_class_options(self):
  c=self.render('<config><page><html><element display_class="tactic.ui.panel.TableLayoutWdg" spt_search_type="p/item" view="table"/></html></page></config>')[0];self.assertEqual(c['kind'],'table');self.assertEqual(c['options']['search_type'],'p/item')
 def test_reference_resolves_original_type_view(self):
  c=self.render('<config><page><html><element type="reference" search_type="p/item" view="reference" name="table"/></html></page></config>')[0];self.assertEqual(c['kind'],'table')
 def test_reference_needs_type_access(self):
  with self.assertRaises(ApiError):self.render('<config><page><html><element type="reference" search_type="unknown/item" view="reference" name="table"/></html></page></config>')
 def test_relative_child_layout_view(self):
  c=self.render('<config><folder.page><html><element name="sub" view=".child"/></html></folder.page></config>','folder.page')[0];self.assertEqual(c['options']['view'],'folder.child');self.assertEqual(c['kind'],'custom-layout')
 def test_missing_display_is_diagnostic_not_random_table(self):
  c=self.render('<config><page><html><element name="missing"/></html></page></config>')[0];self.assertEqual(c['kind'],'unsupported');self.assertIn('Нет определения',c['notice'])
 def test_load_none_does_not_mount_widget(self):
  c=self.render('<config><page><html><element load="none" display_class="tactic.ui.panel.TableLayoutWdg" search_type="p/item"/></html></page></config>')[0];self.assertTrue(c['hidden']);self.assertEqual(c['handler'],'Hidden by configuration')
 def test_manual_load_is_not_automatically_executed(self):
  c=self.render('<config><page><html><element load="manual" display_class="tactic.ui.panel.TableLayoutWdg" search_type="p/item"/></html></page></config>')[0];self.assertEqual(c['kind'],'unsupported');self.assertIn('manual',c['notice'])
 def test_nested_definitions_not_double_counted(self):
  c=self.render('<config><page><html><element display_class="tactic.ui.container.TabWdg"><display class="tactic.ui.container.TabWdg"><config><tab><element name="inner"/></tab></config></display></element></html></page></config>');self.assertEqual(len(c),1)
