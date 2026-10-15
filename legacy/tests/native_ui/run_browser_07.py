"""0.7 browser config/cells/audit/CSV contracts; TEST DB, not live PostgreSQL.

Native navigation is the default. --bridge explicitly substitutes HTTP/session,
URL/history/storage only for environments that prohibit localhost navigation.
The saved CSV is downloaded from a real Blob after real API CSV generation.
"""
import argparse,base64,csv,json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--bridge',action='store_true');p.add_argument('--url',default='http://127.0.0.1:9167');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--output',default=str(ROOT/'docs/native-ui/0.7/browser-07'));a=p.parse_args()
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
   page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE 0.7</title></head><body><div id="app"></div></body></html>')
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
  def first(name):return page.locator('tbody tr').first.locator('td[data-field="'+name+'"]')
  top=page.locator('.nav-section').first.locator(':scope > ul > li > button').evaluate_all('(ns)=>ns.map(n=>n.title)');assert top==['create_project','global_admin','project_admin','project_essentials'];passed('Original configured admin roots unchanged')
  page.get_by_label('Проект',exact=True).select_option('fixture');nav('formatted').wait_for();openview('formatted','TEST · Форматы и итоги')
  assert page.locator('tbody tr').count()==20 and '235 записей' in page.locator('.pager').inner_text();passed('Original search_limit selects 20 of 235 records')
  assert first('code').inner_text()=='ROW0234';passed('Multi-column configured sorting reaches browser unchanged')
  assert first('amount').inner_text()=='1468.57' and first('ratio').inner_text()=='12.50%';passed('Original number and percent formats render separately from raw data')
  assert first('timestamp').inner_text()=='01/10/2026';passed('Original date/timezone options format browser cell')
  assert first('approved').locator('input').is_disabled() and not first('approved').locator('input').is_checked();passed('Checkbox is safe typed display, not legacy injected HTML')
  assert first('alias').inner_text()==first('name').inner_text();passed('Simple widget column alias displays its source field')
  assert 'Не перенесено' in first('column.custom').inner_text();passed('Dotted unknown widget remains visible with explicit unsupported state')
  assert 'Total:' in page.locator('tfoot').inner_text() and 'Avg:' in page.locator('tfoot').inner_text();passed('Page totals and average from original Search appear in table footer')
  assert 'TEST FIXTURE' in page.locator('.fixture-banner').inner_text();page.screenshot(path=str(out/'screenshots/configured-formats.png'))
  page.get_by_role('button',name='Источник колонок',exact=True).click();ready('.config-layers li');assert page.locator('.config-layers li').count()==3;passed('Inspector shows resolved personal/project/custom-column layers')
  page.locator('.audit-fields button').filter(has=page.locator('code',has_text='amount')).click();assert 'tactic.ui.table.FormatElementWdg' in page.locator('.audit-definition').inner_text();assert 'total_summary' in page.locator('.config-audit pre').last.inner_text();passed('Selected field exposes real handler options and provenance')
  page.screenshot(path=str(out/'screenshots/config-provenance.png'))
  page.locator('.audit-fields button').filter(has=page.locator('code',has_text='column.custom')).click();assert 'Не перенесён' in page.locator('.audit-definition').inner_text();passed('Config inspector distinguishes unimplemented custom renderer')
  page.get_by_label('Закрыть проверку конфигурации').click();page.wait_for_selector('.config-audit',state='detached')
  page.get_by_role('button',name='Карточки',exact=True).click();ready('.entity-card');assert page.locator('.entity-card').count()==20 and '12.50%' in page.locator('.entity-card').first.inner_text();passed('Cards reuse same configured cells rather than independent data formatter')
  page.get_by_role('button',name='Таблица',exact=True).click();ready('tbody tr')
  openview('inline','TEST · Inline-конфигурация');assert [v.strip() for v in page.locator('thead th button').all_text_contents()]==['Имя из inline','Целая сумма','Код'];passed('Inline XML replaces order/title and inherits omitted field definitions')
  assert first('amount').inner_text()=='1469';passed('Inline display options override inherited numeric format')
  openview('code_view','TEST · config_code');assert page.locator('thead th button').count()==1 and 'Из config_code' in page.locator('thead').inner_text();passed('config_code resolves its own stored view without default merge')
  openview('compact','TEST · Настройки таблицы');assert page.locator('thead').count()==0 and page.locator('td.check-cell').count()==0;passed('Configured header and selection flags honored')
  assert page.locator('.table-tools').count()==0 and page.locator('.query-toolbar').count()==0 and page.locator('.advanced-filter').count()==0;passed('Configured shelf and search disabled without rewriting sidebar')
  page.locator('tbody tr').first.click(button='right');assert page.locator('.context-menu').count()==0;passed('Original show_context_menu none disables custom right-click menu')
  assert page.locator('.pager button').count()==0;passed('Original search-limit controls flag honored')
  openview('formatted','TEST · Форматы и итоги');page.get_by_role('button',name='Экспорт CSV',exact=True).click();ready('.csv-export')
  custom=page.locator('.export-columns input[value="column.custom"]');assert not custom.is_checked();passed('CSV defaults exclude unimplemented widget, but retain explicit choice')
  def columns(names):
   inputs=page.locator('.export-columns input');
   for x in inputs.all():x.set_checked(x.get_attribute('value') in names)
  def download(name):
   with page.expect_download(timeout=15000) as event:page.get_by_role('button',name='Скачать CSV',exact=True).click()
   f=out/(name+'.csv');event.value.save_as(str(f));page.locator('.csv-export .success').wait_for();return list(csv.reader(f.open(encoding='utf-8-sig',newline='')))
  columns(['code','name','amount','ratio','timestamp']);data=download('configured-display');assert len(data)==236 and data[1][0]=='ROW0234';passed('Browser downloads 235 server matches, not just table page')
  assert data[1][2:] == ['1468.57','12.50%','01/10/2026'];passed('Displayed CSV values use same widget formatting as cells')
  assert next(r for r in data[1:] if r[0]=='ROW0000')[1].startswith("'=HYPERLINK");passed('CSV download protects formula-leading text')
  page.screenshot(path=str(out/'screenshots/csv-configured.png'))
  columns(['amount','ratio']);page.get_by_label('Значения экспорта').select_option('raw');data=download('configured-raw');assert data[1]==['1468.567','0.125'];passed('Raw CSV mode preserves unrounded database values')
  page.get_by_label('Закрыть экспорт').click();page.wait_for_selector('.csv-export',state='detached')
  page.locator('tbody tr td.check-cell input').nth(0).check();page.locator('tbody tr td.check-cell input').nth(2).check();page.get_by_role('button',name='Экспорт CSV',exact=True).click();ready('.csv-export');assert page.get_by_label('Выборка экспорта').input_value()=='selected';columns(['code']);data=download('configured-selected');assert [r[0] for r in data[1:]]==['ROW0234','ROW0230'];passed('Selected CSV applies same original sort, not click order')
  columns(['column.custom']);page.get_by_role('button',name='Скачать CSV',exact=True).click();page.locator('.csv-export .error').wait_for();assert 'Не перенесён' in page.locator('.csv-export .error').inner_text();passed('Unsupported widget export fails explicitly and leaves current table intact')
  page.get_by_label('Закрыть экспорт').click();page.wait_for_selector('.csv-export',state='detached');assert first('code').inner_text()=='ROW0234';passed('CSV errors do not mutate data or current selection')
  openview('filtered','TEST · Сохранённый фильтр');assert '118 записей' in page.locator('.pager').inner_text();page.get_by_role('button',name='Экспорт CSV',exact=True).click();ready('.csv-export');columns(['code','department']);data=download('configured-filtered');assert len(data)==119 and all(r[1]=='A' for r in data[1:]);passed('Saved original filter remains active in browser export')
  page.get_by_label('Закрыть экспорт').click();page.get_by_role('button',name='Источник колонок',exact=True).click();ready('.config-layers');page.set_viewport_size({'width':390,'height':844});assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Resolved-view modal fits mobile viewport');page.screenshot(path=str(out/'screenshots/config-mobile.png'))
  page.get_by_label('Закрыть проверку конфигурации').click();assert not errors,errors;assert not any('get_widget' in u for u in called);passed('No uncaught JS or legacy get_widget calls in new paths')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout closes configuration/export state')
 except Exception as exc:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'real config/Select/format/CSV with TEST schema and auth','transport':'explicit Python HTTP bridge: substitutes fetch/cookies/URL/history/storage; original Blob download' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
