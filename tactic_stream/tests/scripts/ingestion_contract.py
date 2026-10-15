"""Same ingest/check-in calls against the original and Stream kernels."""
from pathlib import Path

from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command.ingestion_cmd import IngestionCmd, CheckinRuleSaveCmd, CheckinRuleCmd


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        definition = SearchType.get('sthpw/project')
        definition.set_value('metadata_parser', '')
        definition.commit(triggers=False)
        directory = Path(Environment.get_tmp_dir()) / 'ingestion_contract'
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / 'publish.txt'
        source.write_bytes(b'ingest source')
        options = dict(scan_type='rule', action='file', mode='scan', base_dir='',
                       session_base_dir=directory.as_posix(), pattern='{snapshot.context}.txt',
                       search_type='sthpw/project', search_key=parent.get_search_key(),
                       extra_name=[], extra_value=[], rule='{snapshot.context}.txt', title='Ingest files')
        Command.execute_cmd(CheckinRuleSaveCmd(**options))
        rules = Search('config/ingest_rule')
        rules.add_filter('title', 'Ingest files')
        rule = rules.get_sobject()
        report = {'saved': [rule.get_value('base_dir'), rule.get_value('rule'),
                            rule.get_json_value('data')['mode']]}
        cmd = IngestionCmd(**options)
        cmd.init()
        cmd.paths_invalid = []
        report['patterns'] = []
        for path, pattern in [('/files/ABC/publish.txt', '/files/{code}/{snapshot.context}.txt'),
                              ('/files/ABC/publish.txt', '/files/{sobject.code}/{snapshot.context}.txt'),
                              ('/files/ABC/publish.txt', '/files/{code}/{snapshot.context}.txX'),
                              ('/files/ABC/publish.txt.extra', '/files/{code}/{snapshot.context}.txt')]:
            cmd.sobject_tags, cmd.snapshot_tags = {}, {}
            matched = cmd.process_pattern(path, pattern)
            report['patterns'].append([matched, cmd.sobject_tags, cmd.snapshot_tags])
        cmd.sobject_tags, cmd.snapshot_tags = {}, {}
        try:
            cmd.process_path(source.as_posix(), directory.as_posix() + '/{snapshot.context}.txt', 'file')
            report['scan'] = [cmd.data[source.as_posix()]['size'], cmd.data[source.as_posix()]['status'],
                              cmd.snapshot_tags['context'], source.exists()]
        except TypeError as error:
            report['scan'] = type(error).__name__
        try:
            Command.execute_cmd(IngestionCmd(**options))
            report['walk'] = 'ok'
        except Exception as error:
            report['walk'] = type(error).__name__
        rows = []
        for context, mode in [('ingest_copy', 'copy'), ('ingest_move', 'move')]:
            file = directory / (context + '.txt')
            file.write_text(context)
            checkin = FileCheckin(parent, [file.as_posix()], context=context, mode=mode,
                                  checkin_type='strict', ingest_mode='ingest', md5s=[None])
            snapshot = Command.execute_cmd(checkin)
            data = checkin.get_file_objects()[0]
            rows.append([snapshot.get_version(), bool(snapshot.get_value('is_latest')),
                         data.get_value('snapshot_code') == snapshot.get_code(),
                         Path(snapshot.get_lib_path_by_type()).read_text(), file.exists()])
        report['checkins'] = rows
        if self.kwargs.get('fail'):
            raise ValueError('late bulk ingest failure')
        return report


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


class Import(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        directory = Path(Environment.get_tmp_dir()) / 'ingest_import'
        directory.mkdir(parents=True, exist_ok=True)
        for name in ('alpha.txt', 'beta.txt', 'ignored.txt', 'other.bin'):
            (directory / name).write_text(name)
        definition = SearchType.get('sthpw/project')
        definition.set_value('metadata_parser', '')
        definition.commit(triggers=False)
        session = SearchType.create('config/ingest_session')
        session.set_value('code', 'INGEST_SESSION')
        session.set_value('base_dir', directory.as_posix())
        session.commit()
        options = dict(title='Import', scan_type='rule', action='file', mode='scan',
                       base_dir='', session_code='INGEST_SESSION', rule='{snapshot.context}.txt',
                       ignore='ignored.txt', filter='/.*\\.txt/', search_key=Project.get().get_search_key())
        Command.execute_cmd(CheckinRuleSaveCmd(**options))
        search = Search('config/ingest_rule')
        search.add_filter('title', 'Import')
        rule = search.get_sobject()
        scan = CheckinRuleCmd(rule_code=rule.get_code())
        Command.execute_cmd(scan)
        scan_snapshots = Search('sthpw/snapshot')
        scan_snapshots.add_filters('context', ['alpha', 'beta'])
        assert scan_snapshots.get_count() == 0
        result = [sorted(Path(path).name for path in scan.info['paths_matched']),
                  sorted(Path(path).name for path in scan.info['paths_not_matched'])]
        if self.kwargs.get('fail'):
            script = SearchType.create('config/custom_script')
            script.set_value('code', 'INGEST_FAIL')
            script.set_value('folder', 'ingest')
            script.set_value('title', 'fail')
            script.set_value('language', 'python')
            script.set_value('script', 'if input["path"].endswith("beta.txt"):\n    raise ValueError("ingest handler failed")\nreturn True')
            script.commit()
            options['process_script'] = 'ingest/fail'
        if self.kwargs.get('reject'):
            script = SearchType.create('config/custom_script')
            script.set_value('code', 'INGEST_VALIDATE')
            script.set_value('folder', 'ingest')
            script.set_value('title', 'validate')
            script.set_value('language', 'python')
            script.set_value('script', 'if input["path"].endswith("alpha.txt"):\n    raise IngestException("invalid file")\nreturn True')
            script.commit()
            options['validation_script'] = 'ingest/validate'
        publish = IngestionCmd(**dict(options, mode='checkin', pattern=options['rule'],
                                    scan_type='list', file_list='\n'.join((directory / name).as_posix()
                                    for name in ('alpha.txt', 'beta.txt'))))
        Command.execute_cmd(publish)
        search = Search('sthpw/snapshot')
        search.add_filters('context', ['alpha', 'beta'])
        search.add_order_by('context')
        snapshots = search.get_sobjects()
        result.append([[snapshot.get_value('context'), snapshot.get_version(),
                        Path(snapshot.get_lib_path_by_type()).read_text(),
                        snapshot.get_json_value('metadata')['size']] for snapshot in snapshots
                       if snapshot.get_version() > 0])
        result.append(all((directory / name).read_text() == name for name in ('alpha.txt', 'beta.txt')))
        if self.kwargs.get('reject'):
            result.append([Path(path).name for path in publish.info['paths_invalid']])
        if self.kwargs.get('late_fail'):
            raise ValueError('late ingest failure')
        return result


def import_files(fail=False, late_fail=False, reject=False):
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
        return Command.execute_cmd(Import(fail=fail, late_fail=late_fail, reject=reject))
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
