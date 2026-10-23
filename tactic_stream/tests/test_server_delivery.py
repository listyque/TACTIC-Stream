"""Independent server packages retain data and never import a workstation checkout."""
import copy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from tools.file_project_delivery import ROOT, release_version
from tools.server_delivery import release_compose


def deployment_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'deploy/docker' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServerDelivery(unittest.TestCase):
    def test_release_metadata_agrees(self):
        self.assertRegex(release_version(), r'^\d+\.\d+\.\d+$')

    def test_release_metadata_drift_blocks_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'frontend').mkdir()
            (root / 'pyproject.toml').write_text('[project]\nversion = "1.2.3"\n')
            (root / 'frontend/package.json').write_text('{"version":"1.2.2"}')
            (root / 'frontend/package-lock.json').write_text('{"version":"1.2.3","packages":{"":{"version":"1.2.3"}}}')
            with patch('tools.file_project_delivery.ROOT', root), self.assertRaises(AssertionError):
                release_version()

    def test_compose_removes_checkout_and_global_volume_names(self):
        config = dict(services={
            'app': dict(build={}, environment={'PYTHONPATH': '/source', 'TACTIC_PORTS': '8081|8082|8083'}, volumes=[
                dict(type='bind', source='../../src', target='/opt/stream-src'),
                dict(type='volume', source='python_packages', target='/opt/python-packages'),
                dict(type='volume', source='stream_data', target='/var/lib/tactic_stream')]),
            'apache': dict(build={}), 'postgres': dict(image='postgres:18.6',
                environment={'POSTGRES_DB': 'sthpw'}, healthcheck={'test': []})},
            volumes={'stream_data': {'name': 'old_data'}, 'python_packages': {}},
            networks={'default': {'name': 'old_network'}},
            secrets={'postgres_password': {'name': 'old_secret', 'file': 'D:/private/password'}})
        result = release_compose(copy.deepcopy(config), '1.2.3')
        self.assertEqual(result['services']['app']['image'], 'tactic-stream-server-app:1.2.3')
        self.assertEqual(result['services']['app']['volumes'], [config['services']['app']['volumes'][-1]])
        self.assertEqual(result['services']['app']['depends_on']['postgres']['condition'], 'service_healthy')
        self.assertEqual(result['services']['postgres']['environment']['POSTGRES_DB'], 'postgres')
        self.assertEqual(result['services']['postgres']['healthcheck']['test'][-1], 'postgres')
        self.assertNotIn('PYTHONPATH', result['services']['app']['environment'])
        self.assertFalse(any('build' in service for service in result['services'].values()))
        self.assertEqual(result['volumes'], {'stream_data': {}})
        self.assertEqual(result['networks'], {'default': {}})
        self.assertEqual(result['secrets']['postgres_password'], {'file': '.local/postgres-password'})
        config['services']['apache']['volumes'] = [dict(type='bind', source='D:/private', target='/private')]
        with self.assertRaises(AssertionError):
            release_compose(config, '1.2.3')

    def test_new_postgres_config_and_existing_data_guards(self):
        prepare = deployment_module('init-postgres').prepare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare(root)
            path = root / 'config/tactic-conf.xml'
            text = path.read_bytes()
            tree = ET.fromstring(text)
            self.assertEqual(tree.findtext('./database/vendor'), 'PostgreSQL')
            self.assertEqual(tree.findtext('./database/password_file'), '/run/secrets/postgres_password')
            self.assertEqual(tree.findtext('./checkin/asset_base_dir'), (root / 'assets').as_posix())
            prepare(root)
            self.assertEqual(path.read_bytes(), text)
            path.write_text('<config><database><vendor>Sqlite</vendor></database></config>')
            text = path.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(root)
            self.assertEqual(path.read_bytes(), text)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'db').mkdir()
            with self.assertRaises(FileExistsError):
                prepare(root)
            self.assertFalse((root / 'config').exists())

    def test_installed_init_and_update_do_not_build_or_mount_source(self):
        manager = deployment_module('manage')
        for action in ('init', 'update'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'manifest.json').write_text('{"format":"tactic-stream-server"}')
                for name in ('init-postgres.py', 'apache.conf'):
                    (root / name).write_text('test fixture')
                calls = []

                def run(command, **kwargs):
                    calls.append(command)
                    code = 1 if command[1:3] == ['volume', 'inspect'] else 0
                    return subprocess.CompletedProcess(command, code)

                with patch.object(manager, 'HERE', root), patch.object(manager.shutil, 'which', return_value='docker'), \
                        patch.object(manager.subprocess, 'run', side_effect=run), \
                        patch('sys.argv', ['manage.py', action, '--project-name', 'owned-test']):
                    manager.main()
                self.assertFalse(any('build' in call or '-v' in call or 'install-dependencies.py' in str(call) for call in calls))
                postgres = next(index for index, call in enumerate(calls) if call[-1] == 'postgres')
                operation = next(index for index, call in enumerate(calls) if call[-2:] == ['tactic-stream', 'init' if action == 'init' else 'upgrade'])
                self.assertLess(postgres, operation)
                self.assertTrue(any('owned-test_postgres_data' in call for call in calls))
                if os.name != 'nt':
                    self.assertEqual((root / '.local').stat().st_mode & 0o777, 0o700)
                    self.assertEqual((root / '.local/postgres-password').stat().st_mode & 0o777, 0o644)

    def test_load_rejects_corrupt_archive_before_docker(self):
        manager = deployment_module('manage')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'images.tar').write_bytes(b'corrupted')
            manifest = dict(format='tactic-stream-server', files=[dict(path='images.tar', bytes=4, sha256=sha256(b'good').hexdigest())])
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with patch.object(manager, 'HERE', root), patch.object(manager.shutil, 'which', return_value='docker'), \
                    patch.object(manager.subprocess, 'run') as run, patch('sys.argv', ['manage.py', 'load']), \
                    self.assertRaises(SystemExit):
                manager.main()
            run.assert_not_called()
