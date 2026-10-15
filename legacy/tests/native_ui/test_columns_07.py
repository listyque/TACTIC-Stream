"""0.7 raw/display separation, alias ACL, upstream formatting and summaries."""
import ast,copy,datetime,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
from dateutil import parser
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.core.format_value import FormatValueMixin
from tactic.ui_api.column_service import NativeFormat,format_cell,safe_link,simple_cell
from tactic.ui_api.contracts import clean_query,ApiError
from column_test_store_07 import Store,Backend,ST,XML,INLINE,ConfigSource,model
from pyasm.common import TimeCode
from pyasm.biz import ProdSetting

class FormattingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  tree=ast.parse((R/'tests/native_ui/reference_07/format_element_wdg_06.py.txt').read_text());c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FormatElementWdg');methods=[copy.deepcopy(n) for n in c.body if isinstance(n,ast.FunctionDef) and n.name in ('get_format_value','convert_to_float','number_format','currency_format')];ref=ast.ClassDef(name='Original',bases=[],keywords=[],body=methods,decorator_list=[]);m=ast.Module(body=[ref],type_ignores=[]);ast.fix_missing_locations(m);ns={'parser':parser,'datetime':datetime,'TimeCode':TimeCode,'ProdSetting':ProdSetting};exec(compile(m,'ORIGINAL06:format_element_wdg','exec'),ns);cls.original=ns['Original']();cls.original.get_option=lambda key:24 if key=='fps' else None
 def test_exact_unchanged_helper_ast_hashes(self):
  t=ast.parse((R/'src/tactic/core/format_value.py').read_text());hashes=json.loads((R/'tests/native_ui/source-provenance-07.json').read_text())['unchanged_methods']
  for name,want in hashes.items():
   fn=next(n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name==name);self.assertEqual(hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest(),want)
 def test_numeric_formats_against_original_body(self):
  for fmt in ('-1234','-1234.12','-13%','-12.95%','-1.23E+03','-1.234E+03','True|False','true|false'):
   for value in ('',None,0,1,-1234.567,0.125,'bad number','0'):
    with self.subTest(format=fmt,value=value):self.assertEqual(NativeFormat().get_format_value(value,fmt),self.original.get_format_value(value,fmt))
 def test_all_literal_date_time_formats_against_original_body(self):
  formats=['31/12/99','December 31, 1999','31/12/1999','Dec 31, 99','Dec 31, 1999','31 Dec, 1999','31 December 1999','Fri, Dec 31, 99','Fri 31/Dec 99','Fri, December 31, 1999','Friday, December 31, 1999','12-31','99-12-31','1999-12-31','12-31-1999','12/99','31/Dec','December','52','13:37','13:37:46','01:37 PM','DATE','DATETIME']
  with patch.object(ProdSetting,'get_value_by_key',return_value=''):
   for fmt in formats:
    with self.subTest(format=fmt):self.assertEqual(NativeFormat().get_format_value('2026-10-01 13:37:46',fmt),self.original.get_format_value('2026-10-01 13:37:46',fmt))
 def test_timecode_uses_original_timecode(self):
  for fmt in ('MM:SS.FF','MM:SS:FF','MM:SS','HH:MM:SS.FF','HH:MM:SS:FF','HH:MM:SS'):
   for n in (0,24,100,86400):
    with self.subTest(fmt=fmt,n=n):self.assertEqual(NativeFormat({'fps':24}).get_format_value(n,fmt),self.original.get_format_value(n,fmt))
 def test_file_size_original_thresholds(self):
  # C-only test host has no monetary locale. Supply the same deterministic
  # locale collaborator to both bodies; production helper AST is checked above.
  currency=lambda v,**kw:'$%.2f'%float(v)
  with patch.object(NativeFormat,'currency_format',side_effect=currency),patch.object(self.original,'currency_format',side_effect=currency):
   for size in (0,1,511,512,513,1024,1024**2,1024**5):self.assertEqual(NativeFormat().get_format_value(size,'KB'),self.original.get_format_value(size,'KB'))
 def test_checkbox_is_typed_not_html(self):
  self.assertEqual(format_cell(1,{'format':'Checkbox'},'approved'),{'kind':'boolean','checked':True,'text':'True'});self.assertFalse(format_cell(0,{'format':'Checkbox'},'approved')['checked'])
 def test_checkbox_preserves_original_python_truthiness(self):self.assertTrue(format_cell('0',{'format':'Checkbox'},'approved')['checked'])
 def test_negative_currency_has_no_html(self):
  with patch.object(NativeFormat,'currency_format',return_value='-$1,234.00'):
   cell=format_cell(-1234,{'format':'($1,234.00)'},'amount');self.assertEqual(cell['text'],'($1,234.00)');self.assertTrue(cell['negative']);self.assertNotIn('<',str(cell))
 def test_invalid_locale_is_diagnostic(self):
  with patch.object(NativeFormat,'currency_format',side_effect=ValueError('locale')):self.assertEqual(format_cell(20,{'format':'-$1,234.00'},'amount')['kind'],'error')
 def test_invalid_date_does_not_become_blank_or_zero(self):self.assertEqual(format_cell('nonsense',{'format':'31/12/1999'},'timestamp')['kind'],'error')
 def test_explicit_timezone_conversion(self):self.assertEqual(format_cell('2026-10-01 23:00:00+00:00',{'type':'date','format':'31/12/1999','timezone':'Asia/Tokyo'},'timestamp')['text'],'02/10/2026')
 def test_day_column_skips_timezone(self):self.assertEqual(format_cell('2026-10-01',{'type':'date','format':'31/12/1999','timezone':'bad'},'date',True)['text'],'01/10/2026')
 def test_duration_fix(self):
  d=datetime.timedelta(days=2,seconds=3);self.assertEqual(NativeFormat().get_format_value(d,'DAYS'),2);self.assertEqual(NativeFormat().get_format_value(d,'SECONDS'),172803)
 def test_plain_timestamp_uses_original_pattern(self):self.assertEqual(simple_cell('2026-10-01 10:20:30',{'timezone':'UTC'},'timestamp','timestamp')['text'],'Oct 01, 2026 - 10:20')
 def test_plain_empty_placeholder_and_null(self):
  self.assertEqual(simple_cell(None,{},'name','text')['text'],'');self.assertEqual(simple_cell(0,{'empty':'true'},'number','integer')['text'],'--Select--')
 def test_wiki_and_html_stay_inert_text(self):self.assertEqual(simple_cell('<script>x()</script>',{},'name','varchar')['text'],'<script>x()</script>')
 def test_static_safe_links(self):
  for value in ('/tactic/admin/','https://example.invalid/a','http://example.invalid','mailto:test@example.invalid'):self.assertEqual(safe_link(value)['kind'],'link')
 def test_unsafe_links_disabled(self):
  for value in ('javascript:alert(1)','//evil.invalid','data:text/html,x',' https://a','https://a\nb','/\\evil','{arbitrary()}'):self.assertEqual(safe_link(value)['kind'],'error')

