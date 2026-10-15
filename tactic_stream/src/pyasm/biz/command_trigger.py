"""Trigger definitions, adapted from pyasm/biz/command_trigger.py.

See LICENSE.TACTIC and compatibility/source_manifest.json.
"""
from pyasm.search.search import SObject


class TriggerSObj(SObject):
    SEARCH_TYPE = 'sthpw/trigger'

    @staticmethod
    def get_search_columns():
        return ['event', 'class_name']

    @staticmethod
    def get_required_columns():
        return ['event', 'class_name']

    def get_primary_key(self):
        return 'class_name'

    def get_description(self):
        return self.get_primary_key_value()


class Trigger(TriggerSObj):
    # Original deprecated pyasm.biz.Trigger, distinct from pyasm.command.Trigger.
    pass
