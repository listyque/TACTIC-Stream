import shutil
import tempfile
from pathlib import Path
import sys
import test_read_parity as read_tests
from pyasm.command import Command
from pyasm.search.search import RequestContext, Search, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case

def concurrent_versions(store, password):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from pyasm.biz import Pipeline
    api = Api(store)
    ticket = api.get_ticket('admin', password)
    barrier = Barrier(2)
    def save():
        with request_context(RequestContext(store, 'admin', 'one')):
            api.auth.bind_security('admin', ticket)
            barrier.wait(timeout=10)
            class Save(Command):
                def execute(self):
                    self.get_transaction().set_sync(False)
                    return Pipeline.get_by_code('PV_MAIN').save_version().get_value('version')
            return Command.execute_cmd(Save())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        return sorted(future.result(timeout=20) for future in futures)

class PipelineVersions(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
        cls.cases = [dict(method='pipeline_versions_contract', name='pipeline versions', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        import pipeline_versions_contract as contract
        self.assertEqual([obj['version'] for obj in result['versions']], [1, 2])
        self.assertEqual(result['properties'], original['properties'])
        self.assertEqual(result['created_category'], original['created_category'])
        self.assertIsNone(original['original_workflow'])  # Source retains the pre-edit process cache.
        for new, old in zip(result['versions'], original['versions']):
            self.assertEqual(new['parent_code'], old['parent_code'])
            self.assertEqual(new['version'], old['version'])
            self.assertEqual(new['workflow'], {key: value for key, value in result['original_workflow'].items() if key != 'pipeline_code'})
            self.assertEqual(new['script'], contract.SCRIPT)
            self.assertIsNone(old['script'])  # Source resolves an unbound cached definition.
            self.assertTrue(new['xml_code_matches'])
            self.assertTrue(new['trigger_uses_own_script'])
            self.assertTrue(new['workflow_owner_matches'])
            self.assertTrue(new['progress_owner_matches'])
            self.assertFalse(old['xml_code_matches'])
            self.assertFalse(old['trigger_uses_own_script'])

    def test_unported_filter_dependencies_and_sql_are_rejected(self):
        from pyasm.common.errors import UnsupportedContract
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            for filters in (['amount >= 0'],
                            [['other_table.code', 'A']], [['code', '@@', 'secret']]):
                with self.assertRaises(UnsupportedContract):
                    Search('contract/dep_parent').add_op_filters(filters)

    def test_versions_execute_templates_and_rollback(self):
        import pipeline_versions_contract as contract
        from pyasm.biz import Pipeline
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                run_snapshot_case(self.cases[0])
                for pipeline in Search('sthpw/pipeline').get_sobjects():
                    if pipeline.get_value('parent_code') == 'PV_MAIN':
                        self.assertEqual(len(pipeline.get_related_sobjects('config/process')), 2)
                self.assertEqual(contract.native_lifecycle(), {'pipeline_code': 'PV_MAIN', 'notes': ['frozen action', 'current action']})
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
                            for table in ('pipeline', 'spt_process', 'spt_trigger', 'spt_custom_script', 'transaction_log')}
                before = records()
                class Fail(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        Pipeline.get_by_code('PV_MAIN').save_version()
                        raise ValueError('late version failure')
                with self.assertRaisesRegex(ValueError, 'late version failure'):
                    Command.execute_cmd(Fail())
                self.assertEqual(records(), before)
                self.assertEqual(contract.templates(), {'name': 'work', 'type': 'manual', 'xpos': '10',
                    'label': 'Template label', 'color': '#112233', 'process_code_matches': True, 'checkin_mode': 'copy'})
            self.assertEqual(concurrent_versions(store, 'private-test-password'), [3, 4])
            with request_context(RequestContext(store, 'admin', 'one')):
                from pyasm.common.errors import SecurityException
                Api(store).auth.bind_security('admin', self.ticket)
                loaded = Pipeline.get_by_code('PV_MAIN')
                with store.connection(write=True) as db:
                    db.execute("UPDATE login SET s_status='retired' WHERE login='admin'")
                before = records()
                with self.assertRaises(SecurityException):
                    loaded.save_version()
                self.assertEqual(records(), before)
