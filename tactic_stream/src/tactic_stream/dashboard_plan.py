"""Portable dashboard bricks shared by agent schemas and native server commands."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DashboardFilter(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    column: str = Field(min_length=1, max_length=128)
    relation: Literal['=', '!=', '<', '<=', '>', '>=', 'like'] = '='
    value: str | int | float | bool | None


class DashboardPageFilter(DashboardFilter):
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    search_type: str = Field(min_length=1, max_length=256)
    enabled: bool = False


class DashboardFilterValue(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool
    value: str | int | float | bool | None


class DashboardGrouping(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    column: str = Field(min_length=1, max_length=128)
    title: str = Field(default='', max_length=256)
    period: Literal['value', 'year', 'month', 'day'] = 'value'


class DashboardAggregate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    function: Literal['count', 'sum', 'avg', 'min', 'max'] = 'count'
    column: str = Field(default='', max_length=128)


class DashboardAppearance(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    fill: str = Field(default='transparent', pattern=r'^(transparent|panel|workspace|surfaceContainerLow|surfaceContainerLowest|#[0-9a-fA-F]{6})$')
    stroke: str = Field(default='outlineVariant', pattern=r'^(outlineVariant|contentAccent|transparent|#[0-9a-fA-F]{6})$')
    stroke_width: int = Field(default=0, ge=0, le=8)
    radius: int = Field(default=0, ge=0, le=48)
    shadow: bool = False
    animate: bool = False


class DashboardSizing(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    width_mode: Literal['auto', 'fixed', 'fill', 'content'] = 'auto'
    height_mode: Literal['auto', 'fixed', 'fill', 'content'] = 'auto'
    min_width: int = Field(default=0, ge=0, le=2400)
    max_width: int | None = Field(default=None, ge=40, le=2400)
    min_height: int = Field(default=0, ge=0, le=1600)
    max_height: int | None = Field(default=None, ge=24, le=1600)

    @model_validator(mode='after')
    def check_ranges(self):
        for axis in ('width', 'height'):
            maximum = getattr(self, 'max_' + axis)
            if maximum is not None and maximum < getattr(self, 'min_' + axis):
                raise ValueError('Maximum size must not be smaller than minimum size')
        return self


class DashboardBlock(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    region: Literal['header', 'content', 'footer'] = 'content'
    kind: Literal['row', 'column', 'text', 'markdown', 'metric', 'table', 'items', 'details', 'link', 'chart', 'summary', 'grid', 'heading', 'icon', 'image', 'button', 'divider', 'spacer', 'field', 'form', 'action']
    title: str = Field(default='', max_length=256)
    text: str = Field(default='', max_length=65536)
    source_key: str = Field(default='', max_length=2048)
    field: str = Field(default='', max_length=128)
    binding: Literal['auto', 'static', 'project', 'selection', 'record'] = 'auto'
    search_type: str = Field(default='', max_length=256)
    view: str = Field(default='table', pattern=r'^[A-Za-z_][\w.@-]{0,127}$')
    filters: list[DashboardFilter] = Field(default_factory=list, max_length=32)
    page_filters: dict[str, str] | None = Field(default=None, max_length=8)
    group_by: list[DashboardGrouping] = Field(default_factory=list, max_length=3)
    aggregates: list[DashboardAggregate] = Field(default_factory=list, max_length=8)
    measure: str = Field(default='', max_length=48)
    chart_type: Literal['bar', 'line', 'donut'] = 'bar'
    group_limit: int = Field(default=50, ge=1, le=100)
    group_order: Literal['group', 'value_asc', 'value_desc'] = 'group'
    href: str = Field(default='', max_length=2048)
    weight: int = Field(default=1, ge=1, le=12)
    width: int | None = Field(default=None, ge=40, le=2400)
    height: int | None = Field(default=None, ge=24, le=1600)
    padding: list[Annotated[int, Field(ge=0, le=256)]] = Field(default_factory=lambda: [0, 0, 0, 0], min_length=4, max_length=4)
    margin: list[Annotated[int, Field(ge=0, le=256)]] = Field(default_factory=lambda: [0, 0, 0, 0], min_length=4, max_length=4)
    gap: int = Field(default=8, ge=0, le=128)
    offset_x: int = Field(default=0, ge=-2400, le=2400)
    offset_y: int = Field(default=0, ge=-1600, le=1600)
    appearance: DashboardAppearance = Field(default_factory=DashboardAppearance)
    sizing: DashboardSizing = Field(default_factory=DashboardSizing)
    columns: int = Field(default=3, ge=1, le=12)
    min_cell_width: int = Field(default=200, ge=80, le=1200)
    row_height: int = Field(default=120, ge=40, le=800)
    column_span: int = Field(default=1, ge=1, le=12)
    row_span: int = Field(default=1, ge=1, le=12)
    collapse_width: int = Field(default=600, ge=0, le=2400)
    text_role: Literal['auto', 'caption', 'body', 'bodyLarge', 'title', 'heading', 'display', 'statistic', 'hero'] = 'auto'
    text_align: Literal['left', 'center', 'right'] = 'left'
    text_color: str = Field(default='auto', pattern=r'^(auto|primaryText|secondaryText|contentAccent|error|#[0-9a-fA-F]{6})$')
    text_weight: Literal[400, 600, 700] = 400
    icon: str = Field(default='', max_length=128, pattern=r'^[A-Za-z0-9_./:-]*$')
    icon_size: int = Field(default=32, ge=16, le=128)
    image_fit: Literal['cover', 'contain'] = 'contain'
    button_style: Literal['normal', 'primary', 'tonal'] = 'normal'
    fields: list[str] = Field(default_factory=list, max_length=16)
    edit_view: str = Field(default='edit', pattern=r'^[A-Za-z_][\w.@-]{0,127}$')
    format: Literal['plain', 'badge', 'progress', 'date', 'datetime', 'number'] = 'plain'
    suffix: str = Field(default='', max_length=32)
    native_action: Literal['details', 'edit', 'notes', 'copy_link', 'refresh'] = 'details'
    controls: list[Literal['search', 'searchLimit', 'shelf', 'selection', 'gear', 'insert']] | None = Field(default=None, max_length=6)
    children: list['DashboardBlock'] = Field(default_factory=list, max_length=32)


class DashboardDocument(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    filters: list[DashboardPageFilter] = Field(default_factory=list, max_length=8)
    blocks: list[DashboardBlock] = Field(min_length=0, max_length=32)


_SCALAR_DEFAULTS = (
    ('region', 'content', str),
    ('title', '', str),
    ('text', '', str),
    ('source_key', '', str),
    ('field', '', str),
    ('binding', 'auto', str),
    ('search_type', '', str),
    ('view', 'table', str),
    ('measure', '', str),
    ('chart_type', 'bar', str),
    ('group_limit', 50, int),
    ('group_order', 'group', str),
    ('href', '', str),
    ('weight', 1, int),
    ('width', None, int),
    ('height', None, int),
    ('gap', 8, int),
    ('offset_x', 0, int),
    ('offset_y', 0, int),
    ('columns', 3, int),
    ('min_cell_width', 200, int),
    ('row_height', 120, int),
    ('column_span', 1, int),
    ('row_span', 1, int),
    ('collapse_width', 600, int),
    ('text_role', 'auto', str),
    ('text_align', 'left', str),
    ('text_color', 'auto', str),
    ('text_weight', 400, int),
    ('icon', '', str),
    ('icon_size', 32, int),
    ('image_fit', 'contain', str),
    ('button_style', 'normal', str),
    ('edit_view', 'edit', str),
    ('format', 'plain', str),
    ('suffix', '', str),
    ('native_action', 'details', str),
)
_APPEARANCE_DEFAULTS = (
    ('fill', 'transparent', str),
    ('stroke', 'outlineVariant', str),
    ('stroke_width', 0, int),
    ('radius', 0, int),
    ('shadow', False, bool),
    ('animate', False, bool),
)
_SIZING_DEFAULTS = (
    ('width_mode', 'auto', str),
    ('height_mode', 'auto', str),
    ('min_width', 0, int),
    ('max_width', None, int),
    ('min_height', 0, int),
    ('max_height', None, int),
)
_SCALAR_MAP = {k: (d, t) for k, d, t in _SCALAR_DEFAULTS}
_APPEARANCE_MAP = {k: (d, t) for k, d, t in _APPEARANCE_DEFAULTS}
_SIZING_MAP = {k: (d, t) for k, d, t in _SIZING_DEFAULTS}
_BLOCK_KINDS = set(DashboardBlock.model_fields['kind'].annotation.__args__)


def _write_filter_attrs(elem, item):
    elem.set('column', item['column'])
    if item.get('relation', '=') != '=':
        elem.set('relation', item['relation'])
    val = item.get('value')
    if val is not None:
        if isinstance(val, bool):
            elem.set('value', 'true' if val else 'false')
            elem.set('value_type', 'bool')
        elif isinstance(val, int):
            elem.set('value', str(val))
            elem.set('value_type', 'int')
        elif isinstance(val, float):
            elem.set('value', str(val))
            elem.set('value_type', 'float')
        else:
            elem.set('value', str(val))


def _read_filter_value(elem):
    if 'value' not in elem.attrib:
        return None
    raw = elem.attrib['value']
    vtype = elem.attrib.get('value_type', 'str')
    if vtype == 'bool':
        if raw not in ('true', 'false'):
            raise ValueError('Filter boolean value must be true or false')
        return raw == 'true'
    if vtype == 'int':
        return int(raw)
    if vtype == 'float':
        return float(raw)
    if vtype == 'null':
        return None
    return raw


def _parse_typed(raw: str, typ, name: str):
    if typ is bool:
        if raw not in ('true', 'false'):
            raise ValueError(f'Attribute {name} must be true or false')
        return raw == 'true'
    if typ is int:
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f'Attribute {name} must be a whole number') from None
    return raw


def dashboard_to_xml(document: dict | DashboardDocument) -> str:
    from xml.etree import ElementTree as ET

    doc = (
        document.model_dump(mode='json')
        if isinstance(document, DashboardDocument)
        else DashboardDocument.model_validate(document).model_dump(mode='json')
    )
    root = ET.Element('config')
    view = ET.SubElement(root, 'view', name='dashboard.' + doc['name'], title=doc['title'])
    dash = ET.SubElement(view, 'dashboard')

    for pf in doc.get('filters') or []:
        f_elem = ET.SubElement(dash, 'filter', name=pf['name'], title=pf['title'], search_type=pf['search_type'])
        _write_filter_attrs(f_elem, pf)
        if pf.get('enabled'):
            f_elem.set('enabled', 'true')

    def emit_block(parent, block):
        elem = ET.SubElement(parent, block['kind'])
        multiline_text = False
        for key, default, _ in _SCALAR_DEFAULTS:
            val = block.get(key, default)
            if val != default and val is not None:
                if key == 'text' and '\n' in val:
                    multiline_text = True
                    continue
                elem.set(key, str(val))
        for key in ('padding', 'margin'):
            val = block.get(key)
            if val and val != [0, 0, 0, 0]:
                elem.set(key, ','.join(str(x) for x in val))
        if block.get('fields'):
            elem.set('fields', ','.join(block['fields']))
        if block.get('controls') is not None:
            elem.set('controls', ','.join(block['controls']))
        app = block.get('appearance') or {}
        for key, default, typ in _APPEARANCE_DEFAULTS:
            val = app.get(key, default)
            if val != default:
                elem.set(key, ('true' if val else 'false') if typ is bool else str(val))
        sz = block.get('sizing') or {}
        for key, default, _ in _SIZING_DEFAULTS:
            val = sz.get(key, default)
            if val != default and val is not None:
                elem.set(key, str(val))
        if multiline_text:
            ET.SubElement(elem, 'content').text = block['text']
        for flt in block.get('filters') or []:
            _write_filter_attrs(ET.SubElement(elem, 'filter'), flt)
        pf_map = block.get('page_filters')
        if pf_map is not None:
            if not pf_map:
                ET.SubElement(elem, 'page_filters', none='true')
            else:
                for k, v in pf_map.items():
                    ET.SubElement(elem, 'page_filter', name=k, column=v)
        for grp in block.get('group_by') or []:
            g_elem = ET.SubElement(elem, 'group_by', column=grp['column'])
            if grp.get('title'):
                g_elem.set('title', grp['title'])
            if grp.get('period', 'value') != 'value':
                g_elem.set('period', grp['period'])
        for agg in block.get('aggregates') or []:
            a_elem = ET.SubElement(elem, 'aggregate', name=agg['name'], title=agg['title'])
            if agg.get('function', 'count') != 'count':
                a_elem.set('function', agg['function'])
            if agg.get('column'):
                a_elem.set('column', agg['column'])
        for child in block.get('children') or []:
            emit_block(elem, child)

    for blk in doc.get('blocks') or []:
        emit_block(dash, blk)
    ET.indent(root, space='  ')
    if len(dash) == 0:
        dash.text = ''
    return ET.tostring(root, encoding='unicode')


def dashboard_from_xml(source, fallback_name: str = '') -> DashboardDocument:
    import json
    from xml.etree import ElementTree as ET

    if isinstance(source, DashboardDocument):
        return source
    if isinstance(source, dict):
        return DashboardDocument.model_validate(source)
    if isinstance(source, str):
        stripped = source.strip()
        if stripped.startswith('{'):
            return DashboardDocument.model_validate_json(stripped)
        try:
            elem = ET.fromstring(stripped)
        except ET.ParseError as exc:
            raise ValueError('Invalid dashboard XML') from exc
    elif isinstance(source, ET.Element):
        elem = source
    else:
        raise ValueError('Choose an existing dashboard')

    view_name = ''
    view_title = ''
    if elem.tag == 'dashboard':
        dash = elem
    elif elem.find('dashboard') is not None:
        view_name = elem.get('name') or (elem.tag if elem.tag != 'view' else '')
        view_title = elem.get('title') or ''
        dash = elem.find('dashboard')
    else:
        view_node = elem.find('view')
        if view_node is None:
            view_node = next((child for child in elem if child.find('dashboard') is not None), None)
        if view_node is not None:
            view_name = view_node.get('name') or (view_node.tag if view_node.tag != 'view' else '')
            view_title = view_node.get('title') or ''
            dash = view_node.find('dashboard')
        else:
            dash = elem.find('.//dashboard')

    if dash is None:
        raise ValueError('Choose an existing dashboard')

    raw_text = (dash.text or '').strip()
    if len(dash) == 0 and raw_text.startswith('{'):
        return DashboardDocument.model_validate_json(raw_text)
    if raw_text:
        raise ValueError('Unexpected text inside <dashboard>')

    name = dash.get('name') or (view_name[10:] if view_name.startswith('dashboard.') else view_name) or fallback_name
    title = dash.get('title') or view_title or name
    filters = []
    blocks = []

    def parse_block(node):
        if node.tag not in _BLOCK_KINDS:
            raise ValueError(f'Unsupported page widget <{node.tag}>')
        if (node.text or '').strip():
            raise ValueError(f'Use text attribute or <content> inside <{node.tag}>')
        blk: dict = {'kind': node.tag}
        app: dict = {}
        sz: dict = {}
        for attr, val in node.attrib.items():
            if attr in _SCALAR_MAP:
                blk[attr] = _parse_typed(val, _SCALAR_MAP[attr][1], attr)
            elif attr in ('padding', 'margin'):
                parts = [p.strip() for p in val.split(',')]
                if len(parts) != 4:
                    raise ValueError(f'Attribute {attr} requires four comma-separated numbers')
                blk[attr] = [_parse_typed(p, int, attr) for p in parts]
            elif attr == 'fields':
                blk['fields'] = [p.strip() for p in val.split(',') if p.strip()]
            elif attr == 'controls':
                blk['controls'] = [p.strip() for p in val.split(',') if p.strip()]
            elif attr in _APPEARANCE_MAP:
                app[attr] = _parse_typed(val, _APPEARANCE_MAP[attr][1], attr)
            elif attr in _SIZING_MAP:
                sz[attr] = _parse_typed(val, _SIZING_MAP[attr][1], attr)
            else:
                raise ValueError(f'Unsupported attribute "{attr}" on <{node.tag}>')
        if app:
            blk['appearance'] = app
        if sz:
            blk['sizing'] = sz
        b_filters = []
        b_page_filters = None
        b_group_by = []
        b_aggregates = []
        b_children = []
        for child in node:
            ctag = child.tag
            if ctag == 'content':
                blk['text'] = child.text or ''
            elif ctag == 'filter':
                allowed = {'column', 'relation', 'value', 'value_type'}
                if set(child.attrib) - allowed or 'column' not in child.attrib:
                    raise ValueError('Invalid <filter> attributes')
                b_filters.append({
                    'column': child.attrib['column'],
                    'relation': child.attrib.get('relation', '='),
                    'value': _read_filter_value(child),
                })
            elif ctag == 'page_filters':
                if child.attrib.get('none') == 'true' and b_page_filters is None:
                    b_page_filters = {}
            elif ctag == 'page_filter':
                if 'name' not in child.attrib or 'column' not in child.attrib or set(child.attrib) - {'name', 'column'}:
                    raise ValueError('Invalid <page_filter> attributes')
                if b_page_filters is None:
                    b_page_filters = {}
                b_page_filters[child.attrib['name']] = child.attrib['column']
            elif ctag == 'group_by':
                if 'column' not in child.attrib or set(child.attrib) - {'column', 'title', 'period'}:
                    raise ValueError('Invalid <group_by> attributes')
                b_group_by.append({
                    'column': child.attrib['column'],
                    'title': child.attrib.get('title', ''),
                    'period': child.attrib.get('period', 'value'),
                })
            elif ctag == 'aggregate':
                if 'name' not in child.attrib or 'title' not in child.attrib or set(child.attrib) - {'name', 'title', 'function', 'column'}:
                    raise ValueError('Invalid <aggregate> attributes')
                b_aggregates.append({
                    'name': child.attrib['name'],
                    'title': child.attrib['title'],
                    'function': child.attrib.get('function', 'count'),
                    'column': child.attrib.get('column', ''),
                })
            elif ctag == 'appearance':
                for k, v in child.attrib.items():
                    if k not in _APPEARANCE_MAP:
                        raise ValueError(f'Unsupported appearance attribute "{k}"')
                    app[k] = _parse_typed(v, _APPEARANCE_MAP[k][1], k)
                blk['appearance'] = app
            elif ctag == 'sizing':
                for k, v in child.attrib.items():
                    if k not in _SIZING_MAP:
                        raise ValueError(f'Unsupported sizing attribute "{k}"')
                    sz[k] = _parse_typed(v, _SIZING_MAP[k][1], k)
                blk['sizing'] = sz
            elif ctag in _BLOCK_KINDS:
                b_children.append(parse_block(child))
            else:
                raise ValueError(f'Unsupported element <{ctag}> inside <{node.tag}>')
        if b_filters:
            blk['filters'] = b_filters
        if b_page_filters is not None:
            blk['page_filters'] = b_page_filters
        if b_group_by:
            blk['group_by'] = b_group_by
        if b_aggregates:
            blk['aggregates'] = b_aggregates
        if b_children:
            blk['children'] = b_children
        return blk

    for child in dash:
        if child.tag == 'filter':
            allowed = {'name', 'title', 'search_type', 'column', 'relation', 'value', 'value_type', 'enabled'}
            if set(child.attrib) - allowed or not {'name', 'title', 'search_type', 'column'}.issubset(child.attrib):
                raise ValueError('Invalid page <filter> attributes')
            filters.append({
                'name': child.attrib['name'],
                'title': child.attrib['title'],
                'search_type': child.attrib['search_type'],
                'column': child.attrib['column'],
                'relation': child.attrib.get('relation', '='),
                'value': _read_filter_value(child),
                'enabled': _parse_typed(child.attrib.get('enabled', 'false'), bool, 'enabled'),
            })
        else:
            blocks.append(parse_block(child))

    return DashboardDocument.model_validate({
        'name': name,
        'title': title,
        'filters': filters,
        'blocks': blocks,
    })
