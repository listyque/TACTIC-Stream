"""SObjectDetailElementWdg target contract used by Handler's table inspector."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
from tactic.ui.common import BaseTableElementWdg


class SObjectDetailElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('use_parent', 'tab_element_names', 'show_task_process', 'show_default_elements'), {})

    def get_width(self):
        return 50

    def is_editable(self):
        return False

    def get_cell_value(self):
        target = self.get_current_sobject()
        if self.get_option('use_parent') in (True, 'true'):
            target = target.get_parent() or target
        return dict(text='', targetSearchKey=target.get_search_key(use_id=False))
