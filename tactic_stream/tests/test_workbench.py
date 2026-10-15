"""Workspace acceptance on a private Store; its server always closes in cleanup."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from xmlrpc.client import Binary

import test_transport
from pyasm.security.authenticator import hash_password

ROOT = Path(__file__).resolve().parents[1]


class Workbench(unittest.TestCase):
    def test_complete_mobile_in_chromium(self):
        test_transport.Transport.setUpClass()
        self.addCleanup(test_transport.Transport.tearDownClass)
        fixture = test_transport.Transport()
        self.addCleanup(fixture.doCleanups)
        fixture._workspace_schema_fixture()
        proxy, auth, parent, _ = fixture._task_process_fixture(title='Phone assets')
        proxy.upload_file(auth, 'phone-preview.txt', Binary(b'Native phone snapshot preview'))
        proxy.simple_checkin(auth, parent['__search_key__'], 'publish/phone', 'phone-preview.txt', dict(mode='uploaded', create_icon=False))
        result = subprocess.run([shutil.which('node'), 'tests/mobile_complete.mjs', test_transport.Transport.url], cwd=ROOT/'frontend',
            env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_workspace_in_chromium(self):
        test_transport.Transport.setUpClass()
        self.addCleanup(test_transport.Transport.tearDownClass)
        self.url = test_transport.Transport.url
        fixture = test_transport.Transport()
        self.addCleanup(fixture.doCleanups)
        fixture._workspace_schema_fixture()
        fixture._task_process_fixture()
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            proxy.insert(auth, 'sthpw/login', dict(login='workspace_user', password=hash_password('private-test-password')))
        result = subprocess.run([shutil.which('node'), 'tests/workspace_complete.mjs', self.url], cwd=ROOT/'frontend',
            env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=150)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
