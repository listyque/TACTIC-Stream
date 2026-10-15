"""Data-only parts of TabWdg/EditWdg. No Wdg construction or browser code.

Source: tactic/ui/container/tab_wdg.py:get_display and
        tactic/ui/panel/edit_wdg.py:init/get_config.
Callbacks read the current authorized TACTIC context, not request-supplied XML.
"""
from __future__ import annotations
import ast
import copy
import json
import re
import xml.etree.ElementTree as ET
from .config_model import ConfigModel, ConfigSource, parse_xml, view_node, xml_text
from .view_resolution import inline_xml

MAX_TABS = 64


def false(value):
    return value is False or value == 'false'


def tab_model(options, include_reader, db_reader, saved_reader=lambda key: None):
    """Preserve legacy inline/saved/include/category precedence (last include).

    A saved state extends an explicit inline configuration; it does NOT replace
    the inline order/definitions. This sometimes surprising upstream rule is
    intentional here. Native saving of that combination is not advertised.
    """
    opts = dict(options or {})
    view = opts.get('view') or 'tab'
    raw = inline_xml(opts['config_xml']) if opts.get('config_xml') else None
    save_key = opts.get('save_state')
    if save_key in (True, 'true'):
        save_key = 'save_state|main_tab'
    if save_key and not isinstance(save_key, str):
        raise ValueError('Некорректный ключ save_state')
    saved = saved_reader(save_key) if save_key else None
    if saved:
        saved = inline_xml(saved)
        if raw:
            root, saved_root = parse_xml(raw), parse_xml(saved)
            current = next((n for n in root if isinstance(n.tag, str)), None)
            previous = next((n for n in saved_root if isinstance(n.tag, str)), None)
            if current is not None and previous is not None:
                names = {n.get('name') for n in current}
                for n in previous:
                    if n.get('name') not in names:
                        current.append(copy.deepcopy(n))
            raw = xml_text(root)
        else:
            raw = saved
    origin = 'TabWdg inline / saved state'
    if not raw and view != 'tab':
        # The original loop replaces config for EACH include, even when a later
        # include does not contain the view. Do not turn it into first-match.
        candidate = None
        for include in (opts.get('include') or '').split('|'):
            if not include:
                continue
            text = include_reader(include)
            candidate = text if view_node(parse_xml(text), view) is not None else None
        raw = candidate or db_reader(view)
        origin = 'TabWdg include / category=TabWdg'
    if not raw:
        root = ET.Element('config')
        node = ET.SubElement(root, 'view', {'name': view}) if '@' in view else ET.SubElement(root, view)
        if view == 'tab':
            ET.SubElement(node, 'element', {'name': 'untitled', 'title': '(Untitled)'})
        raw = xml_text(root)
    from pathlib import Path
    aliases = json.loads((Path(__file__).parent / 'widget_aliases.json').read_text(encoding='utf-8'))
    model = ConfigModel(view, [ConfigSource(raw, view, origin)], aliases)
    names = model.names() if save_key else None
    if not names:
        names = opts.get('element_names')
        if isinstance(names, str):
            names = names.split(',')
    names = names or model.names()
    if not isinstance(names, (list, tuple)) or len(names) > MAX_TABS:
        raise ValueError(f'Контейнер ограничен {MAX_TABS} вкладками')
    if any(not isinstance(n, str) or len(n) > 250 for n in names):
        raise ValueError('Некорректное имя вкладки')
    return model, list(names), save_key


def tab_items(parent, model, names, evaluate=None):
    from .config_model import target_spec
    opts = parent.get('options', {})
    state = dict(opts.get('state') or opts)
    if opts.get('search_key'):
        state['search_key'] = opts['search_key']
    selected = opts.get('selected') or (names[0] if names else '')
    protected = str(opts.get('show_remove_tabs') or '').split('|')
    result = []
    for index, name in enumerate(names):
        el = model.describe(name)
        if el['attributes'].get('display') == 'false':
            continue
        options = dict(el['options'])
        for key, value in list(options.items()):
            if isinstance(value, str) and re.search(r'^{[@$]', value) and value.endswith('}'):
                if evaluate is None:
                    raise ValueError('Вкладка требует server expression provider')
                options[key] = evaluate(value, state)
        if options.get('use_state') in (True, 'true'):
            options.update(state)
        child = target_spec(el['handler'], options, el['attributes'])
        child.update(id=parent['id'] + '/~tab/' + str(index), name=name,
                     title=el['title'], config_view=model.view, tab_index=index,
                     preload=el['attributes'].get('load') == 'true',
                     selected=name == selected,
                     removable=not false(opts.get('show_remove')) and name not in protected)
        result.append(child)
    return result


def default_values(value):
    """Legacy accepts a JSON object or Python dict literal. Never use eval."""
    if value in (None, ''):
        return {}
    if isinstance(value, str):
        if len(value) > 256 * 1024:
            raise ValueError('Слишком большой default')
        try:
            value = json.loads(value)
        except ValueError:
            value = ast.literal_eval(value)
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError('default должен быть словарём')
    # Return a detached JSON-safe object; no arbitrary Python values.
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def edit_base_model(stype, view, mode):
    """Original EditWdg.get_config order for nonstandard edit views."""
    from pyasm.search import WidgetDbConfig
    from .widget_config import WidgetConfigView
    if view in ('edit', 'insert'):
        return ConfigModel.from_tactic(WidgetConfigView.get_by_search_type(stype, view, use_cache=False))
    configs = []
    config = WidgetDbConfig.get_by_search_type(stype, view)
    got_edit_definition = False
    if config:
        configs.append(config)
        got_edit_definition = True
        config = WidgetDbConfig.get_by_search_type(stype, 'edit_definition')
        if config:
            configs.append(config)
    else:
        if mode == 'insert':
            config = WidgetDbConfig.get_by_search_type(stype, 'insert')
            if config:
                configs.append(config)
        config = WidgetDbConfig.get_by_search_type(stype, 'edit')
        if config:
            configs.append(config)
    configs.extend(WidgetConfigView.get_configs_from_file(stype, view))
    configs.extend(WidgetConfigView.get_configs_from_file(stype, 'edit'))
    if not got_edit_definition:
        config = WidgetDbConfig.get_by_search_type(stype, 'edit_definition')
        if config:
            configs.append(config)
    return ConfigModel.from_tactic(WidgetConfigView(stype, view, configs, layout='EditWdg'))


def resolve_edit(base, options):
    sources = list(base.sources)
    if options.get('layout_view'):
        raise ValueError('EditWdg.layout_view требует отдельного переноса HTML layout')
    if options.get('config_xml'):
        raw = inline_xml(options['config_xml'])
        sources = [ConfigSource(raw, base.view, 'EditWdg inline:view'),
                   ConfigSource(raw, 'tab', 'EditWdg inline:tab')] + sources
    names = options.get('element_names')
    if names:
        if isinstance(names, str):
            names = names.split(',')
        if not isinstance(names, (list, tuple)) or len(names) > 500:
            raise ValueError('Некорректный element_names формы')
        root = ET.Element('config'); node = ET.SubElement(root, 'native_form_order')
        for name in names:
            if not isinstance(name, str) or len(name) > 200:
                raise ValueError('Некорректное поле формы')
            ET.SubElement(node, 'element', {'name': name})
        sources.insert(0, ConfigSource(xml_text(root), 'native_form_order', 'EditWdg element_names'))
    return ConfigModel(base.view, sources, base.aliases)
