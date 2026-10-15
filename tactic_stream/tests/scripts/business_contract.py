"""Unchanged server script run in TACTIC and Stream on disposable databases."""
from pyasm.biz import Task, Note, Project
from pyasm.command import Command, Trigger
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class BusinessCommand(Command):
    def __init__(self, operation, key=None, triggers=True):
        super().__init__()
        self.operation, self.key, self.triggers = operation, key, triggers

    def execute(self):
        self.get_transaction().set_sync(False)
        if self.operation == 'create':
            task = Task.create(Project.get(), 'publish', description="Работа O'Reilly", assigned='admin',
                               project_code=Project.get_project_code(), triggers=self.triggers)
            note = Note.create(task, 'Комментарий 100%', context='publish/review')
            return task.get_search_key(), note.get_search_key()
        obj = Search.get_by_search_key(self.key)
        if self.operation == 'delete':
            obj.delete()
        else:
            obj.set_value('status', self.operation)
            obj.commit(triggers=self.triggers)


def run(case):
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    try:
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        if case.get('sort'):
            parent = Search.get_by_code('contract/entity', 'B')
            tasks = [Task.create(parent, process, commit=False) for process in ('review', 'start')]
            try:
                return {'sorted': [obj.get_process() for obj in Task.sort_shot_tasks(tasks)]}
            except TypeError as exc:
                return {'error': type(exc).__name__}
        SearchType.get('sthpw/task')
        # WebInit installs this in original TACTIC; Batch does not.
        if not any(obj.get_value('class_name') == 'tactic.core.bootstrap.StatusLogTrigger'
                   for obj in Trigger.get_static_triggers()):
            trigger = SearchType.create('sthpw/trigger')
            trigger.set_value('event', 'change|sthpw/task|status', temp=True)
            trigger.set_value('class_name', 'tactic.core.bootstrap.StatusLogTrigger', temp=True)
            trigger.set_value('mode', 'same process,same transaction', temp=True)
            Trigger.append_static_trigger(trigger)
        triggers = case.get('triggers', True)
        create = BusinessCommand('create', triggers=triggers)
        task_key, note_key = Command.execute_cmd(create)
        task = Search.get_by_search_key(task_key)
        note = Search.get_by_search_key(note_key)
        fields = ('process', 'context', 'status', 'pipeline_code', 'project_code', 'assigned', 'description', 'login')
        result = {'created': {key: task.get_value(key) for key in fields},
                  'completion': [task.get_completion()],
                  'note': {key: note.get_value(key) for key in ('process', 'context', 'note', 'login', 'search_type', 'search_code')},
                  'parents': [task.get_parent().get_code(), note.get_parent().get_code()]}
        for status in ('Pending', 'Complete', 'Complete', 'Pending'):
            Command.execute_cmd(BusinessCommand(status, task_key, triggers))
            task = Search.get_by_search_key(task_key)
            result['completion'].append(task.get_completion())
        result['ended'] = bool(task.get_value('actual_end_date'))
        search = Search('sthpw/status_log')
        search.add_order_by('id')
        result['status_log'] = [[obj.get_value('from_status'), obj.get_value('to_status')]
                                for obj in search.get_sobjects()]
        result['journal'] = Search('sthpw/transaction_log').get_count()
        result['change_timestamps'] = sorted((obj.get_value('search_type'), obj.get_value('search_code'))
                                            for obj in Search('sthpw/change_timestamp').get_sobjects())
        Command.execute_cmd(BusinessCommand('delete', note_key))
        Command.execute_cmd(BusinessCommand('delete', task_key))
        result['deleted'] = [Search('sthpw/task').get_count(), Search('sthpw/note').get_count()]
        return result
    finally:
        Environment.set_security(previous)
