"""Table CellEdit and original EditMultipleCmd over ORIGINAL TACTIC/SQLite.
Requires the disposable installation prepared by run_original_012.py.
"""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True);a=p.parse_args()
s=requests.Session();base=a.url+'/api/ui/v2';headers={'X-Tactic-UI':'1'};results=[];target='admin_views/global_admin/users'
def request(method,path,**data):return s.request(method,base+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers,timeout=60)
def op(method,path,**data):return request(method,path,project='admin',target=target,**data)
def good(r):
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text)
 return r.json()
def check(name,ok):
 if not ok:raise AssertionError(name)
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def getrow(key):return good(op('GET','/record',key=key))
def events():
 return good(request('POST','/query',project='admin',target='admin_views/global_admin/debug_log',limit=100))['items']
def editor(key,name,pending=None):return good(op('POST','/cell-editor',key=key,field=name,pending=pending or {}))
def entry(key,values):
 e=editor(key,next(iter(values)),values)
 return {'key':key,'revision':e['revision'],'config_revision':e['config_revision'],'values':values}
def save(records,table_revision=None):
 spec=good(op('GET','/open'))['spec']
 return op('POST','/table-changes',table_revision=table_revision or spec['revision'],records=records)
try:
 check('Anonymous cell editor denied',op('GET','/cell-editor',key='x',field='first_name').status_code==401)
 auth=good(request('POST','/session',login='admin',password='Native-Test-Only-123'));headers['X-CSRF-Token']=auth['csrf']
 check('Original DB authentication',auth['user']['mode']=='tactic')
 rows=good(op('POST','/query',limit=100))['items'];anna=next(r for r in rows if r['values'].get('login')=='grid_anna');alex=next(r for r in rows if r['values'].get('login')=='grid_alex')
 ak,bk=anna['key'],alex['key'];before=getrow(ak)
 check('Ordinary preview resolved from original ThumbWdg',anna['cells']['preview']['kind']=='thumbnail' and anna['cells']['preview']['state']=='ready')
 preview=s.get(a.url+anna['cells']['preview']['image'],timeout=30)
 check('Preview served as authenticated registered PNG',preview.status_code==200 and preview.content.startswith(b'\x89PNG') and preview.headers['Content-Type'].startswith('image/png'))
 check('Other row without snapshot has original empty preview state',alex['cells']['preview']['state']=='empty')
 check('Preview cannot be read without session',requests.get(a.url+anna['cells']['preview']['image'],timeout=30).status_code==401)

 e=editor(ak,'first_name')
 check('CellEdit uses DB edit_item TextArea override',e['field']['kind']=='textarea' and e['field']['handler']=='TextAreaWdg')
 form=good(op('GET','/form',key=ak));check('CellEdit differs from original popup edit form',next(f for f in form['spec']['fields'] if f['name']=='first_name')['handler']!='TextAreaWdg')
 check('Opening editor never changes record',getrow(ak)['revision']==before['revision'])
 e2=editor(ak,'last_name',{'first_name':'Новый черновик'})
 check('Definition revision stable across single vs multiple changed fields',e['config_revision']==e2['config_revision'])
 check('Draft request does not write either field',getrow(ak)['values']['first_name']==before['values']['first_name'])
 one=entry(ak,{'first_name':'Анна сохранена','last_name':'Новая фамилия'});two=entry(bk,{'first_name':'Алексей сохранён'})
 before_events=len(events())
 r=good(save([one,two]));check('One Save Changes invokes original EditMultipleCmd',r['updated']==2 and r['cells']==3 and 'EditMultipleCmd' in r['transaction'] and r['save_view']=='edit_item')
 check('Original update_multi fires once for the batch',len(events())==before_events+1)
 check('First original row has both edits',getrow(ak)['values']['first_name']=='Анна сохранена' and getrow(ak)['values']['last_name']=='Новая фамилия')
 check('Second original row committed in batch',getrow(bk)['values']['first_name']=='Алексей сохранён')
 check('Replaying stale batch cannot silently repeat side effects',save([one,two]).status_code==409)
 before1,before2=getrow(ak),getrow(bk)
 one=entry(ak,{'first_name':'This must roll back'});two=entry(bk,{'first_name':''})
 before_events=len(events())
 bad=save([one,two]);check('Original NonEmptyAction rejects second row',bad.status_code>=400)
 check('First row rollback after second action error',getrow(ak)['revision']==before1['revision'])
 check('Failed batch leaves no update_multi record',len(events())==before_events)
 check('Second row unchanged after failed batch',getrow(bk)['revision']==before2['revision'])
 one=entry(ak,{'first_name':'Preflight must not write'});two=entry(bk,{'first_name':'Other'});two['revision']='stale'
 check('Conflict anywhere aborts full batch',save([one,two]).status_code==409)
 check('Preflight conflict preserved first row',getrow(ak)['revision']==before1['revision'])
 one=entry(ak,{'last_name':'Another'});one['config_revision']='stale'
 check('Stale cell config rejected',save([one]).status_code==409)
 one=entry(ak,{'last_name':'Another'})
 check('Stale table config rejected',save([one],table_revision='stale').status_code==409)
 check('Duplicate row keys rejected',save([one,one]).status_code==400)
 check('Empty batch rejected',save([]).status_code==400)
 check('More than 100 rows rejected',save([one]*101).status_code==400)
 check('Unknown field cannot be injected into cell editor',op('POST','/cell-editor',key=ak,field='unconfigured',pending={}).status_code==403)
 check('Sensitive secret field cannot be requested',op('POST','/cell-editor',key=ak,field='password',pending={}).status_code==403)
 check('Pending foreign field cannot be smuggled',op('POST','/cell-editor',key=ak,field='first_name',pending={'ticket':'x'}).status_code==403)
 check('Protected identity field cannot be edited',op('POST','/cell-editor',key=ak,field='code',pending={}).status_code==403)
 check('Row type cannot be substituted',op('POST','/cell-editor',key='sthpw/project?code=admin',field='first_name',pending={}).status_code>=400)
 check('Original action type surfaced in descriptor',e['field']['action']=='NonEmptyAction')
 one=entry(ak,{'last_name':None});good(save([one]));check('Explicit NULL preserved through original action adapter',getrow(ak)['values']['last_name'] is None)
 one=entry(ak,{'last_name':'Готово'});good(save([one]));check('Subsequent batch still works after rollback and conflicts',getrow(ak)['values']['last_name']=='Готово')
 payload={'project':'admin','target':target,'records':[one],'table_revision':'x'}
 check('CSRF required for table saving',s.post(base+'/table-changes',json=payload,headers={'X-Tactic-UI':'1'},timeout=20).status_code==403)
 good(request('DELETE','/session'));check('Logout invalidates cell editing',op('GET','/cell-editor',key=ak,field='first_name').status_code==401)
except Exception as e:results.append({'scenario':'failure','passed':False,'error':str(e)});raise
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'backend':'Original TACTIC + SQLite, original auth/actions/transaction; explicit test signature isolation','scenarios':results},ensure_ascii=False,indent=2)+'\n')
