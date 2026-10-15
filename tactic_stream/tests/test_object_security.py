"""Real Security policies compared with unchanged code on the original kernel."""
import ast

import test_read_parity as read_tests
from pyasm.common import Environment
from pyasm.security import Security
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, Search, request_context
from tools.security_probe import run_security_case


def policy_cases():
    cases = []
    allow = '<rule group="search_type" code="contract/entity" access="allow"/>'
    def add(policy, rules='', **kwargs):
        cases.append({'method': 'security_contract', 'operation': 'policy', 'policy': policy,
                      'name': policy + '_' + str(len(cases)), 'rules': '<rules>' + rules + '</rules>', **kwargs})
    for rules in ['', allow, '<rule group="search_type" code="*" access="allow"/>',
                  '<rule group="search_type" code="contract/entity" project="one" access="allow"/>',
                  '<rule group="search_type" code="contract/entity" project="two" access="allow"/>',
                  '<rule group="search_type" code="contract/entity" access="view"/>',
                  allow + '<rule group="search_type" code="contract/entity" access="deny"/>']:
        for operation in ['rows', 'count', 'rows_count', 'count_rows', 'delete_sql']:
            add(operation, rules)
    for kwargs in [{'login': 'admin'}, {'search_options': {'sudo': True}},
                   {'search_type': 'contract/entity?project=two', 'project': 'one'},
                   {'search_options': {'project_code': 'two'}, 'project': 'one'}]:
        add('rows_count', allow, **kwargs)
    for column, value, op in [('code', 'A', None), ('code', 'B', '!='), ('name', 'NULL', '='),
                              ('name', 'NULL', '!='), ('amount', '0', '>='), ('active', 'true', None),
                              ('code', 'A|B', None), ('code', 'A|B', 'not in')]:
        rule = '<rule group="search_filter" search_type="contract/entity" column="%s" value="%s"%s/>' % (
            column, value, (' op="%s"' % op) if op else '')
        for operation in ['rows', 'count', 'rows_count', 'count_rows']:
            add(operation, allow + rule, **({'bugfix': 'pipe'} if '|' in value else {}))
    for suffix in ['project="one"', 'project="two"', 'project="*"', 'search_type="other/type"']:
        target = '' if suffix.startswith('search_type') else 'search_type="contract/entity"'
        add('rows_count', allow + '<rule group="search_filter" %s %s column="code" value="A"/>' % (target, suffix))
    or_rules = '<rule group="search_filter" search_type="contract/entity" column="code" value="A"/><rule group="search_filter" search_type="contract/entity" column="code" value="B"/>'
    add('count_rows', allow + or_rules)
    add('rows_count', allow + or_rules + '<rule group="search_filter" search_type="contract/entity" column="amount" value="0"/>')
    add('count_rows', allow + or_rules, limit=1)
    for kwargs in [{}, {'temp': True}, {'allow_none': True}, {'no_exception': True}]:
        for access in ['deny', 'view', 'edit', 'allow']:
            add('field', '<rule group="sobject_column" search_type="contract/entity" column="name" project="one" access="%s"/>' % access,
                kwargs=kwargs, value=None if kwargs.get('allow_none') else 'changed')
    for project in ['one', 'two', '*']:
        add('field', '<rule group="sobject_column" search_type="contract/entity" column="name" project="%s" access="deny"/>' % project)
    add('field', allow, statement=True)
    add('field', '<rule group="sobject_column" search_type="sthpw/project" column="title" project="*" access="deny"/>',
        search_type='sthpw/project', code='one', column='title')
    add('field', '<rule group="sobject_column" search_type="sthpw/project" column="title" project="one" access="deny"/>',
        search_type='sthpw/project', code='one', column='title')
    for stype in ['contract/entity', 'config/custom_script', 'sthpw/project']:
        for login in ['artist', 'admin']:
            add('commit_security', search_type=stype, new=True, login=login)
    for rules in ['', '<rule group="search_type" key="sthpw/login" access="deny"/>',
                  '<rule group="search_type" key="sthpw/login" access="view"/>']:
        for options in [{}, {'sudo': True}]:
            add('permission', rules, search_type='sthpw/login', search_options=options)
            add('rows', rules, search_type='sthpw/login', search_options=options)
    for kwargs in [{'log': False}, {'triggers': False}, {'log': False, 'triggers': False}]:
        add('delete_sql', allow, kwargs=kwargs)
    add('delete_sql', new=True)
    for rules in ['', allow + '<rule group="search_filter" search_type="contract/entity" column="code" value="B"/>']:
        add('cache_policy', rules, bugfix='cache_policy')
    add('cache_policy', allow)
    add('cache_policy', allow + '<rule group="search_filter" search_type="contract/entity" column="code" value="A"/>')
    return cases


