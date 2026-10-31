"""Real PostgreSQL foundation. STREAM_POSTGRES_HOST/password file opt in; private schemas only."""
import ast
from contextlib import closing
from decimal import Decimal
import inspect
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import DbContainer, DbResource, DatabaseImpl, Insert, PostgresImpl, Sql, Update, Transaction
from pyasm.biz.project import Project
from pyasm.search.search import RequestContext, Search, SearchType, SObject, request_context
from pyasm.search.sql import DatabaseException, SqlException
from pyasm.search.storage import identifier, Store
from pyasm.security.authenticator import hash_password


@unittest.skipUnless(os.environ.get('STREAM_POSTGRES_HOST'), 'Set STREAM_POSTGRES_HOST for a real isolated PostgreSQL check')
class PostgreSQL(unittest.TestCase):
    def test_first_installation_upgrade_and_failed_install_cleanup(self):
        import psycopg
        from unittest.mock import patch
        from xml.etree.ElementTree import Element, SubElement, tostring
        from pyasm.common import Config
        password = Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip()
        values = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                      user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=password)
        database = 'stream_bootstrap_' + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            root = Element('config', version='2')
            section = SubElement(root, 'database')
            for name, value in dict(vendor='PostgreSQL', sobject_database=database,
                                    password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                                    **{key: value for key, value in values.items() if key != 'password'}).items():
                SubElement(section, name).text = value
            config = Path(temporary) / 'tactic-conf.xml'
            config.write_bytes(tostring(root))
            with psycopg.connect(dbname='postgres', autocommit=True, **values) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(config), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config()
                        digest = hash_password('private-bootstrap-check')
                        store.initialize(digest)
                        self.assertFalse(store.database_path('sthpw').exists())
                        from tactic_stream.__main__ import main
                        with patch('sys.argv', ['tactic-stream', '--data-dir', str(store.data_dir), 'init', '--if-needed']), \
                                patch('getpass.getpass', side_effect=AssertionError('Existing PostgreSQL must not prompt')):
                            main()
                        import sys
                        sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
                        import business_contract
                        import generation_contract
                        import workflow_contract
                        import python_contract
                        import engine_contract
                        import snapshot_contract
                        import snapshot_write_contract
                        import naming_contract
                        import expression_contract
                        import expression_write_contract
                        import file_contract
                        import repository_contract
                        import checkin_contract
                        import versionless_contract
                        import delete_contract
                        import append_group_contract
                        import preallocation_contract
                        import upload_checkin_contract
                        import icon_contract
                        import batch_api_contract
                        import file_api_contract
                        import workflow_api_contract
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_business = business_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_workflow = workflow_contract.run({})
                            self.assertEqual(pg_workflow['checks'], [True, False, True])
                            self.assertEqual(pg_workflow['filters'], [2, 2])
                        with psycopg.connect(dbname=database, **values) as db:
                            generation_contract.install_fixture(db)
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_generation = generation_contract.run({'copies': True})
                            self.assertNotIn('error', pg_generation, pg_generation)
                            self.assertEqual(len(pg_generation['tasks']), 4)
                            self.assertEqual(len(pg_generation['repeated']), 4)
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_python = python_contract.run({})
                        with psycopg.connect(dbname=database, **values) as db:
                            engine_contract.install_fixture(db)
                        pg_engine = {}
                        for graph in engine_contract.GRAPHS:
                            with request_context(RequestContext(store, 'admin', 'admin')):
                                pg_engine[graph] = engine_contract.run({'graph': graph})
                        with psycopg.connect(dbname=database, **values) as db:
                            snapshot_contract.install_fixture(db)
                            expression_contract.install_fixture(db)
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_snapshot = snapshot_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_naming = naming_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_expression = expression_contract.run({})
                        pg_expression_write = {}
                        for fail in (True, False):
                            with request_context(RequestContext(store, 'admin', 'admin')):
                                pg_expression_write[fail] = expression_write_contract.run({'fail': fail})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_files = file_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_files_rollback = file_contract.run({'rollback': True})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_repository = repository_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_repository_rollback = repository_contract.run({'fail': True})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_checkin = checkin_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_checkin_rollback = checkin_contract.run({'fail': True})
                        pg_versionless = {}
                        for fail in (False, True):
                            with request_context(RequestContext(store, 'admin', 'admin')):
                                pg_versionless[fail] = versionless_contract.run({'fail': fail})
                        pg_delete = {}
                        for fail in (False, True):
                            with request_context(RequestContext(store, 'admin', 'admin')):
                                pg_delete[fail] = delete_contract.run({'fail': fail})
                        group_cases = ({}, {'lifecycle': True}, {'lifecycle': True, 'fail': True})
                        pg_groups = []
                        for case in group_cases:
                            with request_context(RequestContext(store, 'admin', 'admin')):
                                pg_groups.append(append_group_contract.run(case))
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_preallocation = preallocation_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_upload_checkin = upload_checkin_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_icons = icon_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_batch_api = batch_api_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_file_api = file_api_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_workflow_api = workflow_api_contract.run({})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_snapshot_write = snapshot_write_contract.run({'context': 'pg_contract'})
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            pg_snapshot_rollback = snapshot_write_contract.run({'context': 'pg_rollback', 'fail': True})
                        sqlite_business_data = Path(temporary) / 'sqlite-business'
                        with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': '', 'TACTIC_DATA_DIR': str(sqlite_business_data)}):
                            Config.reload_config()
                            sqlite_business = Store(sqlite_business_data)
                            sqlite_business.initialize(digest)
                            with sqlite_business.connection(write=True) as db:
                                generation_contract.install_fixture(db)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(business_contract.run({}), pg_business)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(workflow_contract.run({}), pg_workflow)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(generation_contract.run({'copies': True}), pg_generation)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(python_contract.run({}), pg_python)
                            with sqlite_business.connection(write=True) as db:
                                engine_contract.install_fixture(db)
                            for graph in engine_contract.GRAPHS:
                                with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                    self.assertEqual(engine_contract.run({'graph': graph}), pg_engine[graph])
                            with sqlite_business.connection(write=True) as db:
                                snapshot_contract.install_fixture(db)
                                expression_contract.install_fixture(db)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(snapshot_contract.run({}), pg_snapshot)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(naming_contract.run({}), pg_naming)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(expression_contract.run({}), pg_expression)
                            for fail in (True, False):
                                with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                    self.assertEqual(expression_write_contract.run({'fail': fail}), pg_expression_write[fail])
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(file_contract.run({}), pg_files)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(file_contract.run({'rollback': True}), pg_files_rollback)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(repository_contract.run({}), pg_repository)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(repository_contract.run({'fail': True}), pg_repository_rollback)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(checkin_contract.run({}), pg_checkin)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(checkin_contract.run({'fail': True}), pg_checkin_rollback)
                            for fail in (False, True):
                                with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                    self.assertEqual(versionless_contract.run({'fail': fail}), pg_versionless[fail])
                            for fail in (False, True):
                                with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                    self.assertEqual(delete_contract.run({'fail': fail}), pg_delete[fail])
                            for case, expected in zip(group_cases, pg_groups):
                                with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                    self.assertEqual(append_group_contract.run(case), expected)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(preallocation_contract.run({}), pg_preallocation)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(upload_checkin_contract.run({}), pg_upload_checkin)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(icon_contract.run({}), pg_icons)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(batch_api_contract.run({}), pg_batch_api)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(file_api_contract.run({}), pg_file_api)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(workflow_api_contract.run({}), pg_workflow_api)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(snapshot_write_contract.run({'context': 'pg_contract'}), pg_snapshot_write)
                            with request_context(RequestContext(sqlite_business, 'admin', 'admin')):
                                self.assertEqual(snapshot_write_contract.run({'context': 'pg_rollback', 'fail': True}), pg_snapshot_rollback)
                        Config.reload_config()
                        with psycopg.connect(dbname=database, **values) as db:
                            self.assertEqual(db.execute('SELECT login,password FROM login').fetchone(), ('admin', digest))
                            self.assertEqual(db.execute('SELECT login_group FROM login_in_group').fetchone(), ('admin',))
                            self.assertEqual(db.execute('SELECT code FROM project ORDER BY code').fetchall(), [('admin',), ('sthpw',)])
                            self.assertTrue(db.execute("SELECT 1 FROM search_object WHERE search_type='sthpw/db_resource'").fetchone())
                        with self.assertRaises(FileExistsError):
                            store.initialize(digest)
                        from tactic_stream.server.api import Api
                        from pyasm.common.errors import AuthenticationError
                        api = Api(store)
                        with self.assertRaises(AuthenticationError):
                            api.get_ticket('admin', 'wrong-password')
                        ticket = {'ticket': api.get_ticket('admin', 'private-bootstrap-check'), 'project': 'admin'}
                        self.assertEqual(api.dispatch('eval', (ticket, '6 * 7')), '42.0')
                        expression_key = 'sthpw/note?code=EX_NOTE'
                        updated = ast.literal_eval(api.dispatch('eval', (ticket, "@UPDATE(sobject,note,'rpc changed')", [expression_key])))
                        self.assertEqual(updated[0]['note'], 'rpc changed')
                        with self.assertRaises(ValueError):
                            api.dispatch('eval', (ticket, "@UPDATE(sobject,note,'must roll back');@COLOR(color,invalid)", [expression_key]))
                        self.assertEqual(ast.literal_eval(api.dispatch('eval', (ticket, '@GET(.note)', [expression_key]))), ['rpc changed'])
                        self.assertEqual(ast.literal_eval(api.dispatch('eval', (ticket, '@PYTHON(expression/run)', [expression_key]))),
                                         {'root': 'EX_NOTE', 'calc': 42, 'project': 'admin'})
                        from concurrent.futures import ThreadPoolExecutor
                        with ThreadPoolExecutor(max_workers=3) as pool:
                            versions = list(pool.map(lambda _: api.dispatch('create_snapshot', (ticket, 'contract/snapshot_entity?project=admin&code=A', 'pg_parallel'))['version'], range(6)))
                        self.assertEqual(sorted(versions), list(range(1, 7)))
                        latest = api.dispatch('get_snapshot', (ticket, 'contract/snapshot_entity?project=admin&code=A'), {'context': 'pg_parallel'})
                        self.assertEqual(latest['version'], 6)
                        self.assertTrue(latest['is_current'])
                        self.assertEqual(api.auth.validate(ticket['ticket']), 'admin')
                        api.auth.renew(ticket['ticket'])
                        self.assertEqual(api.dispatch('ping', (ticket,)), 'OK')
                        script = api.dispatch('insert', (ticket, 'config/custom_script',
                                              {'folder': 'pg', 'title': 'run', 'script': "return {'value':value,'project':server.get_project()}"}))
                        self.assertEqual(api.dispatch('execute_python_script', (ticket, 'pg/run', {'value': 7}))['info'],
                                         {'value': 7, 'project': 'admin'})
                        before_notes = api.dispatch('query', (ticket, 'sthpw/note'))
                        api.dispatch('update', (ticket, script['__search_key__'],
                                     {'script': "server.insert('sthpw/note', {'note':'rollback','process':'python'})\nraise ValueError('failed PG script')"}))
                        with self.assertRaisesRegex(ValueError, 'failed PG script'):
                            api.dispatch('execute_python_script', (ticket, 'pg/run', {}))
                        self.assertEqual(api.dispatch('query', (ticket, 'sthpw/note')), before_notes)
                        api.dispatch('delete_sobject', (ticket, script['__search_key__']))
                        group = api.dispatch('insert', (ticket, 'sthpw/login_group', {'login_group': 'crew', 'name': 'Crew'}))
                        login = api.dispatch('insert', (ticket, 'sthpw/login', {'login': 'lead', 'password': hash_password('private-lead-check')}))
                        member = api.dispatch('insert', (ticket, 'sthpw/login_in_group', {'login': 'lead', 'login_group': 'admin'}))
                        lead = {'ticket': api.get_ticket('lead', 'private-lead-check'), 'project': 'admin'}
                        self.assertEqual(api.dispatch('ping', (lead,)), 'OK')
                        with self.assertRaises(Exception):
                            api.dispatch('update', (ticket, [login['__search_key__'], login['__search_key__']],
                                                   [{'first_name': 'rollback'}, {'missing_column': 'fail'}]))
                        self.assertNotEqual(api.dispatch('get_by_search_key', (ticket, login['__search_key__']))['first_name'], 'rollback')
                        with request_context(RequestContext(store, 'admin')):
                            self.assertGreater(Search('sthpw/transaction_log').get_count(), 0)
                            self.assertGreater(Search('sthpw/sobject_log').get_count(), 0)
                            self.assertGreater(Search('sthpw/change_timestamp').get_count(), 0)
                        api.dispatch('delete_sobject', (ticket, member['__search_key__']))
                        self.assertEqual(api.dispatch('ping', (lead,)), 'OK')
                        with self.assertRaises(SecurityException):
                            api.dispatch('query', (lead, 'sthpw/login'))
                        with self.assertRaises(SecurityException):
                            api.dispatch('insert', (lead, 'sthpw/login_group', {'login_group': 'forbidden'}))
                        from pyasm.security import Sudo
                        from pyasm.security.security import _security_transaction
                        with request_context(RequestContext(store, 'lead')):
                            security = api.auth.bind_security('lead', lead['ticket'])
                            sudo = Sudo()
                            try:
                                # The timestamp validator rejects the payload before raw-SQL authorization.
                                with self.assertRaises(ValueError):
                                    with _security_transaction():
                                        sql = DbContainer.get('sthpw')
                                        self.assertEqual(sql.get_int('SELECT 1'), 1)
                                        with self.assertRaises(UnsupportedContract):
                                            sql.do_update("UPDATE login_group SET name='forbidden'")
                                        account = security.get_login()
                                        account.set_value('first_name', 'must rollback')
                                        account.commit()
                                        session = security.get_ticket()
                                        session.set_value('expiry', "now(); UPDATE login SET password='bad'", quoted=False)
                                        session.commit(triggers='none')
                            finally:
                                sudo.exit()
                            self.assertFalse(Sudo.is_sudo())
                        self.assertNotEqual(api.dispatch('get_by_search_key', (ticket, login['__search_key__']))['first_name'], 'must rollback')
                        api.dispatch('delete_sobject', (ticket, group['__search_key__']))
                        script = '''
from tactic_stream.server.api import Api
api = Api(store)
ticket = {'ticket': api.get_ticket('admin', 'private-bootstrap-check'), 'project': 'admin'}
record = api.dispatch('insert', (ticket, 'sthpw/login_group', {'login_group': 'same_script', 'name': 'Команда'}))
updated = api.dispatch('update', (ticket, record['__search_key__'], {'name': 'Команда 2'}))
stored = api.dispatch('get_by_search_key', (ticket, record['__search_key__']))
deleted = api.dispatch('delete_sobject', (ticket, record['__search_key__']))
from pyasm.search import Sql
from pyasm.search.search import RequestContext, request_context
from pyasm.security import Login, Sudo
from pyasm.common.errors import AuthenticationError, UnsupportedContract
with request_context(RequestContext(store, 'admin')):
    api.auth.bind_security('admin', ticket['ticket'])
    Login.create('artist', 'private-artist-check')
    sql = Sql('sthpw')
    assert sql.get_column_info('login', 'login')['data_type'] == 'varchar'
    assert sql.get_column_types('login')['password'] == 'varchar'
    assert not sql.is_in_transaction()
artist = api.get_ticket('artist', 'private-artist-check')
with request_context(RequestContext(store, 'artist')):
    security = api.auth.bind_security('artist', artist)
    security.get_login().set_password('private-replacement-check')
    try:
        Sql('sthpw').do_update("UPDATE login SET password='bad'")
    except UnsupportedContract:
        pass
    else:
        raise AssertionError('Ordinary SQL write was accepted')
    assert not Sudo.is_sudo()
try:
    api.auth.validate(artist)
except AuthenticationError:
    pass
else:
    raise AssertionError('Old ticket survived password change')
replacement = api.get_ticket('artist', 'private-replacement-check')
result = (record['id'] > 0, record['login_group'], updated['name'], stored['name'], deleted['login_group'],
          api.auth.validate(replacement), api.dispatch('ping', ({'ticket': replacement},)))
api.auth.logout(replacement)
api.auth.logout(ticket['ticket'])
'''
                        pg_script = {'store': store}
                        exec(script, pg_script)
                        sqlite_data = Path(temporary) / 'sqlite-script'
                        with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_DATA_DIR': str(sqlite_data)}):
                            sqlite_store = Store(sqlite_data)
                            sqlite_store.initialize(digest)
                            sqlite_script = {'store': sqlite_store}
                            exec(script, sqlite_script)
                        self.assertEqual(pg_script['result'], sqlite_script['result'])
                        security_config = SubElement(root, 'security')
                        SubElement(security_config, 'inactive_ticket_expiry').text = '20 minute'
                        SubElement(security_config, 'invalid_login_attempts').text = '3'
                        config.write_bytes(tostring(root))
                        Config.reload_config()
                        with self.assertRaises(AuthenticationError):
                            api.get_ticket('lead', 'wrong-password')
                        with psycopg.connect(dbname=database, **values) as db:
                            self.assertEqual(db.execute("SELECT data->>'invalid_logins' FROM login WHERE login='lead'").fetchone(), ('1',))
                        reset_ticket = api.get_ticket('lead', 'private-lead-check')
                        with psycopg.connect(dbname=database, **values) as db:
                            self.assertEqual(db.execute("SELECT data->>'invalid_logins' FROM login WHERE login='lead'").fetchone(), ('0',))
                        api.auth.logout(reset_ticket)
                        with request_context(RequestContext(store, 'lead')):
                            api.auth.bind_security('lead', lead['ticket'])
                            from pyasm.security import Ticket
                            Ticket.update_session_expiry()
                        self.assertEqual(api.auth.validate(lead['ticket']), 'lead')
                        self.check_system_runtime(store, config, ticket, lead)
                        api.auth.logout(ticket['ticket'])
                        with self.assertRaises(AuthenticationError):
                            api.auth.validate(ticket['ticket'])
                        self.assertFalse(store.database_path('sthpw').exists())
                        self.assertFalse(store.upgrade())
                        with psycopg.connect(dbname=database, **values) as db:
                            db.execute('ALTER TABLE project DROP COLUMN database')
                            db.execute("UPDATE search_object SET class_name='conflict' WHERE search_type='sthpw/db_resource'")
                        with self.assertRaises(ValueError):
                            store.upgrade()
                        with psycopg.connect(dbname=database, **values) as db:
                            self.assertFalse(db.execute("SELECT 1 FROM information_schema.columns WHERE table_name='project' AND column_name='database'").fetchone())
                        maintenance.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(database)))
                        with self.assertRaises(psycopg.errors.StringDataRightTruncation):
                            store.initialize('x' * 1000)
                        self.assertFalse(maintenance.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone())
                finally:
                    Config.reload_config()
                    if maintenance.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
                        maintenance.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(database)))

    def check_system_runtime(self, store, config, administrator, ordinary):
        import json
        import socket
        import subprocess
        import sys
        import time
        from urllib.request import Request, urlopen
        from xmlrpc.client import ServerProxy, Fault
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        environment = dict(os.environ, TACTIC_CONFIG_PATH=str(config), TACTIC_DATA_DIR=str(store.data_dir))
        environment.pop('TACTIC_PORTS', None)
        output = store.data_dir / 'test-server.log'
        with output.open('wb') as log:
            process = subprocess.Popen([sys.executable, '-B', '-m', 'tactic_stream', '--data-dir', str(store.data_dir),
                'serve', '--host', '127.0.0.1', '--port', str(port), '--workers', '2'],
                env=environment, stdout=log, stderr=subprocess.STDOUT)
            status_path = store.data_dir / 'temp/log/monitor.json'
            base = 'http://127.0.0.1:%s' % port
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and process.poll() is None:
                    if status_path.exists() and json.loads(status_path.read_text())['state'] == 'running':
                        break
                    time.sleep(.1)
                else:
                    self.fail('PG server did not start: ' + output.read_text()[-2000:])
                state = json.loads(status_path.read_text())
                self.assertEqual([w['service'] for w in state['workers']], ['tactic', 'tactic', 'updates'])
                with urlopen(base + '/health', timeout=5) as response:
                    self.assertTrue(json.load(response)['database_initialized'])
                with urlopen(base + '/', timeout=5) as response:
                    self.assertEqual(response.status, 200)
                with ServerProxy(base + '/tactic/admin/Api/', allow_none=True) as client:
                    self.assertEqual(client.ping(ordinary), 'OK')
                    with self.assertRaises(Fault) as denied:
                        client.query(ordinary, 'sthpw/login')
                    self.assertEqual(denied.exception.faultCode, 403)
                    group = client.insert(administrator, 'sthpw/login_group', {'login_group': 'http_crew', 'name': 'Команда'})
                    updated = client.update(administrator, group['__search_key__'], {'name': "O'Reilly 100%"})
                    self.assertEqual(updated['name'], "O'Reilly 100%")
                    client.delete_sobject(administrator, group['__search_key__'])
                    task = client.insert(administrator, 'sthpw/task', {'process': 'publish', 'status': 'Pending'})
                    note = client.insert(administrator, 'sthpw/note', {'context': 'publish', 'login': 'admin', 'note': "Комментарий O'Reilly", 'access': 'private'}, {}, task['__search_key__'])
                    self.assertEqual(client.get_parent(administrator, note['__search_key__'])['code'], task['code'])
                    self.assertEqual(client.get_by_code(ordinary, 'sthpw/note', note['code']), {})
                    client.update(administrator, task['__search_key__'], {'status': 'Complete'})
                    self.assertTrue(client.get_by_search_key(administrator, task['__search_key__'])['actual_end_date'])
                    with self.assertRaises(Fault):
                        client.update(administrator, [task['__search_key__'], note['__search_key__']],
                                      [{'description': 'must roll back'}, {'missing_column': 'fail'}])
                    self.assertNotEqual(client.get_by_search_key(administrator, task['__search_key__'])['description'], 'must roll back')
                    client.delete_sobject(administrator, note['__search_key__'])
                    client.delete_sobject(administrator, task['__search_key__'])
                    key = 'sthpw/project?code=admin|http|status'
                    self.assertEqual(client.log_message(administrator, key, {'name': 'Данные'}, 'pending'), 'OK')
                    message = client.get_message(administrator, key)
                    self.assertEqual(client.get_by_search_key(administrator, message['__search_key__'])['code'], key)
                    state = client.insert(administrator, 'config/process_state', {'process': 'http', 'status': 'pending'}, {}, 'sthpw/project?code=admin')
                    with self.assertRaises(Fault):
                        client.update(administrator, [state['__search_key__'], message['__search_key__']],
                                      [{'status': 'complete'}, {'missing_column': 'fail'}])
                    self.assertEqual(client.get_by_search_key(administrator, state['__search_key__'])['status'], 'pending')
                    self.assertEqual(json.loads(client.get_message(administrator, key)['message']), {'name': 'Данные'})
                    client.delete_sobject(administrator, state['__search_key__'])
                    client.delete_sobject(administrator, message['__search_key__'])
                request = Request(base + '/admin/rpc', data=json.dumps({'method': 'ping', 'args': [ordinary]}).encode(),
                                  headers={'Content-Type': 'application/json', 'Origin': base})
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(json.load(response)['result'], 'OK')
                self.assertFalse(store.database_path('sthpw').exists())
            finally:
                if process.poll() is None:
                    status_path.parent.mkdir(parents=True, exist_ok=True)
                    (status_path.parent / 'stop.monitor').write_text('')
                    try:
                        process.wait(12)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(12)
            self.assertEqual(process.returncode, 0, output.read_text()[-2000:])
            self.assertEqual(json.loads(status_path.read_text())['state'], 'stopped')

    def test_project_search_sobjects_and_api_use_native_resource(self):
        import sqlite3
        import psycopg
        from tactic_stream.server.api import Api
        password = Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip()
        values = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                      user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=password)
        database = 'stream_project_' + uuid.uuid4().hex
        script = '''
from pyasm.biz import Project
from pyasm.search import Search, SearchType, SObject
search = Search('contract/entity')
search.add_filters('code', ['A', 'B'])
search.add_filter('active', True)
search.add_order_by('code', 'desc')
objects = search.get_sobjects()
obj = Search.get_by_code('contract/entity', 'A')
child = Search.get_by_code('contract/child', 'child')
result = {
    'objects': [(x.get_code(), x.get_value('name'), x.get_value('active')) for x in objects],
    'key': obj.get_search_key(), 'parent': child.get_parent('contract/entity').get_code(),
    'count': search.get_count(), 'columns': SearchType.get_columns('contract/entity'),
    'base': isinstance(obj, SObject), 'database': Project.get().get_database_name(),
}
'''
        rows = [(1, 'A', "Юникод O'Reilly 100%", True, None, 0),
                (2, 'B', 'Beta', False, None, 3), (3, 'C', 'Archived', True, 'retired', None)]
        with psycopg.connect(dbname=os.environ.get('STREAM_POSTGRES_DATABASE', 'sthpw'), **values, autocommit=True) as owner:
            owner.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(database)))
            try:
                with psycopg.connect(dbname=database, **values) as pg:
                    pg.execute('CREATE TABLE entity (id integer PRIMARY KEY, code varchar(256), name text, '
                               'active boolean, s_status varchar(256), amount integer)')
                    pg.execute('CREATE TABLE child (id integer PRIMARY KEY, code text, entity_code text, s_status text)')
                    pg.execute('CREATE TABLE ref (id integer PRIMARY KEY, code text, search_type text, search_code text, s_status text)')
                    with pg.cursor() as cursor:
                        cursor.executemany('INSERT INTO entity VALUES (%s,%s,%s,%s,%s,%s)', rows)
                    pg.execute("INSERT INTO child VALUES (1,'child','A',NULL)")
                    pg.execute("INSERT INTO ref VALUES (1,'ref','contract/entity?project=local','A',NULL)")
                with tempfile.TemporaryDirectory(prefix='stream-project-') as temporary:
                    store = Store(Path(temporary))
                    store.initialize(hash_password('private-project-test'))
                    with store.connection(write=True) as db:
                        db.execute('INSERT INTO db_resource (code,host,port,vendor,login,password) VALUES (?,?,?,?,?,?)',
                                   ('pg', values['host'], values['port'], 'PostgreSQL', values['user'], password))
                        db.executemany('INSERT INTO project (code,title,"database",db_resource) VALUES (?,?,?,?)',
                                       [('one', 'Remote project', database, 'pg'), ('local', 'Local project', 'local_db', None)])
                        db.execute("INSERT INTO login (code,login,password) SELECT 'ordinary','ordinary',password FROM login WHERE login='admin'")
                        for table in ('entity', 'child', 'ref'):
                            stype = 'contract/' + table
                            db.execute('INSERT INTO search_object (code,search_type,namespace,"database",table_name,class_name) '
                                       'VALUES (?,?,\'contract\',\'{project}\',?,\'pyasm.search.SObject\')', (stype, stype, table))
                        schema = '<schema parent="__NONE__"><connect from="contract/child" to="contract/entity" '
                        schema += 'relationship="code" from_col="entity_code" to_col="code"/>'
                        schema += '<connect from="contract/ref" to="contract/entity" relationship="search_type"/></schema>'
                        db.executemany('INSERT INTO "schema" (code,project_code,"schema") VALUES (?,?,?)',
                                       [('one', 'one', schema), ('local', 'local', schema)])
                    # The same unmodified script also runs against the SQLite project.
                    with closing(sqlite3.connect(store.database_path('local_db'))) as local, local:
                        local.execute('CREATE TABLE entity (id integer PRIMARY KEY, code varchar(256), name text, '
                                      'active boolean, s_status varchar(256), amount integer)')
                        local.execute('CREATE TABLE child (id integer PRIMARY KEY, code text, entity_code text, s_status text)')
                        local.executemany('INSERT INTO entity VALUES (?,?,?,?,?,?)', rows)
                        local.execute("INSERT INTO child VALUES (1,'child','A',NULL)")
                    results = []
                    for project in ('one', 'local'):
                        with request_context(RequestContext(store, 'admin', project)):
                            namespace = {}
                            exec(script, namespace)
                            result = namespace['result']
                            self.assertEqual(result.pop('database'), database if project == 'one' else 'local_db')
                            self.assertEqual(result.pop('key'), 'contract/entity?project=%s&code=A' % project)
                            results.append(result)
                    self.assertEqual(results[0], results[1])
                    self.assertEqual(results[0]['objects'], [('A', "Юникод O'Reilly 100%", True)])
                    self.assertEqual(results[0]['parent'], 'A')
                    self.assertTrue(results[0]['base'])
                    # Report buckets and fixed aggregate functions use the same visible scope on both vendors.
                    with psycopg.connect(dbname=database, **values, autocommit=True) as pg:
                        pg.execute('ALTER TABLE entity ADD COLUMN report_date timestamptz')
                        pg.execute("UPDATE entity SET report_date=CASE WHEN code='A' THEN '2026-01-31T23:30:00-02:00'::timestamptz ELSE '2026-02-05 03:00:00 +0300'::timestamptz END")
                    with closing(sqlite3.connect(store.database_path('local_db'))) as local, local:
                        local.execute('ALTER TABLE entity ADD COLUMN report_date timestamp')
                        local.execute("UPDATE entity SET report_date=CASE WHEN code='A' THEN '2026-01-31T23:30:00-02:00' ELSE '2026-02-05 03:00:00 +0300' END")
                    aggregates = []
                    for project in ('one', 'local'):
                        with request_context(RequestContext(store, 'admin', project)):
                            search = Search('contract/entity')
                            aggregates.append(search.get_aggregates([('report_date', 'month')],
                                [(function, '' if function == 'count' else 'amount')
                                 for function in ('count', 'sum', 'avg', 'min', 'max')]))
                    self.assertEqual(aggregates[0], aggregates[1])
                    self.assertEqual(aggregates[0], [('2026-02', 2, 3, Decimal('1.5'), 0, 3)])
                    with request_context(RequestContext(store, 'admin', 'one')):
                        resource = Project.get().get_project_db_resource()
                        self.assertEqual(resource.get_vendor(), 'PostgreSQL')
                        self.assertEqual(resource.get_database(), database)
                        self.assertEqual(DbResource.get_by_code('pg', database).get_key(), resource.get_key())
                        self.assertEqual(Project.get().get_project_db_resource('sthpw').get_vendor(), 'Sqlite')
                        self.assertEqual(Search('contract/entity?project=local').get_database(), 'local_db')
                        self.assertEqual(Search.get_by_code('contract/entity', 'A').get_database_type(), 'PostgreSQL')
                        self.assertEqual(Store(Path(temporary)).tables(resource), {'child': 'child', 'entity': 'entity', 'ref': 'ref'})
                        search = Search('contract/entity')
                        search.add_filter('code', 'A')
                        self.assertEqual(search.get_count(), 1)
                        self.assertEqual(search.get_sobject_ids(), [1])
                        self.assertEqual(Search('contract/entity').get_sobject_codes(), ['A', 'B'])
                        search = Search('contract/entity')
                        search.set_limit(1)
                        search.set_offset(1)
                        self.assertEqual(search.get_sobject().get_code(), 'B')
                        search = Search('contract/entity')
                        search.add_regex_filter('name', "^Юникод.*100%$", 'EQ')
                        self.assertEqual(search.get_sobject_codes(), ['A'])
                        search = Search('contract/child')
                        search.add_order_by('entity.name')
                        self.assertEqual(search.get_sobject().get_code(), 'child')
                        related = Search('contract/entity')
                        related.add_filter('code', 'A')
                        related.add_column('code')
                        search = Search('contract/child')
                        search.add_search_filter('entity_code', related)
                        self.assertEqual(search.get_sobject_codes(), ['child'])
                        search = Search('contract/entity?project=local')
                        search.add_relationship_search_filter(Search('contract/ref?project=one'))
                        self.assertEqual(search.get_sobject_codes(), ['A'])
                        sql = resource.get_sql()
                        sql.start()
                        sql.do_update("UPDATE entity SET name='pending' WHERE code='A'")
                        self.assertEqual(Search('contract/entity').get_sobject().get_value('name'), 'pending')
                        sql.rollback()
                        self.assertEqual(Search('contract/entity').get_sobject().get_value('name'), rows[0][2])
                        search = Search('contract/entity')
                        search.add_filter('name', "' OR true -- %s ?")
                        self.assertEqual(search.get_sobject_codes(), [])
                        obj = SearchType.create('contract/entity')
                        obj.set_value('name', 'blocked')
                        with self.assertRaises(UnsupportedContract):
                            obj.commit()
                    api = Api(store)
                    ticket = {'ticket': api.get_ticket('admin', 'private-project-test'), 'project': 'one'}
                    records = ast.literal_eval(api.dispatch('query', (ticket, 'contract/entity', [['code', 'A']])))
                    self.assertEqual(records[0]['name'], rows[0][2])
                    self.assertEqual(records[0]['__search_key__'], 'contract/entity?project=one&code=A')
                    self.assertTrue(records[0]['active'])
                    self.assertEqual(api.dispatch('get_table_info', (ticket, 'contract/entity')), {'child': 'child', 'entity': 'entity', 'ref': 'ref'})
                    self.assertEqual(api.dispatch('get_column_names', (ticket, 'contract/entity')), results[0]['columns'] + ['report_date'])
                    ordinary = {'ticket': api.get_ticket('ordinary', 'private-project-test'), 'project': 'one'}
                    with self.assertRaises(SecurityException):
                        api.dispatch('query', (ordinary, 'sthpw/db_resource'))
                    with request_context(RequestContext(store, 'ordinary', 'one')):
                        with self.assertRaises(SecurityException):
                            Search('sthpw/db_resource')
                        self.assertEqual(Search('contract/entity').get_sobject_codes(), ['A', 'B'])
                        import xml.etree.ElementTree as ET
                        from pyasm.biz.schema import Schema
                        ET.SubElement(Schema.get(project_code='sthpw').xml, 'connect', {
                            'from': 'sthpw/project', 'to': 'sthpw/db_resource', 'relationship': 'code',
                            'from_col': 'db_resource', 'to_col': 'code'})
                        with self.assertRaises(SecurityException):
                            Search('sthpw/project').add_order_by('db_resource.password')
                    self.assertFalse(store.database_path('one').exists())
                    self.assertFalse(store.database_path(database).exists())
                print('\nPostgreSQL project: native Search/SObject, project database override, related objects, '
                      'same script on SQLite/PG, API reads, rollback and secret access guards')
            finally:
                owner.execute(psycopg.sql.SQL('DROP DATABASE {}').format(psycopg.sql.Identifier(database)))

    def test_native_resources_transactions_metadata_and_original_dialect(self):
        import psycopg
        password = Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip()
        values = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                      user=os.environ.get('STREAM_POSTGRES_USER', 'stream'), password=password)
        database = os.environ.get('STREAM_POSTGRES_DATABASE', 'sthpw')
        schema = 'stream_check_' + uuid.uuid4().hex + '"quote'
        table = 'record"quote'
        impl = DatabaseImpl.get('PostgreSQL')
        self.assertIsInstance(impl, PostgresImpl)
        with psycopg.connect(dbname=database, **values) as owner:
            owner.execute(psycopg.sql.SQL('CREATE SCHEMA {}').format(psycopg.sql.Identifier(schema)))
            owner.commit()
            try:
                with tempfile.TemporaryDirectory(prefix='stream-postgres-') as temporary:
                    store = Store(Path(temporary))
                    store.initialize(hash_password('private-postgres-test'))
                    resource = DbResource(database, vendor='PostgreSQL', schema=schema, **values)
                    with request_context(RequestContext(store, 'admin')):
                        sql = DbContainer.get(resource)
                        self.assertIs(DbContainer.get(resource), sql)
                        self.assertNotIn(password, str(resource))
                        self.assertNotIn(password, repr(resource._get_connection_key()))
                        self.assertEqual(sql.get_vendor(), 'PostgreSQL')
                        self.assertEqual(Sql(resource).get_db_resource(), resource)
                        sql.do_update('CREATE TABLE %s (id serial PRIMARY KEY, code varchar(42), active boolean, '
                                      'amount numeric, timestamp timestamp, data jsonb, "odd""column" text)' % identifier(table))
                        columns = impl.get_column_info(sql, table)
                        self.assertEqual(columns['code'], {'data_type': 'varchar', 'nullable': True, 'size': 42})
                        self.assertEqual(columns['id']['data_type'], 'integer')
                        self.assertFalse(columns['id']['nullable'])
                        self.assertEqual(columns['data']['data_type'], 'json')
                        self.assertEqual(columns['timestamp']['data_type'], 'timestamp')
                        sql.do_update('CREATE TABLE serial_check (id %s)' % impl.get_serial(8))
                        self.assertEqual(impl.get_table_info(resource), {table: table, 'serial_check': 'serial_check'})
                        self.assertEqual(impl.get_column_info(resource, 'serial_check')['id']['data_type'], 'bigint')
                        self.assertEqual(impl.get_column_info(resource, "missing' OR true --"), {})
                        self.assertIs(impl.get_column_info(resource, table), columns)
                        sql.do_update('ALTER TABLE %s ADD COLUMN extra text' % identifier(table))
                        self.assertNotIn('extra', impl.get_column_info(resource, table))
                        self.assertIn('extra', impl.get_column_info(resource, table, use_cache=False))
                        self.assertIn('extra', impl.get_column_info(resource, table))

                        insert = Insert()
                        insert.set_database(sql)
                        insert.set_table(table)
                        for name, value in {'code': "Юникод ' ; --", 'active': True, 'amount': "Decimal('12.50')",
                                            'timestamp': 'NOW', 'data': '{"a":false}', 'odd"column': 'quoted identifier'}.items():
                            insert.set_value(name, value)
                        sql.do_update(insert.get_statement())
                        self.assertEqual(sql.get_row_count(), 1)
                        rows = sql.do_query('SELECT code,active,amount,timestamp IS NOT NULL FROM %s' % identifier(table))
                        self.assertEqual(rows, [("Юникод ' ; --", True, Decimal('12.50'), True)])

                        sql.start()
                        sql.do_update("UPDATE %s SET code='pending'" % identifier(table))
                        with sql.read_connection() as reader:
                            self.assertEqual(reader.execute('SELECT code FROM %s' % identifier(table)).fetchone(), {'code': 'pending'})
                            for operation in (reader.commit, reader.rollback, reader.close, sql.commit, sql.rollback,
                                              lambda: sql.do_update('DELETE FROM %s' % identifier(table))):
                                with self.assertRaises(UnsupportedContract):
                                    operation()
                            borrowed_cursor = reader.cursor()
                        self.assertTrue(borrowed_cursor.closed)
                        with self.assertRaises(UnsupportedContract):
                            reader.cursor()
                        for forbidden in ('COMMIT', 'ROLLBACK', 'SELECT 1; COMMIT',
                                          'DELETE FROM ' + identifier(table),
                                          'WITH removed AS (DELETE FROM %s RETURNING id) SELECT * FROM removed' % identifier(table),
                                          "SELECT set_config('transaction_read_only', 'off', true)"):
                            with self.assertRaises(SqlException, msg=forbidden):
                                sql.do_query(forbidden)
                            self.assertEqual(sql.get_value('SELECT code FROM %s' % identifier(table)), 'pending')
                        sql.do_update("UPDATE %s SET code='after read'" % identifier(table))
                        sql.set_savepoint('point"quoted')
                        sql.do_update("UPDATE %s SET code='savepoint'" % identifier(table))
                        with self.assertRaises(SqlException):
                            sql.do_update('INSERT INTO %s(id) VALUES(1)' % identifier(table))
                        sql.rollback_savepoint('point"quoted')
                        self.assertEqual(sql.get_value('SELECT code FROM %s' % identifier(table)), 'after read')
                        sql.rollback()
                        self.assertEqual(sql.get_value('SELECT code FROM %s' % identifier(table)), "Юникод ' ; --")

                        update = Update()
                        update.set_database(sql)
                        update.set_table(table)
                        update.set_value('code', 'committed')
                        update.set_value('active', None)
                        update.add_filter('id', 1)
                        update.add_filter('code', "Юникод ' ; --")
                        tx = Transaction.get(create=True)
                        tx.set_record(False)
                        self.assertIs(DbContainer.get(resource), sql)
                        sql.do_update(update.get_statement())
                        tx.commit()
                        self.assertEqual(owner.execute(psycopg.sql.SQL('SELECT code, active FROM {}.{}').format(
                            psycopg.sql.Identifier(schema), psycopg.sql.Identifier(table))).fetchone(), ('committed', None))
                        owner.rollback()

                        sequence = table + '_id_seq'
                        self.assertEqual(sql.get_int(impl.get_currval_select(sequence, resource)), 1)
                        sql.do_update('SELECT ' + impl.get_nextval(sequence))
                        self.assertEqual(sql.get_int(impl.get_currval_select(sequence, resource)), 2)
                        sql.do_update('UPDATE %s SET data=%s' % (identifier(table), impl.get_json_counter_update('data', "counter'quote")))
                        self.assertEqual(sql.get_int("SELECT data->>'counter''quote' FROM %s" % identifier(table)), 1)
                        self.assertEqual(sql.get_int('SELECT count(*) FROM %s WHERE %s' % (
                            identifier(table), impl.get_regex_filter('code', 'COMMITTED'))), 1)
                        json_update = Update()
                        json_update.set_database(sql)
                        json_update.set_table(table)
                        json_update.set_value('extra', 'safe JSON key')
                        json_update.add_filter("data->>counter'quote", 1)
                        sql.do_update(json_update.get_statement())
                        self.assertEqual(sql.get_row_count(), 1)
                        sql.do_update('DELETE FROM ' + identifier(table))
                        self.assertEqual(sql.get_row_count(), 1)
                        sql.do_update(impl.get_reset_table_sequence_statement(table, resource))
                        sql.do_update('SELECT ' + impl.get_nextval(sequence))
                        self.assertEqual(sql.get_int(impl.get_currval_select(sequence, resource)), 1)
                        with self.assertRaises(SqlException):
                            sql.do_update('INSERT INTO missing_table VALUES(1)')
                        self.assertEqual(sql.get_int('SELECT 7'), 7)

                        # A second credential must authenticate, rather than reuse the first connection.
                        wrong = DbResource(database, vendor='PostgreSQL', schema=schema, **dict(values, password='wrong-private-test'))
                        with self.assertRaises(DatabaseException):
                            DbContainer.get(wrong)
                        unsafe = DbResource(database, vendor='PostgreSQL', schema=schema, **values, autocommit=True)
                        with self.assertRaises(UnsupportedContract):
                            DbContainer.get(unsafe)
                        tx.start()
                        self.assertIs(DbContainer.get(resource), sql)
                        other = DbResource(database, vendor='PostgreSQL', schema=schema, **values, application_name='another-connection')
                        with self.assertRaises(UnsupportedContract):
                            DbContainer.get(other)
                        tx.rollback()
                        store.database_path('other').touch(exist_ok=False)
                        local = DbContainer.get(DbResource.get_default('other'))
                        local.do_update('CREATE TABLE local_check(id integer, code varchar(42), data text, extra text)')
                        local_impl = local.get_database_impl()
                        self.assertTrue(local_impl.has_savepoint())
                        local.start()
                        local.do_update("INSERT INTO local_check(id, code, data) VALUES (1, 'initial', '{\"a\":false}')")
                        local.set_savepoint('point"quoted')
                        local.do_update("UPDATE local_check SET code='savepoint'")
                        local.rollback_savepoint('point"quoted')
                        self.assertEqual(local.get_value('SELECT code FROM local_check'), 'initial')
                        local.do_update('UPDATE local_check SET data=%s' % local_impl.get_json_counter_update('data', "counter'quote"))
                        local_update = Update()
                        local_update.set_database(local)
                        local_update.set_table('local_check')
                        local_update.set_value('code', 'committed')
                        local_update.set_value('extra', 'safe JSON key')
                        local_update.add_filter('id', 1)
                        local_update.add_filter("data->>counter'quote", 1)
                        local.do_update(local_update.get_statement())
                        self.assertEqual(local.do_query('SELECT code, extra FROM local_check'), [('committed', 'safe JSON key')])
                        local.rollback()
                        self.assertEqual(local.get_int('SELECT count(*) FROM local_check'), 0)
                        tx.start()
                        DbContainer.get(resource)
                        DbContainer.get(DbResource.get_default('other'))
                        sql.do_update('INSERT INTO %s(code) VALUES(\'mixed write\')' % identifier(table))
                        with self.assertRaises(UnsupportedContract):
                            local.do_update('INSERT INTO local_check VALUES(1)')
                        tx.rollback()
                        self.assertEqual(sql.get_int('SELECT count(*) FROM %s' % identifier(table)), 0)
                        self.assertEqual(local.get_int('SELECT count(*) FROM local_check'), 0)
                        sql.start()
                        sql.do_update('INSERT INTO %s(code) VALUES(\'request exit\')' % identifier(table))
                    self.assertEqual(owner.execute(psycopg.sql.SQL('SELECT count(*) FROM {}.{}').format(
                        psycopg.sql.Identifier(schema), psycopg.sql.Identifier(table))).fetchone(), (0,))
                    owner.rollback()
                    with request_context(RequestContext(store, 'ordinary-user')):
                        with self.assertRaises(UnsupportedContract):
                            DbContainer.get(resource)
                    with request_context(RequestContext(store, 'admin')):
                        with self.assertRaises(UnsupportedContract):
                            sql.do_query('SELECT 1')
                self.compare_original_dialect(impl)
            finally:
                owner.rollback()
                owner.execute(psycopg.sql.SQL('DROP SCHEMA {} CASCADE').format(psycopg.sql.Identifier(schema)))
                owner.commit()

    def compare_original_dialect(self, impl):
        original_path = Path(os.environ.get('STREAM_POSTGRES_ORIGINAL') or
                             Path(__file__).resolve().parents[2] / 'legacy/src/pyasm/search/database_impl.py')
        source = original_path.read_text(encoding='utf-8')
        original = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == 'PostgresImpl')
        cases = {'get_page': [(None,), (5,), (5, 3)], 'get_boolean': [(), (True,)],
                 'get_serial': [(), (4, True)], 'get_int': [(), (8, True)],
                 'get_float': [(), (True,)], 'get_text': [(), (True,)],
                 'get_char': [(), (32, True)], 'get_varchar': [(), (None,), (-1, True), ('max',)],
                 'get_nvarchar': [(), (64, True)], 'get_timestamp': [(), ('now', True, True)],
                 'get_json': [(), (True,)], 'get_database_type': [()], 'has_sequences': [()],
                 'get_timestamp_now': [(), (3, 'hour', '-')]}
        names = set(cases) | {'process_value', 'get_nextval', 'get_currval'}
        original.body = [node for node in original.body if isinstance(node, ast.FunctionDef) and node.name in names]
        namespace = {'BaseSQLDatabaseImpl': object, 'basestring': str}
        exec(compile(ast.Module(body=[original], type_ignores=[]), str(original_path), 'exec'), namespace)
        old = namespace['PostgresImpl']()
        comparisons = 0
        for name, arguments in cases.items():
            self.assertEqual(inspect.signature(getattr(old, name)), inspect.signature(getattr(impl, name)))
            for args in arguments:
                self.assertEqual(getattr(old, name)(*args), getattr(impl, name)(*args), (name, args))
                comparisons += 1
        self.assertEqual(old.process_value('ts', 'NOW', 'timestamp')['quoted'], True)
        self.assertEqual(impl.process_value('ts', 'NOW', 'timestamp')['quoted'], False)
        self.assertEqual(old.get_nextval('seq'), '"seq".nextval')
        self.assertEqual(impl.get_nextval('seq'), 'nextval(\'"seq"\')')
        self.assertEqual(impl.process_value('active', 'NULL', 'boolean'), {'value': 'NULL', 'quoted': False})
        self.assertEqual(old.get_serial(8), 'serial')
        self.assertEqual(impl.get_serial(8), 'bigserial')
        print('\nPostgreSQL: native CRUD, read guards, savepoints, rollback, isolation, metadata; '
              '%s pure original dialect comparisons, separately asserted fixes' % comparisons)


if __name__ == '__main__':
    unittest.main(verbosity=2)
