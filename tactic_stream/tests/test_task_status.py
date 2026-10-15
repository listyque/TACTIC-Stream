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


class TaskStatus(read_tests.ReadParity):
    filter_test_search_type = 'contract/dep_child'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract, task_schedule_contract, task_status_contract as contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
            task_schedule_contract.install_fixture(db)
        cls.cases = [dict(method='task_status_contract', name=mode, operation=mode, project='one') for mode in contract.CASES]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        mode = case['operation']
        if mode in ('output', 'branch'):
            self.assertEqual(result['notes'], [[{'value': 7}, {'value': 9}]])
            self.assertEqual(result['states']['done'], 'complete')
            self.assertEqual(result['tasks'], original['tasks'])
            if mode == 'output':
                self.assertEqual(original['notes'], [])
                self.assertEqual(original['states']['done'], 'In Progress')
            else:
                self.assertEqual(result['states'], original['states'])
                self.assertEqual(original['notes'], [[None, None]])
            return
        prefix = 'gate/' if mode == 'nested' else 'CS_alternate::' if mode == 'alternate' else ''
        self.assertEqual(result['active']['states'][prefix + 'work'], 'in_progress')
        self.assertEqual(result['first']['notes'], [])
        self.assertEqual(result['final']['states'][prefix + 'work'], 'complete')
        self.assertEqual(result['final']['notes'], [[{'value': 7}, {'value': 9}]])
        self.assertEqual([row[1] for row in result['final']['tasks']], ['Ready', 'Ready'])
        if mode == 'xml':
            self.assertEqual(original['final']['states'], {'work': 'Ready', '__PIPELINE__': ''})
            self.assertEqual(original['final']['notes'], [])
            return
        if mode == 'alternate':
            self.assertEqual(original['final']['states'], {'work': 'pending'})
            self.assertEqual(original['final']['notes'], [])
            self.assertTrue(all(row[0] == 'work' for row in original['final']['tasks']))
            self.assertTrue(all(row[0] == prefix + 'work' for row in result['final']['tasks']))
            return
        if mode == 'nested':
            self.assertEqual(original['active']['states'], {'gate': 'in_progress', 'work': 'Working'})
            self.assertEqual(original['final']['states'], {'gate': 'complete', 'work': 'complete', '__PIPELINE__': 'complete', 'done': 'complete'})
            self.assertEqual(original['final']['notes'], [[None, None]])
            self.assertEqual(result['final']['states']['gate'], 'complete')
            self.assertEqual(result['final']['states']['gate/done'], 'complete')
            self.assertEqual(result['final']['tasks'], original['final']['tasks'])
            return
        self.assertEqual(original['active']['states']['work'], 'Working')
        original['active']['states']['work'] = 'in_progress'
        self.assertEqual(original['first']['states'].pop('__PIPELINE__'), '')
        self.assertEqual(result, original)

    def test_cycle_and_invalid_mapping_roll_back(self):
        import task_status_contract as contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                Command.execute_cmd(contract.Setup())
                Command.execute_cmd(contract.Begin())
                revised = Command.execute_cmd(contract.Change(status='Back'))
                self.assertEqual(revised['states']['work'], 'revise')
                self.assertEqual([row[1] for row in revised['tasks']], ['Back', 'Pending'])
                class Configure(Command):
                    def execute(self):
                        search = Search('config/process')
                        search.add_filter('pipeline_code', 'CS_v2_STATUS')
                        search.add_filter('process', 'Ready')
                        definition = search.get_sobject()
                        definition.set_json_value('workflow', self.kwargs['workflow'])
                        definition.commit()
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
                            for table in ('task', 'spt_process_state', 'message', 'message_log', 'note', 'status_log', 'transaction_log', 'change_timestamp')}
                for workflow, error in (({'version': 2, 'direction': 'current', 'status': 'Ready'}, 'Circular custom status transition'),
                                        ({'version': 2, 'mapping': 'unknown'}, 'Unknown task status mapping')):
                    Command.execute_cmd(Configure(workflow=workflow))
                    before = records()
                    with self.assertRaisesRegex(ValueError, error):
                        Command.execute_cmd(contract.Change())
                    self.assertEqual(records(), before)
