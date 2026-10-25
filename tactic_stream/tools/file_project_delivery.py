"""Build a source delivery with a server wheel, Handler runtime and SHA-256 inventory."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def handler_archive(handler, target):
    # Explicit roots exclude saved presets, tickets, user scripts, databases and logs.
    roots = ('thlib', 'handler_server', 'tactic_handler_api', 'tactic_handler_dcc', 'side_tools/frame_tool',
             'launch.py', 'launch.pyw', 'execute_after_start.py', 'requirements.txt', 'LICENSE', 'README.md',
             'CHANGELOG.md', 'docs')
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in roots:
            source = handler / name
            if not source.exists():
                raise FileNotFoundError(source)
            for path in sorted(source.rglob('*')) if source.is_dir() else [source]:
                if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(handler.resolve()):
                    raise ValueError('Runtime source escapes application root')
                archive.write(path, 'TACTIC-Handler/' + path.relative_to(handler).as_posix())


def release_version():
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    frontend = json.loads((ROOT / 'frontend/package.json').read_text())['version']
    lock = json.loads((ROOT / 'frontend/package-lock.json').read_text())
    assert version == frontend == lock['version'] == lock['packages']['']['version']
    assert re.search(r'__version__ = "' + re.escape(version) + r'"', (ROOT / 'src/tactic_stream/__init__.py').read_text())
    return version


def build(handler, output, evidence=None):
    version = release_version()
    assert (ROOT / 'src/tactic_client_lib/file_transfer.py').read_bytes() == (handler / 'thlib/side/client/tactic_client_lib/file_transfer.py').read_bytes()
    assert (ROOT / 'src/tactic_client_lib/file_workspace.py').read_bytes() == (handler / 'thlib/side/client/tactic_client_lib/file_workspace.py').read_bytes()
    handler_version = '.'.join(json.loads((handler / 'thlib/version.json').read_text())[key] for key in ('major', 'minor', 'build', 'revision'))
    output.mkdir(parents=True, exist_ok=False)
    # Build a fresh snapshot so stale/shared build output cannot enter the delivery.
    with tempfile.TemporaryDirectory(prefix='file-delivery-build-') as temporary:
        source = Path(temporary)
        shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ('pyproject.toml', 'README.md', 'LICENSE.TACTIC', 'LICENSE.HANDLER', 'LICENSE.QUICKJS-NG'):
            shutil.copyfile(ROOT / name, source / name)
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                        '--wheel-dir', str(output), str(source)], check=True, timeout=180)
    wheel, = output.glob('*.whl')
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        for name in ('tactic/command/file_project_cmd.py', 'tactic/command/project_template_cmd.py',
                     'tactic_client_lib/file_transfer.py', 'tactic_stream/web/index.html',
                     'tactic_stream/web/help/project_creation.en.md', 'tactic_stream/web/help/project_creation.ru.md'):
            assert name in names, name
    handler_archive(handler, output / ('tactic-handler-' + handler_version + '-source.zip'))
    for name in ('FILE_PROJECT_DELIVERY.en.md', 'FILE_PROJECT_DELIVERY.ru.md', 'FILE_WORKSPACE_SCOPE.md', 'FILE_WORKSPACE_ACCEPTANCE.md', 'HANDLER_DEPLOYMENT.md', 'SERVER_DELIVERY.en.md', 'SERVER_DELIVERY.ru.md', 'WINDOWS_DELIVERY.en.md', 'WINDOWS_DELIVERY.ru.md', 'RECOVERY_ACCEPTANCE.md',
                 'LICENSE.TACTIC', 'LICENSE.HANDLER', 'LICENSE.QUICKJS-NG'):
        source = ROOT / 'docs/delivery' / name if name.endswith('.md') else ROOT / name
        shutil.copyfile(source, output / name)
    verification = output / 'verification'
    verification.mkdir()
    (verification / 'tools').mkdir()
    (verification / 'tests').mkdir()
    for name in ('file_project_checks.py', 'file_transfer_benchmark.py', 'file_project_scale.py', 'file_project_delivery.py', 'file_project_install_checks.py', 'file_workspace_platform_checks.py'):
        shutil.copyfile(ROOT / 'tools' / name, verification / 'tools' / name)
    for name in ('test_file_project.py', 'test_file_project_resilience.py', 'test_file_change.py',
                 'test_file_workspace.py', 'test_file_transfer.py', 'test_file_catalog.py', 'test_file_delivery.py'):
        shutil.copyfile(ROOT / 'tests' / name, verification / 'tests' / name)
    for name in ('test_monitor.py', 'monitor_runtime.py'):
        shutil.copyfile(ROOT / 'tests' / name, verification / 'tests' / name)
    (verification / 'tests/scripts').mkdir()
    shutil.copyfile(ROOT / 'tests/scripts/file_project_crash.py', verification / 'tests/scripts/file_project_crash.py')
    if evidence:
        shutil.copytree(evidence, output / 'qualification')
    inventory = []
    for path in sorted(output.rglob('*')):
        if path.is_file():
            digest = sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
            inventory.append({'path': path.relative_to(output).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()})
    manifest = {'server_version': version, 'handler_version': handler_version,
                'format': 'server-wheel-and-handler-source', 'production_accepted': False, 'files': inventory}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'server_version': version, 'handler_version': handler_version, 'files': len(inventory), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing deliveries are never overwritten')
    parser.add_argument('--evidence', type=Path, help='Public qualification artifacts; never pass raw logs or saved client settings')
    args = parser.parse_args()
    build(args.handler.resolve(), args.output.resolve(), args.evidence.resolve() if args.evidence else None)
