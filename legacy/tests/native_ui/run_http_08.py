"""HTTP regression: read-only system metadata from actual stock seed, TEST auth."""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9168');p.add_argument('--output',required=True);a=p.parse_args()
s=requests.Session();h={'X-Tactic-UI':'1'};results=[]
base={'project':'admin','target':'admin_views/global_admin/system_info'}
def check(name,value):
 assert value,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def call(method,path,data=None):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=h,timeout=15)
try:
 check('System metadata requires a session',call('GET','/system',base).status_code==401)
 r=call('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=r.json()['csrf']
 r=call('GET','/open',base);check('Original widget-config SystemInfoWdg opens native system panel',r.status_code==200 and r.json()['handler']=='tactic.ui.app.SystemInfoWdg' and r.json()['kind']=='system')
 r=call('GET','/system',base);check('Real metadata service responds through bundled CherryPy',r.status_code==200)
 data=r.json();schema=data['schema'];checks=schema['databases'][0]['checks']
 check('Runtime version comes from NATIVE_UI_VERSION',data['ui_version']==((Path(__file__).resolve().parents[2]/'NATIVE_UI_VERSION').read_text().strip()+'.0-source-fork'))
 check('Original seed is honestly reported as incomplete',schema['read_only'] is True and schema['ready'] is False)
 check('Missing message_log table is not masked',any(x.get('table')=='message_log' and x['state']=='missing_table' for x in checks))
 check('Widget config registration preserves unprefixed original table',any(x.get('table')=='widget_config' for x in checks) and not any(x.get('table')=='spt_widget_config' for x in checks))
 check('Report distinguishes columns from absent tables',any(x['state']=='missing_columns' for x in checks))
 check('No credential/installation path dump in system data','password' not in str(data).lower() and 'tactic-conf.xml' not in str(data) and '.runtime' not in str(data))
 check('Schema check has no browser migration action','MANAGE_TACTIC.bat db upgrade' in schema['upgrade_notice'] and 'execute' not in schema)
 check('Normal table target cannot invoke system metadata',call('GET','/system',dict(base,target='admin_views/project_essentials/project_tasks')).status_code==403)
 check('System POST does not execute upgrades',call('POST','/system',dict(base,operation='upgrade')).status_code==405)
 second=call('GET','/system',base);check('Repeated GET retains identical schema and does not repair it',second.json()['schema']==schema)
 check('Response is private/no-store',r.headers.get('Cache-Control')=='no-store')
 check('Production writes stay disabled',json.loads((Path(__file__).resolve().parents[2]/'src/tactic/ui_api/config.json').read_text())['allow_writes'] is False)
except Exception as exc:
 results.append({'scenario':'failure','passed':False,'error':str(exc)});raise
finally:
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'backend':'actual read-only original seed metadata, production system service, TEST auth/context','scenarios':results},ensure_ascii=False,indent=2)+'\n')
