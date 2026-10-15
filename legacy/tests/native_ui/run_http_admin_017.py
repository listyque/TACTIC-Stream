"""Original TACTIC HTTP/SQLite administrative edits. Companion runner owns disposable seed."""
import argparse,json,uuid,xml.etree.ElementTree as ET
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
report={'passed':False,'backend':'original TACTIC / SQLite / original commands','scenarios':[]};s=requests.Session();h={'X-Tactic-UI':'1','Origin':a.url};nonce='n17_'+uuid.uuid4().hex[:8]
pj='native11test';SEC='admin_views/project_admin/manage_security';USERS='admin_views/project_admin/manage_users';ST='admin_views/project_admin/manage_search_types';GROUP='admin_views/global_admin/groups';USER='admin_views/global_admin/users'
def req(method,path,**data):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=h,timeout=90)
def op(method,path,**data):return req(method,path,project=pj,**data)
def good(r):
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text[:2000])
 return r.json()
def check(name,v=True):
 report['scenarios'].append({'scenario':name,'passed':bool(v)});print(('PASS ' if v else 'FAIL ')+name,flush=True)
 if not v:raise AssertionError(name)
def matrix(cat):return good(op('GET','/security-matrix',target=SEC,category=cat,groups=json.dumps([gkey])))
def change(cat,row=None,val=True):
 d=matrix(cat);row=row or next(x for x in d['rows'] if x['value']=='*');r=op('PATCH','/security-matrix',target=SEC,category=cat,groups=[gkey],revision=d['revision'],changes=[{'row':row['id'],'group':gkey,'value':val}]);return d,row,r
