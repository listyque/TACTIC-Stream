"""Authenticated TH companions relay only fixed executor start/stop operations."""
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

from pyasm.common import Environment
from pyasm.common.config import config_file_lock
from tactic.ui.panel.agent_request_cmd import identity, text

TTL = 20
BUSY = ('preparing', 'starting', 'connected', 'stopping')


def path():
    owner = hashlib.sha256(Environment.get_user_name().encode()).hexdigest()
    return Path(Environment.get_data_dir()) / 'agent_desktops' / (owner + '.json')


def read(file):
    return json.loads(file.read_text(encoding='utf-8')) if file.is_file() else {}


def write(file, document):
    temporary = file.with_suffix('.tmp')
    temporary.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(file)


def targets(project):
    now = time.time()
    return [dict(id=code, kind='desktop', label=row['label'], **row.get('projects', {}).get(project,
        dict(state='stopped', error=''))) for code, row in read(path()).items() if now - row['seen'] < TTL]


def poll(values):
    device = identity(values.get('device'))
    label = text(values.get('label'), 128)
    reports, acknowledgements = values.get('reports', {}), values.get('acks', [])
    if not isinstance(reports, dict) or len(reports) > 100 or not isinstance(acknowledgements, list) or len(acknowledgements) > 200:
        raise ValueError('Invalid desktop executor report')
    for report in reports.values():
        if (not isinstance(report, dict) or set(report) != {'operation', 'state', 'error'}
                or report['state'] not in (*BUSY, 'stopped', 'failed')):
            raise ValueError('Invalid desktop executor state')
        identity(report['operation'])
        text(report['error'], 2000, empty=True)
    for code in acknowledgements:
        identity(code)
    file = path()
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with config_file_lock(file):
        document = read(file)
        now = time.time()
        document = {code: row for code, row in document.items() if code == device or now - row['seen'] < 86400}
        if device not in document and len(document) >= 20:
            document = {code: row for code, row in document.items() if now - row['seen'] < TTL}
            if len(document) >= 20:
                raise ValueError('Too many connected desktops')
        row = document.setdefault(device, dict(label=label, seen=now, projects={}, commands=[]))
        row.update(label=label, seen=now)
        for project, report in reports.items():
            current = row['projects'].get(project)
            if current and report['operation'] == current['operation']:
                row['projects'][project] = dict(report)
        row['commands'] = [command for command in row['commands'] if command['operation'] not in acknowledgements]
        for command in list(row['commands']):
            if now - command['created'] > 60:
                row['projects'][command['project']].update(state='failed', error='TACTIC Handler did not accept the connection request. Open it and try again.')
                row['commands'].remove(command)
        write(file, document)
        return dict(commands=row['commands'])


def control(device, project, action, unavailable=False):
    identity(device)
    file = path()
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with config_file_lock(file):
        document = read(file)
        row = document.get(device)
        if not row or time.time() - row['seen'] >= TTL:
            raise ValueError('Open TACTIC Handler on the selected computer and sign in to the same account.')
        current = row['projects'].get(project, {})
        if action == 'start':
            if current.get('state') in BUSY:
                return
            if unavailable or any(value.get('projects', {}).get(project, {}).get('state') in BUSY
                    and time.time() - value['seen'] < TTL for value in document.values()):
                raise ValueError('Disconnect the current agent before starting it on another computer.')
        elif current.get('state') not in BUSY:
            return
        if len(row['projects']) >= 100 and project not in row['projects']:
            raise ValueError('Too many desktop project connections')
        operation = str(uuid4())
        row['commands'] = [command for command in row['commands'] if command['project'] != project]
        row['commands'].append(dict(operation=operation, action=action, project=project, created=time.time()))
        row['projects'][project] = dict(operation=operation, state='starting' if action == 'start' else 'stopping', error='')
        write(file, document)
