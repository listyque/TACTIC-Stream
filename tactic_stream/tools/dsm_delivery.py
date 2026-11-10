"""Package a verified server delivery for DSM's native Docker Project Worker."""
import argparse
import copy
import gzip
from hashlib import file_digest
import io
import json
from pathlib import Path
import tarfile
import tempfile

from tools.file_project_delivery import ROOT, release_version


def digest(path, algorithm='sha256'):
    with path.open('rb') as source:
        return file_digest(source, algorithm).hexdigest()


def dsm_compose(config, demo):
    config = copy.deepcopy(config)
    config['name'] = 'tactic-stream-dsm' + ('-demo' if demo else '')
    services = config['services']
    app = services['app']
    app['user'] = '10001:10001'
    app['volumes'] = [dict(type='bind', source='./state/data/stream', target='/var/lib/tactic_stream')]
    app['depends_on']['initialize'] = dict(condition='service_completed_successfully')
    services['postgres']['user'] = '0:0'
    services['postgres']['volumes'] = [dict(type='bind', source='./state/data/postgres', target='/var/lib/postgresql')]
    services['apache']['user'] = '0:0'
    services['apache']['ports'] = [dict(target=80, published='__STREAM_PORT__', protocol='tcp')]
    # Docker populates these configuration volumes from the image on first start.
    config['volumes'] = {name: value for name, value in config['volumes'].items()
                         if name in ('apache_config', 'webmin_config')}
    config['secrets'] = {name: dict(file='./state/secrets/' + name)
                         for name in ('postgres_password', 'webmin_password', 'admin_password')}
    initialize = dict(image=app['image'], user='0:0', restart='no',
        command=['python', '-B', '/bootstrap/bootstrap.py'],
        environment={'TACTIC_DATA_DIR': '/var/lib/tactic_stream'},
        volumes=[*copy.deepcopy(app['volumes']), dict(type='bind', source='../bootstrap', target='/bootstrap', read_only=True)],
        secrets=['postgres_password', 'admin_password'],
        depends_on={'postgres': dict(condition='service_healthy')}, logging=copy.deepcopy(app['logging']))
    if demo:
        initialize['volumes'].append(dict(type='bind', source='../demo', target='/opt/tactic-demo', read_only=True))
    services['initialize'] = initialize
    return config


def add(archive, name, value, executable=False):
    info = tarfile.TarInfo(name)
    info.mode = 0o755 if executable else 0o644
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = 'root'
    if isinstance(value, bytes):
        info.size = len(value)
        archive.addfile(info, io.BytesIO(value))
    else:
        if value.is_symlink():
            raise ValueError('Linked SPK input: ' + str(value))
        info.size = value.stat().st_size
        with value.open('rb') as source:
            archive.addfile(info, source)


