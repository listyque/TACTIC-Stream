"""Directed same-type instance reads, compared with the original identity fallback."""
import xml.etree.ElementTree as ET
import ast
import unittest
from contextlib import nullcontext
from unittest.mock import patch

import test_read_parity as read_tests
from test_schema import key
from test_search_links import link_fixture
from tools.legacy_read_probe import run_link_case
from pyasm.search import Search, SObject
from pyasm.search.search import RequestContext, request_context


def self_instance_fixture(store, projects=('one', 'two'), database_connection=None):
    links = '''
        <connect from="contract/node" to="contract/node" relationship="instance" instance_type="contract/node_in_node"/>
        <connect from="contract/node_in_node" to="contract/node" relationship="code" from_col="child_code" path="parent"/>
        <connect from="contract/node_in_node" to="contract/node" relationship="code" from_col="parent_code" path="child"/>
    '''
    parameter = store.get_db_resource().get_database_impl().get_parameter()
    with nullcontext(database_connection) if database_connection is not None else store.connection(write=True) as db:
        for name in ('node', 'node_in_node'):
            kind = 'contract/' + name
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                       "VALUES ({p},{p},'contract','{{project}}',{p},'pyasm.search.SObject')".format(p=parameter), (kind, kind, name))
        rows = db.execute('SELECT id,"schema" FROM "schema" WHERE project_code IN (\'one\',\'two\')').fetchall()
        for row in rows:
            db.execute('UPDATE "schema" SET "schema"={p} WHERE id={p}'.format(p=parameter), (row['schema'].replace('</schema>', links + '</schema>'), row['id']))
    for project in projects:
        with nullcontext(database_connection) if database_connection is not None else store.connection(store.resolve('contract/node', project)[1], write=True) as db:
            primary = 'serial PRIMARY KEY' if store.get_db_resource().get_vendor() == 'PostgreSQL' else 'INTEGER PRIMARY KEY'
            db.execute(f'CREATE TABLE node (id {primary}, code text, name text, s_status text)')
            db.execute(f'CREATE TABLE node_in_node (id {primary}, code text, parent_code text, child_code text, s_status text, parent_id integer, child_id integer)')
            db.executemany('INSERT INTO node VALUES ({p},{p},{p},{p})'.format(p=parameter), [
                (1, 'A', 'Owner ' + project, None), (2, 'B', 'Child', None),
                (3, 'C', 'Archived child', 'retired'), (4, 'D', 'Leaf', None), (5, 'E', 'Other owner', None)])
            rows = [
                (1, 'N1', 'A', 'B', None), (2, 'N2', 'A', 'B', None),
                (3, 'N3', 'A', 'C', None), (4, 'N4', 'B', 'D', 'retired'),
                (5, 'N5', 'E', 'B', None), (6, 'N6', 'D', 'missing', None),
                (7, 'N7', None, 'D', None), (8, 'N8', 'A', 'A', None),
                (9, 'N9', 'missing', 'B', None), (10, 'N10', 'B', 'A', None)]
            identities = dict(A=1, B=2, C=3, D=4, E=5, missing=999)
            db.executemany('INSERT INTO node_in_node VALUES ({p},{p},{p},{p},{p},{p},{p})'.format(p=parameter),
                           [row + (identities.get(row[2]), identities.get(row[3])) for row in rows])
            if store.get_db_resource().get_vendor() == 'PostgreSQL':
                db.execute("SELECT setval(pg_get_serial_sequence('node', 'id'), 5)")
                db.execute("SELECT setval(pg_get_serial_sequence('node_in_node', 'id'), 10)")


