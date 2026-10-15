"""Run unchanged in the original and native TACTIC kernels."""
from pathlib import Path
from pyasm.biz import Project, Snapshot, File, FileRange, FileGroup
from pyasm.checkin import FileCheckin, FileAppendCheckin, FileGroupCheckin, FileGroupAppendCheckin
from pyasm.command import Command
from pyasm.common import Environment, Xml, Container
from pyasm.search import Search, SearchType
from pyasm.security import Security


def files(snapshot):
    # Query rows directly so legacy's stale snapshot file-map does not hide append.
    search = Search('sthpw/file')
    search.add_filter('snapshot_code', snapshot.get_code())
    search.add_order_by('id')
    result = []
    for file in search.get_sobjects():
        path = str(Path(file.get_lib_dir(snapshot=snapshot)) / file.get_file_name())
        paths = FileGroup.expand_paths(path, FileRange.get(file.get_file_range())) if file.get_file_range() else [path]
        result.append([file.get_type(), file.get_file_name(), file.get_file_range(),
                       file.get_value('base_type'), file.get_value('st_size'),
                       [Path(path).read_text(encoding='utf-8') if Path(path).is_file() else None for path in paths]])
    return result


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        folder = Path(Environment.get_tmp_dir()) / 'append_group_contract'
        folder.mkdir(parents=True, exist_ok=True)
        def source(name, payload):
            path = folder / name
            path.write_text(payload, encoding='utf-8')
            return str(path)
        first = Command.execute_cmd(FileCheckin(parent, [source('first.txt', 'first')],
                    context='append_contract', mode='copy', checkin_type='strict', is_current=True))
        second = Command.execute_cmd(FileCheckin(parent, [source('second.txt', 'second')],
                    context='append_contract', mode='copy', checkin_type='strict', is_current=False))
        code, version = first.get_code(), first.get_version()
        command = FileAppendCheckin(code, [source('extra.txt', 'extra')], ['extra'], mode='copy')
        appended = Command.execute_cmd(command)
        assert appended.get_code() == code and appended.get_version() == version
        snapshots = Search('sthpw/snapshot')
        snapshots.add_filter('context', 'append_contract')
        snapshots.add_order_by('version')
        flags = [[row.get_version(), bool(row.get_value('is_latest')), bool(row.get_value('is_current'))]
                 for row in snapshots.get_sobjects()]
        second.add_file([source('thumb.txt', 'thumb'), source('proxy.txt', 'proxy')], ['thumb', 'proxy'], mode='copy')
        result = {'append': [files(Snapshot.get_by_code(code)), files(Snapshot.get_by_code(second.get_code()))],
                  'flags': flags, 'groups': []}
        file_range = FileRange(1, 5, 2)
        for index, mode in enumerate(('copy', 'move', 'create', 'inplace')):
            directory = folder / str(index)
            directory.mkdir(exist_ok=True)
            template = str(directory / ('image.####.txt' if index % 2 == 0 else 'image.%04d.txt'))
            paths = FileGroup.expand_paths(template, file_range)
            for path in paths:
                Path(path).write_text(Path(path).name, encoding='utf-8')
            command = FileGroupCheckin(parent, [template], ['main'], file_range,
                        context='group_contract_' + str(index), mode=mode, keep_file_name=True, checkin_type='strict')
            snapshot = Command.execute_cmd(command)
            added = str(directory / 'extra.####.txt')
            for path in FileGroup.expand_paths(added, file_range):
                Path(path).write_text('extra frame', encoding='utf-8')
            appended = Command.execute_cmd(FileGroupAppendCheckin(snapshot.get_code(), [added], ['extra'],
                        file_range, keep_file_name=True, mode='copy'))
            assert appended.get_code() == snapshot.get_code() and appended.get_version() == 1
            xml = appended.get_snapshot_xml()
            ranges = [Xml.get_attribute(node, 'file_range') for node in xml.get_nodes('snapshot/file')]
            result['groups'].append([mode, files(appended), ranges, [Path(path).exists() for path in paths]])
        # Legacy's default group naming loses source paths in copy/move mode.
        template = str(folder / 'named.####.txt')
        for path in FileGroup.expand_paths(template, file_range):
            Path(path).write_text('named', encoding='utf-8')
        try:
            named = Command.execute_cmd(FileGroupCheckin(parent, [template], ['main'], file_range,
                                context='group_named', mode='copy', checkin_type='strict'))
            result['named'] = ['ok', files(named)[0][1]]
        except Exception as error:
            result['named'] = [type(error).__name__]
        return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        if case.get('lifecycle'):
            return lifecycle(case.get('fail', False))
        return Command.execute_cmd(Run())
    finally:
        Environment.set_security(previous)


