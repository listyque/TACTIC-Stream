"""Native changelist API: snapshots, bounded integration, permissions and rollback."""
import base64
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import FileProjectRecord, access, find, save
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from tactic_stream.server.api import Api
from pyasm.search.storage import Store
from pyasm.command import Trigger
from test_file_project import FileProjectFixture
import test_file_project_resilience as resilience


class CatalogVisibility(Trigger):
    fail = False

    def execute(self):
        staged = self.get_caller().get_json_value('data').get('integration')
        if staged:
            for key in ('root', 'work_root', 'conflicts_root', 'acquired_root'):
                find('page', staged[key])
            if staged['complete'] and self.fail:
                raise ValueError('last chunk failure')


class FileChangeTest(FileProjectFixture, unittest.TestCase):
    client = resilience.FileProjectResilience.client
    race = resilience.FileProjectResilience.race
    writer = resilience.FileProjectResilience.writer

    def edit(self, change, operations, chunk='edit'):
        return self.call('edit', change=change, chunk=chunk,
                         edit_revision=self.call('status', change=change)['edit_revision'], operations=operations)

    def start(self, change, kind='rebase', **kwargs):
        return self.call(kind + '_begin', change=change, request_id=kind,
                         edit_revision=self.call('status', change=change)['edit_revision'], **kwargs)

    def next(self, job, request='next'):
        return self.call('integration_next', change=job['change'], integration=job['integration'],
                         edit_revision=job['edit_revision'], after=job['after'], request_id=request)

    def finish(self, job):
        return self.call('integration_finish', change=job['change'], integration=job['integration'],
                         edit_revision=job['edit_revision'], request_id='finish')

    def resolve(self, job, resolutions):
        return self.call('resolve', change=job['change'], integration=job['integration'],
                         edit_revision=job['edit_revision'], request_id='resolve', resolutions=resolutions)

    def seed(self, paths=('a',)):
        change = self.change()
        blob = self.upload(change, b'base')
        self.edit(change, [{'path': p, 'blob': blob} for p in paths])
        self.call('submit', change=change)
        return change

    def test_metadata_move_remove_and_revision_history(self):
        self.seed()
        source, target = self.change(), self.change()
        opened = self.call('checkout', change=source, paths=['a', 'new'], mode='exclusive')
        self.assertEqual(opened['edit_revision'], 1)
        blob = self.upload(source, b'moved')
        self.edit(source, [{'path': 'a', 'blob': blob}, {'path': 'new', 'blob': blob}])
        self.edit(source, [{'path': 'a', 'blob': blob}], chunk='again')
        args = dict(change=source, target_change=target, edit_revision=3, target_edit_revision=0,
                    paths=['a', 'new'], request_id='move')
        result = self.call('move_files', **args)
        self.assertEqual(self.call('move_files', **args), result)
        self.assertEqual(result['source']['edit_revision'], 4)
        self.assertEqual(self.call('change_files', change=source)['files'], 0)
        self.assertEqual(base64.b64decode(self.call('read', change=source, path='a')['data']), b'base')
        with self.assertRaisesRegex(ValueError, 'Exclusive checkout'):
            self.call('checkout', change=self.change(), paths=['a'])
        args = dict(change=target, edit_revision=1, description='Moved assets', request_id='metadata')
        result = self.call('update_change', **args)
        self.assertEqual(self.call('update_change', **args), result)
        self.assertEqual(result['description'], 'Moved assets')
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            self.call('update_change', **{**args, 'request_id': 'stale'})
        self.call('remove_files', change=target, paths=['new'], edit_revision=2, request_id='remove')
        self.call('checkout', change=source, paths=['new'], mode='exclusive')
        self.call('submit', change=target)
        history = self.call('history', stream='main', path='a')['items']
        self.assertEqual([row['number'] for row in history], [2, 1])
        self.assertEqual([row['change'] for row in history[:1]], [target])
        self.assertEqual(self.call('list', stream='main')['files'], 1)

    def test_shelf_is_immutable_and_unshelve_is_bounded_and_resumable(self):
        source = self.change()
        blob = self.upload(source, b'shelved')
        self.edit(source, [{'path': '%04d' % i, 'blob': blob} for i in range(1000)])
        self.edit(source, [{'path': '%04d' % i, 'blob': blob} for i in range(1000, 1003)], chunk='tail')
        args = dict(change=source, edit_revision=2, request_id='shelf')
        shelf = self.call('shelve', **args)
        self.assertEqual(self.call('shelve', **args), shelf)
        self.call('remove_files', change=source, paths=['0000'], edit_revision=2, request_id='remove')
        self.call('revert', change=source)
        self.assertEqual(self.call('change_files', shelf=shelf['code'], limit=1)['files'], 1003)
        self.assertEqual(base64.b64decode(self.call('read', shelf=shelf['code'], path='0000')['data']), b'shelved')
        dest = self.change()
        job = self.start(dest, 'unshelve', shelf=shelf['code'])
        first = self.next(job)
        self.assertFalse(first['complete'])
        self.assertEqual(self.call('list', change=dest)['files'], 0)
        self.assertEqual(self.next(job), first)
        self.api = Api(Store(self.store.data_dir))
        last = self.next(first, 'tail')
        self.assertTrue(last['complete'])
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        result = self.finish(last)
        self.assertEqual(self.finish(last), result)
        self.call('submit', change=dest)
        self.assertEqual(self.call('list', stream='main')['files'], 1003)
        self.assertEqual(self.call('history', stream='main', path='0000')['items'][0]['change'], dest)
        from pyasm.search.search import RequestContext, request_context
        with request_context(RequestContext(self.store, 'admin', 'files')), access('files'):
            self.assertEqual(Search('file_project/blob').get_count(), 1)
            record = find('change', shelf['code'])
            data = record.get_json_value('data')
            with self.assertRaisesRegex(ValueError, 'Shelved changelists are immutable'):
                save(record, {**data, 'description': 'tampered'})

    def test_rebase_three_way_resolutions_and_delete_conflicts(self):
        self.seed(('ours', 'theirs', 'merged', 'deleted', 'untouched'))
        ours, theirs = self.change(), self.change()
        mine, other = self.upload(ours, b'mine'), self.upload(theirs, b'other')
        self.edit(ours, [{'path': p, 'blob': mine} for p in ('ours', 'theirs', 'merged')] + [{'path': 'deleted', 'delete': True}])
        self.edit(theirs, [{'path': p, 'blob': other} for p in ('ours', 'theirs', 'merged', 'deleted')])
        self.call('submit', change=theirs)
        job = self.next(self.start(ours))
        self.assertEqual(job['conflicts'], 4)
        conflicts = self.call('conflicts', change=ours, integration=job['integration'], edit_revision=1, limit=2)
        self.assertEqual(len(conflicts['items']), 2)
        self.assertIsNotNone(conflicts['after'])
        for side, expected in (('base', b'base'), ('ours', b'mine'), ('theirs', b'other')):
            self.assertEqual(base64.b64decode(self.call('read', change=ours, integration=job['integration'],
                edit_revision=1, conflict_side=side, path='ours')['data']), expected)
        with self.assertRaisesRegex(ValueError, 'resolve all conflicts'):
            self.finish(job)
        merged = self.upload(ours, b'merged')
        job = self.resolve(job, [{'path': 'ours', 'choice': 'ours'}, {'path': 'theirs', 'choice': 'theirs'},
                                 {'path': 'merged', 'choice': 'blob', 'blob': merged}, {'path': 'deleted', 'choice': 'ours'}])
        self.assertEqual(job['conflicts'], 0)
        self.finish(job)
        self.call('submit', change=ours)
        for path, expected in (('ours', b'mine'), ('theirs', b'other'), ('merged', b'merged'), ('untouched', b'base')):
            self.assertEqual(base64.b64decode(self.call('read', stream='main', path=path)['data']), expected)
        self.assertEqual([v['number'] for v in self.call('history', stream='main', path='ours')['items']], [3, 2, 1])
        self.assertEqual([v['number'] for v in self.call('history', stream='main', path='theirs')['items']], [2, 1])
        self.assertTrue(self.call('history', stream='main', path='deleted')['items'][0]['deleted'])

    def test_unrelated_rebase_stale_head_and_cancel(self):
        self.seed(('a', 'b'))
        first, second = self.change(), self.change()
        self.edit(first, [{'path': 'a', 'blob': self.upload(first, b'first')}])
        self.edit(second, [{'path': 'b', 'blob': self.upload(second, b'second')}])
        self.call('submit', change=second)
        job = self.next(self.start(first))
        self.assertEqual(job['conflicts'], 0)
        with self.assertRaisesRegex(ValueError, 'integration'):
            self.edit(first, [{'path': 'a', 'delete': True}], chunk='blocked')
        later = self.change()
        self.edit(later, [{'path': 'c', 'blob': self.upload(later)}])
        self.call('submit', change=later)
        with self.assertRaisesRegex(ValueError, 'head changed again'):
            self.finish(job)
        args = dict(change=first, integration=job['integration'], edit_revision=1, request_id='cancel')
        self.assertTrue(self.call('integration_cancel', **args)['complete'])
        self.assertEqual(self.call('integration_cancel', **args)['edit_revision'], 2)
        job = self.call('rebase_begin', change=first, edit_revision=2, request_id='restart')
        self.finish(self.next(job, 'restart-next'))
        self.call('submit', change=first)
        self.assertEqual(self.call('list', stream='main')['files'], 3)

    def test_unshelve_local_conflict_preserves_existing_edit_and_cancel_locks(self):
        self.seed(('a', 'b'))
        source = self.change()
        self.edit(source, [{'path': 'a', 'blob': self.upload(source, b'shelf')}])
        shelf = self.call('shelve', change=source, edit_revision=1, request_id='shelf')['code']
        self.call('revert', change=source)
        dest = self.change()
        self.edit(dest, [{'path': 'a', 'blob': self.upload(dest, b'local')}])
        job = self.next(self.start(dest, 'unshelve', shelf=shelf))
        self.assertEqual(job['conflicts'], 1)
        job = self.resolve(job, [{'path': 'a', 'choice': 'theirs'}])
        self.finish(job)
        self.call('submit', change=dest)
        self.assertEqual(base64.b64decode(self.call('read', stream='main', path='a')['data']), b'local')
        dest = self.change()
        self.call('checkout', change=dest, paths=['b'], mode='exclusive')
        job = self.next(self.start(dest, 'unshelve', shelf=shelf))
        self.call('integration_cancel', change=dest, integration=job['integration'], edit_revision=1, request_id='cancel')
        other = self.change()
        self.call('checkout', change=other, paths=['a'], mode='exclusive')
        with self.assertRaisesRegex(ValueError, 'Exclusive checkout'):
            self.call('checkout', change=other, paths=['b'])

    def test_move_and_finish_trigger_failures_roll_back_all_roots_and_locks(self):
        source, dest = self.change(), self.change()
        self.edit(source, [{'path': 'a', 'blob': self.upload(source)}])
        before = self.call('status', change=source)
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_code() == dest and record.get_json_value('data')['edit_revision'] == 1:
                raise ValueError('late destination trigger')
            return original(record, *args, **kwargs)
        args = dict(change=source, target_change=dest, edit_revision=1, target_edit_revision=0, paths=['a'], request_id='move')
        with patch.object(FileProjectRecord, '_call_triggers', fail):
            with self.assertRaisesRegex(ValueError, 'late destination trigger'):
                self.call('move_files', **args)
        self.assertEqual(self.call('status', change=source), before)
        self.assertEqual(self.call('change_files', change=dest)['files'], 0)
        self.call('move_files', **args)
        self.call('submit', change=source)
        job = self.next(self.start(dest))
        before = self.call('status', change=dest)
        def finish_fail(record, *args, **kwargs):
            if record.get_code() == dest and record.get_json_value('data')['edit_revision'] == 2:
                raise ValueError('finish trigger')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', finish_fail):
            with self.assertRaisesRegex(ValueError, 'finish trigger'):
                self.finish(job)
        self.assertEqual(self.call('status', change=dest), before)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.finish(job)
        self.call('submit', change=dest)

    def test_permissions_shared_shelf_and_parallel_move_retry(self):
        artist = self.writer()
        source, dest = self.change(), self.change()
        self.edit(source, [{'path': 'a', 'blob': self.upload(source)}])
        shelf = self.call('shelve', change=source, edit_revision=1, request_id='shelf')['code']
        foreign = self.client(artist, 'create_change', workspace='artist')['code']
        with self.assertRaises(SecurityException):
            self.client(artist, 'update_change', change=source, edit_revision=1, request_id='bad', description='bad')
        with self.assertRaises(SecurityException):
            self.call('move_files', change=source, target_change=foreign, edit_revision=1, target_edit_revision=0, paths=['a'], request_id='bad')
        self.assertEqual(len(self.client(artist, 'change_files', shelf=shelf)['items']), 1)
        blob = self.call('change_files', change=source)['items'][0]['file']['blob']
        with self.assertRaises(SecurityException):
            self.client(artist, 'edit', change=foreign, edit_revision=0, chunk='injection', operations=[{'path': 'a', 'blob': blob}])
        job = self.client(artist, 'unshelve_begin', change=foreign, shelf=shelf, edit_revision=0, request_id='shelf')
        job = self.client(artist, 'integration_next', change=foreign, integration=job['integration'], edit_revision=0, request_id='next', after='')
        self.client(artist, 'integration_finish', change=foreign, integration=job['integration'], edit_revision=0, request_id='finish')
        args = dict(change=source, target_change=dest, edit_revision=1, target_edit_revision=0, paths=['a'], request_id='move')
        results = self.race([lambda: self.client(self.ticket, 'move_files', **args)] * 3)
        self.assertTrue(all(row == results[0] for row in results), results)
        self.assertEqual(self.call('status', change=source)['edit_revision'], 2)

    def test_old_pending_changelist_index_and_unchanged_subtrees(self):
        change = self.change()
        self.edit(change, [{'path': 'a', 'blob': self.upload(change)}])
        self.call('checkout', change=change, paths=['checkout-only'], mode='exclusive')
        from pyasm.search.search import RequestContext, request_context
        with request_context(RequestContext(self.store, 'admin', 'files')), access('files'):
            self.api.auth.bind_security('admin', self.token)
            record = find('change', change)
            data = record.get_json_value('data')
            data.pop('work_root')
            from pyasm.command import Command
            command = Command()
            command.execute = lambda: save(record, data)
            Command.execute_cmd(command)
        with self.assertRaisesRegex(ValueError, 'Index this older'):
            self.call('change_files', change=change)
        self.assertTrue(self.call('index_change', change=change)['complete'])
        files = self.call('change_files', change=change)['items']
        self.assertEqual([entry['path'] for entry in files], ['a', 'checkout-only'])
        self.assertEqual(files[1]['mode'], 'exclusive')

    def test_chunk_failure_cancel_and_trigger_catalog_visibility(self):
        source = self.change()
        blob = self.upload(source)
        self.edit(source, [{'path': '%04d' % i, 'blob': blob} for i in range(1000)])
        self.edit(source, [{'path': '1000', 'blob': blob}], chunk='tail')
        shelf = self.call('shelve', change=source, edit_revision=2, request_id='shelf')['code']
        self.call('revert', change=source)
        dest = self.change()
        job = self.next(self.start(dest, 'unshelve', shelf=shelf))
        before = self.call('status', change=dest)
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'catalog-visibility',
            'event': 'update|file_project/change', 'class_name': 'test_file_change.CatalogVisibility',
            'mode': 'same process,same transaction'}))
        with patch.object(CatalogVisibility, 'fail', True):
            with self.assertRaisesRegex(ValueError, 'last chunk failure'):
                self.next(job, 'tail')
        self.assertEqual(self.call('status', change=dest), before)
        self.assertEqual(self.call('list', change=dest)['files'], 0)
        last = self.next(job, 'tail')
        args = dict(change=dest, integration=last['integration'], edit_revision=0, request_id='cancel-first')
        cancelled = self.call('integration_cancel', **args)
        self.assertTrue(cancelled['cancelling'])
        self.assertEqual(self.call('integration_cancel', **args), cancelled)
        self.assertFalse(self.call('status', change=dest)['integration']['acquired_root'] == before['integration']['acquired_root'])
        result = self.call('integration_cancel', **{**args, 'request_id': 'cancel-last'})
        self.assertTrue(result['complete'])
        self.call('checkout', change=self.change(), paths=['0000', '1000'], mode='exclusive')

    def test_checkout_retry_and_unshelve_cannot_cross_stream_or_accept_foreign_merge(self):
        self.seed(('a',))
        ours, theirs = self.change(), self.change()
        args = dict(change=ours, edit_revision=0, paths=['a'], mode='ordinary', request_id='open')
        opened = self.call('checkout', **args)
        self.assertEqual(self.call('checkout', **args), opened)
        mine, foreign = self.upload(ours, b'mine'), self.upload(theirs, b'theirs')
        self.edit(ours, [{'path': 'a', 'blob': mine}])
        self.edit(theirs, [{'path': 'a', 'blob': foreign}])
        shelf = self.call('shelve', change=ours, edit_revision=2, request_id='shelf')['code']
        self.call('submit', change=theirs)
        job = self.next(self.start(ours))
        before = self.call('status', change=ours)
        with self.assertRaises(SecurityException):
            self.resolve(job, [{'path': 'a', 'choice': 'blob', 'blob': foreign}])
        self.assertEqual(self.call('status', change=ours), before)
        self.call('create_stream', code='branch', depot='main', parent='main')
        self.call('create_workspace', code='branch', stream='branch', local_root='D:/branch')
        target = self.call('create_change', workspace='branch')['code']
        with self.assertRaisesRegex(ValueError, 'same stream'):
            self.start(target, 'unshelve', shelf=shelf)
        self.assertNotIn('integration', self.call('status', change=target))

    def test_shelf_history_excludes_overwritten_draft_versions(self):
        change = self.change()
        self.edit(change, [{'path': 'a', 'blob': self.upload(change, b'draft')}])
        shelf = self.call('shelve', change=change, edit_revision=1, request_id='shelf')['code']
        self.edit(change, [{'path': 'a', 'blob': self.upload(change, b'published')}], chunk='new')
        self.call('submit', change=change)
        self.assertEqual(self.call('history', shelf=shelf, path='a')['items'], [])
        self.assertEqual(len(self.call('history', stream='main', path='a')['items']), 1)
