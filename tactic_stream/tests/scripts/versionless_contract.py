"""Run the same CURRENT/LATEST check-in script in the original and native kernels."""
from pathlib import Path
from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Container, Environment, Xml
from pyasm.search import Search, SearchType
from pyasm.security import Security


class Run(Command):
    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.context = 'versionless_fail' if fail else 'versionless_contract'

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        inputs = Path(Environment.get_tmp_dir()) / self.context
        inputs.mkdir(parents=True, exist_ok=True)
        source = inputs / 'scene.txt'
        rows = []
        for named in (False, True):
            context = self.context + ('_named' if named else '_auto')
            if named:
                namings = []
                for mode in ('latest', 'current'):
                    naming = SearchType.create('config/naming')
                    for key, value in {'search_type': 'sthpw/project', 'snapshot_type': 'file',
                                       'context': context, mode + '_versionless': True,
                                       'file_naming': '{basefile}_' + mode + '.{ext}',
                                       'dir_naming': '{project.code}/' + context}.items():
                        naming.set_value(key, value, temp=True)
                    namings.append(naming)
                # Original supported request-local naming cache, no fixture SQL or mocks.
                Container.put('Naming:namings', namings)
                for suffix in ('', ':latest', ':current'):
                    Container.put('Naming:cache:admin' + suffix, None)
            snapshots = []
            for version in (1, 2):
                source.write_text('payload ' + str(version), encoding='utf-8')
                snapshots.append(Command.execute_cmd(FileCheckin(parent, [str(source)], ['main'],
                                 context=context, mode='copy', md5s=[None],
                                 checkin_type='strict' if named else 'auto')))
                self.aliases = []
                for mode in ('latest', 'current'):
                    alias = Snapshot.get_versionless(parent.get_search_type(), parent.get_code(),
                                                     context, mode=mode, create=False)
                    if alias is None:
                        rows.append([named, version, mode, None])
                        continue
                    files = alias.get_all_file_objects()
                    assert len(files) == 1
                    file = files[0]
                    path = Path(file.get_lib_path())
                    self.aliases.append(str(path))
                    xml = alias.get_xml_value('snapshot')
                    rows.append([named, version, mode, alias.get_version(),
                                 file.get_file_name(), path.read_text(encoding='utf-8'),
                                 Xml.get_value(xml, 'snapshot/@ref_snapshot_code') == snapshots[-1].get_code(),
                                 file.get_value('snapshot_code') == alias.get_code(),
                                 file.get_value('relative_dir'), len(alias.get_all_file_codes())])
            assert Path(snapshots[0].get_lib_path_by_type('main')).read_text(encoding='utf-8') == 'payload 1'
            assert Path(snapshots[1].get_lib_path_by_type('main')).read_text(encoding='utf-8') == 'payload 2'
            search = Search('sthpw/snapshot')
            search.add_filter('context', context)
            search.add_order_by('version')
            rows.append([named, 'flags', [[row.get_version(), bool(row.get_value('is_latest')),
                         bool(row.get_value('is_current'))] for row in search.get_sobjects()]])
        if self.fail:
            raise ValueError('versionless rollback')
        return rows


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run(case.get('fail', False))
        if not command.fail:
            return Command.execute_cmd(command)
        try:
            Command.execute_cmd(command)
            raise AssertionError('Missing rollback')
        except ValueError as error:
            assert str(error) == 'versionless rollback'
        search = Search('sthpw/snapshot')
        search.add_filter('context', command.context + '%', op='like')
        return [search.get_count(), [Path(path).exists() for path in command.aliases]]
    finally:
        Environment.set_security(previous)
