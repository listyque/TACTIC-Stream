import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case
from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileCheckin, CheckinException, SingleSnapshotException, FileAppendCheckin, FileGroupCheckin
from pyasm.command import Command
from pyasm.common.errors import UnsupportedContract, SecurityException
from pyasm.search import Search
from unittest.mock import patch


class CheckinParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='checkin_contract', project='admin', name='strict_file_checkin')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', case.get('project', 'admin'))):
                return run_snapshot_case(case)

    def test_late_checkin_failure_rolls_back_files_rows_and_flags(self):
        self.new_result(dict(method='checkin_contract', fail=True))

    def test_checkin_guards_and_single_snapshot_preserve_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            source = Path(directory) / 'input.txt'
            source.write_bytes(b'original input')
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                parent = Project.get()
                before = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                for options in ({'ingest_mode': 'ingestX'},
                                {'mode': 's3'}):
                    arguments = dict(context='guard', mode='create', checkin_type='strict')
                    arguments.update(options)
                    with self.assertRaises(UnsupportedContract):
                        Command.execute_cmd(FileCheckin(parent, [str(source)], **arguments))
                    self.assertEqual(source.read_bytes(), b'original input')
                    self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                with self.assertRaises(CheckinException):
                    FileAppendCheckin('missing', [str(source)], ['main'])
                with self.assertRaises(CheckinException):
                    FileGroupCheckin(parent, [str(source)], ['main'], '1-2')
                with patch('pyasm.biz.FileNaming.get_file_name', return_value='../escape.txt'), self.assertRaises(CheckinException):
                    Command.execute_cmd(FileCheckin(parent, [str(source)], context='guard', checkin_type='strict'))
                self.assertFalse((Path(directory).parent / 'escape.txt').exists())
                self.assertEqual(source.read_bytes(), b'original input')
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before)
                paths = []
                for name in ('first', 'second'):
                    folder = Path(directory) / name
                    folder.mkdir()
                    path = folder / 'shared.txt'
                    path.write_text(name)
                    paths.append(str(path))
                snapshot = Command.execute_cmd(FileCheckin(parent, paths, ['first', 'second'],
                                  context='duplicate', mode='copy', checkin_type='strict',
                                  file_naming='{basefile}_{file_type}.{ext}',
                                  dir_naming='{project.code}/duplicate/{file_type}'))
                for kind in ('first', 'second'):
                    file = snapshot.get_file_by_type(kind)
                    self.assertEqual(file.get_value('relative_dir'), 'admin/duplicate/' + kind)
                    self.assertEqual(Path(snapshot.get_lib_path_by_type(kind)).read_text(), kind)
                first = Command.execute_cmd(FileCheckin(parent, [str(source)], context='single', mode='copy', checkin_type='strict'))
                upload_src = Path(directory) / 'append_upload.txt'
                upload_src.write_bytes(b'append upload payload')
                manual_src = Path(directory) / 'append_manual.txt'
                manual_src.write_bytes(b'append manual payload')
                append_cmd = Command()
                def _append_modes():
                    first.add_file(str(upload_src), file_type='upload_extra', mode='upload')
                    first.add_file(str(manual_src), file_type='manual_extra', mode='manual')
                append_cmd.execute = _append_modes
                Command.execute_cmd(append_cmd)
                refreshed = Snapshot.get_by_code(first.get_code())
                self.assertEqual(Path(refreshed.get_lib_path_by_type('upload_extra')).read_bytes(), b'append upload payload')
                self.assertEqual(Path(refreshed.get_lib_path_by_type('manual_extra')).read_bytes(), b'append manual payload')
                with self.assertRaises(SingleSnapshotException):
                    Command.execute_cmd(FileCheckin(parent, [str(source)], context='single', mode='copy',
                                                   checkin_type='strict', single_snapshot=True))
                search = Search('sthpw/snapshot')
                search.add_filter('context', 'single')
                snapshots = search.get_sobjects()
                self.assertEqual(len(snapshots), 1)
                self.assertEqual(snapshots[0].get_code(), first.get_code())
                self.assertTrue(snapshots[0].is_latest())
                self.assertEqual(Path(first.get_lib_path_by_type()).read_bytes(), b'original input')
            with request_context(RequestContext(store, 'anonymous', 'admin')):
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(FileCheckin(Project.get(), [str(source)], context='denied', mode='copy', checkin_type='strict'))
                self.assertEqual(source.read_bytes(), b'original input')

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('fixes'), {
            'inputs': [False, False, False, False, True, False],
            'string_md5': 'AssertionError', 'sizes': 'ok',
            'inplace_prefix': '_old',
            'auto_naming': ['{basefile}_{snapshot.process}_v{version}.{ext}',
                            {'default': '{project.code}/{search_type.table_name}/{code}/{snapshot.process}/versions'}]})
        self.assertEqual(result.pop('fixes'), {
            'inputs': [True] * 6, 'string_md5': 'ok', 'sizes': 'CheckinException',
            'inplace_prefix': '',
            'auto_naming': ['chosen.txt', 'chosen/dir']})
        self.assertTrue(original['rows'][5][4])
        self.assertFalse(result['rows'][5][4])
        original['rows'][5][4] = False
        # Each trigger sees the corrected local flag but only exposes version/filenames here.
        self.assertEqual(result, original)


class VersionlessParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='versionless_contract', project='admin', name='versionless_links')]

    new_result = CheckinParity.new_result

    def test_late_checkin_failure_rolls_back_files_rows_and_flags(self):
        self.assertEqual(self.new_result(dict(method='versionless_contract', fail=True)), [0, [False, False]])

    def test_replacement_failure_preserves_alias_metadata_and_versioned_files(self):
        from pyasm.common import Environment
        from pyasm.biz import File
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                parent = Project.get()
                source = Path(directory) / 'old.txt'
                source.write_bytes(b'original')
                first = Command.execute_cmd(FileCheckin(parent, str(source), context='alias_refresh', mode='copy'))
                alias = Snapshot.get_versionless(parent.get_search_type(), parent.get_code(), 'alias_refresh',
                                                 mode='latest', create=False)
                old_file = alias.get_file_by_type('main')
                old_path = Path(old_file.get_lib_path())
                before_xml = alias.get_value('snapshot')
                self.assertEqual(old_file.get_value('project_code'), 'admin')
                self.assertEqual(old_file.get_value('source_path'), str(source))
                source2 = Path(directory) / 'new.txt'
                source2.write_bytes(b'replacement')
                cmd = Command()
                def execute():
                    cmd.get_transaction().set_sync(False)
                    Command.execute_cmd(FileCheckin(parent, str(source2), context='alias_refresh', mode='copy'))
                    raise ValueError('after alias replacement')
                cmd.execute = execute
                with self.assertRaisesRegex(ValueError, 'after alias replacement'):
                    Command.execute_cmd(cmd)
                alias = Snapshot.get_by_code(alias.get_code())
                self.assertEqual(alias.get_value('snapshot'), before_xml)
                self.assertEqual(old_path.read_bytes(), b'original')
                self.assertIsNotNone(File.get_by_code(old_file.get_code()))
                self.assertFalse((old_path.parent / 'new_alias_refresh.txt').exists())
                second = Command.execute_cmd(FileCheckin(parent, str(source2), context='alias_refresh', mode='copy'))
                self.assertFalse(old_path.exists())
                self.assertFalse((old_path.parent / ('.' + old_path.name + '.link')).exists())
                self.assertIsNone(File.get_by_code(old_file.get_code()))
                alias = Snapshot.get_by_code(alias.get_code())
                self.assertEqual(Path(alias.get_lib_path_by_type()).read_bytes(), b'replacement')
                # A missing versioned source must retain the previous working alias and rows.
                versioned = Path(first.get_lib_path_by_type())
                versioned.unlink()
                cmd = Command()
                def execute_missing():
                    first.set_value('is_latest', True)
                    first.update_versionless('latest', checkin_type='auto')
                cmd.execute = execute_missing
                with self.assertRaises(FileNotFoundError):
                    Command.execute_cmd(cmd)
                self.assertEqual(Path(alias.get_lib_path_by_type()).read_bytes(), b'replacement')
                versioned.write_bytes(b'original')
                cmd = Command()
                cmd.execute = lambda: first.set_latest()
                Command.execute_cmd(cmd)
                alias = Snapshot.get_by_code(alias.get_code())
                self.assertEqual(Path(alias.get_lib_path_by_type()).read_bytes(), b'original')
                self.assertEqual(Path(second.get_lib_path_by_type()).read_bytes(), b'replacement')
