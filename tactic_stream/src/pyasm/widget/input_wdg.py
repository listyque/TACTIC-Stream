# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original primitive input metadata and value resolution; no HTML runtime."""
from pyasm.common import Common, TacticException
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import NamingUtil
from pyasm.search import SearchKey
from pyasm.search import Search
from pyasm.web import WebContainer, WidgetSettings

class InputException(Exception):
    pass


class BaseInputWdg:
    def __init__(self, name=None, type=None, label=None, **kwargs):
        self.name = name
        self.input_prefix = None
        self.value = ''
        self.options = kwargs or dict(default='', persist='false')
        self.kwargs = kwargs
        self.cached_values = None
        self.label = label
        self.title = ''
        self.prefix = ''
        self.parent_wdg = None
        self.state = {}
        self.persistence = False
        self.persistence_obj = None
        self._sobjects = []
        self._attributes = {}

    def set_sobjects(self, sobjects, search=None):
        self._sobjects = sobjects

    def set_sobject(self, sobject, search=None):
        if sobject:
            self.set_sobjects([sobject], search)

    def get_current_sobject(self):
        return self._sobjects[0] if self._sobjects else None

    def get_class_name(self):
        return Common.get_full_class_name(self)

    def add_attr(self, name, value):
        self._attributes[name] = value

    def check_persistent_values(self, values):
        if self.persistence or self.get_option('persist') == 'true':
            raise UnsupportedContract('Persistent/filter input state is not migrated')
        return False

    check_persistent_display = check_persistent_values

    def _set_persistent_values(self, values):
        if self.persistence:
            raise UnsupportedContract('Persistent/filter input state is not migrated')

    def get_display(self):
        raise UnsupportedContract('Legacy HTML widget rendering is excluded')


    def set_state(self, state):
        """Set the state for this table element"""
        self.state = state

    def get_state(self):
        """get the state for this table element"""
        return self.state

    def set_title(self, title):
        self.title = title

    def get_display_title(self):
        """Function that that gives a title represenation of this widget"""
        if self.title:
            return self.title
        name = self.get_name()
        name = name.replace('_', ' ')
        return name.title()

    def set_parent_wdg(self, parent_wdg):
        """method to set the parent widget.  This is typicaly the EditWdg"""
        self.parent_wdg = parent_wdg

    def get_parent_wdg(self):
        return self.parent_wdg

    def set_input_prefix(self, input_prefix):
        self.input_prefix = input_prefix

    def get_input_name(self, name=''):
        input_name = self.name
        if name:
            input_name = name
        if self.input_prefix:
            return '%s|%s' % (self.input_prefix, input_name)
        else:
            return input_name

    def set_name(self, name):
        """set the name externally"""
        self.name = name

    def get_name(self):
        return self.name

    def set_options(self, options):
        self.options = options
        if self.has_option('search_key'):
            search_key = options.get('search_key')
            if search_key:
                sobj = SearchKey.get_by_search_key(search_key)
                self.set_sobjects([sobj])

    def has_option(self, key):
        return key in self.options

    def set_option(self, key, value):
        if isinstance(value, type({}.keys())):
            value = list(value)
        self.options[key] = value

    def get_option(self, key):
        """gets the value of the specified option"""
        if key in self.options:
            return self.options[key]
        else:
            return ''

    def is_read_only(self):
        """ if the read_only option is true, either set disabled or readonly"""
        if self.get_option('read_only') in ['true', True]:
            return True
        return False

    def is_edit_only(self):
        return self.get_option('edit_only') == 'true'

    def is_editable(self):
        return True

    def get_timezone_value(self, value):
        '''Use the widget timezone, then My Preferences timezone, then local time.'''
        from pyasm.biz import PrefSetting
        from pyasm.common import SPTDate
        timezone = self.get_option('timezone')
        if not timezone:
            timezone = PrefSetting.get_value_by_key('timezone')
        if timezone in ['local', '']:
            return SPTDate.convert_to_local(value)
        return SPTDate.convert_to_timezone(value, timezone)

    def get_values(self, for_display=False):
        """gets the current value of this input element.  The order of
        importance is as follows.  If the form was submitted, this value
        will always take precedence.  Then externally set values through
        code."""
        values = []
        if self.get_option('value'):
            values = [self.get_option('value')]
            return values
        web = WebContainer.get_web()
        if self.has_option('search_key') and (not self.get_current_sobject()):
            sobject = SearchKey.get_by_search_key(self.options.get('search_key'))
            if sobject:
                self.set_sobjects([sobject])
        cgi_values = web.get_form_values(self.get_input_name())
        if for_display:
            column = self.get_option('column')
            if not column:
                column = self.name
            current_sobject = self.get_current_sobject()
            if current_sobject and current_sobject.has_value(column):
                sobject = self.get_current_sobject()
                values = [sobject.get_value(column)]
                if not values:
                    values = []
                return values
            if self.value != '':
                values = [self.value]
                self._set_persistent_values(values)
                return values
            values = self.check_persistent_display(cgi_values)
            if values != False:
                return values
            else:
                values = []
            if self.get_option('web_state') == 'true':
                values = cgi_values
                if values and values[0] != '':
                    self._set_persistent_values(values)
                    return values
        elif self.cached_values != None:
            return self.cached_values
        else:
            temp_values = self.check_persistent_values(cgi_values)
            if temp_values != False:
                return temp_values
        if not for_display and cgi_values:
            values = cgi_values
        elif self.value != '':
            values = [self.value]
        elif self.get_current_sobject() and self.get_current_sobject().has_value(self.name):
            sobject = self.get_current_sobject()
            values = [sobject.get_value(self.name)]
            if not values:
                values = []
        elif self.get_option('web_state') == 'true':
            values = cgi_values
            self._set_persistent_values(values)
            self.cached_values = values
            return values
        elif self.persistence:
            class_path = Common.get_full_class_name(self.persistence_obj)
            key = '%s|%s' % (class_path, self.name)
            values = WidgetSettings.get_key_values(key)
        if values == None and self.persistence or (values == [] and (not self.persistence)):
            default = self.get_option('default')
            if default != '':
                if isinstance(default, list):
                    values = default
                else:
                    values = [default]
                new_values = []
                for value in values:
                    new_value = NamingUtil.eval_template(value)
                    new_values.append(new_value)
                values = new_values
            else:
                values = []
        if values:
            web.set_form_value(self.get_input_name(), values)
            self._set_persistent_values(values)
        if not for_display:
            self.cached_values = values
        return values

    def get_value(self, for_display=False):
        values = self.get_values(for_display)
        if not values:
            return ''
        else:
            return values[0]

    def set_value(self, value, set_form_value=True):
        self.value = value
        name = self.get_input_name()
        if not name:
            return
        if set_form_value:
            web = WebContainer.get_web()
            web.set_form_value(name, value)

    def is_form_submitted(self):
        web = WebContainer.get_web()
        if web.get_form_value('is_from_login') == 'yes':
            return False
        if web.get_form_value('ajax'):
            return True
        return web.get_form_value('is_form_submitted') == 'yes'


