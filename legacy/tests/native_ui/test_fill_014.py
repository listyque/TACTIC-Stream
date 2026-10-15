"""Structural preview boundaries; separate original HTTP tests cover persistence."""
from pathlib import Path
import copy, sys, unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from tactic.ui_api.table_edit_service import TableEditService
from tactic.ui_api.contracts import ApiError

class FillService(TableEditService):
 def __init__(self):
  self.allow_writes=True;self.opened={'search_type':'test/item','spec':{'revision':'table','capabilities':{'update':True}}}
  self.rows={'a':{'key':'a','revision':'ra','values':{'field':'old-a'}},'b':{'key':'b','revision':'rb','values':{'field':'old-b'}}}
  self.check_native_write=Mock();self._check_actions=Mock(side_effect=AssertionError('must not construct actions'));self._write=Mock(side_effect=AssertionError('must not commit'))
  self.options=[];self.field_kind='text';self.nullable=True;self.supported=True
 def _table_edit_target(self,data):return self.opened
 def _table_save_options(self,opened):return 'edit_item',None
 def _checked_cell_form(self,opened,key,names,pending=None):
  if key not in self.rows or set(names)-{'field'}:raise ApiError(403,'field','denied')
  return {'record':copy.deepcopy(self.rows[key]),'cell_config_revision':'editor', 'spec':{'fields':[{'name':'field','label':'Field','kind':self.field_kind,'nullable':self.nullable,'read_only':False,'supported':self.supported,'action':'DatabaseAction','options':self.options}]}}
class PreviewTests(unittest.TestCase):
 def setUp(self):
  self.s=FillService();self.data={'table_revision':'table','field':'field','value':'new','records':[{'key':'a','revision':'ra'},{'key':'b','revision':'rb'}]}
 def preview(self,**kw):return self.s.table_edit_operation('POST','/table-fill-preview',dict(self.data,**kw))
 def test_no_commands_or_mutations(self):
  before=copy.deepcopy(self.s.rows);r=self.preview();self.assertEqual(len(r['items']),2);self.assertFalse(r['writes_performed']);self.assertEqual(before,self.s.rows);self.s._write.assert_not_called();self.s._check_actions.assert_not_called()
 def test_both_original_values_returned(self):self.assertEqual([i['original'] for i in self.preview()['items']],['old-a','old-b'])
 def test_each_editor_resolved_individually(self):self.preview();self.assertEqual(self.s.check_native_write.call_count,2)
 def test_table_revision_required(self):
  with self.assertRaises(ApiError):self.preview(table_revision='old')
 def test_row_revision_required(self):
  with self.assertRaises(ApiError):self.preview(records=[{'key':'a'}])
 def test_last_row_conflict_cannot_commit_prefix(self):
  with self.assertRaises(ApiError):self.preview(records=[{'key':'a','revision':'ra'},{'key':'b','revision':'old'}])
  self.s._write.assert_not_called()
 def test_duplicate_key_rejected(self):
  with self.assertRaises(ApiError):self.preview(records=[self.data['records'][0]]*2)
 def test_empty_records_rejected(self):
  with self.assertRaises(ApiError):self.preview(records=[])
 def test_too_many_records_rejected(self):
  with self.assertRaises(ApiError):self.preview(records=[self.data['records'][0]]*101)
 def test_nullable_none(self):self.assertIsNone(self.preview(value=None)['items'][0]['value'])
 def test_nonnullable_none_rejected(self):
  self.s.nullable=False
  with self.assertRaises(ApiError):self.preview(value=None)
 def test_bad_value_type(self):
  with self.assertRaises(ApiError):self.preview(value={'unexpected':True})
 def test_readonly_table_rejected(self):
  self.s.allow_writes=False
  with self.assertRaises(ApiError):self.preview()
 def test_unsupported_editor_rejected(self):
  self.s.supported=False
  with self.assertRaises(ApiError):self.preview()
 def test_select_choices_preserved(self):
  self.s.options=[{'value':'allowed','label':'Allowed'}]
  with self.assertRaises(ApiError):self.preview(value='not-allowed')
  self.assertEqual(self.preview(value='allowed')['items'][0]['value'],'allowed')
 def test_integer_spelling_does_not_round_in_json(self):
  self.s.field_kind='integer';self.assertEqual(self.preview(value='9007199254740993')['items'][0]['value'],'9007199254740993')
 def test_editor_revision_check(self):
  with self.assertRaises(ApiError):self.preview(records=[{'key':'a','revision':'ra','config_revision':'changed'}])
 def test_preview_method_cannot_be_get(self):
  with self.assertRaises(ApiError) as e:self.s.table_edit_operation('GET','/table-fill-preview',self.data)
  self.assertEqual(e.exception.status,405)
if __name__=='__main__':unittest.main()
