"""Replay the native adoption of pre-existing unowned Workflow states."""
from functools import partial

import test_plugin_installation as plugin_tests
from test_user_cross_project_workflow import exercise, UserCrossProjectTransport
from test_user_cross_project_undo import CrossProjectUndoParity
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context


class UserPipelineAdoption(plugin_tests.PluginInstallation):
    exercise = staticmethod(partial(exercise, replay=True, adoption=True))


class UserPipelineAdoptionTransport(UserCrossProjectTransport):
    exercise = staticmethod(partial(exercise, replay=True, adoption=True))


class PipelineAdoptionParity(CrossProjectUndoParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with request_context(RequestContext(cls.store, 'admin', 'one')):
            cls.api.auth.bind_security('admin', cls.ticket)
            command = Command(log_exception=False)
            command.get_transaction().set_sync(False)
            def setup():
                parent = Search.get_by_code('contract/entity', 'A')
                parent.set_value('pipeline_code', 'LOOKUP_one'); parent.commit(triggers='none')
                state = SearchType.create('config/process_state')
                state.set_sobject_value(parent)
                state.set_value('code', 'LEGACY_WORK')
                state.set_value('process', 'work')
                state.set_value('status', 'unknown')
                state.set_value('state', '{"preserved":"legacy"}')
                state.commit(triggers='none')
            command.execute = setup; Command.execute_cmd(command)
        cls.cases = [dict(cls.cases[0], name='Legacy process-state pipeline adoption', adoption=True)]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['after'], result['redone'])
        row = result['after']['one'][0]
        self.assertEqual(row['pipeline'], 'LOOKUP_one')
        self.assertEqual(result['undone']['one'], [dict(row, pipeline='', status='unknown')])
        self.assertEqual(row['state'], '{"preserved":"legacy"}')
        self.assertEqual(result['undone']['messages'], [])
        self.assertEqual(original['after']['one'][0]['pipeline'], '')
        self.assertEqual(original['after']['one'][0]['state'], row['state'])
        self.assertEqual(original['undone']['messages'], original['after']['messages'])
