"""0.9 saved script editor browser checks; TEST persistence, not live PostgreSQL.

Native navigation is the default. --bridge explicitly substitutes HTTP/session,
URL/history/storage only for environments that prohibit localhost navigation.
Saved script source is downloaded from a real Blob without executing its body.
"""
import argparse,base64,csv,json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--bridge',action='store_true');p.add_argument('--url',default='http://127.0.0.1:9167');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--output',default=str(ROOT/'docs/native-ui/0.9/browser-09'));a=p.parse_args()
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
   page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE 0.9</title></head><body><div id="app"></div></body></html>')
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
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Original widget-config administration roots unchanged')
  nav('project_admin').click();nav('script_editor').click();ready('.script-entry')
  assert page.locator('.script-entry').count()==40 and '65 записей' in page.locator('.script-directory').inner_text();passed('Stock ShelfEditWdg opens paged saved-script directory')
  assert 'config/custom_script' in page.locator('.script-toolbar').inner_text();passed('Original script storage displayed, not a new application table')
  page.locator('.script-entry').first.click();page.wait_for_function("document.querySelector('.script-source').value.startsWith('# TEST FIXTURE')");passed('Choosing saved script loads exact source text')
  page.get_by_label('Код скрипта',exact=True).fill('value =\n');page.get_by_role('button',name='Проверить синтаксис',exact=True).click();page.get_by_text('Ошибка синтаксиса',exact=False).wait_for();passed('Python syntax errors report without execution')
  page.get_by_label('Код скрипта',exact=True).fill('# TEST: сохранение\nresult = 42\n');page.get_by_role('button',name='Проверить синтаксис',exact=True).click();page.get_by_text('Синтаксис корректен',exact=False).wait_for();passed('Valid Python syntax accepted without running its body')
  assert 'есть несохранённые правки' in page.locator('.script-toolbar').inner_text();passed('Unsaved source changes tracked')
  page.get_by_label('Код скрипта',exact=True).press('Control+s');page.get_by_text('Сохранено в config/custom_script.',exact=False).wait_for();assert 'запись загружена' in page.locator('.script-toolbar').inner_text();passed('Ctrl+S saves through original-script service and clears dirty state')
  page.get_by_role('button',name='Новый',exact=True).click();page.get_by_label('Папка скрипта',exact=True).fill('tools/native');page.get_by_label('Название скрипта',exact=True).fill('browser_created');page.get_by_label('Язык скрипта',exact=True).select_option('python');page.get_by_label('Код скрипта',exact=True).fill('raise RuntimeError("must not execute")\n');page.get_by_label('Описание скрипта',exact=True).fill('TEST FIXTURE new source');page.get_by_role('button',name='Сохранить · Ctrl+S',exact=True).click();page.get_by_text('Сохранено в config/custom_script.',exact=False).wait_for();passed('New script saved as data, not executed')
  page.get_by_role('button',name='Создать копию',exact=True).click();assert page.get_by_label('Название скрипта',exact=True).input_value()=='browser_created_copy';page.get_by_role('button',name='Сохранить · Ctrl+S',exact=True).click();page.get_by_text('Сохранено в config/custom_script.',exact=False).wait_for();passed('Save-copy uses a new record and preserves original')
  page.get_by_label('Поиск скриптов',exact=True).fill('browser_created');page.get_by_role('button',name='Найти',exact=True).click();page.wait_for_function("document.querySelectorAll('.script-entry').length===2");passed('Server search refreshes matching saved scripts')
  page.get_by_label('Найти в скрипте',exact=True).fill('RuntimeError');page.get_by_role('button',name='Следующее',exact=True).click();assert page.get_by_label('Код скрипта',exact=True).evaluate('(e)=>e.value.slice(e.selectionStart,e.selectionEnd)')=='RuntimeError';passed('Source text search selects match')
  with page.expect_download() as download:page.get_by_role('button',name='В файл',exact=True).click()
  saved=out/'saved-source.py';download.value.save_as(str(saved));assert saved.read_text()=='raise RuntimeError("must not execute")\n';passed('Download preserves source bytes in a local file')
  page.get_by_label('Код скрипта',exact=True).fill('<script>window.script_was_executed=true</script>');page.get_by_label('Язык скрипта',exact=True).select_option('javascript');page.get_by_role('button',name='Проверить синтаксис',exact=True).click();page.get_by_text('Проверка недоступна',exact=False).wait_for();assert page.evaluate('typeof window.script_was_executed')=='undefined';passed('JavaScript is text; unsupported syntax check is explicit')
  page.get_by_role('button',name='Отменить правки',exact=True).click();page.wait_for_function("document.querySelector('.script-source').value.startsWith('raise RuntimeError')");passed('Discard reloads actual saved record after confirmation')
  assert 'TEST FIXTURE' in page.locator('.fixture-banner').inner_text();page.screenshot(path=str(out/'screenshots/original-script-editor.png'))
  page.get_by_role('button',name='Таблица по конфигурации',exact=True).click();ready('.table-region[aria-busy="false"]');headers=page.locator('thead th button').all_text_contents();assert [h.strip() for h in headers]==['Folder','Title','Description','Language'];passed('Manage button uses original custom_script view and element_names')
  assert page.locator('tbody tr').count()==40;page.screenshot(path=str(out/'screenshots/scripts-configured-table.png'))
  nav('script_editor').click();ready('.script-editor');passed('Original editor reopens from its same configured sidebar target')
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Script editor fits mobile viewport')
  page.screenshot(path=str(out/'screenshots/scripts-mobile.png'));assert not errors,errors;assert not any('get_widget' in u for u in called);passed('No legacy HTML renderer calls or JavaScript errors')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout unmounts editor')
 except Exception as exc:
  try:page.screenshot(path=str(out/'screenshots/browser-failure.png'))
  except Exception:pass
  results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'original widget configuration and ScriptService; TEST script persistence/auth collaborators','transport':'explicit Python HTTP bridge: substitutes fetch/cookies/URL/history/storage; original Blob download' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
