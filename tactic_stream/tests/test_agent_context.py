"""Cross-project chat references retain ownership, message history and permissions."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests import test_agent_requests as fixture
try:
    from mcp import Client
    from tactic_stream.admin_agent import COMMANDS, StreamConnection, create_server
except ImportError:
    Client = None


@unittest.skipIf(Client is None, 'Install tactic-stream[agent] for conversation tools')
class AgentContext(unittest.TestCase):
    setUp = fixture.AgentRequests.setUp
    call = fixture.AgentRequests.call
    submit = fixture.AgentRequests.submit

    def source(self):
        self.document.update(prompt='Create tracker other with tasks and plans',allow_changes=True)
        row,_=self.submit()
        self.call('claim',host_id=self.host)
        return self.call('update',request_id=row['request_id'],host_id=self.host,status='completed',
                         answer='Created other. Remaining: custom pages. '+('Reference detail. '*600))

    def target(self):
        self.api.dispatch('execute_cmd',(dict(self.auth,project='admin'),'tactic.command.CreateProjectCmd',
            dict(project_code='other',project_title='Other project')))
        self.target_auth=dict(self.auth,project='other')
        context=dict(self.document['context'],project='other',search_type='',page='',title='',search_keys=[])
        return self.other('draft',request_id=str(uuid4()),context=context)

    def other(self,action,**values):
        return self.api.dispatch('execute_cmd',(self.target_auth,fixture.COMMAND,
            dict(action=action,project_code='other',**values)))['info']

    def test_link_and_read_old_task_without_copying_scope_or_authorization(self):
        source=self.source();target=self.target()
        before=deepcopy(target)
        args=dict(request_id=target['request_id'],source_project='one',source_request=source['request_id'])
        linked=self.other('link_source',**args)
        from tactic_stream.agent_host import task_prompt
        self.assertIn(source['request_id'],task_prompt(linked))
        self.assertEqual(linked['document'],before['document'])
        self.assertFalse(linked['document']['allow_changes'])
        self.assertEqual(linked['messages'],before['messages'])
        self.assertEqual(self.other('link_source',**args),linked)
        found=self.other('history_search',query='other')['requests']
        self.assertTrue(any(row['request_id']==source['request_id'] and row['project']=='one' for row in found))
        parts=[];offset=0
        while True:
            page=self.other('history_read',source_project='one',source_request=source['request_id'],offset=offset)
            self.assertLessEqual(len(page['text']),6000)
            parts.append(page['text'])
            if page['next_offset'] is None:break
            offset=page['next_offset']
        text=''.join(parts)
        self.assertIn('Create tracker other',text)
        self.assertIn('Remaining: custom pages',text)
        self.assertEqual(self.call('read',request_id=source['request_id'])['messages'],source['messages'])
        self.other('heartbeat',host_id=self.host,label='Fixture',capabilities=dict(changes=True,trials=False))
        saved=self.other('submit',request_id=target['request_id'],host_id=self.host,
            document=dict(linked['document'],prompt='Continue'))
        self.assertEqual(saved['related_conversations'],linked['related_conversations'])
        with self.assertRaisesRegex(ValueError,'current turn'):self.other('link_source',**args)

    def test_private_sources_missing_projects_and_invalid_offsets_are_refused(self):
        from pyasm.search.search import RequestContext,request_context
        from pyasm.search import Search
        from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
        source=self.source();target=self.target()
        with request_context(RequestContext(self.store,'admin','one')):
            self.api.auth.bind_security('admin',self.auth['ticket'])
            cmd=AgentRequestCmd();cmd.owner='another-user';cmd.sql=Search('config/trigger').get_sql()
            private=dict(deepcopy(source),request_id=str(uuid4()))
            cmd.save('spt_agent_request',private['request_id'],private)
        for action in ('history_read','link_source'):
            with self.assertRaisesRegex(ValueError,'unavailable'):
                self.other(action,request_id=target['request_id'],source_project='one',source_request=private['request_id'])
        with self.assertRaises(ValueError):self.other('history_read',source_project='one',source_request=source['request_id'],offset=-1)
        with self.assertRaises(LookupError):self.other('history_read',source_project='missing',source_request=source['request_id'])
        with self.assertRaisesRegex(ValueError,'another conversation'):
            self.other('link_source',request_id=target['request_id'],source_project='other',source_request=target['request_id'])

    def test_real_mcp_catalogue_finds_previous_task_and_reports_linked_context(self):
        source=self.source();target=self.target()
        self.other('link_source',request_id=target['request_id'],source_project='one',source_request=source['request_id'])
        connection=StreamConnection('http://fixture.invalid','other','private-fixture')
        def command(owner,action,**values):
            return self.api.dispatch('execute_cmd',(self.target_auth,COMMANDS[owner],
                dict(action=action,project_code='other',**values)))['info']
        async def run():
            server=create_server(connection,fixture.ROOT,request_id=target['request_id'])
            async with Client(server) as client:
                context=await client.call_tool('agent_context',{})
                self.assertFalse(context.is_error)
                context=context.structured_content
                self.assertEqual(context['context']['project'],'other')
                self.assertFalse(context['allow_changes'])
                self.assertEqual(context['project_rules'], {})
                self.assertEqual(context['related_conversations'][0]['request_id'],source['request_id'])
                found=await client.call_tool('agent_conversations',dict(query='other'))
                self.assertFalse(found.is_error)
                self.assertEqual(found.structured_content['requests'][0]['request_id'],source['request_id'])
                read=await client.call_tool('agent_conversation_read',dict(project='one',conversation_id=source['request_id']))
                self.assertFalse(read.is_error)
                self.assertIn('Create tracker other',read.structured_content['text'])
        with patch.object(connection,'command',side_effect=command):asyncio.run(run())
