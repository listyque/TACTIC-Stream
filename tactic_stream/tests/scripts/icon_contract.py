"""Same IconCreator, FileUpload and API script in both actual TACTIC kernels."""
from io import BytesIO
from pathlib import Path
from PIL import Image
from pyasm.biz import IconCreator, Project, Snapshot
from pyasm.command import Command, FileUpload
from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security, Ticket


def image_info(path):
    with Image.open(path) as image:
        return [Path(path).name, image.format, list(image.size), image.mode,
                list(image.convert('RGB').getpixel((0, 0)))]


class Storage:
    def __init__(self, path, payload):
        self.filename = 'upload.png'
        self.file = BytesIO(payload)
        self.path = path
        path.write_bytes(payload)

    def get_path(self):
        return str(self.path)


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('icon_fixture', 'admin')
        directory = Path(Environment.get_upload_dir())
        source = directory / 'landscape.0001.png'
        Image.new('RGB', (800, 400), (40, 80, 120)).save(source)
        rows = []
        creator = IconCreator(str(source))
        assert creator.get_web_file_size() == (640, 480)
        assert creator.get_icon_file_size() == (120, 100)
        creator.create_icons()
        rows.append([image_info(creator.get_web_path()), image_info(creator.get_icon_path())])
        creator = IconCreator(str(source))
        creator.set_icon_mode()
        creator.execute()
        rows.append([creator.get_web_path(), image_info(creator.get_icon_path())])
        creator = IconCreator(str(source))
        creator.set_texture_mode()
        creator.execute()
        rows.append([image_info(creator.get_web_path()), image_info(creator.get_icon_path())])
        paths, types = IconCreator.add_icons([str(source)])
        rows.append([types, [image_info(path) for path in paths]])
        storage = Storage(directory / 'incoming', source.read_bytes())
        upload = FileUpload()
        upload.set_file_dir(str(directory))
        upload.set_field_storage(storage, 'upload.png')
        upload.execute()
        rows.append([upload.get_file_types(), [image_info(path) for path in upload.get_files()]])
        storage.file.close()
        parent = Project.get()
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'ticket': Environment.get_ticket(), 'project': 'admin', 'language': 'python'}
        result = api.simple_checkin(ticket, parent.get_search_key(), 'icon_checkin',
            '/client/upload.png', 'file', 'Image with previews', False, 'main', True, None,
            {}, None, False, {}, False, True, 'pyasm.checkin.FileCheckin', None,
            'strict', None, None, None)
        rows.append([[file['type'], image_info(Path(file['checkin_dir']) / file['file_name'])]
                      for file in result['__file_sobjects__']])
        snapshot = Snapshot.create(parent, 'file', 'icon_append')
        api.add_file(ticket, snapshot.get_code(), str(source), 'main', False, None, True)
        search = Search('sthpw/file')
        search.add_filter('snapshot_code', snapshot.get_code())
        search.add_order_by('id')
        rows.append([[file.get_type(), image_info(Path(file.get_value('checkin_dir')) / file.get_file_name())]
                      for file in search.get_sobjects()])
        return rows


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
