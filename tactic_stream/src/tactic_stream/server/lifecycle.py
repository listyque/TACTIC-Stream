"""Administrator restart requests consumed only by this configuration's monitor."""
import json
from pathlib import Path
import time
from uuid import UUID

from pyasm.common import Config, Environment
from pyasm.common.config import ConfigConflict, config_file_lock, save_config_file
from pyasm.common.errors import SecurityException


def monitor_directory():
    return Path(Environment.get_tmp_dir()) / 'log'


def read_runtime():
    security = Environment.get_security()
    if security is None or not security.is_admin():
        raise SecurityException('Server configuration requires administrator access')
    path = monitor_directory() / 'monitor.json'
    try:
        status = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return dict(available=False, reason='This server is not managed by TacticMonitor.')
    fresh = time.time() - status.get('updated_at', 0) < max(10, 3 * float(Config.get_value('services', 'check_interval') or 1))
    matching = Path(status.get('config_path', '')).resolve() == Path(Config.get_config_path()).resolve()
    available = fresh and matching and bool(status.get('instance_id')) and status.get('state') in ('running', 'starting', 'restarting')
    return dict(available=available, reason='' if available else 'The server monitor is unavailable or outdated.',
        state=status.get('state'), instance_id=status.get('instance_id'), restart_id=status.get('restart_id', ''),
        restart_error=status.get('restart_error', ''),
        web_workers=sum(row['service'] == 'tactic' and row['state'] == 'ready' for row in status.get('workers', [])))


def request_restart(revision, instance_id, request_id):
    # The same administrative boundary guards both facts and mutation.
    runtime = read_runtime()
    for value in (instance_id, request_id):
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError('Invalid restart identity')
    if not isinstance(revision, str) or not revision:
        raise ValueError('A configuration revision is required')
    with config_file_lock(Path(Config.get_config_path())):
        Config.reload_config()
        runtime = read_runtime()
        if runtime.get('restart_id') == request_id:
            return runtime
        if not runtime['available'] or runtime['state'] != 'running':
            raise ConfigConflict('The server monitor is not ready')
        if runtime['instance_id'] != instance_id or Config.get_revision() != revision:
            raise ConfigConflict('Server or configuration changed; reload before restarting')
        path = monitor_directory() / 'restart.monitor'
        if path.exists():
            pending = json.loads(path.read_text(encoding='utf-8'))
            if pending['request_id'] == request_id:
                return dict(runtime, state='restarting', restart_id=request_id)
            raise ConfigConflict('Another restart is already pending')
        save_config_file(path, json.dumps(dict(revision=revision, instance_id=instance_id,
            request_id=request_id)), expected_revision=None)
    return dict(runtime, state='restarting', restart_id=request_id)
