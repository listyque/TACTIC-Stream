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
__all__ = ['TaskCompletionWdg']

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
