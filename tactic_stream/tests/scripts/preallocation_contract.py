"""Same preallocation and local API script in both actual kernels."""
from pathlib import Path
from xmlrpc.client import Binary
from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileAppendCheckin, FileCheckin
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security, Ticket


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('preallocation_fixture', 'admin')
        parent = Project.get()
        snapshot = Snapshot.create(parent, 'file', 'preallocation_contract')
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'ticket': Environment.get_ticket(), 'project': 'admin', 'language': 'python'}
        root = Environment.get_asset_dir().replace('\\', '/')
        def relative(path):
            return path.replace('\\', '/').replace(root, 'ASSETS')
        paths = []
        for protocol in (None, 'client_repo', 'web'):
            path = snapshot.get_preallocated_path(file_name='scene.txt', mkdir=False, protocol=protocol, checkin_type='strict')
            paths.append(relative(path))
        reserved = snapshot.get_preallocated_path(file_name='scene.txt', mkdir=False, checkin_type='strict')
        assert not Path(reserved).parent.exists()
        api_path = api.get_preallocated_path(ticket, snapshot.get_code(), 'main', 'scene.txt', False, None, '', 'strict')
        assert api_path == reserved, (api_path, reserved)
        reserved = api.get_preallocated_path(ticket, {'code': snapshot.get_code()}, 'main', 'scene.txt', True, None, '', 'strict')
        Path(reserved).write_bytes('Предварительно размещённый файл'.encode('utf-8'))
        code = snapshot.get_code()
        appended = api.add_file(ticket, code, reserved, 'main', False, 'preallocate')
        assert appended['code'] == code and appended['version'] == 1
        # Query fresh metadata rather than the legacy cached file map.
        search = Search('sthpw/snapshot')
        search.add_filter('code', code)
        snapshot = search.get_sobject()
        rows = [[snapshot.get_version(), snapshot.get_all_file_names(),
                 Path(snapshot.get_lib_path_by_type()).read_bytes().decode('utf-8')]]
        for name, payload in (('audio.bin', b'\x00\xffbinary'), ('empty.bin', b'')):
            assert api.upload_file(ticket, '/client/' + name, Binary(payload)) is True
            assert api.get_upload_file_size(ticket, name) == len(payload)
        supplied_paths = ['/client/audio.bin', '/client/empty.bin']
        supplied_types = ['audio', 'empty']
        api.add_file(ticket, code, supplied_paths, supplied_types)
        search = Search('sthpw/snapshot')
        search.add_filter('code', code)
        snapshot = search.get_sobject()
        rows.append([snapshot.get_version(), snapshot.get_all_file_names(),
                     list(Path(snapshot.get_lib_path_by_type('audio')).read_bytes()),
                     Path(snapshot.get_lib_path_by_type('empty')).stat().st_size,
                     supplied_paths == ['/client/audio.bin', '/client/empty.bin'], supplied_types == ['audio', 'empty']])
        api.remove_file(ticket, {'code': code}, 'empty')
        search = Search('sthpw/file')
        search.add_filter('snapshot_code', code)
        search.add_order_by('id')
        rows.append([file.get_file_name() for file in search.get_sobjects()])
        # A virtual path does not persist a Snapshot or File.
        virtual = api.get_virtual_snapshot_path(ticket, parent.get_search_key(), 'virtual_preallocation',
                    'file', None, 'main', 'preview.txt', False, None, '', 'strict')
        search = Search('sthpw/snapshot')
        search.add_filter('context', 'virtual_preallocation')
        assert search.get_count() == 0
        return {'paths': paths, 'rows': rows, 'virtual': relative(virtual)}


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
        return Command.execute_cmd(Run())
    finally:
        security._ticket = old_ticket
        Environment.set_security(previous)
