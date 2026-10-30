# Copyright (c) 2010, Southpaw Technology. See LICENSE.TACTIC.
"""Plugin manager extracted from the original PluginWdg, without its HTML shell.

Native PluginCreator/Installer/Reloader/Uninstaller own package semantics. This
command owns the administrator's catalogue and transactional package-file edits.
"""
import hashlib
import json
import re
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment, TacticException
from pyasm.search import DbContainer, FileUndo, Search, SearchType
from pyasm.security.security import _require_admin
from tactic.command import PluginCreator, PluginInstaller, PluginReloader, PluginUninstaller
from tactic.command.plugin import _manifest_xml, _package_path
from tactic.command.python_cmd import check_script_execution
from tactic.command import plugin_resources as Resources


def _roots():
    return {'plugins': Path(Environment.get_plugin_dir()).resolve(),
            'builtin': Path(Environment.get_builtin_plugin_dir()).resolve()}


def _package(identity):
    source, separator, relative = identity.partition(':')
    if source not in _roots() or not separator or not relative:
        raise TacticException('Select a plugin package')
    root = _roots()[source]
    path = _package_path(root, relative)
    if (path == root or not (path / 'manifest.xml').is_file()
            or not (path / 'manifest.xml').resolve().is_relative_to(path)):
        raise TacticException('Plugin package does not exist')
    return root, path, source == 'builtin'


def _data(path):
    text = (path / 'manifest.xml').read_text(encoding='utf-8-sig')
    xml = _manifest_xml(text)
    if xml.get_root_node().tag != 'manifest':
        raise TacticException('Expected manifest XML root')
    return text, {name: xml.get_value('manifest/data/' + name) or
                  xml.get_value('manifest/@' + name) or ''
                  for name in ('code', 'title', 'description', 'version')}


def _active():
    if Project.get_project_code() in ('admin', 'sthpw'):
        return []
    return Search('config/plugin').get_sobjects()


def _is_active(data, path, active):
    return any(row.get_code() == data['code'] and
               str(row.get_value('version') or '') == data['version'] and
               str(row.get_value('rel_dir') or '') == path
               for row in active)


def _catalog():
    rows, active = [], _active()
    for source, root in _roots().items():
        if not root.exists():
            continue
        # Do not follow directory links outside the configured package roots.
        for manifest in sorted(root.rglob('manifest.xml')):
            path = manifest.parent
            relative = path.relative_to(root).as_posix()
            row = dict(identity=source + ':' + relative, path=relative,
                       builtin=source == 'builtin', active=False, error='')
            try:
                if not manifest.resolve().is_relative_to(root) or not path.resolve().is_relative_to(root):
                    continue
                _, data = _data(path)
                row.update(data, active=_is_active(data, relative, active))
            except (OSError, ValueError, ET.ParseError, TacticException) as error:
                row.update(title=path.name, code=path.name, version='', description='', error=str(error))
            rows.append(row)
    return rows


def _revision(path):
    entries = []
    for item in sorted(path.rglob('*')):
        if not item.resolve().is_relative_to(path) or item.is_symlink():
            continue
        stat = item.stat()
        entries.append((item.relative_to(path).as_posix(), stat.st_size, stat.st_mtime_ns))
    entries.append(('manifest', hashlib.sha256((path / 'manifest.xml').read_bytes()).hexdigest()))
    entries.extend((row.get_code(), row.get_value('version'), row.get_value('rel_dir')) for row in _active())
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def _file(path, relative):
    target = _package_path(path, relative)
    if target == path:
        raise TacticException('Select a file inside the plugin')
    if target.is_symlink():
        raise TacticException('Symbolic links cannot be edited')
    return target


def _write(path, content):
    if not isinstance(content, str) or len(content.encode('utf-8')) > 2 * 1024 * 1024:
        raise TacticException('Text files must be UTF-8 and at most 2 MiB')
    FileUndo.mkdir(str(path.parent))
    if path.exists():
        FileUndo.remove(str(path))
    FileUndo.create(str(path), io_action=False)
    path.write_text(content, encoding='utf-8', newline='\n')


