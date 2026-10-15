"""Run file-core contracts in an owned disposable PostgreSQL container or SQLite."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from time import monotonic, sleep
import unittest
import uuid
from xml.etree.ElementTree import Element, SubElement, tostring

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / name) for name in ('src', 'tests')]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@contextmanager
def postgres():
    """No production credentials, existing container or persistent volume is used."""
    name = 'stream-file-check-' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='file-postgres-') as temporary:
        directory = Path(temporary)
        password = directory / 'password'
        password.write_text(secrets.token_urlsafe(32))
        env = directory / 'postgres.env'
        env.write_text('POSTGRES_PASSWORD=' + password.read_text() + '\n')
        def docker(*args):
            return subprocess.run(['docker', *args], check=True, capture_output=True, text=True, timeout=60).stdout.strip()
        try:
            docker('run', '--detach', '--rm', '--name', name, '--label', 'tactic-stream.test=file-project',
                   '--publish', '127.0.0.1::5432', '--env-file', str(env), 'postgres:18.6')
            port = docker('port', name, '5432/tcp').rsplit(':', 1)[1]
            deadline = monotonic() + 30
            while True:
                # The bootstrap server accepts Unix sockets before the final TCP server starts.
                probe = subprocess.run(['docker', 'exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'],
                                       capture_output=True, timeout=5)
                if probe.returncode == 0:
                    break
                if monotonic() >= deadline:
                    raise TimeoutError('Owned PostgreSQL did not start')
                sleep(.1)
            config = Element('config', version='2')
            database = SubElement(config, 'database')
            values = dict(vendor='PostgreSQL', host='127.0.0.1', port=port, user='postgres',
                          password_file=str(password), sobject_database='fp_system')
            for key, value in values.items():
                SubElement(database, key).text = value
            path = directory / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            yield str(path)
        finally:
            if name in docker('ps', '--all', '--format', '{{.Names}}').splitlines():
                docker('rm', '--force', name)
            if name in docker('ps', '--all', '--format', '{{.Names}}').splitlines():
                raise RuntimeError('Owned PostgreSQL container was not removed')


def run(config='', tests=()):
    import test_file_project
    import test_file_project_resilience
    from pyasm.common import Config
    from unittest.mock import patch
    import test_file_change
    import test_file_workspace
    import test_file_transfer
    classes = (test_file_project.FileProjectTest, test_file_project_resilience.FileProjectResilience,
               test_file_change.FileChangeTest, test_file_workspace.FileWorkspaceTest, test_file_transfer.FileTransferTest)
    # Only this freshly-created container is reset between cases.
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            if config:
                import psycopg
                from psycopg import sql
                from xml.etree.ElementTree import parse
                section = parse(config).getroot().find('database')
                credentials = {key: section.findtext(key) for key in ('host', 'port', 'user')}
                credentials['password'] = Path(section.findtext('password_file')).read_text()
                with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as db:
                    for name in ('files', 'files_two', 'classic', 'fp_system'):
                        db.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
            super().startTest(test)
    suite = unittest.TestSuite()
    known = set()
    for cls in classes:
        cls.database_config = config
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            known.add(name)
            if tests and name not in tests:
                continue
            suite.addTest(cls(name))
    if set(tests) - known:
        raise ValueError('Unknown test methods: ' + ', '.join(sorted(set(tests) - known)))
    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
        Config.reload_config()
        try:
            return unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite).wasSuccessful()
        finally:
            for cls in classes:
                cls.database_config = ''
            Config.reload_config()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--postgres', action='store_true', help='Use a new disposable postgres:18.6 container')
    parser.add_argument('tests', nargs='*', help='Optional test method names')
    args = parser.parse_args()
    if args.postgres:
        with postgres() as config:
            success = run(config, args.tests)
    else:
        success = run(tests=args.tests)
    sys.exit(0 if success else 1)
