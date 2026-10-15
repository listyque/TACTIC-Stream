"""Directional native writes: real source comparisons and XML-RPC/SQL effects."""
import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from test_search_links import link_fixture
from test_search_self_instances import self_instance_fixture
from tools.snapshot_probe import run_snapshot_case
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api


def cases():
    result = []
    for id_keys in (False, True):
        for operation, owner, member in (('create', 'D', 'E'), ('roundtrip', 'D', 'E'),
                                         ('reverse', 'D', 'E'), ('self', 'D', 'D'),
                                         ('remove', 'A', 'B'), ('remove', 'B', 'A'),
                                         ('remove', 'A', 'C'), ('remove', 'B', 'D')):
            result.append(dict(method='self_instance_contract', project='one', id_keys=id_keys,
                               name=f'self_write_{id_keys}_{operation}_{owner}_{member}',
                               operation=operation, owner=owner, member=member))
    return result


class SelfInstanceWrites(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        link_fixture(cls.store)
        self_instance_fixture(cls.store)
        cls.cases = cases()

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='self-instance-write-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result['before'], original['before'])
        self.assertEqual(len(result['before']), 10)
        operation, owner, member = case['operation'], case['owner'], case['member']
        identity = dict(A=1, B=2, C=3, D=4, E=5)
        parent_index = 2 if case['id_keys'] else 0
        owner_key = identity[owner] if case['id_keys'] else owner
        owned = [[None if value == '' else value for value in row[:4]]
                 for row in result['after_add'] if row[parent_index] == owner_key and row[4] != 'retired']
        self.assertEqual(result['owned'], owned)
        if case['id_keys']:
            pair = [None, None, identity[owner], identity[member], None]
            # Original resolves child twice, leaving the member end unset.
            if result['created'] is not None:
                self.assertEqual(result['created'], [None, None, identity[owner], identity[member]])
                self.assertEqual(original['created'], [None, None, identity[member], None])
        else:
            pair = [owner, member, None, None, None]
            if result['created'] is not None:
                self.assertEqual(result['created'], [owner, member, None, None])
                self.assertEqual(original['created'], [member, None, None, None])
        if operation == 'create':
            self.assertEqual(result['after_remove'], result['before'] + [pair])
        elif operation == 'roundtrip':
            self.assertEqual(result['after_remove'], result['before'])
            self.assertNotEqual(original['after_remove'], original['before'])
        elif operation == 'reverse':
            reverse = [None, None, identity[member], identity[owner], None] if case['id_keys'] else [member, owner, None, None, None]
            self.assertEqual(result['after_remove'], result['before'] + [reverse])
        elif operation == 'self':
            self.assertEqual(result['after_remove'], result['before'])
            self.assertNotEqual(original['after_remove'], original['before'])
        else:
            expected = [row for row in result['before'] if row[4] == 'retired' or
                        (row[2:4] if case['id_keys'] else row[:2]) !=
                        ([identity[owner], identity[member]] if case['id_keys'] else [owner, member])]
            self.assertEqual(result['after_remove'], expected)
            self.assertEqual(original['after_remove'], original['before'])

    def test_unsaved_stale_missing_cross_project_and_invalid_schema_are_rejected(self):
        from pyasm.common.errors import UnsupportedContract
        from pyasm.command import Command
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            owner = Search.get_by_code('contract/node', 'D')
            member = Search.get_by_code('contract/node', 'E')
            original_count = Search('contract/node_in_node').get_count()
            for operation in (owner.add_instance, owner.remove_instance):
                with self.assertRaisesRegex(ValueError, 'must be saved'):
                    operation(SearchType.create('contract/node'))
                with self.assertRaisesRegex(UnsupportedContract, 'one type, project'):
                    operation(Search.get_by_code('contract/node?project=two', 'E'))
            with self.assertRaisesRegex(UnsupportedContract, 'one type, project'):
                owner.get_instances('contract/node?project=two')
            member.set_value('code', 'pending key')
            try:
                with self.assertRaisesRegex(ValueError, 'key is empty or changed'):
                    owner.add_instance(member)
            finally:
                member.set_value('code', 'E')
            missing = SearchType.create('contract/node')
            missing.set_value('id', 999)
            missing.set_value('code', 'missing')
            with self.assertRaisesRegex(LookupError, 'no longer exists'):
                owner.remove_instance(missing)
            schema = owner.get_schema()
            parent = next(node for node in schema.xml.findall('connect')
                          if node.get('from') == 'contract/node_in_node' and node.get('path') == 'parent')
            old_column = parent.get('from_col')
            parent.set('from_col', 'parent_code')
            schema.relationships.clear()
            try:
                with self.assertRaisesRegex(UnsupportedContract, 'different link columns'):
                    owner.add_instance(member)
            finally:
                parent.set('from_col', old_column)
                schema.relationships.clear()
            self.assertEqual(Search('contract/node_in_node').get_count(), original_count)
            command = Command()
            def abort():
                owner.add_instance(member)
                raise ValueError('self write rollback')
            command.execute = abort
            with self.assertRaisesRegex(ValueError, 'self write rollback'):
                Command.execute_cmd(command)
            self.assertEqual(Search('contract/node_in_node').get_count(), original_count)

    def test_committed_api_direction_duplicates_self_links_and_trigger_failure_rollback(self):
        from pyasm.command import Trigger
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='self-instance-api-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            auth = dict(ticket=self.ticket, project='one')
            owner = 'contract/node?project=one&code=D'
            member = 'contract/node?project=one&code=E'
            def add(first, second):
                return api.dispatch('add_instance', (auth, first, second))
            def remove(first, second):
                return api.dispatch('remove_instance', (auth, first, second))
            first = add(owner, member)
            self.assertEqual((first['parent_code'], first['child_code']), ('D', 'E'))
            reverse = add(member, owner)
            duplicate = add(owner, member)
            self.assertNotEqual(first['__search_key__'], duplicate['__search_key__'])
            own = add(owner, owner)
            self.assertEqual(len(api.dispatch('get_instances', (auth, owner, 'contract/node?project=one'))), 4)
            remove(owner, member)
            for removed in (first, duplicate):
                with self.assertRaisesRegex(LookupError, 'does not exist'):
                    api.dispatch('get_by_search_key', (auth, removed['__search_key__']))
            self.assertEqual(api.dispatch('get_by_search_key', (auth, reverse['__search_key__']))['parent_code'], 'E')
            self.assertEqual(api.dispatch('get_by_search_key', (auth, own['__search_key__']))['child_code'], 'D')
            remove(owner, member)
            remove(owner, owner)
            remove(member, owner)
            self.assertEqual([row['code'] for row in api.dispatch('get_instances', (auth, owner, 'contract/node'))], ['N6'])
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                before = [Search(kind).get_count() for kind in ('contract/node_in_node', 'sthpw/sobject_log')]
            original_insert = Trigger.call_by_key
            def fail_insert(key, obj, *args, **kwargs):
                result = original_insert(key, obj, *args, **kwargs)
                if key.get('event') == 'insert|contract/node_in_node':
                    self.assertEqual((obj.get_value('parent_code'), obj.get_value('child_code')), ('D', 'E'))
                    raise ValueError('self-instance insert trigger failure')
                return result
            with patch.object(Trigger, 'call_by_key', side_effect=fail_insert):
                with self.assertRaisesRegex(ValueError, 'insert trigger failure'):
                    add(owner, member)
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                self.assertEqual([Search(kind).get_count() for kind in ('contract/node_in_node', 'sthpw/sobject_log')], before)
            original_delete = Trigger.call
            def fail_delete(obj, event, *args, **kwargs):
                result = original_delete(obj, event, *args, **kwargs)
                if event == 'delete|contract/node_in_node':
                    raise ValueError('self-instance delete trigger failure')
                return result
            with patch.object(Trigger, 'call', side_effect=fail_delete):
                with self.assertRaisesRegex(ValueError, 'delete trigger failure'):
                    remove('contract/node?project=one&code=A', 'contract/node?project=one&code=B')
            remaining = api.dispatch('get_instances', (auth, 'contract/node?project=one&code=A', 'contract/node'))
            self.assertEqual([row['code'] for row in remaining], ['N1', 'N2', 'N3', 'N8'])

    def test_link_write_permissions(self):
        from pyasm.security.authenticator import hash_password
        from pyasm.common.errors import SecurityException
        with tempfile.TemporaryDirectory(prefix='self-instance-permissions-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            with store.connection(write=True) as db:
                db.execute("INSERT INTO login(code,login,password) VALUES ('self_writer','self_writer',?)", (hash_password('private-reader-password'),))
                db.execute("INSERT INTO login_group(code,login_group,access_rules) VALUES ('self_writers','self_writers','<rules/>')")
                db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES ('self_writer_group','self_writer','self_writers')")
            auth = dict(ticket=api.get_ticket('self_writer', 'private-reader-password'), project='one')
            owner, member = 'contract/node?project=one&code=A', 'contract/node?project=one&code=B'
            for access in ('view', 'deny'):
                rules = '<rules><rule group="project" code="one" access="allow"/><rule group="search_type" code="contract/node" project="one" access="allow"/><rule group="search_type" code="contract/node_in_node" project="one" access="%s"/></rules>' % access
                with store.connection(write=True) as db:
                    db.execute("UPDATE login_group SET access_rules=? WHERE code='self_writers'", (rules,))
                if access == 'view':
                    self.assertEqual(len(api.dispatch('get_instances', (auth, owner, 'contract/node'))), 4)
                else:
                    with self.assertRaises(SecurityException):
                        api.dispatch('get_instances', (auth, owner, 'contract/node'))
                for method in ('add_instance', 'remove_instance'):
                    with self.assertRaises(SecurityException):
                        api.dispatch(method, (auth, owner, member))
                admin = dict(ticket=self.ticket, project='one')
                self.assertEqual(len(api.dispatch('get_instances', (admin, owner, 'contract/node'))), 4)
