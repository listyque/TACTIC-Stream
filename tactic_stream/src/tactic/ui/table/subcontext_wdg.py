"""Native data from the original task subcontext table element."""
from tactic.ui.common import BaseTableElementWdg
from tactic.ui.common import SimpleTableElementWdg


class SubContextElementWdg(BaseTableElementWdg):
    def _get_subcontext(self):
        context = self.get_current_sobject().get_value('context')
        return context.split('/', 1)[1] if context and '/' in context else ''

    def get_cell_value(self):
        return {'text': self._get_subcontext()}


class ProcessElementWdg(SimpleTableElementWdg):
    def get_cell_value(self):
        task = self.get_current_sobject()
        parent = task.get_parent() if not task.is_insert() else None
        return dict(text=task.get_value('process'),
                    parentPipeline=parent.get_value('pipeline_code', no_exception=True) if parent else '')
