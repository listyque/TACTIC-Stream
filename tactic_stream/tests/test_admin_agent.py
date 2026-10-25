"""MCP -> actual HTTP -> native TACTIC, on owned SQLite data only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from uuid import uuid4
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from mcp import Client, StdioServerParameters
except ImportError:
    Client = None
else:
    from mcp.server.mcpserver.exceptions import ToolError
    from tactic_stream.admin_agent import MAX_RESPONSE, StreamConnection, create_server

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(Client is None, 'Install tactic-stream[agent] to test the optional MCP adapter')
class AgentTransport(unittest.TestCase):
    def test_origin_validation(self):
        for value in ('file:///data', 'http://user:secret@host', 'http://host/api',
                      'http://host/?ticket=secret', 'http://host/#fragment', 'http://host\n'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                StreamConnection(value, 'one', 'private-test-ticket')
        with self.assertRaises(ValueError):
            StreamConnection('http://host', 'one', '')

    def test_redirect_errors_invalid_json_and_response_bounds(self):
        visited = []
        ticket = 'secret-"quoted-ticket'

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                visited.append(self.path)
                if self.path == '/redirect':
                    self.send_response(307)
                    self.send_header('Location', '/leak')
                    self.end_headers()
                    return
                self.send_response(403 if self.path == '/error' else 200)
                self.end_headers()
                self.wfile.write({'/error': json.dumps({'error': ticket}).encode(),
                                  '/invalid': b'not JSON', '/large': b' ' * (MAX_RESPONSE + 1),
                                  '/ok': b'{"result":false}'}[self.path])

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = StreamConnection(f'http://127.0.0.1:{server.server_port}', 'one', ticket)
            for path, message in (('/redirect', 'redirect refused'), ('/error', 'REDACTED'),
                                  ('/invalid', 'invalid JSON'), ('/large', 'retrieval limit')):
                with self.subTest(path=path), self.assertRaisesRegex(ToolError, message):
                    connection.request(path)
            self.assertNotIn('/leak', visited)
            self.assertIs(connection.request('/ok')['result'], False)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)
        self.assertFalse(thread.is_alive())

    def test_references_and_strict_tool_inputs(self):
        async def run():
            connection = StreamConnection('http://127.0.0.1:1', 'one', 'private-test-ticket')
            server = create_server(connection, ROOT)
            async with Client(server) as client:
                result = await client.call_tool('reference_read', {'reference': 'ts.start', 'limit': 2})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content['next_offset'], 2)
                self.assertEqual(result.structured_content['owner'], 'TS')
                catalog = await client.call_tool('reference_catalog', {})
                for item in catalog.structured_content['references']:
                    if item['owner'] == 'TS':
                        self.assertTrue(item['available'], item['id'])
                for arguments in ({'reference': '../data/config/tactic-conf.xml'},
                                  {'reference': 'th.api'}, {'reference': 'ts.start', 'limit': 51},
                                  {'reference': 'ts.start', 'offset': -1},
                                  {'reference': 'ts.start', 'offset': True}):
                    result = await client.call_tool('reference_read', arguments)
                    self.assertTrue(result.is_error)
                draft = dict(search_type='contract/entity', document={'file_naming': '{code}.{ext}'},
                             sample={'key': 'contract/entity?project=one&code=A', 'file': 'input.exr'})
                for field, value in (('allow_execution', True), ('ticket', 'model-ticket'),
                                     ('latest_versionless', 'false')):
                    result = await client.call_tool('ts_naming_preview', dict(
                        draft, document=dict(draft['document'], **{field: value})))
                    self.assertTrue(result.is_error)
                    self.assertNotIn('connection failed', str(result.content))
            handler = ROOT.parents[1] / 'TH'
            if handler.is_dir():
                async with Client(create_server(connection, ROOT, handler)) as client:
                    result = await client.call_tool('reference_read', {'reference': 'th.triggers', 'limit': 2})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content['owner'], 'TH')
        asyncio.run(run())


@unittest.skipIf(Client is None, 'Install tactic-stream[agent] to test the optional MCP adapter')
class AgentNativeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the HTTP fixture lifecycle, without inheriting its unrelated tests.
        from test_transport import Transport
        cls.transport = Transport
        Transport.setUpClass()
        cls.addClassCleanup(Transport.tearDownClass)

    def test_stdio_native_naming_and_legacy_host(self):
        from tactic_stream.server.api import Api
        api = Api(self.transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=ticket, project='one')
        from pyasm.security.authenticator import hash_password
        api.dispatch('insert', (auth, 'sthpw/login', {
            'login': 'agent_guest', 'password': hash_password('private-guest-password')}))
        guest_ticket = api.get_ticket('agent_guest', 'private-guest-password')
        types = ('config/naming', 'sthpw/snapshot', 'sthpw/file')

        def records():
            return {kind: api.dispatch('query', (auth, kind)) for kind in types}

        before = records()
        environment = dict(os.environ, TACTIC_AGENT_TICKET=ticket,
                           PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
        parameters = StdioServerParameters(command=sys.executable, args=[
            '-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent',
            '--server', self.transport.url, '--project', 'one', '--stream-root', str(ROOT),
        ], env=environment)

        async def run():
            async with Client(parameters) as client:
                listed = await client.list_tools()
                names = {tool.name for tool in listed.tools}
                self.assertEqual(len(names), 19)
                self.assertFalse(any('save' in name or 'execute' in name for name in names))

                async def call(name, **arguments):
                    result = await client.call_tool(name, arguments)
                    self.assertFalse(result.is_error, result.content)
                    self.assertNotIn(ticket, str(result))
                    return result.structured_content

                capability = await call('agent_capabilities')
                self.assertFalse(capability['can_apply'])
                self.assertEqual(capability['project'], 'one')
                self.assertTrue(capability['server']['database_initialized'])
                catalog = await call('ts_types', limit=1)
                self.assertEqual(len(catalog['items']), 1)
                self.assertEqual(catalog['next_offset'], 1)
                metadata = await call('ts_type_read', identity='contract/entity')
                self.assertIn('columns', metadata['metadata'])
                schema = await call('ts_schema_read')
                self.assertIn('revision', schema)
                loaded = await call('ts_naming_read', search_type='contract/entity')
                self.assertIn('revision', loaded)
                self.assertLessEqual(len(loaded['items']), 50)
                arguments = dict(search_type='contract/entity', document=dict(
                    context='agent/*', dir_naming='{project.code}/{sobject.code}/{parent.code}',
                    file_naming='{sobject.code}_{snapshot.context[1]}_v{version}.{ext}'),
                    sample=dict(key='contract/entity?project=one&code=A', file='input.exr',
                                version=12, process='agent', context='agent/main'))
                preview = await call('ts_naming_preview', **arguments)
                self.assertFalse(preview['executedCustomCode'])
                self.assertTrue(preview['matches'])
                self.assertEqual(preview['results'][0]['path'], 'one/A/NO_PARENT/A_main_v012.exr')
                modes = await call('ts_naming_preview', **dict(arguments, document=dict(
                    arguments['document'], latest_versionless=True, current_versionless=True)))
                self.assertEqual([item['mode'] for item in modes['results']], ['version', 'latest', 'current'])
                for key, value in (('sample', dict(arguments['sample'], key='contract/entity?project=two&code=A')),
                                   ('document', dict(arguments['document'], script_path='agent/not-allowed')),
                                   ('document', dict(arguments['document'], file_naming='{@PYTHON(agent/unsafe)}'))):
                    result = await client.call_tool('ts_naming_preview', dict(arguments, **{key: value}))
                    self.assertTrue(result.is_error)
                reference = await call('reference_read', reference='ts.start', limit=3)
                self.assertEqual(reference['next_offset'], 3)
                self.assertTrue((await client.call_tool('ts_naming_save', {})).is_error)
            # A 2025-era host must also negotiate against the same SDK-owned transport.
            async with Client(parameters, mode='legacy') as client:
                result = await client.call_tool('ts_naming_read', {'search_type': 'contract/entity'})
                self.assertFalse(result.is_error, result.content)
            for denied_ticket in ('invalid-ticket', guest_ticket):
                connection = StreamConnection(self.transport.url, 'one', denied_ticket)
                async with Client(create_server(connection, ROOT)) as client:
                    result = await client.call_tool('ts_naming_read', {'search_type': 'contract/entity'})
                    self.assertTrue(result.is_error)
                    self.assertIn('403', str(result.content))
        asyncio.run(run())
        self.assertEqual(records(), before, 'Preview must not save naming, snapshots or files')

    def test_save_replay_restart_and_real_checkin(self):
        from tactic_client_lib import TacticServerStub
        from tactic_stream.server.api import Api
        api = Api(self.transport.store)
        ticket = api.get_ticket('admin', 'private-test-password')
        connection = StreamConnection(self.transport.url, 'one', ticket)
        operation_id = str(uuid4())
        document = dict(context='agent_save/*', checkin_type='strict',
                        dir_naming='{project.code}/agent_save/{sobject.code}',
                        file_naming='{sobject.code}_{snapshot.context[1]}_v{version}.{ext}')
        sample = dict(key='contract/entity?project=one&code=A', file='source.bin',
                      process='agent_save', context='agent_save/main')
        parameters = StdioServerParameters(command=sys.executable, args=[
            '-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent', '--server', self.transport.url,
            '--project', 'one', '--stream-root', str(ROOT), '--allow-naming-save'],
            env=dict(os.environ, TACTIC_AGENT_TICKET=ticket, PYTHONUTF8='1', PYTHONPATH=str(ROOT/'src')))

        async def save():
            async with Client(parameters) as client:
                loaded = await client.call_tool('ts_naming_read', {'search_type': 'contract/entity'})
                args = dict(search_type='contract/entity', document=document, sample=sample,
                            expected_revision=loaded.structured_content['revision'], operation_id=operation_id)
                preview = await client.call_tool('ts_naming_preview', dict(search_type='contract/entity',
                                                                         document=document, sample=sample))
                self.assertFalse(preview.is_error, preview.content)
                result = await client.call_tool('ts_naming_save', args)
                self.assertFalse(result.is_error, result.content)
                self.assertEqual(result.structured_content['status'], 'applied')
                replay = await client.call_tool('ts_naming_save', args)
                self.assertEqual(replay.structured_content, result.structured_content)
                stale = await client.call_tool('ts_naming_save', dict(args, operation_id=str(uuid4())))
                self.assertTrue(stale.is_error)
                changed = await client.call_tool('ts_naming_save', dict(args, document=dict(document, file_naming='other.bin')))
                self.assertTrue(changed.is_error)
                return args, result.structured_content, preview.structured_content['results'][0]
        args, receipt, preview = asyncio.run(save())
        # Both the MCP process above and the HTTP server restart; receipts are database-owned.
        self.transport.stop_server()
        self.transport.start_server()
        connection = StreamConnection(self.transport.url, 'one', ticket)

        async def verify():
            async with Client(create_server(connection, ROOT, allow_naming_save=True)) as client:
                replay = await client.call_tool('ts_naming_save', args)
                self.assertFalse(replay.is_error, replay.content)
                self.assertEqual(replay.structured_content, receipt)
                status = await client.call_tool('ts_naming_operation', dict(
                    search_type='contract/entity', operation_id=operation_id))
                self.assertEqual(status.structured_content, receipt)
                loaded = await client.call_tool('ts_naming_read', dict(search_type='contract/entity'))
                self.assertNotEqual(loaded.structured_content['revision'], args['expected_revision'])
                self.assertEqual(sum(row['identity'] == receipt['identity'] for row in loaded.structured_content['rules']), 1)
        asyncio.run(verify())

        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.transport.url)
        client.set_project('one')
        client.set_ticket(ticket)
        self.addCleanup(client.server.__exit__, None, None, None)
        source = Path(self.transport.temp.name) / 'source.bin'
        source.write_bytes(b'agent native check-in one')
        first = client.simple_checkin(sample['key'], sample['context'], str(source),
                                      mode='upload', create_icon=False, checkin_type='strict')
        file = first['__file_sobjects__'][0]
        destination = Path(file['checkin_dir']) / file['file_name']
        self.assertEqual(file['file_name'], preview['file'])
        self.assertEqual(file['relative_dir'], preview['directory'])
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        source.write_bytes(b'agent native check-in two')
        second = client.simple_checkin(sample['key'], sample['context'], str(source),
                                       mode='upload', create_icon=False, checkin_type='strict')
        second_file = second['__file_sobjects__'][0]
        self.assertIn('_v002.bin', second_file['file_name'])
        self.assertEqual(destination.read_bytes(), b'agent native check-in one')
        self.assertEqual((Path(second_file['checkin_dir']) / second_file['file_name']).read_bytes(), source.read_bytes())

        class LostReply(StreamConnection):
            def request(self, path, payload=None):
                result = super().request(path, payload)
                if payload and payload.get('method') == 'execute_cmd' and payload['args'][2]['action'] == 'apply':
                    raise ToolError('Connection lost after server committed')
                return result

        async def recover_lost_reply():
            current = connection.command('naming', 'load', search_type='contract/entity')
            retry = dict(args, operation_id=str(uuid4()), identity=receipt['identity'],
                         expected_revision=current['revision'], document=dict(document,
                         file_naming='{sobject.code}_recovered_v{version}.{ext}'))
            failing = LostReply(self.transport.url, 'one', ticket)
            async with Client(create_server(failing, ROOT, allow_naming_save=True)) as host:
                result = await host.call_tool('ts_naming_save', retry)
                self.assertTrue(result.is_error)
                self.assertIn('ts_naming_operation', str(result.content))
            async with Client(create_server(connection, ROOT, allow_naming_save=True)) as host:
                status = await host.call_tool('ts_naming_operation', dict(
                    search_type='contract/entity', operation_id=retry['operation_id']))
                self.assertEqual(status.structured_content['status'], 'applied')
                replay = await host.call_tool('ts_naming_save', retry)
                self.assertEqual(replay.structured_content, status.structured_content)
                current = await host.call_tool('ts_naming_read', {'search_type': 'contract/entity'})
                self.assertEqual(sum(row['identity'] == receipt['identity'] for row in current.structured_content['rules']), 1)
        asyncio.run(recover_lost_reply())
