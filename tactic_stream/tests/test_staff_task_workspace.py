"""Ordinary staff use Task Manager through native permissions and transactions."""
import unittest
import os

from pyasm.common.errors import SecurityException
from pyasm.search import Search
import test_table_services as fixture
from test_project_writes import install_writer, set_rules, PASSWORD


READ = 'task_workspace.TaskWorkspaceCmd'
EDIT = 'task_workspace_edits.TaskWorkspaceEditCmd'


class StaffTaskWorkspace(unittest.TestCase):
    setUp = fixture.TableServices.setUp

    @unittest.skipUnless(os.environ.get('RUN_STAFF_BROWSER'), 'Explicit browser integration run')
    def test_staff_browser(self):
        from pathlib import Path
        import shutil
        import subprocess
        from types import SimpleNamespace
        from test_file_transfer import FileTransferTest
        self.prepare_staff('view', 'view')
        self.temp = SimpleNamespace(name=str(self.store.data_dir.parent))
        self.database_config = None
        root = Path(__file__).parents[1]
        with FileTransferTest.http(self) as url:
            for access in ('view', 'edit'):
                with self.subTest(access=access):
                    self.policy(access, access)
                    result = subprocess.run([shutil.which('node'), 'tests/task_staff.mjs', url, access],
                        cwd=root / 'frontend', env=dict(os.environ, STAFF_PASSWORD=PASSWORD,
                            PLAYWRIGHT_BROWSERS_PATH=str(root / '.browser-cache')),
                        text=True, encoding='utf-8', capture_output=True, timeout=120)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def prepare_staff(self, access='edit', parent_access='edit', extra=''):
        self.api.protocol = 'json'
        install_writer(self.store)
        self.admin = dict(ticket=self.api.get_ticket('admin', 'service-cell-fixture'), project='one')
        self.tasks = [self.api.dispatch('create_task', (self.admin, 'contract/entity?project=one&code=' + code),
            dict(process='publish', assigned='project_writer', description='Task ' + code)) for code in ('A', 'B')]
        self.policy(access, parent_access, extra)
        self.staff = dict(ticket=self.api.get_ticket('project_writer', PASSWORD), project='one')

    def policy(self, access='edit', parent_access='edit', extra=''):
        set_rules(self.store, '<rules><rule group="project" code="one" access="allow"/>'
            '<rule group="search_type" code="sthpw/task" project="one" access="%s"/>'
            '<rule group="search_type" code="contract/entity" project="one" access="%s"/>'
            '<rule group="process" process="*" project="one" access="allow"/>%s</rules>'
            % (access, parent_access, extra))

    def command(self, command=READ, auth=None, **values):
        return self.api.dispatch('execute_cmd', (auth or self.staff, 'tactic.ui.table.' + command, values))['info']

    def draft(self, index=0, **values):
        return dict(search_key='contract/entity?project=one&code=' + ('A', 'B')[index],
                    task_key=self.tasks[index]['__search_key__'], process='publish', **values)

    def test_reader_gets_own_task_page_calendar_and_readonly_fields(self):
        self.prepare_staff('view', 'view')
        page = self.command(scope='user', identity='project_writer')
        self.assertEqual({task['code'] for task in page['tasks']}, {task['code'] for task in self.tasks})
        self.assertEqual(page['total'], 2)
        catalog = self.command(action='catalog')
        self.assertFalse(catalog['permissions']['create'])
        plan = self.command(EDIT, action='prepare', plans=[self.draft()])['plans'][0]
        self.assertFalse(any(field['editable'] for field in plan['fields']))
        with self.assertRaises(SecurityException):
            self.command(EDIT, action='save', plans=[dict(plan, data=dict(description='Forbidden'))])
        projected = self.command('task_schedule.TaskScheduleCmd', records=[], year=2030, month=1)
        self.assertIn('calendar', projected)

    def test_editor_saves_and_fresh_permissions_reject_revoked_access(self):
        self.prepare_staff()
        plan = self.command(EDIT, action='prepare', plans=[self.draft()])['plans'][0]
        self.command(EDIT, action='save', plans=[dict(plan, data=dict(description='Edited by staff'))])
        saved = self.command(EDIT, action='prepare', plans=[self.draft()])['plans'][0]
        self.assertEqual(saved['task']['description'], 'Edited by staff')
        self.policy('view', 'view')
        with self.assertRaises(SecurityException):
            self.command(EDIT, action='save', plans=[dict(saved, data=dict(description='Stale grant'))])
        with self.assertRaises(Exception):
            self.command(EDIT, action='prepare', plans=[dict(operation='create', draft_id='denied',
                search_key='contract/entity?project=one&code=A', process='publish')])

    def test_hidden_parent_is_removed_before_page_counts_and_facets(self):
        self.prepare_staff(extra='<rule group="search_filter" search_type="contract/entity" column="code" value="A"/>')
        page = self.command(scope='project', query={'filters': {}, 'quickFilters': {}})
        self.assertEqual([task['code'] for task in page['tasks']], [self.tasks[0]['code']])
        self.assertEqual(page['total'], 1)
        self.assertEqual(sum(row['count'] for row in page['facets']['assigned']), 1)
        with self.assertRaises(LookupError):
            self.command(EDIT, action='prepare', plans=[self.draft(1)])

    def test_project_and_process_denies_cannot_be_bypassed(self):
        self.prepare_staff()
        with self.assertRaises(SecurityException):
            self.command(auth=dict(self.staff, project='two'), scope='project')
        with self.assertRaises(ValueError):
            self.command(scope='object', identity='contract/entity?project=two&code=A')
        self.policy(extra='<rule group="process" process="publish" project="one" access="deny"/>')
        page = self.command(scope='project')
        self.assertEqual(page['total'], 0)
        with self.assertRaises(SecurityException):
            self.command(EDIT, action='prepare', plans=[self.draft()])

    def test_readonly_column_is_not_editable_or_returned(self):
        self.prepare_staff(extra='<rule group="sobject_column" search_type="sthpw/task" column="description" project="one" access="deny"/>')
        page = self.command(scope='project')
        self.assertTrue(all('description' not in row for row in page['tasks']))
        plan = self.command(EDIT, action='prepare', plans=[self.draft()])['plans'][0]
        self.assertNotIn('description', plan['task'])
        with self.assertRaises(Exception):
            self.command(EDIT, action='save', plans=[dict(plan, data=dict(description='Forbidden'))])

    def test_inspector_does_not_disclose_denied_assignee(self):
        self.prepare_staff(extra='<rule group="sobject_column" search_type="sthpw/task" column="assigned" project="one" access="deny"/>')
        detail = self.command('task_inspector.TaskInspectorCmd', **self.draft())
        self.assertNotIn('assigned', detail['task'])
        self.assertNotIn('assigned', detail['defaults'])
        self.assertTrue(all(choice['identity'] is None and 'project_writer' not in choice['label']
                            for choice in detail['task_choices']))

    def test_staff_filters_sort_and_shared_page_use_native_read_paths(self):
        self.prepare_staff()
        self.api.dispatch('create_note', (self.admin, self.draft()['search_key'], 'Visible note'))
        page = self.command(scope='project', query=dict(filters=dict(hasNotes=True), sort='user'))
        self.assertEqual([row['code'] for row in page['tasks']], [self.tasks[0]['code']])
        shared = self.command(action='page', project_code='one', filters=[('assigned', 'project_writer')],
                              order_bys=['timestamp desc'], limit=50, query={'sort': 'object'})
        self.assertEqual(shared['total'], 2)
        self.assertTrue(all(row['__permissions__']['edit'] for row in shared['tasks']))
        with self.assertRaises(ValueError):
            self.command(action='page', project_code='two', filters=[], order_bys=[])
        with self.assertRaises(ValueError):
            self.command(action='page', project_code='one', filters=['or'], order_bys=[])

    def test_staff_can_create_project_owned_tasks_without_editing_project_records(self):
        self.prepare_staff('insert')
        plan = self.command(EDIT, action='prepare', plans=[dict(operation='create', draft_id='project-task',
            search_key='', process='task')])['plans'][0]
        saved = self.command(EDIT, action='save', plans=[dict(plan, data={'description': 'Standalone staff task'})])
        self.assertTrue(saved['tasks'][0]['task_key'])
        page = self.command(scope='project')
        self.assertTrue(any(row.get('description') == 'Standalone staff task' for row in page['tasks']))
        with self.assertRaises(SecurityException):
            self.api.dispatch('update', (self.staff, 'sthpw/project?code=one', dict(description='Not a task write')))

    def test_hidden_assignee_cannot_leak_through_facets(self):
        self.prepare_staff(extra='<rule group="sobject_column" search_type="sthpw/task" column="assigned" project="one" access="deny"/>')
        page = self.command(scope='project')
        self.assertEqual(page['facets']['assigned'], [])
        self.assertTrue(all('assigned' not in row for row in page['tasks']))
        with self.assertRaises(SecurityException):
            self.command(scope='project', query={'filters': {'assigned': 'project_writer'}})


if __name__ == '__main__':
    unittest.main()
