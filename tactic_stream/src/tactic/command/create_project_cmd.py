# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""Original project creation, adapted to native drivers and headless Commands."""
import re
from pathlib import Path

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Common, TacticException, Environment, Config
from pyasm.common.errors import UnsupportedContract
from pyasm.search import Search, SearchType, DbContainer, DbResource
from pyasm.security.security import _require_admin


class CreateProjectCmd(Command):
    @classmethod
    def is_undoable(cls):
        return False

    def get_title(self):
        return 'Create Project'

    def get_args_keys(self):
        return {
            'project_code': 'code of the new project',
            'project_title': 'title of the new project',
            'project_type': 'determines the type of project which specifies the initial schema and the naming conventions',
            'project_mode': 'classic (default) or file_project; new projects only',
        }

    def check_security(self):
        _require_admin()
        return True

    def check(self):
        project_code = self.kwargs.get('project_code')
        if not isinstance(project_code, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,29}', project_code):
            raise TacticException('<project_code> [%s] cannot contain special characters or start with a number.' % project_code)
        title = self.kwargs.get('project_title')
        if title is not None and (not isinstance(title, str) or not title.strip() or len(title) > 100):
            raise TacticException('Project title is required and cannot exceed 100 characters')
        namespace = self.kwargs.get('project_type') or 'simple'
        if namespace in ('sthpw', 'prod') or not isinstance(namespace, str):
            raise TacticException('Invalid or reserved project namespace')
        image = self.kwargs.get('project_image_path')
        if image:
            path = Path(image).resolve()
            roots = [Path(Environment.get_upload_dir()).resolve(),
                     (Path(Environment.get_asset_dir()) / 'temp' / Environment.get_ticket()).resolve()]
            if not any(path.is_relative_to(root) for root in roots) or not path.is_file():
                raise TacticException('Project preview must be an uploaded file belonging to this ticket')
            from PIL import Image
            with Image.open(path) as preview:
                preview.verify()
        existing = Search.get_by_code('sthpw/project', project_code, show_retired=True)
        if existing:
            suffix = ' but is retired' if existing.is_retired() else ''
            raise TacticException('Project with code [%s] already exists%s.' % (project_code, suffix))
        resource = DbResource.get_default(project_code)
        if resource.get_database_impl().database_exists(resource):
            raise FileExistsError('Project database already exists: ' + project_code)
        return True

    def execute(self):
        # Original Batch doesn't call check(); preflight must run here too.
        self.check_security()
        self.check()
        self._config_revision = None
        project_code = self.kwargs.get('project_code')
        project_title = self.kwargs.get('project_title')
        project_type = self.kwargs.get('project_type') or 'simple'
        project_mode = self.kwargs.get('project_mode', 'classic')
        if project_mode not in ('classic', 'file_project'):
            raise ValueError('Unknown project_mode')
        if project_mode == 'file_project':
            if self.kwargs.get('project_stype') or self.kwargs.get('project_theme'):
                raise ValueError('File projects use their separate built-in schema')
            project_type = 'file_project'
        elif project_type == 'file_project':
            raise ValueError('Reserved project type: use project_mode=file_project')
        if project_type == 'prod':
            raise UnsupportedContract('Deprecated production project schema is excluded')
        is_template = self.kwargs.get('is_template')
        project_type_sobj = Search.get_by_code('sthpw/project_type', project_type)
        if project_type_sobj and project_type_sobj.get_value('type') != 'simple':
            raise UnsupportedContract('Project base schema is not migrated: %s' % project_type_sobj.get_value('type'))
        if not project_type_sobj:
            if not is_template and project_type == project_code:
                project_type = 'default'
            project_type_sobj = Search.get_by_code('sthpw/project_type', project_type)
            if not project_type_sobj:
                project_type_sobj = SearchType.create('sthpw/project_type')
                project_type_sobj.set_value('code', project_type)
                project_type_sobj.set_value('type', 'simple')
                project_type_sobj.commit()

        Project.set_project('admin')
        project = SearchType.create('sthpw/project')
        project.set_value('code', project_code)
        project.set_value('title', project_title)
        project.set_value('type', project_type)
        if self.kwargs.get('description'):
            project.set_value('description', self.kwargs['description'])
        project.set_value('last_version_update', '2.5.0.v01')
        project.set_value('is_template', is_template in ('true', True, 'True'))
        if project_type != 'default':
            project.set_value('category', Common.get_display_title(project_type))
        project.commit()

        resource = project.get_project_db_resource()
        database = resource.get_database_impl()
        database.create_database(resource)
        database.import_schema(resource, 'simple')
        database.import_default_data(resource, 'simple')
        self.create_search_types()
        if project_mode == 'file_project':
            from pyasm.biz.file_project import install
            install(project_code)
            self.info['project_mode'] = project_mode
        if self.kwargs.get('project_image_path'):
            from pyasm.biz import IconCreator
            from pyasm.checkin import FileCheckin
            path = self.kwargs['project_image_path']
            icon = IconCreator(path)
            icon.execute()
            paths, types = [path], ['main']
            if icon.get_web_path():
                paths += [icon.get_web_path(), icon.get_icon_path()]
                types += ['web', 'icon']
            FileCheckin(project, context='icon', file_paths=paths, file_types=types).execute()
        if self.kwargs.get('project_theme'):
            Project.set_project(project_code)
            self.create_theme(self.kwargs['project_theme'])
            Project.set_project('admin')
        DbContainer.get('sthpw')
        self.info['result'] = 'Finished creating project [%s].' % project_code

    def create_theme(self, theme):
        from tactic.command import PluginInstaller
        from tactic.command.plugin import _package_path
        from xml.etree import ElementTree as ET
        installer = None
        for base in (Environment.get_plugin_dir(), Environment.get_builtin_plugin_dir()):
            path = _package_path(base, theme)
            if (path / 'manifest.xml').is_file():
                installer = PluginInstaller(plugin_dir=str(path), register=True)
                break
            archive = Path(str(path) + '.zip')
            if archive.is_file():
                installer = PluginInstaller(zip_path=str(archive), register=True)
                break
        if installer is None:
            raise TacticException('Installation error: cannot find %s theme' % theme)
        installer.execute()
        search = Search('config/url')
        search.add_filter('url', '/index')
        if search.get_sobject() is None:
            element = ET.Element('element', name='index')
            display = ET.SubElement(element, 'display', {'class': 'tactic.ui.panel.CustomLayoutWdg'})
            ET.SubElement(display, 'view').text = installer.xml.get_value('manifest/data/index_view') or theme.split('/')[-1] + '/index'
            url = SearchType.create('config/url')
            url.set_value('url', '/index')
            url.set_value('widget', ET.tostring(element, encoding='unicode'))
            url.set_value('description', 'Index Page')
            url.commit()

    def commit(self):
        if self.kwargs.get('is_main_project') not in (True, 'true', 'on'):
            return
        from pyasm.common.config import read_config_file
        self._config_path = Config.get_config_path()
        self._previous_config, revision = read_config_file(self._config_path)
        # Config.save_config applies its shared lock, revision check and atomic write.
        Config.get_xml_data(use_cache=False)
        if Config.get_revision() != revision:
            raise TacticException('Server configuration changed during project creation')
        Config.set_value('install', 'default_project', self.kwargs['project_code'])
        Config.save_config()
        self._config_revision = Config.get_revision()

    def rollback(self):
        if getattr(self, '_config_revision', None):
            from pyasm.common.config import save_config_file
            save_config_file(self._config_path, self._previous_config, expected_revision=self._config_revision)
            Config.reload_config()


    def create_search_types(self):
        from tactic.core.schema_commands import SearchTypeCreatorCmd
        search_types = self.kwargs.get('project_stype') or []
        if not isinstance(search_types, (list, tuple)):
            raise ValueError('project_stype must be a list of search types')
        if not search_types:
            return
        project_code = self.kwargs['project_code']
        Project.set_project(project_code)
        try:
            for search_type in search_types:
                if not search_type:
                    continue
                search_type = Common.get_filesystem_name(search_type)
                if '/' not in search_type:
                    search_type = '%s/%s' % (project_code, search_type)
                # Original duplicated the namespace of an already full type.
                table = search_type.split('/')[-1]
                title = Common.get_display_title(table)
                creator = SearchTypeCreatorCmd(database=project_code, namespace=project_code, schema='public',
                    search_type_name=search_type, asset_description=title, asset_title=title, sobject_pipeline=True)
                creator.execute()
        finally:
            Project.set_project('admin')


