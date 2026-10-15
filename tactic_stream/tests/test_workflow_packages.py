import shutil
import sys
import tempfile
from pathlib import Path
from pyasm.command import Command
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
import test_read_parity as read_tests
from tools.snapshot_probe import run_snapshot_case


class WorkflowPackages(read_tests.ReadParity):
    filter_test_search_type = 'contract/dep_child'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
        cls.cases = [dict(method='workflow_packages_contract', name='snapshot packages', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['primary'], original['primary'])
        expected = {'primary': ['primary_final'], 'nested': ['nested_final'], 'alternate': ['alternate_wip'], 'empty': []}
        for kind, contexts in expected.items():
            self.assertEqual(result[kind]['default'], {'keep': 3, 'type': 'snapshot', 'snapshot_codes': contexts})
            self.assertEqual(result[kind]['message'], {'type': 'message', 'body': 'keep message'})
            self.assertEqual(result[kind]['custom'], {'value': 9})
        for kind in ('nested', 'alternate', 'empty'):
            self.assertEqual(original[kind]['default']['snapshot_codes'], ['primary_final'])
