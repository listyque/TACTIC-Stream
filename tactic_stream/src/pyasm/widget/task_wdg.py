"""Legacy task columns using the existing task selector and editor owners.

Source: legacy/src/pyasm/widget/task_wdg.py. The old HTML calendar is not loaded.
"""

from pyasm.widget.table_element_wdg import SimpleTableElementWdg
from tactic.ui.table.task_element_wdg import TaskElementWdg


class SObjectTaskTableElement(TaskElementWdg):
    relationship_type = "hierarchy"
    ARGS_KEYS = dict(TaskElementWdg.ARGS_KEYS, bid_edit={}, simple_date={}, supe={},
                     width={}, process_filter={})

    def __init__(self, **kwargs):
        kwargs.setdefault('show_current_pipeline_only', 'false')
        super().__init__(**kwargs)

    def get_width(self):
        width = str(self.get_option('width') or '250').removesuffix('px')
        if not width.isdecimal() or not 48 <= int(width) <= 4096:
            raise ValueError('Task column width must be between 48 and 4096 pixels')
        return int(width)

    def get_tasks(self, sobject=None, pipeline_code=None):
        tasks = super().get_tasks(sobject, pipeline_code)
        selected = self.state.get(self.get_option('process_filter') or 'process_filter')
        if selected:
            selected = selected if isinstance(selected, list) else str(selected).split('|')
            tasks = [task for task in tasks if task.get_value('process') in selected]
        return tasks

    def get_cell_value(self):
        cell = super().get_cell_value()
        for record in cell['tasks']:
            record['editAssigned'] = str(self.get_option('supe')).lower() == 'true'
            record['editDates'] = str(self.get_option('bid_edit')).lower() == 'true'
            record['simpleDates'] = str(self.get_option('simple_date')).lower() == 'true'
        return cell


class TaskParentSpacingTableElement(SimpleTableElementWdg):
    def get_cell_value(self):
        task = self.get_current_sobject()
        context = str(task.get_value('context') or '')
        return dict(text=context.split('/', 1)[0], tooltip=context)

    def get_text_value(self):
        return self.get_cell_value()['text']
