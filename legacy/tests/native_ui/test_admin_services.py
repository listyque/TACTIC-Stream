"""Boundary tests call ConfigBackend; DB and DDL collaborators are mocks."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.ui_api.config_backend import ConfigBackend
from tactic.ui_api.contracts import ApiError,revision

class AdminServiceTests(unittest.TestCase):
 def setUp(self):
  self.backend=ConfigBackend({'allow_writes':True});self.backend._project=lambda:'fixture';self.backend._write=lambda fn:fn()
  p=patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:True));p.start();self.addCleanup(p.stop)
 def create(self,**changes):
  data={'name':'item','title':'Items','description':'','columns':[]};data.update(changes);return self.backend.config_operation('POST','/search-types',data)
 def test_invalid_type_name_is_rejected_before_ddl(self):
  with self.assertRaises(ApiError) as e:self.create(name='item; DROP TABLE')
  self.assertEqual(e.exception.status,400)
 def test_reserved_column_is_rejected(self):
  with self.assertRaises(ApiError):self.create(columns=[{'name':'id','type':'integer'}])
 def test_duplicate_column_is_rejected(self):
  with self.assertRaises(ApiError):self.create(columns=[{'name':'size','type':'integer'}]*2)
 def test_invalid_column_type_is_rejected(self):
  with self.assertRaises(ApiError):self.create(columns=[{'name':'size','type':'arbitrary SQL'}])
 def test_global_project_creation_refused(self):
  self.backend._project=lambda:'admin'
  with self.assertRaises(ApiError) as e:self.create()
  self.assertEqual(e.exception.status,403)
 def test_original_creator_receives_validated_inputs(self):
  fake=Mock();fake.table_exists.return_value=False;fake.get_search_type_obj.return_value.get_value.return_value='fixture/item'
  with patch('pyasm.search.Search',return_value=Mock(get_sobject=lambda:None)),patch('tactic.core.schema_commands.SearchTypeCreatorCmd',return_value=fake) as creator:
   result=self.create(columns=[{'name':'length','type':'integer'}],pipeline=True)
  self.assertEqual(result['search_type'],'fixture/item');fake.execute.assert_called_once();args=creator.call_args.kwargs;self.assertEqual(args['namespace'],'fixture');self.assertEqual(args['column_name'],['length']);self.assertEqual(args['data_type'],['integer']);self.assertEqual(args['sobject_pipeline'],'on')
 def test_existing_type_is_not_reconfigured(self):
  with patch('pyasm.search.Search',return_value=Mock(get_sobject=lambda:object())),patch('tactic.core.schema_commands.SearchTypeCreatorCmd') as creator:
   with self.assertRaises(ApiError) as e:self.create()
   creator.assert_not_called()
  self.assertEqual(e.exception.status,409)
 def test_existing_unregistered_table_is_not_adopted(self):
  fake=Mock();fake.table_exists.return_value=True
  with patch('pyasm.search.Search',return_value=Mock(get_sobject=lambda:None)),patch('tactic.core.schema_commands.SearchTypeCreatorCmd',return_value=fake):
   with self.assertRaises(ApiError) as e:self.create()
   fake.execute.assert_not_called()
  self.assertEqual(e.exception.code,'table_exists')
 def test_admin_member_removal_is_refused(self):
  self.backend.open_target=lambda _: {'kind':'group-membership'};self.backend._object=lambda *a:Mock(get_value=lambda n:'admin')
  member=Mock(get_value=lambda n:'existing_admin')
  with patch('pyasm.security.LoginInGroup.get_by_group_name',return_value=[member]):
   with self.assertRaises(ApiError) as e:self.backend.config_operation('POST','/memberships',{'target':'x','key':'x','members':[],'revision':revision(['existing_admin'])})
  self.assertEqual(e.exception.code,'admin_removal')
 def test_membership_revision_conflict_precedes_changes(self):
  self.backend.open_target=lambda _: {'kind':'group-membership'};self.backend._object=lambda *a:Mock(get_value=lambda n:'group')
  with patch('pyasm.security.LoginInGroup.get_by_group_name',return_value=[]):
   with self.assertRaises(ApiError) as e:self.backend.config_operation('POST','/memberships',{'target':'x','key':'x','members':[],'revision':'stale'})
  self.assertEqual(e.exception.status,409)
 def test_nonadmin_config_operation_is_refused(self):
  with patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:False)):
   with self.assertRaises(ApiError) as e:self.create()
  self.assertEqual(e.exception.status,403)

if __name__=='__main__':unittest.main()
