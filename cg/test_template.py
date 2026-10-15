"""Run with: python cg/test_template.py. Reads the export without executing scripts."""

import ast
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def records(text):
    for block in text.split('#-- Start Entry --#')[1:]:
        yield {
            ast.literal_eval(node.args[0]): ast.literal_eval(node.args[1])
            for node in ast.walk(ast.parse(block))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'set_value' and len(node.args) == 2
        }


def check():
    root = Path(__file__).resolve().parent
    expected = {'cg/' + name for name in (
        'assets', 'assets_category', 'assets_in_assets', 'assets_in_scenes',
        'scenes', 'shot', 'texture', 'texture_in_assets',
    )}
    manifest = ET.parse(root / 'manifest.xml').getroot()
    assert {node.get('code') for node in manifest.findall('search_type')} == expected
    assert {path.stem.replace('cg_', 'cg/', 1) for path in root.glob('cg_*.spt')} == expected
    assert not [*root.glob('dolly3d_*.spt'), *root.glob('complex_*.spt')]
    old = re.compile(r'(?<![\w/])(?:dolly3d|complex)/|(?:skey://|_triggers/)(?:dolly3d|complex)/')
    unused = re.compile(r'(?<![\w/])cg/(?:2d_animatic|3d_animatic|act|application|chars|compose|'
                        r'props|reference|script|sequence|sets|sourcetex|stage|storyboard|textures|'
                        r'vfx|images|episodes|animatic)\b')
    for path in root.glob('*.spt'):
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text, filename=str(path))
        assert not old.search(text), path.name
        assert not unused.search(text), path.name
        if path.name == 'config_widget_config.spt':
            for data in records(text):
                config = data.get('config', '').strip()
                if config.startswith('{'):
                    json.loads(config)
                elif config:
                    ET.fromstring(config)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not old.search(node.value), path.name
                assert not unused.search(node.value), path.name
        if path.name.startswith('cg_'):
            data = next(records(text))
            search_type = path.stem.replace('cg_', 'cg/', 1)
            assert data['code'] == data['search_type'] == search_type, path.name
            assert data['namespace'] == 'cg', path.name
            assert data['table_name'] == search_type.split('/')[1], path.name
            tables = [ast.literal_eval(node.args[0]) for node in ast.walk(tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == 'CreateTable']
            assert tables == [search_type], path.name
    schema = ET.fromstring(next(records((root / 'sthpw_schema.spt').read_text(encoding='utf-8')))['schema'])
    assert {n.get('name') for n in schema.findall('search_type') if n.get('name').startswith('cg/')} == expected
    for edge in schema.findall('connect'):
        assert all(edge.get(key) in expected for key in ('from', 'to')), edge.attrib
        assert edge.get('instance_type', 'cg/assets') in expected, edge.attrib
    project = next(records((root / 'sthpw_project.spt').read_text(encoding='utf-8')))
    project_type = next(records((root / 'sthpw_project_type.spt').read_text(encoding='utf-8')))
    assert project['type'] == project_type['code'] == 'cg'
    print('OK: 8 cg types, filenames, namespace metadata, schema links and script references')


if __name__ == '__main__':
    check()
