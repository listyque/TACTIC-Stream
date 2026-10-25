"""Native project composition/export/reinstallation on owned databases."""
import ast
import asyncio
import copy
import json
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from xmlrpc.client import Binary

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from pyasm.common import Config
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tactic_stream.server.project_agent import project_agent_request
from tools.checkin_benchmark import prepare


def plan(code='agentstudio'):
    return dict(code=code, title='Studio project', entities=[
        dict(code='sequence', title='Sequences'),
        dict(code='shot', title='Shots', columns=[dict(name='frames', type='integer')]),
        dict(code='asset', title='Assets')],
        relations=[dict(source='shot', target='sequence', source_column='sequence_code'),
                   dict(source='shot', target='asset', instance='shot_asset', source_column='shot_code', target_column='asset_code')],
        pipelines=[dict(entity='shot', processes=['layout', 'animation', 'compositing'],
                        connections=[['layout', 'animation'], ['animation', 'compositing']],
                        statuses=['Waiting', 'Working', 'Approved'])],
        naming=[dict(entity='shot', context='', dir_naming='{project.code}/shots/{parent.code}/{code}',
                     file_naming='{sobject.code}_v{version}.{ext}')])


class NativeProjects(unittest.TestCase):
    database_config = ''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent-project-')
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': self.database_config, 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start(); self.addCleanup(environment.stop)
        Config.reload_config(); self.addCleanup(Config.reload_config)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, self.ticket = prepare(self.store)

    def call(self, action, **values):
        api = Api(self.store)
        login = api.auth.validate(self.ticket)
        with request_context(RequestContext(self.store, login, 'one')):
            api.auth.bind_security(login, self.ticket)
            return project_agent_request(action, dict(ticket=self.ticket, project='one', **values))

    def create(self, document=None):
        document = document or plan()
        args = dict(target=document['code'], document=document, operation_id=str(uuid4()))
        preview = self.call('preview', **args)
        args['expected_revision'] = preview['revision']
        return args, self.call('create', **args)

    def test_create_export_reinstall_and_checkin(self):
        args, result = self.create()
        self.assertEqual(result['status'], 'completed')
        self.assertGreaterEqual(result['result']['naming_rules'], 1)
        self.assertIn('agentstudio/shot_asset', result['result']['entities'])
        self.assertEqual(result, self.call('create', **args))
        self.store = Store(self.store.data_dir)
        self.assertEqual(result, self.call('create', **args))
        changed = copy.deepcopy(args)
        changed['document']['title'] = 'Different'
        with self.assertRaisesRegex(ValueError, 'different request'):
            self.call('create', **changed)
        state = self.call('read', target='agentstudio')
        export_args = dict(target='agentstudio', expected_revision=state['revision'], operation_id=str(uuid4()))
        exported = self.call('export', **export_args)
        self.assertEqual(exported, self.call('export', **export_args))
        self.assertTrue(Path(exported['result']['path']).is_file())
        install_args = dict(target='agentcopy', title='Second production',
                            template_id=exported['result']['template_id'], operation_id=str(uuid4()))
        copied = self.call('install', **install_args)
        self.assertEqual(copied, self.call('install', **install_args))
        self.assertEqual(copied['result']['naming_rules'], result['result']['naming_rules'])
        auth = dict(ticket=self.ticket, project='agentcopy')
        api = Api(self.store)
        api.protocol = 'json'
        api.dispatch('insert', (auth, 'agentstudio/sequence', dict(code='SQ001', name='Opening')))
        shot = api.dispatch('insert', (auth, 'agentstudio/shot',
            dict(code='SH001', name='Flight', sequence_code='SQ001', pipeline_code='agentcopy/shot')))
        pipelines = api.dispatch('query', (auth, 'sthpw/pipeline'), dict(filters=[['project_code', 'agentcopy']]))
        if isinstance(pipelines, str):
            pipelines = ast.literal_eval(pipelines)
        from xml.etree import ElementTree as ET
        graph = ET.fromstring(next(p['pipeline'] for p in pipelines if p['code'] == 'agentcopy/shot'))
        task_pipeline = graph.find('process').get('task_pipeline')
        self.assertIn(task_pipeline, {p['code'] for p in pipelines})
        shot_key = 'agentstudio/shot?project=agentcopy&code=SH001'
        api.dispatch('upload_file', (auth, 'frame.bin', Binary(b'actual project template check-in')))
        snapshot = api.dispatch('simple_checkin', (auth, shot_key, 'publish', 'frame.bin'), dict(mode='uploaded'))
        if isinstance(snapshot, str):
            snapshot = ast.literal_eval(snapshot)
        files = api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[['snapshot_code', snapshot['code']]]))
        if isinstance(files, str):
            files = ast.literal_eval(files)
        self.assertTrue(any(row['file_name'] == 'SH001_v001.bin' for row in files), files)
        self.assertTrue(any('agentcopy/shots/SQ001/SH001' in row['relative_dir'] for row in files), files)

    def test_invalid_stale_failure_and_no_blind_replay(self):
        bad = plan('badstudio')
        bad['relations'][0]['target'] = 'missing'
        with self.assertRaises(ValueError):
            self.call('preview', target='badstudio', document=bad)
        self.assertFalse(self.call('read', target='badstudio')['database_exists'])
        draft = plan('staleplan')
        with self.assertRaisesRegex(ValueError, 'plan changed'):
            self.call('create', target=draft['code'], document=draft, expected_revision='old', operation_id=str(uuid4()))
        from tactic_stream.server.project_agent import ConfigureProjectCmd
        with patch.object(ConfigureProjectCmd, 'execute', side_effect=ValueError('injected configure failure')):
            args = dict(target='brokenplan', document=plan('brokenplan'), operation_id=str(uuid4()))
            args['expected_revision'] = self.call('preview', **args)['revision']
            with self.assertRaisesRegex(ValueError, 'injected'):
                self.call('create', **args)
        state = self.call('operation', target='brokenplan', operation_id=args['operation_id'])
        self.assertEqual(state['status'], 'needs_inspection')
        self.assertTrue(state['current']['registered'])
        self.assertEqual(state['stage'], 'configure')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.call('create', **args)

    def test_concurrent_create_export_revision_and_archive_tampering(self):
        from concurrent.futures import ThreadPoolExecutor
        document = plan('concurrent')
        args = dict(target=document['code'], document=document, operation_id=str(uuid4()))
        args['expected_revision'] = self.call('preview', **args)['revision']
        from pyasm.common.config import ConfigConflict
        with ThreadPoolExecutor(max_workers=2) as workers:
            pending = [workers.submit(self.call, 'create', **args) for _ in range(2)]
            results = []
            for future in pending:
                try:
                    results.append(future.result())
                except ConfigConflict:
                    pass  # Native lock has a bounded wait; a slow first request can report busy.
        self.assertTrue(results)
        results.append(self.call('create', **args))
        self.assertEqual(results[0], results[1])
        with self.assertRaisesRegex(ValueError, 'configuration changed'):
            self.call('export', target='concurrent', expected_revision='stale', operation_id=str(uuid4()))
        state = self.call('read', target='concurrent')
        exported = self.call('export', target='concurrent', expected_revision=state['revision'], operation_id=str(uuid4()))
        with Path(exported['result']['path']).open('ab') as archive:
            archive.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'archive changed'):
            self.call('install', target='tampered', title='Tampered', template_id=exported['operation_id'], operation_id=str(uuid4()))
        self.assertFalse(self.call('read', target='tampered')['database_exists'])
        from tactic_stream.server import project_agent
        native_run = project_agent.run
        def concurrent_edit(command):
            result = native_run(command)
            if isinstance(command, project_agent.ProjectTemplateCreatorCmd):
                Api(self.store).dispatch('add_column_to_search_type',
                    (dict(ticket=self.ticket, project='concurrent'), 'concurrent/shot', 'later_field', 'text'))
            return result
        state = self.call('read', target='concurrent')
        with patch.object(project_agent, 'run', side_effect=concurrent_edit):
            with self.assertRaisesRegex(ValueError, 'changed during export'):
                self.call('export', target='concurrent', expected_revision=state['revision'], operation_id=str(uuid4()))


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP SDK is not installed')
class MCPProjects(unittest.TestCase):
    def test_stdio_http_project_and_template(self):
        from mcp import Client, StdioServerParameters
        from test_transport import Transport
        from tactic_stream.admin_agent import StreamConnection
        Transport.setUpClass()
        self.addCleanup(Transport.tearDownClass)
        api = Api(Transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        args = ['-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent', '--server', Transport.url,
                '--project', 'one', '--stream-root', str(ROOT), '--allow-project-create']
        parameters = StdioServerParameters(command=sys.executable, args=args,
            env=dict(os.environ, TACTIC_AGENT_TICKET=ticket, PYTHONPATH=str(ROOT/'src'), PYTHONUTF8='1'))
        operation_id = str(uuid4())

        async def exercise():
            async with Client(parameters) as client:
                async def call(name, **values):
                    response = await client.call_tool(name, values)
                    self.assertFalse(response.is_error, response.content)
                    return response.structured_content
                draft = plan('mcpstudio')
                preview = await call('ts_project_preview', document=draft)
                rejected = await client.call_tool('ts_project_preview', dict(document=dict(draft, script='print(1)')))
                self.assertTrue(rejected.is_error)
                created = await call('ts_project_create', document=draft, expected_revision=preview['revision'], operation_id=operation_id)
                state = await call('ts_project_read', target='mcpstudio')
                exported = await call('ts_project_export', target='mcpstudio', expected_revision=state['revision'], operation_id=str(uuid4()))
                installed = await call('ts_project_install', template_id=exported['operation_id'], target='mcpcopy',
                                        title='MCP copy', operation_id=str(uuid4()))
                self.assertEqual(installed['status'], 'completed')
                return created
        created = asyncio.run(exercise())
        Transport.stop_server(); Transport.start_server()
        recovered = StreamConnection(Transport.url, 'one', ticket).project_operation('operation', target='mcpstudio', operation_id=operation_id)
        self.assertEqual(recovered['result'], created['result'])
        self.assertTrue(recovered['current']['registered'])
        from pyasm.security.authenticator import hash_password
        from mcp.server.mcpserver.exceptions import ToolError
        api.dispatch('insert', (dict(ticket=ticket, project='one'), 'sthpw/login',
            dict(login='project_guest', password=hash_password('private-guest-password'))))
        guest = api.get_ticket('project_guest', 'private-guest-password')
        with self.assertRaises(ToolError):
            StreamConnection(Transport.url, 'one', guest).project_operation('read', target='mcpstudio')


if __name__ == '__main__':
    if '--postgres' in sys.argv:
        from tools.file_project_checks import postgres
        successful = True
        for method in unittest.defaultTestLoader.getTestCaseNames(NativeProjects):
            with postgres() as config:
                NativeProjects.database_config = config
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([NativeProjects(method)]))
                successful = result.wasSuccessful() and successful
        raise SystemExit(not successful)
    unittest.main()
