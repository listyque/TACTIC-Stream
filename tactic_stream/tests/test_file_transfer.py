"""Bulk manifests, real fresh bytes, resumability, native quotas and safe reclamation."""
from contextlib import contextmanager
from hashlib import sha256
import io
from pathlib import Path
import tarfile
from time import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pyasm.biz.file_project import access, find, FileProjectRecord
from pyasm.command import Command, Trigger
from pyasm.search.search import RequestContext, request_context
from tactic.command.file_storage import maintenance
from tactic_stream.server import file_tasks
from test_file_project import FileProjectFixture
import test_file_workspace as workspaces


class LateGcRootProbe(Trigger):
    enabled = False
    change = None

    def execute(self):
        if not self.enabled:
            return
        type(self).enabled = False
        from tactic.command.file_project_cmd import FileProjectCmd
        command = FileProjectCmd(action='create_change', workspace='work')
        Command.execute_cmd(command)
        type(self).change = command.info['code']


class NestedStorageProbe(Trigger):
    enabled = False

    def execute(self):
        if not self.enabled:
            return
        type(self).enabled = False
        from tactic.command.file_project_cmd import FileProjectCmd
        Command.execute_cmd(FileProjectCmd(action='upload_begin', size=5,
                            change=self.get_caller().get_json_value('data')['change']))


