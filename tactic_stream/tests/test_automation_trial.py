"""Real OS-bound trials are opt-in; receipt/scope/source gates remain deterministic."""
import asyncio
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from tactic_stream.automation_plan import AutomationPlan
from tactic_stream.automation_trial import AutomationTrials, TrialCase, digest, trial_slot


def draft(kind='hook', phase='before', source='RESULT = 1'):
    document = AutomationPlan(title='Trial action', kind=kind, phase=phase, source=source,
        search_type='trial/shot' if kind == 'hook' else '',
        entry_key='trial/shot@shots' if kind == 'shelf' else '').model_dump()
    return dict(draft_id=str(uuid4()), revision=digest(document), document=document, dependency_revision='generation-one')


class TrialBoundary(unittest.TestCase):
    def test_os_slot_refuses_parallel_execution_and_releases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with trial_slot(root):
                with self.assertRaisesRegex(ValueError, 'busy'):
                    with trial_slot(root):
                        self.fail('Concurrent execution was allowed')
            with trial_slot(root):
                pass

    def test_input_paths_and_scope_revision_before_case_gate(self):
        for case in (dict(expect='allow', files=[dict(name='../secret')]),
                     dict(expect='allow', artifacts=[dict(name='x/../secret')])):
            with self.assertRaises(ValueError):
                TrialCase.model_validate(case)
        with tempfile.TemporaryDirectory() as folder:
            image = 'sha256:'+'a'*64
            runner = AutomationTrials(image, folder, ['server', 'project', 'session'])
            document = draft()
            identities = []
            for expected in ('allow', 'reject'):
                identity = str(uuid4()); identities.append(identity)
                runner._save(Path(folder)/(identity+'.json'), dict(trial_id=identity, scope=runner.scope,
                    status='passed', image=image, draft_id=document['draft_id'], draft_revision=document['revision'],
                    document_hash=digest(document['document']), dependency_revision='generation-one', case=dict(expect=expected)))
            runner.require_passed(identities, document, 'generation-one')
            with self.assertRaises(ValueError):
                runner.require_passed(identities[:1], document, 'generation-one')
            with self.assertRaises(ValueError):
                runner.require_passed(identities, document, 'generation-two')
            changed = dict(document, document=dict(document['document'], source='RESULT = 2'))
            with self.assertRaises(ValueError):
                runner.require_passed(identities, changed, 'generation-one')
            with self.assertRaises(ValueError):
                AutomationTrials(image, folder, ['another session']).read(identities[0])

    def test_agent_cannot_expose_activation_without_isolation(self):
        from tactic_stream.admin_agent import create_server, StreamConnection
        with self.assertRaisesRegex(ValueError, 'requires a configured'):
            create_server(StreamConnection('http://127.0.0.1:1', 'one', 'private-test-ticket'),
                          Path(__file__).parents[1], allow_automation_activate=True)


