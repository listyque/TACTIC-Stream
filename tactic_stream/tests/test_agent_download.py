"""Public network boundary, immutable attachment registration and retry receipts."""
import io
import asyncio
import socket
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
from uuid import uuid4

from tactic_stream import agent_download as web
from tests import test_agent_chat as chat

try:
    from mcp import Client
except ImportError:
    Client = None
else:
    from tactic_stream.admin_agent import StreamConnection, create_server


class Downloads(unittest.TestCase):
    @unittest.skipIf(Client is None, 'Install tactic-stream[agent] for MCP checks')
    def test_download_tool_requires_host_opt_in_and_binds_conversation(self):
        connection = StreamConnection('http://example.invalid', 'one', 'private-fixture')
        request_id, operation_id = str(uuid4()), str(uuid4())

        async def run():
            server = create_server(connection, chat.fixture.ROOT, request_id=request_id)
            async with Client(server) as client:
                self.assertNotIn('agent_web_download', [tool.name for tool in (await client.list_tools()).tools])
            server = create_server(connection, chat.fixture.ROOT, request_id=request_id, allow_web_download=True)
            async with Client(server) as client:
                result = await client.call_tool('agent_web_download', dict(url='https://example.org/ref.jpg', operation_id=operation_id))
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content['attachment_id'], operation_id)

        with patch.object(web, 'download_attachment', return_value=dict(attachment_id=operation_id)) as fetch:
            asyncio.run(run())
        fetch.assert_called_once_with(connection, request_id, 'https://example.org/ref.jpg', operation_id)

    def dns(self, host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (host if host in ('127.0.0.1', '169.254.169.254') else '93.184.216.34', 443))]

    def test_private_urls_and_mixed_dns_are_rejected_before_connect(self):
        with patch.object(web.socket, 'getaddrinfo', side_effect=self.dns):
            for url in ('http://example.org/image.jpg', 'https://user:secret@example.org/a', 'https://example.org:8443/a', 'https://127.0.0.1/a', 'https://169.254.169.254/a'):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    web.public_target(url)
        answers = self.dns('example.org') + self.dns('127.0.0.1')
        with patch.object(web.socket, 'getaddrinfo', return_value=answers), self.assertRaises(ValueError):
            web.public_target('https://example.org/a')

    def test_tls_connect_uses_validated_ip_and_original_hostname(self):
        connection = web.PublicHTTPSConnection('example.org', ['93.184.216.34'])
        self.assertTrue(connection._context.check_hostname)
        wrapped = Mock()
        connection._context = Mock()
        connection._context.wrap_socket.return_value = wrapped
        with patch.object(web.socket, 'create_connection', return_value=Mock()) as create:
            connection.connect()
        self.assertEqual(create.call_args.args[0], ('93.184.216.34', 443))
        self.assertEqual(connection._context.wrap_socket.call_args.kwargs['server_hostname'], 'example.org')
        connection.close()

    def response(self, content=b'image bytes', status=200, **headers):
        result = Mock(status=status)
        result.getheader.side_effect = lambda key: headers.get(key)
        result.read.side_effect = io.BytesIO(content).read
        return result

    def test_direct_file_redirect_checks_limits_and_no_credentials(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(web.socket, 'getaddrinfo', side_effect=self.dns), patch.object(web, 'PublicHTTPSConnection') as connection:
            target = Path(directory) / 'payload'
            connection.return_value.getresponse.return_value = self.response(**{'Content-Type':'image/jpeg','Content-Length':'11'})
            metadata = web.download_file('https://example.org/photo.jpg', target)
            self.assertEqual(target.read_bytes(), b'image bytes')
            self.assertEqual(metadata['name'], 'photo.jpg')
            headers = connection.return_value.request.call_args.kwargs['headers']
            self.assertEqual(set(headers), {'User-Agent', 'Accept-Encoding'})
            for response in (
                self.response(status=302, Location='https://127.0.0.1/private'),
                self.response(**{'Content-Type':'text/html'}),
                self.response(**{'Content-Length': str(web.MAX_BYTES+1)}),
                self.response(**{'Content-Length':'12'}),
            ):
                connection.return_value.getresponse.return_value = response
                with self.assertRaises(ValueError):
                    web.download_file('https://example.org/photo.jpg', target)
            connection.return_value.getresponse.return_value = self.response(b'12345')
            with patch.object(web, 'MAX_BYTES', 4), self.assertRaises(ValueError):
                web.download_file('https://example.org/photo.jpg', target)


@unittest.skipIf(Client is None, 'Install tactic-stream[agent] for MCP checks')
class DownloadAttachments(unittest.TestCase):
    setUp = chat.AgentChat.setUp
    call = chat.AgentChat.call
    submit = chat.AgentChat.submit
    command = chat.AgentChat.command

    def test_download_permission_replay_and_native_attachment_ownership(self):
        self.call('heartbeat', host_id=self.host, label='Codex', capabilities=dict(changes=True,trials=False,web_search=True))
        row,_ = self.submit(document=dict(self.document,allow_web=True,allow_changes=True))
        self.call('claim',host_id=self.host)
        connection = StreamConnection('http://example.invalid','one','private-fixture')
        code = str(uuid4())
        def download(url, path):
            path.write_bytes(b'downloaded reference')
            return dict(name='reference.txt',size=20,media_type='text/plain')
        with patch.object(connection,'command',side_effect=self.command), patch.object(web,'download_file',side_effect=download) as fetch:
            first = web.download_attachment(connection,row['request_id'],'https://example.org/ref.txt',code)
            self.assertEqual(web.download_attachment(connection,row['request_id'],'https://example.org/ref.txt',code),first)
            fetch.assert_called_once()
            with self.assertRaisesRegex(ValueError,'another URL'):
                web.download_attachment(connection,row['request_id'],'https://example.org/other.txt',code)
        self.assertEqual(first['attachment_id'],code)
        self.assertEqual(first['source_url'],'https://example.org/ref.txt')
        saved = self.call('read',request_id=row['request_id'])
        self.assertEqual(saved['messages'][-1]['attachments'][0], first)
        common = dict(request_id=row['request_id'])
        state = self.command('editing','workflow_read',search_type='cg/shot',**common)
        self.command('editing','workflow_apply',search_type='cg/shot',expected_revision=state['revision'],
            operation_id=str(uuid4()),processes=['reference'],search_keys=self.document['context']['search_keys'],**common)
        result = self.command('editing','checkin',search_key=self.document['context']['search_keys'][0],
            process='reference',attachments=[code],operation_id=str(uuid4()),**common)
        self.assertEqual(len(result['snapshots']),1)
        blocked,_ = self.submit()
        with patch.object(connection,'command',side_effect=self.command), patch.object(web,'download_file') as fetch, self.assertRaisesRegex(ValueError,'internet access'):
            web.download_attachment(connection,blocked['request_id'],'https://example.org/ref.txt',str(uuid4()))
        fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
