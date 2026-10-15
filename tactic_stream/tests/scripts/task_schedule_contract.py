"""Original task scheduler calls, fixed dates and owned parent/tasks only."""
from datetime import datetime, timedelta
from pyasm.biz import Pipeline, Task, Project
from pyasm.biz.task import TaskAutoSchedule
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security

MODES = ('even', 'even_day', 'from_end_date')
CASES = list(MODES) + ['generate_' + mode for mode in MODES] + ['dependent', 'explicit']


def install_fixture(db):
    for name in ('start_date', 'due_date'):
        db.execute('ALTER TABLE dep_parent ADD COLUMN ' + name + ' timestamp')


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        code = self.kwargs.get('code') or 'TS_PARENT'
        pipeline_code = code + '_PIPE'
        Pipeline.create('Task schedule', '', 'contract/dep_parent',
            '<pipeline><process name="first" type="manual" duration="2"/><process name="second" type="manual" duration="3"/><process name="third" type="manual" duration="2"/><connect from="first" to="second"/><connect from="second" to="third"/></pipeline>', code=pipeline_code)
        parent = SearchType.create('contract/dep_parent?project=' + Project.get_project_code())
        parent.set_value('code', code)
        parent.set_value('pipeline_code', pipeline_code)
        parent.set_value('start_date', '2026-10-05 09:00:00')
        parent.set_value('due_date', '2026-10-11 18:00:00')
        parent.commit(triggers=False)
        if self.kwargs.get('generate'):
            settings = Search('config/prod_setting')
            settings.add_filter('key', 'schedule/mode')
            setting = settings.get_sobject() or SearchType.create('config/prod_setting')
            setting.set_value('key', 'schedule/mode')
            setting.set_value('value', self.kwargs['mode'])
            setting.commit(triggers=False)
            setting.clear_cache()
            return parent.get_search_key()
        previous = None
        for number, process in enumerate(('first', 'second', 'third'), 1):
            start = datetime(2026, 10, 4 + number * 2, 12)
            task = Task.create(parent, process, status='Pending', triggers='none',
                start_date=start, end_date=start + timedelta(days=number), depend_id=previous.get_id() if previous else None)
            previous = task
        return parent.get_search_key()


class Schedule(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        code = self.kwargs.get('code') or 'TS_PARENT'
        parent = Search.get_by_search_key('contract/dep_parent?project=%s&code=%s' % (Project.get_project_code(), code))
        mode = self.kwargs.get('mode') or 'even'
        if self.kwargs.get('generate'):
            tasks = Task.add_initial_tasks(parent, start_date='2026-10-05', schedule_mode='even_day' if self.kwargs.get('explicit') else None)
        else:
            tasks = Task.get_by_sobject(parent, order=False)
            tasks.sort(key=lambda row: row.get_id())
            if mode == 'dependent':
                tasks[0].set_value('bid_start_date', '2026-10-05 12:00:00')
                tasks[0].set_value('bid_end_date', '2026-10-09 12:00:00')
                tasks[0].commit()
                tasks[0].update_dependent_tasks()
            else:
                TaskAutoSchedule(search_key=parent.get_search_key(), tasks=tasks, mode=mode).execute()
                # The source stages dates; its caller commits them.
                for task in tasks:
                    task.commit()
        return result(code)


def result(code='TS_PARENT'):
    tasks = Search('sthpw/task')
    tasks.add_filter('search_code', code)
    tasks.add_filter('project_code', Project.get_project_code())
    tasks.add_order_by('id')
    return [[task.get_value('process'), task.get_datetime_value('bid_start_date').strftime('%Y-%m-%d %H:%M:%S'),
             task.get_datetime_value('bid_end_date').strftime('%Y-%m-%d %H:%M:%S')] for task in tasks.get_sobjects()]


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        name = case.get('operation', 'even')
        generate = name.startswith('generate_') or name == 'explicit'
        mode = 'even' if name == 'explicit' else name.removeprefix('generate_')
        Command.execute_cmd(Setup(code='TS_' + name, generate=generate, mode=mode))
        return Command.execute_cmd(Schedule(code='TS_' + name, generate=generate, mode=mode, explicit=name == 'explicit'))
    finally:
        Environment.set_security(previous)
