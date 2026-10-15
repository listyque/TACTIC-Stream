"""Real bundled CherryPy HTTP + production ScriptService, isolated TEST DB/auth."""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True);a=p.parse_args()
s=requests.Session();headers={'X-Tactic-UI':'1'};results=[]
base={'project':'admin','target':'admin_views/project_admin/script_editor'}
def check(name,ok):
 assert ok,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def req(method,path,data=None,override=None):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=override or headers,timeout=20)
def op(method,path,**data):return req(method,path,dict(base,**data))
try:
 check('Saved scripts require session',op('GET','/scripts').status_code==401)
 r=req('POST','/session',{'login':'fixture','password':'fixture-only'});headers['X-CSRF-Token']=r.json()['csrf']
 side=req('GET','/sidebar',{'project':'admin'}).json()
 def walk(nodes):
  for n in nodes:
   if n.get('name')=='script_editor':yield n
   yield from walk(n.get('children',[]))
 links=list(walk([n for section in side['sections'] for n in section['children']]))
 check('Script editor comes from stock widget_config sidebar',len(links)==1);base['target']=links[0]['id']
 r=op('GET','/open');check('Stock ShelfEditWdg opens native editor',r.status_code==200 and r.json()['kind']=='script-editor' and r.json()['handler']=='tactic.ui.app.ShelfEditWdg')
 data=op('GET','/scripts',limit=20).json();check('Directory is server-paged',data['total']==65 and len(data['items'])==20 and data['has_more'])
 more=op('GET','/scripts',limit=20,offset=20).json();check('Directory pages do not overlap',not {x['key'] for x in data['items']}&{x['key'] for x in more['items']})
 check('Directory does not return all script bodies',all('script' not in x['values'] for x in data['items']))
 check('Virtual nested folder filter',op('GET','/scripts',folder='workflow/review').json()['total']==32)
 check('Injection-like search is a literal string',op('GET','/scripts',q="' OR 1=1 --").json()['total']==0)
 rec=op('GET','/script',key=data['items'][0]['key']).json()['record'];check('Read original source content',rec['values']['script'].startswith('# TEST FIXTURE'))
 check('Original folder/title lookup',op('GET','/script',script_path='tools/script_000').json()['record']['values']['title']=='script_000')
 check('Cross-project search key forbidden',op('GET','/script',key=rec['key'].replace('project=admin','project=fixture')).status_code==403)
 check('Cross-type key forbidden',op('GET','/script',key='sthpw/login?code=admin').status_code==403)
 values={'folder':'native/test','title':'new%_script','language':'python','script':'# Привет\r\nvalue = 0\r\n','description':'Описание'}
 r=op('POST','/script',values=values);check('Save creates original custom_script record via service',r.status_code==200 and r.json()['saved']);created=r.json()['record']
 check('Source whitespace and CRLF survive round trip',created['values']['script']==values['script'])
 check('Exact percent/underscore search preserved',op('GET','/scripts',q='%_').json()['total']==1)
 check('Duplicate path does not overwrite',op('POST','/script',values=values).status_code==409)
 changed=dict(values,script='result = 42\n');r=op('PATCH','/script',key=created['key'],revision=created['revision'],values=changed);check('Update retains same search key',r.status_code==200 and r.json()['record']['key']==created['key'])
 check('Stale source revision rejected',op('PATCH','/script',key=created['key'],revision=created['revision'],values=values).status_code==409)
 check('Rejected stale edit preserves newest source',op('GET','/script',key=created['key']).json()['record']['values']['script']=='result = 42\n')
 check('Python syntax check is not execution',op('POST','/script-check',language='python',script='raise RuntimeError("must not run")').json()=={'checked':True,'valid':True,'executed':False,'notice':'Проверен только синтаксис. Имена, импорты и поведение workflow не проверялись.'})
 check('Python syntax error reports failure',op('POST','/script-check',language='python',script='x =').json()['valid'] is False)
 check('XML entities not read',op('POST','/script-check',language='xml',script='<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><x>&a;</x>').json()['valid'] is False)
 check('JS syntax verification not falsely claimed',op('POST','/script-check',language='javascript',script='anything').json()['checked'] is False)
 check('No Run endpoint',op('POST','/script-run',key=created['key']).status_code>=400)
 check('CSRF required for saving',req('POST','/script',dict(base,values=values),{'X-Tactic-UI':'1','X-CSRF-Token':'wrong'}).status_code==403)
 check('Another configured target cannot read script editor data',req('GET','/scripts',dict(base,target='admin_views/global_admin/system_info')).status_code==403)
 table=req('GET','/open',dict(base,target=data['manage_target']));check('Original Manage operation opens config table',table.status_code==200 and table.json()['search_type']=='config/custom_script' and [f['name'] for f in table.json()['spec']['fields']]==['folder','title','description','language'])
 check('Script responses private no-store',r.headers.get('Cache-Control')=='no-store')
 check('No writes enabled in shipped production config',json.loads((Path(__file__).resolve().parents[2]/'src/tactic/ui_api/config.json').read_text())['allow_writes'] is False)
except Exception as exc:results.append({'scenario':'failure','passed':False,'error':str(exc)});raise
finally:
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'scope':'real HTTP and ScriptService; isolated SQL/persistence/auth collaborators, not production database','scenarios':results},ensure_ascii=False,indent=2)+'\n')
