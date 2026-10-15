"""Core regressions plus comparisons with the ORIGINAL CellEdit config branch.
Database effects/rollback are separately checked by run_original_012.py.
"""
import ast,copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from pyasm.common import Container,SecurityException,Xml
from pyasm.search import SObject,SearchType,WidgetDbConfig,SObjectException
from tactic.core.widget_config import WidgetConfig,WidgetConfigView
from tactic.core.cell_edit_config import cell_config,save_config,CellConfigModel
from tactic.ui_api.cell_value_service import safe_color,CellValueService
from tactic.ui_api.contracts import revision

BASE='<config><edit><element name="name" title="Name"><display class="TextWdg"/><action class="DatabaseAction"/></element><element name="count"><display class="TextWdg"/></element></edit></config>'
INLINE='<config><edit><element name="name" title="Inline"><display class="TextAreaWdg"><rows>4</rows></display></element></edit></config>'
OVERRIDE='<config><edit_item><element name="name" title="Override"><display class="SelectWdg"/><edit><values>a|b</values></edit><action class="NonEmptyAction"/></element></edit_item></config>'
def w(xml,view):return WidgetConfig.get(view=view,xml=xml)
def db(xml,view):
 # Real WidgetDbConfig method semantics, no database construction needed.
 obj=object.__new__(WidgetDbConfig);obj.xml=Xml();obj.xml.read_string(xml);obj.view=view;obj.view_xpath=view;obj.view_as_attr=False;obj.get_code=lambda:'TEST-CONFIG'
 return obj
class CellResolverTests(unittest.TestCase):
 def setUp(self):
  Container.create();self.base=w(BASE,'edit');self.source=WidgetConfigView(search_type='test/item',view='edit',configs=[self.base])
 def resolve(self,inline=None,override=None):
  with patch.object(WidgetConfigView,'get_by_search_type',return_value=self.source),patch.object(WidgetDbConfig,'get_by_search_type',return_value=override):return cell_config('test/item',inline)
 def original(self,inline=None,override=None):
  tree=ast.parse((ROOT/'src/tactic/ui/panel/layout_wdg.py').read_text());cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CellEditWdg');method=copy.deepcopy(next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='init'))
  end=next(i for i,n in enumerate(method.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='sobject' for t in n.targets));method.body=method.body[:end]
  scope={'Container':Container,'WidgetConfig':WidgetConfig,'WidgetConfigView':WidgetConfigView,'WidgetDbConfig':WidgetDbConfig};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'original_CellEditWdg','exec'),scope)
  source=WidgetConfigView(search_type='test/item',view='edit',configs=[w(BASE,'edit')]);o=SimpleNamespace(kwargs={'element_name':'name','search_type':'test/item','layout_version':'2','config_xml':inline})
  with patch.object(WidgetConfigView,'get_by_search_type',return_value=source),patch.object(WidgetDbConfig,'get_by_search_type',return_value=override):scope['init'](o)
  return o.config
 def test_original_order_all_branches(self):
  for inline in (None,INLINE):
   for override in (None,db(OVERRIDE,'edit_item')):
    with self.subTest(inline=bool(inline),override=bool(override)):
     Container.create();expected=self.original(inline,override);Container.create();actual=self.resolve(inline,override)
     for name in ['name','count']:
      self.assertEqual(expected.get_edit_handler(name),actual.get_edit_handler(name));self.assertEqual(expected.get_options(name,'edit'),actual.get_options(name,'edit'));self.assertEqual(expected.get_element_attributes(name),actual.get_element_attributes(name))
 def test_base_source_not_mutated(self):self.resolve(INLINE,db(OVERRIDE,'edit_item'));self.assertEqual(self.source.get_configs(),[self.base])
 def test_db_edit_item_display_not_edit_class(self):
  c=self.resolve(INLINE,db(OVERRIDE.replace('<edit>','<edit class="Company.ShouldNotRun">'),'edit_item'));self.assertEqual(c.get_edit_handler('name'),'SelectWdg')
 def test_inline_without_override(self):self.assertEqual(self.resolve(INLINE).get_edit_handler('name'),'TextAreaWdg')
 def test_db_override_wins(self):self.assertEqual(self.resolve(INLINE,db(OVERRIDE,'edit_item')).get_edit_handler('name'),'SelectWdg')
 def test_original_db_input_options(self):self.assertEqual(self.resolve(INLINE,db(OVERRIDE,'edit_item')).get_options('name','edit'),{'values':'a|b'})
 def test_definition_revision_does_not_depend_on_changed_fields(self):
  with patch.object(WidgetConfigView,'get_by_search_type',return_value=self.source),patch.object(WidgetDbConfig,'get_by_search_type',return_value=None):
   a=CellConfigModel(cell_config('test/item'),save_config('test/item',['name']),['name']);b=CellConfigModel(cell_config('test/item'),save_config('test/item',['name','count']),['name','count'])
  self.assertEqual(a.fingerprint(),b.fingerprint());self.assertEqual(self.source.get_configs(),[self.base])
 def test_definition_revision_tracks_edit_item_change(self):
  a=self.resolve(None,db(OVERRIDE,'edit_item'));b=self.resolve(None,db(OVERRIDE.replace('a|b','a|c'),'edit_item'))
  self.assertNotEqual(CellConfigModel(a,a,['name']).fingerprint(),CellConfigModel(b,b,['name']).fingerprint())
 def test_action_options_not_taken_from_display(self):
  edit=self.resolve();actions=WidgetConfigView(search_type='test/item',view='edit_item',configs=[w(OVERRIDE,'edit_item')]);f=CellConfigModel(edit,actions,['name']).describe('name');self.assertEqual(f['handler'],'TextWdg');self.assertEqual(f['action_handler'],'NonEmptyAction')

