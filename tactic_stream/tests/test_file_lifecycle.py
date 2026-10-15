"""Lifecycle previews, immutable shelf history and cancellable local reconciliation."""
import base64
from pathlib import Path
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import FileProjectRecord
from pyasm.common.errors import SecurityException
from tactic_client_lib.file_workspace import reconcile_workspace, local_page, inspect_local
import test_file_change


class FileLifecycleTest(test_file_change.FileChangeTest):
    # Reuse native fixtures, not the parent test methods.
    def test_selected_shelf_replacement_preserves_number_and_previous_bytes(self):
        change = self.change()
        blob = self.upload(change, b'first')
        self.edit(change, [{'path': path, 'blob': blob} for path in ('a', 'b')])
        shelf = self.call('shelve', change=change, paths=['a'], edit_revision=1, request_id='selected')
        self.assertEqual([row['path'] for row in self.call('change_files', shelf=shelf['code'])['items']], ['a'])
        blob = self.upload(change, b'second')
        self.edit(change, [{'path': 'a', 'blob': blob}], chunk='second')
        preview = self.call('change_preview', change=change, shelf=shelf['code'], edit_revision=2, limit=1)
        self.assertEqual(preview['items'][0]['shelf_status'], 'different')
        args = dict(change=change, shelf=shelf['code'], edit_revision=2, shelf_revision=1, paths=['a'], request_id='replace')
        replaced = self.call('update_shelf', **args)
        self.assertEqual(self.call('update_shelf', **args), replaced)
        self.assertEqual(replaced['number'], shelf['number'])
        self.assertEqual(base64.b64decode(self.call('read', shelf=replaced['previous_shelf'], path='a')['data']), b'first')
        self.assertEqual(base64.b64decode(self.call('read', shelf=shelf['code'], path='a')['data']), b'second')
        removed = self.call('update_shelf', **{**args, 'shelf_revision':2, 'request_id':'delete', 'delete':True})
        self.assertEqual(self.call('change_files', shelf=removed['code'])['files'], 0)

    def test_shelf_replacement_trigger_failure_rolls_back_and_is_retryable(self):
        change = self.change()
        blob = self.upload(change, b'bytes')
        self.edit(change, [{'path':'a', 'blob':blob}])
        shelf = self.call('shelve', change=change, edit_revision=1, request_id='shelf')
        original = FileProjectRecord.commit
        def fail(record, *args, **kwargs):
            if record.get_code() == shelf['code']:
                raise ValueError('shelf trigger failure')
            return original(record, *args, **kwargs)
        args = dict(change=change, shelf=shelf['code'], edit_revision=1, shelf_revision=1, paths=['a'], delete=True, request_id='delete')
        with patch.object(FileProjectRecord, 'commit', fail), self.assertRaisesRegex(ValueError, 'trigger failure'):
            self.call('update_shelf', **args)
        self.assertEqual(self.call('change_files', shelf=shelf['code'])['files'], 1)
        self.assertEqual(self.call('update_shelf', **args)['edit_revision'], 2)

    def test_shelve_and_revert_keeps_bytes_and_releases_pending_work(self):
        change = self.change()
        blob = self.upload(change, b'bytes')
        self.edit(change, [{'path':'a', 'blob':blob}])
        shelf = self.call('shelve', change=change, edit_revision=1, request_id='shelf', revert=True)
        self.assertEqual(self.call('shelve',change=change,edit_revision=1,request_id='shelf',revert=True)['code'],shelf['code'])
        self.assertEqual(self.call('status', change=change)['state'], 'reverted')
        self.assertEqual(self.call('read', shelf=shelf['code'], path='a')['size'], 5)

    def test_local_edit_after_upload_invalidates_staged_copy(self):
        root=Path(self.temp.name)/'local-edit';root.mkdir()
        (root/'a').write_bytes(b'staged')
        change=self.change()
        self.edit(change,[{'path':'a','blob':self.upload(change,b'staged')}])
        class Client:
            rpc=lambda _,action,**kw:self.call(action,**kw)
            progress=lambda *_:None
        cache=Path(self.temp.name)/'local-edit.sqlite'
        reconcile_workspace(Client(),'work',root,cache)
        row=self.call('change_files',change=change)['items'][0];row['local_path']='a'
        inspect_local(cache,root,[row]);self.assertTrue(row['staged_current'])
        (root/'a').write_bytes(b'locally changed')
        inspect_local(cache,root,[row]);self.assertFalse(row['staged_current'])
        self.assertEqual(row['server_status'],'modified_after_upload')

    def test_binary_bulk_resolve_leaves_unselected_conflict_pending(self):
        self.seed(paths=('a','b','c'))
        ours,theirs=self.change(),self.change()
        ours_blob=self.upload(ours,b'\0ours');theirs_blob=self.upload(theirs,b'\0theirs')
        self.edit(ours,[{'path':path,'blob':ours_blob} for path in ('a','b','c')])
        self.edit(theirs,[{'path':path,'blob':theirs_blob} for path in ('a','b','c')])
        self.call('submit',change=theirs)
        job=self.next(self.start(ours))
        self.assertEqual(job['conflicts'],3)
        self.resolve(job,[{'path':path,'choice':'ours'} for path in ('a','b')])
        remaining=self.call('conflicts',change=ours,integration=job['integration'],edit_revision=job['edit_revision'])
        self.assertEqual([row['path'] for row in remaining['items']],['c'])
        with self.assertRaisesRegex(ValueError,'resolve all conflicts'):
            self.finish(job)
        self.call('resolve',change=ours,integration=job['integration'],edit_revision=job['edit_revision'],request_id='remaining',resolutions=[{'path':'c','choice':'theirs'}])
        self.finish(job);self.call('submit',change=ours)
        self.assertEqual(base64.b64decode(self.call('read',stream='main',path='a')['data']),b'\0ours')
        self.assertEqual(base64.b64decode(self.call('read',stream='main',path='c')['data']),b'\0theirs')

    def test_submit_preview_revision_rejects_stale_approval(self):
        change = self.change()
        blob = self.upload(change, b'bytes')
        self.edit(change, [{'path':'a', 'blob':blob}])
        preview = self.call('change_preview', change=change, edit_revision=1)
        self.assertEqual(preview['files'], 1)
        self.call('update_change', change=change, edit_revision=1, request_id='description', description='Edited')
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            self.call('submit', change=change, edit_revision=preview['edit_revision'])
        self.call('submit', change=change, edit_revision=2)
        history = self.call('history', stream='main', path='a')['items'][0]
        self.assertEqual(history['author'], 'admin')
        self.assertEqual(history['description'], 'Edited')
        self.assertEqual(history['action'], 'add')

    def test_file_info_locks_preview_and_binary_metadata(self):
        change = self.change()
        blob = self.upload(change, b'hello\n')
        self.edit(change, [{'path':'a.txt', 'blob':blob}])
        self.call('submit', change=change)
        opened = self.change()
        self.call('checkout', change=opened, paths=['a.txt'], mode='exclusive')
        info = self.call('file_info', stream='main', path='a.txt', workspace='work')
        self.assertEqual(info['head']['number'], 1)
        self.assertEqual(info['local_path'], 'a.txt')
        self.assertEqual(info['holders'][0]['change'], opened)
        self.assertEqual(info['holders'][0]['workspace'], 'work')
        self.assertEqual(self.call('file_preview', stream='main', path='a.txt')['text'], 'hello\n')
        blob = self.upload(opened, b'\0\xff\x01')
        self.edit(opened, [{'path':'a.txt', 'blob':blob}])
        preview = self.call('file_preview', change=opened, stream='main', path='a.txt')
        self.assertEqual(preview['kind'], 'binary')
        self.assertEqual(preview['text'], '00 ff 01')

    def test_integration_acquired_checkouts_block_an_exclusive_competitor_until_cancel(self):
        self.seed()
        source=self.change()
        self.edit(source,[{'path':'a','blob':self.upload(source,b'shelf')}])
        shelf=self.call('shelve',change=source,edit_revision=1,request_id='shelf')
        self.call('revert',change=source)
        destination=self.change()
        job=self.next(self.start(destination,'unshelve',shelf=shelf['code']))
        self.assertTrue(self.call('locks',stream='main',paths=['a'])['items'])
        with self.assertRaisesRegex(ValueError,'Exclusive checkout conflict'):
            self.call('checkout',change=self.change(),paths=['a'],mode='exclusive')
        self.call('integration_cancel',change=destination,edit_revision=job['edit_revision'],integration=job['integration'],request_id='cancel')
        self.call('checkout',change=self.change(),paths=['a'],mode='exclusive')

    def test_cancelled_reconcile_retains_previous_index(self):
        root = Path(self.temp.name) / 'workspace'
        root.mkdir()
        (root/'a.txt').write_text('before')
        cache = Path(self.temp.name)/'local.sqlite'
        class Client:
            rpc = lambda _, action, **kw: self.call(action, **kw)
            progress = lambda *_: None
        client = Client()
        reconcile_workspace(client, 'work', root, cache)
        before = local_page(cache, changes_only=False)
        (root/'b.txt').write_text('after')
        with self.assertRaises(InterruptedError):
            reconcile_workspace(client, 'work', root, cache, cancelled=lambda: True)
        self.assertEqual(local_page(cache, changes_only=False), before)
        reconcile_workspace(client, 'work', root, cache)
        self.assertEqual(len(local_page(cache, changes_only=False)['items']), 2)

    def test_resolve_undo_restores_real_conflict_and_blocks_finish(self):
        self.seed()
        ours, theirs = self.change(), self.change()
        for change, value in ((ours, b'ours'), (theirs, b'theirs')):
            self.edit(change, [{'path':'a', 'blob':self.upload(change, value)}])
        self.call('submit', change=theirs)
        job = self.next(self.start(ours))
        self.assertEqual(job['conflicts'], 1)
        resolved = self.resolve(job, [{'path':'a', 'choice':'ours'}])
        args = dict(change=ours, integration=job['integration'], edit_revision=job['edit_revision'])
        self.assertEqual(self.call('resolved_files', **args)['items'][0]['choice'], 'ours')
        undone = self.call('undo_resolve', **args, paths=['a'], request_id='undo')
        self.assertEqual(undone['conflicts'], 1)
        with self.assertRaisesRegex(ValueError, 'resolve all conflicts'):
            self.finish(job)
        self.call('resolve', **args, request_id='again', resolutions=[{'path':'a','choice':'theirs'}])
        self.finish(job)
        self.assertEqual(base64.b64decode(self.call('read', change=ours, path='a')['data']), b'theirs')

    def test_comparison_uses_real_versions_and_safe_binary_metadata(self):
        first = self.seed()
        second = self.change()
        self.edit(second, [{'path':'a','blob':self.upload(second,b'new\n')}])
        result = self.call('compare_files', left={'stream':'main','path':'a','published_change':first}, right={'stream':'main','path':'a','change':second})
        self.assertEqual(result['kind'], 'text')
        self.assertIn('+new', result['text'])
        binary = self.change()
        self.edit(binary, [{'path':'new','blob':self.upload(binary,b'\0bytes')}])
        result = self.call('compare_files', left={'stream':'main','path':'new'}, right={'stream':'main','path':'new','change':binary})
        self.assertEqual(result['kind'], 'binary')
        self.assertTrue(result['left']['deleted'])
        self.assertEqual(result['right']['size'], 6)

    def test_lost_submit_reply_is_reconciled_without_a_second_publication(self):
        from urllib.error import URLError
        from tactic_client_lib.file_transfer import FileTransferClient
        change = self.change()
        self.edit(change, [{'path':'a','blob':self.upload(change)}])
        publications = []
        def rpc(action, **kwargs):
            result = self.call(action, **kwargs)
            if action == 'submit':
                publications.append(result)
                raise URLError('reply lost after commit')
            return result
        client = FileTransferClient('http://owned-test', self.token, 'files', rpc=rpc)
        self.assertEqual(client.submit(change, edit_revision=1)['state'], 'submitted')
        self.assertEqual(client.submit(change, edit_revision=1)['state'], 'submitted')
        self.assertEqual(len(publications), 1)

    def test_ignore_and_unique_rename_candidates_preserve_ambiguous_adds(self):
        original=self.seed(paths=('old.txt',))
        # Advance Have through the native sync API; no client database emulates server state.
        sync=self.call('sync_begin',workspace='work')
        page=self.call('sync_next',workspace='work',sync=sync['code'])
        self.call('sync_ack',workspace='work',sync=sync['code'],ack_revision=page['ack_revision'],paths=[row['path'] for row in page['items']])
        root=Path(self.temp.name)/'rename-workspace';root.mkdir()
        (root/'new.txt').write_bytes(b'base')
        (root/'.tacticignore').write_text('cache/\n*.tmp\n',encoding='utf-8')
        (root/'cache').mkdir();(root/'cache'/'ignored.bin').write_bytes(b'should not hash')
        (root/'ignored.tmp').write_bytes(b'should not hash')
        cache=Path(self.temp.name)/'rename.sqlite'
        class Client:
            rpc=lambda _,action,**kw:self.call(action,**kw)
            progress=lambda *_:None
        reconcile_workspace(Client(),'work',root,cache)
        rows={row['path']:row for row in local_page(cache,changes_only=False)['items']}
        self.assertEqual(rows['new.txt']['rename_from'],'old.txt')
        self.assertEqual(rows['ignored.tmp']['ignore_rule'],'*.tmp')
        self.assertNotIn('cache/ignored.bin',rows)
        (root/'second.txt').write_bytes(b'base')
        reconcile_workspace(Client(),'work',root,cache)
        rows=local_page(cache,changes_only=False)['items']
        self.assertFalse(any(row.get('rename_from') for row in rows))

    def test_handoff_requires_recipient_acceptance_and_moves_locks_atomically(self):
        artist=self.writer()
        change=self.change()
        self.edit(change,[{'path':'a','blob':self.upload(change)}])
        self.call('checkout',change=change,paths=['a'],mode='exclusive')
        offered=self.call('offer_change',change=change,edit_revision=2,recipient='artist',request_id='offer')
        self.assertEqual(offered['owner'],'admin')
        incoming=self.client(artist,'inspect_change',change=change)
        self.assertFalse(incoming['editable'])
        args=dict(change=change,workspace='artist',edit_revision=3,handoff=offered['handoff']['code'],request_id='accept')
        with self.assertRaises(SecurityException):
            self.call('accept_change',**args)
        accepted=self.client(artist,'accept_change',**args)
        self.assertEqual(accepted['owner'],'artist')
        self.assertEqual(self.client(artist,'accept_change',**args),accepted)
        holders=self.client(artist,'locks',stream='main',paths=['a'])['items'][0]['holders']
        self.assertEqual((holders[0]['owner'],holders[0]['workspace']),('artist','artist'))
        with self.assertRaises(SecurityException):
            self.call('remove_files',change=change,paths=['a'],edit_revision=4,request_id='old-owner')
        self.client(artist,'submit',change=change,edit_revision=4)

    def test_new_checkout_without_upload_cannot_publish_an_empty_file(self):
        change=self.change()
        self.call('checkout',change=change,paths=['missing.txt'])
        preview=self.call('change_preview',change=change)
        self.assertEqual(preview['waiting_uploads'],1)
        with self.assertRaisesRegex(ValueError,'Upload or remove'):
            self.call('submit',change=change)
        self.assertEqual(self.call('status',change=change)['state'],'pending')
        self.edit(change,[{'path':'missing.txt','blob':self.upload(change,b'actual file')}])
        self.assertEqual(self.call('change_preview',change=change)['waiting_uploads'],0)
        self.call('submit',change=change)

    def test_delete_shelved_files_remains_available_after_source_submit(self):
        change=self.change()
        self.edit(change,[{'path':'a','blob':self.upload(change)}])
        args=dict(change=change,edit_revision=1,request_id='shelf')
        shelf=self.call('shelve',**args)
        self.call('submit',change=change)
        updated=self.call('update_shelf',shelf=shelf['code'],shelf_revision=1,paths=['a'],delete=True,request_id='delete')
        self.assertEqual(updated['edit_revision'],2)
        self.assertEqual(self.call('change_files',shelf=shelf['code'])['files'],0)

    def test_rename_conflict_resolves_both_paths_and_retains_history(self):
        self.seed(paths=('z-source',))
        renamed=self.change()
        self.call('rename_files',change=renamed,edit_revision=0,request_id='rename',renames=[{'source':'z-source','target':'a-target'}])
        competing=self.change()
        self.edit(competing,[{'path':'z-source','blob':self.upload(competing,b'changed source')}])
        self.call('submit',change=competing)
        job=self.next(self.start(renamed))
        self.assertEqual(job['conflicts'],2)
        conflicts=self.call('conflicts',change=renamed,edit_revision=job['edit_revision'],integration=job['integration'])['items']
        self.assertEqual({row['rename_partner'] for row in conflicts},{'z-source','a-target'})
        with self.assertRaisesRegex(ValueError,'both sides'):
            self.resolve(job,[{'path':'z-source','choice':'ours'}])
        self.resolve(job,[{'path':path,'choice':'ours'} for path in ('z-source','a-target')])
        self.finish(job)
        self.call('submit',change=renamed)
        self.assertEqual(base64.b64decode(self.call('read',stream='main',path='a-target')['data']),b'base')
        self.assertEqual([row['change'] for row in self.call('history',stream='main',path='a-target')['items'][:2]],[renamed,competing])

    def test_rename_conflict_theirs_cancels_target_and_can_be_undone(self):
        self.seed(paths=('source',))
        renamed=self.change()
        self.call('rename_files',change=renamed,edit_revision=0,request_id='rename',renames=[{'source':'source','target':'target'}])
        competing=self.change()
        self.edit(competing,[{'path':'source','blob':self.upload(competing,b'changed')}])
        self.call('submit',change=competing)
        job=self.next(self.start(renamed))
        self.resolve(job,[{'path':path,'choice':'theirs'} for path in ('source','target')])
        args=dict(change=renamed,edit_revision=job['edit_revision'],integration=job['integration'],request_id='undo',paths=['source','target'])
        self.assertEqual(self.call('undo_resolve',**args)['conflicts'],2)
        self.call('resolve',change=renamed,edit_revision=job['edit_revision'],integration=job['integration'],request_id='again',resolutions=[{'path':path,'choice':'theirs'} for path in ('source','target')])
        self.finish(job)
        self.assertEqual([row['path'] for row in self.call('list',change=renamed)['items']],['source'])
        self.assertEqual(self.call('change_preview',change=renamed)['waiting_uploads'],0)


# Only the lifecycle cases run here; native changelist regression has its own module.
for _name in tuple(vars(test_file_change.FileChangeTest)):
    if _name.startswith('test_'):
        setattr(FileLifecycleTest, _name, None)
