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
parser=argparse.ArgumentParser();parser.add_argument('--bridge',action='store_true');parser.add_argument('--url',default='http://127.0.0.1:9147');parser.add_argument('--chromium',default='/usr/bin/chromium');parser.add_argument('--output',default=str(ROOT/'docs/native-ui/0.5/browser-05'))
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
  page.on('dialog',lambda d:d.accept())
  def ready(selector):page.wait_for_selector(selector);page.wait_for_timeout(180)
  def nav(name):return page.locator('.sidebar button[title="'+name+'"]')
  def no_errors():assert not page.locator('.error:visible').all_text_contents(),page.locator('.error:visible').all_text_contents()
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();ready('.fixture-banner')
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Original admin hierarchy survives new widget handlers')
  page.locator('.project-picker select').select_option('fixture');ready('.sidebar button[title=configured_messages]');nav('configured_messages').click();ready('.message-list-item');assert page.locator('.message-list select').count()==1;passed('SubscriptionWdg from XML mounts native center with configured category')
  page.locator('.message-list-item').filter(has=page.locator('.message-code',has_text=re.compile('^pair$'))).click();ready('.message-detail-head');assert page.get_by_role('button',name='Отписаться',exact=True).count()==0;passed('Configured show_unsubscribe=false changes the available action')
  # Header bar and configured widget are the same native message component.
  page.get_by_label('Закрыть сообщения',exact=True).click();page.get_by_label('Открыть сообщения',exact=True).click();ready('.message-backdrop');panel=page.locator('.message-backdrop');ready('.message-backdrop .message-list-item');assert not panel.locator('.message-code',has_text=re.compile('^(private|foreign)$')).count();passed('Global inbox contains only accessible subscription channels')
  pair=panel.locator('.message-list-item').filter(has=page.locator('.message-code',has_text=re.compile('^pair$')));pair.click();ready('.message-backdrop .message-event');assert panel.locator('.message-event').filter(has_text='Repeated TEST message').count()==2;passed('Repeated message text is retained as separate history events')
  before=panel.locator('.message-event:not(.latest-state)').count();panel.get_by_role('button',name='Загрузить предыдущие сообщения',exact=True).click();page.wait_for_function("document.querySelectorAll('.message-backdrop .message-event:not(.latest-state)').length>50");passed('History keyset paging appends earlier records without replacing new ones')
  text='Browser 0.5 · <img src=x onerror="window.bad=1"> · Привет'
  panel.locator('.message-compose textarea').fill(text);panel.get_by_role('button',name='Отправить сообщение',exact=True).click();page.wait_for_function("(t)=>document.querySelector('.message-history').textContent.includes(t)",arg=text);assert text in panel.locator('.message-history').inner_text();assert page.evaluate('window.bad') is None;assert panel.locator('.message-history img').count()==0;passed('Sent Unicode/markup persists as escaped data, never as executable HTML')
  panel.get_by_role('button',name='Отметить показанное',exact=True).click();page.wait_for_timeout(350);assert pair.locator('.message-badge').count()==0;assert 'не подтверждение прочтения' in panel.inner_text();passed('Explicit acknowledgment clears own badge without a false read receipt')
  panel.locator('.message-participants>summary').click();assert 'bob' in panel.locator('.message-participants').inner_text();passed('Participant information uses actual subscriptions and last_cleared')
  page.screenshot(path=str(out/'screenshots/message-history.png'))
  panel.get_by_label('Закрыть сообщения',exact=True).click();page.get_by_label('Открыть сообщения',exact=True).click();ready('.message-backdrop .message-list-item');panel=page.locator('.message-backdrop');panel.locator('.message-list-item').filter(has=page.locator('.message-code',has_text=re.compile('^pair$'))).click();ready('.message-detail-head');assert text in panel.locator('.message-history').inner_text();passed('Messages survive closing and reopening the native widget')
  panel.get_by_role('button',name='Новая переписка',exact=True).click();ready('.chat-user-results label');panel.locator('.chat-user-results label').filter(has_text='TEST bob').locator('input').check();panel.locator('.chat-user-results label').filter(has_text='TEST carol').locator('input').check();panel.get_by_role('button',name='Открыть переписку',exact=True).click();page.wait_for_function("document.querySelector('.message-detail-head code')?.textContent==='group'");passed('Full selected participant set reuses group chat rather than pair chat')
  panel.get_by_role('button',name='Новая переписка',exact=True).click();ready('.chat-user-results label');panel.locator('.chat-user-results label').filter(has_text='TEST bob').locator('input').uncheck();panel.locator('.chat-user-results label').filter(has_text='TEST carol').locator('input').uncheck();panel.locator('.chat-user-results label').filter(has_text='TEST outsider').locator('input').check();panel.get_by_role('button',name='Открыть переписку',exact=True).click();page.wait_for_selector('.chat-create',state='detached');ready('.message-detail-head');newcode=panel.locator('.message-detail-head code').inner_text();assert newcode not in ('pair','group','legacy');passed('New conversation is created via extracted ChatCmd')
  panel.get_by_role('button',name='Отписаться',exact=True).click();page.wait_for_selector('.message-detail-head',state='detached');panel.locator('.message-code',has_text=newcode).wait_for(state='detached');assert not panel.locator('.message-code',has_text=newcode).count();passed('Unsubscribing removes own channel without deleting its messages')
  panel.locator('.message-list-item').filter(has=page.locator('.message-code',has_text=re.compile('^event$'))).click();ready('.message-changes');assert 'not executed' in panel.locator('.message-changes').inner_text();assert panel.locator('.message-compose').count()==0;passed('Structured SObject event renders changes and cannot be overwritten as chat')
  panel.locator('.message-list-item').filter(has=page.locator('.message-code',has_text=re.compile('^progress$'))).click();ready('.message-content progress');assert panel.locator('progress').get_attribute('value')=='45';passed('Original progress message category is projected as bounded progress')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'screenshots/messages-mobile.png'));assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Message layout remains within a narrow mobile viewport');page.set_viewport_size({'width':1540,'height':980})
  panel.get_by_label('Закрыть сообщения',exact=True).click();page.wait_for_selector('.message-backdrop',state='detached');count=len(called);page.wait_for_timeout(5300);assert not any('/messages?' in x or '/message-history?' in x for x in called[count:]);passed('Polling stops when the last message widget is unmounted')
  nav('my_notification').click();ready('tbody tr');assert page.locator('tbody tr').count()==1;assert 'to: fixture' in page.locator('tbody').inner_text();assert 'TEST email 1' in page.locator('tbody').inner_text();assert page.evaluate('window.bad') is None;passed('My Notifications original config displays only recipient/project-scoped email log')
  page.screenshot(path=str(out/'screenshots/my-notifications.png'))
  nav('fixture_items').click();ready('tbody tr');page.locator('tbody tr').filter(has_text='Atlas').click(button='right');page.get_by_role('menuitem',name='Открыть запись / файлы / связи',exact=True).click();ready('.inspector');page.locator('.inspector').get_by_role('button',name='Подписка',exact=True).click();ready('.subscription-panel');page.get_by_role('button',name='Подписаться на объект',exact=True).click();page.get_by_role('button',name='Отписаться от объекта',exact=True).wait_for();passed('Object subscription stores original SObject message key')
  page.get_by_role('button',name='Открыть события',exact=True).click();ready('.message-backdrop .message-detail-head');assert 'ещё не было событий' in page.locator('.message-backdrop').inner_text();passed('Subscription before first event is an explicit empty state, not fake data')
  page.get_by_label('Закрыть сообщения',exact=True).click();page.get_by_role('button',name='Отписаться от объекта',exact=True).click();page.get_by_role('button',name='Подписаться на объект',exact=True).wait_for();page.locator('.inspector > header > button').click()
  nav('schedule').click();ready('tbody tr');assert page.locator('tbody tr').count()==50;page.get_by_role('button',name='Gantt / календарь',exact=True).click();ready('.timeline');page.locator('.timeline input[type=date]').nth(0).fill('2026-09-01');page.locator('.timeline input[type=date]').nth(1).fill('2026-09-30');page.wait_for_function("document.querySelectorAll('.gantt-row').length===200");assert page.locator('.gantt-bar').count()==400;passed('Gantt loads 200 date-window records independently of 50-row table page')
  assert 'из 320' in page.locator('.timeline-count').inner_text();page.get_by_role('button',name='Загрузить ещё 200 объектов',exact=True).click();page.wait_for_function("document.querySelectorAll('.gantt-row').length===320");assert page.locator('.gantt-bar').count()==640;passed('More data appends remaining objects and both configured plan/actual bars')
  page.screenshot(path=str(out/'screenshots/server-window-gantt.png'))
  page.locator('.timeline input[type=date]').nth(0).fill('2027-01-01');page.locator('.timeline input[type=date]').nth(1).fill('2027-01-31');page.wait_for_function("document.querySelector('.timeline-count')?.textContent.includes('из 0')");assert page.locator('.gantt-row').count()==0;passed('Changing period removes stale table-page tasks outside the window')
  page.get_by_role('button',name='Календарь',exact=True).click();page.locator('.timeline input[type=month]').fill('2026-09');page.wait_for_function("document.querySelectorAll('.calendar-day button').length>200");assert page.locator('.calendar-day').count()==42;passed('Calendar fetches its 42-day grid instead of reusing table pagination')
  page.get_by_role('button',name='Gantt',exact=True).click();page.locator('.timeline input[type=date]').nth(0).fill('2026-09-01');page.locator('.timeline input[type=date]').nth(1).fill('2026-09-30');page.wait_for_function("document.querySelectorAll('.gantt-row').length===200")
  page.locator('.advanced-filter>summary').click();root=page.locator('.advanced-filter>.filter-group');root.get_by_role('button',name='+ Условие',exact=True).click();clause=root.locator('.filter-clause');clause.get_by_label('Поле условия').select_option('status');clause.get_by_label('Оператор условия').select_option('eq');clause.get_by_label('Значение условия').fill('Complete');page.get_by_role('button',name='Применить составной поиск',exact=True).click();page.wait_for_function("document.querySelectorAll('.gantt-row').length===160");assert 'из 160' in page.locator('.timeline-count').inner_text();passed('Configured query predicates refresh both timeline and table semantics')
  no_errors();assert not errors,errors;assert not any('get_widget' in path for path in called);passed('All new screens use native JSON contracts without legacy HTML or JS exceptions')
  page.get_by_role('button',name='Выйти',exact=True).click();ready('.login-card');passed('Logout unmounts data widgets and invalidates browser session')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'test_backend':'original XML + production new services on synthetic SQLite tables; not full TACTIC DB','transport':'Python HTTP bridge; URL/storage/history test shims' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
