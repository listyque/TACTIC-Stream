"""Unchanged file/repository script in both kernels, on private data only."""
import hashlib
from pathlib import Path
from pyasm.common import Environment
from pyasm.biz import File, Project, Snapshot
from pyasm.command import Command
from pyasm.search import FileUndo, Search, SearchType, Transaction
from pyasm.security import Security
from pyasm.checkin.repo import TacticRepo
from pyasm.checkin import SnapshotBuilder


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        root = Path(Environment.get_asset_dir()) / 'file_contract'
        inputs = Path(Environment.get_tmp_dir()) / 'file_inputs'
        inputs.mkdir(parents=True, exist_ok=True)
        for name in ('copy', 'move', 'create'):
            (inputs / (name + '.txt')).write_bytes(('Данные ' + name).encode('utf-8'))
        FileUndo.mkdir(str(root))
        FileUndo.copy(str(inputs / 'copy.txt'), str(root / 'copy.txt'))
        FileUndo.move(str(inputs / 'move.txt'), str(root / 'move.txt'))
        FileUndo.create(str(inputs / 'create.txt'), str(root / 'create.txt'), io_action='copy')
        (root / 'remove.txt').write_bytes(b'removed')
        FileUndo.remove(str(root / 'remove.txt'))
        (root / 'empty').mkdir()
        FileUndo.rmdir(str(root / 'empty'))
        project = Project.get()
        file = File.create(str(root / 'copy.txt'), project.get_search_type(), project.get_id(), search_code=project.get_code())
        digest = hashlib.md5((root / 'copy.txt').read_bytes()).hexdigest()
        repo = TacticRepo()
        assert repo.handle_system_commands(None, None, None, 'local', None) is None
        repo.handle_system_commands(None, [str(root / 'copy.txt')], [file], 'inplace', [digest], commit=True)
        reserved = root / 'reserved.txt'
        reserved.write_bytes(b'preallocated')
        second = File.create(str(reserved), project.get_search_type(), project.get_id(), search_code=project.get_code())
        snapshot = Snapshot.create(project, 'file', 'file_contract', commit=False)
        builder = SnapshotBuilder()
        builder.add_file(second, {'type': 'main'})
        snapshot.set_value('snapshot', builder.to_string())
        repo.handle_system_commands(snapshot, [str(reserved)], [second], 'preallocate', 'ignore', commit=True)
        note = SearchType.create('sthpw/note')
        note.set_value('process', 'file_contract')
        note.set_value('note', 'file metadata committed')
        note.commit()
        xml = Transaction.get().get_xml()
        types = [node.get('type') for node in xml.get_nodes('transaction/file')]
        try:
            file_log = len(Transaction.get().get_file_log().get_nodes('transaction/file'))
        except NameError:
            file_log = 'NameError'
        return {'types': types, 'file_log': file_log,
                'files': {path.name: path.read_bytes().decode('utf-8') for path in root.iterdir() if path.is_file()},
                'metadata': [file.get_value('md5'), second.get_value('type')]}


def rollback_case():
    root = Path(Environment.get_asset_dir()) / 'file_rollback_contract'
    root.mkdir(parents=True, exist_ok=True)
    (root / 'source').write_bytes(b'new')
    (root / 'destination').write_bytes(b'old')
    cmd = Command()
    def execute():
        cmd.get_transaction().set_sync(False)
        FileUndo.copy(str(root / 'source'), str(root / 'destination'))
        FileUndo.move(str(root / 'source'), str(root / 'moved'))
        FileUndo.mkdir(str(root / 'new/deep'))
        note = SearchType.create('sthpw/note')
        note.set_value('process', 'file_rollback_contract')
        note.set_value('note', 'must roll back')
        note.commit()
        raise ValueError('file rollback')
    cmd.execute = execute
    try:
        Command.execute_cmd(cmd)
        raise AssertionError('Missing rollback')
    except ValueError:
        pass
    search = Search('sthpw/note')
    search.add_filter('process', 'file_rollback_contract')
    result = [(root / 'source').read_text(), (root / 'destination').read_text(),
              (root / 'new').exists(), (root / 'moved').exists(), search.get_count()]
    assert result == ['new', 'old', False, False, 0], result
    return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        if case.get('rollback'):
            return rollback_case()
        result = Command.execute_cmd(Run())
        search = Search('sthpw/note')
        search.add_filter('process', 'file_contract')
        result['notes'] = [obj.get_value('note') for obj in search.get_sobjects()]
        return result
    finally:
        Environment.set_security(previous)
