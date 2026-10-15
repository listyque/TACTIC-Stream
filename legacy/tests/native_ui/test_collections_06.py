import ast
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from collection_test_store import Store,Backend,ROOT
from tactic.ui_api.contracts import ApiError
from tactic.core.collection_commands import CollectionAddCmd

class CollectionTests(unittest.TestCase):
 def setUp(self):self.s=Store();self.s.seed();self.b=Backend(self.s);self.bound=self.b.bind();self.bound.__enter__()
 def tearDown(self):self.bound.__exit__(None,None,None);self.s.close()
 def op(self,method,path,**v):return self.b.collection_operation(method,path,dict(target='collections',**v))
 def members(self,folder=None,**v):return self.op('GET','/collection-members',collection=(folder or self.s.folder).get_search_key(),**v)
 def change(self,action,folder=None,keys=None,**v):
  folder=folder or self.s.folder;state=self.members(folder);return self.op('POST','/collection-change',collection=folder.get_search_key(),action=action,keys=keys or [self.s.b.get_search_key()],revision=v.pop('revision',state['revision']),**v)
 def test_original_collection_flag_not_new_table(self):
  data=self.op('GET','/collections');self.assertEqual(data['total'],2);self.assertEqual(data['instance_type'],'fixture/media_in_media')
 def test_members_use_original_subquery(self):
  data=self.members();self.assertEqual(data['total'],2);self.assertEqual({r['values']['code'] for r in data['items']},{'A','CHILD'});self.assertTrue(any('SELECT' in q and 'media_in_media' in q and ' IN ' in q.upper() for q in self.s.statements))
 def test_members_pagination(self):
  a=self.members(limit=1);b=self.members(limit=1,offset=1);self.assertTrue(a['has_more']);self.assertNotEqual(a['items'][0]['key'],b['items'][0]['key'])
 def test_candidates_include_objects_and_nested_collections(self):self.assertEqual(self.op('GET','/collections',mode='records')['total'],4)
 def test_literal_keyword(self):self.assertEqual(self.op('GET','/collections',keyword='Review')['total'],1)
 def test_empty_members(self):self.assertEqual(self.members(self.s.child)['total'],0)
 def test_add_original_command(self):
  r=self.change('add');self.assertEqual(r['operation'],'CollectionAddCmd');self.assertEqual(self.members()['total'],3)
 def test_duplicate_add_does_not_duplicate_instance(self):
  self.change('add');self.change('add');self.assertEqual(self.members()['total'],3);self.assertEqual(self.members()['links'],3)
 def test_remove_deletes_only_link(self):
  r=self.change('remove',keys=[self.s.a.get_search_key()]);self.assertFalse(r['deleted_member_objects']);self.assertEqual(self.members()['total'],1);self.assertIsNotNone(self.s.object('fixture/media',self.s.a.get_search_key()))
 def test_remove_already_missing_conflict(self):
  with self.assertRaises(ApiError):self.change('remove',keys=[self.s.b.get_search_key()])
 def test_direct_self_cycle(self):
  with self.assertRaises(ApiError) as e:self.change('add',keys=[self.s.folder.get_search_key()])
  self.assertEqual(e.exception.code,'collection_cycle');self.assertEqual(self.members()['total'],2)
 def test_ancestor_cycle(self):
  with self.assertRaises(ApiError) as e:self.change('add',self.s.child,keys=[self.s.folder.get_search_key()])
  self.assertEqual(e.exception.code,'collection_cycle')
 def test_deep_cycle_beyond_original_ten_levels(self):
  parent=self.s.child
  for i in range(15):
   child=self.s.row('media',code='D'+str(i),name='deep',_is_collection=True);self.s.link(parent,child);parent=child
  self.s.db.commit()
  with self.assertRaises(ApiError) as e:self.change('add',parent,keys=[self.s.folder.get_search_key()])
  self.assertEqual(e.exception.code,'collection_cycle')
 def test_existing_cycle_does_not_loop(self):
  self.s.link(self.s.child,self.s.folder);self.s.db.commit();c=CollectionAddCmd(collection_code='ROOT',collection_type='fixture/media_in_media');self.assertEqual(c.get_parent_codes(),{'CHILD','ROOT'})
 def test_cross_type_keys_rejected(self):
  with self.assertRaises(ApiError):self.change('add',keys=['sthpw/snapshot?id=1'])
 def test_cross_project_rejected(self):
  with self.assertRaises(ApiError):self.change('add',keys=[self.s.a.get_search_key().replace('project=fixture','project=other')])
 def test_normal_object_not_collection(self):
  with self.assertRaises(ApiError):self.members(self.s.a)
 def test_stale_membership_revision(self):
  old=self.members()['revision'];self.s.link(self.s.folder,self.s.b);self.s.db.commit()
  with self.assertRaises(ApiError) as e:self.change('remove',keys=[self.s.a.get_search_key()],revision=old)
  self.assertEqual(e.exception.code,'conflict')
 def test_stale_name_revision(self):
  old=self.members()['revision'];self.s.folder.set_value('name','Changed');self.s.folder.commit();self.s.db.commit()
  with self.assertRaises(ApiError):self.change('remove',keys=[self.s.a.get_search_key()],revision=old)
 def test_batch_validation_before_side_effect(self):
  n=self.members()['links']
  with self.assertRaises(ApiError):self.change('add',keys=[self.s.b.get_search_key(),'fixture/media?id=9876'])
  self.assertEqual(self.members()['links'],n)
 def test_missing_marker_schema_disabled(self):
  with patch('pyasm.search.SearchType.column_exists',return_value=False):
   with self.assertRaises(ApiError):self.op('GET','/collections')
 def test_read_only(self):
  self.b.allow_writes=False
  with self.assertRaises(ApiError):self.change('add')
 def test_delete_confirmation_required(self):
  with self.assertRaises(ApiError):self.change('delete')
 def test_delete_original_keeps_members(self):
  r=self.change('delete',confirm='DELETE_COLLECTION');self.assertEqual(r['operation'],'CollectionDeleteCmd')
  with self.assertRaises(ApiError):self.s.object('fixture/media',self.s.folder.get_search_key())
  self.assertIsNotNone(self.s.object('fixture/media',self.s.child.get_search_key()));self.assertIsNotNone(self.s.object('fixture/media',self.s.a.get_search_key()))
 def test_delete_cleans_incoming_links(self):
  self.change('delete',self.s.child,confirm='DELETE_COLLECTION');self.assertEqual(self.members()['total'],1)
 def test_duplicates_diagnosed_and_removed_by_original_command(self):
  self.s.link(self.s.folder,self.s.a);self.s.db.commit();self.assertEqual(self.members()['duplicate_links'],1);self.change('remove',keys=[self.s.a.get_search_key()]);self.assertEqual(self.members()['links'],1)
 def test_missing_members_reported(self):
  self.s.row('media_in_media',parent_code='ROOT',search_code='MISSING');self.s.db.commit();self.assertEqual(self.members()['missing_members'],1)
 def test_create_uses_original_view_and_fixed_flag(self):
  r=self.op('POST','/collections',values={'name':'New','description':'test'});o=self.s.object('fixture/media',r['collection']['key']);self.assertTrue(o.get_value('_is_collection'));self.assertEqual(self.b.create_calls[0]['view'],'edit_collection')
 def test_create_cannot_inject_marker(self):
  with self.assertRaises(ApiError):self.op('POST','/collections',values={'name':'New','_is_collection':False})
 def test_create_nested(self):
  old=self.members();self.op('POST','/collections',collection=self.s.folder.get_search_key(),revision=old['revision'],values={'name':'Nested'});self.assertEqual(self.members()['total'],3)
 def test_archived_item_add_denied(self):
  self.s.b.set_value('s_status','retired');self.s.b.commit();self.s.db.commit()
  with self.assertRaises(ApiError):self.change('add')
 def test_empty_selection_denied(self):
  with self.assertRaises(ApiError):self.op('POST','/collection-change',action='add',collection=self.s.folder.get_search_key(),keys=[],revision=self.members()['revision'])
 def test_fixed_widget_scope_cannot_switch_collections(self):
  original=self.b.open_target
  self.b.open_target=lambda k:dict(original(k),options={'collection_key':self.s.folder.get_search_key()})
  data=self.op('GET','/collections');self.assertEqual(data['total'],1);self.assertEqual(data['fixed_collection']['key'],self.s.folder.get_search_key());self.assertIsNone(data['records_target'])
  with self.assertRaises(ApiError):self.members(self.s.child)
 def test_fixed_scope_candidates_still_use_existing_objects(self):
  original=self.b.open_target;self.b.open_target=lambda k:dict(original(k),options={'collection_key':self.s.folder.get_search_key()})
  self.assertEqual(self.op('GET','/collections',mode='records')['total'],4)
 def test_original_shelf_option_disables_create(self):
  original=self.b.open_target;self.b.open_target=lambda k:dict(original(k),options={'show_collection_shelf':'false'})
  self.assertFalse(self.op('GET','/collections')['can_create'])
  with self.assertRaises(ApiError) as e:self.op('POST','/collections',values={'name':'Should not create'})
  self.assertEqual(e.exception.status,403)
 def test_expression_scope_not_silently_dropped(self):
  original=self.b.open_target;self.b.open_target=lambda k:dict(original(k),options={'expression':'@SOBJECT(test/item)'})
  with self.assertRaises(ApiError) as e:self.op('GET','/collections')
  self.assertEqual(e.exception.status,501)
 def test_source_execute_bodies_retained(self):
  data=json.loads((ROOT/'tests/native_ui/source-provenance-06.json').read_text());tree=ast.parse((ROOT/'src/tactic/core/collection_commands.py').read_text())
  for c in tree.body:
   if isinstance(c,ast.ClassDef):
    f=next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='execute');self.assertEqual(hashlib.sha256(ast.dump(f,include_attributes=False).encode()).hexdigest(),data['algorithm_hashes'][c.name+'.execute'])
if __name__=='__main__':unittest.main()
