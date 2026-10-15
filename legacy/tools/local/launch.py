"""Run the ORIGINAL TACTIC CherryPy server, with a private project-local runtime.
No test backend is imported. Existing config is never upgraded or overwritten.
Fresh SQLite initialization is explicit, uses the shipped TACTIC seed and its
original upgrade commands, and fails closed if any upgrade step reports errors.
"""
from __future__ import annotations
import argparse
import getpass
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import types
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
# Embedded Python ._pth and -I omit the executed script directory.
_LOCAL_TOOLS = str(Path(__file__).resolve().parent)
if _LOCAL_TOOLS not in sys.path: sys.path.insert(0, _LOCAL_TOOLS)


def configure_paths(data: Path, config: Path) -> None:
    paths = [ROOT / 'src', ROOT / 'src/client', ROOT / '3rd_party/python3/site-packages', ROOT / '3rd_party/common/site-packages', ROOT]
    sys.path[:0] = [str(p) for p in paths if str(p) not in sys.path]
    # Exact public getters from src/install/data/tacticenv, without a system
    # installation or stale global tactic_paths. All paths point to this fork.
    env = types.ModuleType('tacticenv')
    env.get_install_dir = lambda: str(ROOT).replace('\\', '/')
    env.get_site_dir = lambda: str(data).replace('\\', '/')
    env.get_data_dir = lambda: str(data).replace('\\', '/')
    def temp_dir():
        from pyasm.common import Environment
        return Environment.get_tmp_dir()
    env.get_temp_dir = temp_dir
    sys.modules['tacticenv'] = env
    os.environ.update(TACTIC_INSTALL_DIR=str(ROOT), TACTIC_SITE_DIR=str(data), TACTIC_DATA_DIR=str(data),
                      TACTIC_CONFIG_PATH=str(config), TACTIC_APP_SERVER='cherrypy', TACTIC_CLEANUP='true')
    os.environ.pop('TACTIC_MODE', None)


def dependency_check() -> bool:
    checks = ('cgi', 'lxml.etree', 'six', 'requests', 'PIL.Image', 'dateutil', 'pytz',
              'yaml', 'Cryptodome.Cipher.AES', 'Cryptodome.PublicKey.RSA', 'psycopg2',
              'cherrypy', 'tactic.core.graph_model', 'tactic.ui_api.mount')
    failed = []
    print('Interpreter:', sys.executable, sys.version.split()[0])
    print('Source fork:', ROOT)
    for name in checks:
        try:
            importlib.import_module(name)
            print('OK ', name)
        except Exception as exc:
            failed.append(name)
            print('FAIL', name, type(exc).__name__, str(exc))
    if failed:
        print('Environment check FAILED. Run SETUP_ENV.bat, or repair the listed dependencies.')
    else:
        print('Imports passed. This is NOT a live-database compatibility test.')
    return not failed


def secure_password() -> str:
    password = getpass.getpass('New LOCAL admin password (at least 12 characters): ')
    if len(password) < 12 or password != getpass.getpass('Repeat password: '):
        raise ValueError('Password too short or confirmation differs; nothing initialized')
    return password


