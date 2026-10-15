"""Original handoff API bodies, exercised on isolated files and databases."""
from pathlib import Path
from pyasm.biz import Project, Snapshot, FileGroup, FileRange
from pyasm.command import Command
from pyasm.common import Config, Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security, Ticket
from pyasm.web.api_xmlrpc import ApiXMLRPC


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('handoff_fixture', 'admin')
        directory = Path(Environment.get_tmp_dir()) / 'handoff_fixture'
        directory.mkdir(parents=True, exist_ok=True)
        keys = ('win32_client_handoff_dir', 'linux_client_handoff_dir', 'win32_server_handoff_dir', 'linux_server_handoff_dir')
        old = {key: Config.get_value('checkin', key) for key in keys}
        definition = SearchType.get('sthpw/project')
        old_parser = definition.get_value('metadata_parser', no_exception=True)
        definition.set_value('metadata_parser', '')
        definition.commit(triggers=False)
        try:
            for key in keys:
                Config.set_value('checkin', key, directory.as_posix())
            api = ApiXMLRPC()
            api.set_protocol('local')
            ticket = dict(ticket=Environment.get_ticket(), project='admin', language='python')
            handoff = Path(api.get_handoff_dir(ticket))
            handoff.mkdir(parents=True, exist_ok=True)
            assert handoff.name == Environment.get_ticket()
            parent = Project.get()
            (handoff / 'main.txt').write_bytes(b'main')
            row = api.simple_checkin(ticket, parent.get_search_key(), 'handoff', '/client/main.txt',
                                     'file', 'No description', True, 'main', True, None, {}, None, False, {}, False, False)
            code = row['code']
            result = [row['context'], row['version']]
            (handoff / 'extra.txt').write_bytes(b'extra')
            api.add_file(ticket, code, '/client/extra.txt', 'extra', True)
            snapshot = Snapshot.get_by_code(code)
            result.append([[kind, Path(snapshot.get_lib_path_by_type(kind)).read_text()]
                           for kind in ('main', 'extra')])
            result.append([(handoff / name).exists() for name in ('main.txt', 'extra.txt')])
            for frame in (1, 2):
                (handoff / ('image.%04d.txt' % frame)).write_text('frame%d' % frame)
            row = api.group_checkin(ticket, parent.get_search_key(), 'handoff_frames', '/client/image.####.txt', '1-2')
            snapshot = Snapshot.get_by_code(row['code'])
            result.append([row['context'], row['version'],
                           [Path(path).read_text() for path in snapshot.get_all_lib_paths(expand_paths=True)]])
            for frame in (1, 2):
                (handoff / ('appended.%04d.txt' % frame)).write_text('extra%d' % frame)
            api.add_group(ticket, row['code'], '/client/appended.####.txt', 'extra', '1-2', True)
            snapshot = Snapshot.get_by_code(row['code'])
            file = snapshot.get_file_by_type('extra')
            template = Path(file.get_value('checkin_dir')) / file.get_file_name()
            result.append([Path(path).read_text() for path in FileGroup.expand_paths(str(template), FileRange.get('1-2'))])
            result.append(sorted(path.name for path in handoff.iterdir() if path.is_file()))
            if self.fail:
                raise ValueError('late handoff failure')
            return result
        finally:
            definition.set_value('metadata_parser', old_parser or '')
            definition.commit(triggers=False)
            for key, value in old.items():
                Config.set_value('checkin', key, value or '')


def run(case):
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
        command = Run()
        command.fail = case.get('fail', False)
        return Command.execute_cmd(command)
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
