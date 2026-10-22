"""Public SDK object lifecycle uses native ACLs and one rollback boundary."""
import unittest
from ast import literal_eval
import ast
import json
from pathlib import Path
from urllib.request import urlopen
from xmlrpc.client import Fault

import test_transport
from pyasm.security.authenticator import hash_password
from tactic_client_lib import TacticServerStub


class ApiCompatibility(unittest.TestCase):
    def setUp(self):
        test_transport.Transport.setUpClass()
        self.addCleanup(test_transport.Transport.tearDownClass)
        self.url = test_transport.Transport.url
        self.proxy = test_transport.Transport.proxy(self)
        self.admin = dict(ticket=self.proxy.get_ticket('admin', 'private-test-password'), project='one', language='python')

    def client(self, name, access='allow', extra=''):
        rules = ('<rules><rule group="project" code="one" access="allow"/>'
            '<rule group="project" key="one" access="allow"/>'
            '<rule group="search_type" code="contract/entity" access="'+access+'"/>'+extra+'</rules>')
        self.proxy.insert(self.admin, 'sthpw/login_group', dict(login_group=name, access_rules=rules))
        self.proxy.insert(self.admin, 'sthpw/login', dict(login=name, password=hash_password('private-user-password')))
        self.proxy.insert(self.admin, 'sthpw/login_in_group', dict(login=name, login_group=name))
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(self.url)
        client.set_project('one')
        client.set_ticket(client.get_ticket(name, 'private-user-password'))
        self.addCleanup(client.server.__exit__, None, None, None)
        return client

    def test_remaining_available_entry_points_use_native_contracts(self):
        generated = self.proxy.generate_ticket(self.admin)
        self.assertIsInstance(generated, str)
        self.assertTrue(generated)
        with self.assertRaises(Fault):
            self.proxy.ping(dict(ticket=generated, project='one'))
        self.assertIsInstance(literal_eval(self.proxy.test_speed(self.admin)), list)
        with self.assertRaises(Fault) as error:
            self.proxy.test_error(self.admin)
        self.assertEqual(error.exception.faultCode, 500)
        self.assertEqual(error.exception.faultString, 'Internal server error')
        self.assertEqual(self.proxy.get_doc_link(self.admin, 'absent_contract_alias'), 'none_found')
        self.assertEqual(self.proxy.get_plugin_dir(self.admin, 'API_CONTRACT'), '/tactic/plugins/API_CONTRACT')
        self.assertEqual(self.proxy.get_plugin_dir(self.admin, 'TACTIC_CONTRACT'), '/tactic/builtin_plugins/TACTIC_CONTRACT')
        self.proxy.add_interaction(self.admin, 'api-contract-action', dict(origin='private SDK fixture'))
        self.assertEqual(self.proxy.get_interaction_count(self.admin, 'api-contract-action'), 1)
        self.assertTrue(self.proxy.set_config_definition(self.admin, 'SideBarWdg', 'api_contract'))
        definition = self.proxy.get_config_definition(self.admin, 'SideBarWdg', 'definition', 'api_contract')
        self.assertIn('name="api_contract"', definition)
        self.assertIn('LinkWdg', definition)
        health = self.proxy.send_rest_request(self.admin, 'GET', self.url + '/health')
        self.assertIsInstance(health, dict)
        transaction = dict(self.admin, ticket=self.proxy.start(self.admin, 'one', 'Diagnostic state'))
        try:
            self.assertTrue(self.proxy.set_project(transaction, 'one'))
        finally:
            self.proxy.abort(transaction)

    def test_original_sdk_object_lifecycle_and_snapshot_ownership(self):
        client = self.client('writer')
        item = client.get_unique_sobject('contract/entity', dict(name='API lifecycle', amount=1))
        self.assertEqual(client.get_unique_sobject('contract/entity', dict(name='API lifecycle', amount=1))['code'], item['code'])
        self.assertEqual(client.insert_update(item['__search_key__'], dict(amount=2))['amount'], 2)
        clone = client.server.clone_sobject(client.ticket, item['__search_key__'], dict(name='Native clone'))
        self.assertNotEqual(clone['code'], item['code'])
        self.assertEqual(client.retire_sobject(clone['__search_key__'])['s_status'], 'retired')
        logs = literal_eval(self.proxy.query(self.admin, 'sthpw/retire_log', [['search_code', clone['code']]]))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['login'], 'writer')
        self.assertTrue(logs[0]['code'])
        self.assertIsNone(client.reactivate_sobject(clone['__search_key__'])['s_status'])
        snapshot = client.create_snapshot(item['__search_key__'], 'publish', is_current=False)
        self.assertEqual(snapshot['login'], 'writer')
        self.assertEqual(snapshot['search_code'], item['code'])
        self.assertTrue(client.lock_sobject(item['__search_key__'], 'publish'))
        self.assertEqual(client.get_snapshot(item['__search_key__'], 'publish', version=1)['lock_login'], 'writer')
        self.assertTrue(client.unlock_sobject(item['__search_key__'], 'publish'))
        self.assertTrue(client.set_current_snapshot(snapshot['code'])['is_current'])
        client.delete_sobject(clone['__search_key__'])

    def test_original_sdk_file_checkin_and_local_append_rollback(self):
        client = self.client('file_writer', extra='<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/>')
        key = 'contract/entity?project=one&code=A'
        source = Path(test_transport.Transport.temp.name) / 'sdk-owned.bin'
        source.write_bytes(b'original SDK check-in')
        snapshot = client.simple_checkin(key, 'api/files', str(source), mode='upload', create_icon=False)
        self.assertEqual(snapshot['login'], 'file_writer')
        first = snapshot['__file_sobjects__'][0]
        stored = Path(first['checkin_dir']) / first['file_name']
        self.assertEqual(stored.read_bytes(), source.read_bytes())
        extra = source.with_name('sdk-extra.bin')
        extra.write_bytes(b'local SDK append must roll back')
        client.upload_file(str(extra))
        code = """from pyasm.common import Container
previous = Container.get('Checkin:writing')
server.add_file(kwargs['snapshot'], kwargs['filename'], file_type='extra', create_icon=False)
assert Container.get('Checkin:writing') is previous
server.update(kwargs['parent'], {'missing_column': 'fail'})
"""
        with self.assertRaises(Fault) as failure:
            client.execute_python_script('', dict(code=code, snapshot=snapshot['code'], filename=extra.name, parent=key))
        self.assertIn('missing_column', failure.exception.faultString)
        files = client.get_snapshot(key, 'api/files', include_files=True)['__files__']
        self.assertEqual([row['code'] for row in files], [first['code']])
        self.assertEqual(stored.read_bytes(), source.read_bytes())

    def test_readers_field_denials_and_system_commands_remain_denied(self):
        reader = self.client('reader', 'view')
        key = 'contract/entity?project=one&code=A'
        snapshot = self.proxy.create_snapshot(self.admin, key, 'publish')
        for method, args in [('retire_sobject', (key,)), ('clone_sobject', (key,)),
            ('insert_update', (key, dict(amount=2))),
            ('get_unique_sobject', ('contract/entity', dict(name='Cannot create'))),
            ('create_snapshot', (key, 'publish')), ('lock_sobject', (key, 'publish')),
            ('unlock_sobject', (key, 'publish')), ('set_current_snapshot', (snapshot['code'],))]:
            with self.subTest(method=method), self.assertRaises(Fault):
                getattr(reader.server, method)(reader.ticket, *args)
        writer = self.client('limited', extra='<rule group="sobject_column" search_type="contract/entity" column="s_status" project="one" access="deny"/>')
        with self.assertRaises(Fault):
            writer.retire_sobject(key)
        self.assertIsNone(self.proxy.get_by_search_key(self.admin, key)['s_status'])
        for method, args in [('insert', ('sthpw/login', dict(login='intruder'))),
            ('insert', ('sthpw/retire_log', dict(search_type='contract/entity?project=one', search_code='A', login='limited'))),
            ('execute_cmd', ('tactic.core.schema_commands.SearchTypeCreatorCmd', dict(search_type_name='one/intruder'))),
            ('create_snapshot', ('contract/entity?project=two&code=A', 'publish'))]:
            with self.subTest(method=method), self.assertRaises(Fault):
                getattr(writer, method)(*args)

    def test_late_script_failure_rolls_back_lifecycle_and_snapshot(self):
        client = self.client('rollback', extra='<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/>')
        key = 'contract/entity?project=one&code=A'
        before = self.proxy.eval(self.admin, '@COUNT(sthpw/snapshot)')
        script = """
from pyasm.common import Container
previous_checkin = Container.get('Checkin:writing')
assert server.server.missing_method('unknown', []) is False
assert server.fast_ping() == 'OK'
server.retire_sobject('contract/entity?project=one&code=A')
server.reactivate_sobject('contract/entity?project=one&code=A')
server.create_snapshot('contract/entity?project=one&code=A', 'rollback/api')
assert Container.get('Checkin:writing') is previous_checkin
server.update('contract/entity?project=one&code=A', {'missing_column': 'fail'})
"""
        with self.assertRaises(Fault) as failure:
            client.execute_python_script('', dict(code=script))
        self.assertIn('missing_column', failure.exception.faultString)
        self.assertIsNone(self.proxy.get_by_search_key(self.admin, key)['s_status'])
        self.assertEqual(self.proxy.eval(self.admin, '@COUNT(sthpw/snapshot)'), before)

    def test_current_handler_batch_naming_and_note_history(self):
        source = Path('D:/grav/Tactic Stream/TH/thlib/tactic_query.py').read_text(encoding='utf-8-sig')
        names = ('get_virtual_snapshot_extended', 'get_virtual_snapshots_extended', 'change_note')
        procedures = '\n\n'.join(ast.get_source_segment(source, node) for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef) and node.name in names)

        def call(name, **params):
            code = procedures + '\nreturn ' + name + '(**params)'
            return json.loads(self.proxy.execute_python_script(self.admin, '', dict(code=code, params=params))['info'])

        key = 'contract/entity?project=one&code=A'
        files = json.dumps([['payload', dict(t=['main'], e=['bin'], s=[''], p=[''], m={})]])
        arguments = dict(search_key=key, context='publish', files_dict=files, keep_file_name=True)
        before = self.proxy.eval(self.admin, '@COUNT(sthpw/snapshot)')
        expected = call('get_virtual_snapshot_extended', **arguments)
        self.assertEqual(call('get_virtual_snapshots_extended', operations=[arguments, arguments]),
            [dict(result=expected, error=''), dict(result=expected, error='')])
        with self.assertRaises(Fault):
            call('get_virtual_snapshots_extended', operations=[arguments] * 51)
        self.assertEqual(self.proxy.eval(self.admin, '@COUNT(sthpw/snapshot)'), before)
        note = self.proxy.create_note(self.admin, key, 'Original note', 'publish')
        self.assertEqual(call('change_note', note_search_key=note['__search_key__'], action='edit', body='Edited note'), {'edited': True})
        edited = self.proxy.get_by_search_key(self.admin, note['__search_key__'])
        self.assertEqual(edited['note'], 'Edited note')
        self.assertEqual(json.loads(edited['metadata'])['editHistory'][0]['body'], 'Original note')
        self.assertEqual(call('change_note', note_search_key=note['__search_key__'], action='delete'), {'deleted': True})

    def test_missing_diagnostic_preserves_source_false_and_unknown_rpc_fault(self):
        self.assertIs(self.proxy.missing_method('unknown', ['private-argument']), False)
        with self.assertRaises(Fault):
            self.proxy.unknown(self.admin)

    def test_catalog_and_bilingual_help_expose_the_remaining_contracts(self):
        from tactic_stream.server.api import SUPPORTED_METHODS
        with urlopen(self.url + '/api/documentation') as response:
            catalog = json.load(response)
        methods = {item['name']: item for item in catalog['methods']}
        self.assertEqual(len(methods), 129)
        self.assertEqual({name for name, item in methods.items() if item['status'] == 'available'}, SUPPORTED_METHODS)
        self.assertFalse(catalog['full_api_parity_verified'])
        self.assertFalse(methods['missing_method']['requires_ticket'])
        self.assertEqual({name for name, item in methods.items() if item['status'] == 'not_implemented'},
            set())
        for language in ('en', 'ru'):
            with urlopen(self.url + '/ui/help/api_compatibility.' + language + '.md') as response:
                help_text = response.read().decode('utf-8')
            for method in ('set_palette', 'get_widget', 'get_column_widgets', 'set_application_state', 'execute_js_script'):
                self.assertIn(method, help_text)
            self.assertIn('full_api_parity_verified', help_text)


if __name__ == '__main__':
    unittest.main()
