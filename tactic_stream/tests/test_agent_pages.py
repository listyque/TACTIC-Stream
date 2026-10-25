"""Agent page creation through real MCP/HTTP and the native editor contracts."""
import asyncio
import ast
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from pyasm.common import Config
from pyasm.search.sql import Sql
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.checkin_benchmark import prepare

COMMAND = 'tactic.ui.panel.page_cmd.PageCmd'


def document(name='review'):
    return dict(name=name, title='Review shots', columns=[dict(name='code', title='Shot', width=180),
                dict(name='description', width=320)],
                records=[dict(column='code', relation='=', value='SH001', rowEnabled=True, operator='begin')],
                workspace_layout=dict(panels=[dict(panel_id='results', title='Results', kind='results', x=0., y=0.,
                    width=.7, height=1., visible=True, z=1, dock_area='center'),
                    dict(panel_id='notes', title='Task Inspector', kind='notes', x=.7, y=0., width=.3, height=1.,
                         visible=True, z=2, dock_area='right')],
                    layout=dict(type='split', orientation='horizontal', ratio=.7,
                        first=dict(type='stack', panels=['results'], active='results'),
                        second=dict(type='stack', panels=['notes'], active='notes'))))


class NativePages(unittest.TestCase):
    database_config = ''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agent-page-')
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': self.database_config, 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start(); self.addCleanup(environment.stop)
        Config.reload_config(); self.addCleanup(Config.reload_config)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, ticket = prepare(self.store)
        self.auth = dict(ticket=ticket, project='one', language='python')

    def call(self, action, **kwargs):
        return Api(self.store).dispatch('execute_cmd', (self.auth, COMMAND,
            dict(action=action, project_code='one', search_type='cg/shot', **kwargs)))['info']

    def records(self):
        return ast.literal_eval(self.api.dispatch('query', (self.auth, 'config/widget_config'), dict(order_bys=['id'])))

    def test_preview_atomic_save_replay_and_native_readback(self):
        before = self.records()
        state = self.call('read')
        self.store.upgrade()
        self.assertEqual(state['revision'], self.call('read')['revision'])
        args = dict(document=document(), expected_revision=state['revision'], operation_id=str(uuid4()))
        preview = self.call('preview', **args)
        self.assertEqual(preview['sample']['total'], 1)
        self.assertEqual(preview['sample']['records'][0]['code'], 'SH001')
        self.assertEqual(self.records(), before)
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: self.call('apply', **args), range(2)))
        result = results[0]
        self.assertEqual(results[0], results[1])
        self.assertIn('review', [row['name'] for row in result['navigation']['entries']])
        self.store = Store(self.store.data_dir)
        self.assertEqual(self.call('apply', **args), result)
        self.assertEqual(self.call('operation', operation_id=args['operation_id']), result)
        with self.assertRaisesRegex(ValueError, 'different request'):
            self.call('apply', **dict(args, document=document('other')))
        with self.assertRaisesRegex(Exception, 'dependencies changed'):
            self.call('apply', **dict(args, operation_id=str(uuid4()), document=document('other')))
        after = self.call('read')
        self.assertNotEqual(state['revision'], after['revision'])
        self.assertEqual(len([r for r in self.records() if r['view'] == result['view']]), 1)
        links = [row for row in after['navigation']['entries'] if row['name'] == 'review']
        self.assertTrue(links, dict(names=[r['name'] for r in after['navigation']['entries']],
            layers=[{k: row.get(k) for k in ('id', 'view', 'login', 'priority', 'config')}
                    for row in self.records() if row['search_type'] == 'SideBarWdg' and row['view'] == 'tactic_handler']))
        link = links[0]
        self.assertEqual(link['display']['options']['view'], result['view'])
        self.assertEqual(link['display']['options']['search_view'], result['search']['view'])
        self.assertEqual(link['display']['options']['layout_preset'], result['workspace']['view'])
        self.assertEqual(link['display']['options']['view_mode'], 'table')
        # Every pre-existing source is preserved; native sidebar sources may gain one entry.
        now = {row['code']: row for row in self.records()}
        for row in before:
            if row['search_type'] != 'SideBarWdg' or row['view'] == 'definition' and row.get('login') is not None:
                self.assertEqual(now[row['code']], row)
        self.assertEqual(result['workspace']['configuration'], args['document']['workspace_layout'])

    def test_rollback_stale_native_edit_and_validation(self):
        state = self.call('read')
        args = dict(document=document(), expected_revision=state['revision'], operation_id=str(uuid4()))
        before = self.records()
        update = Sql._do_update
        def fail_receipt(sql, query, *values, **kwargs):
            if query.startswith('INSERT INTO spt_page_operation'):
                raise ValueError('receipt failed')
            return update(sql, query, *values, **kwargs)
        with patch.object(Sql, '_do_update', fail_receipt), self.assertRaisesRegex(ValueError, 'receipt failed'):
            self.call('apply', **args)
        self.assertEqual(self.records(), before)
        self.assertEqual(self.call('read')['revision'], state['revision'])
        self.assertEqual(self.call('operation', operation_id=args['operation_id'])['status'], 'not_found')
        for invalid in (dict(args['document'], columns=[dict(name='missing')]),
                        dict(args['document'], records=[dict(column='_expression', relation='in', value='@PYTHON(unsafe)', rowEnabled=True, operator='begin')]),
                        dict(args['document'], workspace_layout={'panels': [], 'layout': {}})):
            with self.assertRaises(ValueError):
                self.call('preview', **dict(args, document=invalid))
        row = before[0]
        key = row['__search_key__']
        self.api.dispatch('update', (self.auth, key, {'title': 'temporary'}), {'triggers': False})
        self.api.dispatch('update', (self.auth, key, {'title': row.get('title') or ''}), {'triggers': False})
        self.assertNotEqual(self.call('read')['revision'], state['revision'])
        with self.assertRaisesRegex(Exception, 'dependencies changed'):
            self.call('apply', **args)
        from tactic_stream.server.widget_configuration import WidgetConfigConflict
        state = self.call('read')
        def compete(name):
            try:
                return self.call('apply', document=dict(document(name), workspace_layout=None),
                    expected_revision=state['revision'], operation_id=str(uuid4()))
            except WidgetConfigConflict:
                return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            competed = list(workers.map(compete, ('first_page', 'second_page')))
        self.assertEqual(sum(result is not None for result in competed), 1)

    def test_related_task_filters_and_empty_results(self):
        self.api.dispatch('insert', (self.auth, 'cg/shot', dict(code='SH002', name='Other', scenes_code='EP001')))
        for code, process, status in [('SH001', 'lighting', 'Ready'), ('SH002', 'lighting', 'Blocked'), ('SH002', 'model', 'Ready')]:
            self.api.dispatch('insert', (self.auth, 'sthpw/task', dict(search_type='cg/shot?project=one', search_code=code,
                project_code='one', process=process, context=process, status=status, assigned='admin')), {'triggers': False})
        draft = dict(document(), records=[], task_filters=dict(assigned=['__current_login__'], process=['lighting'], status=['Ready']))
        state = self.call('read')
        args = dict(document=draft, expected_revision=state['revision'])
        preview = self.call('preview', **args)
        self.assertEqual([r['code'] for r in preview['sample']['records']], ['SH001'])
        self.assertIn('$LOGIN', preview['records'][0]['value'])
        empty = dict(draft, task_filters=dict(process=['not-configured']))
        self.assertEqual(self.call('preview', **dict(args, document=empty))['sample']['total'], 0)


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Install tactic-stream[agent] for MCP tests')
class MCPPages(unittest.TestCase):
    def test_stdio_page_creation(self):
        from mcp import Client, StdioServerParameters
        from test_transport import Transport
        Transport.setUpClass()
        self.addCleanup(Transport.tearDownClass)
        api = Api(Transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        from pyasm.security.authenticator import hash_password
        from pyasm.common.errors import SecurityException
        api.dispatch('insert', (dict(ticket=ticket, project='one'), 'sthpw/login',
            dict(login='page_guest', password=hash_password('private-guest-password'))))
        guest = api.get_ticket('page_guest', 'private-guest-password')
        with self.assertRaises(SecurityException):
            api.dispatch('execute_cmd', (dict(ticket=guest, project='one'), COMMAND,
                dict(action='read', project_code='one', search_type='contract/entity')))
        args = ['-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent', '--server', Transport.url,
                '--project', 'one', '--stream-root', str(ROOT), '--allow-page-save']
        parameters = StdioServerParameters(command=sys.executable, args=args,
            env=dict(os.environ, TACTIC_AGENT_TICKET=ticket, PYTHONPATH=str(ROOT/'src'), PYTHONUTF8='1'))
        draft = document()
        draft['columns'] = [dict(name='code', title='Code', width=180), dict(name='name', width=320)]
        draft['records'][0]['value'] = 'A'

        async def run():
            async with Client(parameters) as client:
                async def call(name, **values):
                    response = await client.call_tool(name, values)
                    self.assertFalse(response.is_error, response.content)
                    return response.structured_content
                state = await call('ts_page_read', search_type='contract/entity')
                request = dict(search_type='contract/entity', document=draft, expected_revision=state['revision'])
                rejected = await client.call_tool('ts_page_preview', dict(request, document=dict(draft, script='unexpected')))
                self.assertTrue(rejected.is_error)
                preview = await call('ts_page_preview', **request)
                self.assertEqual(preview['sample']['total'], 1)
                request['operation_id'] = str(uuid4())
                saved = await call('ts_page_save', **request)
                self.assertEqual(await call('ts_page_save', **request), saved)
                loaded = await call('ts_page_read', search_type='contract/entity')
                self.assertNotEqual(state['revision'], loaded['revision'])
                return request, saved
        request, saved = asyncio.run(run())
        if os.environ.get('TACTIC_PAGE_UI_CHECK') == '1':
            output = ROOT / '.screenshots/agent-pages'
            output.mkdir(parents=True, exist_ok=True)
            # Real browser opening through navigation, with the persisted filter/table/docks.
            subprocess.run([shutil.which('node'), 'tests/agent_pages.mjs', Transport.url, str(output)],
                cwd=ROOT / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),
                timeout=90, check=True)
            rows = ast.literal_eval(api.dispatch('query', (dict(ticket=ticket, project='one'), 'config/widget_config'), dict(order_bys=['id'])))
            payload = Path(Transport.temp.name) / 'page-config.json'
            payload.write_text(json.dumps(dict(rows=rows, saved=saved)), encoding='utf8')
            subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'tests/scripts/agent_page_handler.py'),
                            '--handler-root', str(ROOT.parent.parent/'TH'), '--fixture', str(payload)],
                           timeout=40, check=True)
        Transport.stop_server(); Transport.start_server()
        args[args.index('--server') + 1] = Transport.url
        parameters = StdioServerParameters(command=sys.executable, args=args,
            env=dict(os.environ, TACTIC_AGENT_TICKET=ticket, PYTHONPATH=str(ROOT/'src'), PYTHONUTF8='1'))
        async def recover():
            async with Client(parameters) as client:
                response = await client.call_tool('ts_page_operation', dict(
                    search_type='contract/entity', operation_id=request['operation_id']))
                self.assertFalse(response.is_error, response.content)
                self.assertEqual(response.structured_content, saved)
        asyncio.run(recover())


if __name__ == '__main__':
    if '--postgres' in sys.argv:
        from tools.file_project_checks import postgres
        sys.argv.remove('--postgres')
        successful = True
        for method in unittest.defaultTestLoader.getTestCaseNames(NativePages):
            with postgres() as config:
                NativePages.database_config = config
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([NativePages(method)]))
                successful = result.wasSuccessful() and successful
        raise SystemExit(not successful)
    unittest.main()
