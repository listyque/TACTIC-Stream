"""The desktop keeps user data independent of the disposable program directory."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import zipfile

from tools.file_project_delivery import ROOT
from tools.windows_delivery import extract, runtime

spec = importlib.util.spec_from_file_location('desktop', ROOT / 'deploy/windows/desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class WindowsDelivery(unittest.TestCase):
    def test_configuration_survives_relaunch_with_another_candidate_port(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            data = Path(directory) / 'данные с пробелами'
            first = desktop.describe(data, 19281)
            self.assertFalse(first['initialized'])
            self.assertEqual(first['port'], 19281)
            config = data / 'config/tactic-conf.xml'
            before = config.read_bytes()
            self.assertIn(b'127.0.0.1', before)
            xml = ET.fromstring(before)
            self.assertEqual(xml.find('./checkin/win32_local_base_dir').text, (data / 'local').as_posix())
            self.assertEqual(xml.find('./checkin/win32_sandbox_dir').text, (data / 'sandbox').as_posix())
            self.assertEqual(desktop.describe(data, 19282)['port'], 19281)
            self.assertEqual(config.read_bytes(), before)

    def test_existing_database_without_config_and_invalid_port_are_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            root = Path(directory)
            (root / 'db').mkdir()
            (root / 'db/sthpw.db').write_bytes(b'existing database')
            with self.assertRaises(FileExistsError):
                desktop.describe(root, 19281)
            with self.assertRaises(ValueError):
                desktop.describe(root, 0)
            self.assertEqual((root / 'db/sthpw.db').read_bytes(), b'existing database')
            self.assertFalse((root / 'config').exists())

    def test_corrupt_runtime_and_archive_traversal_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runtime.zip').write_bytes(b'corrupt download')
            with patch('tools.windows_delivery.RUNTIMES', {'test': ('1', 'https://invalid/runtime.zip', 'wrong')}):
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    runtime('test', root)
            archive = root / 'traversal.zip'
            with zipfile.ZipFile(archive, 'w') as source:
                source.writestr('../outside.txt', 'bad')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                extract(archive, root / 'app')
            self.assertFalse((root / 'outside.txt').exists())
