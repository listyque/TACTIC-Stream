# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Parallel task bars retain original percentages and pipeline process order."""
from pyasm.biz import Pipeline
from tactic.ui.table.statistic_wdg import TaskCompletionWdg
from tactic.ui.common import BaseTableElementWdg
from datetime import datetime, timezone
from dateutil import parser


class ParallelStatusWdg(TaskCompletionWdg):
    ARGS_KEYS = dict.fromkeys(('bar_height', 'label_format', 'report'), {})

    def is_editable(self):
        return False

    def preprocess(self):
        super().preprocess()
        self.max_count = max([len(self.get_status_attr(task).get_pipeline().get_processes())
                              for tasks in self.data.values() for task in tasks] or [6])

    @staticmethod
    def _get_color_code(percent):
        if percent > 80:
            return '#b5e868'
        if percent > 50:
            return '#e8e268'
        if percent > 30:
            return '#e8c268'
        if percent > 10:
            return '#e86868'
        return '#ddd'

    def get_cell_value(self):
        parent = self.get_current_sobject()
        if parent is None or parent.is_insert():
            return dict(text='', groups=[], steps=1)
        pipeline = Pipeline.get_by_sobject(parent, allow_default=True)
        if pipeline is None:
            return dict(text='', groups=[], steps=1, diagnostic='Pipeline is not configured')
        label_format = self.get_option('label_format') or 'reg'
        if label_format not in ('reg', 'small', 'abbr', 'none'):
            raise ValueError('Invalid parallel status label format')
        bar_height = str(self.get_option('bar_height') or '1')
        if not bar_height.isdecimal() or not 1 <= int(bar_height) <= 32:
            raise ValueError('Parallel status bar height must be between 1 and 32 pixels')
        tasks = self.get_tasks(parent)
        attrs = {task.get_search_key(): self.get_status_attr(task) for task in tasks}
        steps = self.max_count
        def groups_for(current, ancestors):
            code = current.get_code()
            if code in ancestors or len(ancestors) >= 8:
                raise ValueError('Cyclic or excessively nested task pipeline')
            result = []
            for process in current.get_processes():
                selected = [task for task in tasks if task.get_value('process') in (process.get_name(), process.get_full_name())]
                bars = []
                for task in selected:
                    percent = attrs[task.get_search_key()].get_percent_completion()
                    end = task.get_value('bid_end_date')
                    end = parser.parse(str(end)) if end else None
                    if end is not None and end.tzinfo is None:
                        end = end.replace(tzinfo=timezone.utc)
                    overdue = bool(end and end < datetime.now(timezone.utc) and percent != 100)
                    bars.append(dict(search_key=task.get_search_key(), taskCode=task.get_code(), process=task.get_value('process'), percent=percent,
                        color='#f00' if overdue else self._get_color_code(percent), status=task.get_value('status'),
                        assigned=task.get_value('assigned'), description=task.get_value('description'),
                        bidStart=task.get_value('bid_start_date'), bidEnd=task.get_value('bid_end_date')))
                child = process.get_child_pipeline()
                result.append(dict(process=process.get_full_name(), label='' if label_format == 'none' else process.get_name()[:3] if label_format == 'abbr' else process.get_name(),
                    count=len(bars), completion=sum(max(0, bar['percent']) for bar in bars)/len(bars) if bars else 0,
                    bars=bars, children=groups_for(child, (*ancestors, code)) if child else []))
            return result
        return dict(text='', groups=groups_for(pipeline, ()), labelFormat=label_format,
                    barHeight=int(bar_height), steps=max(1, steps), report=self.get_option('report') != 'false',
                    targetSearchKey=parent.get_search_key())


class ParallelStatusEditWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        parent = self.get_current_sobject()
        return dict(text='', targetSearchKey=parent.get_search_key(), actions=[
            dict(name='add-task', label='Add Task', icon='add')])
