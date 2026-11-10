"""Exercise the actual compiled installer on disposable Windows installations."""
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.file_project_delivery import ROOT
from tools.handler_windows import installer, launchers


@unittest.skipUnless(os.name == 'nt', 'Windows executable packaging')
class HandlerWindows(unittest.TestCase):
    def test_installer_extracts_preserves_state_and_refuses_modified_application(self):
        handler = ROOT.parent.parent / 'TH'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'payload'
            bundle.mkdir()
            launchers(handler, bundle)
            self.assertTrue(all(path.read_bytes().startswith(b'MZ') for path in bundle.glob('*.exe')))
            (bundle / 'BUILD.json').write_text('{"fixture":true}')
            (bundle / 'TACTIC-Handler').mkdir()
            source = bundle / 'TACTIC-Handler/launch.py'
            source.write_text('# public application')
            (bundle / 'SHA256SUMS').write_text(''.join(
                sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(bundle).as_posix() + '\n'
                for path in sorted(bundle.rglob('*')) if path.is_file()))
            setup = installer(handler, bundle, root / 'setup.exe')
            target = root / 'Установка с пробелами'
            script = root / 'extract.ps1'
            script.write_text("$ErrorActionPreference = 'Stop'\n"
                "$assembly = [Reflection.Assembly]::LoadFile($env:TH_TEST_INSTALLER)\n"
                "$method = $assembly.GetType('Installer').GetMethod('Extract', [Reflection.BindingFlags]'NonPublic,Static')\n"
                "$null = $method.Invoke($null, @($env:TH_TEST_DESTINATION))\n", encoding='utf-8')
            def extract():
                return subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                    env={**os.environ, 'TH_TEST_INSTALLER': str(setup), 'TH_TEST_DESTINATION': str(target)},
                    capture_output=True, text=True, encoding='oem', timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            first = extract()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual((target / 'TACTIC-Handler/launch.py').read_bytes(), source.read_bytes())
            self.assertEqual((target / 'setup-template.bin').read_bytes(), setup.read_bytes())
            settings = target / 'TACTIC-Handler/settings'
            settings.mkdir()
            (settings / 'profile.json').write_text('retained workstation state')
            second = extract()
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual((settings / 'profile.json').read_text(), 'retained workstation state')
            self.assertEqual(len(list(root.glob(target.name + '.previous-*'))), 1)
            (target / 'TACTIC-Handler/launch.py').write_text('# local application change')
            self.assertNotEqual(extract().returncode, 0)
            self.assertEqual((target / 'TACTIC-Handler/launch.py').read_text(), '# local application change')
            self.assertEqual((settings / 'profile.json').read_text(), 'retained workstation state')
            self.assertFalse(list(root.glob(target.name + '.staging-*')))
