"""Run with manage.py check: real Apache, ASGI workers and authenticated PostgreSQL."""
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xmlrpc.client import ServerProxy

from tactic_stream import __version__


url = os.environ.get('STREAM_DEPLOY_URL', 'http://apache').rstrip('/')
data_dir = Path(os.environ.get('TACTIC_DATA_DIR', '/var/lib/tactic_stream'))
with urlopen(url + '/health', timeout=5) as response:
    health = json.load(response)
    assert health['service'] == 'tactic_stream'
    assert health['version'] == __version__
with urlopen(url + '/', timeout=5) as response:
    assert response.url == url + '/'
    html = response.read().decode('utf-8')
assets = re.findall(r'(?:src|href)="(/ui/assets/[^\"]+)"', html)
assert len(assets) >= 2
for asset in assets:
    with urlopen(url + asset, timeout=5) as response:
        assert response.read()
try:
    urlopen(url + '/admin/', timeout=5)
except HTTPError as error:
    assert error.code == 404
    error.close()
else:
    raise AssertionError('Removed UI aliases must not redirect')
with ServerProxy(url + '/tactic/default/Api/', allow_none=True) as rpc:
    assert rpc.fast_ping(None) == 'OK'
body = json.dumps({'method': 'fast_ping', 'args': [None]}).encode()
with urlopen(Request(url + '/admin/rpc', data=body,
        headers={'Content-Type': 'application/json', 'Origin': url}), timeout=5) as response:
    assert json.load(response)['result'] == 'OK'
try:
    urlopen(Request(url + '/admin/rpc', data=body,
            headers={'Content-Type': 'application/json', 'Origin': 'http://other.invalid'}), timeout=5)
except HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError('Apache must preserve the application origin check')
boundary = 'deploy-upload-boundary'
upload = (f'--{boundary}\r\nContent-Disposition: form-data; name="ticket"\r\n\r\ninvalid-ticket\r\n'
          f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="probe.txt"\r\n\r\nprobe\r\n'
          f'--{boundary}--\r\n').encode()
try:
    urlopen(Request(url + '/tactic/default/UploadServer/', data=upload,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}), timeout=5)
except HTTPError as error:
    assert error.code == 403
    assert json.load(error)['error'] == 'Invalid credentials or expired session.'
else:
    raise AssertionError('Apache upload must reach the authenticated native endpoint')
from tactic_stream.server.startup import read_server_config, read_log_dir
state = json.loads((read_log_dir(data_dir) / 'monitor.json').read_text())
assert state['state'] == 'running'
web_workers = [worker for worker in state['workers'] if worker.get('service', 'tactic') == 'tactic']
settings = read_server_config(data_dir)
assert len(web_workers) == settings['process_count']
assert len([worker for worker in state['workers'] if worker.get('service') == 'queue']) == int(settings['queue_enabled'])
assert all(worker['pid'] for worker in state['workers'])
ports = settings['ports'] or [settings['port']]
for port in ports:
    with urlopen('http://127.0.0.1:%s/health' % port, timeout=5) as response:
        health = json.load(response)
        assert health['service'] == 'tactic_stream'
        assert health['version'] == __version__
print('Apache: current assets, XML-RPC, HTTP upload authentication, origin checks; native workers:', list(ports))

from pyasm.search.storage import Store
resource = Store(data_dir).get_db_resource()
if resource.get_vendor() == 'PostgreSQL':
    connection = resource.get_database_impl()._connect(resource)
else:
    assert resource.get_vendor() == 'Sqlite'
    # The default SQLite deployment still checks its separate PostgreSQL service.
    import psycopg
    connection = psycopg.connect(host='postgres', dbname='postgres', user='stream',
        password=Path('/run/secrets/postgres_password').read_text().strip(), connect_timeout=5)
with connection as db:
    db.execute('CREATE TEMP TABLE stream_deploy_check (id integer, name text)')
    db.commit()
    db.execute('INSERT INTO stream_deploy_check VALUES (%s, %s)', (1, 'Проверка'))
    db.rollback()
    assert db.execute('SELECT count(*) FROM stream_deploy_check').fetchone() == (0,)
    db.execute('INSERT INTO stream_deploy_check VALUES (%s, %s)', (2, 'TACTIC Stream'))
    db.commit()
    assert db.execute('SELECT name FROM stream_deploy_check').fetchone() == ('TACTIC Stream',)
print('PostgreSQL: password authentication, UTF-8, commit and rollback; no persistent test tables')
