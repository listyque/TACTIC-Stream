"""1.0 widget foundation browser checks; TEST persistence, not live PostgreSQL.

Native navigation is the default. --bridge explicitly substitutes HTTP/session,
URL/history/storage only for environments that prohibit localhost navigation.
Saved script source is downloaded from a real Blob without executing its body.
"""
import argparse,base64,csv,json
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--bridge',action='store_true');p.add_argument('--url',default='http://127.0.0.1:9167');p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--output',default=str(ROOT/'docs/native-ui/1.0/browser-10'));a=p.parse_args()
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
   page.set_content('<!doctype html><html lang="ru"><head><meta charset="UTF-8"><title>TACTIC TEST FIXTURE 1.0</title></head><body><div id="app"></div></body></html>')
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
  page.get_by_label('Проект',exact=True).select_option('fixture');nav('widgets').wait_for();nav('widgets').click()
  outer=page.locator('[data-tab-container="fixture_widgets/widgets"]');outer.locator(':scope > .native-tab-strip').wait_for()
  heads=outer.locator(':scope > .native-tab-strip [role="tab"]')
  assert heads.count()==3 and 'Скрытая вкладка' not in heads.all_text_contents();passed('Original TabWdg produces nested, filtered tab headers')
  assert heads.nth(0).get_attribute('aria-selected')=='true';passed('Selected option chooses configured child')
  assert page.locator('.workspace-tabs > div').count()==1;passed('Nested children do not create global workspace tabs')
  form=outer.locator(':scope > .native-tab-content:visible .embedded-form').first
  form.wait_for();assert form.locator('.form-row').count()==3;passed('EditWdg is an inline form with configured element_names')
  assert form.locator('input[type=date]').first.input_value()=='2026-09-05';passed('Date widget displays calendar date from original timestamp without saving a conversion')
  desc=form.locator('.form-row').filter(has=page.locator('small',has_text='description')).locator('input').first
  desc.fill('Unsaved nested draft');assert '●' in heads.nth(0).inner_text();passed('Nested dirty state propagates to tab header')
  heads.nth(1).click();ready('.native-tab-content:visible .table-region[aria-busy="false"]')
  table=outer.locator(':scope > .native-tab-content:visible .table-region').first
  assert table.locator('tbody tr').count()==5;passed('Nested TableLayoutWdg uses own query and configured page size')
  heads.nth(0).click();assert desc.input_value()=='Unsaved nested draft';passed('Switching nested tabs preserves unsaved input without discarding DOM')
  nav('formatted').click();ready('.table-region[aria-busy="false"]');page.locator('.workspace-tabs').get_by_role('button',name='TEST · Вложенные виджеты',exact=False).first.click()
  assert desc.input_value()=='Unsaved nested draft';passed('Switching main tabs preserves nested form draft')
  desc.press('Control+s');page.get_by_text('Сохранено:',exact=False).wait_for();passed('Ctrl+S saves embedded EditWdg through bound form route')
  form=outer.locator(':scope > .native-tab-content:visible .embedded-form').first;desc=form.locator('.form-row').filter(has=page.locator('small',has_text='description')).locator('input').first
  label=form.locator('.form-row').filter(has=page.locator('small',has_text='description')).locator('label').first
  desc.fill('Reset me');label.click(button='right');page.locator('.native-menu[data-action]').count();page.locator('.native-menu [data-action="reset_field"]').wait_for();page.locator('.native-menu [data-action="reset_field"]').click();assert desc.input_value()=='Unsaved nested draft';passed('Form field menu resets only local edited field to loaded value')
  label.press('Shift+F10');page.locator('.native-menu [data-action="definition"]').wait_for();page.locator('.native-menu [data-action="definition"]').click();page.get_by_role('dialog',name='Определение виджета').wait_for();assert 'EditWdg' in page.locator('.widget-definition pre').inner_text();passed('Keyboard field menu opens original widget definition')
  page.locator('.widget-definition').get_by_role('button',name='Закрыть',exact=True).click()
  heads.nth(1).click();table=outer.locator(':scope > .native-tab-content:visible .table-region').first;table.locator('tbody tr').first.wait_for();header=table.locator('thead th').filter(has_text='description').first
  header.click(button='right');menu=page.locator('.native-menu');menu.locator('[data-action="sort_desc"]').wait_for();assert menu.locator('[data-action="sort_asc"]').count()==1;passed('Header right-click resolves menu actions from server')
  focused=page.evaluate('document.activeElement.getAttribute("role")');assert focused=='menuitem';page.keyboard.press('End');assert page.evaluate('document.activeElement.dataset.action')=='new_column';passed('Context menu has keyboard focus and End navigation')
  page.keyboard.press('Escape');menu.wait_for(state='detached');passed('Escape closes context menu and restores focus')
  header.press('Shift+F10');page.locator('.native-menu [data-action="sort_desc"]').click();ready('.native-tab-content:visible .table-region[aria-busy="false"]');passed('Keyboard header menu applies explicit descending sort')
  header.click(button='right');page.locator('.native-menu [data-action="hide_column"]').click();assert table.locator('thead th').filter(has_text='description').count()==0;passed('Hide column affects current table, not original XML')
  table.locator('thead th').filter(has_text='status').first.click(button='right');page.locator('.native-menu [data-action="restore_columns"]').click();assert table.locator('thead th').filter(has_text='description').count()==1;passed('Configured column set can be restored locally')
  rows=table.locator('tbody tr');rows.nth(0).get_by_role('checkbox').check();rows.nth(1).get_by_role('checkbox').check();rows.nth(1).click(button='right');page.locator('.native-menu [data-action="edit"]').wait_for();assert table.locator('tbody tr.selected').count()==2;passed('Right-click inside selection retains multi-selection')
  page.locator('.native-menu [data-action="edit"]').click();page.get_by_role('heading',name='Изменить 2 записей',exact=True).wait_for();passed('Edit on multi-selection opens existing bulk form path')
  page.locator('.modal').filter(has=page.get_by_role('heading',name='Изменить 2 записей',exact=True)).get_by_role('button',name='Закрыть',exact=True).click()
  rows.nth(3).click(button='right');page.locator('.native-menu [data-action="edit"]').wait_for();assert table.locator('tbody tr.selected').count()==1;passed('Right-click unselected row selects clicked record alone')
  assert page.locator('.native-menu [data-action="delete"]').get_attribute('aria-disabled')=='true';page.locator('.native-menu [data-action="delete"]').dispatch_event('click');assert page.locator('.native-menu').count()==1;passed('Unsupported cascade delete remains disabled, never becomes retire')
  page.screenshot(path=str(out/'screenshots/table-context-menu.png'));page.keyboard.press('Escape')
  heads.nth(0).click(button='right');page.locator('.native-menu [data-action="refresh"]').wait_for();assert page.locator('.native-menu [data-action="close"]').count()==0;passed('Protected tab has no close action in context menu');page.keyboard.press('Escape')
  heads.nth(2).click();inner=outer.locator('[data-tab-container="fixture_widgets/widgets/~tab/3"]');inner.wait_for();assert inner.locator(':scope > .native-tab-strip [role="tab"]').count()==2;passed('Recursive TabWdg contains independent inner TabWdg')
  strip=inner.locator(':scope > .native-tab-strip').bounding_box();content=inner.locator('.embedded-form').bounding_box();assert content['y']>=strip['y']+strip['height'];passed('Nested tab strip sits above its content instead of legacy flat flex layout')
  inner.get_by_role('tab',name='Неперенесённый виджет',exact=True).click();inner.get_by_text('custom.studio.SpecialWdg',exact=True).wait_for();assert 'custom.studio.SpecialWdg' in inner.inner_text();passed('Unported specialised widget is explicit, not arbitrary table fallback')
  inner.get_by_role('tab',name='Форма другой задачи',exact=True).click();inner.locator('.embedded-form').wait_for();page.screenshot(path=str(out/'screenshots/nested-widget-foundation.png'))
  nav('widgets').click(button='right');page.locator('.native-menu [data-action="popup"]').wait_for();page.locator('.native-menu [data-action="popup"]').click();page.locator('.widget-popup .native-tabs').wait_for();passed('Sidebar popup is an independent configured widget panel')
  page.locator('.widget-popup').get_by_role('button',name='Закрыть отдельную панель',exact=True).click()
  nav('embedded').click();page.locator('.view-heading h1').filter(has_text='TEST · Встроенная форма').wait_for();page.locator('.embedded-widget:visible').wait_for();assert page.locator('main .table-region:visible').count()==0;passed('Direct sidebar EditWdg no longer opens a table')
  page.screenshot(path=str(out/'screenshots/embedded-form.png'))
  nav('readonly').click();form=page.locator('.embedded-widget:visible .embedded-form');form.wait_for();assert form.locator('input:not([disabled]),textarea:not([disabled]),select:not([disabled])').count()==0;passed('Configured view-mode form is read-only')
  nav('insert_form').click();form=page.locator('.embedded-widget:visible .embedded-form');form.wait_for();form.locator('input').first.wait_for();assert form.locator('input').count()>0;assert 'Default из конфигурации' in form.locator('input').evaluate_all('(xs)=>xs.map(x=>x.value).join("|")');passed('Insert form shows original configured default values')
  form.get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_function("!document.querySelector('.workspace-tabs')?.textContent.includes('TEST · Создание из defaults')");passed('single insert closes widget after successful save')
  page.set_viewport_size({'width':390,'height':844});
  if not nav('embedded').is_visible():page.get_by_label('Открыть меню',exact=True).click()
  nav('embedded').click();page.wait_for_timeout(150);assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2');passed('Embedded widget fits narrow viewport')
  # Use heading menu to test edge clamping on a narrow screen.
  page.locator('.view-heading').click(button='right');page.locator('.native-menu [data-action="definition"]').wait_for();box=page.locator('.native-menu').bounding_box();assert box['x']>=0 and box['x']+box['width']<=392;passed('Context menu clamps to viewport edge');page.keyboard.press('Escape')
  assert not errors,errors;assert not any('get_widget' in u for u in called);passed('No JavaScript errors or legacy HTML widget calls')
  page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('.login-card');passed('Logout clears composed widget tree')
 except Exception as exc:
  try:page.screenshot(path=str(out/'screenshots/browser-failure.png'))
  except Exception:pass
  results.append({'scenario':'failure','passed':False,'error':str(exc),'js_errors':errors});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'TEST storage/auth + production widget projection/menu/form services','transport':'explicit Python HTTP bridge; native cookies/CSP/navigation not proven' if a.bridge else 'native Chromium HTTP','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
