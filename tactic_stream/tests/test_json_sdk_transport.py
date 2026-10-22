"""Handler SDK JSON and XML-RPC against the same owned HTTP server."""
from datetime import datetime
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from xmlrpc.client import Binary, DateTime, Fault

import test_transport as transport_fixture
from tactic_stream import rpc_json

_native_path = sys.path.copy()
sys.path.insert(0, 'D:/grav/Tactic Stream/TH')
from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
from thlib.side.client.tactic_client_lib import rpc_json as handler_codec
from thlib import tactic_classes as tc, server_cache
from thlib.environment import env_inst, env_mode, env_server
from thlib.ui.controllers.search_runtime import SearchRuntimeMixin
sys.path[:] = _native_path


class JsonCodecTest(unittest.TestCase):
    def test_codec_copies_and_round_trip_preserve_literal_marker_dictionaries(self):
        self.assertEqual(Path(rpc_json.__file__).read_text(encoding='utf-8'), Path(handler_codec.__file__).read_text(encoding='utf-8'))
        value = {'binary': Binary(b'\x00\xff'), 'date': DateTime('20261015T12:34:56'),
                 'literal': {rpc_json.TYPE: 'binary', 'value': 'unencoded'},
                 'nested': [None, False, 2**62, 'Превью'], 'empty': b''}
        wire = handler_codec.encode(value)
        native = rpc_json.decode(wire, True)
        self.assertEqual(native['binary'], b'\x00\xff')
        self.assertEqual(native['date'], datetime(2026, 10, 15, 12, 34, 56))
        result = handler_codec.decode(rpc_json.encode(native))
        self.assertEqual(result['literal'], value['literal'])
        self.assertEqual(result['binary'].data, b'\x00\xff')
        self.assertEqual(result['date'].value, '20261015T12:34:56')

    def test_invalid_tags_are_rejected_and_writes_are_not_replayed(self):
        for value in ({rpc_json.TYPE: 'other', 'value': 'x'},
                      {rpc_json.TYPE: 'binary', 'value': '***'},
                      {rpc_json.TYPE: 'dict', 'items': [['x', 1], ['x', 2]]},
                      {rpc_json.TYPE: 'datetime', 'value': 'bad'}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rpc_json.decode(value, True)
        server = TacticServerStub(protocol='json', setup=False)
        transport = unittest.mock.Mock()
        server.set_transport(transport)
        server.set_server('http://private-test.invalid')
        transport.open.side_effect = HTTPError(server.server.url, 404, 'not found', {}, io.BytesIO(b'not json'))
        with self.assertRaisesRegex(Fault, 'XML-RPC'):
            server.server.insert({}, 'contract/entity', {'code': 'A'})
        self.assertEqual(transport.open.call_count, 1)

        transport.open.reset_mock()
        transport.open.side_effect = HTTPError(server.server.url, 503, 'unavailable', {}, io.BytesIO(b'{}'))
        with self.assertRaises(HTTPError):
            server.server.insert({}, 'contract/entity', {'code': 'A'})
        self.assertEqual(transport.open.call_count, 1)
        transport.open.reset_mock()
        transport.open.side_effect = TimeoutError('owned test timeout')
        with self.assertRaises(TimeoutError):
            server.server.insert({}, 'contract/entity', {'code': 'A'})
        self.assertEqual(transport.open.call_count, 1)

    def test_connection_test_uses_the_draft_proxy_and_transport(self):
        with (patch.object(tc, 'TacticServerStub') as factory,
              patch.object(tc.proxy, 'UrllibTransport') as transport):
            factory.return_value.fast_ping.return_value = 'OK'
            values = {'enabled': False, 'server': '', 'login': '', 'pass': ''}
            self.assertEqual(tc.server_fast_ping_predefined('http://draft.invalid', values, 'json'), 'ping_ok')
            factory.assert_called_once_with(protocol='json', setup=False)
            transport.return_value.update_proxy.assert_called_once_with(values)
            factory.return_value.set_transport.assert_called_once_with(transport.return_value)


class JsonSdkTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tactic_stream.server.app import create_app
        with patch('test_transport.create_app', side_effect=lambda root: create_app(root, event_collector=False)):
            transport_fixture.Transport.setUpClass.__func__(cls)

    tearDownClass = classmethod(transport_fixture.Transport.tearDownClass.__func__)
    admin_rpc = transport_fixture.Transport.admin_rpc

    def setUp(self):
        transport_fixture.Transport.setUp(self)
        for setting in (patch.object(env_mode, 'current_path', self.temp.name),
                        patch.object(env_server, 'get_proxy', return_value={'enabled': False, 'login': '', 'pass': '', 'server': ''}),
                        patch.object(env_server, 'get_timeout', return_value=5)):
            setting.start()
            self.addCleanup(setting.stop)

    def client(self, protocol):
        client = TacticServerStub(protocol=protocol, setup=False)
        client.set_server(self.url)
        if protocol == 'xmlrpc':
            self.addCleanup(client.server('close'))
        client.set_project('one')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        return client

    def test_both_sdk_transports_keep_auth_query_crud_commands_and_faults(self):
        for protocol in ('xmlrpc', 'json'):
            with self.subTest(protocol=protocol):
                client = self.client(protocol)
                self.assertEqual(client.ping(), 'OK')
                self.assertEqual(client.query('contract/entity', [('code', 'A')])[0]['name'], 'Первый')
                created = client.insert('contract/entity', {'code': 'JSON_' + protocol, 'name': 'Новый'})
                key = created['__search_key__']
                client.update(key, {'name': 'Обновлён'})
                self.assertEqual(client.get_by_search_key(key)['name'], 'Обновлён')
                self.assertEqual(client.execute_python_script('', {'code': 'return [None, False, "Превью"]'})['info'], [None, False, 'Превью'])
                result = client.execute_cmd('tactic.ui.panel.naming_cmd.NamingCmd', {
                    'action': 'load', 'project_code': 'one', 'search_type': 'contract/entity'})
                self.assertIn('revision', result['info'])
                with self.assertRaises(Fault) as caught:
                    client.get_ticket('admin', 'incorrect-password')
                self.assertEqual(caught.exception.faultCode, 403)
                self.assertIn('Login/Password combination incorrect', caught.exception.faultString)
                client.delete_sobject(key)
                self.assertEqual(client.query('contract/entity', [('code', 'JSON_' + protocol)]), [])

    def test_binary_datetime_and_literal_tags_reach_native_python_and_return(self):
        client = self.client('json')
        result = client.execute_python_script('', {'code': 'return kwargs["payload"]', 'payload': {
            'file': Binary(b'\x00\xff'), 'time': DateTime('20261015T12:34:56'),
            'literal': {rpc_json.TYPE: 'binary', 'value': 'data'}}})['info']
        self.assertEqual(result['file'].data, b'\x00\xff')
        self.assertEqual(result['time'].value, '20261015T12:34:56')
        self.assertEqual(result['literal'], {rpc_json.TYPE: 'binary', 'value': 'data'})
        script = 'from pyasm.common import Environment\nfrom pathlib import Path\nreturn (Path(Environment.get_upload_dir()) / "sdk.bin").read_bytes()'
        client.server.upload_file(client.ticket, 'sdk.bin', Binary(b'\x00\xff'))
        self.assertEqual(client.execute_python_script('', {'code': script})['info'].data, b'\x00\xff')

    def test_committed_write_with_failed_response_is_not_replayed(self):
        client = self.client('json')
        source = 'server.insert("contract/entity", {"code":"ONCE_ONLY","name":"Saved"})\nreturn {1, 2}'
        with self.assertLogs('tactic_stream.server.app', level='ERROR'), self.assertRaises(Fault) as caught:
            client.execute_python_script('', {'code': source})
        self.assertEqual(caught.exception.faultCode, 500)
        self.assertEqual(len(client.query('contract/entity', [('code', 'ONCE_ONLY')])), 1)

    def test_configured_auth_ping_and_full_search_use_json(self):
        with (patch.object(env_server, 'get_rpc_transport', return_value='json'),
              patch.object(env_server, 'get_ticket', return_value=None),
              patch.object(env_server, 'get_proxy', return_value={'enabled': False}),
              patch.object(env_server, 'get_timeout', return_value=10)):
            client = tc.server_auth(self.url, 'one', 'admin', 'private-test-password', get_ticket=True)
            self.assertEqual(client.get_protocol(), 'json')
            self.assertEqual(client.ping(), 'OK')
            self.assertEqual(tc.server_fast_ping_predefined(self.url, {}, 'json'), 'ping_ok')
            self.assertEqual(client.query('contract/entity', [('code', 'A')])[0]['code'], 'A')
            project = SimpleNamespace(info={'code': 'one'}, get_code=lambda: 'one', get_stypes=lambda: {})
            with (patch.object(env_server, 'get_ticket', return_value=client.get_login_ticket()),
                  patch.object(env_server, 'get_server', return_value=self.url),
                  patch.object(env_server, 'get_site', return_value={'site_name': ''}),
                  patch.object(env_inst, 'projects', {'one': project}),
                  patch.object(tc, 'get_snapshots_updates_list', return_value=[]),
                  patch.object(tc, 'env_read_config', return_value={}),
                  patch.object(server_cache, 'token', return_value=None),
                  patch.object(server_cache, 'read_entry', return_value=None),
                  patch.object(server_cache, 'invalidate_domains'),
                  self.assertLogs('tactic_stream.server.api', level='INFO') as captured):
                records, info, _ = SearchRuntimeMixin._query_sobjects(
                    'contract/entity', 'one', (), [('code', 'A')], 50, 0, bypass_cache=True)
            self.assertEqual(records[0].get_code(), 'A')
            self.assertTrue(records[0].info['__snapshots_complete__'])
            self.assertEqual(len(captured.records), 1)
            self.assertIn('ApiXMLRPC.execute_python_script', captured.records[0].getMessage())

    def test_plain_browser_json_stays_plain_and_sdk_codec_is_validated(self):
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        value = self.admin_rpc('query', [{'ticket': token, 'project': 'one'}, 'contract/entity'], {'filters': [['code', 'A']]})
        self.assertEqual(value[0]['code'], 'A')
        from urllib.request import Request, urlopen
        for codec in ('unknown', 1):
            body = json.dumps({'method': 'ping', 'args': [{'ticket': token, 'project': 'one'}], 'codec': codec}).encode()
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.url + '/admin/rpc', body, {'Content-Type': 'application/json'}))
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()


if __name__ == '__main__':
    unittest.main()