class HiddenWdg(BaseInputWdg):
    def __init__(self, name=None, value=''):
        super().__init__(name, 'input')
        self.value = value

    def get_title(self):
        return None


class BaseTextWdg(BaseInputWdg):
    pass


class TextWdg(BaseTextWdg):
    def __init__(self, name=None, label=None, **kwargs):
        super().__init__(name, 'input', label=label, **kwargs)
        self.css = 'inputfield'


class TextAreaWdg(BaseTextWdg):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, 'textarea', **kwargs)


class CheckboxWdg(BaseInputWdg):
    def __init__(self, name=None, label=None, css=None, **kwargs):
        super().__init__(name, 'input', label, **kwargs)
        self.css = css


class SelectWdg(BaseInputWdg):
    """SelectWdg option preparation; expressions use the caller's access rights."""
    SELECT_LABEL = '- Select -'

    def __init__(self, name=None, **kwargs):
        super().__init__(name, 'select', **kwargs)
        self.values = []
        self.labels = []
        self.related_type = None
        self.has_set_options = False
        self.empty_option_flag = False
        self.empty_option_label, self.empty_option_value = self.SELECT_LABEL, ''
        self.append_list = []

    def add_empty_option(self, label='---', value=''):
        self.empty_option_flag = True
        self.empty_option_label, self.empty_option_value = label, value

    def append_option(self, label, value):
        self.append_list.append((label, value))

    def set_options(self, options):
        super().set_options(options)
        self.has_set_options = False

    def set_option(self, key, value):
        super().set_option(key, value)
        self.has_set_options = False

    def set_dom_options(self, is_run=True):
        values = self.get_option('values')
        labels = self.get_option('labels')
        if not values and self.get_option('setting'):
            from pyasm.biz import ProjectSetting
            values = ProjectSetting.get_seq_by_key(self.get_option('setting'))
            setting = ProjectSetting.get_by_key(self.get_option('setting'))
            if setting and setting.get_value('type') == 'map':
                pairs = ProjectSetting.get_map_by_key(self.get_option('setting'))
                values, labels = [item[0] for item in pairs], [item[1] for item in pairs]
            else:
                labels = values
        self.values = list(values) if isinstance(values, list) else str(values).split('|')
        self.labels = list(labels) if isinstance(labels, list) else str(labels).split('|') if labels else self.values[:]
        if len(self.values) != len(self.labels):
            raise InputException('values [%s] does not have the same number of elements as [%s]' % (self.values, self.labels))
        query = self.get_option('query')
        if query:
            search_type, value_column, label_column = query.split('|')
            if not value_column or not label_column:
                raise InputException('Query string for SelectWdg is malformed [%s]' % query)
            if '()' in value_column or '()' in label_column:
                raise UnsupportedContract('Method-based select queries are not migrated')
            search = Search(search_type)
            if self.get_option('query_filter'):
                search.add_where(self.get_option('query_filter'))
            if self.get_option('query_limit'):
                search.add_limit(int(self.get_option('query_limit')))
            search.add_order_by(label_column)
            self.related_type = search_type
            objects = search.get_sobjects()
            self.values = [obj.get_value(value_column, no_exception=True) for obj in objects]
            self.labels = [obj.get_value(label_column, no_exception=True) for obj in objects]
        values_expr = self.get_option('values_expr') or self.kwargs.get('values_expr')
        labels_expr = self.get_option('labels_expr') or self.kwargs.get('labels_expr')
        if values_expr:
            objects = self._sobjects if self.get_option('mode_expr') == 'relative' else []
            self.values = Search.eval(values_expr, objects)
            if not isinstance(self.values, (list, tuple)):
                self.values = [] if self.values is None else [self.values]
            self.labels = Search.eval(labels_expr, objects) if labels_expr else list(self.values)
            if not isinstance(self.labels, (list, tuple)):
                self.labels = [] if self.labels is None else [self.labels]
            if len(self.values) != len(self.labels):
                raise InputException('Values and labels expressions returned different counts')
            pairs = sorted(zip(self.values, self.labels), key=lambda pair: pair[1])
            self.values, self.labels = [item[0] for item in pairs], [item[1] for item in pairs]
        extra_values = self.get_option('extra_values')
        if extra_values:
            self.values.extend(extra_values.split('|'))
            extra_labels = self.get_option('extra_labels')
            self.labels.extend(extra_labels.split('|') if extra_labels else extra_values.split('|'))
            if len(self.values) != len(self.labels):
                raise InputException('Extra values and labels have different counts')
        if self.empty_option_flag or self.get_option('empty') not in ('', 'false') or self.get_option('empty_label'):
            self.values.insert(0, self.empty_option_value)
            self.labels.insert(0, self.get_option('empty_label') or self.empty_option_label)
        for label, value in self.append_list:
            self.values.append(value)
            self.labels.append(label)
        if is_run:
            self.has_set_options = True

    def get_select_values(self):
        if not self.has_set_options:
            self.set_dom_options()
        return self.labels, self.values

    def get_display(self):
        # Handler discards rendering and reads values/labels after this initialization.
        # This headless control is not the excluded HTML transport renderer.
        self.get_select_values()
        return self


