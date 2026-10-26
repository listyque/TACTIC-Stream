"""Anonymous, bounded public HTTPS downloads in the external agent host only."""
import base64
import ipaddress
import mimetypes
import socket
import tempfile
import time
from contextlib import closing
from http.client import HTTPSConnection
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urljoin, unquote
from uuid import UUID

MAX_BYTES = 64 * 1024 * 1024


def public_target(url):
    if not isinstance(url, str) or len(url) > 4096 or any(char.isspace() or ord(char) < 32 for char in url):
        raise ValueError('Use a public HTTPS file URL')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None):
        raise ValueError('Only anonymous public HTTPS on port 443 is supported')
    host = parsed.hostname.encode('idna').decode('ascii')
    addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(address).is_global or ipaddress.ip_address(address).is_multicast for address in addresses):
        raise ValueError('Private, loopback and reserved download addresses are not allowed')
    return parsed, host, addresses


class PublicHTTPSConnection(HTTPSConnection):
    """Pin validated DNS results while retaining normal TLS hostname verification."""

    def __init__(self, host, addresses):
        super().__init__(host, timeout=10)
        self.addresses = addresses

    def connect(self):
        for address in self.addresses[:4]:
            try:
                self.sock = socket.create_connection((address, 443), self.timeout)
                self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
                return
            except OSError:
                self.close()
        raise OSError('Could not connect to the public HTTPS origin')


def download_file(url, destination):
    started = time.monotonic()
    for _ in range(6):
        if time.monotonic() - started > 60:
            raise ValueError('Download exceeded its time limit')
        parsed, host, addresses = public_target(url)
        with closing(PublicHTTPSConnection(host, addresses)) as connection:
            target = parsed.path or '/'
            if parsed.query:
                target += '?' + parsed.query
            connection.request('GET', target, headers={'User-Agent': 'TACTIC-Stream-reference/1.0', 'Accept-Encoding': 'identity'})
            with closing(connection.getresponse()) as response:
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if not location:
                        raise ValueError('Download redirect has no destination')
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise ValueError('Download returned HTTP ' + str(response.status))
                media_type = (response.getheader('Content-Type') or '').split(';')[0].strip().lower()
                if media_type in ('text/html', 'application/xhtml+xml'):
                    raise ValueError('This URL is a web page. Use its direct file link instead')
                declared = response.getheader('Content-Length')
                if declared is not None and (not declared.isdecimal() or int(declared) > MAX_BYTES):
                    raise ValueError('Downloaded files must be at most 64 MB')
                size = 0
                with destination.open('wb') as output:
                    while chunk := response.read(min(384 * 1024, MAX_BYTES - size + 1)):
                        size += len(chunk)
                        if size > MAX_BYTES or time.monotonic() - started > 60:
                            raise ValueError('Download exceeded its size or time limit')
                        output.write(chunk)
                if not size or declared is not None and size != int(declared):
                    raise ValueError('The remote file download was empty or incomplete')
                name = PurePosixPath(unquote(parsed.path)).name or 'download'
                if not PurePosixPath(name).suffix:
                    name += mimetypes.guess_extension(media_type) or '.bin'
                return dict(name=name, size=size, media_type=media_type or mimetypes.guess_type(name)[0] or 'application/octet-stream', source_url=url)
    raise ValueError('Too many download redirects')


def download_attachment(connection, request_id, url, operation_id):
    if str(UUID(operation_id)) != operation_id:
        raise ValueError('Expected a canonical operation UUID')
    request = connection.command('request', 'read', request_id=request_id)
    if not request['document'].get('allow_web') or request['status'] != 'running':
        raise ValueError('Web downloads require an active conversation with internet access')
    previous = next((message for message in request.get('messages', []) if message['id'] == operation_id), None)
    if previous:
        if previous.get('source_url') != url:
            raise ValueError('Download operation ID already has another URL')
        return previous['attachments'][0]
    with tempfile.TemporaryDirectory(prefix='tactic-web-download-') as directory:
        target = Path(directory) / 'payload'
        metadata = download_file(url, target)
        connection.command('attachment', 'start', attachment_id=operation_id, name=metadata['name'],
                           size=metadata['size'], media_type=metadata['media_type'])
        with target.open('rb') as source:
            offset = 0
            while chunk := source.read(384 * 1024):
                connection.command('attachment', 'append', attachment_id=operation_id, offset=offset,
                                   data=base64.b64encode(chunk).decode())
                offset += len(chunk)
        connection.command('attachment', 'finish', attachment_id=operation_id)
    return connection.command('request', 'download', request_id=request_id, operation_id=operation_id, source_url=url)
