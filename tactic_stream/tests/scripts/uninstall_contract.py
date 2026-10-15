"""Unchanged uninstall body for original TACTIC and both native databases."""
from pathlib import Path
import tempfile
from unittest.mock import patch

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType, SObject
from pyasm.security import Security
from tactic.command import PluginUninstaller, PluginInstaller, PluginTools


def execute(action):
    command = Command()
    def run():
        command.get_transaction().set_sync(False)
        return action()
    command.execute = run
    return Command.execute_cmd(command)


def table_lifecycle(package, search_type):
    from pyasm.biz import Project
    from pyasm.search import DbContainer
    def setup():
        obj = SearchType.create(search_type)
        obj.set_value('id', 10042)
        obj.set_force_insert(True)
        obj.set_value('code', 'BACKUP_KEEP')
        obj.set_value('name', 'Точный backup')
        obj.set_value('amount', None, allow_none=True)
        obj.commit()
        PluginTools(plugin_dir=str(package), verbose=False).dump_search_type(search_type, 'schema.spt')
    execute(setup)
    (package / 'manifest.xml').write_text('<manifest code="table_backup"><search_type code="%s" path="schema.spt"/></manifest>' % search_type, encoding='utf-8')
    execute(lambda: PluginTools(plugin_dir=str(package), verbose=False).remove_search_type(search_type))
    resource = Project.get_db_resource_by_search_type(search_type)
    sql = DbContainer.get(resource)
    table = SearchType.get(search_type).get_table()
    absent = not sql.get_database_impl().table_exists(resource, table)
    backup = package / 'backup' / (search_type.replace('/', '_') + '.spt')
    text = backup.read_text(encoding='utf-8')
    execute(lambda: PluginInstaller(plugin_dir=str(package), verbose=False).execute())
    # Read committed SQL rows; the original identity cache retains dropped objects.
    row = sql.do_query('SELECT id,name,amount FROM "%s" WHERE code=\'BACKUP_KEEP\'' % table)[0]
    return dict(absent=absent, registry=SearchType.get(search_type).get_base_key() == search_type,
                id_preserved=row[0] == 10042, name=row[1], null=row[2] is None,
                null_literal='None, allow_none=True' in text, backup_removed=not backup.exists())


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    root = Path(Environment.get_tmp_dir())
    root.mkdir(parents=True, exist_ok=True)
    name = case.get('name', 'uninstall')
    plugin_code, code = name + '_plugin', 'UNINSTALL_' + name.upper()
    search_type = case.get('search_type', 'contract/entity')
    try:
        with tempfile.TemporaryDirectory(dir=root) as directory:
            package = Path(directory)
            if case.get('results'):
                from pyasm.biz import Project
                from pyasm.search import DbContainer
                sql = DbContainer.get(Project.get_db_resource_by_search_type(search_type))
                first = sql.do_query('SELECT 1')
                sql.do_query('SELECT 2')
                return dict(result_preserved=first == [(1,)])
            if case.get('table'):
                return table_lifecycle(package, search_type)
            manifest = ('<manifest code="%s"><data><code>%s</code></data>'
                '<sobject search_type="%s" code="%s"/>'
                '<include path="include.py"/><python path="install.py" undo_path="undo.py"/></manifest>') % (
                    plugin_code, plugin_code, search_type, code)
            if case.get('pipeline'):
                manifest = manifest.replace('</manifest>', '<sobject search_type="sthpw/pipeline" code="original/%s"/></manifest>' % name)
            (package / 'manifest.xml').write_text(manifest, encoding='utf-8')
            (package / 'include.py').write_text(
                "return '<manifest><sobject search_type=\"%s\" code=\"%s_INCLUDED\"/></manifest>'" % (search_type, code), encoding='utf-8')
            (package / 'undo.py').write_text('from pyasm.biz import ProjectSetting\n'
                'ProjectSetting.create(%r, "undo called")\n' % name, encoding='utf-8')
            def setup():
                for object_code in (code, code + '_INCLUDED'):
                    obj = SearchType.create(search_type)
                    obj.set_value('code', object_code)
                    obj.set_value('name', 'Удаление')
                    obj.commit()
                plugin = SearchType.create('config/plugin')
                plugin.set_value('code', plugin_code)
                plugin.set_value('manifest', manifest)
                plugin.commit()
                content = SearchType.create('config/plugin_content')
                content.set_value('code', 'CONTENT_' + name.upper())
                content.set_value('plugin_code', plugin_code)
                content.set_value('search_type', search_type)
                content.set_value('search_code', code)
                content.commit()
                if case.get('pipeline'):
                    from pyasm.biz import Project
                    pipeline = SearchType.create('sthpw/pipeline')
                    pipeline.set_value('code', Project.get_project_code() + '/' + name)
                    pipeline.set_value('pipeline', '<pipeline/>')
                    pipeline.set_value('project_code', Project.get_project_code())
                    pipeline.commit(triggers=False)
            execute(setup)
            delete = SObject.delete
            def guarded(self, *args, **kwargs):
                if case.get('bug') == 'delete' and self.get_code() == code:
                    raise ValueError('delete refused')
                return delete(self, *args, **kwargs)
            def uninstall():
                PluginUninstaller(plugin_dir=str(package), verbose=False).execute()
                if case.get('fail'):
                    raise ValueError('late uninstall failure')
            error = None
            try:
                with patch.object(SObject, 'delete', guarded):
                    execute(uninstall)
            except ValueError as exception:
                if not case.get('fail') and not case.get('bug'):
                    raise
                error = str(exception)
            search = Search(search_type)
            search.add_filters('code', [code, code + '_INCLUDED'])
            content = Search('config/plugin_content')
            content.add_filter('plugin_code', plugin_code)
            plugin = Search('config/plugin')
            plugin.add_filter('code', plugin_code)
            from pyasm.biz import ProjectSetting
            result = dict(error=error, rows=search.get_count(), contents=content.get_count(),
                        plugin=plugin.get_count() != 0,
                        undo=ProjectSetting.get_value_by_key(name), files=(package / 'manifest.xml').exists())
            if case.get('pipeline'):
                from pyasm.biz import Project
                pipeline = Search('sthpw/pipeline')
                pipeline.add_filter('code', Project.get_project_code() + '/' + name)
                result['pipeline'] = pipeline.get_count() != 0
            return result
    finally:
        Environment.set_security(previous)
