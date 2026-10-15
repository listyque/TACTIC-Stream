"""Snapshot level API: original runtime comparison and atomic failures."""
import shutil
import tempfile
from pathlib import Path
import test_read_parity as read_tests
from test_checkin import CheckinParity
from pyasm.search.storage import Store
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


class SnapshotLevelsParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='snapshot_levels_contract', project='admin', name='level_API')]

    new_result = CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        self.assertEqual(result.pop('hierarchy'), 1)
        self.assertIsNone(original.pop('hierarchy'))
        self.assertEqual(result.pop('alias_fixes'), [-1, True])
        self.assertEqual(original.pop('alias_fixes'), [0, False])
        self.assertEqual(result.pop('ref_errors'), [])
        self.assertEqual(original.pop('ref_errors'), ['SearchException', 'SearchException'])
        self.assertEqual(result, original)

    def test_level_checkin_late_failure_rolls_back_rows_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                from tools.snapshot_probe import run_snapshot_case
                from pyasm.search import Search
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                with self.assertRaisesRegex(ValueError, 'level API rollback'):
                    run_snapshot_case(dict(method='snapshot_levels_contract', fail=True))
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                self.assertFalse(any(path.is_file() for path in (store.data_dir / 'assets').rglob('*.txt')))
                for method in ('get_snapshot', 'get_paths'):
                    self.assertEqual(getattr(api, method)({}, 'sthpw/project?code=admin',
                        level_key='sthpw/project?code=admin', versionless=True), {})
