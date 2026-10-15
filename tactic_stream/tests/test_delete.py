from pathlib import Path
import shutil
import tempfile

import test_read_parity as read_tests
import test_checkin as checkin_tests
from pyasm.biz import File, Project, Snapshot
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic.ui.tools import DeleteCmd


class DeleteParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='delete_contract', project='admin', name='repository_delete'),
                     dict(method='delete_contract', project='admin', name='repository_delete_rollback', fail=True)]

    new_result = checkin_tests.CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        if case.get('fail'):
            self.assertEqual(original[1], ['main1', None, None, None, None, None])
            self.assertEqual(result[1], ['main1', 'secondary1', 'main2', 'secondary2', 'main3', 'secondary3'])
            original[1] = result[1]
        else:
            self.assertEqual(original[5], [False, True, False, False, False, False])
            self.assertEqual(result[5], [False] * 6)
            original[5] = result[5]
        self.assertEqual(result, original)

    def test_alias_deletion_rollback_cleanup_and_shared_file_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                parent = Project.get()
                context = 'delete_aliases'
                rules = []
                for mode in ('latest', 'current'):
                    row = SearchType.create('config/naming')
                    for key, value in {'search_type': 'sthpw/project', 'snapshot_type': 'file',
                                       'context': context, 'checkin_type': 'strict', mode + '_versionless': True,
                                       'file_naming': '{basefile}_' + mode + '.{ext}',
                                       'dir_naming': '{project.code}/' + context}.items():
                        row.set_value(key, value, temp=True)
                    rules.append(row)
                Container.put('Naming:namings', rules)
                snapshots = []
                source = Path(directory) / 'source.txt'
                for version in (1, 2):
                    source.write_bytes(str(version).encode())
                    snapshots.append(Command.execute_cmd(FileCheckin(parent, str(source), context=context,
                                      checkin_type='strict', mode='copy', is_current=version == 2)))
                aliases = [Snapshot.get_versionless(parent.get_search_type(), parent.get_code(), context,
                                                    mode=mode, create=False) for mode in ('latest', 'current')]
                codes = [alias.get_code() for alias in aliases]
                paths = [Path(alias.get_lib_path_by_type()) for alias in aliases]
                old_xml = [alias.get_value('snapshot') for alias in aliases]
                cmd = Command()
                def execute():
                    cmd.get_transaction().set_sync(False)
                    DeleteCmd(sobject=snapshots[1], auto_discover=True).execute()
                    self.assertEqual(paths[0].read_bytes(), b'1')
                    self.assertFalse(paths[1].exists())
                    raise ValueError('after versionless deletion')
                cmd.execute = execute
                with self.assertRaisesRegex(ValueError, 'after versionless deletion'):
                    Command.execute_cmd(cmd)
                self.assertEqual([path.read_bytes() for path in paths], [b'2', b'2'])
                self.assertEqual([Snapshot.get_by_code(code).get_value('snapshot') for code in codes], old_xml)
                self.assertEqual(Path(snapshots[1].get_lib_path_by_type()).read_bytes(), b'2')
                Command.execute_cmd(DeleteCmd(sobject=snapshots[1], auto_discover=True))
                self.assertEqual(paths[0].read_bytes(), b'1')
                self.assertFalse(paths[1].exists())
                self.assertFalse((paths[1].parent / ('.' + paths[1].name + '.link')).exists())
                self.assertIsNone(Snapshot.get_by_code(codes[1]))
                # Shared XML references never authorize deletion of another Snapshot's File.
                cmd = Command()
                def share():
                    cmd.get_transaction().set_sync(False)
                    shared = Snapshot.create(parent, 'file', 'shared_delete', commit=False)
                    shared.set_value('snapshot', snapshots[0].get_value('snapshot'))
                    shared.commit()
                    shared.remove_file("unknown'quoted")
                    with self.assertRaises(UnsupportedContract):
                        shared.remove_file('main')
                    DeleteCmd(sobject=shared).execute()
                cmd.execute = share
                Command.execute_cmd(cmd)
                self.assertEqual(Path(snapshots[0].get_lib_path_by_type()).read_bytes(), b'1')
                cmd = Command()
                cmd.execute = lambda: snapshots[0].remove_file('main')
                Command.execute_cmd(cmd)
                self.assertFalse(paths[0].exists())
                self.assertEqual(Snapshot.get_by_code(codes[0]).get_all_file_objects(), [])
                Command.execute_cmd(DeleteCmd(sobject=snapshots[0]))
                self.assertIsNone(Snapshot.get_by_code(codes[0]))
            with request_context(RequestContext(store, 'anonymous', 'admin')):
                with self.assertRaises(SecurityException):
                    Command.execute_cmd(DeleteCmd(search_key=snapshots[0].get_search_key()))

    def test_public_dependency_delete_and_directory_files(self):
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.ticket)
                parent = Project.get()
                source = Path(directory) / 'folder'
                source.mkdir()
                (source / 'payload.txt').write_bytes(b'directory data')
                # Imported directory snapshots are deletable before directory check-in is ported.
                from pyasm.checkin import SnapshotBuilder
                from pyasm.search import FileUndo
                cmd = Command()
                def register_directory():
                    cmd.get_transaction().set_sync(False)
                    snapshot = Snapshot.create(parent, 'file', 'directory_delete')
                    file = SearchType.create('sthpw/file')
                    file.set_value('search_type', parent.get_search_type())
                    file.set_value('search_code', parent.get_code())
                    file.set_value('search_id', parent.get_id())
                    for key, value in {'file_name': 'folder', 'base_type': 'directory', 'type': 'main',
                                       'project_code': 'admin', 'snapshot_code': snapshot.get_code(),
                                       'relative_dir': 'admin/directory_delete'}.items():
                        file.set_value(key, value)
                    file.commit(triggers='none')
                    builder = SnapshotBuilder()
                    builder.add_file(file, {'type': 'main'})
                    snapshot.set_value('snapshot', builder.to_string())
                    snapshot.commit(triggers='none')
                    destination = Path(snapshot.get_lib_path_by_type())
                    FileUndo.mkdir(str(destination.parent))
                    FileUndo.copy(str(source), str(destination))
                    return snapshot
                cmd.execute = register_directory
                snapshot = Command.execute_cmd(cmd)
                physical = Path(snapshot.get_lib_path_by_type())
                self.assertEqual((physical / 'payload.txt').read_bytes(), b'directory data')
                file_code = snapshot.get_all_file_codes()[0]
                key = snapshot.get_search_key()
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'admin'}
            file_key = 'sthpw/file?code=' + file_code
            api.dispatch('update', (ticket, file_key, {'base_type': 'sequence'}))
            from pyasm.biz import FileException
            with self.assertRaises(FileException):
                api.dispatch('delete_sobject', (ticket, key), {'include_dependencies': True})
            self.assertEqual((physical / 'payload.txt').read_bytes(), b'directory data')
            api.dispatch('update', (ticket, file_key, {'base_type': 'directory'}))
            api.dispatch('update', (ticket, key, {'level_type': 'sthpw/project', 'level_id': parent.get_id()}))
            result = api.dispatch('delete_sobject', ({'ticket': self.ticket, 'project': 'admin'}, key),
                                  {'include_dependencies': True})
            self.assertEqual(result['code'], snapshot.get_code())
            self.assertFalse(physical.exists())
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.assertIsNone(File.get_by_code(file_code))
                self.assertIsNone(Snapshot.get_by_code(snapshot.get_code()))