def _document(identity, folder='', file='', resource=''):
    root, path, builtin = _package(identity)
    manifest, data = _data(path)
    directory = _package_path(path, folder)
    if not directory.is_dir():
        raise TacticException('Plugin folder does not exist')
    files = []
    for entry in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold())):
        if entry.is_symlink() or not entry.resolve().is_relative_to(path):
            continue
        files.append(dict(name=entry.name, path=entry.relative_to(path).as_posix(),
                          directory=entry.is_dir(), size=entry.stat().st_size if entry.is_file() else 0))
    active = _is_active(data, path.relative_to(root).as_posix(), _active())
    document = dict(data, manifest=manifest, file=None, resource=None)
    if resource:
        if not active:
            raise TacticException('Activate the plugin before editing its project resources')
        document['resource'] = Resources.resource_document(manifest, resource)
    if file:
        target = _file(path, file)
        if target.is_dir():
            raise TacticException('Select a file to edit')
        raw = target.read_bytes() if target.stat().st_size <= 2 * 1024 * 1024 else None
        try:
            content = raw.decode('utf-8-sig') if raw is not None and b'\0' not in raw else None
        except UnicodeDecodeError:
            content = None
        document['file'] = dict(path=file, content=content,
                                revision=hashlib.sha256(raw).hexdigest() if raw is not None else '')
    relative = path.relative_to(root).as_posix()
    return dict(identity=identity, revision=_revision(path), document=document,
                metadata=dict(folder=folder, files=files, builtin=builtin,
                              active=active,
                              resources=Resources.resources(manifest) if active else [],
                              dataTypes=[dict(value=row.get_base_key(), label=row.get_title() or row.get_base_key())
                                         for row in Project.get().get_search_types(include_multi_project=True)] if active else [],
                              pluginTheme=Resources.selected_theme(),
                              project=Project.get_project_code(),
                              docs=next((name for name in ('doc/index.html', 'README.md', 'README.txt', 'doc/README.md')
                                         if (path / name).is_file()), 'README.md'),
                              docsExist=any((path / name).is_file() for name in
                                            ('doc/index.html', 'README.md', 'README.txt', 'doc/README.md'))),
                canWrite=not builtin)


def _checked_zip(path):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 10000 or sum(row.file_size for row in members) > 512 * 1024 * 1024:
            raise TacticException('Plugin archive exceeds the extraction limit')
        if any(row.filename.endswith('manifest.xml') and row.file_size > 2 * 1024 * 1024 for row in members):
            raise TacticException('Plugin manifest is too large')
    package = PluginInstaller(zip_path=str(path), verbose=False)
    if Path(package.plugin_dir).exists():
        raise TacticException('This plugin directory already exists; choose another version')
    package._extract_package()
    return 'plugins:' + Path(package.plugin_dir).relative_to(_roots()['plugins']).as_posix()


