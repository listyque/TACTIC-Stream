"""Identical strict FileCheckin script in the real original and native kernels."""
from pathlib import Path
from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileCheckin, CheckinException, SingleSnapshotException
from pyasm.command import Command, Trigger
from pyasm.common import Container, Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class Record(Trigger):
    def execute(self):
        output = self.get_input()
        row = output['snapshot']
        Container.append_seq('checkin_contract.events', [self.get_event(), row['version'],
                             [file['file_name'] for file in output['files']]])


class Run(Command):
    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.context = 'checkin_rollback' if fail else 'checkin_contract'

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        inputs = Path(Environment.get_tmp_dir()) / self.context
        inputs.mkdir(parents=True, exist_ok=True)
        for event in ('checkin', 'checkin|sthpw/project', 'checkin|sthpw/project|' + self.context):
            trigger = SearchType.create('sthpw/trigger')
            for field, value in {'event': event, 'class_name': 'checkin_contract.Record',
                                 'mode': 'same process,same transaction'}.items():
                trigger.set_value(field, value, temp=True)
            Trigger.append_static_trigger(trigger)
        rows = []
        unchanged_inputs = []
        for index, mode in enumerate(('copy', 'move', 'create', None, 'inplace', 'local')):
            source = inputs / ('file_' + str(index) + '.txt')
            source.write_bytes(('Данные ' + str(index)).encode('utf-8'))
            supplied_paths = [str(source)]
            command = FileCheckin(parent, supplied_paths, ['main'], context=self.context,
                                  mode=mode, checkin_type='strict', md5s=[None],
                                  is_current=index != 1, do_update_versionless=True)
            snapshot = Command.execute_cmd(command)
            unchanged_inputs.append(supplied_paths == [str(source)])
            file = command.get_file_objects()[0]
            path = snapshot.get_lib_path_by_type('main')
            rows.append([mode, snapshot.get_version(), snapshot.get_value('revision'),
                         file.get_file_name(), bool(snapshot.get_value('is_latest')),
                         bool(snapshot.get_value('is_current')), file.get_value('md5'),
                         Path(path).read_bytes().decode('utf-8') if mode != 'local' else None,
                         source.exists()])
        # Explicit revision, naming, and multiple files use the same check-in pipeline.
        paths = [inputs / 'first.txt', inputs / 'second.txt']
        for path in paths:
            path.write_bytes(path.stem.encode('utf-8'))
        command = FileCheckin(parent, [str(path) for path in paths], ['first', 'second'],
                              context=self.context, mode='copy', checkin_type='strict',
                              is_revision=True, file_naming='{basefile}_v{version}_r{revision}.{ext}',
                              dir_naming='{project.code}/checkin/' + self.context + '/custom', md5s=[None, None])
        snapshot = Command.execute_cmd(command)
        rows.append(['revision', snapshot.get_version(), snapshot.get_value('revision'),
                     snapshot.get_all_file_names(), snapshot.get_dir('relative', file_type='first')])
        def outcome(**options):
            try:
                FileCheckin(parent, str(paths[0]), checkin_type='strict', mode='copy', **options)
                return 'ok'
            except Exception as error:
                return type(error).__name__
        auto = FileCheckin(parent, str(paths[0]), checkin_type='auto', mode='copy',
                           file_naming='chosen.txt', dir_naming='chosen/dir', do_update_versionless=False)
        fixes = {'inputs': unchanged_inputs, 'string_md5': outcome(md5s=[None]),
                 'sizes': outcome(file_sizes=[1, 2]), 'auto_naming': [auto.file_naming, auto.dir_naming]}
        auto = FileCheckin(parent, [str(paths[0])], context=self.context + '_auto', mode='copy',
                           do_update_versionless=False, md5s=[None])
        snapshot = Command.execute_cmd(auto)
        rows.append(['auto', snapshot.get_version(), snapshot.get_all_file_names(),
                     snapshot.get_dir('relative'), Path(snapshot.get_lib_path_by_type()).read_text()])
        asset_base = Environment.get_asset_dir().replace('\\', '/')
        sibling = asset_base + '_old/ghost.txt'
        inplace = FileCheckin(parent, [sibling], context=self.context + '_prefix', mode='inplace',
                              base_dir=asset_base, checkin_type='strict')
        Command.execute_cmd(inplace)
        fixes['inplace_prefix'] = inplace.get_file_objects()[0].get_value('relative_dir') or ''
        root = Environment.get_asset_dir()
        self.directory = Path(root) / 'admin/project/admin' / self.context
        self.custom = Path(root) / 'admin/checkin' / self.context / 'custom'
        # Lock/unlock lives on version 1 of the same context, as in TACTIC.
        Snapshot.lock(parent, self.context)
        assert Snapshot.is_locked(parent, self.context)
        blocked = FileCheckin(parent, str(paths[0]), context=self.context, mode='copy', checkin_type='strict')
        try:
            blocked.check_lock()
            raise AssertionError('Missing check-in lock')
        except CheckinException:
            pass
        Snapshot.unlock(parent, self.context)
        assert not Snapshot.is_locked(parent, self.context)
        search = Search('sthpw/snapshot')
        search.add_parent_filter(parent)
        search.add_filter('context', self.context)
        search.add_order_by('version')
        search.add_order_by('revision')
        state = [[obj.get_version(), obj.get_value('revision'), bool(obj.get_value('is_latest')),
                  bool(obj.get_value('is_current'))] for obj in search.get_sobjects()]
        if self.fail:
            raise ValueError('checkin rollback')
        return {'rows': rows, 'state': state, 'events': Container.get_seq('checkin_contract.events'), 'fixes': fixes}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run(fail=case.get('fail', False))
        if not command.fail:
            return Command.execute_cmd(command)
        try:
            Command.execute_cmd(command)
            raise AssertionError('Missing rollback')
        except ValueError as error:
            assert str(error) == 'checkin rollback'
        inputs = Path(Environment.get_tmp_dir()) / command.context
        search = Search('sthpw/snapshot')
        search.add_filter('context', command.context)
        sources = [(inputs / ('file_' + str(index) + '.txt')).exists() for index in range(6)]
        # Consumed create uploads stay in the undo cache, matching the original model.
        result = [command.directory.exists(), command.custom.exists(), sources, search.get_count()]
        # Native FileUndo keeps durable backups in undo, outside journalled cache mkdirs.
        roots = [Path(Environment.get_tmp_dir()) / name for name in ('cache', 'undo')]
        result.append(all(any(path.read_bytes() == ('Данные ' + str(index)).encode('utf-8')
                             for root in roots for path in root.rglob('*.txt')) for index in (2, 3)))
        assert result == [False, False, [True, True, False, False, True, True], 0, True], result
        return result
    finally:
        Environment.set_security(previous)
