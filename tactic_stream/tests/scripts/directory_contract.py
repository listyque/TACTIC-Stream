"""Identical directory check-in and utility calls in original and Stream."""
from pathlib import Path
from datetime import timedelta

from pyasm.biz import Project, Snapshot, FileRange
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Common, Environment, FormatValue, TimeCode
from pyasm.search import Search, SearchType
from pyasm.security import Security


def tree(directory):
    return sorted([[path.relative_to(directory).as_posix(), path.read_text()]
                   for path in directory.rglob('*') if path.is_file()])


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        source = Path(Environment.get_tmp_dir()) / 'directory_contract'
        source.mkdir(parents=True, exist_ok=True)
        (source / 'main.txt').write_text('main')
        (source / 'nested').mkdir(exist_ok=True)
        (source / 'nested' / 'данные.txt').write_text('nested')
        (source / 'empty').mkdir(exist_ok=True)
        parent = Project.get()
        definition = SearchType.get('sthpw/project')
        definition.set_value('metadata_parser', '')
        definition.commit(triggers=False)
        info = Common.get_dir_info(source.as_posix())
        results = {'info': info, 'rows': []}
        for mode in ('copy', 'move', 'inplace'):
            directory = source / mode
            directory.mkdir()
            (directory / 'entry.txt').write_text(mode)
            (directory / 'nested').mkdir()
            (directory / 'nested' / 'entry.txt').write_text('inside')
            (directory / 'empty').mkdir()
            cmd = FileCheckin(parent, [directory.as_posix()], context='directory_' + mode,
                              snapshot_type='directory', mode=mode, checkin_type='strict',
                              do_update_versionless=False, md5s=[None])
            snapshot = Command.execute_cmd(cmd)
            file = cmd.get_file_objects()[0]
            repo = Path(snapshot.get_lib_path_by_type())
            results['rows'].append([mode, snapshot.get_version(), file.get_value('base_type'),
                                   file.get_value('st_size'), file.get_value('md5') or '',
                                   tree(repo), (repo / 'empty').is_dir(), directory.exists()])
        values = [(0, 'KB'), (512, 'KB'), (1024, 'KB'), (False, 'True|False'),
                  ('false', 'true|false'), ({'b': 2, 'a': 1}, 'DICT'),
                  (timedelta(days=2, seconds=3), 'SECONDS'), ('2026-10-07', '31/12/99')]
        results['format'] = []
        for value, format in values:
            try:
                results['format'].append(FormatValue().get_format_value(value, format))
            except Exception as error:
                results['format'].append(type(error).__name__)
        results['timecode'] = []
        for frames in (0, 36, 1800):
            try:
                value = TimeCode(frames=frames, fps=24)
                results['timecode'].append([value.get_timecode(), (value + 24).get_frames(),
                                            (value - 12).get_frames()])
            except Exception as error:
                results['timecode'].append(type(error).__name__)
        if self.kwargs.get('fail'):
            raise ValueError('late directory failure')
        return results


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        return Command.execute_cmd(Run(fail=case.get('fail', False)))
    finally:
        Environment.set_security(previous)


class IngestDirectories(Command):
    def execute(self):
        from tactic.command import IngestionCmd
        self.get_transaction().set_sync(False)
        inputs = Path(Environment.get_tmp_dir()) / 'directory_ingest'
        inputs.mkdir(parents=True, exist_ok=True)
        for name in ('first', 'second'):
            folder = inputs / name
            folder.mkdir()
            (folder / 'main.txt').write_text(name)
            (folder / 'nested').mkdir()
            (folder / 'nested' / 'main.txt').write_text('child')
            (folder / 'empty').mkdir()
        definition = SearchType.get('sthpw/project')
        definition.set_value('metadata_parser', '')
        definition.commit(triggers=False)
        handoff = Path(Environment.get_server_handoff_dir())
        handoff.mkdir(parents=True, exist_ok=True)
        (handoff / 'unrelated.txt').write_text('keep me')
        options = dict(scan_type='rule', action='directory', mode='scan', base_dir='',
                       session_base_dir=inputs.as_posix(), pattern='{snapshot.context}/',
                       search_key=Project.get().get_search_key())
        if self.kwargs.get('list'):
            options.update(scan_type='list', file_list='\n'.join((inputs / name).as_posix() for name in ('first', 'second')))
        scan = IngestionCmd(**options)
        Command.execute_cmd(scan)
        result = [sorted(Path(path).name for path in scan.info['paths_matched'])]
        publish = IngestionCmd(**dict(options, mode='checkin'))
        Command.execute_cmd(publish)
        search = Search('sthpw/snapshot')
        search.add_filters('context', ['first', 'second'])
        search.add_order_by('context')
        result.append([[snapshot.get_value('context'), tree(Path(snapshot.get_lib_path_by_type()))]
                       for snapshot in search.get_sobjects() if snapshot.get_version() > 0])
        result.append((handoff / 'unrelated.txt').read_text())
        if self.kwargs.get('fail'):
            raise ValueError('late directory ingest failure')
        return result


def ingest(fail=False, list=False):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    security = Environment.get_security()
    old_ticket = security._ticket
    security._ticket = Search('sthpw/ticket').get_sobject()
    try:
        return Command.execute_cmd(IngestDirectories(fail=fail, list=list))
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
