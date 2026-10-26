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

    def test_attachment_only_messages_and_private_thumbnail(self):
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (640, 360), 'red').save(buffer, 'PNG')
        file = self.attachment(buffer.getvalue(), 'image.png')
        with self.assertRaisesRegex(ValueError, 'message or attach'):
            self.submit(document=dict(self.document, prompt=''))
        row, _ = self.submit(document=dict(self.document, prompt='', attachments=[file['attachment_id']]))
        self.assertEqual(row['messages'][0]['text'], '')
        self.assertTrue(self.call('state')['requests'][0]['prompt'])
        preview = self.command('attachment', 'preview', attachment_id=file['attachment_id'])
        raw = base64.b64decode(preview['url'].split(',', 1)[1])
        with Image.open(io.BytesIO(raw)) as image:
            self.assertEqual(image.size, (320, 180))
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False, steering=True))
        self.call('claim', host_id=self.host)
        follow = self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='', attachments=[file['attachment_id']])
        self.assertEqual(len(follow['messages']), 2)
        from tactic_stream.agent_host import message_inputs
        from tactic_stream.admin_agent import StreamConnection
        connection = StreamConnection('http://example.invalid', 'one', 'private-fixture')
        with patch.object(connection, 'command', side_effect=self.command):
            inputs = message_inputs(connection, follow['messages'][-1:])
        self.assertTrue(any(item['type'] == 'image' for item in inputs))
        self.assertFalse(any(item['type'] == 'text' and not item['text'] for item in inputs))

    def test_repeated_named_images_keep_original_extensions_and_root_aliases(self):
        from PIL import Image
        from pathlib import Path
        self.document['allow_changes'] = True
        files = []
        for color in ('red', 'blue', 'green'):
            buffer = io.BytesIO()
            Image.new('RGBA', (320, 180), color).save(buffer, 'PNG')
            files.append(self.attachment(buffer.getvalue(), 'image.png'))
        rows = self.api.dispatch('query', (self.auth, 'config/naming'), {'filters': [('search_type', 'cg/shot')]})
        rows = ast.literal_eval(rows) if isinstance(rows, str) else rows
        self.assertTrue(rows)
        for rule in rows:
            self.api.dispatch('update', (self.auth, rule['__search_key__'], dict(dir_naming='{sobject.relative_dir}',
                file_naming='{sobject.name}_v{version}.{ext}', checkin_type='auto')))
        row, _ = self.submit(document=dict(self.document, attachments=[file['attachment_id'] for file in files]))
        self.call('claim', host_id=self.host)
        common = dict(request_id=row['request_id'])
        state = self.command('editing', 'workflow_read', search_type='cg/shot', **common)
        self.command('editing', 'workflow_apply', search_type='cg/shot', expected_revision=state['revision'],
            operation_id=str(uuid4()), processes=['reference'], search_keys=self.document['context']['search_keys'], **common)
        arguments = dict(search_key=self.document['context']['search_keys'][0], process='reference',
            attachments=[file['attachment_id'] for file in files], operation_id=str(uuid4()), **common)
        result = self.command('editing', 'checkin', **arguments)
        self.assertEqual(result, self.command('editing', 'checkin', **arguments))
        self.assertEqual(len(result['snapshots']), 3)
        checked = self.api.dispatch('query', (self.auth, 'sthpw/file'))
        checked = ast.literal_eval(checked) if isinstance(checked, str) else checked
        self.assertFalse(any(Path(file['file_name']).suffix == '.data' for file in checked))
        for file in checked:
            self.assertTrue(Path(file['checkin_dir'], file['file_name']).is_file(), file)
        buffer = io.BytesIO()
        Image.new('RGB', (320, 180), 'yellow').save(buffer, 'JPEG')
        extra = self.attachment(buffer.getvalue(), 'downloaded.jpg')
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False, steering=True))
        self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='Add this reference', attachments=[extra['attachment_id']])
        # This naming rule shares preview paths across extensions: continue its existing series.
        appended = self.command('editing', 'checkin', **dict(arguments, attachments=[extra['attachment_id']],
            context='reference/image.png', operation_id=str(uuid4())))
        self.assertEqual(len(appended['snapshots']), 1)
        history = self.command('editing', 'snapshots', search_key=arguments['search_key'], process='reference', **common)
        self.assertTrue(all(file['exists'] for file in history['rows'] if file['rowType'] == 'file'))
        self.assertTrue(any(snapshot['context'] == 'reference/image.png' and snapshot['version'] == 4 for snapshot in history['snapshots']))
        with self.assertRaisesRegex(ValueError, 'chosen process'):
            self.command('editing', 'checkin', **dict(arguments, context='model/other', operation_id=str(uuid4())))

    def test_web_search_permission_only_changes_native_search(self):
        from tactic_stream.agent_host import codex_command, task_prompt
        from tactic_stream.admin_agent import StreamConnection
        connection = StreamConnection('http://example.invalid', 'one', 'private-fixture')
        with self.assertRaisesRegex(ValueError, 'does not support web'):
            self.submit(document=dict(self.document, allow_web=True))
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False, web_search=True))
        row, _ = self.submit(document=dict(self.document, allow_web=True))
        command = codex_command(connection, row, fixture.ROOT, None, '.')
        self.assertIn('web_search="live"', command)
        self.assertIn('--allow-web-download', str(command))
        self.assertIn('features.shell_tool=false', command)
        self.assertIn('user allows native web search', task_prompt(row))
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False))
        with self.assertRaisesRegex(ValueError, 'does not support web'):
            self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='Continue')


if __name__ == '__main__':
    unittest.main()
