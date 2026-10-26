"""Portable dashboard authoring uses native revisions, receipts and both layout readers."""
import json
import ast
import unittest
from uuid import uuid4
import test_transport

COMMAND='tactic.ui.panel.dashboard_cmd.DashboardCmd'


def document():
    return dict(name='review',title='Review dashboard',blocks=[
        dict(kind='row',children=[dict(kind='metric',title='Chosen entities',search_type='contract/entity',
            filters=[dict(column='code',relation='=',value='A')]),dict(kind='text',text='Native shared UI')]),
        dict(kind='table',title='Review records',search_type='contract/entity',filters=[dict(column='code',relation='=',value='A')]),
        dict(kind='link',title='Open record',href='skey://contract/entity?project=one&code=A')])


class Dashboards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url=test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_revision_idempotent_save_update_and_native_layout(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            def call(action,**values):
                return proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            payload=dict(document=document(),expected_revision=state['revision'])
            preview=call('preview',**payload)
            self.assertEqual(preview['model']['layoutNodes'][0]['children'][0]['text'],'Chosen entities: 1')
            operation=str(uuid4())
            saved=call('apply',operation_id=operation,**payload)
            self.assertEqual(call('apply',operation_id=operation,**payload),saved)
            self.assertEqual(call('operation',operation_id=operation),saved)
            compiled=proxy.execute_cmd(auth,'tactic.ui.table.CustomLayoutReadCmd',dict(view=saved['view']))['info']
            self.assertEqual(compiled['layoutNodes'],preview['model']['layoutNodes'])
            table=compiled['layoutNodes'][1]['table']
            result=proxy.execute_cmd(auth,'tactic.ui.table.NestedTableReadCmd',dict(parent_key=table['parentKey'],
                search_type=table['searchType'],project_scope=True,filters=table['filters']))['info']
            self.assertEqual([row['code'] for row in result['records']],['A'])
            from xmlrpc.client import Fault
            with self.assertRaises(Fault):call('apply',operation_id=str(uuid4()),**payload)
            state=call('read');edited=document();edited['title']='Updated dashboard'
            changed=call('apply',operation_id=str(uuid4()),document=edited,expected_revision=state['revision'])
            self.assertEqual(changed['title'],'Updated dashboard')
            navigation=proxy.execute_python_script(auth,None,dict(code="from tactic_stream.server.navigation import read_navigation\nreturn read_navigation()"))['info']
            self.assertTrue(any(row['title']=='Updated dashboard' for row in navigation['entries']))
            self.assertEqual(len(ast.literal_eval(proxy.query(auth,'config/url',[['url',saved['path']]]))),1)

    def test_untrusted_bricks_and_invalid_filters_are_refused(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            state=proxy.execute_cmd(auth,COMMAND,dict(action='read',project_code='one'))['info']
            for block in (dict(kind='python',text='print(1)'),dict(kind='metric',search_type='contract/entity',filters=[dict(column='not_a_column',value='x')]),
                          dict(kind='link',href='javascript:alert(1)'),dict(kind='table',search_type='contract/entity?project=two')):
                invalid=dict(name='invalid',title='Invalid',blocks=[block])
                with self.assertRaises(Fault):proxy.execute_cmd(auth,COMMAND,dict(action='apply',project_code='one',document=invalid,
                    expected_revision=state['revision'],operation_id=str(uuid4())))
            self.assertEqual(json.loads(proxy.query(auth,'config/url',[['url','/dashboard/invalid']])),[])

    def test_markdown_literal_record_field_and_project_boundary(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            state=proxy.execute_cmd(auth,COMMAND,dict(action='read',project_code='one'))['info']
            draft=dict(name='documents',title='Documents',blocks=[dict(kind='markdown',text='# Plan\n\n**Ready**'),
                dict(kind='markdown',source_key='contract/entity?project=one&code=A',field='code')])
            def preview():
                return proxy.execute_cmd(auth,COMMAND,dict(action='preview',project_code='one',document=draft,expected_revision=state['revision']))['info']
            result=preview()['model']['layoutNodes']
            self.assertEqual(result[0]['kind'],'markdown')
            self.assertEqual(result[0]['text'],'# Plan\n\n**Ready**')
            self.assertEqual(result[1]['text'],'A')
            draft['blocks'][1]['source_key']='contract/entity?project=two&code=A'
            with self.assertRaises(Fault):preview()

    def test_real_agent_tools_compose_and_save_portable_dashboard(self):
        import asyncio
        from pathlib import Path
        from mcp import Client
        from tactic_stream.admin_agent import StreamConnection,create_server
        with test_transport.Transport.proxy(self) as proxy:
            ticket=proxy.get_ticket('admin','private-test-password')
        async def run():
            server=create_server(StreamConnection(self.url,'one',ticket),Path(__file__).resolve().parents[1],allow_page_save=True)
            async with Client(server) as client:
                state=(await client.call_tool('ts_dashboard_read',{})).structured_content
                draft=document();draft['name']='via_mcp'
                values=dict(document=draft,expected_revision=state['revision'])
                preview=await client.call_tool('ts_dashboard_preview',values)
                self.assertFalse(preview.is_error)
                result=await client.call_tool('ts_dashboard_save',dict(values,operation_id=str(uuid4())))
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content['path'],'/dashboard/via_mcp')
        asyncio.run(run())
