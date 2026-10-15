"""SObjectFilesElementWdg inspector target; file reads use the native inspector."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
from tactic.ui.common import BaseTableElementWdg


class SObjectFilesElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        return dict(text='', targetSearchKey=self.get_current_sobject().get_search_key(use_id=False))
