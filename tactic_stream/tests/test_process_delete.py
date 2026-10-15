import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from pyasm.command import Command
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
import test_read_parity as read_tests
from tools.snapshot_probe import run_snapshot_case


class ProcessDelete(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
        cls.cases = [dict(method='process_delete_contract', name='process deletion', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['before'], dict(processes=3, triggers=3, scripts=1, notes=[], tasks=1))
        # The source's stale process cache duplicates definitions on a second sync.
        self.assertEqual(original['before'], dict(processes=6, triggers=3, scripts=1, notes=[], tasks=1))
        self.assertEqual(result['after'], dict(processes=0, triggers=1, scripts=result['before']['scripts'], notes=['custom deleted'], tasks=1))
        self.assertEqual(original['after'], dict(processes=0, triggers=3, scripts=original['before']['scripts'], notes=[], tasks=1))

    def test_delete_rollback_direct_api_and_security(self):
        import process_delete_contract as contract
        from pyasm.biz import Pipeline
        from pyasm.biz.pipeline import PipelineException
        from pyasm.common.errors import SecurityException
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'one'}
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                Command.execute_cmd(contract.Setup())
                key = Pipeline.get_by_code('PD_MAIN').get_process_sobject('custom').get_search_key()
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
                            for table in ('pipeline', 'spt_process', 'spt_trigger', 'spt_custom_script', 'note', 'task', 'transaction_log')}
                before = records()
                class Fail(contract.Delete):
                    def execute(self):
                        super().execute()
                        raise ValueError('late delete failure')
                with self.assertRaisesRegex(ValueError, 'late delete failure'):
                    Command.execute_cmd(Fail())
                self.assertEqual(records(), before)
                config = Search('config/widget_config').get_sobjects()[-1]
                class FailHandler(Command):
                    def execute(self):
                        cfg = Search.get_by_search_key(config.get_search_key())
                        cfg.set_value('config', cfg.get_value('config').replace('/></element>', '><fail>true</fail></display></element>'))
                        cfg.commit()
                        contract.Delete().execute()
                with self.assertRaisesRegex(ValueError, 'custom delete failed'):
                    Command.execute_cmd(FailHandler())
                self.assertEqual(records(), before)
                class SharedTrigger(Command):
                    def execute(self):
                        from pyasm.search import SearchType
                        other = SearchType.create('config/process')
                        other.set_value('pipeline_code', 'PD_OTHER')
                        other.set_value('process', 'shared')
                        action = Pipeline.get_by_code('PD_MAIN').get_process_sobject('action')
                        trigger = Search('config/trigger')
                        trigger.add_filter('process', action.get_code())
                        other.set_json_value('workflow', {'trigger_code': trigger.get_sobject().get_code()})
                        other.commit()
                        action.delete()
                with self.assertRaisesRegex(PipelineException, 'Process trigger is referenced by another process'):
                    Command.execute_cmd(SharedTrigger())
                self.assertEqual(records(), before)
                class Version(Command):
                    def execute(self):
                        return Pipeline.get_by_code('PD_MAIN').save_version().get_code()
                version = Command.execute_cmd(Version())
                loaded = Search.get_by_search_key(key)
                with store.connection(write=True) as db:
                    db.execute("UPDATE login SET s_status='retired' WHERE login='admin'")
                before = records()
                class DirectDelete(Command):
                    def execute(self):
                        loaded.delete()
                with patch('process_delete_contract.DeleteHandler') as handler:
                    with self.assertRaises(SecurityException):
                        Command.execute_cmd(DirectDelete())
                    handler.assert_not_called()
                self.assertEqual(records(), before)
                with store.connection(write=True) as db:
                    db.execute("UPDATE login SET s_status=NULL WHERE login='admin'")
            # Fresh request exercises the same lifecycle via the existing API.
            api.dispatch('delete_sobject', (ticket, key, False))
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                self.assertEqual(contract.result()['notes'], ['custom deleted'])
                self.assertEqual(contract.result()['processes'], 2)
                Command.execute_cmd(contract.Delete())
                self.assertEqual(contract.result()['processes'], 0)
                self.assertEqual(contract.result()['triggers'], 3)  # Frozen action/progress and external listener.
                self.assertEqual(contract.result()['scripts'], 2)
                self.assertEqual(len(Pipeline.get_by_code(version).get_process_sobjects()), 3)
