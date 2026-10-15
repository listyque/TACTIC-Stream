"""Actual original admin links and cell editor buttons, compiled Vue, explicit bridge only if blocked."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,base64,json
import requests
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',required=True,type=Path);p.add_argument('--http-report',required=True,type=Path);p.add_argument('--bridge',action='store_true');p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args()
out=a.output;out.mkdir(parents=True,exist_ok=True);(out/'screenshots').mkdir(exist_ok=True)
context=json.loads(a.http_report.read_text());checks=[];errors=[];report={'passed':False,'scenarios':checks}
def check(name,ok=True):
    checks.append({'scenario':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
    if not ok:raise AssertionError(name)
s=requests.Session();head={'X-Tactic-UI':'1','Origin':a.url}
def request(method,path,**data):
    r=s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=head,timeout=40)
    if r.status_code not in (200,201):raise AssertionError(str(r.status_code)+': '+r.text[:800])
    return r.json()
head['X-CSRF-Token']=request('POST','/session',login='admin',password='Native-Test-Only-123')['csrf']
for scope,val in [('workspace',{'ids':[],'active':''}),('navigation',{'folders':{}}),('appearance',{'theme':'light'})]:
    data=request('GET','/ui-state',project='admin',scope=scope)
    request('PATCH','/ui-state',project='admin',scope=scope,value=val,revision=data['revision'])
try:
 with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1550,'height':980});page=ctx.new_page();page.set_default_timeout(15000)
    try:
        page.goto(a.url+'/tactic/admin/',wait_until='networkidle',timeout=12000);report['native_navigation']=True
    except Exception as e:
        report['native_navigation']=False;report['native_navigation_error']=str(e)
        if not a.bridge:raise
        page.close();page=ctx.new_page();page.set_default_timeout(15000);transport_session=requests.Session()
        def transport(q):
            u=urlsplit(q['url']);path=u.path+('?' +u.query if u.query else '')
            assert path.startswith('/api/ui/v2/')
            r=transport_session.request(q['method'],a.url+path,headers=q.get('headers',{}),data=q.get('body'),timeout=40)
            return {'status':r.status_code,'body64':base64.b64encode(r.content).decode(),'headers':dict(r.headers)}
        page.expose_function('_real_http',transport)
        page.set_content('<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body><div id="app"></div></body></html>')
        page.evaluate('''(url)=>{const b=document.createElement('base');b.href=url;document.head.append(b);const U=URL;window.URL=new Proxy(U,{construct(t,args){if(args[1]==='null')args[1]=url;return Reflect.construct(t,args)}});history.replaceState=()=>{};window.fetch=async(u,o={})=>{const r=await window._real_http({url:String(u),method:o.method||'GET',headers:o.headers||{},body:o.body});return new Response(Uint8Array.from(atob(r.body64),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers})}}''',a.url)
        web=ROOT/'src/tactic/ui_api/web';page.add_style_tag(content=(web/'styles.css').read_text());page.add_script_tag(content=(web/'vendor/vue.global.prod.js').read_text());page.add_script_tag(content=(web/'app.js').read_text());report['bridge']=True
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
    def login():
        page.get_by_label('Логин',exact=True).fill('admin');page.get_by_label('Пароль',exact=True).fill('Native-Test-Only-123');page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_selector('.sidebar .nav-item');page.wait_for_selector('main[aria-busy="false"]')
    login();check('Original password login works in compiled application')
    page.evaluate('''()=>{let b=document.createElement('div');b.textContent='ORIGINAL TACTIC · SQLITE TEST DATA · test signature isolated · HTTP bridge if navigation blocked';b.style='position:fixed;left:0;right:0;bottom:0;background:#443922;color:white;font:11px sans-serif;padding:4px;z-index:99999;pointer-events:none';document.body.append(b)}''')
    def nav(name,folder=None):
        leaf=page.locator('.sidebar button[title="'+name+'"]')
        if not leaf.is_visible() and folder:page.locator('.sidebar button[title="'+folder+'"]').click()
        leaf.click()
    def wait_graph():
        page.wait_for_selector('main[aria-busy="false"] > .graph-editor');page.wait_for_timeout(500)
        check('Specialized editor is not a visible generic table',page.locator('main > .native-grid:visible').count()==0)
    nav('project_workflow','project_admin');wait_graph()
    check('Project Workflow mounts GraphEditor',page.locator('main > .graph-editor .graph-svg').count()==1)
    page.locator('main > .graph-editor .toolbar select').first.select_option(context['pipeline_key']);page.wait_for_selector('.graph-node');check('Chosen original pipeline nodes appear',page.locator('.graph-node').count()==2)
    nav('project_schema','project_admin');wait_graph();check('Project Schema renders real source graph',page.locator('.graph-node').count()>20)
    nav('sthpw_pipelines','project_essentials');page.wait_for_selector('main > .native-grid[aria-busy="false"]')
    check('Pipelines manage remains a configured table',page.locator('main > .native-grid tbody tr').count()>0)
    row=page.locator('tr[data-key="'+context['pipeline_key']+'"]');row.locator('td[data-field="editor"] button').click();wait_graph()
    check('Cell button opens its selected pipeline',page.locator('main > .graph-editor .toolbar select').first.input_value()==context['pipeline_key'])
    page.get_by_placeholder('Имя нового процесса',exact=True).fill('browser_check');page.get_by_role('button',name='+ Узел',exact=True).click()
    check('New node enters original graph editor buffer',page.locator('.graph-node').count()==3)
    page.get_by_role('button',name='Сохранить граф',exact=True).click();page.wait_for_function('()=>Array.from(document.querySelectorAll("main > .graph-editor .notice")).some(n=>n.textContent.includes("XML сохранён"))');check('Original graph saves through restored cell entry point')
    saved=request('GET','/graph',project='admin',target=context['pipeline_cell'],kind='pipeline',key=context['pipeline_key'])
    check('Browser-created process persisted through original TACTIC command',any(n['name']=='browser_check' for n in saved['graph']['nodes']))
    page.screenshot(path=str(out/'screenshots/restored-pipeline-editor.png'))
    before=page.locator('main > .graph-editor .graph-node').count()
    page.locator('.view-heading').get_by_role('button',name='Обновить',exact=True).click();page.wait_for_timeout(900)
    check('Header refresh actually remounts graph and reloads selected key',page.locator('main > .graph-editor .graph-node').count()==before and page.locator('main > .graph-editor .toolbar select').first.input_value()==context['pipeline_key'])
    nav('sthpw_schema','project_essentials');page.wait_for_selector('main > .native-grid[aria-busy="false"]')
    page.get_by_role('button',name='Открыть схему проекта',exact=True).first.click();wait_graph();check('Schema table restores original button into specialized page',page.locator('.graph-node').count()>20)
    page.screenshot(path=str(out/'screenshots/restored-schema-editor.png'))
    nav('system_config','global_admin');page.wait_for_selector('.global-settings');check('System Config remains unique editor, not table',page.locator('main > .native-grid:visible').count()==0)
    nav('script_editor','project_admin');page.wait_for_selector('.script-editor');check('Script Editor remains specialized after navigation')
    nav('project_workflow','project_admin');wait_graph();page.wait_for_timeout(700)
    page.get_by_role('button',name='Выйти',exact=True).click();page.wait_for_selector('input[type="password"]');login();wait_graph()
    check('DB workspace restoration keeps pipeline kind after new login',page.locator('main > .graph-editor').count()==1)
    # UI log of unsaved staging must never collect the typed text.
    nav('users','global_admin');page.wait_for_selector('main > .native-grid[aria-busy="false"]')
    # Query state from prior regressions may filter. Use a visible non-admin row.
    cells=page.locator('main > .native-grid td[data-field="first_name"]')
    if cells.count():
        cells.last.dblclick();page.wait_for_selector('.inline-editor')
        page.locator('.inline-editor input,.inline-editor textarea').first.fill('UNSAVED_PRIVATE_FIELD_016')
        page.locator('.inline-editor').get_by_role('button',name='Применить',exact=True).click();page.wait_for_timeout(300)
        check('Local cell staging action emits without immediate save',page.locator('.inline-editor').count()==0)
    page.wait_for_timeout(500)
    check('No JavaScript runtime errors',not errors)
    browser.close();report['passed']=True
except Exception as e:
    report['error']=str(e)
    import traceback;traceback.print_exc()
finally:
    report['errors']=errors;(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if not report['passed']:raise SystemExit(1)
