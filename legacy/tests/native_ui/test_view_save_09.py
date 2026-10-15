"""Production ViewService regression for the misplaced undefined opts block."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/client")]
from unittest.mock import patch
from tactic.core.config_model import ConfigModel,ConfigSource,parse_xml,view_node
from tactic.ui_api.view_service import ViewService
from tactic.ui_api.contracts import ApiError
XML='<config extension="keep"><table><element name="name" custom="keep"/><element name="cost"/></table><other><element name="unrelated"/></other></config>'
class ViewSave09(unittest.TestCase):
 def setUp(self):
  self.values={'config':XML};self.committed=False;self.stack=ExitStack()
  self.model=ConfigModel('table',[ConfigSource(XML,'table','test DB config')])
  row=SimpleNamespace(get_value=lambda n:self.values.get(n),set_value=lambda k,v:self.values.update({k:v}),commit=lambda:setattr(self,'committed',True),get_search_key=lambda:'config/widget_config?code=TEST')
  query=SimpleNamespace(add_filter=lambda *a:None,add_order_by=lambda *a:None,get_sobject=lambda:row)
  self.stack.enter_context(patch('pyasm.search.Search',return_value=query))
  self.stack.enter_context(patch('pyasm.common.Environment.get_security',return_value=SimpleNamespace(is_admin=lambda:True)))
  self.stack.enter_context(patch('pyasm.common.Environment.get_user_name',return_value='fixture'))
  self.backend=SimpleNamespace(require_type=lambda st:None,_model=lambda *a:self.model,_write=lambda cb:cb())
 def tearDown(self):self.stack.close()
 def save(self,operations,**kwargs):
  data=dict(search_type='fixture/item',view='table',revision=self.model.fingerprint(),operations=operations);data.update(kwargs)
  return ViewService.view_operation(self.backend,'PATCH',data)
 def test_real_view_save_does_not_reference_undefined_opts(self):
  self.assertTrue(self.save([{'op':'update','index':0,'attributes':{'title':'Название'}}])['saved']);self.assertTrue(self.committed)
 def test_preserves_unrelated_view_unknown_attrs_and_order(self):
  self.save([{'op':'update','index':0,'attributes':{'title':'Новое'}}]);root=parse_xml(self.values['config']);self.assertEqual(root.get('extension'),'keep');self.assertEqual(view_node(root,'other')[0].get('name'),'unrelated');self.assertEqual(view_node(root,'table')[0].get('custom'),'keep')
 def test_invalid_operation_does_not_commit(self):
  with self.assertRaises(ApiError):self.save([{'op':'unknown'}])
  self.assertFalse(self.committed);self.assertEqual(self.values['config'],XML)
 def test_stale_view_revision_does_not_commit(self):
  with self.assertRaises(ApiError):self.save([],revision='stale')
  self.assertFalse(self.committed)
 def test_cannot_write_another_persons_override(self):
  with self.assertRaises(ApiError):self.save([],login='another')
  self.assertFalse(self.committed)
