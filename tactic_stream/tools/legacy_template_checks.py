"""Exercise the selected legacy examples against independent delivered servers."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree as ET
import zipfile

from tools.delivery_recovery_checks import ROOT, free_port, run, server, verify_delivery
from tools.prepare_legacy_examples import SOURCES, digest

ARCHIVES = {'vfx': 'vfx-1.0.0-stream.1.zip', 'game': 'game-1.0.0-stream.1.zip'}


def native_check(address, fixtures, bundle, output, environment):
    output.mkdir(parents=True, exist_ok=False)
    reports = {}
    for role, login in (('admin', 'admin'), ('artist', fixtures['ordinary_login'])):
        for kind in ARCHIVES:
            name = role + '-' + kind
            target = output / name
            command = [bundle / 'runtime/python.exe', '-I', '-B', '-X', 'utf8',
                       ROOT / 'tests/scripts/installed_handler_gui.py', bundle, address, login,
                       fixtures['templates'][kind]['project'], target]
            with (output / (name + '.log')).open('wb') as log:
                child = subprocess.Popen([str(part) for part in command], env=environment,
                                         stdout=log, stderr=subprocess.STDOUT)
                try:
                    child.wait(timeout=150)
                finally:
                    if child.poll() is None:
                        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                       check=True, capture_output=True)
                        child.wait(timeout=10)
            report = json.loads((target / 'result.json').read_text(encoding='utf-8'))
            assert child.returncode == 0 and report['status'] == 'passed', report
            reports[name] = report
    return reports


def browser_check(address, fixtures, bundle, output, environment):
    output.mkdir(parents=True, exist_ok=False)
    fixture_file = output / 'fixtures.json'
    fixture_file.write_text(json.dumps(fixtures), encoding='utf-8')
    node_environment = dict(environment, ELECTRON_RUN_AS_NODE='1',
                            PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'))
    run([bundle / 'TACTIC Stream.exe', ROOT / 'frontend/tests/installed_templates.mjs',
         address, fixture_file, output], node_environment, timeout=180)
    return json.loads((output / 'result.json').read_text())


def check(address, handler, password, examples, server_examples, directory, nonce):
    sys.path.insert(0, str(handler))
    from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
    from xmlrpc.client import Fault
    client = TacticServerStub(setup=False, protocol='xmlrpc')
    client.set_server(address)
    client.set_project('admin')
    client.set_ticket(client.get_ticket('admin', password))
    reports = {}
    try:
        for kind, filename in ARCHIVES.items():
            project = 'l12_' + kind + '_' + nonce
            client.set_project('admin')
            client.execute_cmd('tactic.command.ProjectTemplateInstallerCmd', dict(
                project_code=project, path=server_examples.rstrip('/') + '/' + filename, verbose=False))
            client.set_project(project)
            with zipfile.ZipFile(examples / filename) as archive:
                manifest, = [name for name in archive.namelist() if name.endswith('/manifest.xml')]
                types = [node.get('code') for node in ET.fromstring(archive.read(manifest)).findall('search_type')]
            unavailable = {}
            for stype in types:
                try:
                    assert client.query(stype) == []
                except Fault as error:
                    if stype not in ('prod/session_contents', 'vfx/texture', 'vfx/node_data'):
                        raise
                    unavailable[stype] = dict(code=error.faultCode, message=error.faultString)
            assert set(unavailable) == ({'prod/session_contents', 'vfx/texture', 'vfx/node_data'} if kind == 'vfx' else set())
            asset = client.insert(kind + '/asset', dict(code='L12_ASSET', name='Тестовый объект'))
            key = asset['__search_key__']
            assert asset['name'] == 'Тестовый объект'
            updated = client.update(key, dict(name='Updated'))
            assert updated['name'] == 'Updated'
            assert client.query(kind + '/asset', [('code', 'L12_ASSET')])[0]['name'] == 'Updated'
            if kind == 'vfx':
                sequence = client.insert('vfx/sequence', dict(code='L12_SEQ', description='Sequence'))
                shot = client.insert('vfx/shot', dict(code='L12_SHOT', sequence_code=sequence['code'],
                    tc_frame_start=1001, tc_frame_end=1100, frame_in=993, frame_out=1108))
                reference = client.insert('vfx/art_reference', dict(name='L12_REFERENCE'))
                client.connect_sobjects(reference['__search_key__'], sequence['__search_key__'])
                assert client.eval("@COUNT(vfx/sequence['id', %s].vfx/art_reference)" % sequence['id']) == 1
                shot_task = client.create_task(shot['__search_key__'], process='animation', assigned='admin')
                client.update(shot_task['__search_key__'], dict(bid_start_date='2026-10-20', bid_end_date='2026-10-24'))
                relation_type = 'vfx/asset_in_shot'
                relation = dict(asset_code=asset['code'], shot_code=shot['code'])
                assert client.query('vfx/shot', [('sequence_code', sequence['code'])])[0]['tc_frame_start'] == 1001
            else:
                game = client.insert('game/game', dict(code='L12_GAME', title='Game'))
                level = client.insert('game/level', dict(code='L12_LEVEL', game_code=game['code']))
                relation_type = 'game/asset_in_level'
                relation = dict(asset_code=asset['code'], level_code=level['code'])
                assert client.query('game/level', [('game_code', game['code'])])[0]['code'] == level['code']
            instance = client.insert(relation_type, relation)
            assert client.query(relation_type, [('asset_code', asset['code'])])[0]['__search_key__'] == instance['__search_key__']
            task = client.create_task(key, process='model', description='Imported template task')
            assert task['process'] == 'model'
            if kind == 'game':
                assert task['pipeline_code'] == project + '/status_default'
                updated = client.update(task['__search_key__'], dict(status='ready'))
                assert updated['status'] == 'ready'
            note = client.create_note(key, 'Заметка после переноса')
            assert note['note'] == 'Заметка после переноса'
            payload = directory / (kind + '.txt')
            payload.write_bytes(('Template repository ' + kind).encode('utf-8'))
            snapshot = client.simple_checkin(key, 'model', str(payload), mode='upload', create_icon=False)
            file, = client.query('sthpw/file', [('snapshot_code', snapshot['code'])])
            url = address + client.get_base_dirs()['web_base_dir'].rstrip('/') + '/' + file['relative_dir'].strip('/') + '/' + file['file_name']
            with urlopen(quote(url, safe=':/'), timeout=10) as response:
                assert response.read() == payload.read_bytes()
            reports[kind] = dict(project=project, installed=True, available_types=len(types) - len(unavailable),
                                 unavailable_types=unavailable, crud=True, task=True, note=True,
                                 hierarchy_and_asset_instance=True, checkin_and_http_bytes=True, asset_key=key)
        artist = 'l12_artist_' + nonce
        group = 'l12_artists_' + nonce
        projects = [item['project'] for item in reports.values()]
        client.set_project('admin')
        code = ('from pyasm.security import Login, LoginGroup\nfrom pyasm.search import SearchType\n'
                'group=SearchType.create("sthpw/login_group")\n'
                'group.set_value("login_group",' + repr(group) + ')\n'
                'group.set_value("access_level","medium")\n'
                'rules=LoginGroup.get_default_access_rule(LoginGroup.MED,' + repr(projects + ['sthpw']) + ')\n'
                'rules=rules.replace("</rules>",\'<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/><rule group="link" element="*" access="allow"/><rule group="builtin" key="view_side_bar" access="allow"/></rules>\')\n'
                'group.set_value("access_rules",rules)\n'
                'group.commit(triggers=False)\nLogin.create(' + repr(artist) + ',' + repr(password) + ',groups=[' + repr(group) + '])\n')
        client.execute_python_script('', kwargs={'code': code})
        client.set_ticket(client.get_ticket(artist, password))
        for kind in ARCHIVES:
            client.set_project(reports[kind]['project'])
            key = reports[kind]['asset_key']
            assert client.get_by_search_key(key)['name'] == 'Updated'
            updated = client.update(key, dict(name='Artist update'))
            assert updated['name'] == 'Artist update'
        try:
            client.query('sthpw/login_group')
        except Fault as error:
            assert error.faultCode == 403
        else:
            raise AssertionError('Ordinary user read protected security records')
        return dict(templates=reports, ordinary_login=artist, ordinary_read_write=True,
                    ordinary_security_records_denied=True, ordinary_trusted_python_grant=True,
                    ordinary_navigation_granted=True, sdk_unchanged=True)
    finally:
        client.server.__exit__(None, None, None)
        sys.path.pop(0)


@contextmanager
def postgres(package, examples, directory, environment, nonce):
    manifest = verify_delivery(package)
    target = directory / 'server-package'
    shutil.copytree(package, target, ignore=shutil.ignore_patterns('images.tar', '.local'))
    config = json.loads((target / 'compose.yaml').read_text(encoding='utf-8'))
    for service in config['services'].values():
        service['image'] = next(identity for identity, tags in manifest['images'].items() if service['image'] in tags)
    (target / 'compose.yaml').write_text(json.dumps(config, indent=2), encoding='utf-8')
    project = 'l12-templates-' + nonce
    docker = shutil.which('docker')
    if not docker:
        raise FileNotFoundError('Docker is required')
    environment = dict(environment, STREAM_HTTP_PORT=free_port(), STREAM_WEBMIN_PORT=free_port())
    compose = [docker, 'compose', '--project-name', project, '-f', target / 'compose.yaml']
    try:
        run([sys.executable, '-B', target / 'manage.py', 'init', '--project-name', project], environment,
            (environment['RECOVERY_TEST_PASSWORD'] + '\n').encode() * 2)
        run([*compose, 'cp', examples, 'app:/tmp/l12-examples'], environment)
        run([sys.executable, '-B', target / 'manage.py', 'check', '--project-name', project], environment)
        yield 'http://127.0.0.1:' + environment['STREAM_HTTP_PORT'], '/tmp/l12-examples'
    finally:
        run([*compose, 'down', '--volumes', '--remove-orphans'], environment)
        for resource in ('ps', 'volume'):
            command = [docker, resource, 'ls' if resource == 'volume' else '-a', '-q', '--filter',
                       'label=com.docker.compose.project=' + project]
            assert not run(command, environment).strip(), 'Owned template resources survived cleanup'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-bundle', type=Path, required=True)
    parser.add_argument('--server-package', type=Path, required=True)
    parser.add_argument('--examples', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle, package, examples = (p.resolve() for p in (args.windows_bundle, args.server_package, args.examples))
    version = verify_delivery(bundle)['server_version']
    metadata = json.loads((examples / 'manifest.json').read_text())
    assert metadata['source_sha256'] == SOURCES
    for name in ARCHIVES.values():
        assert digest(examples / name) == metadata['files'][name]
    assert not args.output.exists(), 'Choose a new acceptance report path'
    result = dict(stream=version, examples=metadata)
    with tempfile.TemporaryDirectory(prefix='l12-template-acceptance-', dir=ROOT / '.tmp') as temporary:
        directory = Path(temporary)
        environment = dict(os.environ, RECOVERY_TEST_PASSWORD=secrets.token_urlsafe(24),
                           TACTIC_QML_TEST_SETTINGS_DIR=str(directory / 'handler-profile'))
        for key in ('TACTIC_DATA_DIR', 'TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS'):
            environment.pop(key, None)
        os.environ['TACTIC_QML_TEST_SETTINGS_DIR'] = environment['TACTIC_QML_TEST_SETTINGS_DIR']
        python, handler = bundle / 'runtime/python.exe', bundle / 'TACTIC-Handler'
        profile = directory / 'sqlite-profile'
        run([python, '-I', '-B', bundle / 'resources/app/desktop.py', profile / 'server', free_port()], environment)
        init = "import getpass,os,runpy,sys;getpass.getpass=lambda _:os.environ['RECOVERY_TEST_PASSWORD'];sys.argv=['tactic-stream','--data-dir',sys.argv[1],'init'];runpy.run_module('tactic_stream',run_name='__main__')"
        run([python, '-I', '-B', '-c', init, profile / 'server'], environment)
        nonce = secrets.token_hex(6)
        with server(python, profile, environment, version) as address:
            result['sqlite'] = check(address, handler, environment['RECOVERY_TEST_PASSWORD'], examples,
                                     examples.as_posix(), directory, nonce)
            result['sqlite_browser'] = browser_check(address, result['sqlite'], bundle,
                args.output.parent / (args.output.stem + '-sqlite-browser'), environment)
            result['sqlite_native'] = native_check(address, result['sqlite'], bundle,
                args.output.parent / (args.output.stem + '-sqlite-native'), environment)
        print('SQLite template operations and ordinary-user ACL: passed', flush=True)
        with postgres(package, examples, directory, environment, nonce) as (address, remote):
            result['postgres'] = check(address, handler, environment['RECOVERY_TEST_PASSWORD'], examples,
                                       remote, directory, nonce)
            result['postgres_browser'] = browser_check(address, result['postgres'], bundle,
                args.output.parent / (args.output.stem + '-postgres-browser'), environment)
            result['postgres_native'] = native_check(address, result['postgres'], bundle,
                args.output.parent / (args.output.stem + '-postgres-native'), environment)
        print('PostgreSQL/Apache template operations and ordinary-user ACL: passed', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result['browser_gui_tested'] = True
    result['native_gui_tested'] = 'Qt offscreen/software with real login, navigation and RPC'
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
