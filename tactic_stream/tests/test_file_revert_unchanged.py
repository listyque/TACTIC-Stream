"""Local comparisons, native atomic revert, and unchanged-byte preservation."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import unittest

from pyasm.biz.file_project import FileProjectRecord
from pyasm.common.errors import SecurityException
from tactic_client_lib.file_transfer import FileTransferClient
from tactic_client_lib.file_workspace import revert_unchanged_files
from tactic_stream.server import file_tasks
from test_file_project import FileProjectFixture
import test_file_transfer as transfers


class RevertUnchangedTest(FileProjectFixture, unittest.TestCase):
    context = transfers.FileTransferTest.context
    http = transfers.FileTransferTest.http
    writer = transfers.FileTransferTest.writer
    client = transfers.FileTransferTest.client

    def seed(self, names):
        baseline = self.change()
        blob = self.upload(baseline, b'base')
        for offset in range(0, len(names), 1000):
            self.call('edit', change=baseline, edit_revision=offset//1000, chunk=str(offset),
                operations=[{'path':name, 'blob':blob} for name in names[offset:offset+1000]])
        self.call('submit', change=baseline)
        change = self.change()
        for offset in range(0, len(names), 1000):
            self.call('checkout', change=change, edit_revision=offset//1000, request_id=str(offset),
                paths=names[offset:offset+1000], mode='ordinary')
        root = Path(self.temp.name)/'workspace';root.mkdir()
        for name in names:
            file=root/name;file.parent.mkdir(parents=True, exist_ok=True);file.write_bytes(b'base')
        return change, root

    def run_revert(self, change, root, paths=None, callback=None, cancelled=lambda: False):
        fixture = self
        calls = []
        class Client:
            def rpc(self, action, **options):
                calls.append(action)
                result=fixture.call(action, **options)
                if action=='capabilities':result['files_service_configured']=True
                if callback:callback(action,result)
                return result
            def progress(self, value):
                if callback:callback('progress',value)
            def wait_bulk(self, task):
                with fixture.context():return file_tasks.run_bulk(task)
        result = revert_unchanged_files(Client(), change, root, Path(self.temp.name)/'review.sqlite', paths=paths, cancelled=cancelled)
        self.assertFalse((Path(self.temp.name)/'review.sqlite').exists())
        self.assertFalse(any(name.startswith(('upload','transfer_')) for name in calls))
        return result,calls

    def test_only_content_equal_edits_revert_and_no_local_bytes_change(self):
        change,root=self.seed(['clean.txt','changed.txt','missing.txt','delete.txt','rename.txt','staged.txt'])
        (root/'changed.txt').write_bytes(b'edit');(root/'missing.txt').unlink()
        blob=self.upload(change,b'staged')
        self.call('edit',change=change,edit_revision=1,chunk='edits',operations=[
            {'path':'new.txt','blob':blob},{'path':'staged.txt','blob':blob},{'path':'delete.txt','delete':True}])
        self.call('rename_files',change=change,edit_revision=2,request_id='rename',renames=[{'source':'rename.txt','target':'renamed.txt'}])
        (root/'rename.txt').rename(root/'renamed.txt');(root/'new.txt').write_bytes(b'staged')
        before={p.name:p.read_bytes() for p in root.iterdir()}
        result,calls=self.run_revert(change,root)
        self.assertEqual(result['files_done'],2)
        self.assertEqual(calls.count('remove_files'),1)
        remaining={row['path'] for row in self.call('change_files',change=change)['items']}
        self.assertEqual(remaining,{'changed.txt','missing.txt','delete.txt','rename.txt','renamed.txt','new.txt'})
        self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
        self.assertEqual(self.call('status',change=change)['state'],'pending')

    def test_explicit_selection_and_no_matches_are_successful(self):
        change,root=self.seed(['a.txt','b.txt'])
        result,_=self.run_revert(change,root,paths=['b.txt'])
        self.assertEqual(result['files_done'],1)
        (root/'a.txt').write_bytes(b'changed')
        result,calls=self.run_revert(change,root)
        self.assertEqual(result['files_done'],0);self.assertNotIn('remove_files',calls)
        self.assertEqual(self.call('change_files',change=change)['files'],1)

    def test_changed_local_candidate_or_stale_changelist_prevents_all_removal(self):
        change,root=self.seed(['a.txt','b.txt'])
        def modified(action,result):
            if action=='workspace_paths':(root/'a.txt').write_bytes(b'new edit')
            if action=='change_files':
                self.call('update_change',change=change,edit_revision=1,request_id='other',description='other client')
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            self.run_revert(change,root,callback=modified)
        self.assertEqual(self.call('change_files',change=change)['files'],2)
        self.assertEqual((root/'a.txt').read_bytes(),b'new edit')

    def test_more_than_one_page_is_reverted_atomically_and_checked_on_server(self):
        names=['files/%04d.txt'%index for index in range(1003)]
        change,root=self.seed(names)
        original=FileProjectRecord._call_triggers
        def fail(record,*args,**kwargs):
            original(record,*args,**kwargs)
            data=record.get_json_value('data')
            if record.get_code()==change and data.get('edit_revision')==4:
                raise ValueError('late revert failure')
        with patch.object(FileProjectRecord,'_call_triggers',fail):
            with self.assertRaisesRegex(ValueError,'late revert failure'):
                self.run_revert(change,root)
        self.assertEqual(self.call('change_files',change=change)['files'],1003)
        self.assertEqual(self.call('status',change=change)['edit_revision'],2)
        result,calls=self.run_revert(change,root)
        self.assertEqual(result['files_done'],1003)
        self.assertEqual(calls.count('select_unchanged'),2)
        self.assertEqual(calls.count('bulk_begin'),1)
        self.assertEqual(self.call('change_files',change=change)['files'],0)
        self.assertTrue(all((root/name).read_bytes()==b'base' for name in names))

    def test_local_edit_after_comparison_and_cancellation_keep_checkout(self):
        change,root=self.seed(['a.txt'])
        def modify(action,value):
            if action=='progress' and value['files_done']==1:
                (root/'a.txt').write_bytes(b'edited during comparison')
        with self.assertRaisesRegex(ValueError,'changed during comparison'):
            self.run_revert(change,root,callback=modify)
        with self.assertRaises(InterruptedError):
            self.run_revert(change,root,cancelled=lambda:True)
        self.assertEqual(self.call('change_files',change=change)['files'],1)
        self.assertEqual((root/'a.txt').read_bytes(),b'edited during comparison')
        self.assertFalse((Path(self.temp.name)/'review.sqlite').exists())

    def test_native_selection_rejects_forged_digest_additions_and_other_owner(self):
        change,root=self.seed(['a.txt'])
        for digest in ('bad',None):
            with self.assertRaisesRegex(ValueError,'differs'):
                self.call('select_unchanged',change=change,edit_revision=1,request_id=str(digest),
                    files=[{'path':'a.txt','sha256':digest}])
        artist=self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist,'select_unchanged',change=change,edit_revision=1,request_id='foreign',
                files=[{'path':'a.txt','sha256':sha256(b'base').hexdigest()}])

    def test_actual_http_client_reverts_without_uploading(self):
        import threading
        from thlib.ui.file_workspace import initial_state
        from thlib.ui.file_workspace_files import execute_files
        change,root=self.seed(['a.txt','b.txt'])
        (root/'b.txt').write_bytes(b'changed')
        state=initial_state()
        state.update(change=self.call('status',change=change),workspace='work',stream='main',root=str(root),selection_scope='changes')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            self.assertTrue(execute_files(client,state,Path(self.temp.name),'revert_unchanged_change',{},threading.Event()))
        self.assertEqual(state['progress']['files_done'],1)
        self.assertEqual(state['operation_notice']['level'],'INFO')
        self.assertEqual([row['path'] for row in self.call('change_files',change=change)['items']],['b.txt'])
