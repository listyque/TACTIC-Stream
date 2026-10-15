"""TACTIC's monitor/worker lifecycle on spawn processes and shared ASGI sockets.

Source concepts: pyasm/web/monitor.py and bin/startup.py; see source_manifest.json.
Web workers and optional sequential queue service are migrated; watch folders are not.
"""
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import multiprocessing
import os
from pathlib import Path
import signal
import socket
import threading
import time

from pyasm.common.errors import UnsupportedContract
from tactic_stream.server.startup import read_server_config, start_server, start_queue, recover_queue_jobs
from tactic_stream.server.update_collector import start_updates


def lock_monitor(path):
    lock = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise RuntimeError('A monitor is already running for this configuration') from None
    return lock


class TacticMonitor:
    def __init__(self, num_processes=None):
        self.num_processes = num_processes
        self.check_interval = None
        self.host = None
        self.port = None
        self.mode = 'normal'
        self.open_browser = False
        self.settings = None
        self.workers = []
        self.sockets = []
        self.should_exit = threading.Event()
        self.spawn = multiprocessing.get_context('spawn')
        self.log = logging.getLogger('tactic_stream.server.monitor')

    def set_check_interval(self, check_interval):
        if not math.isfinite(check_interval) or check_interval <= 0:
            raise ValueError('The monitor check interval must be positive and finite')
        self.check_interval = check_interval

    def set_dev(self, mode):
        if mode:
            raise UnsupportedContract('Development reload is not migrated')

    def write_log(self, msg):
        self.log.info(msg)

    def execute(self):
        if self.mode != 'normal':
            raise UnsupportedContract('Attaching a monitor to unrelated processes is not migrated')
        self._execute()

    def _execute(self):
        self.settings = read_server_config(Path(os.environ.get('TACTIC_DATA_DIR', 'data')),
            self.host, self.port, self.num_processes)
        self.num_processes = self.settings['process_count']
        self.check_interval = self.check_interval or self.settings['check_interval']
        self.log_dir = Path(self.settings['log_dir'])
        self.log_dir.mkdir(parents=True, exist_ok=True)
        lock = lock_monitor(self.log_dir / 'monitor.lock')
        handler = console = None
        previous = {}
        monitor_flag = os.environ.get('TACTIC_MONITOR')
        state = 'stopped'
        try:
            os.environ['TACTIC_MONITOR'] = 'true'
            handler = RotatingFileHandler(self.log_dir / 'monitor.log', maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(process)d] %(message)s'))
            console = logging.StreamHandler()
            self.log.setLevel(logging.INFO)
            self.log.addHandler(handler)
            self.log.addHandler(console)
            for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
                sig = getattr(signal, name, None)
                if sig is not None:
                    previous[sig] = signal.signal(sig, lambda signum, frame: self.should_exit.set())
            ports = self.settings['ports'] or [self.settings['port']]
            for port in ports:
                family, kind, protocol, _, address = socket.getaddrinfo(self.settings['host'], port, type=socket.SOCK_STREAM)[0]
                listener = socket.socket(family, kind, protocol)
                self.sockets.append(listener)
                option = socket.SO_EXCLUSIVEADDRUSE if os.name == 'nt' else socket.SO_REUSEADDR
                listener.setsockopt(socket.SOL_SOCKET, option, 1)
                listener.bind(address)
                listener.listen(2048)
                listener.setblocking(False)
            self.remove_monitor_pid()
            self.write_log('Started monitor [%s], %s workers, %s:%s' %
                (os.getpid(), self.num_processes, self.settings['host'], '|'.join(str(port) for port in ports)))
            for index in range(self.num_processes):
                self.workers.append(dict(process=None, pid=None, service='tactic', restarts=0, failures=0, next_start=0, reason='starting'))
                self._start_worker(index)
            if self.settings['queue_enabled']:
                self.workers.append(dict(process=None, pid=None, service='queue', restarts=0, failures=0, next_start=0, reason='starting'))
                self._start_worker(len(self.workers) - 1)
            if self.settings.get('files_enabled'):
                self.workers.append(dict(process=None, pid=None, service='files', restarts=0, failures=0, next_start=0, reason='starting'))
                self._start_worker(len(self.workers) - 1)
            self.workers.append(dict(process=None, pid=None, service='updates', restarts=0, failures=0, next_start=0, reason='starting'))
            self._start_worker(len(self.workers) - 1)
            self.monitor()
        except BaseException:
            state = 'failed'
            raise
        finally:
            try:
                self.final_kill()
                self._write_status(state)
            finally:
                for listener in self.sockets:
                    listener.close()
                for sig, old_handler in previous.items():
                    signal.signal(sig, old_handler)
                if monitor_flag is None:
                    os.environ.pop('TACTIC_MONITOR', None)
                else:
                    os.environ['TACTIC_MONITOR'] = monitor_flag
                for output in (handler, console):
                    if output:
                        self.log.removeHandler(output)
                        output.close()
                lock.close()

    def _start_worker(self, index):
        worker = self.workers[index]
        heartbeat = self.spawn.Value('d', 0, lock=False)
        stop = self.spawn.Value('b', 0, lock=False)
        if worker['service'] == 'queue':
            process = self.spawn.Process(target=start_queue, args=(self.settings, heartbeat, stop), name='TACTIC-queue')
        elif worker['service'] == 'updates':
            process = self.spawn.Process(target=start_updates, args=(self.settings, heartbeat, stop), name='TACTIC-updates')
        elif worker['service'] == 'files':
            from .file_tasks import start_files
            process = self.spawn.Process(target=start_files, args=(self.settings, heartbeat, stop), name='TACTIC-files')
        else:
            sockets = [self.sockets[index]] if self.settings['ports'] else self.sockets
            process = self.spawn.Process(target=start_server, args=(self.settings, sockets, heartbeat, stop, index), name='TACTIC-%s' % index)
        process.start()
        worker.update(process=process, pid=process.pid, heartbeat=heartbeat, stop=stop, started=time.monotonic(), reason='starting')
        self.write_log('Started worker %s [%s]' % (index, process.pid))

    def _restart_worker(self, index, reason):
        worker = self.workers[index]
        process = worker['process']
        if process.is_alive():
            process.kill()
        process.join(timeout=self.settings['shutdown_timeout'])
        if process.is_alive():
            raise RuntimeError('Worker %s could not be stopped' % worker['pid'])
        exitcode = process.exitcode
        process.close()
        worker['process'] = None
        if worker['service'] == 'queue':
            recover_queue_jobs(self.settings, worker['pid'])
        worker['restarts'] += 1
        worker['failures'] += 1
        delay = min(self.settings['restart_delay'] * 2 ** min(worker['failures'] - 1, 6), 60)
        worker.update(process=None, next_start=time.monotonic() + delay, reason=reason)
        self.write_log('Worker %s [%s]: %s (exit %s); restarting in %.1fs' % (index, worker['pid'], reason, exitcode, delay))

    def remove_monitor_pid(self):
        # Original method removes the stop marker, despite its name.
        (self.log_dir / 'stop.monitor').unlink(missing_ok=True)

    def monitor(self):
        opened = False
        while not self.should_exit.is_set():
            if (self.log_dir / 'stop.monitor').exists():
                self.should_exit.set()
                break
            now = time.monotonic()
            ready = True
            for index, worker in enumerate(self.workers):
                if self.should_exit.is_set():
                    break
                process = worker['process']
                if process is None:
                    ready = False
                    if now >= worker['next_start']:
                        self._start_worker(index)
                    continue
                heartbeat = worker['heartbeat'].value
                reason = None
                if not process.is_alive():
                    reason = 'exited'
                elif not heartbeat and now - worker['started'] > self.settings['startup_timeout']:
                    reason = 'startup timeout'
                elif heartbeat and now - heartbeat > self.settings['worker_timeout']:
                    reason = 'heartbeat timeout'
                if reason:
                    ready = False
                    self._restart_worker(index, reason)
                elif heartbeat:
                    worker['reason'] = 'ready'
                    if now - worker['started'] > self.settings['startup_timeout']:
                        worker['failures'] = 0
                else:
                    ready = False
            self._write_status('running' if ready else 'starting')
            if ready and self.open_browser and not opened:
                import webbrowser
                host = self.settings['host']
                host = '127.0.0.1' if host in ('0.0.0.0', '::') else host
                webbrowser.open('http://%s:%s/' % ('[%s]' % host if ':' in host else host, self.settings['port']))
                opened = True
            self.should_exit.wait(self.check_interval)

    def _write_status(self, state):
        status = dict(monitor_pid=os.getpid(), state=state, host=self.settings['host'], port=self.settings['port'],
            config_path=self.settings['config_path'], updated_at=time.time(),
            workers=[dict(index=index, pid=worker['pid'], service=worker['service'], state=worker['reason'] if worker['process'] else 'stopped',
                          restarts=worker['restarts']) for index, worker in enumerate(self.workers)])
        temporary = self.log_dir / ('monitor.%s.tmp' % os.getpid())
        try:
            temporary.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary, self.log_dir / 'monitor.json')
        except OSError as error:
            self.write_log('Could not update monitor status: %s' % error)
        finally:
            temporary.unlink(missing_ok=True)

    def final_kill(self):
        self.should_exit.set()
        for worker in self.workers:
            if worker['process']:
                worker['stop'].value = 1
        deadline = time.monotonic() + self.settings['shutdown_timeout']
        for worker in self.workers:
            process = worker['process']
            if process is None:
                continue
            process.join(timeout=max(0, deadline - time.monotonic()))
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            if process.is_alive():
                raise RuntimeError('Worker %s is still running' % worker['pid'])
            process.close()
            worker['process'] = None
            if worker['service'] == 'queue':
                recover_queue_jobs(self.settings, worker['pid'])
            worker.update(process=None, reason='stopped')
        self.write_log('Stopped monitor and all owned workers')
