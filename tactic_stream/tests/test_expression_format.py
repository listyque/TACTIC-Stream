"""Run the same source formatting calls in the original and native kernels."""
import ast
import importlib.util
import locale
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as read_tests
import test_transport
from pyasm.common.errors import SecurityException
from pyasm.search.search import RequestContext, request_context
from tools.snapshot_probe import run_snapshot_case


KEY = 'contract/entity?project=one&code=A'


class ExpressionFormat(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection('one', write=True) as db:
            db.execute("INSERT INTO spt_prod_setting(code,key,value) VALUES ('FORMAT_DATE','DATE','%d.%m.%Y')")
            db.execute("INSERT INTO spt_prod_setting(code,key,value) VALUES ('FORMAT_DATETIME','DATETIME','%d.%m.%Y %H:%M')")
        formats = ['-1234', '-1,234', '-1234.12', '-1,234.12', '-13%', '-12.95%',
                   '-$1,234', '-$1,234.00', '-$1,234.--', '-$1,234.00 CAD', '($1,234.00)',
                   '-1.23E+03', '-1.234E+03', 'KB', 'unrecognized']
        dates = ['31/12/99', 'December 31, 1999', '31/12/1999', 'Dec 31, 99', 'Dec 31, 1999',
                 '31 Dec, 1999', '31 December 1999', 'Fri, Dec 31, 99', 'Fri 31/Dec 99',
                 'Fri, December 31, 1999', 'Friday, December 31, 1999', '12-31', '99-12-31',
                 '1999-12-31', '12-31-1999', '12/99', '31/Dec', 'December', '52',
                 '13:37', '13:37:46', '01:37 PM', '01:37:46 PM', '31/12/99 13:37',
                 '99/12/31 13:37', '1999/12/31 13:37', 'YYYY/MM/DD HH:MM AM',
                 '31/12/99 13:37:46', 'DATE', 'DATETIME', 'TIME_AGO']
        cls.cases = [dict(method='expression_contract', format_value=True, project='one',
                          name='core_' + format, call='core', value=-1234.56, format=format)
                     for format in formats]
        cls.cases += [dict(method='expression_contract', format_value=True, project='one',
                           name='date_' + format, call='core', value='2020-10-07 13:37:46', format=format, date_locale=True)
                      for format in dates]
        for case in cls.cases:
            if case['name'] in ('core_-1,234', 'core_-1,234.12'):
                case.update(source_fix='AttributeError', expected='-1,235' if case['format'] == '-1,234' else '-1,234.56')
        cls.cases += [dict(method='expression_contract', format_value=True, project='one',
                           name='timecode_' + format, call='core', value=1859, format=format, format_option=30)
                      for format in ('MM:SS.FF', 'MM:SS:FF', 'MM:SS', 'HH:MM:SS.FF', 'HH:MM:SS:FF', 'HH:MM:SS')]
        cls.cases += [dict(method='expression_contract', format_value=True, project='one',
                           name=name, call='core', value=value, format=format, **options)
                      for name, value, format, options in [
                          ('empty', '', '-1234.12', {}), ('zero', 0, '-13%', {}),
                          ('none', None, '-1234', {}), ('string_false', 'false', 'True|False', {'source_value': 'True', 'expected': 'False'}),
                          ('false', False, 'true|false', {'source_value': 'true', 'expected': 'false'}),
                          ('dict', {'b': 2, 'a': 1}, 'DICT', {'source_fix': 'SyntaxError', 'expected': 'a : 1<br />b : 2'}),
                          ('days', {'days': 2, 'seconds': 3}, 'DAYS', {'value_type': 'timedelta'}),
                          ('seconds', {'days': 2, 'seconds': 3}, 'SECONDS', {'value_type': 'timedelta'}),
                          ('datetime', [2026, 10, 7, 13, 37, 46], 'DATE', {'value_type': 'datetime'}),
                          ('root', 'folder/scene.ma', 'ROOT', {}), ('ext', 'folder/scene.ma', 'EXT', {}),
                          ('basename', 'folder/scene.ma', 'BASENAME', {}), ('dirname', 'folder/scene.ma', 'DIRNAME', {}),
                      ]]
        cls.cases += [dict(method='expression_contract', format_value=True, project='one',
                           name=name, call=call, expression=expression, roots=roots, **options)
                      for name, call, expression, roots, options in [
                          ('number', 'expression', "@FORMAT(12.345,'-1234.12')", [], {}),
                          ('array', 'expression', "@FORMAT(@GET(contract/entity.amount),'-1234.12')", [], {}),
                          ('single', 'expression', "@FORMAT(12.345,'-1234.12')", [], {'single': True}),
                          ('empty_query', 'expression', "@FORMAT(@GET(contract/entity['code','missing'].amount),'-1234.12')", [], {}),
                          ('root_value', 'expression', "@FORMAT(@GET(.amount),'-13%')", [KEY], {}),
                          ('currency', 'expression', "@FORMAT(-1234.56,'-$1,234.00')", [], {}),
                          ('fps', 'expression', "@FORMAT(1859,'HH:MM:SS:FF',30)", [], {}),
                          ('format_variable', 'expression', '@FORMAT($NUMBER,$PATTERN)', [], {'vars': {'NUMBER': 12.345, 'PATTERN': '-1234.12'}}),
                          ('naming_method', 'naming', "{@FORMAT(@GET(sobject.amount),'-1234.12')}", [KEY], {}),
                          ('naming_suffix', 'naming', "{@GET(sobject.amount),format='-1234.12'}", [KEY], {}),
                          ('no_args', 'expression', '@FORMAT()', [], {'source_fix': 'IndexError', 'expected': {'error': 'SyntaxError'}}),
                          ('no_format', 'expression', '@FORMAT(12)', [], {'source_fix': 'IndexError', 'expected': {'error': 'SyntaxError'}}),
                      ]]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if 'source_value' in case:
            self.assertEqual(original, case['source_value'])
            self.assertEqual(result, case['expected'])
        elif case.get('source_fix'):
            self.assertEqual(original, {'error': case['source_fix']})
            self.assertEqual(result, case['expected'])
        else:
            self.assertEqual(result, original)
        if case['name'] == 'number':
            self.assertEqual(result, ['12.35'])
        if case['name'] == 'currency':
            self.assertEqual(result, ['-$1,234.56'])
        if case['name'] == 'date_DATE':
            self.assertEqual(result, '07.10.2020')

    def test_no_locale_mutation_and_nested_read_policy(self):
        before = locale.setlocale(locale.LC_ALL)
        with patch('locale.setlocale', side_effect=AssertionError('Worker changed locale')):
            self.assertEqual(self.new_result(next(case for case in self.cases if case['name'] == 'currency')), ['-$1,234.56'])
        self.assertEqual(locale.setlocale(locale.LC_ALL), before)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            with patch('tactic_stream.server.api.check_record_access', side_effect=SecurityException('Denied nested read')):
                with self.assertRaisesRegex(SecurityException, 'Denied nested read'):
                    self.api.eval({'project': 'one'}, "@FORMAT(@GET(sthpw/file.st_size),'-1234')")


class ExpressionFormatTransport(unittest.TestCase):
    def test_original_sdk_eval_python_and_rollback(self):
        test_transport.Transport.setUpClass()
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_expression_format_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            with client.server:
                self.assertEqual(client.eval("@FORMAT(12.345,'-1234.12')"), ['12.35'])
                self.assertEqual(client.eval("{@GET(.amount),format='-1234.12'}", search_keys=[KEY]), 0.0)
                body = '''from pyasm.common import FormatValue
from pyasm.biz import ExpressionParser
return [FormatValue().get_format_value(1859,'HH:MM:SS:FF',30), ExpressionParser().eval("@FORMAT(12.345,'-1234.12')")]'''
                self.assertEqual(client.execute_python_script('', dict(code=body))['info'], ['00:01:01:29', ['12.35']])
                before = client.query('contract/entity', [('code', 'A')])[0]['amount']
                with self.assertRaises(Fault):
                    client.eval('@UPDATE(sobject,amount,42);@FORMAT()', search_keys=[KEY])
                self.assertEqual(client.query('contract/entity', [('code', 'A')])[0]['amount'], before)
        finally:
            test_transport.Transport.tearDownClass()
