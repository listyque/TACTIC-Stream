import test_checkin as checkin_tests
import test_read_parity as read_tests
import shutil
import tempfile
from pathlib import Path
from pyasm.biz import Project, Snapshot, FileRange, FileGroup, FileException
from pyasm.checkin import FileCheckin, FileAppendCheckin, FileGroupCheckin, FileGroupAppendCheckin
from pyasm.command import Command
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class AppendGroupParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='append_group_contract', project='admin', name='append_and_frames')]

    new_result = checkin_tests.CheckinParity.new_result

    def test_frame_aliases_append_remove_delete_and_rollback(self):
        self.assertEqual(self.new_result(dict(method='append_group_contract', lifecycle=True)),
                         ['removed', 6, 12, 3, 2])
        result = self.new_result(dict(method='append_group_contract', lifecycle=True, fail=True))
        self.assertEqual(result[0], 'rolled_back')

    def test_auto_append_and_sequence_validation_before_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                parent = Project.get()
                template = str(Path(directory) / 'image.####.txt')
                frame_range = FileRange(1, 3)
                paths = FileGroup.expand_paths(template, frame_range)
                for path in paths:
                    Path(path).write_bytes(b'frame')
                first = Command.execute_cmd(FileGroupCheckin(parent, [template], ['main'], frame_range,
                            context='auto_frames', mode='copy', checkin_type='auto'))
                extra = str(Path(directory) / 'extra.####.txt')
                for path in FileGroup.expand_paths(extra, frame_range):
                    Path(path).write_bytes(b'extra')
                Command.execute_cmd(FileGroupAppendCheckin(first.get_code(), [extra], ['extra'], frame_range, mode='copy'))
                alias = Snapshot.get_versionless(parent.get_search_type(), parent.get_code(), 'auto_frames', mode='latest', create=False)
                self.assertEqual(len(alias.get_all_lib_paths(expand_paths=True)), 6)
                self.assertEqual([Path(path).read_bytes() for path in alias.get_expanded_lib_paths('extra')], [b'extra'] * 3)
                # A regular append also keeps the existing auto alias up to date.
                source = Path(directory) / 'note.txt'
                source.write_bytes(b'note')
                snapshot = Command.execute_cmd(FileCheckin(parent, str(source), context='auto_append', mode='copy'))
                secondary = Path(directory) / 'secondary.txt'
                secondary.write_bytes(b'note')
                Command.execute_cmd(FileAppendCheckin(snapshot.get_code(), [str(secondary)], ['secondary'], mode='copy'))
                alias = Snapshot.get_versionless(parent.get_search_type(), parent.get_code(), 'auto_append', mode='latest', create=False)
                self.assertEqual(Path(alias.get_lib_path_by_type('secondary')).read_bytes(), b'note')
                before = store.database_path('sthpw').read_bytes()
                for invalid in (FileRange(1, 3, 0), FileRange(3, 1), FileRange(1, 3, -1)):
                    command = FileGroupCheckin(parent, [template], ['main'], invalid,
                        context='invalid_frames', mode='copy', checkin_type='strict')
                    # This byte-level check excludes the separately committed error diagnostic.
                    command.kwargs['log_exception'] = False
                    with self.assertRaises(FileException):
                        Command.execute_cmd(command)
                    self.assertEqual(store.database_path('sthpw').read_bytes(), before)
                Path(paths[1]).unlink()
                command = FileGroupCheckin(parent, [template], ['main'], frame_range,
                    context='invalid_frames', mode='move', checkin_type='strict')
                command.kwargs['log_exception'] = False
                with self.assertRaises(FileException):
                    Command.execute_cmd(command)
                self.assertEqual(Path(paths[0]).read_bytes(), b'frame')
                self.assertEqual(store.database_path('sthpw').read_bytes(), before)
                self.assertEqual(FileGroup.expand_paths('folder%/negative.##.txt', FileRange.get('-2-0')),
                                 ['folder%/negative.-2.txt', 'folder%/negative.-1.txt', 'folder%/negative.00.txt'])
                self.assertEqual(FileGroup.expand_paths('folder%/image.%0.4d.txt', FileRange(1, 1)),
                                 ['folder%/image.0001.txt'])
                self.assertEqual(FileGroup.expand_paths('folder#/image.%04d.txt', FileRange(1, 1)),
                                 ['folder#/image.0001.txt'])
            with request_context(RequestContext(store, 'anonymous', 'admin')):
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(FileGroupAppendCheckin(first.get_code(), [extra], ['extra'], frame_range, mode='copy'))

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('flags'), [[1, True, True], [2, False, False]])
        self.assertEqual(result.pop('flags'), [[1, False, True], [2, True, False]])
        self.assertEqual(original.pop('named'), ['FileNotFoundError'])
        self.assertEqual(result.pop('named'), ['ok', 'named.####_group_named_v001.txt'])
        self.assertEqual(original['groups'][3][1][0][-1], [None] * 3)
        self.assertEqual(result['groups'][3][1][0][-1], ['image.0001.txt', 'image.0003.txt', 'image.0005.txt'])
        original['groups'][3][1][0][-1] = result['groups'][3][1][0][-1]
        self.assertEqual(result, original)
