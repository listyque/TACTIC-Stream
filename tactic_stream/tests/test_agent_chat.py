"""Conversation delivery, private files and actual native editing/check-in."""
import base64
import ast
import io
import mimetypes
from copy import deepcopy
import unittest
from uuid import uuid4
from unittest.mock import patch

from tests import test_agent_requests as fixture


class AgentChat(unittest.TestCase):
    setUp = fixture.AgentRequests.setUp
    call = fixture.AgentRequests.call
    submit = fixture.AgentRequests.submit

    def attachment(self, content=b'agent reference\n', name='reference.txt'):
        code = str(uuid4())
        self.command('attachment', 'start', attachment_id=code, name=name, size=len(content), media_type=mimetypes.guess_type(name)[0] or '')
        arguments = dict(attachment_id=code, offset=0, data=base64.b64encode(content).decode())
        self.command('attachment', 'append', **arguments)
        self.command('attachment', 'append', **arguments)
        return self.command('attachment', 'finish', attachment_id=code)

    def command(self, owner, action, **values):
        from tactic_stream.admin_agent import COMMANDS
        return self.api.dispatch('execute_cmd', (self.auth, COMMANDS[owner], dict(action=action, project_code='one', **values)))['info']

    def test_messages_models_private_files_and_completion_race(self):
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False, steering=True, models=[dict(id='available', label='Available')]))
        file = self.attachment()
        document = dict(self.document, attachments=[file['attachment_id']], model='available')
        request, _ = self.submit(document=document)
        self.call('claim', host_id=self.host)
        message = dict(request_id=request['request_id'], message_id=str(uuid4()), text='Use the second option', attachments=[])
        self.call('message', **message)
        self.call('message', **message)
        result = self.call('update', request_id=request['request_id'], host_id=self.host, status='completed', answer='First answer', outcome='needs_input')
        self.assertEqual(result['status'], 'queued')
        self.assertEqual(len(result['messages']), 3)
        self.call('claim', host_id=self.host)
        self.call('ack', request_id=request['request_id'], host_id=self.host, message_ids=[message['message_id']])
        result = self.call('update', request_id=request['request_id'], host_id=self.host, status='completed', answer='Finished')
        self.assertEqual(result['status'], 'completed')
        with self.assertRaisesRegex(ValueError, 'model'):
            self.submit(document=dict(self.document, model='invented'))
        with self.assertRaisesRegex(ValueError, 'different'):
            self.call('message', **dict(message, text='Different'))

    def test_workflow_assignment_real_checkin_and_durable_replay(self):
        self.document['allow_changes'] = True
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (64, 64), 'red').save(buffer, 'PNG')
        file = self.attachment(buffer.getvalue(), 'reference.png')
        request, _ = self.submit(document=dict(self.document, attachments=[file['attachment_id']]))
        self.call('claim', host_id=self.host)
        common = dict(request_id=request['request_id'])
        state = self.command('editing', 'workflow_read', search_type='cg/shot', **common)
        operation = dict(search_type='cg/shot', expected_revision=state['revision'], operation_id=str(uuid4()),
                         processes=['reference', 'model', 'texture', 'rig'], name='Agent references',
                         search_keys=self.document['context']['search_keys'], **common)
        pipeline = self.command('editing', 'workflow_apply', **operation)
        self.assertEqual(self.command('editing', 'workflow_apply', **operation), pipeline)
        checked = dict(search_key=self.document['context']['search_keys'][0], process='reference',
                       attachments=[file['attachment_id']], operation_id=str(uuid4()), **common)
        snapshot = self.command('editing', 'checkin', **checked)
        self.assertEqual(self.command('editing', 'checkin', **checked), snapshot)
        self.assertEqual(len(snapshot['snapshots']), 1)
        rows = self.api.dispatch('query', (self.auth, 'sthpw/file'))
        rows = ast.literal_eval(rows) if isinstance(rows, str) else rows
        self.assertTrue({'main', 'web', 'icon'} <= {item['type'] for item in rows})

    def test_guarded_field_undo_refuses_later_edits_and_replays(self):
        self.document['allow_changes'] = True
        request, _ = self.submit()
        self.call('claim', host_id=self.host)
        common = dict(request_id=request['request_id'])
        item = self.command('editing', 'records', search_type='cg/shot', filters={}, **common)['objects'][0]
        operation = str(uuid4())
        self.command('editing', 'patch', search_key=item['__search_key__'], values=dict(description='Agent edited'),
                     expected_revision=item['revision'], operation_id=operation, **common)
        self.call('update', host_id=self.host, status='completed', answer='Done', **common)
        self.api.dispatch('update', (self.auth, item['__search_key__'], dict(description='User edited')))
        with self.assertRaisesRegex(ValueError, 'changed after'):
            self.call('undo', operation_id=operation, **common)
        self.api.dispatch('update', (self.auth, item['__search_key__'], dict(description='Agent edited')))
        self.call('undo', operation_id=operation, **common)
        self.call('undo', operation_id=operation, **common)
        restored = self.command('editing', 'records', search_type='cg/shot', filters=dict(code=item['code']), **common)['objects'][0]
        self.assertEqual(restored['description'], item.get('description'))

    def test_followup_preserves_the_answer_of_an_old_request(self):
        from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
        request, _ = self.submit()
        self.call('claim', host_id=self.host)
        self.call('update', request_id=request['request_id'], host_id=self.host, status='completed', answer='Original answer')
        load = AgentRequestCmd.load

        def legacy(command, table, code, missing=False):
            row = load(command, table, code, missing)
            if row and table == 'spt_agent_request':
                row.pop('messages', None)
            return row

        with patch.object(AgentRequestCmd, 'load', legacy):
            current = self.call('message', request_id=request['request_id'], message_id=str(uuid4()), text='Continue', attachments=[])
        self.assertEqual([message['role'] for message in current['messages']], ['user', 'assistant', 'user'])
        self.assertEqual(current['messages'][1]['text'], 'Original answer')

    def test_add_workflow_to_an_existing_asset_without_pipeline_column(self):
        self.api.dispatch('execute_cmd', (self.auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
            database='one', namespace='one', schema='public', search_type_name='agent_asset',
            asset_title='Agent asset', asset_description='', sobject_pipeline=False)))
        asset = self.api.dispatch('insert', (self.auth, 'one/agent_asset', dict(code='DRONE', name='Delivery drone')))
        asset = ast.literal_eval(asset) if isinstance(asset, str) else asset
        self.document['allow_changes'] = True
        self.document['context'].update(search_type='one/agent_asset', search_keys=[asset['__search_key__']])
        request, _ = self.submit()
        self.call('claim', host_id=self.host)
        common = dict(request_id=request['request_id'], search_type='one/agent_asset')
        state = self.command('editing', 'workflow_read', **common)
        self.assertNotIn('pipeline_code', state['columns'])
        result = self.command('editing', 'workflow_apply', **common, expected_revision=state['revision'],
            operation_id=str(uuid4()), processes=['reference', 'model', 'texture', 'rig'], search_keys=[asset['__search_key__']])
        state = self.command('editing', 'workflow_read', **common)
        self.assertIn('pipeline_code', state['columns'])
        self.assertEqual(state['objects'][0]['pipeline_code'], result['identity'])

    def test_image_transfer_keeps_bytes_and_checks_integrity(self):
        from tactic_stream.admin_agent import StreamConnection
        file = self.attachment(b'original image bytes', 'fixture.png')
        connection = StreamConnection('http://example.invalid', 'one', 'private-fixture')
        with patch.object(connection, 'command', side_effect=self.command):
            _, data = connection.attachment_bytes(file['attachment_id'])
        self.assertEqual(data, b'original image bytes')


if __name__ == '__main__':
    unittest.main()