class FileTransferTest(FileProjectFixture, unittest.TestCase):
    publish = workspaces.FileWorkspaceTest.publish
    edit = workspaces.FileWorkspaceTest.edit
    client = workspaces.FileWorkspaceTest.client
    writer = workspaces.FileWorkspaceTest.writer

    def nested_storage_trigger(self):
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'nested-storage',
            'event': 'insert|file_project/blob', 'class_name': 'test_file_transfer.NestedStorageProbe',
            'mode': 'same process,same transaction'}))
        NestedStorageProbe.enabled = True
        self.addCleanup(setattr, NestedStorageProbe, 'enabled', False)

    def test_native_nested_upload_reservations_are_added_without_overwriting(self):
        change = self.change()
        self.nested_storage_trigger()
        self.call('upload_begin', change=change, size=4)
        status = self.call('storage_status')
        self.assertEqual((status['allocated_bytes'], status['allocated_files']), (9, 2))

    def test_native_nested_uploads_cannot_jointly_exceed_quota(self):
        change = self.change()
        self.call('storage_policy', revision=0, policy={'bytes_limit': 8})
        self.nested_storage_trigger()
        with self.assertRaisesRegex(ValueError, 'storage quota'):
            self.call('upload_begin', change=change, size=4)
        status = self.call('storage_status')
        self.assertEqual((status['allocated_bytes'], status['allocated_files']), (0, 0))

    def test_checkout_materializes_pinned_base_and_preserves_existing_local_edits(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import checkout_local
        self.publish({'folder/a.txt':b'old base','folder/b.txt':b'baseline'})
        change=self.call('create_change',workspace='work')
        self.publish({'folder/a.txt':b'new head'})
        self.call('checkout',change=change['code'],directories=['folder/'],mode='ordinary')
        root=Path(self.temp.name)/'local'
        (root/'folder').mkdir(parents=True)
        (root/'folder/b.txt').write_bytes(b'local edit')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            checkout_local(client,change['code'],root,materialize=True)
        self.assertEqual((root/'folder/a.txt').read_bytes(),b'old base')
        self.assertEqual((root/'folder/b.txt').read_bytes(),b'local edit')

    def test_review_is_local_and_only_confirmed_publish_uploads_opened_edits(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import checkout_local
        self.publish({'a.txt':b'baseline','unchanged.txt':b'same'})
        change=self.call('create_change',workspace='work')
        self.call('checkout',change=change['code'],paths=['a.txt','unchanged.txt'],mode='ordinary')
        root=Path(self.temp.name)/'editing'
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            checkout_local(client,change['code'],root,materialize=True)
            (root/'a.txt').write_bytes(b'edited fresh')
            (root/'unopened.txt').write_bytes(b'keep outside changelist')
            review=Path(self.temp.name)/'review.sqlite'
            result=client.prepare_change(change['code'],root,review)
            self.assertEqual((result['files'],result['pending_uploads']),(2,1))
            rows=client.rpc('change_files',change=change['code'])['items']
            self.assertEqual({row['path'] for row in rows},{'a.txt','unchanged.txt'})
            a=next(row for row in rows if row['path']=='a.txt')
            self.assertEqual(a['file']['sha256'],sha256(b'baseline').hexdigest())
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])
            (root/'a.txt').write_bytes(b'edited later')
            with self.assertRaisesRegex(ValueError,'changed after review'):
                client.upload_prepared_change(result)
            self.assertEqual(client.rpc('status',change=change['code'])['state'],'pending')
            (root/'a.txt').write_bytes(b'edited fresh')
            client.validate_change(root,review)
            revision=client.upload_prepared_change(result)
            client.submit(change['code'],edit_revision=revision)
            self.assertEqual(client.rpc('file_info',stream='main',path='a.txt')['file']['sha256'],sha256(b'edited fresh').hexdigest())

    def test_local_preparation_rejects_concurrent_change_before_upload_allocation(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import checkout_local
        self.publish({'a.txt':b'baseline'})
        change=self.change();self.call('checkout',change=change,paths=['a.txt'],mode='ordinary')
        root=Path(self.temp.name)/'editing'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            checkout_local(client,change,root,materialize=True)
            original=client.rpc
            def concurrent(action,**kwargs):
                result=original(action,**kwargs)
                if action=='change_files':
                    self.call('update_change',change=change,edit_revision=result['edit_revision'],description='concurrent edit',request_id='other')
                return result
            with patch.object(client,'rpc',side_effect=concurrent),self.assertRaisesRegex(ValueError,'Changelist changed'):
                client.prepare_change(change,root,Path(self.temp.name)/'review.sqlite')
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])
            status=client.rpc('status',change=change)
            with self.assertRaisesRegex(HTTPError,'revision conflict'):
                client.rpc('transfer_begin',change=change,edit_revision=status['edit_revision']-1,request_id='stale')
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])

    def test_1003_local_additions_are_bounded_metadata_only_until_shelve(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import open_local_files, local_page
        root=Path(self.temp.name)/'local';root.mkdir()
        for number in range(1003):
            (root/f'{number:04}.txt').write_bytes(f'fresh set {number}'.encode())
        change=self.call('create_change',workspace='work')
        cache=Path(self.temp.name)/'local.sqlite'
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            native=client.rpc;chunks=[]
            def rpc(action,**kwargs):
                if action in ('checkout','reconcile'):chunks.append((action,len(kwargs.get('paths',kwargs.get('files',[])))))
                return native(action,**kwargs)
            client.rpc=rpc
            with patch.object(client,'upload',side_effect=AssertionError('Add must not upload')):
                result=open_local_files(client,change,root,cache,((file.name,file) for file in sorted(root.iterdir())))
            self.assertEqual(result['files_done'],1003)
            self.assertEqual(chunks,[('checkout',1000),('reconcile',1000),('checkout',3),('reconcile',3)])
            self.assertEqual(client.rpc('change_files',change=change['code'])['info']['waiting_uploads'],1003)
            self.assertFalse(client.rpc('transfer_tasks')['items'])
            self.assertEqual({row['local_status'] for row in local_page(cache,limit=1000)['items']},{'added'})
            review=client.prepare_change(change['code'],root,Path(self.temp.name)/'review.sqlite',paths={'0000.txt'})
            self.assertFalse(client.rpc('transfer_tasks')['items'],'Review/Cancel must not allocate an upload')
            (root/'0000.txt').write_bytes(b'edited after adding')
            with self.assertRaisesRegex(ValueError,'changed after review'):
                client.upload_prepared_change(review)
            self.assertFalse(client.rpc('transfer_tasks')['items'])
            review=client.prepare_change(change['code'],root,Path(self.temp.name)/'review-next.sqlite',paths={'0000.txt'})
            revision=client.upload_prepared_change(review)
            from tactic_client_lib.file_workspace import cache_prepared_change, inspect_local
            cache_prepared_change(cache,review['review'])
            staged=client.rpc('change_files',change=change['code'],prefix='0000.txt')['items'][0]
            staged['local_path']='0000.txt'
            inspect_local(cache,root,[staged])
            self.assertTrue(staged['staged_current'])
            shelf=client.rpc('shelve',change=change['code'],edit_revision=revision,paths=['0000.txt'],request_id='shelf')
            entry=client.rpc('change_files',shelf=shelf['code'])['items'][0]
            self.assertEqual(entry['file']['sha256'],sha256(b'edited after adding').hexdigest())
            self.assertEqual(client.rpc('list',stream='main')['files'],0)
            self.assertEqual(client.rpc('change_files',change=change['code'])['info']['waiting_uploads'],1002)

    def test_existing_local_copies_are_compared_without_have_or_upload(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import open_local_files, local_page
        self.publish({'same.txt':b'same','edited.txt':b'base'})
        root=Path(self.temp.name)/'local';root.mkdir()
        (root/'same.txt').write_bytes(b'same');(root/'edited.txt').write_bytes(b'edited')
        change=self.call('create_change',workspace='work');cache=Path(self.temp.name)/'local.sqlite'
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            open_local_files(client,change,root,cache,((file.name,file) for file in root.iterdir()))
            rows={row['path']:row for row in local_page(cache,changes_only=False)['items']}
            self.assertEqual(rows['same.txt']['local_status'],'clean')
            self.assertEqual(rows['edited.txt']['local_status'],'modified')
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])
            review=client.prepare_change(change['code'],root,Path(self.temp.name)/'review.sqlite')
            revision=client.upload_prepared_change(review)
            client.submit(change['code'],edit_revision=revision)
            self.assertEqual(client.rpc('file_info',stream='main',path='edited.txt')['file']['sha256'],sha256(b'edited').hexdigest())

    def test_confirm_rejects_different_uploaded_bytes_even_if_local_copy_is_restored(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        root=Path(self.temp.name)/'local';root.mkdir()
        file=root/'new.txt';file.write_bytes(b'reviewed')
        change=self.change();self.call('checkout',change=change,paths=['new.txt'])
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            review=client.prepare_change(change,root,Path(self.temp.name)/'review.sqlite')
            original=client.upload
            def changed(*args,**kwargs):
                file.write_bytes(b'concurrent edit')
                try:return original(*args,**kwargs)
                finally:file.write_bytes(b'reviewed')
            with patch.object(client,'upload',side_effect=changed),self.assertRaisesRegex(ValueError,'changed during upload'):
                client.upload_prepared_change(review)
            self.assertEqual(client.rpc('status',change=change)['state'],'pending')
            self.assertEqual(client.rpc('list',stream='main')['files'],0)

    def test_readonly_mapped_sync_and_native_checkout_restore_write_permissions(self):
        from stat import S_IWUSR
        from tactic_client_lib.file_transfer import FileTransferClient
        from tactic_client_lib.file_workspace import checkout_local
        self.publish({'a.txt':b'fresh'})
        self.call('create_workspace',code='readonly',stream='main',local_root='D:/readonly',
                  mappings=[{'stream':'main','source':'...','target':'...','writable':False}])
        root=Path(self.temp.name)/'read'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            client.download('readonly',root)
            self.assertFalse((root/'a.txt').stat().st_mode & S_IWUSR)
            client.download('readonly',root,force=True)
            self.assertFalse((root/'a.txt').stat().st_mode & S_IWUSR)
            own=Path(self.temp.name)/'own'
            client.download('work',own)
            (own/'a.txt').chmod((own/'a.txt').stat().st_mode & ~S_IWUSR)
            change=self.change()
            client.rpc('checkout',change=change,edit_revision=0,paths=['a.txt'],mode='ordinary',request_id='open')
            checkout_local(client,change,own,paths=['a.txt'])
            self.assertTrue((own/'a.txt').stat().st_mode & S_IWUSR)

    def test_renamed_file_can_be_edited_without_losing_move_pair_or_history(self):
        self.publish({'old.txt':b'base'})
        change=self.change()
        self.call('rename_files',change=change,edit_revision=0,renames=[{'source':'old.txt','target':'new.txt'}],request_id='rename')
        blob=self.upload(change,b'edited destination')
        self.call('edit',change=change,edit_revision=1,chunk='edited',operations=[{'path':'new.txt','blob':blob}])
        rows=self.call('change_files',change=change)['items']
        self.assertEqual({row['path']:row['action'] for row in rows},{'new.txt':'move/add','old.txt':'move/delete'})
        self.call('submit',change=change)
        history=self.call('history',stream='main',path='new.txt')['items']
        self.assertEqual([row['path'] for row in history],['new.txt','old.txt'])

    def test_manifest_exposes_waiting_file_locks_and_cancel_restores_pending_state(self):
        task,entries=self.task({'fresh.txt':b'new bytes'},submit=False)
        info=self.call('transfer_status',task=task)
        change=info['change']
        rows=self.call('transfer_items',task=task)['items']
        self.assertEqual([(row['path'],row['state'],row['received']) for row in rows],[('fresh.txt','waiting',0)])
        self.assertEqual(self.call('locks',stream='main',paths=['fresh.txt'])['items'][0]['holders'][0]['change'],change)
        self.assertEqual(self.call('change_files',change=change)['items'][0]['path'],'fresh.txt')
        self.call('transfer_cancel',task=task)
        self.assertEqual(self.call('change_files',change=change)['items'],[])
        self.assertFalse(any(row['holders'] for row in self.call('locks',stream='main',paths=['fresh.txt'])['items']))
        self.assertNotEqual(self.call('transfer_items',task=task)['items'][0]['state'],'staged')

    @contextmanager
    def http(self, worker=False):
        import socket
        import threading
        from time import monotonic, sleep
        import uvicorn
        import os
        from importlib.resources import files
        from xml.etree import ElementTree as ET
        from pyasm.common import Config
        from tactic_stream.server.app import create_app
        config = Path(self.temp.name) / 'http-config.xml'
        source = Path(self.database_config) if self.database_config else self.store.data_dir / 'config/tactic-conf.xml'
        root = ET.parse(source).getroot() if source.is_file() else ET.fromstring(files('tactic_stream').joinpath('config/tactic-conf.xml').read_text())
        if worker:
            services = root.find('services')
            if services is None:
                services = ET.SubElement(root, 'services')
            enabled = services.find('enable')
            if enabled is None:
                enabled = ET.SubElement(services, 'enable')
            enabled.text = 'tactic|files'
        ET.ElementTree(root).write(config, encoding='utf-8')
        environment = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(config), 'TACTIC_TMP_CONFIG_PATH': ''})
        environment.start()
        Config.reload_config()
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        server = uvicorn.Server(uvicorn.Config(create_app(self.store.data_dir, event_collector=False), lifespan='off', log_level='error'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        from types import SimpleNamespace
        stopped, errors = threading.Event(), []
        service_stop = SimpleNamespace(value=False)
        def jobs():
            try:
                file_tasks.start_files({'data_dir': str(self.store.data_dir), 'config_path': str(config)}, stop=service_stop)
            except Exception as error:
                errors.append(error)
        worker_thread = threading.Thread(target=jobs, daemon=True) if worker else None
        thread.start()
        try:
            deadline = monotonic() + 10
            while not server.started and thread.is_alive() and monotonic() < deadline:
                sleep(.01)
            self.assertTrue(server.started)
            if worker_thread:
                worker_thread.start()
            yield 'http://127.0.0.1:%s' % sock.getsockname()[1]
        finally:
            stopped.set()
            if worker_thread and worker_thread.ident:
                service_stop.value = True
                worker_thread.join(10)
                self.assertFalse(worker_thread.is_alive())
            server.should_exit = True
            thread.join(10)
            sock.close()
            environment.stop()
            Config.reload_config()
            self.assertFalse(thread.is_alive())
            if errors:
                raise errors[0]

    def test_http_client_fresh_bytes_upload_download_and_dirty_protection(self):
        from tactic_client_lib.file_transfer import FileTransferClient, digest_file
        source, target = Path(self.temp.name) / 'fresh', Path(self.temp.name) / 'download'
        source.mkdir()
        (source / 'пустой.txt').write_bytes(b'')
        (source / 'new.txt').write_bytes(b'never uploaded before')
        (source / 'large.bin').write_bytes(__import__('os').urandom(9 * 1024 * 1024 + 19))
        events = []
        with self.http(worker=True) as url:
            client = FileTransferClient(url, self.token, 'files', progress=events.append)
            change = self.change()
            status = client.upload(change, source, Path(self.temp.name) / 'outbox.sqlite', submit=True, timeout=20)
            self.assertEqual(status['state'], 'submitted')
            resumed = client.upload(change, source, Path(self.temp.name) / 'outbox.sqlite', submit=True, timeout=20)
            self.assertEqual(resumed['task'], status['task'])
            downloaded = client.download('work', target)
            self.assertEqual(downloaded['state'], 'complete')
            for path in source.iterdir():
                self.assertEqual(digest_file(path), digest_file(target / path.name))
            (target / 'new.txt').write_bytes(b'local edits')
            blocked = client.download('work', target)
            self.assertEqual(blocked['state'], 'blocked')
            self.assertEqual(blocked['reason'], 'local_modified_or_untracked')
            self.assertEqual(blocked['path'], (target / 'new.txt').as_posix())
            self.assertEqual((target / 'new.txt').read_bytes(), b'local edits')
            self.assertEqual(events[-1]['state'], 'blocked')
            (target / 'new.txt').write_bytes((source / 'new.txt').read_bytes())
            self.assertEqual(client.download('work', target, task=blocked['task'])['state'], 'complete')
            self.assertTrue(any(event.get('block_bytes_done') for event in events))
            self.assertTrue(any(event.get('file_bytes_done') for event in events))

    def test_disabled_file_service_rejects_before_allocating_upload(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from pyasm.common import Config
        source = Path(self.temp.name) / 'source'
        source.mkdir()
        (source / 'new.txt').write_bytes(b'fresh bytes')
        change = self.change()
        with self.http() as url:
            original = Config.get_value
            def disabled(section, key, *args, **kwargs):
                return 'tactic|queue' if (section, key) == ('services', 'enable') else original(section, key, *args, **kwargs)
            client = FileTransferClient(url, self.token, 'files')
            with patch.object(Config, 'get_value', side_effect=disabled):
                self.assertFalse(client.rpc('capabilities')['files_service_configured'])
                with self.assertRaisesRegex(ValueError, 'enable files.*restart'):
                    client.upload(change, source, Path(self.temp.name) / 'outbox.sqlite')
            self.assertEqual(client.rpc('transfer_tasks')['items'], [])
            self.assertNotIn('active_transfer', client.rpc('status', change=change))

    def test_new_client_recovers_lost_seal_and_ack_responses(self):
        from tactic_client_lib.file_transfer import FileTransferClient, digest_file
        from urllib.error import URLError
        source, target = Path(self.temp.name) / 'source', Path(self.temp.name) / 'target'
        source.mkdir()
        for index in range(17):
            (source / ('fresh-%02d.txt' % index)).write_bytes(__import__('os').urandom(4096))
        change, journal = self.change(), Path(self.temp.name) / 'outbox.sqlite'
        with self.http(worker=True) as url:
            client = FileTransferClient(url, self.token, 'files')
            rpc = client.rpc
            def lost_seal(action, **kwargs):
                result = rpc(action, **kwargs)
                if action == 'transfer_seal':
                    raise URLError('Lost response after durable seal')
                return result
            client.rpc = lost_seal
            with self.assertRaises(URLError):
                client.upload(change, source, journal, submit=True)
            recovered = FileTransferClient(url, self.token, 'files')
            result = recovered.upload(change, source, journal, submit=True, timeout=20)
            self.assertEqual(result['state'], 'submitted')
            self.assertEqual(recovered.rpc('list', stream='main')['files'], 17)
            rpc = recovered.rpc
            def lost_ack(action, **kwargs):
                result = rpc(action, **kwargs)
                if action == 'transfer_ack':
                    raise URLError('Lost response after durable Have')
                return result
            recovered.rpc = lost_ack
            with self.assertRaises(URLError):
                recovered.download('work', target)
            resumed = FileTransferClient(url, self.token, 'files')
            task = resumed.download('work', target, task=recovered.status['task'])
            self.assertEqual(task['state'], 'complete')
            for path in source.iterdir():
                self.assertEqual(digest_file(path), digest_file(target / path.name))
                self.assertEqual(len(resumed.rpc('history', stream='main', path=path.name)['items']), 1)
            self.assertEqual(len(resumed.rpc('have', workspace='work')['items']), 17)

    def test_two_users_upload_and_sync_simultaneously(self):
        from concurrent.futures import ThreadPoolExecutor
        from tactic_client_lib.file_transfer import FileTransferClient, digest_file
        from urllib.error import HTTPError
        import os
        artist = self.writer()
        self.call('create_stream', code='branch', depot='main', parent='main')
        self.client(artist, 'create_workspace', code='parallel', stream='branch', local_root='D:/artist/parallel')
        changes = [self.change(), self.client(artist, 'create_change', workspace='parallel')['code']]
        roots = [Path(self.temp.name) / ('fresh-%d' % index) for index in range(2)]
        targets = [Path(self.temp.name) / ('download-%d' % index) for index in range(2)]
        for root in roots:
            root.mkdir()
            for index in range(1001):
                (root / ('fresh-%04d.bin' % index)).write_bytes(os.urandom(4096))
        with self.http(worker=True) as url:
            clients = [FileTransferClient(url, ticket['ticket'], 'files', parallel=2) for ticket in (self.ticket, artist)]
            def upload(index):
                return clients[index].upload(changes[index], roots[index], Path(self.temp.name) / ('journal-%d.sqlite' % index), submit=True, timeout=120)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(upload, range(2)))
                self.assertTrue(all(result['state'] == 'submitted' and result['files_done'] == 1001 for result in results))
                def download(index):
                    return clients[index].download(('work', 'parallel')[index], targets[index])
                downloads = list(pool.map(download, range(2)))
            self.assertTrue(all(result['state'] == 'complete' and result['files_done'] == 1001 for result in downloads))
            with self.assertRaises(HTTPError) as denied:
                clients[0].rpc('transfer_status', task=results[1]['task'])
            self.assertEqual(denied.exception.code, 403)
            self.assertEqual(self.call('list', stream='main')['files'], 1001)
            self.assertEqual(self.call('list', stream='branch')['files'], 1001)
            for index in range(2):
                for path in roots[index].iterdir():
                    self.assertEqual(digest_file(path), digest_file(targets[index] / path.name))

    def test_busy_storage_lock_retries_before_mutation_without_failing_task(self):
        from tactic.command.file_project_cmd import FileProjectCmd
        from tactic_client_lib.file_transfer import FileTransferClient
        import sqlite3
        source = Path(self.temp.name) / 'fresh'
        source.mkdir()
        (source / 'new.bin').write_bytes(__import__('os').urandom(4096))
        original, remaining = FileProjectCmd.lock, {'transfer_begin': 5, 'transfer_write_begin': 5,
            'transfer_write_touch': 1, 'transfer_write_abort': 5, 'transfer_claim': 4}
        def busy(command, kind, code):
            action = command.kwargs.get('action')
            if kind == 'chunk' and code == 'storage-policy' and remaining.get(action, 0):
                remaining[action] -= 1
                error = sqlite3.OperationalError('database is locked')
                error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                raise error
            return original(command, kind, code)
        with self.http(worker=True) as url, patch.object(FileProjectCmd, 'lock', busy):
            events = []
            client = FileTransferClient(url, self.token, 'files', progress=events.append)
            result = client.upload(self.change(), source, Path(self.temp.name) / 'journal.sqlite', submit=True, timeout=20)
            self.assertEqual(result['state'], 'submitted')
            self.assertTrue(all(value == 0 for value in remaining.values()), remaining)
            self.assertTrue(any(event.get('phase') == 'waiting' for event in events))
            self.assertEqual(len(client.rpc('transfer_tasks')['items']), 1)
            self.assertEqual(len(client.rpc('history', stream='main', path='new.bin')['items']), 1)

    def test_storage_wait_is_bounded_cancellable_and_rejects_unmarked_errors(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from urllib.error import HTTPError
        from time import monotonic
        marked = HTTPError('http://unused', 503, 'busy', {'X-Tactic-Error': 'file_project_busy'}, None)
        unmarked = HTTPError('http://unused', 503, 'other', None, None)
        self.addCleanup(marked.close)
        self.addCleanup(unmarked.close)
        client = FileTransferClient('http://unused', 'unused', 'files')
        self.assertFalse(client.wait_busy(unmarked, monotonic() + 120))
        with self.assertRaises(HTTPError):
            client.wait_busy(marked, monotonic() - 1)
        def cancel(progress):
            raise InterruptedError('Stopped by user')
        client.progress = cancel
        with self.assertRaisesRegex(InterruptedError, 'Stopped by user'):
            client.wait_busy(marked, monotonic() + 120)

    def test_http_large_range_resume_and_symlink_rejection(self):
        from tactic_client_lib.file_transfer import FileTransferClient, local_path
        raw = __import__('os').urandom(5 * 1024 * 1024 + 3)
        upload, entries = self.task({'dir/new.bin': raw})
        self.block(upload, entries[0]['blob'], 0, raw)
        self.finish_task(upload)
        target = Path(self.temp.name) / 'resume'
        target.mkdir()
        with self.http() as url:
            client = FileTransferClient(url, self.token, 'files')
            task = self.call('transfer_begin', kind='download', workspace='work')['task']
            plan = self.call('transfer_next', task=task)
            entry = plan['items'][0]
            destination = target / 'dir' / 'new.bin'
            destination.parent.mkdir()
            temporary = destination.with_name(destination.name + '.tactic-' + entry['blob'] + '.part')
            temporary.write_bytes(raw[:1024 * 1024])
            with patch.object(client, 'open', wraps=client.open) as requests:
                client.download('work', target, task=task)
            ranges = [call.kwargs.get('headers', {}) for call in requests.call_args_list if call.args[0] == 'download']
            self.assertEqual(ranges, [{'Range': 'bytes=1048576-'}])
            self.assertEqual(destination.read_bytes(), raw)
        for name in ('../escape', '/escape', 'C:/escape', 'dir\\escape', 'dir//escape'):
            with self.assertRaises(ValueError):
                local_path(target, name)

    def test_http_broken_body_preserves_confirmed_offset(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        task, entries = self.task({'new.bin': b'new bytes'})
        with self.http() as url:
            client = FileTransferClient(url, self.token, 'files')
            with self.assertRaises(OSError):
                client.put(task, io.BytesIO(b'new'), 9, blob=entries[0]['blob'], offset=0)
            self.assertEqual(self.call('transfer_received', task=task, blob=entries[0]['blob'])['received'], 0)
            deadline=__import__('time').monotonic()+10
            while True:
                try:
                    client.put(task, io.BytesIO(b'new bytes'), 9, blob=entries[0]['blob'], offset=0)
                    break
                except HTTPError as error:
                    if not client.wait_busy(error,deadline):raise
        self.finish_task(task)

    def test_live_byte_writer_is_marked_busy_without_taking_over_its_lease(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        task,entries=self.task({'new.bin':b'new bytes'})
        lease=self.call('transfer_write_begin',task=task,blob=entries[0]['blob'],offset=0,size=9)
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            with self.assertRaises(HTTPError) as error:
                client.put(task,io.BytesIO(b'new bytes'),9,blob=entries[0]['blob'],offset=0)
            self.assertEqual(error.exception.code,503)
            self.assertEqual(error.exception.headers['X-Tactic-Error'],'file_project_busy')
            self.assertEqual(self.call('transfer_received',task=task,blob=entries[0]['blob'])['received'],0)
            self.call('transfer_write_abort',task=task,token=lease['token'])
            client.put(task,io.BytesIO(b'new bytes'),9,blob=entries[0]['blob'],offset=0)

    def test_gc_reap_retries_after_worker_loss_and_grace(self):
        task, entries = self.task({'orphan.bin': b'orphan'})
        self.batch(task, entries, {'orphan.bin': b'orphan'})
        self.call('transfer_cancel', task=task)
        self.call('revert', change=self.call('transfer_status', task=task)['change'])
        self.age('blob', entries[0]['blob'])
        self.age('sync', task)
        self.call('storage_policy', revision=0, policy={'gc_grace_seconds': 0})
        gc = self.call('gc_begin', dry_run=False)['code']
        for _ in range(100):
            step = self.worker('gc_step', task=gc)
            if step.get('reap'):
                first = step['reap']
                break
        else:
            self.fail('GC did not approve orphan reclamation')
        self.assertEqual(self.worker('gc_step', task=gc)['reap'], first)
        with self.context(), access('files'), self.assertRaisesRegex(ValueError, 'immutable'):
            def revive():
                from pyasm.biz.file_project import save
                row = find('blob', entries[0]['blob'])
                value = row.get_json_value('data')
                value['state'] = 'ready'
                save(row, value)
            command = Command()
            command.execute = revive
            Command.execute_cmd(command)
        with self.context():
            file_tasks.run_gc(gc)
        self.assertEqual(self.call('storage_status')['allocated_files'], 0)

    def test_gc_sweeps_compressed_pages_and_preserves_published_contents(self):
        import base64
        from pyasm.biz.file_project import PageStore
        self.publish({'published.txt': b'keep these bytes'})
        page = {'leaf': True, 'items': [{'path': f'orphan-{index:03d}-' + 'x' * 512, 'size': 0}
                                        for index in range(64)]}
        with self.context(), access('files'):
            store = PageStore()
            code = store.save(page)
            command = Command(log_exception=False)
            command.execute = store.flush
            Command.execute_cmd(command)
            self.assertTrue(find('page', code).get_value('data').startswith('zlib:'))
            self.assertEqual(find('page', code).get_json_value('data'), page)
        self.age('page', code)
        for dry_run in (True, False):
            task = self.call('gc_begin', dry_run=dry_run)['code']
            with self.context():
                result = file_tasks.run_gc(task)
            self.assertEqual(result['state'], 'complete')
            with self.context(), access('files'):
                self.assertEqual(find('page', code, False) is not None, dry_run)
            self.assertEqual(base64.b64decode(self.call('read', stream='main', path='published.txt')['data']),
                             b'keep these bytes')

    def test_compressed_blob_checks_stored_immutable_state(self):
        from pyasm.biz.file_project import save
        blob = self.upload(self.change())
        with self.context(), access('files'):
            def edit(state, padding):
                row = find('blob', blob)
                value = row.get_json_value('data')
                value.update(state=state, padding=padding)
                save(row, value)
            command = Command(log_exception=False)
            command.execute = lambda: edit('ready', 'x' * 15000)
            with maintenance('files'):
                Command.execute_cmd(command)
            self.assertTrue(find('blob', blob).get_value('data').startswith('zlib:'))
            command = Command(log_exception=False)
            command.execute = lambda: edit('collecting', '')
            with self.assertRaisesRegex(ValueError, 'Completed blobs are immutable'):
                Command.execute_cmd(command)
            self.assertEqual(find('blob', blob).get_json_value('data')['state'], 'ready')

    def test_missing_gc_reference_stops_before_sweep(self):
        self.publish({'present.bin': b'present'})
        with self.context(), access('files'), maintenance('files'):
            def corrupt():
                from pyasm.biz.file_project import save
                stream = find('stream', 'main')
                data = stream.get_json_value('data')
                data['root'] = 'f' * 64
                save(stream, data)
            command = Command()
            command.execute = corrupt
            Command.execute_cmd(command)
        task = self.call('gc_begin', dry_run=False)['code']
        with self.assertRaisesRegex(ValueError, 'missing'):
            with self.context():
                file_tasks.run_gc(task)
        self.assertEqual(self.call('gc_status', task=task)['state'], 'error')
        self.assertEqual(self.call('storage_status')['allocated_files'], 1)

    def test_service_config_files_and_owned_task_discovery(self):
        from tactic_stream.server.startup import parse_service_config
        from tactic_stream.server.configuration import validate_setting
        validate_setting('services/enable', 'tactic|queue|files')
        self.assertTrue(parse_service_config({'enable': 'tactic|files'}, use_environment=False)['files_enabled'])
        self.assertFalse(parse_service_config({'enable': 'tactic'}, use_environment=False)['files_enabled'])
        task, entries = self.task({'one.bin': b'one'})
        self.batch(task, entries, {'one.bin': b'one'})
        self.call('transfer_seal', task=task)
        tasks, _, _ = file_tasks.pending_tasks(self.store)
        self.assertIn(task, [item['task'] for item in tasks])

    def test_http_more_than_one_manifest_and_declared_progress(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        source, target = Path(self.temp.name) / 'source-many', Path(self.temp.name) / 'many-downloaded'
        source.mkdir()
        for index in range(1001):
            (source / ('new-%04d.txt' % index)).write_bytes(('%d fresh unique bytes' % index).encode())
        events = []
        with self.http(worker=True) as url:
            client = FileTransferClient(url, self.token, 'files', progress=events.append)
            result = client.upload(self.change(), source, Path(self.temp.name) / 'many.sqlite', submit=True, timeout=30)
            self.assertEqual(result['files_done'], 1001)
            self.assertEqual(result['files_manifested'], 1001)
            self.assertTrue(any(event.get('files_total') == 1001 and event['state'] == 'collecting' and event['total_known'] for event in events))
            client.download('work', target)
        self.assertEqual(sum(1 for _ in target.iterdir()), 1001)

    def test_upgrade_old_project_uses_bounded_native_index(self):
        from pyasm.biz.file_project import COMMAND
        with patch('pyasm.biz.file_project.storage_schema'):
            self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'admin'},
                'tactic.command.project_template_cmd.ProjectTemplateInstallerCmd',
                {'project_code': 'files_two', 'project_title': 'Old files', 'template_code': 'perforce_like'}))
        original = self.ticket
        self.ticket = {'ticket': self.token, 'project': 'files_two'}
        try:
            self.call('create_depot', code='main')
            self.call('create_stream', code='main', depot='main')
            self.call('create_workspace', code='work', stream='main', local_root='D:/old')
            self.publish({'old.bin': b'old preserved bytes'})
            with request_context(RequestContext(self.store, 'admin', 'files_two')), access('files_two'), maintenance('files_two'):
                self.api.auth.bind_security('admin', self.token)
                command = Command()
                command.execute = lambda: find('chunk', 'storage-policy').delete(log=False)
                Command.execute_cmd(command)
            self.call('storage_upgrade')
            self.assertFalse(self.call('storage_status')['indexed'])
            for _ in range(30):
                if self.call('storage_index')['indexed']:
                    break
            else:
                self.fail('Storage index did not finish')
            self.assertEqual(self.call('storage_status')['allocated_files'], 1)
            self.assertEqual(self.call('list', stream='main')['files'], 1)
            self.assertTrue(self.call('read', stream='main', path='old.bin')['data'])
        finally:
            self.ticket = original

    def test_forged_archive_foreign_blob_and_callback_rollback(self):
        task, entries = self.task({'safe.bin': b'safe'})
        other, foreign = self.task({'foreign.bin': b'foreign'})
        for name in ('../escape', foreign[0]['blob']):
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                member = tarfile.TarInfo(name)
                member.size = 4
                archive.addfile(member, io.BytesIO(b'safe'))
            lease = self.call('transfer_write_begin', task=task, batch=True, size=len(buffer.getvalue()))
            Path(lease['_path']).write_bytes(buffer.getvalue())
            try:
                with self.assertRaises(Exception):
                    self.call('transfer_batch_commit', task=task, token=lease['token'])
            finally:
                self.call('transfer_write_abort', task=task, token=lease['token'])
                Path(lease['_path']).unlink(missing_ok=True)
        self.assertEqual(self.call('transfer_status', task=task)['files_done'], 0)

    def test_service_can_record_denied_task_without_publishing_as_admin(self):
        task, entries = self.task({'blocked.bin': b'blocked'})
        self.batch(task, entries, {'blocked.bin': b'blocked'})
        self.call('transfer_seal', task=task)
        with self.assertRaises(Exception):
            self.call('transfer_block', task=task, error='forged')
        blocked = self.worker('transfer_block', task=task, error='Owner access was revoked')
        self.assertEqual(blocked['state'], 'error')
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        with self.assertRaises(ValueError):
            self.worker('transfer_claim', task=task)

    def test_retention_expires_abandoned_upload_and_cleans_private_spool(self):
        task, entries = self.task({'abandoned.bin': b'abandoned'}, submit=False)
        self.batch(task, entries, {'abandoned.bin': b'abandoned'})
        lease = self.call('transfer_write_begin', task=task, batch=True, size=10240)
        stage = Path(lease['_path'])
        stage.write_bytes(b'abandoned private archive')
        with self.context(), access('files'):
            def expire_lease():
                from pyasm.biz.file_project import save
                item = find('sync', task)
                data = item.get_json_value('data')
                data['leases'][lease['token']]['expires'] = int(time()) - 1
                save(item, data)
            command = Command()
            command.execute = expire_lease
            Command.execute_cmd(command)
        self.age('sync', task)
        self.age('blob', entries[0]['blob'])
        self.call('storage_policy', revision=0, policy={'gc_grace_seconds': 0})
        self.gc(False)
        self.assertFalse(stage.exists())
        self.assertEqual(self.call('storage_status')['allocated_files'], 0)
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.call('transfer_status', task=task)

    def test_worker_rechecks_revoked_depot_rights_between_steps(self):
        from pyasm.common.errors import SecurityException
        artist = self.writer()
        change = self.client(artist, 'create_change', workspace='artist')['code']
        task = self.client(artist, 'transfer_begin', change=change, request_id='artist', submit=True)['task']
        self.client(artist, 'transfer_seal', task=task)
        with request_context(RequestContext(self.store, 'artist', 'files')):
            self.api.auth.bind_security('artist', artist['ticket'])
            claimed = file_tasks.call('transfer_claim', task=task)
            self.api.dispatch('update', ({'ticket': self.token, 'project': 'admin'},
                'sthpw/login_group?code=artists', {'access_rules': '<rules><rule group="project" code="files" access="allow"/></rules>'}))
            with self.assertRaises(SecurityException):
                file_tasks.call('transfer_verify_next', task=task, worker_token=claimed['worker_token'])
        self.worker('transfer_block', task=task, error='Access revoked')
        self.assertEqual(self.call('list', stream='main')['files'], 0)

    def test_download_begin_reuses_active_workspace_task_and_cancels_cleanly(self):
        first = self.call('transfer_begin', kind='download', workspace='work', client_root='D:/download')
        retry = self.call('transfer_begin', kind='download', workspace='work', client_root='D:/download')
        self.assertEqual(first['task'], retry['task'])
        with self.assertRaisesRegex(ValueError, 'another local root'):
            self.call('transfer_begin', kind='download', workspace='work', client_root='D:/other')
        self.call('transfer_cancel', task=first['task'])
        replacement = self.call('transfer_begin', kind='download', workspace='work', client_root='D:/other')
        self.assertNotEqual(first['task'], replacement['task'])

    def test_download_selection_identity_uses_paths_not_ui_selection_order(self):
        first=self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['b.txt','a.txt'])
        repeated=self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['a.txt','b.txt','a.txt'])
        self.assertEqual(repeated['task'],first['task'])
        self.assertEqual(repeated['paths'],['a.txt','b.txt'])

    def test_stopped_download_allows_latest_of_another_file_and_keeps_local_edits(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        self.publish({'a.txt':b'server a','b.txt':b'server b'})
        root=Path(self.temp.name)/'local';root.mkdir()
        (root/'a.txt').write_bytes(b'local edit')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            blocked=client.download('work',root,paths=['a.txt'])
            original_status=client.rpc('transfer_status',task=blocked['task'])
            self.assertEqual(original_status['state'],'blocked')
            with self.assertRaises(HTTPError):
                client.rpc('transfer_pause',task=blocked['task'],ack_revision=blocked['paused_ack_revision'],
                    reason='insufficient_disk_space',required_bytes=-1,available_bytes=1)
            self.assertEqual(client.rpc('transfer_status',task=blocked['task']),original_status)
            listed={row['task']:row for row in client.rpc('transfer_tasks')['items']}
            self.assertEqual(listed[blocked['task']]['state'],'blocked')
            result=client.download('work',root,paths=['b.txt'])
            self.assertEqual(result['state'],'complete')
            self.assertEqual(client.rpc('transfer_status',task=blocked['task'])['state'],'cancelled')
        self.assertEqual((root/'a.txt').read_bytes(),b'local edit')
        self.assertEqual((root/'b.txt').read_bytes(),b'server b')
        self.assertEqual([row['path'] for row in self.call('have',workspace='work')['items']],['b.txt'])

    def test_same_stopped_selection_resumes_pinned_task_without_replacing_it(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        self.publish({'a.txt':b'pinned'})
        root=Path(self.temp.name)/'local';root.mkdir();(root/'a.txt').write_bytes(b'local edit')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            blocked=client.download('work',root,paths=['a.txt'])
            self.publish({'a.txt':b'new head'})
            (root/'a.txt').write_bytes(b'pinned')
            resumed=client.download('work',root,paths=['a.txt'])
            self.assertEqual(resumed['task'],blocked['task'])
            self.assertEqual(resumed['state'],'complete')
            self.assertNotIn('reason',resumed)
        self.assertEqual((root/'a.txt').read_bytes(),b'pinned')

    def test_download_error_is_persisted_and_does_not_block_another_selection(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from urllib.error import URLError
        self.publish({'a.txt':b'first','b.txt':b'second'})
        root=Path(self.temp.name)/'local'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            original=client.open
            def broken(resource,**kwargs):
                if resource=='sync-download':raise URLError('test interrupted body')
                return original(resource,**kwargs)
            client.open=broken
            with self.assertRaises(URLError):client.download('work',root,paths=['a.txt'])
            task=client.status['task']
            self.assertEqual(client.rpc('transfer_status',task=task)['reason'],'download_error')
            client.open=original
            self.assertEqual(client.download('work',root,paths=['b.txt'])['state'],'complete')

    def test_interrupted_download_keeps_partial_bytes_and_resumes_with_range(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        payload=b'new download payload '*500000
        upload,entries=self.task({'large.bin':payload})
        self.block(upload,entries[0]['blob'],0,payload)
        self.finish_task(upload)
        root=Path(self.temp.name)/'partial-download'
        def stopped(event):
            if event.get('file_bytes_done'):raise InterruptedError('test stop after received bytes')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files',progress=stopped)
            with self.assertRaises(InterruptedError):client.download('work',root,paths=['large.bin'])
            task=client.status['task']
            self.assertEqual(client.rpc('transfer_status',task=task)['reason'],'interrupted')
            partial=next(root.glob('*.part'))
            offset=partial.stat().st_size
            self.assertGreater(offset,0);self.assertLess(offset,len(payload))
            resumed=FileTransferClient(url,self.token,'files')
            original=resumed.open;ranges=[]
            def opened(resource,**kwargs):
                if resource=='download':ranges.append(kwargs.get('headers',{}).get('Range'))
                return original(resource,**kwargs)
            resumed.open=opened
            from types import SimpleNamespace
            with patch('tactic_client_lib.file_transfer.shutil.disk_usage',return_value=SimpleNamespace(free=len(payload)-offset)):
                self.assertEqual(resumed.download('work',root,task=task)['state'],'complete')
            self.assertEqual(ranges,[f'bytes={offset}-'])
        self.assertEqual((root/'large.bin').read_bytes(),payload)
        self.assertFalse(partial.exists())

    def test_download_disk_preflight_blocks_before_bytes_and_resumes_same_task(self):
        from types import SimpleNamespace
        from tactic_client_lib.file_transfer import FileTransferClient
        self.publish({'a.txt':b'old'})
        root=Path(self.temp.name)/'disk-workspace'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            client.download('work',root)
            previous=client.rpc('have',workspace='work')['items']
            self.publish({'a.txt':b'new larger data','b.txt':b'fresh'})
            with patch('tactic_client_lib.file_transfer.shutil.disk_usage',return_value=SimpleNamespace(free=1)),patch.object(client,'open',wraps=client.open) as opened:
                blocked=client.download('work',root)
                self.assertFalse(any(call.args[0] in ('download','sync-download') for call in opened.call_args_list))
            self.assertEqual(blocked['reason'],'insufficient_disk_space')
            self.assertEqual((blocked['required_bytes'],blocked['available_bytes']),(20,1))
            self.assertEqual(client.rpc('transfer_status',task=blocked['task'])['state'],'blocked')
            self.assertEqual(client.rpc('have',workspace='work')['items'],previous)
            self.assertEqual((root/'a.txt').read_bytes(),b'old')
            self.assertFalse((root/'b.txt').exists())
            resumed=client.download('work',root)
            self.assertEqual(resumed['task'],blocked['task'])
            self.assertEqual(resumed['state'],'complete')
            self.assertNotIn('required_bytes',resumed)
        self.assertEqual((root/'a.txt').read_bytes(),b'new larger data')
        self.assertEqual((root/'b.txt').read_bytes(),b'fresh')

    def test_download_rejects_invalid_root_before_server_task(self):
        from tactic_client_lib.file_transfer import FileTransferClient
        from unittest.mock import Mock
        client=FileTransferClient('http://unused','test','files',rpc=Mock())
        with self.assertRaisesRegex(ValueError,'absolute'):
            client.download('work','relative/root')
        root=Path(self.temp.name)/'root.txt';root.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'directory'):
            client.download('work',root)
        client.rpc.assert_not_called()
        self.assertEqual(root.read_bytes(),b'keep')

    def test_download_disk_preflight_is_per_page_and_keeps_acknowledged_have(self):
        from types import SimpleNamespace
        from tactic_client_lib.file_transfer import FileTransferClient
        change=self.change();blob=self.upload(change,b'fresh')
        self.call('edit',change=change,edit_revision=0,chunk='page',operations=[
            {'path':f'{index:04d}.txt','blob':blob} for index in range(1000)])
        self.call('edit',change=change,edit_revision=1,chunk='tail',operations=[{'path':'1000.txt','blob':blob}])
        self.call('submit',change=change)
        root=Path(self.temp.name)/'paged-disk'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            with patch('tactic_client_lib.file_transfer.shutil.disk_usage',side_effect=[SimpleNamespace(free=5000),SimpleNamespace(free=0)]) as space:
                blocked=client.download('work',root)
            self.assertEqual(space.call_count,2)
            self.assertEqual(blocked['reason'],'insufficient_disk_space')
            self.assertEqual(blocked['files_done'],1000)
            self.assertEqual(blocked['required_bytes'],5)
            self.assertEqual(len(client.rpc('have',workspace='work',limit=1000)['items']),1000)
            self.assertFalse((root/'1000.txt').exists())
            self.assertEqual(client.download('work',root)['state'],'complete')
            self.assertEqual((root/'1000.txt').read_bytes(),b'fresh')

    def test_pause_and_replacement_keep_native_rights_have_and_rollback(self):
        from pyasm.common.errors import SecurityException
        self.publish({'a.txt':b'a','b.txt':b'b'})
        first=self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['a.txt'])
        plan=self.call('transfer_next',task=first['task'])
        with self.assertRaisesRegex(ValueError,'another selection'):
            self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['b.txt'])
        artist=self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist,'transfer_pause',task=first['task'],ack_revision=plan['ack_revision'],reason='interrupted')
        self.call('transfer_pause',task=first['task'],ack_revision=plan['ack_revision'],reason='interrupted')
        with self.assertRaisesRegex(ValueError,'another local root'):
            self.call('transfer_begin',kind='download',workspace='work',client_root='D:/other',paths=['b.txt'])
        original=FileProjectRecord._call_triggers
        def fail_new_job(record,*args,**kwargs):
            original(record,*args,**kwargs)
            if record.get_base_search_type()=='file_project/sync' and record.get_json_value('data').get('paths')==['b.txt']:
                raise ValueError('replacement trigger failed')
        with patch.object(FileProjectRecord,'_call_triggers',fail_new_job),self.assertRaisesRegex(ValueError,'replacement trigger failed'):
            self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['b.txt'])
        self.assertEqual(self.call('transfer_status',task=first['task'])['state'],'blocked')
        self.assertEqual(self.call('workspace_status',workspace='work')['active_sync'],plan['sync'])
        self.assertEqual(self.call('have',workspace='work')['items'],[])
        replacement=self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['b.txt'])
        self.assertNotEqual(replacement['task'],first['task'])

    def test_replacing_paused_download_preserves_already_acknowledged_have(self):
        change=self.change();blob=self.upload(change,b'chunk')
        self.call('edit',change=change,edit_revision=0,chunk='page',operations=[{'path':f'{index:04d}.txt','blob':blob} for index in range(1000)])
        self.call('edit',change=change,edit_revision=1,chunk='tail',operations=[{'path':'1000.txt','blob':blob}])
        self.call('submit',change=change)
        task=self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download')
        plan=self.call('transfer_next',task=task['task'])
        self.call('transfer_ack',task=task['task'],ack_revision=plan['ack_revision'],paths=[row['path'] for row in plan['items']])
        with self.assertRaisesRegex(ValueError,'advanced before pause'):
            self.call('transfer_pause',task=task['task'],ack_revision=0,reason='interrupted')
        self.call('transfer_pause',task=task['task'],ack_revision=1,reason='interrupted')
        self.call('transfer_begin',kind='download',workspace='work',client_root='D:/download',paths=['1000.txt'])
        self.assertEqual(len(self.call('have',workspace='work',limit=1000)['items']),1000)
        self.assertEqual(self.call('transfer_status',task=task['task'])['files_done'],1000)

    def test_partial_bulk_staging_cannot_submit_and_cancel_restores_entire_draft(self):
        change = self.change()
        blob = self.upload(change, b'original draft')
        self.call('edit', change=change, chunk='original', edit_revision=0,
                  operations=[{'path': 'kept.txt', 'blob': blob}])
        original = self.call('status', change=change)
        task = self.call('transfer_begin', change=change, request_id='bulk', submit=False)['task']
        files = {'new-%04d.txt' % i: ('fresh-%d' % i).encode() for i in range(1001)}
        entries = list(files.items())
        for start in (0, 1000):
            manifest = self.call('transfer_manifest', task=task, request_id='page-%d' % start,
                files=[{'path': path, 'size': len(data), 'sha256': sha256(data).hexdigest()}
                       for path, data in entries[start:start + 1000]])
            self.batch(task, manifest['items'], files)
        self.call('transfer_seal', task=task)
        staged = []
        native = file_tasks.call
        def stop_after_first_stage(action, **values):
            result = native(action, **values)
            if action == 'transfer_step':
                staged.append(result)
            return result
        with self.context(), patch.object(file_tasks, 'call', stop_after_first_stage):
            file_tasks.run_transfer(task, stopped=lambda: bool(staged))
        self.assertEqual(staged[0]['staged_files'], 1000)
        self.assertEqual(staged[0]['state'], 'running')
        for action, values in [('submit', {}), ('update_change', {'description': 'blocked', 'request_id': 'blocked'})]:
            with self.assertRaisesRegex(ValueError, 'Finish or cancel the upload'):
                self.call(action, change=change, **values)
        self.call('transfer_cancel', task=task)
        restored = self.call('status', change=change)
        self.assertEqual(restored['work_root'], original['work_root'])
        self.assertEqual(restored['files'], original['files'])
        self.assertNotIn('active_transfer', restored)
        self.assertGreater(restored['edit_revision'], original['edit_revision'])
        self.assertEqual(self.call('locks', stream='main', paths=['new-0000.txt'])['items'], [])
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.call('submit', change=change)
        self.assertEqual(self.call('list', stream='main')['items'][0]['path'], 'kept.txt')

    @contextmanager
    def context(self):
        with request_context(RequestContext(self.store, 'admin', 'files')):
            self.api.auth.bind_security('admin', self.token)
            yield

    def worker(self, action, **kwargs):
        with self.context():
            return file_tasks.call(action, **kwargs)

    def task(self, files, submit=True):
        change = self.change()
        task = self.call('transfer_begin', change=change, request_id='begin', submit=submit)['task']
        manifest = self.call('transfer_manifest', task=task, request_id='manifest',
            files=[{'path': path, 'size': len(data), 'sha256': sha256(data).hexdigest()} for path, data in files.items()])
        return task, manifest['items']

    def batch(self, task, descriptors, files):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for entry in descriptors:
                header = tarfile.TarInfo(entry['blob'])
                header.size = len(files[entry['path']])
                archive.addfile(header, io.BytesIO(files[entry['path']]))
        raw = buffer.getvalue()
        lease = self.call('transfer_write_begin', task=task, batch=True, size=len(raw))
        Path(lease['_path']).write_bytes(raw)
        try:
            return self.call('transfer_batch_commit', task=task, token=lease['token'])
        finally:
            self.call('transfer_write_abort', task=task, token=lease['token'])
            Path(lease['_path']).unlink(missing_ok=True)

    def block(self, task, blob, offset, raw):
        lease = self.call('transfer_write_begin', task=task, blob=blob, offset=offset, size=len(raw))
        path = Path(lease['_path'])
        with path.open('r+b' if path.exists() else 'w+b') as stream:
            stream.truncate(offset)
            stream.seek(offset)
            stream.write(raw)
        return self.call('transfer_write_commit', task=task, blob=blob, token=lease['token'])

    def finish_task(self, task):
        self.call('transfer_seal', task=task)
        with self.context():
            return file_tasks.run_transfer(task)

    def age(self, kind, code, seconds=10000000):
        with self.context(), access('files'), maintenance('files'):
            def execute():
                row = find(kind, code)
                row.set_value('created_at', int(time()) - seconds)
                row.set_value('updated_at', int(time()) - seconds)
                row.commit()
            command = Command(log_exception=False)
            command.execute = execute
            Command.execute_cmd(command)

    def gc(self, dry=False):
        task = self.call('gc_begin', dry_run=dry)['code']
        with self.context():
            return file_tasks.run_gc(task)

    def test_batch_blob_permission_failure_rolls_back_all_bytes(self):
        from pyasm.common.errors import SecurityException
        from pyasm.biz.file_project import blob_file_path
        files = {'first.bin': b'first', 'denied.bin': b'denied'}
        task, entries = self.task(files)
        denied = entries[-1]['blob']
        original = FileProjectRecord._check_business_write
        def authorize(row, access=None):
            if row.get_base_search_type() == 'file_project/blob' and row.get_code() == denied and access == 'edit':
                raise SecurityException('Blob edit access revoked')
            return original(row, access)
        with patch.object(FileProjectRecord, '_check_business_write', authorize):
            with self.assertRaisesRegex(SecurityException, 'access revoked'):
                self.batch(task, entries, files)
        status = self.call('transfer_status', task=task)
        self.assertEqual((status['files_done'], status['bytes_done']), (0, 0))
        for entry in entries:
            self.assertEqual(self.call('transfer_received', task=task, blob=entry['blob'])['received'], 0)
            self.assertFalse(blob_file_path('files', entry['blob'], self.store.data_dir).exists())
        self.batch(task, entries, files)
        self.assertEqual(self.finish_task(task)['state'], 'submitted')

    def test_fresh_batch_job_progress_retry_and_real_versions(self):
        files = {'a.bin': b'first new bytes', 'nested/empty': b'', 'b.bin': b'another file'}
        task, entries = self.task(files)
        self.batch(task, entries, files)
        initial = self.call('transfer_status', task=task)
        self.assertEqual((initial['files_done'], initial['verified_files']), (3, 3))
        self.batch(task, entries, files)
        self.assertEqual(self.call('transfer_status', task=task)['bytes_done'], sum(map(len, files.values())))
        self.assertEqual(self.finish_task(task)['state'], 'submitted')
        self.assertEqual(self.call('list', stream='main')['files'], 3)
        import base64
        for path, value in files.items():
            self.assertEqual(base64.b64decode(self.call('read', stream='main', path=path)['data']), value)
        self.assertEqual(self.call('transfer_tasks')['items'][0]['task'], task)

    def test_background_worker_reuses_tickets_between_file_jobs(self):
        from concurrent.futures import ThreadPoolExecutor
        from time import monotonic, sleep
        # One real worker makes the ticket count independent of thread assignment.
        def executor(**kwargs):
            return ThreadPoolExecutor(max_workers=1, thread_name_prefix=kwargs['thread_name_prefix'])
        with patch.object(file_tasks, 'ThreadPoolExecutor', side_effect=executor), self.http(worker=True):
            counts = []
            for index in range(3):
                files = {'reuse-%s.bin' % index: b'fresh bytes'}
                task, entries = self.task(files)
                self.batch(task, entries, files)
                self.call('transfer_seal', task=task)
                deadline = monotonic() + 20
                while True:
                    status = self.call('transfer_status', task=task)
                    if status['state'] in ('submitted', 'error', 'cancelled'):
                        break
                    self.assertLess(monotonic(), deadline, status)
                    sleep(.05)
                self.assertEqual(status['state'], 'submitted', status)
                with self.store.connection() as db:
                    counts.append(db.execute('SELECT COUNT(*) FROM ticket').fetchone()[0])
            self.assertEqual(counts, [counts[0]] * 3)

    def test_resume_committed_offset_partial_tail_and_background_checksum(self):
        data = sha256(b'fresh large source').digest() * 262144
        task, entries = self.task({'large.bin': data})
        blob = entries[0]['blob']
        self.block(task, blob, 0, data[:4 * 1024 * 1024])
        lease = self.call('transfer_write_begin', task=task, blob=blob, offset=4 * 1024 * 1024, size=4 * 1024 * 1024)
        with Path(lease['_path']).open('ab') as stream:
            stream.write(b'uncommitted partial tail')
        self.call('transfer_write_abort', task=task, token=lease['token'])
        plan = self.client(self.ticket, 'transfer_next', task=task)
        self.assertEqual(plan['items'][0]['received'], 4 * 1024 * 1024)
        self.block(task, blob, 4 * 1024 * 1024, data[4 * 1024 * 1024:])
        self.assertEqual(self.call('transfer_status', task=task)['verified_files'], 0)
        self.assertEqual(self.finish_task(task)['state'], 'submitted')
        self.assertEqual(self.call('transfer_status', task=task)['verified_bytes'], len(data))

    def test_quota_is_reserved_before_allocation_and_batch_rolls_back(self):
        self.call('storage_policy', revision=0, policy={'bytes_limit': 5, 'files_limit': 2})
        task, entries = self.task({'a': b'abc', 'b': b'de'})
        with self.assertRaisesRegex(ValueError, 'quota'):
            self.call('transfer_manifest', task=task, request_id='overquota', files=[{'path': 'extra', 'size': 1}])
        self.assertEqual(self.call('storage_status')['allocated_bytes'], 5)
        original = FileProjectRecord._call_triggers
        def failing(row, *args, **kwargs):
            if row.get_base_search_type() == 'file_project/sync' and row.get_json_value('data').get('files_done'):
                raise ValueError('late transfer callback')
            return original(row, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', failing), self.assertRaisesRegex(ValueError, 'late transfer callback'):
            self.batch(task, entries, {'a': b'abc', 'b': b'de'})
        self.assertEqual(self.call('transfer_status', task=task)['files_done'], 0)
        self.assertTrue(all(entry['received'] == 0 for entry in self.call('transfer_next', task=task)['items']))
        self.batch(task, entries, {'a': b'abc', 'b': b'de'})
        self.finish_task(task)
        with self.assertRaisesRegex(ValueError, 'quota'):
            self.call('upload_begin', change=self.change(), size=1)

    def test_worker_forgery_foreign_tasks_and_parallel_limits_are_rejected(self):
        task, entries = self.task({'a': b'abc', 'b': b'def'})
        for action in ('transfer_claim', 'transfer_verify_finish', 'gc_step'):
            with self.assertRaises(Exception):
                self.call(action, task=task, sha256='0' * 64)
        artist = self.writer()
        with self.assertRaises(Exception):
            self.client(artist, 'transfer_status', task=task)
        self.call('storage_policy', revision=0, policy={'max_parallel': 1})
        lease = self.call('transfer_write_begin', task=task, blob=entries[0]['blob'], size=3)
        with self.assertRaisesRegex(ValueError, 'concurrency limit'):
            self.call('transfer_write_begin', task=task, blob=entries[1]['blob'], size=3)
        self.call('transfer_write_abort', task=task, token=lease['token'])
        self.block(task, entries[1]['blob'], 0, b'def')

    def test_background_checksum_failure_never_publishes(self):
        task, entries = self.task({'a': b'expected'})
        self.block(task, entries[0]['blob'], 0, b'wrong!!!')
        self.call('transfer_seal', task=task)
        with self.context(), self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            file_tasks.run_transfer(task)
        self.assertEqual(self.call('transfer_status', task=task)['state'], 'error')
        self.assertEqual(self.call('list', stream='main')['files'], 0)

    def test_gc_keeps_history_shelves_have_and_active_transfer(self):
        published = self.publish({'a': b'published'})
        self.publish({'a': b'latest'})
        draft = self.change()
        blob = self.upload(draft, b'shelf bytes')
        self.edit(draft, [{'path': 'shelf', 'blob': blob}])
        shelf = self.call('shelve', change=draft, edit_revision=1, request_id='shelf')['code']
        self.call('revert', change=draft)
        task, entries = self.task({'active': b'active bytes'})
        self.block(task, entries[0]['blob'], 0, b'active bytes')
        abandoned = self.change()
        garbage = self.upload(abandoned, b'garbage')
        self.call('revert', change=abandoned)
        self.age('change', abandoned)
        self.age('blob', garbage)
        self.call('storage_policy', revision=0, policy={'gc_grace_seconds': 0})
        result = self.gc()
        self.assertEqual(result['state'], 'complete')
        with self.context(), access('files'):
            self.assertEqual(find('blob', garbage).get_json_value('data')['state'], 'purged')
            self.assertEqual(find('blob', blob).get_json_value('data')['state'], 'ready')
        import base64
        self.assertEqual(base64.b64decode(self.call('read', stream='main', path='a', published_change=published)['data']), b'published')
        self.assertEqual(base64.b64decode(self.call('read', shelf=shelf, path='shelf')['data']), b'shelf bytes')
        self.assertEqual(self.finish_task(task)['state'], 'submitted')
        self.assertEqual(self.call('storage_status')['allocated_files'], 4)

    def test_gc_dry_run_fence_and_no_missing_reference_can_be_swept(self):
        import base64
        change = self.change()
        blob = self.upload(change, b'old')
        self.call('revert', change=change)
        self.age('change', change)
        self.age('blob', blob)
        self.call('storage_policy', revision=0, policy={'gc_grace_seconds': 0})
        task = self.call('gc_begin', dry_run=True)['code']
        self.worker('gc_step', task=task)
        self.publish({'new': b'new bytes'})
        result = self.worker('gc_step', task=task)
        self.assertEqual(result['state'], 'running')
        self.assertEqual(result['restarts'], 0)
        with self.context():
            result = file_tasks.run_gc(task)
        self.assertEqual(result['candidate_bytes'], 3)
        with self.context(), access('files'):
            self.assertEqual(find('blob', blob).get_json_value('data')['state'], 'ready')
        self.assertEqual(self.call('list', stream='main')['files'], 1)
        self.assertEqual(base64.b64decode(self.call('read', stream='main', path='new')['data']), b'new bytes')

    def test_gc_completes_during_continuous_submits_and_preserves_new_history(self):
        import base64
        change = self.change()
        garbage = self.upload(change, b'garbage')
        self.call('revert', change=change)
        self.age('change', change)
        self.age('blob', garbage)
        self.call('storage_policy', revision=0, policy={'gc_grace_seconds': 0})
        task = self.call('gc_begin', dry_run=False)['code']
        versions = []
        for index in range(100):
            self.publish({'live.txt': str(index).encode()})
            versions.append(self.call('history', stream='main', path='live.txt')['items'][0])
            result = self.worker('gc_step', task=task)
            for entry in result.get('reap', []):
                from pyasm.biz.file_bytes import byte_lock
                with byte_lock(Path(entry['_path'])):
                    Path(entry['_path']).unlink(missing_ok=True)
                Path(entry['_path'] + '.lock').unlink(missing_ok=True)
                self.worker('gc_purged', task=task, blob=entry['blob'])
            if result['state'] == 'complete':
                break
        self.assertEqual(result['state'], 'complete', {key: result.get(key) for key in ('phase', 'table', 'objects_done', 'restarts')})
        self.assertEqual(result['restarts'], 0)
        self.assertGreater(result['purged'], 0)
        self.assertEqual(base64.b64decode(self.call('read', stream='main', path='live.txt')['data']), str(index).encode())
        self.assertEqual(len(self.call('history', stream='main', path='live.txt', limit=100)['items']), len(versions))

    def test_gc_barrier_includes_roots_created_by_late_native_page_callback(self):
        self.publish({'base.txt': b'base'})
        task = self.call('gc_begin', dry_run=True)['code']
        for _ in range(4):
            self.worker('gc_step', task=task)
        change = self.change()
        blob = self.upload(change, b'late root bytes')
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'late-gc-root',
            'event': 'insert|file_project/page', 'class_name': 'test_file_transfer.LateGcRootProbe',
            'mode': 'same process,same transaction'}))
        LateGcRootProbe.enabled, LateGcRootProbe.change = True, None
        try:
            self.call('edit', change=change, edit_revision=0, chunk='late',
                      operations=[{'path': 'late.txt', 'blob': blob}])
        finally:
            LateGcRootProbe.enabled = False
        self.assertIsNotNone(LateGcRootProbe.change)
        with self.context(), access('files'):
            from pyasm.biz.file_project import PageStore
            from pyasm.biz.file_catalog import FileCatalog
            pages = PageStore()
            catalog = FileCatalog(pages.load, pages.save)
            workspace = find('workspace', 'work').get_json_value('data')
            self.assertIsNotNone(catalog.get(workspace['pending_root'], LateGcRootProbe.change))
            result = file_tasks.run_gc(task)
            self.assertEqual(find('blob', blob).get_json_value('data')['state'], 'ready')
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(result['restarts'], 0)
