"""Server settings and one worker; the parent lifecycle lives in TacticMonitor."""
import logging
from logging.handlers import RotatingFileHandler
import math
import multiprocessing
import os
from pathlib import Path
import re
import time

from pyasm.common.config import Config, ConfigException
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


def check_database_config(bootstrap=False):
    vendor = Config.get_value('database', 'vendor', default='Sqlite')
    if vendor == 'PostgreSQL':
        return
    if vendor.lower() != 'sqlite':
        raise UnsupportedContract('Database vendor %s is not migrated yet' % vendor)
    if Config.get_value('database', 'sobject_database', default='sthpw') != 'sthpw':
        raise UnsupportedContract('A different system database is not migrated yet')


def read_log_dir(data_dir):
    data_dir = Path(data_dir).expanduser().resolve()
    with request_context(RequestContext(Store(data_dir), 'admin')):
        from pyasm.common import Environment
        return Path(Environment.get_tmp_dir()) / 'log'


def parse_service_config(values, port=None, num_processes=None, *, use_environment=True):
    """Shared by monitor startup and configuration edits; no files or processes."""
    def number(key, default, integer=False):
        value = values.get(key, '').strip() or str(default)
        try:
            result = int(value) if integer else float(value)
        except ValueError:
            raise ConfigException('services/%s must be a number' % key, field='services/' + key,
                hint='Enter a whole number.' if integer else 'Enter a positive finite number.') from None
        if not math.isfinite(result) or result <= 0:
            raise ConfigException('services/%s must be positive and finite' % key, field='services/' + key,
                hint='Enter a positive finite number.')
        return result
    enabled = {value.strip() for value in re.split(r'[|,]', values.get('enable', 'tactic')) if value.strip()}
    if 'tactic' not in enabled or enabled - {'tactic', 'queue', 'files'}:
        raise UnsupportedContract('Only tactic, queue and files services are migrated; watch folders are not ready')
    configured_ports = (os.environ.get('TACTIC_PORTS') if use_environment else None) or values.get('ports', '').strip()
    ports = None
    if configured_ports:
        try:
            ports = [int(value.strip()) for value in configured_ports.split('|')]
        except ValueError:
            raise ConfigException('services/ports must be a pipe-separated port list', field='services/ports') from None
        if not ports or len(set(ports)) != len(ports) or any(not 1 <= value <= 65535 for value in ports):
            raise ConfigException('services/ports must contain distinct ports in 1..65535', field='services/ports')
        if port is not None or (num_processes is not None and num_processes != len(ports)):
            raise ConfigException('CLI port/worker overrides conflict with services/ports', field='services/ports')
    count = num_processes if num_processes is not None else number('process_count', 3, True)
    listen_port = port if port is not None else number('start_port', 8081, True)
    if count < 1 or not 1 <= listen_port <= 65535:
        raise ConfigException('Worker count must be positive and port 1..65535', field='services/start_port')
    result = dict(port=ports[0] if ports else listen_port, ports=ports,
        process_count=len(ports) if ports else count, thread_count=number('thread_count', 50, True), queue_enabled='queue' in enabled,
        files_enabled='files' in enabled)
    for key, default in [('check_interval', 1), ('worker_timeout', 120), ('startup_timeout', 60),
                         ('shutdown_timeout', 10), ('restart_delay', 1)]:
        result[key] = number(key, default)
    result['update_interval'] = number('update_interval', .5)
    if not .1 <= result['update_interval'] <= 2:
        raise ConfigException('services/update_interval must be between 0.1 and 2 seconds',
            field='services/update_interval', hint='Enter a number between 0.1 and 2 seconds.')
    return result


def read_server_config(data_dir, host=None, port=None, num_processes=None):
    data_dir = Path(data_dir).expanduser().resolve()
    with request_context(RequestContext(Store(data_dir), 'admin')):
        values = {key: Config.get_value('services', key) for key in Config.get_section_values('services')}
        result = parse_service_config(values, port, num_processes)
        check_database_config()
        hostname = host or Config.get_value('install', 'hostname', default='127.0.0.1')
        if hostname == 'localhost':
            hostname = '127.0.0.1'
        if '{port}' in hostname:
            raise UnsupportedContract('IIS hostname placeholders are not migrated')
        from tactic_stream.server.configuration import validate_setting
        validate_setting('install/hostname', hostname)
        result.update(data_dir=data_dir.as_posix(), config_path=Config.get_config_path(), host=hostname, log_dir=read_log_dir(data_dir).as_posix())
        return result


