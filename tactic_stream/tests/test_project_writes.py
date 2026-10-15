"""Real ordinary-user project CRUD, original comparison and bound SQL guards."""
from pathlib import Path
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as ET
from unittest.mock import patch

import test_read_parity as read_tests
from test_search_links import link_fixture
from test_search_self_instances import self_instance_fixture
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, DbContainer
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


PASSWORD = 'private-project-writer-password'


def rules(access='allow', extra=''):
    return ('<rules><rule group="project" code="one" access="allow"/>'
            '<rule group="search_type" code="contract/node" project="one" access="%s"/>'
            '<rule group="search_type" code="contract/node_in_node" project="one" access="%s"/>%s</rules>') % (access, access, extra)


def install_writer(store):
    resource = store.get_db_resource()
    parameter = resource.get_database_impl().get_parameter()
    with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
        db.execute('INSERT INTO login(code,login,password) VALUES (%s,%s,%s)' % ((parameter,) * 3),
                   ('project_writer', 'project_writer', hash_password(PASSWORD)))
        db.execute('INSERT INTO login_group(code,login_group,access_rules) VALUES (%s,%s,%s)' % ((parameter,) * 3),
                   ('project_writers', 'project_writers', rules()))
        db.execute('INSERT INTO login_in_group(code,login,login_group) VALUES (%s,%s,%s)' % ((parameter,) * 3),
                   ('project_writer_group', 'project_writer', 'project_writers'))
        for row in [('USER_REDO', 'project_writer', 'redo', '<transaction/>'),
                    ('OTHER_REDO', 'admin', 'redo', '<transaction/>')]:
            db.execute('INSERT INTO transaction_log(code,login,type,"transaction") VALUES (%s,%s,%s,%s)' % ((parameter,) * 4), row)


def set_rules(store, xml):
    resource = store.get_db_resource()
    parameter = resource.get_database_impl().get_parameter()
    with resource.get_database_impl()._connect(resource) if resource.get_vendor() == 'PostgreSQL' else store.connection(write=True) as db:
        db.execute('UPDATE login_group SET access_rules=%s WHERE code=%s' % (parameter, parameter),
                   (xml, 'project_writers'))


def committed_project_writes(store):
    """Same committed API calls on SQLite/PostgreSQL; no server-side fake results."""
    install_writer(store)
    api = Api(store)
    auth = dict(ticket=api.get_ticket('project_writer', PASSWORD), project='one')
    created = api.dispatch('insert', (auth, 'contract/node', {'code': 'USER_NODE', 'name': "Writer's object · Тест"}))
    assert created['name'] == "Writer's object · Тест"
    owner = created['__search_key__']
    updated = api.dispatch('update', (auth, owner, {'name': "Writer's update · Тест"}))
    assert updated['name'] == "Writer's update · Тест"
    member = 'contract/node?project=one&code=E'
    link = api.dispatch('add_instance', (auth, owner, member))
    assert (link['parent_code'], link['child_code']) == ('USER_NODE', 'E')
    reverse = api.dispatch('add_instance', (auth, member, owner))
    api.dispatch('add_instance', (auth, owner, member))
    api.dispatch('remove_instance', (auth, owner, member))
    assert api.dispatch('get_instances', (auth, owner, 'contract/node')) == []
    assert api.dispatch('get_by_search_key', (auth, reverse['__search_key__']))['child_code'] == 'USER_NODE'
    api.dispatch('remove_instance', (auth, member, owner))
    api.dispatch('delete_sobject', (auth, owner))
    rows = api.dispatch('get_instances', (auth, member, 'contract/node'))
    assert all(row['child_code'] != 'USER_NODE' for row in rows)
    parameter = store.get_db_resource().get_database_impl().get_parameter()
    with store.connection() as db:
        count = db.execute('SELECT count(*) AS total FROM transaction_log WHERE login='+parameter,
                           ('project_writer',)).fetchone()['total']
        assert count > 0
        actions = {row['action'] for row in db.execute('SELECT action FROM sobject_log WHERE login='+parameter,
                                               ('project_writer',)).fetchall()}
        assert {'insert', 'update'} <= actions, actions
        from pyasm.common import Common
        logs = db.execute('SELECT "transaction" FROM transaction_log WHERE login='+parameter,
                          ('project_writer',)).fetchall()
        assert any(node.get('action') == 'delete' and node.get('search_code') == 'USER_NODE'
                   for row in logs for node in ET.fromstring(Common.decompress_transaction(row['transaction'])
                       if row['transaction'].startswith('zlib:') else row['transaction']).findall('sobject'))
        assert db.execute("SELECT count(*) AS total FROM transaction_log WHERE code='USER_REDO'").fetchone()['total'] == 0
        assert db.execute("SELECT count(*) AS total FROM transaction_log WHERE code='OTHER_REDO'").fetchone()['total'] == 1
        indexed = db.execute('SELECT count(*) AS total FROM sobject_list WHERE search_code='+parameter,
                             ('USER_NODE',)).fetchone()['total']
        assert indexed == 0
    return dict(created=created['name'], updated=updated['name'], reverse_preserved=True, deleted=True)


