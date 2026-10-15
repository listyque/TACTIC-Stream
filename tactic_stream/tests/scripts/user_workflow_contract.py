"""Identical ordinary-user task transitions in both native runtimes."""
from pyasm.biz import Pipeline, Task
from pyasm.command import Command, Workflow
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security


class ComparisonRollback(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__('Workflow comparison rollback')


def run(case):
    previous = Environment.get_security()
    security = Security(); security._is_logged_in = 1
    Environment.set_security(security)
    try:
        security._login = Search.get_by_code('sthpw/login', 'project_writer')
        security.setup_access_manager()
        security.get_access_manager().add_xml_rules(case['rules'])
        Workflow().init(quiet=True)
        command = Command(log_exception=False)
        def execute():
            command.get_transaction().set_sync(False)
            parent = Search.get_by_search_key('contract/entity?project=one&code=' + case.get('parent_code', 'A'))
            task = Task.create(parent, 'work', status='Pending', triggers='none')
            for status in ('In Progress', 'Complete'):
                task.set_value('status', status); task.commit()
            search = Search('config/process_state'); search.add_sobject_filter(parent); search.add_order_by('process')
            states = [dict(process=row.get_value('process'), status=row.get_value('status'),
                           pipeline=row.get_value('pipeline_code'), code=bool(row.get_code())) for row in search.get_sobjects()
                      if row.get_value('process') != '__PIPELINE__']
            search = Search('sthpw/message_log'); search.add_filter('project_code', 'one'); search.add_order_by('id')
            messages = [dict(key=row.get_value('message_code'), message=row.get_value('message'),
                             login=row.get_value('login'), project=row.get_value('project_code')) for row in search.get_sobjects()]
            raise ComparisonRollback(dict(states=states, messages=messages, status=task.get_value('status'),
                                          parent_name=Search.get_by_search_key(parent.get_search_key()).get_value('name')))
        command.execute = execute
        try:
            Command.execute_cmd(command)
        except ComparisonRollback as error:
            result = error.result
        search = Search('config/process_state'); search.add_filter('pipeline_code', case.get('pipeline_code', 'USER_WORKFLOW'))
        result['remaining_states'] = search.get_count()
        return result
    finally:
        Environment.set_security(previous)
