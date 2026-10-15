# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original EditWdg configuration/field preparation, without HTML generation."""
from ast import literal_eval
from pyasm.common import Common, Environment, jsonloads, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Project
from pyasm.search import Search, SearchType, SearchKey, WidgetDbConfig
from pyasm.widget import WidgetConfig, WidgetConfigView, TextWdg, TextAreaWdg, CheckboxWdg
from pyasm.web import WebContainer, Web

basestring = str
EditException = TacticException

class EditWdg:
    def __init__(self, **kwargs):
        if WebContainer.get_web() is None:
            WebContainer.set_web(Web())
        self.kwargs = kwargs
        self.title = ''
        self.security_denied = False
        self.widgets = []
        self.sobjects = []
        if kwargs.get('layout_view'):
            raise UnsupportedContract('Custom HTML form layouts are excluded')
        self.init()

    def set_sobjects(self, sobjects, search=None):
        self.sobjects = sobjects
        self.search = search

    def get_widgets(self):
        return self.widgets

    def explicit_display(self, cls=None):
        # Handler calls this to initialize inputs, then reads their metadata.
        # HTML generation remains excluded; get_display never returns JSON as HTML.
        if cls is not None:
            raise UnsupportedContract('Alternative HTML form renderers are excluded')
        for widget in self.widgets:
            widget.set_input_prefix(self.input_prefix)
            if hasattr(widget, 'get_input'):
                widget.input = widget.get_input()
            widget.get_values()

    def get_display(self):
        raise UnsupportedContract('Legacy HTML widget rendering is excluded')

    @classmethod
    def get_default_display_wdg(cls, element_name, display_options, element_type, kbd_handler=False):
        if element_type in ('integer', 'smallint', 'bigint', 'int', 'int2', 'int4', 'int8', 'string', 'link', 'varchar', 'character', 'timecode'):
            widget = TextWdg('main')
        elif element_type in ('float', 'text'):
            widget = TextAreaWdg('main')
        elif element_type == 'boolean':
            widget = CheckboxWdg('main')
        elif element_type in ('timestamp', 'date', 'time', 'datetime2'):
            from tactic.ui.widget import CalendarInputWdg
            if element_name.endswith('_time'):
                widget = TextWdg('main')
            else:
                widget = CalendarInputWdg()
                widget.set_option('show_activator', False)
        elif element_type == 'datetime':
            from tactic.ui.widget import CalendarInputWdg
            widget = CalendarInputWdg()
            widget.set_option('show_time', 'true')
        elif element_type == 'sqlserver_timestamp':
            return None
        else:
            raise UnsupportedContract('Input type is not migrated: ' + str(element_type))
        # Date/time defaults keep the original widget options as well as XML options.
        if element_type == 'datetime' or element_type in ('timestamp', 'date', 'time', 'datetime2') and not element_name.endswith('_time'):
            widget.set_options(dict(widget.options, **display_options))
        else:
            widget.set_options(display_options)
        return widget


    def init(self):
        self.is_refresh = self.kwargs.get('refresh')
        self.search_key = self.kwargs.get('search_key')
        self.ticket_key = self.kwargs.get('ticket')
        self.parent_key = self.kwargs.get('parent_key')
        self.expression = self.kwargs.get('expression')
        self.disables = self.kwargs.get('disables')
        if not self.disables:
            self.disables = {}
        self.code = self.kwargs.get('code')
        sobject = None
        if self.search_key:
            sobject = Search.get_by_search_key(self.search_key)
            if not sobject:
                raise Exception('No sobject found for search_key [%s]' % self.search_key)
            self.search_id = sobject.get_id()
            self.search_type = sobject.get_base_search_type()
            if sobject.is_insert():
                self.mode = 'insert'
            else:
                self.mode = 'edit'
        elif self.expression:
            sobject = Search.eval(self.expression, single=True)
            self.search_id = sobject.get_id()
            self.search_type = sobject.get_base_search_type()
            self.mode = 'edit'
        elif self.ticket_key:
            raise Exception('EditWdg: ticket_key no long supported')
            '\n            from pyasm.security import Ticket, Login\n            ticket = Ticket.get_by_valid_key(self.ticket_key)\n            if not ticket:\n                raise TacticException("No valid ticket")\n            login_code = ticket.get_value("login")\n            login = Login.get_by_code(login_code)\n            self.search_type = "sthpw/login"\n            self.search_id = login.get_id()\n            self.mode = \'edit\'\n            '
        elif self.code:
            self.search_type = self.kwargs.get('search_type')
            search = Search(self.search_type)
            search.add_filter('code', self.code)
            sobject = search.get_sobject()
            self.search_id = sobject.get_id()
            self.search_type = sobject.get_base_search_type()
            self.mode = 'edit'
        else:
            self.search_type = self.kwargs.get('search_type')
            self.search_id = self.kwargs.get('search_id')
            if not self.search_id:
                self.search_id = -1
            self.search_id = int(self.search_id)
            if self.search_id != -1:
                self.mode = 'edit'
            else:
                self.mode = 'insert'
        assert self.search_type
        if self.kwargs.get('mode'):
            self.mode = self.kwargs.get('mode')
        self.view = self.kwargs.get('view')
        if not self.view:
            self.view = self.kwargs.get('config_base')
        if not self.view:
            self.view = 'edit'
        self.display_mode = self.kwargs.get('display_mode')
        if not self.display_mode:
            self.display_mode = 'default'
        default_data = self.kwargs.get('default')
        if not default_data:
            default_data = {}
        elif isinstance(default_data, basestring):
            try:
                default_data = jsonloads(default_data)
            except:
                try:
                    default_data = literal_eval(default_data)
                except:
                    print('Warning: Cannot evaluate [%s]' % default_data)
                    default_data = {}
        if sobject:
            self.set_sobjects([sobject], None)
        else:
            self.do_search()
        if self.view not in ['insert', 'edit']:
            self.config = self.get_config()
        else:
            self.config = WidgetConfigView.get_by_search_type(self.search_type, self.view, use_cache=False)
        config_xml = self.kwargs.get('config_xml')
        if config_xml:
            config = WidgetConfig.get(view='tab', xml=config_xml)
            self.config.insert_config(0, config)
            config = WidgetConfig.get(view=self.view, xml=config_xml)
            self.config.insert_config(0, config)
        self.skipped_element_names = []
        layout_view = self.kwargs.get('layout_view')
        if layout_view:
            layout_view = layout_view.replace('/', '.')
            search = Search('config/widget_config')
            search.add_filter('view', layout_view)
            layout_config = search.get_sobject()
            xml = layout_config.get_xml_value('config')
            self.element_names = xml.get_values('config//html//element/@name')
        else:
            self.element_names = self.config.get_element_names()
        override_element_names = self.kwargs.get('element_names')
        if override_element_names:
            self.element_names = override_element_names
            self.element_names = self.element_names.split(',')
        ignore = self.kwargs.get('ignore')
        if isinstance(ignore, basestring):
            ignore = ignore.split('|')
        if not ignore:
            ignore = []
        self.element_titles = []
        self.element_descriptions = []
        for element_name in self.element_names:
            self.element_titles.append(self.config.get_element_title(element_name))
            self.element_descriptions.append(self.config.get_element_description(element_name))
        if not self.element_names:
            impl = SearchType.get_database_impl_by_search_type(self.search_type)
            if impl.get_database_type() == 'MongoDb':
                self.element_names = impl.get_default_columns()
                self.element_titles = ['Code', 'Name', 'Description']
                self.element_descriptions = ['Code', 'Name', 'Description']
        self.input_prefix = self.kwargs.get('input_prefix')
        if not self.input_prefix:
            self.input_prefix = 'edit'
        security = Environment.get_security()
        default_access = 'edit'
        project_code = Project.get_project_code()
        if self.parent_key:
            from pyasm.biz import Schema
            schema = Schema.get()
            parent_stype = SearchKey.extract_base_search_type(self.parent_key)
            relationship = schema.get_relationship_attrs(parent_stype, self.search_type)
            for element_name in self.element_names:
                if element_name == relationship.get('from_col'):
                    ignore.append(element_name)
        for i, element_name in enumerate(self.element_names):
            if element_name in ignore:
                self.skipped_element_names.append(element_name)
                continue
            access_key2 = {'search_type': self.search_type, 'project': project_code}
            access_key1 = {'search_type': self.search_type, 'key': element_name, 'project': project_code}
            access_keys = [access_key1, access_key2]
            is_editable = security.check_access('element', access_keys, 'edit', default=default_access)
            if not is_editable:
                self.skipped_element_names.append(element_name)
                continue
            widget = self.config.get_display_widget(element_name, kbd_handler=False)
            if not widget:
                self.skipped_element_names.append(element_name)
                continue
            widget.set_sobject(self.sobjects[0])
            widget.set_state({'search_type': self.search_type})
            default_value = default_data.get(element_name)
            if element_name in default_data:
                widget.set_value(default_value)
            attrs = self.config.get_element_attributes(element_name)
            editable = widget.is_editable()
            if editable:
                editable = attrs.get('edit')
                editable = editable != 'false'
            if not editable:
                self.skipped_element_names.append(element_name)
                continue
            widget.set_parent_wdg(self)
            if self.mode == 'insert' and self.parent_key:
                widget.set_option('parent_key', self.parent_key)
            title = self.element_titles[i]
            if title:
                widget.set_title(title)
            description = attrs.get('description')
            if description:
                widget.add_attr('description', description)
            self.widgets.append(widget)
            description = self.element_descriptions[i]
            widget.add_attr('title', description)

    def get_config(self):
        configs = []
        config = WidgetDbConfig.get_by_search_type(self.search_type, self.view)
        get_edit_def = False
        if config:
            configs.append(config)
            get_edit_def = True
            config = WidgetDbConfig.get_by_search_type(self.search_type, 'edit_definition')
            if config:
                configs.append(config)
        else:
            if self.mode == 'insert':
                config = WidgetDbConfig.get_by_search_type(self.search_type, 'insert')
                if config:
                    configs.append(config)
            config = WidgetDbConfig.get_by_search_type(self.search_type, 'edit')
            if config:
                configs.append(config)
        file_configs = WidgetConfigView.get_configs_from_file(self.search_type, self.view)
        configs.extend(file_configs)
        file_configs = WidgetConfigView.get_configs_from_file(self.search_type, 'edit')
        configs.extend(file_configs)
        if not get_edit_def:
            config = WidgetDbConfig.get_by_search_type(self.search_type, 'edit_definition')
            if config:
                configs.append(config)
        config = WidgetConfigView(self.search_type, self.view, configs, layout='EditWdg')
        return config

    def do_search(self):
        """this widget has its own search mechanism"""
        web = WebContainer.get_web()
        id = self.search_id
        search = None
        sobject = None
        search_type_base = SearchType.get(self.search_type).get_base_key()
        if self.mode == 'insert':
            sobject = SearchType.create(self.search_type)
            self.current_id = -1
            value_keys = web.get_form_keys()
            if value_keys:
                for key in value_keys:
                    value = web.get_form_value(key)
                    sobject.set_value(key, value)
        else:
            search = Search(self.search_type)
            if web.get_form_value('do_edit') == 'Edit/Next':
                search_ids = web.get_form_value('%s_search_ids' % search_type_base)
                if search_ids == '':
                    self.current_id = id
                else:
                    search_ids = search_ids.split('|')
                    next = search_ids.index(str(id)) + 1
                    if next == len(search_ids):
                        next = 0
                    self.current_id = search_ids[next]
                    last_search = Search(self.search_type)
                    last_search.add_id_filter(id)
                    self.last_sobject = last_search.get_sobject()
            else:
                self.current_id = id
            search.add_id_filter(self.current_id)
            sobject = search.get_sobject()
        if not sobject and self.current_id != -1:
            raise EditException('No SObject found')
        self.set_sobjects([sobject], search)

    @classmethod
    def get_default_display_handler(cls, element_name):
        return None
