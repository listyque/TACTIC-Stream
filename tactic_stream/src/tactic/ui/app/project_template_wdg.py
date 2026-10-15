# Copyright (c) 2010, Southpaw Technology. See LICENSE.TACTIC.
"""Original template manager commands without HTML; bounded paths and FileUndo."""
from pathlib import Path

from pyasm.command import Command
from pyasm.common import Environment, TacticException
from pyasm.search import FileUndo
from pyasm.security.security import _require_admin
from tactic.command.plugin import PluginInstaller, _package_path


class ProjectTemplateInstallCmd(Command):
    def execute(self):
        _require_admin()
        paths = self.kwargs.get('paths')
        if not isinstance(paths, list) or not paths or not all(isinstance(path, str) for path in paths):
            raise TacticException('Select template ZIP files')
        base = Environment.get_template_dir()
        FileUndo.mkdir(base)
        for value in paths:
            name = value.replace('\\', '/').split('/')[-1]
            if not name.lower().endswith('.zip'):
                raise TacticException('Select template ZIP files')
            source = _package_path(Environment.get_upload_dir(), name)
            package = PluginInstaller(zip_path=str(source), base_dir=base)
            # Reuse the installer's checked extraction; staging executes no scripts.
            package._extract_package()
            FileUndo.copy(str(source), str(_package_path(base, name)))


class ProjectTemplateDownloadCmd(Command):
    def execute(self):
        _require_admin()
        base = Path(Environment.get_template_dir()).resolve()
        selected = Path(self.kwargs.get('template_dir') or '').resolve()
        if selected == base or not selected.is_relative_to(base):
            raise TacticException('Template path escapes its directory')
        archive = None
        for path in sorted(base.glob('*.zip')):
            package = PluginInstaller(zip_path=str(path), base_dir=str(base))
            if Path(package.plugin_dir).resolve() == selected:
                archive = path
                break
        if archive is None:
            raise TacticException('No template archive is available for download')
        cache = Path(Environment.get_asset_dir()) / '_cache' / Environment.get_ticket()
        FileUndo.mkdir(str(cache))
        FileUndo.copy(str(archive), str(cache / archive.name))
        self.info['filename'] = archive.name


class ProjectTemplateExportCmd(Command):
    """Export through the native creator and the existing ticket cache download path."""
    def execute(self):
        _require_admin()
        from tactic.command import ProjectTemplateCreatorCmd
        from pyasm.biz import Project
        code = self.kwargs.get('project_code')
        if not isinstance(code, str) or not code or len(code) > 64:
            raise TacticException('Select a business project for the template archive')
        project = Project.get_by_code(code)
        if not project or project.get_code() in ('admin', 'sthpw'):
            raise TacticException('Select a business project for the template archive')
        creator = ProjectTemplateCreatorCmd(project_code=project.get_code())
        Command.execute_cmd(creator)
        archive = Path(creator.get_zip_path())
        cache = Path(Environment.get_asset_dir()) / '_cache' / Environment.get_ticket()
        FileUndo.mkdir(str(cache))
        FileUndo.copy(str(archive), str(cache / archive.name))
        self.info['filename'] = archive.name


class ProjectTemplateDeleteCmd(Command):
    def execute(self):
        _require_admin()
        name = self.kwargs.get('template')
        if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise TacticException('Invalid template name')
        base = Path(Environment.get_template_dir()).resolve()
        selected = _package_path(str(base), name)
        if selected == base or not (selected / 'manifest.xml').is_file():
            raise TacticException('Template package does not exist')
        archives = []
        for path in sorted(base.glob('*.zip')):
            package = PluginInstaller(zip_path=str(path), base_dir=str(base))
            if Path(package.plugin_dir).resolve() == selected:
                archives.append(path.resolve())
        # Every removal target is resolved within the template directory above.
        FileUndo.remove(str(selected))
        for path in archives:
            if not path.is_relative_to(base):
                raise TacticException('Template archive escapes its directory')
            FileUndo.remove(str(path))
