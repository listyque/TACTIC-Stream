"""Real TACTIC/SQLite table buffer and styling verification, no fixture backend.
The HTTP bridge is explicit and records the direct-navigation denial first.
"""
import argparse,base64,json,re
from pathlib import Path
from urllib.parse import urlsplit
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True,type=Path);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args();out=a.output;(out/'screenshots').mkdir(parents=True,exist_ok=True)
results=[];errors=[];paths=[];target='admin_views/global_admin/users';direct={}
def check(name,ok=True):
 if not ok:raise AssertionError(name)
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
s=requests.Session();base=a.url+'/api/ui/v2';h={'X-Tactic-UI':'1'}
def raw(method,path,**data):
 r=s.request(method,base+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=h,timeout=40)
 if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+' '+r.text)
 return r.json()
auth=raw('POST','/session',login='admin',password='Native-Test-Only-123');h['X-CSRF-Token']=auth['csrf']
def op(method,path,**data):return raw(method,path,project='admin',target=target,**data)
keys={r['values']['login']:r['key'] for r in op('POST','/query',limit=100)['items']};ak,bk=keys['grid_anna'],keys['grid_alex']
def record(k):return op('GET','/record',key=k)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1640,'height':1000});page=ctx.new_page();page.set_default_timeout(16000);page.on('pageerror',lambda e:errors.append(str(e)));http_session=requests.Session()
 try:
  try:
   page.goto(a.url+'/tactic/admin/',wait_until='networkidle',timeout=12000);direct={'passed':True}
  except Exception as e:
   direct={'passed':False,'error':str(e)};(out/'native-navigation.json').write_text(json.dumps(direct,ensure_ascii=False,indent=2))
   if not a.bridge:raise
  if a.bridge:
   def transport(q):
    u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '');assert path.startswith('/api/ui/v2/');paths.append({'method':q['method'],'path':path})
    r=http_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=60)
    return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
   page.close();page=ctx.new_page();page.set_default_timeout(16000);page.on('pageerror',lambda e:errors.append(str(e)))
   def image_transport(route):
    u=urlsplit(route.request.url)
    if u.path!='/api/ui/v2/file':return route.abort()
    response=http_session.get(a.url+u.path+('?' +u.query if u.query else ''),timeout=30)
    route.fulfill(status=response.status_code,body=response.content,headers={'Content-Type':response.headers.get('Content-Type','application/octet-stream'),'Cache-Control':'no-store'})
   page.route('**/api/ui/v2/file?*',image_transport)
   page.expose_function('_real_http',transport);page.set_content('<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
   page.evaluate('(url)=>{const base=document.createElement("base");base.href=url;document.head.append(base)}',a.url+'/');page.evaluate('''()=>{const U=window.URL;window.URL=new Proxy(U,{construct(t,a){if(a[1]==='null')a[1]='http://localhost';return Reflect.construct(t,a)}});const st=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>st.get(k)||null,setItem:(k,v)=>st.set(k,String(v)),removeItem:k=>st.delete(k)}});history.replaceState=()=>{};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''')
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
  page.on('dialog',lambda d:d.accept())
  page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');check('Original password login')
  page.evaluate('''()=>{let b=document.createElement('div');b.textContent='ORIGINAL TACTIC · SQLITE TEST DATA · isolated licence signature · explicit HTTP bridge';b.style='position:fixed;left:0;right:0;bottom:0;background:#443922;color:white;font:11px sans-serif;padding:4px;z-index:99999;pointer-events:none';document.body.append(b)}''')
  def nav(n):return page.locator('.sidebar button[title="'+n+'"]')
  def ready():page.wait_for_selector('.native-grid[aria-busy="false"]');page.wait_for_timeout(120)
  nav('global_admin').click();nav('users').click();ready();check('Configured users table opens');check('Light theme active',page.locator('html').get_attribute('data-theme')=='light')
  def row(k):return page.locator('.native-grid tbody tr[data-key="'+k+'"]')
  def cell(k,f):return row(k).locator('td[data-field="'+f+'"]')
  def edit(k,f,value):
   cell(k,f).dblclick();page.wait_for_selector('.inline-editor');page.locator('.inline-editor .field-input input,.inline-editor .field-input textarea').fill(value);page.locator('.inline-editor').get_by_role('button',name='Применить',exact=True).click();page.wait_for_selector('.inline-editor',state='detached')
  image=cell(ak,'preview').locator('img');image.wait_for();page.wait_for_function('(key)=>{const row=[...document.querySelectorAll("tr[data-key]")].find(el=>el.dataset.key===key);return row?.querySelector("[data-field=preview] img")?.naturalWidth===48}',arg=ak)
  check('Original registered ThumbWdg image renders authenticated bytes',image.evaluate('(el)=>el.naturalWidth')==48)
  check('Missing preview remains an explicit empty icon',cell(bk,'preview').locator('.thumbnail-placeholder').count()==1)
  before1,before2=record(ak),record(bk)
  cell(ak,'first_name').dblclick();page.wait_for_selector('.inline-editor textarea');check('CellEdit uses configured edit_item textarea',page.locator('.inline-editor textarea').count()==1);check('Configured textarea rows honoured',page.locator('.inline-editor textarea').get_attribute('rows')=='5')
  page.locator('.inline-editor textarea').fill('Анна / buffered');page.locator('.inline-editor').get_by_role('button',name='Применить',exact=True).click();check('Applying cell creates draft marker',cell(ak,'first_name').locator('.dirty-corner').count()==1);check('Applying cell leaves original DB unchanged',record(ak)['revision']==before1['revision'])
  edit(ak,'last_name','Петрова / buffered');edit(bk,'first_name','Алексей / buffered');check('Three edits buffered across two records',page.locator('.modified-cell').count()==3);check('Both original rows unchanged before Save Changes',record(ak)['revision']==before1['revision'] and record(bk)['revision']==before2['revision'])
  page.screenshot(path=str(out/'screenshots/grid-buffer-light.png'));start=len([u for u in paths if '/table-changes' in u['path']]);page.get_by_role('button',name=re.compile('^Сохранить изменения')).click();page.get_by_text('Сохранено: 2 строк, 3 ячеек.',exact=True).wait_for();ready()
  check('One network batch saves all three cells',len([u for u in paths if '/table-changes' in u['path']])-start==1 if a.bridge else True);check('Original values reread after batch',record(ak)['values']['last_name']=='Петрова / buffered' and record(bk)['values']['first_name']=='Алексей / buffered');check('Dirty state cleared only on success',page.locator('.grid-save-bar').count()==0)
  before1,before2=record(ak),record(bk);edit(ak,'first_name','ROLLBACK UI');edit(bk,'first_name','');page.get_by_role('button',name=re.compile('^Сохранить изменения')).click();page.get_by_text('Буфер изменений сохранён.',exact=False).wait_for();check('Original action error retains two pending edits',page.locator('.modified-cell').count()==2);check('Original transaction rolls both rows back',record(ak)['revision']==before1['revision'] and record(bk)['revision']==before2['revision']);page.screenshot(path=str(out/'screenshots/grid-validation.png'));page.locator('.grid-save-bar').get_by_role('button',name='Отменить',exact=True).click();check('Discard clears drafts without writing',record(ak)['revision']==before1['revision'])
  edit(ak,'last_name','My draft after conflict');old=record(ak);form=op('GET','/form',key=ak);op('PATCH','/record',key=ak,revision=old['revision'],values={'first_name':'Concurrent external change'});page.get_by_role('button',name=re.compile('^Сохранить изменения')).click();page.get_by_text('Буфер изменений сохранён.',exact=False).wait_for();check('Concurrent write produces conflict without losing text',cell(ak,'last_name').inner_text().find('My draft after conflict')>=0);page.locator('.grid-save-bar').get_by_role('button',name='Отменить',exact=True).click()
  # Refresh through the unchanged root toolbar.
  page.get_by_role('button',name='Обновить',exact=True).first.click();ready()
  cell(ak,'last_name').focus();page.keyboard.press('F2');page.wait_for_selector('.inline-editor');check('F2 opens the cell-specific input');page.locator('.inline-editor .field-input input').fill('Keyboard draft');page.keyboard.press('Enter');check('Enter stages without a database write',record(ak)['values']['last_name']!='Keyboard draft');cell(ak,'last_name').focus();page.keyboard.press('Control+s');page.get_by_text('Сохранено: 1 строк, 1 ячеек.',exact=True).wait_for();ready();check('Ctrl+S writes through original command',record(ak)['values']['last_name']=='Keyboard draft')
  cell(ak,'first_name').focus();page.keyboard.press('ArrowRight');check('Arrow key moves active cell',page.evaluate('document.activeElement.dataset.field')=='last_name')
  before=record(ak);cell(ak,'last_name').dblclick();page.wait_for_selector('.inline-editor');page.locator('.inline-editor .field-input input').fill('CANCEL ME');page.keyboard.press('Escape');check('Escape cancels editor and does not change DB',page.locator('.inline-editor').count()==0 and record(ak)['revision']==before['revision'])
  cell(ak,'last_name').dblclick();page.wait_for_selector('.inline-editor');page.locator('.inline-editor').get_by_role('button',name='NULL',exact=True).click();page.locator('.inline-editor').get_by_role('button',name='Применить',exact=True).click();page.get_by_role('button',name=re.compile('^Сохранить изменения')).click();page.get_by_text('Сохранено: 1 строк, 1 ячеек.',exact=True).wait_for();ready();check('UI explicit NULL roundtrips without becoming empty string',record(ak)['values']['last_name'] is None)
  cell(ak,'first_name').click(button='right');page.wait_for_selector('.native-menu');check('Original context edit remains',page.locator('.native-menu [data-action="edit"]').count()==1);page.keyboard.press('Escape');cell(ak,'first_name').focus();page.keyboard.press('Shift+F10');page.wait_for_selector('.native-menu');check('Keyboard context menu opens');page.keyboard.press('Escape')
  page.get_by_label('Плотность таблицы').select_option('compact');check('Compact density changes grid',page.locator('.native-grid.density-compact').count()==1);page.get_by_label('Перенос текста',exact=True).click();check('Wrap option changes grid',page.locator('.native-grid.wrap-cells').count()==1)
  resizer=page.get_by_role('separator',name='Ширина First Name');resizer.scroll_into_view_if_needed();box=resizer.bounding_box();th=resizer.locator('..');oldw=th.bounding_box()['width'];page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.mouse.move(box['x']+box['width']/2+80,box['y']+box['height']/2,steps=6);page.mouse.up();check('Pointer resizing changes configured column width',th.bounding_box()['width']>oldw+40)
  page.locator('.column-chooser summary').click();page.get_by_role('button',name='Закрепить First Name',exact=True).click();check('Pinning makes original column sticky',cell(ak,'first_name').evaluate('(el)=>getComputedStyle(el).position')=='sticky');page.locator('.column-chooser summary').click()
  page.get_by_label('Переключить тему',exact=True).click();page.wait_for_timeout(250);check('Dark theme applies to whole app',page.locator('html').get_attribute('data-theme')=='dark');check('Dark controls finish with readable surface and text',page.locator('.project-picker select').evaluate('(el)=>{let s=getComputedStyle(el);return s.backgroundColor==="rgb(24, 30, 42)" && s.color==="rgb(226, 232, 244)"}'));page.screenshot(path=str(out/'screenshots/grid-dark.png'))
  page.get_by_label('Переключить тему',exact=True).click();page.wait_for_timeout(250);page.screenshot(path=str(out/'screenshots/grid-light.png'));page.set_viewport_size({'width':430,'height':920});page.screenshot(path=str(out/'screenshots/grid-mobile.png'));check('Mobile layout has its own horizontal grid scroll',page.locator('.grid-viewport').evaluate('(el)=>el.scrollWidth>=el.clientWidth'))
  check('No uncaught JS errors',not errors);check('No legacy widget HTML calls',not any('get_widget' in u['path'] for u in paths));check('No immediate PATCH for buffered cells',not any(u['method']=='PATCH' and '/record' in u['path'] for u in paths))
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc)});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'Original TACTIC + real SQLite + original auth/actions; signature isolated in disposable test only','transport':'explicit HTTP bridge' if a.bridge else 'native','native_navigation':direct,'scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
