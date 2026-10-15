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


"""Original project-template export, installation and checks on the native backend."""
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from pyasm.common import Common, Xml, Environment, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, SearchType, DbContainer
from tactic.command.python_cmd import check_script_execution
from .create_project_cmd import CreateProjectCmd
from .plugin import PluginInstaller, _package_path

__all__ = ['ProjectTemplateInstallerCmd', 'ProjectTemplateCheckCmd', 'ProjectTemplateCreatorCmd']
__all__.append('ProjectTemplateUpdaterCmd')


class ProjectTemplateUpdaterCmd(Command):
    def execute(self):
        check_script_execution()
        raise UnsupportedContract('Original ProjectTemplateUpdaterCmd has no implementation; use ProjectTemplateInstallerCmd(new_project=False) for an explicit import')


class ProjectTemplateInstallerCmd(Command):
    def execute(self):
        check_script_execution()
        if self.kwargs.get('template_code') == 'perforce_like' and not self.kwargs.get('path'):
            if self.kwargs.get('new_project') in (False, 'false'):
                raise ValueError('File-project template only creates new projects')
            creator = CreateProjectCmd(**{**self.kwargs, 'project_mode': 'file_project'})
            creator.execute()
            self.info = creator.get_info()
            return
        self.new_project = self.kwargs.get('new_project') not in (False, 'false')
        self.mode = self.kwargs.get('mode') or 'copy'
        if self.mode != 'copy':
            raise UnsupportedContract('Template move installation is not migrated')
        self.project_code = self.kwargs.get('project_code')
        if not self.project_code:
            raise TacticException('project_code is required')
        self.path = self.kwargs.get('path')
        self.template_code = self.kwargs.get('template_code') or self.project_code
        self.template_project_code = self.template_code
        self.is_template = self.kwargs.get('is_template')
        project = Project.get_by_code(self.project_code)
        if self.new_project and project:
            raise TacticException('Project [%s] already exists in this installation. Exiting...' % self.project_code)
        if not self.new_project and not project:
            raise TacticException('Project does not exist: ' + self.project_code)
        if self.kwargs.get('force_database') and not self.new_project:
            raise UnsupportedContract('Forced database import into an existing project is not supported')
        self.import_template()

    def import_template(self):
        if self.path:
            path = Path(self.path).resolve()
        else:
            version = self.kwargs.get('version')
            name = self.template_code + ('-' + version if version else '')
            path = Path(self.get_template_dir(str(_package_path(Environment.get_template_dir(), name))))
            if not path.exists():
                path = Path(str(path) + '.zip')
            if Project.get_by_code(self.template_code) and not version:
                creator = ProjectTemplateCreatorCmd(project_code=self.template_code)
                creator.execute()
                path = Path(creator.get_zip_path())
        if not path.exists():
            raise TacticException('No template found for [%s]' % self.template_code)
        arguments = {'plugin_dir' if path.is_dir() else 'zip_path': str(path),
                     'base_dir': Environment.get_template_dir(), 'register': True,
                     'filter_sobject_handler': self.filter_sobject_handler,
                     'verbose': self.kwargs.get('verbose', False)}
        installer = PluginInstaller(**arguments)
        # Original packages do not require their directory/ZIP name to be the code.
        self.template_project_code = installer.code
        if self.is_template is None:
            self.is_template = self.template_project_code == self.project_code
        self.is_template = self.is_template in (True, 'true', 'True')
        if self.new_project:
            creator = CreateProjectCmd(project_code=self.project_code,
                project_title=self.kwargs.get('project_title') or Common.get_display_title(self.project_code),
                project_type=self.template_project_code, is_template=self.is_template,
                use_default_side_bar=False, project_image_path=self.kwargs.get('project_image_path'))
            creator.execute()
        Project.set_project(self.project_code)
        installer.execute()
        project = Project.get_by_code(self.project_code)
        if self.kwargs.get('project_title'):
            project.set_value('title', self.kwargs['project_title'])
            project.commit()

    def filter_line_handler(self, path, line):
        return line

    def get_template_dir(self, template_dir):
        '''check if it exists and return the one that does'''
    
        if not os.path.exists(template_dir):
            # for backward compatibility
            template_dir2 = '%s_template' %template_dir
            if not os.path.exists(template_dir2):
                return template_dir
            else:
                return template_dir2
    
        return template_dir

    def remap_pipeline_references(self, sobject):
    
        search_type = sobject.get_base_search_type()
        # Definitions and their references must move together. Legacy exports
        # keep task/subpipeline references in XML and nested workflow JSON.
        reference_keys = {'pipeline_code', 'task_pipeline', 'subpipeline', 'subpipeline_code',
                          'from_pipeline', 'to_pipeline'}
        def pipeline_reference(value):
            if isinstance(value, str) and value.startswith(self.template_project_code + '/'):
                return self.project_code + value[len(self.template_project_code):]
            if isinstance(value, str) and value.startswith(self.template_project_code + '_'):
                return self.project_code + '/' + value
            return value

        def references(value):
            if isinstance(value, dict):
                return {key: pipeline_reference(item) if key in reference_keys else references(item)
                        for key, item in value.items()}
            if isinstance(value, list):
                return [references(item) for item in value]
            return value

        if self.template_project_code != self.project_code:
            for column in reference_keys:
                if SearchType.column_exists(sobject, column):
                    value = sobject.get_value(column)
                    if pipeline_reference(value) != value:
                        sobject.set_value(column, pipeline_reference(value))
            for column in ('workflow', 'data'):
                if search_type in ('config/process', 'config/trigger', 'sthpw/pipeline') and SearchType.column_exists(sobject, column):
                    text = sobject.get_value(column)
                    if text and text.lstrip().startswith(('{', '[')):
                        original = json.loads(text)
                        remapped = references(original)
                        if remapped != original:
                            sobject.set_json_value(column, remapped)
            if search_type == 'sthpw/pipeline' and sobject.get_value('pipeline'):
                text = sobject.get_value('pipeline')
                root = ET.fromstring(text)
                changed = False
                for node in root.iter():
                    for key, value in list(node.attrib.items()):
                        if key in reference_keys and pipeline_reference(value) != value:
                            node.set(key, pipeline_reference(value))
                            changed = True
                if changed:
                    sobject.set_value('pipeline', ET.tostring(root, encoding='unicode'))
    
    def filter_sobject_handler(self, sobject):
        self.remap_pipeline_references(sobject)
        search_type = sobject.get_base_search_type()

        if search_type == 'sthpw/project':
            project = Project.get_by_code(self.project_code)
            if project:
                sobject.set_value("id", project.get_id() )
                sobject.set_force_insert(False)
    
            # change the code of the project
            sobject.set_value("code", self.project_code)
            if SearchType.column_exists(sobject, 'database'):
                sobject.set_value('database', project.get_database_name())
            if SearchType.column_exists(sobject, 'db_resource'):
                sobject.set_value('db_resource', project.get_value('db_resource', no_exception=True), allow_none=True)
    
            title = Common.get_display_title(self.project_code)
            sobject.set_value("title", title)
    
            if self.is_template:
                sobject.set_value("is_template", True)
            else:
                sobject.set_value("is_template", False)
    
        elif search_type == 'sthpw/schema':
            sobject.set_value("code", self.project_code)
    
        elif search_type == 'sthpw/notification':
            sobject.set_value("project_code", self.project_code)
            sobject.set_value("code", "")
    
        elif search_type in ['sthpw/pipeline']:
            sobject.set_value("project_code", self.project_code)
            if self.template_project_code != self.project_code:
                # get the old code
                old_code = sobject.get_code()
                if old_code.startswith("%s/" % self.template_project_code):
                    new_code = old_code.replace("%s/" % self.template_project_code, "%s/" % self.project_code)
                else:
                    new_code = "%s/%s" % (self.project_code, old_code)
                sobject.set_value("code", new_code)
    
        elif search_type in ['sthpw/login_group']:
            sobject.set_value("project_code", self.project_code)
            if self.template_project_code != self.project_code:
    
                # get the old login_group
                for column in ['login_group', 'code']:
                    old_code = sobject.get_value(column)
                    if old_code.startswith("%s/" % self.template_project_code):
                        new_code = old_code.replace("%s/" % self.template_project_code, "%s/" % self.project_code)
                    else:
                        new_code = "%s/%s" % (self.project_code, old_code)
                    sobject.set_value(column, new_code)
    
                # go through the access rules and replace project
                access_rules = sobject.get_xml_value("access_rules")
                nodes = access_rules.get_nodes("rules/rule")
                for node in nodes:
                    project_code = Xml.get_attribute(node, "project")
                    if project_code and project_code != "*" and project_code == self.template_project_code:
                        Xml.set_attribute(node, "project", self.project_code)
                sobject.set_value("access_rules", access_rules.to_string())
    
    
        return sobject