class ObjectSecurityParity(read_tests.ReadParity):
    # Match the owned backend's restricted API scope. Original defaults to open;
    # that branch requires Config/Site and is not exposed by Flow yet.
    security_config = {'api_mode': 'closed'}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            db.execute("INSERT INTO login (code,login) VALUES ('artist','artist')")
            # First-run registry already includes this type; this owned fixture uses its small test table.
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/custom_script','config/custom_script','config','{project}','custom_script','pyasm.search.SObject') ON CONFLICT(search_type) DO UPDATE SET database=excluded.database,table_name=excluded.table_name,class_name=excluded.class_name")
        for project in ['one', 'two']:
            with cls.store.connection(project, write=True) as db:
                db.execute('CREATE TABLE custom_script (id INTEGER PRIMARY KEY, code varchar(256))')
        cls.cases = policy_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_security_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('bugfix') == 'pipe':
            negative = 'not in' in case['rules']
            if negative:
                self.assertEqual(original['error'], 'SqlException')
                self.assertIn("no such table: A|B", original['message'])
            else:
                if 'rows' in original:
                    self.assertEqual(original['rows'], [])
                if 'count' in original:
                    self.assertEqual(original['count'], 0)
            rows = ['', 'D', 'E', 'F', 'G'] if negative else ['A', 'B']
            expected = {'filtered': True}
            if case['policy'] != 'count':
                expected['rows'] = rows
            if case['policy'] != 'rows':
                expected['count'] = len(rows)
            self.assertEqual(result, expected)
        elif case.get('bugfix') == 'cache_policy':
            self.assertEqual(original, {'fetched': 'A', 'same': True, 'admin': False})
            self.assertEqual(result, {'fetched': None, 'same': False, 'admin': False})
        else:
            super().assert_case_result(case, result, original)

    def test_failed_expression_filters_do_not_partially_mutate_or_bypass_retry(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            security = Security()
            security._login = Search.get_by_code('sthpw/login', 'artist')
            security._is_logged_in = 1
            Environment.set_security(security)
            security.get_access_manager().add_xml_rules('<rules><rule group="search_type" code="contract/entity" access="allow"/><rule group="search_filter" search_type="contract/entity" column="name" value="good"/><rule group="search_filter" search_type="contract/entity" column="code" value="@GET(contract/entity.code)"/></rules>')
            search = Search('contract/entity')
            for operation in [search.get_count, search.get_sobjects, search.get_count, search.get_sobjects]:
                with self.assertRaisesRegex(UnsupportedContract, 'access filters'):
                    operation()
                self.assertEqual(search.filters, [])
                self.assertEqual(search.parameters, [])
                self.assertFalse(search.security_filter)
                self.assertFalse(security.is_admin())

    def test_base_policy_method_is_original_and_writes_remain_closed(self):
        original = ast.parse((read_tests.LEGACY / 'src/pyasm/search/search.py').read_text(encoding='utf-8'))
        actual = ast.parse((read_tests.ROOT / 'src/pyasm/search/search.py').read_text(encoding='utf-8'))
        def method(tree):
            return next(m for c in tree.body if isinstance(c, ast.ClassDef) and c.name == 'SObject'
                        for m in c.body if isinstance(m, ast.FunctionDef) and m.name == 'check_access')
        self.assertEqual(ast.dump(method(actual)), ast.dump(method(original)))
        with request_context(RequestContext(self.store, 'admin', 'one')):
            obj = Search.get_by_code('contract/entity', 'A')
            for operation in [obj.commit, obj.delete]:
                with self.assertRaises(UnsupportedContract):
                    operation()

    def test_delete_sql_quotes_string_identity_and_does_not_execute(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            obj = Search.get_by_code('contract/entity', 'A')
            obj.set_value('id', "1' OR 1=1 --", temp=True)
            statement = obj.delete(log=False, return_sql=True)
            with self.store.connection('one', write=True) as db:
                before = db.execute('SELECT count(*) FROM entity').fetchone()[0]
                # The constructed SQL can run as one harmless, quoted predicate.
                db.execute('SAVEPOINT quoted_identity')
                try:
                    db.execute(statement)
                    self.assertEqual(db.execute('SELECT count(*) FROM entity').fetchone()[0], before)
                finally:
                    db.execute('ROLLBACK TO quoted_identity')
                    db.execute('RELEASE quoted_identity')
