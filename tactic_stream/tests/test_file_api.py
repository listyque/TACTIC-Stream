import test_checkin as checkin_tests
import test_read_parity as read_tests
import tempfile
import shutil
from pathlib import Path
from tactic_stream.server.api import Api
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class FileApiParity(read_tests.ReadParity):
    maxDiff = None
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='file_api_contract', project='admin', name='repository_snapshot_group_API')]

    new_result = checkin_tests.CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('latest_flags'), [[1, True], [2, False]])
        self.assertEqual(result.pop('latest_flags'), [[1, False], [2, True]])
        self.assertEqual(original.pop('current_flags'), [[1, True], [2, True]])
        self.assertEqual(result.pop('current_flags'), [[1, True], [2, False]])
        self.assertFalse(original.pop('found_latest'))
        self.assertTrue(result.pop('found_latest'))
        self.assertEqual(result, original)

    def test_file_api_late_failure_restores_database_and_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/snapshot', 'sthpw/file', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'file API rollback'):
                    run_snapshot_case(dict(method='file_api_contract', fail=True))
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                self.assertFalse(any(path.is_file() for path in (store.data_dir / 'assets').rglob('*.txt')))
