"""Additional real HTTP tests; backend remains synthetic, not a live TACTIC DB."""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/0.3/http-deep-results.json'));a=p.parse_args()
s=requests.Session();results=[]
def ok(name,condition):
 assert condition,name
 results.append({'scenario':name,'passed':True});print('PASS',name)
def call(method,path,data=None,headers=None):
 return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers or h,timeout=8)
h={'X-Tactic-UI':'1'}
try:
 r=call('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=r.json()['csrf'];ok('Authenticated deep test session',r.status_code==200)
 args={'project':'admin','target':'admin_views/project_essentials/project_tasks'}
 r=call('GET','/open',args);spec=r.json()['spec'];ok('Task target resolved from original XML',r.status_code==200 and spec['type']=='sthpw/task')
 r=call('POST','/query',{**args,'limit':50,'offset':0,'filters':[]});rows=r.json()['items'];ok('Native task query',r.status_code==200 and len(rows)==12)
 forms=[call('GET','/form',{**args,'key':row['key']}).json() for row in rows[:2]]
 data={**args,'records':[{'key':f['record']['key'],'revision':f['record']['revision'],'values':{'description':'Bulk HTTP check'}} for f in forms]}
 r=call('PATCH','/bulk-records',data);ok('Bulk operation across two rows via real transport',r.status_code==200 and r.json()['count']==2)
 r=call('PATCH','/bulk-records',data);ok('Stale bulk revisions return conflict',r.status_code==409)
 note={**args,'key':rows[0]['key'],'process':'review','note':'HTTP note'}
 r=call('POST','/notes',note);ok('Create discussion note',r.status_code==200)
 r=call('GET','/notes',note);ok('Read persisted discussion contract',r.status_code==200 and r.json()['items'][0]['note']=='HTTP note')
 r=call('GET','/relations',note);ok('Read configured relation target',r.status_code==200 and '/~related/' in r.json()['items'][0]['target'])
 r=call('GET','/snapshots',note);snapshot=r.json()['items'][0];ok('Version owns explicit file list',r.status_code==200 and snapshot['files'][0]['code']=='TESTFILE')
 fileargs={**args,'key':rows[0]['key'],'snapshot':snapshot['key'],'file':'TESTFILE'}
 r=call('GET','/file',fileargs);ok('Actual streamed download, not JSON filesystem path',r.status_code==200 and r.content==b'TACTIC native UI 0.3 test file\n' and 'attachment' in r.headers.get('Content-Disposition',''))
 ok('Private download headers',r.headers.get('Cache-Control')=='no-store' and r.headers.get('X-Content-Type-Options')=='nosniff' and "sandbox" in r.headers.get('Content-Security-Policy',''))
 r=call('GET','/file',fileargs,{'Range':'bytes=0-5'});ok('Byte-range delivery for media transport',r.status_code==206 and r.content==b'TACTIC')
 r=call('GET','/file',{**fileargs,'file':'NOT-IN-SNAPSHOT'});ok('Unknown version file not served',r.status_code==404)
 r=requests.get(a.url+'/api/ui/v2/file',params=fileargs,timeout=8);ok('File delivery requires an active session',r.status_code==401)
 graphargs={'project':'admin','kind':'pipeline','key':'sthpw/pipeline?code=FIXTURE'}
 g=call('GET','/graph',graphargs).json();op={**graphargs,'revision':g['revision'],'operations':[{'op':'add_node','name':'http_test','attributes':{'type':'manual','xpos':10,'ypos':20}}]}
 r=call('PATCH','/graph',op);ok('Graph XML structure mutation via HTTP',r.status_code==200)
 r=call('PATCH','/graph',op);ok('Graph stale revision rejected',r.status_code==409)
 g=call('GET','/graph',graphargs).json();ok('Original extension attributes preserved', 'custom="A &amp; B"' in g['xml'])
 r=call('PATCH','/graph',{**graphargs,'revision':g['revision'],'operations':[{'op':'delete_everything'}]});ok('Unknown graph operation rejected as 400',r.status_code==400)
 viewargs={'project':'admin','search_type':'sthpw/task','view':'table'};v=call('GET','/view-config',viewargs).json()
 r=call('PATCH','/view-config',{**viewargs,'revision':v['revision'],'operations':[{'op':'update','index':1,'attributes':{'title':'HTTP description'}}]});ok('View metadata edit stored through HTTP',r.status_code==200)
 r=call('GET','/view-config',viewargs);ok('View title round trip',r.json()['elements'][1]['title']=='HTTP description')
 r=call('PATCH','/view-config',{**viewargs,'revision':v['revision'],'operations':[]});ok('View stale revision rejected',r.status_code==409)
 r=call('GET','/open',{'project':'admin','target':'admin_views/create_project'});ok('Source app.ProjectCreateWdg is mapped to native screen',r.json()['kind']=='project-create')
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'transport':'real requests HTTP to original bundled CherryPy','backend':'synthetic fixtures; not live PostgreSQL','scenarios':results},ensure_ascii=False,indent=2)+'\n')
