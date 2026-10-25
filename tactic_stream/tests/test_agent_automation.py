"""Draft and native Handler binding lifecycle; source is never evaluated by the server."""
import ast
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from pyasm.common import Config
from pyasm.search.storage import Store
from pyasm.search.sql import Sql
from tactic_stream.server.api import Api
from tools.checkin_benchmark import prepare

COMMAND = 'tactic.ui.panel.handler_automation_cmd.HandlerAutomationCmd'


class NativeAutomation(unittest.TestCase):
    database_config = ''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent-automation-')
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': self.database_config, 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start(); self.addCleanup(environment.stop)
        Config.reload_config(); self.addCleanup(Config.reload_config)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one', language='python')

    def call(self, action, **values):
        return Api(self.store).dispatch('execute_cmd', (self.auth, COMMAND, dict(action=action, project_code='one', **values)))['info']

    def query(self, logical):
        result = Api(self.store).dispatch('query', (self.auth, logical), dict(show_retired=True))
        return ast.literal_eval(result) if isinstance(result, str) else result

    def draft(self, document):
        preview = self.call('preview', document=document)
        args = dict(document=document, expected_revision=preview['revision'], operation_id=str(uuid4()))
        result = self.call('save_draft', **args)
        self.assertEqual(self.call('save_draft', **args), result)
        return result

    def test_draft_activation_replay_atomic_failure_and_stale_dependencies(self):
        before = {logical: self.query(logical) for logical in ('config/custom_script', 'config/trigger', 'config/widget_config')}
        draft = self.draft(dict(kind='hook', title='Validate files', phase='before', search_type='cg/shot',
                                source="raise RuntimeError('This source must never run on the server')"))
        self.assertEqual(before, {logical: self.query(logical) for logical in before})
        saved = self.call('draft', draft_id=draft['draft_id'])
        args = dict(draft_id=draft['draft_id'], draft_revision=draft['revision'],
                    expected_revision=saved['dependency_revision'], operation_id=str(uuid4()))
        applied = self.call('activate', **args)
        self.assertEqual(applied, self.call('activate', **args))
        self.store = Store(self.store.data_dir)
        self.assertEqual(applied, self.call('operation', operation_id=args['operation_id']))
        current = self.call('read')
        self.assertEqual(current['records'][-1]['script_path'], applied['script'])
        self.assertEqual(self.query('config/custom_script')[-1]['language'], 'local_python')
        with self.assertRaisesRegex(ValueError, 'different request'):
            self.call('activate', **dict(args, draft_revision='changed'))
        with self.assertRaisesRegex(ValueError, 'dependencies changed'):
            self.call('save_hooks', rules=[], expected_revision=saved['dependency_revision'], operation_id=str(uuid4()))
        second = self.draft(dict(kind='hook', title='Post publish', phase='after', source='RESULT = 1'))
        operation = dict(draft_id=second['draft_id'], draft_revision=second['revision'],
            expected_revision=self.call('read')['revision'], operation_id=str(uuid4()))
        update = Sql._do_update
        def fail_receipt(sql, statement, *values, **kwargs):
            if statement.startswith('INSERT INTO spt_automation_operation'):
                raise ValueError('receipt failed')
            return update(sql, statement, *values, **kwargs)
        before = {logical: self.query(logical) for logical in before}
        with patch.object(Sql, '_do_update', fail_receipt), self.assertRaisesRegex(ValueError, 'receipt failed'):
            self.call('activate', **operation)
        self.assertEqual(before, {logical: self.query(logical) for logical in before})
        self.assertEqual(self.call('operation', operation_id=operation['operation_id'])['status'], 'not_found')

    def test_shelf_binding_uses_actual_tab_and_keeps_existing_buttons(self):
        from tactic_stream.server.script_shelf import shelf_configuration_xml
        existing = dict(id='existing', title='Existing tool', description='', icon='play-arrow', script=self.call('read')['scripts'][0]['path'])
        values = dict(search_type='SideBarWdg', view='script_shelf@global', login='', category='script_shelf',
                      config=shelf_configuration_xml(dict(scope='global', entryKey='', buttons=[existing]), 'script_shelf@global'))
        original = next((row for row in self.query('config/widget_config') if row.get('view') == 'script_shelf@global' and not row.get('login')), None)
        if original:
            self.api.dispatch('update', (self.auth, original['__search_key__'], values))
        else:
            self.api.dispatch('insert', (self.auth, 'config/widget_config', values))
        self.api.dispatch('insert', (self.auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler',
            priority=2000, login='', config='<config><tactic_handler><element name="shots" title="Shots"><display class="LinkWdg"><search_type>cg/shot</search_type><view>table</view></display></element></tactic_handler></config>')))
        draft = self.draft(dict(kind='shelf', title='Shot tool', source='RESULT = 42', entry_key='cg/shot@shots'))
        saved = self.call('draft', draft_id=draft['draft_id'])
        applied = self.call('activate', draft_id=draft['draft_id'], draft_revision=draft['revision'],
            expected_revision=saved['dependency_revision'], operation_id=str(uuid4()))
        shelves = self.call('read')['shelves']
        self.assertTrue(any(button['script'] == applied['script'] for row in shelves for button in row['configuration']['buttons']))
        preset = next(row for row in shelves if row['code'] == applied['binding']['savedCode'])
        self.assertEqual(preset['configuration']['buttons'][0], existing)
        self.assertEqual(next(row for row in shelves if row['view'] == 'script_shelf@global')['configuration']['buttons'], [existing])
        self.assertTrue(any('script_shelf@' in row.get('config', '') and 'shots' in row.get('config', '')
                            for row in self.query('config/widget_config') if row.get('view') == 'tactic_handler'))

    def test_activation_checks_execution_and_native_edits_invalidate_revision(self):
        draft = self.draft(dict(kind='hook', title='Check', source='RESULT = True'))
        state = self.call('read')
        from pyasm.common.errors import SecurityException
        with patch('tactic.command.python_cmd.check_script_execution', side_effect=SecurityException('execution denied')):
            with self.assertRaisesRegex(SecurityException, 'execution denied'):
                self.call('activate', draft_id=draft['draft_id'], draft_revision=draft['revision'],
                    expected_revision=state['revision'], operation_id=str(uuid4()))
        self.assertEqual(state['records'], self.call('read')['records'])
        rule = self.query('config/custom_script')[0]
        for value in ('changed', rule['script']):
            self.api.dispatch('update', (self.auth, rule['__search_key__'], dict(script=value)), dict(triggers=False))
        self.assertNotEqual(state['revision'], self.call('read')['revision'])
        with self.assertRaisesRegex(ValueError, 'dependencies changed'):
            self.call('activate', draft_id=draft['draft_id'], draft_revision=draft['revision'],
                expected_revision=state['revision'], operation_id=str(uuid4()))


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP SDK is not installed')
class MCPAutomation(unittest.TestCase):
    def test_agent_to_native_handler_checkin_and_modal_shelf(self):
        from mcp import Client, StdioServerParameters
        from test_transport import Transport
        Transport.setUpClass()
        self.addCleanup(Transport.tearDownClass)
        api = Api(Transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=ticket, project='one')
        api.dispatch('insert', (auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler',
            priority=2000, login='', config='<config><tactic_handler><element name="entities" title="Entities"><display class="LinkWdg"><search_type>contract/entity</search_type><view>table</view></display></element></tactic_handler></config>')))
        marker = Path(Transport.temp.name) / 'after.txt'
        validator = [sys.executable, '-c', "import pathlib,sys; raise SystemExit(7 if pathlib.Path(sys.argv[1]).name=='blocked.bin' else 0)", '{file}']
        post = [sys.executable, '-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', str(marker), '{result_search_key}']
        documents = [dict(kind='hook', title='Input validator', search_type='contract/entity', phase='before',
                         source='from tactic_handler_api.automation import run_checkin_program\nRESULT = run_checkin_program(%r, TACTIC_SCRIPT_KWARGS, per_file=True)' % validator),
                     dict(kind='hook', title='After publication', search_type='contract/entity', phase='after',
                         source='from tactic_handler_api.automation import run_checkin_program\nRESULT = run_checkin_program(%r, TACTIC_SCRIPT_KWARGS)' % post),
                     dict(kind='shelf', title='Selected entities', entry_key='contract/entity@entities',
                         source="from side_tools.frame_tool.showcase import show\nshow([{'id': key, 'title': key} for key in TACTIC_SCRIPT_KWARGS['search_keys']], modal=True)")]
        args = ['-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent', '--server', Transport.url,
                '--project', 'one', '--stream-root', str(ROOT), '--allow-automation-draft', '--allow-automation-activate']
        parameters = StdioServerParameters(command=sys.executable, args=args,
            env=dict(os.environ, TACTIC_AGENT_TICKET=ticket, PYTHONPATH=str(ROOT/'src'), PYTHONUTF8='1'))
        async def author():
            results = []
            async with Client(parameters) as client:
                async def call(name, **values):
                    response = await client.call_tool(name, values)
                    self.assertFalse(response.is_error, response.content)
                    return response.structured_content
                for document in documents:
                    preview = await call('th_automation_preview', document=document)
                    saved = await call('th_automation_save_draft', document=document, expected_revision=preview['revision'], operation_id=str(uuid4()))
                    state = await call('th_automation_read')
                    values = dict(draft_id=saved['draft_id'], draft_revision=saved['revision'], expected_revision=state['revision'], operation_id=str(uuid4()))
                    activated = await call('th_automation_activate', **values)
                    self.assertEqual(activated, await call('th_automation_activate', **values))
                    results.append(activated)
            return results
        results = asyncio.run(author())
        from urllib.parse import urlsplit
        shelf = results[-1]
        saved_code = shelf['binding']['savedCode']
        row = next(row for row in shelf['binding']['shelves'] if row['code'] == saved_code)
        fixture = Path(Transport.temp.name) / 'handler-automation.json'
        fixture.write_text(json.dumps(dict(ticket=ticket, server=urlsplit(Transport.url).netloc,
            marker=str(marker), shelf_view=row['view'], button_id=shelf['draft_id'])), encoding='utf-8')
        handler = ROOT.parent.parent / 'TH'
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'tests/scripts/agent_automation_handler.py'),
            '--handler-root', str(handler), '--fixture', str(fixture)], cwd=handler,
            env=dict(os.environ, PYTHONPATH=str(handler)), capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(marker.is_file())


if __name__ == '__main__':
    if '--postgres' in sys.argv:
        from tools.file_project_checks import postgres
        successful = True
        for method in unittest.defaultTestLoader.getTestCaseNames(NativeAutomation):
            with postgres() as config:
                NativeAutomation.database_config = config
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([NativeAutomation(method)]))
                successful = result.wasSuccessful() and successful
        raise SystemExit(not successful)
    unittest.main()
