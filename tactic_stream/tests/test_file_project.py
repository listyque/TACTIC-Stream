"""Isolated native API checks for the parallel file-project backend."""
import base64
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.biz.file_project import COMMAND
from pyasm.common import Config
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from pyasm.command import Trigger


class VersionProbe(Trigger):
    counts = []

    def execute(self):
        from pyasm.search import Search
        self.counts.append(Search('file_project/version').get_count())


class FileProjectFixture:
    database_config = ''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'TACTIC_CONFIG_PATH': self.database_config, 'TACTIC_TMP_CONFIG_PATH': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(self.temp.name))
        self.store.initialize(hash_password('file-test-password'))
        self.api = Api(self.store)
        self.token = self.api.get_ticket('admin', 'file-test-password')
        ticket = {'ticket': self.token, 'project': 'admin'}
        self.api.dispatch('execute_cmd', (ticket, 'tactic.command.project_template_cmd.ProjectTemplateInstallerCmd',
            {'project_code': 'files', 'project_title': 'Files', 'template_code': 'perforce_like'}))
        self.ticket = {'ticket': self.token, 'project': 'files'}
        self.call('create_depot', code='main')
        self.call('create_stream', code='main', depot='main')
        self.call('create_workspace', code='work', stream='main', local_root='D:/local/files')

    def call(self, action, **kwargs):
        return self.api.dispatch('execute_cmd', (self.ticket, COMMAND, {'action': action, **kwargs}))['info']

    def change(self):
        return self.call('create_change', workspace='work')['code']

    def upload(self, change, data=b'hello'):
        blob = self.call('upload_begin', change=change, size=len(data))['code']
        if data:
            self.call('upload_chunk', change=change, blob=blob, offset=0, data=base64.b64encode(data).decode('ascii'))
        self.call('upload_finish', change=change, blob=blob, sha256=sha256(data).hexdigest())
        return blob


