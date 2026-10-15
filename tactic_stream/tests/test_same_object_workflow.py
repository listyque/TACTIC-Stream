import shutil
import sys
import tempfile
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case

class SameObject(read_tests.ReadParity):
    filter_test_search_type = 'contract/dep_parent'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import dependency_contract, same_object_contract
        with cls.store.connection(write=True) as db:
            dependency_contract.install_fixture(db)
            same_object_contract.install_fixture(db)
        cls.cases = [dict(method='same_object_contract', name='two alternate pipelines', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(original['error'], 'RecursionError')  # Source completion/listener calls recurse on the shared state.
        self.assertEqual(result['error'], '')
        self.assertNotIn('SAME_ALT1::work', original['states'])
        self.assertNotIn('SAME_ALT2::work', original['states'])
        self.assertNotIn('work', result['states'])
        self.assertEqual(result['states']['start'], 'in_progress')
        self.assertEqual(result['states']['start2'], 'in_progress')
        self.assertEqual(result['states']['SAME_ALT1::work'], 'pending')
        self.assertEqual(result['states']['SAME_ALT2::work'], 'pending')
        self.assertEqual(result['tasks'], [['SAME_ALT1::work', 'Pending'], ['SAME_ALT2::work', 'Pending'], ['work', 'Pending']])

    def test_fresh_requests_completion_and_rollback(self):
        import same_object_contract as contract
        from pyasm.search import Search, SearchType
        from pyasm.command import Command
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            def request(operation):
                with request_context(RequestContext(store, 'admin', 'one')):
                    Api(store).auth.bind_security('admin', self.ticket)
                    return operation()
            class LegacyState(Command):
                def execute(self):
                    self.get_transaction().set_sync(False)
                    state = SearchType.create('config/process_state')
                    state.set_sobject_value(Search.get_by_code('contract/dep_parent', 'SAME'))
                    state.set_value('process', 'work')
                    state.set_value('status', 'pending')
                    state.commit()
                    return state.get_search_key()
            legacy_key = request(lambda: Command.execute_cmd(LegacyState()))
            request(lambda: contract.run({}))
            def check_packages():
                from pyasm.biz import Pipeline
                from pyasm.command.workflow import WorkflowManualNodeHandler
                obj = Search.get_by_code('contract/dep_parent', 'SAME')
                for code, value in (('SAME_ALT1', 7), ('SAME_ALT2', 8)):
                    handler = WorkflowManualNodeHandler(input={'sobject': obj, 'pipeline': Pipeline.get_by_code(code), 'process': 'work'})
                    state = handler.retrieve_state()
                    self.assertEqual(state['data'], {'value': value})
                    self.assertEqual(state['packages']['test'], {'value': value})
            request(check_packages)
            middle = request(lambda: contract.finish('SAME_ALT1::work'))
            self.assertEqual(middle['states']['start'], 'complete')
            self.assertEqual(middle['states']['start2'], 'in_progress')
            self.assertNotIn('done', middle['states'])
            second = request(lambda: contract.finish('SAME_ALT2::work'))
            self.assertEqual(second['states']['start2'], 'complete')
            self.assertEqual(second['states']['work'], 'pending')
            def records():
                with store.connection() as db:
                    return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY id')]
                        for table in ('spt_process', 'spt_process_state', 'task', 'message', 'note', 'transaction_log')}
            before = records()
            with self.assertRaisesRegex(ValueError, 'late same-object failure'):
                request(lambda: contract.finish('work', fail=True))
            self.assertEqual(records(), before)
            final = request(lambda: contract.finish('work'))
            self.assertEqual(final['states']['done'], 'complete')
            self.assertEqual(final['states']['__PIPELINE__'], 'complete')
            self.assertEqual(final['states']['SAME_ALT1::__PIPELINE__'], 'complete')
            self.assertEqual(final['states']['SAME_ALT2::__PIPELINE__'], 'complete')
            self.assertIn(['SAME_MAIN', 'start', 'complete', {'value': 7}], final['notes'])
            self.assertIn(['SAME_MAIN', 'start2', 'complete', {'value': 8}], final['notes'])
            with request_context(RequestContext(store, 'admin', 'one')):
                states = Search('config/process_state')
                states.add_filter('process', 'SAME_ALT1::work')
                self.assertEqual(states.get_sobject().get_value('pipeline_code'), 'SAME_ALT1')
                self.assertEqual(Search.get_by_search_key(legacy_key).get_value('pipeline_code'), 'SAME_MAIN')

    def test_alternate_hierarchy_routes_task_to_its_root(self):
        import same_object_contract as contract
        from pyasm.biz import Pipeline
        from pyasm.command import Command
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                class Hierarchy(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        Pipeline.create('Same child', '', 'contract/dep_parent',
                            '<pipeline><process name="work" type="manual"/><process name="exit" type="output"/><connect from="work" to="exit"/></pipeline>', code='SAME_CHILD')
                        pipeline = Pipeline.get_by_code('SAME_ALT1')
                        definition = pipeline.get_process_sobject('work')
                        definition.set_value('process', 'gate')
                        definition.set_value('subpipeline_code', 'SAME_CHILD')
                        definition.set_json_value('workflow', {'version': 2, 'default': {'subpipeline': 'SAME_CHILD', 'task_creation': 'subtasks_only'}})
                        definition.commit()
                        pipeline.set_value('pipeline', '<pipeline><process name="gate" type="hierarchy"/><process name="done" type="action"/><connect from="gate" to="done"/></pipeline>')
                        pipeline.commit()
                        caller = Pipeline.get_by_code('SAME_MAIN').get_process_sobject('start')
                        workflow = caller.get_json_value('workflow')
                        workflow['default']['related_process'] = 'gate'
                        caller.set_json_value('workflow', workflow)
                        caller.commit()
                Command.execute_cmd(Hierarchy())
                result = contract.run({})
                self.assertEqual(result['error'], '')
                self.assertIn(['SAME_ALT1::gate/work', 'Pending'], result['tasks'])
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                result = contract.finish('SAME_ALT1::gate/work')
                self.assertEqual(result['states']['SAME_ALT1::gate/work'], 'complete')
                self.assertEqual(result['states']['SAME_ALT1::done'], 'complete')
                self.assertEqual(result['states']['start'], 'complete')
                self.assertEqual(result['states']['start2'], 'in_progress')
