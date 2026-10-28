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
    def test_position_and_appearance_round_trip_and_validation(self):
        from xmlrpc.client import Fault

        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(
                ticket=proxy.get_ticket("admin", "private-test-password"), project="one"
            )
            call = lambda action, **values: proxy.execute_cmd(
                auth, COMMAND, dict(action=action, project_code="one", **values)
            )["info"]
            draft = dict(
                name="styled_selection",
                title="Styled",
                blocks=[
                    dict(
                        kind="text",
                        text="Styled",
                        offset_x=24,
                        offset_y=-12,
                        appearance=dict(
                            fill="panel",
                            stroke="#729AB2",
                            stroke_width=2,
                            radius=6,
                            shadow=True,
                            animate=True,
                        ),
                    )
                ],
            )
            revision = call("read")["revision"]
            preview = call("preview", document=draft, expected_revision=revision)
            node = preview["model"]["layoutNodes"][0]
            self.assertEqual((node["offsetX"], node["offsetY"]), (24, -12))
            self.assertEqual(node["appearance"]["stroke_width"], 2)
            call(
                "apply",
                document=draft,
                expected_revision=revision,
                operation_id=str(uuid4()),
            )
            self.assertEqual(
                call("read", name="styled_selection")["document"], preview["document"]
            )
            for patch in [
                dict(offset_x=True),
                dict(offset_y=1601),
                dict(appearance=dict(stroke="url(x)")),
                dict(appearance=dict(radius=49)),
                dict(appearance=dict(shadow="true")),
            ]:
                invalid = dict(
                    name="invalid_style",
                    title="Invalid",
                    blocks=[dict(kind="text", text="Test", **patch)],
                )
                with self.assertRaises(Fault):
                    call(
                        "preview",
                        document=invalid,
                        expected_revision=call("read")["revision"],
                    )


    def test_source_catalog_typed_bindings_and_project_boundaries(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            catalog=call('sources')['searchTypes']
            self.assertTrue(any(row['value']=='contract/entity' and row['projectOwned'] for row in catalog))
            source=call('sources',search_type='contract/entity',query='Перв')
            self.assertTrue(any(row['value']=='amount' for row in source['fields']))
            self.assertTrue(source['tableViews']);self.assertTrue(source['itemViews'])
            self.assertTrue(source['records'])
            self.assertNotIn('sources',source);self.assertNotIn('layers',source)
            key=source['records'][0]['value']
            state=call('read')
            draft=dict(name='bound_sources',title='Bound',blocks=[
                dict(kind='text',binding='project',field='title'),
                dict(kind='text',binding='record',search_type='contract/entity',source_key=key,field='amount'),
                dict(kind='items',search_type='contract/entity',view='continuous_example'),
                dict(kind='details',children=[dict(kind='text',binding='selection',search_type='contract/entity',field='name')])])
            preview=call('preview',document=draft,expected_revision=state['revision'],detail_key=key)
            self.assertEqual(preview['model']['layoutNodes'][1]['text'],'0')
            self.assertTrue(preview['model']['layoutDetail']['layoutNodes'][0]['text'])
            for values in [dict(search_type='contract/entity?project=two'),
                           dict(search_type='contract/entity',record_key='contract/entity?project=two&code=A'),
                           dict(search_type='contract/entity',query='x'*257)]:
                with self.assertRaises(Fault):call('sources',**values)
            for changed in [dict(kind='text',binding='selection',search_type='contract/entity',field='name'),
                            dict(kind='text',binding='record',source_key=key,field='missing'),
                            dict(kind='text',binding='static',field='title')]:
                with self.assertRaises(Fault):call('preview',document=dict(name='bad_binding',title='Bad',blocks=[changed]),expected_revision=state['revision'])

    def test_zero_false_and_null_filters_match_metric_table_and_native_query(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            for search_type,column,relation,value in [('contract/entity','amount','=',0),('contract/entity','amount','=',None),
                    ('contract/entity','amount','!=',None),('sthpw/project','is_template','=',False)]:
                with self.subTest(value=value,relation=relation):
                    condition=dict(column=column,relation=relation,value=value)
                    preview=call('preview',document=dict(name='typed_filters',title='Typed',blocks=[
                        dict(kind='metric',search_type=search_type,filters=[condition]),dict(kind='table',search_type=search_type,filters=[condition])]),
                        expected_revision=call('read')['revision'])
                    metric,table=preview['model']['layoutNodes']
                    filters=table['table']['filters']
                    native=ast.literal_eval(proxy.query(auth,search_type,filters))
                    nested=proxy.execute_cmd(auth,'tactic.ui.table.NestedTableReadCmd',dict(search_type=search_type,
                        view='table',parent_key='sthpw/project?code=one',project_scope=not search_type.startswith('sthpw/'),filters=filters,limit=50))['info']['records']
                    self.assertEqual(metric['value'],len(native))
                    self.assertEqual({row['__search_key__'] for row in native},{row['__search_key__'] for row in nested})

    def test_native_page_editor_transport_reads_real_types_and_saves(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[3]/'TH/thlib/ui/admin/dashboard_api.py').read_text(encoding='utf-8')
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            def native(**arguments):
                code=source+'\nreturn dashboard_editor_request(**'+repr(arguments)+')'
                value=proxy.execute_python_script(auth,None,dict(code=code))['info']
                return json.loads(value)
            state=native(action='list',project_code='one')
            self.assertTrue(state['canWrite'])
            self.assertTrue(all('/' in row['value'] for row in state['metadata']['searchTypes']))
            saved=native(action='save',project_code='one',document=dict(name='native_canvas',title='Native',blocks=[]),
                         expected_revision=state['metadata']['revision'],operation_id=str(uuid4()))
            self.assertEqual(saved['identity'],'native_canvas')
            self.assertEqual(saved['document']['blocks'],[])
            self.assertEqual(saved['metadata']['compiled']['layoutNodes'],[])
            state=native(action='list',project_code='one')
            detail_document=dict(name='native_details',title='Native details',blocks=[
                dict(kind='items',search_type='contract/entity',view='continuous_example',filters=[dict(column='code',value='A')]),
                dict(kind='details',children=[dict(kind='column',search_type='contract/entity',children=[dict(kind='text',title='Code',field='code')])])])
            preview=native(action='preview',project_code='one',document=detail_document,
                expected_revision=state['metadata']['revision'],detail_key='contract/entity?project=one&code=A')
            self.assertEqual(preview['model']['layoutDetail']['layoutNodes'][0]['children'][0]['text'],'Code: A')
    def test_canvas_spacing_blank_drafts_and_revisioned_save(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            draft=dict(name='canvas',title='Canvas',blocks=[])
            self.assertEqual(call('preview',document=draft,expected_revision=state['revision'])['model']['layoutNodes'],[])
            draft['blocks']=[dict(kind='column',height=320,gap=12,padding=[4,8,12,16],margin=[1,2,3,4],
                children=[dict(kind='text',text='Status',width=240,height=48)])]
            payload=dict(document=draft,expected_revision=state['revision'])
            preview=call('preview',**payload)
            group=preview['model']['layoutNodes'][0]
            self.assertEqual((group['height'],group['gap'],group['padding']),(320,12,[4,8,12,16]))
            self.assertEqual(group['children'][0]['editorPath'],[0,0])
            self.assertEqual(group['children'][0]['width'],'240px')
            operation=str(uuid4())
            saved=call('apply',operation_id=operation,**payload)
            self.assertEqual(call('apply',operation_id=operation,**payload),saved)
            self.assertEqual(call('read',name='canvas')['document'],preview['document'])
            for field,value in [('padding',[-1,0,0,0]),('margin',[0,0,0]),('gap',129),('width',True)]:
                invalid=dict(name='bad_canvas',title='Bad',blocks=[dict(kind='text',text='Bad',**{field:value})])
                with self.assertRaises(Fault):
                    call('preview',document=invalid,expected_revision=call('read')['revision'])
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

    def test_items_brick_reuses_project_records_and_native_navigation(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            def call(action,**values):return proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            draft=dict(name='native_items',title='Project work',blocks=[dict(kind='items',search_type='contract/entity',height=600,filters=[dict(column='code',value='A')])])
            preview=call('preview',document=draft,expected_revision=state['revision'])
            scope=preview['model']['layoutItems']
            self.assertEqual(scope,preview['model']['layoutNodes'][0]['items'])
            self.assertEqual(scope['searchType'],'contract/entity')
            page=proxy.execute_cmd(auth,'tactic.ui.table.NestedTableReadCmd',dict(search_type=scope['searchType'],view=scope['view'],parent_key=scope['parentKey'],project_scope=True,filters=scope['filters']))['info']
            self.assertEqual([row['code'] for row in page['records']],['A'])
            saved=call('apply',document=draft,expected_revision=state['revision'],operation_id=str(uuid4()))
            compiled=proxy.execute_cmd(auth,'tactic.ui.table.CustomLayoutReadCmd',dict(view=saved['view']))['info']
            self.assertEqual(compiled['layoutItems'],scope)
            target=proxy.execute_cmd(auth,'tactic.ui.panel.custom_url_cmd.CustomUrlCmd',dict(action='resolve',path=saved['path'],parameters={}))['info']
            self.assertEqual(target['search_type'],'contract/entity')
            state=call('read');draft['blocks'].append(dict(draft['blocks'][0]))
            with self.assertRaises(Fault):call('preview',document=draft,expected_revision=state['revision'])

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

    def test_details_follow_selected_record_and_keep_native_tree_scope(self):
        from xmlrpc.client import Fault
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            call=lambda action,**values:proxy.execute_cmd(auth,COMMAND,dict(action=action,project_code='one',**values))['info']
            state=call('read')
            draft=dict(name='selection_details',title='Selected work',blocks=[dict(kind='row',children=[
                dict(kind='items',search_type='contract/entity',weight=4),
                dict(kind='details',weight=8,children=[dict(kind='column',search_type='contract/entity',children=[
                    dict(kind='text',title='Code',field='code'),
                    dict(kind='markdown',title='Goal',text='First section'),
                    dict(kind='markdown',title='Result',text='Second section'),
                    dict(kind='table',search_type='contract/entity',controls=['search'])])])])])
            preview=call('preview',document=draft,expected_revision=state['revision'])
            self.assertEqual(preview['model']['layoutItems']['searchType'],'contract/entity')
            self.assertNotIn('layoutDetail',preview['model'])
            from copy import deepcopy
            edited=deepcopy(draft)
            edited['blocks'][0]['children'][1]['children'][0]['children'][0]['title']='Draft code'
            resolved=call('preview',document=edited,expected_revision=state['revision'],detail_key='contract/entity?project=one&code=A')
            self.assertTrue(resolved['model']['layoutHasDetails'])
            self.assertEqual(resolved['model']['layoutDetail']['layoutNodes'][0]['children'][0]['text'],'Draft code: A')
            with self.assertRaises(Fault):
                call('preview',document=edited,expected_revision=state['revision'],detail_key='contract/entity?project=two&code=A')
            saved=call('apply',document=draft,expected_revision=state['revision'],operation_id=str(uuid4()))
            read=lambda key:proxy.execute_cmd(auth,'tactic.ui.table.CustomLayoutReadCmd',dict(view=saved['view'],detail_key=key))['info']
            details=read('contract/entity?project=one&code=A')
            self.assertEqual(details['layoutNodes'][0]['children'][0]['text'],'Code: A')
            self.assertEqual(details['layoutNodes'][0]['children'][1]['text'],'## Goal\n\nFirst section')
            self.assertEqual(details['layoutNodes'][0]['children'][2]['text'],'## Result\n\nSecond section')
            self.assertEqual(details['layoutNodes'][0]['children'][3]['table']['parentKey'],details['targetSearchKey'])
            self.assertEqual(details['layoutNodes'][0]['children'][2]['editorPath'],[0,1,0,2])
            self.assertNotIn('layoutItems',details,'detail refresh cannot replace the tree')
            with self.assertRaises(Fault):read('contract/entity?project=two&code=A')
            for invalid in (dict(kind='text',field='missing'),dict(kind='details',children=[dict(kind='text',text='nested')])):
                draft['blocks'][0]['children'][1]['children'][0]['children']=[invalid]
                with self.assertRaises(Fault):call('preview',document=draft,expected_revision=call('read')['revision'])

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
                source=(await client.call_tool('ts_dashboard_sources',dict(search_type='contract/entity'))).structured_content
                self.assertTrue(any(row['value']=='amount' for row in source['fields']))
                state=(await client.call_tool('ts_dashboard_read',{})).structured_content
                draft=document();draft['name']='via_mcp'
                draft['blocks'].append(dict(kind='text',title='Project',binding='project',field='title'))
                draft['blocks'][0]['children'][0]['filters']=[dict(column=next(row['value'] for row in source['fields'] if row['value']=='amount'),relation='=',value=0)]
                values=dict(document=draft,expected_revision=state['revision'])
                preview=await client.call_tool('ts_dashboard_preview',values)
                self.assertFalse(preview.is_error)
                self.assertEqual(preview.structured_content['model']['layoutNodes'][-1]['text'],'Project: One')
                draft['filters']=[dict(name='minimum',title='Minimum amount',search_type='contract/entity',column='amount',relation='>=',value=0,enabled=True)]
                draft['blocks'].append(dict(kind='chart',title='Amounts',search_type='contract/entity',group_by=[dict(column='amount')],
                    aggregates=[dict(name='total',title='Total',function='sum',column='amount')]))
                preview=await client.call_tool('ts_dashboard_preview',dict(values,filter_values={'minimum':dict(enabled=True,value=1)}))
                self.assertFalse(preview.is_error)
                self.assertEqual(preview.structured_content['model']['layoutNodes'][-1]['report']['rows'],[dict(group_0=7,total=7)])
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
        draft['blocks'][1]['kind']='items'
        draft['blocks'][1]=dict(kind='row',children=[draft['blocks'][1],dict(kind='details',children=[
            dict(kind='column',search_type='contract/entity',children=[dict(kind='text',field='code')])])])
        draft['filters']=[dict(name='minimum',title='Minimum amount',search_type='contract/entity',column='amount',relation='>=',value=0,enabled=True)]
        draft['blocks'].append(dict(kind='summary',title='Amounts',search_type='contract/entity',group_by=[dict(column='amount')],
            aggregates=[dict(name='total',title='Total',function='sum',column='amount')]))

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
                    name,arguments='ts_dashboard_save',dict(values,operation_id=operation)
                elif step==4:
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
        connection.command('request','submit',request_id=request_id,host_id=host,document=dict(prompt='Create a dashboard with a count and our existing expandable item view.',allow_changes=True,provider=profile['id'],model='fixture-model',context=dict(client='TS',project='one',page='entities',title='Entities',search_type='contract/entity',view='table',search_keys=[])))
        request=connection.command('request','claim',host_id=host)['request']
        options=SimpleNamespace(allow_changes=True,stream_root=Path(__file__).resolve().parents[1],handler_root=None,trial_image=None,trial_directory=None)
        asyncio.run(run_provider(connection,request,profile,host,options,lambda:None,task_prompt,message_inputs))
        saved=connection.command('request','read',request_id=request_id)
        self.assertEqual((saved['status'],saved['outcome']),('completed','completed'))
        self.assertEqual(len(requests),5)
        self.assertNotIn(ticket,json.dumps(requests))
        self.assertEqual(connection.command('dashboard','read',name='chat_dashboard')['document']['name'],'chat_dashboard')
        compiled=connection.request('/admin/rpc',dict(method='execute_cmd',args=[dict(ticket=ticket,project='one'),'tactic.ui.table.CustomLayoutReadCmd',dict(view='dashboard.chat_dashboard')],kwargs={}))['result']['info']
        self.assertEqual(compiled['layoutItems']['searchType'],'contract/entity')
        self.assertEqual(compiled['layoutNodes'][1]['kind'],'row')
        self.assertEqual(compiled['layoutNodes'][1]['children'][1]['kind'],'details')
        self.assertEqual(compiled['layoutNodes'][-1]['report']['rows'],[dict(group_0=0,total=0),dict(group_0=7,total=7)])
        tools={row['function']['name']:row['function']['parameters'] for row in requests[0]['tools']}
        self.assertIn('ts_dashboard_save',tools)
        self.assertIn('name',tools['ts_dashboard_read']['properties'])
        # Model writes remain unavailable when the chat's changes permission is off.
        from tactic_stream.admin_agent import create_server
        from mcp import Client
        async def check_readonly():
            async with Client(create_server(connection,options.stream_root,request_id=request_id)) as client:
                self.assertNotIn('ts_dashboard_save',{tool.name for tool in (await client.list_tools()).tools})
        asyncio.run(check_readonly())
