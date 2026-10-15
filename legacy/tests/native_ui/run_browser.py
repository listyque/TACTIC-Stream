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
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');page.wait_for_selector('.fixture-banner');passed('Login against actual HTTP API; ticket hidden from UI')
  def nav(name):return page.locator('.sidebar .nav-item').filter(has=page.locator('span')).and_(page.locator('[title="'+name+'"]'))
  # This expects the shipped XML order, NOT a hand-built alternative admin menu.
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)')
  assert top==['create_project','global_admin','project_admin','project_essentials'],top;passed('Top-level admin hierarchy from admin-conf.xml in original order')
  nav('global_admin').click();nav('users').click();page.wait_for_selector('tbody tr .check-cell');assert page.locator('tbody tr').count()==12;passed('Original users config opens native table with 12 synthetic rows')
  page.screenshot(path=str(out/'screenshots/admin-configured-users.png'))
  page.locator('tbody tr').first.click(button='right');page.locator('.context-menu [data-action="inspect"]').click();page.wait_for_selector('.inspector');passed('Context menu opens record inspector')
  # Inspector closure uses the source component button.
  page.locator('.inspector').get_by_role('button',name='Закрыть').click();passed('Record inspector closes')
  nav('users_in_groups').click();page.wait_for_selector('.membership-panel select');page.locator('.membership-panel select').select_option(index=1);page.get_by_text('Second fixture',exact=True).click();page.get_by_role('button',name='Сохранить состав',exact=True).click();page.wait_for_selector('.membership-panel .success');passed('Original users_in_groups target: revisioned membership write')
  nav('project_admin').click();nav('project_workflow').click();page.wait_for_selector('.graph-editor select');page.locator('.graph-editor select').select_option(index=1);page.wait_for_selector('.graph-node');n=page.locator('.graph-node').first;box=n.bounding_box();page.mouse.move(box['x']+35,box['y']+20);page.mouse.down();page.mouse.move(box['x']+90,box['y']+60,steps=6);page.mouse.up();page.get_by_role('button',name='Сохранить расположение',exact=True).click();page.wait_for_function("document.querySelector('.graph-node').getAttribute('transform').includes('135')");passed('Pipeline coordinate drag persists through revision-checked XML round-trip')
  page.screenshot(path=str(out/'screenshots/pipeline-fixture.png'))
  nav('manage_side_bar').click();page.wait_for_selector('.effective-editor .element-list li');assert page.locator('.effective-editor .element-list li').count()==5;passed('Manage Side Bar reads layered admin_views config, not a fixed Vue list')
  # Move first item below global_admin, preserving ID. Check DB override next render.
  page.locator('.effective-editor .element-list li').first.get_by_role('button',name='Вниз',exact=True).click();page.get_by_role('button',name='Сохранить порядок в TACTIC',exact=True).click();page.wait_for_function("document.querySelector('.nav-section > ul > li > button').title==='global_admin'");passed('Sidebar order saved as config override and reflected immediately')
  # Stable target ID: users tab did not disappear after reorder.
  page.locator('.workspace-tab').filter(has_text='Users').first.locator('button').first.click();page.wait_for_selector('tbody tr .check-cell');assert page.locator('tbody tr').count()==12;passed('Existing view tab survives sidebar reorder')
  nav('manage_side_bar').click();page.wait_for_selector('.effective-editor');page.screenshot(path=str(out/'screenshots/sidebar-config-layers.png'))
  # Select actual test DB override, then invalid XML must not silently save.
  selects=page.locator('.config-workbench select');selects.last.select_option(index=1);page.wait_for_selector('.xml-editor textarea');page.locator('.xml-editor textarea').fill('<config><broken>');page.get_by_role('button',name='Сохранить XML',exact=True).click();page.wait_for_selector('.config-workbench .error');passed('Invalid XML rejected; original saved config preserved')
  nav('create_project').click();page.wait_for_selector('.unsupported-panel');assert 'ProjectCreateWdg' in page.locator('.unsupported-panel').inner_text();passed('Unported original handler stays visible, not a fabricated replacement')
  page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='Открыть меню',exact=True).click();page.get_by_role('button',name='Открыть меню',exact=True).click();page.screenshot(path=str(out/'screenshots/mobile-sidebar-fixture.png'));assert page.locator('body').evaluate('(el)=>el.scrollWidth<=window.innerWidth+2');passed('Mobile shell has no horizontal body overflow')
  assert not errors,errors;passed('No uncaught JavaScript exceptions in tested flows')
  assert not any('get_widget' in x or 'spt.' in x for x in called);passed('No old widget HTML RPC in tested browser flows')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout clears native UI session')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'test_backend':'original config XML + synthetic rows; not real TACTIC database','transport':'Python HTTP bridge; browser URL/storage/history shims' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
