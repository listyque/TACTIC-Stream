"""The source delivery must not contain workstation data or omit its launchers."""
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.file_project_delivery import handler_archive


class FileDeliveryTest(unittest.TestCase):
    def test_runtime_allowlist_keeps_launchers_and_excludes_private_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('thlib', 'handler_server', 'tactic_handler_api', 'tactic_handler_dcc', 'docs', 'side_tools/frame_tool'):
                (root / folder).mkdir(parents=True)
                (root / folder / 'module.py').write_text('pass')
            (root / 'thlib/__pycache__').mkdir()
            (root / 'thlib/__pycache__/cached.pyc').write_bytes(b'cache')
            for name in ('launch.py', 'launch.pyw', 'execute_after_start.py', 'requirements.txt', 'LICENSE', 'README.md', 'CHANGELOG.md'):
                (root / name).write_text('public runtime')
            for folder in ('settings', 'log', 'custom_scripts'):
                (root / folder).mkdir()
                (root / folder / 'private.json').write_text('private saved credentials or user data')
            target = root / 'runtime.zip'
            handler_archive(root, target)
            with zipfile.ZipFile(target) as archive:
                names = archive.namelist()
                self.assertIn('TACTIC-Handler/launch.py', names)
                self.assertIn('TACTIC-Handler/thlib/module.py', names)
                self.assertIn('TACTIC-Handler/side_tools/frame_tool/module.py', names)
                self.assertFalse(any('private' in name or '__pycache__' in name for name in names))
            with self.assertRaises(FileExistsError):
                handler_archive(root, target)
