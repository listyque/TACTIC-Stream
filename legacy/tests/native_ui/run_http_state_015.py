"""Original HTTP project lifecycle + DB view-state, never fixture persistence."""
import argparse,json,time,uuid
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
results=[];info={'passed':False,'scenarios':results,'storage':'original TACTIC + SQLite, real auth and commands'}
s=requests.Session();h={'X-Tactic-UI':'1','Origin':a.url};prefix='p015_'+uuid.uuid4().hex[:9]
base=a.url+'/api/ui/v2'
def check(name,ok=True,**extra):
 results.append({'scenario':name,'passed':bool(ok),**extra});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
def request(method,path,session=s,headers=h,**data):
 return session.request(method,base+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers,timeout=120)
def good(r):
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text[:2000])
 return r.json()
def state(scope,target='',project='admin'):
 return good(request('GET','/ui-state',project=project,scope=scope,target=target))
def store(scope,value,target='',project='admin',expected=None):
 old=state(scope,target,project)
 return request('PATCH','/ui-state',project=project,scope=scope,target=target,value=value,revision=old['revision'] if expected is None else expected)
target='admin_views/global_admin/users';wizard='admin_views/create_project'
try:
 h['X-CSRF-Token']=good(request('POST','/session',login='admin',password='Native-Test-Only-123'))['csrf']
 check('Original password login')
 options=good(request('GET','/project-create',project='admin',target=wizard))
 check('Wizard describes two supported original sources',{x['code'] for x in options['types']}=={'simple','default'})
 check('Unsupported template/icon/theme branches disclosed',bool(options['unsupported']))
 def payload(code=prefix,**extras):return dict(project='admin',target=wizard,code=code,title='Проект 015 / проверка',type='default',description='Исходная команда создания',**extras)
 for code in ['123project','../escape','sthpw','admin','a'*31,'русский']:
  check('Invalid/reserved project code rejected: '+code,request('POST','/project-preflight',**payload(code)).status_code==400)
 bad=payload();bad['type']='../../template';check('No arbitrary schema or template path',request('POST','/project-preflight',**bad).status_code==400)
 bad=payload();bad['target']=target;check('Create only from configured wizard',request('POST','/project-preflight',**bad).status_code==403)
 pre=good(request('POST','/project-preflight',**payload()));check('Preflight succeeds without creating project',pre['ready'] and prefix not in {x['code'] for x in good(request('GET','/projects'))['items']})
 bad=payload();bad['title']='changed';bad['revision']=pre['revision'];check('Changed review cannot silently create',request('POST','/project-create',**bad).status_code==409)
 made=good(request('POST','/project-create',**payload(),revision=pre['revision']));info['created_project']=prefix
 check('Original command creates new project and verifies schema',made['created'] and made['schema_checked'])
 check('Project URL is a server-derived project path',made['project_url']=='/tactic/'+prefix+'/')
 response=s.get(a.url+made['project_url'],headers={'Accept':'text/html'},timeout=60);check('New native project URL serves compiled UI',response.status_code==200 and '/tactic-ui/app.js' in response.text)
 check('New project enters project switcher',prefix in {x['code'] for x in good(request('GET','/projects'))['items']})
 sidebar=good(request('GET','/sidebar',project=prefix));check('Original sidebar available without restart',sidebar['project']==prefix and sidebar['source']=='config/widget_config + original XML')
 check('New project catalogue loads',isinstance(good(request('GET','/catalog',project=prefix))['types'],list))
 check('Repeated creation rejected rather than overwriting database',request('POST','/project-create',**payload()).status_code==409)
 simple=prefix+'s';created=good(request('POST','/project-create',project='admin',target=wizard,code=simple,title='Simple / 015',type='simple'))
 check('Original simple source also creates and passes schema check',created['created'] and created['schema_checked'])
 st=good(request('POST','/search-types',project=prefix,name='item',title='Объекты проекта',columns=[{'name':'quantity','type':'integer'}]))['search_type']
 check('SearchType created inside the NEW project',st==prefix+'/item')
 catalogue=good(request('GET','/search-types',project=prefix))['types'];item=next(x for x in catalogue if x['code']==st);view=item['target'];info['created_target']=view
 check('Original schema generates table target for new type',bool(view))
 opened=good(request('GET','/open',project=prefix,target=view));check('New type resolves widget_config table',opened['kind']=='table' and any(f['name']=='name' for f in opened['spec']['fields']))
 f=good(request('GET','/form',project=prefix,target=view));check('New project Insert/Edit form opens',f['spec']['capabilities']['create'])
 record=good(request('POST','/record',project=prefix,target=view,values={'name':'Тестовый объект','description':'создан после визарда'}))
 check('SObject persisted through original form command',bool(record['key']))
 rows=good(request('POST','/query',project=prefix,target=view,limit=50))['items'];check('Object visible in new-project query',any(x['key']==record['key'] for x in rows))
 # Real nested configuration, in the new project's ORIGINAL widget_config.
 import xml.etree.ElementTree as ET
 configs=good(request('GET','/configs',project=prefix,search_type='SideBarWdg'))['items']
 cfg=next(x for x in configs if x['view']=='project_view' and not x['login'])
 original_cfg=good(request('GET','/config',project=prefix,key=cfg['key']))
 root=ET.fromstring(original_cfg['xml']);link=ET.SubElement(root.find('project_view'),'element',name='state_tabs015',title='Persisted nested tables')
 disp=ET.SubElement(link,'display',{'class':'tactic.ui.container.TabWdg'})
 ET.SubElement(disp,'show_remove_tabs').text='first'
 nested=ET.Element('config');tab=ET.SubElement(nested,'tab')
 for name in ('first','second','hidden'):
  el=ET.SubElement(tab,'element',name=name,title=name)
  if name=='hidden':el.set('display','false')
  display=ET.SubElement(el,'display',{'class':'tactic.ui.panel.TableLayoutWdg'})
  ET.SubElement(display,'search_type').text=st;ET.SubElement(display,'view').text='table'
 ET.SubElement(disp,'config_xml').text=ET.tostring(nested,encoding='unicode')
 good(request('PATCH','/config',project=prefix,key=cfg['key'],revision=original_cfg['revision'],xml=ET.tostring(root,encoding='unicode')))
 tabs='project_view/state_tabs015';opened_tabs=good(request('GET','/open',project=prefix,target=tabs))
 check('Nested source configuration exposes real child names',[x['name'] for x in opened_tabs['children']]==['first','second'])
 tab_value={'order':['second','first'],'closed':['second'],'selected':'first','titles':{'first':'Своё имя'}}
 check('Nested tab state stored in original database',good(store('tabs',tab_value,tabs,project=prefix))['storage']=='sthpw/wdg_settings')
 check('Nested order titles closed state roundtrip',state('tabs',tabs,project=prefix)['value']==tab_value)
 check('Configured protected tab cannot be closed',store('tabs',dict(tab_value,closed=['first']),tabs,project=prefix).status_code in (400,403))
 check('Hidden source child cannot be injected in state',store('tabs',dict(tab_value,order=['hidden']),tabs,project=prefix).status_code==400)
 nt=opened_tabs['children'][0]['id'];ng=good(store('geometry',{'widths':{'name':340}},nt,project=prefix))
 check('Nested table has independent original-DB geometry',state('geometry',nt,project=prefix)['value']['widths']['name']==340)
 timeline_target='admin_views/global_admin/users'
 tspec=good(request('GET','/open',project='admin',target=timeline_target))['spec']
 dates=[f['name'] for f in tspec['fields'] if f.get('storage') and f['kind'] in ('date','datetime') and not f.get('hidden')]
 timeline={'mode':'calendar','start':'2026-10-01','end':'2026-11-11','month':'2026-10','zoom':34,'startField':dates[0] if dates else '', 'endField':'','includeUndated':True}
 good(store('timeline',timeline,timeline_target));check('Calendar range zoom and fields persist without result rows',state('timeline',timeline_target)['value']==timeline)
 # Original widget_config projection remains unchanged when preferences change.
 original=good(request('GET','/open',project='admin',target=target))['spec']['revision']
 geometry={'widths':{'login':280},'order':['login','first_name','last_name'],'hidden':['email'],'pinned':['login'],'density':'compact','wrap':True,'groupField':'','mode':'table'}
 g=good(store('geometry',geometry,target));check('Geometry written in original wdg_settings',g['storage']=='sthpw/wdg_settings')
 check('Geometry read back from server',state('geometry',target)['value']==geometry)
 check('Preferences do not rewrite widget_config',good(request('GET','/open',project='admin',target=target))['spec']['revision']==original)
 old=state('geometry',target);changed=dict(geometry,wrap=False);good(store('geometry',changed,target));check('Concurrent revision conflict is explicit',store('geometry',geometry,target,expected=old['revision']).status_code==409)
 check('Conflict keeps saved server value',state('geometry',target)['value']['wrap'] is False)
 bad=dict(geometry,widths={'secret_password':100});check('Unknown/hidden-secret field rejected',store('geometry',bad,target).status_code==400)
 bad=dict(geometry,rows=[record]);check('SObjects/drafts are not a settings payload',store('geometry',bad,target).status_code==400)
 q={'filters':[{'field':'login','op':'contains','value':'grid'}],'where':{'op':'or','children':[{'field':'first_name','op':'contains','value':'Анна'},{'field':'last_name','op':'not_null','value':None}]},'sort':{'field':'login','direction':'asc'},'record_state':'all','offset':0,'limit':37,'presentation':'data','search_open':True,'quickField':'login','quickText':'grid','quickOp':'contains'}
 good(store('query',q,target));restored=state('query',target)['value'];check('Advanced AND/OR, quick filters, sorting and paging persisted',restored==q)
 check('Restored query executes against actual Search',isinstance(good(request('POST','/query',project='admin',target=target,**{k:v for k,v in restored.items() if k in ('filters','where','sort','record_state','offset','limit')}))['items'],list))
 check('Arbitrary expression not accepted as stored search',store('query',dict(q,expression='@PYTHON(1)'),target).status_code==400)
 check('Workspace ids and active tab saved',good(store('workspace',{'ids':[target,wizard],'active':target}))['saved'])
 good(store('appearance',{'theme':'dark'}));check('Theme also stored server-side',state('appearance')['value']=={'theme':'dark'})
 check('Another project has independent workspace',state('workspace',project=prefix)['value'] is None)
 good(store('workspace',{'ids':[view],'active':view},project=prefix));check('Project-specific state does not replace admin workspace',state('workspace')['value']['active']==target)
 denied=request('PATCH','/ui-state',project='admin',scope='workspace',login='other',revision=state('workspace')['revision'],value={'ids':[],'active':''});check('User identity cannot be overridden in state writes',denied.status_code==400)
 check('Unsupported scope cannot access arbitrary settings',request('GET','/ui-state',project='admin',scope='password').status_code==400)
 check('Unknown target cannot store geometry',request('GET','/ui-state',project='admin',scope='geometry',target='not_configured').status_code==403)
 old_cookie=s.cookies.get_dict();good(request('DELETE','/session'));h.pop('X-CSRF-Token',None)
 check('State access requires an authenticated original session',request('GET','/ui-state',project='admin',scope='workspace').status_code==401)
 s=requests.Session();s.headers.update({'X-Tactic-UI':'1','Origin':a.url})
 # request default captured old session intentionally bypass with explicit session.
 login=good(request('POST','/session',session=s,login='admin',password='Native-Test-Only-123'));h['X-CSRF-Token']=login['csrf']
 again=good(request('GET','/ui-state',session=s,project='admin',scope='workspace'))
 check('DB state survives logout/new session, no browser storage',again['value']['active']==target and s.cookies.get_dict()!=old_cookie)
 info['passed']=True
except Exception as exc:
 info['error']=str(exc)
 import traceback;traceback.print_exc()
finally:
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
if not info['passed']:raise SystemExit(1)
