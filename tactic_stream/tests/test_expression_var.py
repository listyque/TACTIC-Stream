"""Observed original VAR behavior, including its absence of assignment/evaluation."""
import importlib.util
import unittest
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.search.search import RequestContext, request_context
from tools.snapshot_probe import run_snapshot_case


class ExpressionVar(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='expression_contract', variable=True, project='one', name=name,
                          expression=expression, expected=expected, **options)
                     for name, expression, expected, options in [
                         ('literal', '@VAR(NAME,42)', [], {}),
                         ('string', "@VAR(NAME,'value')", [], {}),
                         ('empty_arguments', '@VAR(,)', {'error': 'SyntaxError'}, {'source_error': 'IndexError'}),
                         ('extra_arguments', '@VAR(NAME,42,ignored)', [], {}),
                         ('lowercase', '@var(NAME,42)', [], {}),
                         ('single', '@VAR(NAME,42)', None, {'single': True}),
                         ('no_assignment', "@VAR(NAME,42);'$NAME'", '$NAME', {}),
                         ('supplied_variable', "@VAR(NAME,42);'$NAME'", 'untouched', {'vars': {'NAME': 'untouched'}}),
                         ('opaque_update', '@VAR(NAME,@UPDATE(sobject,amount,99))', [], {}),
                         ('opaque_python', '@VAR(NAME,@PYTHON(missing/script))', [], {}),
                         ('opaque_query', '@VAR(NAME,@GET(sthpw/login.password))', [], {}),
                         ('opaque_invalid_method', '@VAR(NAME,@BOGUS())', [], {}),
                         ('naming', 'prefix{@VAR(NAME,42)}suffix', 'prefixsuffix', {'naming': True}),
                         ('builtin_login', '@VAR(LOGIN,someone);\'$LOGIN\'', 'admin', {}),
                         ('no_args', '@VAR()', {'error': 'SyntaxError'}, {'source_error': 'IndexError'}),
                         ('one_argument', '@VAR(NAME)', {'error': 'SyntaxError'}, {'source_error': 'IndexError'}),
                     ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['result'], case['expected'])
        self.assertEqual(result['vars'], case.get('vars', {}))
        self.assertEqual(result['amount'], 0)
        if case.get('source_error'):
            self.assertEqual(original['result'], {'error': case['source_error']})
            original['result'] = case['expected']
        self.assertEqual(result, original)


class ExpressionVarTransport(unittest.TestCase):
    def test_original_sdk_eval_script_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_var_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            key = 'contract/entity?project=one&code=A'
            with client.server:
                self.assertEqual(client.eval('@VAR(NAME,42)'), [])
                self.assertEqual(client.eval("@VAR(NAME,42);'$NAME'", vars={'NAME': 'untouched'}), 'untouched')
                self.assertEqual(client.eval('@VAR(NAME,@UPDATE(sobject,amount,99))', search_keys=[key]), [])
                body = '''from pyasm.biz import ExpressionParser
values = {'NAME': 'untouched'}
result = ExpressionParser().eval("@VAR(NAME,42);'$NAME'", vars=values)
return {'result': result, 'vars': values}'''
                self.assertEqual(client.execute_python_script('', dict(code=body))['info'],
                                 {'result': 'untouched', 'vars': {'NAME': 'untouched'}})
                with self.assertRaises(Fault):
                    client.eval('@UPDATE(sobject,amount,99);@VAR()', search_keys=[key])
                self.assertEqual(client.query('contract/entity', [('code', 'A')])[0]['amount'], 0)
        finally:
            test_transport.Transport.tearDownClass()