class PluginManagerCmd(Command):
    """Admin-only original plugin workflows on the native file/database journal."""

    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'list')
        project = self.kwargs.get('project_code')
        if not project or project != Project.get_project_code():
            raise TacticException('Select a project before managing plugins')
        if action == 'list':
            self.info.update(catalog=_catalog(), metadata={}, canWrite=True)
            return
        if action == 'new':
            self.info.update(identity='', revision='', document=dict(code='', title='', description='', type=''),
                             metadata=dict(new=True, project=project), canWrite=True)
            return
        identity = self.kwargs.get('identity') or ''
        if action in ('load', 'browse', 'open_file', 'open_resource'):
            self.info.update(_document(identity, self.kwargs.get('folder', ''), self.kwargs.get('file', ''),
                                       self.kwargs.get('resource', '')))
            return
        check_script_execution()
        # Keep cross-project package writers serialized until Command commits or rolls back.
        sql = DbContainer.get('sthpw')
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/project').get_table())
        root = _roots()['plugins']
        FileUndo.mkdir(str(root))
        identity = self._mutate(action, identity)
        if identity:
            self.info.update(_document(identity, self.kwargs.get('folder', ''),
                                       self.kwargs.get('file', '') if action == 'save' else
                                       self.kwargs.get('path', '') if action in ('new_file', 'download_file', 'upload') else '',
                                       self.kwargs.get('resource', '')))
        else:
            self.info.update(identity='', revision='', document={}, metadata={}, canWrite=True)
        self.info['catalog'] = _catalog()
        if 'run_result' in self.kwargs:
            self.info['metadata']['runResult'] = self.kwargs['run_result']
        self.info['metadata']['changed'] = action != 'save' or bool(self.kwargs.get('resource'))
        self.add_description('Plugin manager: ' + action)

    def _mutate(self, action, identity):
        if action == 'create':
            return self._create()
        if action in ('install', 'download_url'):
            return self._install(action)
        root, path, builtin = _package(identity)
        if _revision(path) != self.kwargs.get('expected_revision'):
            raise TacticException('Plugin changed on the server. Reload before continuing.')
        if builtin and action not in ('activate', 'reload', 'deactivate', 'clean', 'download_file', 'apply_theme', 'reset_theme', 'run_resource'):
            raise TacticException('Built-in plugin files are read-only')
        base = dict(base_dir=str(root), plugin_dir=str(path), verbose=False)
        if action in ('deactivate', 'clean', 'delete', 'delete_file', 'clear_spt', 'reload'):
            if self.kwargs.get('confirmation') is not True:
                raise TacticException('Confirm the destructive plugin operation')
        if action in ('activate', 'reload', 'deactivate', 'clean'):
            if Project.get_project_code() in ('admin', 'sthpw'):
                raise TacticException('Select a business project to activate or remove a plugin')
            _, data = _data(path)
            installed = Search.get_by_code('config/plugin', data['code'])
            if installed and str(installed.get_value('rel_dir') or '') != path.relative_to(root).as_posix():
                raise TacticException('Another version is active. Remove it from this project first.')
            if action in ('activate', 'reload'):
                command = PluginReloader(**base) if action == 'reload' else PluginInstaller(**base, register=True)
            else:
                command = PluginUninstaller(**base)
            Command.execute_cmd(command)
        elif action in ('add_resource', 'apply_theme', 'reset_theme', 'run_resource'):
            manifest, data = _data(path)
            if not _is_active(data, path.relative_to(root).as_posix(), _active()):
                raise TacticException('Activate the plugin before changing its project resources')
            if action == 'add_resource':
                values = self.kwargs.get('values') or {}
                if values.get('kind') == 'hooks':
                    name = str(values.get('name') or '')
                    if not re.fullmatch(r'[A-Za-z_][\w.-]{0,127}', name):
                        raise TacticException('Choose a valid hook name')
                    install, undo = name + '_install.py', name + '_uninstall.py'
                    if (path / install).exists() or (path / undo).exists():
                        raise TacticException('Hook files already exist')
                    _write(path / install, '# Install hook. Use native APIs; the surrounding Command owns rollback.\n')
                    _write(path / undo, '# Removal hook. Undo only the changes owned by this package.\n')
                    tree = _manifest_xml(manifest).get_root_node()
                    ET.SubElement(tree, 'python', path=install, undo_path=undo)
                    manifest, key = ET.tostring(tree, encoding='unicode'), ''
                else:
                    manifest, key = Resources.add_resource(manifest, values)
                _write(path / 'manifest.xml', manifest)
                self._export_resources(base, data, manifest)
                self.kwargs['resource'] = key
            elif action == 'run_resource':
                if self.kwargs.get('confirmation') is not True:
                    raise TacticException('Confirm running trusted server Python')
                resource = Resources.resource_document(manifest, self.kwargs.get('resource'))
                if resource['kind'] != 'python':
                    raise TacticException('Select a Python resource')
                arguments = json.loads(self.kwargs.get('inputs') or '{}')
                if not isinstance(arguments, dict) or set(arguments) & {'code', 'file_path', 'script_path'}:
                    raise TacticException('Python inputs must be a JSON object without code/file_path/script_path')
                from tactic.command import PythonCmd
                row = Search.get_by_search_key(resource['key'])
                command = PythonCmd(script_path=row.get_value('folder') + '/' + row.get_value('title'), **arguments)
                self.kwargs['run_result'] = Command.execute_cmd(command)
            else:
                from pyasm.biz import ProjectSetting
                view = ''
                if action == 'apply_theme':
                    item = Resources.resource_document(manifest, self.kwargs.get('resource'))
                    if item['kind'] != 'theme':
                        raise TacticException('Select a theme resource')
                    if not item.get('palette'):
                        raise TacticException(item.get('validationError') or 'Invalid theme palette')
                    view = item['title']
                ProjectSetting.create(Resources.THEME_SETTING, json.dumps(dict(view=view, plugin=data['code'])) if view else '')
        elif action == 'save':
            draft = self.kwargs.get('document')
            if not isinstance(draft, dict):
                raise TacticException('Plugin document is required')
            if draft.get('resource'):
                manifest, data = _data(path)
                if not _is_active(data, path.relative_to(root).as_posix(), _active()):
                    raise TacticException('Activate the plugin before editing its project resources')
                Resources.save_resource(manifest, draft['resource'])
                self._export_resources(base, data, manifest)
                self.kwargs['resource'] = draft['resource']['key']
            elif draft.get('file'):
                file = draft['file']
                target = _file(path, file['path'])
                if hashlib.sha256(target.read_bytes()).hexdigest() != file.get('revision'):
                    raise TacticException('File changed on the server. Reload before saving.')
                if target == path / 'manifest.xml':
                    package = PluginInstaller(manifest=file['content'], base_dir=str(root))
                    _, old = _data(path)
                    if package.code != old['code'] or str(package.version or '') != old['version']:
                        raise TacticException('Use Publish to change a plugin code or version')
                _write(target, file['content'])
                self.kwargs['file'] = file['path']
            else:
                manifest = draft.get('manifest')
                tree = _manifest_xml(manifest).get_root_node()
                data = tree.find('data')
                if data is None:
                    data = ET.SubElement(tree, 'data')
                for field in ('title', 'description'):
                    if field in self.kwargs.get('changed_fields', []):
                        node = data.find(field)
                        if node is None:
                            node = ET.SubElement(data, field)
                        node.text = str(draft.get(field) or '')
                manifest = ET.tostring(tree, encoding='unicode')
                package = PluginInstaller(manifest=manifest, base_dir=str(root))
                _, old = _data(path)
                if package.code != old['code'] or str(package.version or '') != old['version']:
                    raise TacticException('Use Publish to change a plugin code or version')
                _write(path / 'manifest.xml', manifest)
        elif action in ('export', 'publish'):
            destination = path
            if action == 'publish':
                version = str(self.kwargs.get('version') or '').strip()
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', version) or version in ('.', '..', 'DEV'):
                    raise TacticException('Enter a release version before publishing')
                _, data = _data(path)
                destination = _package_path(root, data['code'] + '-' + version)
                if destination.exists():
                    raise TacticException('This plugin version already exists')
                FileUndo.copy(str(path), str(destination))
                tree = ET.fromstring((destination / 'manifest.xml').read_text(encoding='utf-8-sig'))
                node = tree.find('data')
                if node is None:
                    node = ET.SubElement(tree, 'data')
                version_node = node.find('version')
                if version_node is None:
                    version_node = ET.SubElement(node, 'version')
                version_node.text = version
                tree.attrib.pop('version', None)
                _write(destination / 'manifest.xml', ET.tostring(tree, encoding='unicode'))
                base['plugin_dir'] = str(destination)
            creator = PluginCreator(**base)
            Command.execute_cmd(creator)
            self._download(Path(creator.get_zip_path()))
            identity = 'plugins:' + destination.relative_to(root).as_posix()
        elif action == 'delete':
            _, data = _data(path)
            for project in Search('sthpw/project').get_sobjects():
                code = project.get_code()
                if code in ('admin', 'sthpw'):
                    continue
                # A shared package must not disappear beneath another project.
                search = Search(SearchType.build_search_type('config/plugin', code))
                relative = path.relative_to(root).as_posix()
                if any(str(row.get_value('rel_dir') or '') == relative or
                       str(row.get_value('rel_dir') or '').startswith(relative + '/')
                       for row in search.get_sobjects()):
                    raise TacticException('Remove this plugin from every project before deleting its files')
            FileUndo.remove(str(path))
            archive_name = data['code'].split('/')[-1] + ('-' + data['version'] if data['version'] else '') + '.zip'
            for archive in (Path(str(path) + '.zip'), _package_path(Environment.get_dist_dir(), archive_name)):
                if archive.is_file():
                    FileUndo.remove(str(archive))
            identity = ''
        elif action == 'clear_spt':
            for item in path.rglob('*.spt'):
                FileUndo.remove(str(_file(path, item.relative_to(path).as_posix())))
        elif action in ('new_file', 'new_folder', 'rename', 'delete_file', 'upload', 'download_file'):
            self._file_action(action, path)
        else:
            raise TacticException('Unknown plugin operation: ' + str(action))
        return identity

    def _export_resources(self, base, data, manifest):
        # The native dumper, filesystem journal and surrounding Command share one transaction.
        Command.execute_cmd(PluginCreator(**base, manifest=manifest, register=False))
        installed = Search.get_by_code('config/plugin', data['code'])
        installed.set_value('manifest', manifest)
        installed.commit()

    def _file_action(self, action, path):
        name = str(self.kwargs.get('path') or '')
        target = _file(path, name)
        if action in ('new_file', 'new_folder') and target.exists():
            raise TacticException('A file or folder with that name already exists')
        if action in ('rename', 'delete_file', 'download_file') and not target.exists():
            raise TacticException('The selected plugin file no longer exists')
        if action == 'new_file':
            _write(target, '')
        elif action == 'new_folder':
            FileUndo.mkdir(str(target))
        elif action == 'rename':
            destination = _file(path, str(self.kwargs.get('destination') or ''))
            if destination.exists() or destination.is_relative_to(target):
                raise TacticException('Choose an unused destination outside the source folder')
            if target == path / 'manifest.xml':
                raise TacticException('The package manifest cannot be renamed')
            FileUndo.move(str(target), str(destination))
        elif action == 'delete_file':
            if target == path / 'manifest.xml' or (path / 'manifest.xml').is_relative_to(target):
                raise TacticException('The package manifest cannot be deleted')
            FileUndo.remove(str(target))
        elif action == 'upload':
            source = _package_path(Environment.get_upload_dir(), self.kwargs.get('upload_file_name') or '')
            if not source.is_file():
                raise TacticException('Uploaded file does not exist')
            if target.exists() and (target.is_dir() or self.kwargs.get('confirmation') is not True):
                raise TacticException('Confirm replacement of the existing plugin file')
            if target == path / 'manifest.xml':
                if source.stat().st_size > 2 * 1024 * 1024:
                    raise TacticException('Plugin manifest is too large')
                package = PluginInstaller(manifest=source.read_text(encoding='utf-8-sig'))
                _, old = _data(path)
                if package.code != old['code'] or str(package.version or '') != old['version']:
                    raise TacticException('Use Publish to change a plugin code or version')
            FileUndo.mkdir(str(target.parent))
            FileUndo.copy(str(source), str(target))
        elif action == 'download_file':
            if not target.is_file():
                raise TacticException('Select a file to download')
            self._download(target)

    def _download(self, source):
        cache = Path(Environment.get_asset_dir()) / '_cache' / Environment.get_ticket() / ('plugin-' + uuid.uuid4().hex)
        FileUndo.mkdir(str(cache))
        FileUndo.copy(str(source), str(cache / source.name))
        self.info['download'] = dict(directory=cache.name, filename=source.name)

    def _install(self, action):
        if action == 'install':
            source = _package_path(Environment.get_upload_dir(), self.kwargs.get('upload_file_name') or '')
        else:
            url = self.kwargs.get('url') or ''
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
                raise TacticException('Enter an HTTP or HTTPS plugin ZIP URL without credentials')
            source = _package_path(Environment.get_upload_dir(), 'plugin-' + uuid.uuid4().hex + '.zip')
            FileUndo.mkdir(str(source.parent))
            FileUndo.create(str(source), io_action=False)
            with urllib.request.urlopen(url, timeout=30) as response, source.open('xb') as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 64 * 1024 * 1024:
                        raise TacticException('Plugin download exceeds 64 MiB')
                    output.write(chunk)
            checksum = str(self.kwargs.get('checksum') or '').strip().lower()
            if checksum:
                if not re.fullmatch(r'(?:[0-9a-f]{32}|[0-9a-f]{64})', checksum):
                    raise TacticException('Enter a SHA-256 or MD5 checksum')
                algorithm = 'md5' if len(checksum) == 32 else 'sha256'
                with source.open('rb') as stream:
                    actual = hashlib.file_digest(stream, algorithm).hexdigest()
                if actual != checksum:
                    raise TacticException('Plugin checksum does not match')
        return _checked_zip(source)

    def _create(self):
        draft = self.kwargs.get('document') or {}
        kind = draft.get('type', '')
        if kind == 'project':
            if Project.get_project_code() in ('admin', 'sthpw'):
                raise TacticException('Select a business project to export a template')
            from tactic.command import ProjectTemplateCreatorCmd
            command = ProjectTemplateCreatorCmd(project_code=Project.get_project_code())
            Command.execute_cmd(command)
            self._download(Path(command.get_zip_path()))
            return ''
        code = str(draft.get('code') or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', code):
            raise TacticException('Enter a plugin code using letters, digits, underscores and slashes')
        path = _package_path(_roots()['plugins'], code)
        if path.exists():
            raise TacticException('This plugin directory already exists')
        if kind not in ('', 'project', 'widget', 'column', 'theme'):
            raise TacticException('Select a supported plugin type')
        tree = ET.Element('manifest')
        data = ET.SubElement(tree, 'data')
        for field in ('code', 'title', 'description'):
            ET.SubElement(data, field).text = code if field == 'code' else str(draft.get(field) or '')
        if kind:
            view = code.replace('/', '.')
            config = SearchType.create('config/widget_config')
            view = view if re.match(r'[A-Za-z_]', view) else 'plugin.' + view
            config.set_value('view', view)
            config.set_value('search_type', 'ALL')
            config.set_value('widget_type', kind)
            config.set_value('category', 'PluginTheme' if kind == 'theme' else 'CustomLayoutWdg')
            config.set_value('config', Resources.scaffold(kind, view))
            config.commit()
            ET.SubElement(tree, 'sobject', search_type='config/widget_config', view=view,
                          path='config/config_widget_config.spt')
        command = PluginCreator(code=code, title=draft.get('title') or code,
                                description=draft.get('description') or '',
                                manifest=ET.tostring(tree, encoding='unicode'), register=True, verbose=False)
        Command.execute_cmd(command)
        return 'plugins:' + path.relative_to(_roots()['plugins']).as_posix()
