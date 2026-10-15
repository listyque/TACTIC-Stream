"""Real task ACLs and native StatusLog on both storage vendors."""
from unittest.mock import patch
import ast
import unittest

from pathlib import Path
import shutil
import tempfile
import test_read_parity as read_tests
from tools.snapshot_probe import run_snapshot_case
from pyasm.biz import Task
from pyasm.command import Command, Trigger
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, DbContainer, SObject
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD


def exercise_user_status(store, prefix):
    check = unittest.TestCase()
    api = Api(store)
    project = prefix + '_ok'
    admin = dict(ticket=api.get_ticket('admin', 'plugin-test-password'), project='admin')
    api.dispatch('execute_cmd', (admin, 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private task status', project_stype=['asset'])))
    admin['project'] = project
    stype = project + '/asset'
    parent = api.dispatch('insert', (admin, stype, dict(code='STATUS_PARENT', name='Task parent')))
    # Exercise task/history separately from Workflow effects.
    api.dispatch('update', (admin, parent['__search_key__'], dict(pipeline_code='')))
    install_writer(store)
    resource = store.get_db_resource()
    parameter = resource.get_database_impl().get_parameter()
    def permissions(extra='', task_access='allow', parent_access='allow', project_access='allow'):
        xml = ('<rules><rule group="project" code="%s" access="%s"/>'
               '<rule group="search_type" code="%s" project="%s" access="%s"/>'
               '<rule group="search_type" code="sthpw/task" project="%s" access="%s"/>%s</rules>') % (
                   project, project_access, stype, project, parent_access, project, task_access, extra)
        with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
            db.execute('UPDATE login_group SET access_rules=%s WHERE code=%s' % (parameter, parameter),
                       (xml, 'project_writers'))
    permissions()
    token = api.get_ticket('project_writer', PASSWORD)
    auth = dict(ticket=token, project=project)
    task = api.dispatch('create_task', (auth, parent['__search_key__']), dict(process='publish', description='Задача · test'))
    key = task['__search_key__']
    check.assertEqual(task['project_code'], project)
    check.assertEqual(task['search_code'], 'STATUS_PARENT')
    def history():
        return ast.literal_eval(api.dispatch('query', (admin, 'sthpw/status_log'), dict(filters=[('search_code', task['code'])], order_bys=['id'])))
    api.dispatch('update', (auth, key, dict(status='Working')))
    logs = history()
    check.assertEqual([(row['from_status'], row['to_status'], row['login'], row['project_code']) for row in logs],
                      [(None, 'Working', 'project_writer', project)])
    api.dispatch('update', (auth, key, dict(status='Working')))
    check.assertEqual(len(history()), 1)
    permissions(task_access='insert')
    inserted = api.dispatch('insert', (auth, 'sthpw/task', dict(process='insert_only', status='Ready',
        search_type=stype + '?project=' + project, search_code=parent['code'], search_id=parent['id'])))
    permissions()
    api.dispatch('update', (auth, key, dict(status='Complete')))
    completed = api.dispatch('get_by_search_key', (auth, key))
    check.assertTrue(completed['actual_end_date'])
    check.assertEqual([(row['from_status'], row['to_status']) for row in history()],
                      [(None, 'Working'), ('Working', 'Complete')])

    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', admin['ticket'])
        def configure_workflow():
            command.get_transaction().set_sync(False)
            from pyasm.biz import Pipeline
            from pyasm.command.workflow import Workflow
            Pipeline.create('User Workflow dependency', '', stype,
                            '<pipeline><process name="publish" type="manual"/></pipeline>', code='USER_STATUS_WORKFLOW')
            definition = Pipeline.get_by_code('USER_STATUS_WORKFLOW').get_process_sobject('publish')
            definition.set_json_value('workflow', {'on_custom': 'return True'})
            definition.commit()
            Workflow().init(startup=True, quiet=True)
            obj = Search.get_by_search_key(parent['__search_key__'])
            obj.set_value('pipeline_code', 'USER_STATUS_WORKFLOW'); obj.commit()
        command = Command(log_exception=False)
        command.execute = configure_workflow
        Command.execute_cmd(command)
    with check.assertRaisesRegex(SecurityException, 'Script execution'):
        api.dispatch('update', (auth, key, dict(status='Workflow guarded')))
    check.assertEqual(api.dispatch('get_by_search_key', (auth, key))['status'], 'Complete')
    check.assertEqual(len(history()), 2)
    api.dispatch('update', (admin, parent['__search_key__'], dict(pipeline_code='')))

    before = history()
    for options in (dict(task_access='view'), dict(parent_access='view'), dict(project_access='deny'),
                    dict(extra='<rule group="search_filter" search_type="%s" column="code" value="HIDDEN"/>' % stype),
                    dict(extra='<rule group="sobject_column" search_type="sthpw/task" column="status" project="%s" access="deny"/>' % project)):
        permissions(**options)
        with check.assertRaises(SecurityException):
            api.dispatch('update', (auth, key, dict(status='Rejected')))
        check.assertEqual(history(), before)
    permissions()
    original_trigger = Trigger.call_by_key
    def fail_after_history(event, obj, *args, **kwargs):
        result = original_trigger(event, obj, *args, **kwargs)
        if event.get('event') == 'change|sthpw/task|status':
            raise ValueError('late status trigger failure')
        return result
    with patch.object(Trigger, 'call_by_key', side_effect=fail_after_history):
        with check.assertRaisesRegex(ValueError, 'late status trigger failure'):
            api.dispatch('update', (auth, key, dict(status='Failed trigger')))
    check.assertEqual(history(), before)
    check.assertEqual(api.dispatch('get_by_search_key', (auth, key))['status'], 'Complete')
    with check.assertRaises(UnsupportedContract):
        api.dispatch('update_multiple', (auth, {key: dict(status='First partial'),
                     inserted['__search_key__']: dict(search_code='FORGED_PARENT')}))
    check.assertEqual(history(), before)
    check.assertEqual(api.dispatch('get_by_search_key', (auth, key))['status'], 'Complete')
    api.dispatch('delete_sobject', (auth, inserted['__search_key__']))
    with check.assertRaises(UnsupportedContract):
        api.dispatch('update', (auth, key, dict(search_code='FORGED_PARENT')))
    for values in (dict(process='publish', project_code='other', search_type=stype + '?project=' + project,
                        search_code='STATUS_PARENT', search_id=parent['id']),
                   dict(process='publish', project_code=project, search_type=stype + '?project=' + project,
                        search_code='STATUS_PARENT', search_id=parent['id'] + 1)):
        with check.assertRaises(SecurityException):
            api.dispatch('insert', (auth, 'sthpw/task', values))
    with check.assertRaises(SecurityException):
        api.dispatch('insert', (auth, 'sthpw/status_log', dict(login='project_writer', to_status='Forged')))
    with check.assertRaises(SecurityException):
        api.dispatch('delete_sobject', (auth, before[0]['__search_key__']))

    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', token)
        security = Environment.get_security()
        def run(action):
            command = Command(log_exception=False)
            def execute():
                command.get_transaction().set_sync(False)
                return action()
            command.execute = execute
            return Command.execute_cmd(command)
        def late_failure():
            obj = Search.get_by_search_key(key)
            obj.set_value('status', 'Rollback')
            obj.commit()
            check.assertIsNone(Container.get('StatusLog:writing'))
            raise ValueError('late task failure')
        with check.assertRaisesRegex(ValueError, 'late task failure'):
            run(late_failure)
        check.assertEqual(Search.get_by_search_key(key).get_value('status'), 'Complete')
        check.assertIsNone(Container.get('StatusLog:writing'))
        def fail_inside_history():
            obj = Search.get_by_search_key(key)
            obj.set_value('status', 'History failure'); obj.commit()
        original_commit = SObject.commit
        def history_failure(obj, *args, **kwargs):
            result = original_commit(obj, *args, **kwargs)
            if obj.get_base_search_type() == 'sthpw/status_log':
                raise ValueError('history commit failed')
            return result
        with patch.object(SObject, 'commit', new=history_failure):
            with check.assertRaisesRegex(ValueError, 'history commit failed'):
                run(fail_inside_history)
        check.assertIsNone(Container.get('StatusLog:writing'))
        check.assertEqual(Search.get_by_search_key(key).get_value('status'), 'Complete')
        def workflow_dependency():
            from pyasm.command.workflow import BaseProcessTrigger
            obj = Search.get_by_search_key(key)
            obj.set_value('status', 'Workflow pending'); obj.commit()
            handler = BaseProcessTrigger(); handler.input = {}
            handler.get_process_state(Search.get_by_search_key(parent['__search_key__']), 'publish')
            raise ValueError('late Workflow failure')
        with check.assertRaisesRegex(ValueError, 'late Workflow failure'):
            run(workflow_dependency)
        check.assertEqual(Search.get_by_search_key(key).get_value('status'), 'Complete')
        check.assertIsNone(Container.get('Workflow|process_state|' + parent['__search_key__']))
        def revoked_column():
            obj = Search.get_by_search_key(key)
            obj.set_value('status', 'staged value')
            security.get_access_manager().add_xml_rules('<rules><rule group="sobject_column" search_type="sthpw/task" column="status" project="%s" access="deny"/></rules>' % project)
            with check.assertRaises(SecurityException):
                DbContainer.get('sthpw')._do_security_dml('task', {'status': 'bound bypass'},
                                                       obj.get_id_col(), obj.get_id(), sobject=obj)
            with check.assertRaises(SecurityException):
                obj.commit()
        run(revoked_column)
        api.auth.bind_security('project_writer', token)
        def native_create():
            obj = Task.create(Search.get_by_search_key(parent['__search_key__']), 'native', status='Ready')
            search = Search('sthpw/status_log'); search.add_filter('search_code', obj.get_code())
            check.assertEqual(search.get_count(), 1)
            return obj.get_search_key()
        native_key = run(native_create)
        def raw_write():
            with check.assertRaises(UnsupportedContract):
                DbContainer.get('sthpw').do_update("UPDATE status_log SET to_status='raw'")
            with check.assertRaises(SecurityException):
                saved = Search.get_by_search_key(before[0]['__search_key__'])
                saved.set_value('to_status', 'forged'); saved.commit()
        run(raw_write)
        check.assertFalse(security.is_admin())
    check.assertEqual(history(), before)
    api.dispatch('delete_sobject', (auth, native_key))
    with check.assertRaises(LookupError):
        api.dispatch('get_by_search_key', (auth, native_key))
    return dict(history=2, completed=True, rollback=True, protected=True, native_initial_history=1)


class UserStatus(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise_user_status)


class UserStatusParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_writer(cls.store)
        xml = ('<rules><rule group="project" code="*" access="allow"/>'
               '<rule group="search_type" code="contract/entity" access="allow"/>'
               '<rule group="search_type" code="sthpw/task" access="allow"/></rules>')
        cls.cases = [dict(method='user_status_contract', name=project, parent_project=project, rules=xml)
                     for project in ('one', 'two')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['status'], 'Working')
        self.assertEqual(result['project'], case['parent_project'])
        self.assertEqual([row['status'] for row in result['logs']], ['Ready', 'Working'])
        self.assertEqual([row['previous'] for row in result['logs']], ['', 'Ready'])
        self.assertTrue(all(row['linked'] and row['code'] and row['login'] == 'project_writer' for row in result['logs']))
        self.assertEqual(result['remaining_tasks'], 0)
        self.assertEqual(result['remaining_logs'], 0)
        if case['parent_project'] == 'two':
            self.assertTrue(all(row['project'] == 'one' for row in original['logs']))
            self.assertTrue(all(row['project'] == 'two' for row in result['logs']))
            for row in original['logs']:
                row['project'] = 'two'
        self.assertEqual(result, original)


class UserStatusTransport(unittest.TestCase):
    def test_unchanged_sdk_tasks_and_history(self):
        import importlib.util
        import test_transport
        from test_project_writes import set_rules
        from xmlrpc.client import Fault
        test_transport.Transport.setUpClass()
        client = None
        try:
            store = test_transport.Transport.store
            install_writer(store)
            xml = ('<rules><rule group="project" code="one" access="allow"/>'
                   '<rule group="search_type" code="contract/entity" project="one" access="allow"/>'
                   '<rule group="search_type" code="sthpw/task" project="one" access="allow"/></rules>')
            set_rules(store, xml)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.status_client',
                read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url); client.set_project('one')
            client.set_ticket(client.get_ticket('project_writer', PASSWORD))
            task = client.create_task('contract/entity?project=one&code=A', description='SDK · Задача')
            key = task['__search_key__']
            client.update(key, dict(status='Working'))
            logs = client.query('sthpw/status_log', filters=[('search_code', task['code'])])
            self.assertEqual([(row['login'], row['to_status']) for row in logs], [('project_writer', 'Working')])
            set_rules(store, xml.replace('code="sthpw/task" project="one" access="allow"', 'code="sthpw/task" project="one" access="view"'))
            with self.assertRaises(Fault):
                client.update(key, dict(status='Blocked'))
            self.assertEqual(client.get_by_search_key(key)['status'], 'Working')
            with self.assertRaises(Fault):
                client.insert('sthpw/status_log', dict(login='project_writer', to_status='forged'))
            self.assertEqual(len(client.query('sthpw/status_log', filters=[('search_code', task['code'])])), 1)
            set_rules(store, xml.replace('</rules>', '<rule group="api_method" key="create_task" access="deny"/></rules>'))
            from pyasm.common import Config
            config_value = Config.get_value
            with patch.object(Config, 'get_value', side_effect=lambda section, name, *a, **kw:
                              'true' if (section, name) == ('security', 'api_method_restricted') else config_value(section, name, *a, **kw)):
                with self.assertRaises(Fault) as denied:
                    client.create_task('contract/entity?project=one&code=A')
                self.assertEqual(denied.exception.faultCode, 403, denied.exception.faultString)
            self.assertEqual(len(client.query('sthpw/task', filters=[('search_code', 'A')])), 1)
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
