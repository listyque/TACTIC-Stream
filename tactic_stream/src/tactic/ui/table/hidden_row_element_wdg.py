"""Hidden rows open an actual configured table, independently of the parent table."""
from tactic.ui.common import BaseTableElementWdg
from .nested_scope import nested_cell


class HiddenRowElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys((
        'dynamic_class', 'dynamic', 'search_type', 'view', 'expression',
        'icon', 'title_icon', 'icon_tip', 'label', 'mode', 'init_load_num',
        'show_search_limit', 'show_insert', 'show_row_select', 'show_select',
        'show_gear', 'show_search', 'show_shelf', 'show_resize_scroll', 'related_types', 'include_mako', 'html',
    ), {})

    def is_editable(self):
        return False

    def get_cell_value(self):
        sobject = self.get_current_sobject()
        if not sobject or sobject.is_insert():
            return {'text': '', 'actions': []}
        return nested_cell(sobject.get_search_key(), dict(self.options), self.get_name())


class RowAddElementWdg(HiddenRowElementWdg):
    def get_cell_value(self):
        sobject = self.get_current_sobject()
        if not sobject or sobject.is_insert():
            return {'text': '', 'actions': []}
        options = dict(self.options)
        options.setdefault('search_type', options.get('related_types') or 'sthpw/task')
        return nested_cell(sobject.get_search_key(), options, self.get_name())