def create_local_seed(data: Path, config: Path) -> None:
    if data.exists() and any(data.iterdir()):
        raise ValueError('Data directory is not empty. Existing files will NOT be replaced: ' + str(data))
    if not sys.stdin.isatty():
        raise ValueError('Fresh initialization requires an interactive terminal; no default password is generated')
    print('Create a NEW TACTIC SQLite installation using the original seed at:', data)
    print('This is an experimental standalone database, not a PostgreSQL replacement or a test fixture.')
    if input('Type CREATE to continue: ').strip() != 'CREATE':
        raise ValueError('Cancelled')
    password = secure_password()
    from pyasm.security import Login
    encrypted = Login.encrypt_password(password)
    del password
    stage = data.with_name(data.name + '.initializing')
    if stage.exists():
        raise ValueError('Incomplete initialization exists; inspect it before retrying: ' + str(stage))
    shutil.copytree(ROOT / 'src/install/start', stage)
    for folder in ('config', 'assets', 'tmp', 'plugins', 'dist', 'log', 'backup'):
        (stage / folder).mkdir(parents=True, exist_ok=True)
    root = ET.Element('config', {'version': '2'})
    sections = {
        'database': {'vendor': 'Sqlite', 'sqlite_db_dir': str(data / 'db')},
        'install': {'hostname': '127.0.0.1', 'server': 'localvue'},
        'security': {'version': '2', 'password': encrypted, 'allow_guest': 'false'},
        'checkin': {'asset_base_dir': str(data / 'assets'), 'web_base_dir': '/assets',
                    'win32_client_repo_dir': str(data / 'assets'), 'linux_client_repo_dir': str(data / 'assets'),
                    'win32_sandbox_dir': str(data / 'sandbox'), 'linux_sandbox_dir': str(data / 'sandbox'),
                    'sudo_no_password': 'false', 'version_padding': '3'},
        'services': {},
    }
    for category, values in sections.items():
        node = ET.SubElement(root, category)
        for key, value in values.items(): ET.SubElement(node, key).text = str(value).replace('\\', '/')
    target = stage / 'config/tactic-conf.xml'
    ET.ElementTree(root).write(target, encoding='utf-8', xml_declaration=True)
    try: target.chmod(0o600)
    except OSError: pass
    (stage / 'local-install.json').write_text(json.dumps({'format': 1, 'source': str(ROOT), 'created': datetime.now(timezone.utc).isoformat(),
                                                         'state': 'seed-requires-upgrade', 'seed': 'src/install/start'}, indent=2), encoding='utf-8')
    if data.exists(): data.rmdir()  # guaranteed empty above
    stage.rename(data)
    if config != data / 'config/tactic-conf.xml':
        raise ValueError('Fresh initialization requires the default local config path')
    print('Original seed copied. Run MANAGE_TACTIC.bat db upgrade before starting.')


def upgrade_local(data: Path, config: Path) -> None:
    marker = data / 'local-install.json'
    if not marker.is_file() or config != data / 'config/tactic-conf.xml':
        raise ValueError('This command only upgrades a managed LOCAL SQLite copy. Existing installations require their normal DBA procedure.')
    root = ET.parse(config).getroot()
    if root.findtext('database/vendor') != 'Sqlite': raise ValueError('Not a managed SQLite installation')
    print('LOCAL schema upgrade modifies databases. Stop all local TACTIC processes first.')
    if not sys.stdin.isatty() or input('Type UPGRADE to back up and apply original upgrades: ').strip() != 'UPGRADE':
        raise ValueError('Cancelled')
    from managed_sqlite import perform_upgrade
    return perform_upgrade(ROOT, data, config)