class ColumnBackendTests(unittest.TestCase):
 def setUp(self):
  self.store=Store(8);self.b=Backend(self.store);self.context=self.store.bind();self.context.__enter__();self.addCleanup(self.context.__exit__,None,None,None);self.addCleanup(self.store.close)
 def spec(self,options=None):return self.b.view(ST,'table',options)
 def query(self,spec=None,**data):
  s=spec or self.spec();return self.b.query(ST,s,clean_query(data,s['fields'],s.get('default_sort')))
 def test_real_backend_inherits_inline_columns(self):
  s=self.spec({'config_xml':INLINE});self.assertEqual([f['name'] for f in s['fields']],['name','amount','code']);self.assertEqual(s['fields'][0]['width'],'260');self.assertEqual(self.query(s)['items'][0]['cells']['amount']['text'],'1242')
 def test_custom_order_by_is_not_silently_ignored(self):
  self.b.xml=self.b.xml.replace('<format>-1234.12</format>','<format>-1234.12</format><order_by>LOWER(code)</order_by>')
  s=self.spec();f=next(f for f in s['fields'] if f['name']=='amount');self.assertFalse(f['sortable'])
  with self.assertRaises(ApiError):clean_query({'sort':{'field':'amount','direction':'asc'}},s['fields'])
  self.assertTrue(self.spec({'order_by':'amount asc'})['sort_error'])
 def test_active_target_config_used_consistently(self):
  self.b.active_target['options']={'config_xml':INLINE};self.assertEqual([f['name'] for f in self.spec()['fields']],['name','amount','code'])
 def test_code_view_does_not_merge_default(self):
  s=self.spec({'config_code':'CONFIG07'});self.assertEqual(s['resolved_view'],'card');self.assertEqual([f['name'] for f in s['fields']],['code'])
 def test_empty_config_can_query_without_invented_columns(self):
  s=self.spec({'config_xml':'<config><table/></config>'});page=self.query(s);self.assertEqual(s['fields'],[]);self.assertEqual(page['total'],8);self.assertEqual(page['items'][0]['values'],{})
 def test_virtual_dot_element_not_silently_dropped(self):
  f=next(f for f in self.spec()['fields'] if f['name']=='column.custom');self.assertFalse(f['storage']);self.assertFalse(f['supported']);self.assertEqual(f['display_support'],'unsupported')
 def test_sensitive_fields_never_exposed(self):self.assertNotIn('password',str(self.spec()['fields']));self.assertNotIn('DO-NOT-EXPORT',str(self.query()))
 def test_raw_value_separate_from_display(self):
  row=self.query()['items'][0];self.assertAlmostEqual(row['values']['ratio'],.125);self.assertEqual(row['cells']['ratio']['text'],'12.50%');self.assertIsInstance(row['values']['amount'],float)
 def test_alias_reads_correct_source(self):
  row=self.query()['items'][0];self.assertEqual(row['values']['alias'],row['values']['name']);self.assertTrue(next(f for f in self.spec()['fields'] if f['name']=='alias')['read_only'])
 def test_alias_cannot_bypass_source_acl(self):
  self.store.denied.add('name');s=self.spec();a=next(f for f in s['fields'] if f['name']=='alias');self.assertFalse(a['supported']);row=self.query(s)['items'][0];self.assertNotIn('name',row['values']);self.assertIsNone(row['values']['alias'])
 def test_alias_cannot_read_sensitive_column(self):
  self.b.xml=self.b.xml.replace('<column>name</column>','<column>password</column>');s=self.spec();self.assertFalse(next(f for f in s['fields'] if f['name']=='alias')['supported']);self.assertNotIn('DO-NOT-EXPORT',str(self.query(s)))
 def test_unknown_expression_not_evaluated(self):
  self.b.xml=self.b.xml.replace('<column>name</column>','<expression>@SOBJECT(sthpw/login)</expression>');s=self.spec();self.assertFalse(next(f for f in s['fields'] if f['name']=='alias')['supported'])
 def test_original_page_sum_and_average(self):
  page=self.query(limit=3,sort={'field':'code','direction':'asc'});totals={s['field']:s for s in page['summaries']};self.assertAlmostEqual(totals['amount']['value'],1234.567*3+3);self.assertEqual(totals['ratio']['cell']['text'],'12.50%');self.assertEqual(totals['amount']['scope'],'page')
 def test_summary_not_over_entire_matching_query(self):
  self.assertNotEqual(self.query(limit=2)['summaries'][0]['value'],self.query(limit=8)['summaries'][0]['value'])
 def test_multicolumn_config_sort_applied_to_sql(self):
  s=self.spec({'order_by':'department asc, amount desc'});rows=self.query(s)['items'];self.assertEqual([r['values']['code'] for r in rows[:4]],['ROW0006','ROW0004','ROW0002','ROW0000'])
 def test_client_sort_overrides_config_sort(self):
  s=self.spec({'order_by':'department asc, amount desc'});self.assertEqual(self.query(s,sort={'field':'code','direction':'asc'})['items'][0]['values']['code'],'ROW0000')
 def test_config_sql_sort_is_not_executed(self):
  s=self.spec({'order_by':'random()'});self.assertTrue(s['sort_error']);
  with self.assertRaises(ApiError):self.query(s)
 def test_options_change_revision_not_only_xml(self):self.assertNotEqual(self.spec({'show_header':'false'})['revision'],self.spec()['revision'])
 def test_heading_comes_from_original_form(self):
  s=self.b.view(ST,'edit',{'native_form':True});f=s['fields'][0];self.assertEqual(f['kind'],'heading');self.assertEqual(f['label'],'Основные параметры');self.assertTrue(f['read_only'])
 def test_inspector_reports_one_order_owner(self):
  report=self.b.resolved_view({'target':'t'});self.assertEqual(sum(s['owns_order'] for s in report['layers']),1);self.assertEqual([f['name'] for f in report['fields']],[f['name'] for f in self.spec()['fields']])
 def test_bad_secondary_sort_rejected_before_sql(self):
  with self.assertRaises(ApiError):clean_query({},self.spec()['fields'],[{'field':'code','direction':'asc'},{'field':'password','direction':'asc'}])

if __name__=='__main__':unittest.main()
