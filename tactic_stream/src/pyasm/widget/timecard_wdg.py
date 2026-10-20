"""Timecard identity and original Monday–Sunday values, without the CGI controls."""
from pyasm.widget.table_element_wdg import BaseTableElementWdg
from pyasm.search import Search


class WeekTableElement(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        days = [dict(day=day, label=day.title(), value=str(obj.get_value(day) or ''))
                for day in ('mon','tue','wed','thu','fri','sat','sun')]
        return dict(text='', widthHint=430, timeDays=days, total=sum(float(item['value'] or 0) for item in days))


class TimecardInfoTableElement(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        obj = self.get_current_sobject()
        search_type = obj.get_value('search_type')
        if not search_type:
            return dict(text='', label='General')
        if search_type.split('?')[0] != 'sthpw/task':
            raise ValueError('The original timecard supports task associations only')
        task = Search.get_by_id(search_type, obj.get_value('search_id'))
        if task is None:
            return dict(text='', label='Task is unavailable')
        parent = task.get_parent()
        return dict(text=' · '.join(str(value) for value in (
            parent.get_code() if parent else '', task.get_value('process'), task.get_value('description')) if value),
            targetSearchKey=task.get_search_key(),
            actions=[dict(name='sobject_detail', label='Open details', icon='search')])
