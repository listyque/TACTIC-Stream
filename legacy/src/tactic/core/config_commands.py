"""Legacy configuration test command kept separate from metadata imports."""
from pyasm.command import Command

class WidgetConfigTestCmd(Command):
    '''This is used for Client API testing only'''

    def execute(self):
        search_type = self.kwargs.get('search_type')
        element_name = self.kwargs.get('element_name')
        view = self.kwargs.get('view')
        match = self.kwargs.get('match')
        
        from .sidebar_config import SidebarConfig
        config_view = SidebarConfig.get_config(search_type, view)
        expected = config_view.get_display_handler(element_name)
        display_options = config_view.get_display_options(element_name)
        
        if match != expected:
            from pyasm.common import TacticException
            raise TacticException('Match falied ', match, expected)
        
        # send some info back for further assertion
        self.info['display_options'] = display_options
        self.info['display_handler'] = expected
