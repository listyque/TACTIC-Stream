import json
import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class WorkflowNodes(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import workflow_nodes_contract as contract
        with cls.store.connection(write=True) as db:
            contract.install_fixture(db)
        cls.cases = [dict(method='workflow_nodes_contract', name=code, graph=code, project='admin') for code in contract.CASES]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        code = case['graph']
        if code in ('ROOT', 'NESTED', 'REUSED', 'HOLD_ROOT'):
            self.assertEqual(result['after']['states']['done'], 'complete')
            self.assertEqual(result['after']['states']['__PIPELINE__'], 'complete')
            if code == 'HOLD_ROOT':
                self.assertEqual(result['before']['states']['start'], 'in_progress')
                self.assertNotIn('done', result['before']['states'])
                self.assertEqual(result['after']['states']['start/hold'], 'complete')
                self.assertEqual(result['after']['tasks'], [['start', 'Complete'], ['start/hold', 'Complete']])
                self.assertEqual(original['before']['states']['start'], 'complete')
                return
            prefix = 'start/start' if code == 'NESTED' else 'first' if code == 'REUSED' else 'start'
            self.assertEqual(result['after']['states'][prefix + '/work'], 'complete')
            if code == 'REUSED':
                self.assertEqual(result['after']['states']['second/work'], 'complete')
            self.assertNotIn('work', result['after']['states'])
            new_notes = [json.loads(note) for note in result['after']['notes']]
            self.assertTrue(all(note[3:] == [{'value': 7}, {'value': 9}] for note in new_notes))
            old_notes = [json.loads(note) for note in original['after']['notes']]
            self.assertTrue(any(note[0] == 'CHILD' and note[3] is None for note in old_notes))
            self.assertEqual(sum(note[:3] == [code, 'done', 'action'] for note in new_notes), 1)
            return
        if code == 'HOOK':
            self.assertIn('success hook', result['after']['notes'])
            self.assertNotIn('success hook', original['after']['notes'])
            self.assertNotIn('left', result['after']['states'])
            self.assertEqual(original['after']['states']['join'], 'complete')
            return
        if code != 'PROGRESS':
            for moment in ('before', 'after'):
                notes = original[moment]['notes']
                # Source runs on_complete once before on_action and once through the event.
                self.assertEqual(json.loads(notes[0])[1:3], ['choose', 'complete'])
                self.assertEqual(json.loads(notes[1])[1:3], ['choose', 'action'])
                del notes[0]
                if code in ('STREAMS', 'NAMES'):
                    for index, text in enumerate(notes):
                        note = json.loads(text)
                        if note[1] != 'choose':
                            self.assertIsNone(note[4])
                            note[4] = {'value': 9}
                            notes[index] = json.dumps(note)
        else:
            notes = original['after']['notes']
            note = json.loads(notes[-1])
            self.assertEqual(note[1:], ['start', 'revise', None, None])
            note[3:] = [{'value': 7}, {'value': 9}]
            notes[-1] = json.dumps(note)
        super().assert_case_result(case, result, original)
        if code in ('STREAMS', 'NAMES'):
            self.assertEqual(result['after']['states']['left'], 'complete')
            self.assertEqual(result['after']['states']['right'], 'not_required')
            self.assertEqual(result['after']['states']['join'], 'complete')

    def test_hierarchy_failure_rolls_back_tasks_states_and_callbacks(self):
        import workflow_nodes_contract as contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                from tactic_stream.server.api import Api
                Api(store).auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/task', 'config/process_state', 'sthpw/note', 'sthpw/message', 'sthpw/transaction_log')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'late hierarchy failure'):
                    contract.run({'graph': 'HOLD_ROOT', 'fail': True})
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)

    def test_hierarchy_preflight_and_task_regeneration(self):
        from pyasm.biz import Pipeline, Task
        from pyasm.command import Command
        from pyasm.command.workflow import _check_workflow
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                Api(store).auth.bind_security('admin', self.ticket)
                parent = Search.get_by_code('contract/nodes', 'HOLD_ROOT')
                pipeline = Pipeline.get_by_code('HOLD_ROOT')
                child = Pipeline.get_by_code('HOLD_CHILD')
                class Generate(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        first = Task.add_initial_tasks(parent, start_date='2026-10-05')
                        self_outer.assertEqual([row.get_value('process') for row in first], ['start/hold', 'start'])
                        self_outer.assertEqual(Task.add_initial_tasks(parent, start_date='2026-10-05'), [])
                        second = Task.add_initial_tasks(parent, start_date='2026-10-05', skip_duplicate=False)
                        self_outer.assertEqual([row.get_value('process') for row in second], ['start/hold', 'start'])
                        self_outer.assertEqual([row.get_value('context') for row in second], ['hold/001', 'start/001'])
                        # A child cannot re-enter its own parent before any writes/callbacks.
                        child.set_pipeline('<pipeline><process name="start" type="hierarchy"/></pipeline>', cache=False)
                        definition = child.get_process_sobject('start')
                        definition.set_value('subpipeline_code', 'HOLD_ROOT')
                        definition.commit()
                        with self_outer.assertRaisesRegex(ValueError, 'Recursive task hierarchy'):
                            _check_workflow({'sobject': parent, 'pipeline': pipeline, 'process': 'start'})
                        raise ValueError('rollback temporary hierarchy')
                self_outer = self
                with self.assertRaisesRegex(ValueError, 'rollback temporary hierarchy'):
                    Command.execute_cmd(Generate())
                self.assertEqual(Task.get_by_sobject(parent), [])
