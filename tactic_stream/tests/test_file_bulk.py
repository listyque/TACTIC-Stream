"""Real queued selections, atomic late failures, cancellation and owner isolation."""
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import find, access
from pyasm.biz.file_job_signals import FileJobSignals
from pyasm.common.errors import SecurityException
from pyasm.command import Trigger
from tactic_stream.server import file_tasks
from test_file_project import FileProjectFixture
import test_file_transfer as transfers


class LateCheckoutFailure(Trigger):
    def execute(self):
        row=self.get_caller().get_json_value('data')
        if row['path']=='dir/1004.txt':
            raise ValueError('late native checkout failure')


class FileBulkTest(FileProjectFixture,unittest.TestCase):
    context=transfers.FileTransferTest.context
    http=transfers.FileTransferTest.http
    writer=transfers.FileTransferTest.writer
    client=transfers.FileTransferTest.client

    def seed(self,count=1105):
        change=self.change();blob=self.upload(change,b'fresh bulk bytes')
        for offset in range(0,count,1000):
            self.call('edit',change=change,edit_revision=offset//1000,chunk='seed'+str(offset),
                      operations=[{'path':'dir/%04d.txt'%index,'blob':blob} for index in range(offset,min(count,offset+1000))])
        self.call('submit',change=change)

    def begin(self,change,operation='checkout',**kwargs):
        status=self.call('status',change=change)
        select=self.call('select_query',source='depot' if operation=='checkout' else 'change',stream='main',change=change,prefix='dir/')
        args=dict(change=change,edit_revision=status['edit_revision'],selection=select['selection'],operation=operation,request_id='job-'+operation,**kwargs)
        return self.call('bulk_begin',**args),args

    def perform(self,task):
        with self.context():
            return file_tasks.run_bulk(task)

    def test_pinned_checkout_is_server_owned_atomic_and_idempotent(self):
        self.seed();change=self.change();job,args=self.begin(change)
        self.assertEqual(self.call('bulk_begin',**args)['task'],job['task'])
        self.assertEqual(self.call('change_files',change=change)['items'],[])
        with self.assertRaisesRegex(ValueError,'bulk operation'):
            self.call('checkout',change=change,edit_revision=0,request_id='edit',paths=['dir/0000.txt'])
        result=self.perform(job['task'])
        self.assertEqual((result['state'],result['files_done']),('complete',1105))
        self.assertEqual(self.call('change_files',change=change)['files'],1105)
        self.assertEqual(self.call('bulk_begin',**args)['state'],'complete')
        self.assertNotIn('active_bulk',self.call('status',change=change))

    def test_late_trigger_failure_rolls_back_first_chunk_and_locks(self):
        self.seed();change=self.change();job,_=self.begin(change)
        self.api.dispatch('insert',(self.ticket,'config/trigger',{'code':'late-checkout','event':'change|file_project/checkout',
            'class_name':'test_file_bulk.LateCheckoutFailure','mode':'same process,same transaction'}))
        with self.assertRaisesRegex(ValueError,'late native'):
            self.perform(job['task'])
        self.assertEqual(self.call('bulk_status',task=job['task'])['state'],'error')
        self.assertEqual(self.call('status',change=change)['edit_revision'],0)
        self.assertEqual(self.call('change_files',change=change)['items'],[])
        self.assertFalse(self.call('locks',stream='main',paths=['dir/0000.txt'])['items'])

    def test_cancel_during_transaction_uses_signal_and_rolls_back_every_path(self):
        self.seed();change=self.change();job,_=self.begin(change)
        original=FileJobSignals.progress
        def cancel(signals,value):
            original(signals,value)
            signals.cancel()
        with patch.object(FileJobSignals,'progress',cancel):
            result=self.perform(job['task'])
        self.assertEqual(result['state'],'cancelled')
        self.assertEqual(self.call('change_files',change=change)['items'],[])
        self.assertEqual(self.call('status',change=change)['edit_revision'],0)

    def test_bulk_move_and_remove_preserve_native_revision_and_selected_scope(self):
        self.seed();source=self.change();job,_=self.begin(source);self.perform(job['task'])
        target=self.change()
        job,_=self.begin(source,'move_files',target_change=target,target_edit_revision=0)
        self.assertEqual(self.perform(job['task'])['files_done'],1105)
        self.assertEqual(self.call('change_files',change=source)['files'],0)
        self.assertEqual(self.call('change_files',change=target)['files'],1105)
        selection=self.call('select_query',source='change',change=target,prefix='dir/',name='100')
        job=self.call('bulk_begin',change=target,selection=selection['selection'],operation='remove_files',edit_revision=2,request_id='remove')
        self.assertEqual(self.perform(job['task'])['files_done'],12)
        self.assertEqual(self.call('change_files',change=target)['files'],1093)

    def test_private_job_and_selection_cannot_be_borrowed_by_another_user(self):
        self.seed(2);change=self.change();job,args=self.begin(change)
        artist=self.writer()
        for action,kwargs in [('bulk_status',{'task':job['task']}),('bulk_cancel',{'task':job['task']}),('bulk_begin',args)]:
            with self.subTest(action=action),self.assertRaises(SecurityException):
                self.client(artist,action,**kwargs)

    def test_bulk_mark_delete_is_staged_until_atomic_submit(self):
        self.seed();change=self.change();job,_=self.begin(change);self.perform(job['task'])
        job,_=self.begin(change,'mark_delete')
        self.assertEqual(self.perform(job['task'])['files_done'],1105)
        self.assertEqual(self.call('change_preview',change=change)['actions'],{'delete':1105})
        self.assertFalse(self.call('file_info',stream='main',path='dir/0000.txt')['file'].get('deleted'))
        self.call('submit',change=change)
        self.assertTrue(self.call('file_info',stream='main',path='dir/0000.txt')['file']['deleted'])

    def test_inclusive_range_is_pinned_paged_and_only_mutates_selected_paths(self):
        self.seed();change=self.change()
        selected=self.call('select_query',source='depot',stream='main',prefix='dir/',start_path='dir/0999.txt',end_path='dir/1003.txt')
        page=self.call('selection_page',selection=selected['selection'],limit=2)
        self.assertEqual([row['path'] for row in page['items']],['dir/0999.txt','dir/1000.txt'])
        job=self.call('bulk_begin',change=change,edit_revision=0,selection=selected['selection'],operation='checkout',request_id='range')
        self.assertEqual(self.perform(job['task'])['files_done'],5)
        self.assertEqual(self.call('change_files',change=change)['files'],5)
        self.assertEqual(len(self.call('bulk_items',task=job['task'])['items']),5)

    def test_queue_worker_executes_job_without_client_chunk_requests(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        self.seed(1005);change=self.change()
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            selected=client.rpc('select_query',source='depot',stream='main',prefix='dir/')
            job=client.rpc('bulk_begin',change=change,selection=selected['selection'],operation='checkout',edit_revision=0,request_id='http')
            from time import monotonic,sleep
            deadline=monotonic()+20
            while job['state'] not in ('complete','cancelled','error') and monotonic()<deadline:
                sleep(.1);job=client.rpc('bulk_status',task=job['task'])
            self.assertEqual(job['state'],'complete',job)
            self.assertEqual(job['files_done'],1005)

    def test_http_cancel_remains_responsive_during_atomic_write(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from tactic_client_lib.file_transfer import FileTransferClient
        self.seed();change=self.change();job,_=self.begin(change)
        started,released=threading.Event(),threading.Event()
        active=self.call('workspace_active')
        self.call('switch_workspace',workspace='work',revision=active['revision'],request_id='active')
        self.assertEqual(self.call('workspace_switch_preview',workspace='work')['active_bulk_tasks'],1)
        original=FileJobSignals.progress
        def pause(signals,value):
            original(signals,value);started.set()
            if not released.wait(10):raise TimeoutError('Test did not release its worker')
        with self.http() as url,ThreadPoolExecutor(max_workers=1) as pool,patch.object(FileJobSignals,'progress',pause):
            future=pool.submit(self.perform,job['task'])
            try:
                self.assertTrue(started.wait(10))
                client=FileTransferClient(url,self.token,'files')
                self.assertEqual(client.rpc('bulk_status',task=job['task'])['state'],'running')
                self.assertTrue(client.rpc('bulk_cancel',task=job['task'])['cancel_requested'])
            finally:released.set()
            self.assertEqual(future.result(timeout=10)['state'],'cancelled')
        self.assertEqual(self.call('change_files',change=change)['files'],0)
        self.assertEqual(self.call('workspace_switch_preview',workspace='work')['active_bulk_tasks'],0)

    def test_lost_commit_reply_recovers_completed_job(self):
        from pyasm.command import Command
        self.seed(3);change=self.change();job,_=self.begin(change)
        original=Command.execute_cmd
        def lost(command,*args,**kwargs):
            result=original(command,*args,**kwargs)
            if command.kwargs.get('action')=='bulk_run':raise OSError('lost committed reply')
            return result
        with patch.object(Command,'execute_cmd',side_effect=lost):
            self.assertEqual(self.perform(job['task'])['state'],'complete')
        self.assertEqual(self.call('change_files',change=change)['files'],3)

    def test_partial_rename_range_fails_without_moving_either_side(self):
        self.seed(2);source=self.change();target=self.change()
        self.call('rename_files',change=source,edit_revision=0,renames=[{'source':'dir/0000.txt','target':'dir/renamed.txt'}],request_id='rename')
        selected=self.call('select_query',source='change',change=source,start_path='dir/renamed.txt',end_path='dir/renamed.txt')
        job=self.call('bulk_begin',change=source,edit_revision=1,target_change=target,target_edit_revision=0,selection=selected['selection'],operation='move_files',request_id='partial-pair')
        with self.assertRaisesRegex(ValueError,'both sides'):
            self.perform(job['task'])
        self.assertEqual(self.call('change_files',change=source)['files'],2)
        self.assertEqual(self.call('change_files',change=target)['files'],0)
