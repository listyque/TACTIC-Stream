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

"""Original TACTIC sidebar configuration order, extracted from panel_wdg.py."""
import os
from xml.sax.saxutils import escape
from pyasm.common import Environment, Container, XmlException
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.biz import Project, Schema
from .widget_config import WidgetConfig, WidgetConfigView

class SidebarConfig:
    ERR_MSG = "SideBar_Error"
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.project = Project.get()

    def get_views(self):

        views = []
        view = self.kwargs.get("view")
        if view:
            extra_views = view.split("|")
            views.extend(extra_views)

        if not Project.get().is_admin():
            views.append('project_view')


        # detemine whether this use is allowed to see views other than the
        # main project_view
        security = Environment.get_security()
        if security.check_access("builtin", "view_save_my_view", "allow", default='allow'):
            # show self views section
            my_view = "my_view_%s" % Environment.get_user_name()
            my_view = my_view.replace("\\", "_")
            views.append(my_view)




        if security.get_version() == 1:
            if security.check_access("side_bar", "admin_views", "allow", default='allow'):
                if security.check_access("builtin", "view_site_admin", "allow"):
                    views.append('admin_views')
                else:
                    views.append('_my_admin')
            else:
                views.append('_my_admin')

        else:
            if security.check_access("link", "admin_views", "allow", default="deny"):
                if security.check_access("builtin", "view_site_admin", "allow"):
                    views.append('admin_views')
                else:
                    views.append('_my_admin')
            else:
                views.append('_my_admin')

        return views

    def add_internal_config(configs, views):
        '''add an internal config based on project base type'''
        project = Project.get()
        project_type = project.get_base_type()
        # catch potential invalid xpath error
        try:
            if project_type:
                tmp_path = os.path.join(os.path.dirname(__file__), "..", "ui", "panel", "panel_wdg.py")
                dir_name = os.path.dirname(tmp_path)
                file_path="%s/../config/%s-conf.xml" % (dir_name, project_type)
                if os.path.exists(file_path):
                    for view in views:
                        config = WidgetConfig.get(file_path=file_path, view=view)

                        view_node = config.get_view_node()
                        if view_node is not None:
                            configs.append(config)

            # finally, just look at the DEFAULT config
            tmp_path = os.path.join(os.path.dirname(__file__), "..", "ui", "panel", "panel_wdg.py")
            dir_name = os.path.dirname(tmp_path)
            file_path="%s/../config/%s-conf.xml" % (dir_name, "DEFAULT")

            if os.path.exists(file_path):
                for view in views:
                    config = WidgetConfig.get(file_path=file_path, view=view)

                    view_node = config.get_view_node()

                    if view_node is not None:
                        configs.append(config)

        except XmlException as e:
            msg = "Error with view [%s]"% ' '.join(views)
            print("Error: ", str(e))

            error_list = Container.get_seq(SidebarConfig.ERR_MSG)
            if msg not in error_list:
                Container.append_seq(SidebarConfig.ERR_MSG, msg)
                print(e.__str__())
    add_internal_config = staticmethod(add_internal_config)

    def get_config(cls, config_search_type, view, default=False, personal=False):

        #print("view: ", view)

        config = None
        configs = []
        login = None
        defined_view = view
        '''
        if '.' in view:
            parts  = view.split('.')
            login = parts[0]
            defined_view = parts[1]
        '''
        # this is really for the predefined view that shouldn't go to the db
        # otherwise, it is a never ending cycle.
        if default:
            views = [defined_view, 'definition']
            SidebarConfig.add_internal_config(configs, views)

        # special condition for children
        elif view in ['children']:
            tmp_path = os.path.join(os.path.dirname(__file__), "..", "ui", "panel", "panel_wdg.py")
            dir_name = os.path.dirname(tmp_path)
            file_path="%s/../config/children-conf.xml" % (dir_name)
            config = WidgetConfig.get(file_path=file_path, view=defined_view)
            configs.append(config)


        elif view == "definition":
            # look for a definition in the database
            search = Search("config/widget_config")
            search.add_filter("search_type", config_search_type)
            search.add_filter("view", "definition")
            # lower the chance of getting some other definition files
            if personal:
                login = Environment.get_user_name()

            search.add_filter("login", login)

            config = search.get_sobject()
            if config:
                configs.append(config)
            # We should not allow redefinition of a predefined item
            # so it is fine to add internal config for definition
            # then look for a definition in the definition file
            SidebarConfig.add_internal_config(configs, ['definition'])



        else:
            # first look in the database
            search = Search("config/widget_config")
            search.add_filter("search_type", config_search_type)
            search.add_filter("view", view)
            if search.column_exists("priority"):
                search.add_order_by("priority desc")
            config = search.get_sobject()
            if config:
                configs.append(config)

            # then look for a file
            SidebarConfig.add_internal_config(configs, [defined_view])

            logins = []
            if personal:
                logins.append(Environment.get_user_name())

            logins.append(None)
            for login in logins:
                # look for a definition in the database
                search = Search("config/widget_config")
                search.add_filter("search_type", config_search_type)
                search.add_filter("view", "definition")
                # lower the chance of getting some other definition files
                search.add_filter("login", login)

                key = '%s|definition|%s'%(config_search_type, login)
                config = WidgetDbConfig.get_by_search(search, key)
                #config = search.get_sobject()
                if config:
                    configs.append(config)


            # then look for a definition in the definition file
            SidebarConfig.add_internal_config(configs, ['definition'])

        widget_config_view = WidgetConfigView(config_search_type, view, configs)

        return widget_config_view
    get_config = classmethod(get_config)


    def get_schema_xml(self):

        config_xml = []

        config_xml.append( '''
        <config>
        <schema>
        <element name='schema_view' title='Schema Views' icon="dependency">
          <display class='FolderWdg'>
              <view>schema_view</view>
          </display>
        </element>
        </schema>
        ''')

        # get project type schema
        project = self.project
        project_code = project.get_code()
        project_type = project.get_type()
        schema = Schema.get_by_code(project_code)

        if project_code in ['sthpw', 'admin']:
            self.is_admin = True
        else:
            self.is_admin = False



        config_xml.append( '''
        <schema_view>
        ''')

        if not self.is_admin:
            config_xml.append( '''
            <element name='_current_schema' title='%s Schema'>
              <display class='FolderWdg'>
                <view>_current_schema</view>
              </display>
            </element>
            ''' % project_code.capitalize() )

            if project_type != "simple":
                config_xml.append( '''
                <element name='_prod_schema' title='%s Schema'>
                  <display class='FolderWdg'>
                    <view>_prod_schema</view>
                  </display>
                </element>
                ''' % project_type.capitalize() )

            config_xml.append( '''
            <element name='_config_schema' title='Config Schema'>
              <display class='FolderWdg'>
                <view>_config_schema</view>
              </display>
            </element>
            ''')

        config_xml.append( '''
        <element name='_admin_schema' title='Global Config/Data'>
          <display class='FolderWdg'>
            <view>_admin_schema</view>
          </display>
        </element>
        ''')

        config_xml.append( '''
        </schema_view>

        ''')


        if schema:
            self.get_schema_snippet("_current_schema", schema, config_xml)
        if project_type:
            schema = Schema.get_predefined_schema(project_type)
            self.get_schema_snippet("_prod_schema", schema, config_xml)


        config_schema = Schema.get_predefined_schema('config')
        self.get_schema_snippet("_config_schema", config_schema, config_xml)
        schema = Schema.get_admin_schema()
        self.get_schema_snippet("_admin_schema", schema, config_xml)


        config_xml.append( '''
        </config>
        ''')

        xml = "".join(config_xml)
        return xml


    def get_schema_snippet(cls, view, schema, config_xml):
        schema_xml = schema.get_xml_value("schema")
        search_types = schema_xml.get_values("schema/search_type/@name")
        if not search_types:
            return

        search_types.sort()

        js_load ="false"

        config_xml.append( '''
        <%s>
        ''' % view)
        for search_type in search_types:
            try:
                search_type_obj = SearchType.get(search_type)
            except:
                print("WARNING: search type [%s] does not exist" % search_type)
                continue
            if not search_type_obj:
                continue

            title = search_type_obj.get_value("title")
            if not title:
                title = search_type
            config_xml.append( '''
            <element name='%s' title='%s'>
              <display class='LinkWdg'>
                  <search_type>%s</search_type>
                  <view>table</view>
                  <height>auto</height>
                  <js_load>%s</js_load>
                  <schema_default_view>true</schema_default_view>
              </display>
            </element>
            ''' % (escape(search_type, {"'": '&apos;'}), escape(title, {"'": '&apos;'}), escape(search_type), js_load) )
        config_xml.append( '''
        </%s>
        ''' % view)

    get_schema_snippet = classmethod(get_schema_snippet)
