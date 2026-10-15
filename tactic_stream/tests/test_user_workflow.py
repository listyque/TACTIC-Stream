import ast
import importlib.util
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from pyasm.biz import Pipeline
from pyasm.command import Command, Trigger
from pyasm.command.workflow import Workflow, BaseProcessTrigger, _commit_effect
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, SObject, DbContainer
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api
import test_plugin_installation as plugin_tests
import test_read_parity as read_tests
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case
from test_project_writes import install_writer, PASSWORD


def exercise_user_workflow(store, prefix):
    check = unittest.TestCase()
    api = Api(store)
    project = prefix + '_ok'
    stype = project + '/asset'
    admin = dict(ticket=api.get_ticket('admin', 'plugin-test-password'), project='admin')
    api.dispatch('execute_cmd', (admin, 'tactic.command.CreateProjectCmd',
                 dict(project_code=project, project_title='Private Workflow', project_stype=['asset'])))
    admin['project'] = project
    parent = api.dispatch('insert', (admin, stype, dict(code='WORKFLOW_PARENT', name='Workflow parent')))
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', admin['ticket'])
        command = Command(log_exception=False)
        def setup():
            command.get_transaction().set_sync(False)
            Pipeline.create('User Workflow', '', stype,
                '<pipeline><process name="work" type="manual"/><process name="finish" type="action"/>'
                '<connect from="work" to="finish"/></pipeline>', code='USER_WORKFLOW')
            Workflow().init(startup=True, quiet=True)
            obj = Search.get_by_search_key(parent['__search_key__'])
            obj.set_value('pipeline_code', 'USER_WORKFLOW'); obj.commit()
        command.execute = setup
        Command.execute_cmd(command)
    install_writer(store)
    resource = store.get_db_resource()
    parameter = resource.get_database_impl().get_parameter()
    def permissions(extra='', parent_access='allow', task_access='allow', project_access='allow'):
        xml = ('<rules><rule group="project" code="%s" access="%s"/>'
               '<rule group="search_type" code="%s" project="%s" access="%s"/>'
               '<rule group="search_type" code="sthpw/task" project="%s" access="%s"/>%s</rules>') % (
                   project, project_access, stype, project, parent_access, project, task_access, extra)
        with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
            db.execute('UPDATE login_group SET access_rules=%s WHERE code=%s' % (parameter, parameter), (xml, 'project_writers'))
    permissions()
    token = api.get_ticket('project_writer', PASSWORD)
    auth = dict(ticket=token, project=project)
    key = parent['__search_key__']
    task = api.dispatch('create_task', (auth, key), dict(process='work'))
    def rows(stype):
        return ast.literal_eval(api.dispatch('query', (admin, stype), dict(order_bys=['id'])))
    def snapshot():
        return {name: rows(name) for name in ('config/process_state', 'sthpw/message', 'sthpw/message_log',
                'sthpw/status_log', 'sthpw/task', 'sthpw/note')}
    api.dispatch('call_pipeline_event', (auth, key, 'work', 'pending'))
    api.dispatch('update', (auth, task['__search_key__'], dict(status='In Progress')))
    check.assertEqual({r['process']: r['status'] for r in rows('config/process_state')}['work'], 'in_progress')
    api.dispatch('update', (auth, task['__search_key__'], dict(status='Complete')))
    check.assertEqual({r['process']: r['status'] for r in rows('config/process_state')}['finish'], 'complete')
    check.assertTrue(all(r['login'] == 'project_writer' and r['project_code'] == project for r in rows('sthpw/message_log')))
    before = snapshot()
    for options in (dict(parent_access='view'), dict(task_access='view'),
                    dict(extra='<rule group="search_filter" search_type="%s" column="code" value="HIDDEN"/>' % stype),
                    dict(extra='<rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/>' % project),
                    dict(extra='<rule group="sobject_column" search_type="sthpw/message_log" column="message" project="%s" access="deny"/>' % project)):
        permissions(**options)
        with check.assertRaises((SecurityException, LookupError)):
            api.dispatch('call_pipeline_event', (auth, key, 'work', 'pending'))
        check.assertEqual(snapshot(), before)
    permissions()
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', token)
        def run(action):
            command = Command(log_exception=False)
            def execute():
                command.get_transaction().set_sync(False)
                return action()
            command.execute = execute
            return Command.execute_cmd(command)
        # Use the public trigger path, as handlers are constructed by the engine.
        def revise():
            Trigger.call(Command(), 'process|revise', dict(sobject=Search.get_by_search_key(key),
                         pipeline=Pipeline.get_by_code('USER_WORKFLOW'), process='work', error='Ошибка · native Workflow'))
        run(revise)
        notes = Search('sthpw/note').get_sobjects()
        check.assertEqual(len(notes), 1)
        check.assertEqual(notes[0].get_value('login'), 'project_writer')
        check.assertEqual(notes[0].get_value('context'), 'work/error')
        def forbidden():
            obj = Search.get_by_search_key(key)
            state = BaseProcessTrigger(); state.input = dict(sobject=obj, pipeline=Pipeline.get_by_code('USER_WORKFLOW'))
            state = state.get_process_state(obj, 'work')
            with check.assertRaises(SecurityException):
                state.set_value('status', 'forged'); state.commit()
            with check.assertRaises(UnsupportedContract):
                DbContainer.get(state.get_db_resource()).do_update("UPDATE spt_process_state SET status='raw'")
            message = Search('sthpw/message').get_sobject()
            with check.assertRaises(SecurityException):
                message.set_value('message', 'forged'); message.commit()
            foreign = SearchType.create('config/process_state')
            foreign.set_sobject_value(obj); foreign.set_value('search_code', 'FORGED')
            with check.assertRaises(SecurityException):
                _commit_effect(foreign, obj)
            original_dml = DbContainer.get(state.get_db_resource())._do_security_dml
            def check_bound(table, data=None, *args, **kwargs):
                if table == 'spt_process_state' and data is not None:
                    with check.assertRaises(UnsupportedContract):
                        original_dml(table, dict(data, search_code='FORGED'), *args, **kwargs)
                return original_dml(table, data, *args, **kwargs)
            state.set_value('status', 'in_progress')
            with patch.object(DbContainer.get(state.get_db_resource()), '_do_security_dml', side_effect=check_bound):
                _commit_effect(state, obj)
            state.set_value('status', 'revoked staged status')
            Environment.get_security().get_access_manager().add_xml_rules(
                '<rules><rule group="sobject_column" search_type="config/process_state" column="status" project="%s" access="deny"/></rules>' % project)
            with check.assertRaises(SecurityException):
                _commit_effect(state, obj)
        run(forbidden)
        api.auth.bind_security('project_writer', token)
        check.assertFalse(Environment.get_security().is_admin())
        for scope in ('Workflow:writing', 'Workflow:message_source', 'Workflow:note_source', 'StatusLog:writing'):
            check.assertIsNone(Container.get(scope))
    before = snapshot()
    original = SObject.commit
    def late_failure(obj, *args, **kwargs):
        result = original(obj, *args, **kwargs)
        if obj.get_base_search_type() == 'config/process_state' and obj.get_value('status') == 'pending':
            raise ValueError('late Workflow write failure')
        return result
    with patch.object(SObject, 'commit', new=late_failure):
        with check.assertRaisesRegex(ValueError, 'late Workflow write failure'):
            api.dispatch('call_pipeline_event', (auth, key, 'work', 'pending'))
    check.assertEqual(snapshot(), before)
    with request_context(RequestContext(store, 'project_writer', 'admin')):
        api.auth.bind_security('project_writer', token)
        command = Command(log_exception=False)
        def different_request_project():
            command.get_transaction().set_sync(False)
            obj = Search.get_by_search_key(key)
            handler = BaseProcessTrigger(); handler.input = {}
            handler.log_message(obj, 'cross_context', 'in_progress')
            state = handler.get_process_state(obj, 'cross_context')
            check.assertEqual(state.get_project_code(), project)
            check.assertEqual(state.get_db_resource().get_database(), project)
            message = Search.get_by_code('sthpw/message', key + '|cross_context|status')
            check.assertEqual(message.get_value('project_code'), project)
            raise ValueError('cross-context rollback')
        command.execute = different_request_project
        with check.assertRaisesRegex(ValueError, 'cross-context rollback'):
            Command.execute_cmd(command)
    check.assertEqual(snapshot(), before)
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', admin['ticket'])
        command = Command(log_exception=False)
        def callback():
            command.get_transaction().set_sync(False)
            definition = Pipeline.get_by_code('USER_WORKFLOW').get_process_sobject('work')
            definition.set_json_value('workflow', {'on_pending': "raise ValueError('must not execute')"})
            definition.commit()
        command.execute = callback
        Command.execute_cmd(command)
    with check.assertRaisesRegex(SecurityException, 'Script execution'):
        api.dispatch('call_pipeline_event', (auth, key, 'work', 'pending'))
    check.assertEqual(snapshot(), before)
    grant = '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/>'
    permissions(extra=grant)
    with check.assertRaisesRegex(ValueError, 'must not execute'):
        api.dispatch('call_pipeline_event', (auth, key, 'work', 'pending'))
    check.assertEqual(snapshot(), before)
    script_code = "server.update(parent_key, {'name': 'Python · user'})\nreturn {'login': server.login, 'value': value}"
    script = api.dispatch('insert', (admin, 'config/custom_script', dict(folder='contract', title='user', language='python', script=script_code)))
    check.assertEqual(api.dispatch('execute_python_script', (auth, 'contract/user', dict(parent_key=key, value=42)))['info'],
                      dict(login='project_writer', value=42))
    check.assertEqual(api.dispatch('get_by_search_key', (auth, key))['name'], 'Python · user')
    api.dispatch('insert', (admin, 'config/custom_script', dict(folder='contract', title='trigger', language='python',
        script="return {'login': server.login, 'value': input['value']}")))
    api.dispatch('insert', (admin, 'sthpw/trigger', dict(event='contract|user_python', class_name='',
        script_path='contract/trigger', project_code=project, mode='same process,same transaction')))
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', token)
        from tactic.command.python_cmd import check_script_execution
        from pyasm.security import Sudo
        with check.assertRaises(UnsupportedContract):
            check_script_execution(python=True)
        with check.assertRaises(SecurityException):
            check_script_execution(require_transaction=False)
        sudo = Sudo()
        try:
            with check.assertRaises(SecurityException):
                check_script_execution(require_transaction=False, python=True)
        finally:
            sudo.exit()
        check.assertFalse(Environment.get_security().is_admin())
        security = Environment.get_security()
        security.set_admin(True)
        try:
            with check.assertRaises(SecurityException):
                check_script_execution(require_transaction=False, python=True)
        finally:
            security.set_admin(False)
        command = Command(log_exception=False)
        def python_trigger():
            command.get_transaction().set_sync(False)
            triggers = Trigger.call(command, 'contract|user_python', dict(value=11))
            check.assertEqual([trigger.get_ret_val() for trigger in triggers], [dict(login='project_writer', value=11)])
        command.execute = python_trigger
        Command.execute_cmd(command)
    before = snapshot()
    api.dispatch('update', (admin, script['__search_key__'], dict(script="server.update(parent_key, {'name': 'Must rollback'})\nraise ValueError('Python rollback')")))
    with check.assertRaisesRegex(ValueError, 'Python rollback'):
        api.dispatch('execute_python_script', (auth, 'contract/user', dict(parent_key=key)))
    check.assertEqual(api.dispatch('get_by_search_key', (auth, key))['name'], 'Python · user')
    check.assertEqual(snapshot(), before)
    for options in (dict(extra='', parent_access='allow'), dict(extra=grant, project_access='deny'),
                    dict(extra=grant + '<rule group="project" code="*" access="allow"/>', project_access='deny'),
                    dict(extra=grant.replace('access="allow"', 'project="other_project" access="allow"')),
                    dict(extra=grant, parent_access='view'),
                    dict(extra=grant + '<rule group="sobject_column" search_type="%s" column="name" project="%s" access="deny"/>' % (stype, project))):
        permissions(**options)
        with check.assertRaises(SecurityException):
            api.dispatch('execute_python_script', (auth, 'contract/user', dict(parent_key=key)))
        check.assertEqual(api.dispatch('get_by_search_key', (admin, key))['name'], 'Python · user')
    permissions(extra=grant)
    result = api.dispatch('execute_python_script', (auth, '', dict(code="return {'login': server.login, 'value': value}", value=7)))
    check.assertEqual(result['info'], dict(login='project_writer', value=7))
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', token)
        security = Environment.get_security()
        security._is_logged_in = 0
        try:
            with check.assertRaisesRegex(SecurityException, 'authenticated security'):
                check_script_execution(require_transaction=False, python=True)
        finally:
            security._is_logged_in = 1
        login = security._login
        security._login = Search.get_by_code('sthpw/login', 'admin')
        try:
            with check.assertRaisesRegex(SecurityException, 'authenticated security'):
                check_script_execution(require_transaction=False, python=True)
        finally:
            security._login = login
        api.dispatch('update', (admin, login.get_search_key(), dict(s_status='retired')))
        with check.assertRaisesRegex(SecurityException, 'Script execution'):
            check_script_execution(require_transaction=False, python=True)
    return dict(complete=True, messages=True, error_note=True, denied=True, rollback=True, python_grant=True)


