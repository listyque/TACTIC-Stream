"""Bounded reads under long history, bulk rename and idle transfer polling."""
from pathlib import Path
from unittest.mock import patch
import os
import sys
import threading
import unittest

from test_file_project import FileProjectFixture
from test_file_workspace_reads import query_trace
import test_file_workspace as workspaces
from pyasm.common.errors import SecurityException
from tactic_client_lib import file_transfer


class FileReadHotpathTest(FileProjectFixture, unittest.TestCase):
    writer = workspaces.FileWorkspaceTest.writer
    client = workspaces.FileWorkspaceTest.client

    def publish(self, paths):
        change=self.change();blob=self.upload(change)
        self.call('edit',change=change,edit_revision=0,chunk='fresh',operations=[{'path':path,'blob':blob} for path in paths])
        self.call('submit',change=change)
        return change

    def test_folder_page_and_selected_file_seek_keep_siblings_bounded(self):
        self.publish(['folder/%04d.txt' % index for index in range(420)] +
                     ['folder/nested/%04d.txt' % index for index in range(40)])
        page=self.call('read_page',source='list',stream='main',workspace_context='work',
                       prefix='folder/',folder=True,limit=200)
        self.assertEqual(len(page['items']),200)
        self.assertEqual(page['after'],'folder/0199.txt')
        self.assertTrue(all('holders' in row and 'head' in row for row in page['items']))
        last=self.call('read_page',source='list',stream='main',prefix='folder/',folder=True,after='folder/0399.txt')
        self.assertEqual([row['path'] for row in last['items']],['folder/%04d.txt'%index for index in range(400,420)])
        self.assertIsNone(last['after'])
        with self.assertRaises(ValueError):
            self.call('read_page',source='list',stream='main',prefix='folder/',folder=True,after='elsewhere/file')
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen');sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        state=initial_state()
        rows=self.call('browse',stream='main',directory='folder/',limit=1000)['items']
        state.update(workspace='work',stream='main',active_tab='files',files_stream='main',files_source='depot',
            files_prefix='folder/',files_selection=[rows[350]],context_row=rows[350],
            depot_tree=[{**row,'stream':'main'} for row in rows])
        fixture=self;calls=[]
        class Client:
            def rpc(self,action,**values):
                calls.append(action)
                return fixture.call(action,**values)
        state=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','select_tree_files',{},threading.Event())
        self.assertEqual(calls,['read_page'])
        self.assertEqual(len(state['rows']),200)
        self.assertIn('folder/0350.txt',[row['path'] for row in state['rows']])
        self.assertEqual(state['cursor'],'folder/0199.txt')
        self.assertEqual(state['cursors'],[''])
        # Refresh uses the same bounded page inside its existing snapshot, with no second file read.
        calls.clear();Client.url='http://isolated';Client.project='files'
        with patch('thlib.environment.env_server.get_user',return_value='admin'):
            FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','refresh',{},threading.Event())
        self.assertEqual(calls,['workspace_snapshot'])
        self.assertIn('folder/0350.txt',[row['path'] for row in state['rows']])
        self.assertEqual(state['cursor'],'folder/0199.txt')

    def test_preview_and_file_entries_preserve_content_boundaries_and_acl(self):
        published=self.publish(['a.txt','b.txt'])
        result=self.call('file_info',stream='main',path='a.txt',workspace='work',preview=True)
        self.assertEqual(result['preview'],self.call('file_preview',stream='main',path='a.txt'))
        self.assertEqual(result['preview']['text'],'hello')
        with self.assertRaises(ValueError):self.call('file_info',stream='main',path='a.txt',preview='yes')
        entries=self.call('file_entries',stream='main',paths=['a.txt','missing.txt'])
        self.assertEqual(entries['published_change'],published)
        self.assertIsNone(entries['items'][1]['file'])
        with self.assertRaises(ValueError):self.call('file_entries',stream='main',paths=['../escape'])
        with self.assertRaises(ValueError):self.call('file_entries',stream='main',paths=['a.txt']*1001)
        private=self.change();artist=self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist,'file_entries',stream='main',change=private,paths=['a.txt'])

    def test_history_prefetches_versions_and_changes_but_returns_only_published_links(self):
        self.publish(['a.txt'])
        for index in range(29):
            change=self.change();blob=self.upload(change)
            self.call('edit',change=change,edit_revision=0,chunk='fresh',operations=[{'path':'a.txt','blob':blob}])
            self.call('submit',change=change)
        abandoned=self.change();blob=self.upload(abandoned)
        self.call('edit',change=abandoned,edit_revision=0,chunk='abandoned',operations=[{'path':'a.txt','blob':blob}])
        with query_trace() as queries:result=self.call('history',stream='main',path='a.txt',limit=30)
        self.assertEqual([row['number'] for row in result['items']],list(range(30,0,-1)))
        self.assertFalse(result['more'])
        self.assertNotIn(abandoned,[row['change'] for row in result['items']])
        self.assertLessEqual(sum('FROM "version"' in sql for sql in queries),3)
        self.assertLessEqual(sum('FROM "change"' in sql for sql in queries),2)
        bounded=self.call('history',stream='main',path='a.txt',limit=5)
        self.assertEqual(len(bounded['items']),5);self.assertTrue(bounded['more'])
        with self.assertRaises(ValueError):self.call('history',stream='main',path='a.txt',limit=1001)

    def test_changelist_tab_and_polling_have_one_request_each(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen');sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        change=self.call('create_change',workspace='work')
        state=initial_state();state.update(workspace='work',stream='main',change=change,active_tab='pending')
        fixture=self;calls=[]
        class Client:
            def rpc(self,action,**kwargs):
                calls.append(action)
                if action=='transfer_status':return {'task':'owned','state':'running','bytes_done':10}
                return fixture.call(action,**kwargs)
        result=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache','activate_tab',{'tab':'pending'},threading.Event())
        self.assertEqual(calls,['read_batch']);self.assertEqual(result['change']['code'],change['code'])
        calls.clear();result['tasks']=[{'task':'owned','state':'queued'}]
        result=FileWorkspaceController._execute(Client(),result,Path(self.temp.name)/'cache','transfer_status',{'task':'owned'},threading.Event())
        self.assertEqual(calls,['transfer_status']);self.assertEqual(result['tasks'][0]['bytes_done'],10)

    def test_fifty_reconcile_renames_use_one_bounded_entries_read(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen');sys.path.insert(0,'D:/code/th_codex')
        from thlib.ui.file_workspace import initial_state
        from thlib.ui.file_workspace_files import execute_files
        paths=['old%02d.txt'%index for index in range(50)]
        self.publish(paths);change=self.call('create_change',workspace='work')
        root=Path(self.temp.name)/'local';root.mkdir()
        state=initial_state();state.update(workspace='work',root=str(root),stream='main',change=change,view='local',selection_scope='files')
        records={}
        for index,path in enumerate(paths):
            target='new%02d.txt'%index;file=root/target;file.write_bytes(b'hello')
            records[target]={'path':target,'source_path':target,'stream':'main','writable':True,'local_status':'added',
                'rename_from':path,'sha256':file_transfer.digest_file(file),'fingerprint':list(file_transfer.fingerprint(file))}
        state.update(selection_ids=list(records),selection_records=records)
        fixture=self;calls=[]
        class Client:
            def rpc(self,action,**kwargs):calls.append(action);return fixture.call(action,**kwargs)
        self.assertTrue(execute_files(Client(),state,Path(self.temp.name)/'cache','target_files',
            {'operation':'apply_reconcile','target':change['code']},threading.Event()))
        self.assertEqual(calls.count('file_entries'),1);self.assertNotIn('file_info',calls)
        self.assertEqual(calls.count('rename_files'),1)
        self.assertEqual(self.call('status',change=change['code'])['edit_revision'],1)


class PollingTest(unittest.TestCase):
    def test_idle_backoff_resets_on_progress_and_errors_still_surface(self):
        client=file_transfer.FileTransferClient('http://owned.invalid','unused','files')
        status={'state':'running','phase':'verifying','verified_bytes':1}
        results=[status]*12+[{**status,'verified_bytes':2},{'state':'ready'}]
        with patch.object(client,'rpc',side_effect=results),patch.object(file_transfer.time,'sleep') as sleep:
            self.assertEqual(client.wait('owned')['state'],'ready')
        delays=[call.args[0] for call in sleep.call_args_list]
        self.assertEqual(delays[0],.25);self.assertEqual(max(delays),2);self.assertEqual(delays[-1],.25)
        with patch.object(client,'rpc',return_value={'state':'error','error':'verification failed'}):
            with self.assertRaisesRegex(ValueError,'verification failed'):client.wait('owned')
        with patch.object(client,'rpc',return_value={'state':'running'}),patch.object(file_transfer.time,'monotonic',side_effect=[0,2,2,2]):
            with self.assertRaises(TimeoutError):client.wait('owned',timeout=1)

    def test_bulk_polling_resets_instead_of_staying_slow_after_progress(self):
        client=file_transfer.FileTransferClient('http://owned.invalid','unused','files')
        status={'state':'running','files_done':1}
        with patch.object(client,'rpc',side_effect=[status]*6+[{**status,'files_done':2},{'state':'complete'}]),patch.object(file_transfer.time,'sleep') as sleep:
            self.assertEqual(client.wait_bulk('owned')['state'],'complete')
        self.assertGreater(sleep.call_args_list[-2].args[0],1)
        self.assertEqual(sleep.call_args_list[-1].args[0],.25)


if __name__=='__main__':unittest.main()
