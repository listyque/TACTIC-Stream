"""Real shared session files, OS processes, HTTP proxy transport and failure tests."""
from pathlib import Path
import contextlib, io, json, os, sqlite3, subprocess, sys, tempfile, threading, time, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools/local'))
from tactic.ui_api.shared_sessions import SharedSessionStore
from tactic.ui_api.contracts import ApiError
from cluster_gateway import Gateway, RoutingPool, filtered_headers, is_balanced
from local_lock import local_lock
from cluster import Cluster, preflight

class SharedSessionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'sessions.sqlite3';self.store=SharedSessionStore(self.path)
 def tearDown(self):self.tmp.cleanup()
 def test_other_store_reads_exact_session(self):
  token,s=self.store.create('user','original-ticket','site',{'name':'Тест'});other=SharedSessionStore(self.path).get(token)
  self.assertEqual(other,s)
 def test_shared_logout(self):
  token,_=self.store.create('u','ticket');SharedSessionStore(self.path).delete(token)
  with self.assertRaises(ApiError):self.store.get(token)
 def test_empty_or_unknown_cookie_rejected(self):
  for token in ('','unknown',None):
   with self.assertRaises(ApiError):self.store.get(token)
 def test_expired_cookie_rejected(self):
  s=SharedSessionStore(self.path,ttl=-1);token,_=s.create('u','t')
  with self.assertRaises(ApiError):s.get(token)
 def test_capacity_shared_between_workers(self):
  SharedSessionStore(self.path,max_sessions=1).create('a','t')
  with self.assertRaises(ApiError):SharedSessionStore(self.path,max_sessions=1).create('b','t')
 def test_expired_slots_reclaimed(self):
  SharedSessionStore(self.path,ttl=-1,max_sessions=1).create('a','t')
  token,_=SharedSessionStore(self.path,max_sessions=1).create('b','t');self.assertEqual(self.store.get(token).login,'b')
 def test_cookie_not_stored_in_clear(self):
  token,_=self.store.create('u','t')
  with sqlite3.connect(self.path) as db:row=db.execute('select digest from sessions').fetchone()
  self.assertNotEqual(row[0],token);self.assertEqual(row[0],self.store._key(token))
 def test_login_rate_limit_shared(self):
  for i in range(10):SharedSessionStore(self.path).login_attempt('127.0.0.1')
  with self.assertRaises(ApiError) as e:self.store.login_attempt('127.0.0.1')
  self.assertEqual(e.exception.status,429)
 def test_csrf_is_the_same_for_all_workers(self):
  token,s=self.store.create('u','t');other=SharedSessionStore(self.path);other.check_csrf(other.get(token),s.csrf)
  with self.assertRaises(ApiError):other.check_csrf(other.get(token),'bad')
 def test_access_from_actual_second_process(self):
  token,_=self.store.create('u','t')
  code='from tactic.ui_api.shared_sessions import SharedSessionStore; import sys; s=SharedSessionStore(sys.argv[1]); assert s.get(sys.argv[2]).ticket=="t"; s.delete(sys.argv[2])'
  env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')
  result=subprocess.run([sys.executable,'-c',code,str(self.path),token],env=env,capture_output=True,timeout=10)
  self.assertEqual(result.returncode,0,result.stderr)
  with self.assertRaises(ApiError):self.store.get(token)
 def test_private_file_permissions(self):
  if os.name!='nt':self.assertEqual(self.path.stat().st_mode & 0o777,0o600)

