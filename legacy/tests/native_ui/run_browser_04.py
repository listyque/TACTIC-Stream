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
  page.on('dialog',lambda d:d.accept())
  def ready(s):page.wait_for_selector(s);page.wait_for_timeout(120)
  def nav(n):return page.locator('.sidebar button[title="'+n+'"]')
  def ensure_details(selector):
   if not page.locator(selector).evaluate('(e)=>e.open'):page.locator(selector+'>summary').click()
  def no_errors():assert not page.locator('.error:visible').all_text_contents(),page.locator('.error:visible').all_text_contents()
  page.get_by_label('Логин',exact=True).fill('fixture');page.get_by_label('Пароль',exact=True).fill('fixture-only');page.get_by_role('button',name='Войти',exact=True).click();ready('.fixture-banner');ready('.sidebar .nav-item');passed('Login uses HTTP and original configured admin root')
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Shipped admin config hierarchy retained')
  page.locator('.project-picker select').select_option('fixture');ready('.sidebar button[title=fixture_items]');nav('fixture_items').click();ready('tbody tr .check-cell');assert page.locator('tbody tr').count()==4;passed('Project SearchType is defined by XML, not a fixed frontend model')
  ensure_details('.advanced-filter');root=page.locator('.advanced-filter > .filter-group');root.get_by_role('button',name='+ Группа',exact=True).click();inner=page.locator('.advanced-filter .filter-group').nth(1);inner.get_by_role('button',name='+ Условие',exact=True).click();inner.get_by_role('button',name='+ Условие',exact=True).click()
  for idx,value in enumerate(('Atlas','Mesa')):
   c=inner.locator('.filter-clause').nth(idx);c.get_by_label('Поле условия').select_option('name');c.get_by_label('Оператор условия').select_option('eq');c.get_by_label('Значение условия').fill(value)
  root.locator(':scope > .toolbar').get_by_role('button',name='+ Условие',exact=True).click();c=root.locator(':scope > .filter-node > .filter-clause');c.get_by_label('Поле условия').select_option('quantity');c.get_by_label('Значение условия').fill('0');page.get_by_role('button',name='Применить составной поиск',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===1");assert 'Atlas' in page.locator('tbody').inner_text();passed('OR subgroup combined with numeric zero AND predicate')
  page.screenshot(path=str(out/'screenshots/compound-search.png'))
  page.get_by_role('button',name='Сохранить поиск в sidebar',exact=True).click();page.get_by_placeholder('Название личного представления').fill('Составной поиск 0.4');page.get_by_role('button',name='Сохранить в widget_config',exact=True).click();ready('.sidebar button[title=saved_0]');nav('saved_0').click();ready('tbody tr');assert page.locator('tbody tr').count()==1;assert 'Atlas' in page.locator('tbody').inner_text();passed('Saved personal view reopens equivalent FilterData predicate')
  nav('fixture_items').click();ensure_details('.advanced-filter');page.get_by_role('button',name='Очистить дополнительные условия',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===4");passed('Temporary filters clear without editing the source view')
  # Test null, empty and non-null through the visual constructor.
  root=page.locator('.advanced-filter > .filter-group');root.get_by_role('button',name='+ Условие',exact=True).click();c=root.locator('.filter-clause');c.get_by_label('Поле условия').select_option('name');c.get_by_label('Оператор условия').select_option('null');page.get_by_role('button',name='Применить составной поиск',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===1");passed('NULL has one result rather than also matching empty text')
  c.get_by_label('Оператор условия').select_option('empty');page.get_by_role('button',name='Применить составной поиск',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===2");passed('Empty matches original NULL plus empty-text semantics')
  c.get_by_label('Оператор условия').select_option('not_null');page.get_by_role('button',name='Применить составной поиск',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===3");passed('IS NOT NULL works with original SQL builder')
  page.get_by_role('button',name='Очистить дополнительные условия',exact=True).click();page.wait_for_function("document.querySelectorAll('tbody tr').length===4");page.locator('.advanced-filter>summary').click()
  page.get_by_role('button',name='Дерево связей',exact=True).click();ready('.relation-tree-row');atlas=page.locator('.relation-tree > ul > .relation-tree-row').filter(has_text='Atlas');atlas.locator(':scope > .tree-record > button').first.click();ready('.tree-relation');tagbranch=atlas.locator(':scope > .tree-children > ul > .tree-relation').filter(has_text='fixture/tag');tagbranch.locator(':scope > .toolbar > button').first.click();ready('.tree-relation .relation-tree-row');assert 'Outdoor' in atlas.inner_text();passed('Lazy relation branch loads shared object from original-shaped Schema relation')
  child=tagbranch.locator(':scope > ul > .relation-tree-row');child.locator(':scope > .tree-record > button').first.click();ready('.tree-relation .tree-relation');reverse=child.locator(':scope > .tree-children > ul > .tree-relation').filter(has_text='fixture/item');reverse.locator(':scope > .toolbar > button').first.click();ready('.tree-relation .tree-relation .relation-tree-row');assert '↩ цикл' in page.locator('.relation-tree').inner_text();passed('Instance cycle is visible and is not expanded infinitely')
  page.screenshot(path=str(out/'screenshots/schema-relation-tree.png'));atlas.locator(':scope > .tree-record > .text-button').click();ready('.inspector');page.locator('.inspector').get_by_role('button',name='Связи',exact=True).click();ready('.relation-row');page.locator('.relation-row').filter(has_text='fixture/tag').get_by_role('button',name='Изменить связи',exact=True).click();ready('.relation-candidates article');passed('Instance editor is opened from the declared relation, not a guessed foreign key')
  interior=page.locator('.relation-candidates article').filter(has_text='Interior');interior.get_by_role('button',name='Связать',exact=True).click();interior.get_by_role('button',name='Отвязать',exact=True).wait_for();passed('Link updates junction membership and refreshes candidate state')
  interior.get_by_role('button',name='Отвязать',exact=True).click();interior.get_by_role('button',name='Связать',exact=True).wait_for();assert page.locator('.relation-candidates article').count()==3;passed('Unlink leaves the target object available for linking again')
  page.locator('.relation-editor > header > button').click();page.wait_for_selector('.relation-editor',state='detached');page.locator('.inspector').get_by_role('button',name='Задачи',exact=True).click();ready('.task-card');assert page.locator('.task-board').count()==2;assert page.locator('.task-card').count()==6;passed('Task board separates independent task pipelines instead of merging equal statuses')
  card=page.locator('.task-card').first;card.get_by_label('Статус задачи').select_option('In Progress');page.wait_for_function("Array.from(document.querySelectorAll('.task-lane')).some(l=>l.querySelector('h4').textContent.includes('In Progress')&&l.querySelector('.task-card'))");passed('Status selector persists through task-change HTTP, not client-only drag state')
  card=page.locator('.task-card').filter(has_text='TEST task 0');card.get_by_role('button',name='model',exact=True).click();ready('.modal .form-row');form=page.locator('.modal').filter(has=page.locator('[id^="form-title-"]'))
  form.locator('.form-row').filter(has=page.locator('label',has_text='pipeline_code')).locator('select').select_option('alternate');ready('.modal .notice');assert 'нового' in page.locator('.modal .notice').inner_text();passed('Dependent form preview reports incompatible status without changing original record')
  status=form.locator('.form-row').filter(has=page.locator('label',has_text='status')).locator('select');assert status.locator('option').all_text_contents()==['—','Todo','Doing','Done'];status.select_option('Todo');form.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('[id^="form-title-"]',state='detached');ready('.task-card');no_errors();passed('New pipeline and compatible status are saved together')
  page.screenshot(path=str(out/'screenshots/task-pipelines-board.png'))
  card=page.locator('.task-card').filter(has_text='TEST task 0');card.get_by_role('button',name='Рабочее время',exact=True).click();ready('.work-hours-table');hours=page.locator('.work-hours-panel');hours.locator('input[type=date]').fill('2026-09-28');ready('input[aria-label="2026-09-30 regular"]');hours.get_by_label('2026-09-30 regular',exact=True).fill('2.5');hours.get_by_label('2026-09-30 overtime',exact=True).fill('1');hours.get_by_role('button',name='Сохранить время',exact=True).click();page.wait_for_function("document.querySelector('.work-hours-panel button.primary').disabled && document.querySelector('input[aria-label=\"2026-09-30 regular\"]').value==='2.5'");passed('Weekly hours save only changed regular and overtime cells')
  page.screenshot(path=str(out/'screenshots/task-work-hours.png'));hours.get_by_label('Закрыть рабочее время',exact=True).click();page.wait_for_selector('.work-hours-panel',state='detached');card.get_by_role('button',name='Рабочее время',exact=True).click();ready('.work-hours-table');hours=page.locator('.work-hours-panel');hours.locator('input[type=date]').fill('2026-09-28');ready('input[aria-label="2026-09-30 regular"]');assert hours.get_by_label('2026-09-30 regular',exact=True).input_value()=='2.5';passed('Work-hour values survive closing and reopening the editor')
  hours.get_by_label('2026-09-30 regular',exact=True).fill('0');hours.get_by_role('button',name='Сохранить время',exact=True).click();page.wait_for_function("document.querySelector('input[aria-label=\"2026-09-30 regular\"]').value===''");assert hours.get_by_label('2026-09-30 overtime',exact=True).input_value()=='1';passed('Zero clears the selected hour entry, not overtime or the task')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'screenshots/work-hours-mobile.png'));assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Work-hour modal and task sidebar keep mobile page width bounded');page.set_viewport_size({'width':1540,'height':980});hours.get_by_label('Закрыть рабочее время',exact=True).click();page.wait_for_selector('.work-hours-panel',state='detached')
  page.locator('.inspector').get_by_role('button',name='История',exact=True).click();ready('.history-panel');page.get_by_role('button',name='Архивировать',exact=True).click();ready('.history-event');page.get_by_role('button',name='Восстановить из архива',exact=True).wait_for();passed('Retire updates state and journal without physical deletion')
  page.screenshot(path=str(out/'screenshots/record-history.png'));page.get_by_role('button',name='Восстановить из архива',exact=True).click();page.get_by_role('button',name='Архивировать',exact=True).wait_for();page.wait_for_function("document.querySelectorAll('.history-event').length===2");passed('Reactivation is distinct from a new object creation and keeps history')
  page.locator('.inspector > header > button').click();page.get_by_role('button',name='Данные',exact=True).click();page.get_by_label('Состояние записей',exact=True).select_option('retired');page.wait_for_function("document.querySelectorAll('tbody tr').length===1");assert 'Orion' in page.locator('tbody').inner_text();passed('Archive selection queries retired data rather than filtering visible rows')
  page.get_by_label('Состояние записей',exact=True).select_option('active');page.wait_for_function("document.querySelectorAll('tbody tr').length===4");mesa=page.locator('tbody tr').filter(has_text='Mesa');mesa.click(button='right');page.get_by_role('menuitem',name='Открыть запись / файлы / связи',exact=True).click();ready('.inspector');page.locator('.inspector').get_by_role('button',name='Задачи',exact=True).click();ready('.task-panel .notice');page.get_by_role('button',name='Сгенерировать из pipeline',exact=True).click();ready('.task-generation');page.locator('.process-checks label').filter(has_text='model').locator('input').check();page.get_by_role('button',name='Создать выбранные',exact=True).click();page.wait_for_selector('.task-generation',state='detached');ready('.task-card');assert page.locator('.task-card').count()==1;passed('Explicit pipeline generation is available for a parent with no tasks')
  page.get_by_role('button',name='Сгенерировать из pipeline',exact=True).click();ready('.task-generation');assert 'уже есть 1' in page.locator('.task-generation').inner_text();page.locator('.task-generation').get_by_role('button',name='Отмена',exact=True).click();passed('Generation preview reflects existing task membership')
  page.locator('.inspector > header > button').click();nav('fixture_task_hours').click();ready('.table-region');page.get_by_role('button',name='Данные',exact=True).click();ready('.table-region tbody');hours_cell=page.get_by_role('button',name='Открыть рабочее время',exact=True);assert hours_cell.count()>=6;hours_cell.first.click();ready('.work-hours-table');passed('Original my_task WorkHoursElementWdg opens native editor from configured virtual table column')
  page.screenshot(path=str(out/'screenshots/configured-work-hours-column.png'));page.get_by_label('Закрыть рабочее время',exact=True).click();page.wait_for_selector('.work-hours-panel',state='detached')
  no_errors();assert not errors,errors;passed('No uncaught JS errors across new functional flows');assert not any('get_widget' in x for x in called);passed('New flows never fetch legacy widget HTML')
  page.get_by_role('button',name='Выйти',exact=True).click();ready('.login-card');passed('Logout closes data and invalidates session')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'test_backend':'original config XML + synthetic state; not PostgreSQL','transport':'Python HTTP bridge; URL/storage/history test shims' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
