"""Actual HTTP checks against the test-only bundled CherryPy process."""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/http-results.json'));a=p.parse_args()
results=[];s=requests.Session()
def ok(name,condition):
 assert condition,name
 results.append({'scenario':name,'passed':True});print('PASS',name)
def request(method,path,**kw):return s.request(method,a.url+path,timeout=8,**kw)
try:
 for path in ('/','/tactic/admin/','/tactic/admin/link/users','/tactic/fixture/'):
  r=request('GET',path,headers={'Accept':'text/html'});ok('Native shell '+path,r.status_code==200 and '/tactic-ui/app.js' in r.text)
  ok('CSP excludes eval '+path,"'unsafe-eval'" not in r.headers.get('Content-Security-Policy','') and "frame-ancestors 'none'" in r.headers.get('Content-Security-Policy',''))
 for path in ('/tactic/default/Api/','/tactic/admin/REST/','/tactic/admin/UploadServer/'):
  r=request('GET',path,headers={'Accept':'text/html'});ok('Legacy service not intercepted '+path,'LEGACY SERVICE SENTINEL'==r.text)
 r=request('HEAD','/tactic/admin/',headers={'Accept':'text/html'});ok('Native HEAD no body',r.status_code==200 and not r.content)
 r=request('GET','/tactic-ui/app.js');ok('Compiled application static delivery',r.status_code==200 and 'Vue.createApp' in r.text and '<html' not in r.text)
 r=request('GET','/api/ui/v2/health');ok('Health honestly separates transport from database',r.json()['mode']=='test-fixture' and r.json()['database_checked'] is False)
 r=request('POST','/api/ui/v2/session',json={'login':'fixture','password':'fixture-only'},headers={'X-Tactic-UI':'1'});d=r.json();ok('POST JSON through actual bundled raw body reader',r.status_code==200 and 'csrf' in d);ok('Cookie flags/path and private ticket hidden','HttpOnly' in r.headers['Set-Cookie'] and 'SameSite=Strict' in r.headers['Set-Cookie'] and 'Path=/api/ui/v2' in r.headers['Set-Cookie'] and 'not-a-real-tactic-ticket' not in r.text)
 headers={'X-Tactic-UI':'1','X-CSRF-Token':d['csrf']}
 r=request('GET','/api/ui/v2/sidebar',params={'project':'admin'});ok('Original XML tree returned over HTTP',r.status_code==200 and r.json()['sections'])
 r=request('GET','/api/ui/v2/open',params={'project':'admin','target':'invented/anything'});ok('Unknown config target is denied',r.status_code==403)
 r=request('POST','/api/ui/v2/query',json={'project':'admin'},headers={'X-Tactic-UI':'1'});ok('Missing CSRF rejected',r.status_code==403)
 r=request('POST','/api/ui/v2/query',json={'project':'admin'},headers={**headers,'Origin':'https://foreign.invalid'});ok('Foreign Origin rejected',r.status_code==403)
 r=request('PATCH','/api/ui/v2/config',data='not json',headers={**headers,'Content-Type':'application/json'});ok('Malformed JSON gets JSON 400',r.status_code==400 and r.json().get('error'))
 r=request('DELETE','/api/ui/v2/session',json={},headers=headers);ok('Logout invalidates HTTP cookie session',r.status_code==200)
 r=request('GET','/api/ui/v2/projects');ok('Revoked session cannot read projects',r.status_code==401)
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'transport':'real HTTP via requests to original bundled CherryPy','backend':'test-only synthetic storage; original sidebar XML','scenarios':results},ensure_ascii=False,indent=2)+'\n')
