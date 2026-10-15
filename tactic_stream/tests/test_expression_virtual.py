"""Virtual SObjects and state/date expressions against the actual original runtime."""
import ast
import datetime
import importlib.util
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.biz import ExpressionParser
from pyasm.common import Container
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tools.snapshot_probe import run_snapshot_case


class ExpressionVirtual(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='expression_contract', virtual=True, project='one', name=name, **options)
                     for name, options in [
                         ('empty_object', dict(object=True)),
                         ('dynamic_fields', dict(object=True, values={'label': 'тест', 'number': 0, 'enabled': False})),
                         ('row_pending', dict(object=True, columns=['id', 'label'], row=[7, 'before'], values={'label': 'after'})),
                         ('factory', dict(object=True, factory=True, values={'label': 'same'})),
                         ('normal_columns', dict(object=True, values={'label': 'value', 'count': 3}, serialize={'columns': ['label']})),
                         ('csharp', dict(object=True, values={'label': ''}, serialize={'language': 'c#'})),
                         ('none_allowed', dict(object=True, values={'label': None}, write_options={'allow_none': True})),
                         ('state_scalar', dict(expression='@GET(state.label)', state={'label': 'тест'})),
                         ('state_zero', dict(expression='@GET(state.count)', state={'count': 0}, single=True)),
                         ('state_false', dict(expression='@GET(state.enabled)', state={'enabled': False})),
                         ('state_none', dict(expression='@GET(state.empty)', state={'empty': None})),
                         ('state_object', dict(expression='@SOBJECT(state)', state={'label': 'value', 'empty': None})),
                         ('root_state', dict(expression='@GET(state.label)', root=True, state={'label': 'with root'})),
                         ('state_dictionary', dict(expression='@GET(state.label)', dictionary=True, state={'label': 'value'})),
                         ('date_now', dict(expression='@GET(date.now)')),
                         ('date_today', dict(expression='@GET(date.today)', root=True)),
                         ('date_object', dict(expression='@SOBJECT(date)')),
                         ('date_format', dict(expression="@FORMAT(@GET(date.now),'31/12/1999')")),
                         ('date_naming', dict(expression="day{@FORMAT(@GET(date.now),'31/12/1999')}", root=True, naming=True)),
                     ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, original)
        expected = {'state_scalar': ['тест'], 'state_zero': 0, 'state_false': [False],
                    'state_none': [''], 'root_state': ['with root'], 'state_dictionary': {},
                    'date_now': ['2026-10-09 15:24:37.123456'],
                    'date_today': ['2026-10-09 15:24:37.123456'], 'date_format': ['09/10/2026'],
                    'date_naming': 'day09/10/2026'}
        if case['name'] in expected:
            self.assertEqual(result, expected[case['name']])
        if case.get('object'):
            self.assertEqual(result['search_type'], 'sthpw/virtual')
            self.assertEqual(result['database'], 'sthpw')
            self.assertEqual(result['table'], 'unknown')
            self.assertEqual(result['column_info'], {})
            self.assertEqual(result['column_types'], {})
            self.assertEqual(set(result['normal']) - {'__search_key__', '__search_type__'}, set(result['data']))

    def test_virtual_objects_never_generate_persistent_sql(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            obj = SearchType.create('sthpw/virtual')
            obj.set_value('label', 'temporary')
            for operation in (obj.commit, obj.delete):
                for return_sql in (False, True):
                    with self.assertRaisesRegex(UnsupportedContract, 'no persistent table'):
                        operation(return_sql=return_sql)
            self.assertEqual(obj.get_value('label'), 'temporary')

    def test_state_cache_isolation_and_nested_read_policy(self):
        ticket = {'ticket': self.ticket, 'project': 'one'}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            parser = ExpressionParser()
            self.assertEqual(parser.eval('@GET(state.label)', state={'label': 'first'}), ['first'])
            self.assertEqual(parser.eval('@GET(state.label)', state={'label': 'second'}), ['second'])
            self.assertEqual(parser.eval('@GET(state.label)'), [''])
            def policy(base):
                if base == 'sthpw/virtual':
                    raise SecurityException('Denied virtual read')
            with patch('tactic_stream.server.api.check_record_access', side_effect=policy):
                with self.assertRaisesRegex(SecurityException, 'Denied virtual read'):
                    self.api.eval(ticket, '@GET(date.now)')
            self.assertIsNone(Container.get('Expression:check_record_access'))

    def test_reader_retains_virtual_column_permissions(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('virtual_reader','virtual_reader',?)",
                       (hash_password('private-virtual-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('virtual_readers','virtual_readers',?)",
                       ('<rules><rule group="search_type" default="allow"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('virtual_reader_group','virtual_reader','virtual_readers')")
        reader = {'ticket': self.api.get_ticket('virtual_reader', 'private-virtual-reader'), 'project': 'one'}
        row = ast.literal_eval(self.api.dispatch('eval', (reader, '@SOBJECT(date)')))[0]
        self.assertEqual(row['__search_type__'], 'sthpw/virtual')
        self.assertEqual(row['id'], -1)
        with self.store.connection(write=True) as db:
            db.execute("UPDATE login_group SET access_rules=? WHERE code='virtual_readers'",
                       ('<rules><rule group="search_type" default="allow"/>'
                        '<rule group="sobject_column" search_type="sthpw/virtual" column="now" access="deny"/></rules>',))
        with self.assertRaisesRegex(SecurityException, 'not editable'):
            self.api.dispatch('eval', (reader, '@GET(date.now)'))


class ExpressionVirtualTransport(unittest.TestCase):
    def test_original_sdk_date_objects_python_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_virtual_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            with client.server:
                before = datetime.datetime.now()
                rows = client.eval('@SOBJECT(date)')
                after = datetime.datetime.now()
                self.assertEqual(rows[0]['__search_type__'], 'sthpw/virtual')
                self.assertEqual(rows[0]['__search_key__'], 'sthpw/virtual?id=-1')
                for field in ('today', 'now'):
                    self.assertLessEqual(before, datetime.datetime.fromisoformat(rows[0][field]))
                    self.assertLessEqual(datetime.datetime.fromisoformat(rows[0][field]), after)
                body = '''from pyasm.search import SearchType
from pyasm.biz import ExpressionParser
obj = SearchType.create('sthpw/virtual')
obj.set_value('label', 'temporary')
return {'object': obj.get_sobject_dict(),
        'state': ExpressionParser().eval('@GET(state.label)', state={'label': 'supplied'})}'''
                info = client.execute_python_script('', dict(code=body))['info']
                self.assertEqual(info['object']['label'], 'temporary')
                self.assertEqual(info['state'], ['supplied'])
                with self.assertRaises(Fault):
                    client.execute_python_script('', dict(code='''from pyasm.search import Search, SearchType
obj = Search.get_by_code('contract/entity', 'A')
obj.set_value('amount', 99)
obj.commit()
virtual = SearchType.create('sthpw/virtual')
virtual.set_value('label', 'temporary')
virtual.commit()'''))
                self.assertEqual(client.query('contract/entity', [('code', 'A')])[0]['amount'], 0)
        finally:
            test_transport.Transport.tearDownClass()


if __name__ == '__main__':
    unittest.main()