class ProjectTemplateCheckCmd(Command):
    '''This will check the integrity of a project to see if is suitable
    for export as a distributable project template'''

    def execute(self):

        check_script_execution()
        self.project_code = self.kwargs.get("project_code")
        self.prefix = self.kwargs.get("prefix")


        if not isinstance(self.prefix, str) or not self.prefix:
            raise TacticException('prefix is required')
        self.project = Project.get_by_code(self.project_code)
        if not self.project or self.project.is_retired():
            raise TacticException('Project does not exist: ' + str(self.project_code))
        self.project_type = self.project.get_value("type")

        self.check_project()
        self.check_search_type()



    def check_project(self):


        # check that the project code starts with the prefix
        if not self.project.get_code().startswith("%s_" % self.prefix):
            raise TacticException("Project code [%s] does not start with prefix [%s]" % (self.project_code, self.prefix) )


        # check that the project type is the same as the project code
        if self.project_code != self.project_type:
            raise TacticException("Project code [%s] does not match the project_type [%s]" % (self.project_code, self.project_type) )



    def check_search_type(self):

        # all search objects in the namespace of <project_code> should
        # start with the prefix


        search = Search("sthpw/search_object")
        search.add_filter("namespace", self.project_type)
        search_types = search.get_sobjects()


        for search_type in search_types:
            if not search_type.get_value("search_type").startswith("%s_" % self.prefix):
                raise TacticException( "sType [%s] does not start with prefix [%s]" % (search_type.get_value("search_type"), self.prefix) )


