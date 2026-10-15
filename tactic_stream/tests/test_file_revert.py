"""Native atomic revert and workspace-only optional local Trash cleanup."""
from pathlib import Path
from unittest.mock import patch
import os
import sys
import threading
import unittest

from test_file_project import FileProjectFixture
import test_file_workspace as workspaces
import test_file_transfer as transfers
from tactic_client_lib.file_transfer import FileTransferClient
from pyasm.biz.file_project import FileProjectRecord
from pyasm.common.errors import SecurityException

sys.path.insert(0,'D:/code/th_codex')
from thlib.ui.file_workspace import initial_state
from thlib.ui.file_workspace_revert import revert_files


class FileRevertTest(FileProjectFixture,unittest.TestCase):
    http=transfers.FileTransferTest.http
    writer=workspaces.FileWorkspaceTest.writer
    client=workspaces.FileWorkspaceTest.client

    def pending(self, paths):
        change=self.change();blob=self.upload(change)
        self.call('edit',change=change,edit_revision=0,chunk='files',operations=[{'path':path,'blob':blob} for path in paths])
        return self.call('status',change=change)

    def worker(self, change, action='revert', values=None, callback=None):
        root=Path(self.temp.name)/'local';root.mkdir(exist_ok=True)
        cache=Path(self.temp.name)/'cache';cache.mkdir(exist_ok=True)
        state=initial_state();state.update(workspace='work',root=str(root),stream='main',change=change)
        fixture=self;calls=[]
        class Client:
            def rpc(self,operation,**kwargs):
                calls.append(operation);result=fixture.call(operation,**kwargs)
                if callback:callback(operation,result)
                return result
        values=values or {'change':change['code'],'edit_revision':change['edit_revision']}
        revert_files(Client(),state,cache,action,values,threading.Event())
        return state,calls

    def test_default_revert_keeps_local_files_and_has_one_mutation(self):
        change=self.pending(['new.txt']);root=Path(self.temp.name)/'local';root.mkdir()
        file=root/'new.txt';file.write_bytes(b'new local bytes')
        state,calls=self.worker(change)
        self.assertEqual(calls,['revert']);self.assertEqual(file.read_bytes(),b'new local bytes')
        self.assertEqual(self.call('status',change=change['code'])['state'],'reverted')
        self.assertEqual(list((Path(self.temp.name)/'cache').glob('revert-*')),[])

    def test_selected_revert_finds_own_changes_and_only_trashes_new_files(self):
        baseline=self.pending(['tracked.txt']);self.call('submit',change=baseline['code'])
        first=self.pending(['tracked.txt','added.txt']);second=self.pending(['other.txt'])
        root=Path(self.temp.name)/'local';root.mkdir()
        for path in ('tracked.txt','added.txt','other.txt','unselected.txt'):(root/path).write_bytes(b'local '+path.encode())
        removed=[]
        def trash(path):
            file=Path(path);self.assertTrue(file.is_relative_to(root));removed.append(file.name);file.unlink();return True
        with patch('thlib.ui.file_workspace_revert.QFile.moveToTrash',side_effect=trash):
            state,calls=self.worker(first,'revert_files',{'delete_not_in_depot':True,'files':[
                {'stream':'main','path':path} for path in ('tracked.txt','added.txt','other.txt')]})
        self.assertEqual(set(removed),{'added.txt','other.txt'})
        self.assertTrue((root/'tracked.txt').exists());self.assertTrue((root/'unselected.txt').exists())
        self.assertEqual(self.call('change_files',change=first['code'])['items'],[])
        self.assertEqual(self.call('change_files',change=second['code'])['items'],[])
        self.assertEqual(state['progress']['deleted_files'],2)
        self.assertTrue(state['local_dirty']);self.assertEqual(calls.count('revert_files'),1)

    def test_trigger_failure_rolls_back_all_selected_changes_before_local_cleanup(self):
        first=self.pending(['a.txt']);second=self.pending(['b.txt'])
        root=Path(self.temp.name)/'local';root.mkdir()
        for name in ('a.txt','b.txt'):(root/name).write_bytes(b'keep')
        original=FileProjectRecord._call_triggers
        def fail(record,*args,**kwargs):
            original(record,*args,**kwargs)
            if record.get_base_search_type()=='file_project/change' and record.get_code()==max(first['code'],second['code']):
                raise ValueError('late revert trigger failure')
        with patch.object(FileProjectRecord,'_call_triggers',fail),patch('thlib.ui.file_workspace_revert.QFile.moveToTrash') as trash:
            with self.assertRaisesRegex(ValueError,'late revert trigger'):
                self.worker(first,'revert_files',{'delete_not_in_depot':True,'files':[
                    {'stream':'main','path':name} for name in ('a.txt','b.txt')]})
            trash.assert_not_called()
        for change,name in ((first,'a.txt'),(second,'b.txt')):
            self.assertEqual([row['path'] for row in self.call('change_files',change=change['code'])['items']],[name])
            self.assertEqual((root/name).read_bytes(),b'keep')

    def test_stale_revision_and_foreign_owner_cannot_revert(self):
        change=self.pending(['new.txt'])
        self.call('update_change',change=change['code'],edit_revision=1,request_id='edit',description='changed')
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            self.call('revert',change=change['code'],edit_revision=1,request_id='stale')
        artist=self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist,'revert_files',workspace='artist',request_id='foreign',groups=[
                {'change':change['code'],'edit_revision':2,'paths':['new.txt']}])
        with self.assertRaises(ValueError):
            self.call('revert_files',workspace='work',request_id='invalid',groups=[
                {'change':change['code'],'edit_revision':2,'paths':[['new.txt']]}])

    def test_changes_after_server_revert_are_preserved_and_newly_published_file_is_kept(self):
        for publish in (False,True):
            name='publish.txt' if publish else 'edited.txt';change=self.pending([name])
            root=Path(self.temp.name)/'local';root.mkdir(exist_ok=True);file=root/name;file.write_bytes(b'before')
            def changed(operation,result):
                if operation!='revert':return
                if publish:
                    later=self.pending([name]);self.call('submit',change=later['code'])
                else:file.write_bytes(b'changed after server commit')
            with patch('thlib.ui.file_workspace_revert.QFile.moveToTrash') as trash:
                state,_=self.worker(change,values={'change':change['code'],'edit_revision':1,'delete_not_in_depot':True},callback=changed)
                trash.assert_not_called()
            self.assertTrue(file.exists());self.assertEqual(state['operation_notice']['level'],'WARNING')

    def test_plan_and_full_cleanup_page_more_than_a_thousand_paths(self):
        root=Path(self.temp.name)/'local';root.mkdir()
        change=self.change();blob=self.upload(change)
        paths=['f%04d.txt'%index for index in range(1003)]
        for start in (0,1000):
            page=paths[start:start+1000]
            self.call('edit',change=change,edit_revision=start//1000,chunk=str(start),operations=[{'path':name,'blob':blob} for name in page])
            for name in page:(root/name).write_bytes(b'local')
        info=self.call('status',change=change)
        def trash(path):Path(path).unlink();return True
        with patch('thlib.ui.file_workspace_revert.QFile.moveToTrash',side_effect=trash):
            state,calls=self.worker(info,values={'change':change,'edit_revision':2,'delete_not_in_depot':True})
        self.assertEqual(calls.count('revert_plan'),2)
        self.assertEqual(state['progress']['deleted_files'],1003)
        self.assertFalse(list(root.iterdir()))

    def test_revert_pair_and_receipt_are_complete_and_idempotent(self):
        baseline=self.pending(['old.txt']);self.call('submit',change=baseline['code'])
        change=self.call('create_change',workspace='work')
        self.call('rename_files',change=change['code'],edit_revision=0,request_id='rename',renames=[{'source':'old.txt','target':'new.txt'}])
        plan=self.call('revert_plan',workspace='work',files=[{'stream':'main','path':'new.txt','change':change['code']}])
        self.assertEqual(set(plan['groups'][0]['paths']),{'old.txt','new.txt'})
        self.assertFalse(any(row['delete_local'] for row in plan['items']))
        options={'workspace':'work','groups':plan['groups'],'request_id':'same'}
        self.assertEqual(self.call('revert_files',**options),self.call('revert_files',**options))
        whole=self.call('create_change',workspace='work')
        options={'change':whole['code'],'edit_revision':0,'request_id':'same'}
        self.assertEqual(self.call('revert',**options),self.call('revert',**options))

    def test_native_http_exposes_authorized_plan_and_atomic_revert(self):
        change=self.pending(['new.txt'])
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            plan=client.rpc('revert_plan',workspace='work',files=[{'stream':'main','path':'new.txt'}])
            self.assertTrue(plan['items'][0]['delete_local'])
            result=client.rpc('revert_files',workspace='work',groups=plan['groups'],request_id='http-revert')
            self.assertEqual(result['changes'][0]['code'],change['code'])
            self.assertEqual(client.rpc('change_files',change=change['code'])['items'],[])

    def test_real_qt_trash_only_removes_owned_new_workspace_file(self):
        change=self.pending(['revert-real-trash.txt'])
        root=Path(self.temp.name)/'local';root.mkdir()
        file=root/'revert-real-trash.txt';file.write_bytes(b'owned revert integration fixture')
        self.assertTrue(file.resolve().is_relative_to(Path(self.temp.name).resolve()))
        state,_=self.worker(change,values={'change':change['code'],'edit_revision':1,'delete_not_in_depot':True})
        self.assertFalse(file.exists())
        self.assertEqual(state['progress']['deleted_files'],1)


if __name__=='__main__':unittest.main()
