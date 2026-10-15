"""Browser flows against ORIGINAL TACTIC startup/models and full seed copies.
--bridge only after a recorded navigation denial; original HTTP/auth stays real.
"""
import argparse,base64,json,uuid,re
from pathlib import Path
from urllib.parse import urlsplit
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True,type=Path);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args();out=a.output;(out/'screenshots').mkdir(parents=True,exist_ok=True);results=[];errors=[];paths=[];nonce=uuid.uuid4().hex[:7]
def check(name,ok=True):
 if not ok:raise AssertionError(name)
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1660,'height':1050});page=ctx.new_page();page.set_default_timeout(18000);page.on('pageerror',lambda e:errors.append(str(e)));http_session=requests.Session()
 try:
  if a.bridge:
   def transport(q):
    u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '');assert path.startswith('/api/ui/v2/');paths.append(path)
    r=http_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=60)
    return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
   page.expose_function('_real_http',transport);page.set_content('<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
   page.evaluate('''()=>{const U=window.URL;window.URL=new Proxy(U,{construct(t,a){if(a[1]==='null')a[1]='http://localhost';return Reflect.construct(t,a)}});const st=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>st.get(k)||null,setItem:(k,v)=>st.set(k,String(v)),removeItem:k=>st.delete(k)}});history.replaceState=()=>{};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''')
   web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text())
  else:page.goto(a.url+'/tactic/admin/',wait_until='networkidle')
  page.on('dialog',lambda d:d.accept())
  page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');check('Vue logs in against original DB authentication')
  page.evaluate('''()=>{let b=document.createElement('div');b.textContent='ORIGINAL TACTIC + SQLITE SEED · TEST DATA · подпись лицензии изолирована в тесте · HTTP bridge';b.style='position:fixed;left:0;right:0;bottom:0;background:#53441f;color:#fff;font:12px sans-serif;padding:5px;z-index:99999;pointer-events:none';document.body.append(b)}''')
  def nav(n):return page.locator('.sidebar button[title="'+n+'"]')
  def ready(sel):page.wait_for_selector(sel);page.wait_for_timeout(120)
  def clean():check('No visible error after '+page.locator('.view-heading h1').inner_text(),not any(t.strip() for t in page.locator('.error:visible').all_text_contents()))
  nav('global_admin').click()
  expected={'projects':'.table-region','template_projects':'.table-region','users':'.table-region','groups':'.table-region','users_in_groups':'.membership-panel','global_translations':'.table-region','exception_log':'.table-region','debug_log':'.table-region','wdg_settings':'.table-region','license':'.global-settings .license-info','system_info':'.admin-panel','system_config':'.global-settings-grid','db_resource':'.table-region'}
  for name,selector in expected.items():
   nav(name).click();ready(selector);check('Actual Globals screen renders: '+name,page.locator('.unsupported-panel:visible').count()==0);clean()
  nav('system_config').click();ready('.global-settings-grid');check('All seven original system groups displayed',page.locator('.global-settings-grid fieldset').count()==7)
  thread=page.locator('[id="setting-services/thread_count"]');thread.fill(str(int(thread.input_value() or '8')+1));page.locator('.global-settings').get_by_role('button',name='Сохранить',exact=True).click();page.get_by_text('Файл сохранён с резервной копией.',exact=False).wait_for();check('SystemConfig saves through actual file endpoint');page.screenshot(path=str(out/'screenshots/globals-system-config.png'))
  nav('users').click();ready('.table-region[aria-busy="false"]');page.get_by_role('button',name='Новая запись',exact=True).click();ready('.modal .form-row')
  def field(n):return page.locator('.modal:visible .form-row').filter(has=page.locator('small',has_text=n)).filter(has=page.locator('label small',has_text=n)).locator('input,textarea,select').first
  # Exact technical field names, not coincidental matches in label descriptions.
  def ff(n):return page.locator('.modal:visible .form-row').filter(has=page.locator('label small').filter(has_text=__import__('re').compile('^'+__import__('re').escape(n)+'$'))).locator('.field-input input,.field-input textarea,.field-input select').first
  login='ui_'+nonce;ff('login').fill(login);ff('password').fill('Private-UI-Pass-123');ff('password re-enter').fill('Private-UI-Pass-123');ff('first_name').fill('Original form');page.locator('.modal').get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('.modal-backdrop',state='detached');ready('.table-region[aria-busy="false"]')
  row=page.locator('.table-region tbody tr').filter(has=page.locator('[data-field="login"]',has_text=login));row.wait_for();check('Table creation persists original user and displays new row')
  row.click(button='right');page.locator('.native-menu [data-action="edit"]').click();ready('.modal .form-row');check('Password field is blank on existing user',ff('password').input_value()=='');ff('first_name').fill('Edited UI');page.locator('.modal').get_by_role('button',name='Сохранить',exact=True).click();page.wait_for_selector('.modal-backdrop',state='detached');row.get_by_text('Edited UI',exact=True).wait_for();check('Context edit rereads saved original fields')
  row.locator('[data-field="first_name"]').dblclick();ready('.inline-editor');page.locator('.inline-editor input').fill('Inline original');page.locator('.inline-editor').get_by_role('button',name='Применить',exact=True).click();page.wait_for_selector('.inline-editor',state='detached');page.get_by_role('button',name=re.compile('^Сохранить изменения')).click();page.get_by_text('Сохранено: 1 строк, 1 ячеек.',exact=True).wait_for();row.get_by_text('Inline original',exact=True).wait_for();check('Shared table buffered inline editor uses actual save path')
  page.screenshot(path=str(out/'screenshots/globals-users-table.png'))
  nav('groups').click();ready('.table-region[aria-busy="false"]');group=page.locator('.table-region tbody tr').filter(has=page.locator('[data-field="login_group"]')).first;group.wait_for();group.locator('[data-field="user_assign"] button').click();ready('.modal .membership-panel .member-grid');check('Group cell opens bound original assignment widget');page.locator('.modal.wide > header > button').click();ready('.table-region[aria-busy="false"]');group=page.locator('.table-region tbody tr').filter(has=page.locator('[data-field="login_group"]')).first;group.locator('[data-field="access_rules_hidden"] button').click();ready('.expanded-widget-row .widget-table');check('HiddenRow creates inline configured nested table');nested=page.locator('.expanded-widget-row .widget-table').first;check('Nested table has one shelf, no duplicated wrapper buttons',nested.locator(':scope > .native-grid > .table-commandbar').count()==1 and nested.locator(':scope > .widget-table-heading button').count()==0);check('Nested search initially collapsed',not nested.locator('.table-search-panel').first.is_visible());page.screenshot(path=str(out/'screenshots/globals-group-widgets.png'))
  page.get_by_label('Проект',exact=True).select_option('native11test');ready('.sidebar button[title="project_admin"]');nav('project_admin').click();nav('project_workflow').click();ready('.graph-editor select');check('Project Workflow has an enabled create button',page.get_by_role('button',name='+ Pipeline',exact=True).is_enabled())
  page.get_by_role('button',name='+ Pipeline',exact=True).click();page.get_by_placeholder('Код pipeline',exact=True).fill('ui_pipe_'+nonce);page.get_by_placeholder('Название',exact=True).fill('UI original pipeline');page.locator('.graph-editor form.toolbar').get_by_role('button',name='Создать',exact=True).click();ready('.graph-tools');page.get_by_placeholder('Имя нового процесса',exact=True).fill('work');page.get_by_role('button',name='+ Узел',exact=True).click();page.get_by_role('button',name='Сохранить граф',exact=True).click();page.get_by_text('XML сохранён исходной командой.',exact=False).wait_for();check('Graph creates pipeline and process through original commands')
  page.locator('.graph-node').first.click();page.locator('.graph-properties').get_by_label('Подпись',exact=True).fill('Edited without Apply');check('Pending properties enable Save Graph',page.get_by_role('button',name='Сохранить граф',exact=True).is_enabled());page.get_by_role('button',name='Сохранить граф',exact=True).click();page.locator('.graph-node').get_by_text('Edited without Apply',exact=True).wait_for();check('Save Graph includes pending properties rather than losing them');page.screenshot(path=str(out/'screenshots/original-pipeline-save.png'))
  nav('project_schema').click();ready('.graph-node');check('Source or saved schema opens without manual DB-row creation');page.screenshot(path=str(out/'screenshots/original-schema.png'))
  check('No uncaught JavaScript errors',not errors);check('No legacy HTML widget fetches',not any('get_widget' in u for u in paths))
 except Exception as e:
  page.screenshot(path=str(out/'screenshots/browser-failure.png'));results.append({'scenario':'failure','passed':False,'error':str(e)});raise
 finally:
  (out/'browser-results.json').write_text(json.dumps({'backend':'Original TACTIC startup/DB auth/commands/SQLite; only signature verification isolated in test subprocess','transport':'explicit HTTP bridge; native navigation/cookies/CSP not proven' if a.bridge else 'native','scenarios':results,'js_errors':errors},ensure_ascii=False,indent=2)+'\n');browser.close()
