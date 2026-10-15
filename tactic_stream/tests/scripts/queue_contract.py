"""Unchanged persistent queue commands in original and Stream runtimes."""
from pyasm.common import Environment, TacticException
from pyasm.biz import Project, ProjectSetting
from pyasm.command import Command
from pyasm.security import Batch
from pyasm.search import Search
from tactic.command.queue import Queue, JobTask


class QueueCommand(Command):
    attempts = 0
    def execute(self):
        type(self).attempts += 1
        ProjectSetting.create(self.kwargs['key'], Environment.get_user_name() + ':' + Project.get_project_code())
        if self.kwargs.get('failure') == 'tactic':
            raise TacticException('Permanent failure')
        if self.kwargs.get('failure') == 'retry' and type(self).attempts < 3:
            raise ValueError('Retry this command')
        if self.kwargs.get('failure') == 'always':
            raise ValueError('Retries exhausted')


def run(case):
    batch = Batch(login_code='admin', project_code=Project.get_project_code()) if Environment.get_security() is None else None
    try:
        QueueCommand.attempts = 0
        key = 'queue_' + case.get('failure', 'ok')
        command = Command()
        def add():
            command.get_transaction().set_sync(False)
            return Queue.add('queue_contract.QueueCommand', dict(key=key, failure=case.get('failure')), 'contract', 1, 'Exact command')
        command.execute = add
        job = Command.execute_cmd(command)
        task = JobTask(name='contract', queue='contract')
        task.check_new_job('contract')
        search = Search('sthpw/queue')
        search.add_filter('id', job.get_id())
        saved = search.get_sobject()
        return dict(state=saved.get_value('state'), value=ProjectSetting.get_value_by_key(key), attempts=QueueCommand.attempts,
                    completed=task.jobs_completed, jobs=len(task.jobs), project=Project.get_project_code())
    finally:
        if batch is not None and getattr(batch, '_scope', None) is not None:
            batch._scope.__exit__(None, None, None)
            batch._scope = None