class UserWorkflow(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise_user_workflow)


class UserWorkflowParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_writer(cls.store)
        with request_context(RequestContext(cls.store, 'admin', 'one')):
            cls.api.auth.bind_security('admin', cls.ticket)
            command = Command(log_exception=False)
            def setup():
                command.get_transaction().set_sync(False)
                script = "server.update(input['sobject']['__search_key__'], {'name': 'Python callback · user'})\nreturn True"
                custom = SearchType.create('config/custom_script')
                for name, value in dict(folder='contract', title='workflow', language='python', script=script).items():
                    custom.set_value(name, value)
                custom.commit()
                for root, parent, callback in (('USER_WORKFLOW', 'A', {'on_action': script}),
                                               ('USER_WORKFLOW_SAVED', 'B', {'on_action_path': 'contract/workflow'})):
                    Pipeline.create('User Workflow', '', 'contract/entity',
                        '<pipeline><process name="work" type="manual"/><process name="finish" type="action"/>'
                        '<connect from="work" to="finish"/></pipeline>', code=root)
                    definition = Pipeline.get_by_code(root).get_process_sobject('finish')
                    definition.set_json_value('workflow', callback); definition.commit()
                    obj = Search.get_by_code('contract/entity', parent)
                    obj.set_value('pipeline_code', root); obj.commit()
            command.execute = setup
            Command.execute_cmd(command)
        rules = (
            '<rules><rule group="project" code="one" access="allow"/>'
            '<rule group="search_type" code="contract/entity" access="allow"/>'
            '<rule group="search_type" code="sthpw/task" access="allow"/>'
            '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/></rules>')
        cls.cases = [dict(name='ordinary inline Workflow callback', method='user_workflow_contract', rules=rules),
                     dict(name='ordinary saved Workflow callback', method='user_workflow_contract', rules=rules,
                          parent_code='B', pipeline_code='USER_WORKFLOW_SAVED')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['status'], 'Complete')
        self.assertEqual([(r['process'], r['status']) for r in result['states']], [('finish', 'complete'), ('work', 'complete')])
        self.assertEqual(result['remaining_states'], 0)
        self.assertEqual(result['parent_name'], 'Python callback · user')
        self.assertEqual([r['pipeline'] for r in result['states']], [case.get('pipeline_code', 'USER_WORKFLOW')] * 2)
        self.assertEqual([r['pipeline'] for r in original['states']], ['', ''])
        # The existing alternate-pipeline migration fills the original empty owner.
        self.assertEqual([{k: v for k, v in r.items() if k != 'pipeline'} for r in result['states']],
                         [{k: v for k, v in r.items() if k != 'pipeline'} for r in original['states']])
        self.assertEqual({k: v for k, v in result.items() if k != 'states'},
                         {k: v for k, v in original.items() if k != 'states'})


