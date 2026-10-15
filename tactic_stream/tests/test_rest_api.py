"""REST API compared with the original runtime on an owned HTTP server."""
import shutil
import tempfile
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


class RestParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        class RestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
                data = dict(method=self.command, query=parse_qs(urlsplit(self.path).query), body=parse_qs(body))
                self.send_response(409 if self.path.startswith('/error') else 200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'invalid JSON' if self.path.startswith('/invalid') else json.dumps(data, ensure_ascii=False).encode('utf-8'))
            do_POST = do_GET
            def log_message(self, *args):
                pass
        cls.rest_server = ThreadingHTTPServer(('127.0.0.1', 0), RestHandler)
        cls.rest_thread = threading.Thread(target=cls.rest_server.serve_forever, daemon=True)
        cls.rest_thread.start()
        cls.addClassCleanup(cls.rest_server.server_close)
        cls.addClassCleanup(cls.rest_server.shutdown)
        url = 'http://127.0.0.1:%s' % cls.rest_server.server_port
        cls.cases = []
        for method, path in (('GET', '/echo?existing=1'), ('POST', '/echo?existing=1'),
                             ('DELETE', '/echo'), ('GET', '/error'), ('GET', '/invalid')):
            cls.cases.append(dict(method='rest_contract', name='rest_' + method + path,
                project='one', rest=dict(method=method, url=url + path,
                params=dict(name='Сцена', tags=['a', 'b'], absent=None))))
        cls.cases.append(dict(method='rest_contract', name='rest_without_params', project='one',
            rest=dict(method='POST', url=url + '/echo', params=None)))

    def new_result(self, case):
        from tools.snapshot_probe import run_snapshot_case
        with tempfile.TemporaryDirectory() as directory:
            store = type(self.store)(Path(directory))
            shutil.copytree(self.store.data_dir, store.data_dir, dirs_exist_ok=True)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, original)
