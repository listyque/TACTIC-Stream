"""Hidden rows open an actual configured table, independently of the parent table."""
from tactic.ui.common import BaseTableElementWdg
from .nested_scope import nested_cell


class HiddenRowElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys((
        'dynamic_class', 'dynamic', 'search_type', 'view', 'expression',
        'icon', 'title_icon', 'icon_tip', 'label', 'mode', 'init_load_num',
        'show_search_limit', 'show_insert', 'show_row_select', 'show_select',
        'show_gear', 'show_search', 'show_shelf', 'related_types', 'include_mako', 'html',
    ), {})

    def is_editable(self):
        return False

    def get_cell_value(self):
        return nested_cell(self.get_current_sobject().get_search_key(), self.options, self.get_name())


class RowAddElementWdg(HiddenRowElementWdg):
    def get_cell_value(self):
        # The original RowAdd always overrides related_types with sthpw/task.
        options = dict(self.options, search_type='sthpw/task')
        return nested_cell(self.get_current_sobject().get_search_key(), options, self.get_name())
