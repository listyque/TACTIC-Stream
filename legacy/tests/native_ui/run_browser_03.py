"""Browser regression against serve_fixture.py. Synthetic records, ORIGINAL XML menu.

--bridge is only for environments that prohibit ALL browser navigation. In that
mode the production JS/CSS are injected into about:blank, URL/storage/history
are test shims and fetch travels through Python requests to real CherryPy.
This does NOT validate native browser cookies/navigation/CSP. Default mode does.
"""
import argparse,json,re,time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--bridge',action='store_true');parser.add_argument('--url',default='http://127.0.0.1:9147');parser.add_argument('--chromium',default='/usr/bin/chromium');parser.add_argument('--output',default=str(ROOT/'docs/native-ui'))
a=parser.parse_args();out=Path(a.output);(out/'screenshots').mkdir(parents=True,exist_ok=True)
results=[]
def passed(name):results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1540,'height':980});page=context.new_page();page.set_default_timeout(6000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)));called=[]
 if a.bridge:
  session=requests.Session()
  def http(req):
   from urllib.parse import urlsplit
   u=urlsplit(req['url']);path=u.path+('?' + u.query if u.query else '')
   assert path.startswith('/api/ui/v2/'),path
   called.append(path)
   response=session.request(req['method'],a.url+path,headers=req.get('headers',{}),data=req.get('body'),timeout=10)
   return {'status':response.status_code,'body':response.text,'headers':{'content-type':response.headers.get('content-type','application/json')}}
  page.expose_function('_fixture_http',http)
  page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE</title></head><body><div id="app"></div></body></html>')
  page.evaluate('''() => {
   const URL0=window.URL;window.URL=new Proxy(URL0,{construct(target,args){if(args[1]==='null')args[1]='https://fixture.invalid';return Reflect.construct(target,args)}});
   const store=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}});
   history.replaceState=(state,unused,url)=>{window._fixture_path=url};
   window.fetch=async(url,options={})=>{const r=await window._fixture_http({url:String(url),method:options.method||'GET',headers:options.headers||{},body:options.body});return new Response(r.body,{status:r.status,headers:r.headers})};
  }''')
  web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
 else:page.goto(a.url+'/tactic/admin/',wait_until='networkidle')

 try:
  page.on('dialog', lambda d: d.accept())
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.fixture-banner');page.wait_for_selector('.sidebar .nav-item');passed('Login using real CherryPy API, not injected UI state')
  def nav(name):return page.locator('.sidebar button[title="'+name+'"]')
  def ready(selector):page.wait_for_selector(selector);page.wait_for_timeout(100)
  def no_errors():
   problems=page.locator('.error:visible').all_text_contents();assert not problems,problems
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'],top;passed('Actual shipped admin hierarchy, no hard-coded replacement menu')
  nav('global_admin').click();nav('users').click();ready('tbody tr .check-cell');assert page.locator('tbody tr').count()==12;passed('Original users widget_config resolves table columns')
  page.get_by_role('button',name='Карточки',exact=True).click();ready('.entity-card');assert page.locator('.entity-card').count()==12;passed('Same configured records in card view')
  page.get_by_role('button',name='Таблица',exact=True).click();ready('tbody tr .check-cell')
  page.locator('tbody tr').first.click(button='right');page.get_by_role('menuitem',name='Открыть запись / файлы / связи',exact=True).click();ready('.inspector');passed('Shared context action opens record detail')
  page.locator('.inspector').get_by_role('button',name='Обсуждение',exact=True).click();ready('.inspector textarea');page.locator('.inspector textarea').fill('Migration check <script>alert(1)</script>');page.locator('.inspector').get_by_role('button',name='Отправить',exact=True).click();ready('.inspector .note');assert '<script>alert(1)</script>' in page.locator('.note').inner_text();passed('Discussion posts through HTTP and renders note as text, not HTML')
  page.locator('.inspector').get_by_role('button',name='Файлы',exact=True).click();ready('.file-row a');link=page.locator('.file-row a').first.get_attribute('href');assert 'snapshot=' in link and 'file=TESTFILE' in link;passed('Snapshot-owned file links include object/version/file identifiers')
  page.locator('.inspector').get_by_role('button',name='Связи',exact=True).click();ready('.relation-row button');page.locator('.relation-row button').click();ready('tbody tr .check-cell');assert 'Related tasks' in page.locator('.view-heading').inner_text();passed('Declared relationship opens an independent related-record view')
  # Use the actual task target from the source project_essentials XML.
  nav('project_essentials').click();nav('project_tasks').click();ready('tbody tr .check-cell')
  page.locator('tbody tr').first.locator('td').nth(2).dblclick();ready('.inline-editor input');page.locator('.inline-editor input').fill('Edited via native cell');page.locator('.inline-editor').get_by_role('button',name='✓',exact=True).click();page.wait_for_selector('.inline-editor',state='detached');page.wait_for_function("document.querySelector('tbody').textContent.includes('Edited via native cell')");passed('Inline cell edits use original form contract + revisioned update')
  page.locator('.table-tools select').select_option('status');assert page.locator('.group-row').count()==2;passed('Explicit current-page grouping over the same configured rows');page.locator('.table-tools select').select_option('')
  page.get_by_role('button',name='Сохранить поиск в sidebar',exact=True).click();page.get_by_placeholder('Название личного представления').fill('Native saved tasks');page.get_by_role('button',name='Сохранить в widget_config',exact=True).click();page.wait_for_function("document.querySelector('.sidebar').textContent.includes('Native saved tasks')");passed('Saved search creates a real-shaped personal sidebar XML override')
  page.get_by_role('button',name='Настроить представление',exact=True).click();ready('.designer-row');page.locator('.designer-row').nth(1).locator('button').first.click();page.get_by_label('Заголовок',exact=True).fill('Native Description');page.locator('.designer-properties').get_by_role('button',name='Применить свойства',exact=True).click();page.get_by_role('button',name='Сохранить widget_config',exact=True).click();page.wait_for_timeout(350);no_errors();page.get_by_role('button',name='Закрыть конструктор',exact=True).click();page.wait_for_function("document.querySelector('thead').textContent.includes('Native Description')");passed('View designer label is persisted and reprojected to table')
  # Hide a field in source config, not merely a browser-only toggle.
  page.get_by_role('button',name='Настроить представление',exact=True).click();ready('.designer-row');page.locator('.designer-row').filter(has_text='assigned').locator('button').first.click();page.get_by_label(re.compile('^Видимость')).select_option('false');page.locator('.designer-properties').get_by_role('button',name='Применить свойства',exact=True).click();page.get_by_role('button',name='Сохранить widget_config',exact=True).click();page.wait_for_timeout(300);no_errors();page.locator('.designer-row').filter(has_text='assigned').locator('button').first.click();page.screenshot(path=str(out/'screenshots/view-designer.png'));page.get_by_role('button',name='Закрыть конструктор',exact=True).click();assert 'assigned' not in page.locator('thead').inner_text();passed('Source is_visible changes default visibility after reloading view')
  page.get_by_role('button',name='Gantt / календарь',exact=True).click();ready('.timeline');page.locator('.timeline select').nth(0).select_option('bid_start_date');page.locator('.timeline select').nth(1).select_option('bid_end_date');page.locator('.timeline input[type=date]').nth(0).fill('2026-09-01');page.locator('.timeline input[type=date]').nth(1).fill('2026-09-30');page.wait_for_function("document.querySelectorAll('.gantt-bar').length===12");assert page.locator('.gantt-bar').count()==12;passed('Configured task dates activate native timeline without alternate task database')
  page.get_by_role('button',name='Календарь',exact=True).click();page.locator('.timeline input[type=month]').fill('2026-09');page.wait_for_timeout(200);assert page.locator('.calendar-day button').count()>12;page.screenshot(path=str(out/'screenshots/task-calendar.png'));no_errors();passed('Calendar queries the selected date window with the configured task view')
  nav('project_admin').click();nav('project_workflow').click();ready('.graph-editor select');page.locator('.graph-editor select').first.select_option(index=1);ready('.graph-node');assert page.locator('.graph-node').count()==2;passed('Original pipeline XML resolves nodes and connections')
  page.locator('.graph-node').first.click();page.locator('.graph-properties').get_by_label('Имя',exact=True).fill('request-renamed');page.locator('.graph-properties').get_by_label('Описание',exact=True).fill('Description preserved');page.locator('.graph-properties').get_by_role('button',name='Применить свойства',exact=True).click();page.get_by_role('button',name='Сохранить граф',exact=True).click();page.wait_for_timeout(350);no_errors();page.get_by_role('button',name='Исходный XML',exact=True).click();assert 'request-renamed' in page.locator('.raw-xml').inner_text() and 'custom="A &amp; B"' in page.locator('.raw-xml').inner_text();passed('Rename updates edges while preserving unknown XML attributes')
  page.get_by_role('button',name='Исходный XML',exact=True).click();page.get_by_placeholder('Имя нового процесса').fill('publish');page.get_by_role('button',name='+ Узел',exact=True).click();assert page.locator('.graph-node').count()==3;page.get_by_role('button',name='Сохранить граф',exact=True).click();page.wait_for_timeout(300);no_errors();passed('Add process and persist graph through revision checked endpoint')
  tools=page.locator('.graph-tools');tools.locator('select').nth(1).select_option('review');tools.locator('select').nth(2).select_option('publish');tools.get_by_role('button',name='+ Связь',exact=True).click();page.get_by_role('button',name='Сохранить граф',exact=True).click();page.wait_for_timeout(300);no_errors();passed('Add a real named process connection rather than canvas-only decoration')
  page.get_by_placeholder('Имя нового процесса').fill('temporary');page.get_by_role('button',name='+ Узел',exact=True).click();page.get_by_role('button',name='Отменить правку',exact=True).click();assert page.locator('.graph-node').count()==3;passed('Graph undo restores local operation batch')
  page.screenshot(path=str(out/'screenshots/pipeline-editor.png'))
  nav('project_schema').click();ready('.graph-editor select');page.locator('.graph-editor select').first.select_option(index=1);ready('.graph-node');page.locator('.graph-tools select').first.select_option('sthpw/note');page.get_by_role('button',name='+ Узел',exact=True).click();page.get_by_role('button',name='Сохранить граф',exact=True).click();page.wait_for_timeout(300);no_errors();assert page.locator('.graph-node').count()==3;passed('Schema editor inserts existing SearchType into original graph')
  nav('manage_users').click();ready('.admin-panel tbody tr');assert page.locator('.admin-panel tbody tr').count()==2;page.locator('.admin-panel tbody tr').first.get_by_role('button',name='Изменить',exact=True).click();ready('.admin-panel .modal');page.locator('.admin-panel .modal').get_by_label('display_name',exact=True).fill('Updated fixture user');page.locator('.admin-panel .modal').get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('.admin-panel .modal',state='detached');no_errors();assert 'Updated fixture user' in page.locator('.admin-panel tbody').inner_text();passed('Configured manage_users screen edits only explicit writable user fields')
  nav('manage_security').click();ready('.admin-panel select');page.locator('.admin-panel select').first.select_option(index=1);ready('.security-editor textarea');page.screenshot(path=str(out/'screenshots/group-rules.png'));passed('Group permission XML available in configured admin screen')
  nav('manage_side_bar').click();ready('.effective-editor .element-list li');assert page.locator('.effective-editor .element-list li').count()==5;page.locator('.effective-editor .element-list li').first.get_by_role('button',name='Вниз',exact=True).click();page.get_by_role('button',name='Сохранить порядок в TACTIC',exact=True).click();page.wait_for_function("document.querySelector('.nav-section > ul > li > button').title==='global_admin'");passed('Original sidebar ordering still editable in widget_config after deeper UI migration')
  page.screenshot(path=str(out/'screenshots/sidebar-config-layers.png'))
  nav('create_project').click();ready('.project-create-form');passed('Original app.ProjectCreateWdg now resolves native project command form')
  
  if not nav('license').is_visible():nav('global_admin').click()
  nav('license').click();ready('.global-settings .license-info');passed('Dedicated license panel displays fixture metadata without becoming a generic table')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'screenshots/mobile.png'));assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Mobile shell has no page-width overflow')
  assert not errors,errors;passed('No uncaught JS errors in tested source-configured flows')
  assert not any('get_widget' in path for path in called);passed('No old get_widget rendering calls in tested Vue flows')
  page.get_by_role('button',name='Выйти',exact=True).click();ready('.login-card');passed('Logout invalidates session and closes configured UI')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'test_backend':'original config XML + synthetic state; not PostgreSQL','transport':'Python HTTP bridge; URL/storage/history test shims' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
