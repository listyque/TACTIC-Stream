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

__all__ = ['ExceptionLog']

from pyasm.common import Environment, Config, Container
from pyasm.common.errors import SecurityException, UnsupportedContract
from .search import SObject, SObjectFactory, RequestContext, request_context, _context
from .transaction import Transaction

import sys,traceback

class ExceptionLog(SObject):
    '''Class that controls the logging of all of the exceptions that occur
    during the Tactic runtime'''


    def log(exception, message=None):
        
        tb = sys.exc_info()[2]
        stacktrace_str = ExceptionLog.get_stack_trace(exception)

        # replace crazy windows paths with normal paths
        stacktrace_str = stacktrace_str.replace("\\", "/")

        # record the exception
        security = Environment.get_security()
        user_name = security.get_user_name() if security else None
        if not user_name:
            user_name = "UNKNOWN"

        if not message:
            message = str(exception)

        class_name = exception.__class__.__name__

        if Config.get_value("services", "notify_user"):
            raise UnsupportedContract('Exception email notification is not migrated')
        exception_log = _write_log('sthpw/exception_log', {
            'login': user_name, 'class': class_name, 'message': message,
            'stack_trace': stacktrace_str,
        })
        del tb

        return exception_log

    log = staticmethod(log)


    def get_stack_trace(exception):
        if getattr(exception, 'tactic_script_sources', None):
            from tactic.command.python_cmd import format_script_traceback
            return format_script_traceback(exception).replace('\\', '/')
        tb = sys.exc_info()[2]
        stacktrace = traceback.format_tb(tb)
        stacktrace_str = "".join(stacktrace)

        # replace crazy windows paths with normal paths
        stacktrace_str = stacktrace_str.replace("\\", "/")
        return stacktrace_str
    get_stack_trace = staticmethod(get_stack_trace)




def _write_log(search_type, values):
    """Diagnostic rows commit on an owned connection without touching the caller."""
    if search_type not in ('sthpw/exception_log', 'sthpw/debug_log'):
        raise ValueError('Only diagnostic log types are accepted')
    context = _context.get(None)
    security = Environment.get_security()
    if (context is None or security is None or not security.is_logged_in() or
            security.get_user_name() != context.login or values.get('login') != context.login):
        raise SecurityException('Persistent diagnostics require the authenticated request identity')
    transaction = Transaction.get()
    if transaction and transaction.is_in_transaction():
        system = context.store.get_db_resource()._get_connection_key()
        if any(sql._has_writes and sql.get_db_resource()._get_connection_key() == system
               for sql in transaction.get_databases().values()):
            # ponytail: independent writes conflict with an active system writer;
            # add durable deferred logs when their immediate SObject contract is resolved.
            raise UnsupportedContract('Independent logging during a system-database write is not migrated')
    from pyasm.command import Command
    # A failed project installation can already have rolled its project back.
    # System diagnostics must not depend on that now unavailable project.
    with request_context(RequestContext(context.store, context.login, 'admin')):
        Environment.set_security(security)
        cmd = Command(log_exception=False)
        def execute():
            cmd.get_transaction().set_record(False)
            cmd.get_transaction().set_sync(False)
            obj = SObjectFactory.create(search_type)
            for key, value in values.items():
                obj.set_value(key, value)
            # Only this new diagnostic row receives internal write authority.
            Container.put('Diagnostics:writing', obj)
            try:
                obj.commit(triggers='none', log_transaction=False)
            finally:
                Container.put('Diagnostics:writing', None)
            return obj
        cmd.execute = execute
        return Command.execute_cmd(cmd)
