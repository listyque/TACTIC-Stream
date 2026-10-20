# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Original TaskStatusSelectWdg form status and access filtering; no HTML."""
from pyasm.biz import Pipeline
from pyasm.widget import SelectWdg
from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract
from tactic.ui.common import SimpleTableElementWdg


def task_status_pipeline(task):
    code = task.get_value('pipeline_code', no_exception=True)
    if task.get_base_search_type() == 'sthpw/snapshot':
        code = 'snapshot'
    if not code and not task.is_insert():
        parent = task.get_parent()
        parent_code = parent.get_value('pipeline_code', no_exception=True) if parent else ''
        parent_pipeline = Pipeline.get_by_code(parent_code) if parent_code else None
        if parent_pipeline:
            code = parent_pipeline.get_process_attrs(task.get_value('process')).get('task_pipeline')
    return Pipeline.get_by_code(code or 'task') or Pipeline.get_by_code('task')


class TaskStatusElementWdg(SimpleTableElementWdg):
    ARGS_KEYS = {'edit_scope': {}}

    def assert_editable(self):
        scope = self.get_option('edit_scope') or 'all'
        if scope not in ('all', 'assigned'):
            raise ValueError('Invalid task status edit scope')
        task = self.get_current_sobject()
        if scope == 'assigned' and not Environment.get_security().is_admin() and task.get_value('assigned') != Environment.get_user_name():
            from pyasm.common import SecurityException
            raise SecurityException('Only the assigned user can edit this status')

    def get_cell_value(self):
        from pyasm.biz import Task
        task = self.get_current_sobject()
        pipeline = task_status_pipeline(task)
        status = task.get_value(self.get_name() or 'status')
        process = pipeline.get_process(status) if pipeline else None
        color = (process.get_color() if process else '') or Task.get_default_color(status)
        return dict(text=status, statusColor=color or '', statusPipeline=pipeline.get_code() if pipeline else '',
                    editScope=self.get_option('edit_scope') or 'all')


class TaskStatusSelectWdg(SelectWdg):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.is_preprocess = False

    def preprocess(self):
        from tactic.ui.panel import EditWdg
        if not isinstance(self.get_parent_wdg(), EditWdg):
            raise UnsupportedContract('Task status choices require an EditWdg field context')
        self.task_mapping = {}
        task = self.get_current_sobject()
        pipeline = task_status_pipeline(task)
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
