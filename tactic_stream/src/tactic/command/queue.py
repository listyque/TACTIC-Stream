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

"""Original Queue and sequential, three-attempt JobTask; native owned process lifecycle."""
from pyasm.common import Environment, jsondumps
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Project
from pyasm.search import Search, SearchType, DbContainer, SObject
from pyasm.search.storage import identifier

__all__ = ['Queue', 'JobTask']

class Queue:

    def get_next_job(job_search_type="sthpw/queue", queue_type=None, server_code=None):

        # Claiming is a write even when the queue is empty.
        from pyasm.security.security import _require_admin
        _require_admin()
        probe = SearchType.create(job_search_type)
        if probe.get_base_search_type() != 'sthpw/queue':
            raise UnsupportedContract('Only the original system queue is migrated')
        probe._check_business_write()
        sql = DbContainer.get(probe.get_db_resource())

        search_type_obj = SearchType.get(job_search_type)
        table = search_type_obj.get_table()

        # get the entire queue
        search = Search(job_search_type)
        if queue_type:
            search.add_filter("queue", queue_type)
        if server_code:
            search.add_filter("server_code", server_code)
        search.add_filter("state", "pending")

        search.add_order_by("priority")
        search.add_order_by("timestamp")
        search.add_order_by("id")


        chunk = 10
        search.add_limit(chunk)

        queues = search.get_sobjects()
        queue_id = 0

        for queue in queues:

            queue_id = queue.get_id()

            # attempt to lock this queue
            # have to do this manually
            update = "UPDATE %s SET state = 'locked' WHERE id = %s AND state = 'pending'" % (identifier(table), int(queue_id))

            sql.do_update(update)
            row_count = sql.get_row_count()

            if row_count == 1:
                SObject.get_cache_dict(search_type=job_search_type).clear()
                break
            else:
                queue_id = 0

        if queue_id:
            queue = Search.get_by_id(job_search_type, queue_id)
            return queue
        else:
            return None

    get_next_job = staticmethod(get_next_job)


    def add(command, kwargs, queue_type, priority, description, message_code=None):

        if not isinstance(command, str) or not command or not isinstance(kwargs, dict):
            raise ValueError('Queue requires a command class path and argument dictionary')
        queue = SearchType.create("sthpw/queue")
        queue.set_value("project_code", Project.get_project_code())
        #queue.set_sobject_value(sobject)

        if not queue_type:
            queue_type = "default"
        queue.set_value("queue", queue_type)

        queue.set_value("state", "pending")

        queue.set_value("login", Environment.get_user_name())

        queue.set_value("command", command)
        data = jsondumps(kwargs)
        queue.set_value("data", data)

        if message_code:
            queue.set_value("message_code", message_code)


        if priority is None or priority == "":
            priority = 9999
        queue.set_value("priority", priority)

        if description:
            queue.set_value("description", description)

        queue.set_user()
        queue.commit()

        return queue

    add = staticmethod(add)


import logging
import math
import os
import platform
import threading
import time

from pyasm.common import Common, TacticException
from pyasm.command import Command, CommandExitException
from pyasm.search import Transaction
from pyasm.search.search import RequestContext, request_context
from pyasm.search.transaction import PartialCommitException
from pyasm.security import Batch, Ticket
from .scheduler import Scheduler, SchedulerTask

log = logging.getLogger(__name__)


class _ClaimJobCmd(Command):
    def execute(self):
        task = self.kwargs['task']
        job = task.get_next_job(self.kwargs['queue_type'])
        if job:
            job.set_value('host', task.get_process_key())
            from .checkin_queue_cmd import JOB_COMMAND, save_queue, job_updated
            if job.get_value('command') == JOB_COMMAND:
                save_queue(job)
            else:
                job.commit()
                SObject.get_cache_dict(search_type='sthpw/queue').clear()
            job_updated(job)
        return job


