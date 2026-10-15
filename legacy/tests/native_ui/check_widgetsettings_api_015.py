"""TEST ONLY: original WidgetSettings API interoperability; disposable test login."""
import requests,xmlrpc.client,json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();url=args.url;target='admin_views/global_admin/users'
s=requests.Session();h={'X-Tactic-UI':'1'}
r=s.post(url+'/api/ui/v2/session',json={'login':'admin','password':'Native-Test-Only-123'},headers=h);r.raise_for_status();h['X-CSRF-Token']=r.json()['csrf']
a={'project':'admin','scope':'geometry','target':target};r=s.get(url+'/api/ui/v2/ui-state',params=a,headers=h);r.raise_for_status();state=r.json()
with xmlrpc.client.ServerProxy(url+'/tactic/default/Api/',allow_none=True) as rpc:
 ticket=rpc.get_ticket('admin','Native-Test-Only-123');env={'ticket':ticket,'project':'admin','language':'python','site':''}
 actual=json.loads(rpc.get_widget_setting(env,state['setting_key']))
 assert actual['value']==state['value']
 original_key='last_search:native015_verification_only';original='<config><search><filter>unchanged</filter></search></config>'
 rpc.set_widget_setting(env,original_key,original)
 changed=dict(state['value'],wrap=not state['value']['wrap'])
 r=s.patch(url+'/api/ui/v2/ui-state',json={**a,'revision':state['revision'],'value':changed},headers=h);r.raise_for_status()
 assert rpc.get_widget_setting(env,original_key)==original
 out={'passed':True,'checks':[{'name':'Original XML-RPC get_widget_setting sees exact native JSON in original DB','passed':True},{'name':'Updating native geometry leaves separate legacy setting unchanged','passed':True}]}
 args.output.write_text(json.dumps(out,indent=2)+'\n')
