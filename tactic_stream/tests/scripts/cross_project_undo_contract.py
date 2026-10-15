"""Unchanged source/native Workflow journal across two project databases."""
from pyasm.command import Command, UndoCmd, RedoCmd
from pyasm.command.workflow import BaseProcessTrigger
from pyasm.common import Environment
from pyasm.search import Search, SObject
from pyasm.security import Security


def run(case):
    previous = Environment.get_security()
    security = Security(); security._is_logged_in = 1
    Environment.set_security(security)
    try:
        security._login = Search.get_by_code('sthpw/login', 'project_writer')
        security.setup_access_manager(); security.get_access_manager().add_xml_rules(case['rules'])
        projects = ('one',) if case.get('adoption') else ('one', 'two')
        parents = [Search.get_by_search_key('contract/entity?project=' + project + '&code=A') for project in projects]
        command = Command(log_exception=False)
        command.get_transaction().set_sync(False)
        def transition():
            handler = BaseProcessTrigger(); handler.input = {}
            for parent in parents:
                handler.log_message(parent, 'work', 'pending')
        command.execute = transition; Command.execute_cmd(command)
        query = Search('sthpw/transaction_log'); query.add_filter('login', 'project_writer'); query.add_order_by('id desc'); query.set_limit(1)
        log = query.get_sobject()
        def state():
            for kind in ('config/process_state', 'sthpw/message'):
                SObject.get_cache_dict(search_type=kind).clear()
            result = {}
            for project in projects:
                query = Search('config/process_state?project=' + project); query.add_order_by('code')
                result[project] = []
                for row in query.get_sobjects():
                    data = dict(parent=row.get_value('search_type'), status=row.get_value('status'))
                    if case.get('adoption'):
                        data.update(pipeline=row.get_value('pipeline_code') or '', state=row.get_value('state'), id=row.get_id())
                    result[project].append(data)
            query = Search('sthpw/message'); query.add_order_by('code')
            result['messages'] = [row.get_value('message') for row in query.get_sobjects()]
            return result
        after = state()
        undo = UndoCmd(transaction_log=log)
        undo.get_transaction().set_sync(False); undo.get_transaction().set_record(False); Command.execute_cmd(undo)
        undone = state()
        redo = RedoCmd(transaction_log=log)
        redo.get_transaction().set_sync(False); redo.get_transaction().set_record(False); Command.execute_cmd(redo)
        return dict(after=after, undone=undone, redone=state())
    finally:
        Environment.set_security(previous)
