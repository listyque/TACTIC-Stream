# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original task parent resolution, without the HTML lookup popup."""
from pyasm.biz import Project
from pyasm.search import SearchKey
from pyasm.widget import BaseInputWdg, HiddenWdg
from pyasm.common.errors import UnsupportedContract

__all__ = ['TaskSObjectInputWdg']


class TaskSObjectInputWdg(BaseInputWdg):
    def get_input(self):
        current = self.get_current_sobject()
        self.parent_project = None
        self.no_parent_type = False
        if current.is_insert():
            parent_key = self.get_option('parent_key')
            if parent_key:
                parent = SearchKey.get_by_search_key(parent_key)
                if not parent:
                    raise ValueError('Task parent no longer exists')
                self.parent_label = parent.get_code()
            else:
                self.parent_project = Project.get_project_code()
                self.parent_label = 'Project: %s' % Project.get_project_code()
            text = HiddenWdg(self.get_input_name(), parent_key)
            text.set_option('size', '40')
            return text
        search_type = current.get_value('search_type')
        self.no_parent_type = not search_type
        self.parent_label = 'No parent type'
        if search_type:
            parent = current.get_parent()
            if not parent:
                raise UnsupportedContract('Task parent lookup for missing objects is not migrated')
            self.parent_label = parent.get_code()
        return HiddenWdg(self.get_input_name())
