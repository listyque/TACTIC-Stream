"""Unchanged plugin body, executed in original TACTIC and native vendors."""
from pathlib import Path
import tempfile

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, DbContainer
from pyasm.security import Security
from tactic.command import PluginInstaller


class Install(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        command = PluginInstaller(plugin_dir=str(self.package), verbose=False)
        command.execute()
        if self.reinstall:
            path = self.package / 'objects.spt'
            path.write_text(path.read_text(encoding='utf-8').replace('Плагин', 'Обновлённый плагин'), encoding='utf-8')
            PluginInstaller(plugin_dir=str(self.package), verbose=False).execute()
        if self.fail:
            raise ValueError('late plugin failure')


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
            package = Path(directory)
            search_type = case.get('search_type', 'contract/entity')
            (package / 'manifest.xml').write_text('''<manifest code="contract_plugin">
                <sobject search_type="%s" path="objects.spt" unique="true"/>
                <include path="include.py"/><python path="finish.py"/>
                </manifest>''' % search_type, encoding='utf-8')
            (package / 'objects.spt').write_text('''#-- Start Entry --#
insert = SearchType.create(%r)
insert.set_value('code', 'PLUGIN_OBJ')
insert.set_value('name', 'Плагин')
insert.set_value('amount', 10)
#-- End Entry --#
''' % search_type, encoding='utf-8')
            (package / 'include.py').write_text('''return '<manifest><sobject search_type="%s" path="objects.spt" unique="true"/></manifest>'
''' % search_type, encoding='utf-8')
            (package / 'finish.py').write_text('''from pyasm.search import Search
obj = Search.get_by_code(%r, 'PLUGIN_OBJ')
obj.set_value('amount', 77)
obj.commit()
''' % search_type, encoding='utf-8')
            code = 'PLUGIN_EXPLICIT' if case.get('explicit_id') else 'PLUGIN_OBJ'
            if case.get('explicit_id'):
                path = package / 'objects.spt'
                path.write_text(path.read_text(encoding='utf-8').replace(
                    "insert.set_value('code'", "insert.set_value('id', 42)\ninsert.set_value('code'"), encoding='utf-8')
                for path in (package / 'objects.spt', package / 'finish.py'):
                    path.write_text(path.read_text(encoding='utf-8').replace('PLUGIN_OBJ', code), encoding='utf-8')
            command = Install()
            command.package, command.fail = package, case.get('fail', False)
            command.reinstall = bool(case.get('explicit_id'))
            error = None
            try:
                Command.execute_cmd(command)
            except ValueError as exception:
                if not command.fail:
                    raise
                error = str(exception)
            # Check SQL effects after commit/rollback, independent of object caches.
            from pyasm.biz import Project
            from pyasm.search import SearchType
            sql = DbContainer.get(Project.get_db_resource_by_search_type(search_type))
            table = SearchType.get(search_type).get_table()
            rows = list(sql.do_query('SELECT code,name,amount FROM "%s" WHERE code=\'%s\'' % (table, code)))
            probe = PluginInstaller(plugin_dir=str(package), verbose=False)
            node = probe.xml.get_node('manifest/sobject')
            assert Path(probe.get_path_from_node(node)).samefile(package / 'objects.spt')
            probe.xml.set_attribute(node, 'code', code)
            assert len(probe.get_sobjects_by_node(node)) == len(rows)
            return dict(error=error, rows=rows)
    finally:
        Environment.set_security(previous)
