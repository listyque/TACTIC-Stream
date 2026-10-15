"""Real revisions, mapped workspaces and native transactional/ACL contracts."""
import base64
from hashlib import sha256
from pathlib import Path
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import FileProjectRecord
from pyasm.biz.file_view import FileView
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from test_file_project import FileProjectFixture
import test_file_change as changes


class FileViewTest(unittest.TestCase):
    def test_roundtrip_exclusions_case_and_collisions(self):
        rules = [{'stream': 'main', 'source': 'art/*/...', 'target': 'src/*/...', 'writable': True},
                 {'stream': 'main', 'source': 'art/*/cache/...', 'exclude': True},
                 {'stream': 'lib', 'source': '...', 'target': 'vendor/...'}]
        view = FileView(rules, False)
        self.assertEqual(view.forward('main', 'art/Car/model.bin')['path'], 'src/Car/model.bin')
        self.assertEqual(view.reverse('SRC/Car/model.bin')['source_path'], 'art/Car/model.bin')
        self.assertIsNone(view.forward('main', 'art/Car/cache/a'))
        self.assertIsNone(view.reverse('src/Car/cache/a'))
        self.assertFalse(view.reverse('vendor/a')['writable'])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            FileView([rules[0], {**rules[2], 'target': 'src/...'}])
        for source, target in [('...', '../...'), ('.../bad', '...'), ('*', '...')]:
            with self.assertRaises(ValueError):
                FileView([{'stream': 'main', 'source': source, 'target': target}])
        empty = FileView([{'stream': 'main', 'source': 'a*', 'target': '*'}])
        with self.assertRaises(ValueError):
            empty.forward('main', 'a')


