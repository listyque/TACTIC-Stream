"""Native group denies and named API execution, using an isolated store."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search.storage import Store
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.script_access import query_runner_access
from tactic_stream.server.script_shelf import script_shelf_request
from tactic_stream.server.script_editor import read_scripts


class RunnerAccessTests(unittest.TestCase):
    def test_access_catalog_contains_every_active_custom_script(self):
        from tactic_stream.server.security_rules import security_rules_request
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''
        }):
            Config.reload_config()
            store = Store(Path(directory) / 'sqlite')
            store.initialize(hash_password('isolated-test-password'))
            api = Api(store)
            ticket = api.get_ticket('admin', 'isolated-test-password')
            for folder, title, language in (
                ('helpers', 'cache_math', 'local_python'),
                ('server', 'utility', 'python'),
                ('templates', 'view_definition', 'xml'),
            ):
                api.dispatch('insert', (dict(ticket=ticket, project='admin'), 'config/custom_script',
                    dict(folder=folder, title=title, language=language, script='test fixture')))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket)
                targets = security_rules_request('read', {'project': 'admin'})['metadata']['targets']['script_runner']
                self.assertEqual({row['attributes']['key'] for row in targets}, {
                    '*', 'helpers/cache_math', 'server/utility', 'templates/view_definition',
                })

    def test_default_group_deny_admin_and_api_paths(self):
        path = 'tools/runners/example_runner'
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''
        }):
            Config.reload_config()
            store = Store(Path(directory) / 'sqlite')
            store.initialize(hash_password('isolated-test-password'))
            api = Api(store)
            with store.connection(write=True) as db:
                db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)',
                           ('runner_reader', 'runner_reader', hash_password('isolated-test-password')))
                db.execute('INSERT INTO login_group (code, login_group, access_level, access_rules) VALUES (?, ?, ?, ?)',
                           ('runner_group', 'runner_group', 'none', '<rules>'
                            '<rule group="project" code="admin" access="allow"/>'
                            '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/>'
                            '<rule group="search_type" code="config/widget_config" access="view"/>'
                            '<rule group="search_type" code="config/custom_script" access="view"/>'
                            '<rule group="script_runner" key="' + path + '" project="admin" access="deny"/>'
                            '</rules>'))
                db.execute('INSERT INTO login_in_group (login, login_group) VALUES (?, ?)',
                           ('runner_reader', 'runner_group'))
            ticket = api.get_ticket('runner_reader', 'isolated-test-password')
            admin = api.get_ticket('admin', 'isolated-test-password')
            api.dispatch('insert', (dict(ticket=admin, project='admin'), 'config/custom_script', {
                'folder': 'tools/runners', 'title': 'example_runner', 'language': 'javascript', 'script': 'return 42;'}))
            auth = dict(ticket=ticket, project='admin')
            with request_context(RequestContext(store, 'runner_reader', 'admin')):
                api.auth.bind_security('runner_reader', ticket)
                self.assertEqual(json.loads(query_runner_access('admin'))['denied'], [path])
                catalog = script_shelf_request('read', {})
                self.assertEqual(catalog['deniedRunners'], [path])
                self.assertFalse(any(row['path'] == path for row in catalog['scripts']))
                self.assertEqual(read_scripts()['scripts'], [])
                with self.assertRaisesRegex(SecurityException, 'cannot run'):
                    script_shelf_request('script', {'path': path})
                with self.assertRaisesRegex(SecurityException, 'cannot run'):
                    api.execute_js_script(auth, path, {})
            with self.assertRaisesRegex(SecurityException, 'cannot run'):
                api.dispatch('execute_python_script', (auth, path, {}))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', admin)
                self.assertEqual(json.loads(query_runner_access('admin'))['denied'], [])
