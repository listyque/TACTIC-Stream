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
#

"""Business triggers registered once during each worker's startup."""
from pyasm.common import Common
from pyasm.command import Trigger
from pyasm.search import SearchType
from pyasm.biz import StatusLog


class StatusLogTrigger(Trigger):
    def execute(self):
        sobject = self.get_caller()
        changes = self.get_input() or {}
        prev_value = changes.get('prev_data', {}).get('status', sobject.get_prev_value('status'))

        value = changes.get('update_data', {}).get('status', sobject.get_value('status'))
        if not value:
            return
        # record the change if it is different
        if prev_value != value:
            # if this is successful, the store it in the status_log
            StatusLog.create(sobject, value, prev_value)

class DisplayNameTrigger(Trigger):

    def execute(self):
        sobject = self.get_caller()
        first = sobject.get_value('first_name')
        last = sobject.get_value('last_name')
        display = sobject.get_value('display_name')

        if not display:
            if first and last:
                sobject.set_value('display_name', '%s %s'%(first, last))
            elif first:
                sobject.set_value("display_name", first)
            elif last:
                sobject.set_value("display_name", last)
            else:
                sobject.set_value("display_name", sobject.get_value("code"))


        # The admin user may not be committed yet
        if sobject.get_value("code") == 'admin':
            return

        sobject.commit(triggers=False)

class CoreInit(Common):
    initialized = False

    def execute(self):
        if self.initialized:
            return
        for event in ("change|sthpw/task|status", "change|config/process_state|status", "insert|sthpw/login"):
            trigger = SearchType.create("sthpw/trigger")
            trigger.set_value("event", event, temp=True)
            name = "DisplayNameTrigger" if event == "insert|sthpw/login" else "StatusLogTrigger"
            trigger.set_value("class_name", "tactic.core.bootstrap." + name, temp=True)
            trigger.set_value("mode", "same process,same transaction", temp=True)
            Trigger.append_static_trigger(trigger, startup=True)
        from pyasm.command.workflow import Workflow
        Workflow().init(startup=True, quiet=True)
        from pyasm.biz import Snapshot
        Snapshot.add_integral_trigger()
        CoreInit.initialized = True
