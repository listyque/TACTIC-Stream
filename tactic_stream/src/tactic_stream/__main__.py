import argparse
import getpass
import json
import os
from pathlib import Path

from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store
from pyasm.common.config import Config
from tactic.startup import FirstRunInit


def main():
    parser = argparse.ArgumentParser(description="TACTIC Stream server")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get('TACTIC_DATA_DIR', 'data')))
    parser.add_argument('--config', type=Path, help='Explicit tactic-conf.xml; overrides TACTIC_CONFIG_PATH')
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Explicitly initialize NEW data; refuse existing databases")
    init.add_argument("--login", default="admin")
    init.add_argument('--if-needed', action='store_true', help='Skip initialization when the configured system database already exists')
    commands.add_parser("upgrade", help="Upgrade owned system and registered project schemas")
    commands.add_parser('status', help='Show the monitor and worker state')
    commands.add_parser('stop', help='Request graceful shutdown through stop.monitor')
    register = commands.add_parser('register', help='Register an account using native Login.create (administrator required)')
    register.add_argument('login')
    register.add_argument('--administrator', default='admin')
    register.add_argument('--group', action='append', default=[])
    register.add_argument('--first-name')
    register.add_argument('--last-name')
    register.add_argument('--display-name')
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument('--workers', type=int, default=None)
    serve.add_argument('--config', type=Path, default=argparse.SUPPRESS, help='Explicit tactic-conf.xml')
    serve.add_argument("--open-browser", action="store_true", help="Open the application after startup")
    args = parser.parse_args()
    os.environ['TACTIC_DATA_DIR'] = args.data_dir.expanduser().resolve().as_posix()
    if args.config:
        os.environ['TACTIC_CONFIG_PATH'] = args.config.expanduser().resolve().as_posix()
    if args.command in ('init', 'upgrade'):
        from tactic_stream.server.startup import check_database_config
        check_database_config(bootstrap=True)
    if args.command == "init":
        if args.if_needed and Store(args.data_dir).is_initialized():
            FirstRunInit().execute()
            print('Configured system database is already initialized')
            return
        password = getpass.getpass("New administrator password: ")
        if password != getpass.getpass("Repeat password: "):
            parser.error("Passwords do not match")
        Store(args.data_dir).initialize(hash_password(password), args.login)
        FirstRunInit().execute()
        print("Initialized new owned TACTIC Stream data")
    elif args.command == "upgrade":
        changed = Store(args.data_dir).upgrade()
        FirstRunInit().execute()
        print("Updated owned system/project schemas" if changed else "System/project schemas are up to date")
    elif args.command == 'register':
        from pyasm.security import Login
        from pyasm.security.authenticator import Authenticator
        from pyasm.search.search import RequestContext, request_context
        store = Store(args.data_dir)
        auth = Authenticator(store)
        ticket = auth.get_ticket(args.administrator, getpass.getpass('Administrator password: '))
        try:
            with request_context(RequestContext(store, args.administrator, 'admin')):
                security = auth.bind_security(args.administrator, ticket)
                if not security.is_admin():
                    parser.error('Administrator access is required')
                password = getpass.getpass('New user password: ')
                if password != getpass.getpass('Repeat password: '):
                    parser.error('Passwords do not match')
                if not password or len(password) > 4096:
                    parser.error('A non-empty password of at most 4096 characters is required')
                Login.create(args.login, password, args.first_name, args.last_name,
                             args.group or None, display_name=args.display_name)
            print('Registered account: ' + args.login)
        finally:
            auth.logout(ticket)
    elif args.command in ('status', 'stop'):
        from tactic_stream.server.startup import read_log_dir
        log_dir = read_log_dir(args.data_dir)
        status_path = log_dir / 'monitor.json'
        if not status_path.is_file():
            parser.error('No monitor state exists for this configuration')
        status = json.loads(status_path.read_text(encoding='utf-8'))
        if args.command == 'status':
            print(json.dumps(status, indent=2))
        elif status['state'] in ('stopped', 'failed'):
            print('Monitor is already stopped')
        else:
            (log_dir / 'stop.monitor').write_text('', encoding='utf-8')
            print('Monitor shutdown requested')
    else:
        from tactic_stream.server.monitor import TacticMonitor
        from tactic_stream.server.startup import check_database_config
        check_database_config()
        FirstRunInit().execute()
        Config.reload_config()
        monitor = TacticMonitor(args.workers)
        monitor.host = args.host
        monitor.port = args.port
        monitor.open_browser = args.open_browser
        monitor.execute()


if __name__ == "__main__":
    main()
