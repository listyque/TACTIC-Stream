import shutil
import tempfile
from pathlib import Path
import sys
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.engine_probe import run_engine_case


class EngineParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import engine_contract
        with cls.store.connection(write=True) as db:
            engine_contract.install_fixture(db)
        cls.cases = [dict(method='engine_contract', project='admin', name=code, graph=code)
                     for code in engine_contract.GRAPHS]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_engine_case(case)

    def assert_case_result(self, case, result, original):
        if case['graph'] == 'APPROVAL_FORK':
            self.assertEqual(original['after']['states']['join'], '')
            self.assertEqual(result['after']['states']['join'], 'complete')
            self.assertEqual(original['after']['states']['__PIPELINE__'], '')
            self.assertEqual(result['after']['states']['__PIPELINE__'], 'complete')
            self.assertEqual(result['after']['notes'], original['after']['notes'] + ['join|action'])
            original['after']['states']['join'] = 'complete'
            original['after']['states']['__PIPELINE__'] = 'complete'
            original['after']['notes'] += ['join|action']
        if case['graph'] == 'CUSTOM':
            self.assertIn('processes_obj', original['error'])
            self.assertEqual(original['after']['states'], {'start': 'Assignment', '__PIPELINE__': ''})
            self.assertEqual(original['after']['notes'], [])
            self.assertEqual(result, {'error': '', 'after': {
                'states': {'start': 'revise', '__PIPELINE__': ''},
                'notes': ['start|revise'], 'tasks': []}})
            return
        if case['graph'] == 'WAIT':
            self.assertEqual(original['before']['states']['__PIPELINE__'], 'complete')
            self.assertEqual(result['before']['states']['__PIPELINE__'], '')
            original['before']['states']['__PIPELINE__'] = ''
        elif case['graph'] == 'REJECT':
            for moment in ('before', 'after'):
                self.assertEqual(original[moment]['states']['__PIPELINE__'], 'complete')
                self.assertEqual(result[moment]['states']['__PIPELINE__'], '')
                original[moment]['states']['__PIPELINE__'] = ''
        super().assert_case_result(case, result, original)

    def test_atomic_graph_and_configuration_rollback_security_and_preflight(self):
        from pyasm.command import Command, Workflow, Trigger
        from pyasm.command.workflow import BaseProcessTrigger
        from pyasm.biz import Pipeline
        from pyasm.search import Search
        from pyasm.common.errors import UnsupportedContract, SecurityException
        from pyasm.security.authenticator import hash_password
        from tactic_stream.server.api import Api
        import engine_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-engine-check'))
            with store.connection(write=True) as db:
                engine_contract.install_fixture(db)
            api = Api(store)
            ticket = api.get_ticket('admin', 'private-engine-check')
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket)
                pipeline = Pipeline.get_by_code('ENGINE')
                parent = Search.get_by_code('contract/engine', 'ENGINE')
                definition = pipeline.get_process_sobject('start')
                callback_lookup = BaseProcessTrigger()
                self.assertEqual(callback_lookup.get_process_sobj(pipeline, 'start').get_value('code'), 'ENGINE_start')
                kinds = ('sthpw/task', 'sthpw/note', 'sthpw/message', 'sthpw/message_log', 'config/process_state',
                         'sthpw/status_log', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                original_workflow = definition.get_value('workflow')
                class Fail(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        definition.set_value('workflow', {'on_action': "raise ValueError('engine failed')"})
                        definition.commit()
                        Workflow().init(quiet=True)
                        Trigger.call(self, 'process|pending', {'pipeline': pipeline, 'sobject': parent, 'process': 'start'})
                with self.assertRaisesRegex(ValueError, 'engine failed'):
                    Command.execute_cmd(Fail())
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                self.assertEqual(pipeline.get_process_sobject('start').get_value('workflow'), original_workflow)
                self.assertEqual(callback_lookup.get_process_sobj(pipeline, 'start').get_value('workflow'), original_workflow)
                manual_pipeline = Pipeline.get_by_code('MANUAL_COMPLETE')
                manual_parent = Search.get_by_code('contract/engine', 'MANUAL_COMPLETE')
                class FailManual(Command):
                    def execute(self):
                        from pyasm.biz import Task
                        self.get_transaction().set_sync(False)
                        done = manual_pipeline.get_process_sobject('done')
                        done.set_value('workflow', {'on_action': "raise ValueError('manual failed')"})
                        done.commit()
                        first = Task.create(manual_parent, 'start', status='Pending', triggers='none')
                        second = Task.create(manual_parent, 'start', status='Pending', triggers='none')
                        Workflow().init(quiet=True)
                        Trigger.call(self, 'process|pending', {'pipeline': manual_pipeline, 'sobject': manual_parent, 'process': 'start'})
                        first.set_value('status', 'Complete')
                        first.commit()
                        self_outer.assertEqual(engine_contract.snapshot(manual_parent, manual_pipeline)['states']['done'], '')
                        second.set_value('status', 'Complete')
                        second.commit()
                self_outer = self
                with self.assertRaisesRegex(ValueError, 'manual failed'):
                    Command.execute_cmd(FailManual())
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                for graph in ('<pipeline><process name="a" type="action"/><connect from="a" to="a"/></pipeline>',
                              '<pipeline><process name="a" type="unported"/></pipeline>'):
                    pipeline.set_pipeline(graph, cache=False)
                    class Unsupported(Command):
                        def execute(self):
                            self.get_transaction().set_sync(False)
                            Trigger.call(self, 'process|pending', {'pipeline': pipeline, 'sobject': parent, 'process': 'a'})
                    with self.assertRaises(UnsupportedContract):
                        Command.execute_cmd(Unsupported())
                    self.assertEqual([Search(kind).get_count() for kind in kinds], before)
            admin = {'ticket': ticket, 'project': 'admin'}
            api.dispatch('insert', (admin, 'sthpw/login', {'login': 'reader', 'password': hash_password('private-reader-check')}))
            reader = api.get_ticket('reader', 'private-reader-check')
            with self.assertRaises(SecurityException):
                api.dispatch('insert', ({'ticket': reader, 'project': 'admin'}, 'config/process', {'process': 'forbidden'}))
