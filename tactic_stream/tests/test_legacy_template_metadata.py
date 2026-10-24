"""Legacy TEL formats are metadata; layout code must still pass its read-time guard."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class LegacyTemplateMetadata(unittest.TestCase):
    def test_saved_tel_formats_and_layouts_keep_code_execution_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('owned-template-test'))
            api = Api(store)
            api.protocol = 'json'
            ticket = api.get_ticket('admin', 'owned-template-test')
            auth = dict(ticket=ticket, project='admin')

            def save(kind, view, body):
                return api.dispatch('insert', (auth, 'config/widget_config', dict(
                    search_type=kind, view=view, config='<config><' + view + '>' + body + '</' + view + '></config>')))

            for index, expression in enumerate(('${@GET(.total_cost)}', '${@SUM(.total_cost)}', '${@GET(.total_cost, %0.2f)}')):
                body = '<element name="cost"><display widget="expression"><display_expression>' + expression + '</display_expression></display></element>'
                record = save('sthpw/note', 'tel_' + str(index), body)
                loaded = api.dispatch('get_by_search_key', (auth, record['__search_key__']))
                self.assertIn(expression, loaded['config'])
            for index, source in enumerate(('${value}', '${__import__("os")}', '<% import os %>')):
                with self.subTest(source=source), self.assertRaises(UnsupportedContract):
                    save('sthpw/note', 'unsafe_' + str(index), '<![CDATA[' + source + ']]>')
            save('CustomLayoutWdg', 'safe_layout', '<html><![CDATA[<div>${sobject.get("login")}</div>]]></html>')
            save('CustomLayoutWdg', 'unsafe_layout', '<html><![CDATA[<% import os %>blocked]]></html>')
            admin, = api.dispatch('query', (auth, 'sthpw/login', [['login', 'admin']]))
            from tactic.ui.table.custom_layout_element_wdg import read_custom_layout
            readers = [read_custom_layout]
            handler = Path(__file__).resolve().parents[3] / 'TH'
            for path in (handler / 'thlib/ui/table/requests.py', handler / 'thlib/tactic_query.py'):
                tree = ast.parse(path.read_text(encoding='utf-8'))
                function, = [node for node in ast.walk(tree)
                             if isinstance(node, ast.FunctionDef) and node.name == 'read_custom_layout']
                namespace = {}
                exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
                readers.append(namespace['read_custom_layout'])
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket)
                for reader in readers:
                    with self.subTest(reader=reader.__code__.co_filename):
                        result = reader(admin['__search_key__'], view='safe_layout')
                        self.assertIn('admin', json.dumps(result))
                        with self.assertRaisesRegex(ValueError, 'data-only Mako'):
                            reader(admin['__search_key__'], view='unsafe_layout')
