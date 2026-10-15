"""Project catalogs adapted from Handler's project chooser and creation wizard."""
from pathlib import Path

from pyasm.biz import Project, PluginUtil
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security.security import _require_admin
from tactic.command.plugin import PluginInstaller


def get_project_catalog():
    """Handler get_projects_and_logins project scope and ProjectModel previews."""
    from pyasm.biz import Snapshot
    security = Environment.get_security()
    search = Search('sthpw/project'); search.set_show_retired(True); search.add_order_by('code')
    all_allowed = security.check_access('project', {'code': '*'}, 'allow', default='deny')
    projects = [item for item in search.get_sobjects() if item.get_code() in ('admin', 'sthpw') or
                all_allowed or security.check_access('project', {'code': item.get_code()}, 'allow', default='deny')]
    snapshots = [item for item in Snapshot.get_by_sobjects(projects, process=['icon', 'publish'])
                 if item.get_value('version') in (-1, 0) or item.is_latest()]
    snapshots.sort(key=lambda item: (item.get_value('process') != 'icon',
                                    item.get_value('version') not in (-1, 0), -int(item.get_value('version') or 0)))
    files = Snapshot.get_files_dict_by_snapshots(snapshots)
    previews = {}
    image_types = ('web', 'preview', 'image', 'icon', 'main')
    for snapshot in snapshots:
        code = snapshot.get_value('search_code')
        if code in previews:
            continue
        candidates = sorted(files.get(snapshot.get_code(), []), key=lambda item:
                            image_types.index(item.get_value('type')) if item.get_value('type') in image_types else len(image_types))
        for item in candidates:
            if str(item.get_value('file_name') or '').rsplit('.', 1)[-1].lower() in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'avif', 'ico'):
                previews[code] = item.get_web_path().replace('\\', '/')
                break
    fields = ('code', 'title', 'category', 'description', 'type', 'status', 's_status', 'is_template')
    return [{**{field: item.get_value(field, no_exception=True) for field in fields}, '__builtin__': item.get_code() in ('admin', 'sthpw'),
             'project_mode': 'file_project' if item.get_value('type') == 'file_project' else 'classic',
             'preview': previews.get(item.get_code(), '')} for item in projects]


def get_project_creation_catalog():
    _require_admin()
    search = Search('sthpw/project')
    search.add_filter('is_template', True)
    templates = [{'value': item.get_code(), 'label': item.get_value('title') or item.get_code(), 'kind': 'project'}
                 for item in search.get_sobjects()]
    templates.append({'value': 'perforce_like', 'label': 'Perforce-like file project', 'kind': 'builtin'})
    installed = []
    directory = Path(Environment.get_template_dir())
    for path in sorted(directory.iterdir()) if directory.is_dir() else []:
        if path.is_symlink():
            continue
        if path.is_dir() and (path / 'manifest.xml').is_file():
            installed.append({'code': path.name, 'path': path.as_posix()})
        if path.suffix.lower() != '.zip' or not path.is_file():
            continue
        package = PluginInstaller(zip_path=str(path), base_dir=str(directory))
        templates.append({'value': package.code + '|' + path.as_posix(), 'label': package.code,
                          'kind': 'file'})
    builtin_dir = Path(Environment.get_builtin_plugin_dir()) / 'TACTIC'
    for code in ('vfx', 'scrum'):
        path = builtin_dir / code
        if (path / 'manifest.xml').is_file():
            templates.append({'value': code + '|' + path.as_posix(), 'label': code, 'kind': 'builtin'})
    data = PluginUtil().get_plugins_data('theme')
    data.update(PluginUtil(base_dir=Environment.get_builtin_plugin_dir()).get_plugins_data('theme'))
    themes = [{'value': code, 'label': code, 'description': str(values.get('description') or ''),
               'preview': '/tactic/%s/%s/media/screenshot.jpg' % (
                   'builtin_plugins' if Environment.is_builtin_plugin(code) else 'plugins', code)}
              for code, values in sorted(data.items())]
    default_code = Project.get_default_project()
    default_project = Project.get_by_code(default_code) if default_code else None
    all_codes = Search('sthpw/project')
    all_codes.set_show_retired(True)
    return {'templates': templates, 'installedTemplates': installed, 'themes': themes,
            'projectCodes': [item.get_code() for item in all_codes.get_sobjects()],
            'defaultProject': {'code': default_code or '', 'title': default_project.get_value('title') if default_project else ''},
            'isMainProject': not default_project and not Project.get_all_projects()}
