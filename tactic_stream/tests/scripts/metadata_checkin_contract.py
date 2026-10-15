"""One check-in script run by the original and native kernels on private data."""
from pathlib import Path
from PIL import Image
from pyasm.biz import Project
from pyasm.checkin import FileCheckin, PILMetadataParser, CheckinMetadataHandler
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class Run(Command):
    def __init__(self, hook=False):
        super().__init__()
        self.hook = hook

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        definition = SearchType.get(parent.get_search_type())
        definition.set_value('metadata_parser', 'PIL' if self.hook else '')
        definition.commit(triggers=False)
        source = Path(Environment.get_tmp_dir()) / 'metadata.png'
        source.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (31, 17), (20, 40, 60)).save(source)
        parser = PILMetadataParser(path=str(source))
        rows = [parser.get_metadata(), parser.get_tactic_metadata()]
        for i in range(3):
            command = FileCheckin(parent, [str(source)], ['main'], context='metadata_checkin',
                context_index_padding=3, mode='copy', checkin_type='strict', file_naming='metadata.png', dir_naming='admin/metadata/{snapshot.context}')
            snapshot = Command.execute_cmd(command)
            file = snapshot.get_file_by_type('main')
            if not self.hook:
                CheckinMetadataHandler(snapshot=snapshot, files=[str(source)], file_objects=[file], parser='PIL', commit=False).execute()
            metadata = file.get_metadata()
            assert metadata == snapshot.get_metadata()
            assert metadata['Dirname'].replace('\\', '/') == str(Path(file.get_lib_path()).parent).replace('\\', '/')
            assert 'width=31' in file.get_value('metadata_search')
            assert Path(file.get_lib_path()).read_bytes() == source.read_bytes()
            del metadata['Dirname']
            rows.append([snapshot.get_value('context'), snapshot.get_version(),
                         command.context, metadata])
        rows.append(CheckinMetadataHandler().get_searchable({'Width': 31, 'Color Space': 'RGB (8 bit)', '__keys__': ['Width'], '42': 'ignored'}))
        return rows


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        return Command.execute_cmd(Run(case.get('hook', False)))
    finally:
        Environment.set_security(previous)
