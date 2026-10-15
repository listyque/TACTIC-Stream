"""Search/Select interoperability against the unchanged original runtime."""
import unittest
import importlib.util

import test_read_parity as read_tests
import test_transport
from pyasm.common.errors import UnsupportedContract, SecurityException
from pyasm.search import Search, Sql, DbContainer, DbResource
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tools.snapshot_probe import run_snapshot_case


def search_select_cases():
    def step(method, *args, target='select', **kwargs):
        return dict(method=method, args=list(args), kwargs=kwargs, target=target)
    def case(name, *steps, **options):
        return dict(name=name, method='expression_contract', search_select=True, steps=list(steps), **options)
    return [
        case('direct_filter', step('add_filter', 'code', 'A')),
        case('mixed_filters', step('add_filter', 'amount', 0, op='>=', target='search'), step('add_filter', 'code', 'B')),
        case('reverse_filters', step('add_filter', 'code', 'B'), step('add_filter', 'amount', 0, op='>=', target='search')),
        case('postfix', step('add_op', 'begin'), step('add_filter', 'code', 'A', target='search'), step('add_filter', 'code', 'B'), step('add_op', 'or')),
        case('nested_postfix', step('add_op', 'begin', target='search'), step('add_op', 'begin'), step('add_filter', 'code', 'A'), step('add_filter', 'code', 'B', target='search'), step('add_op', 'or'), step('add_filter', 'amount', 0, op='>=', target='search'), step('add_op', 'and')),
        case('direct_list', step('add_filters', 'code', ['A', 'B'])),
        case('empty_list', step('add_filters', 'code', [])),
        case('quoted_value', step('add_filter', 'name', "O'Reilly")),
        case('sql_value', step('add_filter', 'name', "';DROP TABLE entity;--")),
        case('literal_all', step('add_filter', 'code', '__ALL__')),
        case('explicit_raw', step('add_filter', 'amount', 'amount + 1', quoted=False, op='<')),
        case('null_scope', step('set_null_filter', target='search'), counts=True),
        case('none', step('add_filter', 'name', None)),
        case('boolean', step('add_filter', 'active', True)),
        case('raw_where', step('add_where', 'amount >= 0'), step('add_filter', 'code', 'A', target='search')),
        case('raw_literal_marker', step('add_where', "'?' = '?'"), step('add_filter', 'code', 'A', target='search')),
        case('raw_remove', step('add_where', 'amount >= 0'), step('add_where', 'amount > 100'), step('remove_where', 'amount > 100')),
        case('paging', step('set_limit', 2), step('set_offset', 1)),
        case('paging_counts', step('set_limit', 1), step('set_offset', 100), counts=True),
        case('offset_without_limit', step('set_offset', 100)),
        case('last_limit_search', step('set_limit', 1), step('set_limit', 2, target='search')),
        case('last_limit_select', step('set_limit', 2, target='search'), step('set_limit', 1)),
        case('retired', step('set_show_retired', True, target='search')),
        case('projection', step('add_column', 'code'), step('add_filters', 'code', ['A','B'])),
        case('execute_bound', step('add_column', 'code'), step('add_filter', 'code', 'A', target='search'), execute=True),
        case('execute_inherited_scope', execute=True),
        case('count_inherited_scope', select_count=True),
        case('direct_join', step('add_join', 'child', column='id', column2='entity_id'), step('add_filter', 'code', 'CA', table='child')),
        case('mixed_join', step('add_filter', 'code', 'A', target='search'), step('add_join', 'child', column='id', column2='entity_id')),
        case('search_copy', step('add_filters', 'code', ['A','B']), copy='search', copy_filter='A'),
        case('select_copy', step('add_filters', 'code', ['A','B']), copy='select', copy_filter='A'),
    ]


