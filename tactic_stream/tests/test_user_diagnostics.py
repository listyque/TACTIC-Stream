"""Authenticated diagnostics persist independently without system write rights."""
from unittest.mock import patch
import unittest
from pathlib import Path
import shutil
import tempfile

from pyasm.biz import DebugLog
from pyasm.command import Command
from pyasm.common import Container, Environment, Config
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, ExceptionLog, Transaction, DbContainer
from pyasm.search.exception_log import _write_log
from pyasm.search.search import RequestContext, request_context, _context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from test_plugin_installation import PluginInstallation
from test_project_writes import install_writer, PASSWORD, rules
from test_configs import DiagnosticParity
from tools.snapshot_probe import run_snapshot_case


def exercise_user_diagnostics(store, prefix):
    check = unittest.TestCase()
    api = Api(store)
    admin = dict(ticket=api.get_ticket('admin', 'plugin-test-password'), project='admin')
    project = prefix + '_ok'
    api.dispatch('execute_cmd', (admin, 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private diagnostics', project_stype=['asset'])))
    install_writer(store)
    resource = store.get_db_resource()
    parameter = resource.get_database_impl().get_parameter()
    with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
        db.execute('UPDATE login_group SET access_rules=%s WHERE code=%s' % (parameter, parameter),
            ('<rules><rule group="project" code="%s" access="allow"/>'
             '<rule group="search_type" code="%s/asset" project="%s" access="allow"/></rules>' % (project, project, project),
             'project_writers'))
    token = api.get_ticket('project_writer', PASSWORD)
    auth = dict(ticket=token, project=project)
    check.assertIs(api.dispatch('log', (auth, 'warning', "Writer's Текст & данные", 'user_api')), True)
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', token)
        security = Environment.get_security()
        check.assertFalse(security.is_admin())
        from pyasm.security import Batch
        before = _context.get()
        batch = Batch(login_code='project_writer', project_code=project, ticket=token)
        try:
            check.assertEqual(_context.get().login, 'project_writer')
            check.assertFalse(Environment.get_security().is_admin())
            DebugLog.debug('Batch Текст', 'user_batch')
            guard = Command(log_exception=False)
            guard.execute = lambda: DbContainer.get('sthpw').do_update("UPDATE project SET title='forbidden'")
            with check.assertRaises(UnsupportedContract):
                Command.execute_cmd(guard)
        finally:
            batch.__del__()
        check.assertIs(_context.get(), before)
        check.assertIs(Environment.get_security(), security)
        log = DebugLog.debug('Standalone Текст', 'user_standalone')
        check.assertGreater(log.get_id(), 0)
        check.assertEqual(log.get_value('login'), 'project_writer')
        check.assertIs(Environment.get_security(), security)
        check.assertFalse(security.is_admin())
        check.assertIsNone(Container.get('Diagnostics:writing'))
        with check.assertRaises(ValueError):
            DebugLog.log('invalid', 'rejected')
        for values in ({'login': 'admin', 'message': 'forged'}, {'message': 'missing author'}):
            with check.assertRaises(SecurityException):
                _write_log('sthpw/debug_log', values)
        with patch.object(security, 'is_logged_in', return_value=False):
            with check.assertRaises(SecurityException):
                DebugLog.log('info', 'unauthenticated')

        command = Command()
        def execute():
            command.get_transaction().set_sync(False)
            obj = SearchType.create(project + '/asset')
            obj.set_value('code', 'DIAG_ROLLBACK')
            obj.set_value('name', 'Must roll back')
            obj.commit(triggers='none')
            current = Transaction.get()
            DebugLog.log('info', 'Survives rollback', 'user_rollback')
            check.assertIs(Transaction.get(), current)
            check.assertTrue(current.is_in_transaction())
            check.assertTrue(current.record_flag)
            raise ValueError("User's original error · Тест")
        command.execute = execute
        with check.assertRaisesRegex(ValueError, "User's original error"):
            Command.execute_cmd(command)
        check.assertIsNone(Search.get_by_code(project + '/asset', 'DIAG_ROLLBACK'))
        search = Search('sthpw/exception_log')
        search.add_filter('message', "User's original error · Тест")
        error = search.get_sobject()
        check.assertIsNotNone(error)
        check.assertEqual(error.get_value('login'), 'project_writer')
        check.assertEqual(error.get_value('class'), 'ValueError')
        check.assertIn('raise ValueError', error.get_value('stack_trace'))
        check.assertNotIn('\\', error.get_value('stack_trace'))

        outer = Command(); inner = Command()
        inner.execute = lambda: (_ for _ in ()).throw(ValueError('user nested diagnostic'))
        outer.execute = lambda: Command.execute_cmd(inner)
        with check.assertRaisesRegex(ValueError, 'user nested diagnostic'):
            Command.execute_cmd(outer)
        search = Search('sthpw/exception_log'); search.add_filter('message', 'user nested diagnostic')
        check.assertEqual(search.get_count(), 1)

        # An already active system writer must remain owned by its caller.
        command = Command(log_exception=False)
        def execute_system_writer():
            command.get_transaction().set_sync(False)
            obj = SearchType.create(project + '/asset'); obj.set_value('code', 'DIAG_SYSTEM_ROLLBACK')
            obj.commit()
            with check.assertRaisesRegex(UnsupportedContract, 'Independent logging'):
                DebugLog.log('info', 'blocked by system writer')
            check.assertTrue(command.get_transaction().is_in_transaction())
            raise ValueError('rollback user system writer')
        command.execute = execute_system_writer
        with check.assertRaisesRegex(ValueError, 'rollback user system writer'):
            Command.execute_cmd(command)
        search = Search(project + '/asset'); search.add_filter('code', 'DIAG_SYSTEM_ROLLBACK')
        check.assertEqual(search.get_count(), 0)
        check.assertIsNone(Search.get_by_code(project + '/asset', 'DIAG_SYSTEM_ROLLBACK'))

        command = Command(log_exception=False)
        def execute_guard():
            obj = SearchType.create('sthpw/debug_log'); obj.set_value('login', 'project_writer')
            obj.set_value('message', 'direct write must fail')
            with check.assertRaises(SecurityException):
                obj.commit(triggers='none')
            sql = DbContainer.get('sthpw')
            with check.assertRaises(UnsupportedContract):
                sql.do_update("INSERT INTO debug_log(message) VALUES ('raw write')")
            saved = Search.get_by_id('sthpw/debug_log', log.get_id())
            with check.assertRaises(SecurityException):
                saved.delete()
        command.execute = execute_guard
        Command.execute_cmd(command)
        check.assertFalse(security.is_admin())
        check.assertIsNone(Container.get('Diagnostics:writing'))

    for kind in ('sthpw/debug_log', 'sthpw/exception_log'):
        with check.assertRaises((SecurityException, UnsupportedContract)):
            api.dispatch('insert', (auth, kind, {'login': 'project_writer', 'message': 'direct API write'}))
    for name in ('user_api', 'user_batch', 'user_standalone', 'user_rollback'):
        with store.connection() as db:
            row = db.execute('SELECT login,message FROM debug_log WHERE category=%s' % parameter, (name,)).fetchone()
            check.assertIsNotNone(row)
            check.assertEqual(row['login'], 'project_writer')
    return dict(logs=4, rollback=True, nested=1, protected=True)


class UserDiagnostics(PluginInstallation):
    exercise = staticmethod(exercise_user_diagnostics)


class UserDiagnosticParity(DiagnosticParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_writer(cls.store)
        cls.cases = [dict(method='diagnostic_contract', name='user_standalone', standalone=True, user='project_writer', rules=rules()),
                     dict(method='diagnostic_contract', name='user_api', api=True, user='project_writer', rules=rules())]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                return run_snapshot_case(case)


class UserDiagnosticTransport(unittest.TestCase):
    def test_unchanged_sdk_and_method_policy(self):
        import importlib.util
        import test_transport
        from test_foundation import LEGACY
        from xmlrpc.client import Fault
        test_transport.Transport.setUpClass()
        client = None
        try:
            store = test_transport.Transport.store
            install_writer(store)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.diagnostic_client',
                LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url); client.set_project('one')
            client.set_ticket(client.get_ticket('project_writer', PASSWORD))
            self.assertIs(client.log('info', 'SDK Текст & данные', 'user_sdk'), True)
            with self.assertRaises(Fault):
                client.log('invalid', 'bad level')
            resource = store.get_db_resource()
            parameter = resource.get_database_impl().get_parameter()
            with store.connection() as db:
                row = db.execute('SELECT login,message FROM debug_log WHERE category=%s' % parameter,
                                 ('user_sdk',)).fetchone()
                self.assertEqual((row['login'], row['message']), ('project_writer', 'SDK Текст & данные'))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM exception_log WHERE login=%s AND class=%s' %
                                           (parameter, parameter), ('project_writer', 'ValueError')).fetchone()[0], 1)
            with store.connection(write=True) as db:
                db.execute('UPDATE login_group SET access_rules=? WHERE code=?',
                    ('<rules><rule group="api_method" code="log" access="deny"/></rules>', 'project_writers'))
            with patch.object(Config, 'get_value', side_effect=lambda section, name, *a, **kw:
                              'true' if (section, name) == ('security', 'api_method_restricted') else ''):
                with self.assertRaises(Fault):
                    client.log('info', 'must not log', 'user_sdk_denied')
            with store.connection() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM debug_log WHERE category=?',
                                           ('user_sdk_denied',)).fetchone()[0], 0)
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
