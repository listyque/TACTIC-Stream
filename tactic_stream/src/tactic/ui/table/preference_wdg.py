"""Descriptions and help hints from the original server preference table."""
from tactic.ui.common import BaseTableElementWdg


class PreferenceDescriptionWdg(BaseTableElementWdg):
    def get_cell_value(self):
        obj = self.get_current_sobject()
        hints = {
            'Debug': 'If set to [true], you can view the Debug Widget at the bottom left corner of your page.',
            'Filter': 'If set to [multi], It generally applies to filters in the filter box for Artist Tab.',
            'Quick Text': 'A list of | separated phrases a user can pick from to enter into the note area of Note Sheet.'
        }
        return {'text': obj.get_description(), 'tooltip': hints.get(obj.get_value('title'), '')}