class UserWorkflowTransport(unittest.TestCase):
    def test_unchanged_sdk(self):
        import test_transport
        from test_project_writes import set_rules
        from xmlrpc.client import Fault
        test_transport.Transport.setUpClass()
        client = None
        try:
            store = test_transport.Transport.store
            api = Api(store)
            ticket = api.get_ticket('admin', 'private-test-password')
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', ticket)
                command = Command(log_exception=False)
                def setup():
                    command.get_transaction().set_sync(False)
                    Pipeline.create('SDK Workflow', '', 'contract/entity',
                        '<pipeline><process name="work" type="manual"/></pipeline>', code='SDK_WORKFLOW')
                    Workflow().init(startup=True, quiet=True)
                    parent = Search.get_by_code('contract/entity', 'A')
                    parent.set_value('pipeline_code', 'SDK_WORKFLOW'); parent.commit()
                    script = SearchType.create('config/custom_script')
                    for name, value in dict(folder='contract', title='sdk', language='python',
                            script="return {'login': server.login, 'value': value}").items():
                        script.set_value(name, value)
                    script.commit()
                command.execute = setup
                Command.execute_cmd(command)
            install_writer(store)
            rules = ('<rules><rule group="project" code="one" access="allow"/>'
                     '<rule group="search_type" code="contract/entity" access="allow"/>'
                     '<rule group="search_type" code="sthpw/task" access="allow"/></rules>')
            set_rules(store, rules)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.workflow_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url); client.set_project('one')
            client.set_ticket(client.get_ticket('project_writer', PASSWORD))
            parent_key = 'contract/entity?project=one&code=A'
            task = client.create_task(parent_key, process='work')
            client.call_pipeline_event(parent_key, 'work', 'pending')
            client.update(task['__search_key__'], dict(status='Complete'))
            self.assertEqual(client.query('config/process_state', filters=[('process', 'work')])[0]['status'], 'complete')
            with self.assertRaises(Fault):
                client.insert('config/process_state', dict(process='forged', status='complete'))
            with self.assertRaises(Fault) as denied:
                client.execute_python_script('contract/sdk', dict(value=42))
            self.assertEqual(denied.exception.faultCode, 403)
            python_rules = rules.replace('</rules>', '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/></rules>')
            set_rules(store, python_rules)
            self.assertEqual(client.execute_python_script('contract/sdk', dict(value=42))['info'],
                             dict(login='project_writer', value=42))
            set_rules(store, python_rules.replace('</rules>', '<rule group="api_method" key="execute_python_script" access="deny"/></rules>'))
            from pyasm.common import Config
            config_value = Config.get_value
            with patch.object(Config, 'get_value', side_effect=lambda section, name, *a, **kw:
                              'true' if (section, name) == ('security', 'api_method_restricted') else config_value(section, name, *a, **kw)):
                with self.assertRaises(Fault) as denied:
                    client.execute_python_script('contract/sdk', dict(value=7))
                self.assertEqual(denied.exception.faultCode, 403, denied.exception.faultString)
            set_rules(store, rules.replace('</rules>', '<rule group="api_method" key="call_pipeline_event" access="deny"/></rules>'))
            from pyasm.common import Config
            with patch.object(Config, 'get_value', side_effect=lambda section, name, *a, **kw:
                              'true' if (section, name) == ('security', 'api_method_restricted') else config_value(section, name, *a, **kw)):
                with self.assertRaises(Fault) as denied:
                    client.call_pipeline_event(parent_key, 'work', 'pending')
                self.assertEqual(denied.exception.faultCode, 403, denied.exception.faultString)
            self.assertEqual(client.query('config/process_state', filters=[('process', 'work')])[0]['status'], 'complete')
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