def lifecycle(fail):
    from tactic.ui.tools import DeleteCmd
    parent = Project.get()
    context = 'frames_rollback' if fail else 'frames_lifecycle'
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
    folder = Path(Environment.get_tmp_dir()) / context
    folder.mkdir(parents=True, exist_ok=True)
    file_range = FileRange(1, 5, 2)
    templates = [str(folder / 'render.####.txt'), str(folder / 'preview.%04d.txt')]
    sources = [path for template in templates for path in FileGroup.expand_paths(template, file_range)]
    for path in sources:
        Path(path).write_text('original frame', encoding='utf-8')
    first = Command.execute_cmd(FileGroupCheckin(parent, templates, ['main', 'main'], file_range,
                context=context, mode='copy', checkin_type='strict', keep_file_name=True))
    original_paths = first.get_all_lib_paths(expand_paths=True)
    assert len(set(original_paths)) == 6
    aliases = [Snapshot.get_versionless(parent.get_search_type(), parent.get_code(), context,
                        mode=mode, create=False) for mode in ('latest', 'current')]
    codes = [alias.get_code() for alias in aliases]
    old_xml = [alias.get_value('snapshot') for alias in aliases]
    alias_paths = [path for alias in aliases for path in alias.get_all_lib_paths(expand_paths=True)]
    assert len(set(alias_paths)) == 12
    assert all(Path(path).read_text(encoding='utf-8') == 'original frame' for path in alias_paths)
    addition = str(folder / 'extra.####.txt')
    extra_sources = FileGroup.expand_paths(addition, file_range)
    for path in extra_sources:
        Path(path).write_text('extra frame', encoding='utf-8')
    command = Command()
    def mutate():
        command.get_transaction().set_sync(False)
        appended = Command.execute_cmd(FileGroupAppendCheckin(first.get_code(), [addition], ['extra'],
                        file_range, keep_file_name=True, mode='move'))
        assert appended.get_code() == first.get_code() and appended.get_version() == 1
        assert all(not Path(path).exists() for path in extra_sources)
        appended.remove_file('main')
        assert all(not Path(path).exists() for path in original_paths + alias_paths)
        if fail:
            raise ValueError('after frame append/remove')
        return appended
    command.execute = mutate
    if fail:
        try:
            Command.execute_cmd(command)
            raise AssertionError('Missing frame rollback')
        except ValueError as error:
            assert str(error) == 'after frame append/remove'
        assert [Snapshot.get_by_code(code).get_value('snapshot') for code in codes] == old_xml
        assert all(Path(path).read_text(encoding='utf-8') == 'original frame' for path in original_paths + alias_paths)
        assert all(Path(path).read_text(encoding='utf-8') == 'extra frame' for path in extra_sources)
        return ['rolled_back', files(Snapshot.get_by_code(first.get_code()))]
    appended = Command.execute_cmd(command)
    extra_paths = appended.get_all_lib_paths(expand_paths=True)
    assert len(extra_paths) == 3
    assert all(Path(path).read_text(encoding='utf-8') == 'extra frame' for path in extra_paths)
    # Replace a three-frame alias with a single frame; old frames/sidecars disappear.
    for path in FileGroup.expand_paths(templates[0], FileRange(1, 1)):
        Path(path).write_text('replacement', encoding='utf-8')
    second = Command.execute_cmd(FileGroupCheckin(parent, [templates[0]], ['main'], FileRange(1, 1),
                context=context, mode='copy', checkin_type='strict'))
    final_alias_paths = []
    for code in codes:
        alias = Snapshot.get_by_code(code)
        paths = alias.get_all_lib_paths(expand_paths=True)
        assert len(paths) == 1
        assert Path(paths[0]).read_text(encoding='utf-8') == 'replacement'
        final_alias_paths.extend(paths)
    # First is no longer latest; deleting it must preserve the surviving aliases.
    Command.execute_cmd(DeleteCmd(sobject=appended))
    assert all(not Path(path).exists() for path in extra_paths)
    assert all(Path(path).read_text(encoding='utf-8') == 'replacement' for path in final_alias_paths)
    Command.execute_cmd(DeleteCmd(sobject=second))
    assert all(not Path(path).exists() for path in final_alias_paths)
    assert all(not (Path(path).parent / ('.' + Path(path).name + '.link')).exists() for path in alias_paths + final_alias_paths)
    assert all(Snapshot.get_by_code(code) is None for code in codes)
    return ['removed', len(original_paths), len(alias_paths), len(extra_paths), len(final_alias_paths)]
