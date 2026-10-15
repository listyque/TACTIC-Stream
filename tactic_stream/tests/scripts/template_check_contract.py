"""Unchanged template validation calls in original TACTIC and native vendors."""
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command import ProjectTemplateCheckCmd


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Command()
        def execute():
            command.get_transaction().set_sync(False)
            code = 'contract_' + case.get('name', 'template')
            project = SearchType.create('sthpw/project')
            project.set_value('code', code)
            project.set_value('type', 'other' if case.get('bug') == 'type' else code)
            project.commit(triggers=False)
            definition = SearchType.create('sthpw/search_object')
            definition.set_value('search_type', ('wrong' if case.get('bug') == 'namespace' else code) + '/entity')
            definition.set_value('namespace', code)
            definition.set_value('database', '{project}')
            definition.set_value('table_name', 'entity')
            definition.set_value('class_name', 'pyasm.search.SObject')
            definition.commit(triggers=False)
            checker = ProjectTemplateCheckCmd(project_code=code,
                prefix='incorrect' if case.get('bug') == 'prefix' else 'contract')
            try:
                if case.get('bug') == 'namespace':
                    checker.project_type, checker.prefix = code, 'contract'
                    checker.check_search_type()
                else:
                    checker.execute()
            except Exception as error:
                return {'error': type(error).__name__}
            return {'error': None}
        command.execute = execute
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
