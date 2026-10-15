import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import test_read_parity as read_tests
from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract
from pyasm.command import Command
from pyasm.search import FileUndo, SearchType, Transaction, TransactionException, TransactionLog
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class FileUndoParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='file_contract', project='admin', name='repository_files'),
                     dict(method='repository_contract', project='admin', name='repository_naming')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case['method'] == 'file_contract':
            self.assertEqual(original.pop('file_log'), 'NameError')
            self.assertEqual(result.pop('file_log'), 7)
        else:
            self.assertEqual(original.pop('journal'), ['create', 'move', 'create'])
            self.assertEqual(result.pop('journal'), ['mkdir', 'create', 'move', 'create'])
        self.assertEqual(result, original)

    def test_repository_rollback(self):
        self.assertEqual(self.new_result(dict(method='repository_contract', fail=True)),
                         [False, [True, True, False], 0, True])

    def test_naming_fixes_and_repository_validation(self):
        from types import SimpleNamespace
        from pyasm.biz import DirNaming, FileNaming, Project, Snapshot
        from pyasm.checkin import CheckinException, TacticRepo
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Project.get()
            snapshot = Snapshot.create(parent, 'file', 'naming_fixes', commit=False)
            snapshot.set_value('snapshot', '<snapshot><file type="main" use_naming="false"/></snapshot>')
            naming = DirNaming(parent, snapshot, file_type='main')
            with patch('pyasm.biz.naming.Naming.get', return_value=None):
                self.assertTrue(naming.get_lib_dir().endswith('/one/project/one/naming_fixes'))
            # Missing file rows must not be dereferenced; custom constructors receive real objects.
            row = SimpleNamespace(get_value=lambda key, **kw: {'class_name': 'custom.Naming'}.get(key, ''))
            with patch('pyasm.biz.naming.Naming.get', return_value=row), \
                    patch('pyasm.common.Common.create_from_class_path', return_value=SimpleNamespace(get_file=lambda: 'custom.txt')) as create:
                self.assertEqual(FileNaming(parent, snapshot).get_from_db_naming('sthpw/project'), 'custom.txt')
                self.assertIs(create.call_args.args[2]['sobject'], parent)
            # An empty custom result falls back to the original Naming row.
            with patch('pyasm.biz.naming.Naming.get', return_value=row), \
                    patch('pyasm.common.Common.create_from_class_path', return_value=SimpleNamespace(get_dir=lambda: None)):
                self.assertIsNone(naming.get_from_db_naming('file'))
            selected = Project.get_by_code('admin')
            selected.set_value('dir_naming_cls', 'custom.Naming', temp=True)
            with patch('pyasm.common.Common.create_from_class_path', return_value=naming) as create:
                self.assertIs(Project.get_dir_naming(parent, selected), naming)
                create.assert_called_once_with('custom.Naming')
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                file = SearchType.create('sthpw/file')
                file.set_value('file_name', '../escape.txt')
                repo = TacticRepo()
                with self.assertRaises(CheckinException):
                    repo.handle_system_commands(snapshot, ['unused'], [file], 'copy', None, source_paths=['unused'])
                with self.assertRaises(ValueError):
                    repo.handle_system_commands(snapshot, ['unused'], [file], 'move', None)
                self.assertEqual(Transaction.get().get_xml().get_nodes('transaction/file'), [])
            cmd.execute = execute
            Command.execute_cmd(cmd)

    def test_file_paths_follow_each_file_code_and_recorded_directory(self):
        from pyasm.biz import File, FileNaming, Project, Snapshot
        from pyasm.checkin import SnapshotBuilder
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                project = Project.get()
                snapshot = Snapshot.create(project, 'file', 'path_order', commit=False)
                files = []
                for name in ('first', 'second'):
                    file = File.create(name + '.txt', project.get_search_type(), project.get_id(), requires_file=False)
                    file.set_value('relative_dir', 'recorded/' + name)
                    file.set_value('type', name)
                    file.commit(triggers='none')
                    files.append(file)
                builder = SnapshotBuilder()
                # XML order deliberately differs from database order.
                for file in reversed(files):
                    builder.add_file(file, {'type': file.get_type()})
                snapshot.set_value('snapshot', builder.to_string())
                self.assertEqual(FileNaming(project, snapshot, files[0], ext='exr').add_default_ending(['frame']),
                                 'frame_path_order_v001.####.exr')
                paths = snapshot.get_all_paths_dict('relative')
                for file in files:
                    name = file.get_type()
                    self.assertEqual(paths[name], ['recorded/' + name + '/' + name + '.txt'])
                    self.assertTrue(file.get_lib_dir(snapshot).endswith('/recorded/' + name))
                    self.assertEqual(file.get_web_dir(snapshot), '/assets/recorded/' + name)
                    self.assertTrue(snapshot.get_web_path_by_type(name).endswith('/recorded/' + name + '/' + name + '.txt'))
                self.assertEqual(snapshot.get_all_web_paths(), ['/assets/recorded/second/second.txt', '/assets/recorded/first/first.txt'])
            cmd.execute = execute
            Command.execute_cmd(cmd)

    def test_rollback_restores_overwrites_and_same_basename_backups(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            root = Path(Environment.get_asset_dir()) / 'rollback_files'
            root.mkdir(parents=True)
            for name in ('one', 'two'):
                (root / name).mkdir()
                (root / name / 'same.txt').write_text(name)
            (root / 'source.txt').write_text('new')
            (root / 'destination.txt').write_text('old')
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                FileUndo.remove(str(root / 'one/same.txt'))
                FileUndo.remove(str(root / 'two/same.txt'))
                FileUndo.copy(str(root / 'source.txt'), str(root / 'destination.txt'))
                FileUndo.move(str(root / 'source.txt'), str(root / 'moved.txt'))
                FileUndo.mkdir(str(root / 'new/deep'))
                note = SearchType.create('sthpw/note')
                note.set_value('code', 'FILE_ROLLBACK')
                note.set_value('note', 'must roll back')
                note.commit()
                raise ValueError('file rollback')
            cmd.execute = execute
            with self.assertRaisesRegex(ValueError, 'file rollback'):
                Command.execute_cmd(cmd)
            self.assertEqual((root / 'one/same.txt').read_text(), 'one')
            self.assertEqual((root / 'two/same.txt').read_text(), 'two')
            self.assertEqual((root / 'destination.txt').read_text(), 'old')
            self.assertEqual((root / 'source.txt').read_text(), 'new')
            self.assertFalse((root / 'new').exists())
            self.assertFalse((root / 'moved.txt').exists())
            from pyasm.search import Search
            self.assertIsNone(Search.get_by_code('sthpw/note', 'FILE_ROLLBACK'))

    def test_partial_copy_and_failed_journal_cannot_commit(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            root = Path(Environment.get_asset_dir()) / 'partial_files'
            root.mkdir(parents=True)
            source, destination = root / 'source', root / 'destination'
            source.write_bytes(b'new')
            destination.write_bytes(b'old')
            def partial(src, dst):
                Path(dst).write_bytes(b'partial')
                raise OSError('disk failure')
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                with patch('pyasm.search.transaction.shutil.copyfile', side_effect=partial):
                    try:
                        FileUndo.copy(str(source), str(destination))
                    except OSError:
                        pass
            cmd.execute = execute
            with self.assertRaises(TransactionException):
                Command.execute_cmd(cmd)
            self.assertEqual(destination.read_bytes(), b'old')
            cmd = Command()
            cmd.execute = lambda: FileUndo.copy(str(source), str(root / 'created'))
            with patch.object(TransactionLog, 'create', side_effect=ValueError('journal failure')):
                with self.assertRaisesRegex(ValueError, 'journal failure'):
                    Command.execute_cmd(cmd)
            self.assertFalse((root / 'created').exists())

    def test_file_log_copy_redo_and_guarded_dependencies(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            root = Path(Environment.get_asset_dir()) / 'redo_files'
            root.mkdir(parents=True)
            source = root / 'source.txt'
            source.write_text('retained')
            with self.assertRaises(UnsupportedContract):
                FileUndo.copy(str(source), str(root / 'unguarded'))
            transaction = Transaction.get(create=True)
            transaction.set_sync(False)
            with self.assertRaises(ValueError):
                FileUndo.copy(str(root), str(root / 'inside'))
            self.assertFalse((root / 'inside').exists())
            FileUndo.create(str(source), str(root / 'created.txt'), io_action='copy')
            file_log = transaction.get_file_log()
            self.assertEqual(len(transaction.get_xml().get_nodes('transaction/file')), 1)
            node = file_log.get_nodes('transaction/file')[0]
            FileUndo.undo(node)
            FileUndo.undo(node)
            self.assertFalse((root / 'created.txt').exists())
            FileUndo.redo(node)
            self.assertEqual((root / 'created.txt').read_text(), 'retained')
            transaction.rollback()
            transaction = Transaction.get(create=True)
            FileUndo.create(str(source), str(root / 'cached.txt'), io_action='copy')
            with patch('pyasm.search.transaction.shutil.move', side_effect=OSError('cache unavailable')):
                with self.assertRaises(TransactionException):
                    transaction.rollback()
            self.assertEqual((root / 'cached.txt').read_text(), 'retained')
            transaction.rollback()
            self.assertFalse((root / 'cached.txt').exists())
            with self.assertRaises(UnsupportedContract):
                FileUndo.symlink(str(source), str(root / 'alias'))
            from pyasm.biz import File
            import hashlib
            self.assertEqual(File.get_md5(str(source)), hashlib.md5(b'retained').hexdigest())
        from pyasm.common.errors import SecurityException
        with request_context(RequestContext(self.store, 'anonymous', 'admin')):
            with self.assertRaises(SecurityException):
                FileUndo.remove(str(source))
        self.assertTrue(source.exists())

    def test_versionless_links_update_undo_redo_and_failure_preserve_versions(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            root = self.store.data_dir / 'assets/link_contract'
            root.mkdir(parents=True)
            first, second, alias = (root / name for name in ('v001.txt', 'v002.txt', 'latest.txt'))
            first.write_bytes(b'first'); second.write_bytes(b'second')
            for mode in ('hardlink', 'symlink'):
                alias.write_bytes(b'previous')
                transaction = Transaction.get(create=True); transaction.set_sync(False)
                try:
                    FileUndo.symlink(str(first), str(alias), mode=mode)
                except OSError as error:
                    transaction.rollback()
                    self.assertEqual(alias.read_bytes(), b'previous')
                    if mode == 'symlink' and getattr(error, 'winerror', None) == 1314:
                        alias.unlink()
                        continue  # Linux verifies symlinks; this Windows account lacks the privilege.
                    raise
                self.assertTrue(os.path.samefile(first, alias))
                FileUndo.symlink(str(second), str(alias), mode=mode)
                self.assertTrue(os.path.samefile(second, alias))
                self.assertEqual(first.read_bytes(), b'first')
                nodes = transaction.get_xml().get_nodes('transaction/file')
                for node in reversed(nodes):
                    FileUndo.undo(node)
                self.assertEqual(alias.read_bytes(), b'previous')
                for node in nodes:
                    FileUndo.redo(node)
                self.assertTrue(os.path.samefile(second, alias))
                transaction.rollback()
                self.assertEqual(alias.read_bytes(), b'previous')
                self.assertEqual(second.read_bytes(), b'second')
                alias.unlink()

    def test_versionless_copy_undo_redo_and_partial_failure_restore_previous_alias(self):
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            root = Path(Environment.get_asset_dir()) / 'versionless_undo'
            root.mkdir(parents=True)
            source, alias = root / 'version2.txt', root / 'current.txt'
            source.write_bytes(b'new version')
            alias.write_bytes(b'previous version')
            link = root / '.current.txt.link'
            link.write_text('previous-source.txt', encoding='utf-8')
            transaction = Transaction.get(create=True)
            transaction.set_sync(False)
            FileUndo.symlink(str(source), str(alias), mode='copy')
            nodes = transaction.get_file_log().get_nodes('transaction/file')
            self.assertEqual(alias.read_bytes(), b'new version')
            from copy import deepcopy
            historical = deepcopy(nodes[-1])
            historical.attrib.pop('state')
            with self.assertRaises(UnsupportedContract):
                FileUndo.undo(historical)
            with self.assertRaises(UnsupportedContract):
                FileUndo.redo(historical)
            self.assertEqual(alias.read_bytes(), b'new version')
            for node in reversed(nodes):
                FileUndo.undo(node)
                FileUndo.undo(node)
            self.assertEqual(alias.read_bytes(), b'previous version')
            self.assertEqual(link.read_text(encoding='utf-8'), 'previous-source.txt')
            for node in nodes:
                FileUndo.redo(node)
            self.assertEqual(alias.read_bytes(), b'new version')
            self.assertEqual(Path(link.read_text(encoding='utf-8')), source)
            transaction.rollback()
            self.assertEqual(alias.read_bytes(), b'previous version')
            def partial(src, dst):
                Path(dst).write_bytes(b'partial')
                raise OSError('alias disk failure')
            cmd = Command()
            cmd.execute = lambda: FileUndo.symlink(str(source), str(alias), mode='copy')
            with patch('pyasm.search.transaction.shutil.copyfile', side_effect=partial):
                with self.assertRaisesRegex(OSError, 'alias disk failure'):
                    Command.execute_cmd(cmd)
            self.assertEqual(alias.read_bytes(), b'previous version')
            self.assertEqual(link.read_text(encoding='utf-8'), 'previous-source.txt')
            self.assertEqual(source.read_bytes(), b'new version')
