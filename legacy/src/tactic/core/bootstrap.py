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

"""Business bootstrap; does not import web widgets. Called once by WebInit."""
from pyasm.common import Common
from pyasm.command import Trigger
from pyasm.search import SearchType
from pyasm.biz import StatusLog

class StatusLogTrigger(Trigger):
    def execute(self):
        sobject = self.get_caller()
        prev_value = sobject.get_prev_value('status')

        value = sobject.get_value('status')
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
    def execute(self):
        # FIXME: should this really be a web_init trigger?  This needs
        # to be run even from batch commands
        event = "change|sthpw/task|status"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event)
        trigger.set_value("class_name", "tactic.core.bootstrap.StatusLogTrigger")
        trigger.set_value("mode", "same process,same transaction")
        Trigger.append_static_trigger(trigger, startup=True)


        event = "change|config/process_state|status"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event)
        trigger.set_value("class_name", "tactic.core.bootstrap.StatusLogTrigger")
        trigger.set_value("mode", "same process,same transaction")
        Trigger.append_static_trigger(trigger, startup=True)



        # FIXME: should this be here??
        from pyasm.command.workflow import Workflow
        Workflow().init(startup=True)




        event = "insert|sthpw/login"
        trigger = SearchType.create("sthpw/trigger")
        trigger.set_value("event", event)
        trigger.set_value("class_name", "tactic.core.bootstrap.DisplayNameTrigger")
        trigger.set_value("mode", "same process,same transaction")
        Trigger.append_static_trigger(trigger, startup=True)



        #from tactic.command.queue import JobTask
        #JobTask.start()

        from pyasm.biz import Snapshot
        Snapshot.add_integral_trigger()










