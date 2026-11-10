"""Export the portable Windows x64 desktop with isolated Python and native Handler."""
import argparse
from hashlib import file_digest
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import tempfile
import tomllib
import urllib.request
import zipfile

from tools.file_project_delivery import ROOT, build as build_source, release_version
from tools.demo_delivery import build as build_demo
from tools.handler_windows import launchers, installer

RUNTIMES = {
    'python': ('3.14.9', 'https://www.python.org/ftp/python/3.14.9/python-3.14.9-embed-amd64.zip',
               '3c01d7cfc666f746a6f064f60fb2156ab0ec464d3d738ab796371a46a9bb24a2'),
    'electron': ('44.9.3', 'https://github.com/electron/electron/releases/download/v44.9.3/electron-v44.9.3-win32-x64.zip',
                 '41a1ffa0541cb0f2c9b9fe920dd2cef1793ad0ea2ada1a9582958880f4d1b23c'),
}


def digest(path):
    with path.open('rb') as source:
        return file_digest(source, 'sha256').hexdigest()


def extract(archive, target):
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            if not (target / member.filename).resolve().is_relative_to(target.resolve()):
                raise ValueError('Archive member escapes delivery: ' + member.filename)
        source.extractall(target)


def runtime(name, cache):
    _, url, expected = RUNTIMES[name]
    target = cache / url.rsplit('/', 1)[1]
    if not target.exists():
        partial = target.with_suffix('.download')
        urllib.request.urlretrieve(url, partial)
        if digest(partial) != expected:
            raise ValueError('Runtime checksum mismatch: ' + name)
        partial.replace(target)
    if digest(target) != expected:
        raise ValueError('Runtime checksum mismatch: ' + name)
    return target


