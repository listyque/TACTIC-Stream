"""Historical subtree sync, per-file revisions, force repair and native ACLs."""
from datetime import datetime, timezone
from pathlib import Path
from time import time_ns
import unittest
from unittest.mock import patch

from test_file_project import FileProjectFixture
import test_file_transfer as transfers
from tactic_client_lib.file_transfer import FileTransferClient


class FileRevisionTest(FileProjectFixture, unittest.TestCase):
    http=transfers.FileTransferTest.http
    writer=transfers.FileTransferTest.writer
    client=transfers.FileTransferTest.client
    context=transfers.FileTransferTest.context

    def publish(self, files, stamp):
        change=self.call('create_change',workspace='work')
        operations=[{'path':path,'blob':self.upload(change['code'],content)} for path,content in files.items()]
        self.call('edit',change=change['code'],edit_revision=0,chunk='files',operations=operations)
        with patch('tactic.command.file_project_cmd.time_ns',return_value=stamp*1000):
            self.call('submit',change=change['code'])
        return self.call('status',change=change['code'])

    def history(self):
        stamp=time_ns()//1000+1000000
        first=self.publish({'docs/deep/readme.txt':b'first','docs/neighbor.txt':b'neighbor','outside.txt':b'outside'},stamp)
        second=self.publish({'docs/deep/readme.txt':b'second','docs/deep/new.txt':b'new'},stamp+1000000)
        return first,second,datetime.fromtimestamp(stamp/1000000,timezone.utc).isoformat()

    def test_indexed_snapshot_revision_date_and_changelist(self):
        first,second,date=self.history()
        for selector in ({'revision':1},{'at_date':date},{'changelist':first['number']}):
            page=self.call('list',stream='main',prefix='docs/deep/',**selector)
            self.assertEqual([row['path'] for row in page['items']],['docs/deep/readme.txt'])
            self.assertEqual(page['items'][0]['number'],1)
            self.assertEqual(page['published_change'],first['code'])
        page=self.call('list',stream='main',path='docs/deep/readme.txt',file_revision=1)
        self.assertEqual(page['items'][0]['number'],1)
        artist=self.writer()
        self.assertEqual(self.client(artist,'list',stream='main',path='docs/deep/readme.txt',file_revision=1)['items'][0]['number'],1)
        with self.assertRaises(ValueError):self.call('revision_snapshot',stream='main',revision=1,at_date=date)
        with self.assertRaises(ValueError):self.call('revision_snapshot',stream='main',revision=2**63)
        pending=self.call('create_change',workspace='work')
        with self.assertRaises(ValueError):self.call('revision_snapshot',stream='main',changelist=pending['number'])

    def test_http_historical_subtree_force_and_resume(self):
        first,second,date=self.history()
        root=Path(self.temp.name)/'workspace'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            self.assertEqual(client.download('work',root,prefix='docs/deep/')['state'],'complete')
            self.assertEqual((root/'docs/deep/readme.txt').read_bytes(),b'second')
            self.assertFalse((root/'docs/neighbor.txt').exists())
            self.assertFalse((root/'outside.txt').exists())
            target=root/'docs/deep/readme.txt';target.write_bytes(b'local edits')
            historical=client.download('work',root,prefix='docs/deep/',at_date=date)
            self.assertEqual(historical['state'],'blocked')
            forced=client.download('work',root,prefix='docs/deep/',at_date=date,force=True)
            self.assertEqual(forced['state'],'complete')
            self.assertEqual(target.read_bytes(),b'first')
            self.assertFalse((root/'docs/deep/new.txt').exists())
            target.write_bytes(b'local edits again')
            self.assertEqual(client.download('work',root,prefix='docs/deep/',force=True)['state'],'complete')
            self.assertEqual(target.read_bytes(),b'second')
            target.unlink()
            self.assertEqual(client.download('work',root,prefix='docs/deep/',force=True)['state'],'complete')
            self.assertEqual(target.read_bytes(),b'second')

    def test_per_file_revision_subtree_skips_missing_without_deleting_have(self):
        first,second,date=self.history()
        root=Path(self.temp.name)/'workspace'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            client.download('work',root,prefix='docs/',force=True)
            result=client.download('work',root,prefix='docs/',file_revision=2,force=True)
            self.assertEqual(result['state'],'complete')
            self.assertEqual(result['missing_revisions'],2)
            self.assertEqual((root/'docs/neighbor.txt').read_bytes(),b'neighbor')
            self.assertEqual((root/'docs/deep/new.txt').read_bytes(),b'new')
            self.assertEqual((root/'docs/deep/readme.txt').read_bytes(),b'second')
            result=client.download('work',root,prefix='docs/',file_revision=1,force=True)
            self.assertEqual(result['missing_revisions'],0)
            self.assertEqual((root/'docs/deep/readme.txt').read_bytes(),b'first')

    def test_branch_revisions_are_bounded_by_the_fork(self):
        first,second,date=self.history()
        self.call('create_stream',code='branch',depot='main',parent='main')
        self.publish({'docs/deep/readme.txt':b'parent future'},time_ns()//1000+3000000)
        old=self.call('list',stream='branch',path='docs/deep/readme.txt',file_revision=1)
        self.assertEqual(old['items'][0]['version'],self.call('list',stream='main',revision=1)['items'][0]['version'])
        with self.assertRaisesRegex(ValueError,'No published file revision'):
            self.call('list',stream='branch',path='docs/deep/readme.txt',file_revision=3)

    def test_scoped_depot_sync_keeps_other_have_and_large_historical_case(self):
        first,second,date=self.history()
        self.call('create_depot',code='other')
        self.call('create_stream',code='lib',depot='other')
        self.call('create_workspace',code='lib',stream='lib',local_root='D:/lib')
        change=self.call('create_change',workspace='lib')
        self.call('edit',change=change['code'],edit_revision=0,chunk='lib',operations=[{'path':'Mixed/Case.txt','blob':self.upload(change['code'],b'library')}])
        self.call('submit',change=change['code'])
        self.call('create_workspace',code='mapped',stream='main',local_root='D:/mapped',case_sensitive=False,mappings=[
            {'stream':'main','source':'...','target':'src/...','writable':True},
            {'stream':'lib','source':'...','target':'vendor/...'}])
        root=Path(self.temp.name)/'mapped'
        with self.http() as url, patch('tactic_client_lib.file_transfer.SMALL',2):
            client=FileTransferClient(url,self.token,'files')
            client.download('mapped',root,force=True)
            have=client.rpc('have',workspace='mapped')['items']
            lib=next(row for row in have if row['stream']=='lib')
            target=root/'vendor/Mixed/Case.txt'
            target.chmod(target.stat().st_mode | 0o200)
            target.write_bytes(b'local')
            result=client.download('mapped',root,paths=['vendor/Mixed/Case.txt'],file_revision=1,force=True)
            self.assertEqual(result['state'],'complete')
            self.assertEqual((root/'vendor/Mixed/Case.txt').read_bytes(),b'library')
            client.download('mapped',root,paths=['src/docs/deep/readme.txt'],changelist=first['number'],force=True)
            self.assertEqual((root/'src/docs/deep/readme.txt').read_bytes(),b'first')
            client.download('mapped',root,source_depot='main',revision=1,force=True)
            self.assertEqual((root/'src/docs/deep/readme.txt').read_bytes(),b'first')
            self.assertEqual(next(row for row in client.rpc('have',workspace='mapped')['items'] if row['stream']=='lib'),lib)
            client.download('mapped',root)
            self.assertEqual((root/'src/docs/deep/readme.txt').read_bytes(),b'second')

    def test_index_upgrade_requires_admin_and_rolls_back_trigger_failure(self):
        from pyasm.biz.file_project import FileProjectRecord, create, find, access
        from pyasm.common.errors import SecurityException
        self.history()
        artist=self.writer()
        with self.assertRaises(SecurityException):self.client(artist,'revision_upgrade')
        from pyasm.command import Command
        from pyasm.search import Search
        from tactic.command.file_storage import maintenance
        with self.context(),access('files'):
            command=Command()
            def unindexed():
                with maintenance('files'):
                    for row in Search('file_project/version').get_sobjects():
                        row.set_value('number',0);row.commit()
                return create('chunk',{'table':'version','after':0,'complete':False},'revision-index')
            command.execute=unindexed
            Command.execute_cmd(command)
        self.assertFalse(self.call('capabilities')['revision_index_ready'])
        with self.assertRaisesRegex(ValueError,'revision_upgrade'):
            self.call('sync_begin',workspace='work',file_revision=1)
        original=FileProjectRecord._call_triggers
        def failure(record,*args,**kwargs):
            if record.get_base_search_type()=='file_project/version':raise ValueError('index trigger failure')
            return original(record,*args,**kwargs)
        with patch.object(FileProjectRecord,'_call_triggers',failure):
            with self.assertRaisesRegex(ValueError,'index trigger failure'):self.call('revision_upgrade')
        with self.context(),access('files'):
            self.assertEqual(find('chunk','revision-index').get_json_value('data')['after'],0)
            self.assertTrue(all(row.get_value('number')==0 for row in Search('file_project/version').get_sobjects()))
        self.assertTrue(self.call('revision_upgrade')['complete'])
        self.assertTrue(self.call('capabilities')['revision_index_ready'])


class LegacyRevisionUpgradeTest(FileProjectFixture,unittest.TestCase):
    http=transfers.FileTransferTest.http
    publish=FileRevisionTest.publish

    def setUp(self):
        with patch('pyasm.biz.file_project.revision_schema'):
            super().setUp()

    def test_handler_upgrades_missing_schema_before_historical_download(self):
        import threading
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        self.publish({'folder/file.txt':b'first'},time_ns()//1000)
        self.publish({'folder/file.txt':b'second'},time_ns()//1000)
        self.assertFalse(self.call('capabilities')['revision_index_ready'])
        state=initial_state()
        root=Path(self.temp.name)/'local'
        cache=Path(self.temp.name)/'handler-cache';cache.mkdir()
        state.update(workspace='work',stream='main',root=str(root),context_row={'kind':'directory','stream':'main','directory':'folder/'},selection_scope='depot')
        events=[]
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files',progress=events.append)
            FileWorkspaceController._execute(client,state,cache,'get_revision',{'scope':'folder','file_revision':'1'},threading.Event())
        self.assertEqual((root/'folder/file.txt').read_bytes(),b'first')
        self.assertTrue(self.call('capabilities')['revision_index_ready'])
        self.assertTrue(any(row.get('state')=='indexing_history' for row in events))


if __name__=='__main__':unittest.main()
