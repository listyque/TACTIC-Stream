import unittest
from collection_test_store import Store,Backend
from tactic.ui_api.contracts import ApiError

class VersionTests(unittest.TestCase):
 def setUp(self):
  self.s=Store();self.s.seed();self.b=Backend(self.s);self.bound=self.b.bind();self.bound.__enter__()
  for n in range(125):
   self.s.row('snapshot',code='SNAP'+str(n),search_type=self.s.a.get_search_type(),search_code='A',context='publish' if n<120 else 'review',process='publish',version=n+1,timestamp='2026-09-01 10:%02d:%02d'%(n//60,n%60),login='fixture',is_current=n==119,is_latest=n==119,snapshot='<snapshot><file file_code="FILE"/></snapshot>')
  self.s.row('file',code='FILE',name='image.png',size=1234,type='main');self.s.db.commit()
 def tearDown(self):self.bound.__exit__(None,None,None);self.s.close()
 def op(self,method='GET',path='/file-versions',**v):return self.b.version_operation(method,path,dict(target='media',key=self.s.a.get_search_key(),**v))
 def snap(self,n=0):return self.s.search_code('sthpw/snapshot','SNAP'+str(n))
 def current(self,n=0,**v):return self.op(path='/snapshot-current',snapshot=self.snap(n).get_search_key(),**v)
 def test_not_capped_at_100(self):
  data=self.op();self.assertEqual(data['total'],125);self.assertEqual(len(data['items']),40);self.assertTrue(data['has_more'])
 def test_stable_pages(self):
  rows=[]
  for offset in (0,40,80,120):rows.extend(self.op(offset=offset)['items'])
  self.assertEqual(len(rows),125);self.assertEqual(len({r['key'] for r in rows}),125)
 def test_context_filter(self):self.assertEqual(self.op(context='review')['total'],5)
 def test_no_foreign_versions(self):
  self.s.row('snapshot',code='SECRET',search_type=self.s.b.get_search_type(),search_code='B',context='publish',version=1);self.assertEqual(self.op()['total'],125)
 def test_file_data_comes_from_snapshot_xml(self):
  row=self.op()['items'][0];self.assertEqual(row['files'][0]['code'],'FILE');self.assertEqual(row['files'][0]['name'],'image.png');self.assertTrue(row['files'][0]['preview'])
 def test_missing_registered_file_reported(self):
  self.s.search_code('sthpw/file','FILE').delete();row=self.op()['items'][0];self.assertTrue(row['files'][0]['missing_registration'])
 def test_current_preview_shows_current_not_latest(self):
  data=self.current();self.assertEqual(data['selected']['code'],'SNAP0');self.assertEqual([r['code'] for r in data['current']],['SNAP119'])
 def test_current_calls_original_stub(self):
  preview=self.current();r=self.op('POST','/snapshot-current',snapshot=self.snap().get_search_key(),revision=preview['revision'],confirm='SET_CURRENT');self.assertFalse(r['latest_changed']);self.assertEqual(self.b.current_calls,['SNAP0']);self.assertEqual(self.s.versionless_calls,[('SNAP0','current')]);self.assertTrue(self.snap(119).get_value('is_latest'))
 def test_current_stale_conflict(self):
  preview=self.current();row=self.snap(1);row.set_value('description','Changed');row.commit();self.s.db.commit()
  with self.assertRaises(ApiError) as e:self.op('POST','/snapshot-current',snapshot=self.snap().get_search_key(),revision=preview['revision'],confirm='SET_CURRENT')
  self.assertEqual(e.exception.code,'conflict');self.assertFalse(self.b.current_calls)
 def test_current_requires_confirmation(self):
  with self.assertRaises(ApiError):self.op('POST','/snapshot-current',snapshot=self.snap().get_search_key(),revision=self.current()['revision'])
 def test_retired_not_current(self):
  row=self.snap();key=row.get_search_key();row.set_value('s_status','retired');row.commit()
  with self.assertRaises(ApiError):self.op(path='/snapshot-current',snapshot=key)
 def test_versionless_not_current(self):
  row=self.snap();row.set_value('version',-1);row.commit()
  with self.assertRaises(ApiError):self.current()
 def test_id_only_legacy_snapshot_not_current(self):
  row=self.snap();row.set_value('search_code','');row.commit()
  # Scope guard normally rejects the id-only fixture. Isolate the downstream guard.
  self.b._snapshot_for=lambda *a:row
  with self.assertRaises(ApiError) as e:self.current()
  self.assertEqual(e.exception.code,'legacy_snapshot')
 def test_archive_toggle(self):
  row=self.snap();row.set_value('s_status','retired');row.commit();self.assertEqual(self.op()['total'],124);self.assertEqual(self.op(record_state='all')['total'],125)
 def test_read_only(self):
  self.b.allow_writes=False;preview=self.current();self.assertFalse(preview['can_write'])
  with self.assertRaises(ApiError):self.op('POST','/snapshot-current',snapshot=self.snap().get_search_key(),revision=preview['revision'],confirm='SET_CURRENT')
 def test_level_scope(self):
  row=self.snap();row.set_value('level_type','test/level');row.set_value('level_id',1);row.commit();self.assertEqual(self.current()['current'],[])
 def test_invalid_pagination(self):
  for kw in ({'offset':-1},{'limit':101},{'limit':True}):
   with self.subTest(kw=kw),self.assertRaises(ApiError):self.op(**kw)
 def test_no_server_paths(self):self.assertNotIn('/mnt/',str(self.op()))
if __name__=='__main__':unittest.main()