def build(server, target):
    if target.exists():
        raise FileExistsError(target)
    manifest = json.loads((server / 'manifest.json').read_text(encoding='utf-8'))
    version = release_version()
    if manifest['format'] != 'tactic-stream-server' or manifest['version'] != version:
        raise ValueError('DSM and server delivery versions must agree')
    for item in manifest['files']:
        path = server / item['path']
        if not path.resolve().is_relative_to(server.resolve()) or path.is_symlink():
            raise ValueError('Invalid server package path')
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('Server package checksum mismatch: ' + item['path'])
    demo = manifest['demo']
    package = 'TacticStreamDemo' if demo else 'TacticStream'
    port = '8884' if demo else '8882'
    title = 'TACTIC Stream' + (' Demo' if demo else '')
    config = dsm_compose(json.loads((server / 'compose.yaml').read_text()), demo)
    dsm = ROOT / 'deploy/dsm'
    with tempfile.TemporaryDirectory(prefix='stream-dsm-') as temporary:
        stage = Path(temporary)
        entries = [('images/stream-images.tar', server / 'images.tar'),
            ('project/compose.template', (json.dumps(config, indent=2) + '\n').encode()),
            ('bootstrap/bootstrap.py', dsm / 'bootstrap.py'),
            ('bootstrap/init-postgres.py', ROOT / 'deploy/docker/init-postgres.py'),
            ('bootstrap/release.json', json.dumps(dict(version=version, demo=demo)).encode())]
        if demo:
            entries += [('demo/' + p.relative_to(server / 'demo').as_posix(), p)
                        for p in sorted((server / 'demo').rglob('*')) if p.is_file()]
        for language in ('en', 'ru'):
            entries.append(('README.' + language + '.md', ROOT / ('docs/delivery/DSM_DELIVERY.' + language + '.md')))
        for path in ROOT.glob('LICENSE*'):
            entries.append((path.name, path))
        ui = {'.url': {'com.tactic.' + package: dict(type='url', title=title,
            desc='Projects, files and workflows', icon='images/stream-{0}.png',
            protocol='http', port='__STREAM_PORT__', url='/', allUsers=False)}}
        entries.append(('ui/config.template', json.dumps(ui, ensure_ascii=False).encode()))
        from PIL import Image
        with Image.open(ROOT / 'frontend/public/assets/stream-logo.png') as original:
            for size in (16, 24, 32, 48, 64, 72, 256):
                path = stage / ('icon-' + str(size) + '.png')
                original.resize((size, size), Image.Resampling.LANCZOS).save(path)
                entries.append(('ui/images/stream-' + str(size) + '.png', path))
        from hashlib import sha256
        checksums = ''.join((sha256(value).hexdigest() if isinstance(value, bytes) else digest(value))
                            + '  ' + name + '\n' for name, value in entries)
        entries.append(('SHA256SUMS', checksums.encode()))
        payload = stage / 'package.tgz'
        with payload.open('wb') as output, gzip.GzipFile(fileobj=output, mode='wb', compresslevel=6, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.GNU_FORMAT) as archive:
                for name, value in entries:
                    add(archive, name, value)
        info = dict(package=package, displayname=title, version=version + '-1',
            os_min_ver='7.2.1-69057', arch='x86_64', maintainer='listyque',
            description='Preview: projects, files and workflows with PostgreSQL. ' +
                ('Includes fictional demonstration projects.' if demo else 'Starts with no business projects.'),
            install_dep_packages='ContainerManager>=20.10.23-1437', dsmuidir='ui', dsmappname='com.tactic.' + package,
            checkport='no', ctl_stop='yes', silent_install='no', silent_upgrade='no', silent_uninstall='yes',
            extractsize=str((sum(len(v) if isinstance(v, bytes) else v.stat().st_size for _, v in entries) + 1023) // 1024),
            beta='yes', checksum=digest(payload, 'md5'))
        resource = {'docker-project': {'preload-image': 'images/stream-images.tar', 'projects': [
            dict(name=config['name'], path='project', build_params=dict(build=False, force_pull=False, force_recreate=True))]}}
        wizard = json.loads((dsm / 'install_uifile').read_text(encoding='utf-8').replace('__PORT__', port).replace('__TITLE__', title))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output, tarfile.open(fileobj=output, mode='w', format=tarfile.GNU_FORMAT) as archive:
            add(archive, 'INFO', ''.join(key + '=' + json.dumps(value) + '\n' for key, value in info.items()).encode())
            add(archive, 'package.tgz', payload)
            add(archive, 'conf/resource', json.dumps(resource).encode())
            add(archive, 'conf/privilege', b'{"defaults":{"run-as":"package"}}')
            add(archive, 'WIZARD_UIFILES/install_uifile', json.dumps(wizard, ensure_ascii=False).encode())
            for path in sorted((dsm / 'scripts').iterdir()):
                content = path.read_text(encoding='utf-8').replace('__PACKAGE__', package).replace('__PORT__', port)
                add(archive, 'scripts/' + path.name, content.encode(), executable=True)
            for name in ('postupgrade', 'preuninst', 'postuninst'):
                add(archive, 'scripts/' + name, b'#!/bin/sh\nexit 0\n', executable=True)
            add(archive, 'LICENSE', ROOT / 'LICENSE.TACTIC')
            add(archive, 'PACKAGE_ICON.PNG', stage / 'icon-64.png')
            add(archive, 'PACKAGE_ICON_256.PNG', stage / 'icon-256.png')
    target.with_suffix('.spk.sha256').write_text(digest(target) + '  ' + target.name + '\n', encoding='utf-8')
    print(json.dumps(dict(path=str(target), bytes=target.stat().st_size, demo=demo, dsm_device_tested=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True, help='Verified Docker delivery directory')
    parser.add_argument('--output', type=Path, required=True, help='New .spk file')
    args = parser.parse_args()
    build(args.server.resolve(), args.output.resolve())
