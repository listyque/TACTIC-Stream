"""One isolated directory/ZIP/template lifecycle on both native vendors."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring

from pyasm.common import Config, Environment
from pyasm.common.errors import SecurityException
from pyasm.command import Command, Trigger
from pyasm.search import Search, SearchType, DbContainer, WidgetDbConfig, SObject
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.command import PluginCreator, PluginInstaller, PluginUninstaller, ProjectTemplateInstallerCmd, ProjectTemplateCreatorCmd, CreateProjectCmd
from tactic_stream.server.api import Api


def entry(code):
    return '#-- Start Entry --#\n' + code + '\n#-- End Entry --#\n'


def exercise(store, prefix):
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    ticket = dict(ticket=token, project='admin', language='python')
    project_code = prefix + '_ok'
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
        dict(project_code=project_code, project_title='Plugin test', project_stype=['asset'])))
    ticket['project'] = project_code
    api.dispatch('add_column_to_search_type', (ticket, project_code + '/asset', 'amount', 'integer'))
    with request_context(RequestContext(store, 'admin', project_code)):
        api.auth.bind_security('admin', token)
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        try:
            import plugin_contract
            comparison = [plugin_contract.run(dict(search_type=project_code + '/asset', fail=fail))
                          for fail in (True, False)]
            explicit = plugin_contract.run(dict(search_type=project_code + '/asset', explicit_id=True))
            assert explicit == dict(error=None, rows=[('PLUGIN_EXPLICIT', 'Обновлённый плагин', 77)])
            import config_contract
            comparison.extend(config_contract.run(dict(search_type=project_code + '/asset', **case)) for case in (
                dict(name='failure', fail=True), dict(name='config'), dict(name='warm', warm_cache=True), dict(name='move', bug='move')))
            assert comparison[-3]['setting'] == ['one', 'two']
            assert comparison[-2]['trigger'] == ['called']
            assert comparison[-1]['move'] == dict(error=None, names=['amount', 'name'])
            comparison.extend(config_contract.run(dict(search_type=project_code + '/asset', **case)) for case in (
                dict(name='extra_failure', extra_config=True, fail=True), dict(name='extra', extra_config=True)))
            assert comparison[-1]['extra_config']['process_rows'] == ['first', 'second']
            comparison.append(config_contract.run(dict(search_type=project_code + '/asset',
                name='bad_drop', extra_config=True, bug='property_drop')))
            assert comparison[-1] == dict(error='SqlException', widget_rows=0)
            import export_contract
            comparison.extend(export_contract.run(dict(search_type=project_code + '/asset', **case)) for case in (
                dict(name='export'), dict(name='export_quotes', bug='quotes'),
                dict(name='export_empty', bug='empty'), dict(name='export_failure', fail=True)))
            assert comparison[-1] == dict(error='late export failure', previous=True, zip_exists=False, rows=0)
            import template_check_contract
            comparison.extend(template_check_contract.run(dict(name='check_' + str(index), **case))
                              for index, case in enumerate(({}, {'bug': 'type'}, {'bug': 'prefix'}, {'bug': 'namespace'})))
            import uninstall_contract
            comparison.extend(uninstall_contract.run(dict(search_type=project_code + '/asset', **case)) for case in (
                dict(name='uninstall'), dict(name='uninstall_failure', fail=True),
                dict(name='uninstall_delete', bug='delete'), dict(name='uninstall_pipeline', pipeline=True),
                dict(name='uninstall_table', table=True)))
            assert comparison[-1]['id_preserved'] and comparison[-1]['backup_removed']
        finally:
            sys.path.pop(0)
        from pyasm.biz import ProjectSetting, Project
        from pyasm.common.errors import UnsupportedContract
        from pyasm.common import Xml
        def execute(action):
            cmd = Command()
            def run():
                cmd.get_transaction().set_sync(False)
                return action()
            cmd.execute = run
            return Command.execute_cmd(cmd)
        # Original upgrade permits the same key scoped to different search types.
        execute(lambda: [ProjectSetting.create('scoped', value, search_type=stype)
                         for stype, value in (('first/type', 'first'), ('second/type', 'second'))])
        assert ProjectSetting.get_value_by_key('scoped', 'first/type') == 'first'
        assert ProjectSetting.get_value_by_key('scoped', 'second/type') == 'second'
        widget = WidgetDbConfig.get_by_search_type(project_code + '/asset', 'contract_config')
        with unittest.TestCase().assertRaises(UnsupportedContract):
            widget.get_display_widget('name')
        copied = widget.import_element_node('name')
        assert copied is not widget.get_element_node('name') and Xml.get_parent(copied) is None
        assert widget.get_element_names() == ['name', 'amount']
        # Merged lower priority defaults cannot replace the first fallback or action.
        configs = []
        for priority, body in ((10, '<element name="name"><action class="custom.Action"/></element>'),
                               (5, '<element name="name" title="middle"><display class="custom.Default"/></element>'),
                               (None, '<element name="name" title="last"/>')):
            config = WidgetDbConfig()
            for key, value in dict(view='table', search_type=project_code + '/asset', priority=priority,
                                   config='<config><table>' + body + '</table></config>').items():
                config.set_value(key, value, allow_none=True)
            config._init()
            configs.append(config)
        merged = WidgetDbConfig.merge_configs(configs)
        assert merged.get_element_title('name') == 'middle'
        assert merged.get_display_handler('name') == 'custom.Default'
        assert merged.get_xml().get_value('config/table/element/action/@class') == 'custom.Action'
        def attribute_view():
            config = WidgetDbConfig.create(project_code + '/asset', 'table@user')
            config.append_display_element('name', 'custom.Cell')
            config.commit_config()
        execute(attribute_view)
        assert WidgetDbConfig.get_by_search_type(project_code + '/asset', 'table@user').has_view()
        from pyasm.common.lxml_wrapper import XmlException
        with unittest.TestCase().assertRaises(XmlException):
            execute(lambda: WidgetDbConfig.create(project_code + '/asset', 'broken', '<config>'))
        assert WidgetDbConfig.get_by_search_type(project_code + '/asset', 'broken') is None
        with unittest.TestCase().assertRaises(UnsupportedContract):
            execute(lambda: WidgetDbConfig.create(project_code + '/asset', 'mako', '<config><mako>${value}</mako></config>'))
        # CustomProperty.delete(log=True) drops the actual target column, with
        # schema/row rollback together and authorization before the first DDL.
        from pyasm.command import ColumnAddCmd
        from pyasm.biz import CustomProperty
        def add_property():
            ColumnAddCmd(project_code + '/asset', 'temporary_property', 'integer').execute()
            prop = SearchType.create('config/custom_property')
            for name, value in dict(code='DROP_PROPERTY', search_type=project_code + '/asset', name='temporary_property').items():
                prop.set_value(name, value)
            prop.commit()
        execute(add_property)
        def drop_property(fail=False):
            prop = Search.get_by_code('config/custom_property', 'DROP_PROPERTY')
            assert isinstance(prop, CustomProperty)
            prop.delete(log=True)
            assert not SearchType.column_exists(project_code + '/asset', 'temporary_property')
            if fail:
                raise ValueError('discard column drop')
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            with unittest.TestCase().assertRaises(SecurityException):
                execute(drop_property)
        assert SearchType.column_exists(project_code + '/asset', 'temporary_property')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'discard column drop'):
            execute(lambda: drop_property(True))
        assert SearchType.column_exists(project_code + '/asset', 'temporary_property')
        assert Search.get_by_code('config/custom_property', 'DROP_PROPERTY') is not None
        execute(drop_property)
        assert Search.get_by_code('config/custom_property', 'DROP_PROPERTY') is None
        def discard_config():
            current = WidgetDbConfig.get_by_search_type(project_code + '/asset', 'contract_config')
            current.remove_node('amount')
            current.commit_config()
            assert WidgetDbConfig.get_by_search_type(project_code + '/asset', 'contract_config').get_element_names() == ['name']
            raise ValueError('discard config')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'discard config'):
            execute(discard_config)
        assert WidgetDbConfig.get_by_search_type(project_code + '/asset', 'contract_config').get_element_names() == ['name', 'amount']
        event = 'config_contract_contract_warm'
        def discard_trigger():
            Search.get_by_code('config/trigger', 'TRIGGER_contract_warm').delete()
            assert Trigger.call(None, event, {'setting_key': 'after_delete'}) == []
            raise ValueError('discard trigger')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'discard trigger'):
            execute(discard_trigger)
        assert len(execute(lambda: Trigger.call(None, event, {'setting_key': 'after_rollback'}))) == 1
        package = store.data_dir / 'package_input'
        package.mkdir(parents=True)
        search_type = 'contract/plugin_item'
        registry = entry("insert = SearchType.create('sthpw/search_object')\n"
            "insert.set_value('code', %r)\ninsert.set_value('search_type', %r)\n"
            "insert.set_value('namespace', 'contract')\ninsert.set_value('database', '{project}')\n"
            "insert.set_value('table_name', 'plugin_item')\ninsert.set_value('class_name', 'pyasm.search.SObject')\n"
            "insert.set_value('schema', 'public')" % (search_type, search_type))
        ddl = entry("table = CreateTable()\ntable.set_table('plugin_item')\n"
                    "table.add('id', 'serial', primary_key=True)\ntable.add('code', 'varchar', length=256)\n"
                    "table.add('name', 'text')\ntable.add('amount', 'integer')\n"
                    "table.add('timestamp', 'timestamp')\ntable.add('s_status', 'varchar', length=256)")
        payload = entry("insert = SearchType.create(%r)\ninsert.set_value('id', 100)\n"
                        "insert.set_value('code', 'PACKAGED')\ninsert.set_value('name', 'Пакет')\n"
                        "insert.set_value('amount', 17)" % search_type)
        (package / 'manifest.xml').write_text('''<manifest code="native_plugin"><!-- original package comment -->
            <data><code>native_plugin</code><version>1.0</version></data>
            <search_type code="contract/plugin_item"/>
            <sobject search_type="contract/plugin_item" seq_max="150" unique="true" path="rows.spt"/>
            <sobject search_type="sthpw/pipeline" unique="true"/>
            </manifest>''', encoding='utf-8')
        (package / 'contract_plugin_item.spt').write_text(registry + ddl, encoding='utf-8')
        (package / 'rows.spt').write_text(payload, encoding='utf-8')
        (package / 'sthpw_pipeline.spt').write_text(entry("insert = SearchType.create('sthpw/pipeline')\n"
            "insert.set_value('code', 'template/package_pipe')\n"
            "insert.set_value('pipeline', '<pipeline><process name=\"start\" type=\"manual\"/></pipeline>')"), encoding='utf-8')
        archive = store.data_dir / 'native_plugin.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for path in package.iterdir():
                output.write(path, 'native_plugin/' + path.name)
        arguments = dict(zip_path=str(archive), register=True, verbose=False)
        result = api.dispatch('execute_cmd', (ticket, 'tactic.command.PluginInstaller', arguments))
        assert result['status'] == 'OK'
        assert Search.get_by_code('config/plugin', 'native_plugin').get_value('version') == '1.0'
        destination = Path(Environment.get_plugin_dir()) / 'native_plugin-1.0'
        assert (destination / 'manifest.xml').exists()
        # Reinstallation with an explicit imported ID must update, not force insert.
        api.dispatch('execute_cmd', (ticket, 'tactic.command.PluginInstaller', arguments))
        pipeline = Search('sthpw/pipeline')
        pipeline.add_filter('code', project_code + '/package_pipe')
        assert pipeline.get_count() == 1
        assert Search.get_by_code('sthpw/pipeline', 'template/package_pipe') is None
        search = Search(search_type)
        search.add_filter('code', 'PACKAGED')
        assert search.get_count() == 1
        assert search.get_sobject().get_value('name') == 'Пакет'
        saved = {path.relative_to(destination): path.read_bytes() for path in destination.rglob('*') if path.is_file()}
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            # A cached/Sudo administrator flag cannot grant package execution.
            with unittest.TestCase().assertRaises(SecurityException):
                PluginInstaller(**arguments).execute()
        assert {path.relative_to(destination): path.read_bytes() for path in destination.rglob('*') if path.is_file()} == saved
        # A broken later payload restores the replaced directory and every DB write.
        with zipfile.ZipFile(archive, 'a') as output:
            output.writestr('native_plugin/broken.spt', entry("raise ValueError('broken package payload')"))
        with zipfile.ZipFile(archive) as old:
            content = {name: old.read(name) for name in old.namelist()}
        content['native_plugin/manifest.xml'] = content['native_plugin/manifest.xml'].replace(
            b'</manifest>', b'<sobject path="broken.spt"/></manifest>')
        with zipfile.ZipFile(archive, 'w') as output:
            for name, data in content.items():
                output.writestr(name, data)
        cmd = Command()
        def install_bad():
            cmd.get_transaction().set_sync(False)
            PluginInstaller(**arguments).execute()
        cmd.execute = install_bad
        with unittest.TestCase().assertRaisesRegex(ValueError, 'broken package payload'):
            Command.execute_cmd(cmd)
        assert {path.relative_to(destination): path.read_bytes() for path in destination.rglob('*') if path.is_file()} == saved
        assert Search(search_type).get_count() == 1
        # No ID collision after explicit ID import, on either vendor.
        insert = Command()
        def insert_next():
            insert.get_transaction().set_sync(False)
            obj = SearchType.create(search_type)
            obj.set_value('code', 'NEXT')
            obj.commit()
            return obj.get_id()
        insert.execute = insert_next
        assert Command.execute_cmd(insert) > 100
        malicious = store.data_dir / 'malicious.zip'
        with zipfile.ZipFile(malicious, 'w') as output:
            output.writestr('../escape.txt', 'escape')
            output.writestr('manifest.xml', '<manifest code="unsafe"/>')
        with unittest.TestCase().assertRaisesRegex(Exception, 'Unsafe ZIP member'):
            PluginInstaller(zip_path=str(malicious))
        assert not (store.data_dir.parent / 'escape.txt').exists()
        # Native template installer shares the same SPT importer and database owner.
        template = store.data_dir / 'template_input'
        template.mkdir()
        (template / 'manifest.xml').write_text('''<manifest code="base_template">
            <sobject search_type="sthpw/project" unique="true"/>
            <sobject search_type="config/custom_script" unique="true"/>
            </manifest>''', encoding='utf-8')
        (template / 'sthpw_project.spt').write_text(entry("insert = SearchType.create('sthpw/project')\n"
            "insert.set_value('code', 'base_template')\ninsert.set_value('type', 'base_template')\n"
            "insert.set_value('database', 'old_template_db')"), encoding='utf-8')
        (template / 'config_custom_script.spt').write_text(entry("insert = SearchType.create('config/custom_script')\n"
            "insert.set_value('folder', 'template')\ninsert.set_value('title', 'hello')\n"
            "insert.set_value('script', 'return 42')"), encoding='utf-8')
        target = prefix + '_tpl'
        template_cmd = Command()
        def install_template():
            template_cmd.get_transaction().set_sync(False)
            ProjectTemplateInstallerCmd(path=str(template), project_code=target, verbose=False).execute()
        template_cmd.execute = install_template
        Command.execute_cmd(template_cmd)
        from pyasm.biz import Project
        assert Project.get().get_code() == target
        assert Project.get().get_database_name() == target
        assert WidgetDbConfig.get_by_search_type(project_code + '/asset', 'contract_config') is None
        assert execute(lambda: Trigger.call(None, event, {'setting_key': 'other_project'})) == []
        assert ProjectSetting.get_value_by_key('other_project') == ''
        assert Search('config/custom_script').get_sobject().get_value('script') == 'return 42'
        template_zip = store.data_dir / 'template.zip'
        with zipfile.ZipFile(template_zip, 'w') as output:
            for path in template.iterdir():
                output.write(path, 'base_template/' + path.name)
        repeat = Command()
        def repeat_template():
            repeat.get_transaction().set_sync(False)
            from tactic.command import CopyProjectFromTemplateCmd
            CopyProjectFromTemplateCmd(path=str(template_zip), project_code=target, new_project=False, verbose=False).execute()
        repeat.execute = repeat_template
        Command.execute_cmd(repeat)
        assert Search('config/custom_script').get_count() == 1
        # Failure after new project DB creation removes only its owned resources.
        with (template / 'config_custom_script.spt').open('a', encoding='utf-8') as output:
            output.write(entry("raise ValueError('bad template')"))
        failed = prefix + '_bad'
        template_cmd = Command()
        template_cmd.execute = lambda: ProjectTemplateInstallerCmd(path=str(template), project_code=failed, verbose=False).execute()
        with unittest.TestCase().assertRaisesRegex(ValueError, 'bad template'):
            Command.execute_cmd(template_cmd)
        assert Search.get_by_code('sthpw/project', failed) is None
        resource = store.get_db_resource(failed)
        assert not resource.get_database_impl().database_exists(resource)
        # Export an actual source type, then install its schema/data/config into
        # the other existing project. Both vendors execute this same lifecycle.
        Project.set_project(project_code)
        source_sql = DbContainer.get(Project.get().get_project_db_resource())
        def required_column():
            source_sql.do_update('ALTER TABLE asset ADD COLUMN required_value integer NOT NULL DEFAULT 0')
            source_sql.clear_table_cache()
            obj = Search.get_by_code(project_code + '/asset', 'EXPORT_EXPORT')
            obj.set_value('required_value', 7)
            obj.commit()
            assert source_sql.get_value("SELECT required_value FROM asset WHERE code='EXPORT_EXPORT'") == 7, obj.get_data()
            script = SearchType.create('config/custom_script')
            for name, value in dict(code='EXPORT_SCRIPT', folder='export.nested', title='Exact script',
                                   script='return """Текст\nбез изменений"""').items():
                script.set_value(name, value)
            script.commit()
        execute(required_column)
        export_dir = store.data_dir / 'plugins/export/package'
        export_dir.mkdir(parents=True)
        manifest = ('<manifest code="export/package" version="1">'
            '<search_type code="%s/asset" path="schema.spt"/>'
            '<sobject search_type="%s/asset" code="EXPORT_EXPORT" path="objects.spt" include_id="true" unique="true"/>'
            '<sobject search_type="%s/asset" code="MISSING" path="empty.spt"/>'
            '<sobject search_type="sthpw/pipeline" code="%s/package_pipe" path="pipeline.spt" replace_variable="true"/>'
            '<sobject search_type="config/custom_script" relative_dir_column="folder" path="scripts"/>'
            '<include path="include.py"/><python path="finish.py"/></manifest>') % (project_code, project_code, project_code, project_code)
        (export_dir / 'manifest.xml').write_text(manifest, encoding='utf-8')
        (export_dir / 'include.py').write_text("return '<manifest><sobject search_type=\"config/prod_setting\" path=\"settings.spt\"/></manifest>'", encoding='utf-8')
        (export_dir / 'finish.py').write_text('return None', encoding='utf-8')
        kwargs = dict(plugin_dir=str(export_dir), base_dir=str(store.data_dir / 'plugins'), verbose=False, register=True)
        creator = PluginCreator(**kwargs)
        execute(creator.execute)
        assert creator.version == '1'
        archive_path = Path(creator.get_zip_path())
        assert archive_path.name == 'package-1.zip'
        assert Search.get_by_code('config/plugin', 'export/package').get_value('manifest') == creator.manifest
        assert (export_dir / 'empty.spt').read_bytes() == b''
        assert '$PROJECT/package_pipe' in (export_dir / 'pipeline.spt').read_text(encoding='utf-8')
        assert any((export_dir / 'scripts').rglob('*.spt'))
        before = {p.relative_to(export_dir): p.read_bytes() for p in export_dir.rglob('*') if p.is_file()}
        zip_before = archive_path.read_bytes()
        with unittest.TestCase().assertRaisesRegex(Exception, 'already existed'):
            execute(PluginCreator(**kwargs).execute)
        assert before == {p.relative_to(export_dir): p.read_bytes() for p in export_dir.rglob('*') if p.is_file()}
        assert archive_path.read_bytes() == zip_before
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            with unittest.TestCase().assertRaises(SecurityException):
                execute(PluginCreator(**kwargs).execute)
        assert archive_path.read_bytes() == zip_before
        # Bound paths and unsupported nodes fail, restoring any earlier output.
        for bad in ('<sobject search_type="%s/asset" path="../escape.spt"/>' % project_code, '<theme/>'):
            bad_manifest = '<manifest code="bad_export">' + bad + '</manifest>'
            bad_dir = export_dir.parent / 'bad'
            with unittest.TestCase().assertRaises(Exception):
                execute(PluginCreator(manifest=bad_manifest, plugin_dir=str(bad_dir), verbose=False).execute)
            assert not bad_dir.exists() and not (bad_dir.parent / 'escape.spt').exists()
        Project.set_project(target)
        execute(PluginInstaller(zip_path=str(archive_path), base_dir=str(store.data_dir / 'installed'), register=True, verbose=False).execute)
        restored = Search.get_by_code(project_code + '/asset', 'EXPORT_EXPORT')
        assert restored.get_value('name') == 'Скрипт\nreturn "hello"' and restored.get_value('amount') == 23
        assert restored.get_value('required_value') == 7
        target_sql = DbContainer.get(Project.get().get_project_db_resource())
        constraints = target_sql.get_database_impl().get_constraints(target_sql.get_db_resource(), 'asset')
        assert any(c['mode'] == 'UNIQUE' and c['columns'] == ['code'] for c in constraints)
        assert target_sql.get_column_info('asset', 'required_value')['nullable'] is False
        assert Search.get_by_code('sthpw/pipeline', target + '/package_pipe') is not None
        assert Search.get_by_code('config/custom_script', 'EXPORT_SCRIPT').get_value('script') == 'return """Текст\nбез изменений"""'
        assert ProjectSetting.get_value_by_key('scoped', 'first/type') == 'first'
        # Uninstall keeps shared definitions and backs up rows outside manifest
        # selections. Reinstall restores their identities and repairs the sequence.
        installed = store.data_dir / 'installed/export/package-1'
        def keep_row():
            obj = SearchType.create(project_code + '/asset')
            for name, value in dict(id=15000, code='KEEP', name='Сохранить', required_value=3).items():
                obj.set_value(name, value)
            obj.set_value('amount', None, allow_none=True)
            obj.set_force_insert(True)
            obj.commit()
        execute(keep_row)
        before = {p.relative_to(installed): p.read_bytes() for p in installed.rglob('*') if p.is_file()}
        def uninstall_fail():
            PluginUninstaller(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False).execute()
            assert not target_sql.get_database_impl().table_exists(target_sql.get_db_resource(), 'asset')
            raise ValueError('late uninstall rollback')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'late uninstall rollback'):
            execute(uninstall_fail)
        assert Search.get_by_code(project_code + '/asset', 'KEEP').get_id() == 15000
        assert Search.get_by_code('config/plugin', 'export/package') is not None
        assert before == {p.relative_to(installed): p.read_bytes() for p in installed.rglob('*') if p.is_file()}
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            with unittest.TestCase().assertRaises(SecurityException):
                execute(PluginUninstaller(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False).execute)
        # A dependent view refuses DROP without CASCADE. Its error restores
        # already deleted manifest objects/settings and leaves no backup behind.
        execute(lambda: target_sql.do_update('CREATE VIEW uninstall_dependency AS SELECT code FROM asset'))
        from pyasm.search import SqlException
        with unittest.TestCase().assertRaises(SqlException):
            execute(PluginUninstaller(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False).execute)
        assert Search.get_by_code('config/plugin', 'export/package') is not None
        assert before == {p.relative_to(installed): p.read_bytes() for p in installed.rglob('*') if p.is_file()}
        execute(lambda: target_sql.do_update('DROP VIEW uninstall_dependency'))
        result = api.dispatch('execute_cmd', (dict(ticket=token, project=target, language='python'),
            'tactic.command.PluginUninstaller', dict(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False)))
        assert result['status'] == 'OK'
        # API dispatch owns a separate request Container; the enclosing test
        # request must discard its earlier identity/metadata caches for reads.
        from pyasm.search import SObject
        target_sql.clear_table_cache()
        for stype in ('config/plugin', 'sthpw/pipeline', project_code + '/asset'):
            SObject.get_cache_dict(search_type=stype).clear()
        assert Search.get_by_code('config/plugin', 'export/package') is None
        assert Search.get_by_code('sthpw/pipeline', target + '/package_pipe') is None
        assert not target_sql.get_database_impl().table_exists(target_sql.get_db_resource(), 'asset')
        assert SearchType.get(project_code + '/asset').get_table() == 'asset'
        backup = installed / 'backup' / (project_code + '_asset.spt')
        assert backup.exists() and '15000' in backup.read_text(encoding='utf-8')
        execute(PluginInstaller(plugin_dir=str(installed), base_dir=str(store.data_dir / 'installed'), register=True, verbose=False).execute)
        assert not backup.exists()
        keep = Search.get_by_code(project_code + '/asset', 'KEEP')
        assert keep.get_id() == 15000 and keep.get_value('amount', auto_convert=False) is None
        def next_row():
            obj = SearchType.create(project_code + '/asset')
            obj.set_value('code', 'NEXT_AFTER_REINSTALL')
            obj.set_value('required_value', 4)
            obj.commit()
            return obj.get_id()
        assert execute(next_row) > 15000
        from tactic.command import PluginReloader
        def reload_fail():
            PluginReloader(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False).execute()
            raise ValueError('reload rollback')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'reload rollback'):
            execute(reload_fail)
        assert Search.get_by_code(project_code + '/asset', 'KEEP').get_id() == 15000
        assert Search.get_by_code('config/plugin', 'export/package') is not None
        execute(PluginReloader(code='export/package', base_dir=str(store.data_dir / 'installed'), verbose=False).execute)
        assert not backup.exists()
        assert Search.get_by_code('config/plugin', 'export/package') is not None
        assert Search.get_by_code(project_code + '/asset', 'KEEP').get_id() == 15000
        assert Search.get_by_code(project_code + '/asset', 'NEXT_AFTER_REINSTALL') is not None
        # Nested packages and real Python undo/file effects share one Command.
        nested = store.data_dir / 'nested_input'
        child = nested / 'child'
        child.mkdir(parents=True)
        (nested / 'manifest.xml').write_text('<manifest code="nested_root"><plugin code="child"/>'
            '<python path="install.py" undo_path="undo.py"/></manifest>', encoding='utf-8')
        (nested / 'install.py').write_text('return None', encoding='utf-8')
        marker = nested / 'marker.txt'
        marker.write_bytes(b'before')
        (nested / 'undo.py').write_text('from pathlib import Path\nfrom pyasm.search import FileUndo\n'
            'path = Path(%r)\nFileUndo.remove(str(path))\nFileUndo.create(str(path), io_action=False)\n'
            'path.write_bytes(b"after")\n' % str(marker), encoding='utf-8')
        (child / 'manifest.xml').write_text('<manifest code="nested_child"><sobject search_type="config/custom_script" code="NESTED_OBJECT" path="objects.spt" unique="true"/></manifest>', encoding='utf-8')
        (child / 'objects.spt').write_text(entry("insert = SearchType.create('config/custom_script')\n"
            "insert.set_value('code','NESTED_OBJECT')\ninsert.set_value('folder','native/nested')\n"
            "insert.set_value('title','Nested')\ninsert.set_value('script','return None')"), encoding='utf-8')
        execute(PluginInstaller(plugin_dir=str(nested), register=True, verbose=False).execute)
        def nested_failure():
            PluginUninstaller(plugin_dir=str(nested), verbose=False).execute()
            raise ValueError('nested rollback')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'nested rollback'):
            execute(nested_failure)
        assert marker.read_bytes() == b'before'
        assert Search.get_by_code('config/custom_script', 'NESTED_OBJECT') is not None
        assert Search.get_by_code('config/plugin', 'nested_child') is not None
        execute(PluginUninstaller(plugin_dir=str(nested), verbose=False).execute)
        assert marker.read_bytes() == b'after'
        assert Search.get_by_code('config/custom_script', 'NESTED_OBJECT') is None
        assert Search.get_by_code('config/plugin', 'nested_child') is None
        assert Search.get_by_code('config/plugin', 'nested_root') is None
        cycle = nested / 'cycle'
        cycle.mkdir()
        (cycle / 'manifest.xml').write_text('<manifest code="cycle"><plugin code="."/></manifest>', encoding='utf-8')
        with unittest.TestCase().assertRaisesRegex(Exception, 'Recursive plugin uninstall'):
            execute(PluginUninstaller(plugin_dir=str(cycle), verbose=False).execute)
        include_cycle = nested / 'include_cycle'
        include_cycle.mkdir()
        (include_cycle / 'manifest.xml').write_text('<manifest code="cycle"><include path="cycle.py"/></manifest>', encoding='utf-8')
        (include_cycle / 'cycle.py').write_text('return \'<manifest><include path="cycle.py"/></manifest>\'', encoding='utf-8')
        with unittest.TestCase().assertRaisesRegex(Exception, 'Recursive manifest include'):
            execute(PluginUninstaller(plugin_dir=str(include_cycle), verbose=False).execute)
        # Whole-project template: original command + existing SPT importer, no
        # asset payload. A different project_type must not hide its own types.
        source, copied = prefix + '_exp', prefix + '_copy'
        execute(CreateProjectCmd(project_code=source, project_title='Template export', project_stype=['asset']).execute)
        Project.set_project(source)
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        try:
            import template_export_contract
            comparison.extend(template_export_contract.run(dict(search_type=source + '/asset', **case))
                              for case in ({}, {'namespace': True}, {'fail': True}))
        finally:
            sys.path.pop(0)
        assert comparison[-1] == dict(previous=True, zip_exists=False)
        source_sql = DbContainer.get(Project.get().get_project_db_resource())
        impl = source_sql.get_database_impl()
        script_table = SearchType.get('config/custom_script').get_table()
        def template_metadata():
            payload = SearchType.create(source + '/asset')
            payload.set_value('code', 'PAYLOAD_NOT_IN_TEMPLATE')
            payload.commit(triggers=False)
            config = WidgetDbConfig.create(source + '/asset', 'template_view')
            config.append_display_element('code', 'custom.Cell')
            config.commit_config()
            ProjectSetting.create('template_setting', 'Точное значение')
            for stype, values in (
                ('sthpw/pipeline', dict(code=source + '/asset', project_code=source,
                    search_type=source + '/asset', pipeline='<pipeline><process name="start" type="manual"/></pipeline>')),
                ('sthpw/login_group', dict(code=source + '/artists', login_group=source + '/artists',
                    project_code=source, access_rules='<rules><rule group="sobject" project="%s" default="allow"/></rules>' % source)),
                ('sthpw/notification', dict(code='TEMPLATE_NOTICE', project_code=source,
                    event='template_notice', subject='Тема письма', message='Текст письма'))):
                # SearchTypeCreatorCmd already creates the default asset pipeline.
                obj = Search.get_by_code(stype, values['code']) or SearchType.create(stype)
                for name, value in values.items():
                    obj.set_value(name, value)
                obj.commit(triggers=False)
            # Keep a floor above actual rows, as after deleting a high ID.
            impl.ensure_table_sequence(source_sql, script_table, 900)
        execute(template_metadata)
        floor = impl.get_table_sequence_value(source_sql, script_table)
        assert floor == 900
        notice = Trigger.get_notifications_by_event('template_notice')[0]
        def change_notice():
            notice.set_value('event', 'template_notice_changed')
            notice.commit(triggers=False)
        execute(change_notice)
        assert Trigger.get_notifications_by_event('template_notice') == []
        assert len(Trigger.get_notifications_by_event('template_notice_changed')) == 1
        base = store.data_dir / 'exported_templates'
        creator = ProjectTemplateCreatorCmd(project_code=source, base_dir=str(base), version='1')
        execute(creator.execute)
        whole_zip = Path(creator.get_zip_path())
        assert impl.get_table_sequence_value(source_sql, script_table) == floor
        with zipfile.ZipFile(whole_zip) as output:
            assert any(name.endswith('/manifest.xml') for name in output.namelist())
        previous_files = {p.relative_to(base): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        previous_zip = whole_zip.read_bytes()
        def failed_export():
            creator.execute()
            raise ValueError('late whole export')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'late whole export'):
            execute(failed_export)
        assert previous_files == {p.relative_to(base): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        assert whole_zip.read_bytes() == previous_zip
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            with unittest.TestCase().assertRaises(SecurityException):
                execute(creator.execute)
        execute(ProjectTemplateInstallerCmd(path=str(whole_zip), project_code=copied, verbose=False).execute)
        assert Project.get().get_database_name() == copied
        assert Search(source + '/asset').get_count() == 0
        assert Search.get_by_code('config/custom_script', 'TEMPLATE_SCRIPT').get_value('script') == 'return 42\n# Точный текст'
        assert WidgetDbConfig.get_by_search_type(source + '/asset', 'template_view').get_element_names() == ['code']
        assert ProjectSetting.get_value_by_key('template_setting') == 'Точное значение'
        group = Search.get_by_code('sthpw/login_group', copied + '/artists')
        assert group.get_value('project_code') == copied
        assert group.get_xml_value('access_rules').get_value('rules/rule/@project') == copied
        assert Search.get_by_code('sthpw/pipeline', copied + '/asset') is not None
        notices = Search('sthpw/notification')
        notices.add_filter('project_code', copied)
        notices.add_filter('event', 'template_notice_changed')
        restored = notices.get_sobject()
        assert restored.get_value('subject') == 'Тема письма' and restored.get_value('event') == 'template_notice_changed'
        copied_sql = DbContainer.get(Project.get().get_project_db_resource())
        copied_impl = copied_sql.get_database_impl()
        assert copied_impl.get_table_sequence_value(copied_sql, script_table) == floor
        def discard_floor():
            copied_impl.ensure_table_sequence(copied_sql, script_table, 5000)
            raise ValueError('discard sequence floor')
        with unittest.TestCase().assertRaisesRegex(ValueError, 'discard sequence floor'):
            execute(discard_floor)
        assert copied_impl.get_table_sequence_value(copied_sql, script_table) == floor
        def next_script():
            obj = SearchType.create('config/custom_script')
            obj.set_value('code', 'AFTER_TEMPLATE')
            obj.commit(triggers=False)
            return obj.get_id()
        assert execute(next_script) > floor
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        try:
            import config_api_contract
            comparison.extend(config_api_contract.run(case) for case in (
                {}, {'bug': 'personal'}, {'bug': 'separator'}, {'bug': 'attribute'},
                {'bug': 'subscription', 'other_project': source}))
            assert comparison[-2] == dict(error=None, names=['second', 'first'])
            # Late failure restores user settings, config/subscription/interaction,
            # system journal and this ticket's removed upload directory together.
            Project.set_project(source)
            upload = Path(Environment.get_upload_dir())
            upload.mkdir(parents=True, exist_ok=True)
            (upload / 'keep.txt').write_bytes(b'keep')
            kinds = ('sthpw/wdg_settings', 'sthpw/subscription', 'sthpw/interaction',
                     'config/widget_config', 'sthpw/transaction_log', 'sthpw/sobject_log')
            before = [Search(kind).get_count() for kind in kinds]
            with unittest.TestCase().assertRaisesRegex(ValueError, 'config API rollback'):
                config_api_contract.run({'fail': True})
            assert [Search(kind).get_count() for kind in kinds] == before
            assert (upload / 'keep.txt').read_bytes() == b'keep'
        finally:
            sys.path.pop(0)
        # HTTP/XML-RPC dispatch and fresh request caches use these same methods.
        rpc_ticket = dict(ticket=token, project=source, language='python')
        assert api.dispatch('set_widget_setting', (rpc_ticket, 'rpc_setting', 'rpc value')) is True
        assert api.dispatch('get_widget_setting', (rpc_ticket, 'rpc_setting')) == 'rpc value'
        # A different ticket's files must survive clearing the current upload.
        other_upload = Path(Environment.get_upload_dir('other_owned_ticket'))
        (other_upload / 'keep.txt').write_bytes(b'other')
        assert api.dispatch('clear_upload_dir', (rpc_ticket,)) is True
        assert api.dispatch('clear_upload_dir', (rpc_ticket,)) is False
        assert (other_upload / 'keep.txt').read_bytes() == b'other'
        assert api.dispatch('subscribe', (rpc_ticket, 'rpc_key'))['login'] == 'admin'
        assert api.dispatch('unsubscribe', (rpc_ticket, 'rpc_key'))['message_code'] == 'rpc_key'
        result = api.dispatch('add_config_element', (rpc_ticket, 'contract/rpc', 'table', 'column', 'custom.Cell'))
        assert result == {'element_name': 'column'}
        with unittest.TestCase().assertRaisesRegex(Exception, 'requested element'):
            api.dispatch('set_config_definition', (rpc_ticket, 'contract/rpc', 'column', '<element name="wrong"/>'))
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            for method, arguments in (('subscribe', ('denied',)), ('set_widget_setting', ('denied', 'value')),
                                      ('add_config_element', ('contract/rpc', 'table', 'denied')),
                                      ('clear_upload_dir', ())):
                with unittest.TestCase().assertRaises((SecurityException, UnsupportedContract)):
                    api.dispatch(method, (rpc_ticket, *arguments))
        with unittest.TestCase().assertRaisesRegex(Exception, 'without enabling'):
            api.dispatch('fast_query', (rpc_ticket, source + '/asset'))
        from pyasm.web.api_xmlrpc import ApiException
        with unittest.TestCase().assertRaises(ApiException):
            api.dispatch('unsubscribe', (rpc_ticket, 'missing_subscription'))
        from tactic.command import ProjectTemplateUpdaterCmd
        with unittest.TestCase().assertRaisesRegex(UnsupportedContract, 'no implementation'):
            execute(ProjectTemplateUpdaterCmd(project_code=source).execute)
        # Template manager commands: staging from upload, multi-file rollback, export, download, delete.
        from tactic.ui.app.project_template_wdg import (
            ProjectTemplateInstallCmd, ProjectTemplateDownloadCmd,
            ProjectTemplateExportCmd, ProjectTemplateDeleteCmd,
        )
        upload_dir = Path(Environment.get_upload_dir())
        upload_dir.mkdir(parents=True, exist_ok=True)
        staged_zip = upload_dir / whole_zip.name
        staged_zip.write_bytes(whole_zip.read_bytes())
        bad_zip = upload_dir / 'corrupt_template.zip'
        bad_zip.write_bytes(b'not-a-zip')
        tpl_base = Path(Environment.get_template_dir())
        had_extracted = (tpl_base / (source + '-1')).exists()
        with unittest.TestCase().assertRaises(Exception):
            execute(ProjectTemplateInstallCmd(paths=[whole_zip.name, 'corrupt_template.zip']).execute)
        assert not (tpl_base / whole_zip.name).exists()
        assert (tpl_base / (source + '-1')).exists() == had_extracted
        execute(ProjectTemplateInstallCmd(paths=[whole_zip.name]).execute)
        assert (tpl_base / whole_zip.name).is_file()
        assert (tpl_base / (source + '-1') / 'manifest.xml').is_file()
        dl_cmd = ProjectTemplateDownloadCmd(template_dir=str(tpl_base / (source + '-1')))
        execute(dl_cmd.execute)
        assert dl_cmd.get_info()['filename'] == whole_zip.name
        cache_dir = Path(Environment.get_asset_dir()) / '_cache' / Environment.get_ticket()
        assert (cache_dir / whole_zip.name).is_file()
        execute(ProjectTemplateDeleteCmd(template=source + '-1').execute)
        assert not (tpl_base / (source + '-1')).exists() and not (tpl_base / whole_zip.name).exists()
        exp_cmd = ProjectTemplateExportCmd(project_code=source)
        execute(exp_cmd.execute)
        exp_zip_name = exp_cmd.get_info()['filename']
        assert (cache_dir / exp_zip_name).is_file()
        assert (tpl_base / source / 'manifest.xml').is_file()
        return comparison


def exercise_command_api(store, prefix):
    from test_client_transactions import exercise_client_transactions, exercise_client_transaction_failures
    assert exercise_client_transactions(store, 'plugin-test-password')
    assert exercise_client_transaction_failures(store, 'plugin-test-password')
    from test_schema_replay import exercise_schema_replay
    assert exercise_schema_replay(store, prefix)
    from concurrent.futures import ThreadPoolExecutor
    from pyasm.biz import ProjectSetting, Project
    from pyasm.common import Common
    from pyasm.common.errors import UnsupportedContract
    from tactic.command import Queue
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    ticket = dict(ticket=token, project='admin')
    milestone = api.dispatch('insert', (ticket, 'sthpw/milestone',
        dict(code=prefix + '_milestone', description='Original milestone', due_date='2026-10-20 12:00:00')))
    assert milestone['project_code'] == 'admin'
    found = api.dispatch('query', (ticket, 'sthpw/milestone', [('code', milestone['code'])]))
    assert milestone['code'] in found
    api.dispatch('delete_sobject', (ticket, milestone['__search_key__']))
    note = api.dispatch('insert', (ticket, 'sthpw/note', dict(code=prefix + '_undo', note='before')))
    key = note['__search_key__']
    assert api.dispatch('undo', (ticket,)) is True
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', note['code'])) == {}
    assert api.dispatch('redo', (ticket,)) is True
    assert api.dispatch('get_by_search_key', (ticket, key))['note'] == 'before'
    api.dispatch('update', (ticket, key, dict(note='after')))
    api.dispatch('undo', (ticket,))
    assert api.dispatch('get_by_search_key', (ticket, key))['note'] == 'before'
    api.dispatch('redo', (ticket,))
    assert api.dispatch('get_by_search_key', (ticket, key))['note'] == 'after'
    api.dispatch('delete_sobject', (ticket, key))
    api.dispatch('undo', (ticket,))
    assert api.dispatch('get_by_search_key', (ticket, key))['note'] == 'after'
    api.dispatch('redo', (ticket,))
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', note['code'])) == {}
    metadata = api.dispatch('execute_python_script', (ticket, '', {'code': '''
from pyasm.biz import Project, Schema
from pyasm.widget import WidgetConfigView
from decimal import Decimal
from pyasm.search import SearchType
view = WidgetConfigView.get_by_search_type('sthpw/note', 'table')
obj = server.query('sthpw/project', [('code', 'admin')], single=True, return_sobjects=True)
draft = SearchType.create('sthpw/file')
draft.set_value('code', 'DECIMAL_CONTRACT')
draft.set_value('size', Decimal('12345678901234567890.123456789'))
return {'has_note': Project.get().has_table('sthpw/note'),
        'has_types': bool(Project.get().get_search_types(include_sthpw=True, include_config=True)),
        'has_elements': bool(view.get_element_names()),
        'schema': Schema.get().get_xml().get_root_node().tag,
        'native_object': obj.get_code(),
        'serialized': server.server._get_sobjects_dict([obj])[0]['code'],
        'decimal': server.server._get_sobject_dict(draft)['size']}
'''}))['info']
    assert metadata == {'has_note': True, 'has_types': True, 'has_elements': True, 'schema': 'schema',
                        'native_object': 'admin', 'serialized': 'admin', 'decimal': '12345678901234567890.123456789'}
    project = prefix + '_ok'
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd', dict(project_code=project, project_title='Command API test')))
    ticket['project'] = project
    sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
    try:
        import command_api_contract
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            results = []
            for case in ({}, dict(zero=True), dict(snapshot=True), dict(snapshot=True, quotes=True, context='command_api_snapshot_quotes')):
                row = command_api_contract.run(case)
                if 'queue' in row:
                    row['queue']['project_code'] = 'PROJECT'
                    assert row['claimed'] == 'locked'
                else:
                    assert row['xml_error'] is None and row['checkout_error'] is None
                    assert row['cache_unchanged'] and row['trigger'] == case.get('context', 'command_api_snapshot')
                results.append(row)
            counts = {name: Search(name).get_count() for name in ('sthpw/queue', 'config/prod_setting')}
            try:
                command_api_contract.run(dict(fail=True))
            except ValueError as error:
                assert str(error) == 'late command API failure'
            else:
                raise AssertionError('Expected a rollback')
            assert {name: Search(name).get_count() for name in counts} == counts
            for method in ('_private', 'save()', "save;print('bad')"):
                with unittest.TestCase().assertRaises(ValueError):
                    Common.create_from_method('command_api_contract.ApiProbe', method, {})
        info = api.dispatch('get_connection_info', (ticket,), environ={'SERVER_PORT': '8081'})
        assert info['port'] == '8081' and info['keys'] == ['SERVER_PORT']
        assert info['num_database_connections'] == sum(info['databases'].values())
        for n in range(8):
            api.dispatch('add_queue_item', (ticket, 'tactic.command.QueueTest', {'n': n}, 'concurrent', n+1))
        def claim_jobs():
            ids = []
            with request_context(RequestContext(store, 'admin', project)):
                api.auth.bind_security('admin', token)
                while True:
                    cmd = Command()
                    cmd.get_transaction().set_sync(False)
                    cmd.execute = lambda: Queue.get_next_job(queue_type='concurrent')
                    job = Command.execute_cmd(cmd)
                    if job is None:
                        break
                    assert job.get_value('state') == 'locked'
                    ids.append(job.get_id())
            return ids
        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = [number for batch in pool.map(lambda _: claim_jobs(), range(2)) for number in batch]
        assert len(claimed) == len(set(claimed)) == 8
        api.dispatch('execute_class_method', (ticket, 'command_api_contract.ApiProbe', 'save',
                                             dict(key='rpc_command', value='from RPC')))
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            assert ProjectSetting.get_value_by_key('rpc_command') == 'from RPC'
            search = Search('sthpw/snapshot')
            search.add_filter('context', 'command_api_snapshot')
            snapshot_code = search.get_sobject().get_code()
            from pyasm.web import Url
            url = Url('https://example.invalid')
            url.set_option('item', ['один', 'two'])
            from urllib.parse import parse_qs, urlsplit
            assert parse_qs(urlsplit(url.to_string()).query) == {'item': ['один', 'two']}
        import asyncio, json
        from xmlrpc.client import dumps, loads
        from tactic_stream.server.app import create_app
        app = create_app(store.data_dir)
        async def http_request(body, path, content_type):
            messages = []
            async def receive():
                return {'type': 'http.request', 'body': body, 'more_body': False}
            async def send(message):
                messages.append(message)
            await app(dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method='POST',
                           scheme='https', path=path, raw_path=path.encode(), query_string=b'', root_path='',
                           headers=[(b'content-type', content_type), (b'host', b'example.invalid:9443')],
                           server=('example.invalid', 9443), client=('127.0.0.1', 1234)), receive, send)
            assert messages[0]['status'] == 200
            return b''.join(message.get('body', b'') for message in messages)
        response = asyncio.run(http_request(json.dumps(dict(method='get_connection_info', args=[ticket])).encode(),
                                            '/admin/rpc', b'application/json'))
        info = json.loads(response)['result']
        assert info['port'] == '9443' and 'BASE_URL' in info['keys']
        response = asyncio.run(http_request(dumps((ticket, snapshot_code), methodname='get_full_snapshot_xml').encode(),
                                            '/tactic/default/Api/', b'text/xml'))
        from xml.etree.ElementTree import fromstring
        xml = fromstring(loads(response)[0][0])
        assert xml.find('file').get('web_dir').startswith('https://example.invalid:9443/')
        with patch('pyasm.security.authenticator.Authenticator._admin', return_value=False):
            for name, args in [('execute_class_method', (ticket, 'command_api_contract.ApiProbe', 'save', {'key': 'denied', 'value': 'x'})),
                ('add_queue_item', (ticket, 'tactic.command.QueueTest'))]:
                with unittest.TestCase().assertRaises((SecurityException, UnsupportedContract)):
                    api.dispatch(name, args)
        with patch('pyasm.security.Security.is_admin', return_value=False):
            for method in ('test_speed', 'get_connection_info'):
                with unittest.TestCase().assertRaises(SecurityException):
                    api.dispatch(method, (ticket,))
        import snapshot_levels_contract
        with request_context(RequestContext(store, 'admin', 'admin')):
            api.auth.bind_security('admin', token)
            levels = snapshot_levels_contract.run({})
            assert levels['hierarchy'] == 1 and levels['alias_fixes'] == [-1, True]
            assert levels['aliases'] == [-1, 0] and levels['ref_errors'] == []
        return results
    finally:
        sys.path.pop(0)


class PluginInstallation(unittest.TestCase):
    exercise = staticmethod(exercise)
    def test_sqlite_and_optional_postgres(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite')
                store.initialize(hash_password('plugin-test-password'))
                expected = self.exercise(store, 'plugin_contract')
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import psycopg
            from psycopg import sql
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            prefix = 'stream_pl_' + uuid.uuid4().hex[:12]
            database = prefix + '_sys'
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                    password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                    **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config()
                        store = Store(root / 'postgres')
                        store.initialize(hash_password('plugin-test-password'))
                        self.assertEqual(self.exercise(store, prefix), expected)
                finally:
                    for name in (database, prefix + '_ok', prefix + '_tpl', prefix + '_bad', prefix + '_exp', prefix + '_copy'):
                        maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(name)))
                    Config.reload_config()


class CommandApiLifecycle(PluginInstallation):
    exercise = staticmethod(exercise_command_api)



def exercise_queue(store, prefix):
    from tactic.command import JobTask, Scheduler, SchedulerTask
    from pyasm.security import Batch
    from pyasm.biz import ProjectSetting, Project
    from pyasm.common.errors import TacticException, UnsupportedContract
    import threading
    from datetime import time as daytime
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    ticket = dict(ticket=token, project='admin', language='python')
    project = prefix + '_ok'
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Queue contract', project_stype=['asset'])))
    sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
    results = []
    try:
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            import queue_contract
            with patch.object(JobTask, '_wait', return_value=False):
                for failure in (None, 'tactic', 'retry', 'always'):
                    result = queue_contract.run(dict(failure=failure) if failure else {})
                    expected_state = 'error' if failure in ('tactic', 'always') else 'complete'
                    assert result['state'] == expected_state, result
                    assert result['attempts'] == (3 if failure in ('retry', 'always') else 1), result
                    assert bool(result['value']) == (expected_state == 'complete'), result
                    assert result['completed'] == 1 and result['jobs'] == 0
                    results.append({**result, 'value': bool(result['value']), 'project': 'owned'})
            from pyasm.security import Ticket
            task = JobTask()
            cmd = Command()
            cmd.execute = lambda: queue_contract.Queue.add('queue_contract.QueueCommand', dict(key='renewed'), 'renew', 1, '')
            renewed = Command.execute_cmd(cmd)
            # This represents an expired internal service ticket, not an invalid HTTP session.
            task.login_ticket = Ticket(search_type='sthpw/ticket')
            task.login_ticket.set_value('code', 'expired-service-ticket')
            task.check_new_job('renew')
            with request_context(RequestContext(store, 'admin', project)):
                api.auth.bind_security('admin', token)
                assert Search.get_by_id('sthpw/queue', renewed.get_id()).get_value('state') == 'complete'
            # Real scheduler thread must retain this temporary Store, even without TACTIC_DATA_DIR.
            done = threading.Event()
            class SaveTask(SchedulerTask):
                def execute(self):
                    ProjectSetting.create('scheduled', Environment.get_user_name() + ':' + Project.get_project_code())
                    done.set()
            scheduler = Scheduler()
            task = SaveTask(name='once')
            scheduler.add_single_task(task, delay=.01)
            scheduler.start_thread()
            try:
                assert done.wait(5), 'Scheduled command did not execute'
                # The event precedes the Command commit; stop joins scheduler, then task thread ends.
                import time
                deadline = time.monotonic() + 3
                def saved():
                    with request_context(RequestContext(store, 'admin', project)):
                        api.auth.bind_security('admin', token)
                        return ProjectSetting.get_value_by_key('scheduled')
                while time.monotonic() < deadline and not saved():
                    time.sleep(.01)
                assert saved() == 'admin:' + project, repr(saved())
                scheduler.add_weekly_task(SaveTask(name='weekly'), 1, daytime(12, 30))
                assert scheduler.get_task('weekly').days == (1,)
                scheduler.cancel_task('weekly')
                assert 'weekly' not in scheduler.get_task_names()
                scheduler.add_single_task(SaveTask(name='cancelled'), delay=30)
                scheduler.cancel_task('cancelled')
                assert scheduler.get_task('cancelled') is None
                with unittest.TestCase().assertRaises(UnsupportedContract):
                    scheduler.add_single_task(SaveTask(name='fork'), mode='forked')
            finally:
                scheduler.stop()
            # Exact dead owner recovery leaves every unrelated process's lock alone.
            from tactic.command.queue import _FinishJobsCmd
            def add_locked():
                first = queue_contract.Queue.add('queue_contract.QueueCommand', dict(key='dead'), 'contract', 1, '')
                second = queue_contract.Queue.add('queue_contract.QueueCommand', dict(key='foreign'), 'contract', 1, '')
                for job, host in ((first, 'dead:1'), (second, 'foreign:2')):
                    job.set_value('state', 'locked'); job.set_value('host', host); job.commit()
                return first.get_id(), second.get_id()
            cmd = Command(); cmd.execute = add_locked
            first, second = Command.execute_cmd(cmd)
            Command.execute_cmd(_FinishJobsCmd(host='dead:1', state='pending'))
            SObject.clear_cache()
            assert Search.get_by_id('sthpw/queue', first).get_value('state') == 'pending'
            assert Search.get_by_id('sthpw/queue', second).get_value('state') == 'locked'
    finally:
        sys.path.pop(0)
    return results


class QueueLifecycle(PluginInstallation):
    exercise = staticmethod(exercise_queue)



def exercise_diagnostics(store, prefix):
    from pyasm.biz import DebugLog, Project, ProjectSetting
    from pyasm.search import ExceptionLog, Transaction
    from pyasm.common.errors import UnsupportedContract
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    ticket = dict(ticket=token, project='admin', language='python')
    project = prefix + '_ok'
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Diagnostic contract', project_stype=['asset'])))
    ticket['project'] = project
    assert api.dispatch('log', (ticket, 'warning', 'API Текст & данные', 'api')) is True
    sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
    try:
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            import diagnostic_contract
            results = [diagnostic_contract.run(case) for case in
                       (dict(name='standalone', standalone=True), dict(name='commit'), dict(name='rollback', fail=True))]
            assert all(result['saved'] and len(result['logs']) == 1 for result in results), results
            assert results[-1]['error'] == 'ValueError' and not results[-1]['value'] and results[-1]['exceptions'] == 1
            assert all(result.get('recorded', True) for result in results)
            obj = SearchType.create('sthpw/debug_log')
            assert isinstance(obj, DebugLog)
            with unittest.TestCase().assertRaises(ValueError):
                DebugLog.log('invalid', 'rejected')
            # Manual diagnostics may not roll back the caller or silently share its system writer.
            original = Project.get().get_value('description')
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                obj = Project.get()
                obj.set_value('description', 'uncommitted diagnostic guard')
                obj.commit()
                for write in (lambda: DebugLog.log('info', 'blocked'), lambda: ExceptionLog.log(ValueError('blocked'))):
                    with unittest.TestCase().assertRaises(UnsupportedContract):
                        write()
                assert cmd.get_transaction().is_in_transaction()
                raise ValueError('rollback-system-writer')
            cmd.execute = execute
            with unittest.TestCase().assertRaisesRegex(ValueError, 'rollback-system-writer'):
                Command.execute_cmd(cmd)
            assert Project.get().get_value('description') == original
            search = Search('sthpw/exception_log'); search.add_filter('message', 'rollback-system-writer')
            assert search.get_count() == 1
            # Nested failures create one exception row, not a row for each command level.
            outer = Command(); inner = Command()
            inner.execute = lambda: (_ for _ in ()).throw(ValueError('nested diagnostic error'))
            outer.execute = lambda: Command.execute_cmd(inner)
            with unittest.TestCase().assertRaisesRegex(ValueError, 'nested diagnostic error'):
                Command.execute_cmd(outer)
            search = Search('sthpw/exception_log'); search.add_filter('message', 'nested diagnostic error')
            assert search.get_count() == 1
            # A failed journal connection preserves the original business exception.
            failure = Command()
            failure.execute = lambda: (_ for _ in ()).throw(ValueError('original exception'))
            with patch('pyasm.search.exception_log._write_log', side_effect=PermissionError('diagnostic connection failed')):
                with unittest.TestCase().assertRaisesRegex(ValueError, 'original exception'):
                    Command.execute_cmd(failure)
            # Diagnostic authority requires the same authenticated request identity.
            with patch('pyasm.security.Security.get_user_name', return_value='another_user'):
                with unittest.TestCase().assertRaises(SecurityException):
                    DebugLog.log('info', 'denied')
            with patch('pyasm.security.Security.is_logged_in', return_value=False):
                with unittest.TestCase().assertRaises(SecurityException):
                    api.dispatch('log', (ticket, 'info', 'denied'))
            # Real XML-RPC transport exercises authentication and the original True result.
            import asyncio, json
            from xmlrpc.client import dumps, loads
            from tactic_stream.server.app import create_app
            app = create_app(store.data_dir)
            body = dumps((ticket, 'info', 'XML-RPC Текст', 'xmlrpc'), methodname='log').encode()
            sent = []
            delivered = False
            async def receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': body, 'more_body': False}
                return {'type': 'http.disconnect'}
            async def send(message):
                sent.append(message)
            asyncio.run(app(dict(type='http', http_version='1.1', method='POST', path='/tactic/default/Api/',
                raw_path=b'/tactic/default/Api/', query_string=b'', headers=[(b'content-type', b'text/xml')],
                scheme='http', server=('testserver', 80), client=('127.0.0.1', 123)), receive, send))
            response = b''.join(item.get('body', b'') for item in sent)
            assert loads(response)[0][0] is True, response
            body = json.dumps(dict(method='log', args=[ticket, 'info', 'JSON Текст', 'json'])).encode()
            sent.clear()
            delivered = False
            asyncio.run(app(dict(type='http', http_version='1.1', method='POST', path='/admin/rpc',
                raw_path=b'/admin/rpc', query_string=b'', headers=[(b'content-type', b'application/json')],
                scheme='http', server=('testserver', 80), client=('127.0.0.1', 123)), receive, send))
            assert json.loads(b''.join(item.get('body', b'') for item in sent))['result'] is True
            return results
    finally:
        sys.path.pop(0)


class DiagnosticLifecycle(PluginInstallation):
    exercise = staticmethod(exercise_diagnostics)


if __name__ == '__main__':
    unittest.main()