class FileWorkspaceTest(FileProjectFixture, unittest.TestCase):
    def test_workspace_tree_browses_mapped_have_with_page_and_owner_guards(self):
        self.publish({'assets/hero/a': b'a', 'assets/hero/b': b'b', 'root.txt': b'root'})
        self.mapped()
        self.sync()
        page = self.call('workspace_browse',workspace='mapped',limit=1)
        self.assertEqual([item['path'] for item in page['items']],['src/'])
        children = self.call('workspace_browse',workspace='mapped',root=page['root'],directory='src/')
        self.assertEqual([item['path'] for item in children['items']],['src/assets/','src/root.txt'])
        files = self.call('read_page',source='have',workspace='mapped',workspace_context='mapped',prefix='src/',folder=True)
        self.assertEqual([item['path'] for item in files['items']],['src/root.txt'])
        self.assertEqual(files['items'][0]['source_path'],'root.txt')
        self.assertIsNotNone(files['items'][0]['have'])
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist,'workspace_browse',workspace='mapped')
        with self.assertRaises(SecurityException):
            self.client(artist,'read_page',source='have',workspace='mapped',workspace_context='mapped',prefix='src/',folder=True)
        with self.assertRaises(ValueError):
            self.call('workspace_browse',workspace='mapped',root='stale')
        with self.assertRaises(ValueError):
            self.call('workspace_browse',workspace='mapped',limit=1001)

    def test_local_tree_seeks_directory_children_and_literal_prefixes(self):
        import json
        import sqlite3
        from tactic_client_lib.file_workspace import local_browse,local_page
        cache=Path(self.temp.name)/'local-tree.sqlite'
        with sqlite3.connect(cache) as db:
            db.execute('CREATE TABLE local(path TEXT PRIMARY KEY,data TEXT NOT NULL)')
            paths=['assets/hero/%04d.txt' % i for i in range(1100)]+['assets/props/tool','100%/literal_1','root.txt']
            db.executemany('INSERT INTO local VALUES(?,?)',[(path,json.dumps({'path':path,'local_status':'added','server_status':'untracked'})) for path in paths])
        db.close()
        page=local_browse(cache,limit=1)
        self.assertEqual(page['items'][0]['path'],'100%/')
        remaining=local_browse(cache,after=page['after'])
        self.assertEqual([item['path'] for item in remaining['items']],['assets/','root.txt'])
        self.assertEqual([item['path'] for item in local_browse(cache,'assets/')['items']],['assets/hero/','assets/props/'])
        self.assertEqual(len(local_browse(cache,'assets/hero/')['items']),200)
        self.assertEqual([item['path'] for item in local_page(cache,changes_only=False,prefix='100%/')['items']],['100%/literal_1'])

    edit = changes.FileChangeTest.edit
    start = changes.FileChangeTest.start
    next = changes.FileChangeTest.next
    finish = changes.FileChangeTest.finish
    resolve = changes.FileChangeTest.resolve
    client = changes.FileChangeTest.client
    writer = changes.FileChangeTest.writer
    race = changes.FileChangeTest.race

    def publish(self, files, workspace='work', stream=None):
        args = {'workspace': workspace}
        if stream:
            args['stream'] = stream
        change = self.call('create_change', **args)['code']
        operations = [{'path': path, 'delete': True} if data is None else
                      {'path': path, 'blob': self.upload(change, data)} for path, data in files.items()]
        for offset in range(0, len(operations), 1000):
            self.edit(change, operations[offset:offset + 1000], str(offset))
        self.call('submit', change=change)
        return change

    def test_exact_file_sync_does_not_touch_neighbors_or_full_checkpoint(self):
        self.publish({'a.txt':b'a','a.txt.other':b'neighbor','folder/b.txt':b'b'})
        self.mapped()
        job=self.call('sync_begin',workspace='mapped',paths=['src/a.txt'])
        items=[]
        for _ in range(8):
            page=self.call('sync_next',sync=job['code']);items.extend(page['items'])
            result=self.call('sync_ack',sync=job['code'],ack_revision=page['ack_revision'],paths=[item['path'] for item in page['items']])
            if result['state']=='complete':break
        self.assertEqual([item['source_path'] for item in items],['a.txt'])
        self.assertEqual([item['path'] for item in self.call('have',workspace='mapped')['items']],['src/a.txt'])
        self.publish({'a.txt':b'new'})
        self.sync()
        self.assertEqual(len(self.call('have',workspace='mapped')['items']),3)
        self.assertEqual(self.call('have',workspace='mapped')['items'][0]['sha256'],sha256(b'new').hexdigest())
        with self.assertRaisesRegex(ValueError,'mapped'):
            self.call('sync_begin',workspace='mapped',paths=['excluded/a.txt'])
        self.assertIsNone(self.call('workspace_status',workspace='mapped')['active_sync'])
        for values in ({'paths':[]},{'paths':['src/a.txt'],'prefix':'src/'},{'paths':['../outside']}):
            with self.subTest(values=values),self.assertRaises(ValueError):
                self.call('sync_begin',workspace='mapped',**values)

    def branch(self, code, parent='main'):
        self.call('create_stream', code=code, depot='main', parent=parent)
        self.call('create_workspace', code=code, stream=code, local_root='D:/' + code)

    def mapped(self, code='mapped', rules=None, **kwargs):
        return self.call('create_workspace', code=code, stream='main', local_root='D:/' + code,
                         mappings=rules or [{'stream': 'main', 'source': '...', 'target': 'src/...', 'writable': True}], **kwargs)

    def sync(self, workspace='mapped'):
        job = self.call('sync_begin', workspace=workspace)
        all_items = []
        for _ in range(20):
            plan = self.call('sync_next', sync=job['code'])
            all_items.extend(plan['items'])
            job = self.call('sync_ack', sync=job['code'], ack_revision=plan['ack_revision'],
                            paths=[item['path'] for item in plan['items']])
            if job['state'] == 'complete':
                return all_items
        self.fail('Sync did not terminate')

    def merge(self, change, source, **kwargs):
        job = self.start(change, 'merge', source_stream=source, **kwargs)
        index = 0
        while not job['complete']:
            job = self.next(job, str(index))
            index += 1
        return job

    def data(self, stream, path, **kwargs):
        return base64.b64decode(self.call('read', stream=stream, path=path, **kwargs)['data'])

    def test_multiple_depots_mappings_have_and_exclusions(self):
        self.publish({'a': b'main', 'cache/a': b'excluded'})
        self.call('create_depot', code='shared')
        self.call('create_stream', code='lib', depot='shared')
        self.call('create_workspace', code='lib', stream='lib', local_root='D:/lib')
        self.publish({'a': b'library'}, 'lib')
        self.mapped(rules=[{'stream': 'main', 'source': '...', 'target': 'src/...', 'writable': True},
                           {'stream': 'main', 'source': 'cache/...', 'exclude': True},
                           {'stream': 'lib', 'source': '...', 'target': 'vendor/...'}])
        self.assertEqual(len(self.call('depots')['items']), 2)
        self.assertEqual(len(self.call('streams', depot='shared')['items']), 1)
        items = self.sync()
        self.assertEqual({item['local_path'] for item in items}, {'src/a', 'vendor/a'})
        have = self.call('have', workspace='mapped')['items']
        self.assertEqual({item['stream'] for item in have}, {'main', 'lib'})
        self.assertEqual(self.sync(), [])
        change = self.call('create_change', workspace='mapped')['code']
        with self.assertRaises(SecurityException):
            self.call('checkout', change=change, paths=['cache/a'])
        with self.assertRaises(SecurityException):
            self.call('create_change', workspace='mapped', stream='lib')
        self.call('revert', change=change)
        artist = self.writer()
        self.assertEqual([item['code'] for item in self.client(artist, 'depots')['items']], ['main'])
        with self.assertRaises(SecurityException):
            self.client(artist, 'create_workspace', code='bad', stream='main', local_root='D:/bad',
                        mappings=[{'stream': 'main', 'source': '...', 'target': 'src/...'},
                                  {'stream': 'lib', 'source': '...', 'target': 'lib/...'}])

    def test_mapping_preview_resolves_exclusions_reverse_paths_and_case_collisions(self):
        rules=[{'stream':'main','source':'assets/...','target':'art/...','writable':True},
               {'stream':'main','source':'assets/private/...','exclude':True}]
        result=self.call('workspace_preview',stream='main',case_sensitive=False,mappings=rules,paths=[
            {'stream':'main','path':'assets/A.txt'},{'stream':'main','path':'assets/a.txt'},
            {'stream':'main','path':'assets/private/hidden.txt'},{'local_path':'art/other.txt'}])
        self.assertFalse(result['valid'])
        self.assertTrue(all(row['collision'] for row in result['items'][:2]))
        self.assertTrue(result['items'][2]['excluded'])
        self.assertEqual(result['items'][3]['source_path'],'assets/other.txt')
        with self.assertRaisesRegex(ValueError,'1000'):
            self.call('workspace_preview',stream='main',case_sensitive=False,mappings=rules,paths=[{'local_path':'art/a.txt'}]*1001)

    def test_workspace_switch_view_guards_cleanup_and_root_change(self):
        self.publish({'a': b'base'})
        self.mapped()
        args = dict(workspace='mapped', revision=0, request_id='switch')
        switched = self.call('switch_workspace', **args)
        self.assertEqual(self.call('switch_workspace', **args), switched)
        self.assertEqual(self.call('workspace_active')['workspace'], 'mapped')
        self.assertEqual(self.client(self.ticket, 'workspace_active')['revision'], 1)
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            self.call('switch_workspace', workspace='work', revision=0, request_id='stale')
        change = self.call('create_change', workspace='mapped')['code']
        with self.assertRaisesRegex(ValueError, 'pending changelists'):
            self.call('update_workspace', workspace='mapped', view_revision=0, request_id='blocked')
        self.call('revert', change=change)
        self.sync()
        self.branch('branch')
        self.publish({'a': b'branch'}, 'branch')
        self.call('update_workspace', workspace='mapped', stream='branch', view_revision=0, request_id='branch')
        self.assertEqual(self.sync()[0]['stream'], 'branch')
        self.call('update_workspace', workspace='mapped', view_revision=1, request_id='map',
                  mappings=[{'stream': 'branch', 'source': '...', 'target': 'new/...', 'writable': True}])
        plan = self.sync()
        self.assertEqual({item['local_path'] for item in plan}, {'src/a', 'new/a'})
        self.assertEqual([item['path'] for item in self.call('have', workspace='mapped')['items']], ['new/a'])
        self.call('update_workspace', workspace='mapped', view_revision=2, request_id='root', local_root='D:/other')
        self.assertEqual(self.call('have', workspace='mapped')['items'], [])
        artist = self.writer()
        self.assertIsNone(self.client(artist, 'workspace_active')['workspace'])
        with self.assertRaises(SecurityException):
            self.client(artist, 'switch_workspace', workspace='mapped', revision=0, request_id='other')

    def test_mapped_pagination_empty_ack_and_pinned_heads(self):
        change = self.change()
        blob = self.upload(change, b'x')
        for i in range(2):
            self.edit(change, [{'path': 'cache/%04d' % n, 'blob': blob} for n in range(i * 600, (i + 1) * 600)], str(i))
        self.edit(change, [{'path': 'z', 'blob': blob}], 'z')
        self.call('submit', change=change)
        self.mapped(rules=[{'stream': 'main', 'source': '...', 'target': 'src/...', 'writable': True},
                           {'stream': 'main', 'source': 'cache/...', 'exclude': True}])
        job = self.call('sync_begin', workspace='mapped')
        plan = self.call('sync_next', sync=job['code'])
        self.assertEqual(plan['items'], [])
        self.assertTrue(plan['more'])
        self.publish({'z': b'new'})
        args = dict(sync=job['code'], ack_revision=0, paths=[])
        acknowledged = self.call('sync_ack', **args)
        self.assertEqual(self.call('sync_ack', **args), acknowledged)
        plan = self.client(self.ticket, 'sync_next', sync=job['code'])
        self.assertEqual(plan['items'][0]['sha256'], sha256(b'x').hexdigest())
        self.assertEqual(self.call('have', workspace='mapped')['items'], [])
        self.call('sync_ack', sync=job['code'], ack_revision=1, paths=['src/z'])
        self.assertEqual(self.sync()[0]['sha256'], sha256(b'new').hexdigest())

    def test_reconcile_content_case_missing_and_snapshot_guards(self):
        original = self.publish({'Car.bin': b'base', 'b': b'base'})
        self.mapped(case_sensitive=False)
        self.sync()
        digest = sha256(b'base').hexdigest()
        first = self.call('reconcile', workspace='mapped', files=[{'path': 'SRC/car.bin', 'size': 4, 'sha256': digest}])
        self.assertEqual((first['items'][0]['local_status'], first['items'][0]['server_status']), ('clean', 'current'))
        self.assertEqual(first['items'][0]['source_path'], 'Car.bin')
        self.publish({'Car.bin': b'next', 'b': None})
        result = self.call('reconcile', workspace='mapped', have_root=first['have_root'], view_revision=0,
            files=[{'path': 'src/car.bin', 'size': 4, 'sha256': sha256(b'edit').hexdigest()},
                   {'path': 'src/b', 'missing': True}, {'path': 'src/new', 'size': 0, 'sha256': sha256(b'').hexdigest()},
                   {'path': 'outside', 'missing': True}])
        self.assertEqual([(i['local_status'], i['server_status']) for i in result['items']],
                         [('modified', 'newer'), ('missing', 'deleted'), ('added', 'untracked'), ('unmapped', 'unmapped')])
        pinned = self.call('reconcile', workspace='mapped', heads=first['heads'], files=[{'path': 'src/b', 'missing': True}])
        self.assertEqual(pinned['items'][0]['server_status'], 'current')
        self.assertEqual(pinned['heads']['main'], original)
        with self.assertRaisesRegex(ValueError, 'view changed'):
            self.call('reconcile', workspace='mapped', view_revision=1, files=[{'path': 'src/b', 'missing': True}])
        self.sync()
        with self.assertRaisesRegex(ValueError, 'Have changed'):
            self.call('reconcile', workspace='mapped', have_root=first['have_root'], files=[{'path': 'src/b', 'missing': True}])

    def test_storage_binding_pins_existing_bytes_and_native_rollback(self):
        roots = {'default': str(Path(self.temp.name) / 'assets'), 'fast': str(Path(self.temp.name) / 'fast')}
        with patch.object(Environment, 'get_asset_dirs', return_value=roots.copy()), patch.object(Environment, 'get_asset_dir', return_value=roots['default']):
            self.call('update_depot', depot='main', revision=0, repository='fast')
            first = self.publish({'a': b'first'})
            descriptor = self.call('transfer', stream='main', path='a')
            private = Path(descriptor['_storage_root'])
            self.assertEqual(private.name, 'fast.file-projects')
            self.assertFalse(private.is_relative_to(Path(roots['fast'])))
            self.call('update_depot', depot='main', revision=1, repository='default')
            self.publish({'a': b'second'})
            self.assertEqual(self.data('main', 'a', published_change=first), b'first')
            self.assertEqual(self.data('main', 'a'), b'second')
            self.assertNotEqual(self.call('transfer', stream='main', path='a')['_storage_root'], str(private))
            original = FileProjectRecord._call_triggers
            def failing(record, *args, **kwargs):
                if record.get_base_search_type() == 'file_project/depot':
                    raise ValueError('depot callback failure')
                return original(record, *args, **kwargs)
            with patch.object(FileProjectRecord, '_call_triggers', failing), self.assertRaisesRegex(ValueError, 'callback failure'):
                self.call('update_depot', depot='main', revision=2, repository='fast')
            self.assertEqual(self.call('depots')['items'][0]['storage']['repository'], 'default')
            with self.assertRaises(ValueError):
                self.call('update_depot', depot='main', revision=2, repository='D:/arbitrary')
        with patch.object(Environment, 'get_asset_dirs', return_value={**roots, 'parent': self.temp.name}):
            with self.assertRaisesRegex(ValueError, 'public repository'):
                self.call('update_depot', depot='main', revision=2, repository='fast')

    def test_real_branch_merge_versions_history_and_incremental_base(self):
        baseline = self.publish({'a': b'base', 'gone': b'delete'})
        original = self.call('list', stream='main')['items'][0]['version']
        self.branch('branch')
        self.assertEqual(self.data('branch', 'a'), b'base')
        source = self.publish({'a': b'branch', 'gone': None, 'new': b'new'}, 'branch')
        branch_version = self.call('list', stream='branch')['items'][0]['version']
        self.assertEqual(self.call('history', stream='branch', path='a')['items'][0]['previous'], original)
        dest = self.change()
        job = self.merge(dest, 'branch')
        self.assertEqual(job['conflicts'], 0)
        self.assertEqual(self.data('main', 'a'), b'base')
        self.finish(job)
        self.assertEqual(base64.b64decode(self.call('read', change=dest, path='a')['data']), b'branch')
        self.call('submit', change=dest)
        self.assertEqual(self.data('main', 'a'), b'branch')
        self.assertEqual(self.data('main', 'a', published_change=baseline), b'base')
        history = self.call('history', stream='main', path='a')['items']
        self.assertEqual(history[0]['previous'], original)
        self.assertEqual(history[0]['integrated_from'], {'stream': 'branch', 'change': source, 'version': branch_version})
        with self.assertRaises(FileNotFoundError):
            self.data('main', 'gone')
        self.publish({'a': b'next'}, 'branch')
        second = self.change()
        job = self.merge(second, 'branch')
        self.assertEqual(job['conflicts'], 0)
        self.finish(job)
        self.call('submit', change=second)
        self.assertEqual(self.data('main', 'a'), b'next')
        third = self.change()
        job = self.merge(third, 'branch')
        self.assertEqual(job['after'], '')
        self.finish(job)
        self.call('submit', change=third)
        self.assertEqual(len(self.call('history', stream='main', path='a')['items']), 3)

    def test_merge_conflicts_custom_bytes_reverse_and_sibling_ancestry(self):
        self.publish({'a': b'base'})
        self.branch('left')
        self.publish({'a': b'left'}, 'left')
        self.publish({'extra': b'parent advance'})
        self.branch('right')
        self.publish({'a': b'right'}, 'right')
        dest = self.call('create_change', workspace='right')['code']
        job = self.merge(dest, 'left')
        self.assertEqual(job['conflicts'], 1)
        conflict = self.call('conflicts', change=dest, integration=job['integration'], edit_revision=0)['items'][0]
        self.assertEqual(conflict['base']['sha256'], sha256(b'base').hexdigest())
        blob = self.upload(dest, b'merged')
        job = self.resolve(job, [{'path': 'a', 'choice': 'blob', 'blob': blob}])
        self.finish(job)
        self.call('submit', change=dest)
        self.assertEqual(self.data('right', 'a'), b'merged')
        self.assertEqual(self.data('right', 'extra'), b'parent advance')
        reverse = self.change()
        job = self.merge(reverse, 'right')
        self.assertEqual(job['conflicts'], 0)
        self.finish(job)
        self.call('submit', change=reverse)
        self.assertEqual(self.data('main', 'a'), b'merged')
        self.branch('nested', 'left')
        self.publish({'nested': b'nested'}, 'nested')
        dest = self.call('create_change', workspace='right')['code']
        job = self.merge(dest, 'nested')
        self.assertEqual(job['conflicts'], 1)
        job = self.resolve(job, [{'path': 'a', 'choice': 'theirs'}])
        self.finish(job)
        self.call('submit', change=dest)
        self.assertEqual(self.data('right', 'nested'), b'nested')
        self.assertEqual(self.data('right', 'a'), b'merged')

    def test_merge_pinned_source_late_failure_and_stale_target(self):
        self.publish({'a': b'base'})
        self.branch('branch')
        source = self.publish({'a': b'first'}, 'branch')
        dest = self.change()
        job = self.start(dest, 'merge', source_stream='branch')
        self.publish({'a': b'second'}, 'branch')
        original = FileProjectRecord._call_triggers
        def failing(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data').get('integration', {}).get('complete'):
                raise ValueError('merge chunk failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', failing), self.assertRaisesRegex(ValueError, 'merge chunk failure'):
            self.next(job)
        self.assertEqual(self.call('status', change=dest)['integration']['after'], '')
        job = self.next(job)
        self.finish(job)
        self.assertEqual(base64.b64decode(self.call('read', change=dest, path='a')['data']), b'first')
        self.assertEqual(self.call('status', change=dest)['merge_sources'][0]['change'], source)
        def submit_failure(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data')['state'] == 'submitted':
                raise ValueError('merge submit failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', submit_failure), self.assertRaisesRegex(ValueError, 'merge submit failure'):
            self.call('submit', change=dest)
        self.assertEqual(self.call('stream_status', stream='main')['revision'], 1)
        self.call('submit', change=dest)
        other = self.change()
        job = self.merge(other, 'branch')
        self.publish({'unrelated': b'head advance'})
        with self.assertRaisesRegex(ValueError, 'head changed again'):
            self.finish(job)
        self.call('integration_cancel', change=other, integration=job['integration'], edit_revision=job['edit_revision'], request_id='cancel')
        self.call('revert', change=other)

    def test_merge_bounded_chunks_and_removed_files_are_not_skipped(self):
        self.branch('branch')
        change = self.call('create_change', workspace='branch')['code']
        blob = self.upload(change, b'new files')
        self.edit(change, [{'path': '%04d' % n, 'blob': blob} for n in range(1000)])
        self.edit(change, [{'path': '%04d' % n, 'blob': blob} for n in range(1000, 1100)], 'last')
        self.call('submit', change=change)
        dest = self.change()
        job = self.start(dest, 'merge', source_stream='branch')
        first = self.next(job)
        self.assertFalse(first['complete'])
        self.assertEqual(self.call('list', change=dest)['files'], 0)
        job = self.next(first, 'last')
        self.assertTrue(job['complete'])
        self.finish(job)
        self.call('remove_files', change=dest, edit_revision=1, paths=['0000'], request_id='remove')
        self.assertNotIn('merge_sources', self.call('status', change=dest))
        self.call('submit', change=dest)
        another = self.change()
        job = self.merge(another, 'branch')
        self.assertEqual(job['conflicts'], 0)
        self.finish(job)
        self.call('submit', change=another)
        self.assertEqual(self.call('list', stream='main')['files'], 1100)

    def test_have_ack_view_and_pending_index_roll_back_atomically(self):
        self.publish({'a': b'base'})
        self.mapped()
        job = self.call('sync_begin', workspace='mapped')
        plan = self.call('sync_next', sync=job['code'])
        original = FileProjectRecord._call_triggers
        def failing(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/sync' and record.get_json_value('data')['ack_revision']:
                raise ValueError('ack callback failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', failing), self.assertRaisesRegex(ValueError, 'ack callback failure'):
            self.call('sync_ack', sync=job['code'], ack_revision=0, paths=['src/a'])
        self.assertEqual(self.call('have', workspace='mapped')['items'], [])
        self.assertEqual(self.call('sync_status', sync=job['code'])['ack_revision'], 0)
        self.assertEqual(self.call('sync_next', sync=job['code']), plan)
        with self.assertRaisesRegex(ValueError, 'Finish sync'):
            self.call('update_workspace', workspace='mapped', view_revision=0, request_id='blocked')
        self.call('sync_ack', sync=job['code'], ack_revision=0, paths=['src/a'])
        change = self.call('create_change', workspace='mapped')['code']
        def pending_failure(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/workspace':
                raise ValueError('pending index callback failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', pending_failure), self.assertRaisesRegex(ValueError, 'pending index callback failure'):
            self.call('submit', change=change)
        self.assertEqual(self.call('status', change=change)['state'], 'pending')
        with self.assertRaisesRegex(ValueError, 'pending changelists'):
            self.call('update_workspace', workspace='mapped', view_revision=0, request_id='still-blocked')
        self.call('revert', change=change)
        self.call('update_workspace', workspace='mapped', view_revision=0, request_id='okay')

    def test_case_collision_never_acknowledges_ambiguous_files(self):
        self.publish({'Car': b'first', 'car': b'second'})
        self.mapped(case_sensitive=False)
        job = self.call('sync_begin', workspace='mapped')
        with self.assertRaisesRegex(ValueError, 'one local path'):
            self.call('sync_next', sync=job['code'])
        self.assertEqual(self.call('have', workspace='mapped')['items'], [])
        self.call('sync_cancel', sync=job['code'])

    def test_active_workspace_compare_and_swap_between_clients(self):
        self.mapped()
        self.call('switch_workspace', workspace='work', revision=0, request_id='first')
        result = self.race([lambda workspace=workspace: self.client(self.ticket, 'switch_workspace',
                           workspace=workspace, revision=1, request_id=workspace) for workspace in ('work', 'mapped')])
        self.assertEqual(sum(isinstance(value, dict) for value in result), 1, result)
        self.assertEqual(sum(isinstance(value, ValueError) for value in result), 1, result)
        self.assertEqual(self.call('workspace_active')['revision'], 2)

    def test_private_storage_http_ranges_and_mapped_archive(self):
        import io
        import socket
        import tarfile
        import threading
        from time import monotonic, sleep
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        import uvicorn
        from fastapi import FastAPI
        from tactic_stream.server.file_project import install_routes, FileProjectStaticFiles
        root = Path(self.temp.name)
        assets = root / 'assets'
        assets.mkdir()
        (assets / 'classic.bin').write_bytes(b'classic')
        with patch.object(Environment, 'get_asset_dirs', return_value={'default': str(assets)}), patch.object(Environment, 'get_asset_dir', return_value=str(assets)):
            self.call('update_depot', depot='main', revision=0, repository='default')
            self.publish({'a.bin': b'hello'})
        descriptor = self.call('transfer', stream='main', path='a.bin')
        self.mapped()
        job = self.call('sync_begin', workspace='mapped')
        app = FastAPI()
        install_routes(app, self.api)
        app.mount('/assets', FileProjectStaticFiles(directory=root,private_jobs=root/'file-jobs'))
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        url = 'http://127.0.0.1:%s' % sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        try:
            deadline = monotonic() + 10
            while not server.started and thread.is_alive() and monotonic() < deadline:
                sleep(.01)
            self.assertTrue(server.started)
            with urlopen(url + '/assets/assets/classic.bin') as response:
                self.assertEqual(response.read(), b'classic')
            private = 'assets.file-projects/files/blobs/%s/%s' % (descriptor['blob'][:2], descriptor['blob'])
            for name in (private, private.replace('assets.file-projects', 'ASSETS.FILE-PROJECTS')):
                with self.assertRaises(HTTPError) as denied:
                    urlopen(url + '/assets/' + name)
                self.assertEqual(denied.exception.code, 404)
                denied.exception.close()
            telemetry=root/'file-jobs/files/job/progress.json'
            telemetry.parent.mkdir(parents=True)
            telemetry.write_text('{"worker_token":"private"}',encoding='utf-8')
            with self.assertRaises(HTTPError) as denied:
                urlopen(url+'/assets/file-jobs/files/job/progress.json')
            self.assertEqual(denied.exception.code,404)
            denied.exception.close()
            ordinary=assets/'file-jobs/ordinary.bin'
            ordinary.parent.mkdir(parents=True)
            ordinary.write_bytes(b'classic public content')
            with urlopen(url+'/assets/assets/file-jobs/ordinary.bin') as response:
                self.assertEqual(response.read(),b'classic public content')
            download = url + '/file-project/download?project=files&stream=main&path=a.bin'
            with urlopen(Request(download, headers={'X-Tactic-Ticket': self.token, 'Range': 'bytes=1-3'})) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), b'ell')
            with urlopen(Request(url + '/file-project/sync-download?project=files&sync=' + job['code'],
                                 headers={'X-Tactic-Ticket': self.token})) as response:
                with tarfile.open(fileobj=io.BytesIO(response.read())) as archive:
                    self.assertEqual(archive.getnames(), ['src/a.bin'])
                    self.assertEqual(archive.extractfile('src/a.bin').read(), b'hello')
        finally:
            server.should_exit = True
            thread.join(10)
            sock.close()
            self.assertFalse(thread.is_alive(), 'Owned HTTP server did not stop')

    def test_incremental_sync_skips_unchanged_trees_and_case_only_rename(self):
        change = self.change()
        blob = self.upload(change, b'base')
        for offset in range(0, 3000, 1000):
            self.edit(change, [{'path': 'file%04d' % n, 'blob': blob} for n in range(offset, offset + 1000)], str(offset))
        self.edit(change, [{'path': 'Car', 'blob': blob}], 'car')
        self.call('submit', change=change)
        self.mapped(case_sensitive=False)
        self.sync()
        self.publish({'Car': None, 'car': b'renamed', 'file0010': b'changed', 'file1000': None})
        from pyasm.biz.file_catalog import FileCatalog
        original = FileCatalog.entries
        def guarded(catalog, *args, **kwargs):
            self.fail('Incremental sync must not enumerate unchanged catalog or Have')
            return original(catalog, *args, **kwargs)
        with patch.object(FileCatalog, 'entries', guarded):
            items = self.sync()
            self.assertEqual(self.sync(), [])
        self.assertEqual(len(items), 3)
        self.assertEqual([item['source_path'] for item in items if item['path'] == 'src/car'], ['car'])
        have = self.call('have', workspace='mapped', prefix='SRC/CAR')['items']
        self.assertEqual(have[0]['source_path'], 'car')
        self.assertNotIn('_have', have[0])
