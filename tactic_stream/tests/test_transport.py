import ast
import gzip
import importlib.util
import json
from pathlib import Path
import socket
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from xmlrpc.client import Binary, Fault, ServerProxy, dumps, loads

from test_foundation import ROOT, LEGACY, fixture
from test_search_links import link_fixture
from tactic_stream.server.app import MAX_BODY, create_app
from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store
import uvicorn


class Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tactic.core.bootstrap import CoreInit
        from pyasm.command import Trigger
        from pyasm.command.workflow import Workflow
        from pyasm.biz import Snapshot
        cls.native_startup = (CoreInit.initialized, Trigger.STATIC_TRIGGERS[:],
                              Trigger.INTEGRAL_TRIGGERS[:], Snapshot.integral_trigger_added,
                              Workflow.startup_initialized)
        cls.previous_path = sys.path.copy()
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'data')
        from tactic.startup import FirstRunInit
        from pyasm.search.search import RequestContext, request_context
        with request_context(RequestContext(cls.store, 'admin')):
            FirstRunInit().execute()
        cls.store.initialize(hash_password("private-test-password"))
        fixture(cls.store)
        link_fixture(cls.store)
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import snapshot_contract
        with cls.store.connection(write=True) as db:
            snapshot_contract.install_fixture(db)
        cls.baseline = Path(cls.temp.name) / 'baseline'
        shutil.copytree(cls.store.data_dir, cls.baseline)
        cls.server = None
        cls.start_server()

    @classmethod
    def start_server(cls):
        cls.socket = socket.socket()
        cls.socket.bind(("127.0.0.1", 0))
        cls.socket.listen()
        cls.port = cls.socket.getsockname()[1]
        cls.url = f"http://127.0.0.1:{cls.port}"
        cls.server = uvicorn.Server(uvicorn.Config(create_app(cls.store.data_dir), log_level="error", access_log=False, timeout_graceful_shutdown=2))
        cls.thread = threading.Thread(target=cls.server.run, kwargs={"sockets": [cls.socket]}, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 10
        while not cls.server.started:
            if not cls.thread.is_alive() or time.monotonic() > deadline:
                cls.tearDownClass()
                raise RuntimeError("Test server failed to start")
            time.sleep(0.01)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.stop_server()
            cls.temp.cleanup()
        finally:
            # A stopped web fixture must not leave its startup handlers in unrelated headless probes.
            from tactic.core.bootstrap import CoreInit
            from pyasm.command import Trigger
            from pyasm.command.workflow import Workflow
            from pyasm.biz import Snapshot
            (CoreInit.initialized, Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS,
             Snapshot.integral_trigger_added, Workflow.startup_initialized) = cls.native_startup
            sys.path[:] = cls.previous_path

    @classmethod
    def stop_server(cls):
        if cls.server is None:
            return
        cls.server.should_exit = True
        cls.thread.join(10)
        cls.socket.close()
        if cls.thread.is_alive():
            raise RuntimeError("Test server did not shut down")
        cls.server = None

    def setUp(self):
        # Each transport scenario starts from the same private DB and repositories.
        target = self.store.data_dir.resolve()
        if target != (Path(self.temp.name) / 'data').resolve():
            raise RuntimeError('Fixture reset must stay in its private data directory')
        self.stop_server()
        shutil.rmtree(target)
        shutil.copytree(self.baseline, target)
        self.start_server()

    def proxy(self):
        proxy = ServerProxy(self.url + "/tactic/default/Api/", allow_none=True)
        self.addCleanup(proxy.__exit__, None, None, None)
        return proxy

    def test_object_report_pages_and_acl(self):
        from tactic_stream.server.api import Api
        from tactic_stream.server.result_items import read_result_items
        from pyasm.search.search import RequestContext, request_context
        from pyasm.common import Environment
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one')
        with self.store.connection(write=True) as db:
            schema = db.execute('SELECT id, "schema" FROM "schema" WHERE project_code=\'one\'').fetchone()
            xml = ET.fromstring(schema['schema'])
            for edge in list(xml):
                if edge.tag == 'connect' and edge.get('from', '').startswith(('contract/', 'sthpw/contract_')):
                    xml.remove(edge)
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?', (ET.tostring(xml, encoding='unicode'), schema['id']))
        kind = 'one/report_assets'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
            dict(search_type_name=kind, asset_title='Report assets')))
        owner = api.dispatch('insert', (auth, kind, dict(code='REPORT', name='Report Robot', description='Object description\ntactic-search://open?project=one&search_type=one/report_assets')))
        task = api.dispatch('create_task', (auth, owner['__search_key__'], 'model'))
        api.dispatch('update', (auth, task['__search_key__'], dict(assigned='admin', description='Model description')))
        api.dispatch('insert', (auth, 'sthpw/note', dict(search_type=kind + '?project=one', search_code=owner['code'],
            project_code='one', process='publish', note='Object note', login='admin')))
        api.dispatch('insert', (auth, 'sthpw/note', dict(search_type='sthpw/task', search_code=task['code'],
            project_code='one', process='model', note='Task note', login='admin')))
        api.dispatch('upload_file', (auth, 'Report details.txt', Binary(b'Report file contents')))
        api.dispatch('simple_checkin', (auth, owner['__search_key__'], 'model', 'Report details.txt'),
            dict(mode='uploaded', create_icon=False, description='Report package'))
        with request_context(RequestContext(self.store, 'admin', 'one')):
            api.auth.bind_security('admin', auth['ticket'])
            def report(page='tasks'):
                return read_result_items(kind, [owner['__search_key__']], dict(kind='object_report', path=page))
            data = report()
            self.assertEqual(data['summary']['title'], 'Report Robot')
            self.assertEqual(data['metrics']['tasks'], 1)
            self.assertEqual(data['metrics']['notes'], 2)
            self.assertEqual(data['metrics']['taskNotes'], 1)
            self.assertEqual(data['tasks'][0]['searchKey'], task['__search_key__'])
            self.assertEqual(data['participants'][0]['login'], 'admin')
            self.assertEqual({row['body'] for row in report('notes')['notes']}, {'Object note', 'Task note'})
            self.assertEqual(report('children')['children'], [])
            snapshot_page = report('snapshots')
            self.assertTrue(snapshot_page['files'])
            self.assertEqual({row['title'] for row in snapshot_page['files']}, {'Report details_model_v001.txt'})
            self.assertEqual(snapshot_page['metrics']['files'], len(snapshot_page['files']))
            self.assertEqual(len(snapshot_page['snapshot_processes']), 1)
            self.assertIsInstance(report('activity')['activity'], list)
            with self.assertRaisesRegex(ValueError, 'Invalid object report page'):
                report('unknown')
            security = Environment.get_security()
            original = security.check_access
            def restricted(group, keys, access, **options):
                if group == 'sobject_column' and isinstance(keys, dict) and keys.get('column') in ('hourly_wage', 'description'):
                    return False
                return original(group, keys, access, **options)
            with patch.object(security, 'check_access', side_effect=restricted):
                hidden = report()
            self.assertFalse(hidden['metrics']['canViewCosts'])
            self.assertNotIn('totalCost', hidden['metrics'])
            self.assertNotIn('cost', hidden['participants'][0])
            self.assertEqual(hidden['summary']['description'], '')
            hour = api.dispatch('insert', (auth, 'sthpw/work_hour', dict(
                project_code='one', task_code=task['code'], login='admin',
                straight_time=4, over_time=0, category='regular')))
            private_columns = {'hourly_wage', 'assigned', 'login', 'status',
                'progress', 'completion', 'st_size', 'straight_time', 'over_time', 'category'}
            def private(group, keys, access, **options):
                if group == 'sobject_column' and isinstance(keys, dict) and keys.get('column') in private_columns:
                    return False
                return original(group, keys, access, **options)
            from pyasm.biz import Task, WorkHour
            with patch.object(security, 'check_access', side_effect=private), patch.object(
                Task, 'get_completion', side_effect=AssertionError('Hidden status must not be derived')
            ), patch.object(WorkHour, 'get_total_hours', side_effect=AssertionError('Hidden hours must not be aggregated')):
                masked = report()
                masked_files = report('snapshots')
            self.assertEqual(masked['participants'], [])
            self.assertEqual(masked['metrics']['participants'], 0)
            self.assertEqual(masked['metrics']['workHours'], 0)
            self.assertEqual(masked['metrics']['totalSize'], '0 B')
            self.assertEqual(masked['tasks'][0]['assigned'], '')
            self.assertEqual(masked['tasks'][0]['status'], '')
            self.assertEqual(masked['tasks'][0]['progress'], 0)
            self.assertTrue(all(row['size'] == 0 for row in masked_files['files']))
            api.dispatch('delete_sobject', (auth, hour['__search_key__']))
        result = subprocess.run([shutil.which('node'), str(ROOT/'frontend/tests/object_report.mjs'), self.url],
            cwd=ROOT/'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(api.dispatch('query', (auth, kind, [['code', 'REPORT']])), [])
        self.assertFalse(Path(snapshot_page['files'][0]['path']).exists())

    def test_task_report_ignores_closed_journal_relations_and_has_readable_title(self):
        from tactic_stream.server.api import Api
        from tactic_stream.server.result_items import read_result_items
        from pyasm.search.search import RequestContext, request_context
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one')
        owner = api.dispatch('query', (auth, 'contract/entity', [['code', 'A']]))[0]
        task = api.dispatch('create_task', (auth, owner['__search_key__']), dict(process='model', description='Model the robot'))
        api.dispatch('create_note', (auth, task['__search_key__'], 'Task report note'))
        api.dispatch('insert', (auth, 'sthpw/work_hour', dict(
            project_code='one', task_code=task['code'], login='admin',
            straight_time=4, over_time=0, category='regular')))
        with request_context(RequestContext(self.store, 'admin', 'one')):
            api.auth.bind_security('admin', auth['ticket'])
            for page in ('tasks', 'notes', 'children', 'snapshots', 'activity'):
                result = read_result_items('sthpw/task', [task['__search_key__']], dict(kind='object_report', path=page))
                self.assertEqual(result['summary']['title'], 'model · A')
                self.assertEqual(result['summary']['description'], 'Model the robot')
                self.assertEqual(result['metrics']['workHours'], 4)
                self.assertFalse({row['value'] for row in result['child_types']} & {
                    'sthpw/sobject_log', 'sthpw/transaction_state', 'sthpw/exception_log', 'sthpw/debug_log'})
                if page == 'notes':
                    self.assertEqual([row['body'] for row in result['notes']], ['Task report note'])

    def test_naming_editor_commands(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        command = 'tactic.ui.panel.naming_cmd.NamingCmd'
        def call(action, **values):
            return proxy.execute_cmd(auth, command, dict(action=action, project_code='one', search_type='contract/entity', **values))['info']
        from tactic.ui.panel.naming_cmd import FIELDS, BOOLEANS
        draft = {field: False if field in BOOLEANS else '' for field in FIELDS}
        draft.update(search_type='contract/entity', checkin_type='strict', context='naming/*',
                     dir_naming='{project.code}/{search_type.table_name}/{sobject.code}/{parent.code}',
                     file_naming='{sobject.code}_{snapshot.context[1]}_v{version}_{@GET(.amount)}.{ext}')
        sample = dict(key='contract/entity?project=one&code=A', file='example.exr', version=12,
                      process='naming', context='naming/main', fileType='main', snapshotType='file')
        before = [len(ast.literal_eval(proxy.query(auth, kind))) for kind in ('sthpw/snapshot', 'sthpw/file')]
        preview = call('preview', document=draft, sample=sample)
        result = preview['results'][0]
        self.assertTrue(result['matches'])
        self.assertEqual(result['directory'], 'one/entity/A/NO_PARENT')
        self.assertEqual(result['file'], 'A_main_v012_0.exr')
        self.assertEqual(before, [len(ast.literal_eval(proxy.query(auth, kind))) for kind in ('sthpw/snapshot', 'sthpw/file')])
        loaded = call('load')
        saved = call('save', document=draft, expected_revision=loaded['revision'])
        identity = saved['identity']
        self.assertTrue(identity)
        self.assertNotEqual(saved['revision'], loaded['revision'])
        native = proxy.execute_python_script(auth, '', {'code': """
from pyasm.biz import DirNaming, FileNaming, Snapshot
from pyasm.search import Search, SearchType
obj = Search.get_by_code('contract/entity', 'A')
snapshot = Snapshot.create(obj, 'file', 'naming/main', version=12, commit=False)
file = SearchType.create('sthpw/file')
file.set_value('file_name', 'example.exr', temp=True)
file.set_value('base_type', 'file', temp=True)
file.set_value('type', 'main', temp=True)
return {'directory': DirNaming(obj, snapshot, file_type='main', file_object=file).get_from_db_naming('file'),
        'file': FileNaming(obj, snapshot, file_object=file).get_from_db_naming('contract/entity')}
"""})
        self.assertEqual(native['info']['directory'], result['directory'])
        self.assertEqual(native['info']['file'], result['file'])

        with self.assertRaises(Fault):
            call('save', document=draft, expected_revision=loaded['revision'])
        self.assertEqual(len(call('load')['rules']), len(loaded['rules']) + 1)
        draft.update(latest_versionless=True, current_versionless=True, manual_version=True,
                     file_naming='{sobject.code}_v{version}.{ext}')
        sample.update(file='item_v024.exr')
        preview = call('preview', identity=identity, document=draft, sample=sample)
        self.assertEqual(preview['results'][0]['version'], 24)
        self.assertEqual(before, [len(ast.literal_eval(proxy.query(auth, kind))) for kind in ('sthpw/snapshot', 'sthpw/file')])
        sample.update(key='contract/entity?project=two&code=A')
        with self.assertRaises(Fault):
            call('preview', identity=identity, document=draft, sample=sample)
        sample.update(key='contract/entity?project=one&code=A', file='example.exr')
        draft.update(manual_version=False, latest_versionless=False, current_versionless=False,
                     condition='@GET(snapshot.context) == other')
        self.assertFalse(call('preview', document=draft, identity=identity, sample=sample)['matches'])
        draft.update(condition='', dir_naming='one/entity/A', file_naming='fixed.exr')
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO file (code,file_name,relative_dir,type,project_code,search_type,search_id,snapshot_code) VALUES ('naming_collision','fixed.exr','one/entity/A','main','one','contract/entity',1,'naming_snapshot')")
        self.assertTrue(call('preview', document=draft, identity=identity, sample=sample)['results'][0]['collisions'])
        with self.store.connection(write=True) as db:
            db.execute("DELETE FROM file WHERE code='naming_collision'")
        script = proxy.insert(auth, 'config/custom_script', dict(folder='naming_test', title='paths', language='python',
                              script="return 'native-' + input['mode']"))
        draft.update(script_path='naming_test/paths')
        with self.assertRaises(Fault):
            call('preview', document=draft, identity=identity, sample=sample)
        result = call('preview', document=draft, identity=identity, sample=sample, allow_execution=True)['results'][0]
        self.assertEqual(result['directory'], 'native-dir')
        self.assertEqual(result['file'], 'native-file')
        self.assertEqual(result['sandbox'], 'native-sandbox_dir')
        proxy.delete_sobject(auth, script['__search_key__'])
        proxy.insert(auth, 'sthpw/login', dict(login='naming_guest', password=hash_password('guest-test-password')))
        guest = dict(ticket=proxy.get_ticket('naming_guest', 'guest-test-password'), project='one')
        with self.assertRaises(Fault):
            proxy.execute_cmd(guest, command, dict(action='load', project_code='one', search_type='contract/entity'))

    def test_workflow_editor_and_process_rules_commands(self):
        import copy
        proxy = self.proxy()
        ticket = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        def workflow(action, **kwargs):
            return proxy.execute_cmd(ticket, 'tactic.ui.panel.workflow_cmd.WorkflowCmd', dict(action=action, project_code='one') | kwargs)['info']
        self.assertIn('manual', workflow('new', identity='contract/entity')['metadata']['nodeTypes'])
        document = dict(name='Workflow editor contract', description='Native graph', color='', searchType='contract/entity',
                        xml='<pipeline custom="keep"><!--preserve--><process name="work" type="manual" xpos="-10"/><process name="finish" type="action"/><connect from="work" to="finish" from_attr="a &amp; b"/><custom/></pipeline>',
                        processSettings={'work': {'version': 2, 'node_type': 'manual', 'properties': {'duration': 2}},
                                         'finish': {'version': 2, 'node_type': 'action', 'default': {'script': 'return True', 'language': 'python'}}}, processDescriptions={})
        saved = workflow('save', document=document)
        identity = saved['identity']
        self.assertTrue(identity)
        root = ET.fromstring(saved['document']['xml'])
        self.assertEqual(root.get('custom'), 'keep')
        self.assertIsNotNone(root.find('custom'))
        self.assertIn('<!--preserve-->', saved['document']['xml'])
        self.assertTrue(all(node.get('process_code') for node in root.findall('process')))
        self.assertEqual(saved['document']['processSettings']['finish']['default']['script'], 'return True')
        self.assertEqual(ET.fromstring(workflow('layout', document={'xml': saved['document']['xml']}, style='flow')['xml']).tag, 'pipeline')
        changed = copy.deepcopy(saved['document']); changed['description'] = 'Changed'
        updated = workflow('save', identity=identity, document=changed, expected_revision=saved['revision'])
        with self.assertRaises(Fault):
            workflow('save', identity=identity, document=changed, expected_revision=saved['revision'])
        bad = copy.deepcopy(updated['document']); bad['xml'] = bad['xml'].replace('name="work"', 'name="renamed"')
        with self.assertRaises(Fault):
            workflow('save', identity=identity, document=bad, expected_revision=updated['revision'])
        self.assertEqual(workflow('load', identity=identity)['revision'], updated['revision'])
        def rules(action, process, **kwargs):
            return proxy.execute_cmd(ticket, 'tactic.ui.panel.process_rules_cmd.ProcessRulesCmd', dict(action=action, project_code='one', identity=process) | kwargs)['info']
        work = updated['metadata']['processCodes']['work']
        loaded = rules('load', work)
        rule = dict(key='', kind='trigger', action='task_date', title='Set date', scope='local', event='change|sthpw/task|status',
                    srcStatus='', column='actual_start_date', mode='same process,same transaction')
        saved_rules = rules('save', work, document={'rules': [rule]}, expected_revision=loaded['revision'])
        self.assertEqual(saved_rules['document']['rules'][0]['action'], 'task_date')
        with self.assertRaises(Fault):
            rules('save', work, document={'rules': []}, expected_revision=loaded['revision'])
        notification = dict(key='', kind='notification', action='notification', title='Notice', scope='local', event='change|sthpw/task|status',
                            srcStatus='', subject='Subject', body='Body', mailTo='admin', mailCc='', rules='<rules><!--keep--><rule>@GET(.status) != "blocked"</rule></rules>')
        saved_rules = rules('save', work, document={'rules': saved_rules['document']['rules'] + [notification]}, expected_revision=saved_rules['revision'])
        self.assertEqual(len(saved_rules['document']['rules']), 2)
        managed = rules('load', updated['metadata']['processCodes']['finish'])
        self.assertTrue(any(row['managed'] for row in managed['document']['rules']))
        with self.assertRaises(Fault):
            rules('save', managed['identity'], document={'rules': []}, expected_revision=managed['revision'])
        rules('save', work, document={'rules': []}, expected_revision=saved_rules['revision'])
        self.assertEqual(rules('load', work)['document']['rules'], [])
        shared = proxy.insert(ticket, 'sthpw/pipeline', dict(code='editor_shared_contract', project_code='', search_type='contract/entity', pipeline='<pipeline/>', name='Shared editor contract'))
        with self.store.connection('sthpw', write=True) as db:
            db.execute('UPDATE pipeline SET project_code=NULL WHERE code=?', (shared['code'],))
        readonly = workflow('load', identity=shared['code'])
        self.assertFalse(readonly['canWrite'])
        with self.assertRaises(Fault):
            workflow('save', identity=shared['code'], document=readonly['document'], expected_revision=readonly['revision'])
        proxy.insert(ticket, 'sthpw/login', dict(login='editor_reader', password=hash_password('reader-password')))
        reader = dict(ticket=proxy.get_ticket('editor_reader', 'reader-password'), project='one', language='python')
        with self.assertRaises(Fault):
            proxy.execute_cmd(reader, 'tactic.ui.panel.workflow_cmd.WorkflowCmd', dict(action='list', project_code='one'))
        with self.assertRaises(Fault):
            proxy.execute_cmd(reader, 'tactic.ui.panel.process_rules_cmd.ProcessRulesCmd', dict(action='load', project_code='one', identity=work))

    def test_schema_editor_command_and_creation_revision(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin', language='python')
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='schema_contract', project_title='Schema contract'))
        auth['project'] = 'schema_contract'
        schema_cmd = 'tactic.ui.panel.schema_cmd.SchemaCmd'
        types_cmd = 'tactic.ui.panel.search_types_cmd.SearchTypesCmd'
        def schema(action, **values):
            return proxy.execute_cmd(auth, schema_cmd, dict(action=action, project_code=auth['project'], **values))['info']
        def create(title, **values):
            return proxy.execute_cmd(auth, types_cmd, dict(action='save', project_code=auth['project'], document=dict(title=title), **values))['info']
        before = schema('load')
        parent = create('Schema parent', schema_revision=before['revision'])
        with self.assertRaises(Fault):
            create('Stale creation', schema_revision=before['revision'])
        self.assertFalse(any(row['identity'].endswith('/stale_creation') for row in schema('load')['metadata']['searchTypes']))
        child = create('Schema child')
        loaded = schema('load')
        draft = ET.fromstring(loaded['document']['xml'], parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
        draft.append(ET.Comment('authored comment'))
        draft.append(ET.Element('custom', {'preserve': 'yes'}))
        ET.SubElement(draft, 'connect', {'from': child['identity'], 'to': parent['identity'], 'relationship': 'code', 'type': 'hierarchy', 'from_col': 'parent_code', 'to_col': 'code'})
        document = {'xml': ET.tostring(draft, encoding='unicode')}
        with self.assertRaises(Fault):
            schema('save', document=document, expected_revision=loaded['revision'])
        self.assertNotIn('parent_code', proxy.get_column_names(auth, child['identity']))
        document['createColumns'] = [{'from': child['identity'], 'to': parent['identity'], 'path': ''}]
        saved = schema('save', document=document, expected_revision=loaded['revision'])
        self.assertIn('parent_code', proxy.get_column_names(auth, child['identity']))
        self.assertIn('authored comment', saved['document']['xml'])
        self.assertIn('preserve="yes"', saved['document']['xml'])
        with self.assertRaises(Fault):
            schema('save', document={'xml': '<schema/>'}, expected_revision=loaded['revision'])
        columns = schema('columns', search_types=[parent['identity'], child['identity']])
        self.assertTrue(columns[child['identity']]['tableAvailable'])
        arranged = schema('layout', document=saved['document'], style='flow')
        self.assertIn('authored comment', arranged['xml'])
        self.assertNotEqual(arranged['xml'], saved['document']['xml'])
        # A second absent key causes no partial DDL or XML publication.
        draft = ET.fromstring(saved['document']['xml'])
        draft.find('connect').set('from_col', 'another_code')
        ET.SubElement(draft, 'connect', {'from': parent['identity'], 'to': child['identity'], 'relationship': 'code', 'from_col': 'broken', 'to_col': 'not_present'})
        with self.assertRaises(Fault):
            schema('save', document={'xml': ET.tostring(draft, encoding='unicode'), 'createColumns': document['createColumns']}, expected_revision=saved['revision'])
        self.assertNotIn('another_code', proxy.get_column_names(auth, child['identity']))
        self.assertEqual(schema('load')['revision'], saved['revision'])
        with self.assertRaises(Fault):
            schema('save', document={'xml': '<schema><search_type name="schema_contract/schema_parent" xpos="NaN"/></schema>'}, expected_revision=saved['revision'])
        # M:N creates an instance with the opposite keys' actual SQL types.
        draft = ET.fromstring(saved['document']['xml'])
        instance = 'schema_contract/parent_in_child'
        ET.SubElement(draft, 'search_type', {'name': instance, 'type': 'instance', 'xpos': '200', 'ypos': '150'})
        for endpoint, column in [(parent['identity'], 'parent_code'), (child['identity'], 'child_code')]:
            ET.SubElement(draft, 'connect', {'from': instance, 'to': endpoint, 'from_col': column, 'to_col': 'code', 'relationship': 'code'})
        linked = schema('save', document={'xml': ET.tostring(draft, encoding='unicode'), 'newTypes': {instance: {}}}, expected_revision=saved['revision'])
        self.assertTrue(any(row['identity'] == instance for row in linked['metadata']['searchTypes']))
        self.assertIn('parent_code', proxy.get_column_names(auth, instance))
        self.assertIn('child_code', proxy.get_column_names(auth, instance))
        self.assertEqual(ast.literal_eval(proxy.query(auth, instance)), [])
        auth['project'] = 'admin'
        self.assertFalse(schema('load')['canWrite'])
        with self.assertRaises(Fault):
            schema('save', document={'xml': '<schema/>'}, expected_revision=schema('load')['revision'])
        reader = proxy.insert(auth, 'sthpw/login', {'login': 'schema_reader', 'password': hash_password('schema-reader-password')})
        auth.update(ticket=proxy.get_ticket('schema_reader', 'schema-reader-password'), project='schema_contract')
        with self.assertRaises(Fault):
            schema('load')
        auth.update(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin')
        proxy.delete_sobject(auth, reader['__search_key__'])

    def test_search_types_editor_command(self):
        proxy = self.proxy()
        ticket = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        command = 'tactic.ui.panel.search_types_cmd.SearchTypesCmd'
        def request(action, **values):
            return proxy.execute_cmd(ticket, command, dict(action=action, project_code='one') | values)['info']
        catalog = request('list')['catalog']
        self.assertTrue(any(row['identity'] == 'contract/entity' for row in catalog))
        created = request('save', document=dict(title='Editor contract', description='Created by command',
                                             columns=[dict(name='weight', type='integer')]))
        identity = created['identity']
        self.assertEqual(identity, 'one/editor_contract')
        self.assertIn('weight', created['metadata']['columns'])
        record = proxy.insert(ticket, identity, dict(name='Proof', weight=12))
        self.assertEqual(ast.literal_eval(proxy.query(ticket, identity))[0]['weight'], 12)
        retired = proxy.insert(ticket, identity, dict(name='Retired proof', s_status='retired'))
        pipelines = [proxy.insert(ticket, 'sthpw/pipeline', dict(code='summary_' + owner, name=owner,
                    project_code=owner if owner != 'shared' else '', search_type=identity,
                    pipeline='<pipeline>' + '<process name="work"/>' * count + '</pipeline>'))
                    for owner, count in [('one', 1), ('shared', 2), ('two', 3)]]
        summary = request('load', identity=identity)['metadata']
        self.assertEqual(summary['summary'], dict(total=2, active=1, retired=1,
                         fields=len(summary['columns']), pipelines=2, processes=3))
        self.assertTrue(summary['projectLocal'])
        self.assertEqual(summary['relationshipGraph']['center'], identity)
        self.assertEqual(len(summary['relationshipGraph']['nodes']), 1)
        for pipeline in pipelines:
            proxy.delete_sobject(ticket, pipeline['__search_key__'])
        proxy.delete_sobject(ticket, retired['__search_key__'])
        link = request('load', identity='contract/entity_in_collection')['metadata']
        graph = link['relationshipGraph']
        self.assertTrue(link['linkTable'])
        self.assertEqual({node['identity'] for node in graph['nodes']},
                         {'contract/entity_in_collection', 'contract/entity', 'contract/collection'})
        self.assertEqual({(edge['from'], edge['to']) for edge in graph['edges']},
                         {('contract/collection', 'contract/entity_in_collection'),
                          ('contract/entity_in_collection', 'contract/collection'),
                          ('contract/entity_in_collection', 'contract/entity')})
        self.assertEqual(len(graph['edges']), 3)
        self.assertTrue(all(edge['from'] != edge['to'] for edge in graph['edges']))
        self.assertTrue(any('M:N' in edge['label'] for edge in graph['edges']))
        inherited = request('load', identity='contract/entity')['metadata']
        self.assertTrue(any(edge['from'] == 'contract/inherited' and edge['schema'] == 'base'
                            for edge in inherited['relationships']))
        self.assertFalse(request('load', identity='sthpw/login')['metadata']['projectLocal'])
        # Native pipeline triggers may add pipeline_code to the associated table.
        current_revision = request('load', identity=identity)['revision']
        changed = request('save', identity=identity, expected_revision=current_revision,
                          document=dict(title='Edited title', columns=[dict(name='comment', type='text')]))
        self.assertIn('comment', changed['metadata']['columns'])
        with self.assertRaises(Fault):
            request('save', identity=identity, expected_revision=created['revision'],
                    document=dict(title='Stale title', columns=[dict(name='stale', type='integer')]))
        fresh = request('load', identity=identity)
        self.assertEqual(fresh['document']['title'], 'Edited title')
        self.assertNotIn('stale', fresh['metadata']['columns'])
        with self.assertRaises(Fault):
            request('save', document=dict(title='Invalid editor', columns=[dict(name='bad', type='invalid')]))
        self.assertFalse(any(row['identity'] == 'one/invalid_editor' for row in request('list')['catalog']))
        config = proxy.insert(ticket, 'config/widget_config', dict(search_type=identity, view='definition',
            config='<config><definition><element name="weight"/><element name="comment"/></definition></config>'))
        with self.store.connection('one', write=True) as db:
            db.execute('CREATE INDEX editor_comment_index ON editor_contract (comment)')
        with self.assertRaises(Fault):
            request('save', identity=identity, expected_revision=changed['revision'],
                    document=dict(title='Must roll back', removedColumns=['weight', 'comment']))
        fresh = request('load', identity=identity)
        self.assertEqual(fresh['document']['title'], 'Edited title')
        self.assertIn('weight', fresh['metadata']['columns'])
        self.assertEqual(ast.literal_eval(proxy.query(ticket, identity))[0]['weight'], 12)
        self.assertIn('name="weight"', proxy.get_by_search_key(ticket, config['__search_key__'])['config'])
        with self.store.connection('one', write=True) as db:
            db.execute('DROP INDEX editor_comment_index')
        for column in ('id', 'code', 'pipeline_code'):
            with self.assertRaises(Fault):
                request('save', identity=identity, expected_revision=fresh['revision'],
                        document=dict(title='Must not save', removedColumns=[column]))
        removed = request('save', identity=identity, expected_revision=fresh['revision'],
            document=dict(title='Edited title', removedColumns=['weight'], columns=[dict(name='price', type='numeric')]))
        self.assertNotIn('weight', removed['metadata']['columns'])
        self.assertEqual(removed['metadata']['columns']['price']['data_type'], 'numeric')
        self.assertNotIn('name="weight"', proxy.get_by_search_key(ticket, config['__search_key__'])['config'])
        self.assertIn('name="comment"', proxy.get_by_search_key(ticket, config['__search_key__'])['config'])
        with self.store.connection() as db:
            journal = db.execute('SELECT id FROM transaction_log ORDER BY id DESC LIMIT 1').fetchone()
        proxy.undo(ticket, None, journal['id'])
        restored = request('load', identity=identity)
        self.assertIn('weight', restored['metadata']['columns'])
        self.assertNotIn('price', restored['metadata']['columns'])
        self.assertEqual(ast.literal_eval(proxy.query(ticket, identity))[0]['weight'], 12)
        self.assertIn('name="weight"', proxy.get_by_search_key(ticket, config['__search_key__'])['config'])
        proxy.redo(ticket, None, journal['id'])
        self.assertNotIn('weight', request('load', identity=identity)['metadata']['columns'])
        self.assertNotIn('name="weight"', proxy.get_by_search_key(ticket, config['__search_key__'])['config'])
        with self.assertRaises(Fault):
            request('save', identity=identity, expected_revision=fresh['revision'],
                    document=dict(title='Stale deletion', removedColumns=['comment']))
        self.assertIn('comment', request('load', identity=identity)['metadata']['columns'])
        reader = proxy.insert(ticket, 'sthpw/login', {'login': 'column_reader', 'password': hash_password('private-column-reader')})
        reader_auth = dict(ticket=proxy.get_ticket('column_reader', 'private-column-reader'), project='one')
        with self.assertRaises(Fault):
            proxy.execute_cmd(reader_auth, 'tactic.ui.panel.AlterSearchTypeCbk', {'alter_mode': 'Remove Column'},
                {'target_search_type': identity, 'column_name': 'comment'})
        self.assertIn('comment', request('load', identity=identity)['metadata']['columns'])
        proxy.delete_sobject(ticket, reader['__search_key__'])
        with self.assertRaises(Fault):
            proxy.execute_cmd(dict(ticket='invalid', project='one'), command, dict(action='list', project_code='one'))
        with self.assertRaises(Fault):
            request('list', project_code='two')
        proxy.delete_sobject(ticket, record['__search_key__'])
        proxy.delete_sobject(ticket, config['__search_key__'])

    def test_native_deletion_security_selection_and_xml_operations(self):
        from tactic_stream.server.api import Api
        api = Api(self.store)
        token = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='one')
        kind = 'one/native_operations'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                                    dict(search_type_name=kind, asset_title='Native operation items')))
        record = api.dispatch('insert', (auth, kind, dict(name='Native deletion')))
        note = api.dispatch('create_note', (auth, record['__search_key__'], 'Must survive unchecked deletion'))
        def request(action, **changes):
            payload = dict(ticket=token, project='one', search_type=kind, search_key=record['__search_key__'])
            payload.update(changes)
            request = Request(self.url + '/admin/object-deletion/' + action, json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'})
            try:
                with urlopen(request) as response:
                    return response.status, json.load(response)
            except HTTPError as response:
                with response:
                    return response.code, json.load(response)
        status, result = request('read')
        self.assertEqual(status, 200, result)
        self.assertEqual(next(group['count'] for group in result['result']['groups'] if group['search_type'] == 'sthpw/note'), 1)
        self.assertEqual(request('read', ticket='invalid')[0], 403)
        self.assertEqual(request('read', search_key=record['__search_key__'].replace('project=one', 'project=two'))[0], 400)
        self.assertEqual(request('apply', related_types=['sthpw/login'])[0], 400)
        self.assertEqual(request('apply', related_types='sthpw/note')[0], 400)
        self.assertIsNotNone(api.dispatch('get_by_search_key', (auth, record['__search_key__'])))
        from tactic.ui.tools import DeleteCmd
        delete = DeleteCmd.do_delete
        def interrupted(command, target, related_types=None):
            delete(command, target, related_types)
            raise ValueError('Forced deletion interruption')
        with patch.object(DeleteCmd, 'do_delete', interrupted):
            self.assertEqual(request('apply', related_types=['sthpw/note'])[0], 400)
        self.assertIsNotNone(api.dispatch('get_by_search_key', (auth, record['__search_key__'])))
        self.assertIsNotNone(api.dispatch('get_by_search_key', (auth, note['__search_key__'])))
        self.assertEqual(request('apply', related_types=[])[0], 200)
        with self.assertRaisesRegex(LookupError, 'SObject does not exist'):
            api.dispatch('get_by_search_key', (auth, record['__search_key__']))
        self.assertIsNotNone(api.dispatch('get_by_search_key', (auth, note['__search_key__'])))
        api.dispatch('delete_sobject', (auth, note['__search_key__']))
        from pyasm.search.search import RequestContext, request_context
        from tactic_stream.server.interface import read_interface
        config = api.dispatch('insert', (auth, 'config/widget_config', dict(search_type=kind, view='operations_test',
            config='<config><operations_test edit="false" insert="false" delete="false" retire="false"><element name="name"/></operations_test></config>')))
        with request_context(RequestContext(self.store, 'admin', 'one')):
            api.auth.bind_security('admin', token)
            operations = read_interface(kind, 'operations_test')['operations']
            self.assertEqual({name: operations[name] for name in ('edit', 'create', 'retire', 'delete')},
                             dict(edit=False, create=False, retire=False, delete=False))
        api.dispatch('delete_sobject', (auth, config['__search_key__']))

    def test_native_batch_operations_atomic_selection(self):
        from tactic_stream.server.api import Api
        from pyasm.search import SObject
        api = Api(self.store)
        token = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='one')
        kind = 'one/batch_operations'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                                    dict(search_type_name=kind, asset_title='Batch operation items')))
        records = [api.dispatch('insert', (auth, kind, dict(name=name))) for name in ('First', 'Second')]
        keys = [record['__search_key__'] for record in records]
        def request(path, **changes):
            payload = dict(ticket=token, project='one', search_type=kind, search_keys=keys)
            if path == '/admin/object-status':
                payload['operation'] = 'retire'
            payload.update(changes)
            try:
                with urlopen(Request(self.url + path, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
                    return response.status, json.load(response)
            except HTTPError as response:
                with response:
                    return response.code, json.load(response)
        self.assertEqual(request('/admin/object-status', ticket='invalid')[0], 403)
        self.assertEqual(request('/admin/object-status', search_keys=[])[0], 400)
        self.assertEqual(request('/admin/object-status', search_keys=[keys[0], keys[1].replace('project=one', 'project=two')])[0], 400)
        retire = SObject.retire
        def interrupted(record):
            retire(record)
            if record.get_id() == records[1]['id']:
                raise ValueError('Forced batch interruption')
        with patch.object(SObject, 'retire', interrupted):
            self.assertEqual(request('/admin/object-status')[0], 400)
        for key in keys:
            self.assertNotEqual(api.dispatch('get_by_search_key', (auth, key))['s_status'], 'retired')
        alias = kind + '?project=one&id=' + str(records[0]['id'])
        status, result = request('/admin/object-status', search_keys=[*keys, alias])
        self.assertEqual(status, 200, result)
        self.assertEqual(result['result']['count'], 2)
        self.assertEqual(request('/admin/object-status')[1]['result']['count'], 0)
        self.assertEqual(request('/admin/object-status', operation='reactivate')[1]['result']['count'], 2)
        for key in keys:
            api.dispatch('create_note', (auth, key, 'Batch dependency'))
        # One DeleteCmd owns every source and dependency; a late failure restores all of them.
        from tactic.ui.tools import DeleteCmd
        delete = DeleteCmd.do_delete
        def interrupted_delete(command, record, related_types=None):
            delete(command, record, related_types)
            if record.get_id() == records[1]['id']:
                raise ValueError('Forced batch deletion interruption')
        with patch.object(DeleteCmd, 'do_delete', interrupted_delete):
            self.assertEqual(request('/admin/object-deletion/apply', related_types=['sthpw/note'])[0], 400)
        for key in keys:
            self.assertIsNotNone(api.dispatch('get_by_search_key', (auth, key)))
        self.assertEqual(next(group['count'] for group in request('/admin/object-deletion/read')[1]['result']['groups']
                              if group['search_type'] == 'sthpw/note'), 2)
        payload = dict(ticket=token, project='one', search_type=kind, search_keys=[*keys, alias], related_types=['sthpw/note'])
        with urlopen(Request(self.url + '/admin/object-deletion/apply', json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(len(json.load(response)['result']['search_keys']), 2)
        for key in keys:
            with self.assertRaises(LookupError):
                api.dispatch('get_by_search_key', (auth, key))

    def test_related_forms_original_commands_connections_and_rollback(self):
        from tactic_stream.server.api import Api
        from pyasm.biz import SObjectConnection
        from tactic.ui.panel import EditCmd
        api = Api(self.store)
        token = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='one')
        parent = 'contract/entity?project=one&code=A'
        other = 'contract/entity?project=one&code=B'
        kind = 'one/related_forms'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
            search_type_name=kind, asset_title='Related items', column_name=['entity_code'], data_type=['varchar'],
            sobject_parent='contract/entity')))
        for view in ('insert', 'edit'):
            configs = api.dispatch('query', (auth, 'config/widget_config'), dict(filters=[['search_type', kind], ['view', view]]))
            configs = ast.literal_eval(configs) if isinstance(configs, str) else configs
            xml = '<config><%s><element name="name"/><element name="entity_code"/></%s></config>' % (view, view)
            for config in configs:
                api.dispatch('update', (auth, config['__search_key__'], dict(config=xml)))
        def native(path='/admin/form', **changes):
            payload = dict(ticket=token, project='one', search_type=kind, view='insert', parent_key=parent)
            if path == '/admin/object-relations':
                payload = dict(ticket=token, project='one', search_type='contract/entity', search_key=parent)
            payload.update(changes)
            try:
                with urlopen(Request(self.url + path, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
                    return response.status, json.load(response)
            except HTTPError as response:
                with response:
                    return response.code, json.load(response)
        status, result = native('/admin/object-relations')
        self.assertEqual(status, 200, result)
        relation = next(item for item in result['result']['relations'] if item['search_type'] == kind)
        self.assertTrue(relation['available'])
        self.assertTrue(relation['can_create'])
        self.assertFalse(next(item for item in result['result']['relations'] if item['search_type'] == 'contract/collection')['available'])
        status, result = native(connect_key=other)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['result']['parent_key'], parent)
        self.assertNotIn('entity_code', [item['name'] for item in result['result']['fields']])
        for changes in (dict(parent_key=parent.replace('project=one', 'project=two')), dict(parent_key='sthpw/login?code=admin'),
                        dict(parent_key='missing'), dict(view='edit'), dict(connect_key=other.replace('project=one', 'project=two'))):
            self.assertEqual(native(**changes)[0], 400, changes)
        self.assertEqual(native(ticket='invalid')[0], 403)
        proxy = self.proxy()
        args = dict(view='insert', parent_key=parent, connect_key=other, element_names=['name'])
        values = dict(search_type=kind, search_id='-1', **{'edit|name': 'Connected child'})
        created = proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, values)['info']['sobject']
        self.assertEqual(created['entity_code'], 'A')
        self.assertEqual([item['code'] for item in proxy.get_connected_sobjects(auth, created['__search_key__'], 'task')], ['B'])
        script = 'from pyasm.search import Search\nreturn [obj.get_code() for obj in Search.get_by_search_key(kwargs["key"]).get_connections("task")]'
        self.assertEqual(proxy.execute_python_script(auth, '', dict(code=script, key=created['__search_key__']))['info'], ['B'])
        self.assertEqual([item['code'] for item in ast.literal_eval(proxy.query(auth, kind, [], None, [], False, None, None, False, None, False, parent))], [created['code']])
        create_connection = SObjectConnection.create
        def interrupted(*args, **kwargs):
            create_connection(*args, **kwargs)
            raise ValueError('Forced connection interruption')
        with patch.object(SObjectConnection, 'create', interrupted):
            with self.assertRaises(Fault):
                proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, {**values, 'edit|name': 'Must roll back'})
        self.assertEqual(ast.literal_eval(proxy.query(auth, kind, [['name', 'Must roll back']])), [])
        self.assertEqual(len(proxy.get_connected_sobjects(auth, other, 'task')), 1)
        # query(parent_key) must select by search_id when a reference has no search_code.
        ref = api.dispatch('insert', (auth, 'contract/id_ref', dict(code='RELATED_ID', search_type='contract/entity?project=one', search_id=1)))
        found = ast.literal_eval(proxy.query(auth, 'contract/id_ref', [], None, [], False, None, None, False, None, False, parent))
        self.assertIn(ref['code'], [item['code'] for item in found])
        without_code = 'contract/id_entity?project=one&id=1'
        found = ast.literal_eval(proxy.query(auth, 'contract/id_ref', [], None, [], False, None, None, False, None, False, without_code))
        self.assertIn('IR1', [item['code'] for item in found])
        self.assertEqual(native(search_type='contract/id_child', connect_key=None)[0], 200)
        by_id = proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd',
            dict(view='insert', parent_key=parent, data={'name': 'Id child'}),
            dict(search_type='contract/id_child', search_id='-1'))['info']['sobject']
        self.assertEqual(by_id['entity_id'], 1)
        api.dispatch('insert', (auth, 'sthpw/login', dict(login='related_reader', code='related_reader', password=hash_password('private-test-password'))))
        reader = api.get_ticket('related_reader', 'private-test-password')
        self.assertEqual(native('/admin/object-relations', ticket=reader)[0], 403)
        with self.assertRaises(Fault):
            proxy.execute_cmd(dict(ticket=reader, project='one'), 'tactic.ui.panel.EditCmd', args, values)

    def test_batch_edit_selected_fields_and_rollback(self):
        from tactic_stream.server.api import Api
        from tactic.ui.panel import EditCmd
        api = Api(self.store)
        token = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='one')
        kind = 'one/batch_edit'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
            search_type_name=kind, asset_title='Batch edit items', column_name=['amount', 'active', 'keywords'],
            data_type=['integer', 'boolean', 'varchar'])))
        xml = '''<config><edit><element name="name"/><element name="description"/>
          <element name="amount"/><element name="active"><display class="pyasm.widget.CheckboxWdg"/></element>
          <element name="keywords"><display class="pyasm.widget.MultiSelectWdg"><values>a|b</values></display>
            <action class="pyasm.command.MultiDatabaseAction"/></element></edit></config>'''
        api.dispatch('insert', (auth, 'config/widget_config', dict(search_type=kind, view='edit', config=xml)))
        records = [api.dispatch('insert', (auth, kind, dict(name=name, description=name, amount=index+5,
            active=True, keywords='a'))) for index, name in enumerate(('First', 'Second'))]
        keys = [record['__search_key__'] for record in records]
        def form(**changes):
            payload = dict(ticket=token, project='one', search_type=kind, search_keys=keys)
            payload.update(changes)
            try:
                with urlopen(Request(self.url + '/admin/form', json.dumps(payload).encode(),
                                    headers={'Content-Type': 'application/json'})) as response:
                    return response.status, json.load(response)
            except HTTPError as response:
                with response:
                    return response.code, json.load(response)
        status, result = form(search_keys=[*keys, kind+'?project=one&id='+str(records[0]['id'])])
        self.assertEqual(status, 200, result)
        self.assertEqual(len(result['result']['search_keys']), 2)
        fields = {field['name']: field for field in result['result']['fields']}
        self.assertTrue(fields['amount']['mixed'])
        self.assertFalse(fields['active']['mixed'])
        for changes in (dict(search_keys=[]), dict(search_keys=keys[0]), dict(search_key=keys[0]),
                        dict(source_key=keys[0]), dict(view='insert'), dict(search_keys=[keys[0], keys[1].replace('project=one', 'project=two')])):
            self.assertEqual(form(**changes)[0], 400, changes)
        proxy = self.proxy()
        update = dict(description='', amount=0, active=False, keywords=['b', 'a'])
        args = dict(view='edit', search_keys=keys, update_data=json.dumps([update, update]),
                    extra_data='[{},{}]', extra_action='[{},{}]')
        execute = EditCmd.execute
        completed = []
        def interrupted(command):
            execute(command)
            completed.append(command.search_key)
            if command.search_key == keys[1]:
                raise ValueError('Forced batch edit interruption')
        with patch.object(EditCmd, 'execute', interrupted):
            with self.assertRaises(Fault):
                proxy.execute_cmd(auth, 'tactic.ui.panel.EditMultipleCmd', args, {})
        self.assertEqual(completed, keys)
        for index, key in enumerate(keys):
            record = proxy.get_by_search_key(auth, key)
            self.assertEqual(record['description'], records[index]['description'])
            self.assertEqual(record['amount'], index+5)
            self.assertTrue(record['active'])
        result = proxy.execute_cmd(auth, 'tactic.ui.panel.EditMultipleCmd', args, {})
        self.assertEqual(len(result['info']['search_keys']), 2)
        for index, key in enumerate(keys):
            record = proxy.get_by_search_key(auth, key)
            self.assertEqual(record['name'], records[index]['name'])
            self.assertEqual(record['code'], records[index]['code'])
            self.assertEqual((record['description'], record['amount'], record['active'], record['keywords']),
                             (None, 0, False, '||a||b||'))
        # An empty list clears tags; it must not become a nested list in DatabaseAction.
        args['update_data'] = json.dumps([dict(keywords=[]), dict(keywords=[])])
        proxy.execute_cmd(auth, 'tactic.ui.panel.EditMultipleCmd', args, {})
        self.assertIsNone(proxy.get_by_search_key(auth, keys[0])['keywords'])
        api.dispatch('insert', (auth, 'sthpw/login', dict(login='batch_reader', code='batch_reader',
            password=hash_password('private-test-password'))))
        reader = api.get_ticket('batch_reader', 'private-test-password')
        self.assertEqual(form(ticket=reader)[0], 403)
        with self.assertRaises(Fault):
            proxy.execute_cmd(dict(ticket=reader, project='one'), 'tactic.ui.panel.EditMultipleCmd', args, {})

    def test_search_object_creation_form(self):
        proxy = self.proxy()
        token = proxy.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='admin')
        def form(view='insert', key=None):
            payload = dict(ticket=token, project='admin', search_type='sthpw/search_object',
                           view=view, search_key=key)
            with urlopen(Request(self.url + '/admin/form', json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})) as response:
                return json.load(response)['result']
        definition = form()
        color = next(field for field in definition['fields'] if field['name'] == 'color')
        self.assertEqual(color['class_name'], 'tactic.ui.input.color_input_wdg.ColorInputWdg')
        self.assertRegex(color['input']['value'], '^#[0-9a-f]{6}$')
        args = dict(view=definition['view'], input_prefix=definition['input_prefix'],
                    element_names=[field['name'] for field in definition['fields']])
        document = dict(search_type='contract/color_form', namespace='contract', description='Color form',
                        database='{project}', table_name='color_form', class_name='pyasm.search.SObject', color='#123abc')
        values = dict(search_type='sthpw/search_object', search_id='-1')
        values.update({definition['input_prefix'] + '|' + field['name']: document.get(field['name'], '')
                       for field in definition['fields']})
        result = proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, values)['info']
        key = result['search_key']
        self.assertEqual(proxy.get_by_search_key(auth, key)['color'], '#123abc')
        edited = form('edit', key)
        self.assertEqual(next(field for field in edited['fields'] if field['name'] == 'color')['input']['value'], '#123abc')
        args.update(view=edited['view'], search_key=key, element_names=['color'])
        proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, {edited['input_prefix'] + '|color': ''})
        self.assertFalse(proxy.get_by_search_key(auth, key)['color'])
        # Single start_color was broken by the original comma condition; preserve
        # the original palette/override behavior while accepting one color too.
        script = """from tactic.ui.input import ColorInputWdg
from pyasm.web import Web, WebContainer
WebContainer.set_web(Web())
single = ColorInputWdg(name='color', start_color='#456abc')
single.set_input_prefix('insert')
palette = ColorInputWdg(name='color', start_color='#111111,#222222')
return {'single': single.get_input().get_value(), 'name': single.get_input().get_name(),
        'palette': palette.get_input().get_value()}
"""
        prepared = proxy.execute_python_script(auth, '', dict(code=script))['info']
        self.assertEqual(prepared['single'], '#456abc')
        self.assertEqual(prepared['name'], 'insert|color')
        self.assertIn(prepared['palette'], ('#111111', '#222222'))

    def test_edit_form_original_client_and_handler_script(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_form_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('forms_rpc','Forms RPC','sthpw')")
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('forms_rpc')
        token = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(token)
        self.addCleanup(client.server.__exit__, None, None, None)
        kind = 'forms_rpc/item'
        client.create_search_type(kind, 'Form item')
        client.update_config(kind, 'form_test', ['name', 'description'])
        record = client.insert(kind, dict(code='FORM1', name='Original'))
        payload = dict(ticket=token, project='forms_rpc', search_type=kind, view='form_test', search_key=record['__search_key__'])
        def form(**changes):
            body = dict(payload, **changes)
            with urlopen(Request(self.url + '/admin/form', json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                return json.load(response)['result']
        description = form()
        self.assertEqual([item['name'] for item in description['fields']], ['name', 'description'])
        self.assertEqual(description['fields'][0]['values'], ['Original'])
        result = client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=record['__search_key__'],
            view='form_test', element_names=['name']), values={'edit|name': 'Changed'})
        self.assertEqual(result['info']['action'], 'Updated')
        self.assertEqual(client.get_by_search_key(record['__search_key__'])['name'], 'Changed')
        # Execute the existing Handler procedure body without importing/modifying its GUI.
        path = Path('D:/grav/Tactic Stream/TH/thlib/tactic_query.py')
        source = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'query_EditWdg')
        code = ast.get_source_segment(source, function)
        code += '\nreturn query_EditWdg(args=kwargs["form_args"], search_type=kwargs["kind"])'
        result = client.execute_python_script('', kwargs=dict(code=code, kind=kind,
            form_args=dict(search_type=kind, search_key=record['__search_key__'], view='form_test')))
        data = json.loads(result['info'])
        self.assertEqual(data['EditWdg']['element_names'], ['name', 'description'])
        self.assertEqual(data['InputWidgets'][0]['__display_values__'], ['Changed'])
        self.assertEqual(data['InputWidgets'][0]['class_name'], 'pyasm.widget.input_wdg.TextWdg')
        self.assertEqual(form()['fields'][0]['values'], ['Changed'])
        client.add_column_to_search_type(kind, 'deadline', 'timestamp')
        client.update_config(kind, 'calendar_test', ['deadline'])
        client.add_config_element(kind, 'calendar_test', 'deadline',
                                  class_name='tactic.ui.widget.CalendarInputWdg', display_options={'show_time': 'true'}, unique=False)
        client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(search_key=record['__search_key__'],
            view='calendar_test', element_names=['deadline']), values={'edit|deadline': '2026-11-02T01:30:15.250Z'})
        data = json.loads(client.execute_python_script('', kwargs=dict(code=code, kind=kind,
            form_args=dict(search_type=kind, search_key=record['__search_key__'], view='calendar_test')))['info'])
        self.assertEqual(data['InputWidgets'][0]['class_name'], 'tactic.ui.widget.calendar_wdg.CalendarInputWdg')
        self.assertEqual(data['InputWidgets'][0]['__display_values__'], ['2026-11-02 01:30:15.250000'])
        inserted = client.execute_cmd('tactic.ui.panel.EditCmd', args=dict(view='form_test', data={'name': 'New item'}),
            values={'search_type': kind, 'search_id': '-1'})
        self.assertEqual(inserted['info']['action'], 'Inserted')
        self.assertEqual(client.get_by_search_key(inserted['info']['search_key'])['name'], 'New item')
        for changes in (dict(ticket='invalid'), dict(search_key='sthpw/project?code=admin'),
                        dict(search_key=kind + '?project=two&code=FORM1'), dict(default=[])):
            with self.assertRaises(HTTPError) as caught:
                form(**changes)
            self.assertIn(caught.exception.code, (400, 403))
            caught.exception.close()
        client.insert('sthpw/login', dict(login='forms_reader', code='forms_reader',
                                        password=hash_password('private-test-password')))
        reader = client.get_ticket('forms_reader', 'private-test-password')
        with self.assertRaises(HTTPError) as caught:
            form(ticket=reader)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()

    def test_creator_views_refresh_from_original_xmlrpc(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_views_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('views_rpc','Views RPC','sthpw')")
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('views_rpc')
        token = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(token)
        self.addCleanup(client.server.__exit__, None, None, None)
        kind = 'views_rpc/ui_item'
        client.execute_cmd('tactic.core.schema_commands.SearchTypeCreatorCmd',
                           dict(search_type_name=kind, asset_title='Items & jobs'))
        client.insert(kind, dict(code='UI_ROW', name='First item'))
        def read(**changes):
            payload = dict(ticket=token, project='views_rpc', search_type=kind)
            payload.update(changes)
            with urlopen(Request(self.url + '/admin/interface', json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                return json.load(response)['result']
        definition = read()
        self.assertEqual(definition['schema_version'], 1)
        self.assertEqual([item['name'] for item in definition['table']['elements']], ['name', 'description', 'data', 'notes'])
        self.assertIn('code', definition['columns'])
        link = next(item for item in definition['navigation']['elements'] if item['name'] == 'ui_item_list')
        self.assertEqual(link['title'], 'Items & jobs')
        self.assertEqual(link['display']['options']['search_type'], kind)
        client.update_config(kind, 'table', ['description', 'name'])
        client.add_config_element(kind, 'definition', 'name', class_name='custom.missing.Display',
                                  element_attrs={'title': 'Renamed & safe'}, display_options={'column': 'name'})
        changed = read()
        self.assertEqual([item['name'] for item in changed['table']['elements']], ['description', 'name'])
        self.assertEqual(changed['table']['elements'][1]['title'], 'Renamed & safe')
        self.assertEqual(changed['table']['elements'][1]['display']['handler'], 'custom.missing.Display')
        client.update_config(kind, 'table', [])
        # Explicitly empty view must stay empty; update_config([]) retains an existing view.
        for record in client.query('config/widget_config', [['search_type', kind], ['view', 'table']]):
            client.update(record['__search_key__'], {'config': '<config><table/></config>'})
        self.assertTrue(read()['table']['configured'])
        self.assertEqual(read()['table']['elements'], [])
        for changes in ({'ticket': 'invalid'}, {'view': "table/element[@name='secret']"},
                        {'view': 'missing_view'}, {'project': 'missing'}, {'search_type': kind + '?project=one'}):
            with self.assertRaises(HTTPError) as caught:
                read(**changes)
            self.assertIn(caught.exception.code, (400, 403))
            caught.exception.close()
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO login (code,login,password) SELECT 'view_reader','view_reader',password FROM login WHERE login='admin'")
        user = self.admin_rpc('get_ticket', ['view_reader', 'private-test-password'])
        with self.assertRaises(HTTPError) as caught:
            read(ticket=user)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()

    def test_original_client_search_type_template_and_pipeline(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_template_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        import schema_template_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('template_rpc','Template RPC','sthpw')")
            schema_template_contract.install_fixture(db)
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('template_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        child = 'contract/rpc_template_copy'
        args = dict(search_type_name=child, copy_from_template='contract/tmpl_original')
        client.execute_cmd('tactic.core.schema_commands.SearchTypeCreatorCmd', args)
        self.assertEqual(client.query(child), [])
        row = client.insert(child, dict(code='RPC_COPY'))
        self.assertEqual([row['id'], row['name'], row['tmpl_original_value'], row['active']], [1, 'tmpl_original', 7, False])
        self.assertEqual(len(client.query('contract/tmpl_original')), 1)
        with self.assertRaises(Fault):
            client.execute_cmd('tactic.core.schema_commands.SearchTypeCreatorCmd', args)
        self.assertEqual(len(client.query(child)), 1)
        with self.assertRaises(Fault):
            client.insert(child, dict(code='NEGATIVE', tmpl_original_value=-1))
        client.execute_cmd('tactic.core.schema_commands.SearchTypeCreatorCmd',
                           dict(search_type_name='contract/rpc_pipeline', sobject_pipeline=True, process=['model', 'Review & approve']))
        graph = client.get_by_code('sthpw/pipeline', 'template_rpc/rpc_pipeline')
        tree = ET.fromstring(graph['pipeline'])
        self.assertEqual([node.get('name') for node in tree.findall('process')], ['model', 'Review & approve'])
        self.assertEqual([node.attrib for node in tree.findall('connect')], [{'from': 'model', 'to': 'Review & approve'}])
        processes = client.query('config/process', [['pipeline_code', graph['code']]], order_bys=['sort_order'])
        self.assertEqual([row['process'] for row in processes], ['model', 'Review & approve'])
        self.assertEqual([row['sort_order'] for row in processes], [1, 2])
        self.assertEqual(len(client.query('config/naming', [['search_type', child]])), 1)

    def test_original_client_schema_editor_commands(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_schema_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('schema_rpc','Schema RPC','sthpw')")
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('schema_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        child, parent = 'schema_rpc/rpc_schema_child', 'schema_rpc/rpc_schema_parent'
        client.execute_cmd('tactic.ui.tools.SchemaSaveCmd', dict(from_search_type='rpc_schema_child', to_search_type='rpc_schema_parent'))
        connector = dict(left_search_type=child, left='rpc_schema_parent_code', right_search_type=parent, right='code')
        client.execute_cmd('tactic.ui.tools.SchemaConnectorCbk', connector)
        client.execute_cmd('tactic.ui.tools.schema_wdg.SchemaConnectorCbk', connector)
        self.assertIn('rpc_schema_parent_code', client.get_column_names(child))
        first = client.insert(parent, dict(code='RPC_PARENT', name='Parent'))
        second = client.insert(child, dict(code='RPC_CHILD'), parent_key=first['__search_key__'])
        self.assertEqual(second['rpc_schema_parent_code'], 'RPC_PARENT')
        config = client.query('config/widget_config', [['search_type', child], ['view', 'edit_definition']])
        self.assertEqual(len(config), 1)
        tree = ET.fromstring(config[0]['config'])
        self.assertEqual(len(tree.findall('edit_definition')), 1)
        self.assertEqual([node.text for node in tree.findall('.//values_expr')], ['@GET(%s.code)' % parent] * 2)
        with self.assertRaises(Fault):
            client.execute_cmd('tactic.ui.tools.SchemaConnectorCbk', dict(connector, left='bad column', right='must_not_exist'))
        self.assertNotIn('must_not_exist', client.get_column_names(parent))

    def test_original_client_parent_and_collections(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_collection_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        import collection_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title) VALUES ('collection_transport','Collection transport')")
            collection_contract.install_fixture(db, project='collection_transport')
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('collection_transport')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        root = client.insert('contract/collect', {'code': 'TRANSPORT_ROOT', 'name': 'Root', '_is_collection': True})
        child = client.insert('contract/parent_child', {'code': 'TRANSPORT_CHILD'}, parent_key=root['__search_key__'])
        self.assertEqual(child['collect_code'], root['code'])
        # The stock SDK's insert wrapper predates the API's collection_key.
        member = client.server.insert(client.ticket, 'contract/collect', {'code': 'TRANSPORT_MEMBER'}, {}, None, {}, False, True, root['__search_key__'])
        self.assertEqual(len(client.query('contract/collect_in_collect', [('search_code', member['code'])])), 1)
        with self.assertRaises(Fault):
            client.server.insert(client.ticket, 'contract/collect', {'code': 'TRANSPORT_BAD'}, {}, None, {}, False, True, member['__search_key__'])
        self.assertEqual(client.query('contract/collect', [('code', 'TRANSPORT_BAD')]), [])
        # The original creator flag adds the marker, not a fabricated junction.
        client.execute_cmd('tactic.core.schema_commands.SearchTypeCreatorCmd',
            {'database': 'collection_transport', 'search_type_name': 'contract/collection_created', 'sobject_collection': True})
        self.assertIn('_is_collection', client.get_column_names('contract/collection_created'))
        sub = client.insert('contract/collect', {'code': 'TRANSPORT_SUB', 'name': 'Sub', '_is_collection': True})
        added = client.execute_cmd('tactic.ui.panel.CollectionAddCmd',
            {'collection_keys': [root['__search_key__']], 'search_keys': [sub['__search_key__']]})
        self.assertEqual(added['info']['message'], {'Root': 'Insert OK'})
        circular = client.execute_cmd('tactic.ui.panel.collection_wdg.CollectionAddCmd',
            {'collection_keys': [sub['__search_key__']], 'search_keys': [root['__search_key__']]})
        self.assertEqual(circular['info']['message']['circular'], 'True')
        client.execute_cmd('tactic.ui.panel.CollectionRemoveCmd',
            {'collection_key': root['__search_key__'], 'search_keys': [member['__search_key__']]})
        from concurrent.futures import ThreadPoolExecutor
        def add_concurrently():
            with ServerProxy(self.url + '/tactic/default/Api/', allow_none=True) as proxy:
                return proxy.execute_cmd(client.ticket, 'tactic.ui.panel.CollectionAddCmd',
                    {'collection_keys': [root['__search_key__']], 'search_keys': [member['__search_key__']]})
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: add_concurrently(), range(2)))
        self.assertEqual(sorted(result['info']['message']['Root'] for result in results), ['Insert OK', 'No insert'])
        self.assertEqual(len(client.query('contract/collect_in_collect', [('parent_code', root['code']), ('search_code', member['code'])])), 1)
        client.execute_cmd('tactic.core.collection_commands.CollectionAddCmd',
            {'collection_keys': [sub['__search_key__']], 'search_keys': [member['__search_key__']]})
        client.execute_cmd('tactic.ui.panel.collection_wdg.CollectionDeleteCmd', {'collection_key': sub['__search_key__']})
        self.assertEqual(client.query('contract/collect', [('code', sub['code'])]), [])
        self.assertEqual(client.query('contract/collect_in_collect', [('parent_code', sub['code'])]), [])
        self.assertEqual(client.query('contract/collect_in_collect', [('search_code', sub['code'])]), [])
        self.assertEqual(client.get_by_search_key(member['__search_key__'])['code'], member['code'])
        with self.assertRaises(Fault):
            client.execute_cmd('tactic.ui.panel.CollectionDeleteCmd', {'collection_key': member['__search_key__']})
        self.assertEqual(client.get_by_search_key(member['__search_key__'])['code'], member['code'])

    def test_original_client_creates_project_database_through_command_api(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        result = client.execute_cmd('tactic.command.CreateProjectCmd',
            dict(project_code='project_transport', project_title='Проект', project_stype=['asset']))
        self.assertEqual(result['info']['result'], 'Finished creating project [project_transport].')
        self.assertTrue(self.store.database_path('project_transport').is_file())
        client.set_project('project_transport')
        self.assertEqual(client.query('project_transport/asset'), [])
        self.assertIn('pipeline_code', client.get_column_names('project_transport/asset'))
        record = client.insert('project_transport/asset', dict(code='PROJECT_WRITE', name='Объект'))
        updated = client.update(record['__search_key__'], dict(description='Updated'))
        self.assertEqual(updated['description'], 'Updated')
        from pyasm.search.sql import Sql
        commit = Sql.commit
        def fail_system(sql):
            if sql.get_database_name() == 'sthpw' and sql._has_writes:
                raise ValueError('simulated system commit failure')
            return commit(sql)
        with self.assertLogs('tactic_stream.server.app', level='ERROR'), patch.object(Sql, 'commit', fail_system):
            with self.assertRaisesRegex(Fault, 'already committed: project_transport'):
                client.update(record['__search_key__'], dict(name='Committed before failure'))
            with self.assertRaises(HTTPError) as caught:
                self.admin_rpc('update', [client.ticket, record['__search_key__'], dict(description='JSON partial commit')])
            payload = json.load(caught.exception)
            caught.exception.close()
            self.assertEqual(payload['error_code'], 'partial_commit')
            self.assertIn('already committed: project_transport', payload['error'])
        self.assertEqual(client.get_by_search_key(record['__search_key__'])['name'], 'Committed before failure')
        self.assertEqual(client.delete_sobject(record['__search_key__'])['code'], 'PROJECT_WRITE')
        self.assertEqual(client.query('project_transport/asset'), [])
        with self.assertRaises(Fault):
            client.execute_cmd('tactic.command.CreateProjectCmd', dict(project_code='project_transport'))
        with self.assertRaises(Fault):
            client.execute_cmd('os.system', {'command': 'must not execute'})

    def test_original_client_schema_connections_instances_and_columns(self):
        from tactic_client_lib import TacticServerStub
        import schema_api_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title) VALUES ('schema_transport','Schema transport')")
            schema_api_contract.install_fixture(db, project='schema_transport')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('schema_transport')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        first = 'contract/schema_asset?project=schema_transport&code=ASSET'
        second = 'contract/schema_tag?project=schema_transport&code=TAG'
        connection = client.connect_sobjects(first, second, 'transport')
        self.assertEqual(connection['context'], 'transport')
        self.assertEqual(client.get_connected_sobject(first, 'transport')['code'], 'TAG')
        self.assertEqual([row['code'] for row in client.get_connected_sobjects(second, 'transport')], ['ASSET'])
        # No named SDK wrappers exist for these instance methods.
        instance = client.server.add_instance(client.ticket, first, second)
        self.assertEqual((instance['asset_code'], instance['tag_code']), ('ASSET', 'TAG'))
        self.assertEqual(len(client.server.get_instances(client.ticket, first, 'contract/schema_tag')), 1)
        self.assertIsNone(client.server.remove_instance(client.ticket, first, second))
        self.assertEqual(client.server.get_instances(client.ticket, first, 'contract/schema_tag'), [])
        created = client.create_search_type('contract/transport_schema', 'Transport', 'Описание', has_pipeline=True)
        self.assertEqual(created['title'], 'Transport')
        self.assertTrue(client.add_column_to_search_type('contract/transport_schema', 'extra', 'varchar(80)'))
        self.assertFalse(client.add_column_to_search_type('contract/transport_schema', 'extra', 'varchar(80)'))
        record = client.insert('contract/transport_schema', {'code': 'TRANSPORT', 'name': 'Тест', 'extra': 'OK'})
        self.assertEqual(client.get_by_search_key(record['__search_key__'])['extra'], 'OK')
        self.assertTrue(client.class_exists('pyasm.search.SObject'))
        self.assertFalse(client.class_exists('pyasm.search.Unknown'))
        self.assertEqual(client.get_server_version(), client.get_release_version())
        self.assertTrue(client.get_server_api_version())
        self.assertTrue(client.check_access('search_type', 'contract/schema_asset', 'edit'))
        ticket = {'ticket': client.get_ticket('admin', 'private-test-password'), 'project': 'schema_transport', 'language': 'python'}
        with self.assertRaises(Fault):
            self.proxy().add_column_to_search_type(ticket, 'contract/transport_schema', 'bad', 'text; DROP TABLE login')
        self.assertNotIn('bad', client.get_column_names('contract/transport_schema'))


    def test_unmodified_source_client_schema_undo_redo(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_schema_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        search_type = 'admin/sdk_schema_replay'
        def journal_id():
            # Fixture inspection; journal reads have a separate API access policy.
            with self.store.connection() as db:
                return db.execute("SELECT id FROM transaction_log WHERE type='undo' ORDER BY id DESC LIMIT 1").fetchone()['id']
        client.create_search_type(search_type, 'SDK schema replay')
        creation = journal_id()
        row = client.insert(search_type, dict(code='SDK_SCHEMA', description='preserved'))
        self.assertTrue(client.undo(transaction_id=creation))
        self.assertTrue(client.redo(transaction_id=creation))
        self.assertEqual(client.get_by_code(search_type, row['code'])['description'], 'preserved')
        self.assertTrue(client.add_column_to_search_type(search_type, 'sdk_value', 'integer'))
        addition = journal_id()
        client.update(row['__search_key__'], dict(sdk_value=73))
        self.assertTrue(client.undo(transaction_id=addition))
        self.assertNotIn('sdk_value', client.get_by_code(search_type, row['code']))
        self.assertTrue(client.redo(transaction_id=addition))
        self.assertEqual(client.get_by_code(search_type, row['code'])['sdk_value'], 73)

    def test_original_client_workflow_pipeline_tasks_and_dependencies(self):
        from tactic_client_lib import TacticServerStub
        import engine_contract
        import workflow_nodes_contract
        with self.store.connection(write=True) as db:
            engine_contract.install_fixture(db)
            workflow_nodes_contract.install_fixture(db)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        pipeline = client.create_pipeline('Transport API', 'sthpw/task', ['draft', 'review'], description='Описание', connected=False)
        self.assertEqual((pipeline['search_type'], pipeline['description']), ('sthpw/task', 'Описание'))
        self.assertEqual(len(client.query('config/process', [['pipeline_code', pipeline['code']]])), 2)
        self.assertNotIn('<connect', pipeline['pipeline'])
        first = 'contract/engine?project=admin&code=ENGINE'
        second = 'contract/engine?project=admin&code=MANUAL'
        tasks = {process: client.create_task(first, process=process) for process in ('start', 'left', 'right', 'join')}
        self.assertEqual(sorted(row['process'] for row in client.get_input_tasks(tasks['join'])), ['left', 'right'])
        self.assertEqual(sorted(row['process'] for row in client.get_output_tasks(tasks['start'])), ['left', 'right'])
        info = client.get_pipeline_xml_info(first, include_hierarchy=True)
        self.assertEqual([row['process'] for row in info['hierarchy']], ['start', 'left', 'right', 'join'])
        self.assertEqual(client.get_pipeline_processes_info(first)['processes'], ['start', 'left', 'right', 'join'])
        self.assertEqual(client.get_pipeline_processes_info(first, related_process='join')['input_processes'], ['left', 'right'])
        self.assertIn('task', client.get_task_status_colors())
        self.assertEqual(client.call_trigger(first, 'absent|event', input=None), 0)
        self.assertIsNone(client.call_pipeline_event([first, second], 'start', 'pending', data={'name': 'Данные'}))
        self.assertEqual([client.get_pipeline_status(key, 'start') for key in (first, second)], ['complete', 'complete'])
        self.assertIsNone(client.get_pipeline_status(first, 'missing'))
        root = 'contract/nodes?project=admin&code=NESTED'
        self.assertIsNone(client.call_pipeline_event(root, 'start', 'pending', data={'value': 7}))
        self.assertEqual(client.get_pipeline_status(root, 'start/start/work'), 'complete')
        self.assertEqual(client.get_pipeline_status(root, 'done'), 'complete')
        conditional = 'contract/nodes?project=admin&code=STREAMS'
        self.assertIsNone(client.call_pipeline_event(conditional, 'choose', 'pending', data={'value': 7}))
        self.assertEqual([client.get_pipeline_status(conditional, process) for process in ('left', 'right', 'join')],
                         ['complete', 'not_required', 'complete'])
        owner = 'sthpw/project?code=admin'
        target = client.create_snapshot(owner, 'transport_dependency')
        child = client.create_snapshot(owner, 'transport_dependency_child')
        client.add_dependency_by_code(target, child, type='input_ref', tag="quoted'tag")
        from pyasm.common import Xml
        self.assertEqual(len(Xml(client.get_by_search_key(target)['snapshot']).get_nodes('snapshot/input_ref')), 1)
        source = Path(self.temp.name) / 'transport_reference.txt'
        source.write_text('reference', encoding='utf-8')
        checked = client.simple_checkin(owner, 'transport_reference', str(source), mode='upload', create_icon=False)
        linked = client.add_dependency(target, client.get_path_from_snapshot(checked), type='input_ref', tag='path')
        self.assertEqual(len(Xml(linked['snapshot']).get_nodes('snapshot/input_ref')), 2)
        self.assertTrue(client.lock_sobject(owner, 'transport_dependency'))
        self.assertEqual(client.get_by_search_key(target)['lock_login'], 'admin')
        self.assertTrue(client.unlock_sobject(owner, 'transport_dependency'))
        self.assertFalse(client.get_by_search_key(target)['lock_login'])
        before = client.query('sthpw/pipeline')
        with self.assertRaises(Fault):
            client.create_pipeline('Invalid', 'sthpw/task', ['one', 'two'], process_types=['manual'])
        self.assertEqual(client.query('sthpw/pipeline'), before)
        with self.assertRaises(Fault):
            client.call_pipeline_event(first, 'missing', 'pending')
        reader = client.insert('sthpw/login', {'login': 'workflow_api_reader', 'password': hash_password('private-reader-password')})
        client.set_ticket(client.get_ticket('workflow_api_reader', 'private-reader-password'))
        for name, args in [('create_pipeline', ('Denied', 'sthpw/task')),
                           ('call_pipeline_event', (first, 'start', 'pending')),
                           ('call_trigger', (first, 'absent|event')),
                           ('add_dependency_by_code', (target['code'], child['code'])),
                           ('lock_sobject', (owner, 'transport_dependency'))]:
            with self.subTest(method=name), self.assertRaises(Fault):
                getattr(client, name)(*args)

    def test_original_client_saves_pipeline_and_executes_saved_script(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        pipeline = client.create_pipeline('Saved API commands', 'sthpw/project', ['publish'], process_types=['action'])
        script = "from pyasm.search import Search\nfrom pyasm.biz import Note\nparent = input['sobject']\nif isinstance(parent, dict):\n    parent = Search.get_by_search_key(parent['__search_key__'])\nNote.create(parent, 'XML-RPC saved process', process=input['process'])\nreturn True"
        graph = '<pipeline><process name="publish" type="action" label="A &amp; B"/></pipeline>'
        result = client.execute_cmd('tactic.ui.tools.PipelineSaveCbk', dict(
            search_key=pipeline['__search_key__'], pipeline=graph,
            node_kwargs={'publish': {'version': 2, 'default': {'script': script, 'execute_mode': 'same process,same transaction'}}}))
        self.assertEqual(result['status'], 'OK')
        saved = client.get_by_search_key(pipeline)
        self.assertIn('label="A &amp; B"', saved['pipeline'])
        self.assertNotIn('&amp;amp;', saved['pipeline'])
        parent = client.insert('sthpw/project', {'code': 'saved_api', 'title': 'Saved API', 'pipeline_code': pipeline['code']})
        client.call_pipeline_event(parent, 'publish', 'pending')
        notes = client.query('sthpw/note', [['search_type', 'sthpw/project'], ['search_code', parent['code']]])
        self.assertEqual([note['note'] for note in notes], ['XML-RPC saved process'])
        definition = client.query('config/process', [['pipeline_code', pipeline['code']], ['process', 'publish']])[0]
        client.execute_cmd('tactic.ui.tools.pipeline_wdg.ProcessInfoCmd', dict(node_type='action', pipeline_code=pipeline['code'],
            process='publish', script_path='_triggers/' + pipeline['code'] + '/' + definition['code'], execute_mode='same process,same transaction'))
        client.call_pipeline_event(parent, 'publish', 'pending')
        self.assertEqual(len(client.query('sthpw/note', [['search_type', 'sthpw/project'], ['search_code', parent['code']]])), 2)
        empty = client.execute_cmd('tactic.ui.tools.PipelineSaveCmd', {'name': 'RPC empty workflow', 'category': 'Contract'})
        self.assertEqual(client.get_by_search_key(empty['info']['search_key'])['category'], 'Contract')
        client.execute_cmd('tactic.ui.tools.pipeline_wdg.PipelinePropertyCbk', dict(
            pipeline_code=pipeline['code'], process='publish', contract_flag=True))
        response = client.execute_python_script('', kwargs={'code':
            'from pyasm.biz import Pipeline\n'
            'version = Pipeline.get_by_code(kwargs["pipeline_code"]).save_version()\n'
            'return version.get_sobject_dict()', 'pipeline_code': pipeline['code']})
        version = response['info']
        self.assertEqual(version['version'], 1)
        client.update(parent, {'pipeline_code': version['code']})
        client.execute_cmd('tactic.ui.tools.ProcessInfoCmd', dict(node_type='action', pipeline_code=pipeline['code'],
            process='publish', script=script.replace('XML-RPC saved process', 'current script changed'), execute_mode='same process,same transaction'))
        client.call_pipeline_event(parent, 'publish', 'pending')
        notes = client.query('sthpw/note', [['search_type', 'sthpw/project'], ['search_code', parent['code']]])
        self.assertEqual([note['note'] for note in notes], ['XML-RPC saved process'] * 3)

    def test_original_client_custom_task_statuses(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract, task_schedule_contract, task_status_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('status_rpc','Status RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='status_rpc')
            if 'start_date' not in {row['name'] for row in db.execute('PRAGMA table_info(dep_parent)')}:
                task_schedule_contract.install_fixture(db)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('status_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_cmd('task_status_contract.Setup', {'mode': 'nested'})
        client.execute_cmd('task_status_contract.Begin', {'mode': 'nested'})
        tasks = client.query('sthpw/task', [['search_code', 'CS_nested']], order_bys=['id'])
        self.assertEqual([row['pipeline_code'] for row in tasks], ['CS_nested_STATUS'] * 2)
        client.update(tasks[0], {'status': 'Working'})
        states = client.query('config/process_state', [['search_code', 'CS_nested']])
        self.assertEqual({row['process']: row['status'] for row in states}['gate/work'], 'in_progress')
        client.update(tasks[0], {'status': 'Ready'})
        self.assertEqual(client.query('sthpw/note', [['search_code', 'CS_nested'], ['process', 'custom_status']]), [])
        done = client.query('config/process', [['pipeline_code', 'CS_nested'], ['process', 'done']])[0]
        workflow = json.loads(done['workflow'])
        client.update(done, {'workflow': dict(workflow, on_action='raise ValueError("late custom status failure")')})
        kinds = ('sthpw/task', 'config/process_state', 'sthpw/message', 'sthpw/note', 'sthpw/status_log')
        before = {kind: client.query(kind, order_bys=['id']) for kind in kinds}
        with self.assertRaises(Fault):
            client.update(tasks[1], {'status': 'Ready'})
        self.assertEqual({kind: client.query(kind, order_bys=['id']) for kind in kinds}, before)
        client.update(done, {'workflow': workflow})
        ready = client.query('config/process', [['pipeline_code', 'CS_nested_STATUS'], ['process', 'Ready']])[0]
        mapping = json.loads(ready['workflow'])
        client.update(ready, {'workflow': {'version': 2, 'direction': 'current', 'status': 'Ready'}})
        before = {kind: client.query(kind, order_bys=['id']) for kind in kinds}
        with self.assertRaises(Fault):
            client.update(tasks[1], {'status': 'Ready'})
        self.assertEqual({kind: client.query(kind, order_bys=['id']) for kind in kinds}, before)
        client.update(ready, {'workflow': mapping})
        client.update(tasks[1], {'status': 'Ready'})
        notes = client.query('sthpw/note', [['search_code', 'CS_nested'], ['process', 'custom_status']])
        self.assertEqual([json.loads(row['note']) for row in notes], [[{'value': 7}, {'value': 9}]])
        tasks = client.query('sthpw/task', [['search_code', 'CS_nested']], order_bys=['id'])
        self.assertEqual([row['status'] for row in tasks], ['Ready', 'Ready'])
        states = client.query('config/process_state', [['search_code', 'CS_nested']])
        self.assertEqual({row['process']: row['status'] for row in states}['gate'], 'complete')

    def test_original_client_task_scheduling(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract, task_schedule_contract as contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('schedule_rpc','Schedule RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='schedule_rpc')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(dep_parent)')}
            if 'start_date' not in columns:
                contract.install_fixture(db)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('schedule_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        expected = {
            'even': [('2026-10-05 09:00:00', '2026-10-07 12:00:00'), ('2026-10-07 12:00:00', '2026-10-09 15:00:00'), ('2026-10-09 15:00:00', '2026-10-11 18:00:00')],
            'even_day': [('2026-10-05 12:00:00', '2026-10-07 12:00:00'), ('2026-10-07 12:00:00', '2026-10-09 12:00:00'), ('2026-10-09 12:00:00', '2026-10-11 12:00:00')],
            'from_end_date': [('2026-10-02 18:00:00', '2026-10-04 18:00:00'), ('2026-10-04 18:00:00', '2026-10-09 18:00:00'), ('2026-10-09 18:00:00', '2026-10-11 18:00:00')],
        }
        for mode in contract.MODES:
            code = 'TS_RPC_' + mode
            key = client.execute_cmd('task_schedule_contract.Setup', dict(code=code, generate=True, mode=mode))['info']
            client.add_initial_tasks(key, start_date='2026-10-05')
            tasks = client.query('sthpw/task', [['search_code', code]], order_bys=['id'])
            self.assertEqual([(row['bid_start_date'], row['bid_end_date']) for row in tasks], expected[mode], mode)
            client.add_initial_tasks(key, start_date='2026-10-05')
            self.assertEqual(len(client.query('sthpw/task', [['search_code', code]])), 3)
        parent = client.get_by_search_key(key)
        client.update(parent, {'due_date': '2026-10-01 12:00:00'})
        setting = client.query('config/prod_setting', [['key', 'schedule/mode']])[0]
        client.update(setting, {'value': 'even'})
        before = client.query('sthpw/task', [['search_code', code]], order_bys=['id'])
        with self.assertRaises(Fault):
            client.add_initial_tasks(key, skip_duplicate=False, start_date='2026-10-05')
        self.assertEqual(client.query('sthpw/task', [['search_code', code]], order_bys=['id']), before)

    def test_original_client_workflow_snapshot_packages(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract, workflow_packages_contract as contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('package_rpc','Package RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='package_rpc')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('package_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_cmd('workflow_packages_contract.Setup')
        packages = client.execute_cmd('workflow_packages_contract.Inspect')['info']
        self.assertEqual(packages['nested']['default']['snapshot_codes'], ['nested_final'])
        self.assertEqual(packages['alternate']['default']['snapshot_codes'], ['alternate_wip'])
        client.execute_cmd('workflow_packages_contract.Begin')
        tasks = {row['process']: row for row in client.query('sthpw/task', [['search_code', 'PK_PARENT']])}
        client.update(tasks['work'], {'status': 'Complete'})
        notes = client.query('sthpw/note', [['search_code', 'PK_PARENT'], ['process', 'packages']])
        self.assertEqual(notes, [])
        done = client.query('config/process', [['pipeline_code', 'PK_ROOT'], ['process', 'done']])[0]
        workflow = json.loads(done['workflow'])
        failed_workflow = dict(workflow, on_action=workflow['on_action'].replace('return True', 'raise ValueError("late package failure")'))
        client.update(done, {'workflow': failed_workflow})
        kinds = ('sthpw/task', 'config/process_state', 'sthpw/note', 'sthpw/snapshot', 'sthpw/message')
        before = {kind: client.query(kind, [['code', 'like', '%PK_PARENT%']] if kind == 'sthpw/message'
                                    else [['search_code', 'PK_PARENT']], order_bys=['id']) for kind in kinds}
        with self.assertRaises(Fault):
            client.update(tasks['gate/work'], {'status': 'Complete'})
        after = {kind: client.query(kind, [['code', 'like', '%PK_PARENT%']] if kind == 'sthpw/message'
                                   else [['search_code', 'PK_PARENT']], order_bys=['id']) for kind in kinds}
        self.assertEqual(after, before)
        client.update(done, {'workflow': workflow})
        client.update(tasks['gate/work'], {'status': 'Complete'})
        notes = client.query('sthpw/note', [['search_code', 'PK_PARENT'], ['process', 'packages']])
        self.assertEqual(len(notes), 1)
        result = json.loads(notes[0]['note'])
        contexts = sorted(client.get_by_code('sthpw/snapshot', code)['context'] for code in result['default']['snapshot_codes'])
        self.assertEqual(contexts, ['nested_final'])
        self.assertEqual(result['custom'], {'value': 9})
        self.assertEqual(result['message'], {'body': 'keep message', 'type': 'message'})
        states = client.query('sthpw/message', [['code', 'like', '%PK_PARENT%|gate/work|state']])
        self.assertEqual(len(states), 1)
        self.assertEqual(json.loads(states[0]['message'])['packages'], result)

    def test_original_client_changes_workflow_process_types(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract, process_type_contract as contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('type_rpc','Type RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='type_rpc')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('type_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_cmd('process_type_contract.Setup')
        before = client.query('config/process', [['pipeline_code', 'PT_MAIN']])
        client.update('sthpw/pipeline?code=PT_MAIN', {'pipeline': contract.MANUAL_XML})
        client.execute_cmd('process_type_contract.Change')
        after = client.query('config/process', [['pipeline_code', 'PT_MAIN']])
        self.assertEqual({row['code'] for row in before}, {row['code'] for row in after})
        self.assertTrue(all(json.loads(row['workflow']) == {'version': 2, 'node_type': 'manual'} for row in after))
        codes = {row['code'] for row in before}
        self.assertFalse(any(row['process'] in codes or json.loads(row['data'] or '{}').get('pipeline_code') == 'PT_MAIN'
                             for row in client.query('config/trigger')))
        self.assertEqual([row['note'] for row in client.query('sthpw/note', [['search_code', 'PT_PARENT']])], ['custom type released'])
        self.assertEqual(len(client.query('sthpw/task', [['search_code', 'PT_PARENT']])), 1)
        graph = contract.MANUAL_XML.replace('name="action" type="manual"', 'name="action" type="action"')
        script = "from pyasm.biz import Note\nfrom pyasm.search import Search\nparent = input['sobject']\nif isinstance(parent, dict):\n    parent=Search.get_by_search_key(parent['__search_key__'])\nNote.create(parent, 'new type action', process=input['process'])\nreturn True"
        client.execute_cmd('tactic.core.pipeline_commands.PipelineSaveCbk', {
            'search_key': 'sthpw/pipeline?code=PT_MAIN', 'pipeline': graph,
            'node_kwargs': {'action': {'version': 2, 'default': {'script': script, 'execute_mode': 'same process,same transaction'}}}})
        client.call_pipeline_event('contract/dep_parent?project=type_rpc&code=PT_PARENT', 'action', 'pending')
        self.assertEqual([row['note'] for row in client.query('sthpw/note', [['search_code', 'PT_PARENT']], order_bys=['id'])],
                         ['custom type released', 'new type action'])

    def test_original_client_deletes_workflow_processes(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('delete_rpc','Delete RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='delete_rpc')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('delete_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_cmd('process_delete_contract.Setup')
        process = client.query('config/process', [['pipeline_code', 'PD_MAIN'], ['process', 'custom']])[0]
        self.assertEqual(client.delete_sobject(process['__search_key__'])['code'], process['code'])
        client.execute_cmd('process_delete_contract.Delete')
        self.assertEqual(client.query('config/process', [['pipeline_code', 'PD_MAIN']]), [])
        self.assertEqual([row['code'] for row in client.query('config/trigger')], ['PD_EXTERNAL'])
        self.assertEqual(len(client.query('config/custom_script')), 1)
        self.assertEqual([row['note'] for row in client.query('sthpw/note', [['search_code', 'PD_PARENT']])], ['custom deleted'])
        self.assertEqual(len(client.query('sthpw/task', [['search_code', 'PD_PARENT']])), 1)

    def test_original_client_same_object_alternate_workflows(self):
        from tactic_client_lib import TacticServerStub
        import dependency_contract, same_object_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('same_rpc','Same RPC','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='same_rpc')
            same_object_contract.install_fixture(db, project='same_rpc')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('same_rpc')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        parent = 'contract/dep_parent?project=same_rpc&code=SAME'
        client.create_task(parent, process='work')
        client.execute_python_script('', kwargs={'code':
            'from pyasm.search import Search\nfrom pyasm.biz import Task\n'
            'obj=Search.get_by_code("contract/dep_parent","SAME")\n'
            'Task.add_initial_tasks(obj,pipeline_code="SAME_ALT1",status="Pending")\n'
            'Task.add_initial_tasks(obj,pipeline_code="SAME_ALT2",status="Pending")\nreturn True'})
        client.call_pipeline_event(parent, 'SAME_ALT1::work', 'pending')
        for process, value in (('start', 7), ('start2', 8)):
            client.call_pipeline_event(parent, process, 'pending', data={'value': value})
        tasks = client.query('sthpw/task', [['search_type', 'like', 'contract/dep_parent%'], ['search_code', 'SAME']])
        tasks = {row['process']: row for row in tasks}
        self.assertEqual(set(tasks), {'work', 'SAME_ALT1::work', 'SAME_ALT2::work'})
        self.assertEqual(client.get_pipeline_status(parent, 'SAME_ALT1::work'), 'pending')
        client.update(tasks['SAME_ALT1::work'], {'status': 'Complete'})
        self.assertEqual(client.get_pipeline_status(parent, 'start'), 'complete')
        self.assertEqual(client.get_pipeline_status(parent, 'start2'), 'in_progress')
        client.update(tasks['SAME_ALT2::work'], {'status': 'Complete'})
        self.assertEqual(client.get_pipeline_status(parent, 'work'), 'pending')
        client.update(tasks['work'], {'status': 'Complete'})
        self.assertEqual(client.get_pipeline_status(parent, 'done'), 'complete')
        states = client.query('config/process_state', [['search_type', 'like', 'contract/dep_parent%'], ['search_code', 'SAME']])
        self.assertEqual({row['pipeline_code'] for row in states}, {'SAME_MAIN', 'SAME_ALT1', 'SAME_ALT2'})

    def test_original_client_dependency_completes_after_another_request(self):
        from tactic_client_lib import TacticServerStub
        from pyasm.command import Trigger
        from pyasm.command.workflow import Workflow
        from tactic.core.bootstrap import CoreInit
        import dependency_contract
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO project (code,title,database) VALUES ('dependencies','Dependencies','sthpw')")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dep_parent'").fetchone():
                dependency_contract.install_fixture(db, project='dependencies')
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('dependencies')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        self.assertTrue(CoreInit.initialized)
        self.assertTrue(Workflow.startup_initialized)
        self.assertEqual(sum(item.get_value('class_name') == 'tactic.core.bootstrap.StatusLogTrigger'
                             for item in Trigger.STATIC_TRIGGERS if item.get_value('event') == 'change|sthpw/task|status'), 1)
        parents = ['contract/dep_parent?project=dependencies&code=SHARED', 'contract/dep_parent?project=dependencies&code=SHARED_OTHER']
        child = 'contract/dep_child?project=dependencies&code=SHARED_1'
        task = client.create_task(child, process='work')
        for value, parent in enumerate(parents, 7):
            self.assertIsNone(client.call_pipeline_event(parent, 'start', 'pending', data={'value': value}))
            self.assertEqual(client.get_pipeline_status(parent, 'start'), 'in_progress')
        client.update(task, {'status': 'Complete'})
        for parent in parents:
            self.assertEqual(client.get_pipeline_status(parent, 'done'), 'complete')
        logs = client.query('sthpw/status_log', [['search_type', 'sthpw/task'], ['search_code', task['code']], ['to_status', 'Complete']])
        self.assertEqual(len(logs), 1)

    def test_original_client_repository_snapshot_and_group_api(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        source = Path(self.temp.name) / 'client_frames'
        source.mkdir()
        for version in (1, 2):
            for frame in (1, 2, 3):
                (source / ('transport.%04d.txt' % frame)).write_text('frame '+str(frame), encoding='utf-8')
            result = client.group_checkin('sthpw/project?code=admin', 'transport_group', str(source / 'transport.####.txt'), '1-3', mode='upload')
            self.assertEqual(result['version'], str(version))
            if version == 1:
                first = result['code']
            second = result['code']
        for frame in (1, 2, 3):
            (source / ('extra.%04d.txt' % frame)).write_text('extra frame', encoding='utf-8')
        handoff = Path(client.server.get_handoff_dir(client.ticket))
        self.assertFalse(handoff.exists())
        client.add_group(first, str(source / 'extra.####.txt'), 'extra', '1-3', mode='upload')
        self.assertEqual(Path(client.get_handoff_dir()), handoff)
        self.assertTrue(handoff.is_dir())
        self.assertEqual(len(list(source.glob('*.txt'))), 6)
        rows = client.query_snapshots([['context', 'transport_group'], ['version', '>', 0]], order_bys=['version'], include_paths=True, include_paths_dict=True, include_files=True, include_parent=True, include_web_paths_dict=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['__parent__']['code'], 'admin')
        self.assertEqual({row['type'] for row in rows[0]['__files__']}, {'main', 'extra'})
        self.assertEqual(len(client.get_expanded_paths_from_snapshot(first)), 3)
        all_paths = client.get_all_paths_from_snapshot(first, expand_paths=True, file_types=['main', 'extra'])
        self.assertEqual(len(all_paths), 6)
        self.assertTrue(all(Path(path).is_file() for path in all_paths))
        self.assertEqual(len(client.get_all_paths_from_snapshot(first, expand_paths=False, file_types=['main', 'extra'])), 2)
        self.assertEqual(client.get_path_from_snapshot(first), client.get_path_from_snapshot('sthpw/snapshot?code='+first))
        self.assertEqual(Path(client.get_path_from_snapshot(first)).parent, Path(client.get_client_dir(first)))
        self.assertTrue(client.get_paths('sthpw/project?code=admin', context='transport_group', version=1, path_types=['lib']))
        snapshot = client.get_by_search_key('sthpw/snapshot?code='+first)
        reference = '<ref snapshot_code="%s" search_type="sthpw/project" search_code="admin" context="transport_group" version="2" tag="main"/>' % second
        xml = snapshot['snapshot'].replace('</snapshot>', reference+'</snapshot>')
        client.update(snapshot, {'snapshot': xml})
        dependency = client.get_dependencies(first, include_files=True)[0]
        self.assertEqual(dependency['code'], second)
        self.assertEqual([row['type'] for row in dependency['__files__']], ['main'])
        self.assertEqual(client.get_all_dependencies(first, include_paths=True)[0]['code'], second)
        self.assertTrue(client.set_current_snapshot(first)['is_current'])
        self.assertEqual([(item['version'], item['is_current']) for item in client.query_snapshots([['context', 'transport_group'], ['version', '>', 0]], order_bys=['version'])], [(1, True), (2, False)])
        current = client.get_snapshot('sthpw/project?code=admin', context='transport_group', version=0, include_paths=True, include_paths_dict=True, include_web_paths_dict=True)
        self.assertEqual(current['code'], first)
        self.assertTrue(current['__paths_dict__'])
        relative = rows[1]['__files__'][0]['relative_dir']
        self.assertIn(second, [row['code'] for row in client.server.get_snapshots_by_relative_dir(client.ticket, relative)])
        self.assertEqual(client.server.get_snapshots_by_relative_dir(client.ticket, relative, 'missing_alias'), [])
        self.assertIsInstance(client.get_base_dirs(), dict)
        third = client.create_snapshot('sthpw/project?code=admin', 'transport_group')
        self.assertEqual(client.get_dependencies(first, mode='latest')[0]['code'], third['code'])
        quoted = xml.replace('tag="main"', 'tag="main\'quoted"')
        client.update(snapshot, {'snapshot': quoted})
        self.assertEqual(client.get_dependencies(first, tag="main'quoted")[0]['code'], second)
        selected = client.query_snapshots([['code', first]], columns=['version'], single=True)
        self.assertEqual(len(selected), 1)
        self.assertEqual(set(selected[0]), {'version', '__search_key__', '__search_type__'})
        before = client.query('sthpw/file')
        for frame in (1, 2):
            client.server.upload_file(client.ticket, 'missing.%04d.txt' % frame, Binary(b'input'))
        with self.assertRaises(Fault):
            client.server.add_group(client.ticket, first, 'missing.####.txt', 'invalid', '1-3', False, 'upload')
        self.assertEqual(client.query('sthpw/file'), before)
        self.assertEqual(client.server.get_upload_file_size(client.ticket, 'missing.0001.txt'), 5)

    def test_unmodified_source_client_snapshot_levels_and_metadata(self):
        from xml.etree.ElementTree import fromstring
        spec = importlib.util.spec_from_file_location('tactic_client_lib.source_levels_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        client = original.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        source = Path(self.temp.name) / 'source_level.txt'
        source.write_text('level payload', encoding='utf-8')
        key = 'sthpw/project?code=admin'
        row = client.simple_checkin(key, 'source_level_api', str(source), level_key=key,
            metadata={'label': 'Уровень', 'nested': {'ok': True}}, mode='inplace',
            create_icon=False, checkin_type='strict')
        selected = client.get_snapshot(key, 'source_level_api', 1, level_key=key,
                                      include_full_xml=True, include_files=True)
        self.assertEqual(selected['code'], row['code'])
        self.assertEqual(json.loads(selected['metadata'])['label'], 'Уровень')
        self.assertEqual(fromstring(selected['__full_snapshot_xml__']).get('version'), '1')
        batch = client.query_snapshots([['context', 'source_level_api']], include_full_xml=True)
        self.assertIn('__full_snapshot_xml__', batch[0])
        changed = client.update(row['__search_key__'], metadata={'extra': 0})
        self.assertEqual(json.loads(changed['metadata']), {'label': 'Уровень', 'nested': {'ok': True}, 'extra': 0})
        virtual = client.get_virtual_snapshot_path(key, 'source_level_api', level_key=key,
                                                   file_name='preview.txt', protocol=None)
        self.assertFalse(Path(virtual).exists())

    def test_original_client_batch_api_and_security(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        notes = client.insert_multiple('sthpw/note', [{'note': 'one'}, {'note': 'two'}], use_id=True, triggers=False)
        self.assertTrue(all('?id=' in row['__search_key__'] for row in notes))
        updated = client.update_multiple({row['__search_key__']: {'note': 'updated'} for row in notes}, triggers=False)
        self.assertEqual([row['id'] for row in updated], [row['id'] for row in notes])
        row = client.insert_update('sthpw/note?code=TRANSPORT_BATCH', {'note': 'inserted'}, triggers=False)
        same = client.insert_update(row['__search_key__'], {'note': 'upserted'}, triggers=False)
        self.assertEqual(row['id'], same['id'])
        unique = client.get_unique_sobject('sthpw/note', {'note': 'unique transport'})
        self.assertEqual(client.get_unique_sobject('sthpw/note', {'note': 'unique transport'})['id'], unique['id'])
        cloned = client.server.clone_sobject(client.ticket, unique['__search_key__'], {'note': 'cloned'})
        self.assertNotEqual(cloned['code'], unique['code'])
        task = client.create_task('sthpw/project?code=admin', process='batch transport')
        self.assertEqual(client.retire_sobject(task)['s_status'], 'retired')
        self.assertFalse(client.reactivate_sobject(task)['s_status'])
        tasks = client.server.get_tasks(client.ticket, 'sthpw/project?code=admin', 'batch transport')
        self.assertEqual([row['id'] for row in tasks], [task['id']])
        note = client.create_note(task, 'Комментарий', process='review', subcontext='detail')
        self.assertEqual((note['context'], note['search_code']), ('review/detail', task['code']))
        self.assertIn('<pipeline', client.get_pipeline_xml(task))
        self.assertTrue(client.get_pipeline_processes(task, recurse=True))
        client.set_preference('transport_batch', 'Русский')
        self.assertEqual(client.get_preference('transport_batch'), 'Русский')
        client.set_project('one')
        self.assertEqual(client.get_preference('transport_batch'), '')
        client.set_preference('transport_batch', 'English')
        client.set_project('admin')
        self.assertEqual(client.get_preference('transport_batch'), 'Русский')
        before = client.query('sthpw/note')
        with self.assertRaises(Fault):
            client.insert_multiple('sthpw/note', [{'note': 'rollback'}, {'missing_column': 'failure'}])
        self.assertEqual(client.query('sthpw/note'), before)
        viewer = client.insert('sthpw/login', {'login': 'batch_viewer', 'password': hash_password('private-viewer-password')})
        token = client.get_ticket('batch_viewer', 'private-viewer-password')
        client.set_ticket(token)
        for name, args in [('insert_multiple', ('sthpw/note', [{'note': 'denied'}])),
                           ('update_multiple', ({notes[0]['__search_key__']: {'note': 'denied'}},)),
                           ('clone_sobject', (notes[0]['__search_key__'],)),
                           ('retire_sobject', (task['__search_key__'],)),
                           ('set_preference', ('transport_batch', 'denied'))]:
            with self.subTest(method=name), self.assertRaises(Fault):
                getattr(client.server, name)(client.ticket, *args)

    def ticket(self, proxy):
        return {"ticket": proxy.get_ticket("admin", "private-test-password", None),
                "project": "one", "language": "python", "site": None}

    def test_health_docs_and_complete_contract_inventory(self):
        with urlopen(self.url + "/health") as response:
            health = json.load(response)
            self.assertTrue(health["database_initialized"])
            self.assertEqual(health["service"], "tactic_stream")
        with urlopen(self.url + "/openapi.json") as response:
            self.assertEqual(json.load(response)["info"]["title"], "TACTIC Stream")
        for path in ('/', '/projects/one/'):
            with urlopen(self.url + path) as response:
                self.assertEqual(response.url, self.url + path)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertIn(b'<div id="app">', response.read())
        for path in ('/admin/', '/admin/?project=one', '/admin/assets/missing.js'):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
        with urlopen(self.url + "/api/compatibility") as response:
            manifest = json.load(response)
        self.assertEqual(len(manifest['methods']), 129)
        self.assertFalse(manifest["full_api_parity_verified"])

    def test_original_client_preallocation_and_binary_file_api(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        snapshot = client.create_snapshot('sthpw/project?code=admin', 'transport_preallocation')
        path = client.get_preallocated_path(snapshot, file_name='scene.bin', protocol=None, mkdir=False)
        self.assertFalse(Path(path).parent.exists())
        self.assertEqual(path, client.get_preallocated_path(snapshot, file_name='scene.bin', protocol=None))
        Path(path).write_bytes(b'preallocated through client')
        result = client.add_file(snapshot, path, mode='preallocate')
        self.assertEqual((result['code'], result['version']), (snapshot['code'], 1))
        payload = b'\x00\xff\xfe\x80file'
        self.assertTrue(client.server.upload_file(client.ticket, r'C:\client\payload.bin', Binary(payload)))
        self.assertEqual(client.server.get_upload_file_size(client.ticket, 'payload.bin'), len(payload))
        result = client.add_file(snapshot['code'], 'payload.bin', file_type='secondary')
        self.assertEqual(result['version'], 1)
        files = client.query('sthpw/file', [['snapshot_code', snapshot['code']], ['type', 'secondary']])
        self.assertEqual(len(files), 1)
        self.assertEqual((Path(files[0]['checkin_dir']) / files[0]['file_name']).read_bytes(), payload)
        self.assertEqual(client.server.get_upload_file_size(client.ticket, 'payload.bin'), 0)
        client.remove_file(snapshot, 'secondary')
        self.assertFalse((Path(files[0]['checkin_dir']) / files[0]['file_name']).exists())
        virtual = client.get_virtual_snapshot_path('sthpw/project?code=admin', 'transport_virtual', file_name='preview.txt', protocol=None)
        self.assertTrue(virtual.endswith('preview_transport_virtual_v001.txt'))
        self.assertEqual(client.query('sthpw/snapshot', [['context', 'transport_virtual']]), [])
        client.delete_sobject(snapshot['__search_key__'], include_dependencies=True)

    def test_real_xmlrpc_preserves_original_python_query_envelope(self):
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        self.assertEqual(proxy.fast_ping(None), "OK")
        self.assertEqual(proxy.ping(ticket), "OK")
        raw = proxy.query(ticket, "contract/entity", [["code", "A"]], [], [], False, None, None, True)
        self.assertEqual(ast.literal_eval(raw)["name"], "Первый")
        self.assertIsInstance(raw, str)
        self.assertEqual(proxy.get_by_code(ticket, "contract/entity", "missing"), {})

    def test_raw_large_integer_cells_match_xmlrpc_and_json(self):
        import inspect
        from tactic_client_lib import TacticServerStub
        from tactic_stream.server.raw_database import raw_database_request
        handler = ROOT.parent.parent / 'TH'
        native_path = handler / 'thlib/side/client/tactic_client_lib/tactic_server_stub.py'
        if native_path.is_file():
            with patch.object(sys, 'path', [str(handler), *sys.path]):
                spec = importlib.util.spec_from_file_location('handler_raw_integer_client', native_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                TacticServerStub = module.TacticServerStub
        values = [(2**31 - 1, -(2**31)), (2**31, -(2**31) - 1),
                  (2**53 - 1, 2**40), (2**53, 2**63 - 1)]
        with self.store.connection(write=True) as db:
            db.execute('CREATE TABLE raw_rpc_integer (id INTEGER PRIMARY KEY, number INTEGER)')
            db.executemany('INSERT INTO raw_rpc_integer VALUES (?, ?)', values)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        ticket = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(ticket)
        self.addCleanup(client.server.__exit__, None, None, None)
        source = inspect.getsource(raw_database_request)
        identity = json.dumps(['sthpw', 'raw_rpc_integer'])
        def call(action, **parameters):
            arguments = dict(action=action, project_code='admin', identity=identity, **parameters)
            # Handler embeds arguments in source, so large input integers stay exact too.
            code = source + '\nreturn raw_database_request(' + ', '.join(
                name + '=' + repr(value) for name, value in arguments.items()) + ')'
            return client.execute_python_script('', kwargs={'code': code})['info']
        loaded = call('load')
        with urlopen(Request(self.url + '/admin/raw-database/load',
                json.dumps(dict(ticket=ticket, project='admin', identity=identity)).encode(),
                headers={'Content-Type': 'application/json'})) as response:
            browser = json.load(response)['result']
        self.assertEqual(loaded, browser)
        self.assertEqual(loaded['document']['rows'][1]['key'], [2**31])
        self.assertEqual(loaded['document']['rows'][1]['values']['number'], -(2**31) - 1)
        self.assertEqual(loaded['document']['rows'][3]['values']['id'], str(2**53))
        self.assertEqual(loaded['document']['rows'][3]['values']['number'], str(2**63 - 1))
        loaded['document']['rows'][1]['values']['number'] = 2**40 + 1
        saved = call('save', document=loaded['document'], expected_revision=loaded['revision'])
        self.assertEqual(saved['document']['rows'][1]['values']['number'], 2**40 + 1)

    def test_raw_sparse_edits_preserve_background_rows_and_target_conflicts(self):
        import inspect
        from tactic_client_lib import TacticServerStub
        handler_path = ROOT.parent.parent / 'TH/thlib/ui/admin/raw_database_api.py'
        spec = importlib.util.spec_from_file_location('handler_raw_save_procedure', handler_path)
        handler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler)
        source = inspect.getsource(handler.raw_database_request)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        ticket = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(ticket)
        self.addCleanup(client.server.__exit__, None, None, None)
        for transport in ('handler', 'browser'):
            table = 'raw_background_' + transport
            identity = json.dumps(['sthpw', table])
            with self.store.connection(write=True) as db:
                db.execute('CREATE TABLE ' + table + ' (id INTEGER PRIMARY KEY, value TEXT, counter INTEGER)')
                db.execute('INSERT INTO ' + table + " VALUES (1,'old',0),(2,'background',0)")
            def call(action, **parameters):
                if transport == 'handler':
                    arguments = dict(action=action, project_code='admin', identity=identity, **parameters)
                    code = source + '\nreturn raw_database_request(' + ', '.join(
                        name + '=' + repr(value) for name, value in arguments.items()) + ')'
                    return client.execute_python_script('', kwargs={'code': code})['info']
                payload = dict(ticket=ticket, project='admin', identity=identity, **parameters)
                with urlopen(Request(self.url + '/admin/raw-database/' + action,
                                     json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
                    return json.load(response)['result']
            loaded = call('load')
            with self.store.connection(write=True) as db:
                db.execute('UPDATE ' + table + ' SET counter=1 WHERE id=2')
            row = loaded['document']['rows'][0]
            draft = dict(rows=[dict(key=row['key'], revision=row['revision'], deleted=False, values={'value': 'edited'})], offset=0)
            saved = call('save', document=draft, expected_revision=loaded['revision'])
            self.assertEqual([row['values']['value'] for row in saved['document']['rows']], ['edited', 'background'])
            self.assertEqual(saved['document']['rows'][1]['values']['counter'], 1)
            draft['rows'][0].update(revision=saved['document']['rows'][0]['revision'], values={'value': 'must rollback'})
            with self.store.connection(write=True) as db:
                db.execute('UPDATE ' + table + ' SET counter=1 WHERE id=1')
            with self.assertRaises((Fault, HTTPError)) as conflict:
                call('save', document=draft, expected_revision=saved['revision'])
            if isinstance(conflict.exception, HTTPError):
                with conflict.exception as response:
                    self.assertIn('row changed', response.read().decode())
            else:
                self.assertIn('row changed', conflict.exception.faultString)
            self.assertEqual(call('load')['document']['rows'][0]['values']['value'], 'edited')

    def test_original_client_queries_named_relationships_and_physical_tables(self):
        import search_join_contract
        from tactic_client_lib import TacticServerStub
        with self.store.connection(write=True) as db:
            schemas = db.execute("SELECT id,schema FROM schema WHERE project_code='one'").fetchall()
            search_join_contract.install_fixture(db)
        try:
            client = TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(self.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('admin', 'private-test-password'))
            self.addCleanup(client.server.__exit__, None, None, None)
            for order, expected in [('contract/join_tag.name', ['P2', 'P1']),
                                    ('alternate:contract/join_tag.name', ['P1', 'P2']),
                                    ('alternate:join_tag.name', ['P1', 'P2']),
                                    ('contract/join_alias.name', ['P2', 'P1'])]:
                rows = client.query('contract/join_parent', columns=['code'], order_bys=[order])
                self.assertEqual([row['code'] for row in rows], expected)
            rows = client.query('contract/join_ref', columns=['code'], order_bys=['contract/join_parent.name'])
            self.assertEqual([row['code'] for row in rows], ['R1'])
        finally:
            with self.store.connection(write=True) as db:
                for row in schemas:
                    db.execute('UPDATE schema SET schema=? WHERE id=?', (row['schema'], row['id']))
                db.execute("DELETE FROM search_object WHERE search_type LIKE 'contract/join_%'")
                for table in ('join_ref', 'join_parent', 'join_tag', 'join_id_parent'):
                    db.execute('DROP TABLE ' + table)

    def test_original_client_handoff_checkin_append_and_frame_groups(self):
        from tactic_client_lib import TacticServerStub
        from pyasm.common import Config
        from xml.etree.ElementTree import Element, SubElement, tostring
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        token = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(token)
        self.addCleanup(client.server.__exit__, None, None, None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Element('config', version='2')
            checkin = SubElement(config, 'checkin')
            for prefix in ('win32', 'linux'):
                SubElement(checkin, prefix + '_client_handoff_dir').text = (root / 'client').as_posix()
                SubElement(checkin, prefix + '_server_handoff_dir').text = (root / 'server').as_posix()
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            snapshots = []
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                try:
                    self.assertEqual(Path(client.get_handoff_dir()), root / 'client' / token)
                    handoff = root / 'server' / token
                    handoff.mkdir(parents=True)
                    (handoff / 'main.txt').write_text('main')
                    row = client.simple_checkin('sthpw/project?code=admin', 'http_handoff', '/client/main.txt', use_handoff_dir=True, create_icon=False)
                    snapshots.append(row['__search_key__'])
                    (handoff / 'extra.txt').write_text('extra')
                    client.add_file(row['code'], '/client/extra.txt', 'extra', use_handoff_dir=True)
                    (handoff / 'copied.txt').write_text('copy')
                    # The SDK's high-level copy mode stages client files itself.
                    # Exercise the server-side copy branch through its same XML-RPC transport.
                    client.server.add_file(client.ticket, row['code'], '/client/copied.txt', 'copied', True, 'copy')
                    self.assertEqual((handoff / 'copied.txt').read_text(), 'copy')
                    records = client.query('sthpw/file', [['snapshot_code', row['code']]], order_bys=['id'])
                    self.assertEqual([(record['type'], (Path(record['checkin_dir']) / record['file_name']).read_text()) for record in records],
                                     [('main', 'main'), ('extra', 'extra'), ('copied', 'copy')])
                    for frame in (1, 2):
                        (handoff / ('image.%04d.txt' % frame)).write_text('frame%d' % frame)
                    row = client.group_checkin('sthpw/project?code=admin', 'http_handoff_frames', '/client/image.####.txt', '1-2')
                    snapshots.append(row['__search_key__'])
                    for frame in (1, 2):
                        (handoff / ('more.%04d.txt' % frame)).write_text('more%d' % frame)
                    client.add_group(row['code'], '/client/more.####.txt', 'extra', '1-2', use_handoff_dir=True)
                    # Reads use the same instance and repository as Vue and other API clients.
                    files = client.query('sthpw/file', [['snapshot_code', row['code']]])
                    self.assertEqual(sorted(file['type'] for file in files), ['extra', 'main'])
                    outside = root / 'outside.0001.txt'
                    outside.write_text('keep')
                    with self.assertRaises(Fault):
                        client.group_checkin('sthpw/project?code=admin', 'http_handoff_escape', [str(root / 'outside.####.txt')], '1-1')
                    self.assertEqual(outside.read_text(), 'keep')
                    self.assertEqual(client.query('sthpw/snapshot', [['context', 'http_handoff_escape']]), [])
                finally:
                    for key in snapshots:
                        client.delete_sobject(key, include_dependencies=True)
                    Config.reload_config()
            Config.reload_config()

    def test_original_client_indexed_checkin_and_metadata(self):
        from PIL import Image
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        with self.store.connection(write=True) as db:
            old_parser = db.execute("SELECT metadata_parser FROM search_object WHERE search_type='sthpw/project'").fetchone()[0]
            db.execute("UPDATE search_object SET metadata_parser='PIL' WHERE search_type='sthpw/project'")
        snapshots = []
        try:
            with tempfile.TemporaryDirectory() as directory:
                for index in (1, 2):
                    source = Path(directory) / ('metadata%d.png' % index)
                    Image.new('RGB', (31, 17), (20, 40, 60)).save(source)
                    client.upload_file(str(source))
                    result = client.simple_checkin('sthpw/project?code=admin', 'http_indexed', str(source),
                        mode='upload', create_icon=index == 2, context_index_padding=3, checkin_type='strict')
                    snapshots.append(result['__search_key__'])
                    self.assertEqual(result['context'], 'http_indexed/%03d' % index)
                    self.assertEqual(result['version'], 1)
                    main = result['__file_sobjects__'][0]
                    metadata = json.loads(main['metadata'])
                    self.assertEqual((metadata['width'], metadata['height'], metadata['__parser__']), (31, 17, 'PIL'))
                    self.assertEqual(json.loads(result['metadata']), metadata)
                    self.assertIn('width=31', main['metadata_search'])
                    self.assertEqual((Path(main['checkin_dir']) / main['file_name']).read_bytes(), source.read_bytes())
                    for preview in result['__file_sobjects__'][1:]:
                        self.assertFalse(preview.get('metadata'))
        finally:
            with self.store.connection(write=True) as db:
                db.execute("UPDATE search_object SET metadata_parser=? WHERE search_type='sthpw/project'", (old_parser,))
            for key in snapshots:
                client.delete_sobject(key, include_dependencies=True)

    def test_original_client_directory_checkin_and_expanded_paths(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_python_script('', kwargs={'code':
            'from pyasm.search import SearchType\n'
            'row = SearchType.get("sthpw/project")\n'
            'row.set_value("metadata_parser", "")\nrow.commit(triggers=False)\nreturn True'})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bundle'
            source.mkdir()
            (source / 'main.txt').write_text('main')
            (source / 'nested').mkdir()
            (source / 'nested' / 'main.txt').write_text('child')
            (source / 'empty').mkdir()
            result = client.directory_checkin('sthpw/project?code=admin', 'rpc_directory',
                                               source.as_posix(), mode='copy')
            file = result['__file_sobjects__'][0]
            self.assertEqual(file['base_type'], 'directory')
            self.assertEqual(file['st_size'], 9)
            repo = Path(file['checkin_dir']) / file['file_name']
            self.assertEqual((repo / 'nested' / 'main.txt').read_text(), 'child')
            self.assertTrue((repo / 'empty').is_dir())
            paths = client.get_all_paths_from_snapshot(result['code'], mode='lib', expand_paths=True)
            self.assertIn(repo.as_posix(), [path.replace('\\', '/') for path in paths])
            self.assertIn((repo / 'nested').as_posix(), [path.replace('\\', '/') for path in paths])
            self.assertEqual((source / 'main.txt').read_text(), 'main')
            client.delete_sobject(result['__search_key__'], include_dependencies=True)

    def test_original_client_ingest_command_and_saved_rule(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_python_script('', kwargs={'code':
            'from pyasm.search import SearchType\n'
            'row = SearchType.get("sthpw/project")\n'
            'row.set_value("metadata_parser", "")\nrow.commit(triggers=False)\nreturn True'})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'rpc_ingest.txt'
            source.write_bytes(b'XML-RPC ingest')
            args = dict(scan_type='rule', action='file', mode='scan', title='RPC ingest',
                        base_dir='', session_base_dir=Path(directory).as_posix(),
                        rule='{snapshot.context}.txt', search_key='sthpw/project?code=admin')
            response = client.execute_cmd('tactic.command.CheckinRuleSaveCmd', args=args)
            self.assertEqual(response['status'], 'OK')
            rule = client.query('config/ingest_rule', [('title', 'RPC ingest')], single=True)
            response = client.execute_cmd('tactic.command.CheckinRuleCmd', args={'rule_code': rule['code']})
            self.assertEqual(response['status'], 'OK')
            self.assertEqual(response['info']['paths_matched'], [source.as_posix()])
            self.assertEqual(client.query('sthpw/snapshot', [('context', 'rpc_ingest')]), [])
            client.execute_cmd('tactic.command.CheckinRuleCmd', args={'rule_code': rule['code'], 'mode': 'checkin'})
            snapshot = client.query('sthpw/snapshot', [('context', 'rpc_ingest')], single=True)
            files = client.query('sthpw/file', [('snapshot_code', snapshot['code'])])
            self.assertEqual((Path(files[0]['checkin_dir']) / files[0]['file_name']).read_bytes(), source.read_bytes())
            self.assertEqual(json.loads(snapshot['metadata'])['size'], len(source.read_bytes()))

    def test_original_client_pipeline_and_custom_checkin(self):
        from tactic_client_lib import TacticServerStub
        import command_listener_contract
        with self.store.connection(write=True) as db:
            command_listener_contract.install_fixture(db)
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        client.execute_python_script('', kwargs={'code':
            'from pyasm.command import Command\n'
            'from command_listener_contract import Setup\n'
            'Command.execute_cmd(Setup())\nreturn True'})
        parent = client.get_by_code('contract/listener', 'PUBLISHED')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'custom.txt'
            source.write_bytes(b'custom via XML-RPC')
            client.upload_file(str(source))
            with self.assertRaises(Fault):
                client.simple_checkin(parent['__search_key__'], 'publish', str(source),
                    checkin_cls='command_listener_contract.Listener', create_icon=False)
            self.assertEqual(client.server.get_upload_file_size(client.ticket, source.name), len(source.read_bytes()))
            self.assertEqual(client.query('sthpw/snapshot', [('search_type', 'contract/listener')]), [])
            result = client.simple_checkin(parent['__search_key__'], 'publish', str(source),
                checkin_cls='command_listener_contract.CustomCheckin', create_icon=False, checkin_type='strict')
            self.assertEqual(result['description'], 'custom check-in')
            file = result['__file_sobjects__'][0]
            self.assertEqual((Path(file['checkin_dir']) / file['file_name']).read_bytes(), source.read_bytes())
            # Native SearchKey retains the explicit project even for a system-database type.
            full_type = client.split_search_key(parent['__search_key__'])[0]
            self.assertEqual(result['search_type'], full_type)
            notes = client.query('sthpw/note', [('search_type', full_type), ('search_code', 'PUBLISHED')])
            self.assertEqual([row['note'] for row in notes], ['listener|review'])
            client.delete_sobject(result['__search_key__'], include_dependencies=True)

    def test_original_client_http_upload_and_simple_checkin(self):
        from tactic_client_lib import TacticServerStub
        from tactic_client_lib.common import UploadMultipart, TacticUploadException
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        token = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(token)
        self.addCleanup(client.server.__exit__, None, None, None)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'Файл 🚀.bin'
            payload = b'\x00\xff\xfe\x80multipart' * 97
            source.write_bytes(payload)
            client.upload_file(str(source), chunk_size=113)
            self.assertEqual(client.server.get_upload_file_size(client.ticket, source.name), len(payload))
            result = client.simple_checkin('sthpw/project?code=admin', 'http_checkin', str(source),
                mode=None, create_icon=False, checkin_type='strict')
            file = result['__file_sobjects__'][0]
            self.assertEqual((Path(file['checkin_dir']) / file['file_name']).read_bytes(), payload)
            self.assertEqual(source.read_bytes(), payload)
            self.assertEqual(client.server.get_upload_file_size(client.ticket, source.name), 0)
            client.delete_sobject(result['__search_key__'], include_dependencies=True)
            empty = Path(directory) / 'empty.bin'
            empty.write_bytes(b'')
            empty_result = client.simple_checkin('sthpw/project?code=admin', 'http_empty', str(empty),
                mode='upload', create_icon=False, checkin_type='strict')
            empty_file = empty_result['__file_sobjects__'][0]
            self.assertEqual((Path(empty_file['checkin_dir']) / empty_file['file_name']).read_bytes(), b'')
            client.delete_sobject(empty_result['__search_key__'], include_dependencies=True)
            # A resume sends only the remaining chunks after an interrupted upload.
            uploader = UploadMultipart()
            uploader.set_upload_server(self.url + '/tactic/default/UploadServer/')
            uploader.set_ticket(token)
            uploader.set_chunk_size(113)
            uploader.upload(uploader.server_url, [('ticket', token), ('action', 'create'),
                ('file_name0', 'resume.bin')], [('file', 'resume.bin', payload[:113])])
            resume = Path(directory) / 'resume.bin'
            resume.write_bytes(payload)
            client.upload_file(str(resume), chunk_size=113, offset=1)
            result = client.simple_checkin('sthpw/project?code=admin', 'http_resume', str(resume),
                mode=None, create_icon=False, checkin_type='strict')
            file = result['__file_sobjects__'][0]
            self.assertEqual((Path(file['checkin_dir']) / file['file_name']).read_bytes(), payload)
            client.delete_sobject(result['__search_key__'], include_dependencies=True)
            # base_dir containment replaces the source SDK's ineffective prefix check.
            with self.assertRaises(Exception):
                client.upload_file(str(source), base_dir=str(Path(directory) / 'other'))
            nested = Path(directory) / 'вложенная папка' / 'data.bin'
            nested.parent.mkdir()
            nested.write_bytes(b'nested')
            client.upload_file(str(nested), base_dir=directory)
            uploaded = self.store.data_dir / 'temp' / 'upload' / token / nested.parent.name / nested.name
            self.assertEqual(uploaded.read_bytes(), b'nested')
            # Invalid actions, paths and tickets fail without damaging an existing upload.
            client.upload_file(str(source), chunk_size=113)
            for extra, ticket in (([('subdir', '../outside')], token),
                    ([('action', 'delete')], token), ([], 'invalid-ticket'),
                    ([('transaction_ticket', 'another-ticket')], token),
                    ([('upload_dir', directory)], token)):
                fields = [('ticket', ticket), ('file_name0', 'damage.bin')] + extra
                with self.assertRaises(TacticUploadException):
                    uploader.upload(uploader.server_url, fields, [('file', 'damage.bin', b'damage')])
            self.assertEqual(client.server.get_upload_file_size(client.ticket, source.name), len(payload))

            result = client.simple_checkin('sthpw/project?code=admin', 'http_default_binary', str(source), checkin_type='strict')
            self.assertEqual([file['type'] for file in result['__file_sobjects__']], ['main'])
            client.delete_sobject(result['__search_key__'], include_dependencies=True)
            pdf = Path(directory) / 'unported.pdf'
            pdf.write_bytes(b'pdf')
            client.upload_file(str(pdf))
            with self.assertRaises(Fault):
                client.simple_checkin('sthpw/project?code=admin', 'http_pdf_guard', str(pdf))
            self.assertEqual(client.query('sthpw/snapshot', [['context', 'http_pdf_guard']]), [])
            self.assertEqual(client.server.get_upload_file_size(client.ticket, pdf.name), 3)
            # Exercise the source SDK wrapper itself without editing its file.
            spec = importlib.util.spec_from_file_location('tactic_client_lib.source_upload_contract',
                LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            original_client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            original_client.set_server(self.url)
            original_client.set_project('admin')
            original_client.set_ticket(token)
            self.addCleanup(original_client.server.__exit__, None, None, None)
            result = original_client.simple_checkin('sthpw/project?code=admin', 'source_http_checkin',
                str(source), mode='upload', create_icon=False, checkin_type='strict')
            file = result['__file_sobjects__'][0]
            self.assertEqual((Path(file['checkin_dir']) / file['file_name']).read_bytes(), payload)
            original_client.delete_sobject(result['__search_key__'], include_dependencies=True)

    def test_http_upload_atomic_replacement_browser_and_limits(self):
        from tactic_client_lib.common import UploadMultipart, TacticUploadException
        from unittest.mock import patch
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        token = ticket['ticket']
        url = self.url + '/tactic/default/UploadServer/'
        uploader = UploadMultipart()
        # HTTP upload has its own limit; it accepts chunks larger than the XML-RPC envelope.
        payload = b'\x00\xff' * (MAX_BODY // 2 + 1)
        status, _, _ = uploader.upload(url, [('ticket', token), ('action', 'create'),
            ('file_name0', 'browser.bin')], [('file', 'browser.bin', payload)])
        self.assertEqual(status, 200)
        destination = self.store.data_dir / 'temp' / 'upload' / token / 'browser.bin'
        self.assertEqual(destination.read_bytes(), payload)
        # A bad second file must roll back an earlier replacement in this same request.
        boundary = 'browser-boundary'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="ticket"\r\n\r\n{token}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="num_files"\r\n\r\n2\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file0"; filename="browser.bin"\r\n\r\nreplacement\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file1"; filename="broken.bin"\r\n\r\ndata:xyz/xyz;base64,???\r\n'
                f'--{boundary}--\r\n').encode('utf-8')
        request = Request(url, body, {'Content-Type': 'multipart/form-data; boundary=' + boundary})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(destination.read_bytes(), payload)
        self.assertFalse((destination.parent / 'broken.bin').exists())
        with patch('tactic_stream.server.app.MAX_UPLOAD_BODY', 100):
            with self.assertRaises(HTTPError) as caught:
                urlopen(request)
            self.assertEqual(caught.exception.code, 413)
        raw_body = body.replace(b'data:xyz/xyz;base64,???', b'raw browser bytes')
        with urlopen(Request(url, raw_body, request.headers)) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(destination.read_bytes(), b'replacement')
        self.assertEqual((destination.parent / 'broken.bin').read_bytes(), b'raw browser bytes')
        # UploadServer stages only private ticket files; object writes still require project ACLs.
        reader = proxy.insert(ticket, 'sthpw/login', {'login': 'upload_reader',
            'password': hash_password('private-reader-password')})
        reader_token = proxy.get_ticket('upload_reader', 'private-reader-password', None)
        uploader.upload(url, [('ticket', reader_token)], [('file', 'reader.bin', b'private staging')])
        self.assertEqual((self.store.data_dir / 'temp' / 'upload' / reader_token / 'reader.bin').read_bytes(), b'private staging')
        with self.assertRaises(Fault) as caught:
            proxy.simple_checkin(dict(ticket=reader_token, project='admin'), 'sthpw/project?code=admin',
                'reader_denied', 'reader.bin')
        self.assertEqual(caught.exception.faultCode, 403)
        proxy.delete_sobject(ticket, reader['__search_key__'])
        # Native client retries a create, returns its result, and never retries an ambiguous append.
        with patch.object(uploader, 'posturl', side_effect=[OSError('network'), (200, 'OK', b'')]) as call:
            self.assertEqual(uploader.upload(url, [('action', 'create')], []), (200, 'OK', b''))
            self.assertEqual(call.call_count, 2)
        with patch.object(uploader, 'posturl', side_effect=OSError('network')) as call:
            with self.assertRaises(TacticUploadException):
                uploader.upload(url, [('action', 'append')], [])
            self.assertEqual(call.call_count, 1)

    def test_original_client_default_image_checkin(self):
        from PIL import Image
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'Картинка.png'
            Image.new('RGBA', (800, 400), (255, 0, 0, 0)).save(source)
            payload = source.read_bytes()
            result = client.simple_checkin('sthpw/project?code=admin', 'http_image', str(source),
                mode='upload', checkin_type='strict')
            files = {file['type']: file for file in result['__file_sobjects__']}
            self.assertEqual(sorted(files), ['icon', 'main', 'web'])
            for kind, dimensions in (('main', (800, 400)), ('web', (640, 320)), ('icon', (120, 60))):
                file = files[kind]
                path = Path(file['checkin_dir']) / file['file_name']
                with Image.open(path) as image:
                    self.assertEqual(image.size, dimensions)
                    if kind != 'main':
                        self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                if kind == 'main':
                    self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(source.read_bytes(), payload)
            # add_file uses the same icon pipeline without creating another version.
            client.upload_file(str(source))
            with self.assertRaises(Fault):
                client.add_file(result['code'], source.name, file_type='extra', create_icon=True)
            self.assertEqual(len(client.query('sthpw/file', [['snapshot_code', result['code']]])), 3)
            extra = source.with_name('Extra.png')
            extra.write_bytes(payload)
            client.upload_file(str(extra))
            appended = client.add_file(result['code'], extra.name, file_type='extra', create_icon=True)
            self.assertEqual(appended['version'], result['version'])
            self.assertEqual(len(client.query('sthpw/file', [['snapshot_code', result['code']]])), 6)
            client.delete_sobject(result['__search_key__'], include_dependencies=True)

    def test_real_xmlrpc_task_and_note_lifecycle(self):
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        task = proxy.insert(ticket, 'sthpw/task', {'process': 'publish', 'status': 'Pending'})
        note = proxy.insert(ticket, 'sthpw/note', {'context': 'publish', 'login': 'admin', 'note': "Комментарий O'Reilly"}, {}, task['__search_key__'])
        self.assertEqual(proxy.get_parent(ticket, note['__search_key__'])['code'], task['code'])
        proxy.update(ticket, task['__search_key__'], {'status': 'Complete'})
        self.assertTrue(proxy.get_by_search_key(ticket, task['__search_key__'])['actual_end_date'])
        with self.assertRaises(Fault):
            proxy.update(ticket, [task['__search_key__'], note['__search_key__']],
                         [{'description': 'must roll back'}, {'missing_column': 'fail'}])
        self.assertNotEqual(proxy.get_by_search_key(ticket, task['__search_key__'])['description'], 'must roll back')
        proxy.delete_sobject(ticket, note['__search_key__'])
        proxy.delete_sobject(ticket, task['__search_key__'])
        self.assertEqual(proxy.get_by_code(ticket, 'sthpw/task', task['code']), {})

    def test_api_logs_legacy_blocks_and_faults_without_passwords(self):
        proxy = self.proxy()
        with self.assertLogs('tactic_stream.server.api', level='INFO') as captured:
            ticket = self.ticket(proxy)
            proxy.query(ticket, 'contract/entity', [['code', 'A']])
            proxy.query(ticket, 'sthpw/login', [['password', 'private-filter-secret']])
            with self.assertRaises(Fault):
                proxy.get_ticket('admin', 'private-wrong-password')
            with self.assertRaises(Fault):
                proxy.not_migrated(ticket)
        output = '\n'.join(captured.output)
        for secret in ('private-test-password', 'private-wrong-password', 'private-filter-secret'):
            self.assertNotIn(secret, output)
        self.assertIn('contract/entity', output)
        self.assertIn('Duration:', output)
        self.assertIn('Total Duration:', output)
        self.assertIn('AuthenticationError', output)
        self.assertIn('UnsupportedContract', output)
        self.assertIn('user: admin', output)
        self.assertIn('ticket: ' + ticket['ticket'], output)
        self.assertRegex(output, r'request_id: \d+ - #\d{7}')
        self.assertRegex(output, r'timestamp: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
        self.assertIn('simple method: <function ApiXMLRPC.query at 0x', output)
        self.assertIn('Memory:', output)
        self.assertIn('Increment:', output)
        query_block = next(line for line in captured.output if 'ApiXMLRPC.query' in line and 'contract/entity' in line)
        arguments = query_block.split('\n[', 1)[1].split('\n]\n', 1)[0]
        self.assertEqual(json.loads('[' + arguments + '\n]'), ['contract/entity', [['code', 'A']]])

    def test_admin_rpc_logs_match_xmlrpc_for_results_kwargs_and_errors(self):
        import re

        proxy = self.proxy()
        ticket = self.ticket(proxy)
        cases = (
            ('query', [ticket, 'contract/entity'], {'filters': [['code', 'A']]}, None, None),
            ('query', [ticket, 'sthpw/login'], {'filters': [['password', 'private-filter-secret']]}, None, None),
            ('execute_python_script', [ticket, ''], {'kwargs': {'code': 'return {"ok": True}', '_debug_args': False}}, None, None),
            ('get_ticket', ['admin', 'private-wrong-password'], {}, 403, 'AuthenticationError'),
            ('not_migrated', [ticket], {}, 501, 'UnsupportedContract'),
            ('query', [ticket], {}, 400, 'TypeError'),
        )
        request_ids = set()
        for method, args, kwargs, status, error in cases:
            blocks = []
            for protocol in ('xmlrpc', 'json'):
                with self.subTest(method=method, protocol=protocol, error=error):
                    with self.assertLogs('tactic_stream.server.api', level='INFO') as captured:
                        if protocol == 'xmlrpc':
                            positional = [*args, *kwargs.values()]
                            if status:
                                with self.assertRaises(Fault) as caught:
                                    getattr(proxy, method)(*positional)
                                self.assertEqual(caught.exception.faultCode, status)
                            else:
                                getattr(proxy, method)(*positional)
                        elif status:
                            with self.assertRaises(HTTPError) as caught:
                                self.admin_rpc(method, args, kwargs)
                            self.assertEqual(caught.exception.code, status)
                            caught.exception.close()
                        else:
                            self.admin_rpc(method, args, kwargs)
                    self.assertEqual(len(captured.records), 1)
                    block = captured.records[0].getMessage()
                    request_id = re.search(r'^request_id: (\d+ - #\d{7})$', block, re.M).group(1)
                    self.assertNotIn(request_id, request_ids)
                    request_ids.add(request_id)
                    self.assertRegex(block, r'(?m)^timestamp: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
                    self.assertRegex(block, r'Duration: \d+\.\d{3} seconds \(request_id: ' + re.escape(request_id) + r'\)')
                    for field in ('Memory:', 'Increment:', 'Total Duration:'):
                        self.assertIn(field, block)
                    for secret in ('private-test-password', 'private-wrong-password', 'private-filter-secret'):
                        self.assertNotIn(secret, block)
                    if error:
                        self.assertIn('error: ' + error, block)
                    else:
                        self.assertIn('user: admin', block)
                        self.assertIn('simple method: <function ApiXMLRPC.' + method, block)
                    # Request identity/timing/memory vary; method, arguments and outcome must match.
                    normalized = re.sub(r'(?m)^(request_id:|timestamp:|Duration:|Memory:|Increment:|Total Duration:).*\n?', '', block)
                    blocks.append(normalized)
            self.assertEqual(blocks[0], blocks[1], (method, error))

    def test_real_xmlrpc_task_generation(self):
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        parent = 'contract/entity?project=one&code=A'
        manual = proxy.create_task(ticket, parent, 'review', 'final', 'Check',
                                   '2026-01-16', '2026-01-19', 4, 'admin')
        self.assertEqual((manual['context'], manual['assigned']), ('review/final', 'admin'))
        created = proxy.add_initial_tasks(ticket, parent, None, [], True, 0, '2026-01-16')
        self.assertEqual([row['process'] for row in created], ['publish'])
        self.assertEqual(proxy.add_initial_tasks(ticket, parent), [])
        copied = proxy.add_initial_tasks(ticket, parent, None, [], False, 0, '2026-01-16')
        self.assertEqual(copied[0]['context'], 'publish/001')
        with self.assertRaises(Fault):
            proxy.create_task(ticket, parent, 'review', None, None, '2026-01-19', '2026-01-16')
        for row in [manual, *created, *copied]:
            proxy.delete_sobject(ticket, row['__search_key__'])

    def test_handler_admin_access_rules_through_xmlrpc(self):
        from tactic.ui.panel.security_manager_wdg import permission_list
        from tactic.ui.startup.security_wdg import GearMenuSecurityWdg
        original = ast.parse((LEGACY / 'src/tactic/ui/panel/security_manager_wdg.py').read_text(encoding='utf-8'))
        catalog = next(node for node in original.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'permission_list' for target in node.targets))
        self.assertEqual(permission_list, ast.literal_eval(catalog.value))
        original = ast.parse((LEGACY / 'src/tactic/ui/startup/security_wdg.py').read_text(encoding='utf-8'))
        owner = next(node for node in original.body if isinstance(node, ast.ClassDef) and node.name == 'GearMenuSecurityWdg')
        method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'get_all_menu_names')
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<original gear security catalog>', 'exec'), namespace)
        self.assertEqual(GearMenuSecurityWdg.get_all_menu_names(), namespace['get_all_menu_names'](None))
        path = ROOT.parent.parent / 'TH/thlib/ui/admin/security_api.py'
        source = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                        and node.name == 'security_request')
        code = ast.get_source_segment(source, function)
        code += '\nreturn security_request(action=kwargs["action"], project_code=kwargs["project"], identity=kwargs["project"], document=kwargs.get("document"), expected_revision=kwargs.get("revision", ""))'
        proxy = self.proxy()
        token = self.ticket(proxy)
        def request(project='admin', action='load', **kwargs):
            return json.loads(proxy.execute_python_script(dict(token, project=project), '',
                dict(code=code, project=project, action=action, **kwargs))['info'])
        group = proxy.insert(token, 'sthpw/login_group', dict(code='access_contract', login_group='access_contract',
            access_level='low', access_rules='<rules/>'))
        configs = []
        try:
            for project in ('admin', 'one'):
                data = request(project)
                self.assertEqual(data['identity'], project)
                self.assertTrue(data['canWrite'])
                self.assertIn('access_contract', data['document']['groups'])
                metadata = data['metadata']
                self.assertIn('view_side_bar', [row['key'] for row in metadata['builtinPermissions']])
                self.assertIn('medium', metadata['accessLevels'])
                self.assertTrue(metadata['targets']['gear_menu'])
                self.assertTrue(metadata['targets']['link'])
            auth = dict(token, project='admin')
            for view, xml in (
                    ('project_view', '<config><project_view><element name="contract_folder"/></project_view></config>'),
                    ('contract_child_links', '<config><contract_child_links><element name="contract_users"/></contract_child_links></config>'),
                    ('definition', '<config><definition><element name="contract_folder" title="Contract folder"><display class="FolderWdg"><view>contract_child_links</view></display></element><element name="contract_users" title="Contract users"><display class="LinkWdg"><search_type>sthpw/login</search_type></display></element></definition></config>')):
                configs.append(proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view=view, config=xml, priority=1000)))
            data = request()
            links = data['metadata']['targets']['link']
            self.assertIn(dict(label='Contract users', depth=1, attributes=dict(element='contract_users', project='admin')), links)
            document = data['document']
            document['groups']['access_contract']['xml'] = '<rules><rule group="builtin" key="view_side_bar" access="deny"/></rules>'
            saved = request(action='save', document=document, revision=data['revision'])
            self.assertEqual(saved['document'], document)
            self.assertNotEqual(saved['revision'], data['revision'])
            with self.assertRaisesRegex(Fault, 'changed on the server'):
                request(action='save', document=document, revision=data['revision'])
            invalid = json.loads(json.dumps(document))
            invalid['groups']['access_contract']['xml'] = '<rules><rule group="builtin" key="view_side_bar" access="INVALID"/></rules>'
            with self.assertRaisesRegex(Fault, 'valid access level'):
                request(action='save', document=invalid, revision=saved['revision'])
            self.assertEqual(request()['document'], document)
        finally:
            for config in configs:
                proxy.delete_sobject(dict(token, project='admin'), config['__search_key__'])
            proxy.delete_sobject(token, group['__search_key__'])

    def test_handler_admin_search_types_load_through_xmlrpc(self):
        path = ROOT.parent.parent / 'TH/thlib/ui/admin/search_types_api.py'
        source = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                        and node.name == 'search_types_request')
        code = ast.get_source_segment(source, function)
        code += '\nreturn search_types_request(action="load", project_code=kwargs["project"], identity=kwargs["identity"])'
        proxy = self.proxy()
        token = self.ticket(proxy)
        for project, identity in (('admin', 'sthpw/change_timestamp'),
                                  ('one', 'contract/entity'), ('two', 'contract/entity')):
            with self.subTest(project=project, search_type=identity):
                result = json.loads(proxy.execute_python_script(dict(token, project=project), '',
                    dict(code=code, project=project, identity=identity))['info'])
                self.assertEqual(result['identity'], identity)
                self.assertTrue(result['metadata']['tableAvailable'])
                self.assertTrue(result['metadata']['columns'])
                self.assertTrue(result['canWrite'])

    def test_handler_extended_checkin_through_xmlrpc(self):
        # Run the actual unchanged Handler procedures, including their local SDK
        # helpers, through XML-RPC/Mako rather than substituting simple_checkin.
        source = (ROOT.parent.parent / 'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        functions = {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
                     if isinstance(node, ast.FunctionDef) and node.name in
                     ('get_virtual_snapshot_extended', 'create_snapshot_extended')}
        proxy = self.proxy(); auth = self.ticket(proxy); auth['project'] = 'one'
        key, context = 'contract/entity?project=one&code=A', 'handler_extended_checkin'
        proxy.insert(auth, 'config/naming', dict(search_type='contract/entity', snapshot_type='file',
            context=context, dir_naming='{project.code}/handler/v{version}'))
        proxy.insert(auth, 'config/naming', dict(search_type='contract/entity', snapshot_type='file',
            context=context, latest_versionless=True, dir_naming='{project.code}/handler/latest',
            file_naming='{basefile}.{ext}'))
        files = [['payload', dict(t=['main'], e=['bin'], s=[''], p=[''], m={})]]
        for version in (1, 2):
            payload = bytes([0, 255, version]) + b'Handler file'
            code = functions['get_virtual_snapshot_extended'] + '\nreturn get_virtual_snapshot_extended(**kwargs["options"])'
            plan = json.loads(proxy.execute_python_script(auth, '', dict(code=code, options=dict(
                search_key=key, context=context, files_dict=json.dumps(files), keep_file_name=True)))['info'])
            destination = plan[0][1]['versioned']; alias = plan[0][1]['versionless']
            filename = ''.join(destination['names'][0])
            proxy.upload_file(auth, filename, Binary(payload))
            info = dict(files_types=['main'], file_sizes=[len(payload)], upload_file_names=[filename],
                        version_metadata=[dict(filename='payload', new_filename='payload', new_file_ext='bin', test=version)],
                        versionless_metadata=[dict(test=version)])
            code = functions['create_snapshot_extended'] + '\nreturn create_snapshot_extended(**kwargs["options"])'
            saved = proxy.execute_python_script(auth, '', dict(code=code, options=dict(search_key=key,
                context=context, project_code='one', files_info=json.dumps(info), mode='upload', create_icon=False)))['info']
            self.assertEqual(saved['version'], version)
            self.assertEqual(saved['context'], context)
            snapshot_key = 'sthpw/snapshot?code=' + saved['code']
            paths = proxy.get_all_paths_from_snapshot(auth, snapshot_key)
            self.assertEqual(Path(paths[0]).read_bytes(), payload)
            alias_name = ''.join(alias['names'][0])
            self.assertTrue(Path(paths[0]).as_posix().endswith('/' + destination['paths'][0] + '/' + filename))
            snapshots = ast.literal_eval(proxy.query(auth, 'sthpw/snapshot', [['context', context], ['version', -1]]))
            self.assertEqual(len(snapshots), 1)
            alias_paths = proxy.get_all_paths_from_snapshot(auth, 'sthpw/snapshot?code=' + snapshots[0]['code'])
            self.assertEqual(Path(alias_paths[0]).name, alias_name)
            self.assertEqual(Path(alias_paths[0]).read_bytes(), payload)

    def test_handler_inplace_image_checkin_through_xmlrpc(self):
        previous_path = sys.path.copy()
        try:
            sys.path.insert(0, str(ROOT.parent.parent / 'TH'))
            from thlib.global_functions import FileObject
        finally:
            sys.path[:] = previous_path
        source = (ROOT.parent.parent / 'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                        and node.name == 'create_snapshot_extended')
        code = ast.get_source_segment(source, function) + '\nreturn create_snapshot_extended(**kwargs["options"])'
        proxy = self.proxy(); auth = self.ticket(proxy); auth['project'] = 'one'
        key = 'contract/entity?project=one&code=A'
        root = Path(proxy.execute_python_script(auth, '', dict(code=
            'from pyasm.common import Environment\nreturn Environment.get_asset_dir()'))['info'])
        import base64
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        for only_versionless, storage in ((False, 'copy'), (False, 'hardlink'), (True, 'copy'),
                                         (False, 'empty'), (True, 'empty')):
            context = ('handler_inplace_only' if only_versionless else 'handler_inplace') + '_' + storage
            for version in (1, 2):
                payload = image + bytes([version])
                contents = [b'', payload, b''] if storage == 'empty' else [payload] * 3
                # Handler copies these files into the repository before calling XML-RPC.
                directories = {name: 'one/handler/%s/%s' % (context, suffix)
                               for name, suffix in (('version', 'v%s' % version), ('versionless', 'latest'))}
                paths = {}
                for name, directory in directories.items():
                    folder = root / directory; folder.mkdir(parents=True, exist_ok=True)
                    paths[name] = [(folder / (kind + '.png')).as_posix() for kind in ('main', 'web', 'icon')]
                    for index, path in enumerate(paths[name]):
                        if name == 'versionless' and storage == 'hardlink':
                            Path(path).unlink(missing_ok=True)
                            os.link(paths['version'][index], path)
                        else:
                            Path(path).write_bytes(contents[index])
                measured_paths = paths['versionless' if only_versionless else 'version']
                sizes = FileObject().get_sizes_list(files_list=measured_paths)
                self.assertEqual(sizes, [len(content) for content in contents])
                info = dict(files_types=['main', 'web', 'icon'], file_sizes=sizes,
                    version_files=paths['version'], versionless_files=paths['versionless'],
                    version_files_paths=[directories['version']] * 3,
                    versionless_files_paths=[directories['versionless']] * 3,
                    version_metadata=[dict(test=version)] * 3, versionless_metadata=[dict(test=version)] * 3)
                saved = proxy.execute_python_script(auth, '', dict(code=code, options=dict(search_key=key,
                    context=context, project_code='one', files_info=json.dumps(info), mode='inplace',
                    repo_name='default', create_icon=False, only_versionless=only_versionless)))['info']
                self.assertEqual(saved['version'], -1 if only_versionless else version)
                aliases = ast.literal_eval(proxy.query(auth, 'sthpw/snapshot', [['context', context], ['version', -1]]))
                self.assertEqual(len(aliases), 1)
                for snapshot in (saved, aliases[0]):
                    actual = proxy.get_all_paths_from_snapshot(auth, 'sthpw/snapshot?code=' + snapshot['code'])
                    self.assertEqual(len(actual), 3)
                    for path in actual:
                        index = ('main', 'web', 'icon').index(Path(path).stem)
                        self.assertEqual(Path(path).read_bytes(), contents[index])
                    files = ast.literal_eval(proxy.query(auth, 'sthpw/file',
                        [['snapshot_code', snapshot['code']]]))
                    self.assertEqual(len(files), 3)
                    for file in files:
                        index = ('main', 'web', 'icon').index(Path(file['file_name']).stem)
                        self.assertEqual(int(file['st_size']), len(contents[index]))
                if storage == 'hardlink':
                    self.assertTrue(all(os.path.samefile(left, right)
                                        for left, right in zip(paths['version'], paths['versionless'])))
                if version == 2 and not only_versionless:
                    for path in (root / ('one/handler/%s/v1' % context)).glob('*.png'):
                        index = ('main', 'web', 'icon').index(path.stem)
                        expected = b'' if storage == 'empty' and index != 1 else image + bytes([1])
                        self.assertEqual(path.read_bytes(), expected)

    def test_handler_project_and_user_selects_through_xmlrpc(self):
        path = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        source = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                        and node.name == 'query_EditWdg')
        code = ast.get_source_segment(source, function)
        code += '\nreturn query_EditWdg(args=kwargs["form_args"], search_type=kwargs["kind"])'
        proxy = self.proxy()
        auth = self.ticket(proxy)
        auth['project'] = 'one'
        # Real inherited file configurations, not a minimal custom test form.
        for kind, elements in (('sthpw/milestone', 'project_code'),
                               ('sthpw/note', 'login')):
            with self.subTest(search_type=kind):
                result = json.loads(proxy.execute_python_script(auth, '', dict(code=code, kind=kind,
                    form_args=dict(search_type=kind, view='edit', element_names=elements)))['info'])
                widget = result['InputWidgets'][0]
                self.assertEqual(widget['name'], elements)
                self.assertEqual(widget['values'][0], '')
                self.assertEqual(len(widget['values']), len(widget['labels']))
                if elements == 'project_code':
                    self.assertEqual(widget['class_name'], 'tactic.ui.input.project_user_select_wdg.ProjectSelectWdg')
                    self.assertIn('one', widget['values'])
                    self.assertNotIn('admin', widget['values'])
                    self.assertNotIn('sthpw', widget['values'])
                    self.assertEqual(widget['__display_values__'], ['one'])
                else:
                    self.assertEqual(widget['class_name'], 'tactic.ui.input.project_user_select_wdg.UserSelectWdg')
                    self.assertEqual(widget['values'].count('admin'), 1)
        self.assertFalse((ROOT / 'src/pyasm/prod').exists())

    def test_handler_native_table_layout_through_xmlrpc(self):
        # Execute the existing Handler function without edits or a UI dependency.
        handler = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        tree = ast.parse(handler.read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'query_table_layout')
        source = ast.get_source_segment(handler.read_text(encoding='utf-8'), function)
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        view = 'stream_table_contract'
        xml = '<config><%s><element name="code"/><element name="name" title="Entity name" width="180"/><element name="amount"/></%s></config>' % (view, view)
        config = proxy.insert(ticket, 'config/widget_config', dict(search_type='contract/entity', view=view, config=xml))
        try:
            keys = ['contract/entity?project=one&code=A', 'contract/entity?project=one&code=B']
            code = source + '\nreturn query_table_layout("contract/entity", search_keys=kwargs["keys"], view=kwargs["view"], project_code="one")'
            result = json.loads(proxy.execute_python_script(ticket, '', dict(code=code, keys=keys, view=view))['info'])
            self.assertEqual([column['name'] for column in result['columns']], ['code', 'name', 'amount'])
            self.assertEqual(result['columns'][1]['title'], 'Entity name')
            self.assertEqual(str(result['columns'][1]['width']), '180')
            self.assertTrue(all(column['sortable'] for column in result['columns']))
            self.assertTrue(all(column['resolvedClass'] == 'tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg'
                                for column in result['columns']))
            self.assertEqual(result['rows'][keys[0]]['amount'], dict(text='0', error=''))
            self.assertEqual(result['rows'][keys[1]]['name'], dict(text="O'Reilly", error=''))
            self.assertTrue(all(not cell['error'] for cells in result['rows'].values() for cell in cells.values()))
        finally:
            proxy.delete_sobject(ticket, config['__search_key__'])

    def test_handler_full_checkin_cells_match_stream_for_tasks_and_notes(self):
        path = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        text = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)
        proxy = self.proxy()
        auth = self.ticket(proxy)
        parent = 'contract/entity?project=one&code=A'
        view = 'full_checkin_contract'
        xml = '''<config><full_checkin_contract>
<element name="general_checkin"><display class="tactic.ui.table.CheckinButtonElementWdg"><width>800</width></display></element>
<element name="self_checkin"><display class="tactic.ui.table.CheckinButtonElementWdg"><sobject_mode>self</sobject_mode></display></element>
</full_checkin_contract></config>'''
        for kind in ('sthpw/task', 'sthpw/note'):
            proxy.insert(auth, 'config/widget_config', dict(search_type=kind, view=view, config=xml))
            records = [proxy.insert(auth, kind, dict(process='model', context=context), {}, parent)
                       for context in ('model/main', 'model/001', '')]
            keys = [row['__search_key__'] for row in records]
            code = source + '''
import json
from tactic_stream.server.table_cells import read_table_cells
return {"native": json.loads(query_table_layout(kwargs["kind"], kwargs["keys"], kwargs["view"], project_code="one")),
        "stream": read_table_cells(kwargs["kind"], kwargs["view"], kwargs["keys"])}'''
            result = proxy.execute_python_script(auth, '', dict(code=code, kind=kind, keys=keys, view=view))['info']
            for index, key in enumerate(keys):
                for column in ('general_checkin', 'self_checkin'):
                    native = result['native']['rows'][key][column]
                    self.assertFalse(native['error'], native)
                    self.assertEqual({name: value for name, value in native.items() if name != 'error'},
                                     result['stream'][key][column])
                    self.assertEqual(native['targetSearchKey'], parent if column == 'general_checkin' else key)
                    self.assertEqual(native['process'], 'model')
                    self.assertEqual(native['context'], 'model/main' if index == 0 else 'model')

    def test_handler_extended_table_values_through_xmlrpc(self):
        handler = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        text = handler.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)
        proxy = self.proxy()
        auth = self.ticket(proxy)
        view = 'frame_values'
        task = proxy.insert(auth, 'sthpw/task', dict(code='B07_TASK', process='model', context='model/main',
            status='Pending', bid_end_date='2030-05-01 12:30:00'), {}, 'contract/entity?project=one&code=A')
        xml = '''<config><frame_values>
<element name="sub"><display class="tactic.ui.table.SubContextElementWdg"/></element>
<element name="due"><display class="tactic.ui.table.TaskDaysDueElementWdg"/></element>
<element name="groups"><display class="tactic.ui.table.TaskGroupCompletionWdg"><options>[{"label":"MODEL","context":["model/main"]}]</options></display></element>
<element name="summary"><display class="tactic.ui.table.TaskSummaryElementWdg"><mode>minimal</mode></display></element>
<element name="broken"><display class="tactic.ui.table.TaskGroupCompletionWdg"><options>invalid json</options></display></element>
<element name="select"><display class="pyasm.widget.CheckboxColWdg"/></element>
<element name="search_type"><display class="pyasm.widget.SearchTypeElementWdg"/></element>
</frame_values></config>'''
        config = proxy.insert(auth, 'config/widget_config', dict(search_type='sthpw/task', view=view, config=xml))
        try:
            code = source + '''
import json
from tactic_stream.server.table_cells import read_table_cells
return json.dumps({"native": json.loads(query_table_layout("sthpw/task", search_keys=kwargs["keys"], view=kwargs["view"], project_code="one")), "browser": read_table_cells("sthpw/task", kwargs["view"], kwargs["keys"])})'''
            result = json.loads(proxy.execute_python_script(auth, '', dict(code=code,
                keys=[task['__search_key__']], view=view))['info'])
            native = result['native']['rows'][task['__search_key__']]
            browser = result['browser'][task['__search_key__']]
            for name in ['sub', 'due', 'groups', 'select', 'search_type']:
                self.assertFalse(native[name].get('error'), native[name])
                self.assertFalse(browser[name].get('error'), browser[name])
                self.assertEqual(native[name]['text'], browser[name]['text'])
            self.assertEqual(native['sub']['text'], 'main')
            self.assertEqual(native['select']['search_key'], task['__search_key__'])
            self.assertEqual(native['groups']['groups'][0]['label'], 'MODEL')
            self.assertEqual(browser['summary']['summaryMode'], 'minimal')
            self.assertEqual(browser['summary']['widthHint'], 100)
            self.assertTrue(native['broken']['error'])
            self.assertTrue(browser['broken']['error'])
        finally:
            proxy.delete_sobject(auth, config['__search_key__'])
            proxy.delete_sobject(auth, task['__search_key__'])

    def test_handler_table_metadata_values_through_xmlrpc(self):
        handler = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        text = handler.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)
        proxy = self.proxy()
        auth = self.ticket(proxy)
        with self.store.connection(write=True) as db:
            notice_id = db.execute('INSERT INTO notification_log (subject,message) VALUES (?,?)', ('Frame notification','Test')).lastrowid
            db.executemany('INSERT INTO notification_login (notification_log_id,login,type) VALUES (?,?,?)', [(notice_id,'admin','to'),(notice_id,'test','cc')])
            preference_id = db.execute('INSERT INTO pref_list (key,title,description,type) VALUES (?,?,?,?)', ('frame_table_test','Debug','Frame hint','string')).lastrowid
        notice = proxy.get_by_search_key(auth, 'sthpw/notification_log?id='+str(notice_id))
        preference = proxy.get_by_search_key(auth, 'sthpw/pref_list?id='+str(preference_id))
        for search_type, key, widget in [
                ('sthpw/project', 'sthpw/project?code=one', 'tactic.ui.table.ProjectWdg'),
                ('sthpw/search_object', 'sthpw/search_object?code=contract/entity', 'tactic.ui.app.SearchTypeHasTableElementWdg'),
                ('sthpw/notification_log', notice['__search_key__'], 'tactic.ui.table.RecipientElementWdg'),
                ('sthpw/pref_list', preference['__search_key__'], 'tactic.ui.table.PreferenceDescriptionWdg'),
                ('contract/child', 'contract/child?project=one&code=CH1', 'tactic.ui.table.RelatedElementWdg')]:
            view = 'frame_metadata'
            options = '<template>contract/child.contract/entity</template><column>name</column>' if widget.endswith('.RelatedElementWdg') else ''
            config = proxy.insert(auth, 'config/widget_config', dict(search_type=search_type, view=view,
                config='<config><frame_metadata><element name="metadata"><display class="'+widget+'">'+options+'</display></element></frame_metadata></config>'))
            try:
                code = source + '''
import json
from tactic_stream.server.table_cells import read_table_cells
return json.dumps({"native": json.loads(query_table_layout(kwargs["kind"], search_keys=kwargs["keys"], view=kwargs["view"], project_code="one")), "browser": read_table_cells(kwargs["kind"], kwargs["view"], kwargs["keys"])})'''
                result = json.loads(proxy.execute_python_script(auth, '', dict(code=code,
                    kind=search_type, keys=[key], view=view))['info'])
                native = result['native']['rows'][key]['metadata']
                browser = result['browser'][key]['metadata']
                self.assertFalse(native.get('error'), native)
                self.assertFalse(browser.get('error'), browser)
                self.assertEqual(native['text'], browser['text'])
                if search_type == 'sthpw/project':
                    self.assertEqual(browser['entries'][0]['value'], 'Yes')
                elif search_type == 'sthpw/search_object':
                    self.assertTrue(browser['good'], browser)
                elif search_type == 'sthpw/notification_log':
                    self.assertEqual(browser['text'], 'to: admin\ncc: test')
                    self.assertEqual(len(browser['entries']), 2)
                elif search_type == 'sthpw/pref_list':
                    self.assertEqual(browser['text'], 'Frame hint')
                    self.assertIn('Debug Widget', browser['tooltip'])
                else:
                    self.assertEqual(browser['text'], 'Первый')
            finally:
                proxy.delete_sobject(auth, config['__search_key__'])

    def test_real_xmlrpc_workflow_messages(self):
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        ticket['project'] = 'admin'
        key = "workflow|key O'Reilly"
        self.assertEqual(proxy.get_message(ticket, key), {})
        self.assertEqual(proxy.log_message(ticket, key, {'name': 'Данные'}, 'pending', 'workflow', True), 'OK')
        self.assertEqual(proxy.log_message(ticket, key, None, 'complete', 'workflow', False), 'OK')
        message = proxy.get_message(ticket, key)
        self.assertEqual(json.loads(message['message']), {'name': 'Данные'})
        self.assertEqual(message['status'], 'complete')
        self.assertEqual([row['code'] for row in proxy.get_messages(ticket, [key])], [key])
        state = proxy.insert(ticket, 'config/process_state', {'process': 'design', 'status': 'pending'}, {}, 'sthpw/project?code=admin')
        proxy.update(ticket, state['__search_key__'], {'status': 'complete'})
        self.assertEqual(proxy.get_parent(ticket, state['__search_key__'])['code'], 'admin')
        proxy.delete_sobject(ticket, state['__search_key__'])
        proxy.delete_sobject(ticket, message['__search_key__'])

    def test_original_tactic_client_runs_unchanged_against_new_server(self):
        # Load the unchanged SDK; its six dependency is installed with the package.
        path = LEGACY / "src/client/tactic_client_lib/tactic_server_stub.py"
        self.check_original_client(path, "original_tactic_client")

    def test_handler_client_runs_unchanged_against_new_server(self):
        handler = ROOT.parent.parent / "TH"
        path = handler / "thlib/side/client/tactic_client_lib/tactic_server_stub.py"
        if not path.is_file():
            self.skipTest("Sibling th_codex checkout is required for the real Handler client check")
        previous_path = sys.path.copy()
        try:
            sys.path.insert(0, str(handler))
            self.check_original_client(path, "original_handler_client")
        finally:
            # thlib.side also prepends its vendored dependencies on import.
            sys.path[:] = previous_path

    def test_handler_bootstrap_procedures_run_unchanged(self):
        handler = ROOT.parent.parent / 'TH'
        path = handler / 'thlib/tactic_query.py'
        if not path.is_file():
            self.skipTest('Sibling th_codex checkout required')
        spec = importlib.util.spec_from_file_location('handler_bootstrap_query', path)
        query = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(query)
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        milestone = client.insert('sthpw/milestone', {'code': 'HANDLER_MILESTONE',
            'description': 'Handler contract', 'due_date': '2026-10-20 12:00:00'})
        self.addCleanup(client.delete_sobject, milestone['__search_key__'])
        for name, arguments in (
                ('get_projects_and_logins', {'current_login': 'admin'}),
                ('query_search_types_extended', {'project_code': 'admin'}),
                ('query_search_types_extended', {'project_code': 'sthpw'}),
                ('query_sobjects', {'search_type': 'sthpw/milestone', 'project_code': 'admin',
                    'filters': [('project_code', 'admin')], 'order_bys': ['name', 'due_date', 'description'],
                    'include_snapshots': False, 'include_info': True, 'include_status_log': False}),
                ('query_sobjects', {'search_type': 'contract/snapshot_entity?project=admin', 'project_code': 'admin',
                    'filters': [('code', 'A')], 'limit': 10, 'compressed_return': False,
                    'get_all_snapshots': True}),
                ('query_sobjects', {'search_type': 'contract/snapshot_other?project=admin', 'project_code': 'admin',
                    'compressed_return': True, 'get_all_snapshots': True})):
            with self.subTest(procedure=name):
                code = query.prepare_serverside_script(getattr(query, name), arguments,
                                                      shrink=False, catch_traceback=False)
                code['_debug_args'] = False
                response = client.execute_python_script('', kwargs=code)
                self.assertEqual(response['status'], 'OK')
                payload = response['info']
                if payload.startswith('zlib:'):
                    import zlib
                    payload = zlib.decompress(bytes.fromhex(payload[5:])).decode('utf-8')
                data = json.loads(payload)
                if name == 'get_projects_and_logins':
                    self.assertIn('admin', [item['code'] for item in data['projects']])
                    self.assertIn('admin', [item['login'] for item in data['logins']])
                elif name == 'query_sobjects':
                    self.assertEqual(data['total_sobjects_count'], 1)
                    self.assertEqual(data['total_sobjects_query_count'], 1)
                    self.assertEqual(len(data['sobjects_list']), 1)
                    obj = data['sobjects_list'][0]
                    self.assertEqual(obj['__search_type__'], arguments['search_type'].split('?')[0])
                    if arguments['search_type'] == 'sthpw/milestone':
                        self.assertEqual(obj['code'], milestone['code'])
                        self.assertEqual(obj['project_code'], 'admin')
                        self.assertFalse(obj.get('__snapshots__'))
                        continue
                    self.assertTrue(obj['__snapshots__'])
                    if arguments['search_type'].startswith('contract/snapshot_entity?'):
                        files = [file for snapshot in obj['__snapshots__'] for file in snapshot['__files__']]
                        self.assertIn('scene.ma', [file['file_name'] for file in files])
                        self.assertTrue(all(file['__search_type__'] == 'sthpw/file' for file in files))
                    else:
                        self.assertEqual(obj['__snapshots__'][0]['code'], 'D1')
                else:
                    self.assertTrue(data['stypes'])
                    self.assertIn('task', [item['code'] for item in data['pipelines']])
                    if arguments['project_code'] == 'sthpw':
                        self.assertTrue(all('definition' in item for item in data['stypes']))

    def test_handler_task_workspace_page_runs_unchanged(self):
        path = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        if not path.is_file():
            self.skipTest('Sibling th_codex checkout required')
        spec = importlib.util.spec_from_file_location('handler_task_query', path)
        query = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(query)
        proxy = self.proxy()
        ticket = {'ticket': proxy.get_ticket('admin', 'private-test-password'), 'project': 'one'}
        prefix = 'WORKSPACE_CONTRACT_'
        # Owned transport fixture, never the user's server/database.
        with self.store.connection(write=True) as db:
            db.executemany('INSERT INTO task (code,project_code,search_type,search_code,process,context,status,assigned,bid_end_date) '
                           'VALUES (?,?,?,?,?,?,?,?,?)', [
                (prefix + 'A', 'one', 'contract/entity?project=one', 'A', 'review', 'review', 'pending', 'admin', '2026-10-08 12:00:00'),
                (prefix + 'B', 'one', 'contract/entity?project=one', 'B', 'publish', 'publish', 'pending', '', None),
                (prefix + 'C', 'one', 'contract/entity?project=one', 'A', 'review', 'review/extra', 'done', 'admin', '2026-10-09 12:00:00'),
                (prefix + 'OTHER', 'two', 'contract/entity?project=two', 'A', 'review', 'review', 'pending', 'admin', None),
            ])
            db.execute('INSERT INTO note (code,project_code,search_type,search_code,process,note) VALUES (?,?,?,?,?,?)',
                       (prefix + 'NOTE', 'one', 'contract/entity?project=one', 'A', 'review', 'Root note'))
        def cleanup():
            with self.store.connection(write=True) as db:
                db.execute('DELETE FROM task WHERE code LIKE ?', (prefix + '%',))
                db.execute('DELETE FROM note WHERE code=?', (prefix + 'NOTE',))
        self.addCleanup(cleanup)
        def page(**changes):
            arguments = dict(filters=[['project_code', 'one'], ['code', 'like', prefix + '%']], order_bys=['code'], project_code='one',
                             limit=2, offset=0, query=dict(today='2026-10-07', currentLogin='admin'))
            arguments.update(changes)
            script = query.prepare_serverside_script(query.query_task_workspace_page, arguments,
                                                    shrink=False, catch_traceback=False)
            script['_debug_args'] = False
            result = proxy.execute_python_script(ticket, '', script)
            self.assertEqual(result['status'], 'OK')
            return json.loads(result['info'])
        result = page()
        self.assertEqual(result['total'], 3)
        self.assertEqual([task['code'] for task in result['tasks']], [prefix + 'A', prefix + 'C'])
        self.assertEqual({parent['code'] for parent in result['parents']}, {'A'})
        self.assertEqual([task['__notes_count__'] for task in result['tasks']], [1, 0])
        self.assertEqual({item['key']: item['count'] for item in result['facets']['process']}, {'review': 2, 'publish': 1})
        self.assertEqual(result['facets']['preset']['review'], 2)
        native = proxy.execute_cmd(ticket, 'tactic.ui.table.task_workspace.TaskWorkspaceCmd',
            dict(scope='project', limit=2, query=dict(today='2026-10-07')))['info']
        for key in ('tasks', 'parents', 'total', 'facets', 'offset', 'limit'):
            if key == 'tasks':
                for task in native[key]:
                    self.assertIn('__process__', task)
                    self.assertIn('__hours__', task)
                    self.assertIn('__status__', task)
                value = [{name: value for name, value in task.items()
                          if name not in ('__process__', '__status__', '__hours__')} for task in native[key]]
            else:
                value = native[key]
            if key == 'parents':
                self.assertTrue(all('__preview__' in parent for parent in value))
                value = [{name: value for name, value in parent.items() if name != '__preview__'} for parent in value]
            self.assertEqual(value, result[key], key)
        self.assertTrue(native['hasMore'])
        self.assertEqual(native['loaded'], 2)
        with self.assertRaises(Fault):
            proxy.execute_cmd(ticket, 'tactic.ui.table.task_workspace.TaskWorkspaceCmd', dict(scope='project', limit=501))
        self.assertEqual([task['code'] for task in page(offset=2)['tasks']], [prefix + 'B'])
        for mode in ('recent', 'user', 'process', 'status', 'object', 'search_type', 'project', 'priority', 'milestone'):
            with self.subTest(sort=mode):
                data = page(query=dict(sort=mode, group='user', descending=True), limit=500)
                self.assertEqual({task['code'] for task in data['tasks']}, {prefix + name for name in 'ABC'})
        data = page(query={'filters': {'text': "O'Reilly"}}, limit=500)
        self.assertEqual([task['code'] for task in data['tasks']], [prefix + 'B'])
        data = page(query={'filters': {'hasNotes': True}}, limit=500)
        self.assertEqual([task['code'] for task in data['tasks']], [prefix + 'A'])
        data = page(query={'quickFilters': {'preset': ['review']}, 'sort': 'object'}, limit=500)
        self.assertEqual({task['code'] for task in data['tasks']}, {prefix + 'A', prefix + 'C'})

    def test_task_workspace_edits_through_xmlrpc(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        command = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
        def call(action, plans):
            return proxy.execute_cmd(auth, command, dict(action=action, plans=plans))['info']
        parent_key = 'contract/entity?project=one&code=A'
        catalog = proxy.execute_cmd(auth, 'tactic.ui.table.task_workspace.TaskWorkspaceCmd',
                                   dict(action='catalog', search_key=parent_key))['info']
        self.assertTrue(catalog['revision'])
        plan = call('prepare', [dict(operation='create', draft_id='xmlrpc-task', search_key=parent_key,
                                    process='publish', context='publish/xmlrpc')])['plans'][0]
        self.assertTrue(plan['statuses'])
        saved = call('save', [dict(plan, data=dict(status=plan['statuses'][0], assigned='admin', description='XML-RPC task'))])['tasks'][0]
        with self.assertRaises(Fault):
            call('save', [dict(plan, data=dict(description='Repeated create'))])
        request = dict(search_key=parent_key, process='publish', task_key=saved['task_key'])
        edit = call('prepare', [request])['plans'][0]
        self.assertEqual(edit['task']['context'], 'publish/xmlrpc')
        call('save', [dict(edit, data=dict(description='Updated through XML-RPC'))])
        edit = call('prepare', [request])['plans'][0]
        self.assertEqual(edit['task']['description'], 'Updated through XML-RPC')
        deletion = call('prepare', [dict(request, operation='delete')])['plans'][0]
        result = call('save', [dict(deletion, related_types=[])])['tasks']
        self.assertEqual(result[0]['operation'], 'delete')
        with self.assertRaises(Fault):
            call('prepare', [request])

    def _task_manager_fixture(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        for task in ast.literal_eval(proxy.query(auth, 'sthpw/task', [('project_code','one')])):
            if task['search_type'].split('?')[0] == 'contract/entity':
                proxy.delete_sobject(auth, task['__search_key__'])
        command = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
        plans = proxy.execute_cmd(auth, command, dict(action='prepare', plans=[
            dict(operation='create', draft_id='browser-'+code, search_key='contract/entity?project=one&code='+code, process='publish')
            for code in ('A', 'B')]))['info']['plans']
        proxy.execute_cmd(auth, command, dict(action='save', plans=[dict(plan,
            data=dict(assigned='admin', status=plan['statuses'][0], description='Browser task',
                      bid_start_date='2030-01-04 09:13:00' if index == 0 else '2030-01-07 08:00:00',
                      bid_end_date='2030-01-08 17:20:00' if index == 0 else '2030-01-09 16:45:00')) for index, plan in enumerate(plans)]))

    def test_task_manager_in_chromium(self):
        self._task_manager_fixture()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/task_manager.mjs'), self.url,
            str(ROOT / '.screenshots/task-manager-mobile.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task_manager_context_in_chromium(self):
        self._task_manager_fixture()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/task_manager_context.mjs'), self.url,
            str(ROOT / '.screenshots/task-manager-context.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _task_process_fixture(self, title=''):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        proxy.execute_cmd(auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                          dict(search_type_name='contract/quick_task', asset_title=title, sobject_pipeline=True, process=['model', 'review', 'auto', 'linked']))
        proxy.update(auth, 'sthpw/pipeline?code=one/quick_task', dict(pipeline='<pipeline><process name="model" label="Model" color="#ff5353"/><process name="review" label="Review" color="#25c2e8"/><process name="auto" type="action"/><process name="linked" type="progress"/></pipeline>'))
        parent = proxy.insert(auth, 'contract/quick_task', dict(code='QUICK_A', name='Asset B', pipeline_code='one/quick_task'))
        proxy.insert(auth, 'contract/quick_task', dict(code='QUICK_B', name='Another asset', pipeline_code='one/quick_task'))
        editor = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
        plan = proxy.execute_cmd(auth, editor, dict(action='prepare', plans=[dict(operation='create', draft_id='quick-primary', search_key=parent['__search_key__'], process='model')]))['info']['plans'][0]
        task = proxy.execute_cmd(auth, editor, dict(action='save', plans=[dict(plan, data=dict(status=plan['statuses'][0], assigned='admin'))]))['info']['tasks'][0]
        return proxy, auth, parent, task

    def test_task_process_workspace_through_xmlrpc(self):
        proxy, auth, parent, task = self._task_process_fixture()
        read = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd'
        editor = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
        result = proxy.execute_cmd(auth, read, dict(action='processes', search_key=parent['__search_key__']))['info']
        self.assertEqual([row['value'] for row in result['processes']], ['model', 'review'])
        model, review = result['processes']
        self.assertEqual(model['color'], '#ff5353')
        self.assertEqual(model['selected'], task['task_key'])
        branch = review['branches'][0]
        self.assertEqual(branch['plan']['operation'], 'create')
        self.assertEqual(branch['plan']['task']['status'], '')
        self.assertTrue(branch['statuses'])
        saved = proxy.execute_cmd(auth, editor, dict(action='save', plans=[dict(branch['plan'], data=dict(status=branch['statuses'][0]['value'], assigned='admin'))]))['info']['tasks'][0]
        with self.assertRaises(Fault):
            proxy.execute_cmd(auth, editor, dict(action='save', plans=[dict(branch['plan'], data=dict(assigned='admin'))]))
        with self.assertRaises(Fault):
            proxy.execute_cmd(dict(auth, project='two'), read, dict(action='processes', search_key=parent['__search_key__']))
        result = proxy.execute_cmd(auth, read, dict(action='processes', search_key=parent['__search_key__']))['info']
        self.assertEqual(result['processes'][1]['selected'], saved['task_key'])
        page = proxy.execute_cmd(auth, read, dict(scope='project'))['info']
        self.assertEqual(page['tasks'][0]['__process__']['color'], '#ff5353')
        self.assertEqual(page['tasks'][0]['__hours__']['entryCount'], 0)
        self.assertTrue(all(choice['label'] for choice in model['branches'][0]['plan']['statusChoices']))

    def test_task_process_panel_in_chromium(self):
        self._workspace_schema_fixture()
        self._task_process_fixture()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/task_process_panel.mjs'), self.url,
            str(ROOT / '.screenshots/task-process-cards.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_database_upgrade_adds_original_milestone(self):
        from pyasm.biz import Milestone
        from pyasm.search import SearchType
        from pyasm.search.search import RequestContext, request_context
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-test-password'))
            with store.connection(write=True) as db:
                db.execute('DROP TABLE milestone')
                db.execute("DELETE FROM search_object WHERE search_type='sthpw/milestone'")
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with request_context(RequestContext(store, 'admin', 'admin')):
                self.assertIsInstance(SearchType.create('sthpw/milestone'), Milestone)

    def test_base_dirs_work_with_unchanged_handler_consumer(self):
        from types import SimpleNamespace
        from pyasm.common.config import initialize_config
        initialize_config(self.store.data_dir)
        proxy = self.proxy()
        bases = proxy.get_base_dirs(self.ticket(proxy))
        self.assertEqual(bases['asset_base_dir'], (self.store.data_dir / 'assets').as_posix())
        self.assertEqual(bases['web_base_dir'], '/assets')
        path = ROOT.parent.parent / 'TH/thlib/environment.py'
        if not path.is_file():
            self.skipTest('Sibling th_codex checkout required')
        # Load only the original consumer class; no Qt or real Handler settings.
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Tactic')
        namespace = dict(env_mode=SimpleNamespace(node='private-test'),
                         env_server=SimpleNamespace(get_cur_srv_preset=lambda: 'private-test'),
                         env_read_config=lambda *args, **kwargs: None)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), namespace)
        consumer = namespace['Tactic']()
        consumer.get_default_base_dirs = lambda force=False: bases
        consumer.save_base_dirs = lambda: None
        paths = consumer.get_base_dirs()
        self.assertEqual(len(paths), 12)
        self.assertEqual(paths['asset_base_dir'][0], bases['asset_base_dir'])

    def test_original_client_undo_redo_and_transaction_replay(self):
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        client.set_ticket(client.get_ticket('admin', 'private-test-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        note = client.insert('sthpw/note', {'code': 'TRANSPORT_UNDO', 'note': 'before', 'process': 'publish'})
        self.assertTrue(client.undo())
        self.assertEqual(client.query('sthpw/note', [('code', 'TRANSPORT_UNDO')]), [])
        self.assertTrue(client.redo())
        self.assertEqual(client.query('sthpw/note', [('code', 'TRANSPORT_UNDO')], single=True)['note'], 'before')
        # Source APIs select an explicit journal by its id as well.
        client.update(note['__search_key__'], {'note': 'after'})
        with self.store.connection() as db:
            log_id = db.execute("SELECT id FROM transaction_log WHERE type='undo' AND namespace='admin' ORDER BY timestamp DESC, id DESC LIMIT 1").fetchone()['id']
        self.assertTrue(client.undo(transaction_id=log_id))
        self.assertEqual(client.get_by_search_key(note['__search_key__'])['note'], 'before')
        self.assertTrue(client.redo(transaction_id=log_id))
        self.assertEqual(client.get_by_search_key(note['__search_key__'])['note'], 'after')
        xml = '''<transaction><sobject search_type="sthpw/note" search_code="TRANSPORT_REPLAY" action="insert">
            <column name="note" to="first"/><column name="process" to="publish"/></sobject>
            <sobject search_type="sthpw/note" search_code="TRANSPORT_REPLAY" action="update">
            <column name="note" from="first" to="second"/></sobject></transaction>'''
        self.assertEqual(client.execute_transaction(xml), {'status': 'OK'})
        self.assertEqual(client.query('sthpw/note', [('code', 'TRANSPORT_REPLAY')], single=True)['note'], 'second')
        # A transferred journal is idempotent by its original code.
        row = dict(code='REMOTE_TRANSPORT_LOG', namespace='admin', login='admin', timestamp=datetime.now(timezone.utc).isoformat(),
                   transaction='<transaction><sobject search_type="sthpw/note" search_code="TRANSPORT_REPLAY" action="update"><column name="note" from="second" to="remote"/></sobject></transaction>')
        self.assertEqual(client.execute_transaction(row), {'status': 'OK'})
        self.assertEqual(client.execute_transaction(row), {'status': 'OK'})
        self.assertEqual(client.get_by_search_key('sthpw/note?code=TRANSPORT_REPLAY')['note'], 'remote')
        bad = '''<transaction><sobject search_type="sthpw/note" search_code="REPLAY_ROLLBACK" action="insert"><column name="note" to="temporary"/></sobject>
            <sobject search_type="sthpw/DOES_NOT_EXIST" search_code="missing" action="insert"/></transaction>'''
        with self.assertRaises(Fault):
            client.execute_transaction(bad)
        self.assertEqual(client.query('sthpw/note', [('code', 'REPLAY_ROLLBACK')]), [])
        for method, args in (('undo', ('unfinished-ticket',)), ('execute_transaction', ('<transaction><file type="create"/></transaction>', 'upload'))):
            with self.subTest(method=method), self.assertRaises(Fault):
                getattr(client, method)(*args)
        # Explicit journal replay retains the transport's administrator policy.
        password = 'private-reader-replay'
        with self.store.connection(write=True) as db:
            db.execute('INSERT INTO login (login, password) VALUES (?,?)', ('replay_reader', hash_password(password)))
        client.set_ticket(client.get_ticket('replay_reader', password))
        with self.assertRaises(Fault) as caught:
            client.execute_transaction(xml)
        self.assertEqual(caught.exception.faultCode, 403)

    def test_original_client_grouped_edits_and_file_abort(self):
        spec = importlib.util.spec_from_file_location('tactic_client_lib.original_grouped_client',
            LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        client = module.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('admin')
        login_ticket = client.get_ticket('admin', 'private-test-password')
        client.set_ticket(login_ticket)
        proxies = [client.server]
        self.addCleanup(lambda: [proxy.__exit__(None, None, None) for proxy in proxies])
        key = client.start('Twenty notes')
        proxies.append(client.server)
        notes = [client.insert('sthpw/note', {'code': 'GROUPED_%02d' % n, 'note': 'before' * 200}) for n in range(20)]
        for note in notes[:10]:
            client.update(note['__search_key__'], {'note': 'after'})
        with self.store.connection() as db:
            marker = self.store.get_db_resource().get_database_impl().get_parameter()
            data = db.execute('SELECT data FROM transaction_state WHERE ticket=' + marker, (key,)).fetchone()[0]
            from pyasm.common import Xml
            log_id = int(Xml(data).get_value('state/transaction'))
        self.assertTrue(client.finish('Twenty notes saved'))
        proxies.append(client.server)
        self.assertTrue(client.undo(transaction_id=log_id))
        self.assertEqual(client.query('sthpw/note', [('code', 'in', '|'.join(note['code'] for note in notes))]), [])
        self.assertTrue(client.redo(transaction_id=log_id))
        self.assertEqual(client.get_by_code('sthpw/note', notes[0]['code'])['note'], 'after')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'session.bin'
            source.write_bytes(b'grouped snapshot bytes')
            client.start('Aborted checkin')
            proxies.append(client.server)
            snapshot = client.simple_checkin('sthpw/project?code=admin', 'grouped_abort', str(source), mode='upload', create_icon=False)
            file = snapshot['__file_sobjects__'][0]
            checked_in = Path(file['checkin_dir']) / file['file_name']
            self.assertTrue(checked_in.is_file())
            self.assertTrue(client.abort())
            proxies.append(client.server)
            client.set_ticket(login_ticket)
            self.assertFalse(checked_in.exists())
            self.assertEqual(client.get_by_code('sthpw/snapshot', snapshot['code']), {})
            self.assertEqual(source.read_bytes(), b'grouped snapshot bytes')

    def test_script_fault_contains_source_line_and_persisted_traceback(self):
        proxy = self.proxy()
        ticket = self.ticket(proxy)
        ticket['project'] = 'admin'
        script = proxy.insert(ticket, 'config/custom_script', {'folder': 'contract', 'title': 'traceback',
            'language': 'python', 'script': "def broken():\n    raise ValueError('script failure')\nbroken()"})
        try:
            with self.assertRaises(Fault) as caught:
                proxy.execute_python_script(ticket, 'contract/traceback', {})
            trace = caught.exception.faultString
            self.assertIn('tactic://admin/contract/traceback", line 2, in broken', trace)
            self.assertIn("raise ValueError('script failure')", trace)
            self.assertNotIn('memory:', trace)
            with self.store.connection() as db:
                row = db.execute("SELECT stack_trace FROM exception_log WHERE message='script failure' ORDER BY id DESC").fetchone()
                self.assertIn('tactic://admin/contract/traceback', row['stack_trace'])
                self.assertIn('line 2, in broken', row['stack_trace'])
            with self.assertRaises(HTTPError) as caught:
                self.admin_rpc('execute_python_script', [ticket, 'contract/traceback', {}])
            payload = json.load(caught.exception)
            caught.exception.close()
            self.assertIn('line 2, in broken', payload['error'])
            with self.assertRaises(Fault) as caught:
                proxy.execute_python_script({'ticket': 'invalid', 'project': 'admin'}, 'contract/traceback', {})
            self.assertEqual(caught.exception.faultCode, 403)
            self.assertNotIn('tactic://', caught.exception.faultString)
        finally:
            proxy.delete_sobject(ticket, script['__search_key__'])

    def test_script_permission_fault_keeps_source_and_rollback_without_reauth(self):
        proxy = self.proxy()
        auth = self.ticket(proxy)
        auth['project'] = 'admin'
        source = "server.insert('sthpw/note', {'note': 'denied script rollback', 'process': 'test'})\nfrom pyasm.common.errors import SecurityException\nraise SecurityException('File-project records require the file-project command API')"
        with self.assertRaises(Fault) as caught:
            proxy.execute_python_script(auth, '', {'code': source})
        self.assertEqual(caught.exception.faultCode, 403)
        self.assertIn('tactic://admin/inline.py", line 3', caught.exception.faultString)
        self.assertIn('File-project records require the file-project command API', caught.exception.faultString)
        with self.assertRaises(HTTPError) as caught:
            self.admin_rpc('execute_python_script', [auth, '', {'code': source}])
        self.assertEqual(caught.exception.code, 403)
        payload = json.load(caught.exception)
        caught.exception.close()
        self.assertEqual(payload['error_code'], 'permission_denied')
        self.assertIn('tactic://admin/inline.py", line 3', payload['error'])
        self.assertEqual(json.loads(proxy.query(auth, 'sthpw/note', [['note', 'denied script rollback']])), [])
        proxy.insert(auth, 'sthpw/login', {'login': 'ungranted', 'password': hash_password('private-reader')})
        reader = {'ticket': proxy.get_ticket('ungranted', 'private-reader'), 'project': 'admin'}
        for call in (lambda: proxy.execute_python_script(reader, '', {'code': source}),
                     lambda: self.admin_rpc('execute_python_script', [reader, '', {'code': source}])):
            with self.assertRaises((Fault, HTTPError)) as caught:
                call()
            error = caught.exception
            if isinstance(error, HTTPError):
                payload = json.load(error)
                error.close()
                self.assertEqual(payload['error_code'], 'permission_denied')
                message = payload['error']
            else:
                message = error.faultString
            self.assertEqual(message, 'Permission denied')
        with self.assertRaises(HTTPError) as caught:
            self.admin_rpc('execute_python_script', [{'ticket': 'invalid', 'project': 'admin'}, '', {'code': source}])
        payload = json.load(caught.exception)
        caught.exception.close()
        self.assertEqual(payload['error_code'], 'authentication_failed')
        self.assertNotIn('tactic://', payload['error'])

    def check_original_client(self, path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        client = module.TacticServerStub(setup=False, protocol="xmlrpc")
        client.set_server(self.url)
        client.set_project("one")
        client.set_ticket(client.get_ticket("admin", "private-test-password"))
        self.addCleanup(client.server.__exit__, None, None, None)
        self.assertEqual(client.ping(), "OK")
        rows = client.query("contract/entity", [["code", "A"]])
        self.assertIsInstance(rows, list)
        self.assertEqual(rows[0]["__search_key__"], client.build_search_key("contract/entity", "A"))
        self.assertEqual(client.get_by_search_key(rows[0]["__search_key__"])["name"], "Первый")
        self.assertEqual(client.eval('6 * 7'), 42)
        self.assertEqual(client.eval('@GET(.name)', search_keys=[rows[0]['__search_key__']], single=True), 'Первый')
        self.assertEqual(client.eval('@SOBJECT()', search_keys=rows[0], single=True)['__search_type__'], 'contract/entity?project=one')
        self.assertEqual(client.get_column_info("contract/entity")["code"]["data_type"], "varchar")
        self.assertEqual(client.get_column_names("contract/entity"), ["id", "code", "name", "amount", "s_status"])
        self.assertIn("entity", client.get_table_info("contract/entity"))
        rows = client.query("contract/entity", ["begin", ["code", "A"], ["name", "contains", "Reilly"], "or"])
        self.assertEqual([row["code"] for row in rows], ["A", "B"])
        with self.store.connection("one") as db:
            expected_names = [{"name": row[0]} for row in db.execute("SELECT DISTINCT name FROM entity")]
        self.assertCountEqual(client.query("contract/entity", distinct="name"), expected_names)
        parent_key = client.build_search_key("contract/entity", "A")
        manual = client.create_task(parent_key, process='review', subcontext='sdk', assigned='admin')
        generated = client.add_initial_tasks(parent_key, start_date='2026-01-16')
        self.assertEqual([row['process'] for row in generated], ['publish'])
        self.assertEqual(client.add_initial_tasks(parent_key), [])
        for task in [manual, *generated]:
            client.delete_sobject(task['__search_key__'])
        message_key = name + '|status'
        self.assertEqual(client.log_message(message_key, {'ready': True}), 'OK')
        message = client.get_message(message_key)
        self.assertEqual(json.loads(message['message']), {'ready': True})
        client.delete_sobject(message['__search_key__'])
        client.set_project('admin')
        created_snapshot = client.create_snapshot('contract/snapshot_entity?project=admin&code=A',
                                                  context='sdk_create_' + name, is_current=True)
        revised_snapshot = client.create_snapshot('contract/snapshot_entity?project=admin&code=A',
                                                  context='sdk_create_' + name, is_revision=True)
        self.assertEqual((created_snapshot['version'], created_snapshot['revision']), (1, 0))
        self.assertEqual((revised_snapshot['version'], revised_snapshot['revision']), (1, 1))
        selected_snapshot = client.get_snapshot('contract/snapshot_entity?project=admin&code=A', context='sdk_create_' + name, revision=-1)
        self.assertEqual(selected_snapshot['code'], revised_snapshot['code'])
        client.delete_sobject(revised_snapshot['__search_key__'])
        client.delete_sobject(created_snapshot['__search_key__'])
        snapshot = client.get_snapshot('contract/snapshot_entity?project=admin&code=A', include_files=True)
        self.assertEqual(snapshot['code'], 'CA')
        self.assertEqual([row['code'] for row in snapshot['__files__']], ['FA'])
        self.assertEqual(client.get_snapshot('contract/snapshot_entity?project=admin&code=A', context='missing'), {})
        self.assertEqual(client.get_snapshot('contract/snapshot_entity?project=admin&code=A', context='empty', include_files=True)['__files__'], [])
        definition = client.insert('config/process', {'pipeline_code': 'sdk', 'process': name,
                                                      'workflow': '{"on_action":"return True"}'})
        updated = client.update(definition['__search_key__'], {'description': 'SDK process'})
        self.assertEqual(updated['description'], 'SDK process')
        evaluated = client.eval("@UPDATE(sobject,description,'Expression process')", search_keys=[definition['__search_key__']])
        self.assertEqual(evaluated[0]['description'], 'Expression process')
        self.assertEqual(client.get_by_search_key(definition['__search_key__'])['description'], 'Expression process')
        with self.assertRaises(Fault):
            client.eval("@UPDATE(sobject,description,'must roll back');@COLOR(color,invalid)", search_keys=[definition['__search_key__']])
        self.assertEqual(client.get_by_search_key(definition['__search_key__'])['description'], 'Expression process')
        self.assertEqual(client.get_by_search_key(definition['__search_key__'])['process'], name)
        client.delete_sobject(definition['__search_key__'])
        self.assertEqual(client.get_by_code('config/process', definition['code']), {})
        script = client.insert('config/custom_script', {'folder': 'sdk', 'title': name, 'language': 'python',
                               'script': "return {'value':value,'project':server.get_project(),'login':server.login}"})
        result = client.execute_python_script('sdk/' + name, {'value': 7})
        self.assertEqual(result, {'status': 'OK', 'description': 'Run PythonCmd with script path [sdk/' + name + ']',
                                  'info': {'value': 7, 'project': 'admin', 'login': 'admin'}})
        client.update(script['__search_key__'], {'script': "return {'value':server.eval('6 * 7'),'project':server.get_project(),'root':sobject.get_code()}"})
        self.assertEqual(client.eval('@python(sdk/' + name + ')', search_keys=[script['__search_key__']]),
                         {'value': 42, 'project': 'admin', 'root': script['code']})
        client.delete_sobject(script['__search_key__'])
        client.set_project('one')
        child_key = client.build_search_key("contract/child", "CH1")
        self.assertEqual(client.get_parent_type(child_key), "contract/entity")
        self.assertIn("contract/child", client.get_child_types(parent_key))
        self.assertIn("contract/child", client.get_related_types("contract/entity"))
        self.assertEqual(client.get_parent(child_key)["code"], "A")
        self.assertEqual([row["code"] for row in client.get_all_children(parent_key, "contract/child")], ["CH1", "CH2"])
        self.assertEqual([row["code"] for row in client.query("contract/child", parent_key=parent_key)], ["CH1", "CH2"])
        self.assertEqual(client.get_types_from_instance("contract/link"), ["contract/many", "contract/entity"])
        linked = client.query("contract/collection", parent_key=parent_key)
        # SearchLinks compares the original broken instance filter and this native join separately.
        self.assertEqual([row["code"] for row in linked], ["G1", "G1"])
        linked = client.query("contract/collection", parent_key=parent_key, show_retired=True)
        self.assertEqual([row["code"] for row in linked], ["G1", "G1", "G2"])
        joined = client.query("contract/entity", [["code", "A"]], order_bys=["entity_in_collection.collection.name desc"])
        self.assertEqual([row["code"] for row in joined], ["A", "A", "A"])
        client.set_project("two")
        self.assertEqual(client.query("contract/entity", [["code", "A"]], single=True)["name"], "Второй")
        self.assertEqual([row["code"] for row in client.query("contract/child", parent_key=client.build_search_key("contract/entity", "A"))], ["CH2", "CH4", "CH5"])
        with self.assertRaises(Fault) as caught:
            client.insert("contract/entity", {"code": "NO_WRITE"}, metadata={'unsupported': 'metadata'})
        self.assertEqual(caught.exception.faultCode, 501)

        # The unchanged SDK also exercises the first migrated write subset.
        client.set_project('admin')
        group_name = 'sdk_' + name
        group = client.insert('sthpw/login_group', {'login_group': group_name, 'name': 'SDK Group'})
        self.assertEqual(group['login_group'], group_name)
        self.assertIsNone(group['description'])
        group = client.update(group['__search_key__'], {'description': 'Updated through original SDK'})
        self.assertEqual(group['description'], 'Updated through original SDK')
        deleted = client.delete_sobject(group['__search_key__'])
        self.assertEqual(deleted['login_group'], group_name)
        self.assertEqual(client.query('sthpw/login_group', [['login_group', group_name]]), [])

    def test_authentication_and_unsupported_methods_return_xmlrpc_faults(self):
        proxy = self.proxy()
        with self.assertRaises(Fault) as caught:
            proxy.ping({"ticket": "secret-invalid-ticket", "project": "one"})
        self.assertEqual(caught.exception.faultCode, 403)
        self.assertNotIn("secret-invalid-ticket", caught.exception.faultString)
        with self.assertRaises(Fault) as caught:
            proxy.execute_python_script({}, "", {"code": "print('must not run')"})
        self.assertEqual(caught.exception.faultCode, 403)
        with self.assertRaises(Fault) as caught:
            proxy.__private_helper()
        self.assertEqual(caught.exception.faultCode, 501)

    def test_handler_bootstrap_distinguishes_session_project_and_access_faults(self):
        from types import SimpleNamespace
        sys.path.insert(0, str(ROOT.parent.parent / 'TH'))
        from thlib import tactic_query as tq
        from thlib.ui.debug_logging import DebugLogController
        from thlib.ui.controllers.connection import ConnectionMixin

        proxy = self.proxy()
        auth = self.ticket(proxy)
        script = tq.prepare_serverside_script(tq.get_projects_and_logins,
            {'current_login': 'admin'}, shrink=False, catch_traceback=False)
        result = proxy.execute_python_script(dict(auth, project='sthpw'), '', script)['info']
        if isinstance(result, dict) and 'spt_ret_val' in result:
            result = result['spt_ret_val']
        projects = json.loads(result)['projects']
        self.assertIn('one', [row['code'] for row in projects])
        expired = proxy.insert(auth, 'sthpw/ticket', {
            'ticket': 'handler-expired-test-ticket', 'login': 'admin',
            'expiry': '2000-01-01 00:00:00',
        })
        self.addCleanup(proxy.delete_sobject, auth, expired['__search_key__'])
        reader = proxy.insert(auth, 'sthpw/login', {
            'login': 'handler_auth_reader', 'password': hash_password('private-reader-password'),
        })
        self.addCleanup(proxy.delete_sobject, auth, reader['__search_key__'])
        reader_token = proxy.get_ticket('handler_auth_reader', 'private-reader-password')
        cases = [
            ('expired', dict(auth, ticket='handler-expired-test-ticket'), 'ticket_error'),
            ('invalid', dict(auth, ticket='secret-invalid-ticket'), 'ticket_error'),
            ('project', dict(auth, project='missing_auth_project'), 'no_project_error'),
            ('access', dict(auth, ticket=reader_token), 'permission_error'),
        ]
        for name, identity, expected in cases:
            with self.subTest(case=name):
                with self.assertRaises(Fault) as caught:
                    proxy.execute_python_script(identity, '', {'code': 'return "must not run"'})
                error = caught.exception
                self.assertEqual(error.faultCode, 403)
                self.assertNotIn(identity['ticket'], error.faultString)
                self.assertEqual(DebugLogController.classify_error(error), expected)
                states, requests, notices = [], [], []
                controller = SimpleNamespace(
                    _bootstrap_worker=object(), _bootstrap_request_id='current',
                    _bootstrap_started_at=time.perf_counter(),
                    project_model=SimpleNamespace(replace=lambda _rows: None),
                    navigation_model=SimpleNamespace(replace=lambda _rows: None),
                    workspace_model=SimpleNamespace(clear=lambda: None),
                    debug_log=SimpleNamespace(raise_error=lambda *_args, **_kwargs: None,
                                             classify_error=DebugLogController.classify_error),
                    _set_server_state=lambda state, _message: states.append(state),
                    _set_loading=lambda *_args: None,
                    _transaction_metrics=lambda *_args: '0 ms',
                    _request_authentication=lambda: requests.append('login'),
                    notification_changed=SimpleNamespace(emit=notices.append),
                )
                ConnectionMixin._bootstrap_failed(controller, error)
                self.assertEqual(requests, ['login'] if expected == 'ticket_error' else [])
                self.assertEqual(states, ['authentication' if requests else 'error'])
        with self.assertRaises(Fault) as caught:
            proxy.get_ticket('admin', 'private-wrong-password')
        self.assertEqual(DebugLogController.classify_error(caught.exception), 'login_pass_error')

    def test_malformed_and_entity_xml_rejected_including_utf16(self):
        dtd = '<!DOCTYPE methodCall [<!ENTITY payload "expanded">]><methodCall><methodName>fast_ping</methodName></methodCall>'
        for body in (b"<broken", dtd.encode(), ('<?xml version="1.0" encoding="UTF-16"?>' + dtd).encode("utf-16")):
            request = Request(self.url + "/tactic/default/Api/", body, headers={"Content-Type": "text/xml"})
            with urlopen(request) as response:
                with self.assertRaises(Fault) as caught:
                    loads(response.read())
                self.assertEqual(caught.exception.faultCode, 400)

    def test_request_body_is_bounded(self):
        request = Request(self.url + "/tactic/default/Api/", b" " * (MAX_BODY + 1), headers={"Content-Type": "text/xml"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 413)
        caught.exception.close()

    def admin_rpc(self, method, args=None, kwargs=None):
        body = json.dumps({"method": method, "args": args or [], "kwargs": kwargs or {}}).encode()
        request = Request(self.url + '/admin/rpc', body, headers={'Content-Type': 'application/json'})
        with urlopen(request) as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return json.load(response)['result']

    def test_session_identity_uses_current_account_without_credentials(self):
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        def identity(ticket, **values):
            body = json.dumps(dict(ticket=ticket, **values)).encode()
            request = Request(self.url + '/admin/session/identity', data=body, headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                return json.load(response)['result']
        result = identity(token)
        self.assertEqual(result['login'], 'admin')
        self.assertEqual(result['initials'], 'A')
        self.assertRegex(result['avatarColor'], r'^#[0-9a-f]{6}$')
        self.assertEqual(set(result), {'login', 'displayName', 'retired', 'initials', 'avatarColor', 'avatarUrl', 'administration'})
        self.assertTrue(result['administration'])
        self.assertNotIn('private-test-password', json.dumps(result))
        proxy = self.proxy()
        admin = dict(ticket=token, project='admin', language='python')
        account = proxy.insert(admin, 'sthpw/login', dict(login='identity_reader', password=hash_password('identity-test-password')))
        self.addCleanup(proxy.delete_sobject, admin, account['__search_key__'])
        reader = identity(proxy.get_ticket('identity_reader', 'identity-test-password'))
        self.assertEqual(reader['login'], 'identity_reader')
        self.assertFalse(reader['administration'])
        self.assertEqual(set(reader), set(result))
        for ticket, values, status in [('invalid', {}, 403), (token, {'login': 'someone_else'}, 400)]:
            with self.subTest(status=status), self.assertRaises(HTTPError) as caught:
                identity(ticket, **values)
            self.assertEqual(caught.exception.code, status)
            caught.exception.close()

    def test_admin_json_reads_share_auth_and_original_api(self):
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        ticket = {'ticket': token, 'project': 'one', 'language': 'python'}
        before = self.store.database_path('one').read_bytes()
        rows = self.admin_rpc('query', [ticket, 'contract/entity'], {'filters': [['code', 'A']]})
        self.assertEqual(rows[0]['name'], 'Первый')
        self.assertEqual(rows[0]['amount'], 0)
        ticket['project'] = 'two'
        self.assertEqual(self.admin_rpc('query', [ticket, 'contract/entity'], {'filters': [['code', 'A']]})[0]['name'], 'Второй')
        self.assertEqual(self.store.database_path('one').read_bytes(), before)
        for method, args, status in (
            ('query', [{'ticket': 'invalid'}, 'contract/entity'], 403),
            ('query', [ticket, 'sthpw/transaction_log'], 501),
            ('query', [ticket, 'sthpw/sobject_log'], 501),
            ('insert', [ticket, 'contract/entity', {'code': 'NO_WRITE'}, {'unsupported': 'metadata'}], 501),
            ('__private_helper', [], 501),
        ):
            with self.subTest(method=method), self.assertRaises(HTTPError) as caught:
                self.admin_rpc(method, args)
            self.assertEqual(caught.exception.code, status)
            payload = json.load(caught.exception)
            self.assertNotIn('invalid', payload['error'])
            caught.exception.close()

    def test_concurrent_json_and_xmlrpc_keep_their_original_envelopes(self):
        from concurrent.futures import ThreadPoolExecutor
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        ticket = {'ticket': token, 'project': 'one'}
        options = {'filters': [['code', 'A']], 'columns': ['code', 'name', 'amount'], 'single': True}
        def read(index):
            if index % 2:
                return self.admin_rpc('query', [ticket, 'contract/entity'], options)
            with self.proxy() as proxy:
                value = proxy.query(ticket, 'contract/entity', [['code', 'A']], ['code', 'name', 'amount'],
                                    [], False, None, None, True)
            self.assertIsInstance(value, str)
            return ast.literal_eval(value)
        with ThreadPoolExecutor(max_workers=4) as executor:
            values = list(executor.map(read, range(16)))
        self.assertTrue(all(value == values[0] for value in values))
        self.assertEqual(values[0]['name'], 'Первый')
        self.assertEqual(values[0]['amount'], 0)
        self.assertEqual(self.admin_rpc('query', [ticket, 'contract/entity'],
                                       {'filters': [['code', 'absent']], 'single': True}), {})
        from pyasm.common import Config
        original = Config.get_value
        def configured(module, key, *args, **kwargs):
            return 'true' if (module, key) == ('security', 'enable_fast_query') else original(module, key, *args, **kwargs)
        with patch.object(Config, 'get_value', side_effect=configured):
            fast = self.admin_rpc('fast_query', [ticket, 'contract/entity'], {'filters': [['code', 'A']], 'limit': 1})
        # JSON only unwraps the public query method; aliases retain their
        # existing envelope even when they call query internally.
        self.assertIsInstance(fast, str)
        self.assertEqual(ast.literal_eval(fast)[0]['name'], 'Первый')

    def test_admin_json_input_and_origin_are_bounded(self):
        before = self.store.database_path('sthpw').read_bytes()
        for body, content_type, origin, expected in (
            (b'{broken', 'application/json', None, 400),
            (b'[]', 'application/json', None, 400),
            (b'{"method":"get_ticket","args":["admin","password"],"kwargs":{"extra":1}}', 'application/json', None, 400),
            (b'{"method":"query","args":{},"kwargs":{}}', 'application/json', None, 400),
            (b'{"method":"fast_ping","args":[NaN]}', 'application/json', None, 400),
            (b'{}', 'text/plain', None, 415),
            (b'{"method":"fast_ping","args":[null]}', 'application/json', 'https://outside.invalid', 403),
            (b' ' * (MAX_BODY + 1), 'application/json', None, 413),
        ):
            headers = {'Content-Type': content_type}
            if origin: headers['Origin'] = origin
            with self.subTest(expected=expected), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.url + '/admin/rpc', body, headers=headers))
            self.assertEqual(caught.exception.code, expected)
            caught.exception.close()
        self.assertEqual(self.store.database_path('sthpw').read_bytes(), before)

    def test_admin_assets_are_packaged_and_paths_are_closed(self):
        with urlopen(self.url + '/') as response:
            html = response.read().decode()
            self.assertIn('<title>TACTIC Stream</title>', html)
            self.assertIn('lang="en"', html)
            self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        import re
        assets = re.findall(r'(?:src|href)="(/ui/assets/[^\"]+)"', html)
        self.assertTrue(assets)
        for asset in assets:
            with urlopen(self.url + asset) as response:
                content = response.read()
                self.assertTrue(content)
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                if asset.endswith(('.js', '.css')):
                    self.assertEqual(response.headers['Cache-Control'], 'public, no-cache')
                    self.assertTrue(response.headers['ETag'])
            if asset.endswith('.css'):
                fonts = re.findall(r'url\(([^)]+\.ttf)\)', content.decode())
                self.assertEqual(len(fonts), 4)  # Fluent regular/filled share the resizable font.
                for font in fonts:
                    with urlopen(urljoin(self.url + asset, font.strip('"\''))) as response:
                        self.assertEqual(response.headers['Content-Type'], 'font/ttf')
                        self.assertTrue(response.read())
        with urlopen(self.url + '/ui/licenses/icon-fonts/FONT_AWESOME_LICENSE.txt') as response:
            self.assertIn(b'Font Awesome', response.read())
        for name in ('chat_bg_dark.png', 'chat_bg_light.png'):
            with urlopen(self.url + '/ui/assets/' + name) as response:
                self.assertEqual(response.headers['Content-Type'], 'image/png')
                self.assertTrue(response.read().startswith(b'\x89PNG\r\n\x1a\n'))
        for name in ('UNICODE_EMOJI_LICENSE.txt', 'NOTO_EMOJI_LICENSE.txt'):
            with urlopen(self.url + '/ui/licenses/icon-fonts/' + name) as response:
                self.assertTrue(response.read())
        for path in ('/ui/assets/%2e%2e/index.html', '/ui/assets/none.js', '/ui/../storage.py', '/ui/assets/anything.txt'):
            with self.assertRaises(HTTPError) as caught:
                urlopen(self.url + path)
            self.assertEqual(caught.exception.code, 404)
            caught.exception.close()

    def test_ui_javascript_cache_revalidates_changed_files_and_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / 'web' / 'assets'
            assets.mkdir(parents=True)
            with patch('tactic_stream.server.app.files', return_value=root):
                for name, content_type in [('Example.js','text/javascript'),('Example.js.map','application/json')]:
                    with self.subTest(name=name):
                        resource = assets / name
                        resource.write_bytes(b'first build')
                        address = self.url + '/ui/assets/' + name
                        with urlopen(address) as response:
                            self.assertEqual(response.read(), b'first build')
                            self.assertTrue(response.headers['Content-Type'].startswith(content_type))
                            self.assertEqual(response.headers['Cache-Control'], 'public, no-cache')
                            etag = response.headers['ETag']
                        for header in (etag, 'W/' + etag, '"different", ' + etag, '*'):
                            with self.assertRaises(HTTPError) as caught:
                                urlopen(Request(address, headers={'If-None-Match':header}))
                            self.assertEqual(caught.exception.code,304)
                            self.assertEqual(caught.exception.read(),b'')
                            caught.exception.close()
                        resource.write_bytes(b'next build')
                        with urlopen(Request(address, headers={'If-None-Match':etag})) as response:
                            self.assertEqual(response.status,200)
                            self.assertEqual(response.read(),b'next build')
                            self.assertNotEqual(response.headers['ETag'],etag)

    def test_ui_assets_compress_without_stale_cache_or_api_compression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / 'web' / 'assets'
            assets.mkdir(parents=True)
            content = b'export const example = "public interface";\n' * 200
            resource = assets / 'Example.js'
            resource.write_bytes(content)
            address = self.url + '/ui/assets/Example.js'
            with patch('tactic_stream.server.app.files', return_value=root):
                with urlopen(address) as response:
                    self.assertEqual(response.read(), content)
                    plain_etag = response.headers['ETag']
                for name in ('Example.css', 'Example.js.map', 'Example.ttf'):
                    (assets / name).write_bytes(content)
                    with self.subTest(asset=name):
                        with urlopen(Request(self.url + '/ui/assets/' + name, headers={'Accept-Encoding': 'gzip'})) as response:
                            self.assertEqual(gzip.decompress(response.read()), content)
                            self.assertEqual(response.headers['Content-Encoding'], 'gzip')
                (assets / 'Small.js').write_bytes(b'export const small = true;')
                with urlopen(Request(self.url + '/ui/assets/Small.js', headers={'Accept-Encoding': 'gzip'})) as response:
                    self.assertEqual(response.read(), b'export const small = true;')
                    self.assertIsNone(response.headers.get('Content-Encoding'))
                for encoding in ('gzip', 'br, gzip;q=0.8', '*', 'GZIP'):
                    with self.subTest(encoding=encoding):
                        with urlopen(Request(address, headers={'Accept-Encoding': encoding})) as response:
                            compressed = response.read()
                            self.assertEqual(response.headers['Content-Encoding'], 'gzip')
                            self.assertEqual(response.headers['Vary'], 'Accept-Encoding')
                            self.assertEqual(gzip.decompress(compressed), content)
                            self.assertLess(len(compressed), len(content) / 2)
                            self.assertEqual(int(response.headers['Content-Length']), len(compressed))
                            gzip_etag = response.headers['ETag']
                            self.assertNotEqual(gzip_etag, plain_etag)
                for encoding in ('identity', 'br', 'gzip;q=0', '*;q=1, gzip;q=0', 'gzip;q=invalid'):
                    with self.subTest(encoding=encoding):
                        with urlopen(Request(address, headers={'Accept-Encoding': encoding})) as response:
                            self.assertEqual(response.read(), content)
                            self.assertIsNone(response.headers.get('Content-Encoding'))
                            self.assertEqual(response.headers['ETag'], plain_etag)
                            self.assertEqual(response.headers['Vary'], 'Accept-Encoding')
                headers = {'Accept-Encoding': 'gzip', 'If-None-Match': gzip_etag}
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(address, headers=headers))
                with caught.exception as response:
                    self.assertEqual(response.code, 304)
                    self.assertEqual(response.read(), b'')
                    self.assertEqual(response.headers['Vary'], 'Accept-Encoding')
                with urlopen(Request(address, headers={'Accept-Encoding': 'gzip', 'If-None-Match': plain_etag})) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(gzip.decompress(response.read()), content)
                resource.write_bytes(content.replace(b'public', b'updated'))
                with urlopen(Request(address, headers=headers)) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(gzip.decompress(response.read()), resource.read_bytes())
                    self.assertNotEqual(response.headers['ETag'], gzip_etag)
            with urlopen(Request(self.url + '/health', headers={'Accept-Encoding': 'gzip'})) as response:
                self.assertIsNone(response.headers.get('Content-Encoding'))
                self.assertIn('database_initialized', json.load(response))

    def test_configuration_is_admin_only_read_only_and_masks_secrets(self):
        proxy = self.proxy()
        token = proxy.get_ticket('admin', 'private-test-password', None)
        with self.store.connection(write=True) as db:
            db.execute('INSERT INTO login (login,password) VALUES (?,?)', ('configuration_reader', hash_password('reader-password')))
        reader = proxy.get_ticket('configuration_reader', 'reader-password', None)
        def request(ticket, origin=None, changes=None, revision=None):
            headers = {'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            payload = {'ticket': ticket}
            if changes is not None:
                payload.update(changes=changes, revision=revision)
            return urlopen(Request(self.url + '/admin/configuration' + ('/save' if changes is not None else ''),
                data=json.dumps(payload).encode(), headers=headers))
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'tactic-conf.xml'
            secret = 'private-configuration-secret'
            text = '<config version="2"><services><enable>tactic|queue</enable></services><database><vendor>Sqlite</vendor><password>' + secret + '</password><password_file>/private/secret-file</password_file></database><other><credential>' + secret + '</credential></other></config>'
            config.write_text(text, encoding='utf8')
            with patch.dict(os.environ, TACTIC_CONFIG_PATH=str(config), TACTIC_PORTS='9091|9092'):
                for ticket, expected_code in ((None, 'authentication_failed'), ('invalid', 'authentication_failed'), (reader, 'access_denied')):
                    with self.assertRaises(HTTPError) as caught:
                        request(ticket)
                    with caught.exception as response:
                        self.assertEqual(response.code, 403)
                        self.assertEqual(json.load(response)['error_code'], expected_code)
                with request(token) as response:
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    body = response.read().decode()
                self.assertNotIn(secret, body)
                self.assertNotIn('/private/secret-file', body)
                result = json.loads(body)['result']
                with self.assertRaises(HTTPError) as caught:
                    request(reader, changes={'services/thread_count': '8'}, revision=result['revision'])
                with caught.exception as response:
                    self.assertEqual(response.code, 403)
                    self.assertEqual(json.load(response)['error_code'], 'access_denied')
                settings = {entry['path']: entry for group in result['groups'] for entry in group['settings']}
                self.assertIsNone(settings['schedule/mode']['default'])
                self.assertTrue(settings['schedule/mode']['editable'])
                self.assertFalse(settings['schedule/mode']['restart'])
                self.assertEqual(settings['services/enable']['services'], [{'name': 'tactic', 'enabled': True}, {'name': 'queue', 'enabled': True}, {'name': 'files', 'enabled': False}])
                self.assertEqual(settings['services/ports']['environment_override'], '9091|9092')
                self.assertTrue(settings['database/password']['configured'])
                self.assertIsNone(settings['database/password']['value'])
                self.assertIn('other/credential', result['undocumented'])
                self.assertEqual(config.read_text(encoding='utf8'), text)
                with self.assertRaises(HTTPError) as caught:
                    request(token, 'https://another.example')
                self.assertEqual(caught.exception.code, 403)
                caught.exception.close()
                text = '<config><services enable="tactic" process_count="2"/><database vendor="Sqlite"/></config>'
                config.write_text(text, encoding='utf8')
                with request(token) as response:
                    result = json.load(response)['result']
                settings = {entry['path']: entry for group in result['groups'] for entry in group['settings']}
                self.assertEqual(settings['services/process_count']['value'], '2')
                self.assertFalse(settings['services/enable']['services'][1]['enabled'])
                self.assertEqual(config.read_text(encoding='utf8'), text)

    def test_configuration_edits_validate_preserve_xml_and_refuse_stale_writes(self):
        from concurrent.futures import ThreadPoolExecutor
        from tactic_stream.server.startup import read_server_config
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        def request(payload, save=False):
            with urlopen(Request(self.url + '/admin/configuration' + ('/save' if save else ''),
                data=json.dumps(dict(ticket=token, **payload)).encode(), headers={'Content-Type': 'application/json'})) as response:
                return json.load(response)['result']
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'tactic-conf.xml'
            text = '<config version="2"><!-- keep comment --><services><enable>tactic</enable><process_count>3</process_count></services><database><vendor>Sqlite</vendor><password>keep-secret</password></database><other><keep>original</keep></other></config>'
            config.write_text(text, encoding='utf8')
            with patch.dict(os.environ, TACTIC_CONFIG_PATH=str(config), TACTIC_PORTS=''):
                loaded = request({})
                for changes in ({'services/process_count': '0'}, {'services/thread_count': '2.5'}, {'services/worker_timeout': 'nan'},
                                {'services/enable': 'queue'}, {'database/password': 'replace-secret'}):
                    with self.assertRaises(HTTPError) as caught:
                        request(dict(changes=changes, revision=loaded['revision']), save=True)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()
                    self.assertEqual(config.read_text(encoding='utf8'), text)
                saved = request(dict(changes={'services/process_count': '2', 'services/enable': 'tactic|queue'}, revision=loaded['revision']), save=True)
                self.assertTrue(saved['restart_required'])
                self.assertNotEqual(saved['revision'], loaded['revision'])
                self.assertEqual(config.with_name(config.name + '.previous').read_text(encoding='utf8'), text)
                changed = config.read_text(encoding='utf8')
                self.assertIn('keep comment', changed)
                self.assertIn('keep-secret', changed)
                self.assertIn('<keep>original</keep>', changed)
                self.assertEqual(read_server_config(self.store.data_dir)['process_count'], 2)
                self.assertTrue(read_server_config(self.store.data_dir)['queue_enabled'])
                with self.assertRaises(HTTPError) as caught:
                    request(dict(changes={'services/thread_count': '8'}, revision=loaded['revision']), save=True)
                self.assertEqual(caught.exception.code, 409)
                caught.exception.close()
                self.assertEqual(config.read_text(encoding='utf8'), changed)
                def race(value):
                    try:
                        request(dict(changes={'services/thread_count': value}, revision=saved['revision']), save=True)
                        return 200
                    except HTTPError as error:
                        with error:
                            return error.code
                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(sorted(pool.map(race, ['11', '12'])), [200, 409])
                latest = request({})
                before = config.read_bytes()
                with patch('pyasm.common.config.os.replace', side_effect=OSError('test disk failure')), self.assertLogs('tactic_stream.server.app', level='ERROR'):
                    with self.assertRaises(HTTPError) as caught:
                        request(dict(changes={'services/thread_count': '13'}, revision=latest['revision']), save=True)
                    self.assertEqual(caught.exception.code, 503)
                    caught.exception.close()
                self.assertEqual(config.read_bytes(), before)
                v1 = '<config><!-- legacy format --><services enable="tactic" process_count="3"/><database vendor="Sqlite"/><other secret="retain"/></config>'
                config.write_text(v1, encoding='utf8')
                loaded = request({})
                request(dict(changes={'services/process_count': '4'}, revision=loaded['revision']), save=True)
                self.assertEqual(read_server_config(self.store.data_dir)['process_count'], 4)
                self.assertIn('legacy format', config.read_text(encoding='utf8'))
                self.assertIn('secret="retain"', config.read_text(encoding='utf8'))
                with patch.dict(os.environ, TACTIC_PORTS='9081|9082'):
                    loaded = request({})
                    entries = {entry['path']: entry for group in loaded['groups'] for entry in group['settings']}
                    self.assertFalse(entries['services/process_count']['editable'])
                    with self.assertRaises(HTTPError) as caught:
                        request(dict(changes={'services/process_count': '5'}, revision=loaded['revision']), save=True)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()

    def test_configuration_supported_settings_paths_and_startup(self):
        from tactic_stream.server.startup import read_server_config
        token = self.admin_rpc('get_ticket', ['admin', 'private-test-password'])
        def request(changes=None, revision=None):
            payload = {'ticket': token}
            if changes is not None:
                payload.update(changes=changes, revision=revision)
            with urlopen(Request(self.url + '/admin/configuration' + ('/save' if changes is not None else ''),
                    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
                return json.load(response)['result']
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'tactic-conf.xml'
            original = '<config version="2"><!-- untouched --><services><enable>tactic</enable></services><checkin><repository_display>{"default": {"title": "Studio", "color": [10,20,30]}}</repository_display></checkin><other><script>return "\\n"</script></other></config>'
            config.write_text(original, encoding='utf8')
            with patch.dict(os.environ, TACTIC_CONFIG_PATH=str(config), TACTIC_PORTS='', TACTIC_TMP_CONFIG_PATH=''):
                loaded = request()
                self.assertEqual(loaded['config_path'], config.as_posix())
                self.assertNotIn('\\', loaded['data_dir'])
                fields = {entry['path']:entry for group in loaded['groups'] for entry in group['settings']}
                self.assertEqual(json.loads(fields['checkin/repository_display']['value']), {'default':{'title':'Studio','color':[10,20,30]}}, 'Native repository metadata remains available without rewriting the XML')
                for changes, field in (
                        ({'install/hostname': 'http://localhost:8081'}, 'install/hostname'),
                        ({'services/start_port': '65536'}, 'services/start_port'),
                        ({'services/ports': '9081|9081'}, 'services/ports'),
                        ({'security/ticket_expiry': '-1 hour'}, 'security/ticket_expiry'),
                        ({'security/api_require_password': 'anything'}, 'security/api_require_password'),
                        ({'checkin/version_padding': '100000'}, 'checkin/version_padding'),
                        ({'checkin/web_base_dir': '/admin/assets'}, 'checkin/web_base_dir'),
                        ({'checkin/web_base_dir': 'javascript:alert(1)'}, 'checkin/web_base_dir'),
                        ({'checkin/web_base_dir': '{"missing":"/media"}'}, 'checkin/web_base_dir'),
                        ({'checkin/win32_sandbox_dir': '{"default":false}'}, 'checkin/win32_sandbox_dir')):
                    with self.subTest(field=field), self.assertRaises(HTTPError) as caught:
                        request(changes, loaded['revision'])
                    with caught.exception as response:
                        self.assertEqual(response.code, 400)
                        self.assertEqual(json.load(response)['error_field'], field)
                    self.assertEqual(config.read_text(encoding='utf8'), original)
                changes = {'install/hostname': '127.0.0.2', 'services/start_port': '9012',
                           'install/tmp_dir': r'scratch\logs', 'security/ticket_expiry': '20 minute',
                           'security/inactive_ticket_expiry': '5 minute', 'security/api_password': 'hidden-secret',
                           'security/api_require_password': 'true', 'security/api_method_restricted': 'false',
                           'checkin/version_padding': '4', 'schedule/mode': 'even_day',
                           'checkin/web_base_dir': '/media', 'checkin/win32_client_handoff_dir': r'\\fileserver\share\handoff',
                           'checkin/win32_sandbox_dir': json.dumps({'default': r'X:\work', 'other': r'\\fileserver\share'})}
                saved = request(changes, loaded['revision'])
                self.assertTrue(saved['saved'])
                self.assertTrue(saved['restart_required'])
                entries = {entry['path']: entry for group in saved['groups'] for entry in group['settings']}
                self.assertIsNone(entries['security/api_password']['value'])
                self.assertNotIn('hidden-secret', json.dumps(saved))
                self.assertEqual(entries['checkin/win32_client_handoff_dir']['value'], '//fileserver/share/handoff')
                self.assertEqual(json.loads(entries['checkin/win32_sandbox_dir']['value']), {'default': 'X:/work', 'other': '//fileserver/share'})
                settings = read_server_config(self.store.data_dir)
                self.assertEqual((settings['host'], settings['port']), ('127.0.0.2', 9012))
                self.assertEqual(settings['config_path'], config.as_posix())
                for field in ('data_dir', 'log_dir'):
                    self.assertNotIn('\\', settings[field])
                self.assertTrue(settings['log_dir'].endswith('/scratch/logs/log'))
                bases = self.proxy().get_base_dirs({'ticket': token, 'project': 'admin'})
                self.assertEqual(bases['win32_client_handoff_dir'], '//fileserver/share/handoff')
                self.assertEqual(bases['win32_sandbox_dir'], {'default': 'X:/work', 'other': '//fileserver/share'})
                text = config.read_text(encoding='utf8')
                self.assertIn('untouched', text)
                self.assertIn('return "\\n"', text)
                self.assertEqual(config.with_name(config.name + '.previous').read_text(encoding='utf8'), original)
                hot = request({'schedule/mode': 'even', 'security/api_password': ''}, saved['revision'])
                self.assertTrue(hot['saved'])
                self.assertFalse(hot['restart_required'])
                self.assertFalse(next(entry for group in hot['groups'] for entry in group['settings'] if entry['path'] == 'security/api_password')['configured'])
                ports = request({'services/ports': '9021|9022'}, hot['revision'])
                self.assertEqual(read_server_config(self.store.data_dir)['ports'], [9021, 9022])
                entries = {entry['path']: entry for group in ports['groups'] for entry in group['settings']}
                self.assertFalse(entries['services/start_port']['editable'])
                cleared = request({'services/ports': '', 'services/process_count': '1', 'services/start_port': '9031'}, ports['revision'])
                self.assertTrue(cleared['saved'])
                self.assertEqual(read_server_config(self.store.data_dir)['port'], 9031)

    def test_repository_aliases_do_not_shadow_application_routes(self):
        from pyasm.common import Config, Environment
        from starlette.routing import Mount
        with patch.object(Environment, 'get_asset_dirs', return_value={'other': str(self.store.data_dir / 'other-assets')}):
            with patch.object(Config, 'get_dict_value', return_value={'other': '/repository'}):
                app = create_app(self.store.data_dir)
                mount = next(route for route in app.routes if isinstance(route, Mount))
                self.assertEqual(mount.path, '/repository')
                self.assertEqual(mount.app.directory, str(self.store.data_dir / 'other-assets'))
                self.assertFalse(mount.app.follow_symlink)
            for address in ('/', '/admin/files', '/projects/files', '/ui/files', '/tactic/files', '/api/files', '/health', '/test', '/docs', '/redoc', '/openapi.json', '/assets/../files', 'assets'):
                with self.subTest(address=address), patch.object(Config, 'get_dict_value', return_value={'default': address}):
                    with self.assertRaises(ValueError):
                        create_app(self.store.data_dir)
            with patch.object(Config, 'get_dict_value', return_value={'missing': '/repository'}):
                with self.assertRaises(ValueError):
                    create_app(self.store.data_dir)
            with patch.object(Config, 'get_dict_value', return_value={'default': 'https://repository.example/assets'}):
                self.assertFalse(any(isinstance(route, Mount) for route in create_app(self.store.data_dir).routes))

    def test_api_documentation_and_console(self):
        from tactic_stream.server.api import Api, SUPPORTED_METHODS
        import inspect
        with urlopen(self.url + '/api/documentation') as response:
            catalog = json.load(response)
        methods = {item['name']: item for item in catalog['methods']}
        self.assertEqual(len(methods), 129)
        self.assertEqual({name for name, item in methods.items() if item['status'] == 'available'}, SUPPORTED_METHODS)
        self.assertEqual(methods['query']['signature'], str(inspect.signature(Api.query)).replace('(self, ', '(', 1))
        self.assertIn('@return:', methods['query']['reference'])
        self.assertEqual(methods['commit_session']['status'], 'excluded')
        self.assertTrue(methods['eval']['writes'])
        self.assertTrue(methods['get_preallocated_path']['writes'])
        self.assertFalse(methods['fast_ping']['requires_ticket'])
        api = Api(self.store)
        ticket = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='admin')
        translations = json.loads((ROOT / 'frontend/src/locales/ru.json').read_text(encoding='utf-8'))
        for name, method in methods.items():
            self.assertEqual(set(method['help']), {'en', 'ru'})
            self.assertTrue(method['help']['en'].strip(), name)
            self.assertRegex(method['help']['ru'], '[А-Яа-я]', name)
            for example in method['examples']:
                self.assertIn(example['label'], translations)
                self.assertIn(example['description'], translations)
                if not method['writes']:
                    args = [ticket if method['requires_ticket'] else None] if any(item['name'] == 'ticket' for item in method['parameters']) else []
                    api.dispatch(name, tuple(args + example['args']), example.get('kwargs', {}))
        for address in ('/docs', '/docs/'):
            with urlopen(self.url + address) as response:
                html = response.read().decode()
                self.assertIn('/ui/assets/', html)
                self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])
                self.assertNotIn('swagger-ui', html)
        node = shutil.which('node')
        if not node or not (ROOT / 'frontend/node_modules/playwright').is_dir() or not (ROOT / '.browser-cache').is_dir():
            self.skipTest('npm ci and Playwright Chromium are required for the browser check')
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        arguments = [node, str(ROOT / 'frontend/tests/documentation.mjs'), self.url]
        if environment.get('TACTIC_STREAM_DOCS_SCREENSHOT'):
            arguments.append(environment['TACTIC_STREAM_DOCS_SCREENSHOT'])
        result = subprocess.run(arguments, cwd=ROOT / 'frontend', env=environment, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout.strip())
        snippet = output['snippet'].replace('from getpass import getpass', "getpass = lambda prompt: 'private-test-password'")
        namespace = {'print': lambda *args: None}
        exec(compile(snippet, '<docs XML-RPC example>', 'exec'), namespace)
        try:
            self.assertEqual(ast.literal_eval(namespace['result']), output['records'])
        finally:
            namespace['api'].__exit__(None, None, None)

    def test_navigation_in_chromium(self):
        self._workspace_schema_fixture()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/navigation.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _workspace_schema_fixture(self):
        # Broken wildcard edges belong to negative kernel tests, not ordinary UI projects.
        with self.store.connection(write=True) as db:
            schema = db.execute('SELECT id, "schema" FROM "schema" WHERE project_code=\'one\'').fetchone()
            xml = ET.fromstring(schema['schema'])
            for connection in list(xml):
                if connection.tag == 'connect' and connection.get('from','').startswith(('contract/','sthpw/contract_')) and connection.get('from') not in ('contract/collection','contract/entity_in_collection'):
                    xml.remove(connection)
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(ET.tostring(xml,encoding='unicode'),schema['id']))
        def restore():
            with self.store.connection(write=True) as db:
                db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(schema['schema'],schema['id']))
        self.addCleanup(restore)
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
        navigation = proxy.insert(auth,'config/widget_config',dict(search_type='SideBarWdg',view='project_view',priority=1000,
            config='<config><project_view><element name="entities" title="Entities"><display class="LinkWdg"><search_type>contract/entity</search_type></display></element><element name="collections" title="Collections"><display class="LinkWdg"><search_type>contract/collection</search_type></display></element></project_view></config>'))
        self.addCleanup(lambda: proxy.delete_sobject(auth,navigation['__search_key__']))

    def test_lazy_loading_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/lazy_loading.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout.strip())

    def test_button_geometry_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/button_geometry.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_record_creation_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/record_create.mjs'), self.url,
                                 str(ROOT / '.screenshots/object-creation-touch.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_object_batch_in_chromium(self):
        self._workspace_schema_fixture()
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.store.database_path('one'))) as database, database:
            database.execute('ALTER TABLE entity ADD COLUMN description text')
        result = subprocess.run(
            [shutil.which('node'), str(ROOT / 'frontend/tests/object_batch.mjs'), self.url],
            cwd=ROOT / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=75,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_object_links_in_chromium(self):
        self._workspace_schema_fixture()
        result = subprocess.run(
            [shutil.which('node'), str(ROOT / 'frontend/tests/object_links.mjs'), self.url],
            cwd=ROOT / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=75,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mobile_objects_in_chromium(self):
        self._workspace_schema_fixture()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/mobile_objects.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=75)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_naming_editor_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/naming.mjs'), self.url,
                                 str(ROOT / '.screenshots/naming-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_workflow_editor_in_chromium(self):
        node = shutil.which('node')
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([node, str(ROOT / 'frontend/tests/workflow.mjs'), self.url,
                                 str(ROOT / '.screenshots/workflow-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schema_editor_in_chromium(self):
        node = shutil.which('node')
        browser_cache = ROOT / '.browser-cache'
        if not node or not (ROOT / 'frontend/node_modules/playwright').is_dir() or not browser_cache.is_dir():
            self.skipTest('Playwright Chromium is required')
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin')
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='schema_browser', project_title='Schema browser', project_stype=['schema_a', 'schema_b']))
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_cache)
        result = subprocess.run([node, str(ROOT / 'frontend/tests/schema.mjs'), self.url,
                                str(ROOT / '.screenshots/schema-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_search_types_editor_in_chromium(self):
        node = shutil.which('node')
        browser_cache = ROOT / '.browser-cache'
        if not node or not (ROOT / 'frontend/node_modules/playwright').is_dir() or not browser_cache.is_dir():
            self.skipTest('Playwright Chromium is required')
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_cache)
        result = subprocess.run([node, str(ROOT / 'frontend/tests/search_types.mjs'), self.url,
                                 str(ROOT / '.screenshots/search-types-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_workflow_progress_default_listener(self):
        proxy = self.proxy(); auth = self.ticket(proxy)
        command = 'tactic.ui.panel.workflow_cmd.WorkflowCmd'
        def call(action, **values):
            return proxy.execute_cmd(auth, command, dict(action=action, project_code='one', **values))['info']
        result = call('new', identity='contract/entity'); document = result['document']
        document.update(name='Progress defaults', searchType='contract/entity',
            xml='<pipeline><process name="progress" type="progress" xpos="20" ypos="30"/></pipeline>',
            processSettings={'progress': {'version': 2, 'node_type': 'progress'}})
        saved = call('save', document=document)
        progress = saved['document']['processSettings']['progress']['progress']
        self.assertEqual(progress['related_process'], 'progress')
        self.assertEqual(progress['related_scope'], 'local')
        trigger = ast.literal_eval(proxy.query(auth, 'config/trigger', [('code', progress['trigger_code'])]))[0]
        self.assertEqual(trigger['process'], 'progress')
        self.assertEqual(trigger['class_name'], 'pyasm.command.ProcessStatusTrigger')

    def test_administration_in_chromium(self):
        proxy = self.proxy()
        auth = self.ticket(proxy)
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='capture', project_title='Demo'))
        auth['project'] = 'capture'
        types_command = 'tactic.ui.panel.search_types_cmd.SearchTypesCmd'
        for title, columns in [('Assets', [dict(name='shot_code', type='varchar(256)')]), ('Shots', [])]:
            proxy.execute_cmd(auth, types_command, dict(action='save', project_code='capture', document=dict(title=title, columns=columns)))
        schema_command = 'tactic.ui.panel.schema_cmd.SchemaCmd'
        result = proxy.execute_cmd(auth, schema_command, dict(action='load', project_code='capture'))['info']
        xml = ET.fromstring(result['document']['xml'])
        for node in xml.findall('search_type'):
            if node.get('name') in ('capture/assets', 'capture/shots'):
                node.set('xpos', '20' if node.get('name') == 'capture/assets' else '350'); node.set('ypos', '30')
        ET.SubElement(xml, 'connect', {'from': 'capture/assets', 'to': 'capture/shots', 'relationship': 'code', 'type': 'hierarchy', 'from_col': 'shot_code', 'to_col': 'code'})
        proxy.execute_cmd(auth, schema_command, dict(action='save', project_code='capture', expected_revision=result['revision'], document=dict(xml=ET.tostring(xml, encoding='unicode'))))
        for index in range(3):
            proxy.insert(auth, 'sthpw/login_group', dict(login_group=f'Artists {index}', description=f'Test artists {index}',
                access_level='none', access_rules='<rules><rule group="project" code="one" access="allow"/></rules>' if index == 0 else '<rules/>'))
        proxy.insert(auth, 'sthpw/login', dict(login='artist', display_name='Artist', email='artist@example.test'))
        proxy.insert(auth, 'sthpw/pipeline', dict(code='capture/admin_capture', name='Assets', search_type='capture/assets',
            project_code='capture', pipeline='<pipeline><process name="model" type="manual" xpos="20" ypos="30" color="#6688aa"/><process name="review" type="approval" xpos="350" ypos="30"/><connect from="model" to="review"/></pipeline>'))
        columns_record = proxy.insert(auth, 'config/widget_config', dict(search_type='capture/assets', view='table',
            config='<config custom="kept"><!--keep reorder--><table><element name="code" title="Code"><display widget="text"/></element><element name="name" title="Name"><display widget="text"/></element></table><extension value="kept"/></config>'))
        sidebar = proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='definition',
            config='<config><definition><element name="my_tasks" title="My tasks"><display class="LinkWdg"/><search_type>capture/assets</search_type><search_view>link_search:ready:capture/assets</search_view></element></definition></config>'))
        self.addCleanup(lambda: proxy.delete_sobject(auth, sidebar['__search_key__']))
        sidebar_tabs = proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler', config='<config><tactic_handler><element name="my_tasks"/></tactic_handler></config>'))
        self.addCleanup(lambda: proxy.delete_sobject(auth, sidebar_tabs['__search_key__']))
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/administration.mjs'), self.url,
            str(ROOT / '.screenshots/administration-current'), str(columns_record['id'])], cwd=ROOT / 'frontend',
            env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        saved = ast.literal_eval(proxy.query(auth, 'config/widget_config', [('search_type', 'capture/assets'), ('view', 'table')]))
        saved = [row for row in saved if row['code'] == columns_record['code']]
        self.assertEqual(len(saved), 1)
        self.assertEqual([element.get('name') for element in ET.fromstring(saved[0]['config']).findall('table/element')], ['name', 'code'])
        for fragment in ('<!--keep reorder-->', 'custom="kept"', '<extension value="kept"'):
            self.assertIn(fragment, saved[0]['config'])

    def test_configuration_in_chromium(self):
        proxy = self.proxy(); auth = self.ticket(proxy)
        reader = proxy.insert(auth, 'sthpw/login', dict(login='configuration_preferences_reader', password=hash_password('private-test-password')))
        self.addCleanup(lambda: proxy.delete_sobject(auth, reader['__search_key__']))
        repository = self.store.data_dir / 'browser_repository'
        repository.mkdir(exist_ok=True)
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/configuration.mjs'), self.url,
            str(ROOT / '.screenshots/configuration-current'),repository.as_posix()], cwd=ROOT / 'frontend',
            env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_configuration_project_editor_lifecycle(self):
        proxy = self.proxy()
        auth = dict(self.ticket(proxy), project='admin')
        key = 'sthpw/project?code=one'
        payload = dict(ticket=auth['ticket'], project='admin',
                       search_type='sthpw/project', view='configuration_edit',
                       search_key=key)
        with urlopen(Request(self.url + '/admin/form', json.dumps(payload).encode(),
                             headers={'Content-Type': 'application/json'})) as response:
            definition = json.load(response)['result']
        fields = {field['name']: field for field in definition['fields']}
        self.assertEqual(fields['code']['options']['read_only'], 'true')
        self.assertEqual(fields['s_status']['action']['handler'],
                         'tactic.ui.app.project_editor.ProjectArchiveAction')
        self.assertIn('snapshot', fields)
        args = dict(search_key=key, view='configuration_edit',
                    element_names=['title', 'category', 'description', 'is_template', 's_status'])
        values = {'edit|title': 'Configuration project', 'edit|category': 'Studio',
                  'edit|description': 'Edited through the existing form owner',
                  'edit|is_template': 'on', 'edit|s_status': 'retired'}
        proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, values)
        record = proxy.get_by_search_key(auth, key)
        self.assertEqual(record['title'], 'Configuration project')
        self.assertEqual(record['category'], 'Studio')
        self.assertEqual(record['s_status'], 'retired')
        logs = ast.literal_eval(proxy.query(auth, 'sthpw/retire_log',
                                           [('search_code', 'one')]))
        self.assertEqual(len(logs), 1, 'Lifecycle uses native retirement logging')
        values['edit|s_status'] = ''
        proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, values)
        self.assertIsNone(proxy.get_by_search_key(auth, key)['s_status'])
        values['edit|s_status'] = 'invalid'
        values['edit|title'] = 'Must roll back'
        with self.assertRaises(Fault):
            proxy.execute_cmd(auth, 'tactic.ui.panel.EditCmd', args, values)
        self.assertEqual(proxy.get_by_search_key(auth, key)['title'], 'Configuration project')

    def test_configuration_native_project_archive(self):
        import zipfile
        from io import BytesIO
        proxy = self.proxy()
        auth = self.ticket(proxy)
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='configuration_export', project_title='Configuration export'))
        result = proxy.execute_cmd(auth, 'tactic.ui.app.ProjectTemplateExportCmd', dict(project_code='configuration_export'))
        filename = result['info']['filename']
        with urlopen(self.url + '/assets/_cache/' + auth['ticket'] + '/' + filename) as response:
            data = response.read()
        with zipfile.ZipFile(BytesIO(data)) as archive:
            self.assertTrue(any(name.endswith('manifest.xml') for name in archive.namelist()))
        with self.assertRaises(Fault):
            proxy.execute_cmd(auth, 'tactic.ui.app.ProjectTemplateExportCmd', dict(project_code='admin'))

    def test_configuration_help_in_chromium(self):
        environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'), STREAM_CHECK_PASSWORD='private-test-password')
        result = subprocess.run([shutil.which('node'),str(ROOT / 'frontend/tests/help.mjs'),self.url], cwd=ROOT / 'frontend',
            env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_configuration_repository_paths(self):
        from tactic_stream.server.api import Api
        from pyasm.common import Config, Environment
        from pyasm.common.errors import SecurityException
        api = Api(self.store)
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='admin')
        cmd = 'tactic.ui.app.RepositoryPathsCmd'
        loaded = api.dispatch('execute_cmd', (auth, cmd, {}))['info']['repositories']
        self.assertTrue(any(row['is_default'] for row in loaded))
        self.assertTrue(all(row['status'] == 'unchecked' for row in loaded))
        checked = api.dispatch('execute_cmd', (auth, cmd, dict(action='check')))['info']['repositories']
        self.assertTrue(all(row['status'] == 'available' for row in checked))
        self.assertEqual({row['path'] for row in loaded}, {row['path'] for row in checked})
        for row in checked:
            self.assertTrue(Path(row['path']).is_relative_to(self.store.data_dir), 'Only the private test repository is checked')
            self.assertFalse(list(Path(row['path']).glob('tmp*')), 'Path probes leave no files')
        blocked = self.store.data_dir / 'repository-file'
        blocked.write_bytes(b'preserve')
        with patch.object(Environment, 'get_asset_dirs', return_value={'blocked': str(blocked)}):
            unavailable = api.dispatch('execute_cmd', (auth, cmd, dict(action='check')))['info']['repositories']
        self.assertEqual(next(row['status'] for row in unavailable if row['alias'] == 'blocked'), 'inaccessible')
        self.assertEqual(blocked.read_bytes(), b'preserve')
        draft = api.dispatch('execute_cmd',(auth,cmd,dict(action='check',paths={'draft':'','default':checked[0]['path']})))['info']['repositories']
        self.assertEqual(next(row['status'] for row in draft if row['alias'] == 'draft'),'inaccessible')
        with self.assertRaises(Exception): api.dispatch('execute_cmd',(auth,cmd,dict(action='check',paths={'bad':'\x00'})))
        login = api.dispatch('insert',(auth,'sthpw/login',dict(login='repository_reader',password=hash_password('private-test-password'))))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,login['__search_key__'])))
        guest = dict(ticket=api.get_ticket('repository_reader','private-test-password'),project='admin')
        for command in (cmd, 'tactic.ui.app.ProjectTemplateExportCmd'):
            with self.assertRaises(SecurityException):
                api.dispatch('execute_cmd',(guest,command,dict(project_code='one')))

    def test_repository_configuration_lifecycle(self):
        import shutil
        proxy = self.proxy(); auth = dict(self.ticket(proxy), project='one')
        with tempfile.TemporaryDirectory(dir=self.store.data_dir) as directory:
            root = Path(directory); first = root / 'first'; second = root / 'second'
            first.mkdir(); second.mkdir()
            config = root / 'config.xml'
            config.write_text('<config><services><enable>tactic</enable></services><checkin><asset_base_dir>' + (self.store.data_dir / 'assets').as_posix() + '</asset_base_dir><web_base_dir>/assets</web_base_dir></checkin></config>',encoding='utf-8')
            with patch.dict(os.environ, TACTIC_CONFIG_PATH=str(config), TACTIC_PORTS='', TACTIC_TMP_CONFIG_PATH=''):
                def request(changes=None, revision=None):
                    payload = dict(ticket=auth['ticket'])
                    if changes is not None: payload.update(changes=changes,revision=revision)
                    with urlopen(Request(self.url + '/admin/configuration' + ('/save' if changes is not None else ''),json.dumps(payload).encode(),headers={'Content-Type':'application/json'})) as response:
                        return json.load(response)['result']
                loaded = request()
                roots = {'default':(self.store.data_dir / 'assets').as_posix(),'custom_0':first.as_posix()}
                saved = request({'checkin/asset_base_dir':json.dumps(roots),'checkin/web_base_dir':json.dumps({'default':'/assets','custom_0':'/repository/custom_0'})},loaded['revision'])
                self.assertTrue(saved['restart_required'])
                proxy.upload_file(auth,'repository.txt',Binary(b'repository original'))
                options = dict(search_key='contract/entity?project=one&code=A',context='repository_lifecycle',process='publish',files=['repository.txt'],create_icon=False,repository_alias='custom_0')
                snapshot = proxy.execute_cmd(auth,'tactic.command.uploaded_checkin_cmd.UploadedCheckinCmd',options)['info']['snapshot']
                files = ast.literal_eval(proxy.query(auth,'sthpw/file',[('snapshot_code',snapshot['code']),('type','main')]))
                self.assertEqual(files[0]['base_dir_alias'],'custom_0')
                relative = Path(files[0]['relative_dir']) / files[0]['file_name']
                self.assertEqual((first / relative).read_bytes(),b'repository original')
                changed_roots = dict(roots,custom_0=second.as_posix())
                for changes in ({'checkin/asset_base_dir':roots['default']}, {'checkin/asset_base_dir':json.dumps(changed_roots)}):
                    with self.assertRaises(HTTPError) as caught: request(changes,saved['revision'])
                    with caught.exception as response: self.assertEqual(json.load(response)['error_field'],'checkin/asset_base_dir')
                shutil.copytree(first,second,dirs_exist_ok=True)
                (second / relative).write_bytes(b'wrong')
                with self.assertRaises(HTTPError) as caught: request({'checkin/asset_base_dir':json.dumps(changed_roots)},saved['revision'])
                caught.exception.close()
                (second / relative).write_bytes(b'repository original')
                relocated = request({'checkin/asset_base_dir':json.dumps(changed_roots)},saved['revision'])
                self.assertTrue(relocated['saved'])
                paths = proxy.get_paths(auth,options['search_key'],options['context'],snapshot['version'],'main',None,False,False,None,['lib'])
                self.assertEqual(paths['lib_paths'][0],(second / relative).as_posix())
                import asyncio
                restarted = create_app(self.store.data_dir)
                messages = []
                async def download():
                    async def receive(): return {'type':'http.request','body':b'','more_body':False}
                    async def send(message): messages.append(message)
                    address = '/repository/custom_0/' + relative.as_posix()
                    await restarted(dict(type='http',method='GET',path=address,raw_path=address.encode(),query_string=b'',headers=[],http_version='1.1',scheme='http',server=('test',80),client=('127.0.0.1',0),root_path='',asgi={'version':'3.0','spec_version':'2.4'}),receive,send)
                asyncio.run(download())
                self.assertEqual(messages[0]['status'],200)
                self.assertEqual(b''.join(message.get('body',b'') for message in messages),b'repository original')
                proxy.upload_file(auth,'repository.txt',Binary(b'revision'))
                with self.assertRaises(Fault): proxy.execute_cmd(auth,'tactic.command.uploaded_checkin_cmd.UploadedCheckinCmd',dict(options,is_revision=True,version=snapshot['version'],repository_alias='default'))
                revision = proxy.execute_cmd(auth,'tactic.command.uploaded_checkin_cmd.UploadedCheckinCmd',dict(options,is_revision=True,version=snapshot['version']))
                self.assertEqual(revision['info']['snapshot']['version'],snapshot['version'])
                self.assertEqual((second / relative).read_bytes(),b'revision')
                for item in ast.literal_eval(proxy.query(auth,'sthpw/file',[('base_dir_alias','custom_0')])):
                    proxy.delete_sobject(auth,item['__search_key__'])
                for item in ast.literal_eval(proxy.query(auth,'sthpw/snapshot',[('context',options['context'])])):
                    proxy.delete_sobject(auth,item['__search_key__'])

    def test_description_editor_in_chromium(self):
        from tactic_stream.server.api import Api
        api = Api(self.store); api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin','private-test-password'),project='one',language='python')
        # Contract fixtures include deliberately incomplete wildcard relations, unrelated to this screen.
        with self.store.connection(write=True) as db:
            schema = db.execute('SELECT id, "schema" FROM "schema" WHERE project_code=\'one\'').fetchone()
            xml = ET.fromstring(schema['schema'])
            for connection in list(xml):
                if connection.tag == 'connect' and connection.get('from','').startswith(('contract/','sthpw/contract_')) and connection.get('from') not in ('contract/collection','contract/entity_in_collection'):
                    xml.remove(connection)
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(ET.tostring(xml,encoding='unicode'),schema['id']))
        def restore_schema():
            with self.store.connection(write=True) as db: db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(schema['schema'],schema['id']))
        self.addCleanup(restore_schema)
        kind = 'one/description_assets'
        api.dispatch('execute_cmd',(auth,'tactic.core.schema_commands.SearchTypeCreatorCmd',dict(search_type_name=kind,asset_title='Description assets')))
        records = [api.dispatch('insert',(auth,kind,dict(code='DESCRIPTION_' + suffix,name='Description ' + suffix,description=text))) for suffix,text in [('A','Original description'),('B','Original B')]]
        for record in records: self.addCleanup(lambda key=record['__search_key__']: api.dispatch('delete_sobject',(auth,key)))
        pipeline = api.dispatch('insert',(auth,'sthpw/pipeline',dict(code='description_pipeline',project_code='one',search_type=kind,pipeline='<pipeline><process name="publish" label="Publish" description="Process description" /></pipeline>')))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,pipeline['__search_key__'])))
        api.dispatch('update',(auth,records[0]['__search_key__'],dict(pipeline_code=pipeline['code'])))
        snapshot = api.dispatch('create_snapshot',(auth,records[0]['__search_key__'],'publish','file','Snapshot description'))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,snapshot['__search_key__'])))
        from pyasm.search.search import RequestContext, request_context
        from tactic_stream.server.result_items import read_result_items
        with request_context(RequestContext(self.store,'admin','one')):
            api.auth.bind_security('admin',auth['ticket'])
            self.assertTrue(read_result_items(kind,[records[0]['__search_key__']],dict(kind='children'))['items'][0]['branches'])
        result = subprocess.run([shutil.which('node'),str(ROOT/'frontend/tests/description.mjs'),self.url,str(ROOT/'.screenshots/description-current'),*[record['__search_key__'] for record in records],snapshot['__search_key__']],cwd=ROOT/'frontend',env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)

    def test_knowledge_base_in_chromium(self):
        proxy = self.proxy()
        ticket = proxy.get_ticket('admin', 'private-test-password')
        def operation(action, **values):
            body = json.dumps(dict(ticket=ticket, project='one', **values)).encode('utf-8')
            with urlopen(Request(self.url + '/admin/knowledge/' + action, data=body, headers={'Content-Type': 'application/json'})) as response:
                return json.load(response)['result']
        operation('initialize')
        section = operation('save', document=dict(title='Pipeline guide', kind='section', description='Project documentation'))
        article = operation('save', document=dict(title='Publishing guide', description='How to publish', kind='article', parentCode=section['identity'],
            contentMarkdown='# Publish\n\nUse **native** versions.\n\n## Checks\n\nVerify files before publishing.\n\n```python\nprint("ready")\n```', contentText='Publish Use native versions Checks Verify files before publishing ready'))
        output = ROOT / '.screenshots/knowledge-current'; output.mkdir(parents=True, exist_ok=True)
        (output / 'projection.json').write_text(json.dumps(dict(section=section, article=article), ensure_ascii=False, indent=2), encoding='utf-8')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/knowledge.mjs'), self.url, str(output), article['identity'], section['identity']],
            cwd=ROOT / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_snapshot_browser_with_handler_single_file_metadata(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        owner = proxy.insert(auth, 'contract/entity', dict(code='SINGLE_FILE_METADATA', name='Single file'))
        self.addCleanup(lambda: proxy.delete_sobject(auth, owner['__search_key__']))
        payload = b'Single file without frame ranges'
        proxy.upload_file(auth, 'single.txt', Binary(payload))
        snapshot = proxy.simple_checkin(auth, owner['__search_key__'], 'publish', 'single.txt', dict(mode='uploaded', create_icon=False))
        file = ast.literal_eval(proxy.query(auth, 'sthpw/file', [('snapshot_code', snapshot['code'])]))[0]
        filename = file['file_name']
        metadata = dict(type='file', template='$FILENAME.$EXT', new_template='$FILENAME.$EXT',
                        new_filename=Path(filename).stem, new_file_ext=Path(filename).suffix[1:])
        proxy.update(auth, file['__search_key__'], dict(metadata=metadata))
        def read(kind, key, branch, offset=0):
            request = Request(self.url + '/admin/result-items', data=json.dumps(dict(
                ticket=auth['ticket'], project='one', search_type=kind, search_keys=[key],
                branch=dict(kind=branch, **({'process': ''} if branch == 'snapshot_browser' else {})),
                offset=offset, limit=50)).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=10) as response:
                self.assertEqual(response.status, 200)
                return json.load(response)['result']
        result = read('sthpw/snapshot', snapshot['__search_key__'], 'snapshot_browser')
        self.assertEqual([item['code'] for item in result['snapshots']], [snapshot['code']])
        rows = [row for row in result['rows'] if row['rowType'] == 'file']
        self.assertEqual({row['filename'] for row in rows}, {filename})
        self.assertTrue(all(row['exists'] for row in rows))
        self.assertEqual(Path(rows[0]['fullPath']).read_bytes(), payload)
        members = read('sthpw/file', file['__search_key__'], 'snapshot_members')
        self.assertEqual([row['filename'] for row in members['rows']], [filename])
        self.assertEqual(read('sthpw/file', file['__search_key__'], 'snapshot_members', offset=1)['rows'], [])

    def test_snapshot_browser_in_chromium(self):
        from tactic_stream.server.api import Api
        from pyasm.search.search import RequestContext, request_context
        from tactic_stream.server.result_items import read_result_items
        from PIL import Image, ImageDraw
        api = Api(self.store); api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin','private-test-password'),project='one',language='python')
        with self.store.connection(write=True) as db:
            schema = db.execute('SELECT id, "schema" FROM "schema" WHERE project_code=\'one\'').fetchone()
            xml = ET.fromstring(schema['schema'])
            for edge in list(xml):
                if edge.tag == 'connect' and edge.get('from','').startswith(('contract/','sthpw/contract_')) and edge.get('from') not in ('contract/collection','contract/entity_in_collection'):
                    xml.remove(edge)
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(ET.tostring(xml,encoding='unicode'),schema['id']))
        def restore_schema():
            with self.store.connection(write=True) as db: db.execute('UPDATE "schema" SET "schema"=? WHERE id=?',(schema['schema'],schema['id']))
        self.addCleanup(restore_schema)
        kind = 'one/snapshot_assets'
        api.dispatch('execute_cmd',(auth,'tactic.core.schema_commands.SearchTypeCreatorCmd',dict(search_type_name=kind,asset_title='Snapshot assets')))
        naming = api.dispatch('insert',(auth,'config/naming',dict(search_type=kind,snapshot_type='file',context='publish',latest_versionless=True,dir_naming='{project.code}/snapshot_browser/{sobject.code}/latest',file_naming='{basefile}.{ext}')))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,naming['__search_key__'])))
        records = [api.dispatch('insert',(auth,kind,dict(code='SNAPSHOT_' + suffix,name='Snapshot ' + suffix,description='Snapshot browser owner'))) for suffix in ('A','B')]
        for record in records: self.addCleanup(lambda key=record['__search_key__']: api.dispatch('delete_sobject',(auth,key)))
        pipeline = api.dispatch('insert',(auth,'sthpw/pipeline',dict(code='snapshot_pipeline',project_code='one',search_type=kind,pipeline='<pipeline><process name="publish" label="Publish"/><process name="model" label="Model"/></pipeline>')))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,pipeline['__search_key__'])))
        api.dispatch('update',(auth,records[0]['__search_key__'],dict(pipeline_code=pipeline['code'])))
        source = Path(self.temp.name) / 'Snapshot image.png'
        versions = []
        for number,color in ((1,(60,100,160)),(2,(55,145,95))):
            image = Image.new('RGB',(600,240),color)
            ImageDraw.Draw(image).text((25,25),'Native snapshot version ' + str(number),fill='white')
            image.save(source)
            api.dispatch('upload_file',(auth,source.name,Binary(source.read_bytes())))
            versions.append(api.dispatch('simple_checkin',(auth,records[0]['__search_key__'],'publish',source.name),dict(mode='uploaded',create_icon=False,description='Version ' + str(number))))
        text = Path(self.temp.name) / 'Model description.txt'; text.write_text('Model file',encoding='utf-8')
        api.dispatch('upload_file',(auth,text.name,Binary(text.read_bytes())))
        api.dispatch('simple_checkin',(auth,records[0]['__search_key__'],'model/geometry',text.name),dict(mode='uploaded',create_icon=False))
        task = api.dispatch('create_task',(auth,records[0]['__search_key__'],'model'))
        self.addCleanup(lambda: api.dispatch('delete_sobject',(auth,task['__search_key__'])))
        with request_context(RequestContext(self.store,'admin','one')):
            api.auth.bind_security('admin',auth['ticket'])
            result = read_result_items(kind,[records[0]['__search_key__']],dict(kind='snapshot_browser'))
            self.assertEqual([row['version'] for row in result['snapshots']],[-1,2,1])
            self.assertEqual(len(result['previews']),3)
            from tactic_stream.server.snapshot_browser import preview_url
            sample = result['previews'][0]['file']
            self.assertEqual(sample['path'],Path(sample['fullPath']).parent.as_posix())
            stamp = Path(sample['fullPath']).stat()
            original_url = preview_url(sample)
            os.utime(sample['fullPath'],ns=(stamp.st_atime_ns,stamp.st_mtime_ns + 1_000_000))
            self.assertNotEqual(preview_url(sample),original_url)
            os.utime(sample['fullPath'],ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            from tactic_stream.server.interface import read_form
            definition = read_form('sthpw/file',search_key=next(row['record']['__search_key__'] for row in result['rows'] if row['rowType'] == 'file'))
            self.assertEqual(definition['mode'],'edit')
            (ROOT/'.screenshots/snapshot-file-form.json').write_text(json.dumps(definition,ensure_ascii=False),encoding='utf-8')
            page = read_result_items(kind,[records[0]['__search_key__']],dict(kind='snapshot_browser'),limit=1)
            self.assertTrue(page['has_next'])
            page2 = read_result_items(kind,[records[0]['__search_key__']],dict(kind='snapshot_browser'),offset=1,limit=1)
            self.assertEqual(page2['snapshots'][0]['version'],2)
            explicit = read_result_items('sthpw/snapshot',[versions[0]['__search_key__']],dict(kind='snapshot_browser'))
            self.assertEqual(len(explicit['snapshots']),1)
            self.assertEqual(explicit['snapshots'][0]['version'],1)
            model = read_result_items(kind,[records[0]['__search_key__']],dict(kind='snapshot_browser',process='model'))
            self.assertEqual({row['context'] for row in model['snapshots']},{'model/geometry'})
            self.assertEqual(read_result_items('sthpw/task',[task['__search_key__']],dict(kind='snapshot_browser'))['process'],'model')
            with self.assertRaises(ValueError): read_result_items(kind,[records[0]['__search_key__']],dict(kind='snapshot_browser',process=[]))
            output = ROOT / '.screenshots/snapshot-browser-current'; output.mkdir(parents=True,exist_ok=True)
            for preview in result['previews']:
                target = output / (preview['file']['token'] + '.png')
                shutil.copyfile(preview['file']['fullPath'],target)
                preview['localUrl'] = target.as_uri()
            (output/'projection.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        projection = result
        files = [row for row in projection['rows'] if row['rowType'] == 'file']
        first_version_file = next(file for file in files if file['snapshotKey'] == versions[0]['__search_key__'])
        original_bytes = Path(first_version_file['fullPath']).read_bytes()
        from pyasm.biz import Snapshot
        original_commit = Snapshot.commit
        def fail_snapshot_commit(snapshot, *args, **kwargs):
            if snapshot.get_code() == versions[0]['code']:
                raise ValueError('Forced snapshot file deletion failure')
            return original_commit(snapshot,*args,**kwargs)
        with patch.object(Snapshot,'commit',fail_snapshot_commit), self.assertRaisesRegex(ValueError,'Forced snapshot file deletion failure'):
            api.dispatch('delete_sobject',(auth,first_version_file['record']['__search_key__']),dict(include_dependencies=True))
        self.assertEqual(Path(first_version_file['fullPath']).read_bytes(),original_bytes)
        self.assertEqual(len(api.dispatch('query',(auth,'sthpw/file',[['code',first_version_file['token']]]))),1)
        try:
            result = subprocess.run([shutil.which('node'),str(ROOT/'frontend/tests/snapshot_browser.mjs'),self.url,str(output),records[0]['__search_key__'],records[1]['__search_key__'],versions[0]['__search_key__']],cwd=ROOT/'frontend',env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        except subprocess.TimeoutExpired as error:
            self.fail(f'Snapshot Browser timed out. stdout={error.stdout!r}; stderr={error.stderr!r}')
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertEqual(api.dispatch('query',(auth,'sthpw/file',[['code',files[0]['token']]]))[0]['source_path'],'Snapshot Browser verified source')
        self.assertEqual(api.dispatch('query',(auth,'sthpw/file',[['code',first_version_file['token']]])),[])
        self.assertFalse(Path(first_version_file['fullPath']).exists())
        self.assertEqual(len(api.dispatch('query',(auth,'sthpw/snapshot',[['code',versions[0]['code']]]))),1)
        for file in files:
            if file != first_version_file: self.assertTrue(Path(file['fullPath']).is_file())

    def test_search_type_preview_in_chromium(self):
        node = shutil.which('node')
        browser_cache = ROOT / '.browser-cache'
        if not node or not (ROOT / 'frontend/node_modules/playwright').is_dir() or not browser_cache.is_dir():
            self.skipTest('Playwright Chromium is required')
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_cache)
        result = subprocess.run([node, str(ROOT / 'frontend/tests/search_type_preview.mjs'), self.url,
                                 str(ROOT / '.screenshots/search-type-preview-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_project_navigation(self):
        proxy = self.proxy()
        auth = dict(self.ticket(proxy), project='one')
        configs = []
        reader = None
        def request(**values):
            payload = dict(ticket=auth['ticket'], project='one')
            payload.update(values)
            try:
                response = urlopen(Request(self.url + '/admin/navigation', json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}))
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read())
        def configuration(action, view='definition', **values):
            payload = dict(ticket=auth['ticket'], project='one', search_type='SideBarWdg', view=view)
            payload.update(values)
            try:
                response = urlopen(Request(self.url + '/admin/widget-configuration/' + action, json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}))
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read())
        try:
            definition = '''<config><definition>
<element name="work" title="Work"><display class="SideBarSectionLinkWdg"><view>work_links</view></display></element>
<element name="entity" title="Entity records" icon="FAS_DATABASE"><display class="LinkWdg"><class_name>tactic.ui.panel.ViewPanelWdg</class_name><search_type>contract/entity</search_type><view>table</view></display></element>
<element name="hidden" title="Hidden" is_visible="off"><display class="LinkWdg"><search_type>contract/entity</search_type></display></element>
<element name="unknown" title="Unmigrated"><display class="UnmigratedWdg"/></element>
<element name="divider"><display class="SeparatorWdg"/></element>
</definition></config>'''
            root = '''<config><project_view><element name="work"/><element name="divider"/>
<element name="inline" title="Inline"><display class="SideBarSectionLinkWdg"/>
<element name="inline_entity" title="Inline records"><display class="LinkWdg"><search_type>contract/entity</search_type><view>table</view></display></element>
</element><element name="hidden"/><element name="unknown"/></project_view></config>'''
            for view, xml in [('definition', definition), ('project_view', root), ('work_links', '<config><work_links><element name="entity"/></work_links></config>')]:
                configs.append(proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view=view, config=xml)))
            status, result = request()
            self.assertEqual(status, 200, result)
            result = result['result']
            self.assertTrue(result['configured'])
            self.assertEqual([item['kind'] for item in result['entries']], ['section', 'separator', 'section', 'link'])
            leaf = result['entries'][0]['children'][0]
            self.assertEqual(leaf['default_view_mode'], 'table')
            self.assertEqual([leaf['title'], leaf['icon'], leaf['display']['options']['search_type']], ['Entity records', 'FAS_DATABASE', 'contract/entity'])
            self.assertEqual(result['entries'][2]['children'][0]['title'], 'Inline records')
            status, loaded = configuration('read')
            self.assertEqual(status, 200, loaded)
            loaded = loaded['result']
            edited = definition.replace('Entity records', 'Renamed records')
            arguments = dict(source_id=configs[0]['id'], xml=edited, revision=loaded['revision'])
            status, preview = configuration('preview', **arguments)
            self.assertEqual(status, 200, preview)
            self.assertEqual(preview['result']['interface']['navigation']['entries'][0]['children'][0]['title'], 'Renamed records')
            self.assertEqual(request()[1]['result']['entries'][0]['children'][0]['title'], 'Entity records')
            self.assertEqual(configuration('check', **arguments)[0], 200)
            status, saved = configuration('save', **arguments)
            self.assertEqual(status, 200, saved)
            self.assertEqual(configuration('save', **arguments)[0], 409)
            self.assertEqual(request()[1]['result']['entries'][0]['children'][0]['title'], 'Renamed records')
            self.assertEqual(configuration('save', source_id=configs[0]['id'], xml=definition, revision=saved['result']['revision'])[0], 200)
            child = configuration('read', view='work_links')[1]['result']
            cyclic = '<config><work_links><element name="work"/></work_links></config>'
            self.assertEqual(configuration('save', view='work_links', source_id=configs[2]['id'], xml=cyclic, revision=child['revision'])[0], 400)
            self.assertEqual(request()[0], 200)
            reader = proxy.insert(auth, 'sthpw/login', dict(login='navigation_reader', password=hash_password('private-reader-password')))
            ticket = proxy.get_ticket('navigation_reader', 'private-reader-password')
            status, result = request(ticket=ticket)
            self.assertEqual(status, 200, result)
            self.assertEqual(result['result']['entries'], [])
            self.assertEqual(request(ticket='expired-ticket')[0], 403)
            self.assertEqual(configuration('read', ticket=ticket)[0], 403)
            environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'))
            browser = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/navigation.mjs'), self.url,
                                     str(ROOT / '.screenshots/navigation-touch.png')],
                                    cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=45)
            self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
            # An explicit empty Handler view must not expose the registry instead.
            configs.append(proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler', config='<config><tactic_handler/></config>')))
            self.assertEqual(request()[1]['result'], dict(view='tactic_handler', configured=True, entries=[]))
            proxy.delete_sobject(auth, configs.pop()['__search_key__'])
            cycle = '<config><work_links><element name="work"/></work_links></config>'
            proxy.update(auth, configs[2]['__search_key__'], {'config': cycle})
            self.assertEqual(request()[0], 400)
        finally:
            if reader:
                proxy.delete_sobject(auth, reader['__search_key__'])
            for record in reversed(configs):
                proxy.delete_sobject(auth, record['__search_key__'])

    def test_project_catalog_respects_permissions(self):
        from tactic_stream.server.api import Api
        from pyasm.search.search import RequestContext, request_context
        from pyasm.search import Search
        api = Api(self.store); token = api.get_ticket('admin', 'private-test-password')
        auth = dict(ticket=token, project='admin')
        api.dispatch('insert', (auth, 'sthpw/login_group', dict(login_group='catalog_one', access_level='none',
            access_rules='<rules><rule group="project" code="one" access="allow"/></rules>')))
        api.dispatch('insert', (auth, 'sthpw/login', dict(login='catalog_reader', password=hash_password('private-test-password'))))
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            api.auth.bind_security('admin', token)
            search = Search('sthpw/login'); search.add_filter('login', 'catalog_reader')
            search.get_sobject().add_to_group('catalog_one')
        reader = api.get_ticket('catalog_reader', 'private-test-password')
        body = json.dumps(dict(ticket=reader, project='admin')).encode()
        with urlopen(Request(self.url + '/admin/project-catalog', body, headers={'Content-Type': 'application/json'})) as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            rows = json.load(response)['result']
        self.assertEqual({row['code'] for row in rows}, {'admin', 'sthpw', 'one'})
        self.assertTrue(all(row['__builtin__'] == (row['code'] in ('admin', 'sthpw')) for row in rows))
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.url + '/admin/project-catalog', json.dumps(dict(ticket='invalid', project='admin')).encode(), headers={'Content-Type': 'application/json'}))
        self.assertEqual(caught.exception.code, 403); caught.exception.close()

    def test_project_creation_in_chromium(self):
        import zipfile
        from PIL import Image
        proxy = ServerProxy(self.url + '/tactic/default/Api/', allow_none=True)
        ticket = proxy.get_ticket('admin', 'private-test-password')
        auth = {'ticket': ticket, 'project': 'admin', 'language': 'python'}
        proxy.insert(auth, 'sthpw/project', {'code': 'retired_choice', 'title': 'Archived Choice',
                    'category': 'UI testing', 's_status': 'retired'})
        with tempfile.TemporaryDirectory() as staging:
            preview = Path(staging) / 'preview.png'
            Image.new('RGB', (32, 32), '#78a6c4').save(preview)
            package = Path(staging) / 'navigation_source.zip'
            with zipfile.ZipFile(package, 'w') as archive:
                archive.writestr('manifest.xml', '<manifest><data><code>navigation_source</code></data></manifest>')
            environment = os.environ.copy()
            environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
            result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/project_creation.mjs'), self.url,
                str(preview), str(package), str(ROOT / '.screenshots/project-creation.png')],
                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        project = ast.literal_eval(proxy.query(auth, 'sthpw/project', [['code', 'navigation_test']], ['code', 'title', 'category', 'description']))[0]
        self.assertEqual(project['title'], 'Navigation Test')
        self.assertEqual(project['category'], 'UI testing')
        self.assertEqual(project['description'], 'Navigation and sidebar testing')
        self.assertTrue(ast.literal_eval(proxy.query(auth, 'sthpw/snapshot', [['search_type', 'sthpw/project'], ['search_code', 'navigation_test'], ['context', 'icon']])))
        copied = ast.literal_eval(proxy.query(auth, 'sthpw/project', [['code', 'template_copy']]))[0]
        self.assertEqual(copied['title'], 'Template Copy')
        self.assertFalse(copied['is_template'])

    def test_columns_editor_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin', language='python')
        for view, xml in (
            ('table', '<config><!--keep me--><table><element name="code" title="Code" preserve="yes"><display><parameter>keep</parameter></display></element><element name="title" title="Title" /></table></config>'),
            ('edit_definition', '<config><edit_definition><element name="title" title="Title" /></edit_definition></config>'),
            ('custom_view', '<config><custom_view><element name="custom"><display class="custom.Layout" /></element></custom_view></config>')):
            proxy.insert(auth, 'config/widget_config', dict(search_type='sthpw/project', view=view, config=xml, priority=100))
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/columns_editor.mjs'), self.url,
            str(ROOT / '.screenshots/columns-editor.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_handler_connection_fallback_and_removal_through_xmlrpc(self):
        path = ROOT.parent.parent / 'TH/thlib/tactic_query.py'
        text = path.read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        keys = ['contract/entity?project=one&code=A', 'contract/entity?project=one&code=B']
        proxy.execute_python_script(auth, '', dict(code="from pyasm.biz import SObjectConnection\nfrom pyasm.search import Search\nSObjectConnection.create(Search.get_by_code('contract/entity','A'),Search.get_by_code('contract/entity','B'),direction='one')\nreturn True"))
        proxy.insert(auth, 'config/widget_config', dict(search_type='contract/entity', view='connections_contract', priority=100,
            config='<config><connections_contract><element name="code"/><element name="connections"><display class="pyasm.widget.SObjectConnectionElement"><direction>src</direction></display></element></connections_contract></config>'))
        code = source + '''
from pyasm.widget import SObjectConnectionElement, ThumbWdg
native_connection = SObjectConnectionElement.get_cell_value
native_thumb = ThumbWdg.get_cell_value
del SObjectConnectionElement.get_cell_value
del ThumbWdg.get_cell_value
try:
    return query_table_layout('contract/entity', search_keys=kwargs['keys'], view='connections_contract', project_code='one')
finally:
    SObjectConnectionElement.get_cell_value = native_connection
    ThumbWdg.get_cell_value = native_thumb
'''
        layout = json.loads(proxy.execute_python_script(auth, '', dict(code=code, keys=keys))['info'])
        incoming = layout['rows'][keys[0]]['connections']
        self.assertEqual(incoming['error'], '')
        self.assertEqual(incoming['connectionRows'][0]['searchKey'], keys[1])
        self.assertEqual(layout['rows'][keys[1]]['connections']['connectionRows'], [])
        row = incoming['connectionRows'][0]
        text = (ROOT.parent.parent / 'TH/thlib/ui/table/requests.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'remove_connection')
        code = ast.get_source_segment(text, function) + "\nreturn remove_connection(kwargs['parent_key'],kwargs['connection_key'],kwargs['revision'],'src')"
        arguments = dict(code=code, parent_key=keys[0], connection_key=row['connectionKey'], revision=row['expectedRevision'])
        for _ in range(2):
            self.assertEqual(proxy.execute_python_script(auth, '', arguments)['info']['state'], 'removed')
        self.assertTrue(all(proxy.get_by_search_key(auth, key) for key in keys))

    def test_handler_object_summary_and_project_scope_through_xmlrpc(self):
        text = (ROOT.parent.parent / 'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text,function)
        proxy=self.proxy()
        auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one',language='python')
        key='contract/entity?project=one&code=A'
        proxy.create_task(auth,key,'model','summary_contract')
        proxy.insert(auth,'config/widget_config',dict(search_type='contract/entity',view='summary_contract',priority=100,
            config='<config><summary_contract><element name="code"/><element name="summary"><display class="tactic.ui.table.SObjectSummaryElementWdg"/></element></summary_contract></config>'))
        code=source+"\nreturn query_table_layout('contract/entity',view='summary_contract',project_code='one',search_keys=kwargs['keys'])"
        layout=json.loads(proxy.execute_python_script(auth,'',dict(code=code,keys=[key]))['info'])
        cell=layout['rows'][key]['summary']
        self.assertFalse(cell.get('error'),cell)
        self.assertGreaterEqual(int(cell['summary'][0]['value']),1)
        self.assertEqual(cell['summary'][0]['nestedTable']['projectCode'],'one')
        text=(ROOT.parent.parent / 'TH/thlib/ui/table/requests.py').read_text(encoding='utf-8')
        function=next(node for node in ast.parse(text).body if isinstance(node,ast.FunctionDef) and node.name=='read_nested_scope')
        parent=proxy.query(auth,'sthpw/project',[('code','one')])
        parent=ast.literal_eval(parent) if isinstance(parent,str) else parent
        code=ast.get_source_segment(text,function)+"\nreturn read_nested_scope(kwargs['key'],'sthpw/task')"
        records=proxy.execute_python_script(auth,'',dict(code=code,key=parent[0]['__search_key__']))['info']['records']
        self.assertTrue(records)
        self.assertTrue(all(record['project_code']=='one' for record in records))

    def test_table_connections_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        search_type = 'contract/browser_connections'
        proxy.execute_cmd(auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(search_type_name=search_type))
        for code, description in (('TARGET', 'Connection target'), ('ALPHA', 'Alpha source'),
                ('BETA', 'Archived source'), ('MISSING', 'Deleted source')):
            proxy.insert(auth, search_type, dict(code=code, description=description))
        proxy.execute_python_script(auth, '', dict(code="""
from pyasm.biz import SObjectConnection
from pyasm.search import Search
target = Search.get_by_code('contract/browser_connections', 'TARGET')
for code in ('ALPHA', 'BETA', 'MISSING'):
    source = Search.get_by_code('contract/browser_connections', code)
    SObjectConnection.create(source, target, direction='one')
Search.get_by_code('contract/browser_connections', 'BETA').retire()
Search.get_by_code('contract/browser_connections', 'MISSING').delete()
return True
"""))
        proxy.insert(auth, 'config/widget_config', dict(search_type=search_type, view='connections_test', priority=100,
            config='<config><connections_test><element name="code" width="120"/><element name="connections" width="400"><display class="pyasm.widget.SObjectConnectionElement"><direction>dst</direction><icon_size>60</icon_size></display></element></connections_test></config>'))
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/table_connections.mjs'), self.url],
            cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        records = proxy.execute_python_script(auth, '', dict(code="from pyasm.search import Search\nsearch=Search('contract/browser_connections')\nsearch.set_show_retired(True)\nreturn [row.get_code() for row in search.get_sobjects()]"))
        records = records['info']
        records = ast.literal_eval(records) if isinstance(records, str) else records
        self.assertEqual(set(records), {'TARGET', 'ALPHA', 'BETA'})

    def dependency_fixture(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        key = 'contract/entity?project=one&code=A'
        proxy.upload_file(auth, 'dependency.txt', Binary(b'Concrete dependency contents'))
        snapshot = proxy.simple_checkin(auth, key, 'root', 'dependency.txt', dict(mode='uploaded', create_icon=False))
        proxy.execute_python_script(auth, '', dict(code="""
from pyasm.biz import File, Snapshot
from pyasm.search import Search, SearchType
import xml.etree.ElementTree as ET
root = Snapshot.get_by_code(kwargs['snapshot_code'])
target = Snapshot.create(Search.get_by_code('contract/entity', 'B'), 'file', 'target', triggers=False)
main = root.get_all_file_objects()[0]
group = SearchType.create('sthpw/file')
for name, value in dict(project_code='one', snapshot_code=root.get_code(), type='render',
        search_type=main.get_value('search_type'), search_id=main.get_value('search_id'),
        file_name='render.####.exr', relative_dir=main.get_value('relative_dir'),
        file_range='1001-1000000', base_type=File.BASE_TYPE_SEQ, st_size=0).items():
    group.set_value(name, value)
group.commit(triggers=False)
xml = ET.fromstring(root.get_value('snapshot'))
ET.SubElement(xml, 'ref', snapshot_code=target.get_code(), instance='robot/arm')
ET.SubElement(xml, 'fref', snapshot_code='MISSING')
ET.SubElement(xml, 'file', file_code=group.get_code(), name='render.####.exr', file_range='1001-1000000', type='render')
root.set_value('snapshot', ET.tostring(xml,encoding='unicode'))
root.commit(triggers=False)
target.set_value('snapshot', '<snapshot><input_ref snapshot_code="'+root.get_code()+'"/></snapshot>')
target.commit(triggers=False)
return True
""", snapshot_code=snapshot['code'], key=key))
        from xml.sax.saxutils import escape
        admins = proxy.query(auth, 'sthpw/login', [['login', 'admin']])
        admins = ast.literal_eval(admins) if isinstance(admins, str) else admins
        callback = "spt.panel.load_popup('Summary','tactic.ui.startup.GroupSummaryWdg',{search_key:" + json.dumps(admins[0]['__search_key__']) + "});"
        proxy.insert(auth, 'config/widget_config', dict(search_type='contract/entity',view='dependencies_test',priority=100,
            config='<config><dependencies_test><element name="code"/><element name="dependency"><display class="DependencyLink"/></element>'
            '<element name="summary"><display class="tactic.ui.table.ButtonElementWdg"><icon>group</icon><hint>Open summary</hint><cbjs_action>'
            + escape(callback) + '</cbjs_action></display></element></dependencies_test></config>'))
        proxy.insert(dict(auth, project='admin'), 'config/widget_config', dict(search_type='sthpw/snapshot',view='dependencies_snapshot_test',priority=100,
            config='<config><dependencies_snapshot_test><element name="code"/><element name="dependency"><display class="DependencyLink"/></element></dependencies_snapshot_test></config>'))
        return proxy, auth, snapshot

    def parent_group_fixture(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
        proxy.insert(auth, 'config/widget_config', dict(search_type='sthpw/note', view='parent_test', priority=100,
            config='<config><parent_test><element name="code"/><element name="note"/>'
            '<element name="parent" title="Parent"><display class="tactic.ui.table.ParentGroupTableElementWdg"/>'
            '<action class="tactic.ui.table.ParentGroupAction"/></element></parent_test></config>'))
        proxy.insert(auth, 'config/widget_config', dict(search_type='contract/collection', view='drop_test', priority=100,
            config='<config><drop_test><element name="code"/><element name="name"/>'
            '<element name="entities" title="Entities"><display class="tactic.ui.table.DropElementWdg">'
            '<accepted_drop_type>contract/entity</accepted_drop_type>'
            '<instance_type>contract/entity_in_collection</instance_type>'
            '</display></element></drop_test></config>'))
        notes = [proxy.insert(auth, 'sthpw/note', dict(search_type='contract/entity', search_code='A', search_id=1,
            project_code='one', login='admin', process='publish', note='Parent browser fixture ' + str(index))) for index in range(2)]
        return proxy, auth, notes

    def test_handler_parent_group_through_xmlrpc(self):
        proxy, auth, notes = self.parent_group_fixture()
        text = (ROOT.parent.parent/'TH/thlib/ui/table/requests.py').read_text(encoding='utf-8')
        functions = {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
        def call(name, values):
            result = proxy.execute_python_script(auth, '', dict(code=functions[name] + '\nreturn ' + name + '(**kwargs["values"])', values=values))['info']
            return json.loads(result) if isinstance(result, str) else result
        cell = call('read_parent_cells', dict(search_keys=[notes[0]['__search_key__']]))[notes[0]['__search_key__']]
        self.assertEqual(cell['parent']['code'], 'A')
        args = dict(search_key=notes[0]['__search_key__'], view='parent_test', column='parent', source_id=str(notes[0]['id']))
        prepared = call('edit_parent_group', args)
        candidates = call('edit_parent_group', dict(args, action='candidates', parent_type='contract/entity', expected_revision=prepared['expectedRevision']))
        target = next(row for row in candidates['rows'] if row['code'] == 'B')
        self.assertEqual(call('edit_parent_group', dict(args, action='save', expected_revision=prepared['expectedRevision'],
            parent_key=target['searchKey'], parent_revision=target['revision']))['state'], 'saved')
        text = (ROOT.parent.parent/'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        query = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        result = proxy.execute_python_script(auth, '', dict(code=ast.get_source_segment(text, query) +
            '\nreturn query_table_layout("sthpw/note",view="parent_test",project_code="one",search_keys=kwargs["keys"])', keys=[notes[0]['__search_key__']]))['info']
        result = json.loads(result) if isinstance(result, str) else result
        cell = result['rows'][notes[0]['__search_key__']]['parent']
        self.assertFalse(cell['error'], cell)
        self.assertEqual(cell['parent']['code'], 'B')
        self.assertTrue(cell['parentEditable'])

    def publish_fixture(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')
        with self.store.connection('one', write=True) as database:
            database.execute('ALTER TABLE entity ADD COLUMN attachment text')
        for view, elements in (
            ('publish_test', '<element name="code"/><element name="name"/>'
                '<element name="publish"><display class="PublishTableElement"><multi_publish>true</multi_publish></display></element>'
                '<element name="general"><display class="tactic.ui.table.GeneralPublishElementWdg"><view>review_publish</view></display></element>'),
            ('review_publish', '<element name="name"><display class="pyasm.widget.TextWdg"/></element>'
                '<element name="attachment"><display class="tactic.ui.widget.SimpleUploadWdg"><context>publish/reference</context></display>'
                '<action class="pyasm.command.UploadAction"/></element>'),
            ('multi_publish', '<element name="name"><display class="pyasm.widget.TextWdg"/></element>')):
            proxy.insert(auth, 'config/widget_config', dict(search_type='contract/entity', view=view, priority=100,
                config='<config><'+view+'>'+elements+'</'+view+'></config>'))
        return proxy, auth

    def test_handler_publish_fallback_through_xmlrpc(self):
        proxy, auth = self.publish_fixture()
        text = (ROOT.parent.parent/'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        source = ast.get_source_segment(text, function)
        keys = ['contract/entity?project=one&code=A', 'contract/entity?project=one&code=B']
        source += '''
from unittest.mock import patch
from pyasm.widget import PublishTableElement, ThumbWdg
from tactic.ui.table import GeneralPublishElementWdg
with patch.object(PublishTableElement, 'get_cell_value', None), patch.object(GeneralPublishElementWdg, 'get_cell_value', None):
    return query_table_layout('contract/entity', search_keys=kwargs['keys'], view='publish_test', project_code='one')
'''
        result = proxy.execute_python_script(auth, '', dict(code=source, keys=keys))['info']
        result = json.loads(result) if isinstance(result, str) else result
        for key in keys:
            row = result['rows'][key]
            for name in ('publish', 'general'):
                self.assertFalse(row[name]['error'], row[name])
                self.assertEqual(row[name]['targetSearchKey'], key)
                self.assertEqual(row[name]['projectCode'], 'one')
            self.assertEqual(row['publish']['publishView'], 'publish')
            self.assertEqual(row['general']['publishView'], 'review_publish')
            self.assertIn('preview', row['general'])

    def test_table_publish_in_chromium(self):
        proxy, auth = self.publish_fixture()
        result = subprocess.run([shutil.which('node'), str(ROOT/'frontend/tests/table_publish.mjs'), self.url],
            cwd=ROOT/'frontend', env=os.environ.copy(), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(proxy.get_by_search_key(auth, 'contract/entity?project=one&code=A')['name'], 'Published in browser')
        self.assertEqual(proxy.get_by_search_key(auth, 'contract/entity?project=one&code=B')['name'], "O'Reilly")
        snapshots = proxy.query(auth, 'sthpw/snapshot', [['search_code', 'A'], ['context', 'publish/reference']])
        snapshots = ast.literal_eval(snapshots) if isinstance(snapshots, str) else snapshots
        snapshots = [row for row in snapshots if row['version'] > 0]
        self.assertEqual(len(snapshots), 1)

    def test_handler_configured_publish_actions_through_xmlrpc(self):
        from types import SimpleNamespace
        from pyasm.command import UploadAction
        from pyasm.search import Search
        from pyasm.search.search import RequestContext, request_context
        proxy, auth = self.publish_fixture()
        handler = ROOT.parent.parent/'TH'
        self.enterContext(patch.object(sys, 'path', [str(handler), *sys.path]))
        module = importlib.import_module('thlib.side.client.tactic_client_lib.tactic_server_stub')
        client = module.TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('one')
        client.set_ticket(auth['ticket'])
        self.addCleanup(client.server.__exit__, None, None, None)
        key = 'contract/entity?project=one&code=A'
        text = (handler/'thlib/tactic_query.py').read_text(encoding='utf-8')
        query = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_EditWdg')
        result = client.execute_python_script('', kwargs=dict(code=ast.get_source_segment(text, query)+
            '\nreturn query_EditWdg(kwargs["args"], "contract/entity", "one")',
            args=dict(mode='edit', input_prefix='edit', view='review_publish', search_type='contract/entity', search_key=key)))['info']
        definition = json.loads(result) if isinstance(result, str) else result
        text = (handler/'thlib/tactic_widgets.py').read_text(encoding='utf-8')
        cls = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == 'TacticEditWdg')
        function = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_commit_publish')
        scope = {}
        exec(ast.get_source_segment(text, function), scope)
        owner = SimpleNamespace(options_dict=dict(configured_publish=definition['InputWidgets']), input_prefix='edit',
            view='review_publish', get_search_type=lambda:'contract/entity', get_search_key=lambda:key, get_parent_search_key=lambda:None)
        upload = Path(self.temp.name)/'native-publication.txt'
        payload = b'Actual Handler configured publication\x00'
        upload.write_bytes(payload)
        values = dict(name='Published in Handler', attachment=str(upload))
        original = UploadAction.postprocess
        def fail(action):
            original(action)
            raise ValueError('Late native publication failure')
        with patch.object(UploadAction, 'postprocess', fail), self.assertRaises(Fault):
            scope['_commit_publish'](owner, values, client)
        self.assertEqual(proxy.get_by_search_key(auth, key)['name'], 'Первый')
        record = scope['_commit_publish'](owner, values, client)
        self.assertEqual(record['name'], 'Published in Handler')
        self.assertEqual(record['amount'], 0)
        with request_context(RequestContext(self.store, 'admin', 'one')):
            search = Search('sthpw/snapshot')
            search.add_filter('context', 'publish/reference')
            search.add_filter('version', 0, '>')
            snapshots = search.get_sobjects()
            self.assertEqual(len(snapshots), 1)
            file = next(file for file in snapshots[0].get_all_file_objects() if file.get_type() == 'main')
            self.assertEqual(Path(file.get_lib_path()).read_bytes(), payload)

    def test_table_parent_group_in_chromium(self):
        _proxy, _auth, notes = self.parent_group_fixture()
        environment = os.environ.copy()
        result = subprocess.run([shutil.which('node'), str(ROOT/'frontend/tests/table_parent.mjs'), self.url, notes[0]['code']],
            cwd=ROOT/'frontend', env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_handler_dependencies_through_xmlrpc(self):
        proxy, auth, snapshot = self.dependency_fixture()
        text = (ROOT.parent.parent/'TH/thlib/ui/table/requests.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(text).body if isinstance(node,ast.FunctionDef) and node.name=='read_dependency_node')
        code = ast.get_source_segment(text,function)+"\nreturn read_dependency_node(**kwargs['values'])"
        result = proxy.execute_python_script(auth,'',dict(code=code,values=dict(search_key=snapshot['__search_key__'])))['info']
        if isinstance(result,str): result=json.loads(result)
        self.assertEqual(result['version'],snapshot['version'])
        self.assertEqual(result['identity'],snapshot['code'])
        self.assertTrue(any(row['kind']=='missing' for row in result['rows']))
        sequence=next(row for row in result['rows'] if row.get('fileRange'))
        page=proxy.execute_python_script(auth,'',dict(code=code,values=dict(search_key=result['snapshotKey'],
            expected_revision=result['revision'],file_index=sequence['fileIndex'],offset=100,limit=2)))['info']
        if isinstance(page,str): page=json.loads(page)
        self.assertEqual([row['title'] for row in page['rows']],['render.1101.exr','render.1102.exr'])
        self.assertTrue(page['hasNext'])

        text = (ROOT.parent.parent/'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
        query = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
        code = ast.get_source_segment(text, query) + "\nreturn query_table_layout('sthpw/snapshot',view='dependencies_snapshot_test',project_code='admin',search_keys=[kwargs['key']])"
        layout = proxy.execute_python_script(dict(auth,project='admin'), '', dict(code=code,key=snapshot['__search_key__']))['info']
        layout = json.loads(layout) if isinstance(layout,str) else layout
        cell = layout['rows'][snapshot['__search_key__']]['dependency']
        self.assertFalse(cell.get('error'),cell)
        self.assertEqual(cell['projectCode'],'one')

    def test_table_dependencies_in_chromium(self):
        _proxy, _auth, snapshot = self.dependency_fixture()
        environment=os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.browser-cache')
        result=subprocess.run([shutil.which('node'),str(ROOT/'frontend/tests/table_dependencies.mjs'),self.url,snapshot['code']],
            cwd=ROOT/'frontend',env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_snapshot_append_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin')
        proxy.insert(auth, 'config/widget_config', dict(search_type='sthpw/snapshot', view='append_test', priority=100,
            config='<config><append_test><element name="code"/><element name="version"/><element name="append"><display class="pyasm.widget.FileAppendLinkTableElement"/></element><element name="checkout"><display class="tactic.ui.table.CheckoutButtonElementWdg"/></element></append_test></config>'))
        environment = os.environ.copy()
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/table_append.mjs'), self.url],
            cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_table_cells_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin', language='python')
        for letter, url, enabled in (('A', 'https://example.com/a', True), ('B', 'javascript:alert(1)', False)):
            proxy.insert(auth, 'sthpw/login_group', dict(login_group='CELL_' + letter, description=url, is_default=enabled))
        from scripts.table_cells_contract import XML, VIEW, TYPE, PNG
        proxy.upload_file(auth, 'cell preview.png', Binary(PNG))
        proxy.simple_checkin(auth, 'sthpw/login_group?code=CELL_A', 'icon', 'cell preview.png',
            'file', 'Native preview', False, 'icon', True, None, {}, 'upload', False, {}, True, False)
        proxy.execute_cmd(auth, 'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
                          dict(search_key='sthpw/login_group?code=CELL_A', note='Browser discussion', process='publish', files=[]))
        xml = XML[:XML.index('<element name="error"')] + '</cells_native></config>'
        proxy.insert(auth, 'config/widget_config', dict(search_type=TYPE, view=VIEW, config=xml, priority=100))
        proxy.execute_cmd(auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
            dict(search_type_name='contract/browser_task', sobject_pipeline=True, process=['model', 'review']))
        for code in ('INSPECTOR_A', 'INSPECTOR_EMPTY'):
            proxy.insert(auth, 'contract/browser_task', dict(code=code, pipeline_code='admin/browser_task'))
        parent = 'contract/browser_task?project=admin&code=INSPECTOR_A'
        proxy.upload_file(auth, 'task preview.png', Binary(PNG))
        proxy.simple_checkin(auth, parent, 'icon', 'task preview.png',
            'file', 'Task object preview', False, 'icon', True, None, {}, 'upload', False, {}, True, False)
        login_rows = proxy.query(auth, 'sthpw/login', [('login', 'admin')])
        login_rows = ast.literal_eval(login_rows) if isinstance(login_rows, str) else login_rows
        proxy.upload_file(auth, 'avatar.png', Binary(PNG))
        proxy.simple_checkin(auth, login_rows[0]['__search_key__'], 'icon', 'avatar.png',
            'file', 'Participant avatar', False, 'icon', True, None, {}, 'upload', False, {}, True, False)
        proxy.create_task(auth, parent, 'model')
        secondary = proxy.create_task(auth, parent, 'model', 'secondary')
        secondary = ast.literal_eval(secondary) if isinstance(secondary, str) else secondary
        proxy.execute_python_script(auth, '', dict(code="from pyasm.security import Login\nLogin.create('weekly_user', 'weekly-test-password')\nreturn True"))
        week_parent = proxy.insert(auth, 'contract/browser_task', dict(code='WEEK_BROWSER', pipeline_code='admin/browser_task'))
        week_parent = ast.literal_eval(week_parent) if isinstance(week_parent, str) else week_parent
        hour_command = 'tactic.ui.table.work_hours.WorkHoursCmd'
        for day, login, amount, category, text in (('2030-01-07', 'admin', 1, 'regular', 'Weekly regular'),
                ('2030-01-13', 'weekly_user', 2, 'overtime', 'Weekly overtime')):
            task = proxy.create_task(auth, week_parent['__search_key__'], 'model', login)
            task = ast.literal_eval(task) if isinstance(task, str) else task
            scope = dict(search_key=week_parent['__search_key__'], process='model', task_key=task['__search_key__'])
            result = proxy.execute_cmd(auth, hour_command, scope)['info']
            proxy.execute_cmd(auth, hour_command, dict(scope, action='create', expected_revision=result['revision'],
                data=dict(day=day, hours=amount, category=category, login=login, description=text)))
        proxy.execute_cmd(auth, 'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
            dict(search_key=parent, note='Primary task discussion', process='model', files=[]))
        proxy.execute_cmd(auth, 'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
            dict(search_key=secondary['__search_key__'], note='Secondary task discussion', process='model', files=[]))
        proxy.insert(auth, 'config/widget_config', dict(search_type='contract/browser_task', view='table', priority=100,
            config='<config><table><element name="code"/><element name="tasks"><display class="tactic.ui.table.TaskElementWdg"><show_filler_tasks>true</show_filler_tasks></display></element></table></config>'))
        proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='project_view', priority=100,
            config='<config><project_view><element name="cells" title="Native cells"><display class="LinkWdg"><search_type>' + TYPE + '</search_type><view>' + VIEW + '</view></display></element><element name="task_cells" title="Task cells"><display class="LinkWdg"><search_type>contract/browser_task</search_type></display></element></project_view></config>'))
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='browser_related', project_title='Related browser tasks'))
        related_auth = dict(auth, project='browser_related')
        for kind in ('browser_progress', 'browser_child'):
            proxy.execute_cmd(related_auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
                search_type_name='contract/'+kind, sobject_pipeline=True, process=['model'],
                column_name=['owner_code'] if kind == 'browser_child' else [], data_type=['varchar'] if kind == 'browser_child' else []))
        proxy.insert(related_auth, 'sthpw/pipeline', dict(code='browser_related/PROGRESS', project_code='browser_related',
            pipeline='<pipeline><process name="model" type="manual"/><process name="linked" type="progress"/><process name="empty" type="progress"/></pipeline>'))
        schema = ast.literal_eval(proxy.query(related_auth, 'sthpw/schema', [['code', 'browser_related']]))[0]
        proxy.update(related_auth, schema['__search_key__'], dict(schema=schema['schema'].replace('</schema>',
            '<connect from="contract/browser_child" to="contract/browser_progress" relationship="code" from_col="owner_code" type="hierarchy"/></schema>')))
        definition = ast.literal_eval(proxy.query(related_auth, 'config/process', [['pipeline_code', 'browser_related/PROGRESS'], ['process', 'linked']]))[0]
        proxy.update(related_auth, definition['__search_key__'], dict(workflow='{"search_type":"contract/browser_child"}'))
        proxy.insert(related_auth, 'contract/browser_progress', dict(code='BROWSER_PROGRESS', pipeline_code='browser_related/PROGRESS'))
        child = proxy.insert(related_auth, 'contract/browser_child', dict(code='BROWSER_CHILD', name='Related child', owner_code='BROWSER_PROGRESS', pipeline_code='browser_related/browser_child'))
        child = ast.literal_eval(child) if isinstance(child, str) else child
        proxy.create_task(related_auth, child['__search_key__'], 'model')
        proxy.insert(related_auth, 'config/widget_config', dict(search_type='contract/browser_progress', view='table', priority=100,
            config='<config><table><element name="code"/><element name="tasks"><display class="tactic.ui.table.TaskElementWdg"><show_filler_tasks>true</show_filler_tasks></display></element></table></config>'))
        proxy.insert(related_auth, 'config/widget_config', dict(search_type='SideBarWdg', view='project_view', priority=100,
            config='<config><project_view><element name="progress" title="Progress tasks"><display class="LinkWdg"><search_type>contract/browser_progress</search_type></display></element></project_view></config>'))
        environment = os.environ.copy(); environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/table_cells.mjs'), self.url,
            str(ROOT / '.screenshots/table-cells.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_security_users_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='sthpw', language='python')
        proxy.insert(auth, 'sthpw/login_group', dict(login_group='ui_team', description='People in the UI test'))
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/security_users.mjs'), self.url,
            str(ROOT / '.screenshots/security-users.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        user = ast.literal_eval(proxy.query(auth, 'sthpw/login', [['login', 'ui_user']], ['login', 'display_name', 's_status']))[0]
        self.assertEqual(user['display_name'], 'Test User'); self.assertFalse(user['s_status'])
        self.assertTrue(proxy.get_ticket('ui_user', 'browser-user-password'))

    def test_sidebar_editor_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/sidebar_editor.mjs'), self.url,
            str(ROOT / '.screenshots/sidebar-editor.png')], cwd=ROOT / 'frontend', env=environment,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_search_suggestions_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin', language='python')
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='search_browser', project_title='Search examples'))
        auth['project'] = 'search_browser'
        kind = 'contract/browser_suggestions'
        proxy.execute_cmd(auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(search_type_name=kind))
        for code, name, description, keywords, status in [('A', 'Blue', 'First\ndescription', 'sky-blue', ''),
                ('AB', 'Blue Extra', 'Second description', 'azure', ''), ('D', 'Blue', 'First\ndescription', 'sky-blue', ''),
                ('RETIRED', 'Hidden', '', '', 'retired')]:
            proxy.insert(auth, kind, dict(code=code, name=name, description=description, keywords=keywords, s_status=status))
        for index in range(25):
            proxy.insert(auth, kind, dict(code='ITEM%02d' % index, name='Shelf item%02d' % index))
        proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='project_view', priority=100,
            config='<config><project_view><element name="suggestions" title="Search examples"><display class="LinkWdg"><search_type>' + kind + '</search_type></display></element><element name="projects" title="Projects"><display class="LinkWdg"><search_type>sthpw/project</search_type></display></element></project_view></config>'))
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/search_suggestions.mjs'), self.url,
                                 str(ROOT / '.screenshots/search-suggestions.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_process_visibility_in_chromium(self):
        environment = os.environ.copy()
        environment["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / ".browser-cache")
        result = subprocess.run(
            [
                shutil.which("node"),
                str(ROOT / "frontend/tests/process_visibility.mjs"),
                self.url,
            ],
            cwd=ROOT / "frontend",
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_search_library_in_chromium(self):
        proxy = self.proxy()
        auth = dict(
            ticket=proxy.get_ticket("admin", "private-test-password"),
            project="admin",
            language="python",
        )
        proxy.execute_cmd(
            auth,
            "tactic.command.CreateProjectCmd",
            dict(project_code="library_browser", project_title="Saved searches"),
        )
        auth["project"] = "library_browser"
        kind = "library_browser/items"
        proxy.execute_cmd(
            auth,
            "tactic.core.schema_commands.SearchTypeCreatorCmd",
            dict(search_type_name=kind, asset_title="Library items"),
        )
        items = []
        for code, title in [("ONE", "One object"), ("TWO", "Two object")]:
            item = proxy.insert(auth, kind, dict(code=code, name=title))
            items.append(ast.literal_eval(item) if isinstance(item, str) else item)
        proxy.insert(
            auth,
            "sthpw/task",
            dict(
                project_code="library_browser",
                process="model",
                context="model",
                assigned="admin",
                status="Ready",
            ),
            {},
            items[0]["__search_key__"],
        )
        proxy.insert(
            auth,
            "config/widget_config",
            dict(
                search_type="SideBarWdg",
                view="project_view",
                priority=100,
                config='<config><project_view><element name="items" title="Library items"><display class="LinkWdg"><search_type>'
                + kind
                + "</search_type></display></element></project_view></config>",
            ),
        )
        environment = dict(
            os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / ".browser-cache")
        )
        result = subprocess.run(
            [
                shutil.which("node"),
                str(ROOT / "frontend/tests/search_library.mjs"),
                self.url,
            ],
            cwd=ROOT / "frontend",
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tag_cloud_in_chromium(self):
        proxy = self.proxy()
        auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='admin', language='python')
        proxy.execute_cmd(auth, 'tactic.command.CreateProjectCmd', dict(project_code='tag_browser', project_title='Tag cloud examples'))
        auth['project'] = 'tag_browser'
        kind = 'contract/browser_tags'
        proxy.execute_cmd(auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(search_type_name=kind))
        for code, keywords, status in [('A', 'blue,Blue; red Синий', ''), ('B', 'green red', ''),
                ('C', ' '.join('token%04d' % index for index in range(1500)), ''), ('D', 'hidden', 'retired')]:
            proxy.insert(auth, kind, dict(code=code, name=code, keywords=keywords, s_status=status))
        sidebar = proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='project_view', priority=100,
            config='<config><project_view><element name="tags" title="Tag examples"><display class="LinkWdg"><search_type>' + kind + '</search_type></display></element><element name="projects" title="Projects"><display class="LinkWdg"><search_type>sthpw/project</search_type></display></element></project_view></config>'))
        sidebar = ast.literal_eval(sidebar) if isinstance(sidebar, str) else sidebar
        self.addCleanup(proxy.delete_sobject, auth, sidebar['__search_key__'])
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/tag_cloud.mjs'), self.url,
                                 str(ROOT / '.screenshots/tag-cloud.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_workspace_tabs_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/workspace_tabs.mjs'), self.url,
                                 str(ROOT / '.screenshots/workspace-tabs.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_drop_plate_commit_queue_in_chromium(self):
        from tactic_stream.server.api import Api
        api = Api(self.store); api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin','private-test-password'), project='one')
        kind = 'one/queue_assets'
        api.dispatch('execute_cmd',(auth,'tactic.core.schema_commands.SearchTypeCreatorCmd',dict(search_type_name=kind,asset_title='Queue assets')))
        owner = api.dispatch('insert',(auth,kind,dict(code='QUEUE001',name='Queue asset',description='Queue workflow')))
        for versionless, directory in ((False,'{project.code}/queue/{sobject.code}/v{snapshot.version}'),(True,'{project.code}/queue/{sobject.code}/latest')):
            api.dispatch('insert',(auth,'config/naming',dict(search_type=kind,snapshot_type='file',context='publish/*',latest_versionless=versionless,dir_naming=directory,file_naming='{basefile}.{ext}')))
        output = ROOT / '.screenshots/checkin-current'; output.mkdir(exist_ok=True)
        environment = dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'))
        result = subprocess.run([shutil.which('node'),str(ROOT / 'frontend/tests/checkin.mjs'),self.url,str(output),owner['__search_key__']],
                                cwd=ROOT / 'frontend',env=environment,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
        snapshots = api.dispatch('query',(auth,'sthpw/snapshot'),dict(filters=[('search_type',kind + '?project=one'),('search_code','QUEUE001'),('version','>=',1)]))
        self.assertGreaterEqual(len(snapshots),2)
        self.assertTrue(any(row['description'] == 'Prepared in Commit Queue' for row in snapshots))
        self.assertEqual(len([row for row in snapshots if row['context']=='publish/unknown']),1,
                         'The lost response must leave exactly one published snapshot')

    def test_object_context_menu_in_chromium(self):
        from tactic_stream.server.api import Api
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        kind = 'one/menu_assets'
        original_configs = api.dispatch('query', (auth, 'config/widget_config'))
        def restore_configs():
            originals = {row['id']: row for row in original_configs}
            for row in api.dispatch('query', (auth, 'config/widget_config')):
                if row['id'] not in originals:
                    api.dispatch('delete_sobject', (auth, row['__search_key__']))
                elif row.get('config') != originals[row['id']].get('config'):
                    api.dispatch('update', (auth, row['__search_key__'], dict(config=originals[row['id']]['config'])))
        self.addCleanup(restore_configs)
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                                    dict(search_type_name=kind, asset_title='Menu assets')))
        record = api.dispatch('insert', (auth, kind, dict(name='Menu object')))
        api.dispatch('insert', (auth, kind, dict(name='Menu sibling')))
        for latest in (False,True):
            api.dispatch('insert',(auth,'config/naming',dict(search_type=kind,snapshot_type='file',context='menu_clipboard',
                latest_versionless=latest,dir_naming='{project.code}/menu/{sobject.code}/{snapshot.context}/' + ('latest' if latest else 'v{snapshot.version}'),file_naming='{basefile}.{ext}')))
        from PIL import Image
        image = Path(self.temp.name) / 'menu-preview.png'
        Image.new('RGB', (64, 64), (50, 100, 150)).save(image)
        # Keep valid instance edges in this ordinary project; the shared schema
        # also deliberately registers broken edges for negative kernel tests.
        with self.store.connection(write=True) as db:
            schema = db.execute('SELECT id, "schema" FROM "schema" WHERE project_code=\'one\'').fetchone()
            xml = ET.fromstring(schema['schema'])
            for connection in list(xml):
                if connection.tag == 'connect' and connection.get('from', '').startswith(('contract/', 'sthpw/contract_')) and connection.get('from') not in ('contract/collection', 'contract/entity_in_collection'):
                    xml.remove(connection)
            db.execute('UPDATE "schema" SET "schema"=? WHERE id=?', (ET.tostring(xml, encoding='unicode'), schema['id']))
        def restore_schema():
            with self.store.connection(write=True) as db:
                db.execute('UPDATE "schema" SET "schema"=? WHERE id=?', (schema['schema'], schema['id']))
        self.addCleanup(restore_schema)
        environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'))
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/object_menu.mjs'), self.url,
                                 str(ROOT / '.screenshots/object-menu.png'), record['__search_key__'], str(image)], cwd=ROOT / 'frontend', env=environment,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        def query(kind, filters):
            return api.dispatch('query', (auth, kind), dict(filters=filters))
        snapshots = query('sthpw/snapshot', [('context', 'menu_publish'), ('version', '>=', 0)])
        self.assertEqual(len(snapshots), 2, snapshots)
        revised = next(snapshot for snapshot in snapshots if snapshot['revision'] >= 1)
        files = query('sthpw/file', [('snapshot_code', revised['code']), ('type', 'main')])
        self.assertEqual(len(files), 1)
        self.assertEqual((Path(files[0]['checkin_dir']) / files[0]['file_name']).read_text(), 'native menu revision')
        groups = query('sthpw/snapshot', [('context', 'menu_group'), ('version', '>=', 0)])
        self.assertEqual(len(groups), 1, groups)
        files = query('sthpw/file', [('snapshot_code', groups[0]['code']), ('type', 'main')])
        self.assertEqual(len(files), 2, files)
        self.assertEqual({(Path(file['checkin_dir']) / file['file_name']).read_text() for file in files}, {'group A', 'group B'})
        links = query('contract/entity_in_collection', [('collection_code', 'G1'), ('entity_code', 'A')])
        self.assertEqual(links, [], 'Unlink removes the native instances')
        self.assertTrue(query('contract/entity', [('code', 'A')]), 'Unlink keeps the related object')
        ingested = query('contract/collection', [('name', 'BrowserIngest')])
        self.assertEqual(len(ingested), 2, 'Duplicate creates a second child; update and skip do not')
        ingested_snapshots = query('sthpw/snapshot', [('search_type', 'contract/collection?project=one'), ('search_code', [row['code'] for row in ingested]), ('version', '>=', 0)])
        self.assertEqual(len(ingested_snapshots), 3, 'Initial ingest, update and explicit duplicate each produce a version')
        self.assertFalse(query('contract/collection', [('name', 'Ignored')]))
        self.assertFalse(query('config/ingest_rule', [('title', 'Browser ingest rule')]))

    def test_advanced_duplicate_native_relations_messages_files_and_rollback(self):
        from tactic_stream.server.api import Api
        from pyasm.checkin import FileCheckin
        from pyasm.common import UserException
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        original_object = api.dispatch('insert', (auth, 'contract/entity', dict(code='DUP_NATIVE', name='Native duplicate source', amount=0)))
        source = original_object['__search_key__']
        api.dispatch('insert', (auth, 'contract/child', dict(code='DUP_NATIVE_CHILD', entity_code=original_object['code'], alternate_entity_code=original_object['code'], entity_id=original_object['id'])))
        api.dispatch('insert', (auth, 'contract/entity_in_collection', dict(entity_code=original_object['code'], collection_code='G1')))
        command = 'tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd'
        def call(action, **values):
            return api.dispatch('execute_cmd', (auth, command, dict(action=action, search_key=source, **values)))['info']
        def file(key, name, context, payload=b'duplicate content'):
            api.dispatch('upload_file', (auth, name, Binary(payload)))
            return api.dispatch('simple_checkin', (auth, key, context, name), dict(mode='uploaded', process='publish', create_icon=False))
        file(source, 'duplicate-root.txt', 'publish/root')
        other = api.dispatch('insert', (auth, 'contract/entity', dict(code='DUP_OTHER', name='Other snapshot owner')))
        file(other['__search_key__'], 'other-duplicate-root.txt', 'publish/root')
        file(other['__search_key__'], 'other-duplicate-root.txt', 'publish/root')
        task = api.dispatch('create_task', (auth, source), dict(process='publish'))
        root_note = api.dispatch('create_note', (auth, source, 'Process message'), dict(process='publish'))
        reply = api.dispatch('create_note', (auth, source, 'Thread reply'), dict(process='publish'))
        api.dispatch('update', (auth, reply['__search_key__'], dict(parent_id=root_note['id'])))
        task_note = api.dispatch('create_note', (auth, task['__search_key__'], 'Task message'), dict(process='publish'))
        file(root_note['__search_key__'], 'duplicate-note.txt', 'attachment')
        file(task_note['__search_key__'], 'duplicate-task-note.txt', 'attachment')
        file(task['__search_key__'], 'duplicate-task.txt', 'attachment')
        loaded = call('analyze')
        analysis = loaded['analysis']
        self.assertNotIn('code', [field['name'] for field in analysis['fields']])
        processes = {row['name']: row for row in analysis['processes']}
        self.assertGreaterEqual(processes['publish']['processMessageCount'], 2)
        self.assertGreaterEqual(processes['publish']['taskMessageCount'], 1)
        self.assertGreaterEqual(processes['publish']['taskAttachmentCount'], 2)
        relations = {row['key']: row['mode'] for row in analysis['relations']}
        child = next(row for row in analysis['relations'] if row['searchType'] == 'contract/child' and row['path'] == 'alternate')
        relations[child['key']] = 'copy'
        options = dict(fields={'name': 'Deep duplicate'}, relations=relations,
                       processes={'publish': dict(copySnapshots=True, copyTaskAttachments=True, copyProcessAttachments=True)})
        result = call('duplicate', options=options, revision=loaded['revision'])['result']
        self.assertEqual(result['snapshotsCopied'], 1)
        self.assertEqual(result['tasksCopied'], 1)
        self.assertEqual(result['processMessagesCopied'], 2)
        self.assertEqual(result['taskMessagesCopied'], 1)
        self.assertEqual(result['attachmentFilesCopied'], 3)
        self.assertEqual(result['childrenCopied'], child['count'])
        clone = api.dispatch('get_by_search_key', (auth, result['searchKey']))
        self.assertEqual(clone['name'], 'Deep duplicate')
        cloned_children = api.dispatch('query', (auth, 'contract/child'), dict(filters=[['alternate_entity_code', clone['code']]]))
        self.assertEqual(len(cloned_children), child['count'])
        links = api.dispatch('query', (auth, 'contract/entity_in_collection'), dict(filters=[['entity_code', clone['code']]]))
        self.assertEqual({row['collection_code'] for row in links}, {'G1'})
        originals = api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[['search_type', 'contract/entity?project=one'], ['search_code', original_object['code']]]))
        copies = api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[['search_type', 'contract/entity?project=one'], ['search_code', clone['code']]]))
        self.assertTrue(copies)
        self.assertTrue({row['checkin_dir'] for row in originals}.isdisjoint({row['checkin_dir'] for row in copies}), 'Duplicate owns independent files')
        for row in originals + copies:
            self.assertEqual((Path(row['checkin_dir']) / row['file_name']).read_bytes(), b'duplicate content')
        repository = Path(self.store.data_dir) / 'assets'
        before = {path: path.read_bytes() for path in repository.rglob('*') if path.is_file()}
        loaded = call('analyze')
        options['fields']['name'] = 'Rollback duplicate'
        original = FileCheckin.handle_system_commands
        def fail(checkin, *args):
            original(checkin, *args)
            raise ValueError('Late duplicate failure')
        with patch.object(FileCheckin, 'handle_system_commands', fail), self.assertRaisesRegex(ValueError, 'Late duplicate failure'):
            call('duplicate', options=options, revision=loaded['revision'])
        self.assertFalse(api.dispatch('query', (auth, 'contract/entity'), dict(filters=[['name', 'Rollback duplicate']])))
        self.assertEqual({path: path.read_bytes() for path in repository.rglob('*') if path.is_file()}, before)
        missing = Path(originals[0]['checkin_dir']) / originals[0]['file_name']
        content = missing.read_bytes()
        try:
            missing.unlink()
            with self.assertRaisesRegex(ValueError, 'Snapshot file is missing'):
                call('duplicate', options=options, revision=loaded['revision'])
            self.assertFalse(api.dispatch('query', (auth, 'contract/entity'), dict(filters=[['name', 'Rollback duplicate']])))
        finally:
            missing.write_bytes(content)
        with self.assertRaisesRegex(ValueError, 'editable'):
            call('duplicate', options=dict(options, fields={'id': 42}), revision=loaded['revision'])
        api.dispatch('update', (auth, source, {'name': 'Changed source'}))
        with self.assertRaisesRegex(UserException, 'Source content changed'):
            call('duplicate', options=options, revision=loaded['revision'])
        auth['project'] = 'two'
        with self.assertRaises(ValueError):
            call('analyze')

    def test_advanced_duplicate_wizard_in_chromium(self):
        from tactic_stream.server.api import Api
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        source = api.dispatch('insert', (auth, 'contract/entity', dict(code='DUP_BROWSER', name='Duplicate source', amount=0)))
        key = source['__search_key__']
        api.dispatch('insert', (auth, 'contract/child', dict(code='DUP_BROWSER_CHILD', alternate_entity_code=source['code'])))
        api.dispatch('upload_file', (auth, 'browser-duplicate.txt', Binary(b'browser duplicate file')))
        api.dispatch('simple_checkin', (auth, key, 'publish/browser'), dict(file_path='browser-duplicate.txt', mode='uploaded', process='publish', create_icon=False))
        task = api.dispatch('create_task', (auth, key), dict(process='publish'))
        note = api.dispatch('create_note', (auth, key, 'Browser process message'), dict(process='publish'))
        api.dispatch('create_note', (auth, task['__search_key__'], 'Browser task message'), dict(process='publish'))
        api.dispatch('upload_file', (auth, 'browser-note.txt', Binary(b'browser note attachment')))
        api.dispatch('simple_checkin', (auth, note['__search_key__'], 'attachment', 'browser-note.txt'), dict(mode='uploaded', process='publish', create_icon=False))
        environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'))
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/duplicate_sobject.mjs'), self.url,
                                 str(ROOT / '.screenshots/duplicate'), key], cwd=ROOT / 'frontend', env=environment,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        clones = api.dispatch('query', (auth, 'contract/entity'), dict(filters=[['name', 'Browser deep duplicate']]))
        self.assertEqual(len(clones), 1)
        clone = clones[0]
        self.assertTrue(api.dispatch('query', (auth, 'contract/child'), dict(filters=[['alternate_entity_code', clone['code']]])))
        self.assertTrue(api.dispatch('query', (auth, 'sthpw/task'), dict(filters=[['search_code', clone['code']], ['search_type', 'contract/entity?project=one']])))
        messages = api.dispatch('query', (auth, 'sthpw/note'), dict(filters=[['search_code', clone['code']], ['search_type', 'contract/entity?project=one']]))
        self.assertIn('Browser process message', [message['note'] for message in messages])

    def test_advanced_duplicate_self_hierarchy_and_parent_omission(self):
        from tactic_stream.server.api import Api
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        kind = 'one/duplicate_hierarchy'
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(search_type_name=kind)))
        api.dispatch('execute_cmd', (auth, 'tactic.ui.tools.SchemaConnectorCbk', dict(left_search_type=kind, left='parent_code', right_search_type=kind, right='code')))
        schema = api.dispatch('query', (auth, 'sthpw/schema'), dict(filters=[['code','one']]))[0]
        xml = ET.fromstring(schema['schema'])
        ET.SubElement(xml, 'connect', {'from':kind, 'to':kind, 'relationship':'code', 'from_col':'parent_code', 'to_col':'code'})
        api.dispatch('update', (auth, schema['__search_key__'], dict(schema=ET.tostring(xml, encoding='unicode'))))
        self.addCleanup(lambda: api.dispatch('update', (auth, schema['__search_key__'], {'schema':schema['schema']})))
        parent = api.dispatch('insert', (auth, kind, dict(name='Parent')))
        source = api.dispatch('insert', (auth, kind, dict(name='Source', parent_code=parent['code'])))
        child = api.dispatch('insert', (auth, kind, dict(name='Child', parent_code=source['code'])))
        grandchild = api.dispatch('insert', (auth, kind, dict(name='Grandchild', parent_code=child['code'])))
        command = 'tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd'
        def call(action, **values):
            return api.dispatch('execute_cmd', (auth, command, dict(action=action, search_key=source['__search_key__'], **values)))['info']
        loaded = call('analyze')
        relations = {row['direction']: row for row in loaded['analysis']['relations'] if row['searchType'] == kind}
        self.assertEqual(set(relations), {'parent', 'children'})
        self.assertEqual(relations['parent']['items'][0]['searchKey'], parent['__search_key__'])
        self.assertEqual(relations['children']['items'][0]['searchKey'], child['__search_key__'])
        choices = {relations['parent']['key']: 'link', relations['children']['key']: 'copy'}
        result = call('duplicate', revision=loaded['revision'], options=dict(fields={'name':'Tree copy'}, relations=choices, processes={}))['result']
        clone = api.dispatch('get_by_search_key', (auth, result['searchKey']))
        self.assertEqual(clone['parent_code'], parent['code'])
        children = api.dispatch('query', (auth, kind), dict(filters=[['parent_code', clone['code']]]))
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]['name'], 'Child')
        self.assertEqual(api.dispatch('get_by_search_key', (auth, grandchild['__search_key__']))['parent_code'], child['code'])
        choices[relations['parent']['key']] = 'none'
        choices[relations['children']['key']] = 'none'
        detached = call('duplicate', revision=loaded['revision'], options=dict(fields={}, relations=choices, processes={}))['result']
        self.assertIsNone(api.dispatch('get_by_search_key', (auth, detached['searchKey']))['parent_code'])

    def test_related_ingest_native_upload_conflicts_and_rollback(self):
        from tactic_stream.server.api import Api
        from pyasm.checkin import FileCheckin
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        command = 'tactic.command.related_ingest_cmd.RelatedIngestCmd'
        parent = 'contract/entity?project=one&code=A'
        def call(action, **values):
            return api.dispatch('execute_cmd', (auth, command, dict(action=action, parent_key=parent, search_type='contract/collection', **values)))['info']
        def upload(name, payload=b'relation ingest'):
            api.dispatch('upload_file', (auth, name, Binary(payload)))
        rules = call('rules')['rules']
        self.assertEqual(rules[0]['options']['column'], 'name')
        scan = call('scan', filenames=['NativeIngest.txt', 'Ignored.tmp'], options=dict(ignore='.tmp'))['files']
        self.assertEqual(scan[0]['name'], 'NativeIngest')
        self.assertFalse(scan[1]['accepted'])
        upload('NativeIngest.txt')
        result = call('checkin', filenames=['NativeIngest.txt'])
        child = result['search_key']
        rows = api.dispatch('query', (auth, 'contract/entity_in_collection'), dict(filters=[['entity_code', 'A'], ['collection_code', child.split('code=')[1]]]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['snapshot']['process'], 'publish')
        self.assertTrue(result['snapshot']['context'].startswith('publish'))
        scan = call('scan', filenames=['NativeIngest.txt'])['files'][0]
        self.assertEqual(scan['matches'], [child])
        self.assertTrue(scan['conflict'])
        upload('NativeIngest.txt', b'updated')
        with self.assertRaisesRegex(ValueError, 'Matching items changed'):
            call('checkin', filenames=['NativeIngest.txt'])
        updated = call('checkin', filenames=['NativeIngest.txt'], decision='update', search_key=child)
        self.assertEqual(updated['search_key'], child)
        upload('NativeIngest.txt')
        self.assertTrue(call('checkin', filenames=['NativeIngest.txt'], decision='skip')['skipped'])
        upload('NativeIngest.txt')
        duplicate = call('checkin', filenames=['NativeIngest.txt'], decision='duplicates')
        self.assertNotEqual(duplicate['search_key'], child)
        upload('NativeIngest.txt')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            call('checkin', filenames=['NativeIngest.txt'], decision='update', search_key=child)
        upload('NativeRollback.txt')
        original = FileCheckin.handle_system_commands
        paths = []
        def fail(checkin, *args):
            original(checkin, *args)
            paths.extend(Path(checkin.snapshot.get_lib_dir(file_type=file.get_value('type'), file_object=file)) / file.get_full_file_name() for file in checkin.file_objects)
            raise ValueError('late relation ingest failure')
        with patch.object(FileCheckin, 'handle_system_commands', fail):
            with self.assertRaisesRegex(ValueError, 'late relation ingest failure'):
                call('checkin', filenames=['NativeRollback.txt'])
        self.assertFalse(api.dispatch('query', (auth, 'contract/collection'), dict(filters=[['name', 'NativeRollback']])))
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths), paths)
        from tactic.command.sobject_link_cmd import SObjectLinkCmd
        repository = Path(self.store.data_dir) / 'assets'
        before_files = {file for file in repository.rglob('*') if file.is_file()}
        upload('LinkRollback.txt')
        with patch.object(SObjectLinkCmd, 'execute', side_effect=ValueError('late link failure')):
            with self.assertRaisesRegex(ValueError, 'late link failure'):
                call('checkin', filenames=['LinkRollback.txt'])
        self.assertFalse(api.dispatch('query', (auth, 'contract/collection'), dict(filters=[['name', 'LinkRollback']])))
        self.assertFalse(api.dispatch('query', (auth, 'sthpw/snapshot'), dict(filters=[['context', 'publish/LinkRollback.txt']])))
        self.assertEqual({file for file in repository.rglob('*') if file.is_file()}, before_files, 'Late linking failure rolls back repository files too')
        for path, column, expected in [('', 'entity_code', 'A'), ('alternate', 'alternate_entity_code', 'A'), ('by_id', 'entity_id', 1)]:
            filename = 'NativeChild' + (path or 'main') + '.txt'
            upload(filename)
            child_result = api.dispatch('execute_cmd', (auth, command, dict(action='checkin', parent_key=parent,
                search_type='contract/child', path=path, filenames=[filename], options=dict(extraData={column: 'B' if column != 'entity_id' else 2}))))['info']
            child_row = api.dispatch('get_by_search_key', (auth, child_result['search_key']))
            self.assertEqual(child_row[column], expected, 'Exact branch overrides a foreign parent before naming/check-in')
        upload('Scripted_publish.txt')
        script = api.dispatch('insert', (auth, 'config/custom_script', dict(folder='ingest_test', title='accept', language='python', script="""
assert input['parent'].get_code() == 'A'
assert input['path'].endswith('Scripted_publish.txt')
input['sobject'].set_value('name', 'ScriptedByHook')
input['snapshot'].set_value('context', 'script_context')
return True
""")))
        scripted = call('checkin', filenames=['Scripted_publish.txt'], options=dict(usePattern=True,
            pattern='{sobject.name}_{snapshot.context}.txt', processScript='ingest_test/accept'))
        scripted_row = api.dispatch('get_by_search_key', (auth, scripted['search_key']))
        self.assertEqual(scripted_row['name'], 'ScriptedByHook')
        self.assertTrue(scripted['snapshot']['context'].startswith('script_context'))
        api.dispatch('update', (auth, script['__search_key__'], dict(script="""
server.insert('contract/collection', {'name': 'RejectedSideEffect'})
return False
""")))
        upload('Rejected.txt')
        with self.assertRaisesRegex(Exception, 'Rejected by validation script'):
            call('checkin', filenames=['Rejected.txt'], options=dict(validationScript='ingest_test/accept'))
        self.assertFalse(api.dispatch('query', (auth, 'contract/collection'), dict(filters=[['name', 'RejectedSideEffect']])), 'Rejected hook rolls back its own writes')
        api.dispatch('delete_sobject', (auth, script['__search_key__']))
        unrelated = api.dispatch('insert', (auth, 'contract/collection', dict(name='UnrelatedIngest')))
        self.assertFalse(call('scan', filenames=['UnrelatedIngest.txt'])['files'][0]['conflict'], 'Only this parent relation participates in conflict detection')
        with self.assertRaises(ValueError):
            call('checkin', filenames=['../outside.txt'])
        with self.assertRaises(ValueError):
            call('scan', filenames=['x.txt'], options=dict(extraData={'id': 999}))
        with self.assertRaises(ValueError):
            call('scan', filenames=['999.txt'], options=dict(usePattern=True, pattern='{sobject.id}.txt'))
        auth['project'] = 'two'
        with self.assertRaises(ValueError):
            call('rules')

    def test_uploaded_checkin_revision_and_group_guards(self):
        from tactic_stream.server.api import Api
        from pyasm.checkin import FileCheckin
        from pyasm.checkin.checkin import CheckinException
        api = Api(self.store)
        api.protocol = 'json'
        auth = dict(ticket=api.get_ticket('admin', 'private-test-password'), project='one', language='python')
        key = 'contract/entity?project=one&code=A'
        def upload(name, content):
            api.dispatch('upload_file', (auth, name, Binary(content)))
        def single(**options):
            return api.dispatch('simple_checkin', (auth, key, 'menu_guard', 'guard.txt'),
                                dict(mode='uploaded', create_icon=False, **options))
        upload('guard.txt', b'original')
        snapshot = single()
        files = api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[('snapshot_code', snapshot['code']), ('type', 'main')]))
        path = Path(files[0]['checkin_dir']) / files[0]['file_name']
        upload('guard.txt', b'replacement')
        with self.assertRaises(CheckinException):
            single(version=snapshot['version'])
        self.assertEqual(path.read_bytes(), b'original', 'Ordinary collision never replaces a version')
        original = FileCheckin.handle_system_commands
        interrupted_paths = []
        def interrupted(checkin, files, objects):
            original(checkin, files, objects)
            interrupted_paths.extend(Path(checkin.snapshot.get_lib_dir(file_type=obj.get_type(), file_object=obj)) / obj.get_full_file_name() for obj in objects)
            raise ValueError('Forced check-in interruption')
        with patch.object(FileCheckin, 'handle_system_commands', interrupted), self.assertRaisesRegex(ValueError, 'Forced check-in interruption'):
            single(is_revision=True, version=snapshot['version'])
        self.assertEqual(path.read_bytes(), b'original', 'Revision rollback restores the original file')
        rows = api.dispatch('query', (auth, 'sthpw/snapshot'), dict(filters=[('context', 'menu_guard'), ('version', '>=', 0)]))
        self.assertEqual([row['code'] for row in rows], [snapshot['code']], 'Failed revision rolls back its snapshot')
        command = 'tactic.command.uploaded_checkin_cmd.UploadedCheckinCmd'
        values = dict(search_key=key, context='group_guard', process='publish', files=['first.txt', 'second.txt'])
        upload('first.txt', b'first'); upload('second.txt', b'second')
        with patch.object(FileCheckin, 'handle_system_commands', interrupted), self.assertRaisesRegex(ValueError, 'Forced check-in interruption'):
            api.dispatch('execute_cmd', (auth, command, values))
        self.assertEqual(api.dispatch('query', (auth, 'sthpw/snapshot'), dict(filters=[('context', 'group_guard')])), [])
        self.assertTrue(all(not file.exists() for file in interrupted_paths[1:]), 'Failed group leaves no repository files')
        upload('first.txt', b'first'); upload('second.txt', b'second')
        grouped = api.dispatch('execute_cmd', (auth, command, values))['info']['snapshot']
        self.assertEqual(len(api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[('snapshot_code', grouped['code'])]))), 2)
        upload('preview.png', (ROOT / 'frontend/public/assets/chat_bg_light.png').read_bytes())
        no_preview = api.dispatch('execute_cmd', (auth, command, dict(values, context='no_preview', files=['preview.png'], create_icon=False)))['info']['snapshot']
        self.assertEqual([row['type'] for row in api.dispatch('query', (auth, 'sthpw/file'), dict(filters=[('snapshot_code', no_preview['code'])]))], ['main'])
        with self.assertRaises(ValueError):
            api.dispatch('execute_cmd', (auth, command, dict(values, create_icon='false')))
        for changes in (dict(files=['../escape.txt']), dict(files=['first.txt', 'first.txt']), dict(search_key=key.replace('project=one', 'project=two'))):
            with self.assertRaises((ValueError, LookupError)):
                api.dispatch('execute_cmd', (auth, command, dict(values, **changes)))
        reader = api.dispatch('insert', (auth, 'sthpw/login', dict(login='menu_checkin_reader', password=hash_password('private-test-password'))))
        self.addCleanup(lambda: api.dispatch('delete_sobject', (auth, reader['__search_key__'])))
        guest = dict(ticket=api.get_ticket('menu_checkin_reader', 'private-test-password'), project='one')
        from pyasm.common.errors import SecurityException
        with self.assertRaises(SecurityException):
            api.dispatch('execute_cmd', (guest, command, values))

    def test_lan_http_startup_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/lan_startup.mjs'),
                                 'http://tactic-stream.test/', self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mobile_workspace_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/mobile_workspace.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_support_windows_in_chromium(self):
        environment = os.environ.copy()
        environment.update(
            PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'),
            STREAM_BROWSER_CHANNEL='msedge',
            STREAM_CHECK_LOGIN='admin',
            STREAM_CHECK_PASSWORD='private-test-password',
        )
        for script in ('debug_log.mjs', 'ui_performance.mjs', 'profile_support.mjs'):
            with self.subTest(script=script):
                result = subprocess.run(
                    [shutil.which('node'), str(ROOT / 'frontend/tests' / script), self.url],
                    cwd=ROOT / 'frontend', env=environment, capture_output=True,
                    text=True, encoding='utf-8', errors='replace', timeout=100,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mobile_activity_profile_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/mobile_activity_profile.mjs'), self.url],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=75)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_workspace_layout_in_chromium(self):
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.browser-cache')
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/workspace_layout.mjs'), self.url,
                                 str(ROOT / '.screenshots/workspace-layout-mobile.png')],
                                cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vue_admin_in_real_chromium(self):
        from pyasm.common.config import initialize_config
        initialize_config(self.store.data_dir)
        node = shutil.which('node')
        browser_cache = ROOT / '.browser-cache'
        if not node or not (ROOT / 'frontend/node_modules/playwright').is_dir() or not browser_cache.is_dir():
            self.skipTest('npm ci and Playwright Chromium are required for the browser check')
        with self.store.connection('one', write=True) as db:
            db.executemany('INSERT INTO entity (id,code,name,amount) VALUES (?,?,?,?)',
                           [(1000 + index, f'PAGE_{index:03d}', 'Проверка ' + str(index), index) for index in range(65)])
            db.execute('INSERT INTO entity (id,code,name,amount) VALUES (990,?,?,?)', ('XSS', '<img src=x onerror="window.__xss=1">', 0))
        before = self.store.database_path('one').read_bytes()
        environment = os.environ.copy()
        environment['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_cache)
        try:
            arguments = [node, str(ROOT / 'frontend/tests/admin.mjs'), self.url]
            if environment.get('TACTIC_STREAM_ADMIN_SCREENSHOT'):
                arguments.append(environment['TACTIC_STREAM_ADMIN_SCREENSHOT'])
            result = subprocess.run(arguments,
                                    cwd=ROOT / 'frontend', env=environment, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=75)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.store.database_path('one').read_bytes(), before)
        finally:
            with self.store.connection('one', write=True) as db:
                db.execute('DELETE FROM entity WHERE id>=990')


if __name__ == "__main__":
    unittest.main()
