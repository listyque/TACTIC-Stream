"""Account objects, Security parity, corrected bugs and API trust boundaries."""
import ast
import copy
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import test_read_parity as read_tests

from pyasm.common import Common, Environment
from pyasm.security import Login, LoginGroup, LoginInGroup, Security, Ticket
from pyasm.common.errors import AuthenticationError, UnsupportedContract
from pyasm.search.search import RequestContext, Search, SearchType, request_context
from tools.security_probe import run_security_case


def security_cases():
    cases = []
    def add(operation, **kwargs):
        cases.append({'method': 'security_contract', 'name': operation + '_' + str(len(cases)),
                      'operation': operation, **kwargs})
    for owner, code, functions in [
        ('Login', 'artist', ['get_display_value', 'get_primary_key', 'get_foreign_key', 'get_icon_context',
                            'get_description', 'get_code', 'get_login', 'get_full_name', 'get_full_email',
                            'get_sub_group_names', 'get_sub_groups']),
        ('LoginGroup', 'artists', ['get_display_value', 'get_primary_key', 'get_foreign_key', 'is_admin',
                                 'get_description', 'get_login_group', 'get_sub_group_names', 'get_access_rules',
                                 'get_access_level', 'get_logins']),
        ('LoginInGroup', 'artist:artists', ['get_display_value']),
    ]:
        for function in functions:
            add('call', owner=owner, code=code, function=function)
    for owner, function, arguments in [
        ('Login', 'get_by_login', [['admin'], ['artist'], ['missing'], [''], ['upn@example', None, True]]),
        ('LoginGroup', 'get_by_group_name', [['artists'], ['missing']]),
        ('LoginGroup', 'get', [['one', ['artists']], ['one', []]]),
        ('LoginGroup', 'get_group_names', [['artist'], []]),
        ('LoginGroup', 'get_login_codes_in_group', [['artist']]),
        ('LoginGroup', 'get_by_project', [['one'], ['two']]),
        ('LoginGroup', 'get_project_default', [['one'], ['two']]),
        ('LoginInGroup', 'get_by_names', [['artist', 'artists'], ['missing', 'artists']]),
        ('LoginInGroup', 'get_by_login_name', [['artist'], ['missing']]),
        ('LoginInGroup', 'get_by_group_name', [['artists'], ['missing']]),
        ('Ticket', 'get_by_key', [['contract-ticket'], ['missing']]),
        ('Ticket', 'get_by_valid_key', [['contract-ticket'], ['expired-ticket'], ['missing']]),
    ]:
        for args in arguments:
            add('call', owner=owner, function=function, args=args)
    for level in range(5):
        for projects in ([], ['one'], ['one', 'two']):
            for add_root in (False, True):
                add('call', owner='LoginGroup', function='get_default_access_rule', args=[level, projects, add_root])
    for value in ['Abcd123!', 'weak', 'NoNumber!', 'NOLOWER1!', 'noupper1!', 'GoodPass9&', 'Тест1234!', '']:
        add('call', owner='Login', function='validate_password', args=[value])
    for data in [{'login': 'name'}, {'code': 'code-name'}, {'login': 'name', 'code': 'other'}]:
        add('defaults', search_type='sthpw/login', data=data)
    for data in [{'login_group': 'team'}, {'code': 'team'}, {'login_group': 'team', 'code': 'other'}]:
        add('defaults', search_type='sthpw/login_group', data=data)
    for login in ['artist', 'upn-user', 'admin', 'lead', 'cycle-user']:
        add('security', login=login, reset=True, clear_ticket=True, bugfix='security_state')
    add('cache', login='artist', first={'namespace': 'one'}, second={'namespace': 'two'}, bugfix='namespace_cache')
    add('cache', login='upn@example', first={'use_upn': True}, second={'use_upn': False}, bugfix='namespace_cache')
    add('cache', login='missing', first={}, second={})
    return cases


class SecurityParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            db.executemany('INSERT INTO login (code,login,upn,namespace,first_name,last_name,display_name,email) VALUES (?,?,?,?,?,?,?,?)', [
                ('artist', 'artist', 'artist@example', 'one', 'Ann', 'Artist', 'Ann Artist', 'ann@example'),
                ('upn-user', 'upn-user', 'upn@example', 'two', 'UPN', 'User', 'UPN User', None),
                ('lead', 'lead', 'lead@example', 'one', 'Lead', 'User', 'Lead User', None),
                ('cycle-user', 'cycle-user', None, 'one', None, None, 'Cycle', None),
            ])
            db.executemany('INSERT INTO login_group (code,login_group,name,namespace,sub_groups,access_rules,access_level,project_code,is_default,start_link) VALUES (?,?,?,?,?,?,?,?,?,?)', [
                ('artists', 'artists', 'Artists', 'one', '', '<rules><rule group="builtin" key="sidebar" access="view"/></rules>', 'low', 'one', 1, '/work'),
                ('production', 'production', 'Production', 'one', 'artists|admin', '<rules/>', 'medium', 'one', 0, None),
                ('cycle-a', 'cycle-a', 'Cycle A', 'two', 'cycle-b', '<rules/>', 'low', 'two', 0, None),
                ('cycle-b', 'cycle-b', 'Cycle B', 'two', 'cycle-a', '<rules/>', 'high', 'two', 0, None),
            ])
            db.executemany('INSERT INTO login_in_group (code,login,login_group) VALUES (?,?,?)', [
                ('artist:artists', 'artist', 'artists'), ('lead:production', 'lead', 'production'),
                ('cycle:cycle-a', 'cycle-user', 'cycle-a'),
            ])
            db.executemany('INSERT INTO ticket (code,ticket,login,expiry) VALUES (?,?,?,?)', [
                ('contract-ticket', 'contract-ticket', 'artist', '2099-01-01 00:00:00'),
                ('expired-ticket', 'expired-ticket', 'artist', '2000-01-01 00:00:00'),
            ])
        cls.cases = security_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_security_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('bugfix') == 'namespace_cache':
            self.assertTrue(original['same'])
            expected = copy.deepcopy(original)
            expected['second'], expected['same'] = None, False
            self.assertEqual(result, expected)
        elif case.get('bugfix') == 'security_state':
            expected = copy.deepcopy(original)
            self.assertTrue(original['admin'])  # Original sign_out leaked the earlier admin flag.
            expected.update(default_access='deny', ticket_after_clear='', admin_after_signout=False)
            if case['login'] != 'admin':
                expected['admin'] = False
            if case['login'] == 'admin':
                expected['admin_after_reset'] = True
            if case['login'] == 'lead':
                self.assertNotIn('artists', original['names'])
                expected.update(names=['admin', 'artists', 'default', 'production'],
                    groups=['production', 'admin', 'artists', 'default'], admin=True,
                    start='/work', admin_after_reset=True,
                    checks={'artists': True, 'production': True, 'admin': True, 'missing': False})
            if case['login'] == 'cycle-user':
                self.assertNotIn('cycle-b', original['names'])
                expected.update(names=['cycle-a', 'cycle-b', 'default'], groups=['cycle-a', 'cycle-b', 'default'])
            self.assertEqual(result, expected)
        else:
            super().assert_case_result(case, result, original)

    def test_public_signatures_and_unchanged_method_bodies(self):
        source = ast.parse((read_tests.LEGACY / 'src/pyasm/security/security.py').read_text(encoding='utf-8'))
        actual = ast.parse((read_tests.ROOT / 'src/pyasm/security/security.py').read_text(encoding='utf-8'))
        old = {c.name: c for c in source.body if isinstance(c, ast.ClassDef)}
        new = {c.name: c for c in actual.body if isinstance(c, ast.ClassDef)}
        # The hasher was deliberately renamed when Drupal support was excluded;
        # verify the unchanged algorithm independently of that import spelling.
        for node in ast.walk(old['Login']):
            if isinstance(node, ast.Name) and node.id == 'DrupalPasswordHasher':
                node.id = 'TacticPasswordHasher'
        unchanged = {'Login': ['get_defaults', 'get_full_name', 'get_full_email', 'encrypt_password', 'get_security_level_group'],
                     'LoginGroup': ['get_defaults', 'get_default_access_rule', 'get_by_project', 'get_access_level'],
                     'LoginInGroup': ['get_by_names', 'get_by_login_name', 'get_by_group_name'],
                     'Ticket': ['get_key', 'get_by_key'], 'Security': ['check_access', 'is_in_group', 'setup_access_manager']}
        for name, cls in new.items():
            if name not in old:
                continue
            methods = {m.name: m for m in old[name].body if isinstance(m, ast.FunctionDef)}
            for method in cls.body:
                if not isinstance(method, ast.FunctionDef):
                    continue
                if name == 'Security' and method.name == '__init__':
                    continue  # The licensing argument is deliberately excluded.
                if name == 'Site' and method.name in ('get_id', 'get_search_key', 'get_data'):
                    # Default Site now supplies the missing pseudo-SObject identity contract.
                    continue
                with self.subTest(owner=name, method=method.name):
                    self.assertEqual(ast.dump(method.args), ast.dump(methods[method.name].args))
                    if method.name in unchanged.get(name, []):
                        self.assertEqual(ast.dump(method), ast.dump(methods[method.name]))

    def test_real_security_bound_by_api_and_isolated_after_dispatch(self):
        from tactic_stream.server.api import Api
        api = Api(self.store)
        token = api.get_ticket('admin', 'private-test-password')
        def ping(ticket):
            return {
                'user': Environment.get_user_name(), 'class': type(Environment.get_login()).__name__,
                'ticket': Environment.get_ticket(), 'admin': Environment.get_security().is_admin()}
        with patch.object(api, 'ping', new=ping):
            value = api.dispatch('ping', ({'ticket': token, 'project': 'one'},))
        self.assertEqual(value, {'user': 'admin', 'class': 'Login', 'ticket': token, 'admin': True})
        with request_context(RequestContext(self.store, 'admin', 'two')):
            self.assertIsNone(Environment.get_security())

    def test_filters_retry_and_closed_branches(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = Security()
            Environment.set_security(security)
            security.get_access_manager().add_xml_rules('<rules><rule group="search_type" code="contract/entity" access="allow"/><rule group="search_filter" search_type="contract/entity" column="code" value="@GET(contract/entity.code)"/></rules>')
            search = Search('contract/entity')
            for _ in range(2):
                with self.assertRaises(UnsupportedContract):
                    search.get_sobjects()
                self.assertFalse(search.security_filter)
            for operation in (security.login_as_guest,):
                with self.assertRaises(UnsupportedContract):
                    operation()

    def test_random_alphabet_and_disabled_accounts(self):
        with patch('pyasm.common.common.secrets.choice', side_effect=lambda values: values[-1]):
            self.assertEqual(Common.generate_alphanum_key(8, 'alpha', 4), 'ZZZZ-ZZZZ')
            self.assertEqual(Common.generate_alphanum_key(4, 'numeric'), '9999')
            self.assertEqual(Common.generate_alphanum_key(4, 'hex'), 'FFFF')
        from pyasm.security.authenticator import Authenticator
        from pyasm.search.storage import Store
        from pyasm.security.authenticator import hash_password
        store = Store(self.data / 'disabled')
        store.initialize(hash_password('private-test-password'))
        auth = Authenticator(store)
        token = auth.get_ticket('admin', 'private-test-password')
        with store.connection(write=True) as db:
            db.execute("UPDATE login SET s_status='retired' WHERE login='admin'")
        for operation in (lambda: auth.validate(token), lambda: auth.get_ticket('admin', 'private-test-password')):
            with self.assertRaises(AuthenticationError):
                operation()

    def test_nested_defaults_and_quoted_membership_names(self):
        from pyasm.search.storage import Store
        from pyasm.security.authenticator import hash_password
        store = Store(self.data / 'quoted')
        store.initialize(hash_password('private-test-password'))
        with store.connection(write=True) as db:
            db.execute("INSERT INTO login (code,login) VALUES (?,?)", ("quote'user", "quote'user"))
            db.execute('INSERT INTO login_group (code,login_group,sub_groups,access_level,access_rules) VALUES (?,?,?,?,?)',
                       ("quote'group", "quote'group", '', 'high', '<rules/>'))
            db.execute('INSERT INTO login_in_group (code,login,login_group) VALUES (?,?,?)',
                       ('quoted', "quote'user", "quote'group"))
        with request_context(RequestContext(store, 'admin')):
            security = Security()
            Environment.set_security(security)
            security._login = Search.get_by_code('sthpw/login', "quote'user")
            security._do_login()
            self.assertEqual(security.get_group_names(), ['default', "quote'group"])
            self.assertEqual([obj.get_login() for obj in LoginGroup.get_by_group_name("quote'group").get_logins()], ["quote'user"])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = Security()
            Environment.set_security(security)
            security._login = Search.get_by_code('sthpw/login', 'cycle-user')
            security._do_login()
            default = next(group for group in security.get_groups() if group.get_login_group() == 'default')
            self.assertEqual(default.get_access_rules(), LoginGroup.get_default_access_rule(LoginGroup.HI, ['two']))


class SecurityUpgrade(unittest.TestCase):
    def test_original_migrations_are_atomic_repeatable_and_preserve_accounts(self):
        from pyasm.search.storage import Store, identifier
        from pyasm.security.authenticator import hash_password
        manifest = json.loads((read_tests.ROOT / 'src/tactic_stream/compatibility/security_upgrade.json').read_text())
        source = ast.parse((read_tests.LEGACY / 'src/pyasm/search/upgrade/project/sthpw_upgrade.py').read_text(encoding='utf-8'))
        methods = {node.name: node for node in ast.walk(source) if isinstance(node, ast.FunctionDef)}
        for entry in manifest['columns']:
            strings = [node.value.strip() for node in ast.walk(methods[entry['source_method']])
                       if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            self.assertIn(entry['sql'], strings)
        with tempfile.TemporaryDirectory(prefix='tactic-stream-security-upgrade-') as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-test-password'))
            with store.connection(write=True) as db:
                password = db.execute("SELECT password FROM login WHERE login='admin'").fetchone()[0]
                for entry in manifest['columns']:
                    db.execute('ALTER TABLE ' + identifier(entry['table']) + ' DROP COLUMN ' + identifier(entry['column']))
                db.execute("UPDATE search_object SET class_name='broken' WHERE search_type='sthpw/schema'")
            with self.assertRaises(ValueError):
                store.upgrade()
            self.assertNotIn('upn', store.columns('sthpw', 'login'))
            with store.connection(write=True) as db:
                db.execute("UPDATE search_object SET class_name='pyasm.biz.Schema' WHERE search_type='sthpw/schema'")
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with store.connection() as db:
                account = db.execute("SELECT password,upn FROM login WHERE login='admin'").fetchone()
                self.assertEqual(tuple(account), (password, 'admin'))
                self.assertEqual(db.execute('SELECT count(*) FROM login').fetchone()[0], 1)