def start_server(settings, sockets=None, heartbeat=None, stop=None, slot=0):
    import uvicorn
    from anyio import to_thread
    from tactic_stream.server.app import create_app
    os.environ['TACTIC_DATA_DIR'] = settings['data_dir']
    os.environ['TACTIC_CONFIG_PATH'] = settings['config_path']
    server = uvicorn.Server(uvicorn.Config(create_app(Path(settings['data_dir']), settings['thread_count'], event_collector=sockets is None),
        host=settings['host'], port=settings['port'], timeout_notify=0,
        # Shared Windows listeners cannot belong to multiple Proactor IOCPs.
        loop='asyncio:SelectorEventLoop' if os.name == 'nt' and sockets is not None else 'auto',
        timeout_graceful_shutdown=settings['shutdown_timeout']))
    log_dir = Path(settings['log_dir'])
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / ('worker.%s.log' % slot), maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(process)d] %(name)s: %(message)s'))
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(handler.formatter)
    root.addHandler(console)
    for name in ('', 'uvicorn', 'uvicorn.access'):
        logging.getLogger(name).addHandler(handler)
    parent = multiprocessing.parent_process()
    async def notify():
        if (stop is not None and stop.value) or (parent and not parent.is_alive()):
            server.should_exit = True
            return
        # A live ping thread would miss a blocked event loop or exhausted pool.
        await to_thread.run_sync(time.monotonic)
        if heartbeat is not None:
            heartbeat.value = time.monotonic()
    server.config.callback_notify = notify
    try:
        server.run(sockets=sockets)
    finally:
        root.removeHandler(console)
        console.close()
        root.setLevel(previous_level)
        for name in ('', 'uvicorn', 'uvicorn.access'):
            logging.getLogger(name).removeHandler(handler)
        handler.close()


def startup(port, server=''):
    """Original worker entry-point signature, using the current Python/ASGI server."""
    settings = read_server_config(Path(os.environ.get('TACTIC_DATA_DIR', 'data')), host=server or None, port=port)
    start_server(settings)


def recover_queue_jobs(settings, pid):
    """Called only after the monitor has joined its own dead queue process."""
    import platform
    from pyasm.security import Batch
    from pyasm.command import Command
    from tactic.command.queue import _FinishJobsCmd
    with request_context(RequestContext(Store(Path(settings['data_dir'])), 'admin')):
        batch = Batch(login_code='admin')
        try:
            Command.execute_cmd(_FinishJobsCmd(host='%s:%s' % (platform.node(), pid), state='pending'))
        finally:
            batch._scope.__exit__(None, None, None)
            batch._scope = None


def start_queue(settings, heartbeat=None, stop=None):
    """Owned queue process; heartbeat stops while a command is executing."""
    from pyasm.security import Batch
    from tactic.command import JobTask
    os.environ['TACTIC_DATA_DIR'] = settings['data_dir']
    os.environ['TACTIC_CONFIG_PATH'] = settings['config_path']
    handler = RotatingFileHandler(Path(settings['log_dir']) / 'queue.log',
        maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(process)d] %(name)s: %(message)s'))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(handler.formatter)
    root.addHandler(handler)
    root.addHandler(console)
    batch = None
    try:
        batch = Batch(login_code='admin')
        task = JobTask(check_interval=settings['check_interval'])
        parent = multiprocessing.parent_process()
        def notify():
            if (stop is not None and stop.value) or (parent and not parent.is_alive()):
                task._stop.set()
            elif heartbeat is not None:
                heartbeat.value = time.monotonic()
        task._heartbeat = notify
        task.execute()
    finally:
        if batch is not None:
            batch._scope.__exit__(None, None, None)
            batch._scope = None
        for output in (handler, console):
            root.removeHandler(output)
            output.close()