def self_instance_cases():
    cases = []
    def add(name, operation, **values):
        cases.append(dict(name='self_instance_' + name, method='search_links',
                          search_type='contract/node', operation=operation, **values))
    for path, source, expected in ((None, 'A', ['A', 'B', 'B']),
                                   ('parent', 'A', ['A', 'B', 'B']),
                                   ('child', 'B', ['A', 'A', 'E'])):
        label = path or 'default'
        add(label + '_single', 'add_relationship_filter', key=key('node', source),
            kwargs={'path': path}, expected_codes=expected, source_codes=[source])
        add(label + '_batch', 'add_relationship_filters', keys=[key('node', source)],
            kwargs={'path': path}, expected_codes=expected, source_codes=[source])
        add(label + '_query', 'add_relationship_search_filter',
            sub={'search_type': 'contract/node', 'filters': [['code', source]]},
            kwargs={'path': path}, expected_codes=expected,
            **({'source_codes': [source]} if not path else {'source_error': 'SearchException'}))
    add('retired', 'add_relationship_filter', key=key('node', 'A'), show_retired=True,
        expected_codes=['A', 'B', 'B', 'C'], source_codes=['A'])
    add('leaf', 'add_relationship_filter', key=key('node', 'D'), expected_codes=[], source_codes=['D'])
    add('other_project', 'add_relationship_filter', key=key('node', 'A', 'two'), project='two',
        expected_codes=['A', 'B', 'B'], source_codes=['A'])
    add('children', 'children_alter_search', key=key('node', 'A'), expected_codes=['A', 'B', 'B'],
        source_error='SqlException')
    return cases


class SelfInstancesParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        link_fixture(cls.store)
        self_instance_fixture(cls.store)
        cls.cases = self_instance_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project', 'one'))):
            return run_link_case(Search, case)

    def assert_case_result(self, case, result, original):
        if 'source_error' in case:
            self.assertEqual(original['error'], case['source_error'])
        else:
            self.assertEqual([row['code'] for row in original['rows']], case['source_codes'])
        self.assertEqual([row['code'] for row in result['rows']], case['expected_codes'])
        self.assertEqual(result['count'], len(case['expected_codes']))
        if result['rows']:
            self.assertEqual({row['_related_code'] for row in result['rows']},
                             {'B'} if case.get('kwargs', {}).get('path') == 'child' else {'A'})

    def test_maps_exclusion_source_projection_and_paging(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            owners = Search.get_by_code('contract/node', ['A', 'E', 'D'])
            grouped = Search.get_related_by_sobjects(owners, 'contract/node')
            self.assertEqual({obj.get_code(): [row.get_code() for row in grouped[obj.get_search_key()]]
                              for obj in owners}, {'A': ['A', 'B', 'B'], 'E': ['B'], 'D': []})
            child = Search.get_by_code('contract/node', 'B')
            grouped = Search.get_related_by_sobjects([child], 'contract/node', path='child')
            self.assertEqual([row.get_code() for row in grouped[child.get_search_key()]], ['A', 'A', 'E'])
            selected = Search('contract/node')
            selected.add_column('name', as_column='code')
            selected.add_filters('code', ['A', 'E'])
            selected.add_order_by('id desc')
            selected.set_limit(1)
            for op, expected in (('in', ['B']), ('not in', ['A', 'A', 'B', 'B', 'D'])):
                result = Search('contract/node')
                result.add_relationship_search_filter(selected, op=op)
                self.assertEqual([row.get_code() for row in result.get_sobjects()], expected)
            empty = Search('contract/node')
            empty.add_filter('code', 'no-match')
            result = Search('contract/node')
            result.add_relationship_search_filter(empty)
            self.assertEqual(result.get_count(), 0)
            result = child.get_all_children_search('contract/node')
            result.add_order_by('id desc')
            result.set_limit(1)
            self.assertEqual(result.get_sobject_codes(), ['D'])
            self.assertEqual(result.get_sobject_ids(), [4])

    def test_aliases_copy_select_restore_and_shared_tree(self):
        from tactic_stream.server.result_items import relation_search
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            owner = Search.get_by_code('contract/node', 'A')
            result = Search('contract/node')
            result.add_relationship_filter(owner)
            result.add_relationship_filter(Search.get_by_code('contract/node', 'B'), path='child')
            self.assertEqual(result.get_sobject_codes(), ['A', 'A'])
            self.assertEqual(result.copy().get_sobject_codes(), ['A', 'A'])
            payload = result.get_select().dumps()
            restored = Search('contract/node')
            restored.get_select().loads(payload)
            self.assertEqual(restored.get_sobject_codes(), ['A', 'A'])
            tree = relation_search(owner, {'search_type': 'contract/node', 'path': ''})
            self.assertEqual(tree.get_sobject_codes(), ['A', 'B', 'B'])
            self.assertEqual(tree.get_sobject_ids(), [1, 2, 2])
            for row in tree.get_sobjects():
                self.assertEqual(row.get_search_type(), 'contract/node?project=one')
            with patch.object(SObject, 'alter_search', wraps=SObject.alter_search) as hook:
                fresh = Search('contract/node')
                fresh.add_relationship_filter(owner)
                fresh.get_sobject_codes()
                fresh.get_sobject_ids()
                self.assertEqual(hook.call_count, 1)

    def test_id_endpoints_use_schema_keys_for_both_directions_and_maps(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            schema = Search.get_by_code('contract/node', 'A').get_schema()
            for edge in schema.xml.findall('connect'):
                if edge.get('from') == 'contract/node_in_node':
                    edge.set('relationship', 'id')
                    edge.set('from_col', 'child_id' if edge.get('path') == 'parent' else 'parent_id')
                    edge.set('to_col', 'id')
            schema.relationships.clear()
            for identity, path, expected in (('A', None, ['A', 'B', 'B']), ('B', 'child', ['A', 'A', 'E'])):
                source = Search.get_by_code('contract/node', identity)
                result = Search('contract/node')
                result.add_relationship_filter(source, path=path)
                self.assertEqual(result.get_sobject_codes(), expected)
                self.assertEqual({obj.get_value('_related_code') for obj in result.get_sobjects()}, {source.get_id()})
                grouped = Search.get_related_by_sobjects([source], 'contract/node', path=path)
                self.assertEqual([obj.get_code() for obj in grouped[source.get_search_key()]], expected)
                selected = Search('contract/node')
                selected.add_column('name', as_column='id')
                selected.add_filter('code', identity)
                query = Search('contract/node')
                query.add_relationship_search_filter(selected, path=path)
                self.assertEqual(query.get_sobject_codes(), expected)

    def test_server_api_projection_and_transaction_rollback(self):
        auth = dict(ticket=self.ticket, project='one', language='python')
        owner = key('node', 'A')
        rows = self.api.dispatch('get_all_children', (auth, owner, 'contract/node'), {'columns': ['name']})
        self.assertEqual([row['name'] for row in rows], ['Owner one', 'Child', 'Child'])
        self.assertEqual(set(rows[0]), {'name', '__search_key__', '__search_type__'})
        rows = self.api.dispatch('query', (auth, 'contract/node'), {'parent_key': owner})
        self.assertEqual([row['code'] for row in ast.literal_eval(rows)], ['A', 'B', 'B'])
        script = '''from pyasm.search import Search, SearchType
owner = Search.get_by_code('contract/node', 'D')
child = Search.get_by_code('contract/node', 'E')
link = SearchType.create('contract/node_in_node')
link.add_related_sobject(owner, src_path='child')
link.add_related_sobject(child, src_path='parent')
link.commit()
assert owner.get_all_children_search('contract/node').get_sobject_codes() == ['E']
raise ValueError('self-instance rollback')
'''
        with self.assertRaisesRegex(ValueError, 'self-instance rollback'):
            self.api.dispatch('execute_python_script', (auth, '', {'code': script}))
        self.assertEqual(self.api.dispatch('get_all_children', (auth, key('node', 'D'), 'contract/node')), [])

    def test_instance_acl_nested_policy_and_invalid_endpoints(self):
        from pyasm.common import Container
        from pyasm.common.errors import SecurityException, UnsupportedContract
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            owner = Search.get_by_code('contract/node', 'A')
            with self.assertRaisesRegex(LookupError, 'path is not defined'):
                Search('contract/node').add_relationship_filter(owner, path='unknown')
            prior = Container.get('Expression:check_record_access')
            def deny_link(kind):
                if kind == 'contract/node_in_node':
                    raise SecurityException('self-instance link access denied')
            try:
                Container.put('Expression:check_record_access', deny_link)
                with self.assertRaisesRegex(SecurityException, 'link access denied'):
                    owner.get_all_children('contract/node')
            finally:
                Container.put('Expression:check_record_access', prior)
            schema = owner.get_schema()
            edge = next(node for node in schema.xml.findall('connect')
                        if node.get('from') == 'contract/node_in_node' and node.get('path') == 'child')
            schema.xml.remove(edge)
            schema.relationships.clear()
            with self.assertRaisesRegex(UnsupportedContract, 'explicit parent and child'):
                owner.get_all_children('contract/node')

    def test_ordinary_reader_cannot_read_links_through_aliases(self):
        from pyasm.security.authenticator import hash_password
        from pyasm.common.errors import SecurityException
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('self_reader','self_reader',?)", (hash_password('private-reader-password'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('self_readers','self_readers',?)",
                       ('<rules><rule group="search_type" code="contract/node_in_node" project="one" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('self_reader_group','self_reader','self_readers')")
        auth = {'ticket': self.api.get_ticket('self_reader', 'private-reader-password'), 'project': 'one'}
        try:
            self.assertEqual(self.api.dispatch('get_by_search_key', (auth, key('node', 'A')))['code'], 'A')
            for owner in ('A', 'B'):
                with self.assertRaises(SecurityException):
                    self.api.dispatch('get_all_children', (auth, key('node', owner), 'contract/node'))
            with request_context(RequestContext(self.store, 'self_reader', 'one')):
                self.api.auth.bind_security('self_reader', auth['ticket'])
                owner = Search.get_by_code('contract/node', 'B')
                for path in ('parent', 'child'):
                    with self.assertRaises(SecurityException):
                        Search('contract/node').add_relationship_filter(owner, path=path)
                    with self.assertRaises(SecurityException):
                        Search('contract/node').add_relationship_filters([owner], path=path)
                    with self.assertRaises(SecurityException):
                        Search('contract/node').add_relationship_search_filter(Search('contract/node'), path=path)
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='self_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='self_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='self_readers'")
                db.execute("DELETE FROM login WHERE code='self_reader'")


class SelfInstancesTransport(unittest.TestCase):
    def test_unchanged_sdk_children_query_script_and_rollback(self):
        import importlib.util
        import test_transport
        test_transport.Transport.setUpClass()
        client = None
        try:
            self_instance_fixture(test_transport.Transport.store)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_self_instance_client',
                                                          read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            rows = client.get_all_children(key('node', 'A'), 'contract/node', columns=['code'])
            self.assertEqual([row['code'] for row in rows], ['A', 'B', 'B'])
            self.assertTrue(all(set(row) == {'code', '__search_key__', '__search_type__'} for row in rows))
            self.assertEqual([row['code'] for row in client.query('contract/node', parent_key=key('node', 'A'))], ['A', 'B', 'B'])
            body = '''from pyasm.search import Search
child = Search.get_by_code('contract/node', 'B')
result = Search('contract/node')
result.add_relationship_filter(child, path='child')
grouped = Search.get_related_by_sobjects([child], 'contract/node', path='child')
return {'codes': result.get_sobject_codes(), 'ids': result.get_sobject_ids(),
        'map': [obj.get_code() for obj in grouped[child.get_search_key()]]}
'''
            self.assertEqual(client.execute_python_script('', {'code': body})['info'],
                             {'codes': ['A', 'A', 'E'], 'ids': [1, 1, 5], 'map': ['A', 'A', 'E']})
            fail = body.replace("return {'codes':", "child.set_value('name', 'temporary self write')\nchild.commit()\nraise ValueError('SDK self-instance rollback')\nreturn {'codes':")
            with self.assertRaisesRegex(Exception, 'SDK self-instance rollback'):
                client.execute_python_script('', {'code': fail})
            self.assertEqual(client.get_by_code('contract/node', 'B')['name'], 'Child')
            owner, member = key('node', 'D'), key('node', 'E')
            link = client.server.add_instance(client.ticket, owner, member)
            self.assertEqual((link['parent_code'], link['child_code']), ('D', 'E'))
            reverse = client.server.add_instance(client.ticket, member, owner)
            client.server.add_instance(client.ticket, owner, member)
            client.server.remove_instance(client.ticket, owner, member)
            self.assertEqual([row['code'] for row in client.server.get_instances(client.ticket, owner, 'contract/node')], ['N6'])
            self.assertEqual(client.get_by_search_key(reverse['__search_key__'])['child_code'], 'D')
            client.server.add_instance(client.ticket, owner, owner)
            client.server.remove_instance(client.ticket, owner, owner)
            self.assertEqual([row['code'] for row in client.server.get_instances(client.ticket, owner, 'contract/node')], ['N6'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
