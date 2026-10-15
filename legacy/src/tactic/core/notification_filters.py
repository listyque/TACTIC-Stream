"""Original hidden My Notifications filter, extracted without UI imports.

Source: NotificationLogFilterWdg.alter_search. The native screen MUST retain
this recipient AND project restriction, not just show notification_log.
"""
from pyasm.common import Environment
from pyasm.biz import Project
from pyasm.search import Search, SObject

class NotificationLogScope:
    def alter_search(self, search):

        # Do some built in search
        project_code = Project.get_project_code()
        user_name = Environment.get_user_name()

        # get all the notifications that were sent to you
        sub_search = Search("sthpw/notification_login")
        sub_search.add_filter("login", user_name)
        sub_search.add_filter("project_code", project_code)
        #search.add_filter("type", "to")

        notification_logins = sub_search.get_sobjects()
        notification_ids = SObject.get_values(notification_logins, "notification_log_id", unique=True)

        project_code = Project.get_project_code()
        search.add_filter("project_code", project_code)
        search.add_filters("id", notification_ids)

