# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Original My TACTIC counters as typed data rather than legacy HTML."""

from datetime import datetime, timedelta, timezone

from pyasm.biz import Pipeline, Project
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.widget.table_element_wdg import BaseTableElementWdg


class MyTacticSummaryWdg(BaseTableElementWdg):
    def get_cell_value(self):
        user, project = Environment.get_user_name(), Project.get_project_code()
        now = datetime.now(timezone.utc)
        periods = [('1 hour', now - timedelta(hours=1)),
                   ('today', now.replace(hour=0, minute=0, second=0, microsecond=0)),
                   ('1 week', now - timedelta(days=7))]
        entries = []
        for search_type, title in [('sthpw/notification_login', 'Notifications received'),
                                   ('sthpw/snapshot', 'Checkins'),
                                   ('sthpw/status_log', 'Status Changes')]:
            for period, since in periods:
                search = Search(search_type)
                search.add_filter('login', user)
                if search_type == 'sthpw/snapshot':
                    search.add_regex_filter('search_type', 'project=' + project, op='EQ')
                else:
                    search.add_filter('project_code', project)
                search.add_filter('timestamp', since.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S.%f'), op='>=')
                entries.append(dict(title=title, period=period, value=str(search.get_count()), translateTitle=True))
        pipeline = Pipeline.get_by_code('task')
        for status in pipeline.get_process_names() if pipeline else []:
            search = Search('sthpw/task')
            search.add_filter('assigned', user)
            search.add_filter('status', status)
            count = search.get_count()
            if count:
                entries.append(dict(title=status, value=str(count)))
        return dict(text='\n'.join(f"{entry['title']}: {entry['value']}" for entry in entries), entries=entries)
