"""Integration against real_server_11: ORIGINAL models, real DB auth and SQLite.
Never run against user data: companion server requires .native-real-test.
"""
import argparse,json,uuid
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True);a=p.parse_args()
s=requests.Session();base=a.url+'/api/ui/v2';headers={'X-Tactic-UI':'1'};results=[];nonce=uuid.uuid4().hex[:8];project='admin';keys={}
def req(method,path,**data):return s.request(method,base+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers,timeout=60)
def op(method,path,target=None,**data):return req(method,path,**dict({'project':project},**({'target':target} if target else {}),**data))
def check(name,ok):
 if not ok:raise AssertionError(name)
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def good(r,status=200):
 if r.status_code!=status:raise AssertionError(str(r.status_code)+' '+r.text[:1300])
 return r.json()
def target(name):return 'admin_views/global_admin/'+name
try:
 check('Anonymous Globals are unauthorized',op('GET','/open',target('users')).status_code==401)
 r=good(req('POST','/session',login='admin',password='Native-Test-Only-123'));headers['X-CSRF-Token']=r['csrf'];check('Original DB password authentication returns real admin session',r['user']['login']=='admin' and r['user']['mode']=='tactic')
 tree=good(op('GET','/sidebar'))
 globals_node=next(c for sec in tree['sections'] for c in sec['children'] if c.get('name')=='global_admin')
 links=[i for i in globals_node['children'] if i.get('kind')=='link'];check('Original Globals contains 13 configured links',len(links)==13)
 for node in links:
  opened=good(op('GET','/open',node['id']));check('Globals opens: '+node['name'],opened['kind']!='unsupported')
  if opened['kind']=='table':
   d=good(op('POST','/query',node['id']));check('Original Search works: '+node['name'],'items' in d and 'total' in d)
  else:
   path={'system':'/system','system-config':'/system-config','license':'/license','group-membership':'/memberships'}[opened['kind']]
   d=good(op('GET',path,node['id']));check('Special widget reads original source: '+node['name'],isinstance(d,dict))
 for name,values,edit in (
  ('users',{'login':'n11_'+nonce,'password':'Private-Test-Pass-1','password re-enter':'Private-Test-Pass-1','first_name':'Before','email':'one@example.invalid'},{'first_name':'After'}),
  ('groups',{'name':'group_'+nonce,'description':'Before','add_to_project':True},{'description':'After'}),
  ('db_resource',{'code':'db_'+nonce,'host':'127.0.0.1','port':'5432','vendor':'PostgreSQL','login':'test','password':'Private-Test-DB-2'},{'login':'changed'}),
  ('global_translations',{'name':'native_'+nonce,'en':'Before','fr':'Avant'},{'en':'After'})):
  t=target(name);f=good(op('GET','/form',t));check('Insert form is enabled: '+name,f['spec']['capabilities']['create'])
  d=good(op('POST','/record',t,values=values),201);keys[name]=d['key'];check('Original NativeEditCmd creates: '+name,bool(d['key']))
  check('Secret values not echoed: '+name,'Private-Test' not in json.dumps(d))
  f=good(op('GET','/form',t,key=d['key']));check('Existing original form is editable: '+name,f['spec']['capabilities']['update'])
  r=op('PATCH','/record',t,key=d['key'],revision=f['record']['revision'],values=edit);good(r)
  f2=good(op('GET','/form',t,key=d['key']));check('Reopened original data has edits: '+name,all(f2['record']['values'].get(k)==v for k,v in edit.items()))
  check('Stale edit rejected: '+name,op('PATCH','/record',t,key=d['key'],revision=f['record']['revision'],values=edit).status_code==409)
 check('Duplicate login rejected without overwrite',op('POST','/record',target('users'),values={'login':'n11_'+nonce,'password':'x'}).status_code==409)
 group=keys['groups'];m=good(op('GET','/memberships',target('users_in_groups'),key=group))
 good(op('POST','/memberships',target('users_in_groups'),key=group,revision=m['revision'],members=['n11_'+nonce]));m=good(op('GET','/memberships',target('users_in_groups'),key=group));check('Original UserAssignCbk persists membership',m['members']==['n11_'+nonce])
 rows=good(op('POST','/query',target('groups')))['items'];row=next(i for i in rows if i['key']==group)
 check('DropElementWdg displays original group members','n11_'+nonce in row['cells']['users']['text'])
 member_target=row['cells']['users']['target'];good(op('GET','/open',member_target));check('Group-specific subwidget binds same group',good(op('GET','/memberships',member_target,key=group))['members']==['n11_'+nonce])
 check('Subwidget rejects substituted group',op('GET','/memberships',member_target,key='sthpw/login_group?code=another').status_code==403)
 security_target=row['cells']['global_rules']['target'];good(op('GET','/open',security_target));security=good(op('GET','/security',security_target,key=group));check('SecurityManagerButton opens original rules','<rules' in security['xml'])
 good(op('PATCH','/security',security_target,key=group,revision=security['revision'],xml='<rules custom="preserved"><rule group="project" code="admin" access="allow"/></rules>'));check('Original group rules reopen after save','custom="preserved"' in good(op('GET','/security',security_target,key=group))['xml'])
 check('Bound group cannot create another',op('POST','/security',security_target,name='evil').status_code==403)
 hidden=row['cells']['access_rules_hidden']['target'];hd=good(op('GET','/open',hidden));data=good(op('POST','/query',hidden));check('HiddenRow opens configured child table restricted to clicked row',hd['kind']=='table' and len(data['items'])==1 and data['items'][0]['key']==group)
 dbrow=next(i for i in good(op('POST','/query',target('db_resource')))['items'] if i['key']==keys['db_resource'])
 add=dbrow['cells']['add_project']['target'];form=good(op('GET','/embedded-form',add));check('Original resource-project form resolves query options',any(f['name']=='db_resource' and any(o['value']=='db_'+nonce for o in f['options']) for f in form['spec']['fields']))
 resource=good(op('POST','/embedded-form',add,values={'code':'res_'+nonce,'title':'Reference to an existing DB','db_resource':'db_'+nonce,'database':'unittest'}))
 check('Original resource-project EditWdg creates its reference record',resource['values']['db_resource']=='db_'+nonce and resource['values']['database']=='unittest')
 related=good(op('POST','/query',dbrow['cells']['projects']['target']))
 check('Resource HiddenRow restricts records to original Schema relation',any(x['key']==resource['key'] for x in related['items']) and all(x['values'].get('db_resource')=='db_'+nonce for x in related['items']))
 cfg=good(op('GET','/system-config',target('system_config')));check('System Config follows original seven groups',len(cfg['groups'])==7)
 check('System Config rejects unknown arbitrary keys',op('PATCH','/system-config',target('system_config'),revision=cfg['revision'],changes={'exec/code':'x'},confirm='SAVE_SYSTEM_CONFIG').status_code==400)
 cfg=good(op('GET','/system-config',target('system_config')))
 new_count=str(int(next(f['value'] or 8 for g in cfg['groups'] for f in g['fields'] if f['name']=='services/thread_count'))+1)
 saved=good(op('PATCH','/system-config',target('system_config'),revision=cfg['revision'],changes={'services/thread_count':new_count,'services/mail_password':'Private-Test-Secret-3'},confirm='SAVE_SYSTEM_CONFIG'))
 check('System config writes with backup and restart notice',saved['backup_created'] and saved['restart_required'])
 cfg2=good(op('GET','/system-config',target('system_config')));check('Saved system value rereads while secret stays masked','Private-Test-Secret-3' not in json.dumps(cfg2) and any(f['value']==new_count for g in cfg2['groups'] for f in g['fields'] if f['name']=='services/thread_count'))
 check('Stale system file revision refused',op('PATCH','/system-config',target('system_config'),revision=cfg['revision'],changes={'services/thread_count':'10'},confirm='SAVE_SYSTEM_CONFIG').status_code==409)
 lic=good(op('GET','/license',target('license')));check('License exposes original metadata, not key material','company' in lic['info'] and 'public_key' not in json.dumps(lic))
 check('Legacy pickle licence not accepted by new endpoint',op('POST','/license',target('license'),xml='<license><data><version>1</version></data></license>',revision=lic['revision'],confirm='RENEW_LICENSE').status_code==501)
 check('System config cannot be requested through an unrelated target',op('GET','/system-config',target('users')).status_code==403)
 project='native11test';g='admin_views/project_admin/project_workflow';st='admin_views/project_admin/project_schema'
 sc=good(op('GET','/graph',st,kind='schema'));check('Source schema available without a saved DB row',bool(sc['initial_key']))
 schema=good(op('GET','/graph',st,kind='schema',key=sc['initial_key']));check('Project schema supports editing original record',schema['can_edit'])
 # Add a real registered SearchType; no table is created by schema editor.
 existing={n['name'] for n in schema['graph']['nodes']};node=next((t['code'] for t in sc['search_types'] if t['code'] not in existing),None)
 if node:
  saved=good(op('PATCH','/graph',st,kind='schema',key=schema['key'],revision=schema['revision'],operations=[{'op':'add_node','name':node,'attributes':{'xpos':100,'ypos':100}}]));loaded=good(op('GET','/graph',st,kind='schema',key=saved['key']));check('Schema saves and rereads actual XML',node in {n['name'] for n in loaded['graph']['nodes']})
 created=good(op('POST','/graph',g,kind='pipeline',code='pipe_'+nonce,name='Original command '+nonce));keys['pipeline']=created['key']
 pp=good(op('GET','/graph',g,kind='pipeline',key=created['key']))
 good(op('PATCH','/graph',g,kind='pipeline',key=pp['key'],revision=pp['revision'],operations=[{'op':'add_node','name':'design','attributes':{'type':'manual'}},{'op':'add_node','name':'approval','attributes':{'type':'approval'}},{'op':'add_edge','from':'design','to':'approval','attributes':{}}]))
 pp=good(op('GET','/graph',g,kind='pipeline',key=created['key']));check('PipelineSaveCbk creates real process rows and XML',len(pp['graph']['nodes'])==2 and len(pp['graph']['edges'])==1 and set(pp['settings'])=={'design','approval'})
 project='admin';opened=good(op('GET','/graph',g,kind='pipeline',key=created['key']));check('Admin reads process settings from owning project',opened['owner_project']=='native11test' and set(opened['settings'])=={'design','approval'})
 good(op('PATCH','/graph',g,kind='pipeline',key=opened['key'],revision=opened['revision'],operations=[{'op':'update_node','name':'design','attributes':{'xpos':460,'ypos':240}}]));pp=good(op('GET','/graph',g,kind='pipeline',key=created['key']));check('Admin save keeps owning project command context',next(n for n in pp['graph']['nodes'] if n['name']=='design')['x']==460)
 check('Graph kind cannot substitute the configured widget',op('GET','/graph',target('users'),kind='schema').status_code==403)
 baseline=good(op('GET','/graph',st,kind='schema'));sc=good(op('GET','/graph',st,kind='schema',key=baseline['initial_key']));check('Builtin admin schema renders original nonempty source and stays read-only',len(sc['graph']['nodes'])>20 and not sc['can_edit'])
 check('CSRF still enforced for original data writes',s.post(base+'/record',json={'project':'admin','target':target('users'),'values':{}},headers={'X-Tactic-UI':'1'},timeout=20).status_code==403)
 good(req('DELETE','/session'));check('Logout invalidates original data access',op('GET','/open',target('users')).status_code==401)
except Exception as e:results.append({'scenario':'failure','passed':False,'error':str(e)});raise
finally:
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'scope':'Original startup/DB authentication/Search/NativeEditCmd/Command/SQLite; only licence signature isolated in explicit test server','scenarios':results,'created_test_keys':keys},ensure_ascii=False,indent=2)+'\n')
