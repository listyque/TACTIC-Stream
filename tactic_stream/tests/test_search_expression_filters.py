"""Expression-valued Search filters: actual source, API policy and rollback."""
import ast
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.biz import ExpressionParser
from pyasm.common import Container
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


class SearchExpressionFilters(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        code = "@GET(contract/entity['code','A'].code)"
        name = "@GET(contract/entity['code','B'].name)"
        cls.cases = [dict(method='expression_contract', op_filters=True, project='one',
                          name=name, filters=filters, expected=expected, **options)
                     for name, filters, expected, options in [
                         ('two_get', [['code', code]], ['A'], {}),
                         ('three_get', [['code', '=', code]], ['A'], {}),
                         ('lowercase', [['code', code.replace('@GET', '@get')]], ['A'], {}),
                         ('qualified', [['entity.code', code]], ['A'], {}),
                         ('escaped_name', [['name', name]], ['B'], {}),
                         ('numeric_count', [['amount', '@COUNT(contract/entity)']], [None], {}),
                         ('numeric_three', [['amount', 'gte', '@COUNT(contract/entity)']], [None, 'E'], {}),
                         ('if', [['code', "@IF(@COUNT(contract/entity)>2,'A','B')"]], ['A'], {}),
                         ('template_two', [['code', '{'+code+'}']], ['A'], {}),
                         ('template_three', [['code', '=', '{'+code+'}']], ['A'], {}),
                         ('template_prefix', [['name', 'starts with', "{@GET(contract/entity['code','E'].name)}"]], ['E'], {}),
                         ('brace_numeric_three', [['amount', '=', '{0}']], ['A', 'D'], {}),
                         ('brace_numeric_two_literal', [['amount', '{0}']], [], {}),
                         ('literal_braces_two', [['name', '{literal}']], [], {}),
                         ('literal_braces_three', [['name', '=', '{literal}']], [], {}),
                         ('builtin_login', [['code', '$LOGIN']], ['admin'], {'search_type':'sthpw/login'}),
                         ('builtin_login_template', [['code', '{$LOGIN}']], ['admin'], {'search_type':'sthpw/login'}),
                         ('empty_get_two', [['code', "@GET(contract/entity['code','missing'].code)"]], [None], {}),
                         ('empty_get_three', [['amount', '=', "@GET(contract/entity['code','missing'].amount)"]], ['B','F'], {}),
                         ('var_noop', [['name', '@VAR(NAME,ignored)']], ['F'], {}),
                         ('opaque_var', [['name', '@VAR(NAME,@UPDATE(sobject,amount,99))']], ['F'], {}),
                         ('list_single', [['code', "@GET(contract/entity['code','in','A|B'].code)"]], ['A'], {}),
                         ('pipe_in', [['code', 'in', "@JOIN(@GET(contract/entity['code','in','A|B'].code),'|')"]], ['A','B'], {}),
                         ('pipe_not_in', [['code', 'not in', "@JOIN(@GET(contract/entity['code','in','A|B'].code),'|')"]], ['D','E','F','G'], {}),
                         ('contains', [['name', 'contains', "@GET(contract/entity['code','B'].name)"]], ['B'], {}),
                         ('groups', ['begin',['code',code],['amount','=','{9}'],'or'], ['A','E'], {}),
                         ('skip_empty_triple', [['code','=',None]], ['A','B',None,'D','E','F','G'], {}),
                         ('directives', [['code',code],['@ORDER_BY','id desc'],['@LIMIT',1]], ['A'], {}),
                         ('json_encoded', json.dumps([['amount','&gt;','{@COUNT(contract/entity)}']]), ['E'], {}),
                         ('second_brace_evaluation', [['amount','=',"@IF(1,'{0}','{9}')"]], ['A','D'], {}),
                     ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', case.get('project','one'))):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, case['expected'])
        self.assertEqual(result, original)

    def test_api_nested_policy_restored_on_success_and_failure(self):
        ticket = {'ticket':self.ticket,'project':'one'}
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            self.assertEqual(ExpressionParser().eval('@COUNT(sthpw/login)'), 1)
            read = lambda base: None
            write = lambda method: None
            Container.put('Expression:check_record_access', read)
            Container.put('Expression:check_method_access', write)
            def deny(base):
                if base == 'sthpw/login':
                    raise SecurityException('nested filter read denied')
            with patch('tactic_stream.server.api.check_record_access', side_effect=deny):
                with self.assertRaisesRegex(SecurityException, 'nested filter'):
                    self.api.query(ticket, 'contract/entity', filters=[['amount','@COUNT(sthpw/login)']])
            self.assertIs(Container.get('Expression:check_record_access'), read)
            self.assertIs(Container.get('Expression:check_method_access'), write)
            self.assertEqual(ast.literal_eval(self.api.query(ticket,'contract/entity',filters=[['code',"@GET(contract/entity['code','A'].code)"]]))[0]['code'],'A')
            self.assertIs(Container.get('Expression:check_record_access'), read)
            self.assertIs(Container.get('Expression:check_method_access'), write)

    def test_authenticated_reader_filters_and_protected_nested_reads(self):
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('filter_reader','filter_reader',?)",(hash_password('private-filter-reader'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('filter_readers','filter_readers',?)",('<rules><rule group="search_type" default="allow"/><rule group="search_type" code="contract/entity" project="two" access="deny"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('filter_reader_group','filter_reader','filter_readers')")
        ticket={'ticket':self.api.get_ticket('filter_reader','private-filter-reader'),'project':'one'}
        try:
            query=lambda expression:self.api.dispatch('query',(ticket,'contract/entity'),{'filters':[['amount',expression]]})
            self.assertEqual([obj['code'] for obj in ast.literal_eval(query('@COUNT(contract/entity)'))],[None])
            self.assertEqual([obj['code'] for obj in ast.literal_eval(query('@COUNT(contract/entity?project=two)'))],['A','D'])
            for expression in ('@GET(login.password)','@COUNT(sthpw/login)', '@UPDATE(sthpw/login,password,changed)', '@PYTHON(missing/script)'):
                with self.subTest(expression=expression), self.assertRaises(SecurityException):
                    query(expression)
            with self.assertRaises(UnsupportedContract):
                query('@COUNT(sthpw/transaction_log)')
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='filter_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='filter_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='filter_readers'")
                db.execute("DELETE FROM login WHERE code='filter_reader'")

    def test_filter_write_joins_command_and_later_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/'data')
            shutil.copytree(self.store.data_dir,store.data_dir)
            api=Api(store)
            ticket={'ticket':self.ticket,'project':'one'}
            write="@IF(@UPDATE(@SOBJECT(contract/entity['code','A']),amount,99),'0','0')"
            with self.assertRaises(UnsupportedContract):
                api.dispatch('query',(ticket,'contract/entity'),{'filters':[['amount',write],['missing',1]]})
            self.assertEqual(ast.literal_eval(api.dispatch('query',(ticket,'contract/entity'),{'filters':[['code','A']]}))[0]['amount'],0)
            api.dispatch('query',(ticket,'contract/entity'),{'filters':[['amount',write]]})
            self.assertEqual(ast.literal_eval(api.dispatch('query',(ticket,'contract/entity'),{'filters':[['code','A']]}))[0]['amount'],99)


class SearchExpressionFiltersTransport(unittest.TestCase):
    def test_original_sdk_filters_server_python_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec=importlib.util.spec_from_file_location('tactic_client_lib.source_filter_client',read_tests.LEGACY/'src/client/tactic_client_lib/tactic_server_stub.py')
            original=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client=original.TacticServerStub(setup=False,protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin','private-test-password'))
            with client.server:
                filters=[['code',"@GET(contract/entity['code','A'].code)"]]
                self.assertEqual(client.query('contract/entity',filters=filters)[0]['code'],'A')
                self.assertEqual(client.get_unique_sobject('contract/entity',{'code':filters[0][1]})['code'],'A')
                body="""from pyasm.search import Search
search=Search('contract/entity')
search.add_op_filters([['code', "@GET(contract/entity['code','A'].code)"]])
return search.get_sobject_codes()"""
                self.assertEqual(client.execute_python_script('',dict(code=body))['info'],['A'])
                with self.assertRaises(Fault):
                    client.query('contract/entity',filters=[['amount',"@IF(@UPDATE(@SOBJECT(contract/entity['code','A']),amount,99),'0','0')"],['missing',1]])
                self.assertEqual(client.query('contract/entity',filters=[['code','A']])[0]['amount'],0)
                self.assertEqual(client.query_snapshots(filters=[['code',"@GET(sthpw/snapshot['code','missing'].code)"]]),[])
        finally:
            test_transport.Transport.tearDownClass()
