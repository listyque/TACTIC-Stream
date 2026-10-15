"""Project tasks without artificial SObject parents in a real file project."""
import ast
import unittest
import os
from pathlib import Path
import subprocess
import shutil

from test_file_project import FileProjectFixture


class StandaloneTaskTests(FileProjectFixture, unittest.TestCase):
    def command(self, name, **values):
        return self.api.dispatch('execute_cmd', (self.ticket, 'tactic.ui.table.' + name, values))['info']

    @unittest.skipUnless(os.environ.get('RUN_STANDALONE_BROWSER'), 'Explicit browser integration run')
    def test_real_browser_creation(self):
        from test_file_transfer import FileTransferTest
        root = Path(__file__).parents[1]
        with FileTransferTest.http(self) as url:
            result = subprocess.run([shutil.which('node'), str(root / 'frontend/tests/project_tasks.mjs'), url],
                cwd=root / 'frontend', env=dict(os.environ, STANDALONE_TEST_TICKET=self.token),
                text=True, encoding='utf-8', capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_edit_inspect_and_link_to_file_changelist(self):
        name = 'task_workspace_edits.TaskWorkspaceEditCmd'
        plan = self.command(name, action='prepare', plans=[dict(operation='create',
            draft_id='standalone', search_key='', process='task')])['plans'][0]
        self.assertTrue(plan['statuses'])
        saved = self.command(name, action='save', plans=[dict(plan, data=dict(
            description='Fix file import', status=plan['statuses'][0], assigned='admin'))])['tasks'][0]
        request = dict(search_key='', task_key=saved['task_key'], process='task')
        plan = self.command(name, action='prepare', plans=[request])['plans'][0]
        self.command(name, action='save', plans=[dict(plan, data=dict(description='Fix depot import'))])
        task = ast.literal_eval(self.api.dispatch('query', (self.ticket, 'sthpw/task', [('code', saved['task_key'].split('code=')[-1])])))[0]
        self.assertEqual(task['project_code'], 'files')
        self.assertEqual(task['search_type'].split('?')[0], 'sthpw/project')
        self.assertEqual(task['search_code'], 'files')
        page = self.command('task_workspace.TaskWorkspaceCmd', scope='project')
        self.assertIn(task['code'], [row['code'] for row in page['tasks']])
        inspected = self.command('task_inspector.TaskInspectorCmd', search_key=saved['task_key'], process='task')
        self.assertEqual(inspected['selected_task'], saved['task_key'])
        self.assertEqual(inspected['task']['description'], 'Fix depot import')
        change = self.change()
        self.assertIn(task['code'], [row['code'] for row in self.call('submit_tasks', change=change)['items']])
        blob = self.upload(change)
        self.call('edit', change=change, edit_revision=0, chunk='seed', operations=[dict(path='a.txt', blob=blob)])
        self.call('submit', change=change, edit_revision=1, task_codes=[task['code']])
        self.assertEqual(self.call('inspect_change', change=change)['task_codes'], [task['code']])

    def test_stale_and_foreign_task_rejected(self):
        name = 'task_workspace_edits.TaskWorkspaceEditCmd'
        plan = self.command(name, action='prepare', plans=[dict(operation='create',
            draft_id='standalone', search_key='', process='task')])['plans'][0]
        saved = self.command(name, action='save', plans=[dict(plan, data=dict(description='Original'))])['tasks'][0]
        request = dict(search_key='', task_key=saved['task_key'], process='task')
        plan = self.command(name, action='prepare', plans=[request])['plans'][0]
        self.command(name, action='save', plans=[dict(plan, data=dict(description='Changed'))])
        with self.assertRaisesRegex(Exception, 'changed'):
            self.command(name, action='save', plans=[dict(plan, data=dict(description='Stale'))])
        foreign = dict(self.ticket, project='admin')
        with self.assertRaisesRegex(LookupError, 'does not belong'):
            self.api.dispatch('execute_cmd', (foreign, 'tactic.ui.table.' + name, dict(action='prepare', plans=[request])))
        with self.assertRaisesRegex(ValueError, 'another project'):
            self.api.dispatch('execute_cmd', (foreign, 'tactic.ui.table.task_inspector.TaskInspectorCmd',
                                             dict(search_key=saved['task_key'], process='task')))
