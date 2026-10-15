"""Same native task/history calls on the original and migrated runtimes."""
from pyasm.biz import Task
from pyasm.command import Command, Trigger
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class ComparisonRollback(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__('status contract rollback')


def run(case):
    previous = Environment.get_security()
    security = Security(); security._is_logged_in = 1
    Environment.set_security(security)
    result = None
    try:
        security._login = Search.get_by_code('sthpw/login', 'project_writer')
        security.setup_access_manager()
        security.get_access_manager().add_xml_rules(case['rules'])
        event = 'change|sthpw/task|status'
        klass = 'tactic.core.bootstrap.StatusLogTrigger'
        if not any(obj.get_value('class_name') == klass for obj in Trigger.get_static_triggers_by_event(event)):
            trigger = SearchType.create('sthpw/trigger')
            trigger.set_value('event', event, temp=True)
            trigger.set_value('class_name', klass, temp=True)
            trigger.set_value('mode', 'same process,same transaction', temp=True)
            Trigger.append_static_trigger(trigger)
        command = Command(log_exception=False)
        code = None
        def execute():
            nonlocal code
            command.get_transaction().set_sync(False)
            parent = Search.get_by_search_key('contract/entity?project=%s&code=A' % case['parent_project'])
            task = Task.create(parent, 'publish', status='Ready', triggers='none')
            code = task.get_code()
            task.set_value('status', 'Working'); task.commit()
            task.set_value('status', 'Working'); task.commit()
            search = Search('sthpw/status_log'); search.add_filter('search_code', code); search.add_order_by('id')
            rows = [dict(login=obj.get_value('login'), project=obj.get_value('project_code'),
                         previous=obj.get_value('from_status'), status=obj.get_value('to_status'),
                         linked=obj.get_value('search_id') == task.get_id(), code=bool(obj.get_code()))
                    for obj in search.get_sobjects()]
            raise ComparisonRollback(dict(status=task.get_value('status'), project=task.get_value('project_code'), logs=rows))
        command.execute = execute
        try:
            Command.execute_cmd(command)
        except ComparisonRollback as error:
            result = error.result
        search = Search('sthpw/task'); search.add_filter('code', code)
        result['remaining_tasks'] = search.get_count()
        search = Search('sthpw/status_log'); search.add_filter('search_code', code)
        result['remaining_logs'] = search.get_count()
        return result
    finally:
        Environment.set_security(previous)
