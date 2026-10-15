# Copyright (c) 2005-2008, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native top-layout state; the old Bootstrap application shell is not Vue."""
from pyasm.common import Environment
from tactic.ui.app import PageNavContainerWdg

class BootstrapIndexWdg(PageNavContainerWdg):
    def _get_tab_save_state(self):
            return "main_body_tab_state"

    def _get_top_nav_xml(self):
            return """
            <element name="top_nav">
                  <display class="tactic.ui.bootstrap_app.BootstrapTopNavWdg">
                  </display>
            </element>"""

    def _get_left_nav_xml(self):
             return """
             <element name="left_nav">
               <display class="tactic.ui.bootstrap_app.BootstrapSideBarPanelWdg">
               </display>
             </element> """

    def get_start_link(self):
            return

    def _get_startup_xml(self):
            security = Environment.get_security()
    
            # Use start_link from group security or from kwargs
            start_link = security.get_start_link() or self.kwargs.get('start_link')
            if not start_link:
                start_link = self.get_start_link()
    
            if start_link:
                title = start_link.strip("/")
                parts = title.split("/")
                title = parts[-1].capitalize()
    
                return """
                    <element name="main_body" title="%s">
                        <display class="tactic.ui.panel.HashPanelWdg">
                            <hash>%s</hash>
                        </display>
                    </element>
                """ % (title, start_link)
    
    
            # start_view = "vfx.home.main"
            # start_view = ""
            # if start_view:
            #     return """
            #         <element name="main_body" title="Startup">
            #             <display class="tactic.ui.panel.CustomLayoutWdg">
            #                 <view>%s</view>
            #             </display>
            #         </element>
            #     """ % start_view
    
    
            security = Environment.get_security()
            if security.is_admin():
                return """
                    <element name="main_body" title="Startup">
                      <display class="tactic.ui.startup.MainWdg"/>
                    </element>
                """
            else:
                # FIXME: add a default widget for non-admin users
                return '''
                    <element name="main_body" title="My Tasks">
                      <display class="tactic.ui.panel.ViewPanelWdg">
                        <search_type>sthpw/task</search_type>
                        <expression>@SOBJECT(sthpw/task['assigned','$LOGIN']))</expression>
                        <show_shelf>false</show_shelf>
                      </display>
                    </element>
                '''

    def get_default_config(self):
            use_sidebar = self.kwargs.get('use_sidebar')
    
            top_xml = self._get_top_nav_xml()
            startup_xml = self._get_startup_xml()
    
            if use_sidebar==False:
                config = '''
                <config>
                    <application>
                        %s
                        %s
                    </application>
                </config>
                ''' % (top_xml, startup_xml)
            else:
                left_xml = self._get_left_nav_xml()
                config = '''
                <config>
                    <application>
                        %s
                        %s
                        %s
                    </application>
                </config>
                ''' % (top_xml, left_xml, startup_xml)
    
            return config

