import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.workflow_probe import run_workflow_case


class WorkflowParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.store.connection(write=True) as db:
            # Original registry reads config/pipeline while resolving task templates.
            db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
        cls.cases = [dict(method='workflow_contract', project='admin', name='state_and_inputs'),
                     dict(method='workflow_contract', project='admin', name='internal_failure', internal_failure=True),
                     dict(method='api_body', project='admin', name='log_message_return', call='log_message',
                          args=['workflow|literal', {'name': 'Данные'}])]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            if case['method'] == 'api_body':
                from tactic_stream.server.api import Api
                api = Api(store)
                return api.dispatch(case['call'], ({'ticket': self.ticket, 'project': 'admin'}, *case['args']))
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_workflow_case(case)

    def assert_case_result(self, case, result, original):
        if case['method'] == 'api_body':
            self.assertIsNone(original)
            self.assertEqual(result, 'OK')
            return
        if case.get('internal_failure'):
            self.assertEqual(original, {'internal': True})
            self.assertEqual(result, {'internal': None})
            return
        self.assertEqual(original['state'], {'error': 'TypeError'})
        self.assertEqual(result['state'], result['restored'])
        original['state'] = result['state']
        self.assertFalse(original['missing_manual'])
        self.assertTrue(result['missing_manual'])
        original['missing_manual'] = result['missing_manual']
        self.assertIn('error', original['roundtrip'])
        self.assertTrue(result['roundtrip'])
        original['roundtrip'] = result['roundtrip']
        super().assert_case_result(case, result, original)
        self.assertEqual(result['checks'], [True, False, True])
        self.assertEqual(result['filters'], [2, 2])
        self.assertEqual(result['status_log'], [['', 'pending'], ['pending', 'complete'], ['', 'not_required']])

    def test_atomic_state_rollback_security_and_unported_handlers(self):
        from pyasm.biz import Project, Pipeline
        from pyasm.command import Command, Workflow, BaseWorkflowNodeHandler
        from pyasm.common.errors import SecurityException, UnsupportedContract
        from pyasm.search import Search
        from pyasm.security.authenticator import hash_password
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-state-password'))
            api = Api(store)
            admin = {'ticket': api.get_ticket('admin', 'private-state-password'), 'project': 'admin'}
            api.dispatch('insert', (admin, 'sthpw/login', {'login': 'reader', 'password': hash_password('private-reader-password')}))
            reader = {'ticket': api.get_ticket('reader', 'private-reader-password'), 'project': 'admin'}
            with self.assertRaises(SecurityException):
                api.dispatch('log_message', (reader, 'forbidden', 'payload'))
            with self.assertRaises(SecurityException):
                api.dispatch('insert', (reader, 'config/process_state', {'process': 'forbidden'}))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', admin['ticket'])
                parent = Project.get()
                handler = BaseWorkflowNodeHandler(input={'sobject': parent, 'pipeline': Pipeline.get_by_code('task'), 'process': 'design', 'data': {'value': 1}})
                kinds = ('sthpw/message', 'sthpw/message_log', 'config/process_state', 'sthpw/status_log',
                         'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                Workflow().init(startup=True, quiet=True)
                from pyasm.command import Trigger
                count = len(Trigger.STATIC_TRIGGERS)
                Workflow().init(startup=True, quiet=True)
                self.assertEqual(len(Trigger.STATIC_TRIGGERS), count)
                with self.assertRaises(UnsupportedContract):
                    from pyasm.command.workflow import WorkflowHierarchyNodeHandler
                    WorkflowHierarchyNodeHandler(input=handler.input).handle_complete()
                class Failed(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        handler.log_message(parent, 'design', 'pending')
                        handler.store_state()
                        raise ValueError('failed state command')
                with self.assertRaisesRegex(ValueError, 'failed state command'):
                    Command.execute_cmd(Failed())
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                class Create(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        return handler.get_process_state(parent, 'design')
                state = Command.execute_cmd(Create())
                self.assertFalse(state.get_value('status'))
                self.assertEqual(Search('config/process_state').get_count(), 1)
            self.assertEqual(api.dispatch('get_message', (admin, 'forbidden')), {})