class FileProjectTest(FileProjectFixture, unittest.TestCase):
    def test_numbered_changelist_references_move_and_shelf(self):
        source = self.call('create_change', workspace='work')
        target = self.call('create_change', workspace='work')
        source_ref, target_ref = '#%d' % source['number'], '#%d' % target['number']
        self.assertEqual(self.call('status', change=source_ref)['code'], source['code'])
        blob = self.upload(source['code'])
        self.call('edit', change=source_ref, edit_revision=0, chunk='number', operations=[{'path': 'file.txt', 'blob': blob}])
        self.call('move_files', change=source_ref, target_change=target_ref, edit_revision=1, target_edit_revision=0, request_id='move', paths=['file.txt'])
        self.assertEqual([row['path'] for row in self.call('change_files', change=target_ref)['items']], ['file.txt'])
        shelf = self.call('shelve', change=target_ref, edit_revision=1, request_id='shelf')
        self.assertEqual([row['path'] for row in self.call('change_files', shelf='#%d' % shelf['number'])['items']], ['file.txt'])
        for reference in ('#0', '#-1', '#999999', '#9999999999999999999999999'):
            with self.assertRaises(ValueError):
                self.call('status', change=reference)

    def test_browse_directories_numbers_and_immutable_cursor(self):
        first, second = self.change(), self.change()
        self.assertNotEqual(self.call('status', change=first)['number'], self.call('status', change=second)['number'])
        blob = self.upload(first)
        self.call('edit', change=first, edit_revision=0, chunk='tree', operations=[
            {'path': path, 'blob': blob} for path in ['root.txt', 'assets/hero/main.ma', 'assets/props/tool.ma', 'shots/Шот 01/layout.ma']])
        self.call('submit', change=first)
        page = self.call('browse', stream='main', limit=2)
        self.assertEqual([row['path'] for row in page['items']], ['assets/', 'root.txt'])
        self.assertEqual(page['after'], 'root.txt')
        after = self.call('browse', stream='main', after=page['after'], published_change=page['published_change'])
        self.assertEqual([row['path'] for row in after['items']], ['shots/'])
        inside = self.call('browse', stream='main', directory='assets/')
        self.assertEqual([row['path'] for row in inside['items']], ['assets/hero/', 'assets/props/'])
        next_change = self.change()
        blob = self.upload(next_change)
        self.call('edit', change=next_change, edit_revision=0, chunk='new', operations=[{'path': 'assets/new.txt', 'blob': blob}])
        self.call('submit', change=next_change)
        pinned = self.call('browse', stream='main', directory='assets/', published_change=page['published_change'])
        self.assertEqual(inside['items'], pinned['items'])
        self.assertIn('assets/new.txt', [row['path'] for row in self.call('browse', stream='main', directory='assets/')['items']])
        for arguments in ({'directory': '../'}, {'directory': 'assets'}, {'directory': 'assets/', 'after': 'shots/'}, {'directory': 'assets/', 'after': 'assets/hero/a.ma'}, {'limit': 1001}):
            with self.assertRaises(ValueError):
                self.call('browse', stream='main', **arguments)

    def test_lifecycle_and_isolation(self):
        change = self.change()
        blob = self.upload(change)
        ops = [{'path': 'dir/f%04d.bin' % i, 'blob': blob} for i in range(1000)]
        args = dict(change=change, chunk='chunk1', edit_revision=0, operations=ops)
        result = self.call('edit', **args)
        self.assertEqual(result['files'], 1000)
        self.assertEqual(self.call('edit', **args), result)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        submitted = self.call('submit', change=change)
        self.assertEqual(submitted['revision'], 1)
        page = self.call('list', stream='main', limit=110)
        self.assertEqual(len(page['items']), 110)
        page2 = self.call('list', stream='main', limit=110, after=page['after'], published_change=page['published_change'])
        self.assertGreater(page2['items'][0]['path'], page['items'][-1]['path'])
        self.assertEqual(base64.b64decode(self.call('read', stream='main', path='dir/f0000.bin')['data']), b'hello')
        self.assertEqual(len(self.call('history', stream='main', path='dir/f0000.bin')['items']), 1)
        self.call('create_stream', code='branch', depot='main', parent='main')
        self.assertEqual(self.call('list', stream='branch')['files'], 1000)
        with self.assertRaises(Exception):
            self.api.dispatch('query', (self.ticket, 'file_project/page', []))
        self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'admin'}, 'tactic.command.CreateProjectCmd',
            {'project_code': 'classic', 'project_title': 'Classic'}))
        with self.assertRaisesRegex(ValueError, 'requires a file_project'):
            self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'classic'}, COMMAND, {'action': 'capabilities'}))

    def test_checkout_conflicts_and_atomic_failure(self):
        first, other = self.change(), self.change()
        self.call('checkout', change=first, paths=['a.bin'], mode='exclusive')
        with self.assertRaisesRegex(ValueError, 'Exclusive checkout'):
            self.call('checkout', change=other, paths=['a.bin'])
        blob = self.upload(first)
        self.call('edit', change=first, chunk='one', edit_revision=1, operations=[{'path': 'a.bin', 'blob': blob}])
        from pyasm.biz.file_project import FileProjectRecord
        original = FileProjectRecord._call_triggers
        def failing(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data')['state'] == 'submitted':
                raise ValueError('submission trigger failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', failing):
            with self.assertRaisesRegex(ValueError, 'submission trigger failure'):
                self.call('submit', change=first)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.assertEqual(self.call('status', change=first)['state'], 'pending')
        self.call('submit', change=first)
        self.call('checkout', change=other, paths=['a.bin'])
        with self.assertRaisesRegex(ValueError, 'head changed'):
            self.call('submit', change=other)

    def test_batch_upload_deletion_and_resumable_sync(self):
        change = self.change()
        descriptors = [{'path': 'a.bin', 'size': 3}, {'path': 'b.bin', 'size': 0}]
        args = dict(change=change, request_id='small', files=descriptors)
        uploaded = self.call('upload_begin', **args)
        self.assertEqual(uploaded, self.call('upload_begin', **args))
        self.assertEqual(len(self.call('uploads', change=change)['items']), 2)
        items = [{'blob': row['blob'], 'data': base64.b64encode(b'abc' if row['size'] else b'').decode('ascii')}
                 for row in uploaded['items']]
        result = self.call('upload_batch', change=change, items=items)
        self.assertEqual(result, self.call('upload_batch', change=change, items=items))
        self.call('edit', change=change, chunk='one', edit_revision=0,
                  operations=[{'path': row['path'], 'blob': row['blob']} for row in uploaded['items']])
        self.call('submit', change=change)
        job = self.call('sync_begin', workspace='work')
        self.assertEqual(self.call('workspace_status', workspace='work')['active_sync'], job['code'])
        plan = self.call('sync_next', sync=job['code'])
        self.api = Api(Store(self.store.data_dir))
        self.assertEqual(self.call('sync_next', sync=job['code']), plan)
        self.assertEqual(len(plan['items']), 2)
        deleted = self.change()
        self.call('edit', change=deleted, chunk='delete', edit_revision=0, operations=[{'path': 'a.bin', 'delete': True}])
        self.call('submit', change=deleted)
        self.assertEqual(self.call('list', stream='main')['files'], 1)
        self.assertEqual(len(self.call('history', stream='main', path='a.bin')['items']), 2)
        self.assertEqual(self.call('transfer', stream='main', path='a.bin', published_change=plan['published_change'])['size'], 3)
        ack = dict(sync=job['code'], ack_revision=0, paths=[item['path'] for item in plan['items']])
        done = self.call('sync_ack', **ack)
        self.assertEqual(done['state'], 'complete')
        self.assertEqual(done, self.call('sync_ack', **ack))
        self.assertEqual(self.call('sync_status', sync=job['code'])['bytes_done'], 3)
        job2 = self.call('sync_begin', workspace='work')
        self.assertTrue(self.call('sync_next', sync=job2['code'])['items'][0]['deleted'])
        self.call('sync_cancel', sync=job2['code'])

    def test_ordinary_user_permissions_and_cross_database_trigger(self):
        from pyasm.biz.file_project import FileProjectRecord, TABLES
        from pyasm.common.errors import SecurityException
        password = 'private-file-project-writer-password'
        system = {'ticket': self.token, 'project': 'admin'}
        self.api.dispatch('insert', (system, 'sthpw/login', {'code': 'project_writer', 'login': 'project_writer', 'password': hash_password(password)}))
        group = self.api.dispatch('insert', (system, 'sthpw/login_group', {'code': 'file_writers', 'login_group': 'file_writers'}))
        self.api.dispatch('insert', (system, 'sthpw/login_in_group', {'code': 'file_writer_group', 'login': 'project_writer', 'login_group': 'file_writers'}))
        def set_rules(xml):
            self.api.dispatch('update', (system, group['__search_key__'], {'access_rules': xml}))
        grants = ''.join('<rule group="search_type" code="file_project/%s" project="files" access="allow"/>' % kind for kind in TABLES)
        rules = '<rules><rule group="project" code="files" access="allow"/>' + grants
        set_rules(rules + '<rule group="file_depot" code="main" project="files" access="allow"/></rules>')
        admin = self.ticket
        self.ticket = {'ticket': self.api.get_ticket('project_writer', password), 'project': 'files'}
        self.call('create_workspace', code='artist', stream='main', local_root='D:/artist')
        change = self.call('create_change', workspace='artist')['code']
        blob = self.upload(change)
        self.call('edit', change=change, chunk='one', edit_revision=0, operations=[{'path': 'a.bin', 'blob': blob}])
        set_rules(rules + '<rule group="file_depot" code="main" project="files" access="view"/></rules>')
        self.call('create_workspace', code='reader', stream='main', local_root='D:/reader')
        reader_sync = self.call('sync_begin', workspace='reader')['code']
        self.call('sync_cancel', sync=reader_sync)
        with self.assertRaises(SecurityException):
            self.call('submit', change=change)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        set_rules(rules + '<rule group="file_depot" code="main" project="files" access="allow"/>'
            '<rule group="sobject_column" search_type="file_project/stream" column="data" project="files" access="view"/></rules>')
        with self.assertRaises(SecurityException):
            self.call('submit', change=change)
        set_rules(rules + '<rule group="file_depot" code="main" project="files" access="allow"/></rules>')
        self.call('submit', change=change)
        self.ticket = admin
        with self.assertRaises(SecurityException):
            self.call('status', change=change)
        own = self.change()
        own_blob = self.upload(own)
        self.call('edit', change=own, chunk='one', edit_revision=0, operations=[{'path': 'b.bin', 'blob': own_blob}])
        from pyasm.search import SearchType
        from pyasm.search.transaction import TransactionException
        original = FileProjectRecord._call_triggers
        def other_database(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/change' and record.get_json_value('data')['state'] == 'submitted':
                item = SearchType.create('sthpw/note')
                item.set_value('note', 'must roll back')
                item.set_value('login', 'admin')
                item.commit(log_transaction=False)
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', other_database):
            with self.assertRaises(TransactionException):
                self.call('submit', change=own)
        self.assertEqual(self.call('list', stream='main')['files'], 1)
        self.assertEqual(self.call('status', change=own)['state'], 'pending')

    def test_second_file_project_and_stream_baseline_cursor(self):
        self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'admin'}, 'tactic.command.CreateProjectCmd',
            {'project_code': 'files_two', 'project_title': 'Files two', 'project_mode': 'file_project'}))
        self.assertEqual(self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'files_two'}, COMMAND,
            {'action': 'capabilities'}))['info']['mode'], 'file_project')
        change = self.change()
        blob = self.upload(change)
        self.call('edit', change=change, chunk='one', edit_revision=0, operations=[{'path': 'a.bin', 'blob': blob}])
        with self.assertRaisesRegex(ValueError, 'different data'):
            self.call('edit', change=change, chunk='one', edit_revision=0, operations=[{'path': 'b.bin', 'blob': blob}])
        self.assertEqual(self.call('list', change=change)['files'], 1)
        self.call('submit', change=change)
        self.call('create_stream', code='branch', depot='main', parent='main')
        base = self.call('list', stream='branch')['published_change']
        self.assertIsNotNone(base)
        self.assertEqual(self.call('transfer', stream='branch', path='a.bin', published_change=base)['size'], 5)

    def test_registered_native_triggers_keep_order_and_reject_deferred_submit(self):
        VersionProbe.counts = []
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'version-probe',
            'event': 'insert|file_project/version', 'class_name': 'test_file_project.VersionProbe',
            'mode': 'same process,same transaction'}))
        change = self.change()
        blob = self.upload(change)
        self.call('edit', change=change, chunk='one', edit_revision=0,
                  operations=[{'path': '%d.bin' % index, 'blob': blob} for index in range(3)])
        self.assertEqual(VersionProbe.counts, [1, 2, 3])
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'deferred-probe',
            'event': 'update|file_project/stream', 'class_name': 'test_file_project.VersionProbe',
            'mode': 'same process,new transaction'}))
        from pyasm.common.errors import UnsupportedContract
        with self.assertRaisesRegex(UnsupportedContract, 'synchronous triggers'):
            self.call('submit', change=change)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.assertEqual(self.call('status', change=change)['state'], 'pending')

    def test_checksum_runs_before_writer_lock_and_zero_file_rolls_back(self):
        from pyasm.search.transaction import Transaction
        change = self.change()
        blob = self.call('upload_begin', change=change, size=3)['code']
        self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
        digest = sha256()
        checked = []
        class Probe:
            def update(probe, part):
                for sql in Transaction.get().get_databases().values():
                    self.assertFalse(sql._has_writes, 'Hash must run before writes')
                    if sql.vendor == 'Sqlite' and sql.conn:
                        self.assertFalse(sql.conn.in_transaction, 'Hash must run before SQLite writer locks')
                checked.append(part)
                digest.update(part)
            def hexdigest(probe):
                return digest.hexdigest()
        with patch('tactic.command.file_project_cmd.sha256', return_value=Probe()):
            self.call('upload_finish', change=change, blob=blob)
        self.assertEqual(checked, [b'abc'])
        empty = self.call('upload_begin', change=change, size=0)['code']
        from pyasm.biz.file_project import FileProjectRecord, blob_file_path
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/blob' and record.get_json_value('data')['state'] == 'ready':
                raise ValueError('zero file rollback')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', fail), self.assertRaisesRegex(ValueError, 'zero file rollback'):
            self.call('upload_finish', change=change, blob=empty)
        self.assertFalse(blob_file_path('files', empty, self.store.data_dir).exists())
        self.call('upload_finish', change=change, blob=empty)

    def test_binary_http_transport_and_ranges(self):
        import socket
        import threading
        from time import monotonic, sleep
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        import uvicorn
        from tactic_stream.server.app import create_app
        change = self.change()
        blob = self.call('upload_begin', change=change, size=5)['code']
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        url = 'http://127.0.0.1:%s' % sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(self.store.data_dir), log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        try:
            deadline = monotonic() + 10
            while not server.started and thread.is_alive() and monotonic() < deadline:
                sleep(.01)
            self.assertTrue(server.started)
            upload = url + '/file-project/upload?project=files&change=%s&blob=%s&offset=0' % (change, blob)
            with urlopen(Request(upload, data=b'hello', method='PUT', headers={'X-Tactic-Ticket': self.token})) as response:
                self.assertEqual(response.status, 200)
            self.call('upload_finish', change=change, blob=blob)
            self.call('edit', change=change, chunk='one', edit_revision=0, operations=[{'path': 'a.bin', 'blob': blob}])
            self.call('submit', change=change)
            download = url + '/file-project/download?project=files&stream=main&path=a.bin'
            with urlopen(Request(download, headers={'X-Tactic-Ticket': self.token, 'Range': 'bytes=1-3'})) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), b'ell')
            with self.assertRaises(HTTPError) as denied:
                urlopen(download)
            self.assertEqual(denied.exception.code, 403)
            denied.exception.close()
            job = self.call('sync_begin', workspace='work')
            sync_url = url + '/file-project/sync-download?project=files&sync=' + job['code']
            import io
            import tarfile
            with urlopen(Request(sync_url, headers={'X-Tactic-Ticket': self.token})) as response:
                self.assertEqual(response.headers['X-Tactic-Ack-Revision'], '0')
                with tarfile.open(fileobj=io.BytesIO(response.read())) as archive:
                    self.assertEqual(archive.getnames(), ['a.bin'])
                    self.assertEqual(archive.extractfile('a.bin').read(), b'hello')
            draft = self.change()
            uploaded = self.upload(draft, b'world')
            self.call('edit', change=draft, chunk='draft', edit_revision=0, operations=[{'path': 'a.bin', 'blob': uploaded}])
            shelf = self.call('shelve', change=draft, edit_revision=1, request_id='shelf')['code']
            shelf_url = url + '/file-project/download?project=files&shelf=%s&path=a.bin' % shelf
            with urlopen(Request(shelf_url, headers={'X-Tactic-Ticket': self.token, 'Range': 'bytes=1-3'})) as response:
                self.assertEqual(response.read(), b'orl')
            other = self.change()
            uploaded = self.upload(other, b'other')
            self.call('edit', change=other, chunk='other', edit_revision=0, operations=[{'path': 'a.bin', 'blob': uploaded}])
            self.call('submit', change=other)
            integration = self.call('rebase_begin', change=draft, edit_revision=1, request_id='rebase')['integration']
            self.call('integration_next', change=draft, integration=integration, edit_revision=1, after='', request_id='next')
            conflict_url = url + '/file-project/download?project=files&change=%s&integration=%s&edit_revision=1&conflict_side=base&path=a.bin' % (draft, integration)
            with urlopen(Request(conflict_url, headers={'X-Tactic-Ticket': self.token})) as response:
                self.assertEqual(response.read(), b'hello')
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
            self.assertFalse(thread.is_alive(), 'Owned HTTP test server must be stopped')


if __name__ == '__main__':
    unittest.main()
