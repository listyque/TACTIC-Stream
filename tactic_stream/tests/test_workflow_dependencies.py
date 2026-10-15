import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


def concurrent_waiters(store, password):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from pyasm.biz import Pipeline, Task
    from pyasm.command import Command, Trigger, Workflow
    from pyasm.search import Search, SearchType
    from tactic_stream.server.api import Api
    api = Api(store)
    ticket = api.get_ticket('admin', password)
    with request_context(RequestContext(store, 'admin', 'one')):
        api.auth.bind_security('admin', ticket)
        class Setup(Command):
            def execute(self):
                self.get_transaction().set_sync(False)
                definition = Pipeline.get_by_code('DEP_SHARED').get_process_sobject('start')
                workflow = definition.get_json_value('workflow')
                workflow['default']['related_search_type'] = "@SOBJECT(contract/dep_child['group_code','CONCURRENT'])"
                definition.set_json_value('workflow', workflow)
                definition.commit(triggers=False)
                for code in ('CONCURRENT_A', 'CONCURRENT_B'):
                    parent = SearchType.create('contract/dep_parent')
                    parent.set_value('code', code)
                    parent.set_value('pipeline_code', 'DEP_SHARED')
                    parent.commit(triggers=False)
                child = SearchType.create('contract/dep_child')
                for column, value in dict(code='CONCURRENT_CHILD', group_code='CONCURRENT', pipeline_code='DEP_CHILD').items():
                    child.set_value(column, value)
                child.commit(triggers=False)
                return Task.create(child, 'work', status='Pending', triggers='none').get_search_key()
        task = Command.execute_cmd(Setup())
    barrier = Barrier(2)
    def start(code):
        with request_context(RequestContext(store, 'admin', 'one')):
            api.auth.bind_security('admin', ticket)
            Workflow().init(quiet=True)
            barrier.wait(timeout=10)
            class Start(Command):
                def execute(self):
                    self.get_transaction().set_sync(False)
                    Trigger.call(self, 'process|pending', {'sobject': Search.get_by_code('contract/dep_parent', code),
                        'pipeline': Pipeline.get_by_code('DEP_SHARED'), 'process': 'start', 'data': {'code': code}})
            Command.execute_cmd(Start())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(start, code) for code in ('CONCURRENT_A', 'CONCURRENT_B')]
        for future in futures:
            future.result(timeout=20)
    with request_context(RequestContext(store, 'admin', 'one')):
        api.auth.bind_security('admin', ticket)
        Workflow().init(quiet=True)
        class Finish(Command):
            def execute(self):
                self.get_transaction().set_sync(False)
                child_task = Search.get_by_search_key(task)
                child_task.set_value('status', 'Complete')
                child_task.commit()
        Command.execute_cmd(Finish())
        from pyasm.command.workflow import BaseProcessTrigger
        handler = BaseProcessTrigger()
        handler.input = {}
        return [handler.get_process_status(Search.get_by_code('contract/dep_parent', code), 'done')
                for code in ('CONCURRENT_A', 'CONCURRENT_B')]