class ExplicitNullTests(unittest.TestCase):
 def setUp(self):
  Container.create();self.obj=object.__new__(SObject);o=self.obj;o.full_search_type='test/item';o._skip_invalid_column=False;o.data={'flag':True};o.update_data={};o.quoted_flag={};o.has_updates=False;o.search_type_obj=SimpleNamespace(get_base_key=lambda:'test/item');o.get_search_key=lambda:'test/item?code=ONE';o.get_search_type=lambda:'test/item';o.validate_set_value=Mock();o.process_value=Mock(return_value={'value':False,'quoted':True})
  self.security=SimpleNamespace(check_access=Mock(return_value=True));self.column={'data_type':'boolean','nullable':True}
  for ctx in [patch('pyasm.biz.Translation.get_language',return_value=None),patch('pyasm.biz.Project.get_project_code',return_value='test'),patch('pyasm.common.Environment.get_security',return_value=self.security),patch.object(SearchType,'get_column_type',return_value='boolean'),patch.object(SearchType,'get_column_info',return_value={'flag':self.column})]:ctx.start();self.addCleanup(ctx.stop)
 def test_legacy_none_still_rejected(self):
  with self.assertRaises(SObjectException):self.obj.set_value('flag',None)
  self.assertFalse(self.obj.update_data)
 def test_legacy_no_exception_still_skips(self):self.obj.set_value('flag',None,no_exception=True);self.assertFalse(self.obj.update_data)
 def test_explicit_nullable_boolean_is_none_not_false(self):self.obj.set_value('flag',None,allow_none=True);self.assertIsNone(self.obj.update_data['flag']);self.obj.process_value.assert_not_called()
 def test_explicit_null_still_calls_validation(self):self.obj.set_value('flag',None,allow_none=True);self.obj.validate_set_value.assert_called_once_with('flag',None)
 def test_explicit_null_cannot_bypass_column_permission(self):
  self.security.check_access.return_value=False
  with self.assertRaises(SecurityException):self.obj.set_value('flag',None,allow_none=True)
  self.assertFalse(self.obj.update_data)
 def test_explicit_null_rejects_not_nullable(self):
  self.column['nullable']=False
  with self.assertRaises(SObjectException):self.obj.set_value('flag',None,allow_none=True)
  self.assertFalse(self.obj.update_data)
 def test_explicit_null_has_original_update_tracking(self):self.obj.set_value('flag',None,allow_none=True);self.assertTrue(self.obj.has_updates);self.assertTrue(self.obj.quoted_flag['flag'])
 def test_normal_false_uses_vendor_conversion(self):self.obj.set_value('flag',False);self.obj.process_value.assert_called_once();self.assertIs(self.obj.update_data['flag'],False)
 def test_revision_distinguishes_null_empty_and_zero(self):self.assertEqual(3,len({revision({'x':x}) for x in [None,'',0]}))

class CellValuesTests(unittest.TestCase):
 def test_safe_hex_variants(self):
  for value in ['#123','#1234','#123456','#12345678']:self.assertEqual(safe_color(value),value)
 def test_unsafe_css_not_emitted(self):
  for value in ['url(x)','red;position:fixed','var(--evil)','<script>',None,'#12','#12345']:self.assertIsNone(safe_color(value))
 def test_color_cell_keeps_original_value(self):
  row={'values':{'color':'#abcdef'}};s={'fields':[{'name':'color','handler':'pyasm.widget.ColorWdg','storage':True}]};r=CellValueService()._native_value_cells(None,row,s);self.assertEqual(r['values']['color'],'#abcdef');self.assertEqual(r['cells']['color']['kind'],'color')
 def test_color_not_guessed_from_field_name(self):
  row={'values':{'color':'#abcdef'}};s={'fields':[{'name':'color','handler':'TextWdg','storage':True}]};self.assertFalse(CellValueService()._native_value_cells(None,row,s)['cells'])
 def test_login_label_separate_from_stored_code(self):
  service=CellValueService();service._cell_login_labels={'user01':'Anna Example'};row={'values':{'owner':'user01'}};spec={'fields':[{'name':'owner','handler':'tactic.ui.input.LoginTableElementWdg','storage':True}]};service._native_value_cells(None,row,spec);self.assertEqual(row['values']['owner'],'user01');self.assertEqual(row['cells']['owner']['text'],'Anna Example')
 def test_unknown_login_falls_back_to_stored_code(self):
  service=CellValueService();service._cell_login_labels={};row={'values':{'owner':'missing'}};spec={'fields':[{'name':'owner','handler':'LoginTableElementWdg','storage':True}]};service._native_value_cells(None,row,spec);self.assertEqual(row['cells']['owner']['text'],'missing')