class _FinishJobsCmd(Command):
    def execute(self):
        search = Search('sthpw/queue')
        search.add_filter('host', self.kwargs['host'])
        if self.kwargs.get('job_id') is not None:
            search.add_filter('id', self.kwargs['job_id'])
        search.add_filters('state', ['locked', 'cancel'])
        for job in search.get_sobjects():
            state = 'terminated' if job.get_value('state') == 'cancel' else self.kwargs['state']
            from .checkin_queue_cmd import JOB_COMMAND, save_queue, job_updated
            error = self.kwargs.get('error', '')
            uncertain = self.kwargs.get('uncertain', False)
            if state == 'pending' and job.get_value('command') == JOB_COMMAND:
                state, error = 'error', 'The queue worker stopped. Inspect the snapshot and external trigger effects before retrying.'
                uncertain = True
            job.set_value('state', state)
            if state == 'pending':
                job.set_value('host', '')
            if job.get_value('command') == JOB_COMMAND:
                save_queue(job)
            else:
                job.commit()
                SObject.get_cache_dict(search_type='sthpw/queue').clear()
            job_updated(job, error=error, uncertain=uncertain)


class _RunJobCmd(Command):
    def execute(self):
        # Same local-only transaction policy as the migrated API; remote sync is unported.
        self.get_transaction().set_sync(False)
        job = Search.get_by_id('sthpw/queue', self.kwargs['job_id'])
        if not job or job.get_value('state') != 'locked' or job.get_value('host') != self.kwargs['host']:
            raise CommandExitException('Queue job is no longer owned or was cancelled')
        try:
            kwargs = job.get_json_value('data')
        except (ValueError, TypeError):
            kwargs = job.get_json_value('serialized') if job.has_value('serialized') else {}
        if not kwargs:
            kwargs = {}
        if not isinstance(kwargs, dict):
            raise TacticException('Queue command data must be an argument dictionary')
        kwargs = dict(kwargs, job=job)
        command = job.get_value('command')
        from .checkin_queue_cmd import JOB_COMMAND, save_queue, job_updated
        if command != JOB_COMMAND:
            from .python_cmd import check_script_execution
            check_script_execution()
        script_path = job.get_value('script_path', no_exception=True)
        if script_path:
            command = 'tactic.command.PythonCmd'
            kwargs['script_path'] = script_path
        cmd = Common.create_from_class_path(command, kwargs=kwargs)
        Command.execute_cmd(cmd)
        # Completion joins the command transaction, rather than a later autocommit.
        job.set_value('state', 'complete')
        if command == JOB_COMMAND:
            save_queue(job)
            job_updated(job)
        else:
            job.commit()


