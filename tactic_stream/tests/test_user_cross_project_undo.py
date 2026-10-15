"""Complete own Workflow journals spanning two physical project databases."""
from functools import partial
from pathlib import Path
import shutil
import tempfile

from test_user_cross_project_workflow import exercise, UserCrossProjectTransport
from test_user_cross_project_workflow import CrossProjectLookup
from test_project_writes import install_writer
import test_plugin_installation as plugin_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class UserCrossProjectUndo(plugin_tests.PluginInstallation):
    exercise = staticmethod(partial(exercise, replay=True))


class UserCrossProjectUndoTransport(UserCrossProjectTransport):
    exercise = staticmethod(partial(exercise, replay=True))


class CrossProjectUndoParity(CrossProjectLookup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_writer(cls.store)
        rules = ('<rules><rule group="project" code="one" access="allow"/>'
                 '<rule group="project" code="two" access="allow"/>'
                 '<rule group="search_type" code="contract/entity" access="allow"/></rules>')
        cls.cases = [dict(name='Cross-project Workflow replay', method='cross_project_undo_contract', project='one', rules=rules)]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['after'], result['redone'])
        self.assertEqual(result['undone'], dict(one=[], two=[], messages=[]))
        for project in ('one', 'two'):
            self.assertEqual(result['after'][project], [dict(parent='contract/entity?project=' + project, status='pending')])
        # Source routes both states to the caller's database and never backs up messages.
        self.assertEqual(original['after']['two'], [])
        self.assertEqual(len(original['after']['one']), 2)
        self.assertEqual(original['undone']['messages'], original['after']['messages'])
