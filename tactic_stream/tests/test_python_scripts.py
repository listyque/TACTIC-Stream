import shutil
import tempfile
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.python_probe import run_python_case


class PythonScripts(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='python_contract', project='admin', name='python_and_workflow_callbacks'),
                     dict(method='python_contract', project='admin', name='null_trigger_class', null_class=True)]

    def assert_case_result(self, case, result, original):
        if case.get('null_class'):
            self.assertEqual(original, {'error': 'TypeError'})
            self.assertEqual(result, {'result': 42})
        else:
            super().assert_case_result(case, result, original)

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_python_case(case)

    def test_saved_api_rollback_and_execution_permissions(self):
        from tactic_stream.server.api import Api
        from pyasm.common.errors import SecurityException, UnsupportedContract
        from pyasm.command import Command
        from tactic.command import PythonCmd
        from pyasm.search import Search
        from pyasm.security.authenticator import hash_password
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-script-check'))
            api = Api(store)
            admin = {'ticket': api.get_ticket('admin', 'private-script-check'), 'project': 'admin'}
            script = api.dispatch('insert', (admin, 'config/custom_script', {'folder': 'contract', 'title': 'run', 'language': 'python', 'script': "server.insert('sthpw/note', {'note':'rollback me','process':'python'})\nraise ValueError('script failed')"}))
            kinds = ('sthpw/note', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', admin['ticket'])
                with self.assertRaises(UnsupportedContract):
                    PythonCmd(code='return 42').get_results()
                before = [Search(kind).get_count() for kind in kinds]
            with self.assertRaisesRegex(ValueError, 'script failed'):
                api.dispatch('execute_python_script', (admin, 'contract/run', {}))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', admin['ticket'])
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
            api.dispatch('update', (admin, script['__search_key__'], {'script': "return {'value':value,'login':server.login}"}))
            self.assertEqual(api.dispatch('execute_python_script', (admin, 'contract/run', {'value': 7})), {'status': 'OK', 'description': 'Run PythonCmd with script path [contract/run]', 'info': {'value': 7, 'login': 'admin'}})
            # Source PythonCmd gives a saved path precedence over inline code.
            self.assertEqual(api.dispatch('execute_python_script', (admin, 'contract/run', {'value': 9, 'code': 'return 42'}))['info'], {'value': 9, 'login': 'admin'})
            self.assertEqual(api.dispatch('execute_python_script', (admin, '', {'code': "return {'value':value,'login':server.login}", 'value': 7})),
                             {'status': 'OK', 'description': 'Run PythonCmd with explicit code', 'info': {'value': 7, 'login': 'admin'}})
            with self.assertRaisesRegex(ValueError, 'inline failed'):
                api.dispatch('execute_python_script', (admin, '', {'code': "server.insert('sthpw/note', {'note':'inline rollback','process':'python'})\nraise ValueError('inline failed')"}))
            self.assertEqual(api.dispatch('query', (admin, 'sthpw/note', [['note', 'inline rollback']])), '[]')
            note = api.dispatch('insert', (admin, 'sthpw/note', {'note': 'native object before', 'process': 'python'}))
            with self.assertRaisesRegex(ValueError, 'native object failed'):
                api.dispatch('execute_python_script', (admin, '', {'code': "obj = server.query('sthpw/note', filters=[('code', note_code)], single=True, return_sobjects=True)\nobj.set_value('note', 'native object after')\nobj.commit()\nraise ValueError('native object failed')", 'note_code': note['code']}))
            self.assertEqual(api.dispatch('get_by_search_key', (admin, note['__search_key__']))['note'], 'native object before')
            file = Path(directory) / 'script.py'
            file.write_text("return {'value':value,'login':server.login}", encoding='utf-8')
            self.assertEqual(api.dispatch('execute_python_script', (admin, '', {'file_path': str(file), 'value': 8}))['info'],
                             {'value': 8, 'login': 'admin'})
            with self.assertRaises(ValueError):
                api.dispatch('execute_python_script', (admin, '', {'code': 42}))
            api.dispatch('insert', (admin, 'sthpw/login', {'login': 'reader', 'password': hash_password('private-reader-check')}))
            reader = {'ticket': api.get_ticket('reader', 'private-reader-check'), 'project': 'admin'}
            with self.assertRaises(SecurityException):
                api.dispatch('execute_python_script', (reader, 'contract/run', {}))
            with self.assertRaises(SecurityException):
                api.dispatch('execute_python_script', (reader, '', {'code': 'return 42'}))
            with request_context(RequestContext(store, 'reader', 'admin')):
                api.auth.bind_security('reader', reader['ticket'])
                cmd = PythonCmd(code='return 42')
                cmd.get_transaction().set_sync(False)
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(cmd)

    def test_mako_traceback_points_to_saved_script_line(self):
        from tactic_stream.server.api import Api
        from tactic.command.python_cmd import format_script_traceback
        from pyasm.security.authenticator import hash_password
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-traceback-check'))
            api = Api(store)
            ticket = {'ticket': api.get_ticket('admin', 'private-traceback-check'), 'project': 'admin'}
            api.dispatch('insert', (ticket, 'config/custom_script', {
                'folder': 'contract', 'title': 'traceback', 'language': 'python',
                'script': "def broken():\n    raise ValueError('custom failure')\nbroken()"}))
            try:
                api.dispatch('execute_python_script', (ticket, 'contract/traceback', {}))
            except ValueError as error:
                trace = format_script_traceback(error)
                self.assertIn('tactic://admin/contract/traceback", line 2, in broken', trace)
                self.assertIn("raise ValueError('custom failure')", trace)
                self.assertIn('tactic://admin/contract/traceback", line 3', trace)
                self.assertNotIn('memory:', trace)
                print(trace[trace.index('  File "tactic://'):])
            else:
                self.fail('Script must fail')
            # Both calls are inline templates. Their generated modules must
            # retain separate maps even when the inner script is much shorter.
            source = '\n'.join(['value = 1'] * 80) + "\nserver.execute_python_script('', {'code': \"raise ValueError('nested failure')\"})"
            try:
                api.dispatch('execute_python_script', (ticket, '', {'code': source}))
            except ValueError as error:
                trace = format_script_traceback(error)
                self.assertIn('tactic://admin/inline.py", line 81', trace)
                self.assertIn('tactic://admin/inline.py", line 1', trace)
                self.assertIn("raise ValueError('nested failure')", trace)
            else:
                self.fail('Nested script must fail')
