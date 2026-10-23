"""Restoration validates private backup contents before writing a new target."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import zipfile

from tools.delivery_recovery_checks import cold_archive, restore_archive, relocate_config
from tools.prepare_clean_windows import prepare


class DeliveryRecovery(unittest.TestCase):
    def test_relocation_changes_only_internal_server_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, restored = root / 'old', root / 'restored'
            config = restored / 'server/config/tactic-conf.xml'
            config.parent.mkdir(parents=True)
            tree = ET.Element('config')
            checkin = ET.SubElement(tree, 'checkin')
            ET.SubElement(checkin, 'asset_base_dir').text = (old / 'server/assets').as_posix()
            ET.SubElement(checkin, 'win32_sandbox_dir').text = (root / 'external-sandbox').as_posix()
            ET.SubElement(checkin, 'win32_client_repo_dir').text = (old / 'client-owned').as_posix()
            config.write_text(ET.tostring(tree, encoding='unicode'), encoding='utf-8')
            relocate_config(restored, old)
            values = ET.parse(config)
            self.assertEqual(values.findtext('./checkin/asset_base_dir'), (restored / 'server/assets').as_posix())
            self.assertEqual(values.findtext('./checkin/win32_sandbox_dir'), (root / 'external-sandbox').as_posix())
            self.assertEqual(values.findtext('./checkin/win32_client_repo_dir'), (old / 'client-owned').as_posix())

    def test_sandbox_maps_only_kit_inputs_readonly_and_results_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / 'source'
            required = ('frontend/node_modules/playwright/LICENSE', 'frontend/node_modules/playwright-core/LICENSE',
                        'frontend/tests/windows_delivery.mjs', 'tools/handler_deployment_check.py',
                        'tests/scripts/windows_console_password.py', 'tests/scripts/windows_package_probe.py',
                        'deploy/windows/check-clean-sandbox.ps1')
            for name in required:
                path = sources / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('test fixture')
            archive = root / 'desktop.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('desktop/manifest.json', json.dumps(dict(format='tactic-stream-windows-x64', server_version='1.2.3')))
            target = root / 'kit & isolated'
            with patch('tools.prepare_clean_windows.ROOT', sources):
                prepare(archive, target)
                with self.assertRaises(FileExistsError):
                    prepare(archive, target)
            config = ET.parse(target / 'Check TACTIC Stream.wsb')
            self.assertEqual(config.findtext('Networking'), 'Disable')
            mappings = config.findall('./MappedFolders/MappedFolder')
            self.assertEqual([item.findtext('HostFolder') for item in mappings], [str(target / 'input'), str(target / 'results')])
            self.assertEqual([item.findtext('ReadOnly') for item in mappings], ['true', 'false'])
            self.assertFalse((target / 'results/result.json').exists(), 'Preparing a kit is not a passed VM check')

    def test_cold_copy_restores_config_unicode_files_and_native_profile_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / 'profile'
            for name, content in {'server/config/tactic-conf.xml': '<config/>',
                                  'server/assets/кадр с пробелом.bin': '\x00file bytes',
                                  'handler/settings/preset.json': '{"server":"test"}'}.items():
                path = profile / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            archive = root / 'backup.zip'
            self.assertEqual(cold_archive(profile, archive), 3)
            restored = root / 'restored'
            restore_archive(archive, restored)
            self.assertEqual({p.relative_to(profile): p.read_bytes() for p in profile.rglob('*') if p.is_file()},
                             {p.relative_to(restored): p.read_bytes() for p in restored.rglob('*') if p.is_file()})
            with self.assertRaises(FileExistsError):
                restore_archive(archive, restored)

    def test_corruption_and_unlisted_files_are_refused_before_any_restore_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, inventory, files in (
                ('corrupt', [{'path': 'database.db', 'bytes': 4, 'sha256': 'bad'}], {'database.db': 'data'}),
                ('unlisted', [], {'unlisted.txt': 'extra'}),
                ('escape', [{'path': '../outside', 'bytes': 1, 'sha256': 'bad'}], {'../outside': 'x'}),
            ):
                archive = root / (name + '.zip')
                with zipfile.ZipFile(archive, 'w') as output:
                    output.writestr('backup-manifest.json', json.dumps(dict(format='l12-cold-copy', files=inventory)))
                    for path, payload in files.items():
                        output.writestr(path, payload)
                target = root / name
                with self.assertRaises(ValueError):
                    restore_archive(archive, target)
                self.assertFalse(target.exists())
            self.assertFalse((root / 'outside').exists())
