# Copyright (c) 2005-2009, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native LinkElementWdg metadata; inherited text values retain SDK behavior."""
from pyasm.command import ColumnAddCmd
from tactic.ui.common import SimpleTableElementWdg


class LinkElementWdg(SimpleTableElementWdg):
    ARGS_KEYS = {'icon': 'Icon to display', 'empty': 'Text for an empty link'}

    def get_text_value(self):
        value = super().get_text_value()
        text = '' if value is None else str(value).strip()
        return text or self.get_option('empty') or ''

    def is_sortable(self):
        return False

    def is_editable(self):
        return 'optional'

    def create_required_columns(self, search_type):
        ColumnAddCmd(search_type, self.get_name(), 'varchar').execute()

