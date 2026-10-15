"""Exercise the unchanged Handler client on owned SQLite and PostgreSQL/Apache fixtures."""
import argparse
import importlib.util
from importlib.resources import files
from unittest import TestCase
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xmlrpc.client import Fault
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def backend(args):
    from pyasm.common import Config
    from pyasm.search.storage import Store
    from pyasm.security.authenticator import hash_password
    from tactic.startup import FirstRunInit
    from tactic_stream.server.monitor import TacticMonitor
    data = args.data_dir.resolve()
    data.mkdir(parents=True, exist_ok=False)
    root = ET.fromstring(files('tactic_stream').joinpath('config/tactic-conf.xml').read_text(encoding='utf8'))
    root.find('./install/hostname').text = '0.0.0.0'
    root.find('./services/enable').text = 'tactic'
    root.find('./services/process_count').text = '3' if args.backend == 'PostgreSQL' else '1'
    root.find('./services/start_port').text = str(args.port)
    if args.backend == 'PostgreSQL':
        # Match Compose's Apache balancer: one explicit listener per worker.
        ports = root.find('./services/ports')
        if ports is None:
            ports = ET.SubElement(root.find('./services'), 'ports')
        ports.text = '|'.join(str(args.port + index) for index in range(3))
    root.find('./checkin/asset_base_dir').text = str(data / 'assets')
    root.find('./checkin/win32_sandbox_dir').text = str(data / 'sandbox')
    root.find('./checkin/linux_sandbox_dir').text = str(data / 'sandbox')
    section = root.find('./database')
    section.clear()
    values = dict(vendor=args.backend, sobject_database='handler_system_' + args.nonce if args.backend == 'PostgreSQL' else 'sthpw')
    if args.backend == 'PostgreSQL':
        values.update(host='postgres', user='stream', port='5432', password_file='/run/secrets/postgres_password')
    for key, value in values.items():
        ET.SubElement(section, key).text = value
    config = data / 'tactic-conf.xml'
    ET.ElementTree(root).write(config, encoding='utf-8')
    os.environ.update(TACTIC_DATA_DIR=str(data), TACTIC_CONFIG_PATH=str(config))
    os.environ.pop('TACTIC_TMP_CONFIG_PATH', None)
    os.environ.pop('TACTIC_PORTS', None)
    Config.reload_config()
    try:
        Store(data).initialize(hash_password(os.environ['HANDLER_CHECK_PASSWORD']))
        FirstRunInit().execute()
        TacticMonitor().execute()
    finally:
        if args.backend == 'PostgreSQL':
            import psycopg
            with psycopg.connect(host='postgres', dbname='postgres', user='stream', password=Path(values['password_file']).read_text().strip(), autocommit=True) as db:
                for name in ('handler_project_' + args.nonce, values['sobject_database']):
                    db.execute(psycopg.sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(psycopg.sql.Identifier(name)))


def wait_server(address):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            with urlopen(address + '/health', timeout=2) as response:
                assert json.load(response)['service'] == 'tactic_stream'
            return
        except (HTTPError, URLError, TimeoutError, ConnectionError):
            time.sleep(0.2)
    raise TimeoutError('Owned test server did not become ready: ' + address)


