"""Owned file operations, operation journals and native row callback preservation."""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError
from test_file_project import FileProjectFixture
import test_file_transfer as transfer

sys.path.insert(0,'D:/code/th_codex')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Material')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QSG_RENDER_LOOP','basic')
from PySide6.QtGui import QGuiApplication
from thlib.environment import env_mode,env_inst,env_server
from thlib.ui.file_workspace import FileWorkspaceController,initial_state
from thlib.ui.file_workspace_recovery import operation_context,save_operation,load_operation,resume_operation
from thlib.side.client.tactic_client_lib.file_workspace import rename_workspace_file,reconcile_workspace,pending_local_counts,inspect_local
from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient


class FileWorkspaceCompletionTest(FileProjectFixture,unittest.TestCase):
    http=transfer.FileTransferTest.http
    publish=transfer.FileTransferTest.publish
    edit=transfer.FileTransferTest.edit
    client=transfer.FileTransferTest.client
    context=transfer.FileTransferTest.context
    writer=transfer.FileTransferTest.writer

    @classmethod
    def setUpClass(cls):cls.app=QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        FileProjectFixture.setUp(self)
        for target,name,value in ((env_mode,'current_path',self.temp.name),(env_inst,'projects',{}),(env_server,'get_user',lambda:'admin')):
            scope=patch.object(target,name,value);scope.start();self.addCleanup(scope.stop)

    def test_native_local_rename_preserves_dirty_bytes_and_retry_after_lost_reply(self):
        root=Path(self.temp.name)/'editing';journal=Path(self.temp.name)/'moves'/'rename.json'
        self.publish({'src/old.txt':b'base'})
        change=self.change()
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files');client.download('work',root)
            (root/'src/old.txt').write_bytes(b'local edits')
            native=client.rpc
            def lost(action,**kwargs):
                result=native(action,**kwargs)
                if action=='rename_files':raise URLError('lost response after committed move')
                return result
            with patch.object(client,'rpc',side_effect=lost),self.assertRaises(URLError):
                rename_workspace_file(client,change,root,'src/old.txt','new/deep/name.txt',journal)
            self.assertTrue(journal.exists());self.assertEqual((root/'src/old.txt').read_bytes(),b'local edits')
            result=rename_workspace_file(client,change,root,'src/old.txt','new/deep/name.txt',journal)
            self.assertEqual(result['edit_revision'],1)
            self.assertFalse((root/'src/old.txt').exists())
            self.assertEqual((root/'new/deep/name.txt').read_bytes(),b'local edits')
            self.assertFalse(journal.exists())
            self.assertEqual({row['action'] for row in client.rpc('change_files',change=change)['items']},{'move/add','move/delete'})

    def test_native_rename_rejection_keeps_local_original_and_destinations(self):
        root=Path(self.temp.name)/'local';root.mkdir();(root/'old').write_bytes(b'local')
        change=self.change();journal=Path(self.temp.name)/'move.json'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            with self.assertRaisesRegex(Exception,'Rename source is missing'):
                rename_workspace_file(client,change,root,'old','new',journal)
        self.assertEqual((root/'old').read_bytes(),b'local');self.assertFalse((root/'new').exists())
        self.assertEqual(self.call('status',change=change)['edit_revision'],0)

    def test_reconcile_counts_unstaged_per_change_without_counting_uploaded_bytes(self):
        root=Path(self.temp.name)/'local';cache=Path(self.temp.name)/'local.sqlite'
        self.publish({'a.txt':b'base'})
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files');client.download('work',root)
            change=client.rpc('create_change',workspace='work')
            client.rpc('checkout',change=change['code'],edit_revision=0,paths=['a.txt'],mode='ordinary',request_id='open')
            (root/'a.txt').write_bytes(b'dirty local')
            reconcile_workspace(client,'work',root,cache)
            current=client.rpc('status',change=change['code'])
            counts=pending_local_counts(cache,current['code'],current['edit_revision'])
            self.assertEqual((counts['known'],counts['files'],counts['bytes']),(True,1,11))
            client.upload(current['code'],root,Path(self.temp.name)/'upload.sqlite',sources=[('a.txt',root/'a.txt')])
            reconcile_workspace(client,'work',root,cache)
            current=client.rpc('status',change=change['code'])
            self.assertEqual(pending_local_counts(cache,current['code'],current['edit_revision'])['files'],0)
            row=client.rpc('file_states',workspace='work',paths=[{'stream':'main','path':'a.txt'}])['items'][0]
            inspect_local(cache,root,[row]);self.assertEqual(row['local_number'],1);self.assertTrue(row['local_modified'])
            self.assertFalse(pending_local_counts(cache,current['code'],current['edit_revision']+1)['known'])

    def test_recovery_does_not_repeat_a_committed_submit(self):
        root=Path(self.temp.name)/'root';cache=Path(self.temp.name)/'operations';cache.mkdir()
        change=self.change();blob=self.upload(change,b'new')
        self.call('edit',change=change,edit_revision=0,chunk='fresh',operations=[{'path':'a','blob':blob}])
        state=initial_state();state.update(workspace='work',root=str(root),stream='main',change=self.call('status',change=change))
        save_operation(cache,operation_context(state,'submit',{}))
        self.call('submit',change=change)
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            action,_=resume_operation(client,state,cache,threading.Event())
        self.assertEqual(action,'refresh');self.assertEqual(state['change']['state'],'submitted')
        self.assertEqual(state['change']['submitted_revision'],1)

    def test_stale_read_completion_cannot_release_the_new_worker(self):
        from test_handler_file_workspace_ui import Application
        application=Application();controller=FileWorkspaceController(application)
        try:
            current=object();controller._read_worker=current;controller._read_worker_generation=12
            state=initial_state();state['rows']=[{'path':'stale'}]
            controller._read_result((state,11))
            self.assertIs(controller._read_worker,current);self.assertEqual(controller.data['rows'],[])
            controller._read_worker=None
        finally:controller.shutdown();controller.deleteLater();application.deleteLater()

    def test_cold_client_resumes_exact_upload_after_lost_progress_reply(self):
        from thlib.ui.file_workspace_recovery import cache_directory
        root=Path(self.temp.name)/'cold-root';root.mkdir()
        (root/'selected.txt').write_bytes(b'new selected bytes')
        (root/'leave-local.txt').write_bytes(b'unselected local bytes')
        change=self.change()
        state=initial_state();state.update(workspace='work',root=str(root),stream='main',change=self.call('status',change=change),selected=['selected.txt'])
        with self.http(worker=True) as url:
            cache=cache_directory(self.temp.name,url,'admin','files','work',str(root));cache.mkdir(parents=True)
            save_operation(cache,operation_context(state,'shelve_selected',{'paths':['selected.txt']}))
            retained={}
            def lost_reply(progress):
                retained.update({key:progress[key] for key in ('task','change','workspace','journal','state') if key in progress})
                save_operation(cache,retained,'operation_progress')
                if progress.get('files_done')==1 and progress.get('state')=='collecting':raise URLError('Lost upload reply')
            client=FileTransferClient(url,self.token,'files',progress=lost_reply)
            with self.assertRaises(URLError):
                client.upload(change,root,cache/'outbox.sqlite',sources=[('selected.txt',root/'selected.txt')])
            del client
            fresh=initial_state();fresh.update(workspace='work',root=str(root),stream='main')
            fresh['recovery']=load_operation(cache,fresh)
            self.assertEqual(fresh['recovery']['snapshot']['selected'],['selected.txt'])
            action,_=resume_operation(FileTransferClient(url,self.token,'files'),fresh,cache,threading.Event())
            self.assertEqual(action,'refresh');self.assertEqual(fresh['progress']['state'],'ready')
        self.assertEqual([row['path'] for row in self.call('change_files',change=change)['items']],['selected.txt'])
        self.assertEqual((root/'leave-local.txt').read_bytes(),b'unselected local bytes')

    def test_progress_rate_requires_measured_time_and_phase_changes_reset_eta(self):
        from thlib.side.client.tactic_client_lib import file_transfer
        values=[];client=FileTransferClient('http://owned.invalid','unused','files',progress=values.append)
        status={'task':'owned','kind':'upload','state':'collecting','phase':'uploading','total_known':True,
                'bytes_total':1000,'files_total':2,'files_done':0}
        with patch.object(file_transfer.time,'monotonic',side_effect=[0,0.5,1.2,1.4]):
            client.progress({**status,'bytes_done':0})
            client.progress({**status,'bytes_done':200})
            self.assertNotIn('eta_seconds',values[-1])
            client.progress({**status,'bytes_done':600})
            self.assertEqual(values[-1]['bytes_per_second'],500)
            self.assertAlmostEqual(values[-1]['eta_seconds'],.8)
            client.progress({**status,'phase':'verifying','verified_bytes':100,'verified_files':1})
            self.assertNotIn('eta_seconds',values[-1])
            self.assertEqual(values[-1]['phase_bytes_done'],100)
            self.assertEqual(values[-1]['operation_stage'],5)

    def test_task_error_retains_file_attribution_at_the_sdk_boundary(self):
        client=FileTransferClient('http://owned.invalid','unused','files')
        with patch.object(client,'rpc',return_value={'state':'error','error':'atomic batch failed',
            'file_error':{'path':'nested/a.bin','operation':'verification','cause':'checksum mismatch'}}):
            with self.assertRaises(ValueError) as error:client.wait('owned')
        self.assertEqual(error.exception.file_error['path'],'nested/a.bin')

    def test_only_last_staging_chunk_uses_faster_completion_wait(self):
        from thlib.side.client.tactic_client_lib import file_transfer
        client=FileTransferClient('http://owned.invalid','unused','files')
        status={'kind':'upload','task':'owned','state':'running','phase':'staging','files_total':3000}
        with patch.object(client,'rpc',side_effect=[{**status,'staged_files':1000},{**status,'staged_files':2000},
            {**status,'state':'ready','staged_files':3000}]),patch.object(file_transfer.time,'sleep') as wait:
            self.assertEqual(client.wait('owned')['state'],'ready')
        self.assertEqual([call.args[0] for call in wait.call_args_list],[.25,.1])
