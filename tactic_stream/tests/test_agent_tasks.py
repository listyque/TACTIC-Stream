"""Agent task scopes and status packets use the ordinary native table command."""
import ast
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests import test_agent_chat as fixture


class AgentTasks(unittest.TestCase):
    call = fixture.AgentChat.call
    command = fixture.AgentChat.command
    submit = fixture.AgentChat.submit

    def record(self, method, *args, **kwargs):
        result = self.api.dispatch(method, (self.auth, *args), kwargs)
        return ast.literal_eval(result) if isinstance(result, str) else result

    def setUp(self):
        fixture.AgentChat.setUp(self)
        from tactic.core.bootstrap import CoreInit
        from pyasm.search.search import RequestContext, request_context
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            CoreInit().execute()
        for trigger in self.record('query', 'config/trigger'):
            if trigger.get('script_path'):
                self.record('update', trigger['__search_key__'], dict(s_status='retired'), triggers=False)
        self.record('insert', 'sthpw/pipeline', dict(code='one/task_statuses', project_code='one',
            pipeline='<pipeline><process name="Start" completion="0"/><process name="Ready" completion="100"/><connect from="Start" to="Ready"/></pipeline>'))
        self.record('insert', 'sthpw/pipeline', dict(code='one/asset_work', project_code='one',
            pipeline='<pipeline><process name="model" task_pipeline="one/task_statuses"/></pipeline>'))
        self.assets = [self.record('insert','cg/assets',dict(code='TASK_ASSET_'+str(index),name='Asset '+str(index),
            pipeline_code='one/asset_work'),triggers=False) for index in range(3)]
        self.tasks = [self.record('create_task',asset['__search_key__'],process='model') for asset in self.assets]
        self.tasks.append(self.record('create_task',self.assets[0]['__search_key__'],process='model',subcontext='variant'))
        for task in self.tasks:
            self.record('update', task['__search_key__'], dict(status='Start'))
        self.episode = self.record('query','cg/scenes')[0]
        self.record('execute_cmd','tactic.command.sobject_link_cmd.SObjectLinkCmd',dict(
            parent_key=self.episode['__search_key__'],search_type='cg/assets',path='',
            insert_search_keys=[asset['__search_key__'] for asset in self.assets[:2]],exclude_search_keys=[]))
        self.document['allow_changes'] = True
        self.document['context'].update(search_type='cg/scenes',search_keys=[self.episode['__search_key__']])
        self.request,_ = self.submit()
        self.call('claim',host_id=self.host)
        self.common = dict(request_id=self.request['request_id'])

    def read(self, **values):
        return self.command('editing','tasks_read',related_type='cg/assets',**self.common,**values)

    def changes(self, read=None):
        return [dict(task_key=row['task_key'],status='Ready',expected_revision=row['expected_revision'])
                for row in (read or self.read())['tasks']]

    def test_linked_asset_tasks_native_status_journal_and_replay(self):
        state=self.read()
        self.assertEqual(len(state['tasks']),3)
        self.assertEqual({row['parent_title'] for row in state['tasks']},{'Asset 0','Asset 1'})
        self.assertEqual({row['completion'] for row in state['workflows']['one/task_statuses']['statuses']},{'0','100'})
        self.assertEqual(state['workflows']['one/task_statuses']['connections'],[dict(source='Start',target='Ready')])
        changes=self.changes(state)
        result=self.command('editing','task_status',changes=changes,**self.common)
        self.assertEqual(result['count'],3)
        self.assertTrue(all(row['status']=='Ready' for row in result['tasks']))
        before=self.record('query','sthpw/status_log')
        self.assertEqual(result,self.command('editing','task_status',changes=changes,**self.common))
        self.assertEqual(self.record('query','sthpw/status_log'),before)
        self.assertEqual(self.record('query','sthpw/task',filters=[('code',self.tasks[2]['code'])])[0]['status'],'Start')
        self.assertEqual(len([row for row in before if row.get('to_status')=='Ready'
                              and row.get('search_type','').split('?')[0]=='sthpw/task']),3)
        self.record('update',changes[0]['task_key'],dict(status='Start'))
        with self.assertRaisesRegex(ValueError,'changed after'):
            self.command('editing','task_status',changes=changes,**self.common)

    def test_preflight_conflicts_invalid_status_and_native_field_permissions(self):
        changes=self.changes()
        invalid=deepcopy(changes);invalid[-1]['status']='invented'
        with self.assertRaisesRegex(ValueError,'status is not accessible'):
            self.command('editing','task_status',changes=invalid,**self.common)
        self.assertTrue(all(row['status']=='Start' for row in self.read()['tasks']))
        with patch('tactic.ui.table.task_inspector.task_fields',return_value=[dict(name='status',editable=False)]):
            with self.assertRaisesRegex(ValueError,'read-only'):
                self.command('editing','task_status',changes=changes,**self.common)
        self.record('update',changes[-1]['task_key'],dict(description='Concurrent user edit'))
        with self.assertRaisesRegex(Exception,'Tasks changed'):
            self.command('editing','task_status',changes=changes,**self.common)
        self.assertTrue(all(row['status']=='Start' for row in self.read()['tasks']))

    def test_project_type_selection_and_conversation_authorization(self):
        for values in (dict(search_keys=[self.assets[0]['__search_key__'].replace('project=one','project=foreign')]),dict(offset=-1)):
            with self.assertRaises((ValueError, LookupError)):self.read(**values)
        with self.assertRaisesRegex(ValueError,'existing task'):
            self.command('editing','task_status',changes=[dict(task_key=self.assets[0]['__search_key__'],status='Ready',expected_revision='x')],**self.common)
        readonly,_=self.submit(document=dict(self.document,allow_changes=False))
        self.call('update',request_id=self.request['request_id'],host_id=self.host,status='completed',answer='Read only test')
        self.call('claim',host_id=self.host)
        with self.assertRaisesRegex(ValueError,'authorize active changes'):
            self.command('editing','task_status',request_id=readonly['request_id'],changes=self.changes())

    def test_mcp_catalog_and_native_batch_without_operation_uuid(self):
        from mcp import Client
        from tactic_stream.admin_agent import create_server, StreamConnection
        from pathlib import Path
        connection=StreamConnection('http://example.invalid','one','private-fixture-ticket')
        async def run():
            for allowed in (False,True):
                server=create_server(connection,Path(__file__).resolve().parents[1],request_id=self.request['request_id'],allow_project_edit=allowed)
                async with Client(server) as client:
                    names={tool.name for tool in (await client.list_tools()).tools}
                    self.assertIn('ts_tasks_read',names)
                    self.assertEqual('ts_task_status_set' in names,allowed)
                    if allowed:
                        read=await client.call_tool('ts_tasks_read',dict(related_type='cg/assets'))
                        self.assertFalse(read.is_error,read.content)
                        result=await client.call_tool('ts_task_status_set',dict(changes=self.changes(read.structured_content)))
                        self.assertFalse(result.is_error,result.content)
                        self.assertEqual(result.structured_content['count'],3)
        with patch.object(connection,'command',side_effect=self.command):asyncio.run(run())

    def test_imported_native_task_callbacks_keep_the_bound_project(self):
        paths={'tasks/in_progress_status_handle','tasks/storyboard_status_handle',
               'tasks/layout_status_handle','tasks/scripts_shorts_status_handle'}
        enabled=[]
        for trigger in self.record('query','config/trigger',show_retired=True):
            if trigger.get('script_path') in paths:
                self.record('update',trigger['__search_key__'],dict(s_status=''),triggers=False)
                enabled.append(trigger['script_path'])
        self.assertEqual(set(enabled),paths)
        result=self.command('editing','task_status',changes=self.changes(),**self.common)
        self.assertEqual(result['count'],3)
