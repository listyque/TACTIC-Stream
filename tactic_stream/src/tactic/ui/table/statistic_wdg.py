###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Native completion values; the browser owns rendering and preferences."""
from pyasm.biz import Task, SimpleStatusAttr
from pyasm.search import Search, SearchKey
from tactic.ui.common import BaseTableElementWdg
from .task_element_wdg import TaskElementWdg
__all__ = ['TaskCompletionWdg', 'MilestoneCompletionWdg', 'TaskGroupCompletionWdg', 'TaskDaysDueElementWdg']

class TaskCompletionWdg(BaseTableElementWdg):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init()

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self.init()

    def set_options(self, options):
        super().set_options(options)
        self.kwargs.update(options)
        self.init()

    def set_option(self, key, value):
        self.set_options({key: value})

    def preprocess(self):
        self.data = {obj.get_search_key(): [] for obj in self.sobjects}
        self.pipelines = {}
        self.total_completion = 0.0
        self.num_sobjects = 0
        self.expression = self.kwargs.get('task_expr')
        if self.sobjects and not self.expression:
            # Native relationships determine grouping; empty parents stay cached.
            from pyasm.biz import Schema
            schema = Schema.get()
            for task in Task.get_by_sobjects(self.sobjects):
                search_type = task.get_value('search_type')
                attrs = schema.get_relationship_attrs('sthpw/task', search_type)
                attrs = schema.resolve_relationship_attrs(attrs, 'sthpw/task', search_type)
                identity = task.get_value(attrs['from_col'])
                key = SearchKey.build_search_key(search_type, identity, column=attrs['to_col'])
                self.data.setdefault(key, []).append(task)
        self.is_preprocessed = True

    def get_tasks(self, sobject):
        if not self.is_preprocessed:
            self.preprocess()
        if isinstance(sobject, Task):
            tasks = [sobject]
        elif self.expression:
            tasks = Search.eval(self.expression, sobjects=[sobject])
        else:
            key = sobject.get_search_key()
            if key not in self.data:
                self.data[key] = Task.get_by_sobjects([sobject])
            tasks = self.data[key]
        return [task for task in tasks if TaskElementWdg.can_view_process(task.get_value('process'))]

    def get_status_attr(self, task):
        attr = SimpleStatusAttr('status', task)
        attr.set_option('pipeline', 'task')
        code = task.get_value('pipeline_code', no_exception=True) or 'task'
        if code not in self.pipelines:
            attr.init()
            self.pipelines[code] = attr.get_pipeline()
        else:
            attr.pipeline = self.pipelines[code]
        return attr

    def get_cell_value(self):
        sobject = self.get_current_sobject()
        completion = None if sobject is None or sobject.is_insert() else self.get_completion(sobject)
        return dict(text='' if sobject is None or sobject.is_insert() else '%0.1f%%' % (completion or 0),
                    completion=completion, count=len(self.tasks) if completion is not None else 0)

    @classmethod
    def get_args_keys(cls):
        return cls.ARGS_KEYS

    def is_sortable(self):
        return False

    ARGS_KEYS = {

        "task_expr": {
            'description': "an expression that retrieves the tasks e.g. @SOBJECT(sthpw/task['context','anim'])",
            'type': 'TextAreaWdg',
            'order': 0,
            'category': 'Display'
        }
    }

    def init(self):
        self.is_preprocessed = False
        self.data = {}
        self.cal_sub_task = None
        self.cal_sub_task_value = False

        # this is meant for handle_td()
        self.row_completion = 0
        self.expression = None

    @classmethod
    def is_editable(cls):
        return False

    def get_width(self):
        '''not used I think'''
        width = self.kwargs.get("width")

        if not width:
            width = 400
        return int(width)

    def get_text_value(self):
        sobject = self.get_current_sobject()
        if sobject is None or sobject.is_insert():
            return ''

        if not self.is_preprocessed:
            self.preprocess()

        sobject = self.get_current_sobject()
        completion = self.get_completion(sobject)
        if not completion:
            completion = 0
        return "%0.1f%%" % completion

    def get_completion(self, sobject):
        self.tasks = self.get_tasks(sobject)
        
        percent = 0
        # count the tasks with invalid or obsolete status
        #invalid_count = 0
        for task in self.tasks:
            status_attr = self.get_status_attr(task)
            task_percent = status_attr.get_percent_completion()
            if task_percent < 0:
                task_percent = 0
                #invalid_count += 1
            percent += task_percent

        if self.tasks:
            # NOT sure if I should subtract total # of tasks by invalid
            # task, leave it for now
            percent = float(percent) / len(self.tasks)
        else:
            return None

        return percent


