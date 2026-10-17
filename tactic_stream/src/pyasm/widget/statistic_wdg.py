"""The older task completion cell rounds down, unlike the newer table widget."""

from pyasm.biz import Pipeline, Task
from tactic.ui.table.statistic_wdg import TaskCompletionWdg as ModernTaskCompletionWdg


class TaskCompletionWdg(ModernTaskCompletionWdg):
    def get_tasks(self, sobject):
        tasks = super().get_tasks(sobject)
        if isinstance(sobject, Task):
            return tasks
        pipeline = Pipeline.get_by_sobject(sobject)
        if pipeline:
            processes = pipeline.get_process_names(recurse=self.cal_sub_task_value)
            return [task for task in tasks if task.get_value("process") in processes]
        return tasks

    def get_completion(self, sobject):
        percent = super().get_completion(sobject)
        return None if percent is None else int(percent)

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if obj is None or obj.is_insert():
            return {"text": "", "completion": None, "count": 0}
        percent = self.get_completion(obj)
        return {
            "text": "%d%%" % (percent or 0),
            "completion": percent,
            "count": len(self.tasks),
        }
