"""Actual local provider HTTP -> MCP -> native instance command, on test data."""
import asyncio
import ast
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from tests import test_agent_requests as fixture
try:
    from tactic_stream.admin_agent import COMMANDS, StreamConnection
    from tactic_stream.provider_host import run_provider, refresh_profiles
except ImportError:
    run_provider=None


@unittest.skipIf(run_provider is None,'Install tactic-stream[agent] for provider runtime tests')
class ProviderRuntime(unittest.TestCase):
    setUp=fixture.AgentRequests.setUp
    call=fixture.AgentRequests.call
    submit=fixture.AgentRequests.submit

    def command(self,owner,action,**values):
        return self.api.dispatch('execute_cmd',(self.auth,COMMANDS[owner],dict(action=action,project_code='one',**values)))['info']

    def test_local_api_links_selection_without_receiving_tactic_credentials(self):
        requests=[]
        discoveries=[]
        parent='cg/scenes?project=one&code=EP001'
        steps=[('agent_selection',{}),('ts_records',dict(search_type='cg/scenes',filters=dict(name='Episode_01'))),
               ('ts_instance_link',dict(search_key=parent)),('agent_finish',dict(outcome='completed',answer='Linked the two selected assets.'))]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(server):
                discoveries.append(dict(path=server.path,headers=dict(server.headers)))
                data=json.dumps(dict(data=[dict(id='fixture-model')])).encode()
                server.send_response(200);server.send_header('Content-Type','application/json');server.send_header('Content-Length',str(len(data)));server.end_headers();server.wfile.write(data)
            def do_POST(server):
                request=json.loads(server.rfile.read(int(server.headers['Content-Length'])))
                requests.append(dict(path=server.path,headers=dict(server.headers),body=request))
                name,arguments=steps[len(requests)-1]
                response=dict(choices=[dict(message=dict(role='assistant',content='Applying the native operation.',
                    tool_calls=[dict(id='call-'+str(len(requests)),type='function',function=dict(name=name,arguments=json.dumps(arguments)))]))])
                data=json.dumps(response).encode()
                server.send_response(200);server.send_header('Content-Type','application/json');server.send_header('Content-Length',str(len(data)));server.end_headers();server.wfile.write(data)
            def log_message(self,*args):pass
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        self.addCleanup(http.server_close);self.addCleanup(http.shutdown)
        url='http://127.0.0.1:'+str(http.server_port)+'/v1'
        state=self.command('providers','state')
        state=self.command('providers','save',provider='',expected_revision=state['revision'],document=dict(name='Local fixture',kind='local',url=url,secret='private-provider-fixture',secret_env='',clear_secret=False,enabled=True,default_model='fixture-model',default=False))
        profile=next(row for row in state['profiles'] if row['kind']=='local')
        from tactic_stream.provider_credentials import new_host_key
        private,public=new_host_key()
        self.call('heartbeat',host_id=self.host,label='Fixture',capabilities=dict(changes=True,trials=False,credential_key=public))
        connection=StreamConnection('http://example.invalid','one',self.auth['ticket'])
        with patch.object(connection,'command',side_effect=self.command):
            discovered=refresh_profiles(connection,self.host,private,{},lambda:[dict(id='account-fixture',label='Account fixture')],lambda:None)
        self.assertTrue(any(row['provider']==profile['id'] and row['id']=='fixture-model' for row in discovered['models']))
        self.assertEqual(discoveries,[dict(path='/v1/models',headers=discoveries[0]['headers'])])
        self.assertEqual(discoveries[0]['headers']['Authorization'],'Bearer private-provider-fixture')
        profile['secret']='private-provider-fixture'
        assets=[]
        for code in ('ASSET_A','ASSET_B'):
            row=self.api.dispatch('insert',(self.auth,'cg/assets',dict(code=code,name=code)),dict(triggers=False))
            assets.append(ast.literal_eval(row) if isinstance(row,str) else row)
        self.document.update(allow_changes=True,provider=profile['id'],model='fixture-model',context=dict(
            client='TS',project='one',page='assets',title='Assets',search_type='cg/assets',view='table',search_keys=[row['__search_key__'] for row in assets]))
        capabilities=dict(changes=True,trials=False,providers=[{key:profile[key] for key in ('id','name','kind')}],models=[dict(id='fixture-model',label='Fixture model',provider=profile['id'],is_default=True)])
        self.call('heartbeat',host_id=self.host,label='Fixture',capabilities=capabilities)
        row,_=self.submit()
        row=self.call('claim',host_id=self.host)['request']
        connection=StreamConnection('http://example.invalid','one',self.auth['ticket'])
        options=SimpleNamespace(allow_changes=True,stream_root=fixture.ROOT,handler_root=None,trial_image=None,trial_directory=None)
        from tactic_stream.agent_host import message_inputs,task_prompt
        with patch.object(connection,'command',side_effect=self.command):
            asyncio.run(run_provider(connection,row,profile,self.host,options,lambda:None,task_prompt,message_inputs))
        saved=self.call('read',request_id=row['request_id'])
        self.assertEqual((saved['status'],saved['outcome']),('completed','completed'))
        self.assertEqual(len(requests),4)
        self.assertNotIn(self.auth['ticket'],json.dumps(requests))
        for request in requests:
            self.assertEqual(request['path'],'/v1/chat/completions')
            self.assertNotIn('private-provider-fixture',json.dumps(request['body']))
            self.assertEqual(request['headers']['Authorization'],'Bearer private-provider-fixture')
        linked=self.command('editing','relations',request_id=row['request_id'],search_key=parent,search_type='cg/assets')['objects']
        self.assertEqual({row['code'] for row in linked},{'ASSET_A','ASSET_B'})
