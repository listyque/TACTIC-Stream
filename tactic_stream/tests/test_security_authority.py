"""Real native inheritance and desktop RPC guards on a private SQLite store."""

from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os

from pyasm.common import Config, Environment
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security import Login
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.security_rules import security_rules_request


class SecurityAuthority(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}))
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(root) / 'data')
        self.store.initialize(hash_password('private-authority-password'))
        self.api = Api(self.store)
        self.admin_ticket = self.api.get_ticket('admin', 'private-authority-password')
        with self.session('admin', self.admin_ticket):
            Login.create('operator', 'private-operator-password')
        self.ticket = self.api.get_ticket('operator', 'private-operator-password')

    @contextmanager
    def session(self, login, ticket):
        with request_context(RequestContext(self.store, login, 'admin')):
            yield self.api.auth.bind_security(login, ticket)

    def group(self, name, xml='<rules/>', children=''):
        group = SearchType.create('sthpw/login_group')
        for field, value in dict(login_group=name, access_level='none', access_rules=xml, sub_groups=children).items():
            group.set_value(field, value)
        group.commit()
        return group

    def test_nested_grants_denies_and_revocation_use_fresh_server_authority(self):
        with self.session('admin', self.admin_ticket):
            child = self.group('reviewers', '<rules><rule group="builtin" key="edit" access="view"/></rules>')
            parent = self.group('production', '<rules><rule group="builtin" key="edit" access="deny"/></rules>', 'reviewers')
            Login.get_by_login('operator').add_to_group('production')
            child_code, parent_code = child.get_code(), parent.get_code()
        with self.session('operator', self.ticket) as security:
            self.assertEqual(set(security.get_group_names()) - {'default'}, {'production', 'reviewers'})
            self.assertFalse(security.is_admin())
            self.assertTrue(security.check_access('builtin', 'edit', 'view', default='deny'))
            self.assertFalse(security.check_access('builtin', 'edit', 'edit', default='deny'))
        with self.session('admin', self.admin_ticket):
            catalog = security_rules_request('read', dict(project='admin'))
            draft = catalog['document']
            draft['groups'][parent_code]['subGroups'] = ''
            security_rules_request('save', dict(project='admin', document=draft, expected_revision=catalog['revision']))
        # The same ticket must lose inherited access on the next request.
        with self.session('operator', self.ticket) as security:
            self.assertNotIn('reviewers', security.get_group_names())
            self.assertFalse(security.check_access('builtin', 'edit', 'view', default='deny'))
        with self.session('admin', self.admin_ticket):
            self.assertIsNotNone(Search.get_by_code('sthpw/login_group', child_code))
            self.assertTrue(Environment.get_security().is_admin())

    def test_desktop_administration_procedures_reject_privileged_looking_names(self):
        handler = Path(__file__).resolve().parents[3] / 'TH' / 'thlib' / 'ui'
        if not handler.is_dir():
            self.skipTest('Requires the independently supplied Handler source checkout')
        import ast
        procedures = (
            ('admin/security_api.py', 'security_request', ('load', 'admin', 'admin')),
            ('admin/users_api.py', 'query_admin_users', ()),
            ('admin/schema_api.py', 'schema_request', ('list', 'admin')),
            ('admin/schema_api.py', 'schema_columns_request', ('admin', [])),
            ('admin/workflow_api.py', 'workflow_request', ('list', 'admin')),
            ('admin/search_types_api.py', 'search_types_request', ('list', 'admin')),
            ('security_store.py', 'query_security_groups', ()),
            ('security_store.py', 'save_security_group', ('', 'admin', '', ['operator'], [], '')),
        )
        with self.session('admin', self.admin_ticket):
            for name in ('supervisor', 'not_a_supervisor'):
                self.group(name)
                Login.get_by_login('operator').add_to_group(name)
        with self.session('operator', self.ticket):
            self.assertFalse(Environment.get_security().is_admin())
            for file, name, args in procedures:
                source = ast.parse((handler / file).read_text(encoding='utf-8'))
                function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == name)
                namespace = {}
                exec(compile(ast.Module(body=[function], type_ignores=[]), str(handler / file), 'exec'), namespace)
                with self.subTest(procedure=name), self.assertRaises(PermissionError):
                    namespace[name](*args)
                self.assertFalse(Environment.get_security().is_admin())


if __name__ == '__main__':
    unittest.main()
