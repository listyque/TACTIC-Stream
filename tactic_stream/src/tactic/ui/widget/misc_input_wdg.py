# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Original TaskStatusSelectWdg form status and access filtering; no HTML."""
from pyasm.biz import Pipeline
from pyasm.widget import SelectWdg
from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract


class TaskStatusSelectWdg(SelectWdg):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.is_preprocess = False

    def preprocess(self):
        from tactic.ui.panel import EditWdg
        if not isinstance(self.get_parent_wdg(), EditWdg):
            raise UnsupportedContract('Inline task status switching is not migrated')
        self.task_mapping = {}
        task = self.get_current_sobject()
        task_pipe_code = task.get_value('pipeline_code', no_exception=True) or 'task'
        pipeline = Pipeline.get_by_code(task_pipe_code)
        if not pipeline:
            pipeline = Pipeline.get_by_code('task')
        self.task_pipelines = [pipeline]
        self.is_preprocess = True

    def get_input(self):
        if not self.is_preprocess:
            self.preprocess()
        pipeline = self.task_pipelines[0]
        if not pipeline:
            raise ValueError('Default task pipeline not found')
        status_names = pipeline.get_process_names()
        security = Environment.get_security()
        cur_sobject = self.get_current_sobject()
        cur_value = cur_sobject.get_value('status') if cur_sobject else ''
        allowed_statuses = []
        for status in status_names:
            if cur_value == status or security.check_access('process_select', status, access='view', default='deny'):
                allowed_statuses.append(status)
                continue
            access_key = [dict(process='*', pipeline=pipeline.get_code()), dict(process='*', pipeline='*'),
                          dict(process=status, pipeline=pipeline.get_code())]
            if security.check_access('process', access_key, 'view', default='deny'):
                allowed_statuses.append(status)
        select = SelectWdg(self.get_input_name())
        select.add_empty_option('-- Select --')
        if cur_value in allowed_statuses:
            select.set_value(cur_value)
        select.set_option('values', allowed_statuses)
        return select
