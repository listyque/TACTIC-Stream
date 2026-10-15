###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Original schema editor commands; declarative configs, without its HTML renderer."""
import re
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import SearchType, DbContainer, WidgetDbConfig
from tactic_client_lib import TacticServerStub
from tactic.core.schema_commands import SearchTypeCreatorCmd

class SchemaConnectorCbk(Command):

    def execute(self):
        right_search_type = self.kwargs.get('right_search_type')
        right = self.kwargs.get('right')
        left_search_type = self.kwargs.get('left_search_type')
        left = self.kwargs.get('left')
        for search_type, column in ((left_search_type, left), (right_search_type, right)):
            if not isinstance(search_type, str) or not re.fullmatch(r'\w+/\w+', search_type):
                raise ValueError('Expected an unqualified namespace/search_type')
            if not isinstance(column, str) or not re.fullmatch(r'\w+', column):
                raise ValueError('Both connector column names are required')
            DbContainer.get(Project.get_db_resource_by_search_type(search_type)).check_schema_write()
            SearchType.get(search_type)
        col_type = 'integer' if right == 'id' else 'varchar(256)'

        server = TacticServerStub.get() 
        server.add_column_to_search_type(right_search_type, right, col_type)
        server.add_column_to_search_type(left_search_type, left, col_type)

        namespace, left_table = left_search_type.split("/")
        namespace, right_table = right_search_type.split("/")

        # an attempt to simplify the element_name by stripping _code or _id for edit view
        element_name = left
        if element_name.endswith("_code"):
            element_name2 = left[:-5]
        elif element_name.endswith("_id"):
            element_name2 = left[:-3]
        else:
            element_name2 = ""
    
        label_attr = 'name'
        if not SearchType.column_exists(right_search_type, 'name'):
            label_attr = 'code'

        # create a view definition
        element_xml = '''
        <element name='%s'/>
        ''' % (element_name)
        config = WidgetDbConfig.get_by_search_type(left_search_type, "definition")
        if config:
            config.append_xml_element(element_name, element_xml)

            # create a view definition
            if element_name2:
                element_xml = '''
                <element name='%s' edit="true">
                  <display widget='expression'>
                    <expression>@GET(%s.%s)</expression>
                    <calc_mode>fast</calc_mode>
                  </display>
                </element>
                ''' % (element_name2, right_search_type, label_attr)
                config.append_xml_element(element_name2, element_xml)
            config.commit_config()

        # create an edit definition for the code
        element_xml = '''
        <element name='%s'>
          <display class='SelectWdg'>
            <empty>-- Select --</empty>
            <values_expr>@GET(%s.%s)</values_expr>
          </display>
        </element>
        ''' % (element_name, right_search_type, right)

        config = WidgetDbConfig.get_by_search_type(left_search_type, "edit_definition")
        if not config:
            config = SearchType.create("config/widget_config")
            config.set_value("search_type", left_search_type)
            config.set_value("view", "edit_definition")
            config._init()

        config.append_xml_element(element_name, element_xml)

        if element_name2:
            element_xml = '''
            <element name='%s'>
              <display class='SelectWdg'>
                <empty>-- Select --</empty>
                <values_expr>@GET(%s.%s)</values_expr>
                <labels_expr>@GET(%s.%s)</labels_expr>
              </display>
              <action class='DatabaseAction'>
                <column>%s</column>
              </action>
            </element>
            ''' % (element_name2, right_search_type, right, right_search_type, label_attr, element_name)

            config.append_xml_element(element_name2, element_xml)

        config.commit_config()

        # create an edit definition for the code
        if element_name2:
            element_xml = '''
            <element name='%s'/>
            ''' % (element_name2)
            config = WidgetDbConfig.get_by_search_type(left_search_type, "edit")
            if config:
                config.insert_xml_element(element_name2, element_xml, "code")
                config.commit_config()

        else:
            element_xml = '''
            <element name='%s'/>
            ''' % (element_name)
            config = WidgetDbConfig.get_by_search_type(left_search_type, "edit")
            if config:
                config.insert_xml_element(element_name, element_xml, "code")
                config.commit_config()

        # create a view definition for the parent
        element_name = left_table
        element_xml = '''
        <element name='%s'>
          <display widget='hidden_row'>
            <dynamic_class>tactic.ui.panel.FastTableLayoutWdg</dynamic_class>
            <search_type>%s</search_type>
            <view>table</view>
            <show_shelf>true</show_shelf>
          </display>
        </element>
        ''' % (element_name, left_search_type)

        config = WidgetDbConfig.get_by_search_type(right_search_type, "definition")
        if config:
            config.append_xml_element(element_name, element_xml)
            config.commit_config()

class SchemaSaveCmd(Command):

    def get_title(self):
        return "SchemaSaveCmd"

    def execute(self):
        # save the schema

        # go through each connection and ensure that there are the following
        # elements
        project = Project.get()
        project_type = project.get_value("type")
        project_code = Project.get_project_code()

        if project_type:
            namespace = project_type
        else:
            namespace = project_code

        # foreign key
        # photos.store_code -> store.code

        from_search_type = self.kwargs.get("from_search_type")
        to_search_type = self.kwargs.get("to_search_type")
        if not all(isinstance(value, str) and value for value in (from_search_type, to_search_type)):
            raise ValueError('Both connection search types are required')
        if from_search_type.find("/") == -1:
            from_search_type = "%s/%s" % (namespace, from_search_type)
        if to_search_type.find("/") == -1:
            to_search_type = "%s/%s" % (namespace, to_search_type)

        if not all(re.fullmatch(r'\w+/\w+', value) for value in (from_search_type, to_search_type)):
            raise ValueError('Expected an unqualified namespace/search_type')
        DbContainer.get(project.get_project_db_resource()).check_schema_write()

        namespace, from_table = from_search_type.split("/")
        namespace, to_table = to_search_type.split("/")

        from_search_type_obj = SearchType.get(from_search_type, no_exception=True)
        to_search_type_obj = SearchType.get(to_search_type, no_exception=True)

        # register the search types
        if not from_search_type_obj:
            creator = SearchTypeCreatorCmd(search_type_name=from_search_type, sobject_parent=to_search_type)
            creator.execute()
            self.add_description('Saving Schema info with %s' %from_search_type)
        if not to_search_type_obj:
            creator = SearchTypeCreatorCmd(search_type_name=to_search_type)
            creator.execute()
            self.add_description('Saving Schema info with %s' %to_search_type)

        return
