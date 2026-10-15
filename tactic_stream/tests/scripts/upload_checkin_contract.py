"""Unchanged FileUpload/simple_checkin script executed by both actual kernels."""
import base64
from io import BytesIO
from pathlib import Path
from pyasm.biz import Project
from pyasm.command import Command, FileUpload
from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security, Ticket


class Storage:
    def __init__(self, path, payload):
        self.filename = 'payload.bin'
        self.file = BytesIO(payload)
        self.path = path
        path.write_bytes(payload)

    def get_path(self):
        return str(self.path)


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('upload_checkin_fixture', 'admin')
        parent = Project.get()
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'ticket': Environment.get_ticket(), 'project': 'admin', 'language': 'python'}
        directory = Path(Environment.get_upload_dir())
        incoming = directory / 'incoming'
        rows = []
        for version in (1, 2):
            for append, payload in ((False, b'\x00\xffbinary'), (True, b'\x80\xfesecond')):
                encoded = b'data:xyz/xyz;base64,' + base64.b64encode(payload)
                storage = Storage(incoming, encoded)
                upload = FileUpload()
                upload.set_field_storage(storage, 'payload.bin')
                upload.set_create_icon(False)
                upload.set_file_dir(str(directory))
                upload.set_append_mode(append)
                upload.set_decode(True)
                upload.execute()
                storage.file.close()
            assert (directory / 'payload.bin').read_bytes() == b'\x00\xffbinary\x80\xfesecond'
            result = api.simple_checkin(ticket, parent.get_search_key(), 'upload_checkin_contract',
                '/client/payload.bin', 'file', 'Uploaded binary', False, 'main', True, None,
                {}, None, False, {}, False, False, 'pyasm.checkin.FileCheckin', None,
                'strict', None, None, None)
            assert result['version'] == version
            file = result['__file_sobjects__'][0]
            path = Path(file['checkin_dir']) / file['file_name']
            rows.append([result['version'], result['context'], result['description'],
                         file['type'], file['file_name'], file['st_size'], file['md5'],
                         list(path.read_bytes()), file['source_path']])
            assert not (directory / 'payload.bin').exists()
        search = Search('sthpw/snapshot')
        search.add_filter('context', 'upload_checkin_contract')
        search.add_order_by('version')
        return {'rows': rows, 'flags': [[s.get_version(), bool(s.get_value('is_latest')),
                    bool(s.get_value('is_current'))] for s in search.get_sobjects()]}


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
