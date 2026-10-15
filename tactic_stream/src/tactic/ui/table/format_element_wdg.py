# Copyright (c) 2005-2009, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native FormatElementWdg value methods; browser presentation belongs to Vue."""
from pyasm.search import SObject
from tactic.core.format_value import FormatValueMixin
from tactic.ui.common import SimpleTableElementWdg


class FormatElementWdg(FormatValueMixin, SimpleTableElementWdg):
    ARGS_KEYS = {
        'type': {
            'description': 'Determines the type it should be displayed as',
            #'type': 'SelectWdg',
            'type': 'tactic.ui.manager.FormatDefinitionEditWdg',
            'values': 'integer|float|percent|currency|date|time|scientific|boolean|text|timecode',
            'category': 'Required',
            'default': 'text',
            'order': 1
        },
        'total_summary': {
            'description': 'Determines a calculation for the bottom row',
            'type': 'SelectWdg',
            'values': 'count|total|average',
            'category': 'Misc',
            'order': 2
        },
        'format': {
            'description': 'display format',
            'category': 'internal',
            'sub_keys': ['fps']
        },
    
        'constraint': {
            'description': 'Determines what kind of index is put onto the created column',
            'type': 'SelectWdg',
            'values': 'unique|indexed',
            'order': 3,
            'category': 'Misc',
        }
    
        }

    def get_width(self):
        widget_type = self.get_option('type')
        if widget_type == 'integer':
            return 30
        if widget_type in ('float', 'date', 'timecode', 'currency'):
            return 80
        return 100

    def get_text_value(self):
        value = self.get_value()
        widget_type = self.get_option('type')
        if widget_type in ('date', 'time') and value:
            if not SObject.is_day_column(self.get_name()):
                value = str(self.get_timezone_value(value))
        format = self.get_option('format')
        return str(value) if format == 'Checkbox' else self.get_format_value(value, format)

