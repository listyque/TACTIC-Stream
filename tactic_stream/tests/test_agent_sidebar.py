"""Semantic agent edits retain the native sidebar definitions and permissions."""
import unittest
from uuid import uuid4
from xmlrpc.client import Fault
import test_transport

COMMAND='tactic.ui.panel.sidebar_agent_cmd.SidebarAgentCmd'


class SidebarAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url=test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_groups_colors_icons_hidden_items_native_save_and_retry(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            proxy.insert(auth,'config/widget_config',dict(search_type='SideBarWdg',view='definition',config=
                '<config><definition><element name="records" title="Records"><display class="LinkWdg"><search_type>contract/entity</search_type></display><custom keep="yes"/></element>'
                '<element name="duplicate" title="Duplicate"><display class="LinkWdg"><search_type>contract/entity</search_type></display></element></definition></config>'))
            proxy.insert(auth,'config/widget_config',dict(search_type='SideBarWdg',view='tactic_handler',config=
                '<config><tactic_handler><element name="records"/><element name="duplicate"/></tactic_handler></config>'))
            def call(action,**values):
                return proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            document=dict(groups=[dict(name='work',title='Work',icon='folder',color='#5080A0',items=['records'])],
                updates=[dict(item='records',title='All records',icon='table',color='#7080B0')],hidden=['duplicate'])
            values=dict(document=document,expected_revision=state['revision'])
            preview=call('preview',**values)
            self.assertEqual(next(row for row in preview['entries'] if row['name']=='records')['depth'],1)
            operation=str(uuid4())
            saved=call('apply',operation_id=operation,**values)
            self.assertEqual(call('apply',operation_id=operation,**values),saved)
            with self.assertRaises(Fault):call('apply',operation_id=str(uuid4()),**values)
            code="from tactic_stream.server.sidebar_editor import read_sidebar\nfrom tactic_stream.server.navigation import read_navigation\nreturn dict(sidebar=read_sidebar(),navigation=read_navigation())"
            read=proxy.execute_python_script(auth,None,dict(code=code))['info']
            self.assertIn('custom keep="yes"',read['sidebar']['documents']['definition'])
            work=next(row for row in read['navigation']['entries'] if row['name']=='work')
            self.assertEqual(work['color'],'#5080A0')
            self.assertEqual(work['children'][0]['title'],'All records')
            self.assertEqual(work['children'][0]['color'],'#7080B0')
            self.assertFalse(any(row['name']=='duplicate' for row in read['navigation']['entries']))
            self.assertIn('duplicate',read['sidebar']['documents']['definition'])

    def test_real_mcp_sidebar_tools(self):
        import asyncio
        from pathlib import Path
        from mcp import Client
        from tactic_stream.admin_agent import StreamConnection,create_server
        with test_transport.Transport.proxy(self) as proxy:
            ticket=proxy.get_ticket('admin','private-test-password')
        async def run():
            server=create_server(StreamConnection(self.url,'one',ticket),Path(__file__).resolve().parents[1],allow_page_save=True)
            async with Client(server) as client:
                state=await client.call_tool('ts_sidebar_read',{})
                self.assertFalse(state.is_error)
                document=dict(groups=[dict(name='mcp_fixture',title='MCP fixture',items=[])],updates=[],hidden=[])
                values=dict(document=document,expected_revision=state.structured_content['revision'])
                self.assertFalse((await client.call_tool('ts_sidebar_preview',values)).is_error)
                self.assertFalse((await client.call_tool('ts_sidebar_save',dict(values,operation_id=str(uuid4())))).is_error)
        asyncio.run(run())