class CopyFileToAssetTempCmd(Command):
    def execute(self):
        _require_admin()
        from pyasm.biz import IconCreator
        from pyasm.search import FileUndo
        ticket = self.kwargs.get('ticket') or Environment.get_ticket()
        if ticket != Environment.get_ticket():
            raise TacticException('Upload ticket does not belong to this request')
        filename = self.kwargs.get('filename')
        if not isinstance(filename, str) or not filename or Path(filename).name != filename or '/' in filename or '\\' in filename:
            raise TacticException('Invalid upload filename')
        source = (Path(Environment.get_upload_dir()) / filename).resolve()
        if not source.is_relative_to(Path(Environment.get_upload_dir()).resolve()):
            raise TacticException('Upload escapes its ticket directory')
        icon = IconCreator(str(source))
        icon.execute()
        target = Path(Environment.get_asset_dir()) / 'temp' / ticket / filename
        FileUndo.mkdir(str(target.parent))
        FileUndo.copy(icon.get_icon_path() or str(source), str(target))
        self.info = {'web_path': '/assets/temp/%s/%s' % (ticket, filename), 'lib_path': target.as_posix()}


class CopyProjectFromTemplateCmd(Command):

    def execute(self):
        from tactic.command import ProjectTemplateInstallerCmd
        cmd = ProjectTemplateInstallerCmd(**self.kwargs)
        cmd.execute()
