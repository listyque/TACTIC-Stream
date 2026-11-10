"""Export versioned Docker images and an independent PostgreSQL/Apache package."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

from tools.file_project_delivery import ROOT, release_version
from tools.demo_delivery import build as build_demo


def release_compose(config, version, demo=False):
    config['name'] = 'tactic-stream-demo' if demo else 'tactic-stream-server'
    for name, service in config['services'].items():
        service.pop('build', None)
        if name in ('app', 'apache'):
            service['image'] = 'tactic-stream-server-' + name + ':' + version
        if name == 'app':
            service['environment'].pop('PYTHONPATH', None)
            service['volumes'] = [mount for mount in service['volumes']
                                  if mount['target'] not in ('/opt/stream-src', '/opt/python-packages')]
            service['depends_on'] = {'postgres': {'condition': 'service_healthy'}}
        if name == 'postgres':
            # Native bootstrap creates sthpw itself and refuses an existing database.
            service['environment']['POSTGRES_DB'] = 'postgres'
            service['healthcheck']['test'] = ['CMD', 'pg_isready', '-U', 'stream', '-d', 'postgres']
        assert all(mount['type'] == 'volume' for mount in service.get('volumes', []))
    config['volumes'].pop('python_packages', None)
    for resources in ('volumes', 'networks'):
        for resource in config.get(resources, {}).values():
            resource.pop('name', None)
    for name, secret in config['secrets'].items():
        secret.pop('name', None)
        secret['file'] = '.local/' + name.replace('_', '-')
    if demo:
        config['services']['app']['volumes'].append(dict(type='bind', source='./demo', target='/opt/tactic-demo', read_only=True))
    return config


def build(output, demo=False):
    version = release_version()
    output.mkdir(parents=True, exist_ok=False)
    deployment = ROOT / 'deploy/docker'
    docker = shutil.which('docker')
    if not docker:
        raise FileNotFoundError('Docker must be available on PATH')
    result = subprocess.run([docker, 'compose', '--project-name', 'tactic-stream-server',
                             '-f', str(deployment / 'compose.yaml'), 'config', '--format', 'json',
                             '--no-interpolate', '--no-path-resolution'],
                            check=True, capture_output=True, text=True, encoding='utf-8')
    config = release_compose(json.loads(result.stdout), version, demo)
    (output / 'compose.yaml').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    if demo:
        build_demo(output / 'demo')
    for name in ('app', 'apache'):
        subprocess.run([docker, 'build', '--target', name, '-t', config['services'][name]['image'],
                        '-f', str(deployment / 'Dockerfile'), str(ROOT)], check=True)
    subprocess.run([docker, 'pull', config['services']['postgres']['image']], check=True)
    images = [service['image'] for service in config['services'].values()]
    metadata = subprocess.run([docker, 'image', 'inspect', *images], check=True,
                              capture_output=True, text=True, encoding='utf-8')
    image_ids = {item['Id']: item['RepoTags'] for item in json.loads(metadata.stdout)}
    subprocess.run([docker, 'image', 'save', '-o', str(output / 'images.tar'), *images], check=True)
    for name in ('manage.py', 'apache.conf', 'check.py', 'init-postgres.py'):
        shutil.copyfile(deployment / name, output / name)
    for language in ('en', 'ru'):
        shutil.copyfile(ROOT / 'docs/delivery' / ('SERVER_DELIVERY.' + language + '.md'), output / ('README.' + language + '.md'))
    shutil.copyfile(ROOT / 'docs/delivery/RECOVERY_ACCEPTANCE.md', output / 'RECOVERY_ACCEPTANCE.md')
    for path in ROOT.glob('LICENSE*'):
        if path.is_file():
            shutil.copyfile(path, output / path.name)
    inventory = []
    for path in sorted(output.rglob('*')):
        if not path.is_file():
            continue
        digest = sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        inventory.append(dict(path=path.relative_to(output).as_posix(), bytes=path.stat().st_size, sha256=digest.hexdigest()))
    manifest = dict(format='tactic-stream-server', version=version, demo=demo, images=image_ids,
                    production_accepted=False, files=inventory)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(version=version, output=str(output), images=len(images))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing packages are never overwritten')
    parser.add_argument('--demo', action='store_true', help='Include fictional projects for explicit first initialization')
    args = parser.parse_args()
    build(args.output.resolve(), args.demo)
