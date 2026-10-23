# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original form accessors on the headless request Container."""
from pyasm.common import Container, Environment
from .web_environment import WebEnvironment


class WebContainer:
    @staticmethod
    def get_buffer():
        buffers = Container.get_seq('WebContainer:buffers')
        return buffers[0] if buffers else WebContainer.push_buffer()

    @staticmethod
    def push_buffer():
        from .widget import Html
        buffer = Html()
        Container.get_seq('WebContainer:buffers').insert(0, buffer)
        return buffer

    @staticmethod
    def pop_buffer():
        return Container.get_seq('WebContainer:buffers').pop(0)

    @staticmethod
    def clear_buffer():
        for buffer in Container.get_seq('WebContainer:buffers'):
            buffer.clear()
        Container.clear_seq('WebContainer:buffers')
        WebContainer.push_buffer()

    @staticmethod
    def get_num_buffers():
        return len(Container.get_seq('WebContainer:buffers'))

    @staticmethod
    def get_palette():
        from .palette import Palette
        return Palette.get()

    @staticmethod
    def get_event_container():
        from .event_container import EventContainer
        events = Container.get('WebContainer:events')
        if events is None:
            events = EventContainer()
            Container.put('WebContainer:events', events)
        return events

    @staticmethod
    def get_security():
        return Environment.get_security()

    @staticmethod
    def get_user_name():
        return Environment.get_user_name()

    @staticmethod
    def get_login():
        return Environment.get_security().get_login()

    @staticmethod
    def set_web(web):
        Container.put('WebContainer::web', web)

    @staticmethod
    def get_web():
        return Container.get('WebContainer::web')


class Web(WebEnvironment):
    def __init__(self, values=None):
        self.params = dict(values or {})

    def set_form_value(self, name, value):
        assert name
        self.params[name] = value

    def get_env(self, name):
        return (Container.get('Api:environ') or {}).get(name, '')

    def get_request_host(self):
        ip = self.get_env('HTTP_X_FORWARDED_FOR')
        if not ip:
            ip = self.get_env('REMOTE_ADDR')
        return ip.split(',')[0].strip() if ip else ''

    def get_base_url(self):
        return Environment.get_base_url()

    def get_palette(self):
        return WebContainer.get_palette()

    def get_project_url(self):
        from pyasm.biz import Project
        url = self.get_base_url()
        url.append_to_base('/tactic')
        url.append_to_base(Project.get_project_code())
        return url

    def get_form_keys(self):
        return self.params.keys()

    def has_form_key(self, key):
        return key in self.params

    def get_form_data(self):
        return self.params

    def get_form_values(self, name, raw=False):
        """returns a string list of the values of a form element.
            If raw is True, then a nonexistant value returns None"""
        try:
            values = self.params[name]
            if isinstance(values, str):
                return [values]
            elif isinstance(values, (int, float, bool, type)):
                return [values]
            elif values.__class__.__name__ in ['FieldStorage', 'datetime']:
                return [values]
            elif not values:
                return []
            elif isinstance(values, list):
                return values
            else:
                return [values]
        except KeyError:
            if raw == True:
                return None
            else:
                return []

    def get_form_value(self, name, raw=False):
        """returns the string value of the form element.
            If raw is True, then a nonexistant value returns None"""
        values = self.get_form_values(name, raw)
        if values == None:
            return None
        if values.__class__.__name__ == 'FieldStorage':
            return values
        elif len(values) > 0:
            return values[0]
        else:
            return ''
