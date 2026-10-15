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
"""Original API messaging SObject path, shared by Workflow and RPC."""
from pyasm.common import Environment, Container, jsondumps
from pyasm.biz import Project
from pyasm.search import Search, SearchType


def get_message(key):
    message = Search.get_by_code('sthpw/message', key)
    return message.get_sobject_dict() if message else {}


def log_message(key, message=None, status=None, category="default", log_history=True):
    if isinstance(message, dict):
        message = jsondumps(message)
    source = Container.get('Workflow:message_source')
    parent = source[0] if source and source[1] == key else None
    project_code = parent.get_project_code() if parent is not None else Project.get_project_code()

    # Literal key: message keys are data, not an expression program.
    message_search = Search("sthpw/message")
    message_search.add_filter("code", key)
    message_obj = message_search.get_sobject()
    if not message_obj:
        message_obj = SearchType.create("sthpw/message")
        message_obj.set_value("code", key)
        message_obj.set_value("project_code", project_code)

    message_obj.set_value("category", category)
    if message != None:
        message_obj.set_value("message", message)
    if status != None:
        message_obj.set_value("status", status)

    login = Environment.get_user_name()
    message_obj.set_value("login", login)
    message_obj.set_value("timestamp", "NOW")
    if parent is not None:
        from pyasm.command.workflow import _commit_effect
        _commit_effect(message_obj, parent)
    else:
        message_obj.commit()

    # repeat with update the message log
    if log_history:
        message_log_obj = SearchType.create("sthpw/message_log")
        message_log_obj.set_value("message_code", key)
        if message != None:
            message_log_obj.set_value("message", message)
        if status != None:
            message_log_obj.set_value("status", status)

        message_log_obj.set_value("login", login)
        message_log_obj.set_value("project_code", project_code)
        message_log_obj.set_value("timestamp", "NOW")
        message_log_obj.set_value("category", category)
        if parent is not None:
            _commit_effect(message_log_obj, parent)
        else:
            message_log_obj.commit()


    return "OK"
