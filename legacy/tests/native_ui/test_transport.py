import sys,json,unittest,time
from pathlib import Path
from contextlib import contextmanager
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'src'))
from tactic.ui_api.routing import native_page
from tactic.ui_api.api import Api,Request,COOKIE
from tactic.ui_api.session import SessionStore
from tactic.ui_api.contracts import ApiError,clean_query,clean_values,json_safe,revision
from decimal import Decimal

class RoutingTests(unittest.TestCase):
 def test_native_pages(self):
  for path in ('/','/tactic','/tactic/admin/','/tactic/proj/index/','/tactic/proj/link/users'):self.assertTrue(native_page(path),path)
 def test_service_paths_never_native(self):
  for path in ('/tactic/default/Api','/tactic/proj/REST','/tactic/proj/UploadServer/','/api/ui/v2/','/tactic-ui/app.js','/assets/file','/context/tactic.js','/tactic/proj/custom_endpoint'):
   self.assertFalse(native_page(path),path)
 def test_non_get_never_intercepted(self):
  for method in ('POST','DELETE','PATCH','OPTIONS'):self.assertFalse(native_page('/tactic/admin',method))
 def test_non_html(self):self.assertFalse(native_page('/tactic/admin',accept='application/json'))
 def test_multisite_path(self):self.assertTrue(native_page('/tactic/studio/project/index/',site='studio'));self.assertFalse(native_page('/tactic/studio/project/REST/',site='studio'))

class Stub:
 mode='test-only'
 @contextmanager
 def context(self,*a,**k):yield
 def identity(self,session):return {'login':session.login}
 def projects(self):return [{'code':'admin','name':'Admin'}]
 def sidebar(self):return {'sections':[]}
 def login(self,name,pw,two):return {'login':name,'ticket':'NEVER_SEND_THIS','site':''}
 def config_operation(self,m,p,d):raise ValueError('invalid XML')

class TransportTests(unittest.TestCase):
 def setUp(self):
  self.api=Api(Stub());self.token,self.session=self.api.sessions.create('admin','private-ticket')
 def request(self,method,path,data=None,auth=True,csrf=True,origin=None,secure=False):
  h={'host':'localhost:9123','x-tactic-ui':'1','content-type':'application/json'}
  if auth:h['cookie']=COOKIE+'='+self.token
  if csrf:h['x-csrf-token']=self.session.csrf
  if origin:h['origin']=origin
  return self.api.handle(Request(method,path,data or {} if method=='GET' else {},h,b'' if method=='GET' else json.dumps(data or {}).encode(),secure=secure))
 def test_requires_session(self):self.assertEqual(self.request('GET','/projects',auth=False).status,401)
 def test_real_ticket_not_returned(self):
  r=self.request('GET','/session');self.assertEqual(r.status,200);self.assertNotIn('private-ticket',json.dumps(r.data))
 def test_csrf_required(self):self.assertEqual(self.request('POST','/query',{'project':'admin'},csrf=False).status,403)
 def test_foreign_origin_rejected(self):self.assertEqual(self.request('POST','/query',{'project':'admin'},origin='https://evil.invalid').status,403)
 def test_scheme_is_part_of_origin(self):self.assertEqual(self.request('POST','/query',{'project':'admin'},origin='https://localhost:9123').status,403)
 def test_login_cookie_flags_and_no_ticket(self):
  r=self.request('POST','/session',{'login':'admin','password':'x'},auth=False);self.assertEqual(r.status,200);self.assertIn('HttpOnly',r.headers['Set-Cookie']);self.assertIn('SameSite=Strict',r.headers['Set-Cookie']);self.assertIn('/api/ui/v2',r.headers['Set-Cookie']);self.assertNotIn('NEVER_SEND_THIS',json.dumps(r.data))
 def test_xml_input_error_not_500(self):self.assertEqual(self.request('PATCH','/config',{'project':'admin'}).status,400)
 def test_logout_invalidates_session(self):
  self.assertEqual(self.request('DELETE','/session').status,200);self.assertEqual(self.request('GET','/session').status,401)
 def test_health_explicit_fixture_backend(self):self.assertEqual(self.request('GET','/health',auth=False).data['mode'],'test-only')
 def test_bad_json(self):
  r=self.api.handle(Request('POST','/session',{}, {'x-tactic-ui':'1','content-type':'application/json'},b'not json'));self.assertEqual(r.status,400)
 def test_response_never_cached(self):self.assertEqual(self.request('GET','/projects').headers['Cache-Control'],'no-store')

class ValidationTests(unittest.TestCase):
 FIELD={'name':'price','kind':'number','label':'Price','read_only':False,'storage':True}
 def test_exact_decimal(self):self.assertEqual(clean_values({'price':'1234567890123456.12345'},[self.FIELD])['price'],'1234567890123456.12345')
 def test_secret_rejected(self):
  with self.assertRaises(ApiError):clean_values({'password':'x'},[{'name':'password','kind':'text','read_only':False}])
 def test_readonly_rejected(self):
  with self.assertRaises(ApiError):clean_values({'id':5},[{'name':'id','kind':'integer','read_only':False}])
 def test_nan_rejected(self):
  with self.assertRaises(ApiError):clean_values({'price':'NaN'},[self.FIELD])
 def test_query_boundaries(self):
  with self.assertRaises(ApiError):clean_query({'limit':201},[self.FIELD])
 def test_large_ids_not_rounded(self):self.assertEqual(json_safe(9007199254740993),'9007199254740993')
 def test_revision_order_independent(self):self.assertEqual(revision({'a':1,'b':2}),revision({'b':2,'a':1}))
 def test_rate_limit(self):
  s=SessionStore()
  for _ in range(10):s.login_attempt('x')
  with self.assertRaises(ApiError):s.login_attempt('x')
 def test_expired_session(self):
  s=SessionStore(ttl=-1);token,_=s.create('a','private')
  with self.assertRaises(ApiError):s.get(token)

if __name__=='__main__':unittest.main()
