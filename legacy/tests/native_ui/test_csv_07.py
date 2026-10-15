"""CSV export uses production original Search/Select, scoped rows and typed cells."""
import csv,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from column_test_store_07 import Store,Backend,ST,INLINE
from tactic.ui_api.csv_service import CsvService,BytesPayload,csv_cell,protected_csv_value
from tactic.ui_api.contracts import ApiError
class CsvTests(unittest.TestCase):
 def setUp(self):
  self.store=Store(235);self.b=Backend(self.store);self.ctx=self.store.bind();self.ctx.__enter__();self.addCleanup(self.ctx.__exit__,None,None,None);self.addCleanup(self.store.close);self.spec=self.b.view(ST)
 def export(self,**kwargs):
  data=dict(config_revision=self.spec['revision'],columns=['code','name','amount','ratio'],sort={'field':'code','direction':'asc'},**kwargs)
  return self.b.export_csv(ST,self.spec,data)
 def rows(self,payload,delimiter=','):return list(csv.reader(io.StringIO(payload.data.decode('utf-8-sig')),delimiter=delimiter))
 def error(self,status,**kwargs):
  with self.assertRaises(ApiError) as c:self.export(**kwargs)
  self.assertEqual(c.exception.status,status)
 def test_all_pages_not_current_page(self):self.assertEqual(len(self.rows(self.export(limit=20,offset=20))),236)
 def test_matching_scope_keeps_original_filters(self):
  self.b.active_target['options']={'filter':'[{"prefix":"main_body","main_body_enabled":"on","main_body_column":"department","main_body_relation":"is","main_body_value":"A"}]'};rows=self.rows(self.export());self.assertEqual(len(rows),119);self.assertNotIn('Other project',str(rows))
 def test_additional_user_filter_is_conjunction(self):
  self.b.active_target['options']={'filter':'[{"prefix":"main_body","main_body_enabled":"on","main_body_column":"department","main_body_relation":"is","main_body_value":"A"}]'};rows=self.rows(self.export(filters=[{'field':'department','op':'eq','value':'B'}]));self.assertEqual(len(rows),1)
 def test_display_values_match_formatted_columns(self):
  rows=self.rows(self.export());self.assertEqual(rows[1][2:4],['1234.57','12.50%'])
 def test_raw_preserves_unformatted_decimal(self):self.assertEqual(self.rows(self.export(value_mode='raw'))[1][2:4],['1234.567','0.125'])
 def test_selected_keys_still_use_table_order(self):
  rows=self.rows(self.export(selection='selected',keys=[ST+'?id=3',ST+'?id=1']));self.assertEqual([r[0] for r in rows[1:]],['ROW0000','ROW0002'])
 def test_selection_outside_filter_rejected(self):self.error(409,selection='selected',keys=[ST+'?id=1'],filters=[{'field':'department','op':'eq','value':'B'}])
 def test_foreign_object_rejected(self):self.error(404,selection='selected',keys=[ST+'?id=236'])
 def test_wrong_type_key_rejected(self):self.error(403,selection='selected',keys=['sthpw/login?id=1'])
 def test_duplicate_selection_rejected(self):self.error(400,selection='selected',keys=[ST+'?id=1']*2)
 def test_no_selection_rejected(self):self.error(400,selection='selected',keys=[])
 def test_sensitive_column_rejected(self):
  data={'columns':['password'],'config_revision':self.spec['revision']}
  with self.assertRaises(ApiError) as c:self.b.export_csv(ST,self.spec,data)
  self.assertEqual(c.exception.status,403)
 def test_unknown_widget_not_falsely_exported(self):
  with self.assertRaises(ApiError) as c:self.b.export_csv(ST,self.spec,{'columns':['column.custom'],'config_revision':self.spec['revision']})
  self.assertEqual(c.exception.status,501)
 def test_virtual_alias_display_export(self):
  p=self.b.export_csv(ST,self.spec,{'columns':['alias'],'config_revision':self.spec['revision']});self.assertEqual(len(self.rows(p)),236)
 def test_virtual_raw_rejected(self):
  with self.assertRaises(ApiError) as c:self.b.export_csv(ST,self.spec,{'columns':['alias'],'config_revision':self.spec['revision'],'value_mode':'raw'})
  self.assertEqual(c.exception.status,400)
 def test_config_revision_conflict(self):
  with self.assertRaises(ApiError) as c:self.b.export_csv(ST,self.spec,{'columns':['name'],'config_revision':'old'})
  self.assertEqual(c.exception.status,409)
 def test_no_partial_csv_when_cell_bad(self):
  self.store.db.execute('UPDATE columns07 SET timestamp=? WHERE id=4',('bad-date',))
  with self.assertRaises(ApiError) as c:self.b.export_csv(ST,self.spec,{'columns':['timestamp'],'config_revision':self.spec['revision']})
  self.assertEqual(c.exception.status,422)
 def test_utf8_bom_and_quote_roundtrip(self):
  p=self.export();self.assertTrue(p.data.startswith(b'\xef\xbb\xbf'));self.assertIn('Строка 001, "тест"',self.rows(p)[2][1]);self.assertIn(b'\r\n',p.data)
 def test_linebreak_value_roundtrip(self):
  self.store.db.execute('UPDATE columns07 SET name=? WHERE id=2',('Строка\nВторая строка',));self.assertEqual(self.rows(self.export())[2][1],'Строка\nВторая строка')
 def test_formula_protection(self):self.assertTrue(self.rows(self.export())[1][1].startswith("'=HYPERLINK"))
 def test_formula_with_leading_whitespace(self):
  for value in ('=1','+cmd','-1','@SUM(A1:A2)','  =1','\t=1','\n=1'):self.assertEqual(protected_csv_value(value),"'"+value)
 def test_force_string_never_creates_excel_formula(self):self.assertEqual(protected_csv_value('0007',True),"'0007")
 def test_delimiters_roundtrip(self):
  for delimiter in (';', '\t'):self.assertEqual(len(self.rows(self.export(delimiter=delimiter),delimiter)[0]),4)
 def test_invalid_delimiter_rejected(self):self.error(400,delimiter='\n')
 def test_explicit_row_cap(self):
  with patch('tactic.ui_api.csv_service.MAX_ROWS',100):self.error(413)
 def test_explicit_byte_cap(self):
  with patch('tactic.ui_api.csv_service.MAX_BYTES',50):self.error(413)
 def test_download_payload_has_no_path_or_ticket(self):
  p=self.export();self.assertIsInstance(p,BytesPayload);self.assertEqual(p.content_type,'text/csv; charset=utf-8');self.assertTrue(p.filename.endswith('.csv'));self.assertNotIn('DO-NOT-EXPORT',p.data.decode('utf-8-sig'))
 def test_csv_export_works_when_writes_disabled(self):self.assertFalse(self.b.allow_writes);self.assertTrue(self.export().data)

if __name__=='__main__':unittest.main()