class MilestoneCompletionWdg(TaskCompletionWdg):
    def get_tasks(self, sobject):
        search = Search('sthpw/task')
        search.add_filter('milestone_code', sobject.get_code())
        return [task for task in search.get_sobjects()
                if TaskElementWdg.can_view_process(task.get_value('process'))]


class TaskGroupCompletionWdg(TaskCompletionWdg):
    def preprocess(self):
        import json
        source = self.get_option('options')
        self.group_list = json.loads(source) if source else [{'label': 'default', 'context': []}]
        if not isinstance(self.group_list, list) or any(
                not isinstance(group, dict) or not isinstance(group.get('context', []), list)
                for group in self.group_list):
            raise ValueError('Completion groups require a list of labels and context lists')
        super().preprocess()

    def get_cell_value(self):
        if not self.is_preprocessed:
            self.preprocess()
        tasks = self.get_tasks(self.get_current_sobject())
        groups = []
        for group in self.group_list:
            label = group.get('label')
            if not label:
                continue
            values = [self.get_completion(task) for task in tasks
                      if task.get_value('context') in group.get('context', [])]
            percent = sum(value or 0 for value in values) / len(values) if values else 0
            groups.append({'label': label, 'completion': percent, 'count': len(values),
                           'text': '%s: %s%%' % (label, percent)})
        return {'text': '\n'.join(group['text'] for group in groups), 'groups': groups}


class TaskDaysDueElementWdg(BaseTableElementWdg):
    """Original due-date thresholds; rendering uses semantic urgency roles."""

    def get_cell_value(self):
        import calendar
        from datetime import datetime
        from dateutil import parser

        obj = self.get_current_sobject()
        column = self.get_option('due_date_col') or 'bid_end_date'
        value = obj.get_value(column)
        if not value:
            return {'text': 'no date', 'label': 'No date', 'urgency': ''}
        due = parser.parse(value) if isinstance(value, str) else value
        local = datetime.fromtimestamp(calendar.timegm(due.timetuple()))
        local = local.replace(microsecond=due.microsecond)
        now = datetime.now()
        delta = local - now
        seconds = delta.days * 86400 + delta.seconds
        days = abs((local.date() - now.date()).days)
        mode = 'due'
        if seconds < 0:
            mode = 'done' if str(obj.get_value('status') or '').lower() in ('approved', 'complete', 'done') else 'critical'
        elif seconds > 7200 and local.date() == now.date():
            mode = 'today'
        elif 3600 < seconds <= 7200:
            mode = 'warning_1'
        elif 0 < seconds <= 3600:
            mode = 'warning_2'
        if mode == 'critical':
            label = 'Today' if days == 0 else '1 Day Overdue' if days == 1 else '{count} Days Overdue'
        elif mode == 'today':
            label = 'Today'
        elif mode == 'warning_1':
            label = '< 2 Hours'
        elif mode == 'warning_2':
            label = '< 1 Hour'
        elif mode == 'done':
            label = ''
        else:
            label = '1 Day' if days == 1 else '{count} Days'
        return {'text': label.replace('{count}', str(days)), 'label': label,
                'parameters': {'count': days}, 'urgency': mode}
