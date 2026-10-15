"""0.19 compact-chrome acceptance against ORIGINAL TACTIC; original 0.18 design flows retained.

The bridge is opt-in and only used after native navigation fails. It replaces
network delivery, not the original backend, login, commands or database.
"""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,base64,json,traceback,uuid,re
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--http-report',type=Path,required=True);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args()
out=a.output;out.mkdir(parents=True,exist_ok=True);(out/'screenshots').mkdir(exist_ok=True)
data=json.loads(a.http_report.read_text());project=data['project'];stype=data['search_type'];targets=data['targets'];nonce=uuid.uuid4().hex[:7]
r={'passed':False,'scenarios':[],'backend':'original TACTIC/SQLite with fixture records; license signature explicitly isolated by runner'};errors=[];page=None;dialog_accept=[True]
s=requests.Session();head={'X-Tactic-UI':'1','Origin':a.url}
def req(method,path,**d):
 result=s.request(method,a.url+'/api/ui/v2'+path,params=d if method=='GET' else None,json=d if method!='GET' else None,headers=head,timeout=90)
 if result.status_code not in (200,201):raise AssertionError(str(result.status_code)+' '+result.text[:1000])
 return result.json()
def check(name,ok=True):
 r['scenarios'].append({'scenario':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:
  if page:
   page.screenshot(path=str(out/'screenshots/failure.png'))
   (out/'private-page.html').write_text(page.content())
  raise AssertionError(name)
head['X-CSRF-Token']=req('POST','/session',login='admin',password='Native-Test-Only-123')['csrf']
for pj in ('admin',project):
 for scope,value in [('workspace',{'ids':[],'active':''}),('navigation',{'folders':{}}),('appearance',{'theme':'light'})]:
  old=req('GET','/ui-state',project=pj,scope=scope);req('PATCH','/ui-state',project=pj,scope=scope,value=value,revision=old['revision'])
layout=req('GET','/layout-document',project=project,target=targets['layout-editor'],key=data['layout_key'])
script=req('GET','/script',project=project,target=targets['script-editor'],key=data['script_key'])['record']
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1600,'height':1050});page=ctx.new_page();page.set_default_timeout(22000)
  try:page.goto(a.url+'/tactic/admin/',wait_until='networkidle',timeout=12000);r['native_navigation']=True
  except Exception as exc:
   r['native_navigation']=False;r['navigation_error']=str(exc);(out/'navigation-attempt.txt').write_text(str(exc))
   if not a.bridge:raise
   page.close();page=ctx.new_page();page.set_default_timeout(22000);transport_session=requests.Session()
   def transport(q):
    u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '')
    if not path.startswith('/api/ui/v2/'):raise AssertionError('Unapproved bridge route')
    result=transport_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=90)
    return {'status':result.status_code,'body64':base64.b64encode(result.content).decode(),'headers':dict(result.headers)}
   page.expose_function('_real_http',transport);page.set_content('<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
   page.evaluate('''url=>{const b=document.createElement('base');b.href=url;document.head.append(b);const U=URL;window.URL=new Proxy(U,{construct(t,args){if(args[1]==='null')args[1]=url;return Reflect.construct(t,args)}});history.replaceState=()=>{};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''',a.url)
   web=ROOT/'src/tactic/ui_api/web';css=(web/'styles.css').read_text()
   # Same packaged assets, loaded explicitly because this environment blocks network script/link delivery.
   page.add_style_tag(content=css);page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text())
   ace=web/'vendor/ace';page.add_script_tag(content=(ace/'ace.js').read_text())
   for name in ['mode-python.js','mode-javascript.js','mode-xml.js','mode-css.js','mode-html.js','theme-textmate.js','theme-tomorrow_night.js','ext-searchbox.js']:
    if (ace/name).exists():page.add_script_tag(content=(ace/name).read_text())
   page.evaluate('''css=>{const original=Element.prototype.attachShadow;Element.prototype.attachShadow=function(o){const root=original.call(this,o);new MutationObserver(()=>{const l=root.querySelector('link[href="/tactic-ui/styles.css"]');if(l){const st=document.createElement('style');st.textContent=css;l.replaceWith(st)}}).observe(root,{childList:true});return root}}''',css)
   page.add_script_tag(content=(web/'app.js').read_text());r['bridge']=True;r['bridge_assets']='packaged Ace modes/themes and stylesheet including shadow CSS loaded as content'
  page.evaluate('''()=>{const request=window.fetch.bind(window);window.__compactRequests=0;window.fetch=async(...args)=>{window.__compactRequests++;try{return await request(...args)}finally{window.__compactRequests--}}}''')
  page.on('pageerror',lambda exc:errors.append(str(exc)));page.on('dialog',lambda d:d.accept() if dialog_accept[0] else d.dismiss())
  page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');page.wait_for_selector('main[aria-busy="false"]')
  page.get_by_label('Проект',exact=True).select_option(project);page.wait_for_selector('main[aria-busy="false"]');page.wait_for_timeout(400)
  page.evaluate('''()=>{const b=document.createElement('div');b.textContent='ORIGINAL TACTIC · SQLITE TEST DATA · isolated signature · explicit HTTP bridge if native navigation blocked';b.style='position:fixed;bottom:0;left:0;right:0;padding:4px;background:#24382b;color:white;font:11px sans-serif;z-index:999999;pointer-events:none';document.body.append(b)}''')
  def nav(kind):
   name=targets[kind].rsplit('/',1)[-1];leaf=page.locator('.sidebar button[title="'+name+'"]')
   if not leaf.is_visible():page.locator('.sidebar button[title="project_admin"]').click()
   leaf.click();page.wait_for_selector('main[aria-busy="false"]')
  def source(selector,value):
   box=page.locator(selector);box.wait_for(state='visible');page.wait_for_function('(sel)=>!!document.querySelector(sel)?.env?.editor',arg=selector)
   box.evaluate('(el,value)=>el.env.editor.session.setValue(value)',value)
  def read_source(selector):return page.locator(selector).evaluate('(el)=>el.env.editor.getValue()')
  def save_ace(selector):page.locator(selector).evaluate('(el)=>el.env.editor.execCommand("tacticSave")')
  def nav_path(target):
   for folder in target.split('/')[1:-1]:
    node=page.locator('.sidebar button[title="'+folder+'"]')
    if node.count() and node.get_attribute('aria-expanded')=='false':node.click()
   leaf=page.locator('.sidebar button[title="'+target.rsplit('/',1)[-1]+'"]');leaf.click()
   page.wait_for_selector('main[aria-busy="false"]')
  def compact(label,selector,allowed_gap=12):
   panel=page.locator(selector);panel.first.wait_for(state='visible');page.wait_for_timeout(150)
   bar=page.locator('.workspace-tabbar').bounding_box();box=panel.first.bounding_box()
   gap=round(box['y']-(bar['y']+bar['height']),2)
   r.setdefault('compact_measurements',[]).append({'screen':label,'panel_gap_px':gap,'tabbar_height_px':bar['height']})
   check(label+' has no duplicate page hero',page.locator('.workspace .view-heading').count()==0)
   check(label+' content starts immediately below tabs',-1<=gap<=allowed_gap)
  nav('layout-editor');compact('Custom Layout','[data-testid=custom-layout-editor]')
  check('Layout catalog, not an intro block, is first visible content',page.locator('[data-testid=custom-layout-editor] .admin-catalog').bounding_box()['y']-page.locator('[data-testid=custom-layout-editor]').bounding_box()['y']<=12)
  check('Page context menu is accessible from the tab strip',page.get_by_label('Меню представления',exact=True).is_visible())
  page.get_by_label('Меню представления',exact=True).click();page.wait_for_selector('[role="menu"]');check('Original widget menu still opens',page.locator('[role="menu"]').is_visible());page.keyboard.press('Escape')
  check('Menu closes with Escape',page.locator('[role="menu"]').count()==0)
  page.screenshot(path=str(out/'screenshots/compact-layout-catalog.png'))
  # Custom Layout: real saved sections, edit/save, isolated static preview, original nested widget.
  nav('layout-editor');page.wait_for_selector('[data-testid="custom-layout-editor"]');page.locator('[data-testid="custom-layout-editor"] .admin-catalog-item').filter(has_text=layout['view']).first.click()
  box='[data-testid="custom-layout-editor"] .ace-surface';page.wait_for_selector(box)
  check('Custom Layout is a dedicated section editor',page.locator('[data-testid="custom-layout-editor"] .admin-section-tabs button').count()==6)
  check('Local Ace loads without CDN',page.locator(box).evaluate('(el)=>!!el.env?.editor'))
  new_html=re.sub(r'<h2>.*?</h2>','<h2>Layout browser '+nonce+'</h2>',layout['parts']['html'],count=1,flags=re.S)+'<script>window.DESIGN_BROWSER_EXECUTED_018=true</script>'
  source(box,new_html);check('Editing layout stages a draft',page.locator('[data-testid=custom-layout-editor] .editor-status').is_visible())
  page.get_by_role('button',name='Preview',exact=True).click();page.wait_for_selector('.design-preview-block .layout-preview-surface')
  check('Static preview renders markup in isolated shadow',page.locator('.design-preview-block .layout-preview-surface').evaluate('(el)=>el.shadowRoot.textContent.includes("Layout browser")'))
  check('Static preview does not execute scripts or behavior',page.evaluate('()=>window.DESIGN_BROWSER_EXECUTED_018===undefined&&window.DESIGN_PRIVATE_BODY_018===undefined'))
  check('Preview does not write original widget_config',req('GET','/layout-document',project=project,target=targets['layout-editor'],key=layout['key'])['revision']==layout['revision'])
  save_ace(box);page.wait_for_function('()=>document.querySelector("[data-testid=custom-layout-editor]")?.textContent.includes("Сохранено в исходный widget_config")')
  saved=req('GET','/layout-document',project=project,target=targets['layout-editor'],key=layout['key'])
  check('Ace Ctrl+S command persists original layout', 'Layout browser '+nonce in saved['parts']['html'])
  check('HTML edit keeps saved Mako/behaviors intact',saved['parts']['mako']==layout['parts']['mako'] and saved['parts']['behavior']==layout['parts']['behavior'])
  page.get_by_role('button',name='CSS',exact=True).click();source(box,'.layout-card { padding:24px; border:1px solid #5b72aa; border-radius:12px; } /* '+nonce+' */');page.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_function('()=>document.querySelector("[data-testid=custom-layout-editor]")?.textContent.includes("Сохранено в исходный widget_config")')
  page.screenshot(path=str(out/'screenshots/custom-layout-editor.png'))
  page.get_by_role('button',name='Открыть layout',exact=True).click();page.wait_for_selector('.layout-preview .native-grid[aria-busy="false"]');page.wait_for_selector('.layout-preview td[data-field="login"]');check('Saved layout opens original native child table',page.locator('.layout-preview td[data-field="login"]').count()>0)
  check('Nested table reads original user rows',page.locator('.layout-preview tbody tr[data-key]').count()>0);check('Stored behavior still not executed in opened layout',page.evaluate('()=>window.DESIGN_PRIVATE_BODY_018===undefined'))
  page.screenshot(path=str(out/'screenshots/saved-layout-widget.png'))
  # Manage Views: inherited and concrete records, CAS save, original config designer and nested opening.
  nav('views-manager');page.wait_for_selector('[data-testid="manage-views"]');page.locator('[data-testid="manage-views"] select').first.select_option(stype)
  page.locator('[data-testid="manage-views"] .admin-catalog-item').filter(has_text='new_view_018').click();page.wait_for_selector('[data-testid="manage-views"] .admin-editor-pane code')
  check('Manage Views shows inherited and DB layers',page.locator('[data-testid="manage-views"] .design-layer-choice').count()>0)
  page.locator('[data-testid="manage-views"] .design-layer-choice[data-key="'+data['view_key']+'"]').click();vbox='[data-testid="manage-views"] .ace-surface';page.wait_for_selector(vbox)
  src=read_source(vbox);source(vbox,re.sub(r'title="[^"]*"', 'title="Имя из браузера 018"',src,count=1).replace('</config>','<!-- '+nonce+' --></config>'))
  save_ace(vbox);page.wait_for_function('()=>document.querySelector("[data-testid=manage-views]")?.textContent.includes("View сохранён")')
  check('Manage Views save writes exact selected view record','Имя из браузера 018' in req('GET','/view-document',project=project,target=targets['views-manager'],search_type=stype,key=data['view_key'])['xml'])
  page.screenshot(path=str(out/'screenshots/manage-views.png'))
  page.get_by_role('button',name='Элементы и определения',exact=True).click();page.wait_for_selector('.designer-body');check('Manage Views opens existing original-config column designer',page.locator('.designer-body').is_visible())
  page.get_by_role('button',name='Закрыть конструктор',exact=True).click()
  page.locator('[data-testid="manage-views"]').get_by_role('button',name='Открыть',exact=True).click();page.wait_for_selector('.native-grid[aria-busy="false"]');check('Managed view opens original table with configured title',page.get_by_text('Имя из браузера 018',exact=True).count()>0)
  # Script editor: local Ace syntax/diff, saved original execution, no execution of edited text.
  nav('script-editor');page.wait_for_selector('[data-testid="script-editor"]');page.locator('.script-entry').filter(has_text=script['values']['title']).first.click();sbox='[data-testid="script-editor"] .ace-surface';page.wait_for_selector(sbox)
  check('Saved Python uses Ace Python mode',page.locator(sbox).evaluate('(el)=>el.env.editor.session.getMode().$id')=='ace/mode/python')
  source(sbox,'return {"from_browser": input.get("value")}\n# '+nonce+'\n');page.get_by_role('button',name='Изменения',exact=True).click();page.wait_for_selector('.script-diff');check('Script diff compares pending text with saved version','from_browser' in page.locator('.script-diff').inner_text())
  page.locator('.script-run summary').click();check('Cannot run unsaved editor text',page.get_by_role('button',name='Выполнить сохранённый Python',exact=True).is_disabled())
  save_ace(sbox);page.wait_for_function('()=>!document.querySelector("[data-testid=script-editor] .editor-status")')
  check('Script save persists original custom_script','from_browser' in req('GET','/script',project=project,target=targets['script-editor'],key=data['script_key'])['record']['values']['script'])
  page.locator('.script-run textarea').fill('{"value":"original browser command"}');page.get_by_role('button',name='Выполнить сохранённый Python',exact=True).click();page.wait_for_selector('.script-run pre');check('Original saved Python execution returns real result','original browser command' in page.locator('.script-run pre').inner_text())
  page.get_by_label('Найти в скрипте',exact=True).fill('from_browser');page.get_by_role('button',name='Следующее',exact=True).click();check('Ace search works on real source',page.locator(sbox).evaluate('(el)=>el.env.editor.getSelectedText()')=='from_browser')
  page.screenshot(path=str(out/'screenshots/script-editor.png'))
  # Manage sTypes maintains original definitions and adds bounded create-only CSV via real command.
  nav('search-types');page.wait_for_selector('.stype-workbench');page.locator('.stype-workbench .admin-catalog-item').filter(has_text=stype).click();page.wait_for_selector('.schema-editor-table')
  check('SearchType manager restores real physical fields','external_ref' in page.locator('.schema-editor-table').inner_text())
  page.locator('.schema-editor-table tbody tr').filter(has=page.locator('td b',has_text='external_ref')).get_by_role('button',name='Ссылки',exact=True).click();page.wait_for_function('()=>document.querySelector(".stype-workbench")?.textContent.includes("Связи Schema:")');check('Column references do not pretend to allow unsafe DDL',page.get_by_text('Удаление и изменение типа колонок этим экраном не выполняются.',exact=False).is_visible())
  page.get_by_role('button',name='CSV-импорт',exact=True).click();page.wait_for_selector('.csv-import-panel');cbox='.csv-import-panel .ace-surface'
  source(cbox,'name,description\nBrowser '+nonce+',Imported from UI\n');page.get_by_role('button',name='Сопоставить колонки',exact=True).click();page.get_by_role('button',name='Предпросмотр без записи',exact=True).click();page.wait_for_selector('.csv-import-panel .table-scroll')
  check('CSV header maps existing original form fields',page.locator('.csv-import-panel .column-row select').first.input_value()=='name')
  check('CSV preview exposes trimmed new row','Browser '+nonce in page.locator('.csv-import-panel .table-scroll').inner_text())
  page.get_by_role('button',name='Импортировать 1',exact=True).click();page.wait_for_selector('.csv-import-panel .success');check('UI imports through original CsvImportCmd',page.locator('.csv-import-panel .success').is_visible())
  page.get_by_role('button',name='Колонки',exact=True).click();page.screenshot(path=str(out/'screenshots/search-type-tools.png'))
  page.get_by_role('button',name='Открыть таблицу',exact=True).click();page.wait_for_selector('.native-grid[aria-busy="false"]');check('Imported SObject appears in original configured table',page.get_by_text('Browser '+nonce,exact=True).count()>0)
  # Check every requested workspace family without deleting their real controls.
  project_screens=[('Manage Views',targets['views-manager'],'[data-testid=manage-views]'),('Script Editor',targets['script-editor'],'[data-testid=script-editor]'),('SearchTypes',targets['search-types'],'.stype-workbench'),('Sidebar','admin_views/project_admin/manage_side_bar','.sidebar-workbench'),('Security','admin_views/project_admin/manage_security','.security-workspace'),('Users','admin_views/project_admin/manage_users','.user-manager'),('Pipeline','admin_views/project_admin/project_workflow','.graph-editor'),('Schema','admin_views/project_admin/project_schema','.graph-editor')]
  # Resolve sidebar spellings from source configs; no synthetic screens.
  all_nodes=[]
  def walk(nodes):
   for n in nodes:
    all_nodes.append(n);walk(n.get('children',[]))
  walk(req('GET','/sidebar',project=project)['sections'])
  for label,target,selector in project_screens:
   if label=='Sidebar':target=next(n['id'] for n in all_nodes if n.get('kind')=='link' and n.get('renderer')=='sidebar-editor') if any(n.get('renderer')=='sidebar-editor' for n in all_nodes) else next(n['id'] for n in all_nodes if n.get('name') in ['manage_side_bar','manage_sidebar'])
   nav_path(target);compact(label,selector)
   check(label+' has no editor hero',page.locator(selector+' > .design-heading, '+selector+' > .admin-workspace-heading').count()==0)
  # Refresh is retained, cancels safely, then really remounts the editor on approval.
  nav('layout-editor');page.locator('[data-testid=custom-layout-editor] .admin-catalog-item').filter(has_text=layout['view']).first.click();page.wait_for_selector(box)
  current_text=read_source(box);source(box,current_text+'<!-- unsaved compact test -->')
  dialog_accept[0]=False;page.get_by_label('Обновить представление',exact=True).click();page.wait_for_timeout(250)
  check('Cancel refresh preserves the typed layout',read_source(box).endswith('<!-- unsaved compact test -->'))
  dialog_accept[0]=True;old=page.locator('[data-testid=custom-layout-editor]').element_handle();page.get_by_label('Обновить представление',exact=True).click();page.wait_for_function('(el)=>!el.isConnected',arg=old)
  check('Approved refresh remounts actual editor instead of doing nothing',not old.evaluate('(el)=>el.isConnected'))
  page.locator('[data-testid=custom-layout-editor] .admin-catalog-item').filter(has_text=layout['view']).first.click();page.wait_for_selector(box)
  check('Refresh restores stored content, not discarded draft','unsaved compact test' not in read_source(box))
  page.screenshot(path=str(out/'screenshots/compact-layout-light.png'))
  page.get_by_label('Переключить тему',exact=True).click();page.wait_for_timeout(150);page.screenshot(path=str(out/'screenshots/compact-layout-dark.png'))
  check('Theme still toggles without adding page chrome',page.locator('html').get_attribute('data-theme')=='dark')
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250);page.get_by_label('Открыть меню',exact=True).click();page.wait_for_timeout(200)
  check('Compact mobile shell has no horizontal document overflow',page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1'))
  check('Mobile tab actions stay inside viewport',page.get_by_label('Меню представления',exact=True).bounding_box()['x']+page.get_by_label('Меню представления',exact=True).bounding_box()['width']<=390)
  page.screenshot(path=str(out/'screenshots/compact-layout-mobile.png'))
  page.set_viewport_size({'width':1600,'height':1050});page.get_by_label('Открыть меню',exact=True).click();page.get_by_label('Переключить тему',exact=True).click()
  page.get_by_label('Проект',exact=True).select_option('admin');page.wait_for_selector('main[aria-busy="false"]');page.wait_for_timeout(400)
  for label,target,selector in [('System Config','admin_views/global_admin/system_config','.global-settings'),('System Info','admin_views/global_admin/system_info','.admin-panel'),('License','admin_views/global_admin/license','.global-settings'),('Groups','admin_views/global_admin/groups','.native-grid'),('Group Membership','admin_views/global_admin/users_in_groups','.membership-panel'),('Project Wizard','admin_views/create_project','.admin-panel')]:
   nav_path(target);compact(label,selector)
  check('Project wizard retains functional steps',page.locator('.wizard-steps li').count()==4)
  check('Project wizard has no large intro',page.locator('.wizard-intro').count()==0)
  nav_path('admin_views/global_admin/users');page.wait_for_selector('.native-grid[aria-busy="false"]')
  page.locator('.native-grid').get_by_role('button',name='Новая запись',exact=True).click();page.wait_for_selector('.modal[role=dialog]')
  check('Popup form still has visible identification',page.locator('.modal[role=dialog] h2').is_visible())
  check('Popup form title remains compact',page.locator('.modal[role=dialog] header').bounding_box()['height']<90)
  page.get_by_label('Закрыть',exact=True).last.click()
  check('Column headers remain visible and functional',page.locator('.native-grid thead th').count()>3)
  # Packaged Ace assets really served by original server, not just files existing on disk.
  for asset in ('ace.js','mode-python.js','mode-html.js','ext-searchbox.js'):
   response=s.get(a.url+'/tactic-ui/vendor/ace/'+asset,timeout=30);check('Original static endpoint serves '+asset,response.status_code==200 and len(response.content)>500)
  page.wait_for_timeout(900);page.wait_for_function('()=>window.__compactRequests===0');check('No JavaScript page errors',not errors);r['passed']=True;page.wait_for_timeout(100);browser.close()
except Exception as exc:
 r['error']=str(exc);traceback.print_exc()
 if page:
  try:page.screenshot(path=str(out/'screenshots/failure.png'))
  except Exception:pass
finally:
 r['page_errors']=errors;(out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
if not r['passed']:raise SystemExit(1)
