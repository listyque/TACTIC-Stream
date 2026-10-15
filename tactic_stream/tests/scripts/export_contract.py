"""The same backend export script runs in original TACTIC and both native vendors."""
from pathlib import Path
import tempfile
import zipfile

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command import PluginCreator, PluginInstaller, PluginTools


class Export(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        obj = SearchType.create(self.search_type)
        obj.set_value('code', self.code)
        obj.set_value('name', self.value)
        obj.set_value('amount', 23)
        obj.commit()
        creator = PluginCreator(plugin_dir=str(self.package), base_dir=str(self.package.parent),
                                dist_dir=str(self.package.parent / 'dist'), verbose=False,
                                code='export_contract', version='1', title='Пакет')
        creator.execute()
        self.zip_path = creator.get_zip_path()
        tools = PluginTools(plugin_dir=str(self.package), verbose=False)
        tools.dump_search_type(self.search_type, 'schema.spt')
        tools.dump_sobject(self.search_type, 'tools.spt')
        if self.fail:
            raise ValueError('late export failure')


def values(path):
    entries, statement = [], []
    for line in path.read_text(encoding='utf-8').splitlines(True):
        if line.startswith('#-- Start Entry --#'):
            statement = []
        elif line.startswith('#-- End Entry --#'):
            namespace = {'SearchType': SearchType}
            exec(''.join(statement), namespace)
            obj = namespace.get('insert')
            if obj is not None:
                code = obj.get_code()
                code = 'EXPORT_OBJ' if isinstance(code, str) and code.startswith('EXPORT_') else code
                entries.append([code, obj.get_value('name'), obj.get_value('amount')])
        else:
            statement.append(line)
    return entries


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    root = Path(Environment.get_tmp_dir())
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=root) as directory:
            package = Path(directory) / 'export_contract'
            package.mkdir()
            search_type = case.get('search_type', 'contract/entity')
            object_code = 'EXPORT_' + case.get('name', 'export').upper()
            code = 'MISSING_EXPORT_OBJ' if case.get('bug') == 'empty' else object_code
            (package / 'manifest.xml').write_text(
                '<manifest code="export_contract"><sobject search_type="%s" code="%s" path="objects.spt" unique="true"/></manifest>'
                % (search_type, code), encoding='utf-8')
            if case.get('fail'):
                (package / 'objects.spt').write_bytes(b'previous package')
            command = Export()
            command.package, command.search_type, command.fail = package, search_type, case.get('fail', False)
            command.code = object_code
            command.value = 'Скрипт\nreturn "hello"' if case.get('bug') != 'quotes' else 'return """точный текст"""'
            try:
                Command.execute_cmd(command)
            except ValueError:
                if not command.fail:
                    raise
                search = Search(search_type)
                search.add_filter('code', object_code)
                return dict(error='late export failure', previous=(package / 'objects.spt').read_bytes() == b'previous package',
                            zip_exists=(package.parent / 'dist/export_contract-1.zip').exists(),
                            rows=search.get_count())
            exists = (package / 'objects.spt').exists()
            result = dict(exists=exists, rows=values(package / 'objects.spt') if exists else [])
            if case.get('bug'):
                return result
            assert ['EXPORT_OBJ', command.value, 23] in values(package / 'tools.spt')
            with zipfile.ZipFile(command.zip_path) as archive:
                assert 'export_contract/manifest.xml' in archive.namelist()
                assert 'export_contract/objects.spt' in archive.namelist()
            restore = Command()
            def install():
                restore.get_transaction().set_sync(False)
                obj = Search.get_by_code(search_type, object_code)
                obj.set_value('amount', 99)
                obj.commit()
                PluginInstaller(plugin_dir=str(package), verbose=False).execute()
            restore.execute = install
            Command.execute_cmd(restore)
            result['amount'] = Search.get_by_code(search_type, object_code).get_value('amount')
            result['schema'] = 'table = CreateTable(' in (package / 'schema.spt').read_text(encoding='utf-8')
            return result
    finally:
        Environment.set_security(previous)
