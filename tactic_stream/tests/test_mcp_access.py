"""Real MCP HTTP access: scopes, vault, revocation and native dashboard writes."""
import asyncio
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from uuid import uuid4

import test_transport
from pyasm.common import Config
from tests.test_agent_dashboards import document

COMMAND='tactic.ui.panel.agent_mcp_cmd.AgentMcpCmd'


class McpAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        create=test_transport.create_app
        def enabled_app(data_dir):
            original=Config.get_value
            def value(section,key,*args,**kwargs):
                return 'true' if (section,key)==('security','agent_mcp_enabled') else original(section,key,*args,**kwargs)
            with patch.object(Config,'get_value',side_effect=value):
                return create(data_dir,event_collector=False)
        cls.factory=patch.object(test_transport,'create_app',side_effect=enabled_app)
        cls.factory.start()
        test_transport.Transport.setUpClass()
        cls.url=test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        try:test_transport.Transport.tearDownClass()
        finally:cls.factory.stop()

    def test_real_mcp_scoped_tools_write_and_revocation(self):
        with test_transport.Transport.proxy(self) as proxy:
            ticket=proxy.get_ticket('admin','private-test-password')
            auth=dict(ticket=ticket,project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('state')
            self.assertTrue(state['enabled'])
            self.assertFalse(any(tool['name'].startswith(('ts_project_','agent_conversation')) for tool in state['tools']))
            context=dict(client='TS',project='one',page='',title='Project',search_type='contract/entity',view='table',search_keys=['contract/entity?project=one&code=A'])
            names=['agent_context','ts_dashboard_read','ts_dashboard_preview','ts_dashboard_save']
            grant=call('create',title='Fixture access',instructions='Track this project using native records.',tools=names,minutes=60,context=context)
            self.assertNotIn(ticket,json.dumps(grant))
            self.assertNotIn('token',call('state')['connections'][0])
            private=json.loads((test_transport.Transport.store.data_dir/'agent_mcp'/(grant['id']+'.json')).read_text())
            self.assertNotIn(ticket,json.dumps(private))
            self.assertNotIn(grant['token'],json.dumps(private))

            async def run():
                import httpx2
                from mcp import Client
                from mcp.client.streamable_http import streamable_http_client
                async def failed_response(response):
                    if response.status_code>=400:
                        await response.aread()
                        print('MCP transport error',response.status_code,response.text[:1000])
                async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+grant['token']},event_hooks={'response':[failed_response]}) as http:
                    async with Client(streamable_http_client(self.url+grant['path'],http_client=http),mode='legacy') as client:
                        tools=await client.list_tools()
                        self.assertEqual({tool.name for tool in tools.tools},set(names))
                        context_result=await client.call_tool('agent_context',{})
                        self.assertEqual(context_result.structured_content['context']['project'],'one')
                        self.assertEqual(context_result.structured_content['prompt'],'Track this project using native records.')
                        denied=await client.call_tool('ts_project_create',{})
                        self.assertTrue(denied.is_error)
                        state_result=await client.call_tool('ts_dashboard_read',{})
                        self.assertFalse(state_result.is_error)
                        draft=document();draft['name']='mcp_http'
                        values=dict(document=draft,expected_revision=state_result.structured_content['revision'])
                        self.assertFalse((await client.call_tool('ts_dashboard_preview',values)).is_error)
                        applied=await client.call_tool('ts_dashboard_save',dict(values,operation_id=str(uuid4())))
                        self.assertFalse(applied.is_error)
            asyncio.run(run())
            call('revoke',id=grant['id'])
            request=Request(self.url+grant['path'],data=b'{}',headers={'Authorization':'Bearer '+grant['token'],'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as raised:urlopen(request)
            self.assertEqual(raised.exception.code,401)
            raised.exception.close()
            state=proxy.execute_cmd(auth,'tactic.ui.panel.agent_request_cmd.AgentRequestCmd',dict(action='state',project_code='one'))['info']
            self.assertFalse(any(row['request_id']==grant['id'] for row in state['requests']))

    def test_expired_and_readonly_grants_and_default_off(self):
        from xmlrpc.client import Fault
        from tactic_stream.server.app import create_app
        from tactic_stream.server.mcp_access import authorize
        from tactic_stream.server.api import Api
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            context=dict(client='TS',project='one',page='',title='',search_type='',view='',search_keys=[])
            grant=call('create',title='Read only',tools=['agent_context'],minutes=5,context=context)
            api=Api(test_transport.Transport.store)
            record,ticket=authorize(api,grant['id'],grant['token'])
            self.assertFalse(record['allow_changes'])
            with self.assertRaises(Fault):
                proxy.execute_cmd(auth,'tactic.ui.panel.agent_actions_cmd.AgentActionsCmd',dict(project_code='one',request_id=grant['id'],action='create',operation_id=str(uuid4())))
            path=test_transport.Transport.store.data_dir/'agent_mcp'/(grant['id']+'.json')
            record['expires']=0
            path.write_text(json.dumps(record),encoding='utf-8')
            with self.assertRaises(ValueError):authorize(api,grant['id'],grant['token'])
            with self.assertRaises(ValueError):authorize(api,grant['id'],'wrong-token')
            original=Config.get_value
            def disabled(section,key,*args,**kwargs):
                return 'false' if (section,key)==('security','agent_mcp_enabled') else original(section,key,*args,**kwargs)
            with patch.object(Config,'get_value',side_effect=disabled):
                off=create_app(test_transport.Transport.store.data_dir,event_collector=False)
            self.assertFalse(any(getattr(route,'path','')=='/mcp' for route in off.routes))

    def test_chat_can_issue_idempotently_without_receiving_token(self):
        from pathlib import Path
        from mcp import Client
        from tactic_stream.admin_agent import StreamConnection,create_server
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            ticket=proxy.get_ticket('admin','private-test-password')
            auth=dict(ticket=ticket,project='one')
            host,request_id,operation=str(uuid4()),str(uuid4()),str(uuid4())
            context=dict(client='TS',project='one',page='',title='',search_type='',view='',search_keys=[])
            def request(action,**values):
                return proxy.execute_cmd(auth,'tactic.ui.panel.agent_request_cmd.AgentRequestCmd',dict(action=action,project_code='one',**values))['info']
            request('heartbeat',host_id=host,label='Fixture',capabilities=dict(changes=True,trials=False))
            request('submit',request_id=request_id,host_id=host,document=dict(prompt='Issue access',context=context,allow_changes=True))
            request('claim',host_id=host)
            async def run():
                server=create_server(StreamConnection(self.url,'one',ticket),Path(__file__).resolve().parents[1],request_id=request_id,allow_page_save=True)
                async with Client(server) as client:
                    values=dict(title='Tracker MCP',tools=['agent_context'],operation_id=operation,minutes=5)
                    result=await client.call_tool('ts_mcp_connection_create',values)
                    self.assertFalse(result.is_error,str(result))
                    self.assertNotIn('token',result.structured_content)
                    self.assertTrue(result.structured_content['pending'])
                    self.assertEqual(result.structured_content,(await client.call_tool('ts_mcp_connection_create',values)).structured_content)
                    return result.structured_content
            issued=asyncio.run(run())
            values=dict(action='reveal',project_code='one',id=issued['id'])
            collected=proxy.execute_cmd(auth,COMMAND,values)['info']
            self.assertIn('token',collected)
            self.assertFalse(collected['pending'])
            with self.assertRaises(Fault):proxy.execute_cmd(auth,COMMAND,values)
            with self.assertRaises(Fault):
                proxy.execute_cmd(auth,COMMAND,dict(values,request_id=request_id))
