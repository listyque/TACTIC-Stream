"""Notification metadata, adapted from pyasm/biz/notification.py.

See LICENSE.TACTIC and compatibility/source_manifest.json.
"""
from pyasm.search.search import Search, SObject
from pyasm.security import LoginGroup, Login, LoginInGroup, Sudo

__all__ = ["Notification", "GroupNotification"]


class Notification(SObject):
    SEARCH_TYPE = 'sthpw/notification'

    def get_foreign_key(self):
        return 'notification_id'

    def get_defaults(self):
        return {'type': 'email'}

    def get_description(self):
        return self.get_value('description')


class GroupNotification(SObject):
    SEARCH_TYPE = "sthpw/group_notification"

    @staticmethod
    def get_groups_by_code(note_code):
        if not note_code:
            return []
        sudo = Sudo()
        try:
            group_search = Search(GroupNotification.SEARCH_TYPE)
            group_search.add_filter("notification_code", note_code)
            group_names = SObject.get_values(group_search.get_sobjects(), "login_group", unique=True)
            if not group_names:
                return []
            search = Search(LoginGroup.SEARCH_TYPE)
            search.add_filters("login_group", group_names)
            return search.get_sobjects()
        finally:
            sudo.exit()

    @staticmethod
    def get_logins_by_id(note_id):
        if not note_id and note_id != 0:
            return []
        sudo = Sudo()
        try:
            group_search = Search(GroupNotification.SEARCH_TYPE)
            if isinstance(note_id, list):
                if not note_id:
                    return []
                group_search.add_filters("notification_id", note_id)
            else:
                group_search.add_filter("notification_id", note_id)
            group_names = SObject.get_values(group_search.get_sobjects(), "login_group", unique=True)
            if not group_names:
                return []
            member_search = Search(LoginInGroup.SEARCH_TYPE)
            member_search.add_filters("login_group", group_names)
            login_names = SObject.get_values(member_search.get_sobjects(), "login", unique=True)
            if not login_names:
                return []
            search = Search(Login.SEARCH_TYPE)
            search.add_filters("login", login_names)
            return search.get_sobjects()
        finally:
            sudo.exit()