class ThumbnailSelectionTests(unittest.TestCase):
 def setUp(self):
  self.a=SimpleNamespace(get_base_search_type=lambda:'test/item',get_search_key=lambda:'A',get_icon_context=lambda v:v or 'icon')
  self.b=SimpleNamespace(get_base_search_type=lambda:'test/item',get_search_key=lambda:'B',get_icon_context=lambda v:v or 'icon')
 def test_original_cascade_order_and_precedence(self):
  from tactic.ui_api.thumbnail_service import select_snapshots
  with patch('pyasm.biz.Snapshot.get_by_sobjects',side_effect=[{'A':'icon-A'},{'A':'publish-A'},{'B':'process-B'}]) as call:
   result=select_snapshots([self.a,self.b],{})
  self.assertEqual(result,{'A':'icon-A','B':'process-B'});self.assertEqual(call.call_count,3);self.assertEqual(call.call_args_list[0].args[1],'icon');self.assertEqual(call.call_args_list[1].kwargs['context'],'publish');self.assertEqual(call.call_args_list[2].kwargs['process'],'publish')
 def test_cascade_disabled_does_not_pick_arbitrary_other_context(self):
  from tactic.ui_api.thumbnail_service import select_snapshots
  with patch('pyasm.biz.Snapshot.get_by_sobjects',return_value={}) as call:self.assertEqual(select_snapshots([self.a],{'cascade_search':'false'}),{})
  self.assertEqual(call.call_count,1)
 def test_latest_icon_ignores_icon_context_like_original(self):
  from tactic.ui_api.thumbnail_service import select_snapshots
  with patch('pyasm.biz.Snapshot.get_by_sobjects',return_value={'A':'snap'}) as call:select_snapshots([self.a],{'latest_icon':'true'})
  self.assertIsNone(call.call_args.args[1])
 def test_explicit_icon_context_is_preserved(self):
  from tactic.ui_api.thumbnail_service import select_snapshots
  with patch('pyasm.biz.Snapshot.get_by_sobjects',return_value={'A':'snap'}) as call:select_snapshots([self.a],{'icon_context':'review'})
  self.assertEqual(call.call_args.args[1],'review')
 def test_snapshots_themselves_do_not_lookup_latest(self):
  from tactic.ui_api.thumbnail_service import select_snapshots
  obj=SimpleNamespace(get_base_search_type=lambda:'sthpw/snapshot',get_search_key=lambda:'SNAP')
  with patch('pyasm.biz.Snapshot.get_by_sobjects') as call:result=select_snapshots([obj],{})
  self.assertIs(result['SNAP'],obj);call.assert_not_called()
 def test_custom_redirect_not_silently_ignored(self):
  from tactic.ui_api.thumbnail_service import ThumbnailService
  f={'name':'preview','handler':'ThumbWdg','display_options':{'redirect_expr':'@SOBJECT(test/other)'},'reason':''};ThumbnailService()._thumbnail_spec({'fields':[f]});self.assertFalse(f['supported']);self.assertIn('redirect_expr',f['reason'])
 def test_no_thumb_is_invented_for_column_name(self):
  from tactic.ui_api.thumbnail_service import ThumbnailService
  f={'name':'preview','handler':'company.Custom','display_options':{},'reason':'Unknown'};ThumbnailService()._thumbnail_spec({'fields':[f]});self.assertNotIn('renderer',f)
 def test_supported_thumb_stays_readonly_in_grid(self):
  from tactic.ui_api.thumbnail_service import ThumbnailService
  f={'name':'preview','handler':'pyasm.widget.ThumbWdg','display_options':{'icon_size':'60'},'reason':'Unknown'};ThumbnailService()._thumbnail_spec({'fields':[f]});self.assertTrue(f['supported']);self.assertTrue(f['read_only']);self.assertEqual(f['thumbnail_size'],60)

if __name__=='__main__':unittest.main()
