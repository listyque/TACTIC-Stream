import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import mako.template
from pyasm.command import Command
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.command import PythonCmd
from tactic.command.python_cmd import format_script_traceback
from tactic_stream.server.api import Api


class PythonCompilation(unittest.TestCase):
    def setUp(self):
        from tactic.command.python_cmd import _compiled_scripts, _compiled_scripts_lock
        with _compiled_scripts_lock:
            _compiled_scripts.clear()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / 'data')
        self.store.initialize(hash_password('private-compilation-test'))
        self.api = Api(self.store)
        self.ticket = self.api.get_ticket('admin', 'private-compilation-test')
        self.context = dict(ticket=self.ticket, project='admin')

    def execute(self, callback):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            command = Command()
            command.get_transaction().set_sync(False)
            command.execute = callback
            return Command.execute_cmd(command)

    def test_compilation_reused_but_inputs_clock_side_effects_and_globals_are_fresh(self):
        source = """import time
state = globals().setdefault('per_execution_state', [])
state.append(input['filename'])
input['seen'].append(input['filename'])
return (input['filename'], time.time_ns(), list(state))"""
        seen = []
        def run():
            return [PythonCmd(code=source, input=dict(filename=name, seen=seen)).get_results()
                    for name in ('shot_001.abc', 'asset_002.exr', 'shot_003.abc')]
        with patch.object(mako.template, '_compile_text', wraps=mako.template._compile_text) as compilation:
            with patch('time.time_ns', side_effect=[1000000001, 1001000002, 1002000003]):
                first, second, third = self.execute(run)
            self.assertEqual(compilation.call_count, 1)
            self.assertEqual(first, ('shot_001.abc', 1000000001, ['shot_001.abc']))
            self.assertEqual(second, ('asset_002.exr', 1001000002, ['asset_002.exr']))
            self.assertEqual(third, ('shot_003.abc', 1002000003, ['shot_003.abc']))
            self.assertEqual(seen, ['shot_001.abc', 'asset_002.exr', 'shot_003.abc'])
            self.execute(lambda: PythonCmd(code=source, input=dict(filename='new_request', seen=[])).get_results())
            self.assertEqual(compilation.call_count, 1)

    def test_warm_bytecode_keeps_concurrent_request_globals_and_inputs_separate(self):
        from concurrent.futures import ThreadPoolExecutor
        source = "state = globals().setdefault('isolated', [])\nstate.append(kwargs['number'])\nreturn list(state)"
        def run(number):
            return self.api.dispatch('execute_python_script', (self.context, '', dict(code=source, number=number)))['info']
        self.assertEqual(run(-1), [-1])
        with patch.object(mako.template, '_compile_text', wraps=mako.template._compile_text) as compilation:
            with ThreadPoolExecutor(max_workers=4) as pool:
                self.assertEqual(list(pool.map(run, range(16))), [[index] for index in range(16)])
            compilation.assert_not_called()

    def test_bytecode_cache_is_bounded_and_large_sources_stay_request_local(self):
        from tactic.command.python_cmd import _compiled_scripts
        for value in range(35):
            self.assertEqual(self.api.dispatch('execute_python_script',
                (self.context, '', dict(code='return %d' % value)))['info'], value)
        self.assertEqual(len(_compiled_scripts), 32)
        self.assertFalse(any(key[2] == 'return 0' for key in _compiled_scripts))
        large = '#' + 'x' * 65536 + '\nreturn 101'
        with patch.object(mako.template, '_compile_text', wraps=mako.template._compile_text) as compilation:
            for _ in range(2):
                self.assertEqual(self.execute(lambda: [PythonCmd(code=large).get_results() for _ in range(2)]), [101, 101])
            self.assertEqual(compilation.call_count, 2)
        self.assertFalse(any(key[2] == large for key in _compiled_scripts))

    def test_cached_modules_execute_global_mako_blocks_once_per_invocation(self):
        seen = []
        source = """value = 1
%>
<%!
from builtins import _stream_compilation_seen
_stream_compilation_seen.append('execution')
%>
<%
return value"""
        with patch('builtins._stream_compilation_seen', seen, create=True):
            for _ in range(3):
                self.assertEqual(self.api.dispatch('execute_python_script', (self.context, '', dict(code=source)))['info'], 1)
        self.assertEqual(seen, ['execution'] * 3)

    def test_native_non_string_source_keeps_original_mako_conversion(self):
        from tactic.command.python_cmd import _compiled_scripts
        self.assertEqual(self.execute(lambda: PythonCmd(code=42).get_results()), '')
        self.assertFalse(any(key[2] == 42 for key in _compiled_scripts))

    def test_saved_and_file_source_updates_and_labels_are_not_reused(self):
        record = self.api.dispatch('insert', (self.context, 'config/custom_script',
            dict(folder='contract', title='cached', language='python', script='return 1')))
        path = Path(self.directory.name) / 'script.py'
        path.write_text('return 1', encoding='utf-8')
        def run():
            results = [PythonCmd(script_path='contract/cached').get_results()]
            results.append(PythonCmd(file_path=str(path)).get_results())
            saved = Search.get_by_search_key(record['__search_key__'])
            saved.set_value('script', 'return 2')
            saved.commit()
            path.write_text('return 3', encoding='utf-8')
            results.append(PythonCmd(script_path='contract/cached').get_results())
            results.append(PythonCmd(file_path=str(path)).get_results())
            return results
        with patch.object(mako.template, '_compile_text', wraps=mako.template._compile_text) as compilation:
            self.assertEqual(self.execute(run), [1, 1, 2, 3])
            self.assertEqual(compilation.call_count, 4)

    def test_permission_check_still_runs_on_cache_hit(self):
        from tactic.command.python_cmd import check_script_execution
        def run():
            self.assertEqual(PythonCmd(code='return 42').get_results(), 42)
            permission.side_effect = SecurityException('permission revoked')
            with self.assertRaises(SecurityException):
                PythonCmd(code='return 42').get_results()
        with patch('tactic.command.python_cmd.check_script_execution',
                   wraps=check_script_execution) as permission:
            self.execute(run)
            self.assertEqual(permission.call_count, 2)

    def test_cached_native_reads_skip_search_setup_and_keep_resource_policy(self):
        from pyasm.biz import Project
        from pyasm.common import Container
        def run():
            project = Project.get_by_code('admin')
            self.assertIsNone(Project.get_by_code('missing_project'))
            by_id = Project.get_by_id(project.get_id())
            with patch.object(Search, '__init__', autospec=True, side_effect=Search.__init__) as setup:
                for _ in range(3):
                    self.assertIs(Project.get_by_code('admin'), project)
                    self.assertIsNone(Project.get_by_code('missing_project'))
                    self.assertIs(Project.get_by_id(project.get_id()), by_id)
                setup.assert_not_called()
            def deny(base):
                raise SecurityException('read policy revoked: ' + base)
            Container.put('Expression:check_record_access', deny)
            try:
                with self.assertRaisesRegex(SecurityException, 'read policy revoked: sthpw/project'):
                    Project.get_by_code('admin')
            finally:
                Container.remove('Expression:check_record_access')
        self.execute(run)

    def test_retired_and_active_native_identity_lookups_have_separate_caches(self):
        from pyasm.search import SObject
        class CachedProject(SObject):
            SEARCH_TYPE = 'sthpw/project'
        row = self.api.dispatch('insert', (self.context, 'sthpw/project',
            dict(code='retired_cache', type='unittest', s_status='retired')))
        def run():
            for _ in range(3):
                self.assertIsNotNone(CachedProject.get_by_code(row['code']))
                self.assertIsNone(CachedProject.get_by_code(row['code'], show_retired=False))
                self.assertIsNotNone(CachedProject.get_by_id(row['id']))
                # Native explicit id filters include retired rows, regardless of this flag.
                self.assertIsNotNone(CachedProject.get_by_id(row['id'], show_retired=False))
        self.execute(run)

    def test_saved_script_read_cache_refreshes_after_delete_and_recreate(self):
        row = self.api.dispatch('insert', (self.context, 'config/custom_script',
            dict(folder='contract', title='replace', language='python', script='return 1')))
        def run():
            for _ in range(3):
                self.assertEqual(PythonCmd(script_path='contract/replace').get_results(), 1)
            Search.get_by_search_key(row['__search_key__']).delete()
            with self.assertRaisesRegex(Exception, 'does not exist'):
                PythonCmd(script_path='contract/replace').get_results()
            from pyasm.search import SearchType
            replacement = SearchType.create('config/custom_script')
            for key, value in dict(folder='contract', title='replace', language='python', script='return 2').items():
                replacement.set_value(key, value)
            replacement.commit()
            self.assertEqual(PythonCmd(script_path='contract/replace').get_results(), 2)
        self.execute(run)

    def test_cached_nested_errors_keep_source_lines_and_late_failure_rolls_back(self):
        source = "\n".join(['value = 1'] * 80) + "\nserver.execute_python_script('', {'code': \"raise ValueError('nested failure')\"})"
        def run():
            for _ in range(2):
                try:
                    PythonCmd(code=source).get_results()
                except ValueError as error:
                    trace = format_script_traceback(error)
                    self.assertIn('tactic://admin/inline.py\", line 81', trace)
                    self.assertIn('tactic://admin/inline.py\", line 1', trace)
                else:
                    self.fail('Nested script must fail')
            script = "server.insert('sthpw/note', {'note': 'cached rollback', 'process': 'python'})\nif fail:\n    raise ValueError('late failure')\nreturn 42"
            self.assertEqual(PythonCmd(code=script, fail=False).get_results(), 42)
            PythonCmd(code=script, fail=True).get_results()
        with patch.object(mako.template, '_compile_text', wraps=mako.template._compile_text) as compilation:
            with self.assertRaisesRegex(ValueError, 'late failure'):
                self.execute(run)
            self.assertEqual(compilation.call_count, 3)
        self.assertEqual(self.api.dispatch('query', (self.context, 'sthpw/note', [['note', 'cached rollback']])), '[]')

    def test_syntax_errors_keep_original_source_and_cause(self):
        def run():
            try:
                PythonCmd(code='value = 1\nif:').get_results()
            except Exception as error:
                trace = format_script_traceback(error)
                self.assertEqual(error.tactic_script_sources[None],
                                 ('tactic://admin/inline.py', ['value = 1', 'if:'], 3))
                self.assertIsInstance(error.__cause__, SyntaxError)
                self.assertEqual(error.__cause__.lineno, 2)
                self.assertIn('tactic://admin/inline.py', trace)
                self.assertIn('if:', trace)
            else:
                self.fail('Invalid script must fail')
        self.execute(run)
