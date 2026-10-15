###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#


"""Original backend plugin installer; native paths and transactional failures.

Packages execute trusted server Python. Administrator/Command access is required.
Backend install/export/uninstall use native transactions; old UI rendering remains unported.
"""
import os
import functools
import re
import stat
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

from pyasm.common import Xml, Environment, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Project, Schema
from pyasm.command import Command
from pyasm.search import Search, SearchType, SearchException, CreateTable, DbContainer, TableUndo, FileUndo
from pyasm.security import Sudo
from tactic.command.python_cmd import check_script_execution

__all__ = ['PluginBase', 'PluginCreator', 'PluginInstaller', 'PluginUninstaller', 'PluginTools']

from pyasm.search import TableDataDumper, TableSchemaDumper
from pyasm.search.sql_dumper import _open_dump


def _package_path(base, name):
    # Resolve symlinks as well as lexical traversal on both Windows and Linux.
    path = Path(base).resolve() / name
    if not path.resolve().is_relative_to(Path(base).resolve()):
        raise TacticException('Package path escapes its directory: ' + str(name))
    return path.resolve()


def _unsupported_view(*args, **kwargs):
    raise UnsupportedContract('Plugin SQL views are not migrated')


def _manifest_xml(manifest):
    if '<!DOCTYPE' in manifest or '<!ENTITY' in manifest:
        raise TacticException('DTD/entities are not accepted in manifests')
    # Keep the original manifest text in the plugin row; comments are not nodes
    # selected by the original manifest/* XPath. ET also handles CDATA safely.
    return Xml(ET.tostring(ET.fromstring(manifest), encoding='unicode'))


