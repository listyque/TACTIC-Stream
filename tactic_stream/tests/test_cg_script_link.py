"""The CG Script column is a URL or the explicit Not script placeholder."""
import ast
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree

from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.table_cells import read_table_cells


def script_element():
    values = {}
    source = Path(__file__).resolve().parents[2] / 'cg/config_widget_config.spt'
    for statement in ast.parse(source.read_text(encoding='utf-8')).body:
        if isinstance(statement, ast.Assign):
            if values.get('search_type') == 'cg/scenes' and values.get('view') == 'definition':
                return ElementTree.fromstring(values['config']).find("definition/element[@name='script']")
            values = {}
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == 'set_value':
                values[ast.literal_eval(call.args[0])] = ast.literal_eval(call.args[1])
    raise AssertionError('CG Script definition missing')


class ScriptLink(unittest.TestCase):
    def test_native_link_values_and_empty_placeholder(self):
        element = script_element()
        self.assertEqual(element.find('display').get('class'), 'tactic.ui.table.LinkElementWdg')
        self.assertIsNone(element.find('.//dynamic_class'))
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            store.initialize(hash_password('script-test-password'))
            api = Api(store)
            api.protocol = 'json'
            token = api.get_ticket('admin', 'script-test-password')
            auth = dict(ticket=token, project='admin')
            api.dispatch('create_search_type', (auth, 'test/script_link', 'Script link'))
            api.dispatch('add_column_to_search_type', (auth, 'test/script_link', 'script', 'text'))
            root = ElementTree.Element('config')
            ElementTree.SubElement(root, 'definition').append(element)
            api.dispatch('insert', (auth, 'config/widget_config', dict(search_type='test/script_link',
                view='definition', config=ElementTree.tostring(root, encoding='unicode'))))
            api.dispatch('insert', (auth, 'config/widget_config', dict(search_type='test/script_link',
                view='table', config='<config><table><element name="script" width="208"/></table></config>')))
            url = 'https://docs.google.com/document/d/example/edit'
            records = [api.dispatch('insert', (auth, 'test/script_link', dict(script=value) if value is not None else {}))
                       for value in (None, '', '   ', url)]
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', token)
                interface = read_interface('test/script_link')
                descriptor = interface['table']['elements'][0]['cell']
                self.assertEqual(descriptor['kind'], 'link')
                self.assertTrue(descriptor['supported'])
                cells = read_table_cells('test/script_link', 'table', [row['__search_key__'] for row in records])
            for record in records[:3]:
                self.assertEqual(cells[record['__search_key__']]['script'], dict(text='Not script', href=''))
            self.assertEqual(cells[records[3]['__search_key__']]['script'], dict(text=url, href=url))


if __name__ == '__main__':
    unittest.main()
