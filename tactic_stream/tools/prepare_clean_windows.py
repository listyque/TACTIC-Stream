"""Prepare an offline Sandbox acceptance kit; never enables Windows features or launches UAC."""
import argparse
import json
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
import zipfile

from tools.file_project_delivery import ROOT
from tools.windows_delivery import digest


def prepare(archive, output):
    if output.exists():
        raise FileExistsError('Acceptance kit needs a new directory')
    with zipfile.ZipFile(archive) as source:
        manifests = [name for name in source.namelist() if len(name.split('/')) == 2 and name.endswith('/manifest.json')]
        manifest, = manifests
        metadata = json.loads(source.read(manifest))
        assert metadata['format'] == 'tactic-stream-windows-x64'
        assert not any('/TACTIC-Handler/settings/' in name for name in source.namelist())
        bundle = manifest.split('/')[0]
    inputs = output / 'input'
    inputs.mkdir(parents=True)
    results = output / 'results'
    results.mkdir()
    shutil.copyfile(archive, inputs / archive.name)
    for package in ('playwright', 'playwright-core'):
        shutil.copytree(ROOT / 'frontend/node_modules' / package, inputs / 'frontend/node_modules' / package)
    for source, target in (
        ('frontend/tests/windows_delivery.mjs', 'frontend/tests/windows_delivery.mjs'),
        ('tools/handler_deployment_check.py', 'tools/handler_deployment_check.py'),
        ('tests/scripts/windows_console_password.py', 'tests/scripts/windows_console_password.py'),
        ('tests/scripts/windows_package_probe.py', 'tests/scripts/windows_package_probe.py'),
        ('deploy/windows/check-clean-sandbox.ps1', 'run-check.ps1'),
    ):
        path = inputs / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, path)
    inventory = [dict(path=p.relative_to(inputs).as_posix(), sha256=digest(p))
                 for p in sorted(inputs.rglob('*')) if p.is_file()]
    (inputs / 'kit.json').write_text(json.dumps(dict(archive=archive.name, bundle=bundle,
        server_version=metadata['server_version'], files=inventory), indent=2) + '\n', encoding='utf-8')
    config = ET.Element('Configuration')
    for key, value in (('Networking', 'Disable'), ('VGpu', 'Disable'), ('MemoryInMB', '8192'),
                       ('ClipboardRedirection', 'Disable')):
        ET.SubElement(config, key).text = value
    mappings = ET.SubElement(config, 'MappedFolders')
    for path, target, readonly in ((inputs, r'C:\L12\Input', 'true'), (results, r'C:\L12\Results', 'false')):
        mapping = ET.SubElement(mappings, 'MappedFolder')
        ET.SubElement(mapping, 'HostFolder').text = str(path)
        ET.SubElement(mapping, 'SandboxFolder').text = target
        ET.SubElement(mapping, 'ReadOnly').text = readonly
    logon = ET.SubElement(config, 'LogonCommand')
    ET.SubElement(logon, 'Command').text = r'powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\L12\Input\run-check.ps1'
    ET.indent(config)
    (output / 'Check TACTIC Stream.wsb').write_text(ET.tostring(config, encoding='unicode') + '\n', encoding='utf-8')
    (output / 'README.txt').write_text(
        'Requires Windows Sandbox already enabled. This kit does not install components or reboot.\n'
        'Open "Check TACTIC Stream.wsb". The fresh guest has no network and sees only input (read-only) and results.\n'
        'Wait for results/result.json. A passed result is clean-Windows evidence; preparing the kit is not.\n'
        'Guest debug logs stay in C:\\L12\\Work. Closing Sandbox discards guest data.\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), version=metadata['server_version'], prepared=True,
                          clean_windows_verified=False, input_files=len(inventory))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.windows_archive.resolve(), args.output.resolve())
