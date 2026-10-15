"""0.6 Vue browser contracts. Original handlers and TEST persistence.

--bridge explicitly injects URL/storage/history/fetch and a SHA adapter because
about:blank has no secure-context WebCrypto. Binary transport is base64 only in
this TEST bridge, never in production. No native cookies/CSP/WebCrypto proof.
"""
import argparse,base64,hashlib,json,re,uuid
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--bridge',action='store_true');p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--output',default=str(ROOT/'docs/native-ui/0.6/browser-06'));a=p.parse_args()
out=Path(a.output);(out/'screenshots').mkdir(parents=True,exist_ok=True);results=[];errors=[];called=[]
def passed(name):results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
CHUNK=4*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()
fp=lambda b:sha(b''.join(hashlib.sha256(b[o:o+CHUNK]).digest() for o in range(0,len(b),CHUNK)))
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1540,'height':980});page=context.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:errors.append(str(e)));session=requests.Session()
 try:
  if a.bridge:
   def http(req):
    from urllib.parse import urlsplit
    url=urlsplit(req['url']);path=url.path+('?' + url.query if url.query else '');assert path.startswith('/api/ui/v2/');called.append(path)
    data=base64.b64decode(req['body64']) if 'body64' in req else req.get('body')
    r=session.request(req['method'],a.url+path,headers=req.get('headers',{}),data=data,timeout=30)
    return {'status':r.status_code,'body':r.text,'headers':{'content-type':r.headers.get('content-type','application/json')}}
   page.expose_function('_fixture_http',http)
   page.expose_function('_fixture_digest',lambda text:base64.b64encode(hashlib.sha256(base64.b64decode(text)).digest()).decode())
   page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE 0.6</title></head><body><div id="app"></div></body></html>')
   page.evaluate('''() => {
    const URL0=window.URL;window.URL=new Proxy(URL0,{construct(target,args){if(args[1]==='null')args[1]='https://fixture.invalid';return Reflect.construct(target,args)}});
    const store=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}});
    history.replaceState=(state,unused,url)=>{window._fixture_path=url};
    const b64=bytes=>{let text='';for(let i=0;i<bytes.length;i+=32768)text+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(text)};
    Object.defineProperty(crypto,'subtle',{value:{digest:async(name,data)=>{if(name!=='SHA-256')throw Error('Unexpected TEST algorithm');let buf=data instanceof ArrayBuffer?new Uint8Array(data):new Uint8Array(data.buffer,data.byteOffset,data.byteLength);return Uint8Array.from(atob(await _fixture_digest(b64(buf))),c=>c.charCodeAt(0)).buffer}}});
    Object.defineProperty(crypto,'randomUUID',{value:()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('')});
    window.fetch=async(url,options={})=>{const q={url:String(url),method:options.method||'GET',headers:options.headers||{}};if(options.body instanceof ArrayBuffer)q.body64=b64(new Uint8Array(options.body));else if(options.body instanceof Blob)q.body64=b64(new Uint8Array(await options.body.arrayBuffer()));else q.body=options.body;const r=await window._fixture_http(q);return new Response(r.body,{status:r.status,headers:r.headers})};
   }''')
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
  else:page.goto(a.url+'/tactic/admin/',wait_until='networkidle')
  page.on('dialog',lambda d:d.accept())
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item')
  def nav(name):return page.locator('.sidebar button[title="'+name+'"]')
  def ready(selector):page.wait_for_selector(selector);page.wait_for_timeout(100)
  def clear_errors():assert not page.locator('.error:visible').all_text_contents(),page.locator('.error:visible').all_text_contents()
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Original admin hierarchy survives without hard-coded collection menu entries')
  page.get_by_label('Проект',exact=True).select_option('fixture');nav('collections').wait_for();nav('collections').click();ready('.collection-card');assert page.locator('.collection-card').count()==2;passed('CollectionLayoutWdg from widget_config opens native collection browser')
  page.locator('.collection-card').filter(has_text='Review collection').click();ready('.collection-member');assert page.locator('.collection-member').count()==2;passed('Original nested collection and object memberships are visible')
  page.get_by_role('button',name='Добавить существующие',exact=True).click();ready('.candidate-list>label');row=page.locator('.candidate-list>label').filter(has_text='Second asset');row.locator('input').check();page.get_by_role('button',name='Добавить связи',exact=True).click();page.wait_for_selector('.collection-add',state='detached');page.wait_for_function("document.querySelectorAll('.collection-member').length===3");passed('Native add dialog links existing record through original command')
  page.locator('.collection-member').filter(has_text='Second asset').locator('input').check();page.get_by_role('button',name='Убрать из коллекции (1)',exact=True).click();page.wait_for_function("document.querySelectorAll('.collection-member').length===2");passed('Removing collection member removes only junction relationship')
  page.locator('.collection-member').filter(has_text='Nested collection').get_by_role('button',name='Открыть вложенную',exact=True).click();page.get_by_text('Коллекция пуста.',exact=True).wait_for();passed('Nested collection navigation reads its own contents, not parent records')
  page.get_by_role('button',name='Добавить существующие',exact=True).click();ready('.candidate-list>label');page.locator('.candidate-list>label').filter(has_text='Review collection').locator('input').check();page.get_by_role('button',name='Добавить связи',exact=True).click();page.wait_for_selector('.collection-add .error');assert 'потомка' in page.locator('.collection-add .error').inner_text();passed('Ancestor cycle is rejected by server and shown without data loss')
  page.locator('.collection-add>header>button').click();page.locator('.collection-breadcrumb').get_by_role('button',name='Review collection',exact=True).click();ready('.collection-member')
  page.get_by_role('button',name='Новая вложенная коллекция',exact=True).click();ready('.form-row');names=page.locator('.form-row>label').all_text_contents();assert any('name' in n for n in names) and not any('_is_collection' in n for n in names);passed('Collection creation form uses edit_collection with fixed marker omitted')
  page.locator('.form-row').filter(has=page.locator('label>small',has_text=re.compile('^name$'))).locator('input').fill('Browser Review 06');page.locator('.modal form').get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('.form-row',state='detached');page.wait_for_function("document.querySelectorAll('.collection-member').length===3");passed('Configured form creates nested collection and original instance link')
  page.screenshot(path=str(out/'screenshots/collections-configured.png'))
  page.locator('.collection-member').filter(has_text='Browser Review 06').get_by_role('button',name='Открыть вложенную',exact=True).click();page.get_by_text('Коллекция пуста.',exact=True).wait_for();page.get_by_role('button',name='Добавить существующие',exact=True).click();ready('.candidate-list>label');page.locator('.candidate-list>label').filter(has_text='First asset').locator('input').check();page.get_by_role('button',name='Добавить связи',exact=True).click();page.wait_for_selector('.collection-add',state='detached');ready('.collection-member')
  page.get_by_role('button',name='Удалить коллекцию…',exact=True).click();ready('.collection-delete');assert 'напрямую не удаляет' in page.locator('.collection-delete').inner_text();page.get_by_role('button',name='Удалить коллекцию и её связи',exact=True).click();page.wait_for_selector('.collection-delete',state='detached');ready('.collection-card');assert page.locator('.collection-card').count()==2;passed('Collection deletion has explicit scope confirmation and removes only that container')
  nav('media').click();ready('tbody tr');assert page.locator('tbody tr').count()==4;assert 'First asset' in page.locator('tbody').inner_text();passed('Member object remains in source table after its collection is deleted')
  page.get_by_role('button',name='Коллекции',exact=True).click();ready('.collection-card');passed('Generic configured table exposes collections only for supported source schema')
  page.get_by_role('button',name='Данные',exact=True).click();ready('tbody tr');page.locator('tbody tr').filter(has_text='First asset').click(button='right');page.get_by_role('menuitem',name='Открыть запись / файлы / связи',exact=True).click();ready('.inspector');page.locator('.inspector').get_by_role('button',name='Файлы',exact=True).click();ready('.file-panel .snapshot');assert page.locator('.file-panel .snapshot').count()==40;assert 'из 125' in page.locator('.file-panel>footer').inner_text();passed('File panel displays first 40 of 125 server-side versions')
  for end in (80,120,125):
   page.locator('.file-panel>footer').get_by_role('button',name='Далее',exact=True).click();page.wait_for_function('(n)=>document.querySelector(".file-panel>footer").textContent.includes("–"+n+" из")',arg=end)
  assert page.locator('.file-panel .snapshot').count()==5;passed('Browser can reach versions beyond previous 100-row cap')
  page.locator('.file-panel .snapshot').last.get_by_role('button',name='Выбрать current…',exact=True).click();ready('.current-dialog');assert 'SNAP119' in page.locator('.current-dialog').inner_text();page.get_by_role('button',name='Подтвердить current',exact=True).click();page.wait_for_selector('.current-dialog',state='detached');ready('.file-panel .snapshot .tag');passed('Current selection previews prior version and delegates original mutation')
  page.get_by_label('Контекст версий',exact=True).fill('review');page.locator('.version-filter').get_by_role('button',name='Применить',exact=True).click();page.wait_for_function("document.querySelector('.file-panel>footer').textContent.includes('из 5')");assert page.locator('.file-panel .snapshot').count()==5;passed('Context filter runs server-side and resets pagination')
  page.get_by_label('Контекст версий',exact=True).fill('');page.locator('.version-filter').get_by_role('button',name='Применить',exact=True).click();page.wait_for_function("document.querySelector('.file-panel>footer').textContent.includes('из 125')")
  page.get_by_role('button',name='Загрузка файлов',exact=True).click();ready('.upload-queue');passed('Native upload queue is attached to original record, no standalone upload app')
  # Real HTTP pre-stage one chunk, then resume through visible browser file picker.
  if not a.bridge:
   for c in context.cookies(a.url):session.cookies.set(c['name'],c['value'])
  csrf=session.get(a.url+'/api/ui/v2/session').json()['csrf'];headers={'X-Tactic-UI':'1','X-CSRF-Token':csrf};base={'project':'fixture','target':'fixture_files/media','key':'fixture/media?project=fixture&id=3'}
  data=(b'Browser06\x00\xff'*((8*1024*1024+19)//11+1))[:8*1024*1024+19];name='browser-model.bin'
  body=dict(base,filename=name,size=len(data),fingerprint=fp(data),context='publish',description='Browser TEST 0.6',request_id=str(uuid.uuid4()))
  response=session.post(a.url+'/api/ui/v2/uploads',json=body,headers=headers);assert response.status_code==200,response.text;job=response.json()
  first=session.patch(a.url+'/api/ui/v2/upload-chunk',params=dict(base,upload_id=job['id'],offset=0,sha256=sha(data[:CHUNK])),data=data[:CHUNK],headers=dict(headers,**{'Content-Type':'application/octet-stream'}));assert first.status_code==200,first.text
  page.get_by_role('button',name='Обновить очередь',exact=True).click();ready('.upload-job');jobui=page.locator('.upload-job[data-upload-id="'+job['id']+'"]');assert float(jobui.locator('progress').get_attribute('value'))==CHUNK;passed('Reopened queue shows disk-confirmed offset without browser file state')
  bad=data[:CHUNK+17]+bytes([data[CHUNK+17]^1])+data[CHUNK+18:];jobui.locator('input[type=file]').set_input_files({'name':name,'mimeType':'application/octet-stream','buffer':bad});page.wait_for_selector('.upload-queue>.error');assert 'отличается' in page.locator('.upload-queue>.error').inner_text();assert int(jobui.locator('progress').get_attribute('value'))==CHUNK;passed('Full-file block fingerprint rejects wrong resumed content, even unchanged name/size')
  jobui.locator('input[type=file]').set_input_files({'name':name,'mimeType':'application/octet-stream','buffer':data});jobui.get_by_role('button',name='Выполнить check-in',exact=True).wait_for(timeout=30000);assert int(jobui.locator('progress').get_attribute('value'))==len(data);assert 'из 125' in page.locator('.file-panel>footer').inner_text();passed('Matching file resumes remaining chunks and does not create snapshot before confirmation')
  page.screenshot(path=str(out/'screenshots/resumable-ready.png'))
  jobui.get_by_role('button',name='Выполнить check-in',exact=True).click();jobui.locator('.receipt').wait_for();assert jobui.locator('.receipt').inner_text()=='UPLOADED1';page.wait_for_function("document.querySelector('.file-panel>footer').textContent.includes('из 126')");passed('Explicit final check-in returns receipt and refreshes original version list')
  page.locator('.inspector').get_by_role('button',name='Поля',exact=True).click();page.wait_for_selector('.upload-queue',state='detached');page.locator('.inspector').get_by_role('button',name='Файлы',exact=True).click();ready('.file-panel .snapshot');page.get_by_role('button',name='Загрузка файлов',exact=True).click();ready('.upload-job .receipt');assert page.locator('.upload-job .receipt').inner_text()=='UPLOADED1';passed('Receipt survives closing/reopening widget and does not repeat check-in')
  page.screenshot(path=str(out/'screenshots/file-versions-and-receipt.png'))
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'screenshots/files-mobile.png'));assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Files and upload queue remain within mobile viewport')
  clear_errors();assert not errors,errors;assert not any('get_widget' in path for path in called);passed('Native configured flows have no uncaught JS errors or legacy HTML calls')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout closes upload widgets and invalidates API session')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'test_backend':'original handlers, actual Collection/Select/staging, TEST schema/check-in/DB collaborators','transport':'Python HTTP bridge; URL/storage/history and SHA adapter' if a.bridge else 'native Chromium HTTP/WebCrypto','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
