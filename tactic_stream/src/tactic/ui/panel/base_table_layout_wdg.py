# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Configuration/column preparation from BaseTableLayoutWdg, without HTML."""
from pyasm.common import TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.search import Search
from pyasm.widget import WidgetConfig, WidgetConfigView
from pyasm.web import Widget


class BaseTableLayoutWdg(Widget):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        Widget.__init__(self)
        self.search_type = kwargs.get('search_type')
        if not self.search_type:
            raise TacticException('Must define a search type')
        self.view = kwargs.get('view')
        if not self.view or self.view == 'None':
            self.view = 'table'
        self.config = kwargs.get('config')
        config_xml = kwargs.get('config_xml')
        config_code = kwargs.get('config_code')
        if config_xml:
            self.config = WidgetConfigView.get_by_search_type(self.search_type, self.view, use_cache=False)
            self.config.insert_config(0, WidgetConfig.get(view=self.view, xml=config_xml))
        elif config_code:
            config = Search.get_by_code('config/widget_config', config_code)
            if not config:
                raise TacticException('No widget config found: ' + config_code)
            self.config = WidgetConfigView(None, config.get_value('view'), [config])
        elif not self.config:
            self.config = WidgetConfigView.get_by_search_type(self.search_type, self.view)
        self.element_names = kwargs.get('element_names') or self.config.get_element_names()
        if isinstance(self.element_names, str):
            self.element_names = self.element_names.replace(' ', '').split(',')
        self.element_titles = [self.config.get_element_title(name) for name in self.element_names]
        self.element_widths = self.config.get_element_widths()
        self.sobjects = []
        self.search = None
        self.widgets = []
        for index, name in enumerate(self.element_names):
            widget = self.config.get_display_widget(name)
            widget.set_title(self.element_titles[index])
            widget.set_layout_wdg(self)
            widget.width = self.element_widths[index] if index < len(self.element_widths) else 150
            self.widgets.append(widget)

    @classmethod
    def get_default_display_handler(cls, element_name):
        return 'tactic.ui.common.SimpleTableElementWdg'

    def get_config(self):
        return self.config

    def get_view(self):
        return self.view

    def get_widgets(self):
        return self.widgets

    def get_widget(self, name):
        return next((widget for widget in self.widgets if widget.get_name() == name), None)

    def set_sobjects(self, sobjects, search=None):
        self.sobjects = sobjects
        self.search = search
        self.current_index = 0
        for widget in self.widgets:
            widget.set_sobjects(sobjects, search)

    def get_display(self):
        raise UnsupportedContract('Legacy HTML table rendering is excluded')

