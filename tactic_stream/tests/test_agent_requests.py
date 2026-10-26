"""Native request lifecycle, ownership and external-host boundaries on owned data."""
from copy import deepcopy
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from pyasm.common import Config
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.checkin_benchmark import prepare

COMMAND = 'tactic.ui.panel.agent_request_cmd.AgentRequestCmd'


class AgentRequests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='agent-requests-')
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start()
        self.addCleanup(environment.stop)
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(temporary.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one', language='python')
        self.host = str(uuid4())
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False))
        rows = self.api.dispatch('query', (self.auth, 'cg/shot'))
        item = (ast.literal_eval(rows) if isinstance(rows, str) else rows)[0]
        self.document = dict(prompt='Explain this selection', allow_changes=False,
            context=dict(client='TS', project='one', page='shots', title='Shots', search_type='cg/shot',
                         view='table', search_keys=[item['__search_key__']]))

    def call(self, action, **values):
        return Api(self.store).dispatch('execute_cmd', (self.auth, COMMAND,
            dict(action=action, project_code='one', **values)))['info']

    def submit(self, **values):
        arguments = dict(request_id=str(uuid4()), host_id=self.host, document=deepcopy(self.document))
        arguments.update(values)
        return self.call('submit', **arguments), arguments

    def test_model_effort_is_validated_retained_and_frozen_during_execution(self):
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True, trials=False,
            steering=True, models=[dict(id='fixture', label='Fixture', is_default=True, efforts=['low', 'high'])]))
        self.document.update(model='fixture', effort='high')
        row, arguments = self.submit()
        self.assertEqual(row['effort'], 'high')
        self.assertEqual(row, self.call('submit', **arguments))
        self.call('claim', host_id=self.host)
        with self.assertRaisesRegex(ValueError, 'current turn finishes'):
            self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='Correction', effort='low')
        self.call('update', request_id=row['request_id'], host_id=self.host, status='completed')
        for model, effort in [('fixture', 'ultra'), ('unknown', 'high')]:
            with self.assertRaisesRegex(ValueError, 'Choose a'):
                self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='Continue', model=model, effort=effort)
        resumed = self.call('message', request_id=row['request_id'], message_id=str(uuid4()), text='Continue', model='', effort='low')
        self.assertEqual(resumed['model'], '')
        self.assertEqual(resumed['effort'], 'low')
        self.assertEqual(self.call('claim', host_id=self.host)['request']['effort'], 'low')

    def test_replay_capture_claim_and_finished_request_are_durable(self):
        saved, arguments = self.submit()
        self.assertEqual(saved, self.call('submit', **arguments))
        changed = deepcopy(arguments)
        changed['document']['prompt'] = 'Different'
        with self.assertRaisesRegex(ValueError, 'different document'):
            self.call('submit', **changed)
        claimed = self.call('claim', host_id=self.host)['request']
        self.assertEqual(claimed['document'], self.document)
        selected = self.call('selection', request_id=saved['request_id'])['objects']
        self.assertEqual(selected[0]['__search_key__'], self.document['context']['search_keys'][0])
        self.assertNotIn('password', selected[0])
        self.assertEqual(self.call('claim', host_id=self.host), dict(request=None))
        result = self.call('update', host_id=self.host, request_id=saved['request_id'], status='completed', answer='Done')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.call('read', request_id=saved['request_id'])['answer'], 'Done')
        self.assertEqual(self.call('submit', **arguments)['status'], 'completed')
        self.assertEqual(self.call('claim', host_id=self.host), dict(request=None))
        with self.assertRaisesRegex(ValueError, 'already closed'):
            self.call('update', host_id=self.host, request_id=saved['request_id'], status='running')

    def test_cancel_before_and_during_execution_does_not_repeat(self):
        queued, _ = self.submit()
        self.assertEqual(self.call('cancel', request_id=queued['request_id'])['status'], 'cancelled')
        self.assertIsNone(self.call('claim', host_id=self.host)['request'])
        running, _ = self.submit()
        self.call('claim', host_id=self.host)
        self.assertEqual(self.call('cancel', request_id=running['request_id'])['status'], 'cancelling')
        self.assertEqual(self.call('update', host_id=self.host, request_id=running['request_id'])['status'], 'cancelling')
        self.assertEqual(self.call('update', host_id=self.host, request_id=running['request_id'], status='completed', answer='Already applied')['status'], 'cancelled')

    def test_expired_host_and_interrupted_request_require_explicit_recovery(self):
        saved, _ = self.submit()
        self.call('claim', host_id=self.host)
        import time
        with patch('tactic.ui.panel.agent_request_cmd.time.time', return_value=time.time() + 100):
            self.assertEqual(self.call('read', request_id=saved['request_id'])['status'], 'interrupted')
            self.assertEqual(self.call('state')['hosts'], [])
            with self.assertRaisesRegex(ValueError, 'offline'):
                self.submit()
        self.assertIsNone(self.call('claim', host_id=self.host)['request'])

    def test_foreign_host_project_selection_and_unknown_fields_are_rejected(self):
        saved, _ = self.submit()
        self.call('claim', host_id=self.host)
        with self.assertRaisesRegex(ValueError, 'another external host'):
            self.call('update', host_id=str(uuid4()), request_id=saved['request_id'])
        bad = deepcopy(self.document)
        bad['context']['project'] = 'other'
        with self.assertRaisesRegex(ValueError, 'project mismatch'):
            self.submit(document=bad)
        bad = deepcopy(self.document)
        bad['context']['ticket'] = 'never accept credentials in context'
        with self.assertRaisesRegex(ValueError, 'Invalid agent context'):
            self.submit(document=bad)
        bad = deepcopy(self.document)
        bad['context']['search_keys'] *= 201
        with self.assertRaisesRegex(ValueError, '200 distinct'):
            self.submit(document=bad)
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO task (code,project_code,search_type,search_code,process) VALUES ('FOREIGN_TASK','other','cg/shot','SH001','publish')")
        bad = deepcopy(self.document)
        bad['context']['search_keys'] = ['sthpw/task?code=FOREIGN_TASK']
        with self.assertRaisesRegex(ValueError, 'unavailable in this project'):
            self.submit(document=bad)

    def test_host_command_has_no_generic_execution_or_activation(self):
        from tactic_stream.agent_host import codex_command, task_prompt
        from tactic_stream.admin_agent import StreamConnection
        request, _ = self.submit(document=dict(self.document, allow_changes=True))
        connection = StreamConnection('http://example.invalid:8081', 'one', 'private-secret')
        with patch('tactic_stream.agent_host.shutil.which', return_value='codex'):
            command = codex_command(connection, request, ROOT, None, ROOT, changes=True)
        encoded = json.dumps(command)
        self.assertNotIn('private-secret', encoded)
        self.assertNotIn('--allow-automation-activate', encoded)
        self.assertIn('--allow-page-save', encoded)
        self.assertIn('app-server', command)
        self.assertIn('features.hooks=false', command)
        self.assertIn('features.plugins=false', command)
        self.assertIn('read-only', command)
        self.assertIn('features.shell_tool=false', command)
        self.assertIn(request['request_id'], encoded)
        self.assertIn(self.document['context']['search_keys'][0], task_prompt(request))

    def test_windows_prefers_native_codex_and_retains_cmd_fallback(self):
        from tactic_stream.agent_host import codex_executable
        with patch('tactic_stream.agent_host.os.name', 'nt'), patch('tactic_stream.agent_host.shutil.which') as which:
            which.side_effect = lambda name: {'codex.exe': 'desktop-codex', 'codex.cmd': 'older-npm-codex'}.get(name)
            self.assertEqual(codex_executable(), 'desktop-codex')
            which.assert_called_once_with('codex.exe')
            which.reset_mock()
            which.side_effect = lambda name: {'codex.cmd': 'npm-only'}.get(name)
            self.assertEqual(codex_executable(), 'npm-only')
        with patch('tactic_stream.agent_host.os.name', 'posix'), patch('tactic_stream.agent_host.shutil.which', return_value='unix-codex') as which:
            self.assertEqual(codex_executable(), 'unix-codex')
            which.assert_called_once_with('codex')

    def test_idle_host_survives_a_connection_interruption_without_replaying_work(self):
        from tactic_stream import agent_host
        from tactic_stream.admin_agent import ConnectionUnavailable
        from unittest.mock import Mock
        connection = Mock()
        attempts = []
        def command(owner, action, **values):
            if action == 'claim':
                attempts.append(action)
                if len(attempts) == 1:
                    raise ConnectionUnavailable('offline')
                return dict(request=None)
            return {}
        connection.command.side_effect = command
        with (
            patch.object(sys, 'argv', ['agent_host', '--server', 'http://example.invalid',
                '--project', 'one', '--stream-root', str(ROOT)]),
            patch.dict(os.environ, TACTIC_AGENT_TICKET='private-fixture'),
            patch.object(agent_host, 'StreamConnection', return_value=connection),
            patch.object(agent_host, 'model_catalog', return_value=[]),
            patch('tactic_stream.provider_host.refresh_profiles', return_value=dict(models=[],providers=[],default_provider='codex')),
            patch.object(agent_host, 'codex_executable', return_value='fixture'),
            patch.object(agent_host.time, 'sleep', side_effect=[None, KeyboardInterrupt]),
            patch.object(agent_host, 'run_request') as run,
        ):
            agent_host.main()
        self.assertEqual(attempts, ['claim', 'claim'])
        run.assert_not_called()

    def test_followup_clears_the_previous_provider_error(self):
        request, _ = self.submit()
        self.call('claim', host_id=self.host)
        self.call('update', request_id=request['request_id'], host_id=self.host, status='failed', error='Previous model rejected')
        current = self.call('message', request_id=request['request_id'], message_id=str(uuid4()), text='Continue', attachments=[])
        self.assertEqual(current['status'], 'queued')
        self.assertEqual(current['error'], '')

    def test_owner_and_administrator_permission_and_disconnect(self):
        state=self.call('state')
        self.call('group_save',group='',name='Private folder',expected_revision=state['groups_revision'])
        saved, _ = self.submit()
        from pyasm.security.authenticator import hash_password
        self.api.dispatch('insert', (self.auth, 'sthpw/login', dict(login='agent_reader', password=hash_password('private-reader-password'))))
        original = self.auth
        self.auth = dict(ticket=self.api.get_ticket('agent_reader', 'private-reader-password'), project='one', language='python')
        from pyasm.common.errors import SecurityException
        with self.assertRaises(SecurityException):
            self.call('read', request_id=saved['request_id'])
        # The administrator gate is independently proven above; exercise owner scoping too.
        with patch('tactic.ui.panel.agent_request_cmd._require_admin'), patch.object(Api, 'check_method_access'):
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                self.call('read', request_id=saved['request_id'])
            private_state=self.call('state')
            self.assertEqual(private_state['hosts'],[])
            self.assertEqual(private_state['requests'],[])
            self.assertEqual(private_state['groups'],[])
        self.auth = original
        self.call('disconnect', host_id=self.host)
        self.assertEqual(self.call('state')['hosts'], [])
        self.assertEqual(self.call('read', request_id=saved['request_id'])['status'], 'interrupted')

    def test_host_cancellation_stops_the_actual_child_process(self):
        from types import SimpleNamespace
        from tactic_stream.agent_host import run_request, stop_process
        request, _ = self.submit()
        reports = []

        class Connection:
            project = 'one'
            _ticket = 'private-test-secret'

            def command(self, owner, action, **values):
                reports.append(values)
                return dict(status=values.get('status', 'cancelling'))

        program = '''import sys,json
for line in sys.stdin:
    message=json.loads(line)
    if 'id' not in message: continue
    method=message['method']
    result={'thread':{'id':'thread'}} if method=='thread/start' else {'turn':{'id':'turn'}} if method=='turn/start' else {}
    print(json.dumps({'id':message['id'],'result':result}),flush=True)
'''
        options = SimpleNamespace(stream_root=ROOT, handler_root=None, allow_changes=False, trial_image=None, trial_directory=None)
        with patch('tactic_stream.agent_host.codex_command', return_value=[sys.executable, '-u', '-c', program]), \
                patch('tactic_stream.codex_session.stop_process', wraps=stop_process) as stopped:
            run_request(Connection(), request, self.host, options, lambda: None)
        self.assertEqual(reports[-1]['status'], 'cancelled')
        self.assertTrue(stopped.called)
        self.assertIsNotNone(stopped.call_args.args[0].poll())


if __name__ == '__main__':
    unittest.main()
