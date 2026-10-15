"""Native submit options preserve publication atomicity and private review metadata."""
import unittest
import ast
from unittest.mock import patch

from pyasm.biz.file_project import FileProjectRecord
from test_file_project import FileProjectFixture
import test_file_project_resilience as resilience


class FileSubmitTest(FileProjectFixture, unittest.TestCase):
    writer = resilience.FileProjectResilience.writer
    client = resilience.FileProjectResilience.client

    def opened(self):
        change = self.call('create_change', workspace='work')
        blob = self.upload(change['code'])
        self.call('edit', change=change['code'], edit_revision=0, chunk='seed', operations=[
            {'path': name, 'blob': blob} for name in ('a.txt', 'b.txt')])
        return change['code']

    def test_selected_submit_leaves_other_files_and_reopens_atomically(self):
        change = self.opened()
        result = self.call('submit', change=change, edit_revision=1, description='Selected publish', submit_options={
            'selection_all': False, 'selection_paths': ['a.txt'], 'reopen': True, 'unchanged': 'revert'})
        self.assertEqual([row['path'] for row in self.call('list', stream='main')['items']], ['a.txt'])
        pending = self.call('change_files', change=result['pending_change'])
        self.assertEqual({row['path'] for row in pending['items']}, {'a.txt', 'b.txt'})
        self.assertEqual(pending['info']['base_revision'], 1)
        self.assertEqual(self.call('inspect_change', change=change)['description'], 'Selected publish')
        self.assertEqual(self.call('change_files', change=change)['files'], 1)

    def test_submit_trigger_failure_rolls_back_selection_split_and_description(self):
        change = self.opened()
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data').get('state') == 'submitted':
                raise ValueError('submit failed')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', fail), self.assertRaisesRegex(ValueError, 'submit failed'):
            self.call('submit', change=change, edit_revision=1, description='Must roll back', submit_options={'selection_all': False, 'selection_paths': ['a.txt']})
        self.assertEqual(self.call('list', stream='main')['items'], [])
        self.assertEqual(self.call('change_files', change=change)['files'], 2)
        self.assertEqual(len(self.call('changes', state='pending')['items']), 1)
        self.assertEqual(self.call('status', change=change)['description'], '')

    def test_restricted_metadata_hidden_but_depot_files_still_readable(self):
        from pyasm.common.errors import SecurityException
        change = self.opened()
        self.call('submit', change=change, edit_revision=1, description='Private details', restricted=True)
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist, 'inspect_change', change=change)
        self.assertEqual(len(self.client(artist, 'list', stream='main')['items']), 2)
        self.assertNotIn(change, [row['code'] for row in self.client(artist, 'changes', scope='all', state='submitted')['items']])
        self.assertEqual(self.client(artist, 'history', stream='main', path='a.txt')['items'][0]['description'], '')
        self.assertEqual(self.client(artist, 'file_info', stream='main', path='a.txt')['description'], '')
        self.assertIsNone(self.client(artist, 'history', stream='main', path='a.txt')['items'][0]['workspace'])
        self.assertEqual(self.call('history',stream='main',path='a.txt')['items'][0]['workspace'],'work')

    def test_unchanged_policy_and_linked_shelves(self):
        change = self.opened(); self.call('submit', change=change)
        second = self.call('create_change', workspace='work')['code']
        self.call('checkout', change=second, paths=['a.txt', 'b.txt'])
        shelf = self.call('shelve', change=second, edit_revision=1, request_id='shelf')
        self.assertEqual(self.call('submit_shelves', change=second)['items'][0]['code'], shelf['code'])
        with self.assertRaisesRegex(ValueError, 'No files selected'):
            self.call('submit', change=second, edit_revision=1, submit_options={'unchanged': 'revert'})
        self.assertEqual(self.call('change_files', change=second)['files'], 2)
        self.assertEqual(self.call('submit_tasks', change=second)['items'], [])

    def test_linked_task_statuses_follow_successful_submit_and_retry_without_overwrite(self):
        change = self.opened()
        task = self.api.dispatch('insert', ({'ticket': self.token, 'project': 'files'}, 'sthpw/task', {
            'project_code': 'files', 'search_type': 'sthpw/project',
            'search_code': 'files', 'process': 'publish', 'description': 'Submit task'}))
        page = self.call('submit_tasks', change=change)
        row = next(row for row in page['items'] if row['code'] == task['code'])
        self.assertTrue(row['statuses'])
        target = next(item['value'] for item in row['statuses'] if item['value'] != row['status'])
        update = {'code': row['code'], 'revision': row['revision'], 'status': target}
        from pyasm.common.errors import SecurityException
        with patch('tactic.ui.table.task_inspector.task_fields', return_value=[{'name': 'status', 'editable': False}]):
            hidden = self.call('submit_tasks', change=change)['items'][0]
            self.assertEqual(hidden['description'], '')
            self.assertEqual(hidden['statuses'], [])
            with self.assertRaisesRegex(SecurityException, 'read-only'):
                self.call('submit', change=change, edit_revision=1, task_codes=[row['code']], task_status_updates=[update])
        self.assertEqual(self.call('status', change=change)['state'], 'pending')
        self.call('submit', change=change, edit_revision=1, task_codes=[row['code']], task_status_updates=[update])
        # Inspect through the same native API; no system-DB status write occurred in publication.
        record = ast.literal_eval(self.api.dispatch('query', ({'ticket': self.token, 'project': 'files'}, 'sthpw/task', [('code', row['code'])])))[0]
        self.assertEqual(record['status'] or '', row['status'])
        with patch('tactic.ui.table.task_inspector.task_fields', return_value=[]), self.assertRaisesRegex(SecurityException, 'read-only'):
            self.call('submit_task_status', change=change)
        self.assertEqual(self.call('submit_task_status', change=change)['updated'], 1)
        self.assertEqual(self.call('submit_task_status', change=change)['updated'], 0)
        self.assertEqual(self.call('inspect_change', change=change)['task_codes'], [row['code']])

    def test_unchanged_submit_creates_version_and_leave_retains_pending(self):
        original = self.opened(); self.call('submit', change=original)
        change = self.call('create_change', workspace='work')['code']
        self.call('checkout', change=change, paths=['a.txt', 'b.txt'])
        before = self.call('file_info', stream='main', path='a.txt')['file']
        result = self.call('submit', change=change, edit_revision=1, submit_options={'unchanged': 'submit'})
        after = self.call('file_info', stream='main', path='a.txt')['file']
        self.assertNotEqual(before['version'], after['version'])
        self.assertEqual(before['sha256'], after['sha256'])
        self.assertIsNone(result['pending_change'])
        change = self.call('create_change', workspace='work')['code']
        self.call('checkout', change=change, paths=['a.txt', 'b.txt'])
        blob = self.upload(change, b'new contents')
        self.call('edit', change=change, edit_revision=1, chunk='edit', operations=[{'path': 'a.txt', 'blob': blob}])
        result = self.call('submit', change=change, edit_revision=2, submit_options={'unchanged': 'leave'})
        self.assertEqual([row['path'] for row in self.call('change_files', change=result['pending_change'])['items']], ['b.txt'])

    def test_new_selected_bytes_only_uploaded_and_published(self):
        from pathlib import Path
        from tactic_client_lib.file_transfer import FileTransferClient
        import test_file_transfer as transfers
        change = self.call('create_change', workspace='work')['code']
        self.call('checkout', change=change, paths=['selected.txt', 'private.txt'])
        root = Path(self.temp.name)/'local'; root.mkdir()
        (root/'selected.txt').write_bytes(b'publish this')
        (root/'private.txt').write_bytes(b'keep local')
        with transfers.FileTransferTest.http(self, worker=True) as url:
            client = FileTransferClient(url, self.token, 'files')
            snapshot = client.prepare_change(change, root, Path(self.temp.name)/'review.sqlite')
            self.assertFalse(client.rpc('transfer_tasks')['items'])
            options = {'selection_all': False, 'selection_paths': ['selected.txt']}
            client.configure_submit_review(snapshot, options)
            (root/'private.txt').write_bytes(b'local editing can continue')
            revision = client.upload_prepared_change(snapshot)
            result = client.submit(change, edit_revision=revision, submit_options=options)
            self.assertEqual([row['path'] for row in client.rpc('list', stream='main')['items']], ['selected.txt'])
            remaining = client.rpc('change_files', change=result['pending_change'])
            self.assertEqual(remaining['info']['waiting_uploads'], 1)
            self.assertFalse(remaining['items'][0].get('file'))
            self.assertEqual((root/'private.txt').read_bytes(), b'local editing can continue')

    def test_resolved_file_guard_rejects_later_edit(self):
        import test_file_change as changes
        helper = changes.FileChangeTest
        original = self.opened(); self.call('submit', change=original)
        ours = self.call('create_change', workspace='work')['code']
        theirs = self.call('create_change', workspace='work')['code']
        for change, content in ((ours, b'ours'), (theirs, b'theirs')):
            blob = self.upload(change, content)
            self.call('edit', change=change, edit_revision=0, chunk='edit', operations=[{'path': 'a.txt', 'blob': blob}])
        self.call('submit', change=theirs)
        job = helper.next(self, helper.start(self, ours))
        job = helper.resolve(self, job, [{'path': 'a.txt', 'choice': 'ours'}])
        helper.finish(self, job)
        blob = self.upload(ours, b'edited after resolving')
        helper.edit(self, ours, [{'path': 'a.txt', 'blob': blob}], chunk='after')
        with self.assertRaisesRegex(ValueError, 'resolved file changed'):
            self.call('submit', change=ours, submit_options={'guard_resolved': True})
        self.assertEqual(self.call('status', change=ours)['state'], 'pending')
        self.call('submit', change=ours, submit_options={'guard_resolved': False})

    def test_task_changed_after_publish_is_not_overwritten(self):
        change = self.opened()
        task = self.api.dispatch('insert', ({'ticket': self.token, 'project': 'files'}, 'sthpw/task', {
            'project_code': 'files', 'search_type': 'sthpw/project', 'search_code': 'files', 'process': 'publish'}))
        row = self.call('submit_tasks', change=change)['items'][0]
        target = next(item['value'] for item in row['statuses'] if item['value'] != row['status'])
        self.call('update_change', change=change, edit_revision=1, request_id='save',
                  task_codes=[row['code']], task_status_updates=[{'code': row['code'], 'revision': row['revision'], 'status': target}])
        self.assertEqual(self.call('submit_tasks', change=change)['linked'][0]['code'], row['code'])
        self.call('submit', change=change, edit_revision=2)
        self.api.dispatch('update', ({'ticket': self.token, 'project': 'files'}, task['__search_key__'], {'description': 'Someone edited the task'}))
        with self.assertRaisesRegex(ValueError, 'changed after review'):
            self.call('submit_task_status', change=change)
        self.assertEqual(self.call('status', change=change)['state'], 'submitted')
        self.assertEqual(self.call('list', stream='main')['files'], 2)

    def test_task_pages_keep_saved_links_outside_first_page(self):
        change = self.opened()
        self.api.dispatch('insert_multiple', ({'ticket': self.token, 'project': 'files'}, 'sthpw/task', [
            {'project_code': 'files', 'search_type': 'sthpw/project', 'search_code': 'files',
             'process': 'publish', 'description': 'Task %03d' % number} for number in range(101)]))
        first = self.call('submit_tasks', change=change)
        self.assertEqual(len(first['items']), 100)
        self.assertIsInstance(first['after'], str)
        last = self.call('submit_tasks', change=change, after=first['after'])
        self.assertEqual(len(last['items']), 1)
        code = last['items'][0]['code']
        self.call('update_change', change=change, edit_revision=1, request_id='link', task_codes=[code])
        refreshed = self.call('submit_tasks', change=change)
        self.assertNotIn(code, [row['code'] for row in refreshed['items']])
        self.assertEqual([row['code'] for row in refreshed['linked']], [code])

    def test_changelist_inspection_pages_shelves_tasks_and_restriction(self):
        from pyasm.common.errors import SecurityException
        change = self.opened()
        shelf = self.call('shelve', change=change, edit_revision=1, request_id='view-shelf')
        task = self.api.dispatch('insert', ({'ticket':self.token,'project':'files'},'sthpw/task', {
            'project_code':'files','search_type':'sthpw/project','search_code':'files','process':'publish','description':'Linked task'}))
        self.call('update_change', change=change, edit_revision=1, request_id='task', task_codes=[task['code']])
        detail = self.call('changelist_details', change=change)
        self.assertEqual(detail['files']['files'], 2)
        self.assertEqual(detail['shelf_files']['change'], shelf['code'])
        self.assertEqual(detail['tasks']['items'][0]['description'], 'Linked task')
        self.assertTrue(detail['info']['created_at'])
        blob = self.upload(change)
        self.call('edit',change=change,edit_revision=2,chunk='many',operations=[{'path':f'page/{i:03}.txt','blob':blob} for i in range(205)])
        first = self.call('changelist_details', change=change)
        self.assertEqual(len(first['files']['items']), 200)
        page = self.call('changelist_details',change=change,section='files',edit_revision=3,after=first['files']['after'])
        self.assertEqual(len(page['files']['items']), 7)
        self.assertNotIn('tasks',page)
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            self.call('changelist_details',change=change,section='files',edit_revision=2,after=first['files']['after'])
        self.call('submit', change=change)
        artist = self.writer()
        public = self.client(artist,'changelist_details',change=change)
        self.assertEqual(public['files']['files'],207)
        other = self.opened()
        self.call('update_change',change=other,edit_revision=1,request_id='private',restricted=True)
        self.call('submit',change=other)
        with self.assertRaises(SecurityException):
            self.client(artist,'changelist_details',change=other)
