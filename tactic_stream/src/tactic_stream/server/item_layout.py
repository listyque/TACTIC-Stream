"""Bounded, renderer-independent SObject layout metadata over WidgetConfigView."""
import re
from importlib.resources import files

LAYOUT = 'sobject-layout'
WIDGETS = ('group', 'view', 'text', 'title', 'description', 'image', 'link', 'button',
           'metadata', 'snapshot-details', 'snapshot-size', 'snapshot-summary', 'branch-summary', 'file-offline', 'item-menu', 'knowledge', 'quick-actions', 'relations')
ACTIONS = ('inspect', 'operate', 'preview', 'tasks', 'notes', 'upload', 'create', 'link', 'relations')
VARIANTS = ('all', 'main', 'children', 'process', 'relation', 'versions', 'snapshot', 'file')
EXAMPLE_VIEWS = ('continuous_example', 'table_example', 'cards_example')
ROLES = ('', 'preview', 'copy', 'title-line', 'title-actions', 'description', 'metadata', 'actions',
         'hover-actions', 'communication', 'task-button', 'note-button', 'mobile-actions', 'file-offline')
CONDITIONS = ('desktop', 'mobile', 'tree', 'not-tree', 'object', 'object-or-process', 'not-branch',
              'description', 'snapshot', 'branch', 'relation', 'mobile-upload')


def layout_view_names(search_type, records):
    from pyasm.common import XmlException
    from pyasm.common.errors import UnsupportedContract
    from pyasm.widget import WidgetConfig, WidgetConfigException, WidgetConfigView
    names = list(EXAMPLE_VIEWS)
    for record in records:
        view = record.get_value('view')
        if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view) or view in names:
            continue
        try:
            config = WidgetConfig.get(view=view, xml=record.get_value('config'), use_cache=False)
        except (XmlException, WidgetConfigException, UnsupportedContract):
            # Service records may contain filter data rather than widget XML.
            continue
        if config.has_view() and config.get_view_attributes().get('layout') == LAYOUT:
            names.append(view)
    return [view for view in names
            if WidgetConfigView.get_by_search_type(search_type, view, use_cache=False).get_layout_handler() == LAYOUT]


def layout_templates():
    from xml.etree import ElementTree as ET
    directory = files('tactic_stream') / 'config/layouts'
    shared = ET.fromstring((files('tactic_stream') / 'config/search_type/widget/DEFAULT-conf.xml').read_text(encoding='utf-8'))
    templates = []
    for name in ('continuous', 'cards', 'table', 'blank'):
        if name != 'blank':
            root = ET.Element('config')
            root.append(shared.find({'continuous':'continuous_example', 'cards':'cards_example', 'table':'table_example'}[name]))
            xml = ET.tostring(root, encoding='unicode')
        else:
            xml = (directory / (name + '.xml')).read_text(encoding='utf-8')
        templates.append(dict(name=name, xml=xml))
    return templates


