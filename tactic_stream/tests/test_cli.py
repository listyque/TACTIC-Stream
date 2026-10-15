from pathlib import Path
import ast
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from urllib.request import urlopen
from xmlrpc.client import ServerProxy, Binary

from tactic_stream.__main__ import main
from test_monitor import free_port, running
from pyasm.common.config import initialize_config
from pyasm.common.config import Config
from pyasm.search.storage import Store


class Launcher(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'The BAT launcher is Windows-only')
    def test_real_bat_upgrade_and_restart_preserve_project_files_and_preferences(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='stream-bat-') as directory, patch.dict(os.environ):
            data = Path(directory) / 'data'
            for name in ('TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS'):
                os.environ.pop(name, None)
            os.environ['TACTIC_DATA_DIR'] = str(data)
            try:
                with patch('sys.argv', ['tactic-stream', 'init']), patch('getpass.getpass', return_value='private-bat-password'):
                    main()
                config = initialize_config(data)
                xml = ET.parse(config)
                xml.getroot().find('services/enable').text = 'tactic'
                xml.getroot().find('services/process_count').text = '2'
                port = free_port()
                xml.getroot().find('services/start_port').text = str(port)
                xml.write(config, encoding='utf-8', xml_declaration=True)
                Config.reload_config()
                from tactic_stream.server.api import Api
                api = Api(Store(data))
                auth = dict(ticket=api.get_ticket('admin', 'private-bat-password'), project='admin', language='python')
                api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd',
                    dict(project_code='delivery_restart', project_title='Delivery restart', project_stype=['asset'])))
                auth['project'] = 'delivery_restart'
                item = api.dispatch('insert', (auth, 'delivery_restart/asset', dict(code='KEPT', name='Keep me')))
                api.dispatch('set_preference', (auth, 'delivery_restart', 'Preserve preference'))
                api.dispatch('upload_file', (auth, 'kept.txt', Binary(b'Preserve file over upgrade and restart')))
                snapshot = api.dispatch('simple_checkin', (auth, item['__search_key__'], 'publish', 'kept.txt'),
                    dict(mode='uploaded', create_icon=False, keep_file_name=True))
                marker = data / 'opened.json'
                probe = Path(directory) / 'browser_probe.py'
                probe.write_text('import json, os, sys\nfrom pathlib import Path\nfrom urllib.request import urlopen\n'
                    'url = sys.argv[1]\nwith urlopen(url + "test", timeout=5) as response: assert response.read() == b"OK"\n'
                    'Path(os.environ["TACTIC_DATA_DIR"], "opened.json").write_text(json.dumps(url))\n', encoding='utf-8')
                environment = dict(os.environ, BROWSER='"%s" "%s" %%s' % (Path(sys.executable).as_posix(), probe.as_posix()))
                status_path = data / 'temp/log/monitor.json'
                for launch in (1, 2):
                    marker.unlink(missing_ok=True)
                    with (Path(directory) / ('bat-%s.log' % launch)).open('wb') as log:
                        process = subprocess.Popen(['cmd.exe', '/d', '/c', str(root.parent / 'START_TACTIC_STREAM.bat'), '--host', '127.0.0.1'],
                            env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                        try:
                            deadline = time.monotonic() + 35
                            while not marker.is_file() and process.poll() is None and time.monotonic() < deadline:
                                time.sleep(.05)
                            self.assertTrue(marker.is_file(), (Path(directory) / ('bat-%s.log' % launch)).read_text(encoding='utf-8', errors='replace'))
                            self.assertEqual(json.loads(marker.read_text()), 'http://127.0.0.1:%s/' % port)
                            with ServerProxy('http://127.0.0.1:%s/tactic/default/Api/' % port, allow_none=True) as proxy:
                                auth['ticket'] = proxy.get_ticket('admin', 'private-bat-password')
                                rows = ast.literal_eval(proxy.query(auth, 'delivery_restart/asset', [['code', 'KEPT']]))
                                self.assertEqual(rows[0]['name'], 'Keep me')
                                self.assertEqual(proxy.get_preference(auth, 'delivery_restart'), 'Preserve preference')
                                paths = proxy.get_all_paths_from_snapshot(auth, snapshot['__search_key__'])
                                self.assertTrue(paths)
                                self.assertEqual(Path(paths[0]).read_bytes(), b'Preserve file over upgrade and restart')
                        finally:
                            (status_path.parent / 'stop.monitor').touch()
                            try:
                                process.wait(20)
                            except subprocess.TimeoutExpired:
                                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                                process.wait(5)
                        self.assertEqual(process.returncode, 0, (Path(directory) / ('bat-%s.log' % launch)).read_text(encoding='utf-8', errors='replace'))
                    state = json.loads(status_path.read_text())
                    self.assertEqual(state['state'], 'stopped')
                    self.assertTrue(all(not running(worker['pid']) for worker in state['workers']))
            finally:
                Config.reload_config()

    def test_conditional_initialization_preserves_existing_data_and_explicit_init_refuses_it(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            for name in ('TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS'):
                os.environ.pop(name, None)
            store = Store(Path(directory) / 'data')
            argv = ['tactic-stream', '--data-dir', str(store.data_dir), 'init']
            try:
                with patch('sys.argv', argv + ['--if-needed']), patch('getpass.getpass', return_value='private-launch-password') as prompt:
                    main()
                    self.assertEqual(prompt.call_count, 2)
                before = store.database_path('sthpw').read_bytes()
                with patch('sys.argv', argv + ['--if-needed']), patch('getpass.getpass', side_effect=AssertionError('Existing data must not prompt')):
                    main()
                self.assertEqual(store.database_path('sthpw').read_bytes(), before)
                with patch('sys.argv', argv), patch('getpass.getpass', return_value='different-password'):
                    with self.assertRaises(FileExistsError):
                        main()
                self.assertEqual(store.database_path('sthpw').read_bytes(), before)
            finally:
                Config.reload_config()

    def test_browser_opens_after_workers_are_ready_without_creating_database(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            config = initialize_config(data)
            xml = ET.parse(config)
            xml.getroot().find('services/enable').text = 'tactic'
            xml.write(config, encoding='utf-8', xml_declaration=True)
            port = free_port()
            status_path = data / 'temp/log/monitor.json'
            def open_browser(url):
                state = json.loads(status_path.read_text(encoding='utf-8'))
                self.assertEqual(state['state'], 'running')
                self.assertEqual(len(state['workers']), 2)
                with urlopen(url + 'test', timeout=3) as response:
                    self.assertEqual(response.read(), b'OK')
                (status_path.parent / 'stop.monitor').write_text('')
            with patch("sys.argv", ["tactic-stream", "--data-dir", str(data), "serve",
                                    '--host', '127.0.0.1', "--port", str(port), '--workers', '2', "--open-browser"]), \
                    patch.dict(os.environ), \
                    patch("webbrowser.open", side_effect=open_browser) as browser:
                for name in ('TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS'):
                    os.environ.pop(name, None)
                timeout = threading.Timer(12, lambda: (status_path.parent / 'stop.monitor').write_text(''))
                timeout.start()
                try:
                    main()
                finally:
                    timeout.cancel()
                    timeout.join()
                browser.assert_called_once_with("http://127.0.0.1:%s/" % port)
                self.assertTrue((data / 'config/tactic-conf.xml').is_file())
                self.assertFalse(any(path.is_file() for path in (data / 'db').rglob('*')))
                state = json.loads(status_path.read_text(encoding='utf-8'))
                self.assertEqual(state['state'], 'stopped')
                self.assertTrue(all(not running(worker['pid']) for worker in state['workers']))
