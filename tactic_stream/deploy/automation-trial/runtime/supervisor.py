"""Trusted image entrypoint. Source runs only in a child within the verified OCI boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys


def log_tail():
    path = Path('/work/execution.log')
    if not path.is_file():
        return ''
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size-128*1024))
        return stream.read(128*1024).decode(errors='replace')


def main():
    request = json.loads(sys.stdin.buffer.read(2 * 1024 * 1024))
    root = Path('/work')
    (root/'request.json').write_text(json.dumps(request), encoding='utf-8')
    status = Path('/proc/self/status').read_text()
    if os.getuid() == 0 or 'NoNewPrivs:\t1' not in status or 'Seccomp:\t2' not in status:
        raise RuntimeError('Required OS restrictions are absent')
    capabilities = next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:'))
    if int(capabilities, 16):
        raise RuntimeError('Unexpected effective Linux capabilities')
    cgroup = Path('/sys/fs/cgroup')
    if (cgroup/'pids.max').read_text().strip() != '128' or (cgroup/'memory.max').read_text().strip() != str(768*1024*1024):
        raise RuntimeError('Kernel process/memory limits are absent')
    environment = dict(os.environ, PYTHONPATH='/opt/trial/src', TACTIC_CONFIG_PATH='', TACTIC_TMP_CONFIG_PATH='')
    with (root/'execution.log').open('w') as log:
        setup = subprocess.run([sys.executable, '/opt/trial/runtime/fixture.py'],
                               env=environment, stdout=log, stderr=log, timeout=25)
        if setup.returncode:
            raise RuntimeError('Private fixture initialization failed; inspect execution log')
        server = subprocess.Popen([sys.executable, '/opt/trial/runtime/fixture.py', '--serve'],
                                  env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            environment['PYTHONPATH'] = '/opt/trial/handler'
            environment['TACTIC_HANDLER_SETTINGS_DIR'] = '/work/profile'
            worker = subprocess.run([sys.executable, '/opt/trial/runtime/handler.py'],
                                    env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=45)
        finally:
            server.terminate()
            try:
                server.wait(5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(5)
    path = root/'report.json'
    if path.is_file() and path.stat().st_size > 2*1024*1024:
        raise ValueError('Trial report exceeds its size limit')
    report = json.loads(path.read_text()) if path.is_file() else {}
    report['status'] = 'passed' if worker.returncode == 0 and report.get('status') == 'passed' else 'failed'
    report['log'] = log_tail()
    report['log_bytes'] = (root/'execution.log').stat().st_size
    report['log_tail_only'] = report['log_bytes'] > 128*1024
    report['runtime'] = dict(platform='linux', python=sys.version.split()[0], uid=os.getuid(), seccomp=True,
                             no_new_privileges=True, effective_capabilities=capabilities,
                             memory_limit=(cgroup/'memory.max').read_text().strip(), pids_limit=(cgroup/'pids.max').read_text().strip())
    print(json.dumps(report))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print(json.dumps(dict(status='failed', error=str(error), log=log_tail())))
        raise SystemExit(1)
