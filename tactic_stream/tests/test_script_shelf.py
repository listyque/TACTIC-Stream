"""Native shelf XML, ownership, conflicts and atomic sidebar assignments."""
import json
import ast
import uuid
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import test_transport
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import hash_password
from tactic_stream.server.script_shelf import shelf_configuration_from_xml, shelf_configuration_xml, GLOBAL


class ScriptShelf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def test_scopes_xml_permissions_conflict_and_rollback(self):
        with test_transport.Transport.store.connection(write=True) as db:
            db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)', ('shelf_user', 'shelf_user', hash_password('shelf-password')))
            db.execute("INSERT INTO login_in_group (login, login_group) VALUES ('shelf_user', 'admin')")
            db.execute('INSERT INTO login (code, login, password) VALUES (?, ?, ?)', ('shelf_reader', 'shelf_reader', hash_password('shelf-password')))
        with test_transport.Transport.proxy(self) as proxy:
            admin = proxy.get_ticket('admin', 'private-test-password')
            user = proxy.get_ticket('shelf_user', 'shelf-password')
            reader = proxy.get_ticket('shelf_reader', 'shelf-password')
            auth = dict(ticket=admin, project='one')
            sidebar_code = proxy.insert(auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler', category='sidebar', login='',
                config='<config><tactic_handler><element name="entity" title="Entities"><display class="LinkWdg"><search_type>contract/entity</search_type><view>table</view></display></element></tactic_handler></config>'))['code']
            proxy.insert(auth, 'config/custom_script', dict(folder='demo', title='hello', language='python', script="return {'project': server.get_project()}"))
            browser_source = "return {project, selected: searchKeys};"
            proxy.insert(auth, 'config/custom_script', dict(folder='demo', title='browser', language='javascript', script=browser_source))
            proxy.insert(auth, 'config/custom_script', dict(folder='demo', title='server-js', language='server_js', script='return server.ping();'))
            def call(action, ticket=admin, status=200, **values):
                req = Request(test_transport.Transport.url + '/admin/script-shelf/' + action, data=json.dumps(dict(ticket=ticket, project='one', **values)).encode(), headers={'Content-Type': 'application/json'})
                try:
                    response = urlopen(req)
                except HTTPError as error:
                    response = error
                with response:
                    self.assertEqual(response.status, status)
                    return json.load(response).get('result')
            empty = call('read')
            self.assertTrue(next(row for row in empty['scripts'] if row['path'] == 'demo/server-js')['runnable'])
            self.assertIn('demo/hello', [row['path'] for row in empty['scripts']])
            self.assertEqual(call('script', path='demo/browser')['script'], browser_source)
            call('script', path='demo/hello', status=400)
            call('script', path='demo/missing', status=400)
            button = dict(id='first', title='Привет', description='A & B', icon='fontawesome-solid:play', script='demo/hello')
            config = dict(scope='global', entryKey='', buttons=[button])
            # Evaluate only the original pure XML functions, without loading Qt or Handler.
            source = ast.parse(Path('D:/grav/Tactic Stream/TH/thlib/ui/script_shelf.py').read_text(encoding='utf-8'))
            functions = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in ('shelf_configuration_xml', 'shelf_configuration_from_xml')]
            native = dict(ElementTree=ET, json=json, uuid=uuid)
            exec(compile(ast.Module(body=functions, type_ignores=[]), 'handler_script_shelf', 'exec'), native)
            native_xml = native['shelf_configuration_xml']([dict(buttonId='first', title=button['title'], description=button['description'], iconName=button['icon'], script=button['script'])], GLOBAL, scope='global')
            self.assertEqual(shelf_configuration_xml(config, GLOBAL), native_xml)
            self.assertEqual(shelf_configuration_from_xml(native_xml, GLOBAL), config)
            self.assertEqual(native['shelf_configuration_from_xml'](shelf_configuration_xml(config, GLOBAL), GLOBAL)['buttons'][0]['buttonId'], 'first')
            shared = call('save', mode='shared', title='Shared shelf', configuration=config, revision=empty['revision'])
            global_row = next(row for row in shared['shelves'] if row['view'] == GLOBAL)
            self.assertEqual(global_row['configuration'], config)
            call('save', mode='personal', title='Invalid', configuration=dict(config, buttons=[button, button]), revision=shared['revision'], status=400)
            call('save', mode='shared', title='Stale', configuration=config, revision=empty['revision'], status=409)
            call('delete', code=global_row['code'], revision=shared['revision'], status=400)
            own = call('save', ticket=user, mode='personal', title='My shelf', configuration=dict(scope='tab', entryKey='contract/entity@entity', buttons=[]), revision=shared['revision'])
            personal = next(row for row in own['shelves'] if row['personal'])
            self.assertTrue(own['canManage'])
            admin_read = call('read')
            self.assertNotIn(personal['code'], [row['code'] for row in admin_read['shelves']])
            call('delete', code=personal['code'], revision=admin_read['revision'], status=400)
            call('save', ticket=reader, mode='shared', title='Forbidden', configuration=config, revision=own['revision'], status=403)
            limited = call('read', ticket=reader)
            self.assertNotIn(personal['code'], [row['code'] for row in limited['shelves']])
            self.assertFalse(next(row for row in limited['scripts'] if row['path'] == 'demo/hello')['executable'])
            # A missing assignment must roll back the shelf insert as well.
            config = dict(scope='preset', entryKey='', buttons=[button])
            call('save', mode='shared', title='Rolled back', configuration=config, entry_key='contract/entity@missing', revision=admin_read['revision'], status=400)
            current = call('read')
            self.assertNotIn('Rolled back', [row['title'] for row in current['shelves']])
            saved = call('save', mode='shared', title='Entity shelf', configuration=config, entry_key='contract/entity@entity', revision=current['revision'])
            row = next(row for row in saved['shelves'] if row['title'] == 'Entity shelf')
            with request_context(RequestContext(test_transport.Transport.store, 'admin', 'one')):
                stored = Search.get_by_code('config/widget_config', row['code'])
                self.assertEqual(shelf_configuration_from_xml(stored.get_value('config'), row['view']), config)
                self.assertEqual(ET.fromstring(Search.get_by_code('config/widget_config', sidebar_code).get_value('config')).findtext('.//script_shelf'), row['view'])
            removed = call('delete', code=row['code'], revision=saved['revision'])
            self.assertNotIn(row['code'], [row['code'] for row in removed['shelves']])
            with request_context(RequestContext(test_transport.Transport.store, 'admin', 'one')):
                self.assertIsNone(ET.fromstring(Search.get_by_code('config/widget_config', sidebar_code).get_value('config')).find('.//script_shelf'))
            self.assertEqual(proxy.execute_python_script(dict(ticket=admin, project='one'), 'demo/hello', {})['info'], {'project': 'one'})


if __name__ == '__main__':
    unittest.main()

