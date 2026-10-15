"""Native MetadataElementWdg edit contract; its legacy HTML popup is excluded."""
# Copyright (c) 2005-2008 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology,
# and is not to be reproduced, transmitted, or disclosed without written permission.
from tactic.ui.common import SimpleTableElementWdg


class MetadataElementWdg(SimpleTableElementWdg):
    ARGS_KEYS = {'context': 'The context of the snapshot to get the file path from'}

    def is_editable(self):
        return False

    def get_required_columns(self):
        return []

    def get_cell_value(self):
        return dict(text='', targetSearchKey=self.get_current_sobject().get_search_key(use_id=False))