class RouteTests(unittest.TestCase):
 def test_only_explicit_reads_balance(self):
  for method,path in [('GET','/api/ui/v2/session'),('GET','/api/ui/v2/record'),('POST','/api/ui/v2/query')]:self.assertTrue(is_balanced(method,path))
 def test_mutations_and_legacy_stay_writer(self):
  for method,path in [('POST','/api/ui/v2/session'),('POST','/api/ui/v2/table-changes'),('PATCH','/api/ui/v2/record'),('GET','/tactic/admin/REST'),('GET','/api/ui/v2/record/extra'),('POST','/api/ui/v2/query/'),('DELETE','/api/ui/v2/session')]:self.assertFalse(is_balanced(method,path))
 def test_hop_headers_and_nominated_fields_removed(self):
  result=filtered_headers([('Connection','Keep-Alive, X-Private'),('X-Private','secret'),('Keep-Alive','1'),('Content-Type','x'),('Set-Cookie','a'),('Set-Cookie','b')])
  self.assertEqual(result,[('Content-Type','x'),('Set-Cookie','a'),('Set-Cookie','b')])
 def pool(self):return RoutingPool([dict(id=str(i+1),port=10000+i,healthy=True,requests=0,active=0,errors=0) for i in range(3)])
 def test_round_robin(self):
  p=self.pool();self.assertEqual([p.select(True)['id'] for _ in range(6)],['1','2','3','1','2','3'])
 def test_primary_only(self):
  p=self.pool();self.assertEqual([p.select(False)['id'] for _ in range(3)],['1']*3)
 def test_failed_primary_never_falls_back_to_reader(self):
  p=self.pool();p.workers[0]['healthy']=False;self.assertIsNone(p.select(False));self.assertIsNotNone(p.select(True))
 def test_unhealthy_reader_skipped(self):
  p=self.pool();p.workers[1]['healthy']=False;self.assertEqual([p.select(True)['id'] for _ in range(4)],['1','3','1','3'])
 def request(self,env,connection=None):
  p=self.pool();g=Gateway(p,'s'*48,9123);status=[];headers=[]
  base=dict(REMOTE_ADDR='127.0.0.1',HTTP_HOST='127.0.0.1:9123',REQUEST_METHOD='GET',PATH_INFO='/api/ui/v2/record',QUERY_STRING='',CONTENT_LENGTH='0');base['wsgi.input']=io.BytesIO();base.update(env)
  def start(s,h):status.append(s);headers.extend(h)
  if connection is None:body=b''.join(g(base,start))
  else:
   with patch('cluster_gateway.http.client.HTTPConnection',side_effect=connection):body=b''.join(g(base,start))
  return status,headers,body,p
 def test_host_validation(self):self.assertTrue(self.request({'HTTP_HOST':'external.test'})[0][0].startswith('400'))
 def test_nonlocal_client_denied(self):self.assertTrue(self.request({'REMOTE_ADDR':'10.0.0.1'})[0][0].startswith('403'))
 def test_upgrade_denied(self):self.assertTrue(self.request({'HTTP_UPGRADE':'websocket'})[0][0].startswith('400'))
 def test_chunked_input_denied(self):self.assertTrue(self.request({'HTTP_TRANSFER_ENCODING':'chunked'})[0][0].startswith('400'))
 def test_get_body_denied(self):self.assertTrue(self.request({'CONTENT_LENGTH':'1'})[0][0].startswith('400'))
 def test_size_bound(self):self.assertTrue(self.request({'CONTENT_LENGTH':str(34*1024**2)})[0][0].startswith('413'))
 def test_wrong_health_method(self):self.assertTrue(self.request({'REQUEST_METHOD':'POST','PATH_INFO':'/__cluster/health'})[0][0].startswith('405'))
 def test_connection_failure_never_retried(self):
  calls=[]
  def fail(*a,**kw):calls.append(a);raise OSError('lost')
  status,headers,body,p=self.request({'REQUEST_METHOD':'POST','PATH_INFO':'/api/ui/v2/record'},fail)
  self.assertEqual(len(calls),1);self.assertTrue(status[0].startswith('502'));self.assertEqual(p.workers[0]['active'],0);self.assertIn(b'upstream_uncertain',body)
 def test_health_has_no_secret(self):
  status,_,body,_=self.request({'PATH_INFO':'/__cluster/health'});self.assertIn(b'healthy_workers',body);self.assertNotIn(b'sssss',body)

