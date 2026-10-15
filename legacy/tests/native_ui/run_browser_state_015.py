"""Original server, project wizard + fresh-browser DB state. LocalStorage forbidden.
Use --bridge ONLY when Chromium's native navigation really is blocked.
"""
import argparse,base64,json,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args();out=a.output;(out/'screenshots').mkdir(parents=True,exist_ok=True)
report={'passed':False,'scenarios':[],'bridge':a.bridge,'storage':'original sthpw/wdg_settings'};errors=[];paths=[];prefix='web015_'+uuid.uuid4().hex[:8];target='admin_views/global_admin/users'
s=requests.Session();h={'X-Tactic-UI':'1','Origin':a.url}
def call(method,path,**data):
 r=s.request(method,a.url+'/api/ui/v2'+path,headers=h,params=data if method=='GET' else None,json=data if method!='GET' else None,timeout=120)
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text[:1600])
 return r.json()
h['X-CSRF-Token']=call('POST','/session',login='admin',password='Native-Test-Only-123')['csrf']
def state(scope,target=''):return call('GET','/ui-state',project='admin',scope=scope,target=target)
def put(scope,value,target=''):
 r=state(scope,target);return call('PATCH','/ui-state',project='admin',scope=scope,target=target,revision=r['revision'],value=value)