@unittest.skipUnless(os.environ.get('TACTIC_TRIAL_IMAGE'), 'Set TACTIC_TRIAL_IMAGE to a trusted built local image ID')
class RealTrials(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.runner = AutomationTrials(os.environ['TACTIC_TRIAL_IMAGE'], self.temporary.name, ['owned-test'])

    def run_trial(self, document, case):
        return self.runner.run(str(uuid4()), document, case, 'trial')

    def test_before_allow_reject_real_checkin_replay_and_os_probes(self):
        source = """from pathlib import Path
import os, socket
from tactic_handler_api import get_api
objects = get_api().project('trial').stype('trial/shot').query(limit=1)
assert objects.items[0].get_info()['code'] == 'TRIAL001'
assert os.getuid() != 0
assert 'TACTIC_AGENT_TICKET' not in os.environ
assert {name for _,name in socket.if_nameindex()} == {'lo'}
assert not Path('/var/run/docker.sock').exists()
assert not Path('D:/grav/Tactic Stream/TS/tactic_stream/data').exists()
try:
    Path('/opt/trial/escape').write_text('bad')
except OSError:
    pass
else:
    raise RuntimeError('Image filesystem was writable')
connection = socket.socket(); connection.settimeout(.2)
assert connection.connect_ex(('1.1.1.1', 443)) != 0
connection.close()
if Path(TACTIC_SCRIPT_KWARGS['files'][0]['path']).read_text() == 'bad':
    raise RuntimeError('Rejected test file')
"""
        document = draft(source=source)
        results = []
        for expected, content in (('allow', 'good'), ('reject', 'bad')):
            identity = str(uuid4())
            case = dict(expect=expected, files=[dict(name='input.bin', content=content)])
            result = self.runner.run(identity, document, case, 'trial')
            self.assertEqual(result['status'], 'passed', result)
            self.assertEqual(self.runner.run(identity, document, case, 'trial'), result)
            self.assertEqual(self.runner.run(identity, dict(document, dependency_revision='later-edit'), case, 'trial'), result)
            self.assertEqual(result['isolation']['mounts'], [])
            self.assertEqual(result['result']['runtime']['effective_capabilities'], '0000000000000000')
            results.append(identity)
        self.runner.require_passed(results, document, 'generation-one')

    def test_after_program_and_real_shelf_actions(self):
        after = draft(phase='after', source="""import sys
from tactic_handler_api.automation import run_checkin_program
RESULT = run_checkin_program([sys.executable, '-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', '/work/after.txt', '{result_search_key}'], TACTIC_SCRIPT_KWARGS)
""")
        result = self.run_trial(after, dict(expect='allow', artifacts=[dict(name='after.txt', contains='sthpw/snapshot')]))
        self.assertEqual(result['status'], 'passed', result)
        shelf = draft(kind='shelf', source="""from side_tools.frame_tool.showcase import show
show([{'id': key, 'title': key} for key in TACTIC_SCRIPT_KWARGS['search_keys']], modal=True)
""")
        result = self.run_trial(shelf, dict(expect='modal', actions=[dict(kind='point', x=100, y=70),
            dict(kind='text', text='XYZ'), dict(kind='expect', target='batchName', contains='XYZ'),
            dict(kind='backspace'), dict(kind='expect', target='batchName', contains='XY'), dict(kind='click', target='exampleBuild'),
            dict(kind='expect', target='preview', contains='TRIAL001'), dict(kind='click', target='exampleClear'),
            dict(kind='expect', target='records', contains='[]')]))
        self.assertEqual(result['status'], 'passed', result)
        self.assertTrue(base64.b64decode(result['result']['screenshot']).startswith(b'\x89PNG'))

    def test_runtime_error_hang_and_process_tree_cleanup(self):
        identities = []
        for source, expected in [('raise RuntimeError("Expected failure")', 'Expected failure'),
                       ('import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c","import time;time.sleep(120)"],start_new_session=True)\ntime.sleep(120)', 'timed out')]:
            result = self.run_trial(draft(source=source), dict(expect='allow'))
            identities.append(result['trial_id'])
            self.assertEqual(result['status'], 'failed', result)
            self.assertIn(expected, json.dumps(result))
        for identity in identities:
            result = subprocess.run(['docker', 'inspect', 'tactic-automation-trial-'+identity], capture_output=True)
            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_after_failure_and_exception_after_opening_ui_are_not_success(self):
        result = self.run_trial(draft(phase='after', source='raise RuntimeError("After failed")'), dict(expect='allow'))
        self.assertEqual(result['status'], 'failed', result)
        self.assertIn('After failed', json.dumps(result))
        for error in ("RuntimeError('UI failed after opening')", "SystemExit('UI failed after opening')"):
            source = "from side_tools.frame_tool.showcase import show\nshow([], modal=True)\nraise " + error
            result = self.run_trial(draft(kind='shelf', source=source), dict(expect='modal'))
            self.assertEqual(result['status'], 'failed', result)
            self.assertIn('UI failed after opening', json.dumps(result))

    def test_mcp_trial_gate_stale_dependencies_and_activation_replay(self):
        from mcp import Client
        from test_transport import Transport
        from tactic_stream.server.api import Api
        from tactic_stream.admin_agent import StreamConnection, create_server
        Transport.setUpClass()
        self.addCleanup(Transport.tearDownClass)
        api = Api(Transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        connection = StreamConnection(Transport.url, 'one', ticket)
        document = draft(source="from pathlib import Path\nif Path(TACTIC_SCRIPT_KWARGS['files'][0]['path']).read_text() == 'bad':\n    raise RuntimeError('Rejected test file')")['document']
        document['search_type'] = 'contract/entity'
        async def run():
            async with Client(create_server(connection, Path(__file__).parents[1],
                              allow_automation_draft=True, allow_automation_activate=True, trials=self.runner)) as client:
                async def call(tool, **values):
                    result = await client.call_tool(tool, values)
                    self.assertFalse(result.is_error, result.content)
                    return result.structured_content
                preview = await call('th_automation_preview', document=document)
                saved = await call('th_automation_save_draft', document=document,
                    expected_revision=preview['revision'], operation_id=str(uuid4()))
                current = await call('th_automation_draft', draft_id=saved['draft_id'])
                args = dict(draft_id=saved['draft_id'], draft_revision=saved['revision'],
                    expected_revision=current['dependency_revision'], operation_id=str(uuid4()), trial_ids=[str(uuid4())])
                self.assertTrue((await client.call_tool('th_automation_activate', args)).is_error)
                async def trials():
                    identities = []
                    for expected, content in (('allow', 'good'), ('reject', 'bad')):
                        identity = str(uuid4()); identities.append(identity)
                        response = await call('th_automation_trial', draft_id=saved['draft_id'], draft_revision=saved['revision'],
                            trial_id=identity, case=dict(expect=expected, files=[dict(name='input.bin', content=content)]))
                        self.assertEqual(response['status'], 'passed', response)
                        self.assertNotIn('screenshot', response['result'])
                    return identities
                args['trial_ids'] = await trials()
                api.dispatch('insert', (dict(ticket=ticket, project='one'), 'config/widget_config',
                    dict(search_type='SideBarWdg', view='trial-dependency-change', config='<config/>')))
                self.assertTrue((await client.call_tool('th_automation_activate', args)).is_error)
                args['trial_ids'] = await trials()
                args['expected_revision'] = (await call('th_automation_draft', draft_id=saved['draft_id']))['dependency_revision']
                result = await call('th_automation_activate', **args)
                self.assertEqual(result, await call('th_automation_activate', **args))
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
