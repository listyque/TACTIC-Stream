"""Real native inheritance and desktop RPC guards on a private SQLite store."""

from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os

from pyasm.common import Config, Environment
from pyasm.common.errors import SecurityException
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

    def test_effective_report_uses_native_groups_and_preserves_caller_and_tickets(self):
        from pyasm.security.effective import effective_security
        with self.session('admin', self.admin_ticket) as caller:
            self.group('reviewers', '<rules><rule group="builtin" key="edit" access="view"/></rules>')
            self.group('production', '<rules><rule group="builtin" key="edit" access="deny"/></rules>', 'reviewers')
            Login.get_by_login('operator').add_to_group('production')
            tickets = len(Search('sthpw/ticket').get_sobjects())
            report = effective_security('operator')
            self.assertIs(Environment.get_security(), caller)
            self.assertTrue(caller.is_admin())
            self.assertEqual(len(Search('sthpw/ticket').get_sobjects()), tickets)
            self.assertFalse(report['administrator'])
            groups = {group['name']: group for group in report['groups']}
            self.assertTrue(groups['production']['direct'])
            self.assertEqual(groups['reviewers']['paths'], [['production', 'reviewers']])
            rule = next(row for row in report['rules'] if row['scope'] == 'builtin' and row['attributes'].get('key') == 'edit')
            self.assertEqual(rule['access'], 'view')
            self.assertEqual({row['group'] for row in rule['sources']}, {'production', 'reviewers'})
            with self.assertRaises(ValueError):
                effective_security('not-a-user')
            self.assertIs(Environment.get_security(), caller)
        with self.session('operator', self.ticket):
            with self.assertRaises(PermissionError):
                effective_security('admin')

    def test_group_tool_policy_inherits_and_live_calls_recheck_without_new_ticket(self):
        from tactic.ui.panel.agent_request_cmd import AgentRequestCmd
        from tactic_stream.server.agent_security import tool_access
        with self.session('admin', self.admin_ticket):
            child = self.group('agent_readers', '<rules><rule group="agent_tool" key="agent_context" access="allow"/></rules>')
            self.group('limited_admin', '<rules><rule group="agent_tool" key="*" access="deny"/><rule group="mcp_tool" key="*" access="deny"/></rules>', 'admin|agent_readers')
            Login.get_by_login('operator').add_to_group('limited_admin')
        with self.session('operator', self.ticket) as security:
            self.assertTrue(security.is_admin())
            from pyasm.security.effective import effective_security
            report=effective_security('operator')
            source=next(rule for rule in report['rules'] if rule['scope']=='agent_tool' and rule['attributes'].get('key')=='agent_context')
            self.assertEqual(source['access'],'allow')
            self.assertEqual(source['sources'][0]['group'],'agent_readers')
            self.assertTrue(tool_access(security, 'agent_context'))
            self.assertFalse(tool_access(security, 'agent_context', 'mcp'))
            self.assertFalse(tool_access(security, 'ts_project_create'))
            check = AgentRequestCmd(project_code='admin', action='tool_check', tool='agent_context')
            check.execute()
            self.assertTrue(check.info['allowed'])
            with self.assertRaises(SecurityException):
                AgentRequestCmd(project_code='admin', action='tool_check', tool='ts_project_create').execute()
        with self.session('admin', self.admin_ticket):
            child.set_value('access_rules', '<rules/>')
            child.commit()
        with self.session('operator', self.ticket):
            with self.assertRaises(SecurityException):
                AgentRequestCmd(project_code='admin', action='tool_check', tool='agent_context').execute()

    def test_effective_endpoint_summarizes_native_access_and_handler_matches_stream(self):
        import ast
        import json
        with self.session('admin', self.admin_ticket) as caller:
            self.group('task_readers', '<rules><rule group="search_type" code="sthpw/task" project="admin" access="view"/></rules>')
            Login.get_by_login('operator').add_to_group('task_readers')
            result = security_rules_request('effective', dict(project='admin',login='operator'))
            report = result['metadata']['effective']
            self.assertEqual(report['login'],'operator')
            self.assertTrue(report['groups'])
            self.assertIs(Environment.get_security(),caller)
            source = Path(__file__).resolve().parents[3] / 'TH/thlib/ui/admin/security_api.py'
            function = next(node for node in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(node,ast.FunctionDef) and node.name=='security_request')
            namespace = {}
            exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
            handler = json.loads(namespace['security_request']('effective','admin','admin',login='operator'))
            self.assertEqual(handler['metadata']['effective'],report)
            from pyasm.security.effective import effective_security
            checks = effective_security('operator',targets={'search_type':[dict(label='Tasks',attributes=dict(code='sthpw/task'))]})['checks']
            self.assertEqual({row['required']:row['allowed'] for row in checks},{'view':True,'edit':False,'insert':False,'retire':False,'delete':False})

    def test_native_security_remains_available_without_optional_mcp_installation(self):
        import builtins
        original = builtins.__import__
        def missing(name, *args, **kwargs):
            if name == 'tactic_stream.admin_agent':
                raise ModuleNotFoundError('Optional MCP dependency is not installed', name='mcp')
            return original(name, *args, **kwargs)
        with self.session('admin', self.admin_ticket), patch('builtins.__import__', side_effect=missing):
            state = security_rules_request('effective', dict(project='admin',login='operator'))
            self.assertEqual(state['metadata']['agentTools'], [])
            self.assertEqual(state['metadata']['mcpTools'], [])
            self.assertEqual(state['metadata']['effective']['login'], 'operator')

    def test_project_bound_tool_policy_does_not_restrict_another_project(self):
        from tactic_stream.server.agent_security import tool_access
        with self.session('admin', self.admin_ticket):
            group = self.group('project_agent_policy', '<rules><rule group="agent_tool" key="*" access="deny"/></rules>')
            group.set_value('project_code','admin')
            group.commit()
            Login.get_by_login('admin').add_to_group('project_agent_policy')
        with self.session('admin', self.admin_ticket) as security:
            self.assertFalse(tool_access(security,'agent_context'))
        with request_context(RequestContext(self.store,'admin','sthpw')):
            security=self.api.auth.bind_security('admin',self.admin_ticket)
            self.assertTrue(tool_access(security,'agent_context'))

    def test_api_method_denies_apply_to_dispatched_reads(self):
        with self.session('admin', self.admin_ticket):
            self.group('blocked_reads', '<rules><rule group="api_method" key="query" access="deny"/></rules>')
            Login.get_by_login('operator').add_to_group('blocked_reads')
        auth = dict(ticket=self.ticket, project='admin')
        self.assertEqual(self.api.dispatch('query', (auth, 'sthpw/task')), '[]')
        original = Config.get_value
        def configured(section, name, *args, **kwargs):
            return ('true' if (section, name) == ('security', 'api_method_restricted')
                    else original(section, name, *args, **kwargs))
        with patch.object(Config, 'get_value', side_effect=configured):
            with self.assertRaises(SecurityException):
                self.api.dispatch('query', (auth, 'sthpw/task'))
            self.assertEqual(self.api.dispatch('ping', (auth,)), 'OK')


if __name__ == '__main__':
    unittest.main()
