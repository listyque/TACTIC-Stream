# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""Original SearchTypeCreatorCmd and declarative views; Vue handles rendering."""
import re
from pyasm.biz import Project, Schema
from pyasm.command import Command, CommandException, CommandExitException
from pyasm.command.database_cmd import ColumnAddCmd
from pyasm.common import TacticException, Xml
from pyasm.common.errors import UnsupportedContract
from pyasm.search import Search, SearchType, DbContainer, CreateTable, TableUndo, WidgetDbConfig

class SearchTypeCreatorCmd(Command):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

        self.database = kwargs.get('database')
        self.namespace = kwargs.get('namespace')
        self.schema = kwargs.get('schema')

        if not self.database:
            self.project = Project.get()
            self.database = self.project.get_code()
        else:
            self.project = Project.get_by_code(self.database)

        if self.project is None:
            raise LookupError('Project does not exist: %s' % self.database)

        self.search_type_name = self.get_value("search_type_name")
        self.db_resource = self.project.get_project_db_resource()
        if self.search_type_name.startswith('sthpw/'):
            sql = DbContainer.get('sthpw')
            self.db_resource = sql.get_db_resource()
            self.database = 'sthpw'
            self.namespace = 'sthpw'

        if not self.namespace:
            self.namespace = self.project.get_code()

        if not self.schema:
            self.schema = 'public'

        super(SearchTypeCreatorCmd,self).__init__(**kwargs)

        self.column_names = self.get_values("column_name")
        if not self.column_names:
            self.column_names = []
        self.column_types = self.get_values("data_type")
        if not self.column_types:
            self.column_types = []
        self.formats = self.get_values("format")
        if not self.formats:
            self.formats = []

        self.search_type_obj = None

    def get_search_type_obj(self):
        return self.search_type_obj

    def execute(self):
        if any(self.get_value(name) for name in ('image_path', 'sobject_preview')):
            raise UnsupportedContract('Preview search-type creation is not migrated')
        DbContainer.get(self.db_resource).check_schema_write()
        if self.project.get_code() != Project.get_project_code():
            raise UnsupportedContract('Select the target project before creating its search types')
        if self.schema != 'public':
            raise UnsupportedContract('Search-type creation in other schemas is not migrated')
        if len(self.column_names) != len(self.column_types):
            raise ValueError('Each column requires a data type')
        if not self.database or not self.schema:
            raise CommandException("Either database nor schema is not defined")

        if not self.namespace:
            if self.schema == "public":
                self.namespace = self.database
            else:
                self.namespace = "%s/%s" % (self.database,self.schema)

        if self.search_type_name == "":
            raise CommandExitException("No search type supplied")

        if self.search_type_name.find("/") != -1:
            self.namespace, self.search_type_name = self.search_type_name.split("/", 1)

        if not self.namespace or re.search(r'\W', self.namespace):
            raise TacticException("No special characters or spaces allowed in the namespace of sType.")
        if not self.search_type_name or re.search(r'\W', self.search_type_name):
            raise TacticException("No special characters or spaces allowed in the sType name.")

        self.asset_description = self.get_value("asset_description")
        if self.asset_description == "":
            self.asset_description = "No description"

        self.asset_title = self.get_value("asset_title")
        if self.asset_title == "":
            self.asset_title = "No title"

        search_type = "%s/%s" % (self.namespace, self.search_type_name)

        self.info['search_type'] = search_type

        self.register_search_type(search_type)
        if not self.search_type_obj:
            self.search_type_obj = SearchType.get(search_type)
        if self.get_value("sobject_pipeline"):
            self.has_pipeline = True
        else:
            self.has_pipeline = False

        self.has_collection = bool(self.get_value('sobject_collection'))
        self.has_preview = False

        self.add_naming()

        self.parent_type = self.get_value("sobject_parent")

        copy_from_template = self.get_value('copy_from_template')
        if copy_from_template:
            self.copy_template_table(copy_from_template)
        else:
            self.create_table()
            if self.namespace != 'sthpw':
                self.create_config()
                self.create_pipeline()

        project_code = Project.get_project_code()

        schema = Schema.get_by_code(project_code)

        if not schema:
            schema = Schema.create(project_code, "%s project schema" % project_code )

        if schema:
            schema.add_search_type(search_type, self.parent_type)
            schema.commit()
        else:
            raise CommandException("No schema defined for [%s]" % self.database)

        self.add_sidebar_views()

    def register_search_type(self, search_type):
        search = Search( SearchType.SEARCH_TYPE )
        search.add_filter("search_type", search_type)
        test_sobject = search.get_sobject()
        if test_sobject:
            self.search_type_obj = SearchType.get(search_type)
            is_project_specific = self.get_value("project_specific") == "on"
            if self.table_exists() and not is_project_specific:
                msg = "Search type [%s] already exists." % search_type
                if search_type.startswith('sthpw/'):
                    msg = '%s If you are trying to add this to the Project Schema, use the Save button instead of the Register button.'%msg

                raise CommandException(msg)
            else: # continue to add table to current project
                return

        sobject = SearchType( SearchType.SEARCH_TYPE )

        sobject.set_value("search_type", search_type)

        sobject.set_value("namespace", self.namespace)

        if self.get_value("project_specific") == "on":
            sobject.set_value("database", self.database)
        else:
            if self.namespace == 'sthpw':
                sobject.set_value("database", "sthpw")
            else:
                sobject.set_value("database", "{project}")

        layout = self.get_value("layout")
        if layout:
            sobject.set_value("default_layout", layout)

        sobject.set_value("schema", self.schema)

        if self.schema == "public":
            table = self.search_type_name
        else:
            table = "%s.%s" % (self.schema, self.search_type_name)
        sobject.set_value("table_name", table)
        sobject.set_value("class_name", "pyasm.search.SObject")
        sobject.set_value("title", self.asset_title)
        sobject.set_value("description", self.asset_description)

        sobject.commit()

        self.search_type_obj = sobject

    def create_config(self):
        search_type = self.search_type_obj.get_value("search_type")
        columns = SearchType.get_columns(search_type)
        #if self.has_pipeline:
        #    columns.remove("pipeline_code")
        #    columns.append("pipeline")

        # preview is always first
        if self.has_preview:
            columns.insert(0, "preview")

        # remove some of the defaults columns
        if 'id' in columns:
            columns.remove("id")
        if 's_status' in columns:
            columns.remove("s_status")
        if 'login' in columns:
            columns.remove("login")
        if 'timestamp' in columns:
            columns.remove("timestamp")
        if 'keywords' in columns:
            columns.remove("keywords")

        self.show_code = False
        if not self.show_code:
            try:
                columns.remove("code")
            except:
                pass


        if self.has_preview:
            default_columns = ['preview', 'name', 'description']
        else:
            default_columns = ['name', 'description']


        # create the xml document
        for view in ["definition", "table"]:
            xml = Xml()
            xml.create_doc("config")
            root = xml.get_root_node()
            view_node = xml.create_element(view)
            xml.append_child(root, view_node)
            # definition has to be the last in the loop
            #if view == "definition":
            #    columns.append('update')


            for column in default_columns:
                element = xml.create_element("element")
                Xml.set_attribute(element, "name", column)
                xml.append_child(view_node, element)


            for column in columns:

                # skip relative_dir
                if column == 'relative_dir':
                    continue

                # skip pipeline
                if column in ['pipeline_code'] or column in default_columns:
                    continue

                if column in self.column_names:
                    continue

                element = xml.create_element("element")
                Xml.set_attribute(element, "name", column)
                xml.append_child(view_node, element)


            # handle the custom columns
            for column_name, column_type, format in zip(self.column_names, self.column_types, self.formats + [''] * (len(self.column_names) - len(self.formats))):
                if not column_name:
                    continue

                element = xml.create_element("element")
                xml.append_child(view_node, element)
                Xml.set_attribute(element, "name", column_name)

                # need to use xml to add to the config
                if view == 'definition':
                    display = xml.create_element("display")
                    xml.append_child(element, display)
                    Xml.set_attribute(display, "widget", "format")

                    xml.create_text_element("format", format, node=display)
                    xml.create_text_element("type", column_type, node=display)

            # add view if there is a pipeline
            if self.has_pipeline and view == 'table':
                element = xml.create_element("element")
                Xml.set_attribute(element, "name", "pipeline")
                xml.append_child(view_node, element)

                element = xml.create_element("element")
                Xml.set_attribute(element, "name", "task_status_edit")
                xml.append_child(view_node, element)


            element = xml.create_element("element")
            Xml.set_attribute(element, "name", "notes")
            xml.append_child(view_node, element)


            WidgetDbConfig.create(search_type, view, xml.get_xml() )




        # create the edit view
        view = "edit"
        xml = Xml()
        xml.create_doc("config")
        root = xml.get_root_node()
        view_node = xml.create_element(view)
        xml.append_child(root, view_node)

        columns.append("keywords")

        for column in default_columns:
            element = xml.create_element("element")
            Xml.set_attribute(element, "name", column)
            xml.append_child(view_node, element)


        # create code element
        for column in columns:
            if column in ['pipeline_code'] or column in default_columns:
                continue

            if column == 'relative_dir':
                continue

            element = xml.create_element("element")
            Xml.set_attribute(element, "name", column)
            #view_node.appendChild(element)
            xml.append_child(view_node, element)



        WidgetDbConfig.create(search_type, view, xml.get_xml() )


    def add_sidebar_views(self):

        search_type = self.search_type_obj.get_value("search_type")
        namespace, table = search_type.split("/")
        title = self.search_type_obj.get_title()

        # _list view
        class_name = "tactic.ui.panel.ViewPanelWdg"
        display_options = {
            "class_name": class_name,
            "search_type": search_type,
            "layout": "default"
        }

        # this is now handled by the "default" setting


        element_attrs = {
            'title': title
        }

        view = "definition"
        element_name = "%s_list" % table

        config = WidgetDbConfig.append( "SideBarWdg", view, element_name, class_name="LinkWdg", display_options=display_options, element_attrs=element_attrs)

        view = "project_view"
        element_name = "%s_list" % table
        config = WidgetDbConfig.append( "SideBarWdg", view, element_name)


    def copy_template_table(self, template):
        template_type_obj = SearchType.get(template)
        template_table = template_type_obj.get_table()
        table = self.search_type_obj.get_table()
        resource = Project.get_db_resource_by_search_type(template)
        if resource._get_connection_key() != self.db_resource._get_connection_key():
            raise UnsupportedContract('Template copying requires the same database resource')
        sql = DbContainer.get(self.db_resource)
        sql.copy_table_schema(template_table, table)
        TableUndo.log(self.search_type_obj.get_value('search_type'), sql.get_database_name(), table)

    def table_exists(self):
        '''check if table exists'''
        if self.schema == "public":
            table = self.search_type_name
        else:
            table = "%s.%s" % (self.schema, self.search_type_name)

        sql = DbContainer.get(self.db_resource)
        impl = sql.get_database_impl()
        exists = impl.table_exists(self.db_resource, table)
        return exists

    def create_table(self):

        if self.schema == "public":
            table = self.search_type_name
        else:
            table = "%s.%s" % (self.schema, self.search_type_name)

        if self.namespace == 'sthpw':
            search_type = "%s/%s" % (self.namespace, self.search_type_name)
        else:
            search_type = "%s/%s?project=%s" % (self.namespace, self.search_type_name, self.database)
        create = CreateTable(search_type=search_type)

        create.set_table( table )

        create.add("id", "serial", primary_key=True)

        create.add("code", "varchar")
        if self.has_pipeline:
            create.add("pipeline_code", "varchar")
        if self.has_collection:
            create.add("_is_collection", "boolean")

        create.add("name", "varchar")
        create.add("description", "text")
        create.add("keywords", "text")
        create.add("login", "varchar")
        create.add("timestamp", "timestamp")
        create.add("data", "json")
        create.add("s_status", "varchar")
        create.add_constraint(["code"], mode="UNIQUE")

        for column_name, column_type in zip(self.column_names, self.column_types):
            if not column_name:
                continue

            data_type = ColumnAddCmd.get_data_type(search_type, column_type)
            create.add(column_name, data_type)

        if self.folder_naming.find("{sobject.relative_dir}") != -1:
            create.add("relative_dir", "text")
        elif self.folder_naming.find("{sobject.category}") != -1:
            create.add("category", "text")

        statement = create.get_statement()

        sql = DbContainer.get(self.db_resource)
        database = sql.get_database_name()
        impl = sql.get_database_impl()
        exists = impl.table_exists(self.db_resource, table)
        if exists:
            pass
        else:
            create.commit(sql)
            TableUndo.log(self.search_type_obj.get_value("search_type"), database, table)

    def create_pipeline(self):

        if not self.has_pipeline:
            return

        search_type = self.search_type_obj.get_value("search_type")
        namespace, table = search_type.split("/")
        project_code = Project.get_project_code()

        pipeline_code = "%s/%s" % (project_code, table)


        search = Search("sthpw/pipeline")
        search.add_filter("code", pipeline_code)
        pipeline = search.get_sobject()

        if pipeline:
            return

        processes = self.get_values("process")

        filtered = []
        for process in processes:
            if process:
                filtered.append(process)
        processes = filtered

        pipeline_sobj = SearchType.create("sthpw/pipeline")
        pipeline_sobj.set_value("code", pipeline_code)
        xml = Xml('<pipeline/>')
        root = xml.get_root_node()
        last_process = None
        for i, process in enumerate(processes):
            if not isinstance(process, str):
                raise ValueError('Pipeline process names must be strings')
            xml.append_child(root, xml.create_element('process', attrs={'name': process}))
            process_sobj = SearchType.create('config/process')
            process_sobj.set_value('pipeline_code', pipeline_code)
            process_sobj.set_value('process', process)
            process_sobj.set_value('sort_order', i)
            process_sobj.set_json_value('workflow', {'version': 2})
            process_sobj.commit()
            if last_process is not None:
                xml.append_child(root, xml.create_element('connect', attrs={'from': last_process, 'to': process}))
            last_process = process
        pipeline = xml.to_string()

        pipeline_sobj.set_value("pipeline", pipeline)
        pipeline_sobj.set_value("project_code", project_code)
        pipeline_sobj.set_value("search_type", search_type)

        pipeline_sobj.commit()

    def add_naming(self):

        naming_expr = self.get_value("directory_naming")
        file_naming_expr = self.get_value("file_naming")

        if naming_expr == "_CUSTOM":
            naming_expr = self.get_value("custom_naming")

        if not naming_expr or naming_expr == "_DEFAULT":
            naming_expr = "{project.code}/{search_type.table_name}/{sobject.code}"
        naming_expr = naming_expr.strip("/")

        if not file_naming_expr or file_naming_expr == "_DEFAULT":
            file_naming_expr = "{sobject.name}_v{version}.{ext}"

        has_folder_naming = self.get_value("has_folder_naming") == "on"
        has_file_naming = self.get_value("has_file_naming") == "on"

        naming = SearchType.create("config/naming")
        if not has_folder_naming:
            naming_expr = "{sobject.relative_dir}"
        naming.set_value("dir_naming", naming_expr)

        if not has_file_naming:
            file_naming_expr = "{sobject.name}_v{version}.{ext}"

        naming.set_value("file_naming", file_naming_expr)

        naming.set_value("checkin_type", "auto")

        search_type = self.search_type_obj.get_value("search_type")
        naming.set_value("search_type", search_type)

        naming.commit()

        self.folder_naming = naming_expr
        self.file_naming = file_naming_expr
    def get_value(self, name):
        return self.kwargs.get(name, '')

    def get_values(self, name):
        value = self.kwargs.get(name, [])
        return value if isinstance(value, list) else [value]
