############################################################
#
#    Copyright (c) 2010, Southpaw Technology
#                        All Rights Reserved
#
#    PROPRIETARY INFORMATION.  This software is proprietary to
#    Southpaw Technology, and is not to be reproduced, transmitted,
#    or disclosed in any way without written permission.
#
#

'''Scheduler class provides a thin layer on top of the Kronos module
by Kronos scheduler (c) Irmen de Jong.  It provides a more object oriented
abraction layer and also adds some Tactic integration and conveniences'''

__all__ = ['Scheduler', 'SchedulerTask']


from .kronos import Scheduler as KronosScheduler
from pyasm.common import Container, Environment
from pyasm.biz import Project
from pyasm.command import Workflow, Command
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import _context, RequestContext, request_context

import threading



class Scheduler(object):
    '''Wrapper around kronos'''

    def __init__(self):
        self.scheduler = KronosScheduler()
        self.tasks = {}
        self.is_started = False


    def get_task(self, name):
        return self.tasks.get(name)

    def get_all_tasks(self):
        return self.tasks

    def get_task_names(self):
        return self.tasks.keys()

    def cancel_task(self, name, delay=0):
        task = self.tasks.get(name)
        if not task:
            print("WARNING: cannot cancel.  Task [%s] not found." % name)
            return

        self.scheduler.cancel(task)
        del(self.tasks[name])
        return


    def _process_task(self, task, mode):
        if mode not in ("threaded", "sequential"):
            raise UnsupportedContract("Forked scheduler tasks are not migrated")
        if not task.kwargs.get("user"):
            task.kwargs["user"] = Environment.get_user_name()
        if not task.kwargs.get("project"):
            project_code = Project.get_project_code()
            task.kwargs['project'] = project_code

        task.kwargs['mode'] = mode

    def add_single_task(self, task, delay=0, mode='threaded'):
        action = task._do_execute
        self._process_task(task, mode)
        scheduler_task = self.scheduler.add_single_task(
            action=action, taskname=task.get_name(),
            initialdelay=delay,
            processmethod=mode, args=None, kw=None )
        self.tasks[task.get_name()] = scheduler_task


    def add_interval_task(self, task, interval, mode='threaded',delay=0):
        action = task._do_execute
        self._process_task(task, mode)
        scheduler_task = self.scheduler.add_interval_task(
            action=action, taskname=task.get_name(),
            initialdelay=delay, interval=interval,
            processmethod=mode, args=None, kw=None )
        self.tasks[task.get_name()] = scheduler_task


    def add_daily_task(self, task, time, mode="threaded", weekdays=list(range(1,8))):

        if isinstance(time, str):
            hour, minute = time.split(":")
            hour = int(hour)
            minute = int(minute)
        else:
            hour = time.hour
            minute = time.minute
        timeonday = (hour, minute)

        weekdays = weekdays
        action = task._do_execute
        self._process_task(task, mode)

        scheduler_task = self.scheduler.add_daytime_task(
            action=action, taskname=task.get_name(),
            weekdays=weekdays, monthdays=None, timeonday=timeonday,
            processmethod=mode, args=None, kw=None )
        self.tasks[task.get_name()] = scheduler_task

    def add_weekly_task(self, task, weekday, time, mode='threaded'):

        weekdays = (weekday,)
        timeonday = (time.hour, time.minute)
        action = task._do_execute
        self._process_task(task, mode)

        scheduler_task = self.scheduler.add_daytime_task(
            action=action, taskname=task.get_name(),
            weekdays=weekdays, monthdays=None, timeonday=timeonday,
            processmethod=mode, args=None, kw=None )

        self.tasks[task.get_name()] = scheduler_task


    def start(self):
        self.scheduler.start()



    def start_thread(self):
        if self.is_started:
            return

        self.thread = threading.Thread(None, self.start)
        #self.thread.daemon = True
        self.thread.daemon = True
        self.thread.start()

        self.is_started = True


    def stop(self):
        self.scheduler.stop()
        if hasattr(self, "thread") and self.thread is not threading.current_thread():
            self.thread.join()
        self.tasks.clear()
        self.is_started = False



    def add_sobject(self, sobject):
        raise UnsupportedContract("Persistent scheduler definitions are not migrated")


    def get():
        scheduler = Container.get("Scheduler")
        if scheduler == None:
            scheduler = Scheduler()
            Container.put("Scheduler", scheduler)
        return scheduler
    get = staticmethod(get)


class SchedulerTaskCmd(Command):

    def execute(self):
        self.get_transaction().set_sync(False)
        task = self.kwargs.get("task")
        task.execute()


class SchedulerTask(object):
    '''Base class for the scheduler'''
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.store = _context.get().store

        user = self.kwargs.get('user')
        if not user:
            user = Environment.get_user_name()
            self.kwargs["user"] = user

        project = self.kwargs.get('project')
        if not project:
            project = Project.get_project_code()
            self.kwargs["project"] = project


        self.site = self.kwargs.get('site')
        if self.site:
            raise UnsupportedContract("Multi-site scheduling is not migrated")

        self.user = user
        self.project = project

        # reuse the login ticket
        security = Environment.get_security()
        self.login_ticket = security.get_ticket()



    def get_name(self):
        return self.kwargs.get("name")

    def _do_execute(self):
        from pyasm.security import Batch
        scope = request_context(RequestContext(self.store, self.user, self.project))
        scope.__enter__()
        batch = None
        try:
            batch = Batch(site=self.site, login_code=self.user,
                          project_code=self.project, ticket=self.login_ticket)
            self.security = Environment.get_security()
            Workflow().init(quiet=True)
            cmd = SchedulerTaskCmd(task=self)
            Command.execute_cmd(cmd)
        finally:
            if batch is not None:
                batch._scope.__exit__(None, None, None)
                batch._scope = None
            scope.__exit__(None, None, None)


    def execute(self):
        print(self.kwargs)

    def execute_test(self):
        print(self.kwargs)

