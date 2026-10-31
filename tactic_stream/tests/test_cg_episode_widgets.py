"""The supplied Episode view uses executable native cell configurations."""
import ast
from pathlib import Path
import tempfile
import unittest

from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.table_cells import read_table_cells


def configurations():
    source = Path(__file__).resolve().parents[2] / 'cg/config_widget_config.spt'
    for block in source.read_text(encoding='utf-8').split('#-- Start Entry --#')[1:]:
        row = {ast.literal_eval(node.args[0]): ast.literal_eval(node.args[1])
               for node in ast.walk(ast.parse(block)) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and node.func.attr == 'set_value'}
        if row.get('search_type') in ('cg/scenes', 'cg/shot', 'cg/assets', 'cg/texture'):
            yield row


class EpisodeWidgets(unittest.TestCase):
    def test_template_descriptors_and_real_names_previews_and_nested_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            store.initialize(hash_password('episode-widgets-test'))
            api = Api(store)
            token = api.get_ticket('admin', 'episode-widgets-test')
            auth = dict(ticket=token, project='admin')
            for stype in ('cg/scenes', 'cg/shot', 'cg/assets', 'cg/texture'):
                api.dispatch('create_search_type', (auth, stype, stype))
            for name in ('name', 'description', 'script', 'duration'):
                api.dispatch('add_column_to_search_type', (auth, 'cg/scenes', name, 'text'))
            for name in ('texture_type', 'sub_type', 'assets_category_code'):
                api.dispatch('add_column_to_search_type', (auth, 'cg/texture', name, 'text'))
            for row in configurations():
                if row['view'] in ('definition', 'table', 'episode_shots', 'episode_related_assets'):
                    if row['search_type'] == 'cg/scenes' and row['view'] == 'table':
                        row['config'] = row['config'].replace('<element name="duration"', '<element value_icon="FAS_CLOCK" value_style="badge" value_text_style="small" name="duration"')
                    api.dispatch('insert', (auth, 'config/widget_config',
                        {key: row[key] for key in ('search_type', 'view', 'config')}))
            records = [api.dispatch('insert', (auth, 'cg/scenes', dict(name=name)))
                       for name in ('Episode 01', 'Episode 02')]
            texture = api.dispatch('insert', (auth, 'cg/texture', dict(texture_type='diffuse', sub_type='paint')))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', token)
                interface = read_interface('cg/scenes')
                elements = interface['table']['elements']
                duration = next(element for element in elements if element['name'] == 'duration')
                self.assertEqual(duration['attributes']['value_icon'], 'FAS_CLOCK')
                self.assertEqual(duration['attributes']['value_style'], 'badge')
                self.assertEqual(duration['attributes']['value_text_style'], 'small')
                self.assertEqual([e['name'] for e in elements if not e['cell']['supported']], [])
                cells = read_table_cells('cg/scenes', 'table', [r['__search_key__'] for r in records])
                for record in records:
                    values = cells[record['__search_key__']]
                    self.assertEqual(values['name']['text'], record['name'])
                    self.assertNotIn('error', values['preview'])
                    self.assertEqual(values['script'], dict(text='Not script', href=''))
                    self.assertNotIn('error', values['task_pipeline_vertical'])
                # Source relationships and the requested shot columns must survive migration.
                from tactic.ui.table.nested_scope import nested_cell
                for name, stype, view in [('shot', 'cg/shot', 'episode_shots'),
                                           ('assets_in_episode', 'cg/assets', 'episode_related_assets')]:
                    element = next(e for e in elements if e['name'] == name)
                    options = dict(element['display']['options'], label='')
                    nested = nested_cell(records[0]['__search_key__'], options, column=name)['nestedTable']
                    self.assertEqual(nested['parentKey'], records[0]['__search_key__'])
                    self.assertEqual((nested['searchType'], nested['view']), (stype, view))
                    if name == 'assets_in_episode':
                        self.assertEqual(nested['expression'], '@SOBJECT(cg/assets_in_scenes.cg/assets)')
                        self.assertFalse(nested['gear'])
                        self.assertFalse(nested['search'])
                shots = read_interface('cg/shot', view='episode_shots')['table']['elements']
                self.assertEqual([e['name'] for e in shots],
                    ['rendered', 'preview', 'name', 'start_frame', 'end_frame', 'description', 'notes'])
                texture_interface = read_interface('cg/texture')
                self.assertEqual([e['name'] for e in texture_interface['table']['elements'] if not e['cell']['supported']], [])
                from pyasm.search import Search
                stored_texture = Search.get_by_search_key(texture['__search_key__'])
                for name, expected in [('texture_type', 'diffuse'), ('sub_type', 'paint')]:
                    cell = next(e['cell'] for e in texture_interface['table']['elements'] if e['name'] == name)
                    self.assertEqual(cell['kind'], 'text')
                    self.assertEqual(stored_texture.get_value(cell['field']), expected)


if __name__ == '__main__':
    unittest.main()
