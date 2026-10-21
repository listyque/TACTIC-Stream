"""Snapshot dependency action for configured tables."""
from .table_element_wdg import BaseTableElementWdg
from pyasm.biz import Project
from pyasm.search import SearchKey


class DependencyLink(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        base = obj.get_base_search_type()
        if base == 'sthpw/project':
            project = obj.get_code()
        elif base.startswith('sthpw/'):
            project = obj.get_value('project_code', no_exception=True) or Project.get_project_code()
        else:
            project = SearchKey.extract_project(obj.get_search_type()) or Project.get_project_code()
        return dict(text='', targetSearchKey=obj.get_search_key(), projectCode=project,
            actions=[dict(name='dependencies', label='Dependencies', icon='account-tree')])
