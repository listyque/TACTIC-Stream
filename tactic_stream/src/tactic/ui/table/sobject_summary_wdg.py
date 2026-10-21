"""SObjectFilesElementWdg inspector target; file reads use the native inspector."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
from tactic.ui.common import BaseTableElementWdg


def read_summary_cell(search_key):
    """Original summary values, using bounded SQL aggregates instead of all hours."""
    from pyasm.biz import Project
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if SearchKey.extract_project(search_key) not in (None, '', 'sthpw', 'admin', Project.get_project_code()):
        raise ValueError('The configured table target belongs to another project')
    parent = Search.get_by_search_key(search_key)
    if parent is None:
        raise LookupError('Object is no longer available')
    if parent.get_base_search_type() in ('sthpw/message', 'sthpw/message_log'):
        raise ValueError('Open private messages from Messages')
    is_project = parent.get_base_search_type() == 'sthpw/project'
    project = parent.get_code() if is_project else Project.get_project_code()
    result = []
    for search_type, label, icon in (
            ('sthpw/task', 'Tasks', 'task'),
            ('sthpw/snapshot', 'Checkins', 'upload'),
            ('sthpw/note', 'Notes', 'comment'),
            ('sthpw/work_hour', 'Work Hours', 'schedule')):
        search = Search(search_type)
        search.add_filter('project_code', project)
        if not is_project:
            search.add_parent_filter(parent)
        if search_type == 'sthpw/work_hour':
            search.add_column('SUM(straight_time)', quoted=False, as_column='total')
            aggregate = search.get_sobject()
            value = aggregate.get_value('total') if aggregate else 0
        else:
            value = search.get_count()
        entry = dict(label=label, icon=icon, value=str(value or 0))
        if search_type in ('sthpw/task', 'sthpw/snapshot'):
            entry['nestedTable'] = dict(searchType=search_type, view='table', parentKey=search_key,
                projectCode=project, selection=True, insert=False, shelf=False)
        result.append(entry)
    return dict(text='', targetSearchKey=search_key, summary=result)


class SObjectSummaryElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        return read_summary_cell(self.get_current_sobject().get_search_key())


class SObjectFilesElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        return dict(text='', targetSearchKey=self.get_current_sobject().get_search_key(use_id=False))
