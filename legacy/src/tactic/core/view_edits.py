"""Targeted widget_config edits; preserve every unmodified XML extension."""
import re
import xml.etree.ElementTree as ET
from .config_model import parse_xml, view_node, xml_text, reorder_view

NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_ .@:/-]{0,199}$')
ATTRIBUTES = {'title', 'width', 'edit', 'is_visible', 'icon', 'state', 'description'}
KINDS = ('display', 'edit', 'action')


def patch_view(text, view, operations):
    root = parse_xml(text)
    node = view_node(root, view)
    if node is None:
        raise ValueError('View does not exist')
    if not isinstance(operations, list) or len(operations) > 500:
        raise ValueError('Too many view edits')
    for op in operations:
        action = op.get('op') if isinstance(op, dict) else None
        elements = [n for n in node if n.tag == 'element']
        if action == 'reorder':
            order = op.get('order')
            if not isinstance(order, list) or any(type(i) is not int for i in order) or sorted(order) != list(range(len(elements))):
                raise ValueError('Order must be an exact index permutation')
            it = iter(elements[i] for i in order)
            node[:] = [next(it) if child.tag == 'element' else child for child in node]
            continue
        if action == 'add':
            name = op.get('name')
            if not isinstance(name, str) or not NAME.fullmatch(name):
                raise ValueError('Invalid element name')
            if any(el.get('name') == name for el in elements):
                raise ValueError('Duplicate element')
            element = ET.SubElement(node, 'element', {'name': name})
        elif action in ('update', 'remove'):
            index = op.get('index')
            if type(index) is not int or not 0 <= index < len(elements):
                raise ValueError('Invalid element index')
            element = elements[index]
            if action == 'remove':
                node.remove(element)
                continue
        else:
            raise ValueError('Unknown view edit')
        if not isinstance(op.get('attributes', {}), dict):
            raise ValueError('Attributes must be an object')
        for key, value in op.get('attributes', {}).items():
            if key not in ATTRIBUTES or (value is not None and not isinstance(value, str)):
                raise ValueError('Unsupported element attribute')
            if value is None:
                element.attrib.pop(key, None)
            else:
                element.set(key, value[:2000])
        # Only explicitly supplied handler/options change. Absence means inherit.
        for kind in KINDS:
            if kind not in op:
                continue
            patch = op[kind]
            if not isinstance(patch, dict):
                raise ValueError('Handler edit must be an object')
            sub = element.find(kind)
            if sub is None:
                sub = ET.SubElement(element, kind)
            for attr in ('class', 'widget'):
                if attr in patch:
                    val = patch[attr]
                    if val is None or val == '':
                        sub.attrib.pop(attr, None)
                    elif isinstance(val, str) and re.fullmatch(r'[A-Za-z_][\w.]{0,249}', val):
                        sub.set(attr, val)
                    else:
                        raise ValueError('Invalid widget handler')
            if not isinstance(patch.get('options', {}), dict):
                raise ValueError('Options must be an object')
            for key, val in patch.get('options', {}).items():
                if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z_][\w.-]{0,100}', key):
                    raise ValueError('Invalid option key')
                old = sub.find(key)
                if val is None:
                    if old is not None:
                        sub.remove(old)
                else:
                    if not isinstance(val, str) or len(val) > 128 * 1024:
                        raise ValueError('Option must be bounded text')
                    if old is None:
                        old = ET.SubElement(sub, key)
                    # Do not accidentally flatten a structured nested XML option.
                    if len(old):
                        raise ValueError('Structured option must be edited in XML mode')
                    old.text = val
    return xml_text(root)