def choose_config(data: Path, supplied: str | None) -> Path:
    if supplied:
        result = Path(supplied).expanduser().resolve()
        if not result.is_file(): raise ValueError('Config file does not exist: ' + str(result))
        return result
    local = data / 'config/tactic-conf.xml'
    if local.is_file(): return local
    print('No local TACTIC configuration found.')
    print('For an EXISTING TEST installation, paste its full config XML path.')
    print('For a NEW experimental SQLite installation, run MANAGE_TACTIC.bat db init and MANAGE_TACTIC.bat db upgrade instead.')
    if not sys.stdin.isatty(): raise ValueError('Use --config and --data-dir for an existing TEST installation')
    entered = input('Existing TEST config XML path (empty = cancel): ').strip().strip('"')
    if not entered: raise ValueError('Cancelled: no configuration selected')
    result = Path(entered).expanduser().resolve()
    if not result.is_file(): raise ValueError('Config file not found')
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Existing TEST TACTIC config XML; never overwritten or auto-upgraded')
    parser.add_argument('--data-dir', help='Existing installation data directory, or private local_data by default')
    parser.add_argument('--port', type=int, default=9123)
    parser.add_argument('--legacy', action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--check-startup', action='store_true', help='Run original startup/context registration without listening; may perform original startup initialization')
    group.add_argument('--init-sqlite', action='store_true')
    group.add_argument('--upgrade-local', action='store_true')
    group.add_argument('--check-local-db', action='store_true', help='Read-only managed database structure check')
    group.add_argument('--restore-local', action='store_true', help='Restore an interrupted managed promotion')
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535: parser.error('Choose a local port in 1024..65535')
    data = Path(args.data_dir).expanduser().resolve() if args.data_dir else ROOT / 'local_data'
    config = Path(args.config).expanduser().resolve() if args.config else data / 'config/tactic-conf.xml'
    if args.init_sqlite and args.config: parser.error('--init-sqlite cannot overwrite an existing --config')
    if not (args.check or args.init_sqlite):
        config = choose_config(data, args.config)
        if not args.data_dir and config != data / 'config/tactic-conf.xml':
            if config.parent.name.lower() != 'config':
                raise ValueError('Please supply --data-dir for a config outside the standard data/config directory')
            data = config.parent.parent
    configure_paths(data, config)
    if args.legacy: os.environ['TACTIC_UI'] = 'legacy'
    if args.check: return 0 if dependency_check() else 2
    if args.check_local_db:
        from managed_sqlite import inspect_local
        result = inspect_local(ROOT, data, config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        output = ROOT / '.runtime' / 'local-db-check.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Read-only database report:', output)
        return 0 if result['startup_ready'] else 3
    if args.restore_local:
        from local_lock import local_lock
        from managed_sqlite import restore_pending
        if not sys.stdin.isatty() or input('Type RESTORE to roll back an interrupted publication: ').strip() != 'RESTORE':
            raise ValueError('Cancelled')
        with local_lock(data):
            backup = restore_pending(data)
        print('Original database files restored from:', backup)
        return 0
    if not dependency_check(): return 2
    if args.init_sqlite:
        create_local_seed(data, config); return 0
    if args.upgrade_local:
        upgrade_local(data, config); return 0
    if (data / '.sqlite-promotion.json').exists():
        raise RuntimeError('Interrupted database publication. Run MANAGE_TACTIC.bat db restore; do not start the server.')
    marker = data / 'local-install.json'
    if marker.exists() and json.loads(marker.read_text(encoding='utf-8')).get('state') != 'upgraded':
        raise RuntimeError('The original local seed has not been upgraded successfully. Run MANAGE_TACTIC.bat db upgrade and review errors first.')
    # Check port before any server startup side effects or browser opening.
    if not args.check_startup:
        with socket.socket() as sock:
            try: sock.bind(('127.0.0.1', args.port))
            except OSError as exc: raise RuntimeError('Port %d is already in use; use --port N' % args.port) from exc
    if os.name != 'nt' and hasattr(os, 'getuid') and os.getuid() == 0:
        raise RuntimeError('Do not run TACTIC as root; use an unprivileged account')
    print('Config:', config)
    print('Data:', data)
    print('URL: http://127.0.0.1:%d/tactic/admin/' % args.port)
    print('Original TACTIC server, localhost only. Ctrl+C stops it. No fixture backend.')
    from local_lock import local_lock
    with local_lock(data):
        if (data / '.sqlite-promotion.json').exists():
            raise RuntimeError('Interrupted database publication; restore the original files first')
        from tactic.startup import FirstRunInit
        FirstRunInit().execute()
        from pyasm.web.cherrypy30_startup import CherryPyStartup
        server = CherryPyStartup(args.port)
        server.set_config('global', 'server.socket_host', '127.0.0.1')
        server.set_config('global', 'server.socket_port', args.port)
        server.set_config('global', 'server.thread_pool', 20)
        server.set_config('global', 'request.show_tracebacks', False)
        server.set_config('global', 'engine.autoreload.on', False)
        server.set_config('global', 'log.screen', True)
        if args.check_startup:
            # Constructor starts the original cache scheduler. Stop it before
            # returning from this diagnostic-only process; do not run periodic
            # work merely because a check was requested.
            from pyasm.common import Container
            scheduler = Container.get('Scheduler')
            if scheduler is not None:
                scheduler.stop()
                thread = getattr(scheduler, 'thread', None)
                if thread is not None: thread.join(timeout=5)
            from startup_probe import inspect_registered_services
            from tactic.ui_api.mount import install as install_native_ui
            install_native_ui()
            report = inspect_registered_services(server)
            output = ROOT / '.runtime/startup-check.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print('Original startup/context registration passed; no listening socket started.')
            print('Report:', output)
            print('This is not an authenticated HTTP request or a read-only database check.')
            return 0
        server.execute()
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nStopped.'); raise SystemExit(130)
    except Exception as exc:
        import traceback
        log = ROOT / '.runtime' / 'last-launch-error.txt'
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(traceback.format_exc(), encoding='utf-8')
        except OSError: pass
        print('ERROR:', type(exc).__name__, str(exc))
        print('Details:', log)
        raise SystemExit(1)
