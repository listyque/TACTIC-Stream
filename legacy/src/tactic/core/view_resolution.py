"""Resolve the TABLE-specific config branches of BaseTableLayoutWdg.__init__.

WidgetConfigView still loads DB/project/personal/default layers. This module
adds the original inline / config_code / element_names / custom-column branch,
without instantiating a Wdg or mutating the cached WidgetConfigView.
The caller supplies trusted *server-resolved* options, never browser XML.
"""
import re
from copy import deepcopy
from types import SimpleNamespace
from .table_settings import TableSettingsMixin
import xml.etree.ElementTree as ET
from .config_model import ConfigModel, ConfigSource, parse_xml, xml_text


def inline_xml(raw):
    root = parse_xml(raw)
    if root.tag == 'config_xml' and len(root) == 1 and root[0].tag == 'config':
        root = root[0]
    if root.tag != 'config':
        raise ValueError('Inline table config must contain <config>')
    return xml_text(root)


def resolve_table(base, options, columns=(), code_loader=None):
    """Same branch precedence as the original table, including empty views."""
    options = options or {}
    if options.get('config_xml'):
        source = ConfigSource(inline_xml(options['config_xml']), base.view, 'inline:config_xml')
        return ConfigModel(base.view, [source] + list(base.sources), base.aliases)
    if options.get('config_code'):
        if code_loader is None:
            raise ValueError('config_code loader is required')
        code = options['config_code']
        if not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9_.:@-]{1,200}', code):
            raise ValueError('Invalid config_code')
        return code_loader(code)
    sources = list(base.sources)
    names = options.get('element_names')
    if names:
        if isinstance(names, str):
            names = [n.strip() for n in names.split(',')]
        if not isinstance(names, (tuple, list)) or len(names) > 500 or any(not isinstance(n, str) or len(n) > 200 for n in names):
            raise ValueError('Invalid element_names')
        root = ET.Element('config')
        view = ET.SubElement(root, 'custom', {'layout': 'TableLayoutWdg'})
        for name in names:
            ET.SubElement(view, 'element', {'name': name})
        sources.insert(0, ConfigSource(xml_text(root), 'custom', 'inline:element_names'))
    sources.extend(columns)
    return ConfigModel(base.view, sources, base.aliases)


def table_options(options, attributes=None):
    """Presentation flags; these are NOT authorization grants."""
    opts = dict(options or {})
    def flag(name, default=True):
        value = opts.get(name)
        return default if value is None else value not in (False, 'false', 'False', 'none')
    setting = lambda name: bool(TableSettingsMixin.get_setting(SimpleNamespace(kwargs=deepcopy(opts)), name))
    mode = opts.get('layout') or ''
    raw_limit = opts.get('search_limit')
    try: requested_limit = int(raw_limit) if raw_limit else 100
    except (ValueError, TypeError): requested_limit = 100
    page_size = max(1, min(200, requested_limit)) if requested_limit > 0 else 200
    return {
        'show_header': flag('show_header'), 'show_select': flag('show_select'),
        'show_shelf': flag('show_shelf'), 'show_search_limit': setting('search_limit'),
        'show_gear': setting('gear'), 'show_refresh': setting('refresh'),
        'show_insert': setting('insert'),
        'show_context_menu': flag('show_context_menu'),
        'show_column_manager': setting('column_manager'),
        'show_layout_switcher': setting('layout_switcher'),
        'show_search': setting('search'), 'show_keyword_search': setting('keyword_search'),
        'page_size': page_size, 'limit_notice': 'Native page ограничена 200 строками; штатный unlimited/chunk-mode пока не перенесён' if requested_limit <= 0 or requested_limit > 200 else '',
        'initial_mode': 'cards' if mode in ('tile', 'tile_layout') or opts.get('native_layout') == 'cards' else 'table',
        'empty_message': str(opts.get('no_results_msg') or 'Нет записей по этому представлению')[:2000],
    }


def configured_sort(raw, fields):
    """Only plain column ORDER BY is supported; never reinterpret SQL/functions."""
    if not raw:
        return []
    if not isinstance(raw, str) or len(raw) > 1000:
        raise ValueError('Invalid configured order_by')
    allowed = {f['name']: f for f in fields if f.get('storage') and f.get('sortable', True)}
    result = []
    for part in raw.split(','):
        match = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s+(asc|desc))?\s*', part, re.I)
        if not match or match[1] not in allowed:
            raise ValueError('Настроенный order_by не является доступной обычной колонкой: ' + part[:120])
        result.append({'field': match[1], 'direction': (match[2] or 'asc').lower()})
    if len(result) > 8:
        raise ValueError('Слишком много полей order_by')
    return result