class PluginBase(Command):
    UNIQUE_DICT = {
        'config/widget_config': ['view', 'search_type', 'category', 'widget_type', 'login'],
        'config/naming': ['search_type', 'context', 'checkin_type', 'snapshot_type', 'condition',
                          'latest_versionless', 'current_versionless', 'manual_version'],
        'config/custom_script': ['folder', 'title'],
        'config/url': ['url'],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.verbose = kwargs.get('verbose') not in (False, 'false')
        self.code, self.version = kwargs.get('code'), kwargs.get('version')
        self.base_dir = str(Path(kwargs.get('base_dir') or Environment.get_plugin_dir()).resolve())
        self.plugin_dir = kwargs.get('plugin_dir')
        self.manifest = kwargs.get('manifest')
        self.zip_path = kwargs.get('zip_path')
        upload = kwargs.get('upload_file_name')
        if upload:
            ticket = Environment.get_ticket()
            if not ticket or not re.fullmatch(r'[A-Za-z0-9_.-]+', ticket) or ticket in ('.', '..'):
                raise TacticException('A valid upload ticket is required')
            upload_dir = _package_path(Environment.get_tmp_dir(), 'upload/' + ticket[:100])
            self.zip_path = str(_package_path(upload_dir, upload))
        self.zip_root = None
        if self.zip_path:
            with zipfile.ZipFile(self.zip_path) as archive:
                manifests = []
                for member in archive.infolist():
                    name = PurePosixPath(member.filename)
                    if (name.is_absolute() or '..' in name.parts or chr(92) in member.filename
                            or ':' in member.filename or stat.S_ISLNK(member.external_attr >> 16)):
                        raise TacticException('Unsafe ZIP member: ' + member.filename)
                    if name.name == 'manifest.xml':
                        manifests.append(member.filename)
                # A package can contain nested plugins; choose its outer manifest.
                manifests.sort(key=lambda name: len(PurePosixPath(name).parts))
                if not manifests or len(manifests) > 1 and len(PurePosixPath(manifests[0]).parts) == len(PurePosixPath(manifests[1]).parts):
                    raise TacticException('ZIP must contain one package root manifest.xml')
                self.zip_root = str(PurePosixPath(manifests[0]).parent)
                if self.zip_root != '.' and any(not PurePosixPath(m.filename).is_relative_to(self.zip_root) for m in archive.infolist()):
                    raise TacticException('ZIP files must remain under the package root')
                self.manifest = archive.read(manifests[0]).decode('utf-8-sig')
        elif kwargs.get('relative_dir'):
            self.plugin_dir = str(_package_path(self.base_dir, kwargs['relative_dir']))
        elif kwargs.get('search_key') or self.code and not self.manifest and not self.plugin_dir:
            plugin = (Search.get_by_search_key(kwargs['search_key']) if kwargs.get('search_key')
                      else Search.get_by_code('config/plugin', self.code))
            if plugin is None:
                raise TacticException('No plugin found: ' + str(self.code or kwargs.get('search_key')))
            self.code, self.version = plugin.get_code(), plugin.get_value('version')
            self.plugin_dir = str(_package_path(self.base_dir, plugin.get_value('rel_dir') or self.code))
            self.manifest = plugin.get_value('manifest')
        if self.plugin_dir and not self.zip_path:
            self.plugin_dir = str(Path(self.plugin_dir).resolve())
            manifest_path = Path(self.plugin_dir) / 'manifest.xml'
            if manifest_path.exists():
                self.manifest = manifest_path.read_text(encoding='utf-8-sig')
        if not self.manifest:
            raise TacticException('No plugin manifest found')
        self.xml = _manifest_xml(self.manifest)
        if self.xml.get_root_node().tag != 'manifest':
            raise TacticException('Expected manifest XML root')
        self.code = self.code or self.xml.get_value('manifest/data/code') or self.xml.get_value('manifest/@code')
        self.version = self.version or self.xml.get_value('manifest/data/version') or self.xml.get_value('manifest/@version')
        if self.code and (not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', self.code)
                          or any(part in ('.', '..') for part in self.code.split('/'))):
            raise TacticException('Invalid package code: ' + str(self.code))
        if self.version and (not re.fullmatch(r'[A-Za-z0-9_.-]+', self.version) or self.version in ('.', '..')):
            raise TacticException('Invalid package version: ' + str(self.version))
        if not self.code:
            raise TacticException('Plugin code is required')
        if not self.plugin_dir:
            name = self.code + ('-' + self.version if self.version else '')
            self.plugin_dir = str(_package_path(self.base_dir, name))

    def _extract_package(self):
        if not self.zip_path:
            return
        check_script_execution()
        destination = Path(self.plugin_dir)
        if not destination.is_relative_to(Path(self.base_dir)):
            raise TacticException('ZIP destination must remain under base_dir')
        if destination.exists():
            FileUndo.remove(str(destination))
        FileUndo.mkdir(str(destination))
        # Recheck the archive here: the constructor can run before Command starts.
        with zipfile.ZipFile(self.zip_path) as archive:
            for member in archive.infolist():
                name = PurePosixPath(member.filename)
                if (name.is_absolute() or '..' in name.parts or chr(92) in member.filename
                        or ':' in member.filename or stat.S_ISLNK(member.external_attr >> 16)):
                    raise TacticException('Unsafe ZIP member: ' + member.filename)
                if self.zip_root != '.':
                    name = name.relative_to(self.zip_root)
                target = _package_path(destination, str(name))
                if member.is_dir():
                    FileUndo.mkdir(str(target))
                else:
                    FileUndo.mkdir(str(target.parent))
                    FileUndo.create(str(target), io_action=False)
                    with archive.open(member) as src, target.open('xb') as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
        if (destination / 'manifest.xml').read_bytes().decode('utf-8-sig') != self.manifest:
            raise TacticException('Package manifest changed before installation')

    def get_sobjects_by_node(self, node):
        # get the sobjects
        search_type = self.xml.get_attribute(node, "search_type")
        expr = self.xml.get_attribute(node, "expression")
        code = self.xml.get_attribute(node, "code")
    
        try:
            search_type_sobj = SearchType.get(search_type)
        except SearchException as e:
            return []
    
    
        if expr:
            sudo = Sudo()
            try:
                sobjects = Search.eval(expr)
            finally:
                sudo.exit()
    
    
            # order by id
            def sort_sobjects(a, b):
                a_id = a.get_code()
                b_id = b.get_code()
    
                if a_id > b_id:
                    return 1
                elif a_id == b_id:
                    return 0
                else:
                    return -1
    
            #sobjects.sort(sort_sobjects)
            sobjects = sorted(sobjects,key=functools.cmp_to_key(sort_sobjects))
    
    
        elif search_type:
            try:
                search = Search(search_type)
            except SearchException as e:
                return []
    
    
            search.set_show_retired(True)
            if code:
                if search_type == 'sthpw/pipeline' and '/' in code:
                    # Import remaps the project prefix; selection must follow it too.
                    code = Project.get_project_code() + '/' + code.split('/', 1)[1]
                search.add_filter("code", code)
    
    
            # have some specific attributes for specific search types
            # can use wildcards like % and *
            if search_type_sobj.get_base_key() == 'config/widget_config':
                view = Xml.get_attribute(node, "view")
                if view:
                    ignore_columns = 'id,code'
                    Xml.set_attribute(node, "ignore_columns", ignore_columns)
    
                    if view.find("%") != -1 or view.find("*") != -1:
                        view = view.replace("*", "%")
                        view = view.replace("/", ".")
                        search.add_filter("view", view, op="like")
                    else:
                        search.add_filter("view", view)
    
            elif search_type == 'config/url':
                url = Xml.get_attribute(node, "url")
                if url:
                    ignore_columns = 'id,code'
                    Xml.set_attribute(node, "ignore_columns", ignore_columns)
                    if url.find("%") != -1:
                        search.add_filter("url", url, op="like")
                    else:
                        search.add_filter("url", url)
    
    
    
            search.add_order_by("id")
            sobjects = search.get_sobjects()
        else:
            sobjects = []
    
    
        return sobjects

    def get_path_from_node(self, node):
        path = self.xml.get_attribute(node, "path")
        if not path:
            search_type = Xml.get_attribute(node, "search_type")
            if search_type:
                search_type_obj = SearchType.get(search_type)
                search_type = search_type_obj.get_base_key()
                path = "%s.spt" % search_type.replace("/","_")
    
        if path:
            path = str(_package_path(self.plugin_dir, path))
    
        return path


class PluginCreator(PluginBase):
    """Original manifest export on the native Command/file journal."""
    def get_zip_path(self):
        return self.zip_path

    def handle_data(self, node):

        for name in ['code', 'title', 'version', 'description']:
            value = self.kwargs.get(name)
            if value:
                children = self.xml.get_children(node)
                old_node = None
                for child_node in children:
                    child_name = self.xml.get_node_name(child_node)
                    if child_name == name:
                        old_node = child_node

                value_node = self.xml.create_element(name)
                self.xml.set_node_value(value_node, value)
                if old_node is None:
                    self.xml.append_child(node, value_node)
                else:
                    self.xml.replace_child(node, old_node, value_node)

    def dump_sobject(self, node):
        '''dump sobject entries in plugin creation'''
        check_script_execution()
        search_type = self.xml.get_attribute(node, "search_type")
        replace_variable = self.xml.get_attribute(node, "replace_variable")
        include_id = self.xml.get_attribute(node, "include_id")
        if include_id in [True, 'true']:
            include_id = True
        else:
            include_id = False


        ignore_columns = Xml.get_attribute(node, "ignore_columns")
        if ignore_columns:
            ignore_columns = ignore_columns.split(",")
            ignore_columns = [x.strip() for x in ignore_columns]
        else:
            ignore_columns = []

        self._validate_ignore_columns(node, search_type, ignore_columns)

        # FIXME:
        # it is possible that the manifest defines sobjects on search types
        # that don't exist.  This is because it uses the manifest of
        # the new pipeline and not the original ...
        sobjects = self.get_sobjects_by_node(node)
        path = self.get_path_from_node(node)
        if not path:
            raise TacticException('No path specified for exported objects')
        relative_dir_column = Xml.get_attribute(node, 'relative_dir_column')
        if not sobjects:
            if relative_dir_column:
                FileUndo.mkdir(path)
            else:
                with _open_dump(path):
                    pass
            return []

        dumper = TableDataDumper()
        dumper.set_delimiter("#-- Start Entry --#", "#-- End Entry --#")
        dumper.set_include_id(include_id)
        dumper.set_ignore_columns(ignore_columns)
        dumper.set_sobjects(sobjects)
        if isinstance(self, PluginTools):
            dumper.set_skip_invalid_column()

        if replace_variable =="true":
            if search_type == "sthpw/pipeline":
                #regex is looking for a word bfore "/"
                regex = r'^\w+\/'
                dumper.set_replace_token("$PROJECT/", "code", regex)
            elif search_type == "config/process":
                regex = r'^\w+\/'
                dumper.set_replace_token("$PROJECT/", "pipeline_code", regex)


        relative_dir_column = Xml.get_attribute(node, "relative_dir_column")

        dumper.dump_tactic_inserts(path, mode='sobject', relative_dir_column=relative_dir_column)

        print("\t....dumped [%s] entries" % (len(sobjects)))

        return sobjects

    def _validate_ignore_columns(self, node, search_type, ignore_columns):
        '''validate only if unique is set to true'''
        is_unique = self.xml.get_attribute(node, "unique") == 'true'
        if not is_unique:
            return True
        # defaults to ['code']
        restricted_cols = self.UNIQUE_DICT.get(search_type, ['code'])
        for col in restricted_cols:
            if col in ignore_columns:
                raise TacticException("You have '%s' set in ignore_columns and unique='true' set for [%s]. You need to remove this from ignore_columns to enable the unique feature." %(col, search_type))

    def handle_search_type(self, node):
        check_script_execution()

        search_type = self.xml.get_attribute(node, "code")
        if not search_type:
            raise TacticException("No code found for search type in manifest")

        path = self.xml.get_attribute(node, "path")

        if not path:
            path = "%s.spt" % search_type.replace("/", "_")

        path = str(_package_path(self.plugin_dir, path))

        if os.path.exists(path):
            FileUndo.remove(path)

        # dump out search type registration
        search = Search("sthpw/search_object")
        search.add_filter("search_type", search_type)
        sobject = search.get_sobject()
        if not sobject:
            raise TacticException("Search type [%s] does not exist" % search_type)

        dumper = TableDataDumper()
        dumper.set_delimiter("#-- Start Entry --#", "#-- End Entry --#")
        dumper.set_include_id(False)
        dumper.set_sobjects([sobject])
        dumper.dump_tactic_inserts(path, mode='sobject')


        ignore_columns = Xml.get_attribute(node, "ignore_columns")
        if ignore_columns:
            ignore_columns = ignore_columns.split(",")
            ignore_columns = [x.strip() for x in ignore_columns]
        else:
            ignore_columns = []


        # dump out the table definition
        dumper = TableSchemaDumper(search_type)
        dumper.set_delimiter("#-- Start Entry --#", "#-- End Entry --#")
        dumper.set_ignore_columns(ignore_columns)
        dumper.dump_to_tactic(path, mode='sobject')

    def handle_python(self, node):
        path = self.xml.get_attribute(node, "path")
        if not path:
            raise TacticException("No path found for python in manifest")

        if not path.endswith('.py'):
            raise TacticException("Path should have the .py extension for python in manifest")

        path = str(_package_path(self.plugin_dir, path))
        if not os.path.exists(path):
            raise TacticException("Path [%s] does not exist." %path)

    def execute(self):
        check_script_execution()
        if self.zip_path:
            raise UnsupportedContract('Export from a ZIP source is not migrated; use its extracted directory')
        if Project.get_project_code() not in ('admin', 'sthpw'):
            resource = Project.get().get_project_db_resource()
            resource.get_database_impl().upgrade_project_config(resource)
        if Path(self.plugin_dir).resolve() == Path(self.plugin_dir).resolve().parent:
            raise TacticException('A filesystem root cannot be a package directory')
        self._cleaned_paths = set()
        self._includes = set()
        clean = self.kwargs.get('clean') not in (False, 'false', None)
        if Path(self.plugin_dir).exists() and clean:
            if self.kwargs.get('force') not in (True, 'true'):
                raise TacticException('Plugin is already located at [%s]' % self.plugin_dir)
            FileUndo.remove(self.plugin_dir)
        FileUndo.mkdir(self.plugin_dir)
        nodes = self.xml.get_nodes('manifest/*')
        self.delete_files(nodes)
        sobjects = self._export_nodes(nodes)
        data = self.xml.get_node('manifest/data')
        if data is None:
            data = self.xml.create_element('data')
            child = self.xml.get_first_child(self.xml.get_root_node())
            if child is None:
                self.xml.append_child(self.xml.get_root_node(), data)
            else:
                self.xml.insert_before(data, child)
        self.kwargs.setdefault('code', self.code)
        if self.version:
            self.kwargs.setdefault('version', self.version)
        self.handle_data(data)
        self.manifest = self.xml.to_string()
        manifest_path = _package_path(self.plugin_dir, 'manifest.xml')
        if manifest_path.exists():
            FileUndo.remove(str(manifest_path))
        with _open_dump(manifest_path) as output:
            output.write(self.manifest)
        dist = Path(self.kwargs.get('dist_dir') or Environment.get_dist_dir()).resolve()
        if dist.is_relative_to(Path(self.plugin_dir).resolve()):
            raise TacticException('ZIP output cannot be inside the package directory')
        zip_path = _package_path(dist, self.code.split('/')[-1] + ('-' + self.version if self.version else '') + '.zip')
        FileUndo.mkdir(str(dist))
        if zip_path.exists():
            FileUndo.remove(str(zip_path))
        FileUndo.create(str(zip_path), io_action=False)
        with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            self.zip_dir(archive, self.plugin_dir, self.code)
        self.zip_path = str(zip_path)
        if self.kwargs.get('register') in (True, 'true'):
            if Search.get_by_code('config/plugin', self.code):
                raise TacticException('Plugin [%s] already existed in the project.' % self.code)
            plugin = SearchType.create('config/plugin')
            plugin.set_value('code', self.code)
            if self.version:
                plugin.set_value('version', self.version)
            plugin.set_value('manifest', self.manifest)
            directory = Path(self.plugin_dir).resolve()
            if directory.is_relative_to(Path(self.base_dir)):
                plugin.set_value('rel_dir', directory.relative_to(self.base_dir).as_posix())
            plugin.commit()
            if plugin.get_value('type', no_exception=True) == 'config':
                for sobject in sobjects:
                    content = SearchType.create('config/plugin_content')
                    content.set_value('search_type', sobject.get_search_type())
                    content.set_value('search_code', sobject.get_code())
                    content.set_value('plugin_code', self.code)
                    content.commit()

    def _export_nodes(self, nodes):
        sobjects = []
        for node in nodes:
            name = self.xml.get_node_name(node)
            if name == 'data':
                continue
            if name == 'sobject':
                sobjects.extend(self.dump_sobject(node))
            elif name == 'search_type':
                self.handle_search_type(node)
            elif name == 'include':
                sobjects.extend(self.handle_include(node))
            elif name == 'python':
                self.handle_python(node)
            elif name == 'plugin':
                self.handle_plugin(node)
            else:
                raise UnsupportedContract('Plugin export node is not migrated: ' + name)
        return sobjects

    def delete_files(self, nodes):
        check_script_execution()
        for node in nodes:
            if self.xml.get_node_name(node) not in ('sobject', 'search_type'):
                continue
            if self.xml.get_node_name(node) == 'search_type':
                name = self.xml.get_attribute(node, 'path') or self.xml.get_attribute(node, 'code').replace('/', '_') + '.spt'
                path = str(_package_path(self.plugin_dir, name))
            else:
                path = self.get_path_from_node(node)
            cleaned = getattr(self, '_cleaned_paths', set())
            if path and path not in cleaned:
                if Path(path).exists():
                    FileUndo.remove(path)
                cleaned.add(path)
                self._cleaned_paths = cleaned

    def handle_include(self, node):
        path = self.xml.get_attribute(node, 'path')
        if not path or not path.endswith('.py'):
            raise TacticException('A Python include path is required')
        path = str(_package_path(self.plugin_dir, path))
        includes = getattr(self, '_includes', set())
        if path in includes:
            raise TacticException('Recursive manifest include: ' + path)
        self._includes = includes
        from tactic.command import PythonCmd
        manifest = PythonCmd(file_path=path).execute()
        if not manifest:
            return []
        previous = self.xml
        self.xml = _manifest_xml(manifest)
        includes.add(path)
        try:
            if self.xml.get_root_node().tag != 'manifest':
                raise TacticException('Expected included manifest XML root')
            nodes = self.xml.get_nodes('manifest/*')
            self.delete_files(nodes)
            return self._export_nodes(nodes)
        finally:
            self.xml = previous
            includes.remove(path)

    def handle_plugin(self, node):
        raise UnsupportedContract('Nested plugin export is not migrated')

    def zip_dir(self, zip, base_dir, plugin, rel_dir=''):
        check_script_execution()
        directory = _package_path(base_dir, rel_dir)
        for path in sorted(directory.rglob('*')):
            relative = path.relative_to(Path(base_dir).resolve())
            _package_path(base_dir, relative)
            if path.is_symlink():
                raise TacticException('Package symlinks are not accepted: ' + str(relative))
            if '.svn' in relative.parts or not path.is_file():
                continue
            zip.write(path, PurePosixPath(Path(base_dir).name, relative.as_posix()).as_posix())


class PluginInstaller(PluginBase):
    def execute(self):

        check_script_execution()
        if self.kwargs.get('mode') not in (None, '', 'install'):
            raise UnsupportedContract('Deprecated plugin registration mode is not migrated')
        if Project.get_project_code() not in ('admin', 'sthpw'):
            resource = Project.get().get_project_db_resource()
            resource.get_database_impl().upgrade_project_config(resource)
        self._extract_package()

        # install the plugin
        mode = self.kwargs.get("mode")
        if not mode:
            mode = 'install'

        nodes = self.xml.get_nodes("manifest/*")

        # register the plugin.
        register = self.kwargs.get("register")
        code = None
        plugin = None
        if register in ['true', True]:
            node = self.xml.get_node("manifest/data")
            data = {child.tag: self.xml.get_node_value(child) for child in node} if node is not None else {}

            code = data.get("code") or self.code
            version = data.get("version")

            # first check if a plugin with this code already exists
            plugin = Search.get_by_code("config/plugin", code)
            if plugin:
                # uninstall the plugin???
                pass
            else:
                # create a new one
                plugin = SearchType.create("config/plugin")
                if code:
                    plugin.set_value("code", code)


            # update the information
            if version:
                plugin.set_value("version", version)

            # NOTE: is this really needed?
            plugin.set_value("manifest", self.manifest)

            if Path(self.plugin_dir).is_relative_to(Path(self.base_dir)):
                rel_dir = Path(self.plugin_dir).relative_to(self.base_dir).as_posix()
                plugin.set_value("rel_dir", rel_dir)

            plugin.commit()

        self.plugin = plugin



        self.import_manifest(nodes)

        # Users see Activate in the UI
        label = mode
        if mode == 'install':
            label = 'activate'

        if code:
            self.add_description('%s plugin [%s]' % (label.capitalize(), code))

    def import_manifest(self, nodes):

        tools = PluginTools(**dict(self.kwargs, plugin_dir=self.plugin_dir))

        paths_read = []

        for node in nodes:

            node_name = self.xml.get_node_name(node)
            if node_name not in ('data', 'plugin', 'search_type', 'sobject', 'include', 'python'):
                raise UnsupportedContract('Plugin manifest node is not migrated: ' + node_name)
            if node_name == "plugin":

                plugin_code = self.xml.get_attribute(node, 'code')
                mode = self.xml.get_attribute(node, 'mode')

                if mode == "absolute":
                    plugin_base_dir = Environment.get_plugin_dir()
                    plugin_dir = str(_package_path(plugin_base_dir, plugin_code))
                else:
                    plugin_dir = str(_package_path(self.plugin_dir, plugin_code))

                print("Installing plugin: ", plugin_dir)
                installer = PluginInstaller(plugin_dir=plugin_dir, verbose=False, register=True)
                installer.execute()



            elif node_name == 'search_type':
                search_type = self.xml.get_attribute(node, 'code')

                # implicitly add the entry to the schema table.
                # Reset the cache every time to ensure that any updates to
                # the scehma are reflected here.
                schema = Schema.get(reset_cache=True)
                xml = Xml(schema.get_value("schema"))
                schema_node = xml.get_node("schema/search_type[@name='%s']" % search_type)
                parent = xml.get_node("schema")
                if schema_node is None:
                    schema_node = xml.create_element("search_type")
                    xml.set_attribute(schema_node, "name", search_type)

                    #parent = xml.get_parent(node)
                    xml.append_child(parent, schema_node)
                    schema.set_value('schema', xml.to_string() )
                    schema.commit()

                    # TODO: connections?

                path = self.xml.get_attribute(node, "path")
                if not path:
                    path = "%s.spt" % search_type.replace("/", "_")

                path = str(_package_path(self.plugin_dir, path))

                if path in paths_read:
                    continue

                if self.verbose:
                    print("Reading search_type: ", path)

                # NOTE: priviledged knowledge of the order or return values
                jobs = tools.import_data(path, commit=True)

                paths_read.append(path)

                if not jobs:
                    continue

                search_type_obj = jobs[0]

                if len(jobs) == 1:
                    # only the search type was defined
                    table = None
                else:
                    table = jobs[1]


                try:
                    # check to see if the search type already exists
                    search_type_chk = SearchType.get(search_type)
                    if search_type_chk:
                        if self.verbose:
                            print('WARNING: Search Type [%s] is already registered' % search_type_chk.get_value("search_type"))
                    else:
                        search_type_obj.commit()
                except SearchException as e:
                    if e.__str__().find('not registered') != -1:
                        search_type_obj.commit()

                if table and getattr(table, "_plugin_created", False):
                    TableUndo.log(search_type, table.get_database(), table.get_table())

                # import the backup data back
                backup_dir = "%s/backup" % self.plugin_dir
                backup_path = str(_package_path(backup_dir, search_type.replace("/", "_") + '.spt'))
                tools_backup = PluginTools(plugin_dir=self.plugin_dir, verbose=self.verbose)
                if os.path.exists(backup_path):
                    tools_backup.import_data(backup_path)
                    sql = DbContainer.get(table.db_resource if table else Project.get_db_resource_by_search_type(search_type))
                    sql.get_database_impl().ensure_table_sequence(sql, SearchType.get(search_type).get_table())
                    FileUndo.remove(backup_path)
                    if not os.listdir(backup_dir):
                        FileUndo.rmdir(backup_dir)


            elif node_name == 'sobject':
                path = self.xml.get_attribute(node, "path")
                search_type = self.xml.get_attribute(node, "search_type")
                seq_max = self.xml.get_attribute(node, "seq_max") or 0
                try:
                    if seq_max:
                        seq_max = int(seq_max)
                except ValueError:
                    seq_max = 0

                if not path:
                    if search_type:
                        path = "%s.spt" % search_type.replace("/","_")
                if not path:
                    raise TacticException("No path specified")

                path = str(_package_path(self.plugin_dir, path))
                if path in paths_read:
                    continue

                unique = self.xml.get_attribute(node, "unique")
                if unique == 'true':
                    unique = True
                else:
                    unique = False

                if self.verbose:
                    print("Reading: ", path)


                ignore_columns = Xml.get_attribute(node, "ignore_columns")
                if ignore_columns:
                    ignore_columns = ignore_columns.split(",")
                    ignore_columns = [x.strip() for x in ignore_columns]
                else:
                    ignore_columns = []


                # jobs doesn't matter for sobject node
                jobs = tools.import_data(path, unique=unique, ignore_columns=ignore_columns)

                # reset it in case it needs to execute a PYTHON tag right after
                Schema.get(reset_cache=True)
                if search_type:
                    st_obj = SearchType.get(search_type)
                    sql = DbContainer.get(Project.get_db_resource_by_search_type(search_type))
                    sql.get_database_impl().ensure_table_sequence(sql, st_obj.get_table(), seq_max)

                paths_read.append(path)


            elif node_name == 'include':

                path = self.xml.get_attribute(node, "path")

                path = str(_package_path(self.plugin_dir, path))

                from tactic.command import PythonCmd
                cmd = PythonCmd(file_path=path)
                manifest = cmd.execute()

                if manifest:
                    xml = _manifest_xml(manifest)
                    nodes = xml.get_nodes("manifest/*")

                    previous_xml = self.xml
                    self.xml = xml
                    try:
                        self.import_manifest(nodes)
                    finally:
                        self.xml = previous_xml

            elif node_name == 'python':

                path = self.xml.get_attribute(node, "path")
                path = str(_package_path(self.plugin_dir, path))

                # just run the python script
                from tactic.command import PythonCmd
                cmd = PythonCmd(file_path=path)
                cmd.execute()




class PluginUninstaller(PluginBase):

    def execute(self):
        check_script_execution()
        if self.zip_path:
            raise UnsupportedContract('Uninstall requires an installed package directory, not a ZIP')
        active = self.kwargs.setdefault('_uninstalling', set())
        if active is None:
            active = self.kwargs['_uninstalling'] = set()
        directory = str(Path(self.plugin_dir).resolve())
        if directory in active:
            raise TacticException('Recursive plugin uninstall: ' + directory)
        self._includes = set()
        active.add(directory)
        try:
            # uninstall the plugin
            nodes = self.xml.get_nodes("manifest/*")

            nodes.reverse()

            self.handle_nodes(nodes)

            self.add_description('Remove plugin [%s]' %self.code)

        finally:
            active.remove(directory)

    def handle_nodes(self, nodes):
        check_script_execution()
        tools = PluginTools(plugin_dir=self.plugin_dir, verbose=self.verbose)

        depth = getattr(self, '_uninstall_depth', 0)
        self._uninstall_depth = depth + 1
        try:
            for node in nodes:
                node_name = self.xml.get_node_name(node)
                if node_name == 'data':
                    continue
                elif node_name == 'search_type':
                    #self.remove_search_type(node)
                    tools._remove_search_type(node)
                elif node_name == 'sobject':
                    self.remove_sobjects(node)
                elif node_name == 'include':
                    self.handle_include(node)
                elif node_name == 'python':
                    self.handle_python(node)
                elif node_name == 'plugin':
                    self.handle_plugin(node)
                else:
                    raise UnsupportedContract('Plugin uninstall node is not migrated: ' + node_name)
        finally:
            self._uninstall_depth = depth
        if depth == 0:
            # remove plugin contents
            search = Search("config/plugin_content")
            search.add_filter("plugin_code", self.code)
            plugin_contents = search.get_sobjects()
            for plugin_content in plugin_contents:
                plugin_content.delete()



            # deregister the plugin
            plugin = Search.get_by_code("config/plugin", self.code)
            if plugin:
                plugin.delete()

    def handle_plugin(self, node):

        plugin_code = self.xml.get_attribute(node, 'code')
        print("Uninstalling plugin [%s]: " % plugin_code)
        mode = self.xml.get_attribute(node, 'mode')
        if not plugin_code:
            raise TacticException('Nested plugin code is required')
        base = Environment.get_plugin_dir() if mode == 'absolute' else self.plugin_dir
        plugin_dir = str(_package_path(base, plugin_code))

        uninstaller = PluginUninstaller(plugin_dir=plugin_dir, verbose=False, _uninstalling=self.kwargs.get("_uninstalling"))
        uninstaller.execute()



    def remove_sobjects(self, node):

        sobjects = self.get_sobjects_by_node(node)
        if not sobjects:
            #print("Skipping as no sobjects found for: ", node)
            return

        # delete all the sobjects present in the plugin
        for sobject in sobjects:
            sobject.delete()


    def handle_include(self, node):
        path = self.xml.get_attribute(node, "path")
        if not path:
            raise TacticException("No path found for search type in manifest")

        path = str(_package_path(self.plugin_dir, path))

        if not path.endswith('.py'):
            raise TacticException('A Python include path is required')
        includes = getattr(self, '_includes', set())
        self._includes = includes
        if path in includes:
            raise TacticException('Recursive manifest include: ' + path)
        from tactic.command import PythonCmd
        manifest = PythonCmd(file_path=path).execute()
        if not manifest:
            return
        previous = self.xml
        self.xml = _manifest_xml(manifest)
        self._includes.add(path)
        try:
            if self.xml.get_root_node().tag != 'manifest':
                raise TacticException('Expected included manifest XML root')
            nodes = self.xml.get_nodes('manifest/*')
            nodes.reverse()
            self.handle_nodes(nodes)
        finally:
            self.xml = previous
            self._includes.remove(path)

    def handle_python(self, node):
        '''during uninstall, handle the python undo_path'''
        path = self.xml.get_attribute(node, "undo_path")

        # if no path, then nothing to undo
        if not path:
            print("No undo_path defined for this python node")
            return

        if not path.endswith('.py'):
            raise TacticException("Path should have the .py extension for python in manifest")

        path = str(_package_path(self.plugin_dir, path))
        if not os.path.exists(path):
            raise TacticException("Undo Path [%s] does not exist python in manifest" %path)
        if path.endswith(".py"):
            from tactic.command import PythonCmd
            cmd = PythonCmd(file_path=path)
            cmd.execute()

class PluginTools(PluginBase):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.xml = kwargs.get("xml")

        self.plugin_dir = kwargs.get("plugin_dir")
        if not self.plugin_dir:
            self.plugin_dir = "."

        self.verbose = self.kwargs.get("verbose") not in [False, 'false']

        self.plugin = kwargs.get("plugin")

    def get_unique_sobject(self, sobject):
        '''get unique sobject in the existing table when installing plugin'''
        base_st = sobject.get_base_search_type()
        cols = self.UNIQUE_DICT.get(base_st, ['code'])

        search = Search( sobject.get_base_search_type(), sudo=True )
        has_filter = False
        for col in cols:
            value = sobject.get_value(col)
            if value:
                search.add_filter(col, value)
                has_filter = True
            else:
                search.add_filter(col, None)

        # ensure there is some filtering before getting sobject
        if has_filter:
            unique_sobject = search.get_sobject()
        else:
            unique_sobject = None
        return unique_sobject

    def import_data(self, path, commit=True, unique=False, ignore_columns=[]):

        check_script_execution()
        if not os.path.exists(path):
            # This is printed too often in harmless situations
            #print("WARNING: path [%s] does not exist" % path)
            # Original exports omit SPT files for empty tables. The manifest
            # still lists them, including their sequence floor.
            return []


        if os.path.isdir(path):
            files = sorted(p for p in Path(path).rglob('*') if p.is_file())
        else:
            files = [Path(path)]
        f = []
        for source_path in files:
            _package_path(self.plugin_dir, str(source_path.resolve().relative_to(Path(self.plugin_dir).resolve())))
            f.extend(source_path.read_text(encoding='utf-8-sig').splitlines(True))
            f.append("\n")

        statement = []
        in_entry = False
        count = 1

        insert = None
        table = None
        sobject = None

        jobs = []

        filter_line_handler = self.kwargs.get('filter_line_handler')
        filter_sobject_handler = self.kwargs.get('filter_sobject_handler')

        for line in f:

            # FIXME: this SQLServer specific
            #if line.startswith("insert.set_value('Version'"):
            #    #line = "insert.set_value('Version', '')"
            #    continue


            if filter_line_handler:
                line = filter_line_handler(path, line)
                if line == None:
                    continue


            if line.startswith("#-- Start Entry --#"):
                if in_entry:
                    raise TacticException("Nested SPT entry: " + str(path))
                in_entry = True
                statement = []
            elif line.startswith("#-- End Entry --#"):
                if not in_entry:
                    raise TacticException("SPT end without start: " + str(path))
                in_entry = False
                if not statement:
                    continue
                # strip out a line feeds and add proper new lines
                statement.insert(0, "from pyasm.search import SearchType, CreateTable, Search")
                statement_str = "\n".join([x.rstrip("\r\n") for x in statement])

                namespace = {'CreateView': _unsupported_view}
                exec(statement_str, namespace)
                insert, table = namespace.get('insert'), namespace.get('table')

                sobject = insert

                if sobject:
                    jobs.append(sobject)

                    stype_id  = 0
                    if sobject.get_base_search_type() =='sthpw/search_object':
                        stype_id = Search.eval("@GET(sthpw/search_object['search_type', '%s'].id)" %sobject.get_value('search_type'), single=True)

                    else:
                        # if there is an id, then set the sobject to be insert
                        sobject_id = sobject.get_id()
                        if sobject_id and sobject_id != -1:
                            sobject.set_force_insert(True)


                    # if unique, then check to see if it already exists.
                    # Same idea with stype_exists
                    # if so, take the id to turn this from an insert to an
                    # update operation writing over existing data
                    if stype_id:
                        sobject.set_value("id", stype_id)


                    if filter_sobject_handler:
                        sobject = filter_sobject_handler(sobject)
                        if sobject is None:
                            continue



                    # if the search type is in sthpw namespace, then change
                    # the project code to the current project
                    base_search_type = sobject.get_base_search_type()

                    if base_search_type.startswith("config/"):
                        project = Project.get()
                        project_code = project.get_value("code")
                        if base_search_type == "config/process":
                            if "$PROJECT" in sobject.get('pipeline_code'):
                                old_code = sobject.get('pipeline_code')
                                new_code = old_code.replace("$PROJECT",project_code,1)
                                sobject.set_value('pipeline_code',new_code)

                            else:
                                old_pipeline_code = sobject.get("pipeline_code")
                                if old_pipeline_code.find("/") != -1:
                                    parts = old_pipeline_code.split("/", 1)
                                    new_pipeline_code = "%s/%s" % (project_code,parts[1]);
                                    sobject.set_value('pipeline_code',new_pipeline_code)



                    if base_search_type.startswith("sthpw/"):

                        project = Project.get()
                        project_code = project.get_value("code")

                        if SearchType.column_exists(sobject, "project_code"):
                            old_project_code = sobject.get_value("project_code")
                            if "project_code" not in ignore_columns:
                                sobject.set_value("project_code", project_code)
                            else:
                                sobject.set_value("project_code", "__TEMPLATE__")

                        else:
                            old_project_code = None

                        if base_search_type == "sthpw/schema":
                            # if a schema is already defined, the delete
                            # the current one.  This is not necessary
                            # if unique flag is on
                            if not unique:
                                search = Search("sthpw/schema")
                                search.add_filter("code", project_code)
                                old_schema = search.get_sobject()
                                if old_schema:
                                    old_schema.delete()

                            sobject.set_value("code", project_code)


                        if base_search_type == "sthpw/pipeline":

                            if "$PROJECT" in sobject.get('code'):
                                # Not really used
                                old_code = sobject.get('code')
                                new_code = old_code.replace("$PROJECT",project_code,1)
                                search = Search("sthpw/pipeline")
                                search.add_filter("code", new_code)
                                exists = search.get_sobject()
                                sobject.set_value('code',new_code)
                                unique = True

                            else:
                                # This is probably easier to maintain
                                old_code = sobject.get('code')
                                if old_code.find("/") != -1:
                                    parts = old_code.split("/", 1)
                                    new_code =  "%s/%s" % (project.get_code(), parts[1])

                                    search = Search("sthpw/pipeline")
                                    search.add_filter("code", new_code)
                                    exists = search.get_sobject()
                                    sobject.set_value('code',new_code)
                                    unique = True


                        if base_search_type == "sthpw/login_group":
                            if old_project_code:
                                login_group = sobject.get_value("login_group")
                                delimiter = None
                                if login_group.startswith("%s_" % old_project_code):
                                    delimiter = "_"
                                elif login_group.startswith("%s/" % old_project_code):
                                    delimiter = "/"

                                if delimiter:
                                    login_group = login_group[len(old_project_code)+1:]
                                    login_group = "%s%s%s" % (project_code, delimiter, login_group)

                                    sobject.set_value("code", login_group)
                                    sobject.set_value("login_group", login_group)


                            # convert all of xml to this project
                            xml = sobject.get_xml_value("access_rules")
                            nodes = Xml.get_nodes(xml, "rules/rule")
                            for node in nodes:
                                test = xml.get_attribute(node, "project")
                                if test:
                                    xml.set_attribute(node, "project", project_code)

                            sobject.set_value("access_rules", xml.to_string())




                    if unique:
                        unique_sobject = self.get_unique_sobject(sobject)
                        if unique_sobject:
                            sobject.set_value("id", unique_sobject.get_id() )
                            sobject.set_force_insert(False)

                        if sobject == None:
                            continue



                    sudo = Sudo()
                    try:
                        if commit:
                            sobject.commit(triggers=False)
                            # Imported IDs force this INSERT only; cached objects
                            # must return to ordinary UPDATE behavior afterward.
                            sobject.set_force_insert(False)

                            chunk = 100
                            if self.verbose and count and count % chunk == 0:
                                print("\t... handled entry [%s]" % count)


                            if self.plugin and self.plugin.get_value("type", no_exception=True) == "config":
                                plugin_content = SearchType.create("config/plugin_content")
                                plugin_content.set_value("search_type", sobject.get_search_type())
                                plugin_content.set_value("search_code", sobject.get_code())
                                plugin_content.set_value("plugin_code", self.plugin.get_code())
                                plugin_content.commit()

                    finally:
                        sudo.exit()


                if table:
                    jobs.append(table)
                    if commit:
                        sql = DbContainer.get(table.db_resource)
                        table._plugin_created = not sql.get_database_impl().table_exists(table.db_resource, table.get_table())
                        table.commit()
                elif sobject == None:
                    # this is meant for saying the table is None for a search type creation
                    jobs.append(None)

                count += 1
                table = None
                insert = None
                sobject = None
            elif in_entry:
                statement.append(line)

        if in_entry:
            raise TacticException("Unterminated SPT entry: " + str(path))

        if self.verbose:
            print("\t... added [%s] entries" % count)
        return jobs


    def dump_sobject(self, search_type, path):
        self.xml = Xml('<sobject/>')
        node = self.xml.get_root_node()
        self.xml.set_attribute(node, 'path', path)
        self.xml.set_attribute(node, 'search_type', search_type)
        return self._dump_sobject(node)

    def dump_search_type(self, search_type, path):
        self.xml = Xml('<search_type/>')
        node = self.xml.get_root_node()
        self.xml.set_attribute(node, 'path', path)
        self.xml.set_attribute(node, 'code', search_type)
        return self._dump_search_type(node)

    def _dump_sobject(self, node):
        # Original Tools export additionally emits skip_invalid_column().
        # Reuse Creator's selection/variables rather than duplicate the algorithm.
        return PluginCreator.dump_sobject(self, node)

    def _validate_ignore_columns(self, node, search_type, ignore_columns):
        return True

    def _dump_search_type(self, node):
        return PluginCreator.handle_search_type(self, node)


    def remove_search_type(self, search_type):
        self.xml = Xml('<search_type/>')
        node = self.xml.get_root_node()
        self.xml.set_attribute(node, 'code', search_type)
        return self._remove_search_type(node)

    def _remove_search_type(self, node):
        check_script_execution()
        search_type = Xml.get_attribute(node, 'code')
        if not search_type:
            raise TacticException('No code found for search type in manifest')
        search = Search('sthpw/search_object')
        search.add_filter('search_type', search_type)
        search_type_sobj = search.get_sobject()
        if search_type_sobj is None:
            return
        if search_type.startswith(('sthpw/', 'config/')):
            raise UnsupportedContract('Uninstalling system/config table definitions is not migrated')
        from pyasm.search import DropTable, TableDataDumper
        drop = DropTable(search_type)
        sql = DbContainer.get(drop.db_resource)
        sql.check_schema_write()
        if not sql.get_database_impl().table_exists(drop.db_resource, drop.table):
            return
        # Lock before reading: backup and DROP describe the same table contents.
        sql.get_database_impl().lock_table_for_drop(sql, drop.table)
        backup = _package_path(self.plugin_dir, 'backup/' + search_type.replace('/', '_') + '.spt')
        if backup.exists():
            FileUndo.remove(str(backup))
        search = Search(search_type)
        search.set_show_retired(True)
        search.add_order_by('id')
        dumper = TableDataDumper()
        dumper.set_delimiter('#-- Start Entry --#', '#-- End Entry --#')
        dumper.set_sobjects(search.get_sobjects())
        dumper.set_include_id(True)
        dumper.dump_tactic_inserts(str(backup), mode='sobject')
        drop.commit()
        # Original deliberately keeps registry/schema definitions shared by projects.
