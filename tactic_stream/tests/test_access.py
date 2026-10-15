"""Original rule engine parity and explicit boundaries before API writes."""
import ast
import copy
import test_read_parity as read_tests

from pyasm.common import Container, Environment
from pyasm.security import AccessManager, AccessRule, AccessRuleInGroup, AccessRuleBuilder, Sudo
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, SObject, request_context
from tools.access_probe import run_access_case


def access_cases():
    cases = []
    def add(operation, **kwargs):
        cases.append({'name': operation + '_' + str(len(cases)), 'method': 'access_contract',
                      'operation': operation, **kwargs})
    def step(method, *args, **kwargs):
        return {'method': method, 'args': list(args), 'kwargs': kwargs}
    add('builder', steps=[
        step('add_rule', 'search_type', {'code': 'contract/entity', 'project': 'one'}, 'view'),
        step('add_rule', 'builtin', 'view_side_bar', 'edit'),
        step('add_rule', 'search_type', {'project': 'one', 'code': 'contract/entity'}, 'delete'),
        step('add_rule', 'builtin', 'view_side_bar', 'deny', unique=False),
        step('update_rule', "rules/rule[@group='builtin' and @key='view_side_bar']", {'access': 'view'}),
        step('add_default_rule', 'builtin', 'deny'), step('add_default_rule', 'builtin', 'edit'),
        step('get_default', 'builtin'), step('get_default', 'missing'),
        step('remove_rule', 'builtin', 'view_side_bar'),
        step('remove_rule', 'search_type', {'code': 'contract/entity', 'project': 'one'}),
        step('remove_rule', 'builtin', 'missing')])
    xml = '<rules><rule group="builtin" key="first" access="view"/><rule group="builtin" key="first" access="deny"/><rule group="other" key="first" access="allow"/></rules>'
    for xml_object in (False, True):
        add('builder', xml=xml, xml_object=xml_object, steps=[step('add_rule', 'builtin', 'first', 'edit'),
            step('add_default_rule', 'builtin', 'deny'), step('remove_rule', 'builtin', 'first'),
            step('get_default', 'builtin')])
    add('builder', steps=[step('add_rule', 'builtin', {'key': 'Тест/slash and @project=x', 'view': 'a]b'}, 'view'),
        step('add_rule', 'builtin', {'view': 'a]b', 'key': 'Тест/slash and @project=x'}, 'edit'),
        step('remove_rule', 'builtin', {'key': 'Тест/slash and @project=x', 'view': 'a]b'})])
    add('xml', xml=xml, paths=['rules', '/rules', 'rules/rule[@group="builtin"]',
        "rules/rule[@group='builtin' and @key='first']/@access", 'rules/rule[@access]',
        'rules/*[@key]', "rules[@missing]/rule", 'rules/rule[@access=""]'])
    levels = ['false', 'true', 'deny', 'view', 'edit', 'insert', 'retire', 'delete', 'allow']
    for user in levels:
        for required in levels:
            add('manager', steps=[step('compare_access', user, required)])
    for invalid in [None, '', 'unknown', 'VIEW', 1, False]:
        add('manager', steps=[step('_get_access_enum', invalid), step('compare_access', invalid, 'view')])
    rule_sets = [
        '<rules/>',
        '<rules><rule group="builtin" default="deny"/><rule group="builtin" key="sidebar" access="view"/></rules>',
        '<rules><rule category="builtin" key="sidebar" access="edit"/><rule group="builtin" key="sidebar" access="deny"/></rules>',
        '<rules><rule group="builtin" key="sidebar" project="one" access="insert"/><rule group="builtin" key="sidebar" project="two" access="view"/></rules>',
        '<rules><rule group="search_type" code="contract/entity" project="one" access="edit"/><rule group="project" code="one" access="view"/><rule group="project" code="*" access="deny"/></rules>',
        '<rules><rule group="builtin" key="sidebar" access="allow"/><group type="builtin" default="deny"><rule key="sidebar" access="view"/><ignore/></group></rules>',
        '<rules><rule group="builtin" key="sidebar" access="custom"/><rule group="builtin" key="sidebar" access="other"/></rules>',
        '<rules><rule group="search_type" code="contract/entity" access="unknown"/><rule group="search_type" code="contract/entity" access="view"/></rules>',
        '<rules><rule group="builtin" key="sidebar" value="flag" access="view"/></rules>',
    ]
    for xml in rule_sets:
        for project in ('one', 'two'):
            add('manager', project=project, steps=[step('add_xml_rules', xml),
                step('get_access', 'builtin', {'key': 'sidebar', 'project': project}),
                step('get_access', 'builtin', {'key': 'missing', 'project': project}, default='edit'),
                step('get_access', 'builtin', ['missing', 'sidebar'], default='view'),
                step('check_access', 'builtin', 'sidebar', 'edit'),
                step('check_access', 'builtin', 'sidebar', 'view', is_match=True),
                step('check_access', 'builtin', {'key': 'sidebar', 'project': project}, 'insert', default='deny'),
                step('check_access', 'search_type', {'code': 'contract/entity', 'project': 'one'}, 'edit'),
                step('check_access', 'project', 'one', 'view'),
                step('check_access', 'builtin', 'sidebar', 'view', value='flag')])
    for method in ('add_xml_rules', 'get_by_group'):
        for project in ('', 'one', 'two'):
            xml = '<rules><rule group="builtin" key="sidebar" access="view"/></rules>'
            first = step(method, xml, project)
            if method == 'add_xml_rules':
                first['sobject'] = True
            add('manager', steps=[first, step('get_access', 'builtin', {'key': 'sidebar', 'project': 'one'}),
                                  step('get_access', 'builtin', {'key': 'sidebar', 'project': 'two'})])
    for project in ('one', 'two'):
        add('manager', project=project, bugfix='legacy_groups', steps=[step('add_xml_rules',
            '<rules><group type="builtin" default="deny"><rule key="sidebar" access="view"/></group></rules>'),
            step('get_access', 'builtin', 'sidebar'), step('check_access', 'builtin', 'sidebar', 'edit')])
    for login, groups, logged_in in [('artist', [], True), ('admin', [], True), ('artist', ['admin'], True),
                                      ('artist', ['artists'], False), (None, [], False)]:
        add('sudo', bugfix='nested_sudo', login=login, groups=groups, logged_in=logged_in, steps=[step('set_up'),
            step('check_access', 'builtin', 'missing', 'delete', default='deny'),
            step('enter'), step('enter'), {'method': 'exit', 'index': 0},
            step('check_access', 'builtin', 'missing', 'delete', default='deny'),
            {'method': 'exit', 'index': 1}, {'method': 'exit', 'index': 1}])
    for groups in ([], ['artists'], ['admin'], ['artists', 'admin'], ['missing']):
        add('lookup', groups=groups)
    add('common', data={'z': None, 'a': ['Тест'], 'middle': False})
    return cases


class AccessParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            for name, class_name in [('access_rule', 'AccessRule'), ('access_rule_in_group', 'AccessRuleInGroup')]:
                db.execute('INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES (?,?,?,?,?,?)',
                           ('sthpw/' + name, 'sthpw/' + name, 'sthpw', 'sthpw', name, 'pyasm.security.' + class_name))
            db.execute('CREATE TABLE access_rule (id integer PRIMARY KEY, code text, access_rules text, s_status text)')
            db.execute('CREATE TABLE access_rule_in_group (id integer PRIMARY KEY, code text, access_rule_code text, login_group text, s_status text)')
            db.executemany('INSERT INTO access_rule VALUES (?,?,?,?)', [(1, 'R1', '<rules/>', None), (2, 'R2', '<rules/>', None)])
            db.executemany('INSERT INTO access_rule_in_group VALUES (?,?,?,?,?)', [(1, 'C1', 'R1', 'artists', None), (2, 'C2', 'R2', 'admin', None)])
        cls.cases = access_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_access_case(case)

    def assert_case_result(self, case, result, original):
        bugfix = case.get('bugfix')
        if bugfix == 'nested_sudo':
            expected = copy.deepcopy(original)
            for index in (4, 5):  # First Sudo exited; second is still active.
                state = expected[index]
                self.assertEqual(state['count'], 1)
                if state['was_admin'] is False and case['login'] != 'admin':
                    self.assertFalse(state['admin'])
                    self.assertNotIn('admin', state['groups'])
                    state['admin'] = True
                    state['groups'].append('admin')
            self.assertEqual(result, expected)
        elif bugfix == 'legacy_groups':
            self.assertEqual([state['value'] for state in original], [None, None, True])
            self.assertTrue(all(state['groups'] == {} for state in original))
            self.assertEqual([state['value'] for state in result], [None, 'view', False])
            with self.store.connection() as db:
                codes = [row[0] for row in db.execute('SELECT code FROM project')]
            rules = {'__DEFAULT__': 'deny'}
            rules.update({f'sidebar?project={code}': ['view', {'key': 'sidebar'}] for code in codes + ['*']})
            for state in result:
                self.assertEqual(state['groups'], {'builtin': rules})
            self.assertEqual(result[0]['summary'], {})
            self.assertEqual(result[1]['summary'], {})
            self.assertEqual(len(result[2]['summary']), 1)
        else:
            super().assert_case_result(case, result, original)

    def test_source_modules_and_method_bodies_are_preserved(self):
        old = read_tests.LEGACY / 'src/pyasm/security'
        new = read_tests.ROOT / 'src/pyasm/security'
        source = (old / 'access_rule.py').read_text(encoding='utf-8')
        bug = 'if not groups:\n            []'
        self.assertEqual(source.count(bug), 1)
        self.assertEqual(source.replace(bug, 'if not groups:\n            return []'),
                         (new / 'access_rule.py').read_text(encoding='utf-8'))
        def classes(path):
            return {node.name: node for node in ast.parse(path.read_text(encoding='utf-8')).body
                    if isinstance(node, ast.ClassDef)}
        original, actual = classes(old / 'access_manager.py'), classes(new / 'access_manager.py')
        for name in ('AccessManager', 'Sudo'):
            methods = {node.name: node for node in actual[name].body if isinstance(node, ast.FunctionDef)}
            for node in original[name].body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                with self.subTest(owner=name, method=node.name):
                    current = methods[node.name]
                    self.assertEqual(ast.dump(node.args), ast.dump(current.args))
                    if (name, node.name) not in [('Sudo', '__init__'), ('Sudo', 'exit'), ('AccessManager', 'set_up'),
                                               ('AccessManager', 'alter_search'), ('AccessManager', 'add_xml_rules')]:
                        self.assertEqual(ast.dump(node), ast.dump(current))
        self.assertTrue(issubclass(AccessRule, SObject))
        original = classes(read_tests.LEGACY / 'src/pyasm/common/environment.py')['Environment']
        actual = classes(read_tests.ROOT / 'src/pyasm/common/environment.py')['Environment']
        methods = {node.name: node for node in original.body if isinstance(node, ast.FunctionDef)}
        for node in actual.body:
            # Owned paths and startup settings are documented native adaptations.
            copied = ('get_security', 'set_security', 'set_security_list', 'get_ticket',
                      'get_login', 'get_user_name', 'get_group_names', 'get_app_name',
                      'set_env_object', 'get_env_object', 'has_env_object',
                      'get_warning', 'add_warning')
            if isinstance(node, ast.FunctionDef) and node.name in copied:
                with self.subTest(owner='Environment', method=node.name):
                    self.assertEqual(ast.dump(methods[node.name]), ast.dump(node))

    def test_missing_security_and_unported_filters_fail_explicitly(self):
        from unittest.mock import patch
        with request_context(RequestContext(self.store, 'admin', 'one')):
            # Empty groups must return before querying even an unregistered table.
            with patch('pyasm.security.access_rule.Search', side_effect=AssertionError('Unexpected lookup')):
                self.assertEqual(AccessRuleInGroup.get_by_groups([]), [])
            for operation in (Environment, Sudo, AccessManager().set_up):
                with self.assertRaises(UnsupportedContract):
                    operation()
            self.assertIsNone(Container.get('Sudo::is_sudo'))
            manager = AccessManager()
            search = Search('contract/entity')
            self.assertIsNone(manager.alter_search(search))
            manager.add_xml_rules('<rules><rule group="search_filter" search_type="contract/entity" column="code" value="@GET(contract/entity.code)"/></rules>')
            with self.assertRaisesRegex(UnsupportedContract, 'access filters'):
                manager.alter_search(search)
            manager.is_admin_flag = True
            self.assertIs(manager.alter_search(search), True)
            from pyasm.common import Xml
            xml = Xml('<rules/>')
            for path in ('//rule', 'rules/rule[1]', 'rules/rule[@key="a" or @key="b"]', 'rules/rule[contains(@key,"a")]'):
                with self.assertRaises(UnsupportedContract):
                    xml.get_nodes(path)

    def test_environment_and_sudo_are_bound_to_the_request(self):
        from scripts.access_contract import ContractSecurity
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = ContractSecurity('artist', [])
            Environment.set_security(security)
            Environment.set_env_object(security)
            sudo = Sudo()
            with request_context(RequestContext(self.store, 'admin', 'two')):
                self.assertIsNone(Environment.get_security())
                self.assertFalse(Environment.has_env_object())
                self.assertFalse(Sudo.is_sudo())
                with self.assertRaisesRegex(UnsupportedContract, 'request contexts'):
                    sudo.exit()
                self.assertIsNone(Container.get('Sudo::is_sudo'))
            self.assertIs(Environment.get(), security)
            self.assertIs(Environment.get_env_object(), security)
            sudo.exit()
            sudo.exit()
            self.assertFalse(Sudo.is_sudo())
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.assertIsNone(Environment.get_security())
            self.assertFalse(Environment.has_env_object())
            self.assertEqual(Environment.get_ticket(), '')