class ProjectTemplateCreatorCmd(Command):

    def execute(self):
        check_script_execution()

        self.base_dir = self.kwargs.get("base_dir")
        if not self.base_dir:
            self.base_dir = Environment.get_template_dir()


        self.project_code = self.kwargs.get("project_code")
        if not self.project_code:
            self.project_code = Project.get_project_code()

        assert self.project_code

        # project code can be called anything, and we want to have a _template suffix for the template code
        #self.plugin_code = "%s_template" % self.project_code

        #self.template_project_code = re.sub( '_template$', '', self.plugin_code)
        self.template_project_code = self.project_code
        self.project = Project.get_by_code(self.project_code)
        if not self.project or self.project.is_retired():
            raise TacticException('This project [%s] does not exist'%self.project_code)

        self.project_type = self.project.get_value("type")
        if not self.project_type:
            self.project_type = self.project_code
        Project.set_project(self.project_code)

        self.export_template()


    def export_template(self):
        check_script_execution()

        xml = Xml()
        self.xml = xml

        xml.create_doc("manifest")
        manifest_node = xml.get_root_node()

        # Old implementation.  Code is now on the data node
        xml.set_attribute(manifest_node, "code", self.template_project_code)

        # dump the notification entries
        data_node = xml.create_element("data")
        xml.append_child(manifest_node, data_node)

        code_node = xml.create_element("code")
        xml.append_child(data_node, code_node)
        xml.set_node_value(code_node, self.template_project_code)

        version = self.kwargs.get("version") or ""
        version_node = xml.create_element("version")
        xml.append_child(data_node, version_node)
        xml.set_node_value(version_node, version)



        # dump the project entry
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/project['code','%s'])" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/project")
        xml.set_attribute(data_node, "unique", "true")

        # dump the project_type entry
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/project['code','%s'].sthpw/project_type)" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/project_type")
        xml.set_attribute(data_node, "unique", "true")


        # dump the schema entry
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/schema['code','%s'])" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/schema")
        xml.set_attribute(data_node, "unique", "true")

        # find the project template search types
        namespace = self.project_type
        if not namespace or namespace == "default":
            namespace = self.project_code
        search = Search('sthpw/search_object')
        search.add_filters('namespace', list(dict.fromkeys([namespace, self.project_code])))
        project_search_types = [row.get_value('search_type') for row in search.get_sobjects()]

        #project_types = Search.eval("@GET(sthpw/search_object['namespace','%s'].search_type)" % self.project_code)

        # just dump the definition for data
        for search_type in project_search_types:
            data_node = xml.create_element("search_type")
            xml.append_child(manifest_node, data_node)
            xml.set_attribute(data_node, "code", search_type)

        search_types = [
            "config/custom_script",
            "config/widget_config",
            "config/naming",
            "config/client_trigger",
            "config/process",
            "config/trigger",
            "config/url",
            "config/prod_setting",

            #"config/ingest_rule",
            #"config/ingest_session",
        ]

        for search_type in search_types:
            data_node = xml.create_element("sobject")
            xml.append_child(manifest_node, data_node)
            xml.set_attribute(data_node, "search_type", search_type)

            # Read the current floor without advancing/resetting a shared sequence.
            st_obj = SearchType.get(search_type)
            sql = DbContainer.get(Project.get_db_resource_by_search_type(search_type))
            seq_id = sql.get_database_impl().get_table_sequence_value(sql, st_obj.get_table())
            xml.set_attribute(data_node, "seq_max", seq_id)
            
            #xml.set_attribute(data_node, "path", "data.spt")


       



        # dump the login_groups entries
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/login_group['project_code','%s'])" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/login_group")
        xml.set_attribute(data_node, "unique", "true")

        # dump the pipelines entries
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/pipeline['project_code','%s'])" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/pipeline")
        xml.set_attribute(data_node, "unique", "true")

        # dump the notification entries
        data_node = xml.create_element("sobject")
        xml.append_child(manifest_node, data_node)
        xml.set_attribute(data_node, "expression", "@SOBJECT(sthpw/notification['project_code','%s'])" % self.project_code)
        xml.set_attribute(data_node, "search_type", "sthpw/notification")




        from .plugin import PluginCreator
        creator = PluginCreator(base_dir=self.base_dir, manifest=xml.to_string(), force=True,
            version=version, dist_dir=self.kwargs.get('dist_dir'))
        creator.execute()

        self.zip_path = creator.get_zip_path()


    def get_zip_path(self):
        return self.zip_path
