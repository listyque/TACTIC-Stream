"""Real spawn workers, real HTTP, bounded recovery and native XML configuration."""
import ast
from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from xmlrpc.client import ServerProxy
import xml.etree.ElementTree as ET

from pyasm.common import Config
from pyasm.web import TacticMonitor
from pyasm.common.config import ConfigException, initialize_config
from pyasm.common.errors import UnsupportedContract
from pyasm.security.authenticator import hash_password
from tactic_stream.server.startup import read_server_config
from pyasm.search.storage import Store
from pyasm.command import Trigger

ROOT = Path(__file__).resolve().parents[1]


class FileWorkerCrashOnce(Trigger):
    def execute(self):
        from pyasm.common import Environment
        data = self.get_caller().get_json_value('data')
        marker = Path(Environment.get_tmp_dir()) / 'file-worker-crashed-once'
        if data.get('kind') == 'upload' and data.get('verified_files') == 1 and not marker.exists():
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text('owned fixture: kill after the worker claim committed')
            os._exit(74)


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def running(pid):
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        kernel.CloseHandle(handle)


class Runtime(unittest.TestCase):
    def test_sse_connections_are_listed_across_real_worker_processes(self):
        ports = [free_port(), free_port()]
        while ports[0] == ports[1]:
            ports[1] = free_port()
        status = self.start(ports=ports)
        with ServerProxy(self.url + '/tactic/default/Api/', allow_none=True) as server:
            ticket = server.get_ticket('admin', 'monitor-private-password', None)
        def post(port, path, payload):
            return urlopen(Request('http://127.0.0.1:%s' % port + path,
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=5)
        def clients():
            with post(ports[0], '/admin/configuration', dict(ticket=ticket)) as response:
                return json.load(response)['result']['event_clients']
        streams = []
        try:
            for port in ports:
                response = post(port, '/admin/server-events', dict(ticket=ticket, project='admin', channels=[], search_types=[]))
                streams.append(response)
                while response.readline().strip():
                    pass
            rows = self.wait_for(lambda: clients() if len(clients()) == 2 else None)
            self.assertEqual({row['worker'] for row in rows}, {worker['pid'] for worker in status['workers'][:2]})
            self.assertTrue(all(row['login'] == 'admin' and row['project'] == 'admin' for row in rows))
            self.assertNotIn(ticket, json.dumps(rows))
            streams.pop().close()
            self.wait_for(lambda: len(clients()) == 1)
        finally:
            for response in streams:
                response.close()
        self.wait_for(lambda: not clients())
        self.shutdown()
        self.assertTrue(all(not running(worker['pid']) for worker in status['workers']))
        self.assertEqual(list((self.store.data_dir / 'cache' / 'event-clients').glob('*.json')), [])

    def wait_for(self, condition, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = condition()
            if result:
                return result
            time.sleep(.05)
        self.fail('Runtime condition timed out; ' + (self.output.read_text(encoding='utf-8')[-2000:] if hasattr(self, 'output') else ''))

    def start(self, count=2, threads=2, ports=None, mode='normal'):
        directory = tempfile.TemporaryDirectory(prefix='tactic-stream-monitor-')
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name))
        self.store.initialize(hash_password('monitor-private-password'))
        config = initialize_config(self.store.data_dir)
        xml = ET.parse(config)
        xml.getroot().find('install/hostname').text = '127.0.0.1'
        values = {'enable': 'tactic|queue' if mode == 'queue' else 'tactic|files' if mode == 'files' else 'tactic', 'process_count': str(count), 'thread_count': str(threads), 'start_port': str(free_port()),
                  'check_interval': '.2', 'worker_timeout': '2.8', 'startup_timeout': '8',
                  'shutdown_timeout': '3', 'restart_delay': '.1'}
        if mode == 'startup-hang':
            values['startup_timeout'] = '2'
        if ports:
            values['ports'] = '|'.join(map(str, ports))
        services = xml.getroot().find('services')
        for key, value in values.items():
            node = services.find(key)
            if node is None:
                node = ET.SubElement(services, key)
            node.text = value
        xml.write(config, encoding='utf-8', xml_declaration=True)
        self.port = ports[0] if ports else int(values['start_port'])
        self.url = 'http://127.0.0.1:%s' % self.port
        self.output = self.store.data_dir / 'runtime.log'
        log = self.output.open('wb')
        self.addCleanup(log.close)
        environment = dict(os.environ)
        for name in ('TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS'):
            environment.pop(name, None)
        self.environment = environment
        self.process = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'tests/monitor_runtime.py'),
            str(self.store.data_dir), mode], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        self.status_path = self.store.data_dir / 'temp/log/monitor.json'
        self.addCleanup(self.shutdown)
        self.wait_for(lambda: self.status_path.exists())
        if mode != 'startup-hang':
            self.wait_for(lambda: self.status()['state'] == 'running')
        return self.status()

    def status(self):
        return json.loads(self.status_path.read_text(encoding='utf-8'))

    def test_owned_file_worker_restart_and_real_transfer(self):
        self.start(count=1, threads=4, mode='files')
        first = next(worker for worker in self.status()['workers'] if worker['service'] == 'files')
        os.kill(first['pid'], signal.SIGTERM)
        self.wait_for(lambda: next(worker for worker in self.status()['workers'] if worker['service'] == 'files')['pid'] != first['pid'])
        from tactic_stream.server.api import Api
        from pyasm.biz.file_project import COMMAND
        from tactic_client_lib.file_transfer import FileTransferClient
        api = Api(self.store)
        token = api.get_ticket('admin', 'monitor-private-password')
        api.dispatch('execute_cmd', ({'ticket': token, 'project': 'admin'},
            'tactic.command.project_template_cmd.ProjectTemplateInstallerCmd',
            {'project_code': 'files', 'project_title': 'Files', 'template_code': 'perforce_like'}))
        def call(action, **kwargs):
            return api.dispatch('execute_cmd', ({'ticket': token, 'project': 'files'}, COMMAND, {'action': action, **kwargs}))['info']
        call('create_depot', code='main')
        call('create_stream', code='main', depot='main')
        call('create_workspace', code='work', stream='main', local_root='D:/local')
        change = call('create_change', workspace='work')['code']
        source = self.store.data_dir / 'fresh-bytes'
        source.mkdir()
        (source / 'new.bin').write_bytes(os.urandom(256 * 1024))
        client = FileTransferClient(self.url, token, 'files')
        result = client.upload(change, source, self.store.data_dir / 'outbox.sqlite', submit=True, timeout=20)
        self.assertEqual(result['state'], 'submitted')
        destination = self.store.data_dir / 'downloaded'
        client.download('work', destination)
        self.assertEqual((destination / 'new.bin').read_bytes(), (source / 'new.bin').read_bytes())
        pids = [worker['pid'] for worker in self.status()['workers']]
        self.shutdown()
        self.assertTrue(all(not running(pid) for pid in pids))

    def shutdown(self):
        if self.process.poll() is not None:
            return
        (self.status_path.parent / 'stop.monitor').write_text('')
        try:
            self.process.wait(8)
        except subprocess.TimeoutExpired:
            # Reap only the disposable processes started by this test.
            for worker in self.status().get('workers', []):
                if worker['pid'] and running(worker['pid']):
                    os.kill(worker['pid'], signal.SIGTERM)
            self.process.kill()
            self.process.wait(5)
            self.fail('Monitor did not stop its workers')

    def test_claimed_upload_recovers_after_file_worker_process_death(self):
        self.start(count=1, threads=4, mode='files')
        from tactic_stream.server.api import Api
        from pyasm.biz.file_project import COMMAND
        from tactic_client_lib.file_transfer import FileTransferClient, digest_file
        api = Api(self.store)
        token = api.get_ticket('admin', 'monitor-private-password')
        ticket = {'ticket': token, 'project': 'files'}
        api.dispatch('execute_cmd', ({'ticket': token, 'project': 'admin'},
            'tactic.command.ProjectTemplateInstallerCmd', {'project_code': 'files', 'project_title': 'Files', 'template_code': 'perforce_like'}))
        client = FileTransferClient(self.url, token, 'files')
        client.rpc('create_depot', code='main')
        client.rpc('create_stream', code='main', depot='main')
        client.rpc('create_workspace', code='work', stream='main', local_root='D:/owned')
        change = client.rpc('create_change', workspace='work')['code']
        api.dispatch('insert', (ticket, 'config/trigger', {'code': 'worker-crash-once',
            'event': 'update|file_project/sync', 'class_name': 'test_monitor.FileWorkerCrashOnce',
            'mode': 'same process,same transaction'}))
        old_pid = next(worker['pid'] for worker in self.status()['workers'] if worker['service'] == 'files')
        source, target = self.store.data_dir / 'fresh', self.store.data_dir / 'received'
        source.mkdir()
        for index in range(3):
            (source / ('fresh-%d.bin' % index)).write_bytes(os.urandom(5 * 1024 * 1024))
        result = client.upload(change, source, self.store.data_dir / 'outbox.sqlite', submit=True, timeout=90)
        self.assertEqual(result['state'], 'submitted')
        self.assertTrue((self.store.data_dir / 'temp/file-worker-crashed-once').is_file())
        current = next(worker for worker in self.status()['workers'] if worker['service'] == 'files')
        self.assertNotEqual(current['pid'], old_pid)
        self.assertFalse(running(old_pid))
        self.assertEqual(current['restarts'], 1)
        client.download('work', target)
        for path in source.iterdir():
            self.assertEqual(digest_file(path), digest_file(target / path.name))
            self.assertEqual(len(client.rpc('history', stream='main', path=path.name)['items']), 1)
        pids = [worker['pid'] for worker in self.status()['workers']]
        self.shutdown()
        self.assertTrue(all(not running(pid) for pid in pids))

    def test_queue_execution_and_owned_crash_recovery(self):
        self.start(count=1, mode='queue')
        status = self.status()
        queue = next(worker for worker in status['workers'] if worker['service'] == 'queue')
        self.assertEqual(len(status['workers']), 3)
        from tactic_stream.server.api import Api
        from pyasm.command import Command
        from pyasm.search import Search
        from pyasm.search.search import RequestContext, request_context
        from tactic.command import Queue
        api = Api(self.store)
        token = api.get_ticket('admin', 'monitor-private-password')
        ticket = dict(ticket=token, project='admin', language='python')
        job = api.dispatch('add_queue_item', (ticket, 'tactic.command.PythonCmd',
            dict(code="from pyasm.biz import ProjectSetting\nProjectSetting.create('executed', 'yes')"), 'default', 1, 'Execute'))
        def state(job_id):
            with request_context(RequestContext(self.store, 'admin')):
                api.auth.bind_security('admin', token)
                return Search.get_by_id('sthpw/queue', job_id).get_value('state')
        self.wait_for(lambda: state(job['id']) == 'complete')
        # A command that hangs once writes a marker only in this disposable data directory.
        code = "from pathlib import Path\nfrom pyasm.common import Environment\nimport time\np = Path(Environment.get_tmp_dir()) / 'queue-once'\nif not p.exists():\n    p.write_text('hung')\n    time.sleep(30)"
        hung = api.dispatch('add_queue_item', (ticket, 'tactic.command.PythonCmd', dict(code=code), 'default', 1, 'Hang once'))
        self.wait_for(lambda: (self.store.data_dir / 'temp/queue-once').exists())
        pid = queue['pid']
        self.wait_for(lambda: self.status()['workers'][1]['pid'] != pid and self.status()['state'] == 'running')
        self.wait_for(lambda: state(hung['id']) == 'complete')
        self.assertFalse(running(pid))
        self.assertEqual(self.status()['workers'][1]['restarts'], 1)
        self.assertEqual(self.status()['workers'][0]['restarts'], 0)
        self.shutdown()
        self.assertEqual(self.process.returncode, 0)
        self.assertTrue((self.status_path.parent / 'queue.log').exists())

    def test_native_chunk_checkin_on_separate_monitored_queue_worker(self):
        self.start(count=1,mode='queue')
        from tactic_stream.server.api import Api
        from pyasm.search import Search
        from pyasm.search.search import RequestContext,request_context
        from urllib.request import Request
        api = Api(self.store)
        token = api.get_ticket('admin','monitor-private-password')
        auth = dict(ticket=token,project='admin')
        api.dispatch('execute_cmd',(auth,'tactic.command.ProjectTemplateInstallerCmd',
                                   dict(project_code='one',project_title='Queue test',path=str(ROOT.parent/'cg'),verbose=False)))
        auth['project'] = 'one'
        api.dispatch('insert',(auth,'cg/scenes',dict(code='EP001',name='Episode')),dict(triggers=False))
        api.dispatch('insert',(auth,'cg/shot',dict(code='SH001',name='Shot',scenes_code='EP001')),dict(triggers=False))
        fields = dict(auth,batch_id='monitor',chunk_id='one',
                      operations=json.dumps([dict(operation_id='first',options=dict(search_key='cg/shot?project=one&code=SH001',
                          context='publish/queue',process='publish',keep_file_name=True,create_icon=False,update_versionless=False,
                          source_files=[dict(path='payload.txt',size=4)]))]),
                      pieces=json.dumps([dict(operation_id='first',file_index=0,offset=0)]))
        body = b''.join(b'--queue\r\nContent-Disposition: form-data; name="'+key.encode()+b'"\r\n\r\n'+value.encode()+b'\r\n' for key,value in fields.items())
        body += b'--queue\r\nContent-Disposition: form-data; name="file0"; filename="part"\r\n\r\nabcd\r\n--queue--\r\n'
        with urlopen(Request(self.url+'/admin/checkin-queue/submit',data=body,
                             headers={'Content-Type':'multipart/form-data; boundary=queue'}),timeout=10) as response:
            self.assertTrue(json.load(response)['result']['accepted'])
        def complete():
            request = Request(self.url+'/admin/checkin-queue/updates',data=json.dumps(dict(auth,batches=[dict(batch_id='monitor',project='one')])).encode(),
                              headers={'Content-Type':'application/json'})
            with urlopen(request,timeout=3) as response:
                changes = json.load(response)['result']['checkins']
            if changes and changes[0]['state'] == 'error':
                self.fail(changes[0]['error'])
            return changes[0] if changes and changes[0]['state']=='complete' else None
        result = self.wait_for(complete)
        with request_context(RequestContext(self.store,'admin','one')):
            api.auth.bind_security('admin',token)
            snapshot = Search.get_by_code('sthpw/snapshot',result['snapshot']['code'])
            self.assertEqual(Path(snapshot.get_all_file_objects()[0].get_lib_path()).read_bytes(),b'abcd')
        pids = [worker['pid'] for worker in self.status()['workers']]
        self.shutdown()
        self.assertTrue(all(not running(pid) for pid in pids))

    def test_real_workers_api_recovery_and_graceful_stop(self):
        status = self.start()
        pids = [worker['pid'] for worker in status['workers']]
        self.assertEqual(len(set(pids)), 3)
        def serving(expected):
            seen = set()
            def request(_):
                with urlopen(self.url + '/_test/worker-pid', timeout=3) as response:
                    return json.load(response)
            with ThreadPoolExecutor(max_workers=8) as requests:
                def probe():
                    seen.update(requests.map(request, range(16)))
                    return seen == set(expected)
                self.wait_for(probe)
        serving(pids[:2])
        with urlopen(self.url + '/test', timeout=3) as response:
            self.assertEqual(response.read(), b'OK')
        with ServerProxy(self.url + '/tactic/default/Api/', allow_none=True) as server:
            token = server.get_ticket('admin', 'monitor-private-password', None)
            self.assertEqual(server.ping({'ticket': token, 'project': 'admin'}), 'OK')
        os.kill(pids[0], signal.SIGTERM)
        self.wait_for(lambda: self.status()['workers'][0]['pid'] != pids[0] and self.status()['state'] == 'running')
        self.assertEqual(self.status()['workers'][0]['restarts'], 1)
        current = [worker['pid'] for worker in self.status()['workers']]
        serving(current[:2])
        producer = self.status()['workers'][-1]
        self.assertEqual(producer['service'], 'updates')
        os.kill(producer['pid'], signal.SIGTERM)
        self.wait_for(lambda: self.status()['workers'][-1]['pid'] != producer['pid'] and self.status()['state'] == 'running')
        self.assertEqual(self.status()['workers'][-1]['restarts'], 1)
        self.assertEqual([worker['pid'] for worker in self.status()['workers'][:2]], current[:2])
        self.assertFalse(running(producer['pid']))
        current = [worker['pid'] for worker in self.status()['workers']]
        self.shutdown()
        self.assertEqual(self.process.returncode, 0)
        self.assertEqual(self.status()['state'], 'stopped')
        self.assertTrue(all(not running(pid) for pid in current))
        self.assertTrue((self.status_path.parent / 'monitor.log').exists())

    def test_hung_event_loop_is_replaced_and_other_worker_keeps_serving(self):
        ports = [free_port(), free_port()]
        self.start(ports=ports)
        def block():
            try:
                with urlopen(self.url + '/_test/block-loop', timeout=9) as response:
                    return response.read()
            except Exception:
                return None
        with ThreadPoolExecutor(max_workers=1) as requests:
            request = requests.submit(block)
            path = self.store.data_dir / 'blocked.pid'
            self.wait_for(lambda: path.exists())
            pid = int(path.read_text())
            with urlopen('http://127.0.0.1:%s/health' % ports[1], timeout=2) as response:
                self.assertTrue(json.load(response)['database_initialized'])
            self.wait_for(lambda: pid not in [worker['pid'] for worker in self.status()['workers']] and self.status()['state'] == 'running')
            self.assertIsNone(request.result(timeout=3))
        self.assertFalse(running(pid))

    def test_exhausted_request_pool_is_replaced(self):
        self.start(count=1, threads=1)
        def block():
            try:
                urlopen(self.url + '/_test/block-pool', timeout=9).close()
            except Exception:
                pass
        with ThreadPoolExecutor(max_workers=1) as requests:
            request = requests.submit(block)
            path = self.store.data_dir / 'blocked.pid'
            self.wait_for(lambda: path.exists())
            pid = int(path.read_text())
            self.wait_for(lambda: self.status()['workers'][0]['pid'] != pid and self.status()['state'] == 'running')
            request.result(timeout=3)
        self.assertFalse(running(pid))

    def test_startup_deadline_and_explicit_original_ports(self):
        self.start(count=1, mode='startup-hang')
        self.wait_for(lambda: self.status()['workers'][0]['restarts'] > 0)
        self.shutdown()
        ports = [free_port(), free_port()]
        self.start(ports=ports)
        for port in ports:
            with urlopen('http://127.0.0.1:%s/test' % port, timeout=3) as response:
                self.assertEqual(response.read(), b'OK')

    def test_duplicate_monitor_and_controls_after_invalid_config(self):
        before = self.start()
        command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'run.py'), '--data-dir', str(self.store.data_dir)]
        duplicate = subprocess.run(command + ['serve'], cwd=ROOT, env=self.environment, capture_output=True, timeout=8)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn(b'A monitor is already running', duplicate.stderr)
        self.assertEqual(self.status()['monitor_pid'], before['monitor_pid'])
        self.assertEqual([worker['pid'] for worker in self.status()['workers']], [worker['pid'] for worker in before['workers']])
        config = self.store.data_dir / 'config/tactic-conf.xml'
        config.write_text('<config version="2"><database><vendor>PostgreSQL</vendor></database>'
                          '<services><process_count>0</process_count></services></config>')
        state = subprocess.run(command + ['status'], cwd=ROOT, env=self.environment, capture_output=True, timeout=8, check=True)
        self.assertEqual(json.loads(state.stdout)['state'], 'running')
        stopped = subprocess.run(command + ['stop'], cwd=ROOT, env=self.environment, capture_output=True, timeout=8, check=True)
        self.assertIn(b'Monitor shutdown requested', stopped.stdout)
        self.process.wait(8)
        self.assertEqual(self.process.returncode, 0)
        self.assertEqual(self.status()['state'], 'stopped')
        self.assertTrue(all(not running(worker['pid']) for worker in before['workers']))