def build(handler, output, edition='suite', demo=False):
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 14) or struct.calcsize('P') != 8:
        raise RuntimeError('Build on Windows x64 with Python 3.14')
    zip_path = output.parent / (output.name + '.zip')
    if output.exists() or zip_path.exists():
        raise FileExistsError(output)
    version = release_version()
    if edition not in ('handler', 'stream', 'suite'):
        raise ValueError('Choose handler, stream or suite')
    include_handler = edition != 'stream'
    include_server = edition != 'handler' or demo
    cache = ROOT / '.tmp/windows-runtime'
    cache.mkdir(parents=True, exist_ok=True)
    archives = {name: runtime(name, cache) for name in ('python', 'electron') if name == 'python' or include_server}
    qt = next(line.strip() for line in (handler / 'requirements.txt').read_text().splitlines() if line.startswith('PySide6=='))
    wheels = cache / 'wheels'
    dependencies = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['dependencies'] if include_server else []
    subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'download', '--index-url', 'https://pypi.org/simple',
                    '--only-binary=:all:', '--dest', str(wheels), *dependencies, *([qt] if include_handler else [])], check=True, timeout=600)
    with tempfile.TemporaryDirectory(prefix='windows-delivery-') as temporary:
        source = Path(temporary) / 'source'
        build_source(handler, source)
        source_manifest = json.loads((source / 'manifest.json').read_text())
        output.mkdir(parents=True)
        if include_server:
            extract(archives['electron'], output)
            (output / 'electron.exe').rename(output / 'TACTIC Stream.exe')
            (output / 'resources/default_app.asar').unlink()
        extract(archives['python'], output / 'runtime')
        (output / 'runtime/python314._pth').write_text('python314.zip\n.\nLib/site-packages\n' +
            ('../TACTIC-Handler\n' if include_handler else ''), encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install', '--no-index', '--no-compile',
                        '--target', str(output / 'runtime/Lib/site-packages'), '--find-links', str(wheels),
                        *([str(next(source.glob('*.whl')))] if include_server else []),
                        *([qt] if include_handler else [])], check=True, timeout=300)
        for metadata in (output / 'runtime/Lib/site-packages').glob('*.dist-info/direct_url.json'):
            metadata.unlink()
        scripts = output / 'runtime/Lib/site-packages/bin'
        if scripts.exists():
            assert scripts.resolve().is_relative_to(output)
            shutil.rmtree(scripts)  # Generated entry points contain the build interpreter's absolute path.
        if include_handler:
            extract(next(source.glob('tactic-handler-*-source.zip')), output)
    if include_server:
        app = output / 'resources/app'
        app.mkdir()
        (app / 'package.json').write_text(json.dumps(dict(name='tactic-stream', productName='TACTIC Stream',
            version=version, main='main.cjs'), indent=2) + '\n', encoding='utf-8')
        for name in ('main.cjs', 'desktop.py'):
            shutil.copyfile(ROOT / 'deploy/windows' / name, app / name)
        shutil.copyfile(ROOT / 'src/tactic_stream/shared_ui/core/strings.mjs', app / 'strings.mjs')
    if include_handler:
        launchers(handler, output)
        shutil.copyfile(ROOT / 'deploy/windows/Handler.cmd', output / 'Handler.cmd')
    if demo:
        build_demo(output / 'demo')
    for name in ('WINDOWS_DELIVERY.en.md', 'WINDOWS_DELIVERY.ru.md', 'RECOVERY_ACCEPTANCE.md',
                 'LICENSE.TACTIC', 'LICENSE.HANDLER', 'LICENSE.QUICKJS-NG'):
        source = ROOT / 'docs/delivery' / name if name.endswith('.md') else ROOT / name
        shutil.copyfile(source, output / name)
    python = output / 'runtime/python.exe'
    probe = subprocess.run([str(python), '-I', '-B', '-X', 'utf8', '-c',
        'import json,sys; from importlib.metadata import distributions; '
        'stream=__import__("tactic_stream").__version__ if ' + repr(include_server) + ' else None; '
        'qt=__import__("PySide6").__version__ if ' + repr(include_handler) + ' else None; '
        'print(json.dumps(dict(python=sys.version.split()[0],stream=stream,qt=qt,'
        'path=sys.path,dependencies={d.metadata["Name"]: d.version for d in distributions()})))'],
        cwd=output, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONHOME': 'invalid-python-home'},
        check=True, capture_output=True, text=True, timeout=30)
    installed = json.loads(probe.stdout)
    assert installed['python'] == RUNTIMES['python'][0]
    if include_server:
        assert installed['stream'] == installed['dependencies']['tactic-stream'] == version
    if include_handler:
        assert installed['qt'] == qt.partition('==')[2]
    assert all(Path(item).is_relative_to(output) for item in installed['path'])
    build_info = dict(edition=edition, demo=demo, server_version=version if include_server else None,
        handler_version=source_manifest['handler_version'] if include_handler else None)
    (output / 'BUILD.json').write_text(json.dumps(build_info, indent=2) + '\n', encoding='utf-8')
    manifest = dict(format='tactic-stream-windows-x64', **build_info, python_version=installed['python'],
        electron_version=RUNTIMES['electron'][0] if include_server else None, dependencies=installed['dependencies'], production_accepted=False,
        files=[dict(path=path.relative_to(output).as_posix(), bytes=path.stat().st_size, sha256=digest(path))
               for path in sorted(output.rglob('*')) if path.is_file()])
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'SHA256SUMS').write_text(''.join(item['sha256'] + '  ' + item['path'] + '\n' for item in manifest['files'])
        + digest(output / 'manifest.json') + '  manifest.json\n', encoding='utf-8')
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                archive.write(path, output.name + '/' + path.relative_to(output).as_posix())
    if edition == 'handler':
        installer(handler, output, output.with_name(output.name + '-Setup.exe'))
    print(json.dumps(dict(output=str(output), files=len(manifest['files']), server_version=version,
                          handler_version=manifest['handler_version'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--edition', choices=('handler', 'stream', 'suite'), default='suite')
    parser.add_argument('--demo', action='store_true', help='Include fictional projects for first initialization only')
    args = parser.parse_args()
    build(args.handler.resolve(), args.output.resolve(), args.edition, args.demo)