class Dependencies(read_tests.ReadParity):
    filter_test_search_type = 'contract/dep_child'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract as contract
        with cls.store.connection(write=True) as db:
            contract.install_fixture(db)
        cls.cases = [dict(method='dependency_contract', name=code, graph=code, project='one') for code in contract.CASES]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        code = case['graph']
        self.assertEqual(result['before'][code]['states']['start'], 'complete' if code in ('NOWAIT', 'EMPTY', 'READY') else 'in_progress')
        if code == 'WAIT':
            self.assertEqual(result['middle'][code]['states']['start'], 'in_progress')
        self.assertEqual(result['after'][code]['states']['start'], 'revise' if code == 'REVISE' else 'complete')
        if code == 'V1':
            self.assertEqual(original, {'error': 'AttributeError', 'message': "'NoneType' object has no attribute 'startswith'"})
        elif code in ('EMPTY', 'READY'):
            self.assertEqual(original['after'][code]['states'], {'start': 'in_progress'})
        elif code == 'NOWAIT':
            for moment in ('before', 'middle', 'after'):
                self.assertEqual(result[moment][code]['notes'], original[moment][code]['notes'])
                self.assertEqual(result[moment]['NOWAIT_1']['tasks'], original[moment]['NOWAIT_1']['tasks'])
        else:
            # The source cache aliases the caller/child state and loses the normal callbacks.
            self.assertEqual(original['before'][code]['states'], {'start': 'complete'})
            self.assertEqual(original['before'][code]['notes'], [['start', 'action', {'value': 7}]])
            if code == 'SHARED':
                self.assertEqual(original['after']['SHARED_OTHER']['states'], {'start': 'in_progress'})
                self.assertEqual(result['after']['SHARED_OTHER']['states']['done'], 'complete')
                self.assertEqual(result['after']['SHARED_OTHER']['notes'][1], ['start', 'complete', {'value': 8}])
        if code != 'REVISE':
            self.assertEqual(result['after'][code]['states']['__PIPELINE__'], 'complete')
            self.assertEqual(result['after'][code]['notes'], [['start', 'action', {'value': 7}],
                ['start', 'complete', {'value': 7}], ['done', 'action', {'value': 7}], ['done', 'complete', {'value': 7}]])
        else:
            self.assertEqual(original['after']['REVISE_1']['tasks'], [['work', 'Complete']])
            self.assertEqual(result['after']['REVISE_1']['tasks'], [['work', 'Revise']])
            self.assertEqual(result['after'][code]['states']['__PIPELINE__'], 'in_progress')

    def test_late_dependency_failure_rolls_back_completion_and_waiters(self):
        import dependency_contract as contract
        from pyasm.command import Command
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                Command.execute_cmd(contract.Begin('WAIT'))
                Command.execute_cmd(contract.Finish('WAIT', 1))
                tables = ('task', 'spt_process', 'spt_process_state', 'note', 'message', 'status_log', 'transaction_log')
                def records():
                    with store.connection() as db:
                        return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')] for table in tables}
                before = records()
                with self.assertRaisesRegex(ValueError, 'late dependency failure'):
                    Command.execute_cmd(contract.Finish('WAIT', 2, fail=True))
                self.assertEqual(records(), before)
                Command.execute_cmd(contract.Finish('WAIT', 2))

    def test_simultaneous_callers_are_both_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            self.assertEqual(concurrent_waiters(store, 'private-test-password'), ['complete', 'complete'])

    def test_cyclic_dependencies_fail_explicitly(self):
        import dependency_contract as contract
        from pyasm.biz import Pipeline
        from pyasm.command import Command, Trigger, Workflow
        from pyasm.command.workflow import WorkflowException
        from pyasm.search import Search
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                class Invalid(Command):
                    def __init__(self, same):
                        super().__init__()
                        self.same = same
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        pipeline = Pipeline.get_by_code('DEP_WAIT')
                        definition = pipeline.get_process_sobject('start')
                        expression = "@SOBJECT(contract/dep_parent['code','%s'])" % ('WAIT' if self.same else 'SHARED_OTHER')
                        definition.set_value('workflow', {'version': 2, 'default': {'related_search_type': expression, 'related_scope': 'global', 'related_process': 'start', 'related_wait': True}})
                        definition.commit()
                        if not self.same:
                            reverse = Pipeline.get_by_code('DEP_SHARED').get_process_sobject('start')
                            reverse.set_value('workflow', {'version': 2, 'default': {'related_search_type': "@SOBJECT(contract/dep_parent['code','WAIT'])", 'related_scope': 'global', 'related_process': 'start', 'related_wait': True}})
                            reverse.commit()
                        Workflow().init(quiet=True)
                        Trigger.call(self, 'process|pending', {'sobject': Search.get_by_code('contract/dep_parent', 'WAIT'), 'pipeline': pipeline, 'process': 'start'})
                for same, error in ((True, WorkflowException), (False, WorkflowException)):
                    with self.subTest(same=same), self.assertRaises(error):
                        Command.execute_cmd(Invalid(same))
                    self.assertEqual(Search('config/process_state').get_count(), 0)
