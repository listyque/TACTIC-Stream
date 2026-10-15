"""Notification metadata, adapted from pyasm/biz/notification.py.

See LICENSE.TACTIC and compatibility/source_manifest.json. Email is not ported.
"""
from pyasm.search.search import SObject


class Notification(SObject):
    SEARCH_TYPE = 'sthpw/notification'

    def get_foreign_key(self):
        return 'notification_id'

    def get_defaults(self):
        return {'type': 'email'}

    def get_description(self):
        return self.get_value('description')
