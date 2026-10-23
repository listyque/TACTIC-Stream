"""Upgrade delivered PostgreSQL/Apache packages and restore cold copies into fresh volumes."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

from tools.delivery_recovery_checks import (
    ROOT, check, cold_archive, free_port, restore_archive, run, verify_delivery, verify_records,
)

PG = ['sh', '-ec', 'export PGPASSWORD="$(cat /run/secrets/postgres_password)"; exec "$@"', 'owned-postgres']


def qualify(previous, current, handler, directory):
    old_manifest, new_manifest = verify_delivery(previous), verify_delivery(current)
    assert old_manifest['version'] != new_manifest['version'], 'A same-version update is not previous-release acceptance'
    docker = shutil.which('docker')
    if not docker:
        raise FileNotFoundError('Docker is required')
    environment = dict(os.environ, RECOVERY_TEST_PASSWORD=secrets.token_urlsafe(24),
                       STREAM_HTTP_PORT=free_port(), STREAM_WEBMIN_PORT=free_port())
    nonce = secrets.token_hex(6)
    prefix = 'l12-recovery-' + nonce
    owned = []

    def clone(source, name, manifest):
        target = directory / name
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('images.tar', '.local'))
        config = json.loads((target / 'compose.yaml').read_text(encoding='utf-8'))
        for service in config['services'].values():
            image = next(identity for identity, tags in manifest['images'].items() if service['image'] in tags)
            run([docker, 'image', 'inspect', image], environment)
            service['image'] = image  # Run exactly the delivered image ID, independent of mutable local tags.
        (target / 'compose.yaml').write_text(json.dumps(config, indent=2), encoding='utf-8')
        project = prefix + '-' + name
        owned.append((target, project))
        return target, project

    def compose(package, project, *arguments, data=None):
        redactions = [p.read_text().strip() for p in (package / '.local').glob('*-password')]
        return run([docker, 'compose', '--project-name', project, '-f', package / 'compose.yaml', *arguments],
                   environment, data, redactions=redactions)

    def manage(package, project, action, data=None):
        redactions = [p.read_text().strip() for p in (package / '.local').glob('*-password')]
        output = run([sys.executable, '-B', package / 'manage.py', action, '--project-name', project],
                     environment, data, redactions=redactions)
        print(project + ' ' + action + ': OK', flush=True)
        return output

    def backup(package, project, name):
        compose(package, project, 'stop', 'apache', 'app')
        folder = directory / (name + '-files')
        (folder / 'databases').mkdir(parents=True, mode=0o700)
        names = compose(package, project, 'exec', '-T', 'postgres', *PG, 'psql', '-U', 'stream', '-d', 'postgres', '-At',
                        '-c', "SELECT datname FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres' ORDER BY datname").decode().splitlines()
        assert 'sthpw' in names and len(names) >= 2
        for database in names:
            assert re.fullmatch(r'[a-z0-9_]+', database)
            payload = compose(package, project, 'exec', '-T', 'postgres', *PG,
                              'pg_dump', '-U', 'stream', '-Fc', '--create', database)
            (folder / 'databases' / (database + '.dump')).write_bytes(payload)
        for service, volume, mount in (('app', 'stream_data', '/var/lib/tactic_stream'),
                                       ('apache', 'apache_config', '/etc/apache2'),
                                       ('apache', 'webmin_config', '/etc/webmin')):
            payload = compose(package, project, 'run', '--rm', '--no-deps', '-T', '--user', 'root',
                              '--entrypoint', 'tar', service, '-C', mount, '-cf', '-', '.')
            (folder / (volume + '.tar')).write_bytes(payload)
        shutil.copytree(package / '.local', folder / '.local')
        (folder / 'databases.json').write_text(json.dumps(names), encoding='utf-8')
        archive = directory / (name + '.zip')
        count = cold_archive(folder, archive)
        print(name + ': verified cold backup, ' + str(count) + ' files', flush=True)
        return archive

    def restore(source, manifest, archive, name, records):
        restored = directory / (name + '-backup')
        restore_archive(archive, restored)
        package, project = clone(source, name, manifest)
        assert not run([docker, 'volume', 'ls', '-q', '--filter', 'label=com.docker.compose.project=' + project], environment).strip()
        shutil.copytree(restored / '.local', package / '.local')
        compose(package, project, 'up', '-d', '--wait', '--wait-timeout', '120', 'postgres')
        for database in json.loads((restored / 'databases.json').read_text()):
            assert re.fullmatch(r'[a-z0-9_]+', database)
            compose(package, project, 'exec', '-T', 'postgres', *PG,
                    'pg_restore', '-U', 'stream', '--exit-on-error', '--create', '--dbname', 'postgres',
                    data=(restored / 'databases' / (database + '.dump')).read_bytes())
        for service, volume, mount in (('app', 'stream_data', '/var/lib/tactic_stream'),
                                       ('apache', 'apache_config', '/etc/apache2'),
                                       ('apache', 'webmin_config', '/etc/webmin')):
            compose(package, project, 'run', '--rm', '--no-deps', '-T', '--user', 'root', '--entrypoint', 'tar',
                    service, '-C', mount, '-xf', '-', data=(restored / (volume + '.tar')).read_bytes())
        manage(package, project, 'up')
        manage(package, project, 'check')
        assert verify_records('http://127.0.0.1:' + environment['STREAM_HTTP_PORT'], handler,
                              environment['RECOVERY_TEST_PASSWORD'], nonce) == records
        app = compose(package, project, 'ps', '-q', 'app').decode().strip()
        inspection = json.loads(run([docker, 'inspect', app], environment))[0]
        for mount in inspection['Mounts']:
            if mount['Type'] == 'volume':
                assert mount['Name'].startswith(project + '_')
            else:
                assert mount['Destination'].startswith('/run/secrets/')
        manage(package, project, 'stop')
        return True

    try:
        old, project = clone(previous, 'original', old_manifest)
        manage(old, project, 'init', (environment['RECOVERY_TEST_PASSWORD'] + '\n').encode() * 2)
        manage(old, project, 'check')
        address = 'http://127.0.0.1:' + environment['STREAM_HTTP_PORT']
        baseline = check(address, handler, environment['RECOVERY_TEST_PASSWORD'], nonce, directory)
        records = verify_records(address, handler, environment['RECOVERY_TEST_PASSWORD'], nonce)
        config = compose(old, project, 'exec', '-T', 'app', 'cat', '/var/lib/tactic_stream/config/tactic-conf.xml')
        before = backup(old, project, 'before-upgrade')
        updated, unused_project = clone(current, 'updated', new_manifest)
        owned.remove((updated, unused_project))
        shutil.copytree(old / '.local', updated / '.local')
        manage(updated, project, 'update')
        manage(updated, project, 'check')
        assert compose(updated, project, 'exec', '-T', 'app', 'cat', '/var/lib/tactic_stream/config/tactic-conf.xml') == config
        probe = 'import tactic_stream; print(tactic_stream.__version__)'
        assert compose(updated, project, 'exec', '-T', 'app', 'python', '-B', '-c', probe).decode().strip() == new_manifest['version']
        assert verify_records(address, handler, environment['RECOVERY_TEST_PASSWORD'], nonce) == records
        after = backup(updated, project, 'after-upgrade')
        manage(updated, project, 'stop')
        assert not run([docker, 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + project], environment).strip()
        restored = restore(current, new_manifest, after, 'restore', records)
        rollback = restore(previous, old_manifest, before, 'rollback', records)
        return dict(previous_version=old_manifest['version'], current_version=new_manifest['version'],
                    previous_client_scenarios=len(baseline['checks']), upgrade_records_files_config=True,
                    pg_dump_pg_restore=True, administrator_password_preserved=True,
                    repository_apache_webmin_and_secrets=True, separate_restoration_volumes=True,
                    source_services_unavailable=True, restored=restored, rollback=rollback)
    finally:
        for package, project in reversed(owned):
            assert project.startswith(prefix + '-') and len(nonce) == 12
            compose(package, project, 'down', '--volumes', '--remove-orphans', '--timeout', '25')
            for resource, argument in (('ps', '-aq'), ('volume', 'ls')):
                command = [docker, resource, argument]
                if resource == 'volume':
                    command.append('-q')
                assert not run([*command, '--filter', 'label=com.docker.compose.project=' + project], environment).strip()
        print('Owned PostgreSQL acceptance containers and volumes removed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-server', type=Path, required=True)
    parser.add_argument('--server-package', type=Path, required=True)
    parser.add_argument('--handler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='l12-postgres-', dir=ROOT / '.tmp') as temporary:
        os.environ['TACTIC_QML_TEST_SETTINGS_DIR'] = str(Path(temporary) / 'host-handler')
        result = qualify(args.previous_server.resolve(), args.server_package.resolve(), args.handler.resolve(), Path(temporary))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
