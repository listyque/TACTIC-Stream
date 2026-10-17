# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Table column state/value methods from the original widget; no HTML runtime."""
from pyasm.common import Common, SPTDate
from pyasm.common.errors import UnsupportedContract
from pyasm.web import HtmlElement, WebContainer


class BaseTableElementWdg(HtmlElement):
    def __init__(self, name=None, value=None, **kwargs):
        self.kwargs = kwargs
        self.options = dict(kwargs)
        HtmlElement.__init__(self, 'div')
        self.web = WebContainer.get_web()
        self.name = name
        self.value = value
        self.title = ''
        self.sobjects = []
        self.current_index = -1
        self.search = None
        self.width = 0
        self.view_attributes = {}
        self.attributes = {}
        self.state = {}
        self.parent_wdg = None
        self.layout_wdg = None
        self.filter_data = {}

    def set_sobjects(self, sobjects, search=None):
        if search:
            self.search = search
        self.sobjects = sobjects
        self.current_index = 0

    def set_sobject(self, sobject, search=None):
        if sobject:
            self.set_sobjects([sobject], search)

    def get_sobjects(self):
        return self.sobjects

    def set_current_index(self, index):
        self.current_index = index

    def get_current_index(self):
        return self.current_index

    def get_current_sobject(self):
        if self.current_index == -1 or not self.sobjects:
            return None
        return self.sobjects[self.current_index]

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_title(self, title):
        self.title = title

    def set_value(self, value):
        self.value = value

    def get_value(self, name=None):
        # Original truthiness check discarded explicit 0/False/empty overrides.
        if self.value is not None:
            return self.value
        sobject = self.get_current_sobject()
        return sobject.get_value(name or self.name, no_exception=True) if sobject else ''

    def get_data(self, sobject):
        return sobject.get_value(self.name, no_exception=True)

    def set_option(self, key, value):
        self.options[key] = value

    def set_options(self, options):
        self.options.update(options)

    def get_option(self, key):
        value = self.options.get(key)
        return '' if value is None else value

    def set_attributes(self, attrs):
        self.attributes = attrs

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_parent_wdg(self, widget):
        self.parent_wdg = widget

    def get_parent_wdg(self):
        return self.parent_wdg

    def set_layout_wdg(self, widget):
        self.layout_wdg = widget

    def get_layout_wdg(self):
        return self.layout_wdg

    def get_parent_view(self):
        return self.parent_wdg.get_view() if self.parent_wdg else ''

    def get_width(self):
        return self.width

    def get_class_name(self):
        return Common.get_full_class_name(self)

    def set_filter_data(self, filter_data):
        self.filter_data = filter_data

    def get_filter_data(self):
        return self.filter_data

    def preprocess(self):
        """One call per column, before iterating its rows."""
        pass

    def get_onload_js(self):
        return None

    def handle_tr(self, tr):
        pass

    def handle_td(self, td):
        pass

    def get_text_value(self):
        return self.get_value()

    def get_timezone_value(self, value):
        from pyasm.biz import PrefSetting
        timezone = self.get_option('timezone') or PrefSetting.get_value_by_key('timezone')
        return SPTDate.convert_to_local(value) if timezone in ('local', '') else SPTDate.convert_to_timezone(value, timezone)

    @classmethod
    def is_editable(cls):
        return False

    def is_sortable(self):
        return True

    def is_groupable(self):
        return False

    def is_time_groupable(self):
        return False

    def get_display(self):
        raise UnsupportedContract('Legacy HTML table rendering is excluded')


class CheckboxColWdg(BaseTableElementWdg):
    """The native row selection column carries object identity, not a DB value."""

    def get_cell_value(self):
        return {'text': '', 'search_key': self.get_current_sobject().get_search_key()}


class SearchTypeElementWdg(BaseTableElementWdg):
    def get_cell_value(self):
        from pyasm.search import SearchType, SearchException
        value = self.get_current_sobject().get_value(self.get_name())
        try:
            title = SearchType.get(value).get_title()
        except SearchException:
            title = '--'
        return {'text': str(title)}


class SimpleTableElementWdg(BaseTableElementWdg):
    @classmethod
    def is_editable(cls):
        return True

    def is_groupable(self):
        return True


class ArrayTableElementWdg(BaseTableElementWdg):
    """Native array display from legacy pyasm/widget/table_element_wdg.py."""
    def get_text_value(self):
        value = self.get_value()
        return '' if value is None else value.strip('||').replace('||', ', ')

    def get_cell_value(self):
        return {'text': self.get_text_value()}


class XmlWdg(BaseTableElementWdg):
    """Raw/compressed XML, with the original parse diagnostic and safe text."""
    def is_editable(self):
        return True

    def get_width(self):
        return '600px'

    def get_cell_value(self):
        from pyasm.common import Xml, XmlException, jsondumps
        value = self.get_value()
        if not isinstance(value, str):
            value = jsondumps(value)
        elif value.startswith('zlib:'):
            value = Common.decompress_transaction(value)
        diagnostic = ''
        try:
            Xml(string=value)
        except XmlException as error:
            diagnostic = str(error)
        return {'text': value, 'language': 'xml', 'diagnostic': diagnostic}

