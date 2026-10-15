"""UI 0.17 on ORIGINAL TACTIC. Bridge only with an explicit option after a navigation attempt."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,base64,json
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--http-report',type=Path,required=True);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args()
out=a.output;out.mkdir(parents=True,exist_ok=True);(out/'screenshots').mkdir(exist_ok=True);data=json.loads(a.http_report.read_text());project=data['project'];gkey=data['group_key'];gname=data['group_name'];userkey=data['user_key'];stype=data['search_type'];nonce=data['nonce']
checks=[];errors=[];report={'passed':False,'scenarios':checks,'backend':'original TACTIC and SQLite / explicit test licence isolation inherited from runner'}
s=requests.Session();head={'X-Tactic-UI':'1','Origin':a.url}
def request(method,path,**d):
 r=s.request(method,a.url+'/api/ui/v2'+path,params=d if method=='GET' else None,json=d if method!='GET' else None,headers=head,timeout=60)
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text[:1000])
 return r.json()
def check(name,ok=True):
 checks.append({'scenario':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
head['X-CSRF-Token']=request('POST','/session',login='admin',password='Native-Test-Only-123')['csrf']
for pj in ('admin',project):
 for scope,val in [('workspace',{'ids':[],'active':''}),('navigation',{'folders':{}}),('appearance',{'theme':'light'})]:
  old=request('GET','/ui-state',project=pj,scope=scope);request('PATCH','/ui-state',project=pj,scope=scope,value=val,revision=old['revision'])
page=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1600,'height':1000});page=ctx.new_page();page.set_default_timeout(18000)
  try:page.goto(a.url+'/tactic/admin/',wait_until='networkidle',timeout=12000);report['native_navigation']=True
  except Exception as e:
   report['native_navigation']=False;report['navigation_error']=str(e)
   if not a.bridge:raise
   page.close();page=ctx.new_page();page.set_default_timeout(18000);transport_session=requests.Session()
   def transport(q):
    u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '');assert path.startswith('/api/ui/v2/')
    r=transport_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=60)
    return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
   page.expose_function('_real_http',transport);page.set_content('<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
   page.evaluate('''url=>{const b=document.createElement('base');b.href=url;document.head.append(b);const U=URL;window.URL=new Proxy(U,{construct(t,args){if(args[1]==='null')args[1]=url;return Reflect.construct(t,args)}});history.replaceState=()=>{};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''',a.url)
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text());report['bridge']=True
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
  def login():
   page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');page.wait_for_selector('main[aria-busy="false"]')
  login();page.get_by_label('Проект',exact=True).select_option(project);page.wait_for_selector('main[aria-busy="false"]');page.wait_for_timeout(300)
  page.evaluate('''()=>{const b=document.createElement('div');b.textContent='ORIGINAL TACTIC · SQLITE TEST DATA · signature isolated · HTTP bridge when navigation blocked';b.style='position:fixed;bottom:0;left:0;right:0;padding:4px;background:#24382b;color:white;font:11px sans-serif;z-index:999999;pointer-events:none';document.body.append(b)}''')
  def nav(name):
   leaf=page.locator('.sidebar button[title="'+name+'"]')
   if not leaf.is_visible():page.locator('.sidebar button[title="project_admin"]').click()
   leaf.click();page.wait_for_selector('main[aria-busy="false"]')
  nav('manage_users');page.wait_for_selector('.user-manager .native-grid[aria-busy="false"]');check('UserConfig is original three-tab manager',page.get_by_role('button',name='Group Assignment',exact=True).count()==1)
  page.wait_for_selector('.user-manager tr[data-key="'+userkey+'"]');check('UserPanel table uses configured columns and real account',page.locator('.user-manager tr[data-key="'+userkey+'"]').count()==1)
  page.get_by_role('button',name='Group Assignment',exact=True).click();page.wait_for_selector('.security-matrix tbody tr[data-rule="'+nonce+'"]')
  userrow=page.locator('.security-matrix tbody tr[data-rule="'+nonce+'"]');box=userrow.locator('input[aria-label$=" — '+gname+'"]');box.check();check('Membership check enters pending buffer',page.locator('.security-workspace .pending-count').is_visible())
  check('Checkbox has not written membership before Save',gname not in request('GET','/user-groups',project=project,target='admin_views/project_admin/manage_users',key=userkey)['members'])
  page.get_by_role('button',name='Сохранить изменения',exact=True).click();page.wait_for_selector('.security-workspace .success');check('UserSecurityCbk membership saved from Vue',gname in request('GET','/user-groups',project=project,target='admin_views/project_admin/manage_users',key=userkey)['members'])
  userrow.get_by_role('button',name=nonce,exact=True).click();page.wait_for_selector('.modal .membership-panel');check('User row opens original GroupAssign-based editor',page.locator('.modal .membership-panel .member-row').count()>0)
  page.locator('.modal .membership-panel .member-row').filter(has_text=gname).locator('input[type="checkbox"]').uncheck();page.get_by_role('button',name='Сохранить состав',exact=True).click();page.wait_for_selector('.modal .membership-panel .success');check('Explicit group assignment roundtrip from modal',gname not in request('GET','/user-groups',project=project,target='admin_views/project_admin/manage_users',key=userkey)['members']);page.locator('.modal.widget-popup > header button').click()
  page.get_by_role('button',name='Users',exact=True).click();page.wait_for_selector('.user-manager .native-grid[aria-busy="false"]');page.wait_for_selector('.user-manager tr[data-key="'+userkey+'"]');check('Back to actual configured UserPanel table',page.locator('.user-manager tr[data-key="'+userkey+'"]').count()==1)
  page.screenshot(path=str(out/'screenshots/user-manager.png'))
  nav('manage_security');page.wait_for_selector('.security-matrix');page.get_by_role('button',name='sType Security',exact=True).click();page.wait_for_selector('.security-matrix tr[data-rule="'+stype+'"]');r=page.locator('.security-matrix tr[data-rule="'+stype+'"]');b=r.locator('input[aria-label$=" — '+gname+'"]');check('Matrix reads original explicit SearchType permission',b.is_checked());b.uncheck();check('Security editing stages a change',page.locator('.security-workspace .pending-count').inner_text()=='1 правок');page.get_by_role('button',name='Сохранить изменения',exact=True).click();page.wait_for_selector('.security-workspace .success')
  rules=request('GET','/security',project=project,target='admin_views/project_admin/manage_security',key=gkey)['xml'];check('Original SearchType callback removed permission',stype not in rules);check('Custom security rule retained','custom_017' in rules)
  page.screenshot(path=str(out/'screenshots/security-matrix.png'))
  page.get_by_role('button',name='Группы',exact=True).click();page.wait_for_selector('.security-workspace td[data-field="name"]');check('Security Groups uses configured startup view',page.locator('.security-workspace th[data-field="name"]').count()>0 or page.locator('.security-workspace td[data-field="name"]').count()>0)
  page.screenshot(path=str(out/'screenshots/groups-manager.png'))
  nav('manage_search_types');page.wait_for_selector('.stype-workbench');page.locator('.stype-workbench .admin-catalog-item').filter(has_text=stype).click();page.wait_for_selector('.schema-editor-table');check('SearchType editor displays real physical column','estimate' in page.locator('.schema-editor-table').inner_text())
  page.get_by_role('button',name='SearchType',exact=True).click();page.locator('.stype-workbench').get_by_label('Название',exact=True).fill('Редактор браузера 017');page.get_by_role('button',name='Сохранить метаданные',exact=True).click();page.wait_for_selector('.stype-workbench .success');check('Metadata saved through original registry',request('GET','/stype-editor',project=project,target='admin_views/project_admin/manage_search_types',search_type=stype)['metadata']['title']=='Редактор браузера 017')
  page.get_by_role('button',name='Колонки',exact=True).click();page.get_by_role('button',name='Добавить физическую колонку',exact=True).click();page.get_by_placeholder('Имя колонки',exact=True).fill('browser_note');page.get_by_role('button',name='Создать 1 колонок',exact=True).click();page.wait_for_function('()=>document.querySelector(".schema-editor-table")?.textContent.includes("browser_note")');check('ColumnEditCbk works from native UI','browser_note' in page.locator('.schema-editor-table').inner_text())
  page.screenshot(path=str(out/'screenshots/search-type-editor.png'))
  page.get_by_role('button',name='Открыть таблицу',exact=True).click();page.wait_for_selector('main > .native-grid[aria-busy="false"]');check('Open table uses real configured view',page.locator('main > .native-grid tr[data-key="'+data['object_key']+'"]').count()==1)
  nav('manage_side_bar');page.wait_for_selector('.sidebar-workbench .sidebar-outline');outline=page.locator('.sidebar-outline li').filter(has_text=data['link_name']);outline.locator('.sidebar-outline-name').click();page.locator('.sidebar-workbench .admin-editor-pane').get_by_label('Заголовок',exact=True).fill('Новая ссылка 017');page.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('.sidebar-workbench .success');check('Sidebar saves property without separate Apply',any(e['title']=='Новая ссылка 017' for e in request('GET','/sidebar-editor',project=project,view='project_view')['elements']))
  outline=page.locator('.sidebar-outline li').filter(has_text=data['link_name']);outline.click(button='right');page.wait_for_selector('[role="menu"]');check('Sidebar right-click shows contextual actions',page.get_by_role('menuitem',name='Свойства',exact=True).is_visible());page.keyboard.press('Escape')
  child=page.locator('.sidebar-outline li').filter(has_text=data['folder_view']);child.locator('.sidebar-outline-name').dblclick();page.wait_for_function('(v)=>document.querySelector(".sidebar-editor-tools input")?.value===v',arg=data['folder_view']);check('Folder opens its actual child view',page.locator('.sidebar-outline').inner_text().find('inner')>=0)
  page.locator('.sidebar-workbench .admin-add-menu summary').click();page.get_by_role('button',name='Ссылка на таблицу',exact=True).click();page.locator('.sidebar-workbench .admin-editor-pane').get_by_label('Системное имя',exact=True).fill('browser_link');page.locator('.sidebar-workbench .admin-editor-pane').get_by_label('Заголовок',exact=True).fill('Ссылка из Vue');page.locator('.sidebar-workbench .admin-editor-pane').get_by_label('SearchType',exact=True).fill(stype);page.get_by_role('button',name='Добавить в черновик',exact=True).click();check('New link only in buffer before save',not any(e['name']=='browser_link' for e in request('GET','/sidebar-editor',project=project,view=data['folder_view'])['elements']))
  page.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_timeout(500);check('New link persisted as widget_config',any(e['name']=='browser_link' for e in request('GET','/sidebar-editor',project=project,view=data['folder_view'])['elements']))
  page.locator('.sidebar-outline li').filter(has_text='browser_link').locator('.sidebar-outline-name').click();page.screenshot(path=str(out/'screenshots/sidebar-editor.png'))
  page.get_by_role('button',name='Убрать ссылку…',exact=True).click();page.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_timeout(600);check('Removing sidebar reference leaves SObject untouched',request('GET','/record',project=project,target=data['table_target'],key=data['object_key'])['key']==data['object_key'])
  page.get_by_role('button',name='Переключить тему',exact=True).click();page.screenshot(path=str(out/'screenshots/sidebar-editor-dark.png'))
  check('No unhandled JS errors',not errors);report['passed']=True;browser.close()
except Exception as e:
 report['error']=str(e)
 import traceback;traceback.print_exc()
 try:page.screenshot(path=str(out/'screenshots/failure.png'))
 except Exception:pass
finally:report['errors']=errors;(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if not report['passed']:raise SystemExit(1)
