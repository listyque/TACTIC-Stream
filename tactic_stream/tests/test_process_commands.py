import json
import shutil
import sys
import tempfile
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case

class ProcessCommands(read_tests.ReadParity):
    maxDiff = None
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract, process_commands_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
        cls.cases = [dict(method='process_commands_contract', name=code, graph=code, project='one') for code in process_commands_contract.CASES]
    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)
    def assert_case_result(self, case, result, original):
        code = case['graph']
        if code == 'PROGRESS_EXECUTION':
            self.assertEqual(original, {'statuses': ['in_progress', 'in_progress']})
            self.assertEqual(result, {'statuses': ['in_progress', 'complete']})
            return
        if code == 'BAD_SETTINGS':
            self.assertEqual(result['error'], 'ValueError: Invalid settings for process [publish]')
            self.assertEqual(original['error'], '')  # Source silently ignores malformed settings.
            self.assertEqual(result['workflow'], {'version': 2})
            self.assertEqual(result['triggers'], [])
            self.assertIsNone(result['label'])
            return
        if code == 'BAD_HANDLER':
            self.assertEqual(result['error'], original['error'])
            self.assertEqual(result['error'], 'ValueError: custom save failed')
            self.assertEqual(result['workflow'], {'version': 2})
            self.assertIsNone(result['label'])  # Source leaves a changed cached graph after rollback.
            return
        self.assertEqual(result['error'], '')
        self.assertEqual(original['error'], '')
        self.assertEqual(result['notes'], ['saved action'] if code in ('SAVE_V1', 'SAVE_V2', 'SAVED_SCRIPT') else ['custom action'] if code == 'CUSTOM' else [])
        self.assertEqual(original['notes'], ['custom action'] if code == 'CUSTOM' else [])  # Source reuses stale trigger caches.
        if code in ('SAVE_V1', 'SAVE_V2', 'CUSTOM'):
            self.assertEqual(result['label'], 'A & B')
            self.assertEqual(original['label'], 'A &amp; B')
            self.assertEqual(result['process_code'], 'PM_' + code + '_publish')
            self.assertIsNone(original['process_code'])
        if code == 'CUSTOM':
            self.assertEqual(result['description'], 'custom saved')
            self.assertEqual(original['description'], '')
        else:
            self.assertEqual(result['description'], original['description'])
        if code == 'DEPENDENCY':
            self.assertNotIn('wait', original['workflow'])
            self.assertIs(result['workflow']['wait'], False)
            original['workflow']['wait'] = False
        self.assertEqual(result['workflow'], original['workflow'])
        if code in ('SAVE_V1', 'SAVE_V2'):
            self.assertEqual(result['triggers'], [['process|action', '_triggers/PM_' + code + '/PM_' + code + '_publish', '']])
            self.assertEqual(original['triggers'][0][0], 'process|action')
            self.assertTrue(original['triggers'][0][1].startswith('_triggers/PM_' + code + '/SPT_PROCESS'))
        elif code == 'SAVED_SCRIPT':
            self.assertEqual(result['triggers'], [['process|action', 'tests/existing', '']])
            self.assertEqual(original['triggers'], [['process|action', '', '']])
        else:
            self.assertEqual(result['triggers'], original['triggers'])

    def test_progress_waits_for_all_children(self):
        from tactic_stream.server.api import Api
        import process_commands_contract as contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                self.assertEqual(contract.progress_cycle(), ['in_progress', 'complete'])

    def test_custom_handler_rollback_cache_and_security(self):
        from tactic_stream.server.api import Api
        from pyasm.command import Command, CustomProcessConfig
        from pyasm.common import Container
        from pyasm.common.errors import SecurityException
        from pyasm.search import Search
        from unittest.mock import patch
        import process_commands_contract as contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                key = Command.execute_cmd(contract.Setup('BAD_HANDLER'))
                tables = ('pipeline', 'spt_process', 'spt_trigger', 'spt_custom_script', 'spt_widget_config', 'note', 'transaction_log')
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')] for table in tables}
                before = records()
                with self.assertRaisesRegex(ValueError, 'custom save failed'):
                    Command.execute_cmd(contract.Save('BAD_HANDLER', key))
                self.assertEqual(records(), before)
                old = CustomProcessConfig.get_config('contract_custom')
                class Update(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        config = Search.get_by_search_key(old.get_search_key())
                        config.set_value('config', config.get_value('config').replace('process_commands_contract.SaveHandler', 'process_commands_contract.BrokenConstructor'))
                        config.commit()
                        cfg = CustomProcessConfig.get_config('contract_custom')
                        if cfg.get_display_handler('save') != 'process_commands_contract.BrokenConstructor':
                            raise AssertionError('Stale workflow config cache')
                        CustomProcessConfig.get_save_handler('contract_custom', {})
                with self.assertRaisesRegex(ValueError, 'constructor failed'):
                    Command.execute_cmd(Update())
                self.assertEqual(Container.get('process_constructor_calls'), 1)
                self.assertEqual(records(), before)
                with store.connection(write=True) as db:
                    db.execute("UPDATE login SET s_status='retired' WHERE login='admin'")
                with patch('process_commands_contract.SaveHandler') as constructor:
                    with self.assertRaises(SecurityException):
                        CustomProcessConfig.get_save_handler('contract_custom', {})
                    constructor.assert_not_called()
