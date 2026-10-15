"""Presentation-free projection of TACTIC widget configs.

Precedence matches WidgetConfigView: first non-definition view owns order (even
when empty); attributes cascade; handler and options are resolved independently;
options use the first non-empty block, NOT a deep merge. No imported widgets,
HTML rendering, JS execution or eval. Unknown nodes remain in original XML.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

DEFINITIONS = {'definition', 'default_definition', 'edit_definition'}
MAX_XML = 4 * 1024 * 1024


def parse_xml(text):
    if not isinstance(text, (str, bytes)):
        raise ValueError('XML must be text')
    raw = text.encode('utf-8') if isinstance(text, str) else text
    if len(raw) > MAX_XML or re.search(br'<!\s*(DOCTYPE|ENTITY)', raw, re.I):
        raise ValueError('Oversized XML or external entities are not allowed')
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(raw, parser=parser)
    if sum(1 for _ in root.iter()) > 20000:
        raise ValueError('Too many XML nodes')
    return root


def xml_text(root):
    return ET.tostring(root, encoding='unicode')


def revision(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def view_node(root, name):
    # Do not interpolate view names into XPath. Handles names such as "@...".
    for node in root:
        if node.tag == name or (node.tag == 'view' and node.get('name') == name):
            return node
    return None


def title(name):
    # Same spelling/camel-case handling as Common.get_display_title.
    name = str(name).strip()
    if '_' not in name:
        name = re.sub('([A-Z])', r' \1', name).strip().title()
        return re.sub(' +', ' ', name).title()
    return name.replace('_', ' ').title()


@dataclass
class ConfigSource:
    text: str
    view: str
    origin: str = 'configuration'

    def __post_init__(self):
        self.root = parse_xml(self.text)
        if self.root.tag != 'config':
            raise ValueError('Widget config root must be <config>')
        self.node = view_node(self.root, self.view)

    def element(self, name):
        if self.node is not None:
            return next((n for n in self.node if n.tag == 'element' and n.get('name') == name), None)
        return None


class ConfigModel:
    def __init__(self, view, sources, aliases=None):
        self.view, self.sources = view, list(sources)
        self.aliases = aliases or {}

    @classmethod
    def from_tactic(cls, config):
        sources = []
        for item in config.get_configs():
            x = item.get_xml()
            if x is None:
                continue
            raw = x.to_string()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            origin = item.get_file_path() if hasattr(item, 'get_file_path') else None
            if not origin and hasattr(item, 'get_code'):
                origin = 'config/widget_config:' + str(item.get_code())
            sources.append(ConfigSource(raw, item.get_view(), origin or 'generated'))
        aliases = json.loads(Path(__file__).with_name('widget_aliases.json').read_text())
        return cls(config.get_view(), sources, aliases)

    def names(self):
        for source in self.sources:
            if self.view in DEFINITIONS:
                if source.view not in DEFINITIONS:
                    continue
                names = self._names(source)
                if names:
                    return names
            else:
                if source.view in DEFINITIONS:
                    continue
                names = self._names(source)
                if names or source.node is not None:
                    return names
        return []

    @staticmethod
    def _names(source):
        return [n.get('name', '') for n in source.node if n.tag == 'element'] if source.node is not None else []

    def attributes(self, name=None):
        result = {}
        for source in self.sources:
            n = source.node if name is None else source.element(name)
            if n is not None:
                for key, value in n.attrib.items():
                    result.setdefault(key, value)
        return result

    def handler(self, name, kind='display'):
        for source in self.sources:
            if source.node is None:
                continue
            nodes = [e.find(kind) for e in source.node if e.tag == 'element' and e.get('name') == name and e.find(kind) is not None]
            # Original XPath selects the first declared @class across duplicate
            # definitions, then the first @widget. Attributes/order still use
            # the original first element. Duplicate definitions must not mask it.
            declared = next((n.get('class') for n in nodes if n.get('class')), None)
            if declared:
                return declared
            alias = next((n.get('widget') for n in nodes if n.get('widget')), None)
            if alias:
                return self.aliases.get(alias, alias)
        return ''

    def options(self, name, kind='display'):
        for source in self.sources:
            node = next((e.find(kind) for e in source.node if e.tag == 'element' and e.get('name') == name and e.find(kind) is not None), None) if source.node is not None else None
            if node is None:
                continue
            from .config_options import options_from_node
            result = options_from_node(node)
            if result:
                return result
        return {}

    def elements(self):
        return [self.describe(name) for name in self.names() if name]

    def describe(self, name):
        attrs = self.attributes(name)
        provenance = [s.origin for s in self.sources if s.element(name) is not None]
        return {'name': name, 'title': attrs.get('title') or title(name), 'attributes': attrs,
                'handler': self.handler(name), 'options': self.options(name),
                'edit_handler': self.handler(name, 'edit'), 'edit_options': self.options(name, 'edit'),
                'action_handler': self.handler(name, 'action'), 'action_options': self.options(name, 'action'),
                'sources': provenance}

    def fingerprint(self):
        return revision(json.dumps([(s.text, s.view, s.origin) for s in self.sources], ensure_ascii=False))


# Renderer registry describes widget semantics, not sidebar entries.
TABLE_HANDLERS = {'', 'LinkWdg', 'TableWdg', 'TableLayoutWdg', 'FastTableLayoutWdg',
                  'tactic.ui.panel.ViewPanelWdg', 'tactic.ui.panel.TableLayoutWdg',
                  'tactic.ui.panel.FastTableLayoutWdg', 'tactic.ui.panel.table_layout_wdg.FastTableLayoutWdg',
                  'tactic.ui.panel.TileLayoutWdg'}
SCREEN_HANDLERS = {
 'DbConfigWdg':'system-config', 'DbConfigContentWdg':'system-config', 'DbConfigPanelWdg':'system-config',
 'LicenseManagerWdg':'license', 'LicenseUploadWdg':'license',
    'tactic.ui.tools.PipelineToolWdg': 'pipeline',
    'tactic.ui.tools.PipelineEditorWdg': 'pipeline',
    'tactic.ui.tools.SchemaToolWdg': 'schema',
    'tactic.ui.panel.ManageViewPanelWdg': 'sidebar-editor',
    'tactic.ui.manager.ViewManagerWdg': 'views-manager',
    'tactic.ui.tools.CustomLayoutEditWdg': 'layout-editor',
    'tactic.ui.startup.ProjectConfigWdg': 'search-types',
    'tactic.ui.startup.HomeWdg': 'search-types',
    'tactic.ui.panel.EditWdg': 'form',
    'tactic.ui.container.TabWdg': 'tabs',
}


SCREEN_HANDLERS.update({
    'tactic.ui.app.ProjectCreateWdg': 'project-create',
    'tactic.ui.startup.ProjectCreateWdg': 'project-create',
    'tactic.ui.startup.UserConfigWdg': 'users',
    'tactic.ui.startup.UserPanelWdg': 'users',
    'tactic.ui.startup.SecurityWdg': 'security',
    'tactic.ui.app.SystemInfoWdg': 'system',
})

for _widget in ('ShelfEditWdg', 'ScriptEditorWdg'):
    SCREEN_HANDLERS['tactic.ui.app.' + _widget] = 'script-editor'
    SCREEN_HANDLERS['tactic.ui.app.shelf_wdg.' + _widget] = 'script-editor'

# Widget semantics, not hard-coded sidebar entries.
for _widget in ('SubscriptionWdg', 'SubscriptionBarWdg', 'ChatWdg', 'ChatSessionWdg'):
    SCREEN_HANDLERS['tactic.ui.app.' + _widget] = 'message-center'
    SCREEN_HANDLERS['tactic.ui.app.message_wdg.' + _widget] = 'message-center'

for _widget in ('CollectionLayoutWdg', 'CollectionContentWdg', 'CollectionListWdg', 'CollectionAddWdg'):
    SCREEN_HANDLERS['tactic.ui.panel.' + _widget] = 'collections'
    SCREEN_HANDLERS['tactic.ui.panel.collection_wdg.' + _widget] = 'collections'

SCREEN_HANDLERS.update({'EditWdg':'form', 'tactic.ui.panel.edit_wdg.EditWdg':'form',
                        'TabWdg':'tabs', 'tactic.ui.container.tab_wdg.TabWdg':'tabs'})

for _name in ('DbConfigWdg','DbConfigContentWdg','DbConfigPanelWdg'):
    SCREEN_HANDLERS['tactic.ui.startup.'+_name]='system-config'
    SCREEN_HANDLERS['tactic.ui.startup.db_config_wdg.'+_name]='system-config'
for _name in ('LicenseManagerWdg','LicenseUploadWdg'):
    SCREEN_HANDLERS['tactic.ui.app.'+_name]='license'
    SCREEN_HANDLERS['tactic.ui.app.license_manager_wdg.'+_name]='license'

# Explicit original modules/exports: no suffix-based guessing for plugin widgets.
for _name, _module in (
    ('PipelineToolWdg', 'tactic.ui.tools.pipeline_wdg'),
    ('PipelineEditorWdg', 'tactic.ui.tools.pipeline_wdg'),
    ('SchemaToolWdg', 'tactic.ui.tools.schema_wdg'),
    ('ProjectConfigWdg', 'tactic.ui.startup.project_config_wdg'),
    ('ProjectCreateWdg', 'tactic.ui.app.page_header_wdg'),
    ('SystemInfoWdg', 'tactic.ui.app.system_info_wdg'),
    ('UserConfigWdg', 'tactic.ui.startup.project_config_wdg'),
    ('SecurityWdg', 'tactic.ui.startup.security_wdg'),
):
    _base = next((k for k in SCREEN_HANDLERS if k.endswith('.' + _name)), None)
    if _base:
        SCREEN_HANDLERS[_name] = SCREEN_HANDLERS[_base]
        SCREEN_HANDLERS[_module + '.' + _name] = SCREEN_HANDLERS[_base]

# Explicit stock admin widget exports; never match arbitrary plugin basenames.
for _name in ('ProjectSecurityWdg','SearchTypeSecurityWdg','GearMenuSecurityWdg','LinkSecurityWdg','ProcessSecurityWdg','TaskSecurityWdg'):
    for _prefix in ('','tactic.ui.startup.','tactic.ui.startup.security_wdg.'):
        SCREEN_HANDLERS[_prefix+_name]='security'
for _name,_kind in (('UserSecurityWdg','group-assignment'),('GroupAssignWdg','group-assignment'),('SecurityGroupListWdg','groups')):
    for _prefix in ('','tactic.ui.startup.','tactic.ui.startup.security_wdg.'):
        SCREEN_HANDLERS[_prefix+_name]=_kind
for _name,_package,_module,_kind in (
 ('UserPanelWdg','startup','project_config_wdg','users'),
 ('SearchTypeToolWdg','app','search_type_creator_wdg','search-types'),
 ('SearchTypeManagerWdg','panel','search_type_manager_wdg','search-types'),
 ('ColumnEditWdg','startup','column_edit_wdg','search-types'),
 ('ManageViewPanelWdg','panel','manage_view_panel_wdg','sidebar-editor')):
    for _prefix in ('','tactic.ui.'+_package+'.','tactic.ui.'+_package+'.'+_module+'.'):
        SCREEN_HANDLERS[_prefix+_name]=_kind

for _name, _prefixes, _kind in (
 ('ViewManagerWdg', ('', 'tactic.ui.manager.', 'tactic.ui.manager.view_manager_wdg.', 'tactic.ui.panel.', 'tactic.ui.panel.view_manager_wdg.'), 'views-manager'),
 ('CustomLayoutEditWdg', ('', 'tactic.ui.tools.', 'tactic.ui.tools.custom_layout_edit_wdg.'), 'layout-editor')):
    for _prefix in _prefixes: SCREEN_HANDLERS[_prefix+_name]=_kind

for _prefix in ('', 'tactic.ui.panel.', 'tactic.ui.panel.custom_layout_wdg.'):
    SCREEN_HANDLERS[_prefix+'CustomLayoutWdg']='custom-layout'

def target_spec(handler, options, attributes=None):
    options = dict(options)
    # Whitespace around an identifier is layout, unlike whitespace inside scalar display options.
    actual = str(options.get('class_name') or handler or 'tactic.ui.panel.ViewPanelWdg').strip()
    if actual == 'LinkWdg':
        actual = 'tactic.ui.panel.ViewPanelWdg'
    kind = SCREEN_HANDLERS.get(actual)
    if actual in ('pyasm.prod.site.MyNotificationLogWdg', 'pyasm.prod.site.my_tactic_tab_wdg.MyNotificationLogWdg'):
        # Preserve the widget's HIDDEN recipient filter; this is not an
        # unrestricted alias for the notification_log table.
        options.update(search_type='sthpw/notification_log', view='table', native_notification_scope=True)
        kind = 'table'

    if actual in TABLE_HANDLERS and options.get('search_type'):
        kind = 'table'
        if actual == 'tactic.ui.panel.TileLayoutWdg': options['native_layout'] = 'cards'
    if actual == 'tactic.ui.panel.CustomLayoutWdg' and options.get('view') == 'user_to_group_planner':
        kind = 'group-membership'
    # A custom layout isn't silently downgraded to a plain data table.
    return {'kind': kind or 'unsupported', 'handler': actual,
            'search_type': options.get('search_type'), 'view': options.get('view') or (options.get('config_base') or 'edit' if kind == 'form' else 'tab' if kind == 'tabs' else 'table'),
            'options': options, 'attributes': dict(attributes or {})}


class SidebarProjection:
    """Projects original configs into a tree. loader(view, personal)->ConfigModel."""
    def __init__(self, loader, allowed, project, login, max_depth=24):
        self.loader, self.allowed = loader, allowed
        self.project, self.login, self.max_depth = project, login, max_depth
        self.targets = {}

    def build(self, views):
        sections = []
        for view in views:
            model = self.loader(view, view.startswith('my_view_'))
            children = self._children(model, view, (), view.startswith('my_view_'))
            if children:
                heading = model.attributes().get('title') or ('My views' if view.startswith('my_view_') else view.replace('_', ' ').capitalize())
                sections.append({'view': view, 'title': heading, 'children': children, 'revision': model.fingerprint()})
        return sections

    def _children(self, model, path, ancestors, personal):
        if model.view in ancestors or len(ancestors) >= self.max_depth:
            return [{'id': path + '/cycle', 'kind': 'diagnostic', 'title': 'Цикл конфигурации: ' + model.view}]
        result = []
        occurrences = {}
        for index, el in enumerate(model.elements()):
            name, attrs, opts, handler = el['name'], el['attributes'], el['options'], el['handler']
            if not self.allowed(name) or attrs.get('is_visible') == 'false':
                continue
            occurrence = occurrences.get(name, 0)
            occurrences[name] = occurrence + 1
            # Link identity must survive a change in visual order.
            key = path + '/' + quote(name, safe='') + ('#' + str(occurrence) if occurrence else '')
            node = {'id': key, 'name': name, 'title': el['title'], 'icon': attrs.get('icon', ''),
                    'config_view': model.view, 'open': attrs.get('state') == 'open', 'sources': el['sources']}
            if handler == 'SeparatorWdg':
                node['kind'] = 'separator'
            elif handler == 'TitleWdg':
                node['kind'] = 'title'
            elif handler in {'FolderWdg', 'SideBarSectionLinkWdg'}:
                node['kind'] = 'folder'
                view = opts.get('view')
                node['children'] = self._children(self.loader(view, personal), key, ancestors + (model.view,), personal) if view else []
            else:
                node['kind'] = 'link'
                if attrs.get('view'):
                    handler, opts = 'tactic.ui.panel.CustomLayoutWdg', {'view': attrs['view']}
                spec = target_spec(handler, opts, attrs)
                spec.update({'id': key, 'name': name, 'title': node['title'], 'config_view': model.view})
                self.targets[key] = spec
                node['renderer'] = spec['kind']
                # Browser sends ONLY this opaque id; server resolves original config again.
            result.append(node)
        return result


def reorder_view(text, view, order):
    """Reorder existing elements only; preserve extensions, attributes and definitions."""
    root = parse_xml(text)
    node = view_node(root, view)
    if node is None:
        raise ValueError('View not found')
    elements = [n for n in node if n.tag == 'element']
    # Use indices, since duplicate separator names are legal in upstream.
    if not isinstance(order, list) or any(type(i) is not int for i in order) or sorted(order) != list(range(len(elements))):
        raise ValueError('Order must be an exact permutation of existing element indices')
    replacements = iter([elements[i] for i in order])
    children = [next(replacements) if n.tag == 'element' else n for n in node]
    node[:] = children
    return xml_text(root)


def patch_pipeline_positions(text, positions):
    """Only coordinates are changed. Unknown XML/settings/links are retained."""
    root = parse_xml(text)
    if root.tag != 'pipeline':
        raise ValueError('Expected pipeline XML')
    process = {n.get('name'): n for n in root.findall('process')}
    if len(process) != len(root.findall('process')):
        raise ValueError('Duplicate process names')
    if not isinstance(positions, dict) or any(name not in process for name in positions):
        raise ValueError('Unknown process')
    for name, xy in positions.items():
        if not isinstance(xy, dict) or set(xy) != {'x', 'y'}:
            raise ValueError('Expected x/y coordinates')
        for axis in ('x', 'y'):
            value = xy[axis]
            if type(value) not in (int, float) or not -100000 <= value <= 100000:
                raise ValueError('Invalid coordinate')
            process[name].set(axis + "pos", str(round(value, 2)))
    return xml_text(root)
