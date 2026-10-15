"""Connect expressions and native connection helpers against original TACTIC."""
import ast
import importlib.util
import sys
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.biz import ExpressionParser, SObjectConnection
from pyasm.command import Command
from pyasm.common import Container
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from pyasm.security.access_manager import Sudo
from tools.snapshot_probe import run_snapshot_case


FIRST = 'contract/entity?project=one&code=A'
SECOND = 'contract/entity?project=one&code=B'
OTHER = 'contract/entity?project=two&code=B'


class ExpressionConnections(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(read_tests.ROOT / 'tests/scripts'))
        import expression_contract
        with cls.store.connection(write=True) as db:
            expression_contract.install_connection_fixture(db)
        cls.cases = [dict(method='expression_contract', connections=True, project='one', name=name, roots=[FIRST], **options)
                     for name, options in [
                         ('get_publish', dict(expression="@GET(connect['@CONTEXT','publish'].code)")),
                         ('get_filter', dict(expression="@GET(connect['@CONTEXT','publish']['name',\"O'Reilly\"].code)")),
                         ('get_excluded', dict(expression="@GET(connect['@CONTEXT','publish']['code','A'].code)")),
                         ('get_context_regex', dict(expression="@GET(connect['@CONTEXT','EQ','^pub'].code)")),
                         ('get_missing_context', dict(expression="@GET(connect['@CONTEXT','none'].code)")),
                         ('count', dict(expression="@COUNT(connect['@CONTEXT','publish'])")),
                         ('objects', dict(expression="@SOBJECT(connect['@CONTEXT','publish'])")),
                         ('single', dict(expression="@GET(connect['@CONTEXT','publish'].code)", single=True)),
                         ('mixed_objects', dict(expression="@SOBJECT(connect['@CONTEXT','mixed'])")),
                         ('cross_project', dict(expression="@SOBJECT(connect['@CONTEXT','cross'])")),
                         ('dangling', dict(expression="@SOBJECT(connect['@CONTEXT','dangling'])")),
                         ('retired_object', dict(expression="@SOBJECT(connect['@CONTEXT','retired_object'])")),
                         ('retired_link', dict(expression="@SOBJECT(connect['@CONTEXT','retired_link'])", show_retired=True)),
                         ('search', dict(expression="@SEARCH(connect['@CONTEXT','publish'])")),
                         ('search_mixed', dict(expression="@SEARCH(connect['@CONTEXT','mixed'])")),
                         ('chain', dict(expression="@GET(contract/entity['code','A'].connect['@CONTEXT','publish'].code)")),
                         ('chain_search', dict(expression="@SEARCH(contract/entity['code','A'].connect['@CONTEXT','publish'])")),
                         ('naming', dict(expression="name{@GET(connect['@CONTEXT','publish'].code)}", naming=True)),
                         ('core_forward', dict(core=True, context='publish')),
                         ('core_reverse', dict(core=True, context='publish', direction='src')),
                         ('core_filters', dict(core=True, context='publish', filters=[['code', 'B']])),
                         ('core_search', dict(core=True, context='publish', return_search=True)),
                     ]]
        cls.cases += [dict(method='expression_contract', connections=True, project='one', name=name, roots=roots, expression=expression)
                      for name, roots, expression in [
                          ('no_roots', [], '@GET(connect.code)'),
                          ('mixed_roots', [FIRST, OTHER], "@SOBJECT(connect['@CONTEXT','publish'])"),
                          ('chain_no_roots', [], "@GET(contract/entity['code','A'].connect['@CONTEXT','publish'].code)"),
                          ('chain_search_no_roots', [], "@SEARCH(contract/entity['code','A'].connect['@CONTEXT','publish'])"),
                      ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        expected = {'get_publish': ['B'], 'get_filter': ['B'], 'get_excluded': [],
                    'get_missing_context': [], 'count': 1, 'single': 'B', 'naming': 'nameB',
                    'no_roots': [], 'dangling': [], 'retired_object': [], 'retired_link': [],
                    'chain_no_roots': ['B'], 'cross_project': [{'type': 'contract/entity?project=two', 'code': 'B'}]}
        if case['name'] in expected:
            self.assertEqual(result, expected[case['name']])
        if case['name'] == 'mixed_objects':
            self.assertEqual(result, [{'type': 'contract/entity?project=one', 'code': 'B'},
                                      {'type': 'sthpw/project', 'code': 'admin'}])
            self.assertEqual(original, [{'type': 'contract/entity?project=one', 'code': 'A'},
                                       {'type': 'contract/entity?project=one', 'code': 'B'}])
        elif case['name'] == 'mixed_roots':
            self.assertEqual(result, [{'type': 'contract/entity?project=two', 'code': 'A'},
                                      {'type': 'contract/entity?project=one', 'code': 'B'}])
            self.assertEqual(original, [{'type': 'contract/entity?project=two', 'code': 'A'},
                                       {'type': 'contract/entity?project=two', 'code': 'B'}])
        elif case['name'] == 'search_mixed':
            self.assertEqual(result, {'error': 'UnsupportedContract'})
            self.assertEqual(original, {'search_type': 'contract/entity?project=one',
                                       'records': [{'type': 'contract/entity?project=one', 'code': 'A'},
                                                   {'type': 'contract/entity?project=one', 'code': 'B'}]})
        elif case['name'] == 'get_context_regex':
            # Original SQLite treats EQ as LIKE; native implements the actual regex contract.
            self.assertEqual(result, ['B'])
            self.assertEqual(original, [])
        else:
            self.assertEqual(result, original)

    def test_connect_cache_changes_and_rolls_back_with_command(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            first, second = Search.get_by_search_key(FIRST), Search.get_by_search_key(SECOND)
            parser = ExpressionParser()
            expression = "@GET(contract/entity['code','A'].connect['@CONTEXT','new'].code)"
            self.assertEqual(parser.eval(expression), [])
            def execute():
                link = SObjectConnection.create(first, second, context='new', direction='dst')
                self.assertEqual(parser.eval(expression), ['B'])
                self.assertIsNone(SObjectConnection.create(first, second, context='new', direction='dst'))
                self.assertEqual(len(SObjectConnection.get_connections([first], context='new')), 1)
                link.delete()
                self.assertEqual(parser.eval(expression), [])
                SObjectConnection.create(first, second, context='new')
                self.assertEqual(parser.eval(expression), ['B'])
                raise ValueError('connection rollback')
            command = Command()
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'connection rollback'):
                Command.execute_cmd(command)
            self.assertEqual(parser.eval(expression), [])
            self.assertEqual(SObjectConnection.get_connections([first], context='new'), [])

    def test_core_connection_cache_rechecks_nested_policy(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            first = Search.get_by_search_key(FIRST)
            self.assertEqual([obj.get_code() for obj in SObjectConnection.get_connected_sobjects(first, direction='src', context='publish')[1]], ['B'])
            def policy(base):
                if base == 'contract/entity':
                    raise SecurityException('Denied cached target')
            previous = Container.get('Expression:check_record_access')
            Container.put('Expression:check_record_access', policy)
            try:
                with self.assertRaisesRegex(SecurityException, 'Denied cached target'):
                    SObjectConnection.get_connected_sobjects(first, direction='src', context='publish')
            finally:
                Container.put('Expression:check_record_access', previous)

    def test_nested_read_policy_restored(self):
        ticket = {'ticket': self.ticket, 'project': 'one'}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            for denied in ('sthpw/connection', 'contract/entity'):
                def policy(base):
                    if base == denied:
                        raise SecurityException('Denied connected read')
                with patch('tactic_stream.server.api.check_record_access', side_effect=policy):
                    with self.assertRaisesRegex(SecurityException, 'Denied connected read'):
                        self.api.eval(ticket, "@GET(connect['@CONTEXT','publish'].code)", [FIRST])
                self.assertIsNone(Container.get('Expression:check_record_access'))

    def test_reader_and_sudo_cache_do_not_expose_foreign_project(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('connect_reader','connect_reader',?)",
                       (hash_password('private-connect-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('connect_readers','connect_readers',?)",
                       ('<rules><rule group="search_type" default="allow"/>'
                        '<rule group="search_type" code="contract/entity" project="two" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('connect_reader_group','connect_reader','connect_readers')")
        reader = {'ticket': self.api.get_ticket('connect_reader', 'private-connect-reader'), 'project': 'one'}
        self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (reader, "@GET(connect['@CONTEXT','publish'].code)", [FIRST]))), ['B'])
        self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (reader, "@GET(connect['@CONTEXT','cross'].code)", [FIRST]))), [])
        with request_context(RequestContext(self.store, 'connect_reader', 'one')):
            self.api.auth.bind_security('connect_reader', reader['ticket'])
            first = Search.get_by_search_key(FIRST)
            sudo = Sudo()
            try:
                self.assertEqual([obj.get_search_type() for obj in SObjectConnection.get_connected_sobjects(first, direction='src', context='cross')[1]],
                                 ['contract/entity?project=two'])
            finally:
                sudo.exit()
            self.assertEqual(SObjectConnection.get_connected_sobjects(first, direction='src', context='cross')[1], [])


class ExpressionConnectionsTransport(unittest.TestCase):
    def test_original_sdk_connect_script_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            import expression_contract
            with test_transport.Transport.store.connection(write=True) as db:
                expression_contract.install_connection_fixture(db)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_connect_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            with client.server:
                self.assertEqual(client.eval("@GET(connect['@CONTEXT','publish'].code)", search_keys=[FIRST]), ['B'])
                rows = client.eval("@SOBJECT(connect['@CONTEXT','cross'])", search_keys=[FIRST])
                self.assertEqual(rows[0]['__search_type__'], 'contract/entity?project=two')
                body = '''from pyasm.search import Search
from pyasm.biz import ExpressionParser, SObjectConnection
first = Search.get_by_code('contract/entity', 'A')
second = Search.get_by_code('contract/entity', 'B')
SObjectConnection.create(first, second, context='sdk', direction='dst')
return ExpressionParser().eval("@GET(connect['@CONTEXT','sdk'].code)", first)'''
                self.assertEqual(client.execute_python_script('', dict(code=body))['info'], ['B'])
                with self.assertRaises(Fault):
                    client.execute_python_script('', dict(code=body.replace("context='sdk'", "context='sdk_rollback'").replace(
                        'return ExpressionParser()', "raise ValueError('sdk connection rollback')\nreturn ExpressionParser()")))
                self.assertEqual(client.eval("@GET(connect['@CONTEXT','sdk_rollback'].code)", search_keys=[FIRST]), [])
        finally:
            test_transport.Transport.tearDownClass()


if __name__ == '__main__':
    unittest.main()