class LifetimeLockTests(unittest.TestCase):
 def test_multiple_read_leases_allow_workers(self):
  with tempfile.TemporaryDirectory() as d:
   with local_lock(Path(d),shared=True),local_lock(Path(d),shared=True):pass
 def test_exclusive_blocked_by_worker(self):
  with tempfile.TemporaryDirectory() as d:
   with local_lock(Path(d),shared=True):
    with self.assertRaises(RuntimeError):
     with local_lock(Path(d)):pass
 def test_worker_blocked_by_offline_upgrade(self):
  with tempfile.TemporaryDirectory() as d:
   with local_lock(Path(d)):
    with self.assertRaises(RuntimeError):
     with local_lock(Path(d),shared=True):pass
 def test_worker_lease_is_cross_process(self):
  with tempfile.TemporaryDirectory() as d:
   with local_lock(Path(d),shared=True):
    code='from local_lock import local_lock; from pathlib import Path; import sys\nwith local_lock(Path(sys.argv[1])): pass'
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'tools/local')
    p=subprocess.run([sys.executable,'-c',code,d],env=env,capture_output=True,timeout=10)
    self.assertNotEqual(p.returncode,0);self.assertIn(b'Another local TACTIC',p.stderr)
 def test_second_supervisor_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   with local_lock(Path(d),name='.native-cluster-owner.lock'):
    with self.assertRaises(RuntimeError):
     with local_lock(Path(d),name='.native-cluster-owner.lock'):pass
 def test_exclusive_lock_released_after_exception(self):
  with tempfile.TemporaryDirectory() as d:
   try:
    with local_lock(Path(d)):raise ValueError()
   except ValueError:pass
   with local_lock(Path(d)):pass
 def test_startup_rejects_live_auto_upgrade(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.xml';p.write_text('<config><portal><auto_upgrade>true</auto_upgrade></portal></config>')
   with self.assertRaises(RuntimeError):preflight(Path(d),p)
 def test_interrupted_promotion_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'.sqlite-promotion.json').write_text('{}');(p/'config.xml').write_text('<config/>')
   with self.assertRaises(RuntimeError):preflight(p,p/'config.xml')
 def test_concurrent_status_writes_atomic(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);c=Cluster(p,p/'unused.xml');failures=[]
   def write():
    try:
     for _ in range(50):c.write_status();json.loads(c.status_path.read_text())
    except Exception as exc:failures.append(str(exc))
   ts=[threading.Thread(target=write) for _ in range(4)]
   for t in ts:t.start()
   for t in ts:t.join()
   self.assertEqual(failures,[])


class GatewayConcurrencyTests(unittest.TestCase):
 def exercise(self,method,path):
  active=0;peak=0;mu=threading.Lock();calls=[]
  class Response:
   status=200;reason='OK'
   def getheaders(self):return [('Content-Length','0')]
   def read(self,*a):return b''
   def close(self):pass
  class Connection:
   def __init__(self,*a,**kw):self.sock=self;calls.append(a)
   def connect(self):pass
   def settimeout(self,t):pass
   def putrequest(self,*a,**kw):pass
   def putheader(self,*a):pass
   def endheaders(self):pass
   def getresponse(self):
    nonlocal active,peak
    with mu:active+=1;peak=max(peak,active)
    time.sleep(.06)
    with mu:active-=1
    return Response()
   def close(self):pass
  pool=RoutingPool([dict(id=str(i+1),port=10000+i,healthy=True,requests=0,active=0,errors=0) for i in range(3)])
  gateway=Gateway(pool,'s'*48,9123);errors=[]
  def request():
   env=dict(REMOTE_ADDR='127.0.0.1',HTTP_HOST='127.0.0.1:9123',REQUEST_METHOD=method,PATH_INFO=path,CONTENT_LENGTH='0');env['wsgi.input']=io.BytesIO()
   try:list(gateway(env,lambda *a:None))
   except Exception as exc:errors.append(str(exc))
  with patch('cluster_gateway.http.client.HTTPConnection',Connection):
   ts=[threading.Thread(target=request) for _ in range(6)]
   for t in ts:t.start()
   for t in ts:t.join()
  self.assertFalse(errors)
  return peak,calls
 def test_mutation_lane_serializes_parallel_clients(self):
  peak,calls=self.exercise('POST','/api/ui/v2/record');self.assertEqual(peak,1);self.assertEqual(len(calls),6);self.assertEqual({a[1] for a in calls},{10000})
 def test_read_query_lane_does_not_serialize_workers(self):
  peak,calls=self.exercise('POST','/api/ui/v2/query');self.assertGreater(peak,1);self.assertEqual({a[1] for a in calls},{10000,10001,10002})

if __name__=='__main__':unittest.main()