try:
 check('Anonymous security requests denied',op('GET','/security-matrix',target=SEC).status_code==401)
 h['X-CSRF-Token']=good(req('POST','/session',login='admin',password='Native-Test-Only-123'))['csrf']
 for name,kind in [('manage_users','users'),('manage_security','security'),('manage_search_types','search-types'),('manage_side_bar','sidebar-editor')]:
  r=good(op('GET','/open',target='admin_views/project_admin/'+name));check('Original configured '+name+' resolves dedicated '+kind,r['kind']==kind)
 for part in ('users-table','assignment','security'):
  r=good(op('GET','/open',target=USERS+'/~admin/'+part));check('UserConfig original child '+part,r['kind'] in ('table','group-assignment','security'))
 check('Derived admin child cannot be requested from unrelated table',op('GET','/open',target=USER+'/~admin/assignment').status_code==403)
 r=good(op('POST','/record',target=USERS+'/~admin/users-table',values={'login':nonce,'password':'Native17-Only-123','password re-enter':'Native17-Only-123','first_name':'Новый','last_name':'Пользователь'}));ukey=r['key'];report['user_key']=ukey
 check('Original UserPanel form creates login via original handlers',bool(ukey))
 rows=good(op('POST','/query',target=USERS+'/~admin/users-table',limit=200))['items'];check('UserPanel original filter omits admin and guest',all(x['values']['login'] not in ('admin','guest') for x in rows));check('Created account is in UserPanel',any(x['key']==ukey for x in rows))
 r=good(op('POST','/record',target=GROUP,values={'name':nonce,'description':'Native matrix group','add_to_project':True}));gkey=r['key'];report['group_key']=gkey
 f=good(op('GET','/form',target=GROUP,key=gkey));current=good(op('GET','/record',target=GROUP,key=gkey));
 r=good(op('PATCH','/record',target=GROUP,key=gkey,revision=current['revision'],values={'access_level':'none'}));check('Original group edit sets access_level none',bool(r['key']))
 # Original source command may prefix project/group; use source model's actual name.
 membership=good(op('GET','/user-groups',target=USERS,key=ukey));gname=good(op('GET','/record',target=GROUP,key=gkey))['values']['login_group'];report['group_name']=gname
 r=good(op('PATCH','/user-groups',target=USERS,key=ukey,revision=membership['revision'],members=[gname]));check('GroupAssignCbk executed for user membership',r['command']=='GroupAssignCbk')
 after=good(op('GET','/user-groups',target=USERS,key=ukey));check('Membership roundtrip through original login_in_group',after['members']==[gname])
 check('Stale membership revision conflicts',op('PATCH','/user-groups',target=USERS,key=ukey,revision=membership['revision'],members=[]).status_code==409)
 check('Unknown group cannot be injected',op('PATCH','/user-groups',target=USERS,key=ukey,revision=after['revision'],members=['missing_group']).status_code==400)
 assignment=USERS+'/~admin/assignment';d=good(op('GET','/security-matrix',target=assignment,groups=json.dumps([gkey])));row=next(x for x in d['rows'] if x['value']==nonce)
 check('Original UserSecurity matrix recognizes membership',row['cells'][gkey]['checked'])
 good(op('PATCH','/security-matrix',target=assignment,groups=[gkey],revision=d['revision'],changes=[{'row':row['id'],'group':gkey,'value':False}]))
 check('UserSecurityCbk toggle removed only intended membership',good(op('GET','/user-groups',target=USERS,key=ukey))['members']==[])
 # UserSecurity's original callback toggles, so unchanged desired value MUST never be passed through.
 d=good(op('GET','/security-matrix',target=assignment,groups=json.dumps([gkey])));r=good(op('PATCH','/security-matrix',target=assignment,groups=[gkey],revision=d['revision'],changes=[{'row':row['id'],'group':gkey,'value':False}]));check('Unchanged cell does not toggle original callback',r.get('unchanged'))
 # Typed metadata/physical-column editor.
 st=good(op('POST','/search-types',name=nonce,title='Объекты 017',columns=[{'name':'count','type':'integer'}]))['search_type'];report['search_type']=st
 d=good(op('GET','/stype-editor',target=ST,search_type=st));check('Created local SearchType is editable',d['can_write'])
 table=ST+'/~admin/stype-table:'+requests.utils.quote(st,safe='');report['table_target']=table
 opened=good(op('GET','/open',target=table));check('SearchType editor opens original configured table',opened['kind']=='table' and opened['search_type']==st)
 obj=good(op('POST','/record',target=table,values={'name':'Существующий объект','count':7}));report['object_key']=obj['key']
 good(op('PATCH','/stype-editor',target=ST,search_type=st,revision=d['revision'],values={'title':'Новая подпись','description':'Исходный реестр','color':'#5588aa'}))
 check('Metadata revision conflict detected',op('PATCH','/stype-editor',target=ST,search_type=st,revision=d['revision'],values={'title':'stale'}).status_code==409)
 d=good(op('GET','/stype-editor',target=ST,search_type=st));r=good(op('POST','/stype-editor',target=ST,search_type=st,revision=d['revision'],confirm='ADD_COLUMNS',columns=[{'name':'estimate','data_type':'float','format':'-1,234.12'}]));check('ColumnEditCbk creates physical column and original definitions',r['command']=='ColumnEditCbk')
 d=good(op('GET','/stype-editor',target=ST,search_type=st));c=next(c for c in d['columns'] if c['name']=='estimate');check('Physical column and FormatElementWdg definition roundtrip',c['definition']['handler']=='tactic.ui.table.FormatElementWdg' and c['definition']['options']['format']=='-1,234.12')
 check('Original edit definition created',c['edit_definition']['handler']=='TextWdg')
 check('Existing rows and keys preserved',good(op('GET','/record',target=table,key=obj['key']))['values']['name']=='Существующий объект')
 check('Existing column cannot be re-added',op('POST','/stype-editor',target=ST,search_type=st,revision=d['revision'],confirm='ADD_COLUMNS',columns=[{'name':'estimate','data_type':'integer'}]).status_code==400)
 check('No type-changing metadata operation',op('PATCH','/stype-editor',target=ST,search_type=st,revision=d['revision'],values={'table_name':'evil'}).status_code==400)
 # Sidebar: shared definition is not replaced by a browser-owned menu.
 d=good(op('GET','/sidebar-editor',view='project_view'));folder=nonce+'_folder';lname=nonce+'_link';report['folder_view']=folder;report['link_name']=lname
 ops=[{'op':'add','kind':'link','name':lname,'attributes':{'title':'Объекты 017','icon':'table'},'options':{'search_type':st,'view':'table'}},{'op':'add','kind':'folder','name':folder,'attributes':{'title':'Новая папка'},'options':{'view':folder}},{'op':'add','kind':'separator','name':'separator'}]
 good(op('PATCH','/sidebar-editor',view='project_view',revision=d['revision'],operations=ops));check('Sidebar patch creates original references and a child config',True)
 current=good(op('GET','/sidebar-editor',view='project_view'));check('Sidebar source resolves real table handler',any(e['name']==lname and e['renderer']=='table' for e in current['elements']))
 check('Sidebar stale revision conflicts',op('PATCH','/sidebar-editor',view='project_view',revision=d['revision'],operations=[{'op':'remove','index':0}]).status_code==409)
 report['sidebar_target']='project_view/'+lname
 r=good(op('GET','/open',target=report['sidebar_target']));check('New sidebar link opens actual SObject table',r['kind']=='table' and r['search_type']==st)
 child=good(op('GET','/sidebar-editor',view=folder));check('Created folder is an empty real widget_config view',child['elements']==[])
 good(op('PATCH','/sidebar-editor',view=folder,revision=child['revision'],operations=[{'op':'add','name':'inner','kind':'link','options':{'search_type':st,'view':'table'},'attributes':{'title':'Внутри папки'}}]));check('Nested new link resolves through original sidebar',good(op('GET','/open',target='project_view/'+folder+'/inner'))['search_type']==st)
 check('Foreign personal sidebar denied',op('GET','/sidebar-editor',view='my_view_someone_else').status_code==403)
 personal=good(op('GET','/sidebar-editor',view='my_view'));good(op('PATCH','/sidebar-editor',view='my_view',revision=personal['revision'],operations=[{'op':'add','name':lname,'options':{'search_type':st,'view':'table'},'attributes':{'title':'Личная ссылка'}}]));check('Personal widget_config saved separately',good(op('GET','/sidebar-editor',view='my_view'))['personal'])
 # Matrix saves through all six original callback classes. Keep non-target XML and literal comments.
 for cat in ('project','link','gear_menu','search_type','process','task'):
  d,row,response=change(cat);out=good(response);check('Original callback saves '+cat,out['command']=={'project':'ProjectSecurityCbk','link':'LinkSecurityCbk','gear_menu':'GearMenuSecurityCbk','search_type':'SearchTypeSecurityCbk','process':'ProcessSecurityCbk','task':'TaskSecurityCbk'}[cat])
  new=matrix(cat);check('Rule roundtrip '+cat,next(x for x in new['rows'] if x['id']==row['id'])['cells'][gkey]['explicit'])
  check('Stale matrix revision rejected '+cat,op('PATCH','/security-matrix',target=SEC,category=cat,groups=[gkey],revision=d['revision'],changes=[{'row':row['id'],'group':gkey,'value':False}]).status_code==409)
  if cat=='link':report['matrix_target']=SEC
  good(change(cat,val=False)[2]);check('Original callback removes only chosen rule '+cat,not next(x for x in matrix(cat)['rows'] if x['id']==row['id'])['cells'][gkey]['explicit'])
 # A deny rule remains explicit/locked, not painted as a permission to grant.
 raw=good(op('GET','/security',target=SEC,key=gkey));xml='<rules><!--CUSTOM KEEP--><rule group="project" code="'+pj+'" access="allow"/><rule group="custom_017" code="untouched" access="deny"/><rule group="link" element="'+lname+'" project="'+pj+'" access="deny"/></rules>'
 good(op('PATCH','/security',target=SEC,key=gkey,revision=raw['revision'],xml=xml));d=matrix('link');r=next(x for x in d['rows'] if x['value']==lname);check('Custom deny remains locked rather than converted into allow',r['cells'][gkey]['read_only'] and not r['cells'][gkey]['checked'])
 check('Cannot mutate locked deny through matrix request',op('PATCH','/security-matrix',target=SEC,category='link',groups=[gkey],revision=d['revision'],changes=[{'row':r['id'],'group':gkey,'value':True}]).status_code==403)
 d,row,response=change('gear_menu',next(x for x in matrix('gear_menu')['rows'] if x.get('value')=='Column Manager'));good(response)
 final=good(op('GET','/security',target=SEC,key=gkey))['xml'];check('Unrelated custom XML rule and comment survive original callback','CUSTOM KEEP' in final and 'custom_017' in final and 'untouched' in final)
 # Final data for browser: a visible explicit permission and memberships.
 d,row,response=change('search_type',next(x for x in matrix('search_type')['rows'] if x['value']==st));good(response)
 # Observe newly saved results across three native workers, not only the writer.
 pids=set()
 for _ in range(6):
  r=op('GET','/stype-editor',target=ST,search_type=st);d=good(r);pids.add(r.headers.get('X-Tactic-Worker'));check('Reader sees updated SearchType metadata and column',d['metadata']['title']=='Новая подпись' and any(c['name']=='estimate' for c in d['columns']))
 check('New admin reads distributed across all workers',pids=={'1','2','3'})
 report.update(passed=True,project=pj,nonce=nonce)
except Exception as e:
 report['error']=str(e)
 import traceback;traceback.print_exc()
finally:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if not report['passed']:raise SystemExit(1)
