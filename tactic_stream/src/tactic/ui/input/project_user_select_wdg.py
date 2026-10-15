# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Project/user selectors from prod_input_wdg.py, without production or HTML."""
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.widget import SelectWdg


class ProjectSelectWdg(SelectWdg):
    def __init__(self, name='project_filter', label='', css='med'):
        super().__init__(name, label=label, css=css)
        self.add_empty_option('-- Select a Project --')

    def get_input(self):
        search = Search('sthpw/project')
        search.add_where("\"code\" not in ('sthpw','admin')")
        projects = search.get_sobjects()
        codes = [project.get_code() for project in projects]
        self.set_option('values', codes)
        self.set_option('labels', codes)
        self.set_option('default', Project.get_project_code())
        self.get_select_values()
        return self

    get_display = get_input


class UserSelectWdg(SelectWdg):
    def __init__(self, name='user_filter', **kwargs):
        super().__init__(name, **kwargs)
        self.add_empty_option('-- Select a User --')

    def get_input(self):
        search = Search('sthpw/login', sudo=True)
        logins = [user.get_value('login') for user in search.get_sobjects()]
        # Original always appended admin, even when already returned by the query.
        if 'admin' not in logins:
            logins.append('admin')
        self.set_option('values', logins)
        self.set_option('labels', logins)
        if self.kwargs.get('default_user') == 'true':
            self.set_option('default', Environment.get_user_name())
        self.get_select_values()
        return self

    get_display = get_input
