"""Exercise previous delivered SQLite data, cold backups and independent restoration.

All databases, profiles and processes are created below a new disposable directory.
Input deliveries are read-only; this is an acceptance driver, not a production backup CLI.
"""
import argparse
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree as ET
import zipfile

from tools.file_project_delivery import ROOT
from tools.handler_deployment_check import check
from tools.windows_delivery import digest, extract


def run(command, environment, data=None, *, redactions=(), timeout=300):
    result = subprocess.run([str(item) for item in command], env=environment, input=data,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        diagnostic = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        for value in (environment.get('RECOVERY_TEST_PASSWORD', ''), *redactions):
            if value:
                diagnostic = diagnostic.replace(value, '<redacted>')
        raise RuntimeError('Command failed: ' + str(command[:3]) + '\n' + diagnostic[-4000:])
    return result.stdout


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return str(listener.getsockname()[1])


def verify_delivery(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        path = (directory / entry['path']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('Delivery inventory escapes its directory')
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('Delivery checksum mismatch: ' + entry['path'])
    return manifest


def cold_archive(source, archive):
    """Caller stops every writer first; archive is private and includes credentials."""
    entries = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(source.rglob('*')):
            if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
                raise ValueError('Backup requires materialized files inside its root')
            if path.is_file():
                relative = path.relative_to(source).as_posix()
                if relative == 'backup-manifest.json':
                    raise ValueError('Reserved backup inventory name')
                entries.append(dict(path=relative, bytes=path.stat().st_size, sha256=digest(path)))
                output.write(path, relative)
        output.writestr('backup-manifest.json', json.dumps(dict(format='l12-cold-copy', files=entries)))
    return len(entries)


def restore_archive(archive, target):
    if target.exists():
        raise FileExistsError('Restore needs a new directory')
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read('backup-manifest.json'))
        if manifest['format'] != 'l12-cold-copy':
            raise ValueError('Unknown backup format')
        names = {entry['path'] for entry in manifest['files']}
        if len(names) != len(manifest['files']) or set(source.namelist()) != names | {'backup-manifest.json'}:
            raise ValueError('Backup inventory differs from archive contents')
        for entry in manifest['files']:
            if not (target / entry['path']).resolve().is_relative_to(target.resolve()):
                raise ValueError('Backup inventory escapes restoration directory')
            payload = source.read(entry['path'])
            from hashlib import sha256
            if len(payload) != entry['bytes'] or sha256(payload).hexdigest() != entry['sha256']:
                raise ValueError('Backup checksum mismatch: ' + entry['path'])
    extract(archive, target)
    (target / 'backup-manifest.json').unlink()


def relocate_config(profile, original):
    """Only server-owned paths inside the old root move; client/external paths stay explicit."""
    config = profile / 'server/config/tactic-conf.xml'
    root = ET.fromstring(config.read_text(encoding='utf-8'))
    for key in ('install/tmp_dir', 'checkin/asset_base_dir', 'checkin/win32_local_base_dir',
                'checkin/win32_sandbox_dir'):
        node = root.find(key)
        if node is not None and node.text and Path(node.text).is_relative_to(original):
            node.text = (profile / Path(node.text).relative_to(original)).as_posix()
    from pyasm.common.config import read_config_file, save_config_file
    save_config_file(config, ET.tostring(root, encoding='unicode'), expected_revision=read_config_file(config)[1])


@contextmanager
def server(python, profile, environment, expected_version):
    command = [python, '-I', '-B', '-X', 'utf8', '-m', 'tactic_stream', '--data-dir', profile / 'server']
    log = (profile / 'server.log').open('ab')
    child = subprocess.Popen([str(item) for item in [*command, 'serve', '--host', '127.0.0.1']],
                             env=environment, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    port = ET.parse(profile / 'server/config/tactic-conf.xml').findtext('./services/start_port')
    status_path = profile / 'server/temp/log/monitor.json'
    address = 'http://127.0.0.1:' + port
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('Owned fixture server exited; see ' + str(log.name))
            try:
                with urlopen(address + '/health', timeout=2) as response:
                    health = json.load(response)
                status = json.loads(status_path.read_text())
                if health['version'] == expected_version and status['monitor_pid'] == child.pid and status['state'] == 'running':
                    break
            except (OSError, ValueError):
                pass
            time.sleep(.1)
        else:
            raise TimeoutError('Owned fixture server did not become ready')
        yield address
    finally:
        try:
            if child.poll() is None:
                try:
                    run([*command, 'stop'], environment)
                    child.wait(timeout=35)
                except BaseException:
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
                    child.wait(timeout=10)
                    raise
        finally:
            log.close()
        if status_path.exists():
            assert json.loads(status_path.read_text())['state'] == 'stopped'


def verify_records(address, handler, password, nonce):
    sys.path.insert(0, str(handler))
    from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
    client = TacticServerStub(setup=False, protocol='xmlrpc')
    client.set_server(address)
    project = 'handler_project_' + nonce
    client.set_project(project)
    client.set_ticket(client.get_ticket('admin', password))
    try:
        obj, = client.query(project + '/asset', filters=[('code', 'HANDLER_OBJECT')])
        assert obj['name'] == 'Кириллица' and obj['description'] == 'Finished'
        snapshot, = client.query_snapshots([('search_code', obj['code']), ('context', 'publish'), ('version', 1)])
        file, = client.query('sthpw/file', filters=[('snapshot_code', snapshot['code'])])
        bases = client.get_base_dirs()
        paths = client.get_paths(obj['__search_key__'], 'publish', version=1, file_type='main', single=True)
        assert paths['lib_path'].replace('\\', '/').startswith(bases['asset_base_dir'].replace('\\', '/').rstrip('/') + '/')
        base = bases['web_base_dir']
        url = address + base.rstrip('/') + '/' + file['relative_dir'].strip('/') + '/' + file['file_name']
        with urlopen(quote(url, safe=':/'), timeout=10) as response:
            assert response.read() == 'Handler repository Кириллица'.encode('utf-8')
        assert client.query('sthpw/task', filters=[('search_code', obj['code'])])
        assert client.query('sthpw/note', filters=[('search_code', obj['code'])])
        assert client.query('config/naming', filters=[('context', 'publish')])
        return dict(object_code=obj['code'], snapshot_code=snapshot['code'], file_code=file['code'],
                    tasks=True, notes=True, naming=True, administrator_password=True, repository_bytes=True)
    finally:
        client.server.__exit__(None, None, None)
        sys.path.pop(0)


def sqlite_checks(previous, bundle, directory):
    old_manifest, current = verify_delivery(previous), verify_delivery(bundle)
    old_version, new_version = old_manifest['server_version'], current['server_version']
    assert old_version != new_version, 'Previous-version acceptance cannot be a same-release update'
    old = directory / 'old-installed'
    shutil.copytree(bundle / 'runtime', old / 'runtime')
    extract(next(previous.glob('*-source.zip')), old)
    old_python = old / 'runtime/python.exe'
    python = bundle / 'runtime/python.exe'
    environment = dict(os.environ, RECOVERY_TEST_PASSWORD=secrets.token_urlsafe(24))
    for key in ('TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS', 'TACTIC_DATA_DIR',
                'TACTIC_QML_TEST_SETTINGS_DIR', 'TACTIC_HANDLER_SETTINGS_DIR', 'PYTHONPATH', 'PYTHONHOME'):
        environment.pop(key, None)
    for metadata in (old / 'runtime/Lib/site-packages').glob('tactic_stream-*.dist-info'):
        assert metadata.resolve().is_relative_to(old.resolve())
        shutil.rmtree(metadata)
    run([sys.executable, '-m', 'pip', '--isolated', 'install', '--no-index', '--no-deps', '--no-compile', '--upgrade',
         '--target', old / 'runtime/Lib/site-packages', next(previous.glob('*.whl'))], environment)
    probe = "import sys,tactic_stream; from importlib.metadata import version; assert version('tactic-stream')==tactic_stream.__version__==sys.argv[1]"
    run([old_python, '-I', '-B', '-X', 'utf8', '-c', probe, old_version], environment)
    profile = directory / 'previous-profile'
    run([old_python, '-I', '-B', '-X', 'utf8', bundle / 'resources/app/desktop.py', profile / 'server', free_port()], environment)
    init = "import getpass,os,runpy,sys; getpass.getpass=lambda _:os.environ['RECOVERY_TEST_PASSWORD']; sys.argv=['tactic-stream','--data-dir',sys.argv[1],'init']; runpy.run_module('tactic_stream',run_name='__main__')"
    run([old_python, '-I', '-B', '-X', 'utf8', '-c', init, profile / 'server'], environment)
    nonce = secrets.token_hex(6)
    password = environment['RECOVERY_TEST_PASSWORD']
    with server(old_python, profile, environment, old_version) as address:
        baseline = check(address, old / 'TACTIC-Handler', password, nonce, directory)
        records = verify_records(address, old / 'TACTIC-Handler', password, nonce)
    # Native old Handler stored settings in its program directory; operator migration copies the existing tree.
    preset = "from thlib.environment import env_server; env_server.set_server('127.0.0.1:19300'); env_server.set_user('recovery-fixture'); env_server.save_defaults()"
    run([old_python, '-I', '-B', '-X', 'utf8', '-c', preset], environment)
    shutil.copytree(old / 'TACTIC-Handler/settings', profile / 'handler/settings')
    config_before = (profile / 'server/config/tactic-conf.xml').read_bytes()
    backup = directory / 'before-upgrade.zip'
    before_files = cold_archive(profile, backup)
    run([python, '-I', '-B', '-X', 'utf8', '-m', 'tactic_stream', '--data-dir', profile / 'server', 'upgrade'], environment)
    assert (profile / 'server/config/tactic-conf.xml').read_bytes() == config_before
    with server(python, profile, environment, new_version) as address:
        assert verify_records(address, bundle / 'TACTIC-Handler', password, nonce) == records
    for db in (profile / 'server/db').glob('*.db'):
        with closing(sqlite3.connect(db)) as connection:
            assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    post_backup = directory / 'after-upgrade.zip'
    after_files = cold_archive(profile, post_backup)
    unavailable = directory / 'original-unavailable'
    assert profile.resolve().is_relative_to(directory.resolve()) and not unavailable.exists()
    profile.rename(unavailable)
    results = {}
    for name, archive, executable, version, handler in (
        ('rollback', backup, old_python, old_version, old / 'TACTIC-Handler'),
        ('restore', post_backup, python, new_version, bundle / 'TACTIC-Handler'),
    ):
        restored = directory / name
        restore_archive(archive, restored)
        assert (restored / 'server/config/tactic-conf.xml').read_bytes() == config_before
        relocate_config(restored, profile)
        with server(executable, restored, environment, version) as address:
            assert verify_records(address, handler, password, nonce) == records
        preset_environment = dict(environment, TACTIC_HANDLER_SETTINGS_DIR=str(restored / 'handler'))
        probe = "from thlib.environment import env_server; assert env_server.get_server()=='127.0.0.1:19300'; assert env_server.get_user()=='recovery-fixture'"
        run([python, '-I', '-B', '-X', 'utf8', '-c', probe], preset_environment)
        results[name] = True
    assert not profile.exists(), 'Restoration accidentally recreated the unavailable source root'
    return dict(previous_version=old_version, current_version=new_version, previous_client_scenarios=len(baseline['checks']),
                previous_installed_wheel=True, previous_package_metadata_verified=True,
                upgrade_records_files_config=True, handler_profile_preserved=True,
                before_backup_files=before_files, after_backup_files=after_files, backups_verified=True,
                independent_restoration=True, **results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-source', type=Path, required=True)
    parser.add_argument('--windows-bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='l12-sqlite-', dir=ROOT / '.tmp') as temporary:
        os.environ['TACTIC_QML_TEST_SETTINGS_DIR'] = str(Path(temporary) / 'host-handler')
        result = sqlite_checks(args.previous_source.resolve(), args.windows_bundle.resolve(), Path(temporary))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
