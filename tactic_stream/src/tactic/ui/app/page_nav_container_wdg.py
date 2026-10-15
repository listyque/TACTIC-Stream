###########################################################
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
from pyasm.common import Xml, Environment
from pyasm.search import Search
from pyasm.web import WidgetSettings
from tactic.ui.common import BaseRefreshWdg
basestring = str

class PageNavContainerWdg(BaseRefreshWdg):
    def get_display(self):
        from pyasm.common.errors import UnsupportedContract
        raise UnsupportedContract('Native application-shell HTML is not migrated; top_layout state is supported')

    def init(self):
        search = Search('config/widget_config')
        search.add_filter('category', 'top_layout')
        search.add_filter('view', 'welcome')
        config = search.get_sobject()
        value = config.get_value('config') if config else WidgetSettings.get_value_by_key('top_layout')
        self.config_xml = Xml(value or self.get_default_config())

    def get_default_config(self):
            use_sidebar = self.kwargs.get('use_sidebar')
            if use_sidebar==False:
                config = '''
                <config>
                <application>
                <element name="main_body">
                  <display class="tactic.ui.startup.MainWdg"/>
                  <web/>
                </element>
                </application>
                </config>
                '''
            else:
                config = '''
                <config>
                <application>
                <element name="left_nav">
                  <display class="tactic.ui.panel.SideBarPanelWdg">
                    <auto_size>True</auto_size>
                  </display>
                </element>
    
                <element name="main_body">
                  <display class="tactic.ui.startup.MainWdg"/>
                  <web/>
                </element>
                </application>
                </config>
                '''
            return config

    def set_state(self, panel_name, widget_class, options, values):
            '''this is called by side_bar.js mostly'''
    
            # set the class name
            display_node = self.config_xml.get_node("config/application/element[@name='%s']/display" % (panel_name) )
            if display_node is None:
                print("config: ", self.config_xml.to_string() )
                print("xpath: config/application/element[@name='%s']/display" % (panel_name) )
                print("No display node found")
                return
    
            self.config_xml.set_attribute(display_node, "class", widget_class)
    
            # remove all the old options
            #display_node = self.config_xml.get_node("config/application/element[@name='%s']/display" % panel_name )
            for child_node in self.config_xml.get_children(display_node):
                self.config_xml.remove_child(display_node, child_node)
    
            # set the options
            for name, value in options.items():
                node = self.config_xml.get_node("config/application/element[@name='%s']/display/%s" % (panel_name, name) )
    
                if isinstance( value, basestring ):
                    #print("WARNING: set application: skipping [%s] with value [%s]" % (name, value))
                    #continue
                    element = self.config_xml.create_text_element(name, value)
                    self.config_xml.append_child(display_node, element)
    
                elif isinstance( value, dict): # if it is a dictionary
                    # TODO: run recursively.. supports 2 level only now
                    sub_element = self.config_xml.create_element(name)
                    self.config_xml.append_child(display_node, sub_element)
                    for name2, value2 in value.items():
                        if isinstance(value2, dict):
                            sub_element2 = self.config_xml.create_element(name2)
                            self.config_xml.append_child(sub_element, sub_element2)
                            for name3, value3 in value2.items():
                                element = self.config_xml.create_text_element(name3, value3)
                                self.config_xml.append_child(sub_element2, element)
                        else:        
                            element = self.config_xml.create_text_element(name2, value2)
                            self.config_xml.append_child(sub_element, element)
                        
                    
            # web value node
            value_node = self.config_xml.get_node("config/application/element[@name='%s']/web" % (panel_name) )
            if value_node != None:
                for child_node in self.config_xml.get_children(value_node):
                    self.config_xml.remove_child(value_node, child_node)
            else: # create it
                value_node = self.config_xml.create_element('web')
                element_node = self.config_xml.get_node("config/application/element[@name='%s']" % (panel_name) )
                self.config_xml.append_child(element_node, value_node)
    
            # set the values
            for name, value in values.items():
                node = self.config_xml.get_node("config/application/element[@name='%s']/web/%s" % (panel_name, name) )
    
                if not isinstance(value, basestring):
                    print("WARNING: set application: skipping [%s] with value [%s]" % (name, value))
                    continue
                element = self.config_xml.create_text_element(name, value)
                self.config_xml.append_child(value_node, element)
            WidgetSettings.set_key_values("top_layout", [self.config_xml.to_string()])

    def get_state(self):
            return self.config_xml

