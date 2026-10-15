"""Docker deployment, from Windows or Linux. Requires Python 3.10+ and Docker Compose."""
import argparse
from http.cookiejar import CookieJar
import os
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('up', 'init', 'update', 'rebuild', 'apache-config', 'stop', 'status', 'logs', 'check', 'check-postgres'), nargs='?', default='up')
    parser.add_argument('--suite', choices=('foundation', 'schema', 'project', 'plugin', 'command', 'queue', 'diagnostics'), default='foundation', help='PostgreSQL check selection')
    args = parser.parse_args()
    docker = shutil.which('docker')
    if not docker and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Docker/Docker/resources/bin/docker.exe'
        if candidate.is_file():
            docker = str(candidate)
    if not docker:
        parser.error('Docker is not installed or is missing from PATH')
    command = [docker, 'compose', '--project-name', 'tactic-stream-linux', '-f', str(HERE / 'compose.yaml')]

    def compose(*arguments, **kwargs):
        return subprocess.run(command + list(arguments), check=True, **kwargs)

    def apache_config():
        path = '/etc/apache2/sites-available/tactic-stream.conf'
        compose('exec', '-T', 'apache', 'cp', path, path + '.previous')
        compose('exec', '-T', 'apache', 'a2enmod', 'proxy', 'proxy_http', 'proxy_balancer', 'lbmethod_byrequests', 'headers')
        try:
            compose('cp', str(HERE / 'apache.conf'), 'apache:' + path)
            compose('exec', '-T', 'apache', 'apache2ctl', 'configtest')
        except subprocess.CalledProcessError:
            compose('exec', '-T', 'apache', 'cp', path + '.previous', path)
            raise
        compose('exec', '-T', 'apache', 'apache2ctl', 'graceful')

    if args.action in ('up', 'init', 'update', 'rebuild'):
        directory = HERE / '.local'
        directory.mkdir(mode=0o700, exist_ok=True)
        for name, volume in [('postgres', 'postgres_data'), ('webmin', 'webmin_config')]:
            password = directory / (name + '-password')
            if not password.exists():
                existing = subprocess.run([docker, 'volume', 'inspect', 'tactic-stream-linux_' + volume],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if existing.returncode == 0:
                    parser.error('%s data already exists: restore %s; do not generate a new secret' % (name, password))
            try:
                with password.open('x', encoding='utf-8') as output:
                    output.write(secrets.token_urlsafe(40))
                password.chmod(0o600)
            except FileExistsError:
                if not password.read_text(encoding='utf-8').strip():
                    parser.error('%s password file is empty; restore it before starting' % name)
        if args.action in ('init', 'rebuild'):
            compose('build')
        if args.action in ('init', 'update', 'rebuild'):
            compose('stop', 'app')
            compose('run', '--rm', '--no-deps', '-T', '--user', 'root',
                    '-v', str(HERE.parents[1] / 'pyproject.toml') + ':/opt/stream-pyproject.toml:ro',
                    'app', 'python', '-', input=(HERE / 'install-dependencies.py').read_bytes())
        if args.action in ('update', 'rebuild'):
            compose('stop', 'app')
            # Migration failure leaves the app stopped; existing data is never reset.
            compose('run', '--rm', '--no-deps', 'app', 'tactic-stream', 'upgrade')
        if args.action == 'init':
            compose('stop', 'app')
            compose('run', '--rm', '--no-deps', 'app', 'tactic-stream', 'init')
        compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '120')
        apache_config()
        print('Application: http://%s:%s/' % (os.environ.get('STREAM_BIND', '127.0.0.1'), os.environ.get('STREAM_HTTP_PORT', '8082')))
        print('Webmin: https://127.0.0.1:%s/ (root; password in %s)' % (os.environ.get('STREAM_WEBMIN_PORT', '10000'), directory / 'webmin-password'))
        print('System storage follows tactic-conf.xml (SQLite by default); PostgreSQL supports the migrated kernel.')
    elif args.action == 'stop':
        compose('down')  # Named data volumes are retained.
    elif args.action == 'apache-config':
        apache_config()
    elif args.action == 'status':
        compose('ps')
    elif args.action == 'logs':
        compose('logs', '-f', '--tail', '100')
    elif args.action == 'check-postgres':
        root = HERE.parents[1]
        test_file = {'foundation': 'test_postgres.py', 'schema': 'test_schema_postgres.py', 'project': 'test_project_creation.py', 'plugin': 'test_plugin_installation.py', 'command': 'test_plugin_installation.py', 'queue': 'test_plugin_installation.py', 'diagnostics': 'test_plugin_installation.py'}[args.suite]
        target = '/opt/tests/' + test_file
        original = root.parent / 'legacy/src/pyasm/search/database_impl.py'
        if not original.is_file():
            parser.error('Original dialect comparison needs adjacent legacy/src/pyasm/search/database_impl.py')
        compose('run', '--rm', '--no-deps', '-T', '--user', 'root',
                '-v', str(root / 'src') + ':/opt/stream-src:ro',
                '-v', str(root / 'tests') + ':/opt/tests:ro',
                '-v', str(root / 'tools') + ':/opt/tools:ro',
                '-v', str(original) + ':/opt/original_database_impl.py:ro',
                '-e', 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt', '-e', 'STREAM_POSTGRES_HOST=postgres',
                '-e', 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password',
                '-e', 'STREAM_POSTGRES_ORIGINAL=/opt/original_database_impl.py',
                'app', 'python', '-B', target,
                *({'plugin': ['PluginInstallation'], 'command': ['CommandApiLifecycle'], 'queue': ['QueueLifecycle'], 'diagnostics': ['DiagnosticLifecycle']}.get(args.suite, [])))
    else:
        # Root is needed only to read the mode-0600 Compose secret in this check.
        compose('exec', '-T', '--user', 'root', 'app', 'python', '-',
                input=(HERE / 'check.py').read_bytes())
        certificate = compose('exec', '-T', 'apache', 'openssl', 'x509', '-in', '/etc/webmin/miniserv.pem',
                              capture_output=True).stdout.decode()
        tls = ssl.create_default_context(cadata=certificate)
        cookies = CookieJar()
        client = build_opener(HTTPSHandler(context=tls), HTTPCookieProcessor(cookies))
        url = 'https://127.0.0.1:%s' % os.environ.get('STREAM_WEBMIN_PORT', '10000')
        password = (HERE / '.local/webmin-password').read_text().strip()
        login = Request(url + '/session_login.cgi',
                        data=urlencode({'user': 'root', 'pass': password}).encode(),
                        headers={'Cookie': 'testing=1', 'Referer': url + '/'})
        with client.open(login, timeout=15) as response:
            assert response.status == 200
        assert any(cookie.name == 'sid' and cookie.value for cookie in cookies), 'Webmin login failed'
        with client.open(url + '/apache/', timeout=15) as response:
            assert response.status == 200
            assert b'Apache' in response.read()
        client.open(url + '/session_login.cgi?logout=1', timeout=15).close()
        print('Webmin: trusted local HTTPS certificate, root login, Apache module and logout')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)
