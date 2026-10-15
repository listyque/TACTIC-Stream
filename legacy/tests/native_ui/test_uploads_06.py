"""Real disk staging and OS locks; no live TACTIC database is implied."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from tactic.ui_api.upload_store import UploadStore, CHUNK, MiB, filename, integer
from tactic.ui_api.contracts import ApiError

sha=lambda b:hashlib.sha256(b).hexdigest()
fp=lambda b:sha(b''.join(hashlib.sha256(b[o:o+CHUNK]).digest() for o in range(0,len(b),CHUNK)))

def finish_process(root,job,owner,binding):
 import time
 store=UploadStore(root,clock=lambda:1000.)
 def commit(path,state):
  with (Path(root)/'callback.log').open('ab') as log:log.write(b'committed\n');log.flush()
  time.sleep(.15)
  return {'snapshot':{'code':'CROSSPROCESS'}}
 store.finish(job,owner,binding,commit)

def crash_process(root,job):
 import os
 store=UploadStore(root,clock=lambda:1000.)
 with store._lock(job):
  state=store._read(job);state['state']='committing';store._save(state)
  os._exit(37)

class UploadTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=[1000.];self.store=UploadStore(self.tmp.name,clock=lambda:self.now[0]);self.owner='alice';self.binding={'project':'one','target':'items','key':'item-1'};self.count=0
 def tearDown(self):self.tmp.cleanup()
 def create(self,content=b'hello',**kwargs):
  self.count+=1;return self.store.create(self.owner,self.binding,name=kwargs.pop('name','sample.bin'),size=kwargs.pop('size',len(content)),fingerprint=kwargs.pop('fingerprint',fp(content)),context=kwargs.pop('context','publish'),request_id=kwargs.pop('request_id','request-'+str(self.count)),**kwargs)
 def chunk(self,j,b=b'hello',offset=0):return self.store.chunk(j['id'],self.owner,self.binding,offset,b,sha(b))
 def ready(self,b=b'hello',**kw):
  j=self.create(b,**kw)
  for offset in range(0,len(b),CHUNK):self.chunk(j,b[offset:offset+CHUNK],offset)
  return j
 def error(self,code,fn):
  with self.assertRaises(ApiError) as caught:fn()
  self.assertEqual(caught.exception.code,code)
 def test_create(self):
  j=self.create();self.assertEqual(j['offset'],0);self.assertEqual(j['state'],'uploading');self.assertEqual(j['size'],5)
 def test_reserved_metadata_name_is_safe(self):
  j=self.ready(name='state.json');self.assertEqual(self.store._read(j['id'])['offset'],5)
 def test_resume_after_new_store_instance(self):
  b=b'x'*CHUNK+b'last';j=self.create(b);self.chunk(j,b[:CHUNK]);s=UploadStore(self.tmp.name,clock=lambda:self.now[0]);self.assertEqual(s.status(j['id'],self.owner,self.binding)['offset'],CHUNK);self.assertEqual(self.chunk(j,b'last',CHUNK)['state'],'ready')
 def test_exact_chunk_retry_is_idempotent(self):
  j=self.create();a=self.chunk(j);self.assertEqual(self.chunk(j),a)
 def test_changed_chunk_retry_rejected(self):
  j=self.ready();self.error('chunk_replay',lambda:self.chunk(j,b'world'))
 def test_corrupt_chunk_rejected(self):
  j=self.create();self.error('checksum',lambda:self.store.chunk(j['id'],self.owner,self.binding,0,b'hello',sha(b'world')));self.assertEqual(self.store.status(j['id'],self.owner,self.binding)['offset'],0)
 def test_out_of_order_chunk(self):
  j=self.create(size=2*CHUNK);self.error('chunk_offset',lambda:self.chunk(j,b'x'*CHUNK,CHUNK))
 def test_partial_middle_chunk_rejected(self):
  j=self.create(size=CHUNK+1);self.error('chunk_range',lambda:self.chunk(j))
 def test_chunk_too_large(self):
  j=self.create(size=2*CHUNK);self.error('chunk_size',lambda:self.chunk(j,b'x'*(CHUNK+1)))
 def test_wrong_owner(self):
  j=self.create();self.error('upload_missing',lambda:self.store.status(j['id'],'bob',self.binding))
 def test_wrong_project(self):
  j=self.create();self.error('upload_missing',lambda:self.store.status(j['id'],self.owner,dict(self.binding,project='two')))
 def test_wrong_target(self):
  j=self.create();self.error('upload_missing',lambda:self.store.status(j['id'],self.owner,dict(self.binding,target='secret')))
 def test_invalid_id(self):self.error('upload_id',lambda:self.store.status('../state',self.owner,self.binding))
 def test_filename_validation(self):
  for n in ('../x','c:\\x','nul.txt','COM1','a\x00b','a\nb','a.','a ','.','', 'x'*181):
   with self.subTest(n=n):self.error('filename',lambda:filename(n))
 def test_unicode_filename(self):self.assertEqual(self.create(name='Модель №1.exr')['filename'],'Модель №1.exr')
 def test_context_validation(self):
  for c in ('../publish','/tmp','foo\\bar','x\n','',42):
   with self.subTest(c=c):self.error('context',lambda:self.create(context=c))
 def test_limits_reject_bool_and_negative(self):
  for size in (True,False,-1,0,1.5,'01'):
   with self.subTest(size=size):self.error('upload_value',lambda:self.create(size=size))
 def test_reserved_quota(self):
  self.store=UploadStore(self.tmp.name,max_file=100,owner_quota=110,global_quota=200,clock=lambda:self.now[0]);self.create(size=80);self.error('upload_quota',lambda:self.create(size=40))
 def test_global_quota(self):
  self.store=UploadStore(self.tmp.name,max_file=100,owner_quota=150,global_quota=160,clock=lambda:self.now[0]);self.create(size=90);self.owner='bob';self.error('upload_quota',lambda:self.create(size=80))
 def test_create_idempotency(self):
  a=self.create(request_id='stable-id');b=self.create(request_id='stable-id');self.assertEqual(a['id'],b['id']);self.assertEqual(len(list(Path(self.tmp.name).glob('*/state.json'))),1)
 def test_create_changed_body_conflict(self):
  self.create(request_id='stable-id');self.error('upload_replay',lambda:self.create(b'world',request_id='stable-id'))
 def test_file_limit(self):self.error('upload_value',lambda:self.create(size=self.store.max_file+1))
 def test_low_disk_refuses_create(self):
  with patch('tactic.ui_api.upload_store.shutil.disk_usage',return_value=type('D',(),{'free':1})()):self.error('upload_space',lambda:self.create())
 def test_expiry(self):
  j=self.create();self.now[0]+=86401;self.error('upload_expired',lambda:self.store.status(j['id'],self.owner,self.binding))
 def test_expired_can_cancel(self):
  j=self.create();self.now[0]+=86401;self.assertEqual(self.store.cancel(j['id'],self.owner,self.binding)['state'],'cancelled')
 def test_cancel_only_staging(self):
  j=self.ready();self.store.cancel(j['id'],self.owner,self.binding);self.assertFalse((Path(self.tmp.name)/j['id']/'payload'/'sample.bin').exists());self.error('upload_state',lambda:self.chunk(j))
 def test_incomplete_cannot_finish(self):
  j=self.create();self.error('upload_incomplete',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:None))
 def test_finish_calls_once_and_retains_receipt(self):
  j=self.ready();calls=[]
  def commit(path,state):calls.append(path.read_bytes());return {'snapshot':{'code':'SNAP-1'}}
  a=self.store.finish(j['id'],self.owner,self.binding,commit);b=self.store.finish(j['id'],self.owner,self.binding,commit)
  self.assertEqual(a,b);self.assertEqual(calls,[b'hello']);self.assertEqual(a['sha256'],sha(b'hello'));self.assertEqual(a['state'],'complete');self.assertFalse((Path(self.tmp.name)/j['id']/'payload'/'sample.bin').exists())
 def test_full_fingerprint_mismatch_blocks_checkin(self):
  j=self.ready(fingerprint='0'*64);self.error('file_fingerprint',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:self.fail('must not check in')))
  self.assertEqual(self.store.status(j['id'],self.owner,self.binding)['state'],'ready')
 def test_completed_cannot_cancel(self):
  j=self.ready();self.store.finish(j['id'],self.owner,self.binding,lambda *a:{});self.error('upload_state',lambda:self.store.cancel(j['id'],self.owner,self.binding))
 def test_failed_commit_never_retries(self):
  j=self.ready()
  def fail(*a):raise RuntimeError('DB failed after possible side effect')
  with self.assertRaises(RuntimeError):self.store.finish(j['id'],self.owner,self.binding,fail)
  self.assertEqual(self.store.status(j['id'],self.owner,self.binding)['state'],'uncertain');self.error('checkin_uncertain',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:self.fail('must not run')))
 def test_interrupted_commit_becomes_uncertain(self):
  j=self.ready();s=self.store._read(j['id']);s['state']='committing';self.store._save(s);self.assertEqual(self.store.status(j['id'],self.owner,self.binding)['state'],'uncertain')
 def test_unacknowledged_disk_tail_is_truncated(self):
  j=self.create();p=Path(self.tmp.name)/j['id']/'payload'/'sample.bin';p.write_bytes(b'JUNK'*100);self.chunk(j);self.assertEqual(p.read_bytes(),b'hello')
 def test_lost_acknowledged_bytes_fail(self):
  j=self.ready();(Path(self.tmp.name)/j['id']/'payload'/'sample.bin').write_bytes(b'he');self.error('upload_corrupt',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:{}))
 def test_metadata_does_not_expose_path_or_owner(self):
  j=self.ready();self.assertNotIn('owner',j);self.assertNotIn(self.tmp.name,json.dumps(j));self.assertNotIn('binding',j)
 def test_list_is_owner_and_binding_scoped(self):
  self.create();self.owner='bob';self.create();self.assertEqual(len(self.store.list('alice',self.binding)),1)
 def test_cleanup_expired_uploads_and_receipts(self):
  j=self.create();self.now[0]+=86401;self.assertEqual(self.store.cleanup(),1);self.assertFalse((Path(self.tmp.name)/j['id']).exists())
 def test_cleanup_does_not_remove_uncertain(self):
  j=self.create();s=self.store._read(j['id']);s['state']='uncertain';self.store._save(s);self.now[0]+=864001;self.assertEqual(self.store.cleanup(),0)
 def test_parallel_finish_runs_callback_once(self):
  j=self.ready();calls=[];results=[]
  def worker():results.append(self.store.finish(j['id'],self.owner,self.binding,lambda *a:(calls.append(1) or {'code':'snap'})))
  threads=[threading.Thread(target=worker) for _ in range(2)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(calls,[1]);self.assertEqual(len(results),2);self.assertEqual(results[0],results[1])
 def test_os_lock_across_processes_calls_once(self):
  import multiprocessing
  j=self.ready();ctx=multiprocessing.get_context('spawn')
  children=[ctx.Process(target=finish_process,args=(self.tmp.name,j['id'],self.owner,self.binding)) for _ in range(2)]
  for p in children:p.start()
  for p in children:
   p.join(12)
   if p.is_alive():p.kill();p.join()
   self.assertEqual(p.exitcode,0)
  self.assertEqual((Path(self.tmp.name)/'callback.log').read_bytes(),b'committed\n')
 def test_process_death_releases_lock_and_leaves_uncertain(self):
  import multiprocessing
  j=self.ready();p=multiprocessing.get_context('spawn').Process(target=crash_process,args=(self.tmp.name,j['id']));p.start();p.join(12)
  if p.is_alive():p.kill();p.join()
  self.assertEqual(p.exitcode,37);self.assertEqual(self.store.status(j['id'],self.owner,self.binding)['state'],'uncertain')
 def test_mutated_staged_bytes_do_not_reach_checkin(self):
  j=self.ready();(Path(self.tmp.name)/j['id']/'payload'/'sample.bin').write_bytes(b'world')
  self.error('file_fingerprint',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:self.fail('No callback')))
 def test_symlink_payload_rejected(self):
  j=self.ready();p=Path(self.tmp.name)/j['id']/'payload'/'sample.bin';p.unlink();p.symlink_to(Path(self.tmp.name)/j['id']/'state.json');self.error('upload_corrupt',lambda:self.store.finish(j['id'],self.owner,self.binding,lambda *a:{}))

if __name__=='__main__':unittest.main()
