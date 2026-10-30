"""Explicitly started, account/project-scoped agent process; no automatic startup."""
import _thread
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4

from pyasm.common.config import config_file_lock
from tactic_stream.server.monitor import lock_monitor

BUSY = ('starting', 'connected', 'stopping')
_children = []


def directory(data, owner, project):
    scope = hashlib.sha256((owner + '\0' + project).encode()).hexdigest()
    return Path(data) / 'agent_executors' / scope


def write(path, document):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
    temporary.chmod(0o600)
    os.replace(temporary, path)


def current(scope):
    path = scope / 'current.json'
    if not path.is_file():
        return None
    run = json.loads(path.read_text(encoding='utf-8'))['run']
    if str(UUID(run)) != run:
        raise ValueError('Invalid executor run')
    return scope / run


def state(scope):
    run = current(scope)
    if run is None:
        return dict(state='stopped', error='', managed=False)
    value = json.loads((run / 'state.json').read_text(encoding='utf-8'))
    if value['state'] in BUSY:
        try:
            lease = lock_monitor(run / 'process.lock')
        except RuntimeError:
            pass
        else:
            lease.close()
            if value['state'] != 'starting' or time.time() - value['updated'] > 10:
                value.update(state='failed', error='The agent executor stopped unexpectedly. Connect again.')
    if (run / 'stop').exists() and value['state'] in BUSY:
        value['state'] = 'stopping'
    return dict(state=value['state'], error=value.get('error', ''), managed=True)


def start(scope, server, project, ticket, stream_root, handler_root=None):
    scope.mkdir(parents=True, exist_ok=True, mode=0o700)
    with config_file_lock(scope / 'current.json'):
        previous = state(scope)
        if previous['state'] in BUSY:
            return previous
        run = scope / str(uuid4())
        run.mkdir(mode=0o700)
        write(run / 'state.json', dict(state='starting', error='', updated=time.time()))
        write(scope / 'current.json', dict(run=run.name))
        command = [sys.executable, '-B', '-X', 'utf8', '-m', 'tactic_stream.agent_runtime',
                   '--server', server, '--project', project, '--stream-root', str(stream_root), '--allow-changes']
        if handler_root:
            command += ['--handler-root', str(handler_root)]
        environment = dict(os.environ, TACTIC_AGENT_TICKET=ticket, TACTIC_AGENT_RUN_DIR=str(run), PYTHONUTF8='1')
        environment.pop('TACTIC_AGENT_PASSWORD', None)
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=environment, cwd=stream_root,
                start_new_session=os.name != 'nt', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as error:
            write(run / 'state.json', dict(state='failed', error=str(error).replace(ticket, '[redacted]'), updated=time.time()))
        else:
            _children[:] = [child for child in _children if child.poll() is None] + [process]
        return state(scope)


def stop(scope):
    scope.mkdir(parents=True, exist_ok=True, mode=0o700)
    with config_file_lock(scope / 'current.json'):
        value = state(scope)
        if value['state'] in BUSY:
            (current(scope) / 'stop').touch(mode=0o600)
            value['state'] = 'stopping'
        return value


def main():
    run = Path(os.environ.pop('TACTIC_AGENT_RUN_DIR'))
    ticket = os.environ.get('TACTIC_AGENT_TICKET', '')
    lease = lock_monitor(run / 'process.lock')
    finished = threading.Event()
    interrupted = threading.Event()

    def publish(status, error=''):
        write(run / 'state.json', dict(state=status, error=error.replace(ticket, '[redacted]') if ticket else error, updated=time.time()))

    def watch():
        while not finished.wait(.25):
            if (run / 'stop').exists():
                interrupted.set()
                _thread.interrupt_main()
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        if not (run / 'stop').exists():
            from tactic_stream.agent_host import main as host
            host(connected=lambda: publish('connected'))
    except KeyboardInterrupt:
        publish('stopped')
    except Exception as error:
        publish('failed', str(error))
    else:
        publish('stopped')
    finally:
        finished.set()
        watcher.join(timeout=1)
        if interrupted.is_set():
            publish('stopped')
        lease.close()


if __name__ == '__main__':
    main()