def describe_item_layout(description):
    attributes = description['attributes']
    def number(value, default, maximum):
        value = str(value if value is not None else default)
        if not value.isdecimal() or not 1 <= int(value) <= maximum:
            raise ValueError('Invalid layout size')
        return int(value)

    def spacing(attrs):
        values = {}
        for key in ('padding', 'margin'):
            if key not in attrs:
                continue
            text = str(attrs[key]).split()
            if len(text) != 4 or any(not value.isdecimal() or int(value)>256 for value in text):
                raise ValueError('Layout spacing requires four integers from 0 to 256')
            values[key] = [int(value) for value in text]
        if 'gap' in attrs:
            gap = str(attrs['gap'])
            if not gap.isdecimal() or int(gap)>128:
                raise ValueError('Layout gap must be from 0 to 128')
            values['gap'] = int(gap)
        return values

    collection = attributes.get('collection', 'grid')
    if collection not in ('grid', 'list', 'tree', 'table'):
        raise ValueError('Invalid layout collection')
    tracks = attributes.get('tracks', '')
    if tracks and not re.fullmatch(r'(auto|[1-9]\d{0,2}px|[1-9]\d?fr)( (auto|[1-9]\d{0,2}px|[1-9]\d?fr)){0,11}', tracks):
        raise ValueError('Invalid layout tracks')
    flow = attributes.get('flow', 'grid')
    if flow not in ('grid', 'contents'):
        raise ValueError('Invalid layout flow')
    result = dict(collection=collection, flow=flow, tracks=tracks, columns=number(attributes.get('columns'), 12, 12),
                  card_width=number(attributes.get('card_width'), 280, 1200), elements=[], **spacing(attributes))
    if len(description['elements']) > 128:
        raise ValueError('Layout supports at most 128 elements')
    if tracks and len(tracks.split()) != result['columns']:
        raise ValueError('Layout tracks must match columns')
    names = set()
    for element in description['elements']:
        options = element['display']['options']
        attrs = element['attributes']
        name = element['name']
        kind = element['display']['handler']
        role, tag, flow = attrs.get('role', ''), attrs.get('tag', 'div'), attrs.get('flow', 'grid')
        when = [part for part in attrs.get('when', '').split(' ') if part]
        if role not in ROLES or tag not in ('div', 'span', 'strong', 'small') or flow not in ('grid', 'contents') or any(part not in CONDITIONS for part in when):
            raise ValueError('Invalid item presentation setting')
        layer = str(attrs.get('layer', '0'))
        if not re.fullmatch(r'-?\d{1,3}', layer) or not -100 <= int(layer) <= 100:
            raise ValueError('Layout layer must be between -100 and 100')
        if kind not in WIDGETS or element['action']['handler']:
            raise ValueError('Unsupported layout widget or action')
        if not re.fullmatch(r'[A-Za-z_]\w{0,63}', name) or name in names:
            raise ValueError('Invalid or duplicate layout element name')
        names.add(name)
        if set(options) - {'bind', 'text', 'href', 'href_bind', 'badge', 'icon', 'action', 'fit', 'view'}:
            raise ValueError('Unsupported layout widget option')
        for key in ('bind', 'href_bind', 'badge'):
            binding = options.get(key, '')
            if binding and (not re.fullmatch(r'(record|node)\.[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){0,4}', binding)
                            or any(part in ('__proto__', 'constructor', 'prototype') for part in binding.split('.'))):
                raise ValueError('Invalid layout data binding')
        action = options.get('action', '')
        if kind == 'button' and action not in ACTIONS and not (options.get('href') or options.get('href_bind')):
            raise ValueError('Layout button requires an action')
        if kind == 'view' and not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', options.get('view', '')):
            raise ValueError('Layout widget requires a view name')
        variant = attrs.get('variant', 'all')
        search_type = attrs.get('search_type', '')
        if search_type and not re.fullmatch(r'[A-Za-z_]\w*/[A-Za-z_]\w*', search_type):
            raise ValueError('Invalid layout Search Type')
        align = attrs.get('align', 'stretch')
        tone = attrs.get('tone', 'normal')
        if action and action not in ACTIONS or variant not in VARIANTS or align not in ('stretch', 'start', 'center', 'end') or tone not in ('normal', 'muted', 'strong'):
            raise ValueError('Invalid layout element setting')
        if options.get('fit', 'cover') not in ('cover', 'contain'):
            raise ValueError('Invalid image fit')
        result['elements'].append(dict(name=name, title=element['title'], kind=kind, options=options,
            parent=attrs.get('parent', ''), variant=variant, search_type=search_type, align=align, tone=tone, layer=int(layer),
            role=role, tag=tag, flow=flow, when=when, **spacing(attrs),
            hidden=str(attrs.get('hidden', '')).lower() in ('true', '1', 'yes', 'on'),
            row=number(attrs.get('row'), 1, 100), column=number(attrs.get('column'), 1, 12),
            span=number(attrs.get('span'), 12, 12), rows=number(attrs.get('rows'), 1, 100),
            columns=number(attrs.get('columns'), 12, 12), height=number(attrs.get('height'), 40, 1200)))
    by_name = {element['name']: element for element in result['elements']}
    for element in result['elements']:
        parent = element['parent']
        seen = {element['name']}
        while parent:
            if parent in seen or parent not in by_name or by_name[parent]['kind'] != 'group':
                raise ValueError('Invalid or cyclic layout container')
            seen.add(parent)
            if len(seen) > 8:
                raise ValueError('Layout container depth exceeds 8')
            parent = by_name[parent]['parent']
        columns = by_name[element['parent']]['columns'] if element['parent'] else result['columns']
        if element['column'] + element['span'] - 1 > columns:
            raise ValueError('Layout element exceeds its container columns')
    if (result['flow']=='contents' or result['collection']=='table') and (
            any(key in attributes for key in ('padding','margin','gap')) or
            any(any(key in element['attributes'] for key in ('padding','margin','gap')) for element in description['elements'])):
        raise ValueError('Pixel spacing requires a grid card or tree layout')
    return result
