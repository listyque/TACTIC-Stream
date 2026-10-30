"""Managed process lifecycle without inference; native API ownership boundaries."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time
import unittest
from uuid import uuid4
from unittest.mock import patch

from tactic_stream import agent_runtime as runtime
from tests import test_agent_requests as fixture


class Runtime(unittest.TestCase):
    def wait(self, scope, expected):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            value = runtime.state(scope)
            if value['state'] == expected:
                return value
            time.sleep(.02)
        self.fail(str(value))

    def test_real_process_start_repeat_stop_and_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / 'tactic_stream'
            package.mkdir()
            (package / '__init__.py').write_text('__path__.append(%r)' % str(Path(runtime.__file__).parent))
            host = package / 'agent_host.py'
            host.write_text('import time\ndef main(*, connected=None):\n connected()\n while True: time.sleep(.1)\n')
            scope = runtime.directory(root, 'alice', 'one')
            other = runtime.directory(root, 'bob', 'one')
            self.assertEqual(runtime.state(scope)['state'], 'stopped')
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    values = list(pool.map(lambda _: runtime.start(scope, 'http://127.0.0.1:9', 'one', 'private-fixture-ticket', root), range(2)))
                self.assertTrue(all(row['state'] in runtime.BUSY for row in values))
                self.wait(scope, 'connected')
                self.assertEqual(len(list(scope.glob('*/state.json'))), 1)
                self.assertEqual(runtime.stop(other)['state'], 'stopped')
                self.assertEqual(runtime.state(scope)['state'], 'connected')
                self.assertEqual(runtime.stop(scope)['state'], 'stopping')
                self.wait(scope, 'stopped')
                self.assertEqual(runtime.stop(scope)['state'], 'stopped')
                host.write_text('import os\ndef main(*, connected=None):\n raise RuntimeError("Failure " + os.environ["TACTIC_AGENT_TICKET"])\n')
                runtime.start(scope, 'http://127.0.0.1:9', 'one', 'private-fixture-ticket', root)
                failed = self.wait(scope, 'failed')
                self.assertIn('[redacted]', failed['error'])
                for metadata in scope.rglob('*.json'):
                    self.assertNotIn('private-fixture-ticket', metadata.read_text())
            finally:
                runtime.stop(scope)
                for child in runtime._children:
                    child.wait(timeout=12)


class Command(unittest.TestCase):
    setUp = fixture.AgentRequests.setUp
    call = fixture.AgentRequests.call

    def executor(self, action, **values):
        return self.api.dispatch('execute_cmd', (self.auth, 'tactic.ui.panel.agent_executor_cmd.AgentExecutorCmd',
            dict(action=action, project_code='one', target='server') | values))['info']

    def test_desktop_relay_explicit_scope_retry_stop_and_expiry(self):
        self.call('disconnect', host_id=self.host)
        device, other = str(uuid4()), str(uuid4())
        self.assertEqual(self.executor('state')['target'], '')
        with self.assertRaisesRegex(ValueError, 'Choose the computer'):
            self.executor('start', target='')
        def poll(**values):
            return self.executor('desktop_poll', device=device, label='My workstation', **values)
        self.assertEqual(poll()['commands'], [])
        self.assertEqual(self.executor('state')['target'], device)
        self.executor('start', target=device)
        operation = poll()['commands'][0]
        self.assertEqual(operation['action'], 'start')
        self.assertEqual(operation['project'], 'one')
        self.executor('start', target=device)
        self.assertEqual(poll()['commands'], [operation])
        with patch.object(runtime, 'start') as launch:
            with self.assertRaisesRegex(ValueError, 'already connected'):
                self.executor('start')
            launch.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'sign in to the same account'):
            self.executor('start', target=other)
        poll(acks=[operation['operation']], reports={'one': dict(operation=operation['operation'], state='connected', error='')})
        self.assertEqual(poll()['commands'], [])
        self.assertEqual(self.executor('state')['state'], 'connected')
        self.executor('stop', target=device)
        stop = poll()['commands'][0]
        self.assertNotEqual(stop['operation'], operation['operation'])
        poll(reports={'one': dict(operation=operation['operation'], state='connected', error='')})
        self.assertEqual(self.executor('state')['state'], 'stopping')
        with patch('tactic_stream.server.agent_desktops.time.time', return_value=time.time() + 65):
            self.assertEqual(poll()['commands'], [])
            self.assertEqual(self.executor('state')['state'], 'failed')
        with self.assertRaises(ValueError):
            poll(reports={'one': dict(operation=stop['operation'], state='running', error='')})
        from pyasm.common import Environment
        with patch.object(Environment, 'get_user_name', return_value='another-admin'), \
                patch.object(Environment, 'get_data_dir', return_value=self.store.data_dir):
            from tactic_stream.server.agent_desktops import targets, control
            self.assertEqual(targets('one'), [])
            with self.assertRaisesRegex(ValueError, 'sign in to the same account'):
                control(device, 'one', 'start')

    def test_scope_auth_external_host_and_private_environment(self):
        self.assertEqual(self.executor('state')['state'], 'external')
        with patch.object(runtime, 'start') as launch:
            with self.assertRaisesRegex(ValueError, 'already connected'):
                self.executor('start')
            launch.assert_not_called()
        self.call('disconnect', host_id=self.host)
        self.assertEqual(self.executor('state')['state'], 'stopped')
        with self.assertRaisesRegex(ValueError, 'project mismatch'):
            self.executor('state', project_code='two')
        with patch.object(runtime, 'start', return_value=dict(state='starting', managed=True, error='')) as launch:
            self.assertEqual(self.executor('start')['state'], 'starting')
            arguments = launch.call_args.args
            self.assertEqual(arguments[2], 'one')
            self.assertEqual(arguments[3], self.auth['ticket'])
        from pyasm.security import Login
        from pyasm.search.search import RequestContext, request_context
        from pyasm.common.errors import SecurityException
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            Login.create('reader', 'reader-password')
        reader = self.api.get_ticket('reader', 'reader-password')
        with patch.object(runtime, 'start') as launch, self.assertRaises(SecurityException):
            self.api.dispatch('execute_cmd', (dict(ticket=reader, project='one'),
                'tactic.ui.panel.agent_executor_cmd.AgentExecutorCmd', dict(action='start', project_code='one')))
        launch.assert_not_called()
