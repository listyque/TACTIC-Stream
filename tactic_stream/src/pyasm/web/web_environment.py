# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native top-class resolution; HTTP/form access is owned by WebContainer.Web."""
from pyasm.common import Environment, Config
from pyasm.biz import Project


class WebEnvironmentException(Exception):
    pass


class WebEnvironment(Environment):
    DEFAULT_TOP_CLASS = 'tactic.ui.bootstrap_app.BootstrapIndexWdg'

    def get_browser(self):
        user_agent = self.get_env('HTTP_USER_AGENT')
        if not user_agent:
            return ''
        if 'MSIE' in user_agent:
            return 'IE'
        if 'Qt' in user_agent:
            return 'Qt'
        if 'WebKit' in user_agent:
            return 'Webkit'
        return 'Mozilla'

    def is_IE(self):
        return self.get_browser() == 'IE'

    def is_Qt_OSX(self):
        user_agent = self.get_env('HTTP_USER_AGENT')
        return 'Qt' in user_agent and 'Safari' in user_agent

    @classmethod
    def get_top_class_name(cls):
        project = Project.get()
        class_name = project.get_value('top_class_name', no_exception=True)
        if not class_name:
            class_name = Config.get_value('install', 'top_class_name')
        if not class_name:
            class_name = cls.DEFAULT_TOP_CLASS
        return class_name
