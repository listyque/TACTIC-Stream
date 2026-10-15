# Copyright (c) 2005-2008 Southpaw Technology. See LICENSE.TACTIC.
"""Native JSON display from legacy tactic/ui/table/json_element_wdg.py."""
import json
from tactic.ui.common import SimpleTableElementWdg


class JsonElementWdg(SimpleTableElementWdg):
    ARGS_KEYS = {'height': {'description': 'Maximum cell height'}}

    def is_sortable(self):
        return False

    def get_cell_value(self):
        data = self.get_current_sobject().get_json_value(self.get_name())
        return {'text': json.dumps(data, indent=2, sort_keys=True) if data else '', 'language': 'json'}
