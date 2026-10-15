import shutil
import tempfile
import sys
from pathlib import Path
import test_read_parity as read_tests
import test_checkin as checkin_tests
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


class WorkflowApiParity(read_tests.ReadParity):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import engine_contract
        with cls.store.connection(write=True) as db:
            engine_contract.install_fixture(db)
        cls.cases = [dict(method='workflow_api_contract', project='admin', name='workflow_task_dependency_API')]

    new_result = checkin_tests.CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('api_metadata'), {'name': 'API metadata', 'description': 'sthpw/task', 'search_type': '', 'connects': 1})
        self.assertEqual(result.pop('api_metadata'), {'name': 'API metadata', 'description': None, 'search_type': 'sthpw/task', 'connects': 0})
        self.assertEqual(original.pop('core_process_count'), 4)
        self.assertEqual(result.pop('core_process_count'), 2)
        self.assertTrue(original.pop('status_error'))
        self.assertFalse(result.pop('status_error'))
        self.assertEqual(original.pop('statuses'), ['complete', None])
        self.assertEqual(result.pop('statuses'), ['complete', 'complete'])
        self.assertEqual(result, original)

    def test_failed_api_command_rolls_back_pipeline_processes_workflow_refs_and_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/pipeline', 'config/process', 'sthpw/task', 'sthpw/snapshot', 'sthpw/file',
                         'sthpw/message', 'sthpw/message_log', 'config/process_state', 'sthpw/status_log',
                         'sthpw/note', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'workflow API rollback'):
                    run_snapshot_case(dict(method='workflow_api_contract', fail=True))
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)


