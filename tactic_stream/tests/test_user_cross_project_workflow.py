"""Ordinary dependency events across two physical project databases."""
import ast
import importlib.util
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

from pyasm.biz import Pipeline, Project
from pyasm.command import Command, Workflow
from pyasm.common.errors import SecurityException
from pyasm.search import Search, DbContainer
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api
from test_project_writes import install_writer, PASSWORD
import test_plugin_installation as plugin_tests
import test_read_parity as read_tests
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


def exercise(store, prefix, password='plugin-test-password', client=None, replay=False, adoption=False):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    projects = [prefix + suffix for suffix in ('_ok', '_copy')]
    types = [project + '/asset' for project in projects]
    pipes = ['CROSS_PARENT', 'CROSS_CHILD']
    callback_code = "from pyasm.biz import Project\nserver.update(input['sobject']['__search_key__'], {'name': Project.get_project_code()})\n"
    if replay:
        callback_code += "server.create_note(input['sobject']['__search_key__'], 'Cross-project callback', process='work')\n"
    callback_code += 'return True'
    parents = []
    for index, project in enumerate(projects):
        admin = dict(ticket=token, project='admin')
        api.dispatch('execute_cmd', (admin, 'tactic.command.CreateProjectCmd',
            dict(project_code=project, project_title='Private cross-project Workflow', project_stype=['asset'])))
        admin['project'] = project
        parent = api.dispatch('insert', (admin, types[index], dict(code='CROSS_OBJECT', name='Original')))
        parents.append(parent['__search_key__'])
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            command = Command(log_exception=False)
            def setup():
                command.get_transaction().set_sync(False)
                graph = ('<pipeline><process name="start" type="dependency"/><process name="done" type="action"/>'
                         '<connect from="start" to="done"/></pipeline>' if index == 0 else
                         '<pipeline><process name="work" type="manual"/></pipeline>')
                pipeline = Pipeline.create('Cross-project', '', types[index], graph, code=pipes[index])
                if index == 0:
                    definition = pipeline.get_process_sobject('start')
                    definition.set_json_value('workflow', {'version': 2, 'default': {
                        'related_search_type': "@SOBJECT(%s?project=%s['code','CROSS_OBJECT'])" % (types[1], projects[1]),
                        'related_scope': 'global', 'related_process': 'work', 'related_wait': True}})
                    definition.commit()
                    finish = pipeline.get_process_sobject('done')
                    finish.set_json_value('workflow', {'on_action_path': 'contract/cross_finish'})
                    finish.commit()
                else:
                    definition = pipeline.get_process_sobject('work')
                    definition.set_json_value('workflow', {'on_pending': callback_code})
                    definition.commit()
                obj = Search.get_by_search_key(parent['__search_key__'])
                obj.set_value('pipeline_code', pipes[index]); obj.commit()
                Workflow().init(startup=True, quiet=True)
                if adoption:
                    from pyasm.search import SearchType
                    for process in (('start', 'done', '__PIPELINE__') if index == 0 else ('work', '__PIPELINE__')):
                        state = SearchType.create('config/process_state')
                        state.set_sobject_value(obj)
                        state.set_value('process', process)
                        state.set_value('status', 'unknown')
                        state.set_value('state', '{"preserved":"legacy"}')
                        state.commit(triggers='none')
            command.execute = setup
            Command.execute_cmd(command)
    finish_code = callback_code
    admin = dict(ticket=token, project=projects[0])
    script = api.dispatch('insert', (admin, 'config/custom_script',
        dict(folder='contract', title='cross_finish', language='python', script=finish_code)))
    migration_auth = dict(ticket=token, project=projects[1])
    old_state = api.dispatch('insert', (migration_auth, 'config/process_state',
        dict(code='OLD_STATE', process='migration', search_type=types[1] + '?project=' + projects[1],
             search_code='OTHER', state='{"preserved":"original"}')))
    if store.get_db_resource().get_vendor() == 'PostgreSQL':
        with request_context(RequestContext(store, 'admin', projects[1])):
            api.auth.bind_security('admin', token)
            command = Command(log_exception=False)
            def old_schema():
                command.get_transaction().set_sync(False)
                DbContainer.get(Project.get().get_project_db_resource()).do_update('ALTER TABLE spt_process_state ALTER COLUMN state TYPE varchar(256)')
            command.execute = old_schema
            Command.execute_cmd(command)
    store.upgrade()
    check.assertEqual(api.dispatch('get_by_search_key', (migration_auth, old_state['__search_key__']))['state'], '{"preserved":"original"}')
    long_state = '{"preserved":"' + 'state ' * 100 + '"}'
    api.dispatch('update', (migration_auth, old_state['__search_key__'], dict(state=long_state)))
    store.upgrade()
    check.assertEqual(api.dispatch('get_by_search_key', (migration_auth, old_state['__search_key__']))['state'], long_state)
    install_writer(store)
    resource = store.get_db_resource()
    marker = resource.get_database_impl().get_parameter()
    grants = ''.join('<rule group="api_cmd" key="tactic.command.PythonCmd" project="%s" access="allow"/>' % project for project in projects)
    def permissions(target_access='allow', target_project='allow', parent_access='allow', extra=grants):
        rules = '<rules>'
        for index, project in enumerate(projects):
            rules += '<rule group="project" code="%s" access="%s"/>' % (project, 'allow' if index == 0 else target_project)
            rules += '<rule group="search_type" code="%s" project="%s" access="%s"/>' % (types[index], project, parent_access if index == 0 else target_access)
        rules += '<rule group="search_type" code="sthpw/task" access="allow"/>'
        if replay:
            rules += '<rule group="search_type" code="sthpw/note" access="allow"/>'
        rules += extra + '</rules>'
        with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
            db.execute('UPDATE login_group SET access_rules=%s WHERE code=%s' % (marker, marker), (rules, 'project_writers'))
    permissions()
    auth = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=projects[0])
    if client is not None:
        client.set_ticket(auth['ticket'])
    def start():
        if client is not None:
            client.set_project(projects[0])
            return client.call_pipeline_event(parents[0], 'start', 'pending')
        return api.dispatch('call_pipeline_event', (auth, parents[0], 'start', 'pending'))
    def finish():
        if client is not None:
            client.set_project(projects[1])
            return client.update(task['__search_key__'], dict(status='Complete'))
        return api.dispatch('update', (dict(auth, project=projects[1]), task['__search_key__'], dict(status='Complete')))
    denied = Fault if client is not None else SecurityException
    task = api.dispatch('create_task', (dict(auth, project=projects[1]), parents[1]), dict(process='work'))
    def records():
        result = {}
        for project in projects:
            admin = dict(ticket=token, project=project)
            for stype in ('config/process_state', project + '/asset'):
                result[(project, stype)] = ast.literal_eval(api.dispatch('query', (admin, stype), dict(order_bys=['id'])))
        admin = dict(ticket=token, project=projects[0])
        for stype in ('sthpw/task', 'sthpw/message', 'sthpw/message_log', 'sthpw/status_log', 'sthpw/note', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp'):
            with request_context(RequestContext(store, 'admin', projects[0])):
                api.auth.bind_security('admin', token)
                search = Search(stype); search.add_order_by('id')
                result[stype] = [row.get_sobject_dict() for row in search.get_sobjects()]
        return result
    def state(index, process):
        rows = ast.literal_eval(api.dispatch('query', (dict(ticket=token, project=projects[index]), 'config/process_state')))
        return next(row['status'] for row in rows if row['process'] == process)
    def values():
        result = {}
        for kind, data in records().items():
            if kind in ('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp'):
                continue
            stype = kind[1] if isinstance(kind, tuple) else kind
            ignored = ('timestamp', '__search_key__') if stype in ('config/process_state', 'sthpw/task', 'sthpw/note') else ('timestamp', '__search_key__', 'id')
            result[kind] = [{key: value for key, value in row.items() if key not in ignored} for row in data]
        return result
    def replay_transition(before, index):
        from pyasm.common import Common, Xml
        from pyasm.search import SObjectUndo
        logs = records()['sthpw/transaction_log']
        log = next(row for row in reversed(logs) if row['login'] == 'project_writer')
        check.assertEqual(log['namespace'], projects[index])
        data = log['transaction']
        journal = Xml(Common.decompress_transaction(data) if data.startswith('zlib:') else data)
        check.assertEqual(journal.get_root_node().get('workflow_replay'), 'complete')
        if adoption:
            check.assertTrue(any(column.get('name') == 'pipeline_code' and not column.get('from') and column.get('to')
                for node in journal.get_nodes('transaction/sobject') for column in Xml.xpath(node, 'column')))
        check.assertEqual({node.get('search_type').split('project=')[1] for node in journal.get_nodes('transaction/sobject')
                           if node.get('search_type', '').startswith('config/process_state?')}, set(projects))
        after = values()
        unchanged = records()
        with check.assertRaises(denied):
            if client is not None:
                client.set_project(projects[index ^ 1]); client.undo(transaction_id=log['id'])
            else:
                api.dispatch('undo', (dict(auth, project=projects[index ^ 1]),), dict(transaction_id=log['id']))
        check.assertEqual(records(), unchanged)
        def call(method):
            if client is not None:
                client.set_project(projects[index])
                return getattr(client, method)(transaction_id=log['id'])
            return api.dispatch(method, (dict(auth, project=projects[index]),), dict(transaction_id=log['id']))
        def deny(method, options=None):
            unchanged = records()
            with check.assertRaises(denied, msg=repr(options)):
                call(method)
            check.assertEqual(records(), unchanged)
        if adoption:
            adoption_node = next(node for node in journal.get_nodes('transaction/sobject') if any(
                column.get('name') == 'pipeline_code' and not column.get('from') and column.get('to')
                for column in Xml.xpath(node, 'column')))
            state_type, state_code = adoption_node.get('search_type'), adoption_node.get('search_code')
            state_project = state_type.split('project=')[1]
            owner_index = projects.index(state_project)
            def replace(stype, code, field, value):
                with request_context(RequestContext(store, 'admin', state_project)):
                    api.auth.bind_security('admin', token)
                    command = Command(log_exception=False)
                    command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
                    def save():
                        row = Search.get_by_code(stype, code)
                        row.set_value(field, value); row.commit(triggers='none')
                    command.execute = save; Command.execute_cmd(command)
            replace(state_type, state_code, 'pipeline_code', 'FOREIGN_OWNER')
            deny('undo'); replace(state_type, state_code, 'pipeline_code', pipes[owner_index])
            replace(types[owner_index] + '?project=' + state_project, 'CROSS_OBJECT', 'pipeline_code', 'FOREIGN_OWNER')
            deny('undo'); replace(types[owner_index] + '?project=' + state_project, 'CROSS_OBJECT', 'pipeline_code', pipes[owner_index])
            def replace_journal(data):
                with request_context(RequestContext(store, 'admin', projects[index])):
                    api.auth.bind_security('admin', token)
                    command = Command(log_exception=False)
                    command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
                    def save():
                        row = Search.get_by_id('sthpw/transaction_log', log['id'])
                        row.set_value('transaction', data); row.commit(triggers='none')
                    command.execute = save; Command.execute_cmd(command)
            original_xml = journal.to_string()
            original_id = adoption_node.get('search_id')
            check.assertTrue(original_id)
            adoption_node.set('search_id', str(int(original_id) + 999))
            replace_journal(journal.to_string()); deny('undo')
            adoption_node.set('search_id', original_id); replace_journal(original_xml)
            column = next(column for column in Xml.xpath(adoption_node, 'column') if column.get('name') == 'pipeline_code')
            for field in ('from', 'to'):
                previous = column.get(field)
                column.set(field, 'FOREIGN_OWNER')
                replace_journal(journal.to_string()); deny('undo')
                column.set(field, previous); replace_journal(original_xml)
        denial_options = [dict(target_project='deny'), dict(target_access='view'), dict(parent_access='view'),
                *(dict(extra='<rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/>' % project) for project in projects),
                dict(extra='<rule group="search_type" code="sthpw/message_log" project="%s" access="deny"/>' % projects[1]),
                dict(extra='<rule group="sobject_column" search_type="%s" column="name" project="%s" access="deny"/>' % (types[index ^ 1], projects[index ^ 1])),
                dict(extra='<rule group="sobject" search_type="config/process_state" code="%s" project="%s" access="deny"/>' %
                    (next(node.get('search_code') for node in journal.get_nodes('transaction/sobject') if node.get('search_type') == 'config/process_state?project=' + projects[1]), projects[1])),
                dict(extra='<rule group="search_filter" search_type="%s" column="code" value="HIDDEN"/>' % types[1])]
        if any(node.get('search_type') == 'sthpw/task' for node in journal.get_nodes('transaction/sobject')):
            denial_options.append(dict(extra='<rule group="sobject_column" search_type="sthpw/task" column="status" project="%s" access="deny"/>' % projects[1]))
        if adoption:
            adoption_projects = {node.get('search_type').split('project=')[1] for node in journal.get_nodes('transaction/sobject')
                if node.get('search_type', '').startswith('config/process_state?') and any(column.get('name') == 'pipeline_code' for column in Xml.xpath(node, 'column'))}
            denial_options.extend(dict(extra='<rule group="sobject_column" search_type="config/process_state" column="pipeline_code" project="%s" access="deny"/>' % project) for project in adoption_projects)
            denial_options.append(dict(extra='<rule group="search_filter" search_type="config/process" column="code" value="HIDDEN"/>'))
        for options in denial_options:
            with check.subTest(options=options):
                permissions(**options); deny('undo', options)
        permissions(extra='')  # Replay restores recorded callbacks' results without executing Python.
        for method, expected in (('undo', before), ('redo', after)):
            original = getattr(SObjectUndo, method)
            touched = set()
            def fail(node):
                original(node)
                stype = node.get('search_type', '')
                if stype.startswith('config/process_state?'):
                    touched.add(stype)
                    if len(touched) == 2:
                        raise ValueError('late replay across two databases')
            unchanged = records()
            with patch.object(SObjectUndo, method, fail):
                with check.assertRaises(ValueError if client is None else Fault):
                    call(method)
            check.assertEqual(len(touched), 2)
            check.assertEqual(records(), unchanged)
            if method == 'redo':
                permissions(extra='<rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/>' % projects[0])
                deny('redo'); permissions(extra='')
                if adoption:
                    replace(state_type, state_code, 'pipeline_code', 'FOREIGN_OWNER')
                    deny('redo'); replace(state_type, state_code, 'pipeline_code', '')
            if adoption:
                from pyasm.common import Container
                from pyasm.common.errors import UnsupportedContract
                from pyasm.search.sql import Sql
                original_sql = Sql._do_security_dml
                forged = []
                def staged(sql, table, data=None, *args, **kwargs):
                    scope = Container.get('Workflow:replay')
                    if scope and data is not None and 'pipeline_code' in data and not forged:
                        with check.assertRaises(UnsupportedContract):
                            original_sql(sql, table, dict(data, pipeline_code='FORGED_OWNER'), *args, **kwargs)
                        forged.append(True)
                    return original_sql(sql, table, data, *args, **kwargs)
                with patch.object(Sql, '_do_security_dml', staged):
                    call(method)
                check.assertEqual(forged, [True])
            else:
                call(method)
            check.assertEqual(values(), expected)
        permissions()
    before = records()
    for options in (dict(target_access='view'), dict(target_project='deny'), dict(extra=''),
                    dict(extra='<rule group="api_cmd" key="tactic.command.PythonCmd" project="%s" access="allow"/>' % projects[0])):
        permissions(**options)
        with check.assertRaises(denied) as error:
            start()
        if client is not None:
            check.assertEqual(error.exception.faultCode, 403)
        check.assertEqual(records(), before)
    permissions()
    initial = values() if replay else None
    start()
    check.assertEqual(state(0, 'start'), 'in_progress')
    check.assertEqual(state(1, 'work'), 'pending')
    check.assertEqual(api.dispatch('get_by_search_key', (admin, parents[1]))['name'], projects[1])
    if replay:
        replay_transition(initial, 0)
    before = records()
    for options in (dict(target_access='view'), dict(parent_access='view')):
        permissions(**options)
        with check.assertRaises(denied) as error:
            finish()
        if client is not None:
            check.assertEqual(error.exception.faultCode, 403)
        check.assertEqual(records(), before)
    permissions()
    api.dispatch('update', (admin, script['__search_key__'], dict(script=finish_code.replace('return True', "raise ValueError('late cross-project callback')"))))
    before = records()
    if client is not None:
        with check.assertRaises(Fault) as error:
            finish()
        check.assertEqual(error.exception.faultCode, 400)
    else:
        with check.assertRaisesRegex(ValueError, 'late cross-project callback'):
            finish()
    check.assertEqual(records(), before)
    api.dispatch('update', (admin, script['__search_key__'], dict(script=finish_code)))
    initial = values() if replay else None
    finish()
    check.assertEqual(state(0, 'start'), 'complete')
    check.assertEqual(state(0, 'done'), 'complete')
    check.assertEqual(state(1, 'work'), 'complete')
    check.assertEqual(api.dispatch('get_by_search_key', (admin, parents[0]))['name'], projects[0])
    logs = records()['sthpw/message_log']
    check.assertEqual({row['project_code'] for row in logs}, set(projects))
    check.assertTrue(all(row['login'] == 'project_writer' for row in logs))
    if replay:
        replay_transition(initial, 1)
    return dict(started=True, completed=True, denied=True, rollback=True, callbacks=True)


class UserCrossProjectWorkflow(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserCrossProjectTransport(unittest.TestCase):
    exercise = staticmethod(exercise)
    def test_unchanged_sdk_cross_project_callbacks_and_rollback(self):
        import test_transport
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.cross_project_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(self.exercise(test_transport.Transport.store, 'rpc_cross',
                                     password='private-test-password', client=client)['completed'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()


class CrossProjectLookup(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for project in ('one', 'two'):
            with request_context(RequestContext(cls.store, 'admin', project)):
                cls.api.auth.bind_security('admin', cls.ticket)
                command = Command(log_exception=False)
                def setup():
                    command.get_transaction().set_sync(False)
                    Pipeline.create('Project process', '', 'contract/entity',
                        '<pipeline><process name="work" type="manual"/></pipeline>', code='LOOKUP_' + project)
                command.execute = setup
                Command.execute_cmd(command)
        cls.cases = [dict(method='workflow_project_contract', name=project + '_' + owner,
                          project=project, pipeline='LOOKUP_' + owner, owner=owner)
                     for project in ('one', 'two') for owner in ('one', 'two')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', case['project'])):
                Api(store).auth.bind_security('admin', self.ticket)
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['project'], case['project'])
        self.assertEqual(result['owner'], case['owner'])
        self.assertTrue(result['direct'])
        self.assertEqual(result['direct'], result['callback'])
        if case['project'] == case['owner']:
            self.assertEqual(result, original)
        else:
            # Source looks in the caller's config database instead of the pipeline owner.
            self.assertEqual(original, dict(project=case['project'], owner=case['owner'], direct=None, callback=None))
