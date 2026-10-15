"""Run unchanged against the original and migrated TransactionState."""
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment, Xml
from pyasm.search import Search, TransactionState
from pyasm.security import Security


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Command()
        command.get_transaction().set_record(False)
        command.get_transaction().set_sync(False)
        def execute():
            state = TransactionState.create('state_contract')
            state.set_state('value', 'first & <value>')
            first = state.get_state('value')
            state.set_state('value', 'second & <value>')
            second = state.get_state('value')
            count = len(Xml(state.get_value('data')).get_nodes('state/value'))
            state.reset_state()
            state.set_state('project', 'one')
            restored = state.restore_state()
            state.commit()
            saved = TransactionState.get_by_ticket('state_contract')
            return [first, second, count, restored, Project.get_project_code(), saved.get_state('value')]
        command.execute = execute
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
