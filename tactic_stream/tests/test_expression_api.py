import ast
import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search.search import RequestContext, Search, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class ExpressionApiParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='api_body', name=name, call='eval', args=[expression], kwargs=options)
                     for name, expression, options in [
                         ('arithmetic', '6 * 7', {}), ('literal', "'3'", {'single': True}),
                         ('unicode', "'Данные'", {'single': True}),
                         ('columns', '@GET(contract/entity.name)', {}),
                         ('objects', '@SOBJECT(contract/entity)', {}),
                         ('single_object', '@SOBJECT()', {'search_keys': ['contract/entity?project=one&code=A'], 'single': True}),
                         ('dict_roots', '@GET(.name)', {'search_keys': [{'__search_key__': 'contract/entity?project=one&amp;amp;code=A'}]}),
                         ('variables', '$VALUE * 2', {'vars': {'VALUE': 7}}),
                         ('retired', '@COUNT(contract/entity)', {'show_retired': True}),
                         ('empty', '@GET(contract/entity["code","missing"].name)', {'single': True}),
                     ]]

    def new_result(self, case):
        return self.api.dispatch('eval', ({'ticket': self.ticket, 'project': 'one'}, *case['args']), case['kwargs'])

    def test_expression_read_policy_and_write_guards(self):
        with request_context(RequestContext(self.store, 'reader', 'one')):
            from pyasm.biz import ExpressionParser
            from pyasm.security import Security
            security = Security()
            Environment.set_security(security)
            security._is_logged_in = 1
            login = Search.get_by_code('sthpw/login', 'admin')
            login.set_value('login', 'reader', temp=True)
            security._login = login
            ticket = {'project': 'one'}
            # Core may read the login; an API call must not reuse that cached result.
            ExpressionParser().eval('@GET(sthpw/login.password)')
            for expression in ('@GET(sthpw/login.password)', '@GET(login.password)', '@COUNT(login)',
                               '@COUNT(sthpw/login)', '@update(sobject,note,changed)',
                               "@EVAL('@PYTHON(missing/script)')"):
                with self.subTest(expression=expression), self.assertRaises(SecurityException):
                    self.api.eval(ticket, expression)
                self.assertIsNone(Container.get('Expression:check_record_access'))
                self.assertIsNone(Container.get('Expression:check_method_access'))
            for expression in ('@COUNT(sthpw/transaction_log)', '@SOBJECT(sthpw/sobject_log)'):
                with self.assertRaises(UnsupportedContract):
                    self.api.eval(ticket, expression)
            self.assertEqual(ast.literal_eval(self.api.eval(ticket, '6 * 7')), 42)

    def test_eval_method_restriction_and_persisted_admin(self):
        from unittest.mock import patch
        from pyasm.common import Config
        from pyasm.biz import ExpressionParser
        from pyasm.command import Command
        from pyasm.security import Security
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            self.api.check_method_access('eval')
            get_value = Config.get_value
            def restricted_config(section, name, *args, **kwargs):
                if section == 'security' and name in ('api_cmd_restricted', 'api_method_restricted'):
                    return 'true'
                return get_value(section, name, *args, **kwargs)
            with patch.object(Config, 'get_value', side_effect=restricted_config), patch.object(Environment.get_security(), 'check_access', return_value=False):
                for method in ('eval', 'update', 'execute_python_script'):
                    with self.subTest(method=method), self.assertRaises(SecurityException):
                        self.api.check_method_access(method)
                cmd = Command()
                cmd.execute = lambda: ExpressionParser().eval('@python(missing/script)')
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(cmd)
        with request_context(RequestContext(self.store, 'reader', 'one')):
            # In-memory admin/Sudo cannot replace persisted privileges.
            security = Security()
            Environment.set_security(security)
            security._is_logged_in = 1
            security._login = Search.get_by_code('sthpw/login', 'admin')
            cmd = Command()
            cmd.execute = lambda: ExpressionParser().eval('@update(sobject,note,changed)')
            with self.assertRaises((SecurityException, UnsupportedContract)):
                Command.execute_cmd(cmd)

    def test_authenticated_reader_eval_without_write_privileges(self):
        from pyasm.security.authenticator import hash_password
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login(code,login,password) VALUES ('eval_reader','eval_reader',?)", (hash_password('private-reader-check'),))
            db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('eval_readers','eval_readers',?)",
                       ('<rules><rule group="search_type" default="allow"/></rules>',))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('eval_reader_group','eval_reader','eval_readers')")
        ticket = {'ticket': self.api.get_ticket('eval_reader', 'private-reader-check'), 'project': 'one'}
        try:
            self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (ticket, '6 * 7'))), 42)
            self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (ticket, '@GET(.name)', ['contract/entity?project=one&code=A']))), ['Первый'])
            for expression in ('@GET(login.password)', '@update(sobject,note,changed)', '@python(missing/script)'):
                with self.subTest(expression=expression), self.assertRaises(SecurityException):
                    self.api.dispatch('eval', (ticket, expression))
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM ticket WHERE login='eval_reader'")
                db.execute("DELETE FROM login_in_group WHERE code='eval_reader_group'")
                db.execute("DELETE FROM login_group WHERE code='eval_readers'")
                db.execute("DELETE FROM login WHERE code='eval_reader'")


class ExpressionWriteParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='expression_write_contract', project='admin', name='rollback', fail=True),
                     dict(method='expression_write_contract', project='admin', name='write')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, original)
        self.assertEqual(result['after'], [] if case.get('fail') else ['changed', 'from python'])
        self.assertEqual(result['script_exists'], not case.get('fail'))

