"""Shared native layout XML, revisions, assignments and permissions."""
import ast
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.widget_configuration import WidgetConfigConflict
from tactic_stream.server.workspace_layout import layout_configuration_xml, workspace_layout_request as request


class WorkspaceLayout(unittest.TestCase):
    def test_native_xml_shared_presets_revisions_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
            Config.reload_config()
            store = Store(Path(directory)); store.initialize(hash_password('layout-test-password'))
            self.exercise(store)

    def exercise(self, store):
        api = Api(store); ticket = api.get_ticket('admin', 'layout-test-password')
        auth = dict(ticket=ticket, project='admin', language='python')
        layout = dict(layout=dict(type='stack', panels=['results'], active='results'), panels=[dict(panel_id='results', title='Results', kind='results',
            x=0., y=0., width=1., height=1., visible=True, closable=False, z=1, dock_area='center', detached=False, previous_dock_area='')])
        source = Path('D:/code/th_codex/thlib/ui/workspace_layout_presets.py')
        if source.exists():
            tree = ast.parse(source.read_text(encoding='utf-8'))
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith('layout_configuration_')]
            original = dict(json=json, ElementTree=ElementTree)
            exec(compile(ast.Module(functions, []), str(source), 'exec'), original)
            xml = layout_configuration_xml(layout, 'workspace_layout@reference')
            self.assertEqual(original['layout_configuration_from_xml'](xml, 'workspace_layout@reference'), layout)
            self.assertEqual(original['layout_configuration_xml'](layout, 'workspace_layout@reference'), xml)
        with request_context(RequestContext(store, 'admin', 'admin')):
            api.auth.bind_security('admin', ticket)
            loaded = request('read', {})
            saved = request('save', dict(title='Split', configuration=layout, revision=loaded['revision']))
            row = saved['presets'][0]
            self.assertEqual(row['configuration'], layout)
            self.assertTrue(row['view'].startswith('workspace_layout@'))
            with self.assertRaises(WidgetConfigConflict):
                request('save', dict(title='Stale', configuration=layout, revision=loaded['revision']))
            with self.assertRaises(ValueError):
                request('save', dict(title='split', configuration=layout, revision=saved['revision']))
            record = Search.get_by_code('config/widget_config', row['code'])
            updated = api.dispatch('update', (auth, record.get_search_key(), dict(description='Preserve Handler metadata')))
            self.assertEqual(updated['description'], 'Preserve Handler metadata')
            loaded = request('read', {})
            saved = request('save', dict(code=row['code'], title='Split', configuration=layout, revision=loaded['revision']))
            search = Search('config/widget_config'); search.add_filter('code', row['code'])
            self.assertEqual(search.get_sobject().get_value('description'), 'Preserve Handler metadata')
            sidebar = api.dispatch('insert', (auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler',
                config=f'<config><tactic_handler><element name="people"><display><layout_preset>{row["view"]}</layout_preset></display></element></tactic_handler></config>')))
            assigned = request('read', {})
            self.assertEqual(assigned['presets'][0]['assignedCount'], 1)
            with self.assertRaises(ValueError):
                request('delete', dict(code=row['code'], revision=assigned['revision']))
            api.dispatch('delete_sobject', (auth, sidebar['__search_key__']))
            loaded = request('read', {})
            invalid = dict(panels=layout['panels'], layout=dict(type='stack', panels=['results', 'results'], active='results'))
            with self.assertRaises(ValueError):
                request('save', dict(title='Invalid', configuration=invalid, revision=loaded['revision']))
            self.assertEqual(request('read', {})['presets'][0]['view'], row['view'])
            self.assertEqual(request('delete', dict(code=row['code'], revision=loaded['revision']))['presets'], [])
            api.dispatch('insert', (auth, 'sthpw/login', dict(login='layout_user', password=hash_password('layout-user-password'))))
        user_ticket = api.get_ticket('layout_user', 'layout-user-password')
        with request_context(RequestContext(store, 'layout_user', 'admin')):
            api.auth.bind_security('layout_user', user_ticket)
            with self.assertRaises(SecurityException):
                request('save', dict(title='Denied', configuration=layout, revision=''))

    @unittest.skipUnless(os.environ.get('STREAM_POSTGRES_HOST'), 'Set STREAM_POSTGRES_HOST for isolated PostgreSQL')
    def test_postgres_native_layout_lifecycle(self):
        import uuid
        import psycopg
        from psycopg import sql
        database = 'stream_layout_' + uuid.uuid4().hex[:12]
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
            user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
            password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        with tempfile.TemporaryDirectory() as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = ElementTree.Element('config', version='2'); section = ElementTree.SubElement(root, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                    password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                    **{key: value for key, value in credentials.items() if key != 'password'}).items():
                ElementTree.SubElement(section, key).text = value
            path = Path(directory) / 'tactic-conf.xml'; path.write_bytes(ElementTree.tostring(root))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(Path(directory) / 'data'); store.initialize(hash_password('layout-test-password'))
                    self.exercise(store)
            finally:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                Config.reload_config()
