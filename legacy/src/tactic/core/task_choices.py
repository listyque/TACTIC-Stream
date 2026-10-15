"""Metadata providers extracted from TACTIC task input widgets.

No HTML, DOM, SQL or new workflow semantics. Status permissions are the rules
of TaskStatusSelectWdg; recursive process/context choices are ProcessInputWdg.
"""

def allowed_task_statuses(security, pipeline, current=''):
    allowed = []
    for status in pipeline.get_process_names():
        if current == status or security.check_access('process_select', status, access='view', default='deny'):
            allowed.append(status)
            continue
        keys = [{'process': '*', 'pipeline': pipeline.get_code()},
                {'process': '*', 'pipeline': '*'},
                {'process': status, 'pipeline': pipeline.get_code()}]
        if security.check_access('process', keys, 'view', default='deny'):
            allowed.append(status)
    return allowed


def process_choices(pipeline, show_context=False):
    """Original manual/approval/node recursion, preserving nested process names."""
    result = []
    for process in pipeline.get_processes(recurse=True, type=['manual', 'approval', 'node']):
        if show_context:
            for context in pipeline.get_output_contexts(process.get_name()):
                if context not in result:
                    result.append(context)
        else:
            name = process.get_full_name() if process.is_from_sub_pipeline() else process.get_name()
            if name not in result:
                result.append(name)
    return result


class TaskChoiceContext:
    """Non-persistent view of a task for dependent option lists, never a Command.

    The original Task.get_pipeline executes against overridden get_value. No
    setters/commit are exposed and the real task is not changed for a preview.
    """
    def __init__(self, task, values):
        self.task = task
        self.values = dict(values)

    def get_value(self, name, *args, **kwargs):
        if name in self.values:
            return self.values[name]
        return self.task.get_value(name, *args, **kwargs)

    def get_parent(self):
        return self.task.get_parent()

    def get_pipeline(self):
        from pyasm.biz import Task
        return Task.get_pipeline(self)
