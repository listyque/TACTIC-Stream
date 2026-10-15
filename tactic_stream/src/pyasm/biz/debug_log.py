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

__all__ = ['DebugLog']

from pyasm.common import Environment
from pyasm.search import SObject
from pyasm.search.exception_log import _write_log

class DebugLog(SObject):
    '''Class that controls the logging of all debug logs during the Tactic
    runtime'''

    SEARCH_TYPE = "sthpw/debug_log"

    critical = 50
    error = 40
    warning = 30
    info = 20
    debug = 10


    def debug(cls, message, category="default"):
        return cls.log("debug", message, category)
    debug = classmethod(debug)



    def log(cls, level, message, category="default"):
        if level not in ("critical", "error", "warning", "info", "debug"):
            raise ValueError("Invalid debug log level: %s" % level)

        # record the exception
        user_name = Environment.get_user_name()
        if not user_name:
            user_name = "UNKNOWN"

        debug_log = _write_log('sthpw/debug_log', {
            'login': user_name, 'level': level, 'category': category, 'message': message,
        })

        return debug_log

    log = classmethod(log)





