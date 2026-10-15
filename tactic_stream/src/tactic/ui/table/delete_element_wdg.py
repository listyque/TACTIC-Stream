"""DeleteElementWdg availability; deletion belongs to the native delete command."""
# Copyright (c) 2012 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
from tactic.ui.common import BaseTableElementWdg


class DeleteElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        return dict(text='', available=not self.get_current_sobject().is_insert())