def check(name,ok=True):
 report['scenarios'].append({'scenario':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
for scope,value,t in [('workspace',{'ids':[],'active':''},''),('appearance',{'theme':'light'},''),('navigation',{'folders':{}},''),('query',{},target),('geometry',{},target)]:put(scope,value,t)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox'])
 def mount():
  ctx=browser.new_context(viewport={'width':1560,'height':1000});page=ctx.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)))
  deny="Object.defineProperty(window,'localStorage',{get(){throw new Error('TEST: localStorage is forbidden')}});Object.defineProperty(window,'sessionStorage',{get(){throw new Error('TEST: sessionStorage is forbidden')}});"
  ctx.add_init_script(deny)
  try:page.goto(a.url+'/tactic/admin/',wait_until='networkidle',timeout=12000);report['direct_navigation']=True
  except Exception as exc:
   report['direct_navigation']=False;(out/'native-navigation.txt').write_text(str(exc));
   if not a.bridge:raise
  if a.bridge:
   transport_session=requests.Session();page.close();page=ctx.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)))
   def transport(q):
    u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '');assert path.startswith('/api/ui/v2/');paths.append({'method':q['method'],'path':path})
    r=transport_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=120)
    return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
   def image_transport(route):
    u=urlsplit(route.request.url)
    if u.path!='/api/ui/v2/file':return route.abort()
    r=transport_session.get(a.url+u.path+'?'+u.query,timeout=30);route.fulfill(status=r.status_code,body=r.content,headers={'Content-Type':r.headers.get('Content-Type','application/octet-stream')})
   page.route('**/api/ui/v2/file?*',image_transport);page.expose_function('_real_http',transport)
   page.set_content('<html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
   page.evaluate('(url)=>{const b=document.createElement("base");b.href=url;document.head.append(b)}',a.url+'/')
   page.evaluate('''()=>{const U=window.URL;window.URL=new Proxy(U,{construct(t,a){if(a[1]==='null')a[1]='http://localhost';return Reflect.construct(t,a)}});history.replaceState=(s,t,u)=>{window.__projectRoute=u};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''')
   # add_init_script ran in this context; no storage shim is supplied.
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
  page.on('dialog',lambda d:d.accept())
  page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item')
  page.evaluate('''()=>{const b=document.createElement('div');b.textContent='ORIGINAL TACTIC · SQLITE TEST DATA · isolated licence signature · HTTP bridge · localStorage disabled';b.style='position:fixed;bottom:0;left:0;right:0;background:#443922;color:white;padding:4px;font:11px sans-serif;z-index:99999;pointer-events:none';document.body.append(b)}''')
  return ctx,page
 try:
  ctx,page=mount();check('Original UI login works with browser storage forbidden')
  def nav(n):return page.locator('.sidebar button[title="'+n+'"]')
  def ready():page.wait_for_selector('main > .native-grid[aria-busy="false"]');page.wait_for_timeout(180)
  nav('create_project').click();page.wait_for_selector('.project-wizard');check('Configured ProjectCreateWdg opens stepped wizard',page.locator('.wizard-steps li').count()==4)
  page.get_by_label('Название',exact=True).fill('Проект 015 / мастер');page.get_by_label('Код проекта',exact=False).fill(prefix);page.get_by_label('Описание',exact=True).fill('Создан через исходную команду TACTIC')
  page.get_by_role('button',name='Далее',exact=True).click();page.wait_for_selector('.wizard-sources');check('Source step exposes stock choices',page.locator('.wizard-source').count()==2)
  page.get_by_role('button',name='Назад',exact=True).click();check('Back keeps typed project details',page.get_by_label('Код проекта',exact=False).input_value()==prefix)
  page.get_by_role('button',name='Далее',exact=True).click();page.get_by_role('button',name='Проверить',exact=True).click();page.wait_for_selector('.wizard-review');check('Review does not create project',prefix not in {x['code'] for x in call('GET','/projects')['items']})
  check('Review shows genuine non-atomic DDL warning','обратим' in page.locator('.wizard-review').inner_text())
  page.screenshot(path=str(out/'screenshots/project-wizard-review.png'))
  count=sum(x['path'].endswith('/project-create') and x['method']=='POST' for x in paths)
  page.get_by_role('button',name='Создать проект',exact=True).click();page.wait_for_function('(code)=>document.querySelector("select[aria-label=Проект]")?.value===code',arg=prefix,timeout=120000);page.wait_for_selector('.welcome');check('Creation switches to real new project',page.get_by_label('Проект',exact=True).input_value()==prefix)
  check('Created project has native sidebar and no creation error',page.locator('.sidebar .nav-item').count()>0 and page.locator('.global-error').count()==0)
  if a.bridge:check('Project route updated to correct path',page.evaluate('window.__projectRoute')=='/tactic/'+prefix+'/');check('One wizard submit sends one create command',sum(x['path'].endswith('/project-create') and x['method']=='POST' for x in paths)==count+1)
  response=s.get(a.url+'/tactic/'+prefix+'/',headers={'Accept':'text/html'},timeout=60);check('Direct created-project HTTP URL serves Vue shell',response.status_code==200 and '/tactic-ui/app.js' in response.text)
  page.screenshot(path=str(out/'screenshots/new-project-sidebar.png'))
  page.get_by_label('Проект',exact=True).select_option('admin');page.wait_for_selector('.sidebar button[title="global_admin"]');page.wait_for_timeout(300)
  if nav('global_admin').get_attribute('aria-expanded')!='true':nav('global_admin').click()
  nav('users').click();ready();check('Ordinary table has no duplicate large title',page.locator('main > .view-heading').count()==0)
  check('Original table column headers remain',page.locator('main > .native-grid thead th').count()>3)
  grid=page.locator('main > .native-grid');shelf=grid.locator(':scope > .table-commandbar')
  def menu(trigger,*items):
   shelf.get_by_role('button',name=trigger,exact=True).click();page.wait_for_selector('.table-command-menu')
   for text in items:page.locator('.table-command-menu').get_by_role('menuitem',name=text,exact=True).click()
  menu('Вид таблицы','Плотность');page.locator('.table-command-menu').get_by_role('menuitemradio',name='Компактная',exact=True).click();check('Density changed through compact menu',grid.locator(':scope.density-compact').count()==1)
  menu('Вид таблицы');page.locator('.table-command-menu').get_by_role('menuitemcheckbox',name='Перенос текста',exact=True).click();check('Wrap retained as live table option',grid.locator(':scope.wrap-cells').count()==1)
  resizer=page.get_by_role('separator',name='Ширина First Name');resizer.scroll_into_view_if_needed();box=resizer.bounding_box();page.mouse.move(box['x']+2,box['y']+8);page.mouse.down();page.mouse.move(box['x']+100,box['y']+8,steps=5);page.mouse.up();width=resizer.locator('..').bounding_box()['width'];check('Column resized',width>160)
  menu('Вид таблицы','Колонки…');page.get_by_label('Найти колонку',exact=True).fill('first_name');page.get_by_role('button',name='Закрепить First Name',exact=True).click();page.get_by_role('button',name='Закрыть выбор колонок',exact=True).click()
  shelf.get_by_role('button',name='Поиск',exact=False).click();page.get_by_label('Поле быстрого фильтра').select_option('login');page.get_by_label('Значение быстрого фильтра').fill('grid_');page.get_by_role('button',name='Добавить фильтр',exact=True).click();ready();check('Original search filters actual records',page.locator('main > .native-grid tr[data-key]').count()==2)
  grid.locator('thead th').filter(has=page.get_by_role('separator',name='Ширина First Name')).locator('.grid-column-heading > button').first.click();ready()
  page.get_by_label('Свернуть поиск').click();page.get_by_label('Переключить тему').click();check('Theme switched',page.locator('html').get_attribute('data-theme')=='dark')
  # Give debounce one opportunity, then logout must flush remaining channels.
  page.wait_for_timeout(650);page.screenshot(path=str(out/'screenshots/compact-table-db-state.png'));page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card')
  geometry=state('geometry',target)['value'];query=state('query',target)['value'];workspace=state('workspace')['value'];navigation=state('navigation')['value']
  check('Geometry recorded in original database',geometry['density']=='compact' and geometry['wrap'] and 'first_name' in geometry['pinned'])
  check('Column width recorded, not only styled',abs(geometry['widths']['first_name']-width)<4)
  check('Search, sorting, quick input saved together',query['filters'][0]['value']=='grid_' and query['quickText']=='grid_' and query['sort']['field']=='first_name' and not query['search_open'])
  check('Open workspace and sidebar folders saved',workspace['active']==target and navigation['folders']['admin_views/global_admin'])
  check('Theme recorded in original database',state('appearance')['value']['theme']=='dark')
  ctx.close();ctx,page=mount();ready();check('Fresh browser automatically restores active table',page.locator('.workspace-tab.active').inner_text().startswith('Users'))
  check('Fresh browser restores server query results',page.locator('main > .native-grid tr[data-key]').count()==2)
  grid=page.locator('main > .native-grid');check('Fresh browser restores density, wrap, pin',grid.locator(':scope.density-compact.wrap-cells').count()==1 and page.get_by_role('separator',name='Ширина First Name').locator('..').get_attribute('class').find('pinned-column')>=0)
  check('Fresh browser restores width',abs(page.get_by_role('separator',name='Ширина First Name').locator('..').bounding_box()['width']-width)<4)
  check('Fresh browser restores theme and sidebar expansion',page.locator('html').get_attribute('data-theme')=='dark' and nav('global_admin').get_attribute('aria-expanded')=='true')
  check('No browser storage compatibility shim used',page.evaluate('()=>{try{window.localStorage;return false}catch(e){return e.message.includes("forbidden")}}'))
  check('No JS runtime errors',not errors)
  report['created_project']=prefix;report['passed']=True;page.screenshot(path=str(out/'screenshots/restored-from-database.png'));ctx.close()
 except Exception as exc:
  report['error']=str(exc)
  import traceback;traceback.print_exc()
  try:page.screenshot(path=str(out/'screenshots/failure.png'));(out/'failure.txt').write_text(page.locator('body').inner_text())
  except Exception:pass
 finally:
  report['javascript_errors']=errors;report['request_count']=len(paths);(out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');browser.close()
if not report['passed']:raise SystemExit(1)
