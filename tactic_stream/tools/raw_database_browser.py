"""Check the raw editor on an owned temporary HTTP server, then stop it."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pyasm.common import Config
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.app import create_app


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['TACTIC_CONFIG_PATH'] = os.environ['TACTIC_TMP_CONFIG_PATH'] = ''
        Config.reload_config()
        store = Store(Path(directory) / 'data'); store.initialize(hash_password('raw-browser-admin'))
        with store.connection(write=True) as db:
            db.execute("CREATE TABLE raw_browser (id INTEGER PRIMARY KEY, value TEXT, number INTEGER DEFAULT 7, password TEXT DEFAULT 'private-browser-secret')")
            db.execute("INSERT INTO raw_browser (value) VALUES ('old')")
            db.execute('CREATE TABLE raw_page_profile (id INTEGER PRIMARY KEY, value TEXT, ' + ', '.join('column_' + str(index) + ' TEXT' for index in range(10)) + ')')
            db.executemany('INSERT INTO raw_page_profile (value) VALUES (?)', [(str(index),) for index in range(75)])
        ticket = Api(store).get_ticket('admin', 'raw-browser-admin')
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(); port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(store.data_dir, event_collector=False), log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('Temporary server did not start')
                time.sleep(.01)
            result = subprocess.run(['node', str(ROOT / 'tools/raw_database_browser.mjs')],
                input=json.dumps(dict(url='http://127.0.0.1:' + str(port), ticket=ticket)),
                text=True, capture_output=True, timeout=90,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            print(result.stdout)
            if result.returncode:
                raise RuntimeError(result.stderr)
        finally:
            server.should_exit = True
            thread.join(10); sock.close()
            if thread.is_alive():
                raise RuntimeError('Temporary server did not stop')


if __name__ == '__main__':
    main()
