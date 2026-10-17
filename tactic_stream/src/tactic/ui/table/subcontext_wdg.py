"""Native data from the original task subcontext table element."""
from tactic.ui.common import BaseTableElementWdg


class SubContextElementWdg(BaseTableElementWdg):
    def _get_subcontext(self):
        context = self.get_current_sobject().get_value('context')
        return context.split('/', 1)[1] if context and '/' in context else ''

    def get_cell_value(self):
        return {'text': self._get_subcontext()}
