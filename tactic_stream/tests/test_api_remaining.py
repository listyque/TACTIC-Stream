"""Remaining native API variants, with unchanged source calls and real rollback."""
import ast
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_read_parity as reads
import test_transport
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract, SecurityException
from pyasm.search import Search, Delete, DbResource, DbContainer
from pyasm.search.search import RequestContext, request_context
from pyasm.web.api_xmlrpc import ApiClientCmd
from tactic_stream.server.api import Api


class RemainingParity(reads.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        previous_path = sys.path[:]
        cls.addClassCleanup(lambda: sys.path.__setitem__(slice(None), previous_path))
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        cls.cases = [dict(method='api_remaining_contract', name='info', info=True),
                     dict(method='api_remaining_contract', name='command_key'),
                     dict(method='api_remaining_contract', name='direct_command', use_transaction=False),
                     dict(method='api_remaining_contract', name='palette', palette=True)]
        cls.cases.append(dict(method='sql_builder', kind='Delete', name='delete_source_bug',
                              steps=[dict(method='add_filter', args=['code', 'A']),
                                     dict(method='get_statement')]))

    def new_result(self, case):
        import api_remaining_contract
        with tempfile.TemporaryDirectory() as directory:
            from pyasm.search.storage import Store
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', self.ticket)
                if case['method'] == 'sql_builder':
                    from tools.statement_probe import run_builder_case
                    return run_builder_case(case)
                return api_remaining_contract.run(case, api)

    def assert_case_result(self, case, result, original):
        if case['name'] == 'delete_source_bug':
            self.assertTrue(original[-1]['value'].endswith(' AND'))
            self.assertEqual(result[-1]['value'], original[-1]['value'][:-4])
            self.assertEqual(result[-1]['state'], original[-1]['state'])
            return
        self.assertEqual(result, original)

    def test_delete_source_bug_correction_and_rollback(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            sql = DbContainer.get(DbResource.get_default('one'))
            delete = Delete()
            delete.set_database(sql)
            delete.set_table('entity')
            with self.assertRaises(ValueError):
                delete.get_statement()
            with self.assertRaises(ValueError):
                delete.add_filter('code', 'A', "= 'A'; DELETE FROM entity; --")
            delete.add_filter('code', "O'Reilly")
            delete.add_filter('name', None)
            self.assertEqual(delete.get_statement(),
                'DELETE FROM "entity" WHERE "code" = \'O\'\'Reilly\' AND "name" IS NULL')
            before = sql.do_query('SELECT * FROM entity ORDER BY id')

            def execute():
                select_delete = Delete()
                select_delete.set_database(DbResource.get_default('one'))
                select_delete.set_table('entity')
                select_delete.add_filter('code', 'A')
                sql.do_update(select_delete)
                self.assertEqual(sql.get_int("SELECT count(*) FROM entity WHERE code='A'"), 0)
                with sql.read_connection():
                    with self.assertRaises(UnsupportedContract):
                        sql.do_update(select_delete)
                raise ValueError('api9 raw delete rollback')

            command = Command()
            command.kwargs['log_exception'] = False
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'api9 raw delete rollback'):
                Command.execute_cmd(command)
            self.assertEqual(sql.do_query('SELECT * FROM entity ORDER BY id'), before)


    def test_level_delete_preserves_other_levels_and_restores_bytes_on_failure(self):
        from snapshot_levels_contract import level_aliases
        from pyasm.biz import Snapshot
        from pyasm.web.api_xmlrpc import ApiXMLRPC
        from tactic.ui.tools import DeleteCmd
        with tempfile.TemporaryDirectory() as directory:
            from pyasm.search.storage import Store
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                self.api.auth.bind_security('admin', self.ticket)
                api = ApiXMLRPC()
                ticket = dict(ticket=self.ticket, project='one')
                parent = Search.get_by_code('contract/entity', 'A')
                setup = Command()
                def seed():
                    setup.get_transaction().set_sync(False)
                    return level_aliases(api, ticket, parent)
                setup.execute = seed
                Command.execute_cmd(setup)
                level = Search.get_by_code('contract/entity', 'B')
                context = 'level_alias_probe'
                row = api.get_snapshot(ticket, parent.get_search_key(), context, version=1,
                                       level_key=level.get_search_key())
                snapshot = Snapshot.get_by_code(row['code'])
                before_rows = Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()
                before_files = {path: path.read_bytes() for path in (store.data_dir / 'assets').rglob('*')
                                if path.is_file()}
                command = Command()
                def fail():
                    command.get_transaction().set_sync(False)
                    DeleteCmd(sobject=snapshot).execute()
                    raise ValueError('after level deletion')
                command.execute = fail
                with self.assertRaisesRegex(ValueError, 'after level deletion'):
                    Command.execute_cmd(command)
                self.assertEqual((Search('sthpw/snapshot').get_count(), Search('sthpw/file').get_count()), before_rows)
                self.assertEqual({path: path.read_bytes() for path in before_files}, before_files)
                source = Path(Environment.get_upload_dir()) / 'level-alias.txt'
                source.write_text('level 1 newer', encoding='utf-8')
                checkin = Command()
                def add_version():
                    checkin.get_transaction().set_sync(False)
                    return api.simple_checkin(ticket, parent.get_search_key(), context, str(source),
                                              level_key=level.get_search_key(), create_icon=False)
                checkin.execute = add_version
                newer = Command.execute_cmd(checkin)
                promote = Command()
                def remove_newer():
                    promote.get_transaction().set_sync(False)
                    DeleteCmd(search_key=newer['__search_key__']).execute()
                promote.execute = remove_newer
                Command.execute_cmd(promote)
                latest = api.get_paths(ticket, parent.get_search_key(), context, version=-1,
                    level_key=level.get_search_key(), versionless=True, path_types=['lib'])['lib_paths'][0]
                self.assertEqual(Path(latest).read_text(encoding='utf-8'), 'level 1')
                delete = Command()
                def remove():
                    delete.get_transaction().set_sync(False)
                    DeleteCmd(search_key=snapshot.get_search_key()).execute()
                delete.execute = remove
                Command.execute_cmd(delete)
                for level_code, expected in ((None, 'level 0'), ('D', 'level 2'), ('B', None)):
                    key = Search.get_by_code('contract/entity', level_code).get_search_key() if level_code else None
                    for version in (-1, 0):
                        alias = api.get_snapshot(ticket, parent.get_search_key(), context,
                                                 version=version, level_key=key, versionless=True)
                        if expected is None:
                            self.assertEqual(alias, {})
                        else:
                            path = api.get_paths(ticket, parent.get_search_key(), context,
                                version=version, level_key=key, versionless=True, path_types=['lib'])['lib_paths'][0]
                            self.assertEqual(Path(path).read_text(encoding='utf-8'), expected)


class RemainingApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.addClassCleanup(test_transport.Transport.tearDownClass)

    def setUp(self):
        fixture = test_transport.Transport()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.api = Api(test_transport.Transport.store)
        self.auth = dict(ticket=self.api.get_ticket('admin', 'private-test-password'), project='one')
        from pyasm.security.authenticator import hash_password
        self.api.dispatch('insert', (self.auth, 'sthpw/login',
                          {'login':'api9-reader', 'password':hash_password('private-reader-password')}))
        self.reader = dict(ticket=self.api.get_ticket('api9-reader', 'private-reader-password'), project='one')

    def test_write_info_reaches_native_command_and_is_request_local(self):
        observed = []
        def capture(command):
            observed.append((dict(command.get_info()), [obj.get_code() for obj in command.get_sobjects()]))
        with patch.object(ApiClientCmd, 'notify_listeners', capture):
            row = self.api.dispatch('insert', (self.auth, 'contract/entity', {'code':'API9_INFO'}),
                                    {'info': {'title': 'Native', 'nested': {'flag': False}}})
            self.api.dispatch('update', (self.auth, row['__search_key__'], {'name':'Changed'}),
                              {'info': {'phase': 2}})
            self.api.dispatch('insert', (self.auth, 'contract/entity', {'code':'API9_EMPTY'}))
        self.assertEqual(observed[0][0]['title'], 'Native')
        self.assertEqual(observed[0][0]['nested'], {'flag':False})
        self.assertEqual(observed[0][1], ['API9_INFO'])
        self.assertEqual(observed[1][0]['phase'], 2)
        self.assertNotIn('title', observed[1][0])
        self.assertNotIn('phase', observed[2][0])
        self.assertEqual(observed[2][0]['function_name'], 'insert')
        with self.assertRaises(ValueError):
            self.api.dispatch('insert', (self.auth, 'contract/entity', {'code':'API9_BAD'}), {'info':['invalid']})
        self.assertEqual(self.api.dispatch('get_by_code', (self.auth, 'contract/entity', 'API9_BAD')), {})

    def test_keys_bind_arguments_identity_and_resolved_class_policy(self):
        def create_key():
            from pyasm.web import HtmlElement
            return HtmlElement('div').generate_command_key('api_remaining_contract.KeyCmd', {'value':'Bound'})
        with request_context(RequestContext(self.api.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            key = create_key()
            directory = Path(Environment.get_tmp_dir(include_ticket=True))
        args = {'value':'Caller'}
        result = self.api.dispatch('execute_cmd', (self.auth, key, args, {'value':'Form'}))
        self.assertEqual(result['info'], {'value':'Bound', 'form':'Form', 'hooks':['preprocess']})
        self.assertEqual(args, {'value':'Caller'})
        direct = self.api.dispatch('execute_cmd', (self.auth, key, {}, {}), {'use_transaction':False})
        self.assertEqual(direct['info']['hooks'], [])
        for call_key, error in (('$../escape', SecurityException), ('$missing', ValueError),
                                ('api_remaining_contract.KeyCmd', SecurityException)):
            with self.subTest(key=call_key), self.assertRaises(error):
                self.api.dispatch('execute_cmd', (self.auth, call_key))
        with self.assertRaises(SecurityException):
            self.api.dispatch('execute_cmd', (self.reader, key))
        path = directory / ('key_' + key[1:] + '.txt')
        record = json.loads(path.read_text(encoding='utf-8'))
        record['login'] = 'api9-reader'
        path.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaisesRegex(SecurityException, 'another user'):
            self.api.dispatch('execute_cmd', (self.auth, key))
        record['login'] = 'admin'
        path.write_text(json.dumps(record), encoding='utf-8')
        from pyasm.common import Config
        with request_context(RequestContext(self.api.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.auth['ticket'])
            getter = Config.get_value
            with patch.object(Config, 'get_value', side_effect=lambda section, name, *args, **kwargs:
                    'true' if (section, name) == ('security', 'api_cmd_restricted')
                    else getter(section, name, *args, **kwargs)), patch.object(
                    Environment.get_security(), 'check_access', return_value=False):
                with self.assertRaises(SecurityException):
                    self.api.execute_cmd(self.auth, key)

    def test_direct_command_failure_still_rolls_back_outer_api_transaction(self):
        code = "from pyasm.web import HtmlElement\nreturn HtmlElement('div').generate_command_key('api_remaining_contract.KeyCmd')"
        key = self.api.dispatch('execute_python_script', (self.auth, '', {'code':code}))['info']
        for mode in (True, False):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'late command failure'):
                self.api.dispatch('execute_cmd', (self.auth, key, {'write':'API9 rollback', 'fail':True}),
                                  {'use_transaction':mode})
            self.assertEqual(ast.literal_eval(self.api.dispatch('query', (self.auth, 'sthpw/note'),
                                             {'filters':[('note','API9 rollback')]})), [])

    def test_palette_api_and_unsafe_gradient_arguments(self):
        self.assertEqual(ast.literal_eval(self.api.dispatch('eval', (self.reader, '@COLOR(missing)'))), ['#000'])
        self.assertIn('gradient', ast.literal_eval(self.api.dispatch('eval', (self.reader, '@GRADIENT(background,5,-10)')))[0])
        with self.assertRaises(Exception):
            self.api.dispatch('eval', (self.auth, '@GRADIENT(background,__import__("os"),-10)'))
        value = ast.literal_eval(self.api.dispatch('eval', (self.reader, '@PALETTE(DARK)')))
        self.assertEqual(value['color'], '#CCC')

    def test_named_attribute_view_round_trips_and_reorders(self):
        from xml.etree import ElementTree as ET
        for name in ('first', 'second'):
            self.api.dispatch('add_config_element', (self.auth, 'contract/entity', 'named_view', name),
                              {'view_as_attr': True})
        xml = self.api.dispatch('update_config', (self.auth, 'contract/entity', 'named_view', ['second', 'first']))
        root = ET.fromstring(xml)
        node = root.find("view[@name='named_view']")
        self.assertIsNotNone(node)
        self.assertEqual([item.get('name') for item in node.findall('element')], ['second', 'first'])
        self.assertIsNone(root.find('named_view'))
