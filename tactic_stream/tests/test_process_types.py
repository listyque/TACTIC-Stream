import shutil
import sys
import tempfile
from pathlib import Path
from pyasm.command import Command
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
import test_read_parity as read_tests
from tools.snapshot_probe import run_snapshot_case


class ProcessTypes(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
        cls.cases = [dict(method='process_type_contract', name='process type change', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        import process_type_contract as contract
        self.assertEqual(result['workflow'], {name: {'version': 2, 'node_type': 'manual'} for name in contract.NAMES})
        self.assertEqual(result['triggers'], 0)
        self.assertEqual(original['triggers'], 2)
        self.assertEqual(result['subpipeline'], '')
        self.assertEqual(original['subpipeline'], 'PT_CHILD')
        self.assertEqual(result['notes'], ['custom type released'])
        self.assertEqual(original['notes'], [])
        self.assertEqual(result['descriptions'], {name: 'Keep ' + name for name in contract.NAMES})
        self.assertEqual(original['descriptions'], {name: '' for name in contract.NAMES})  # Source reuses stale definitions.
        for key in ('scripts', 'tasks'):
            self.assertEqual(result[key], original[key])

    def test_raw_api_type_change_settings_versions_and_rollback(self):
        import process_type_contract as contract
        from pyasm.biz import Pipeline
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api, ticket = Api(store), {'ticket': self.ticket, 'project': 'one'}
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                key = Command.execute_cmd(contract.Setup())
                identities = {name: (row.get_id(), row.get_code()) for name, row in Pipeline.get_by_code('PT_MAIN').get_process_sobjects().items()}
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
                            for table in ('pipeline', 'spt_process', 'spt_trigger', 'spt_custom_script', 'note', 'task', 'transaction_log')}
                before = records()
                class Fail(Command):
                    def execute(self):
                        cfg = Search('config/widget_config')
                        cfg.add_filter('view', 'type_custom')
                        cfg = cfg.get_sobject()
                        cfg.set_value('config', cfg.get_value('config').replace('/></element>', '><fail>true</fail></display></element>'))
                        cfg.commit()
                        contract.Change().execute()
                with self.assertRaisesRegex(ValueError, 'custom type release failed'):
                    Command.execute_cmd(Fail())
                self.assertEqual(records(), before)
                class Version(Command):
                    def execute(self):
                        return Pipeline.get_by_code('PT_MAIN').save_version().get_code()
                version = Command.execute_cmd(Version())
            api.dispatch('update', (ticket, key, {'pipeline': contract.MANUAL_XML}))
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                pipeline = Pipeline.get_by_code('PT_MAIN')
                self.assertEqual({name: (row.get_id(), row.get_code()) for name, row in pipeline.get_process_sobjects().items()}, identities)
                self.assertEqual(contract.result()['triggers'], 0)
                self.assertEqual(contract.result()['tasks'], 1, records()['task'])
                frozen = Pipeline.get_by_code(version)
                self.assertEqual(frozen.get_process('progress').get_type(), 'progress')
                self.assertTrue(frozen.get_process_sobject('progress').get_json_value('workflow')['progress']['trigger_code'])
                # A second identical save must not call cleanup again.
                Command.execute_cmd(contract.Change())
                self.assertEqual(contract.result()['notes'], ['custom type released'])
                graph = contract.MANUAL_XML.replace('name="action" type="manual"', 'name="action" type="action"')
                Command.execute_cmd(contract.Change(pipeline=graph, node_kwargs={'action': {'version': 2,
                    'default': {'script': 'return True', 'execute_mode': 'same process,same transaction'}}}))
                self.assertEqual(contract.result()['triggers'], 1)
                self.assertEqual(pipeline.get_process_sobject('action').get_json_value('workflow')['default']['script'], 'return True')
                before = records()
                class LateFail(contract.Change):
                    def execute(self):
                        super().execute()
                        raise ValueError('late type change failed')
                with self.assertRaisesRegex(ValueError, 'late type change failed'):
                    Command.execute_cmd(LateFail())
                self.assertEqual(records(), before)
