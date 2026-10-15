import tempfile
import shutil
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case
from tactic_stream.server.api import Api


class BatchApiParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
        cls.cases = [dict(method='batch_api_contract', project='admin', name='batch_api')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertTrue(original.pop('tasks_error'))
        self.assertFalse(result.pop('tasks_error'))
        self.assertEqual(result, original)

    def test_batch_failure_restores_all_rows_and_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/note', 'sthpw/task', 'sthpw/retire_log', 'sthpw/pref_setting', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'batch rollback'):
                    run_snapshot_case(dict(method='batch_api_contract', fail=True))
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
            api = Api(store)
            ticket = {'ticket': api.get_ticket('admin', 'private-test-password'), 'project': 'admin'}
            before = api.dispatch('query', (ticket, 'sthpw/note'))
            with self.assertRaises(Exception):
                api.dispatch('insert_multiple', (ticket, 'sthpw/note', [{'note': 'rollback'}, {'missing_column': 'fail'}]))
            self.assertEqual(api.dispatch('query', (ticket, 'sthpw/note')), before)
