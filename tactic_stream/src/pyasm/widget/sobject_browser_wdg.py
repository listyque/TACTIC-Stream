"""Original connection directions and target rows without the legacy HTML shell."""
# Copyright (c) 2005-2008 Southpaw Technology. MIT; see LICENSE.TACTIC.
from pyasm.widget.table_element_wdg import BaseTableElementWdg
from tactic.ui.table.connections import read_connection_cells


class SObjectConnectionElement(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('direction', 'icon_size'), {})

    def is_editable(self):
        return False

    def preprocess(self):
        self.values = read_connection_cells(
            [obj.get_search_key() for obj in self.sobjects if not obj.is_insert()],
            self.get_option('direction') or 'dst', int(self.get_option('icon_size') or 60))

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if obj is None or obj.is_insert():
            return dict(text='', connectionRows=[])
        if not hasattr(self, 'values'):
            self.preprocess()
        return self.values[obj.get_search_key()]