def cases():
    result = []
    for access in ('allow', 'insert', 'edit', 'view'):
        for operation in ('insert', 'update', 'delete'):
            result.append(dict(method='project_write_contract', name=access+'_'+operation,
                               operation=operation, rules=rules(access), access=access))
    for operation in ('insert', 'update'):
        result.append(dict(method='project_write_contract', name='field_deny_'+operation,
                           operation=operation, rules=rules(extra='<rule group="sobject_column" search_type="contract/node" column="name" project="one" access="deny"/>'),
                           access='field_deny'))
    for operation in ('insert', 'update', 'delete'):
        result.append(dict(method='project_write_contract', name='project_deny_'+operation,
                           operation=operation, rules=rules().replace('group="project" code="one" access="allow"',
                                                                     'group="project" code="one" access="deny"'),
                           access='project_deny'))
    return result


class ProjectWrites(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        link_fixture(cls.store)
        self_instance_fixture(cls.store)
        install_writer(cls.store)
        cls.cases = cases()

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='project-write-compare-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        operation, access = case['operation'], case['access']
        allowed = access == 'allow' or (access == 'insert' and operation != 'delete') or (access == 'edit' and operation == 'update')
        self.assertEqual(result['allowed'], allowed)
        if allowed:
            self.assertEqual(result, original)
        elif access == 'field_deny' or (operation == 'delete' and access != 'project_deny'):
            self.assertFalse(original['allowed'])
        else:
            # Source only checked columns, allowing view/edit users to insert.
            self.assertTrue(original['allowed'])
            self.assertEqual(result['error'], 'SecurityException')

    def private_store(self):
        directory = tempfile.TemporaryDirectory(prefix='project-write-native-')
        self.addCleanup(directory.cleanup)
        store = Store(Path(directory.name) / 'data')
        shutil.copytree(self.store.data_dir, store.data_dir)
        return store

    def test_committed_api_and_permissions(self):
        store = self.private_store()
        # The shared committed check installs its own identity.
        with store.connection(write=True) as db:
            db.execute("DELETE FROM login_in_group WHERE code='project_writer_group'")
            db.execute("DELETE FROM login_group WHERE code='project_writers'")
            db.execute("DELETE FROM login WHERE code='project_writer'")
            db.execute("DELETE FROM transaction_log WHERE code IN ('USER_REDO','OTHER_REDO')")
        self.assertTrue(committed_project_writes(store)['deleted'])
        api = Api(store)
        auth = dict(ticket=api.get_ticket('project_writer', PASSWORD), project='one')
        owner = 'contract/node?project=one&code=D'
        for access in ('view', 'edit', 'insert', 'allow'):
            set_rules(store, rules(access))
            if access == 'view':
                with self.assertRaises(SecurityException):
                    api.dispatch('update', (auth, owner, {'name': 'denied'}))
            else:
                self.assertEqual(api.dispatch('update', (auth, owner, {'name': access}))['name'], access)
            if access in ('view', 'edit'):
                with self.assertRaises(SecurityException):
                    api.dispatch('insert', (auth, 'contract/node', {'code': 'DENIED_'+access}))
                with self.assertRaises(SecurityException):
                    api.dispatch('add_instance', (auth, owner, 'contract/node?project=one&code=E'))
            if access != 'allow':
                with self.assertRaises(SecurityException):
                    api.dispatch('delete_sobject', (auth, owner))
        with self.assertRaises(SecurityException):
            api.dispatch('insert', (auth, 'contract/node?project=two', {'code': 'OTHER_PROJECT'}))
        for kind in ('config/custom_script', 'sthpw/project', 'sthpw/task', 'sthpw/note', 'sthpw/snapshot'):
            with self.assertRaises(SecurityException):
                api.dispatch('insert', (auth, kind, {'code': 'UNAUTHORIZED'}))
        with self.assertRaises(SecurityException):
            api.dispatch('execute_python_script', (auth, ''), {'kwargs': {'code': 'return 1'}})

    def test_raw_sql_staged_rules_read_filters_and_trigger_failure_rollback(self):
        from pyasm.command import Trigger
        store = self.private_store()
        api = Api(store)
        auth = dict(ticket=api.get_ticket('project_writer', PASSWORD), project='one')
        with request_context(RequestContext(store, 'project_writer', 'one')):
            security = api.auth.bind_security('project_writer', auth['ticket'])
            command = Command()
            def execute():
                from pyasm.biz import Project
                sql = DbContainer.get(Project.get_db_resource_by_search_type('contract/node?project=one'))
                with self.assertRaises(UnsupportedContract):
                    sql.do_update("UPDATE node SET name='raw SQL'")
                with self.assertRaises(UnsupportedContract):
                    sql._do_update("DELETE FROM node", security_write=True)
                obj = Search.get_by_code('contract/node', 'D')
                with self.assertRaises(UnsupportedContract):
                    sql._do_security_dml('node', sobject=obj)
                obj.set_value('name', 'staged')
                manager = security.get_access_manager()
                manager.add_xml_rules('<rules><rule group="sobject_column" search_type="contract/node" column="name" project="one" access="deny"/></rules>')
                with self.assertRaises(SecurityException):
                    obj.commit()
                with self.assertRaises(SecurityException):
                    sql._do_security_dml('node', {'name': 'bound bypass'}, obj.get_id_col(), obj.get_id(), sobject=obj)
            command.execute = execute
            Command.execute_cmd(command)
        set_rules(store, rules(extra='<rule group="search_filter" search_type="contract/node" column="code" value="E"/>'))
        with request_context(RequestContext(store, 'project_writer', 'one')):
            api.auth.bind_security('project_writer', auth['ticket'])
            # A cached/Sudo-loaded object cannot evade current row policy at commit.
            from pyasm.security import Sudo
            sudo = Sudo()
            try:
                obj = Search.get_by_id('contract/node', 4)
            finally:
                sudo.exit()
            self.assertIsNotNone(obj)
            obj.set_value('name', 'hidden row')
            command = Command()
            command.execute = obj.commit
            with self.assertRaises(SecurityException):
                Command.execute_cmd(command)
        set_rules(store, rules())
        original = Trigger.call_by_key
        with store.connection() as db:
            before = [db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                      for table in ('transaction_log', 'sobject_log', 'sobject_list')]
        def fail(key, obj, *args, **kwargs):
            result = original(key, obj, *args, **kwargs)
            if key.get('event') == 'insert|contract/node':
                raise ValueError('ordinary writer trigger failure')
            return result
        with patch.object(Trigger, 'call_by_key', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'ordinary writer trigger failure'):
                api.dispatch('insert', (auth, 'contract/node', {'code': 'ROLLBACK_USER', 'name': 'rollback'}))
        admin = dict(ticket=self.ticket, project='one')
        with self.assertRaises(LookupError):
            api.dispatch('get_by_search_key', (admin, 'contract/node?project=one&code=ROLLBACK_USER'))
        with store.connection() as db:
            self.assertEqual([db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                              for table in ('transaction_log', 'sobject_log', 'sobject_list')], before)
        self.assertEqual(api.dispatch('get_by_search_key', (admin, 'contract/node?project=one&code=D'))['name'], 'Leaf')
        data = {'contract/node?project=one&code=D': {'name': 'partial'},
                'contract/node?project=two&code=E': {'name': 'denied project'}}
        with self.assertRaises(SecurityException):
            api.dispatch('update_multiple', (auth, data))
        self.assertEqual(api.dispatch('get_by_search_key', (admin, 'contract/node?project=one&code=D'))['name'], 'Leaf')


class ProjectWritesTransport(unittest.TestCase):
    def test_unchanged_sdk_ordinary_crud_links_and_denials(self):
        import importlib.util
        from xmlrpc.client import Fault
        import test_transport
        test_transport.Transport.setUpClass()
        client = None
        try:
            self_instance_fixture(test_transport.Transport.store)
            install_writer(test_transport.Transport.store)
            spec = importlib.util.spec_from_file_location('tactic_client_lib.project_write_client',
                        read_tests.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            client = original.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            client.set_project('one')
            client.set_ticket(client.get_ticket('project_writer', PASSWORD))
            row = client.insert('contract/node', {'code': 'SDK_USER', 'name': "SDK writer's object"})
            key = row['__search_key__']
            self.assertEqual(client.update(key, {'name': 'SDK updated'})['name'], 'SDK updated')
            member = 'contract/node?project=one&code=E'
            link = client.server.add_instance(client.ticket, key, member)
            self.assertEqual((link['parent_code'], link['child_code']), ('SDK_USER', 'E'))
            client.server.remove_instance(client.ticket, key, member)
            self.assertEqual(client.server.get_instances(client.ticket, key, 'contract/node'), [])
            set_rules(test_transport.Transport.store, rules('view'))
            with self.assertRaises(Fault):
                client.update(key, {'name': 'must not change'})
            self.assertEqual(client.get_by_search_key(key)['name'], 'SDK updated')
            set_rules(test_transport.Transport.store, rules())
            client.delete_sobject(key)
            self.assertEqual(client.query('contract/node', filters=[('code', 'SDK_USER')]), [])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
