"""1.0 widget/menu HTTP contracts; synthetic fixture storage, actual services."""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True);a=p.parse_args()
s=requests.Session();headers={'X-Tactic-UI':'1'};results=[]
root='fixture_widgets/widgets';base={'project':'fixture','target':root}
def req(method,path,**data):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers,timeout=20)
def op(method,path,**data):return req(method,path,**dict(base,**data))
def check(name,ok):
 assert ok,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
try:
 check('Menus require authenticated session',op('GET','/context-menu',scope='widget').status_code==401)
 login=req('POST','/session',login='fixture',password='fixture-only');headers['X-CSRF-Token']=login.json()['csrf']
 data=op('GET','/open').json();check('TabWdg uses nested container kind',data['kind']=='tabs')
 check('Visible child indices preserve hidden position',[x['tab_index'] for x in data['children']]==[0,2,3])
 check('Selected child is original configured name',data['container']['selected']==root+'/~tab/0')
 check('Load and show_remove_tabs are preserved',data['children'][1]['preload'] and not data['children'][0]['removable'])
 check('Save-state limitation explicitly returned','save_state' in data['container']['state_notice'])
 check('Hidden child cannot be opened by URL',op('GET','/open',target=root+'/~tab/1').status_code==403)
 check('Hidden child cannot request a menu',op('GET','/context-menu',target=root+'/~tab/1',scope='widget').status_code==403)
 check('Unrecognized child suffix not authorized',op('GET','/open',target=root+'/~tab/02').status_code==403)
 check('Excessive recursive widget depth rejected',op('GET','/open',target=root+'/~tab/0'*9).status_code==400)
 nested=op('GET','/open',target=root+'/~tab/3').json();check('TabWdg can contain TabWdg',nested['kind']=='tabs' and len(nested['children'])==2)
 check('Nonremovable children retain source setting',all(not t['removable'] for t in nested['children']))
 check('Custom widget remains explicit unported',op('GET','/open',target=root+'/~tab/3/~tab/1').json()['kind']=='unsupported')
 form=op('GET','/embedded-form',target=root+'/~tab/0').json();key=form['record']['key']
 check('Embedded form bound to configured object',key=='sthpw/task?code=FIXTURE0')
 check('Embedded fields use configured order',[f['name'] for f in form['spec']['fields']]==['description','status','bid_start_date'])
 check('Embedded form not table query',op('POST','/query',target=root+'/~tab/0',key=key).status_code==400)
 check('Metadata route remains available',op('GET','/view',target=root+'/~tab/0').status_code==200)
 check('Changing bound form key forbidden',op('PATCH','/embedded-form',target=root+'/~tab/0',key='sthpw/task?code=FIXTURE1',revision=form['record']['revision'],values={'description':'wrong'}).status_code==403)
 check('Generic record route cannot bypass binding',op('PATCH','/record',target=root+'/~tab/0',key='sthpw/task?code=FIXTURE1',revision=form['record']['revision'],values={'description':'wrong'}).status_code==403)
 r=op('PATCH','/embedded-form',target=root+'/~tab/0',key=key,revision=form['record']['revision'],values={'description':'1.0 widget save'});check('Bound form saves through validated command boundary',r.status_code==200 and r.json()['values']['description']=='1.0 widget save')
 check('Stale embedded form rejected',op('PATCH','/embedded-form',target=root+'/~tab/0',key=key,revision=form['record']['revision'],values={'description':'stale'}).status_code==409)
 read=op('GET','/embedded-form',target='fixture_widgets/readonly').json();check('View mode has no writable fields',all(f['read_only'] for f in read['spec']['fields']))
 check('View mode refuses save despite endpoint call',op('PATCH','/embedded-form',target='fixture_widgets/readonly',key=key,revision=read['record']['revision'],values={'description':'wrong'}).status_code==403)
 check('Hidden form header flag preserved',read['widget']['show_header'] is False)
 insert=op('GET','/embedded-form',target='fixture_widgets/insert_form').json();check('Insert defaults come from XML options',insert['defaults']['description']=='Default из конфигурации' and insert['widget']['single'])
 r=op('POST','/embedded-form',target='fixture_widgets/insert_form',values={});check('Defaults enter normal field validation on create',r.status_code==200 and r.json()['values']['description']=='Default из конфигурации')
 table=root+'/~tab/2';query=op('POST','/query',target=table).json();check('Nested table respects configured page size',len(query['items'])==5)
 row=query['items'][0]
 menu=op('GET','/context-menu',target=table,scope='row',key=row['key']).json();ids=[m.get('id') for m in menu['items']]
 check('Row menu includes actions from original scope',{'edit','files','history','subscription','state'}.issubset(ids))
 check('Cascade deletion not substituted by retire',next(m for m in menu['items'] if m.get('id')=='delete')['enabled'] is False)
 cols=op('GET','/context-menu',target=table,scope='column',field='description').json();check('Header provides explicit two-way sorting',{'sort_asc','sort_desc'}.issubset({m.get('id') for m in cols['items']}))
 check('Unsupported field cannot be requested through menu',op('GET','/context-menu',target=table,scope='column',field='password').status_code==403)
 check('Menu cannot accept arbitrary action scope',op('GET','/context-menu',target=table,scope='execute_python').status_code==400)
 check('Menus are read-only endpoint',op('POST','/context-menu',scope='widget').status_code==405)
 check('POST embedded requires correct operation',op('DELETE','/embedded-form',target=root+'/~tab/0').status_code==405)
 m=op('GET','/context-menu',target=root+'/~tab/0',scope='form-field',field='description',key=key).json();check('Form label menu references original field',{'definition','reset_field','null_field'}.issubset({x.get('id') for x in m['items']}))
 m=op('GET','/context-menu',target=root+'/~tab/0',scope='tab').json();check('Protected tab has no Close action','close' not in [x.get('id') for x in m['items']])
 check('Derived child not accepted as sidebar link',op('GET','/context-menu',target=root+'/~tab/0',scope='sidebar').status_code==403)
 m=op('GET','/context-menu',scope='sidebar').json();check('Sidebar provides original open/popup/config scopes',{'open','popup','sidebar_config'}.issubset({x.get('id') for x in m['items']}))
 check('No callback source returned for execution',not any(t in json.dumps(m) for t in ('cbjs_action','eval(')))
 check('Private menu responses not cached',op('GET','/context-menu',scope='widget').headers['Cache-Control']=='no-store')
except Exception as e:results.append({'scenario':'failure','passed':False,'error':str(e)});raise
finally:
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'scope':'TEST storage/auth; production widget projection/menu/form service and HTTP dispatch','scenarios':results},ensure_ascii=False,indent=2)+'\n')
