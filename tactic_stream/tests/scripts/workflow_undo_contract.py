"""Unchanged original/native probe for message replay and GMT timestamps."""
from pyasm.biz import Task
from pyasm.command import Command, UndoCmd, RedoCmd, Workflow
from pyasm.common import Environment
from pyasm.search import Search, SObject
from pyasm.security import Security
import pyasm.common.spt_date as dates
from dateutil.tz import tzoffset


def run(case):
    previous = Environment.get_security()
    previous_timezone = dates.TZLOCAL
    dates.TZLOCAL = tzoffset('GMT+3', 10800)
    security = Security(); security._is_logged_in = 1
    Environment.set_security(security)
    try:
        security._login = Search.get_by_code('sthpw/login', 'project_writer')
        security.setup_access_manager(); security.get_access_manager().add_xml_rules(case['rules'])
        Workflow().init(quiet=True)
        def write(action, record=True):
            command = Command(log_exception=False)
            command.get_transaction().set_sync(False)
            command.get_transaction().set_record(record)
            def execute():
                return action()
            command.execute = execute
            return Command.execute_cmd(command)
        parent = Search.get_by_search_key('contract/entity?project=one&code=A')
        task = write(lambda: Task.create(parent, 'work', status='Pending', triggers='none'))
        def complete():
            query = Search('sthpw/task'); query.add_filter('code', task.get_code())
            current = query.get_sobject()
            current.set_value('status', 'Complete'); current.commit()
        write(complete)
        query = Search('sthpw/transaction_log'); query.add_filter('login', 'project_writer'); query.add_order_by('id desc'); query.set_limit(1)
        log = query.get_sobject()
        def state():
            # Match fresh client requests instead of the source's stale identity cache.
            SObject.get_cache_dict(search_type='sthpw/task').clear()
            SObject.get_cache_dict(search_type='sthpw/message').clear()
            query = Search('sthpw/task'); query.add_filter('code', task.get_code())
            current = query.get_sobject()
            messages = Search('sthpw/message'); messages.add_order_by('code')
            return dict(status=current.get_value('status'), date=str(current.get_value('bid_start_date')),
                        messages=[row.get_value('message') for row in messages.get_sobjects()])
        after = state()
        undo = UndoCmd(transaction_log=log)
        undo.get_transaction().set_sync(False); undo.get_transaction().set_record(False)
        Command.execute_cmd(undo)
        undone = state()
        redo = RedoCmd(transaction_log=log)
        redo.get_transaction().set_sync(False); redo.get_transaction().set_record(False)
        Command.execute_cmd(redo)
        redone = state()
        def date_only():
            query = Search('sthpw/task'); query.add_filter('code', task.get_code())
            current = query.get_sobject()
            current.set_value('bid_start_date', '2026-01-02 03:04:05'); current.commit(triggers='none')
        write(date_only)
        query = Search('sthpw/transaction_log'); query.add_filter('type', 'undo'); query.add_order_by('id desc'); query.set_limit(1)
        date_log = query.get_sobject()
        undo = UndoCmd(transaction_log=date_log)
        undo.get_transaction().set_sync(False); undo.get_transaction().set_record(False); Command.execute_cmd(undo)
        redo = RedoCmd(transaction_log=date_log)
        redo.get_transaction().set_sync(False); redo.get_transaction().set_record(False); Command.execute_cmd(redo)
        return dict(after=after, undone=undone, redone=redone, gmt_date=state()['date'])
    finally:
        dates.TZLOCAL = previous_timezone
        Environment.set_security(previous)
