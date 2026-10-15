"""Original-table Fill preview over HTTP: no writes until original Save Changes."""
import argparse, json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
s=requests.Session();h={'X-Tactic-UI':'1'};root=a.url+'/api/ui/v2';result=[]
def check(n,ok):
 result.append({'scenario':n,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+n,flush=True)
 if not ok:raise AssertionError(n)
def req(method,path,**data):return s.request(method,root+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=h,timeout=60)
def good(r):
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text[:1500])
 return r.json()
args={'project':'admin','target':'admin_views/global_admin/users'}
def op(m,path,**kw):return req(m,path,**args,**kw)
def record(key):return good(op('GET','/record',key=key))
try:
 check('Unauthenticated fill rejected',op('POST','/table-fill-preview').status_code==401)
 h['X-CSRF-Token']=good(req('POST','/session',login='admin',password='Native-Test-Only-123'))['csrf']
 rows=good(op('POST','/query',limit=100))['items'];rows=[r for r in rows if r['values'].get('login') in ('grid_anna','grid_alex')]
 check('Two original user records available',len(rows)==2)
 spec=good(op('GET','/open'))['spec'];before={r['key']:record(r['key']) for r in rows}
 records=[{'key':r['key'],'revision':before[r['key']]['revision'],'pending':{}} for r in rows]
 def preview(**override):
  data={'field':'last_name','value':'Общее значение','table_revision':spec['revision'],'records':records};data.update(override)
  return op('POST','/table-fill-preview',**data)
 data=good(preview());check('Fill resolves each original CellEdit definition',len(data['items'])==2 and all(i['field']['name']=='last_name' for i in data['items']))
 check('Preview explicitly reports no writes',data['writes_performed'] is False)
 check('Preview did not change either original row',all(record(k)['revision']==v['revision'] for k,v in before.items()))
 check('Missing table revision rejected',preview(table_revision=None).status_code==409)
 check('Missing row revision rejected',preview(records=[{'key':rows[0]['key']}]).status_code==409)
 check('Duplicate row keys rejected',preview(records=[records[0],records[0]]).status_code==400)
 check('More than 100 selected rows rejected',preview(records=[records[0]]*101).status_code==400)
 check('Empty selection rejected',preview(records=[]).status_code==400)
 check('Unknown configured field rejected',preview(field='not_a_column').status_code==403)
 check('Protected identity cannot be filled',preview(field='code').status_code==403)
 check('Password cannot be filled',preview(field='password').status_code in (400,403))
 check('Invalid input type rejected before staging',preview(value={'bad':'object'}).status_code==400)
 check('Explicit NULL supported by per-row nullable rules',all(i['value'] is None for i in good(preview(value=None))['items']))
 pending=[{**records[0],'pending':{'first_name':'Unsaved independent value'}},records[1]]
 data=good(preview(records=pending));check('Pending fields used in per-row validation',len(data['items'])==2)
 check('Pending input did not persist from preview',record(rows[0]['key'])['revision']==before[rows[0]['key']]['revision'])
 stale=[dict(records[0]),dict(records[1])];stale[1]['revision']='stale'
 check('Conflict in later row rejects entire preview',preview(records=stale).status_code==409)
 check('No prefix of conflict preview was committed',all(record(k)['revision']==v['revision'] for k,v in before.items()))
 check('Stale editor config rejected',preview(records=[{**records[0],'config_revision':'stale'}]).status_code==409)
 data=good(preview());items=[{'key':i['key'],'revision':i['revision'],'config_revision':i['config_revision'],'values':{'last_name':i['value']}} for i in data['items']]
 saved=good(op('POST','/table-changes',records=items,table_revision=data['table_revision']))
 check('Accepted fill saves through original EditMultipleCmd',saved['updated']==2 and saved['cells']==2 and 'EditMultipleCmd' in saved['transaction'])
 check('Both rows persist only after Save Changes',all(record(r['key'])['values']['last_name']=='Общее значение' for r in rows))
 check('Preview is not an authority to overwrite newer rows',op('POST','/table-changes',records=items,table_revision=data['table_revision']).status_code==409)
 check('All mutations and preview routed to writer',preview().headers.get('X-Tactic-Worker')=='1')
 check('Preview needs CSRF',s.post(root+'/table-fill-preview',json=args,headers={'X-Tactic-UI':'1'},timeout=15).status_code==403)
finally:
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'scenarios':result},ensure_ascii=False,indent=2)+'\n')
