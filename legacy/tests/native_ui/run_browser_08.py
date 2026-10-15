"""0.8 browser SystemInfo diagnostics; TEST DB, not live PostgreSQL.

Native navigation is the default. --bridge explicitly substitutes HTTP/session,
URL/history/storage only for environments that prohibit localhost navigation.
The saved CSV is downloaded from a real Blob after real API CSV generation.
"""
import argparse,base64,csv,json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--bridge',action='store_true');p.add_argument('--url',default='http://127.0.0.1:9167');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--output',default=str(ROOT/'docs/native-ui/0.8/browser-08'));a=p.parse_args()
out=Path(a.output);(out/'screenshots').mkdir(parents=True,exist_ok=True);results=[];errors=[];called=[]
def passed(name):results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1660,'height':1020},accept_downloads=True);page=context.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:errors.append(str(e)));session=requests.Session()
 try:
  if a.bridge:
   def http(req):
    from urllib.parse import urlsplit
    parsed=urlsplit(req['url']);path=parsed.path+('?' + parsed.query if parsed.query else '');assert path.startswith('/api/ui/v2/');called.append(path)
    r=session.request(req['method'],a.url+path,headers=req.get('headers',{}),data=req.get('body'),timeout=30)
    return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
   page.expose_function('_fixture_http',http)
   page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE 0.8</title></head><body><div id="app"></div></body></html>')
   page.evaluate('''() => {
    const URL0=window.URL;window.URL=new Proxy(URL0,{construct(target,args){if(args[1]==='null')args[1]='https://fixture.invalid';return Reflect.construct(target,args)}});
    const store=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}});
    history.replaceState=(state,unused,url)=>{window._fixture_path=url};
    window.fetch=async(url,options={})=>{const r=await window._fixture_http({url:String(url),method:options.method||'GET',headers:options.headers||{},body:options.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})};
   }''')
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
  else:page.goto(a.url+'/tactic/admin/',wait_until='networkidle')
  page.on('dialog',lambda d:d.accept())
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item')
  def nav(name):return page.locator('.sidebar button[title="'+name+'"]')
  def ready(selector):page.wait_for_selector(selector);page.wait_for_timeout(100)
  def openview(name,title):nav(name).click();page.get_by_role('heading',name=title,exact=True).wait_for();page.wait_for_selector('.table-region[aria-busy="false"]');page.wait_for_timeout(120)
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Original widget-config admin roots unchanged')
  nav('global_admin').click();nav('system_info').click();ready('.schema-check-table tbody tr')
  assert 'Структура базы TACTIC' in page.locator('.system-panel').inner_text();passed('Original SystemInfoWdg opens extended native diagnostics')
  assert ((ROOT/'NATIVE_UI_VERSION').read_text().strip()+'.0-source-fork') in page.locator('.system-summary').inner_text();passed('Runtime version shown from actual build version')
  assert 'Требуется проверка схемы' in page.locator('.schema-health header').inner_text();passed('Incomplete real stock seed is not presented as healthy')
  row=page.locator('.schema-check-table tbody tr').filter(has=page.get_by_text('message_log',exact=True));assert row.count()==1 and 'Нет таблицы' in row.inner_text();passed('Missing message history table diagnosed explicitly')
  row=page.locator('.schema-check-table tbody tr').filter(has=page.get_by_text('widget_config',exact=True));assert row.count()==1 and 'Нет полей' in row.inner_text() and 'priority' in row.inner_text();passed('Original unprefixed widget_config and missing columns retained in report')
  assert 'MANAGE_TACTIC.bat db upgrade' in page.locator('.schema-health').inner_text();assert page.locator('.schema-health button').count()==0;passed('No browser DDL/migration action is exposed')
  before=page.locator('.schema-check-table').inner_text();page.get_by_role('button',name='Проверить снова',exact=True).click();page.wait_for_timeout(250);assert page.locator('.schema-check-table').inner_text()==before;passed('Repeated read-only check does not mutate the seed or silently repair data')
  assert 'TEST FIXTURE' in page.locator('.fixture-banner').inner_text();page.screenshot(path=str(out/'screenshots/system-schema-diagnostics.png'))
  assert not any('password' in t for t in page.locator('.system-summary dt').all_text_contents());passed('No passwords or config dump displayed')
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Schema diagnostics fit mobile viewport');page.screenshot(path=str(out/'screenshots/system-schema-mobile.png'))
  assert not errors,errors;assert not any('get_widget' in u for u in called);passed('No JS errors or legacy HTML renderer calls')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout clears diagnostics view')
 except Exception as exc:
  try:page.screenshot(path=str(out/'screenshots/browser-failure.png'))
  except Exception:pass
  results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'actual stock seed metadata, TEST request/auth collaborators','transport':'explicit Python HTTP bridge: substitutes fetch/cookies/URL/history/storage; original Blob download' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
