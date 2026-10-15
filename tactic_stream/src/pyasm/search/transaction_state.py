###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ["TransactionState"]

import re

from pyasm.common import Xml
from .search import SObject, Search, SObjectFactory


class TransactionState(SObject):

    SEARCH_TYPE = "sthpw/transaction_state"

    @staticmethod
    def get_by_ticket(ticket):
        from pyasm.security.security import _require_admin
        _require_admin()
        search = Search(TransactionState)
        search.add_filter("ticket", ticket)
        state = search.get_sobject()

        return state


    @staticmethod
    def create(ticket):
        from pyasm.security.security import _require_admin
        _require_admin()
        state = SObjectFactory.create(TransactionState.SEARCH_TYPE)
        state.set_value("ticket", ticket)
        data = Xml()
        data.create_doc("state")
        state.set_value("data", data.to_string() )
        state.commit()
        return state


    def reset_state(self):
        data = Xml()
        data.create_doc("state")
        self.set_value("data", data.to_string() )


    def set_state(self, name, value):
        from pyasm.security.security import _require_admin
        _require_admin()
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][\w.-]*', name):
            raise ValueError('State names must be XML element names')
        data = Xml(self.get_value('data'))
        if data.get_root_node().tag != 'state':
            raise ValueError('Expected state XML root')
        node = data.get_node('state/%s' % name)
        if node is None:
            data.create_text_element(name, str(value), data.get_root_node())
        else:
            # Original creates another node and keeps returning the first value.
            Xml.set_node_value(node, str(value))
        self.set_value('data', data.to_string())
        return True


    def get_state(self, name):
        '''get a state value'''
        from pyasm.security.security import _require_admin
        _require_admin()
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][\w.-]*', name):
            raise ValueError('State names must be XML element names')
        data = Xml(self.get_value('data'))
        value = data.get_value("state/%s" % name)
        return value





    def restore_state(self):
        '''
        <state>
        <project>bar</project>
        </state>
        '''

        from pyasm.security.security import _require_admin
        _require_admin()
        data = Xml(self.get_value("data"))

        # restore project
        project_code = data.get_value("state/project")

        # if it doesn't exist, maybe it was set through some other means
        if not project_code:
            from pyasm.biz import Project
            project_code = Project.get_project_code()

        if not project_code:
            raise Exception("No project state defined")

        from pyasm.biz import Project
        Project.set_project(project_code)
        
        return True


