"""Unchanged Workflow state calls in the real original kernel and Stream."""
from pyasm.biz import Project, Task
from pyasm.command import Command, Trigger
from pyasm.command.workflow import BaseWorkflowNodeHandler
from pyasm.common import Container, Environment
from pyasm.search import Search, SearchType, DbContainer
from pyasm.security import Security


GRAPH = '''<pipeline><process name="design"/><process name="build"/>
<process name="review"/><process name="automatic" type="auto"/>
<connect from="design" to="review"/><connect from="build" to="review"/></pipeline>'''


class StateCommand(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Project.get()
        pipeline = SearchType.create('sthpw/pipeline')
        pipeline.set_value('code', 'STATE')
        pipeline.set_pipeline(GRAPH)
        data = {'sobject': parent, 'pipeline': pipeline, 'process': 'review',
                'data': {'name': "Данные O'Reilly", 'number': 7},
                'packages': {'default': {'ready': True}}}
        handler = BaseWorkflowNodeHandler(input=data)
        if self.case.get('internal_failure'):
            from unittest.mock import patch
            Task.create(parent, 'design', triggers='none')
            with patch.object(Task, 'commit', side_effect=ValueError('failed task commit')):
                try:
                    handler.set_all_tasks(parent, 'design', 'in_progress')
                except ValueError:
                    pass
            return {'internal': Container.get('TaskStatusChangeTrigger::internal')}
        empty = handler.retrieve_state()
        handler.store_state()
        handler.data = {}
        handler.packages = {}
        restored = handler.restore_state()
        try:
            state = handler.get_state()
        except Exception as exc:
            state = {'error': type(exc).__name__}
        checks = [handler.check_inputs()]
        handler.log_message(parent, 'design', 'pending')
        checks.append(handler.check_inputs())
        handler.log_message(parent, 'design', 'complete')
        handler.log_message(parent, 'build', 'not_required')
        checks.append(handler.check_inputs())
        process_state = handler.get_process_state(parent, 'design')
        cached = handler.get_process_state(parent, 'design') is process_state
        message_key = '%s|design|status' % parent.get_search_key()
        message = Search.get_by_code('sthpw/message', message_key)
        try:
            roundtrip = Search.get_by_search_key(message.get_search_key()).get_code() == message_key
        except Exception as exc:
            roundtrip = {'error': type(exc).__name__}
        single = Search('config/process_state')
        single.add_sobject_filter(parent)
        multiple = Search('config/process_state')
        multiple.add_sobjects_filter([parent])
        handler.input['process'] = 'automatic'
        missing_manual = handler.is_complete(pipeline.get_process('review'))
        return {'empty': empty, 'restored': restored, 'state': state, 'checks': checks,
                'cached': cached, 'status': handler.get_process_status(parent, 'design'),
                'filters': [single.get_count(), multiple.get_count()], 'missing_manual': missing_manual,
                'roundtrip': roundtrip}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        sql = DbContainer.get('sthpw')
        for table in ('task', 'message', 'message_log', 'spt_process_state', 'status_log', 'transaction_log', 'sobject_log', 'change_timestamp'):
            sql.do_update('DELETE FROM "' + table + '"')
        SearchType.get('config/process_state')
        if not any(obj.get_value('class_name') == 'tactic.core.bootstrap.StatusLogTrigger' and
                   obj.get_value('event') == 'change|config/process_state|status'
                   for obj in Trigger.get_static_triggers()):
            trigger = SearchType.create('sthpw/trigger')
            trigger.set_value('event', 'change|config/process_state|status', temp=True)
            trigger.set_value('class_name', 'tactic.core.bootstrap.StatusLogTrigger', temp=True)
            trigger.set_value('mode', 'same process,same transaction', temp=True)
            Trigger.append_static_trigger(trigger)
        result = Command.execute_cmd(StateCommand(case))
        if case.get('internal_failure'):
            return result
        states = Search('config/process_state')
        states.add_order_by('process')
        result['process_states'] = [[obj.get_value(name) for name in ('process', 'status', 'search_type', 'search_code')]
                                    for obj in states.get_sobjects()]
        history = Search('sthpw/message_log')
        history.add_order_by('id')
        result['history'] = [[obj.get_value('message_code'), obj.get_json_value('message'), obj.get_value('login')]
                             for obj in history.get_sobjects()]
        statuses = Search('sthpw/status_log')
        statuses.add_order_by('id')
        result['status_log'] = [[obj.get_value('from_status'), obj.get_value('to_status')]
                                for obj in statuses.get_sobjects()]
        return result
    finally:
        Environment.set_security(previous)