def check(address, handler, password, nonce, directory):
    previous_path = sys.path.copy()
    sys.path.insert(0, str(handler))
    from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
    path = handler / 'thlib/tactic_query.py'
    spec = importlib.util.spec_from_file_location('handler_deployment_queries', path)
    query = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(query)
    client = TacticServerStub(setup=False, protocol='xmlrpc')
    client.set_server(address)
    client.set_project('admin')
    token = client.get_ticket('admin', password)
    client.set_ticket(token)
    checks = []
    try:
        assert client.ping() == 'OK'
        checks.append('login_ticket_ping')
        with urlopen(address + '/', timeout=5) as response:
            assert 'text/html' in response.headers['Content-Type'] and b'<html' in response.read()
        checks.append('vue_next_to_xmlrpc')
        with TestCase().assertRaises(Fault) as denied:
            client.server.query(dict(client.ticket, ticket='invalid'), 'sthpw/project')
        assert denied.exception.faultCode == 403
        checks.append('invalid_ticket_denied')
        code = 'handler_project_' + nonce
        result = client.execute_cmd('tactic.command.CreateProjectCmd', dict(project_code=code, project_title='Handler test', project_stype=['asset']))
        assert result['status'] == 'OK'
        client.set_project(code)
        stype = code + '/asset'
        obj = client.insert(stype, dict(code='HANDLER_OBJECT', name='Кириллица'))
        key = obj['__search_key__']
        assert client.update(key, dict(description='Updated'))['description'] == 'Updated'
        assert client.query(stype, filters=[('code', 'HANDLER_OBJECT')])[0]['name'] == 'Кириллица'
        checks.append('project_schema_object_crud')
        task = client.create_task(key, process='publish', description='Handler task')
        assert task['process'] == 'publish'
        note = client.create_note(key, 'Handler note')
        assert note['note'] == 'Handler note'
        checks.append('tasks_notes')
        for name, kwargs in (
                ('get_projects_and_logins', dict(current_login='admin')),
                ('query_search_types_extended', dict(project_code=code)),
                ('query_sobjects', dict(search_type=stype + '?project=' + code, project_code=code, limit=10, compressed_return=False, include_snapshots=False))):
            script = query.prepare_serverside_script(getattr(query, name), kwargs, shrink=False, catch_traceback=False)
            script['_debug_args'] = False
            response = client.execute_python_script('', kwargs=script)
            assert response['status'] == 'OK'
            value = json.loads(response['info'])
            if name == 'query_sobjects':
                assert value['sobjects_list'][0]['code'] == 'HANDLER_OBJECT'
            checks.append('handler_' + name)
        client.start('Handler abort test')
        client.update(key, dict(description='Aborted'))
        client.abort()
        client.set_ticket(token)
        assert client.get_by_search_key(key)['description'] == 'Updated'
        client.start('Handler finish test')
        client.update(key, dict(description='Finished'))
        client.finish('Finished')
        client.set_ticket(token)
        assert client.get_by_search_key(key)['description'] == 'Finished'
        checks.append('start_finish_abort')
        client.insert('config/naming', dict(search_type=stype, context='publish', checkin_type='strict',
            dir_naming='{project.code}/{sobject.code}/{context}/v{version}', file_naming='{basefile}.{ext}'))
        checks.append('server_naming_config')
        source = directory / 'handler-payload.txt'
        payload = 'Handler repository Кириллица'.encode('utf8')
        source.write_bytes(payload)
        snap = client.simple_checkin(key, 'publish', str(source), mode='upload', create_icon=False)
        paths = client.get_paths(key, 'publish', version=1, file_type='main', single=True)
        assert paths['lib_path']
        files = client.query('sthpw/file', filters=[('snapshot_code', snap['code'])])
        assert files and files[0]['relative_dir'] is not None, {k: files[0].get(k) for k in ('file_name', 'relative_dir', 'checkin_dir', 'snapshot_code', 'type')}
        base = client.get_base_dirs()['web_base_dir']
        url = address + base.rstrip('/') + '/' + files[0]['relative_dir'].strip('/') + '/' + files[0]['file_name']
        url = quote(url, safe=':/')
        with urlopen(url, timeout=5) as response:
            assert response.read() == payload
        with urlopen(Request(url, headers={'Range': 'bytes=0-6'}), timeout=5) as response:
            assert response.status == 206 and response.read() == payload[:7]
        checks.append('http_upload_checkin_repository_download_range')
        for bad_path in ('/ui/assets/%2e%2e/tactic-conf.xml', '/ui/assets/not-existing.js', '/admin/'):
            try:
                urlopen(address + bad_path, timeout=5).close()
            except HTTPError as error:
                assert error.code == 404
            else:
                raise AssertionError('File path escape or Vue fallback: ' + bad_path)
        checks.append('file_path_boundaries')
        return dict(server=address, checks=checks, handler_client_unchanged=True, gui_tested=False)
    finally:
        if client.server:
            client.server.__exit__(None, None, None)
        sys.path[:] = previous_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler', type=Path, default=ROOT.parent.parent / 'th_codex')
    parser.add_argument('--output', type=Path, default=ROOT / '.test-tmp/handler-deployment.json')
    parser.add_argument('--local-only', action='store_true')
    parser.add_argument('--backend', choices=('Sqlite', 'PostgreSQL'))
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--port', type=int)
    parser.add_argument('--nonce')
    args = parser.parse_args()
    if args.backend:
        assert args.nonce and len(args.nonce) == 12 and all(c in '0123456789abcdef' for c in args.nonce)
        return backend(args)
    if not (args.handler / 'launch.pyw').is_file():
        parser.error('Existing Handler checkout with launch.pyw is required')
    nonce = secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    results = {}
    with tempfile.TemporaryDirectory(prefix='stream-handler-') as temporary:
        directory = Path(temporary)
        import socket
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        data = directory / 'local'
        environment = dict(os.environ, HANDLER_CHECK_PASSWORD=password)
        log = (directory / 'local.log').open('wb')
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--backend', 'Sqlite', '--nonce', nonce, '--data-dir', str(data), '--port', str(port)], env=environment, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            address = 'http://127.0.0.1:' + str(port)
            wait_server(address)
            results['local_sqlite'] = check(address, args.handler, password, nonce, directory)
            print('Local SQLite: OK', flush=True)
        except Exception:
            log.flush()
            import sqlite3
            with sqlite3.connect(data / 'db/sthpw.db') as db:
                errors = db.execute('SELECT stack_trace FROM exception_log ORDER BY id DESC LIMIT 1').fetchall()
                if errors:
                    print(errors[0][0], file=sys.stderr)
            print((directory / 'local.log').read_text(encoding='utf8', errors='replace')[-1000:], file=sys.stderr)
            raise
        finally:
            stop = data / 'temp/log/stop.monitor'
            stop.parent.mkdir(parents=True, exist_ok=True)
            stop.touch()
            try:
                process.wait(20)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(5)
            log.close()
        if not args.local_only:
            docker = shutil.which('docker') or str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Docker/Docker/resources/bin/docker.exe')
            compose = [docker, 'compose', '--project-name', 'tactic-stream-linux', '-f', str(ROOT / 'deploy/docker/compose.yaml')]
            def command(*arguments):
                result = subprocess.run(arguments, capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError(result.stderr.strip())
                return result.stdout.strip()
            pg = command(*compose, 'ps', '-q', 'postgres')
            networks = json.loads(command(docker, 'inspect', pg))[0]['NetworkSettings']['Networks']
            network = next(iter(networks))
            apache_container = command(*compose, 'ps', '-q', 'apache')
            image = json.loads(command(docker, 'inspect', apache_container))[0]['Config']['Image']
            backend_name, apache_name = 'handler-api-' + nonce, 'handler-apache-' + nonce
            docker_data = '/tmp/handler-' + nonce
            proxy = directory / 'apache.conf'
            proxy.write_text((ROOT / 'deploy/docker/apache.conf').read_text().replace('http://app:', 'http://' + backend_name + ':'), encoding='utf8')
            try:
                command(*compose, 'run', '-d', '--no-deps', '--name', backend_name, '--user', 'root', '-v', str(ROOT / 'tools') + ':/opt/check-tools:ro', '-v', str(ROOT / 'deploy/docker') + ':/opt/check-deploy:ro', '-e', 'HANDLER_CHECK_PASSWORD=' + password, 'app', 'python', '-B', '/opt/check-tools/handler_deployment_check.py', '--backend', 'PostgreSQL', '--nonce', nonce, '--data-dir', docker_data, '--port', '8081')
                command(docker, 'run', '-d', '--name', apache_name, '--network', network, '-p', '127.0.0.1::80', '-v', str(proxy) + ':/etc/apache2/sites-available/tactic-stream.conf:ro', image, 'apache2ctl', '-D', 'FOREGROUND')
                port = command(docker, 'port', apache_name, '80/tcp').rsplit(':', 1)[1]
                address = 'http://127.0.0.1:' + port
                wait_server(address)
                results['server_postgres_apache'] = check(address, args.handler, password, nonce, directory)
                command(docker, 'exec', '-e', 'STREAM_DEPLOY_URL=http://' + apache_name,
                        '-e', 'TACTIC_DATA_DIR=' + docker_data, '-e', 'TACTIC_CONFIG_PATH=' + docker_data + '/tactic-conf.xml',
                        '-e', 'TACTIC_PORTS=',
                        backend_name, 'python', '/opt/check-deploy/check.py')
                results['server_postgres_apache']['deployment_origin_assets_workers'] = True
                print('PostgreSQL through Apache: OK', flush=True)
            except Exception:
                print(command(docker, 'logs', backend_name)[-3000:], file=sys.stderr)
                raise
            finally:
                subprocess.run([docker, 'exec', backend_name, 'python', '-c', "from pathlib import Path; Path('" + docker_data + "/temp/log/stop.monitor').touch()"], capture_output=True)
                subprocess.run([docker, 'stop', '-t', '20', backend_name], capture_output=True)
                subprocess.run([docker, 'rm', '-f', apache_name, backend_name], capture_output=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
