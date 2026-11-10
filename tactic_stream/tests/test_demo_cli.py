"""Exercise noninteractive first-run initialization in an isolated process."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.demo_delivery import build
from tools.file_project_delivery import ROOT


class DemoCLI(unittest.TestCase):
    def test_secret_file_first_run_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = build(root / 'demo')
            secret = root / 'password'
            secret.write_text('unique-test-administrator\n', encoding='utf-8')
            environment = {key: value for key, value in os.environ.items()
                           if key not in ('TACTIC_DATA_DIR', 'TACTIC_CONFIG_PATH')}
            environment['PYTHONPATH'] = str(ROOT / 'src')
            command = [sys.executable, '-B', '-X', 'utf8', '-m', 'tactic_stream',
                       '--data-dir', str(root / 'data'), 'init', '--demo', str(content),
                       '--password-file', str(secret)]
            result = subprocess.run(command, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn(secret.read_text().strip(), result.stdout + result.stderr)
            accounts = root / 'data/demo-accounts.json'
            before = accounts.read_bytes()
            self.assertEqual(len(json.loads(before)), 3)
            secret.unlink()
            result = subprocess.run([*command, '--if-needed'], env=environment,
                                    capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(accounts.read_bytes(), before)
            secret.write_text('', encoding='utf-8')
            command[command.index(str(root / 'data'))] = str(root / 'empty')
            result = subprocess.run(command, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('non-empty password', result.stderr)
            self.assertFalse((root / 'empty/db/sthpw.db').exists())
