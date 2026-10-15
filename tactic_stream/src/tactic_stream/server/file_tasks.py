"""Owned bounded file-task worker; execution always uses the submitting login."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
import logging
import os
from pathlib import Path
import time
import threading

from pyasm.biz.file_project import MODE, access
from pyasm.command import Command
from pyasm.common import Container
from pyasm.search import Search
from pyasm.security import Batch
from tactic.command.file_project_cmd import FileProjectCmd
from tactic.command.file_storage import FileProjectBusy

log = logging.getLogger(__name__)
credentials = threading.local()


@contextmanager
def worker_scope():
    old = Container.get('FileTransfer:service')
    Container.put('FileTransfer:service', True)
    try:
        yield
    finally:
        Container.put('FileTransfer:service', old)


def call(action, **kwargs):
    from pyasm.search.search import _context
    context = _context.get()
    if not hasattr(credentials, 'tickets'):
        credentials.tickets = {}
    batch = Batch(login_code=context.login, project_code=context.project, ticket_cache=credentials.tickets)
    try:
        with worker_scope():
            for attempt in range(4):
                command = FileProjectCmd(action=action, log_exception=False, **kwargs)
                try:
                    Command.execute_cmd(command)
                    return command.info
                except FileProjectBusy:
                    if attempt == 3:
                        raise
                    time.sleep(.25 * (attempt + 1))
    finally:
        batch._scope.__exit__(None, None, None)
        batch._scope = None


def run_transfer(task, *, stopped=lambda: False, heartbeat=lambda: None):
    claimed = call('transfer_claim', task=task)
    args = {'task': task, 'worker_token': claimed['worker_token']}
    file = {}
    try:
        while not stopped():
            heartbeat()
            file = call('transfer_verify_next', **args)
            if file['complete']:
                break
            if file.get('skipped'):
                continue
            if file['state'] == 'ready':
                value = file['sha256']
            else:
                path = Path(file['_path'])
                initial = path.stat()
                if initial.st_size != file['size']:
                    raise ValueError('Stored upload length changed')
                digest, done, last = sha256(), 0, time.monotonic()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                        if stopped():
                            return
                        digest.update(block)
                        done += len(block)
                        heartbeat()
                        if time.monotonic() - last >= 5 or done == file['size']:
                            call('transfer_verify_progress', path=file['path'], bytes=done, **args)
                            last = time.monotonic()
                final = path.stat()
                if (initial.st_size, initial.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
                    raise ValueError('Stored upload changed during verification')
                value = digest.hexdigest()
            call('transfer_verify_finish', blob=file['blob'], sha256=value, **args)
        while not stopped():
            heartbeat()
            result = call('transfer_step', **args)
            if result['state'] != 'running':
                return result
    except Exception as error:
        if isinstance(error, FileProjectBusy):
            raise
        try:
            details=getattr(error,'file_error',None)
            if not details and file.get('path') and not file.get('complete'):
                details={'path':file['path'],'operation':'verification','cause':str(error)}
            call('transfer_fail', error=str(error), **({'file_error':details} if details else {}), **args)
        except Exception:
            log.exception('Could not record file-task failure')
        raise


def pending_tasks(store, project_after='', task_after='', credential=None):
    from pyasm.search.search import RequestContext, request_context
    with request_context(RequestContext(store, 'admin', 'admin')):
        return _pending_tasks(project_after, task_after, credential)


def _pending_tasks(project_after, task_after, credential):
    """One bounded scan; callers retain cursors between ticks."""
    from pyasm.security import Ticket
    from pyasm.common import Environment
    key = credential[0] if credential else None
    batch = Batch(login_code='admin', ticket=key if key and Ticket.get_by_valid_key(key) else None)
    try:
        if credential is not None:
            credential[:] = [Environment.get_security().get_ticket().get_key()]
        search = Search('sthpw/project')
        search.add_filter('type', MODE)
        search.add_order_by('code')
        search.add_filter('code', project_after, op='>=')
        search.set_limit(1)
        project = search.get_sobject()
        if not project:
            return [], '', ''
        from pyasm.biz import Project
        Project.set_project(project.get_code())
        with access(project.get_code()):
            from pyasm.search import SearchType
            if not SearchType.column_exists('file_project/sync', 'kind'):
                return [], project.get_code() + '\x01', ''
            from pyasm.biz.file_project import find
            policy = find('chunk', 'storage-policy', False)
            policy = policy.get_json_value('data') if policy else {}
            if policy.get('indexed') and policy.get('gc_interval_seconds', 86400) and policy.get('next_gc_at', 0) <= time.time():
                active = Search('file_project/sync')
                active.add_filter('kind', 'gc')
                active.add_filters('state', ['queued', 'running'])
                active.set_limit(1)
                if not active.get_sobject():
                    call('gc_begin', dry_run=False)
            search = Search('file_project/sync')
            search.add_filters('kind', ['upload', 'gc', 'mutation'])
            search.add_filters('state', ['queued', 'running'])
            search.add_filter('lease_until', int(time.time()), op='<=')
            search.add_order_by('code')
            if task_after:
                search.add_filter('code', task_after, op='>')
            search.set_limit(5)
            rows = search.get_sobjects()
            tasks = [{'project': project.get_code(), 'task': row.get_code(), 'owner': row.get_json_value('data')['owner'],
                      'kind': row.get_json_value('data')['kind']} for row in rows[:4]]
            return tasks, project.get_code() if len(rows) > 4 else project.get_code() + '\x01', rows[3].get_code() if len(rows) > 4 else ''
    finally:
        batch._scope.__exit__(None, None, None)
        batch._scope = None


def start_files(settings, heartbeat=None, stop=None):
    os.environ['TACTIC_DATA_DIR'] = settings['data_dir']
    os.environ['TACTIC_CONFIG_PATH'] = settings.get('config_path', '')
    from pyasm.search.storage import Store
    store = Store(Path(settings['data_dir']))
    import multiprocessing
    parent = multiprocessing.parent_process()
    def stopped():
        return bool((stop is not None and stop.value) or (parent and not parent.is_alive()))
    def notify():
        if heartbeat is not None:
            heartbeat.value = time.monotonic()
    def perform(task):
        batch = None
        try:
            if not hasattr(credentials, 'tickets'):
                credentials.tickets = {}
            batch = Batch(login_code=task['owner'], project_code=task['project'], ticket_cache=credentials.tickets)
            if task['kind'] == 'gc':
                run_gc(task['task'], stopped=stopped, heartbeat=notify)
            elif task['kind'] == 'mutation':
                run_bulk(task['task'], stopped=stopped, heartbeat=notify)
            else:
                run_transfer(task['task'], stopped=stopped, heartbeat=notify)
        except FileProjectBusy:
            # The failed lock precedes mutations; queued/running tasks remain resumable.
            pass
        except Exception as error:
            log.exception('File task failed: %s', task['task'])
            if batch is not None:
                batch._scope.__exit__(None, None, None)
                batch._scope = None
                batch = None
            admin = Batch(login_code='admin', project_code=task['project'], ticket_cache=credentials.tickets)
            try:
                action = {'upload':'transfer_block','mutation':'bulk_block','gc':'gc_fail'}[task['kind']]
                call(action, task=task['task'], error=str(error))
            finally:
                admin._scope.__exit__(None, None, None)
                admin._scope = None
        finally:
            if batch is not None:
                batch._scope.__exit__(None, None, None)
                batch._scope = None
    project_after = task_after = ''
    credential = []
    active = {}
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix='file-task') as executor:
        while not stopped():
            notify()
            active = {key: future for key, future in active.items() if not future.done()}
            if len(active) < 4:
                tasks, project_after, task_after = pending_tasks(store, project_after, task_after, credential)
                for task in tasks:
                    key = (task['project'], task['task'])
                    if key not in active and len(active) < 4:
                        active[key] = executor.submit(perform, task)
            time.sleep(.25)


def run_bulk(task, *, stopped=lambda: False, heartbeat=lambda: None):
    claimed = call('bulk_claim', task=task)
    if claimed.get('state') in ('complete','cancelled','error'):
        return claimed
    args = {'task':task,'worker_token':claimed['worker_token']}
    from pyasm.search.search import _context
    from pyasm.biz.file_job_signals import FileJobSignals
    context = _context.get()
    signals = FileJobSignals(context.store.data_dir,context.project,task)
    finished=False
    try:
        command = FileProjectCmd(action='bulk_run', log_exception=False, **args)
        command._bulk_stopped = lambda: (heartbeat(), stopped())[1]
        with worker_scope():
            Command.execute_cmd(command)
        finished=True
        return command.info
    except Exception as error:
        if isinstance(error, FileProjectBusy):
            raise
        # COMMIT can succeed even when its reply is lost; never relabel a committed job as failed.
        try:
            status=call('bulk_status',task=task)
        except Exception:
            status={}
        if status.get('state')=='complete':
            finished=True
            return status
        call('bulk_fail',error=str(error),**args)
        finished=True
        if isinstance(error,InterruptedError):
            return call('bulk_status',task=task)
        raise
    finally:
        if finished:
            signals.clear()


def run_gc(task, *, stopped=lambda: False, heartbeat=lambda: None):
    while not stopped():
        heartbeat()
        try:
            result = call('gc_step', task=task)
        except Exception as error:
            call('gc_fail', task=task, error=str(error))
            raise
        for entry in result.get('reap', []):
            from pyasm.biz.file_bytes import byte_lock
            try:
                with byte_lock(Path(entry['_path'])):
                    Path(entry['_path']).unlink(missing_ok=True)
            except OSError:
                # A stale lease can outlive its HTTP writer; retry after this job's heartbeat expires.
                return result
            Path(entry['_path'] + '.lock').unlink(missing_ok=True)
            call('gc_purged', task=task, blob=entry['blob'])
        for directory in result.get('_staging', []):
            import re
            from pyasm.biz.file_bytes import byte_lock
            directory = Path(directory)
            if not directory.exists():
                continue
            with os.scandir(directory) as entries:
                for entry in entries:
                    heartbeat()
                    if stopped():
                        return
                    if not entry.is_file(follow_symlinks=False) or not re.fullmatch('[0-9a-f]{32}\\.tar(?:\\.lock)?', entry.name):
                        continue
                    path = Path(entry.path)
                    path = path.with_suffix('') if path.suffix == '.lock' else path
                    try:
                        with byte_lock(path):
                            path.unlink(missing_ok=True)
                        path.with_name(path.name + '.lock').unlink(missing_ok=True)
                    except OSError:
                        # An expired HTTP writer may still own the OS lock; a later GC retries.
                        continue
        if result['state'] in ('complete', 'error', 'queued', 'cancelled'):
            return result
