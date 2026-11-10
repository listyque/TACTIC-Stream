"""DSM package boundaries and real lifecycle hooks on Linux, without a NAS."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from tools.dsm_delivery import build, dsm_compose
from tools.file_project_delivery import release_version


def compose():
    return dict(services={
        'app': dict(image='app:test', logging={'driver': 'json-file'}, depends_on={'postgres': {'condition': 'service_healthy'}}),
        'postgres': dict(image='postgres:18.6'),
        'apache': dict(image='apache:test', ports=[])},
        volumes={name: {} for name in ('stream_data', 'postgres_data', 'apache_config', 'webmin_config')})


class DSMDelivery(unittest.TestCase):
    def test_compose_owns_data_and_keeps_databases_private(self):
        for demo in (False, True):
            config = dsm_compose(compose(), demo)
            services = config['services']
            self.assertNotIn('ports', services['postgres'])
            self.assertNotIn('ports', services['app'])
            self.assertEqual([row['target'] for row in services['apache']['ports']], [80])
            self.assertEqual(services['app']['user'], '10001:10001')
            self.assertNotIn('admin_password', services['app'].get('secrets', []))
            self.assertEqual(services['app']['depends_on']['initialize']['condition'], 'service_completed_successfully')
            self.assertEqual(any(row['target'] == '/opt/tactic-demo' for row in services['initialize']['volumes']), demo)
            self.assertEqual(set(config['volumes']), {'apache_config', 'webmin_config'})

    def test_spk_checksums_and_linux_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = root / 'server'
            server.mkdir()
            (server / 'compose.yaml').write_text(json.dumps(compose()))
            (server / 'images.tar').write_bytes(b'isolated image fixture')
            manifest = dict(format='tactic-stream-server', version=release_version(), demo=False,
                files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p.read_bytes()).hexdigest()) for p in server.iterdir()])
            (server / 'manifest.json').write_text(json.dumps(manifest))
            target = root / 'test.spk'
            build(server, target)
            with self.assertRaises(FileExistsError):
                build(server, target)
            outer = root / 'outer'
            with tarfile.open(target) as archive:
                archive.extractall(outer, filter='data')
            self.assertEqual(json.loads((outer / 'conf/privilege').read_text())['defaults']['run-as'], 'package')
            stage = root / 'stage'
            with tarfile.open(outer / 'package.tgz') as archive:
                archive.extractall(stage, filter='data')
            for line in (stage / 'SHA256SUMS').read_text().splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(sha256((stage / name).read_bytes()).hexdigest(), digest)
            self.assertFalse((stage / 'project/state').exists())
            if os.name == 'nt':
                return  # Real shell execution runs in the isolated Linux acceptance container.
            persistent = root / 'var'
            persistent.mkdir()
            environment = dict(os.environ, SYNOPKG_PKGNAME='TacticStream', SYNOPKG_PKGDEST=str(stage),
                SYNOPKG_PKGVAR=str(persistent), SYNOPKG_PKGINST_TEMP_DIR=str(stage),
                SYNOPKG_TEMP_SCRIPTS_DIR=str(outer / 'scripts'), wizard_port='39882',
                wizard_admin_password='private-test-secret', wizard_admin_confirm='private-test-secret')

            def hook(name, *args, success=True, **overrides):
                result = subprocess.run(['sh', str(outer / 'scripts' / name), *args],
                    env={**environment, **overrides}, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                self.assertNotIn(environment['wizard_admin_password'], result.stdout + result.stderr)

            hook('preinst', success=False, wizard_admin_confirm='wrong')
            self.assertFalse((stage / 'project/state').exists())
            hook('preinst', success=False, wizard_port='65536')
            hook('preinst')
            self.assertEqual((stage / 'project/state/secrets').stat().st_mode & 0o777, 0o700)
            hook('postinst')
            self.assertTrue((stage / 'project/state/data').is_symlink())
            (persistent / 'data/stream/keep').write_text('retained')
            hook('start-stop-status', 'start')
            hook('start-stop-status', 'status')
            hook('start-stop-status', 'stop')
            hook('start-stop-status', 'status', success=False)
            hook('preupgrade', success=False)
            hook('preinst', success=False)
            hook('preuninst')
            hook('postuninst')
            self.assertEqual((persistent / 'data/stream/keep').read_text(), 'retained')
            self.assertTrue((persistent / 'secrets/admin_password').is_file())
