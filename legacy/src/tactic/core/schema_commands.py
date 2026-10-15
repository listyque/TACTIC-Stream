
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
"""Original SearchType creation command, extracted from the widget module.

It still writes the same schema/sidebar configurations and uses existing TACTIC
DDL/undo primitives. This is not a replacement ORM or generic SQL endpoint.
"""
import os
import re
from pyasm.common import Environment, Xml, TacticException
from pyasm.biz import Project, Schema
from pyasm.web import WebContainer
from pyasm.command import Command, CommandException, CommandExitException, ColumnAddCmd
from pyasm.search import SearchType, Search, WidgetDbConfig, CreateTable, DbContainer, TableUndo

__all__ = ['SearchTypeCreatorCmd']

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
            # need to have a project with this database name
            # essentially: project == database
            self.project = Project.get_by_code(self.database)

        self.search_type_name = self.get_value("search_type_name")
        self.db_resource = self.project.get_project_db_resource()
        # Advanced mode: special condition for sthpw/.. sType
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
        #self.column_types = self.get_values("column_type")
        self.column_types = self.get_values("data_type")
        if not self.column_types:
            self.column_types = []
        self.formats = self.get_values("format")
        if not self.formats:
            self.formats = []

        self.search_type_obj = None

    def get_title(self):
        return "sType Creator"


    def set_database(self, database):
        self.database = database

    def set_schema(self, schema):
        self.schema = schema


    def get_value(self, name):
        web = WebContainer.get_web()

        value = self.kwargs.get(name)
        if not value:
            value = web.get_form_value(name)

        return value

    def get_values(self, name):
        web = WebContainer.get_web()

        value = self.kwargs.get(name)
        if not value:
            value = web.get_form_values(name)

        return value

    def get_search_type_obj(self):
        return self.search_type_obj


    def get_sobject(self):
        return self.sobject


    def execute(self):
        if not self.database or not self.schema:
            raise CommandException("Either database nor schema is not defined")



        # FIXME: hack this in for now to handle "public"
        if not self.namespace:
            if self.schema == "public":
                self.namespace = self.database
            else:
                self.namespace = "%s/%s" % (self.database,self.schema)

        web = WebContainer.get_web()


        if self.search_type_name == "":
            raise CommandExitException("No search type supplied")

        if self.search_type_name.find("/") != -1:
            self.namespace, self.search_type_name = self.search_type_name.split("/", 1)
            # check if it is a valid namespace
            #proj = Project.get_by_code(self.namespace)
            #if not proj:
            #    raise TacticException('[%s] is not a valid namespace'%self.namespace)

        if re.search(r'\W', self.namespace):
            raise TacticException("No special characters or spaces allowed in the namespace of sType.")
        if re.search(r'\W', self.search_type_name):
            raise TacticException("No special characters or spaces allowed in the sType name.")

        #if re.search(r'[A-Z]', self.namespace):
        #    raise TacticException("No upper case letters allowed in the namespace of sType.")
        #if re.search(r'[A-Z]', self.search_type_name):
        #    raise TacticException("No uppercase letters allowed in the sType name.")


        #self.asset_description = web.get_form_value("asset_description")
        self.asset_description = self.get_value("asset_description")
        if self.asset_description == "":
            self.asset_description = "No description"

        #self.asset_title = web.get_form_value("asset_title")
        self.asset_title = self.get_value("asset_title")
        if self.asset_title == "":
            self.asset_title = "No title"

        #copy_from_template = web.get_form_value("copy_from_template")
        copy_from_template = self.get_value("copy_from_template")
        search_type = "%s/%s" % (self.namespace, self.search_type_name)


        # don't auto lower it cuz the same sType name may get added to the schema
        #search_type = search_type.lower()

        # Save the newly created search_type to info so we can get it and
        # display it when we are ready to refresh the SearchTypeToolWdg.
        self.info['search_type'] = search_type


        self.register_search_type(search_type)
        if not self.search_type_obj:
            self.search_type_obj = SearchType.get(search_type)
        #if web.get_form_value("sobject_pipeline"):
        if self.get_value("sobject_pipeline"):
            self.has_pipeline = True
        else:
            self.has_pipeline = False


        if self.get_value("sobject_collection"):
            self.has_collection = True
        else:
            self.has_collection = False



        if self.get_value("sobject_preview"):
            self.has_preview = True
        else:
            self.has_preview = False


        # add naming first because create table needs it
        self.add_naming()


        #self.parent_type = web.get_form_value("sobject_parent")
        self.parent_type = self.get_value("sobject_parent")

        if not copy_from_template:
            self.create_table()
            # for sthpw sType, create the table only
            if not self.namespace == 'sthpw':
                self.create_config()
                self.create_pipeline()
        else:
            # FIXME: don't copy config yet ... should really copy all
            # ... or have an option
            #self.copy_template_config(copy_from_template)
            self.copy_template_table(copy_from_template)


        # add this search_type to the schema for this project
        project_code = Project.get_project_code()

        schema = Schema.get_by_code(project_code)

        # if it doesn't exist, then create an empty one
        if not schema:
            schema = Schema.create(project_code, "%s project schema" % project_code )

        if schema:
            schema.add_search_type(search_type, self.parent_type)
            schema.commit()
        else:
            raise CommandException("No schema defined for [%s]" % self.database)


        self.add_sidebar_views()

        self.checkin_preview()




    def register_search_type(self, search_type):
        # first check if it already exists
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


        # create the search type
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
            for column_name, column_type, format in zip(self.column_names, self.column_types, self.formats):
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





    def _create_element(self, xml, view_node, name):
        element = xml.create_element("element")
        element.setAttribute("name", name)
        #view_node.appendChild(element)
        xml.append_child(view_node, element)



    def copy_template_table(self, template):
        template_type_obj = SearchType.get(template)
        template_table = template_type_obj.get_table()
        table = self.search_type_obj.get_table()

        database = self.search_type_obj.get_database()

        sql = DbContainer.get(database)
        sql.copy_table_schema(template_table, table)

        # log that this table was creatd
        TableUndo.log(database, table)


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

        # create primary
        create.add("id", "serial", primary_key=True)

        create.add("code", "varchar")
        if self.has_pipeline:
            create.add("pipeline_code", "varchar")
        if self.has_collection:
            create.add("_is_collection", "boolean")


        # add default columns
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



        # DEPRECATED
        #create.set_primary_key("id")

        statement = create.get_statement()

        sql = DbContainer.get(self.db_resource)
        database = sql.get_database_name()
        impl = sql.get_database_impl()
        exists = impl.table_exists(self.db_resource, table)
        if exists:
            #raise TacticException('This table [%s] already exists.'%table)
            pass
        else:
            create.commit(sql)
            TableUndo.log(self.search_type_obj.get_value("search_type"), database, table)
        '''
            # add columns
            db_resource = Project.get_db_resource_by_search_type(search_type)

            sql = DbContainer.get(db_resource)


            # put a unique constraint on code, which works automatically with Plugin creation
            statement = 'ALTER TABLE "%s" ADD CONSTRAINT "%s_code_unique" UNIQUE ("code")' % (table, table)
            #statement = 'CREATE UNIQUE INDEX "%s_code_idx" ON "%s" ("code")' % (table, table)
            sql.do_update(statement)

        '''


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
        """
        layout = self.get_value("layout")

        if layout == "tile":
            class_name = "tactic.ui.panel.ViewPanelWdg"
            display_options = {
                "class_name": class_name,
                "search_type": search_type,
                "layout": "tile"
            }

        elif layout == "card":
            class_name = "tactic.ui.panel.ViewPanelWdg"
            display_options = {
                "class_name": class_name,
                "search_type": search_type,
                "layout": "card"
            }

        elif layout == "browser":
            class_name = "tactic.ui.panel.ViewPanelWdg"
            display_options = {
                "class_name": class_name,
                "search_type": search_type,
                "layout": "browser"
            }



        else:
            class_name = "tactic.ui.panel.ViewPanelWdg"
            display_options = {
                "class_name": class_name,
                "search_type": search_type,
                "view": "table",
                "layout": "default"
            }
        """

        action_options = {}
        action_class_name = {}

        element_attrs = {
            'title': title
        }

        view = "definition"
        element_name = "%s_list" % table

        config = WidgetDbConfig.append( "SideBarWdg", view, element_name, class_name="LinkWdg", display_options=display_options, element_attrs=element_attrs)

        view = "project_view"
        element_name = "%s_list" % table
        config = WidgetDbConfig.append( "SideBarWdg", view, element_name)



    def create_pipeline(self):

        if not self.has_pipeline:
            return

        search_type = self.search_type_obj.get_value("search_type")
        namespace, table = search_type.split("/")
        project_code = Project.get_project_code()

        pipeline_code = "%s/%s" % (project_code, table)

        title = table.replace("_", " ").title()

        # create a pipeline
        search = Search("sthpw/pipeline")
        search.add_filter("code", title)
        search.add_filter("code", pipeline_code)
        pipeline = search.get_sobject()

        # TODO: check for search types??
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
        if not processes:
            # create an empty pipeline
            pipeline = '''<?xml version="1.0" encoding="UTF-8"?>
<pipeline/>
'''
        else:
            p = []
            p.append('''<?xml version="1.0" encoding="UTF-8"?>''')
            p.append('''<pipeline>''')

            for i, process in enumerate(processes):
                p.append('''  <process name="%s"/>''' % process)

                # create the process entry
                process_sobj = SearchType.create("config/process")
                process_sobj.set_value("pipeline_code", pipeline_code)
                process_sobj.set_value("process", process)
                process_sobj.set_value("sort_order", i)
                process_sobj.set_json_value("workflow", {"version": 2})
                process_sobj.commit()

            last_process = None
            for i, process in enumerate(processes):
                if last_process:
                    p.append('''  <connect from="%s" to="%s"/>''' % (last_process, process) )
                last_process = process





            p.append('''</pipeline>''')

            pipeline = "\n".join(p)


        pipeline_sobj.set_value("pipeline", pipeline)
        pipeline_sobj.set_value("project_code", project_code)
        pipeline_sobj.set_value("search_type", search_type)

        pipeline_sobj.commit()




    def checkin_preview(self):
        # if there is an image, check it in
        image_path = self.get_values("image_path")
        if image_path:
            image_path = image_path[0]
            if not image_path:
                return

            image_path = image_path.replace("\\", "/")
            # Can't use upload path because the transaction has changed
            #basename = os.path.basename(image_path)
            # and the ticket is lost
            #upload_dir = Environment.get_upload_dir()
            #upload_path = "%s/%s" % (upload_dir, basename)
            parts = image_path.split("/")
            basename = parts[-1]
            ticket = parts[-2]

            asset_dir = Environment.get_asset_dir()
            upload_path = "%s/temp/%s/%s" % (asset_dir, ticket, basename)

            file_type = 'main'

            file_paths = [upload_path]
            file_types = [file_type]

            source_paths = [upload_path]
            from pyasm.biz import IconCreator
            if os.path.isfile(upload_path):
                icon_creator = IconCreator(upload_path)
                icon_creator.execute()

                web_path = icon_creator.get_web_path()
                icon_path = icon_creator.get_icon_path()
                if web_path:
                    file_paths = [upload_path, web_path, icon_path]
                    file_types = [file_type, 'web', 'icon']

            from pyasm.checkin import FileCheckin
            checkin = FileCheckin(self.search_type_obj, context='icon', file_paths=file_paths, file_types=file_types)
            checkin.execute()



    def add_naming(self):

        naming_expr = self.get_value("directory_naming")
        file_naming_expr = self.get_value("file_naming")


        if naming_expr == "_CUSTOM":
            naming_expr = self.get_value("custom_naming")

        if not naming_expr or naming_expr == "_DEFAULT":
            naming_expr = "{project.code}/{search_type.table_name}/{sobject.code}"
        # fix the slashes
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

