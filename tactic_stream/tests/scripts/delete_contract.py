"""Identical database-only and repository deletion script for both kernels."""
from pathlib import Path
from pyasm.biz import File, Project, Snapshot
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.ui.tools import DeleteCmd


def state(context):
    search = Search('sthpw/snapshot')
    search.add_filter('context', context)
    search.add_order_by('version')
    return [[row.get_version(), bool(row.get_value('is_latest')), bool(row.get_value('is_current')),
             sorted(row.get_all_file_types())] for row in search.get_sobjects()]


class Setup(Command):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        inputs = Path(Environment.get_tmp_dir()) / self.context
        inputs.mkdir(parents=True, exist_ok=True)
        self.snapshots = []
        self.paths = []
        self.codes = []
        for version in (1, 2, 3):
            paths = [inputs / (kind + '.txt') for kind in ('main', 'secondary')]
            for path in paths:
                path.write_text(path.stem + str(version), encoding='utf-8')
            snapshot = Command.execute_cmd(FileCheckin(parent, [str(path) for path in paths],
                            ['main', 'secondary'], context=self.context, mode='copy',
                            checkin_type='strict', is_current=version == 1, md5s=[None, None]))
            snapshot.set_value('timestamp', '2026-01-01 12:00:0' + str(version))
            snapshot.commit(triggers='none')
            self.snapshots.append(snapshot)
            self.paths.extend(snapshot.get_all_lib_paths())
            self.codes.extend(snapshot.get_all_file_codes())
        hour = SearchType.create('sthpw/work_hour')
        hour.set_parent(self.snapshots[1])
        hour.set_value('straight_time', 1.25)
        hour.set_value('over_time', 0.75)
        hour.commit()
        self.hour_code = hour.get_code()
        assert hour.get_value('login') == 'admin'
        assert hour.get_value('project_code') == 'admin'
        return state(self.context)


class Remove(Command):
    def __init__(self, setup, fail):
        super().__init__()
        self.setup, self.fail = setup, fail

    def execute(self):
        self.get_transaction().set_sync(False)
        first, second, third = self.setup.snapshots
        rows = []
        DeleteCmd(sobject=second, auto_discover=True).execute()
        rows.append(state(self.setup.context))
        hours = Search('sthpw/work_hour')
        hours.add_filter('code', self.setup.hour_code)
        assert hours.get_count() == 0
        DeleteCmd(search_key=third.get_search_key()).execute()
        rows.append(state(self.setup.context))
        first.remove_file('secondary')
        rows.append(state(self.setup.context))
        rows.append([Path(path).exists() for path in self.setup.paths])
        if self.fail:
            raise ValueError('delete rollback')
        DeleteCmd(sobject=first).execute()
        rows.append(state(self.setup.context))
        rows.append([File.get_by_code(code) is not None for code in self.setup.codes])
        rows.append([Path(path).exists() for path in self.setup.paths])
        # SObject.delete remains metadata-only, without a physical file cascade.
        parent = Project.get()
        path = Path(Environment.get_tmp_dir()) / 'metadata_delete.txt'
        path.write_text('keep physical file', encoding='utf-8')
        snapshot = Command.execute_cmd(FileCheckin(parent, [str(path)], context=self.setup.context + '_metadata',
                                      checkin_type='strict', mode='copy', md5s=[None]))
        code = snapshot.get_all_file_codes()[0]
        physical = Path(snapshot.get_lib_path_by_type())
        snapshot.delete()
        rows.append([File.get_by_code(code) is not None, physical.read_text(encoding='utf-8')])
        return rows


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        fail = case.get('fail', False)
        setup = Setup('delete_rollback' if fail else 'delete_contract')
        before = Command.execute_cmd(setup)
        if not fail:
            return Remove.execute_cmd(Remove(setup, False))
        try:
            Command.execute_cmd(Remove(setup, True))
            raise AssertionError('Missing rollback')
        except ValueError as error:
            assert str(error) == 'delete rollback'
        files = Search('sthpw/file')
        files.add_filters('code', setup.codes)
        result = [state(setup.context), [Path(path).read_text(encoding='utf-8') if Path(path).exists() else None
                                        for path in setup.paths], files.get_count()]
        assert result[0] == before
        assert result[2] == 6
        hours = Search('sthpw/work_hour')
        hours.add_filter('code', setup.hour_code)
        assert hours.get_count() == 1
        return result
    finally:
        Environment.set_security(previous)
