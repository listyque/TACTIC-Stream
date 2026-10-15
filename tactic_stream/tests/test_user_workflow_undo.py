"""Complete ordinary-user Workflow replay, including native message backups."""
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.biz import Pipeline
from pyasm.command import Command, Workflow
from pyasm.common import Container, Common, Xml
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SObjectUndo
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None):
    check = unittest.TestCase()
    api = Api(store)
    project, stype = prefix + '_ok', prefix + '_ok/asset'
    admin = dict(ticket=api.get_ticket('admin', password), project='admin')
    api.dispatch('execute_cmd', (admin, 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private Workflow replay', project_stype=['asset'])))
    admin['project'] = project
    parent = api.dispatch('insert', (admin, stype, dict(code='WORKFLOW_REPLAY', name='Parent')))
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', admin['ticket'])
        command = Command()
        def setup():
            command.get_transaction().set_sync(False)
            Pipeline.create('Workflow replay', '', stype,
                '<pipeline><process name="work" type="manual"/><process name="finish" type="action"/>'
                '<connect from="work" to="finish"/></pipeline>', code='REPLAY_WORKFLOW')
            Workflow().init(startup=True, quiet=True)
            obj = Search.get_by_search_key(parent['__search_key__'])
            obj.set_value('pipeline_code', 'REPLAY_WORKFLOW'); obj.commit()
        command.execute = setup; Command.execute_cmd(command)
    install_writer(store)
    auth = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=project)
    if client is not None:
        client.set_ticket(auth['ticket']); client.set_project(project)
    def call(method, *args, **kwargs):
        return getattr(client, method)(*args, **kwargs) if client is not None else api.dispatch(method, (auth, *args), kwargs)
    def permissions(extra='', parent_access='allow', task_access='allow'):
        rules = '<rules><rule group="project" code="%s" access="allow"/><rule group="search_type" code="%s" access="%s"/><rule group="search_type" code="sthpw/task" project="%s" access="%s"/>%s</rules>' % (project, stype, parent_access, project, task_access, extra)
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', dict(access_rules=rules)))
    def rows(kind):
        query = Search(kind); query.add_order_by('id')
        return [obj.get_data() for obj in query.get_sobjects()]
    kinds = (stype, 'sthpw/task', 'sthpw/note', 'config/process_state', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log')
    def state(journals=False):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', admin['ticket'])
            return {kind: rows(kind) for kind in kinds + (('sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp') if journals else ())}
    def values():
        return {kind: [{key: value for key, value in row.items() if key not in ('timestamp', 'id')}
            for row in data] for kind, data in state().items()}
    def journal():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', admin['ticket'])
            query = Search('sthpw/transaction_log'); query.add_filter('login', 'project_writer'); query.add_order_by('id desc'); query.set_limit(1)
            return query.get_sobject().get_data()
    def xml(log):
        data = log['transaction']
        return Xml(Common.decompress_transaction(data) if data.startswith('zlib:') else data)
    permissions()
    task = call('create_task', parent['__search_key__'], process='work')
    transitions = []
    for method, args in (('call_pipeline_event', (parent['__search_key__'], 'work', 'pending')),
            ('update', (task['__search_key__'], dict(status='In Progress'))),
            ('update', (task['__search_key__'], dict(status='Complete')))):
        before = values()
        call(method, *args)
        log = journal(); after = values()
        transitions.append(log)
        check.assertEqual(xml(log).get_root_node().get('workflow_replay'), 'complete')
        call('undo', transaction_id=log['id'])
        check.assertEqual(values(), before)
        call('redo', transaction_id=log['id'])
        check.assertEqual(values(), after)
    log = transitions[-1]
    kinds_in_log = {node.get('search_type', '').split('?')[0] for node in xml(log).get_nodes('transaction/sobject')}
    check.assertTrue({'config/process_state', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log'} <= kinds_in_log)
    # Preflight refuses any inaccessible parent/effect or revoked inverse operation.
    for options in (dict(parent_access='view'), dict(task_access='view'),
            dict(extra='<rule group="search_type" code="config/process_state" project="%s" access="view"/>' % project),
            dict(extra='<rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/>' % project),
            dict(extra='<rule group="sobject_column" search_type="sthpw/message" column="message" project="%s" access="deny"/>' % project),
            dict(extra='<rule group="search_type" code="sthpw/message_log" project="%s" access="deny"/>' % project),
            dict(extra='<rule group="search_filter" search_type="config/process_state" column="code" value="HIDDEN"/>'),
            dict(extra='<rule group="search_filter" search_type="%s" column="code" value="HIDDEN"/>' % stype)):
        permissions(**options); before = state(True)
        with check.assertRaises(SecurityException if client is None else Fault):
            call('undo', transaction_id=log['id'])
        check.assertEqual(state(True), before)
    permissions()
    api.dispatch('insert', (admin, 'config/custom_script', dict(folder='contract', title='replay_delete', language='python',
        script="raise ValueError('Replay must not rerun delete callbacks')")))
    api.dispatch('insert', (admin, 'config/trigger', dict(event='delete|config/process_state', class_name='',
        script_path='contract/replay_delete', mode='same process,same transaction')))
    permissions(extra='<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/>')
    call('undo', transaction_id=log['id'])
    permissions(extra='<rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/>' % project)
    before = state(True)
    with check.assertRaises(SecurityException if client is None else Fault):
        call('redo', transaction_id=log['id'])
    check.assertEqual(state(True), before)
    permissions()
    # A validated effect cannot authorize another journal record or a forged SQL payload.
    from pyasm.search.sql import Sql
    original_sql = Sql._do_security_dml
    forged = []
    def bound(sql, table, data=None, *args, **kwargs):
        scope = Container.get('Workflow:replay')
        if scope and scope['node'].get('search_type', '').startswith('config/process_state') and data is not None and not forged:
            with check.assertRaises(UnsupportedContract):
                original_sql(sql, table, dict(data, status='FORGED'), *args, **kwargs)
            other = Search('sthpw/message').get_sobject()
            if other is not None:
                with check.assertRaises(SecurityException):
                    other._check_business_write('edit')
            forged.append(True)
        return original_sql(sql, table, data, *args, **kwargs)
    with patch.object(Sql, '_do_security_dml', bound):
        call('redo', transaction_id=log['id'])
    check.assertEqual(forged, [True])
    # Late native failures must roll back all earlier effects and journal direction.
    for direction in ('undo', 'redo'):
        before = state(True)
        original = getattr(SObjectUndo, direction)
        touched = []
        def fail_late(node, *args, **kwargs):
            result = original(node, *args, **kwargs)
            touched.append(node)
            if len(touched) == 4:
                raise ValueError('late Workflow replay failure')
            return result
        with patch.object(SObjectUndo, direction, fail_late):
            with check.assertRaises(ValueError if client is None else Fault):
                call(direction, transaction_id=log['id'])
        check.assertEqual(len(touched), 4); check.assertEqual(state(True), before)
        call(direction, transaction_id=log['id'])
    # Historical journals cannot silently restore states while leaving messages stale.
    def replace_log(data):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', admin['ticket'])
            command = Command()
            def save():
                command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
                saved = Search.get_by_id('sthpw/transaction_log', log['id']); saved.set_value('transaction', data); saved.commit(triggers='none')
            command.execute = save; Command.execute_cmd(command)
    old = xml(journal())
    original_xml = old.to_string()
    old.get_root_node().attrib.pop('workflow_replay', None)
    replace_log(old.to_string()); before = state(True)
    with check.assertRaises(UnsupportedContract if client is None else Fault):
        call('undo', transaction_id=log['id'])
    check.assertEqual(state(True), before)
    replace_log(original_xml)
    # The configured callback is live for a normal deletion, but not for replay.
    state_code = state()['config/process_state'][0]['code']
    before = state(True)
    with check.assertRaisesRegex(ValueError, 'Replay must not rerun delete callbacks'):
        api.dispatch('delete_sobject', (admin, 'config/process_state?project=%s&code=%s' % (project, state_code)))
    check.assertEqual(state(True), before)
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', auth['ticket'])
        check.assertIsNone(Container.get('Workflow:replay'))
    return dict(complete=True)


class UserWorkflowUndo(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserWorkflowUndoTransport(unittest.TestCase):
    def test_original_sdk_workflow_undo_redo(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.user_workflow_undo_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc'); client.set_server(test_transport.Transport.url)
            self.assertTrue(exercise(test_transport.Transport.store, 'rpc_workflow_undo', password='private-test-password', client=client)['complete'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()


from test_user_workflow import UserWorkflowParity


class WorkflowUndoParity(UserWorkflowParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with request_context(RequestContext(cls.store, 'admin', 'one')):
            cls.api.auth.bind_security('admin', cls.ticket)
            command = Command()
            command.get_transaction().set_sync(False)
            def without_callback():
                from pyasm.biz import PrefSetting
                PrefSetting.create('timezone', 'UTC', user='project_writer')
                process = Pipeline.get_by_code('USER_WORKFLOW').get_process_sobject('finish')
                process.set_json_value('workflow', {}); process.commit()
            command.execute = without_callback; Command.execute_cmd(command)
        rules = ('<rules><rule group="project" code="one" access="allow"/>'
            '<rule group="search_type" code="contract/entity" access="allow"/>'
            '<rule group="search_type" code="sthpw/task" access="allow"/>'
            '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/></rules>')
        cls.cases = [dict(name='Workflow messages and GMT replay', method='workflow_undo_contract', rules=rules)]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['after']['status'], 'Complete')
        self.assertEqual(result['after'], result['redone'])
        self.assertEqual(result['undone']['status'], 'Pending')
        self.assertEqual(result['undone']['messages'], [])
        # Source's partial Workflow journal leaves status/messages stale; GMT dates must survive.
        self.assertEqual(original['undone']['status'], 'Complete', original)
        self.assertEqual(original['undone']['messages'], original['after']['messages'])
        self.assertEqual(result['gmt_date'], '2026-01-02 03:04:05')
        self.assertEqual(original['gmt_date'], '2026-01-02 03:04:05')
