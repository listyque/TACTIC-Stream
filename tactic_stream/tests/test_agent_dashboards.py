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
            metric=preview['model']['layoutNodes'][0]['children'][0]
            self.assertEqual((metric['kind'],metric['text'],metric['value']),('metric','Chosen entities',1))
            operation=str(uuid4())
            saved=call('apply',operation_id=operation,**payload)
            self.assertEqual(call('read',name='review')['document'],preview['document'])
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

    def test_widget_height_and_native_controls_are_preserved(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            draft=document();draft['blocks'][1].update(height=320,controls=['search'])
            preview=call('preview',document=draft,expected_revision=state['revision'])
            table=preview['model']['layoutNodes'][1]
            self.assertEqual(table['height'],320)
            self.assertTrue(table['table']['search'])
            self.assertTrue(all(not table['table'][name] for name in ('shelf','selection','gear','insert','searchLimit')))
            draft['blocks'][1]['controls']=['python']
            with self.assertRaises(Fault):call('preview',document=draft,expected_revision=state['revision'])
            with self.assertRaises(Fault):call('read',name='does_not_exist')

    def test_system_task_widget_uses_existing_project_parent_scope(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            state=proxy.execute_cmd(auth,COMMAND,dict(action='read',project_code='one'))['info']
            draft=dict(name='tasks',title='Tasks',blocks=[dict(kind='table',search_type='sthpw/task',filters=[dict(column='project_code',value='one')])])
            model=proxy.execute_cmd(auth,COMMAND,dict(action='preview',project_code='one',document=draft,expected_revision=state['revision']))['info']['model']
            table=model['layoutNodes'][0]['table']
            self.assertFalse(table['projectScope'])
            result=proxy.execute_cmd(auth,'tactic.ui.table.NestedTableReadCmd',dict(parent_key=table['parentKey'],search_type=table['searchType'],project_scope=table['projectScope'],filters=table['filters']))['info']
            self.assertTrue(all(row['project_code']=='one' for row in result['records']))

    def test_lazy_tree_uses_schema_instances_tasks_notes_and_project_scope(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            def tree_read(tree,**values):
                return proxy.execute_cmd(auth,COMMAND,dict(action='tree',project_code='one',tree=tree,**values))['info']
            tree=dict(search_type='contract/entity',filters=[dict(column='code',value='A')],branches=[dict(search_type='sthpw/task',title_field='process',branches=[dict(search_type='sthpw/note')])])
            roots=tree_read(tree)
            self.assertEqual([row['title'] for row in roots['items']],['Первый'])
            key=roots['items'][0]['key']
            task=proxy.create_task(auth,key,'model')
            if isinstance(task,str):task=ast.literal_eval(task)
            proxy.create_note(auth,task['__search_key__'],'Native tree note')
            tasks=tree_read(tree,branch_path=[0],parent_key=key)
            self.assertEqual([row['title'] for row in tasks['items']],['model'])
            notes=tree_read(tree,branch_path=[0,0],parent_key=tasks['items'][0]['key'])
            self.assertEqual(len(notes['items']),1)
            instances=dict(search_type='contract/collection',branches=[dict(search_type='contract/entity')])
            linked=tree_read(instances,branch_path=[0],parent_key='contract/collection?project=one&code=G1')
            self.assertEqual({row['key'] for row in linked['items']},{key,'contract/entity?project=one&code=B'})
            self.assertEqual(len(linked['items']),2)
            first_link=tree_read(instances,branch_path=[0],parent_key='contract/collection?project=one&code=G1',limit=1)
            second_link=tree_read(instances,branch_path=[0],parent_key='contract/collection?project=one&code=G1',offset=1,limit=1)
            self.assertTrue(first_link['has_next'])
            self.assertEqual([first_link['items'][0]['key'],second_link['items'][0]['key']],[key,'contract/entity?project=one&code=B'])
            page=tree_read(dict(search_type='contract/entity'),limit=1)
            self.assertTrue(page['has_next'])
            next_page=tree_read(dict(search_type='contract/entity'),offset=1,limit=1)
            self.assertNotEqual(page['items'][0]['key'],next_page['items'][0]['key'])
            state=proxy.execute_cmd(auth,COMMAND,dict(action='read',project_code='one'))['info']
            draft=dict(name='hierarchy',title='Hierarchy',blocks=[dict(kind='tree',tree=tree,height=600)])
            preview=proxy.execute_cmd(auth,COMMAND,dict(action='preview',project_code='one',document=draft,expected_revision=state['revision']))['info']
            self.assertEqual(preview['model']['layoutNodes'][0]['kind'],'tree')
            for invalid in [dict(branch_path=[99],parent_key=key),dict(branch_path=[-1],parent_key=key),dict(branch_path=[0],parent_key='contract/entity?project=two&code=A'),dict(branch_path=[0],parent_key='contract/collection?project=one&code=G1'),dict(limit=101)]:
                with self.subTest(invalid=invalid),self.assertRaises(Fault):tree_read(tree,**invalid)
            for invalid_tree in [dict(search_type='contract/entity',branches=[dict(search_type='sthpw/login')]),dict(search_type='contract/entity',title_field='missing'),dict(search_type='contract/entity?project=two')]:
                with self.subTest(invalid_tree=invalid_tree),self.assertRaises(Fault):tree_read(invalid_tree)

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

    def test_internal_chat_provider_can_publish_and_read_back_a_dashboard(self):
        import asyncio
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        from types import SimpleNamespace
        import threading
        from tactic_stream.admin_agent import StreamConnection
        from tactic_stream.provider_host import run_provider
        from tactic_stream.agent_host import message_inputs, task_prompt
        requests=[];values={};operation=str(uuid4())
        draft=document();draft['name']='chat_dashboard'
        draft['blocks']=[dict(kind='tree',tree=dict(search_type='contract/entity',filters=[dict(column='code',value='A')],branches=[dict(search_type='sthpw/task')]))]

        class Provider(BaseHTTPRequestHandler):
            def do_POST(server):
                body=json.loads(server.rfile.read(int(server.headers['Content-Length'])))
                requests.append(body)
                previous=json.loads(body['messages'][-1]['content']) if body['messages'][-1]['role']=='tool' else None
                step=len(requests)
                if step==1:
                    name,arguments='ts_dashboard_read',{}
                elif step==2:
                    values.update(document=draft,expected_revision=previous['revision'])
                    name,arguments='ts_dashboard_preview',values
                elif step==3:
                    name,arguments='ts_dashboard_tree_read',dict(tree=draft['blocks'][0]['tree'])
                elif step==4:
                    name,arguments='ts_dashboard_save',dict(values,operation_id=operation)
                elif step==5:
                    name,arguments='ts_dashboard_read',dict(name='chat_dashboard')
                else:
                    name,arguments='agent_finish',dict(outcome='completed',answer='Open Review dashboard from project navigation.')
                response=dict(choices=[dict(message=dict(role='assistant',content='',tool_calls=[dict(id='call-'+str(step),type='function',function=dict(name=name,arguments=json.dumps(arguments)))]))])
                data=json.dumps(response).encode()
                server.send_response(200);server.send_header('Content-Type','application/json');server.send_header('Content-Length',str(len(data)));server.end_headers();server.wfile.write(data)
            def log_message(self,*args):pass

        http=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        threading.Thread(target=http.serve_forever,daemon=True).start()
        self.addCleanup(http.server_close);self.addCleanup(http.shutdown)
        with test_transport.Transport.proxy(self) as proxy:
            ticket=proxy.get_ticket('admin','private-test-password')
        connection=StreamConnection(self.url,'one',ticket)
        profiles=connection.command('providers','state')
        profiles=connection.command('providers','save',provider='',expected_revision=profiles['revision'],document=dict(name='Dashboard fixture',kind='local',url='http://127.0.0.1:'+str(http.server_port)+'/v1',secret='',secret_env='',clear_secret=False,enabled=True,default_model='fixture-model',default=False))
        profile=next(row for row in profiles['profiles'] if row['name']=='Dashboard fixture')
        host=str(uuid4())
        connection.command('request','heartbeat',host_id=host,label='Fixture',capabilities=dict(changes=True,trials=False,providers=[{key:profile[key] for key in ('id','name','kind')}],models=[dict(id='fixture-model',label='Fixture',provider=profile['id'],is_default=True)]))
        request_id=str(uuid4())
        connection.command('request','submit',request_id=request_id,host_id=host,document=dict(prompt='Create a native review dashboard with a count and filtered table.',allow_changes=True,provider=profile['id'],model='fixture-model',context=dict(client='TS',project='one',page='entities',title='Entities',search_type='contract/entity',view='table',search_keys=[])))
        request=connection.command('request','claim',host_id=host)['request']
        options=SimpleNamespace(allow_changes=True,stream_root=Path(__file__).resolve().parents[1],handler_root=None,trial_image=None,trial_directory=None)
        asyncio.run(run_provider(connection,request,profile,host,options,lambda:None,task_prompt,message_inputs))
        saved=connection.command('request','read',request_id=request_id)
        self.assertEqual((saved['status'],saved['outcome']),('completed','completed'))
        self.assertEqual(len(requests),6)
        roots=json.loads(requests[3]['messages'][-1]['content'])
        self.assertEqual(roots['items'][0]['key'],'contract/entity?project=one&code=A')
        self.assertNotIn(ticket,json.dumps(requests))
        self.assertEqual(connection.command('dashboard','read',name='chat_dashboard')['document']['name'],'chat_dashboard')
        tools={row['function']['name']:row['function']['parameters'] for row in requests[0]['tools']}
        self.assertIn('ts_dashboard_save',tools)
        self.assertIn('ts_dashboard_tree_read',tools)
        self.assertIn('name',tools['ts_dashboard_read']['properties'])
        # Model writes remain unavailable when the chat's changes permission is off.
        from tactic_stream.admin_agent import create_server
        from mcp import Client
        async def check_readonly():
            async with Client(create_server(connection,options.stream_root,request_id=request_id)) as client:
                self.assertNotIn('ts_dashboard_save',{tool.name for tool in (await client.list_tools()).tools})
        asyncio.run(check_readonly())