class JobTask(SchedulerTask):
    """TACTIC's repeat executor: one job at a time, three attempts, five-second retry.

    Each claim/attempt owns a short Command. The monitor supplies stop/heartbeat
    callbacks and recovers only locks belonging to its dead worker.
    """
    def __init__(self, **kwargs):
        self.job = None
        self.ticket_cache = {}
        self.jobs = []
        self.jobs_completed = 0
        self.max_jobs_completed = kwargs.get('max_jobs_completed', -1)
        self.max_jobs = 20
        self.queue_type = kwargs.get('queue')
        self.pid_path = kwargs.get('pid_path')
        self._stop = threading.Event()
        self._heartbeat = None
        self.set_check_interval(kwargs.get('check_interval') or 1)
        super().__init__(**kwargs)

    def get_check_interval(self):
        return self.check_interval

    def set_check_interval(self, interval):
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError('Queue check interval must be positive and finite')
        self.check_interval = interval

    def get_process_key(self):
        return '%s:%s' % (platform.node(), os.getpid())

    def get_job_search_type(self):
        return 'sthpw/queue'

    def get_next_job(self, queue_type=None):
        return Queue.get_next_job(job_search_type=self.get_job_search_type(), queue_type=queue_type)

    def cleanup_db_jobs(self):
        self.cleanup()

    def cleanup(self, count=0):
        Command.execute_cmd(_FinishJobsCmd(host=self.get_process_key(), state='pending'))
        self.jobs = []
        self.job = None

    def _do_execute(self):
        # SchedulerTaskCmd must not wrap an infinite polling loop in a transaction.
        with request_context(RequestContext(self.store, self.user, self.project)):
            batch = Batch(login_code=self.user, project_code=self.project, ticket=self.login_ticket)
            try:
                self.execute()
            finally:
                batch._scope.__exit__(None, None, None)
                batch._scope = None

    def _wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self._stop.is_set():
            if self._heartbeat:
                self._heartbeat()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._stop.wait(min(remaining, .2))
        return True

    def execute(self):
        try:
            while not self._stop.is_set():
                if self.max_jobs_completed != -1 and self.jobs_completed >= self.max_jobs_completed:
                    return
                if self.pid_path and os.path.exists(self.pid_path):
                    os.utime(self.pid_path, None)
                if self._heartbeat:
                    self._heartbeat()
                if self._stop.is_set():
                    return
                self.check_existing_jobs()
                handled = self.check_new_job(self.queue_type)
                if not handled and self._wait(self.check_interval):
                    return
        finally:
            self.cleanup()

    def check_existing_jobs(self):
        keep = []
        for job in self.jobs:
            search = Search(self.get_job_search_type())
            search.add_filter('id', job.get_id())
            current = search.get_sobject()
            if current and current.get_value('state') == 'cancel':
                Command.execute_cmd(_FinishJobsCmd(host=self.get_process_key(), job_id=job.get_id(), state='terminated'))
            elif current and current.get_value('state') == 'locked':
                keep.append(current)
        self.jobs = keep

    def check_new_job(self, queue_type=None):
        transaction = Transaction.get()
        if transaction and transaction.is_in_transaction():
            raise UnsupportedContract('JobTask polling requires its own context outside an active Command')
        if len(self.jobs) >= self.max_jobs:
            return
        self.job = Command.execute_cmd(_ClaimJobCmd(task=self, queue_type=queue_type))
        if not self.job:
            return
        job = self.job
        self.jobs.append(job)
        log.info('Running job %s: %s', job.get_code(), job.get_value('command'))
        completed = False
        failure = ''
        uncertain = False
        try:
            for attempt in range(3):
                if self._stop.is_set():
                    return
                batch = None
                try:
                    # Use the submitter's identity, never the privileged poller's.
                    login = job.get_value('login')
                    if not login:
                        raise TacticException('Queue job has no submitting login')
                    ticket = self.login_ticket if login == self.user else None
                    if ticket and not Ticket.get_by_valid_key(ticket.get_key()):
                        ticket = None  # Trusted service renews its expired credential; Batch rechecks the account.
                    batch = Batch(login_code=login, project_code=job.get_value('project_code'), ticket=ticket,
                                  ticket_cache=self.ticket_cache)
                    if login == self.user:
                        self.login_ticket = Environment.get_security().get_ticket()
                    from pyasm.command import Workflow
                    Workflow().init(quiet=True)
                    Command.execute_cmd(_RunJobCmd(job_id=job.get_id(), host=self.get_process_key()))
                    completed = True
                    break
                except CommandExitException:
                    break
                except (TacticException, UnsupportedContract, PartialCommitException) as exc:
                    failure = str(exc)
                    uncertain = isinstance(exc, PartialCommitException)
                    # Repeating a partially committed command can duplicate effects.
                    log.exception('Job %s failed without retry', job.get_code())
                    break
                except Exception as exc:
                    failure = str(exc)
                    from .checkin_queue_cmd import JOB_COMMAND
                    if job.get_value('command') == JOB_COMMAND:
                        log.exception('Check-in job %s failed without automatic retry', job.get_code())
                        break
                    log.exception('Job %s failed, attempt %s/3', job.get_code(), attempt + 1)
                finally:
                    if batch is not None:
                        batch._scope.__exit__(None, None, None)
                        batch._scope = None
                if attempt < 2 and self._wait(5):
                    return
            if not completed:
                Command.execute_cmd(_FinishJobsCmd(host=self.get_process_key(), job_id=job.get_id(), state='error', error=failure, uncertain=uncertain))
            SObject.get_cache_dict(search_type='sthpw/queue').clear()
            from .checkin_queue_cmd import cleanup_job
            saved = Search.get_by_id('sthpw/queue', job.get_id())
            try:
                cleanup_job(saved)
            except OSError:
                log.exception('Completed job staging cleanup failed: %s', job.get_code())
            self.jobs_completed += 1
            log.info('Job %s: %s', job.get_code(), 'complete' if completed else 'error or cancelled')
        finally:
            from pyasm.common import Container
            Container.remove('Trigger:prev_called_triggers')
            self.jobs.remove(job)
            self.job = None
        return True

    @staticmethod
    def start(**kwargs):
        scheduler = Scheduler.get()
        task = JobTask(**kwargs)
        task.cleanup_db_jobs()
        scheduler.add_single_task(task, mode='threaded', delay=1)
        scheduler.start_thread()



__all__.append('QueueTest')


class QueueTest(Command):
    def execute(self):
        value = Common.randint(0, 10)
        if value != 5:
            raise ValueError('Queue test exception')
