"""Loss-preserving native graph editing over the original TACTIC XML.

Only explicitly requested nodes/attributes are changed. Unknown attributes,
comments, processing configuration and extension nodes are retained. XML lexical
formatting is not promised; element/attribute semantics are. Database checks and
business effects belong to graph_service, not this module.
"""
from copy import deepcopy
import json
import math
import re
import xml.etree.ElementTree as ET
from .config_model import parse_xml, xml_text

PROCESS_TYPES = ('manual', 'approval', 'action', 'condition', 'hierarchy',
                 'progress', 'dependency', 'status', 'input', 'output')
PROCESS_ATTRS = frozenset(('type', 'label', 'color', 'xpos', 'ypos', 'description'))
CONNECT_ATTRS = frozenset(('from_attr', 'to_attr', 'color', 'label', 'type'))
SCHEMA_CONNECT_ATTRS = frozenset(('relationship', 'from_col', 'to_col', 'instance_type',
                                  'path', 'type', 'color', 'label'))
TYPE_NAME = re.compile(r'^[A-Za-z0-9_\-]+/[A-Za-z0-9_\-/]+$')


def name(value, label='name'):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError('Invalid ' + label)
    if any(ord(c) < 32 for c in value) or any(c in value for c in '/\\<>"\''):
        raise ValueError('Invalid characters in ' + label)
    return value.strip()


def _attrs(values, allowed):
    if not isinstance(values, dict) or any(k not in allowed for k in values):
        raise ValueError('Unsupported attribute in edit')
    out = {}
    for key, value in values.items():
        if value is None:
            out[key] = None
        elif key in ('xpos', 'ypos'):
            if isinstance(value, bool):
                raise ValueError('Coordinates must be finite numbers')
            try:
                number = float(value)
            except (ValueError, TypeError) as exc:
                raise ValueError('Coordinates must be numeric') from exc
            if not math.isfinite(number) or not -100000 <= number <= 100000:
                raise ValueError('Coordinate out of range')
            out[key] = str(round(number, 2))
        elif not isinstance(value, str) or len(value) > 4096 or '\x00' in value:
            raise ValueError('Attribute must be a bounded string')
        else:
            out[key] = value
    return out


def _set(node, attrs):
    for key, value in attrs.items():
        if value is None:
            node.attrib.pop(key, None)
        else:
            node.set(key, value)