class MultiSelectWdg(SelectWdg):
    def __init__(self, name=None, label='', css=None, **kwargs):
        super().__init__(name, label=label, **kwargs)
        self.css = css

    def _is_selected(self, value, current_values):
        if not current_values:
            return False
        if len(current_values) == 1:
            current_value = current_values[0]
            if isinstance(current_value, str) and current_value.startswith('||') and current_value.endswith('||'):
                current_values = current_value.strip('||').split('||')
        return value in current_values


class UploadWdg(BaseInputWdg):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

    @classmethod
    def get_default_action(cls):
        return 'MultiUploadAction'

    def get_input(self):
        names = self.get_option('names')
        required = self.get_option('required')
        names = names.split('|') if names else [self.name]
        if len(set(names)) != len(names):
            raise TacticException('[names] in the config file must be unique')
        if self.get_option('names') and required:
            required = required.split('|')
            if len(required) != len(names):
                raise TacticException('required needs to match the number of names if defined in the config file.')
        else:
            required = ['false'] * len(names)
        self.upload_fields = [dict(name=name, required=flag == 'true') for name, flag in zip(names, required)]
        context = self.get_option('context')
        setting = self.get_option('setting')
        self.subcontext = bool(context or setting)
        context_name = '%s|context' % self.get_input_name()
        if context or setting:
            self.context_input = SelectWdg(context_name)
            self.context_input.set_option('values' if context else 'setting', context or setting)
        elif self.get_option('pipeline'):
            from pyasm.biz import Pipeline
            pipeline = Pipeline.get_by_sobject(self.get_current_sobject())
            if not pipeline:
                raise InputException('Upload context requires an object pipeline')
            self.context_input = SelectWdg(context_name)
            self.context_input.set_option('values', pipeline.get_process_names(recurse=True))
        else:
            self.context_input = TextWdg(context_name)
        return self


class ThumbInputWdg(BaseInputWdg):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

    def is_read_only(self):
        return True

