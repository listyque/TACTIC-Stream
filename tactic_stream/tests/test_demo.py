"""Fresh demonstration content, account permissions and non-destructive retries."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary

from pyasm.common.errors import SecurityException
from pyasm.common import Environment
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.startup import FirstRunInit
from tactic_stream.demo import install, verify_content
from tactic_stream.server.api import Api
from tools.demo_delivery import build


class Demo(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data = self.root / 'data'
        environment = patch.dict(os.environ, TACTIC_DATA_DIR=str(self.data))
        environment.start()
        self.addCleanup(environment.stop)
        self.store = Store(self.data)
        self.password = 'private-test-password'
        self.store.initialize(hash_password(self.password))
        with request_context(RequestContext(self.store, 'admin')):
            FirstRunInit().execute()
        self.content = build(self.root / 'demo')
        self.api = Api(self.store)
        self.api.protocol = 'json'
        self.ticket = self.api.get_ticket('admin', self.password)
        self.addCleanup(self.api.auth.logout, self.ticket)

    def test_projects_files_plugins_roles_and_repeat(self):
        result = install(self.store, 'admin', self.password, self.content)
        self.assertEqual(result['projects']['orbit'], dict(assets=6, tasks=21, shots=3, sequences=1))
        self.assertEqual(result['projects']['atlas'], dict(assets=3, tasks=9))
        accounts = json.loads((self.data / 'demo-accounts.json').read_text())
        self.assertEqual(len({row['password'] for row in accounts}), 3)
        for project in ('orbit', 'atlas'):
            auth = dict(ticket=self.ticket, project=project)
            assets = self.api.dispatch('query', (auth, project + '/asset'))
            snapshots = self.api.dispatch('query', (auth, 'sthpw/snapshot', [('project_code', project)]))
            self.assertGreaterEqual(len(snapshots), len(assets) * 2 + 1)
            records = self.api.dispatch('query', (auth, 'sthpw/file', [('project_code', project)]))
            with request_context(RequestContext(self.store, 'admin', project)):
                asset_root = Path(Environment.get_asset_dir())
                self.assertTrue(asset_root.is_relative_to(self.data))
                for record in records:
                    published = asset_root / record['relative_dir'] / record['file_name']
                    self.assertTrue(published.is_file(), published)
                    self.assertGreater(published.stat().st_size, 0)
            self.assertEqual(len(self.api.dispatch('query', (auth, 'studio/review'))), 3)
            for account in accounts:
                ticket = self.api.get_ticket(account['login'], account['password'])
                try:
                    user = dict(ticket=ticket, project=project)
                    self.assertEqual(len(self.api.dispatch('query', (user, project + '/asset'))), len(assets))
                    args = (user, assets[0]['__search_key__'], dict(description='Demonstration permission check'))
                    if account['role'] == 'readers':
                        with self.assertRaises(SecurityException):
                            self.api.dispatch('update', args)
                        with self.assertRaises(SecurityException):
                            self.api.dispatch('create_note', (user, assets[0]['__search_key__'], 'Reader must not write'))
                    else:
                        self.api.dispatch('update', args)
                        self.api.dispatch('create_note', (user, assets[0]['__search_key__'], 'Artist permission check'))
                        self.api.dispatch('upload_file', (user, 'permission.txt', Binary(b'Artist publication')))
                        snapshot = self.api.dispatch('simple_checkin', (user, assets[0]['__search_key__'],
                            'publish/acceptance', 'permission.txt'), dict(mode='upload', create_icon=False))
                        self.assertGreater(snapshot['version'], 0)
                finally:
                    self.api.auth.logout(ticket)
        reader = next(account for account in accounts if account['role'] == 'readers')
        with self.assertRaises(PermissionError):
            install(self.store, reader['login'], reader['password'], self.content)
        credentials = (self.data / 'demo-accounts.json').read_bytes()
        self.assertEqual(install(self.store, 'admin', self.password, self.content), result)
        self.assertEqual((self.data / 'demo-accounts.json').read_bytes(), credentials)

    def test_existing_project_and_damaged_content_are_refused_without_changes(self):
        auth = dict(ticket=self.ticket, project='admin')
        self.api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd',
            dict(project_code='existing', project_title='Keep this project', project_stype=['asset'])))
        with self.assertRaises(FileExistsError):
            install(self.store, 'admin', self.password, self.content)
        projects = self.api.dispatch('query', (auth, 'sthpw/project'))
        self.assertIn('existing', {row['code'] for row in projects})
        self.assertNotIn('orbit', {row['code'] for row in projects})
        self.assertFalse((self.data / 'demo-accounts.json').exists())
        (self.content / 'assets/survey-drone.png').write_bytes(b'damaged')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verify_content(self.content)