class Configuration(unittest.TestCase):
    def test_cached_config_stays_private_and_disk_changes_are_seen_by_new_requests(self):
        from pyasm.search.search import RequestContext, request_context
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            store = Store(data)
            path = initialize_config(data)
            with request_context(RequestContext(store, 'admin')):
                self.assertEqual(Config.get_value('services', 'process_count'), '3')
                Config.set_value('services', 'process_count', '99')
                self.assertEqual(Config.get_value('services', 'process_count'), '99')
            with request_context(RequestContext(store, 'admin')):
                self.assertEqual(Config.get_value('services', 'process_count'), '3')
            path.write_text('<config version="2"><services><process_count>5</process_count></services></config>')
            with request_context(RequestContext(store, 'admin')):
                self.assertEqual(Config.get_value('services', 'process_count'), '5')
                Config.set_value('services', 'process_count', '6')
                Config.reload_config()
                self.assertEqual(Config.get_value('services', 'process_count'), '5')

    def test_standalone_xml_formats_precedence_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with patch.dict(os.environ, {'TACTIC_DATA_DIR': str(data)}, clear=True):
                path = initialize_config(data)
                self.assertEqual(Config.get_config_path(), path.as_posix())
                Config.reload_config()
                self.assertEqual(Config.get_value('services', 'process_count'), '3')
                self.assertEqual(read_server_config(data)['thread_count'], 50)
                self.assertEqual(initialize_config(data), path)
                v1 = data / 'v1.xml'
                v1.write_text('<config><services process_count="2" start_port="9001" thread_count="4"/></config>')
                os.environ['TACTIC_CONFIG_PATH'] = str(v1)
                self.assertEqual(Config.get_value('services', 'process_count'), '2')
                self.assertEqual(read_server_config(data)['port'], 9001)
                os.environ['TACTIC_TMP_CONFIG_PATH'] = str(path)
                self.assertEqual(Config.get_value('services', 'process_count'), '3')
                os.environ.pop('TACTIC_TMP_CONFIG_PATH')
                v1.write_text('<config><services process_count="0"/></config>')
                with self.assertRaises(ConfigException):
                    read_server_config(data)
                v1.write_text('<config><services worker_timeout="nan"/></config>')
                with self.assertRaises(ConfigException):
                    read_server_config(data)
                v1.write_text('<config><database vendor="PostgreSQL" server="pg.example" sobject_database="stream_system"/></config>')
                self.assertEqual(read_server_config(data)['process_count'], 3)
                resource = Store(data).get_db_resource()
                self.assertEqual((resource.get_host(), resource.get_database()), ('pg.example', 'stream_system'))
                v1.write_text('<config><database vendor="MySQL"/></config>')
                with self.assertRaises(UnsupportedContract):
                    read_server_config(data)
                refused = subprocess.run([sys.executable, '-B', str(ROOT / 'run.py'), '--data-dir', str(data), 'serve'],
                    env=dict(os.environ), capture_output=True, timeout=8)
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b'MySQL is not migrated', refused.stderr)
                self.assertFalse((data / 'db').exists())
                os.environ['TACTIC_CONFIG_PATH'] = str(data / 'missing.xml')
                with self.assertRaises(ConfigException):
                    Config.get_xml_data()

    def test_original_monitor_signatures_and_native_import(self):
        from pyasm.web.monitor import TacticMonitor as exported
        self.assertIs(exported, TacticMonitor)
        original = ast.parse((ROOT.parent / 'legacy/src/pyasm/web/monitor.py').read_text(encoding='utf-8'))
        old = next(node for node in original.body if isinstance(node, ast.ClassDef) and node.name == 'TacticMonitor')
        actual = ast.parse((ROOT / 'src/tactic_stream/server/monitor.py').read_text(encoding='utf-8'))
        new = next(node for node in actual.body if isinstance(node, ast.ClassDef) and node.name == 'TacticMonitor')
        for name in ('__init__', 'set_check_interval', 'set_dev', 'execute', '_execute', 'monitor', 'final_kill', 'remove_monitor_pid', 'write_log'):
            old_method = next(node for node in old.body if isinstance(node, ast.FunctionDef) and node.name == name)
            new_method = next(node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(ast.dump(old_method.args), ast.dump(new_method.args), name)