class SearchSelect(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for project in ('one','two'):
            with cls.store.connection(project, write=True) as db:
                db.execute('CREATE TABLE child(id integer PRIMARY KEY, code varchar(256), entity_id integer)')
                db.execute("INSERT INTO child VALUES (1,'CA',1),(2,'CB',2)")
        cls.cases = search_select_cases()

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            return run_snapshot_case(case)

    def assert_case_result(self, case, native, original):
        if case['name'] in ('search_copy','select_copy'):
            self.assertEqual(native, {'copy':['A'], 'original':['A','B']})
            self.assertEqual(native, original)
        elif case['name'] == 'null_scope':
            self.assertEqual(native, {'search':0, 'select':0, 'rows':[]})
            self.assertEqual(original, {'search':0, 'select':8, 'rows':[]})
        elif case['name'] == 'execute_inherited_scope':
            self.assertEqual(native, [1,2,4,5,6,7,8])
            self.assertEqual(original, [1,2,3,4,5,6,7,8])
        elif case['name'] == 'count_inherited_scope':
            self.assertEqual(native, 7)
            self.assertEqual(original, 8)
        else:
            self.assertEqual(native, original)

    def test_compilation_copy_and_filter_removal_preserve_parameters(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            search = Search('contract/entity')
            search.add_filter('code', 'A')
            select = search.get_select()
            select.add_where("'?' = '?' /* ? */")
            select.add_filter('amount', 0, op='>=')
            select.remove_where(select.get_wheres()[0])
            self.assertEqual(search.parameters, ['0'])
            self.assertIn("'?' = '?' /* ? */", select.get_statement())
            self.assertEqual([obj.get_value('code') for obj in search.get_sobjects()], ['','A','D','E'])
            copy = select.copy()
            copy.add_filter('code', 'A')
            self.assertEqual(copy.execute_count(), 1)
            self.assertEqual(select.execute_count(), 4)
            self.assertIs(copy._search_owned.select, copy)
            self.assertIsNot(copy._search_owned, search)
            self.assertIs(search.filters, select.wheres)
            other = DbContainer.get(DbResource.get_default('two'))
            for operation in (lambda: select.execute(other), lambda: select.execute_count(other), lambda: other.do_query(select)):
                with self.assertRaises(UnsupportedContract): operation()
            state = select.dumps()
            select.loads(state)
            self.assertEqual(select.execute_count(), 4)
            with self.assertRaises(UnsupportedContract): select.loads('{}')

    def test_sql_parameter_tokens(self):
        for marker in ('?', '%s'):
            text = "'" + marker + "' = '" + marker + "' AND id=" + marker + ' /* ' + marker + ' */ -- ' + marker + '\n'
            parts = Sql._parameter_parts(text, marker)
            self.assertEqual(len(parts), 2)
            self.assertEqual(marker.join(parts), text)
            self.assertEqual(len(Sql._parameter_parts('$tag$'+marker+'$tag$ '+marker,marker)),2)
        self.assertEqual(Sql._bound_query("name LIKE '100%' AND id=%s", [1], '%s'), "name LIKE '100%%' AND id=%s")

    def test_reader_scope_and_copy_cannot_reopen_denied_search(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            admin_search = Search('contract/entity')
            admin_search.add_filter('code', 'A')
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('select_reader','select_reader',?)", (hash_password('private-select-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('select_readers','select_readers',?)", ('<rules><rule group="search_type" code="contract/entity" project="one" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('select_reader_group','select_reader','select_readers')")
        ticket = self.api.get_ticket('select_reader','private-select-reader')
        try:
            with request_context(RequestContext(self.store, 'select_reader', 'one')):
                self.api.auth.bind_security('select_reader', ticket)
                denied = admin_search.get_select().copy()
                self.assertTrue(denied._search_owned.null_filter)
                self.assertIn('1 = 0', denied.get_statement())
                self.assertEqual(denied._search_owned.get_sobjects(), [])
                self.assertEqual(denied._search_owned.get_count(), 0)
                self.assertEqual(denied.execute(), [])
                self.assertEqual(denied.execute_count(), 0)
                with self.assertRaises(SecurityException):
                    denied.add_where('1 = 1')
                with self.assertRaises(SecurityException):
                    denied.loads(admin_search.get_select().dumps())
                with self.assertRaises(SecurityException):
                    denied.add_join('child', column='id', column2='entity_id')
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='select_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='select_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='select_readers'")
                db.execute("DELETE FROM login WHERE code='select_reader'")


class SearchSelectTransport(unittest.TestCase):
    def test_original_sdk_server_select_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_search_select_client', read_tests.LEGACY/'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin','private-test-password'))
            body = '''from pyasm.search import Search
search = Search('contract/entity')
search.add_filter('code','A')
select = search.get_select()
select.add_column('code')
select.add_filter('amount',0,op='>=')
select.set_limit(1)
return {'rows':select.execute(),'search_count':search.get_count(),'select_count':select.execute_count(),
        'same_statement':search.get_statement()==select.get_statement()}'''
            with client.server:
                self.assertEqual(client.execute_python_script('',{'code':body})['info'],
                                 {'rows':[['A']], 'search_count':1, 'select_count':1, 'same_statement':True})
                before = client.query('contract/entity',filters=[['code','A']])[0]['name']
                failed = '''from pyasm.search import Search
obj=Search.get_by_code('contract/entity','A')
obj.set_value('name','temporary direct select write')
obj.commit()
search=Search('contract/entity')
search.get_select().set_statement('SELECT * FROM entity')
search.get_select().execute()'''
                with self.assertRaisesRegex(Exception,'Replacing Search tables'):
                    client.execute_python_script('',{'code':failed})
                self.assertEqual(client.query('contract/entity',filters=[['code','A']])[0]['name'], before)
                serialized = '''from pyasm.search import Search
search=Search('contract/entity')
search.add_filter('code','A')
select=search.get_select()
select.add_column('code',as_column='label')
select.set_limit(1)
receiver=Search('contract/entity')
receiver.get_select().loads(select.dumps())
receiver.add_filter('amount',0,op='>=')
return {'rows':receiver.get_select().execute(),'label':receiver.get_sobjects()[0].get_value('label'),
        'count':receiver.get_select().execute_count()}'''
                self.assertEqual(client.execute_python_script('',{'code':serialized})['info'],
                                 {'rows':[['A']],'label':'A','count':1})
                failed = '''import json
from pyasm.search import Search
obj=Search.get_by_code('contract/entity','A')
obj.set_value('name','temporary serialized select write')
obj.commit()
select=Search('contract/entity').get_select()
state=json.loads(select.dumps())
state['database']='two'
select.loads(json.dumps(state))'''
                with self.assertRaisesRegex(Exception,'cannot replace the Search database'):
                    client.execute_python_script('',{'code':failed})
                self.assertEqual(client.query('contract/entity',filters=[['code','A']])[0]['name'], before)
        finally:
            test_transport.Transport.tearDownClass()


if __name__ == '__main__':
    unittest.main()
