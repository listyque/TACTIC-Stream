"""Snapshot metadata projection against the current unmodified Handler classes."""
import ast
import collections
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tactic_stream.server.file_presentation import file_display, repository_display, metadata_members
from tactic_stream.server.configuration import validate_setting
from pyasm.common.config import ConfigException


class FilePresentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[3] / 'TH/thlib/global_functions.py'
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        names = {'FileObject', 'MatchTemplate', 'natural_sort_key', 'extract_filename', 'form_path'}
        selected = ast.Module(body=[node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names], type_ignores=[])
        cls.native = dict(collections=collections, re=re, os=os, env_mode=SimpleNamespace(get_platform=lambda:'Windows'))
        exec(compile(selected, str(path), 'exec'), cls.native)

    def test_native_file_names_and_chips(self):
        kinds = {'file': '$FILENAME.$EXT', 'no_ext': '$FILENAME', 'layer_file': '$FILENAME.$LAYER.$EXT',
                 'sequence': '$FILENAME.$FRAME.$EXT', 'layer_sequence': '$FILENAME.$LAYER.$FRAME.$EXT',
                 'udim': '$FILENAME.$UDIM.$EXT', 'uv': '$FILENAME.$UV.$EXT',
                 'layer_udim': '$FILENAME.$LAYER.$UDIM.$EXT', 'layer_uv': '$FILENAME.$LAYER.$UV.$EXT',
                 'udim_sequence': '$FILENAME.$UDIM.$FRAME.$EXT', 'uv_sequence': '$FILENAME.$UV.$FRAME.$EXT',
                 'layer_udim_sequence': '$FILENAME.$LAYER.$UDIM.$FRAME.$EXT', 'layer_uv_sequence': '$FILENAME.$LAYER.$UV.$FRAME.$EXT'}
        for kind, template in kinds.items():
            tiles = ['u2_v2', 'u2_v10'] if 'uv' in kind else ['1001', '1002']
            ranges = [[tiles[0], ['1-3', '5']], [tiles[1], ['2', '4-5']]] if ('uv' in kind or 'udim' in kind) and 'sequence' in kind else ['1-3', '5']
            metadata = dict(type=kind, template=template, new_template=template, new_filename='robot_arm',
                            new_file_ext='exr', new_padding=4, layer='beauty', udims=tiles, frameranges=ranges, app_info={'p': '2026'})
            if 'sequence' not in kind:
                metadata.pop('frameranges')
            if 'udim' not in kind and 'uv' not in kind:
                metadata.pop('udims')
            file = SimpleNamespace(get_metadata=lambda: metadata, get_abs_path=lambda: '/virtual',
                                   get_json_value=lambda *args, **kwargs: metadata, get_value=lambda name: 'original.exr')
            with self.subTest(kind=kind):
                groups = self.native['MatchTemplate']().init_from_tactic_file_object(file)
                native = next(iter(groups.values()))[0]
                expected = [dict(label='Context', value='publish', url='')]
                for label, method, kwargs in [('Range', 'get_sequence_frameranges_string', {'brackets': '[]'}), ('Frames', 'get_sequence_lenght', {}), ('Layer', 'get_layer', {}), ('Tiles', 'get_tiles_count', {})]:
                    value = getattr(native, method)(**kwargs)
                    if value not in (None, '', 0): expected.append(dict(label=label, value=str(value), url=''))
                expected.append(dict(label='Maya', value='2026', url=''))
                self.assertEqual(file_display(file, 'publish'), dict(title=native.get_pretty_file_name(), infoChips=expected))
                names = native.get_all_files_list(filenames=True)
                self.assertEqual(metadata_members(metadata,0,100), names)
                self.assertEqual(metadata_members(metadata,1,2), names[1:3])

    def test_bounded_member_page(self):
        metadata = dict(type='sequence',template='$FILENAME.$FRAME.$EXT',new_template='$FILENAME.$FRAME.$EXT',new_filename='render',new_file_ext='exr',new_padding=8,frameranges=['1-99999999'])
        self.assertEqual(metadata_members(metadata,90000000,2), ['render.90000001.exr','render.90000002.exr'])
        metadata.update(new_padding=4, frameranges=['9998-10002'])
        names = sorted('render.%04d.exr' % frame for frame in range(9998,10003))
        self.assertEqual(metadata_members(metadata,0,50), names)
        self.assertEqual(metadata_members(metadata,1,2), names[1:3])

    def test_fallback_and_compressed_large_ranges(self):
        for metadata in (None, 'invalid JSON', [], {}, {'template': '$FILENAME.$EXT'}, {'template': 'x', 'new_template': '$UNKNOWN'}, {'template': 'x', 'new_template': '$FILENAME.$FRAME.$EXT', 'type': 'sequence', 'new_filename': 'a', 'new_file_ext': 'exr', 'new_padding': 4, 'frameranges': ['-1-2']}):
            file = SimpleNamespace(get_json_value=lambda *args, **kwargs: metadata, get_value=lambda name: 'original.exr')
            self.assertEqual(file_display(file)['title'], 'original.exr')
        metadata = dict(template='$FILENAME.$FRAME.$EXT', new_template='$FILENAME.$FRAME.$EXT', type='sequence',
                        new_filename='large', new_file_ext='exr', new_padding=9, frameranges=['1-200000000'])
        file = SimpleNamespace(get_json_value=lambda *args, **kwargs: metadata, get_value=lambda name: 'large.000000001.exr')
        result = file_display(file)
        self.assertEqual(result['title'], 'large.[#########].exr')
        self.assertEqual(result['infoChips'], [dict(label='Range', value='[1-200000000]', url=''), dict(label='Frames', value='200000000', url='')])

    def test_native_repository_catalog_and_override_validation(self):
        with patch('tactic_stream.server.file_presentation.Config.get_value', return_value=''):
            self.assertEqual(repository_display('base'), dict(repository='General', repositoryColor='#808080'))
            self.assertEqual(repository_display('local'), dict(repository='Local', repositoryColor='#ff8c28'))
            self.assertEqual(repository_display('custom_99'), dict(repository='custom_99', repositoryColor='#607d8b'))
        raw = json.dumps({'custom_0': {'title': 'Studio', 'color': [32, 160, 240]}, 'base': {'title': 'Main', 'color': 'ff0000'}})
        validated = validate_setting('checkin/repository_display', raw)
        with patch('tactic_stream.server.file_presentation.Config.get_value', return_value=validated):
            self.assertEqual(repository_display('custom_0'), dict(repository='Studio', repositoryColor='#20a0f0'))
            self.assertEqual(repository_display('base'), dict(repository='Main', repositoryColor='#ff0000'))
        for value in ('[]', '{"base":{"path":"secret"}}', '{"base":{"title":1}}', '{"base":{"color":"url(x)"}}', '{"base":{"color":[true,0,0]}}'):
            with self.assertRaises(ConfigException): validate_setting('checkin/repository_display', value)
