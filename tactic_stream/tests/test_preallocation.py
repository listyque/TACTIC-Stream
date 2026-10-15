import test_checkin as checkin_tests
import test_read_parity as read_tests
import shutil
import tempfile
from pathlib import Path
from xmlrpc.client import Binary
from pyasm.biz import Project, Snapshot, FileRange
from pyasm.checkin import FileAppendCheckin, FileGroupAppendCheckin, FileCheckin, CheckinException
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from pyasm.security.authenticator import hash_password


class PreallocationParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='preallocation_contract', project='admin', name='paths_and_file_api')]

    new_result = checkin_tests.CheckinParity.new_result

    def test_preallocation_upload_rollback_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            ticket = {'ticket': self.ticket, 'project': 'admin'}
            api = Api(store)
            parent_key = 'sthpw/project?code=admin'
            row = api.dispatch('create_snapshot', (ticket, parent_key, 'preallocation_rollback'))
            api.dispatch('upload_file', (ticket, r'C:\client\old.bin', Binary(b'old')))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', self.ticket)
                snapshot = Snapshot.get_by_code(row['code'])
                upload = Path(Environment.get_upload_dir()) / 'old.bin'
                self.assertEqual(upload.read_bytes(), b'old')
                cmd = Command()
                def overwrite():
                    cmd.get_transaction().set_sync(False)
                    api.upload_file(ticket, 'old.bin', b'new')
                    raise ValueError('upload rollback')
                cmd.execute = overwrite
                with self.assertRaisesRegex(ValueError, 'upload rollback'):
                    Command.execute_cmd(cmd)
                self.assertEqual(upload.read_bytes(), b'old')
                cmd = Command()
                paths = []
                def allocate():
                    cmd.get_transaction().set_sync(False)
                    path = snapshot.get_preallocated_path(file_name='scene.txt', checkin_type='strict')
                    paths.append(Path(path))
                    Path(path).write_bytes(b'preallocated')
                    Command.execute_cmd(FileAppendCheckin(row['code'], [path], ['main'], mode='preallocate', keep_file_name=True))
                    raise ValueError('preallocation rollback')
                cmd.execute = allocate
                with self.assertRaisesRegex(ValueError, 'preallocation rollback'):
                    Command.execute_cmd(cmd)
                self.assertFalse(paths[0].exists())
                self.assertFalse(paths[0].parent.exists())
                self.assertTrue(any(path.read_bytes() == b'preallocated' for path in (Path(Environment.get_tmp_dir()) / 'undo').rglob('*') if path.is_file()))
                snapshot = Snapshot.get_by_code(row['code'])
                self.assertEqual(snapshot.get_all_file_names(), [])
                # A preallocation must not register a file from another directory.
                outside = Path(directory) / 'outside.txt'
                outside.write_bytes(b'outside')
                with self.assertRaises(CheckinException):
                    Command.execute_cmd(FileCheckin(Project.get(), str(outside), context='wrong_preallocation', mode='preallocate', checkin_type='strict'))
                self.assertEqual(outside.read_bytes(), b'outside')
                # Existing File reads stay clean; duplicate registration is refused.
                cmd = Command()
                def register():
                    cmd.get_transaction().set_sync(False)
                    path = snapshot.get_preallocated_path(file_name='registered.txt', checkin_type='strict')
                    Path(path).write_bytes(b'registered')
                    return Command.execute_cmd(FileAppendCheckin(row['code'], [path], ['main'], mode='preallocate', keep_file_name=True))
                cmd.execute = register
                registered = Command.execute_cmd(cmd)
                file = registered.get_file_by_type('main')
                before = file.update_data.copy()
                registered.get_preallocated_path(mkdir=False)
                self.assertEqual(file.update_data, before)
                with self.assertRaises(CheckinException):
                    Command.execute_cmd(FileAppendCheckin(row['code'], [file.get_lib_path()], ['main'], mode='preallocate', keep_file_name=True))
                self.assertEqual(Path(file.get_lib_path()).read_bytes(), b'registered')
            for name in ('..', '../', 'C:\\client\\'):
                with self.assertRaises(CheckinException):
                    api.dispatch('upload_file', (ticket, name, Binary(b'invalid')))
            with self.assertRaises(ValueError):
                api.dispatch('upload_file', (ticket, 'text.bin', 'not binary'))

    def test_preallocated_frames_and_reader_path_access(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'admin'}
            row = api.dispatch('create_snapshot', (ticket, 'sthpw/project?code=admin', 'preallocated_frames'))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', self.ticket)
                snapshot = Snapshot.get_by_code(row['code'])
                cmd = Command()
                def register_frames():
                    cmd.get_transaction().set_sync(False)
                    template = FileCheckin.get_preallocated_path(snapshot, file_name='frame.####.txt', file_range='1-3', checkin_type='strict')
                    from pyasm.biz import FileGroup
                    for path in FileGroup.expand_paths(template, FileRange(1, 3)):
                        Path(path).write_bytes(b'frame')
                    return Command.execute_cmd(FileGroupAppendCheckin(row['code'], [template], ['main'], FileRange(1, 3), mode='preallocate', keep_file_name=True))
                cmd.execute = register_frames
                registered = Command.execute_cmd(cmd)
                self.assertEqual([Path(path).read_bytes() for path in registered.get_all_lib_paths(expand_paths=True)], [b'frame'] * 3)
            api.dispatch('insert', (ticket, 'sthpw/login', {'login': 'path_reader', 'password': hash_password('private-reader-password')}))
            reader_ticket = {'ticket': api.get_ticket('path_reader', 'private-reader-password'), 'project': 'admin'}
            before = store.database_path('sthpw').read_bytes()
            path = api.dispatch('get_preallocated_path', (reader_ticket, row['code']), {'mkdirs': False, 'protocol': None})
            self.assertTrue(path.endswith('frame.####_preallocated_frames_v001.txt'))
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)
            with self.assertRaises(SecurityException):
                api.dispatch('get_preallocated_path', (reader_ticket, row['code']))
            with self.assertRaises(SecurityException):
                api.dispatch('upload_file', (reader_ticket, 'denied.bin', Binary(b'denied')))
