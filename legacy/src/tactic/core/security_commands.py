###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#


"""Group membership command extracted from the original admin widget module."""
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.web import WebContainer

class UserAssignCbk(Command):

    def execute(self):

        web = WebContainer.get_web()
        values = self.kwargs.get("values")
        login_names = values.get("login_name")

        search_key = values.get("search_key")[0]
        group = Search.get_by_search_key(search_key)

        # find all the groups that this user current is in
        search = Search("sthpw/login_in_group")
        search.add_filter("login_group", group.get_value("login_group"))
        login_in_groups = search.get_sobjects()
        current_logins = set()

        for x in login_in_groups:
            if x.get_value("login") not in login_names:
                x.delete()
            else:
                current_logins.add( x.get_value("login") )

        for login_name in login_names:
            if not login_name:
                continue

            # don't add again
            if login_name in current_logins:
                continue

            sobject = SearchType.create("sthpw/login_in_group")
            sobject.set_value("login", login_name )
            sobject.set_value("login_group", group.get_value("login_group"))
            sobject.commit()

