"""Ordinary-user native writes on both kernels, always rolled back."""
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class ComparisonRollback(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__('project write comparison rollback')


def run(case):
    previous = Environment.get_security()
    security = Security()
    security._is_logged_in = 1
    Environment.set_security(security)
    try:
        security._login = Search.get_by_code('sthpw/login', 'project_writer')
        security.setup_access_manager()
        security.get_access_manager().add_xml_rules(case['rules'])
        command = Command()
        def execute():
            command.get_transaction().set_sync(False)
            try:
                operation = case['operation']
                if operation == 'insert':
                    obj = SearchType.create('contract/node')
                    obj.set_value('code', 'PROJECT_WRITTEN')
                    obj.set_value('name', "Writer's object · Тест")
                    obj.commit()
                    result = dict(allowed=True, code=obj.get_code(), name=obj.get_value('name'))
                else:
                    obj = Search.get_by_code('contract/node', 'D')
                    if operation == 'update':
                        obj.set_value('name', "Writer's change · Тест")
                        obj.commit()
                        result = dict(allowed=True, name=Search.get_by_code('contract/node', 'D').get_value('name'))
                    elif operation == 'delete':
                        obj.delete()
                        search = Search('contract/node')
                        search.add_filter('code', 'D')
                        result = dict(allowed=True, remaining=search.get_count())
                    else:
                        raise ValueError('Unknown write comparison operation')
            except Exception as error:
                result = dict(allowed=False, error=type(error).__name__)
            raise ComparisonRollback(result)
        command.execute = execute
        try:
            Command.execute_cmd(command)
        except ComparisonRollback as error:
            return error.result
        raise AssertionError('Write comparison must roll back')
    finally:
        Environment.set_security(previous)
