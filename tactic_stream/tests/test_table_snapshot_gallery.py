"""Original CG Episode gallery declarations work in both server procedures."""

import ast
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Snapshot
from pyasm.search import Search, SearchType
from tactic.ui.table.nested_scope import nested_cell, read_nested_scope
from tactic.ui.table.nested_table import NestedTableReadCmd
from tactic_stream.server.table_cells import describe_cell, read_table_cells


ROOT = Path(__file__).resolve().parents[2]


def episode_options():
    for block in (
        (ROOT / 'cg/config_widget_config.spt')
        .read_text(encoding='utf-8-sig')
        .split('#-- Start Entry --#')
    ):
        if not block.strip():
            continue
        fields = {
            ast.literal_eval(node.args[0]): ast.literal_eval(node.args[1])
            for node in ast.walk(ast.parse(block))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'set_value'
            and len(node.args) == 2
        }
        if (
            fields.get('view') == 'definition'
            and fields.get('search_type') == 'cg/scenes'
        ):
            elements = ET.fromstring(fields['config'])
            return {
                element.get('name'): {
                    option.tag: (option.text or '').strip()
                    for option in element.find('display')
                }
                for element in elements.findall('.//element')
                if element.get('name') in ('storyboard', 'checklist')
            }
    raise AssertionError('Original Episode definition is missing')


def handler_nested_cell():
    source = ROOT.parent / 'TH/thlib/tactic_query.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    query = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout'
    )
    function = next(
        node
        for node in query.body
        if isinstance(node, ast.FunctionDef) and node.name == 'nested_cell'
    )
    namespace = {}
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'),
        namespace,
    )
    return namespace['nested_cell']


class SnapshotGalleries(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def test_original_options_reach_real_cell_projection_in_both_transports(self):
        config = ET.Element('config')
        table = ET.SubElement(config, 'episode_gallery_probe')
        for name, options in episode_options().items():
            display = ET.SubElement(
                ET.SubElement(table, 'element', name=name),
                'display',
                widget='hidden_row',
            )
            for key, value in options.items():
                ET.SubElement(display, key).text = value

        def create():
            record = SearchType.create('config/widget_config')
            record.set_value('search_type', 'contract/entity')
            record.set_value('view', 'episode_gallery_probe')
            record.set_value('config', ET.tostring(config, encoding='unicode'))
            record.commit()

        write(create)
        key = Search.get_by_code('contract/entity', 'A').get_search_key()
        cells = read_table_cells('contract/entity', 'episode_gallery_probe', [key])[key]
        source = ROOT.parent / 'TH/thlib/tactic_query.py'
        query = next(
            node
            for node in ast.parse(source.read_text(encoding='utf-8')).body
            if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout'
        )
        namespace = {}
        exec(
            compile(ast.Module(body=[query], type_ignores=[]), str(source), 'exec'),
            namespace,
        )
        handler = json.loads(
            namespace['query_table_layout'](
                'contract/entity', [key], 'episode_gallery_probe'
            )
        )
        for name in ('storyboard', 'checklist'):
            for result in (cells[name], handler['rows'][key][name]):
                self.assertFalse(result.get('error'), result)
                self.assertEqual(result['nestedTable']['gallery']['scale'], 150)
                self.assertEqual(result['nestedTable']['parentKey'], key)

    def test_original_episode_cells_and_queries_keep_parent_process_and_pages(self):
        parent = Search.get_by_code('contract/entity', 'A')
        other = Search.get_by_code('contract/entity', 'B')

        def create():
            return [
                Snapshot.create(
                    owner, 'file', context, process=process, triggers=False
                ).get_code()
                for owner, process, context in [
                    (parent, 'storyboard', 'storyboard'),
                    (parent, 'storyboard', 'storyboard'),
                    (parent, 'publish', 'publish'),
                    (other, 'storyboard', 'storyboard'),
                    (other, 'publish', 'publish'),
                ]
            ]

        codes = write(create)
        declarations = episode_options()
        self.assertEqual(set(declarations), {'storyboard', 'checklist'})
        for name, options in declarations.items():
            descriptor = describe_cell(
                dict(
                    name=name,
                    display=dict(
                        handler='tactic.ui.table.HiddenRowElementWdg', options=options
                    ),
                    action=dict(handler='', options={}),
                ),
                {},
            )
            self.assertTrue(descriptor['supported'], descriptor)
            for make_cell in (nested_cell, handler_nested_cell()):
                with self.subTest(column=name, procedure=make_cell.__module__):
                    cell = make_cell(parent.get_search_key(), options, name)
                    scope = cell['nestedTable']
                    self.assertEqual(scope['gallery']['scale'], 150)
                    self.assertFalse(scope['selection'])
                    self.assertFalse(scope['refresh'])
                    self.assertEqual(
                        scope['filters'], [['process', '=', options['process']]]
                    )
                    query = dict(
                        parent_key=scope['parentKey'],
                        search_type=scope['searchType'],
                        filters=scope['filters'],
                        limit=1,
                        order_by=['id asc'],
                    )
                    first = read_nested_scope(**query)
                    expected = codes[:2] if name == 'storyboard' else codes[2:3]
                    self.assertEqual(
                        [row['code'] for row in first['records']], expected[:1]
                    )
                    self.assertEqual(first['hasNext'], len(expected) > 1)
                    second = read_nested_scope(**query, offset=1)
                    self.assertEqual(
                        [row['code'] for row in second['records']], expected[1:]
                    )
                    result = NestedTableReadCmd(**query).execute()
                    key = result['records'][0]['__search_key__']
                    self.assertIn('preview', result['cells'][key])
                    self.assertNotIn('error', result['cells'][key]['preview'])
        self.assertEqual(
            read_nested_scope(
                parent.get_search_key(),
                'sthpw/snapshot',
                filters=[['process', '=', 'missing']],
            )['records'],
            [],
        )

    def test_gallery_rejects_scope_substitution_and_unimplemented_modes(self):
        key = Search.get_by_code('contract/entity', 'A').get_search_key()
        original = episode_options()['storyboard']
        for make_cell in (nested_cell, handler_nested_cell()):
            for override in (
                dict(search_key='contract/entity?code=B'),
                dict(scale='0'),
                dict(scale='513'),
                dict(scale='hello'),
                dict(process=['storyboard']),
                dict(allow_drag='true'),
                dict(show_context_menu='true'),
                dict(layout='cards'),
                dict(gallery_align='bottom'),
                dict(checkin_context='other'),
                dict(unknown='true'),
                dict(show_refresh='yes'),
            ):
                with (
                    self.subTest(procedure=make_cell.__module__, override=override),
                    self.assertRaises(ValueError),
                ):
                    make_cell(key, dict(original, **override))


if __name__ == '__main__':
    unittest.main()
