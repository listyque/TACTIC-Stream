"""Configured daily hours use WorkHour semantics and the existing timesheet owner."""
import datetime
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.search import Search
from tactic.ui.common import BaseTableElementWdg


class WorkHoursElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('show_all_users','show_overtime','use_straight_time','unit',
        'day_width','width','days_per_page'), {})

    def is_editable(self):
        return False

    def preprocess(self):
        self._entries = []
        self._start = datetime.date.today()
        self._start -= datetime.timedelta(days=self._start.weekday())
        count = int(self.get_option('days_per_page') or 7)
        if not 1 <= count <= 31 or self.get_option('unit') not in ('', 'hour', 'minute'):
            raise ValueError('Invalid work-hours display range or unit')
        for flag in ('show_all_users', 'show_overtime', 'use_straight_time'):
            if self.get_option(flag) not in ('', True, False, 'true', 'false'):
                raise ValueError('Invalid work-hours display option')
        search = Search('sthpw/work_hour')
        search.add_filter('project_code', Project.get_project_code())
        search.add_filters('task_code', [obj.get_code() for obj in self.sobjects] or [''])
        search.add_filter('day', str(self._start), op='>=')
        search.add_filter('day', str(self._start + datetime.timedelta(days=count)), op='<')
        if self.get_option('show_all_users') not in (True, 'true'):
            search.add_filter('login', Environment.get_user_name())
        self._entries = search.get_sobjects()

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if obj.get_base_search_type() != 'sthpw/task':
            raise ValueError('Work Hours requires a task row')
        count = int(self.get_option('days_per_page') or 7)
        if not 1 <= count <= 31 or self.get_option('unit') not in ('', 'hour', 'minute'):
            raise ValueError('Invalid work-hours display range or unit')
        start = self._start
        all_users = self.get_option('show_all_users') in (True, 'true')
        entries = [entry for entry in self._entries if entry.get_value('task_code') == obj.get_code()]
        factor = 60 if self.get_option('unit') == 'minute' else 1
        days = []
        for index in range(count):
            day = start + datetime.timedelta(days=index)
            matched = [entry for entry in entries if str(entry.get_value('day'))[:10] == str(day)]
            regular = sum((entry.get_regular_hours() for entry in matched), 0) * factor
            overtime = sum((entry.get_overtime_hours() for entry in matched), 0) * factor
            clock = self.get_option('use_straight_time') in (False, 'false')
            days.append(dict(day=str(day), label=day.strftime('%a'), value=str(regular),
                start=' / '.join(str(entry.get_value('start_time') or '') for entry in matched) if clock else '',
                end=' / '.join(str(entry.get_value('end_time') or '') for entry in matched) if clock else '',
                overtime=str(overtime) if self.get_option('show_overtime') in (True, 'true') else ''))
        parent = obj.get_parent()
        return dict(text='', widthHint=int(self.get_option('width') or 380), timeDays=days, total=sum(float(day['value']) for day in days),
            targetSearchKey=parent.get_search_key() if parent else '', taskKey=obj.get_search_key(),
            taskCode=obj.get_code(), process=obj.get_value('process'), week=str(start), allUsers=all_users,
            unit=self.get_option('unit') or 'hour', dayWidth=int(self.get_option('day_width') or 35),
            actions=[] if all_users else [dict(name='work-hours', label='Work Hours', icon='schedule')])
