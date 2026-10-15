"""Run unchanged against both kernels, using only the caller's private data."""
import hashlib
from pathlib import Path

from pyasm.biz import File, FileNaming, Project, Snapshot
from pyasm.checkin import SnapshotBuilder
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, Transaction
from pyasm.security import Security


class Run(Command):
    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.context = 'repository_rollback' if fail else 'repository_contract'

    def execute(self):
        self.get_transaction().set_sync(False)
        project = Project.get()
        snapshot = Snapshot.create(project, 'file', self.context)
        self.directory = Path(project.get_lib_dir(snapshot, create=True))
        inputs = Path(Environment.get_tmp_dir()) / self.context
        inputs.mkdir(parents=True, exist_ok=True)
        files = []
        builder = SnapshotBuilder()
        for mode in ('copy', 'move', 'create'):
            path = inputs / (mode + '.txt')
            path.write_bytes(('Данные ' + mode).encode('utf-8'))
            file = File.create(str(path), project.get_search_type(), project.get_id(), search_code=project.get_code())
            file.set_value('snapshot_code', snapshot.get_code())
            file.set_value('type', mode)
            naming = FileNaming(project, snapshot, file)
            file.set_value('file_name', naming.get_file_name())
            file.set_value('relative_dir', project.get_relative_dir(snapshot, file_type=mode, create=True, file_object=file))
            builder.add_file(file, {'type': mode})
            files.append((mode, path, file))
        snapshot.set_value('snapshot', builder.to_string())
        repo = snapshot.get_repo()
        for mode, path, file in files:
            repo.handle_system_commands(snapshot, [str(path)], [file], mode, None, source_paths=[str(path)], commit=True)
        snapshot.commit(triggers='none')
        root = Environment.get_asset_dir().replace('\\', '/')
        def relative(path):
            return str(path).replace('\\', '/').replace(root, 'ASSETS')
        result = {'files': [], 'paths': {}, 'journal': []}
        for mode, source, file in files:
            path = snapshot.get_lib_path_by_type(mode)
            digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
            assert file.get_value('md5') == digest
            result['files'].append([mode, file.get_file_name(), file.get_value('relative_dir'),
                                    Path(path).read_bytes().decode('utf-8'), source.exists()])
            result['paths'][mode] = [relative(snapshot.get_path_by_type(mode)),
                                     relative(snapshot.get_paths_by_type(mode)[0]),
                                     relative(file.get_lib_path()), file.get_env_path(),
                                     file.get_web_path(), snapshot.get_dir('relative', file_type=mode)]
        result['all'] = [relative(path) for path in snapshot.get_all_lib_paths()]
        result['journal'] = [node.get('type') for node in Transaction.get().get_xml().get_nodes('transaction/file')]
        if self.fail:
            raise ValueError('repository rollback')
        return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        if not case.get('fail'):
            return Command.execute_cmd(Run())
        command = Run(fail=True)
        try:
            Command.execute_cmd(command)
            raise AssertionError('Missing rollback')
        except ValueError as error:
            assert str(error) == 'repository rollback'
        inputs = Path(Environment.get_tmp_dir()) / command.context
        search = Search('sthpw/snapshot')
        search.add_filter('context', command.context)
        result = [command.directory.exists(), [(inputs / (mode + '.txt')).exists() for mode in ('copy', 'move', 'create')], search.get_count()]
        # Original create consumes the staged upload; undo keeps it in the cache for redo.
        # The migrated durable journal keeps undo payloads outside removable cache dirs.
        cache = Path(Environment.get_tmp_dir()) / 'undo'
        result.append(any(path.read_bytes() == 'Данные create'.encode('utf-8') for path in cache.rglob('*.txt')))
        assert result == [False, [True, True, False], 0, True], result
        return result
    finally:
        Environment.set_security(previous)
