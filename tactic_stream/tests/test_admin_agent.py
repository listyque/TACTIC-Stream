"""MCP -> actual HTTP -> native TACTIC, on owned SQLite data only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import threading
import unittest
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
                self.assertEqual(len(names), 8)
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