def graph_spec(text, kind):
    root = parse_xml(text)
    if kind not in ('pipeline', 'schema') or root.tag != kind:
        raise ValueError('Unexpected graph root')
    tag = 'process' if kind == 'pipeline' else 'search_type'
    nodes = []
    for i, node in enumerate(root.findall(tag)):
        def coordinate(axis, default):
            try:
                v = float(node.get(axis, default))
                return v if math.isfinite(v) else default
            except (ValueError, TypeError):
                return default
        nodes.append({'name': node.get('name'), 'attributes': dict(node.attrib),
                      'x': coordinate('xpos', 60 + i % 4 * 250),
                      'y': coordinate('ypos', 70 + i // 4 * 150),
                      'type': node.get('type', 'manual' if kind == 'pipeline' else 'search_type')})
    edges = [{'index': i, 'from': e.get('from'), 'to': e.get('to'),
              'attributes': dict(e.attrib)} for i, e in enumerate(root.findall('connect'))]
    return {'kind': kind, 'attributes': dict(root.attrib), 'nodes': nodes, 'edges': edges}


def apply_graph_edits(text, kind, operations):
    if not isinstance(operations, list) or len(operations) > 500:
        raise ValueError('Expected at most 500 operations')
    root = parse_xml(text)
    if kind not in ('pipeline', 'schema') or root.tag != kind:
        raise ValueError('Unexpected graph root')
    tag = 'process' if kind == 'pipeline' else 'search_type'
    names = [n.get('name') for n in root.findall(tag)]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate node names in original graph')
    removed, renamed = [], {}
    origins = {value: value for value in names}
    for op in operations:
        if not isinstance(op, dict):
            raise ValueError('Invalid graph operation')
        action = op.get('op')
        nodes = {n.get('name'): n for n in root.findall(tag)}
        if action == 'add_node':
            value = op.get('name')
            if kind == 'schema':
                if not isinstance(value, str) or not TYPE_NAME.fullmatch(value):
                    raise ValueError('Invalid SearchType')
            else:
                value = name(value)
            if value in nodes:
                raise ValueError('Node already exists: ' + value)
            attrs = _attrs(op.get('attributes', {}), PROCESS_ATTRS if kind == 'pipeline' else ('xpos', 'ypos', 'label', 'color'))
            if kind == 'pipeline' and attrs.get('type', 'manual') not in PROCESS_TYPES:
                raise ValueError('Unsupported new process type')
            origins[value] = None
            node = ET.SubElement(root, tag, {'name': value})
            if kind == 'pipeline':
                node.set('type', 'manual')
            _set(node, attrs)
        elif action in ('update_node', 'remove_node', 'rename_node'):
            value = op.get('name')
            if value not in nodes:
                raise ValueError('Unknown node')
            node = nodes[value]
            if action == 'update_node':
                allowed = PROCESS_ATTRS if kind == 'pipeline' else ('xpos', 'ypos', 'label', 'color')
                attrs = _attrs(op.get('attributes', {}), allowed)
                if kind == 'pipeline' and 'type' in attrs and attrs['type'] != node.get('type') and attrs['type'] not in PROCESS_TYPES:
                    raise ValueError('Unsupported new process type')
                _set(node, attrs)
            elif action == 'remove_node':
                root.remove(node)
                origin = origins.pop(value, None)
                if origin is not None:
                    removed.append(origin)
                for edge in list(root.findall('connect')):
                    if edge.get('from') == value or edge.get('to') == value:
                        root.remove(edge)
            else:
                if kind != 'pipeline':
                    raise ValueError('Renaming a SearchType requires a database migration')
                new = name(op.get('new_name'))
                if new in nodes:
                    raise ValueError('Node already exists')
                node.set('name', new)
                origins[new] = origins.pop(value)
                for edge in root.findall('connect'):
                    for attr in ('from', 'to'):
                        if edge.get(attr) == value:
                            edge.set(attr, new)
        elif action == 'add_edge':
            a, b = op.get('from'), op.get('to')
            if a not in nodes or b not in nodes:
                raise ValueError('Connection references unknown nodes')
            attrs = _attrs(op.get('attributes', {}), CONNECT_ATTRS if kind == 'pipeline' else SCHEMA_CONNECT_ATTRS)
            edge = ET.SubElement(root, 'connect', {'from': a, 'to': b})
            _set(edge, attrs)
        elif action in ('update_edge', 'remove_edge'):
            index = op.get('index')
            edges = root.findall('connect')
            if type(index) is not int or not 0 <= index < len(edges):
                raise ValueError('Invalid connection index')
            edge = edges[index]
            # Indices are relative to the result of previous operations in this batch.
            if action == 'remove_edge':
                root.remove(edge)
            else:
                _set(edge, _attrs(op.get('attributes', {}), CONNECT_ATTRS if kind == 'pipeline' else SCHEMA_CONNECT_ATTRS))
        else:
            raise ValueError('Unknown graph operation: ' + str(action))
    if len(root.findall(tag)) > 2000 or len(root.findall('connect')) > 5000:
        raise ValueError('Graph too large')
    # Existing edges to inherited schema nodes are legal; do not delete/reject them.
    renamed = {origin: current for current, origin in origins.items() if origin is not None and current != origin}
    return {'xml': xml_text(root), 'removed': removed, 'renamed': renamed}


def normalize_workflow_settings(value):
    """Validate a JSON object, reject executable browser-dispatched callbacks.

    Existing unknown workflow keys are retained server-side; this validates only
    the patch the user explicitly edits. Script editor is a separate privileged
    capability and is not smuggled through process settings.
    """
    if not isinstance(value, dict):
        raise ValueError('Workflow settings must be an object')
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if len(raw.encode('utf-8')) > 128 * 1024:
        raise ValueError('Workflow settings too large')
    forbidden = {'script', 'script_path', 'on_action_class', 'class_name', '_cbk_classes', 'trigger_code', 'process_code'}
    def check(v, depth=0):
        if depth > 16:
            raise ValueError('Workflow nesting too deep')
        if isinstance(v, dict):
            for k, item in v.items():
                if not isinstance(k, str) or k.startswith('_') or k in forbidden:
                    raise ValueError('Executable workflow settings require the script-management capability')
                check(item, depth+1)
        elif isinstance(v, list):
            for item in v:
                check(item, depth+1)
    check(value)
    return deepcopy(value)
