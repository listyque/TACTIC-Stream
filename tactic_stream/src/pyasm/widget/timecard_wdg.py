"""Timecard identity and original Monday–Sunday values, without the CGI controls."""
import datetime
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.widget.table_element_wdg import BaseTableElementWdg

DAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


def _week_monday(obj):
    year = obj.get_value('year', no_exception=True)
    week = obj.get_value('week', no_exception=True)
    if year and week:
        try:
            return datetime.date.fromisocalendar(int(year), max(1, min(53, int(week))), 1)
        except ValueError:
            return datetime.date(int(year), 1, 1)
    return None


class WeekTableElement(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('width',), {})

    def is_editable(self):
        return False

    def preprocess(self):
        raw_width = self.get_option('width')
        if raw_width not in ('', None) and (not str(raw_width).isdecimal() or int(raw_width) <= 0):
            raise ValueError('Invalid timecard week width')
        self._daily_totals = {day: 0.0 for day in DAYS}
        self._tasks = {}
        task_ids = []
        for obj in self.sobjects or []:
            for day in DAYS:
                self._daily_totals[day] += float(obj.get_value(day, no_exception=True) or 0)
            stype = str(obj.get_value('search_type', no_exception=True) or '').split('?')[0]
            sid = obj.get_value('search_id', no_exception=True)
            if stype == 'sthpw/task' and sid:
                task_ids.append(sid)
        if task_ids:
            self._tasks = {str(task.get_id()): task for task in Search.get_by_id('sthpw/task', list(dict.fromkeys(task_ids)))}

    def get_cell_value(self):
        raw_width = self.get_option('width')
        if raw_width not in ('', None) and (not str(raw_width).isdecimal() or int(raw_width) <= 0):
            raise ValueError('Invalid timecard week width')
        obj = self.get_current_sobject()
        monday = _week_monday(obj)
        days = []
        for idx, day in enumerate(DAYS):
            day_key = str(monday + datetime.timedelta(days=idx)) if monday else day
            days.append(dict(day=day_key, label=day.title(), value=str(obj.get_value(day) or '')))
        total = sum(float(item['value'] or 0) for item in days)
        daily_totals = dict(getattr(self, '_daily_totals', None) or {day: float(obj.get_value(day) or 0) for day in DAYS})
        cell = dict(text='', widthHint=int(raw_width or 430), timeDays=days, total=total, dailyTotals=daily_totals)
        if monday:
            cell['week'] = str(monday)
        stype = str(obj.get_value('search_type', no_exception=True) or '')
        sid = obj.get_value('search_id', no_exception=True)
        if stype and stype.split('?')[0] == 'sthpw/task' and sid:
            task = getattr(self, '_tasks', {}).get(str(sid)) or Search.get_by_id(stype, sid)
            if task is not None:
                parent = task.get_parent()
                login = obj.get_value('login', no_exception=True)
                same_user = not login or login == Environment.get_user_name()
                cell.update(
                    targetSearchKey=parent.get_search_key() if parent else '',
                    taskKey=task.get_search_key(),
                    taskCode=task.get_code(),
                    process=task.get_value('process'),
                    actions=[dict(name='work-hours', label='Work Hours', icon='schedule')] if same_user else [],
                )
        return cell


class TimecardInfoTableElement(BaseTableElementWdg):
    def is_editable(self):
        return False

    def preprocess(self):
        self._tasks = {}
        ids = []
        for obj in self.sobjects or []:
            stype = str(obj.get_value('search_type', no_exception=True) or '').split('?')[0]
            sid = obj.get_value('search_id', no_exception=True)
            if stype == 'sthpw/task' and sid:
                ids.append(sid)
        if ids:
            self._tasks = {str(task.get_id()): task for task in Search.get_by_id('sthpw/task', list(dict.fromkeys(ids)))}

    def get_cell_value(self):
        obj = self.get_current_sobject()
        search_type = obj.get_value('search_type')
        if not search_type:
            return dict(text='', label='General')
        if search_type.split('?')[0] != 'sthpw/task':
            raise ValueError('The original timecard supports task associations only')
        sid = obj.get_value('search_id')
        task = getattr(self, '_tasks', {}).get(str(sid)) or Search.get_by_id(search_type, sid)
        if task is None:
            return dict(text='', label='Task is unavailable')
        parent = task.get_parent()
        return dict(text=' · '.join(str(value) for value in (
            parent.get_code() if parent else '', task.get_value('process'), task.get_value('description')) if value),
            targetSearchKey=task.get_search_key(),
            actions=[dict(name='sobject_detail', label='Open details', icon='search')])
