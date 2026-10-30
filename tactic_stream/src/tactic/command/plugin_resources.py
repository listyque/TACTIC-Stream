"""Typed resources over the original plugin manifest and native SObjects.

Packages remain ordinary TACTIC packages. There is no separate resource registry.
"""
import hashlib
import json
import re
import textwrap
from xml.etree import ElementTree as ET

from pyasm.biz import Project, ProjectSetting
from pyasm.common import TacticException
from pyasm.search import Search, SearchType
from tactic.command.plugin import PluginBase, _manifest_xml

THEME_SETTING = 'appearance/plugin_theme'
KINDS = ('widget', 'column', 'theme', 'python', 'data')


def theme_palette(source):
    root = _manifest_xml(source).get_root_node()
    theme = root.find('./*/theme')
    if theme is None or theme.get('style') not in ('md3', 'material5', 'fluent'):
        raise TacticException('Theme requires md3, material5 or fluent style')
    result = dict(style=theme.get('style'))
    for mode in ('light', 'dark'):
        values = theme.find(mode)
        if values is None or set(values.attrib) != {'base', 'accent'}:
            raise TacticException('Theme requires light and dark base/accent colors')
        if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', value) for value in values.attrib.values()):
            raise TacticException('Theme colors must use #RRGGBB')
        result[mode] = dict(values.attrib)
    return result


def selected_theme():
    """Read-only palette for project viewers; never evaluate manifest expressions."""
    if Project.get_project_code() in ('admin', 'sthpw'):
        return None
    source = ProjectSetting.get_value_by_key(THEME_SETTING)
    if not source:
        return None
    try:
        selection = json.loads(source)
    except ValueError:
        return None
    if not isinstance(selection, dict) or not all(isinstance(selection.get(key), str) for key in ('view', 'plugin')):
        return None
    view = selection['view']
    if not Search.get_by_code('config/plugin', selection['plugin']):
        return None
    search = Search('config/widget_config')
    search.add_filter('view', view)
    search.add_filter('widget_type', 'theme')
    theme = search.get_sobject()
    if theme is None:
        return None
    try:
        return dict(theme_palette(theme.get_value('config')), view=view, plugin=selection['plugin'])
    except (ET.ParseError, ValueError, TacticException):
        return None


def resource_revision(row):
    return hashlib.sha256(json.dumps(row.get_data(), sort_keys=True, default=str).encode()).hexdigest()


def resources(manifest):
    """Administrator inventory, with the installer's exact selection semantics."""
    package = PluginBase(manifest=manifest, verbose=False)
    result, seen = [], set()
    for index, node in enumerate(package.xml.get_root_node()):
        if node.tag == 'sobject':
            rows = package.get_sobjects_by_node(node)
            if node.get('search_type') not in ('config/widget_config', 'config/custom_script'):
                result.append(dict(key='manifest:' + str(index), kind='data', title=node.get('search_type', '')
                                   + (' / ' + node.get('code') if node.get('code') else ''),
                                   field='', path=node.get('path', ''), count=len(rows)))
                continue
            for row in rows:
                key = row.get_search_key()
                if key in seen:
                    continue
                seen.add(key)
                base = row.get_base_search_type()
                kind = (row.get_value('widget_type', no_exception=True) or 'configuration'
                        if base == 'config/widget_config' else
                        'python' if row.get_value('language', no_exception=True) in ('python', 'python3') else 'script')
                field = 'config' if base == 'config/widget_config' else 'script' if base == 'config/custom_script' else ''
                result.append(dict(key=key, kind=kind, searchType=base, code=row.get_code(),
                                   title=row.get_value('view', no_exception=True) or row.get_value('title', no_exception=True)
                                   or row.get_value('name', no_exception=True) or row.get_code(),
                                   field=field, language=row.get_value('language', no_exception=True), revision=resource_revision(row)))
        elif node.tag in ('search_type', 'python', 'include', 'plugin'):
            result.append(dict(key='manifest:' + str(index), kind=node.tag,
                               title=node.get('code') or node.get('search_type') or node.get('path') or node.tag,
                               field='', path=node.get('path') or (node.get('code', '').replace('/', '_') + '.spt' if node.tag == 'search_type' else ''), undoPath=node.get('undo_path', '')))
            if node.tag == 'python' and node.get('undo_path'):
                result.append(dict(key='manifest:' + str(index) + ':undo',kind='python',title=node.get('undo_path'),field='',path=node.get('undo_path')))
    order = {kind: index for index, kind in enumerate(('widget', 'column', 'theme', 'python', 'configuration', 'data', 'search_type', 'include', 'plugin'))}
    return sorted(result, key=lambda item: order.get(item['kind'], 10))


def resource_document(manifest, key):
    entry = next((item for item in resources(manifest) if item['key'] == key and item['field']), None)
    if entry is None:
        raise TacticException('Select an editable resource belonging to this plugin')
    row = Search.get_by_search_key(key)
    result = dict(entry, source=row.get_value(entry['field']), palette=None)
    if entry['kind'] == 'theme':
        try:
            result['palette'] = theme_palette(result['source'])
        except (ValueError, ET.ParseError, TacticException) as error:
            result['validationError'] = str(error)
    if entry['kind'] in ('widget', 'column'):
        from pyasm.widget import WidgetConfig, WidgetConfigView
        from tactic_stream.server.interface import describe_composition
        target = row.get_value('search_type')
        sample = Project.get() if target == 'ALL' else Search(target).get_sobject()
        from pyasm.common import XmlException
        from pyasm.widget import WidgetConfigException
        try:
            config = WidgetConfig.get(view=entry['title'], xml=result['source'], use_cache=False)
            description = describe_composition(WidgetConfigView(target, entry['title'], [config]), target)
            if 'item_layout' not in description:
                raise ValueError('This resource requires a modern sobject-layout definition for preview')
            result['layout'] = description['item_layout']
        except (ValueError, ET.ParseError, TacticException, XmlException, WidgetConfigException) as error:
            result['validationError'] = str(error)
        record = sample.get_data() if sample else dict(name='Example item', description='Preview data', status='In progress', progress=50)
        result['sample'] = dict(kind='object', record=record, title=record.get('name') or record.get('title') or 'Example item')
    return result


def save_resource(manifest, document):
    current = resource_document(manifest, document.get('key'))
    if current['revision'] != document.get('revision'):
        raise TacticException('Resource changed on the server. Reload before saving.')
    source = document.get('source')
    if not isinstance(source, str) or len(source.encode('utf-8')) > 2 * 1024 * 1024:
        raise TacticException('Resource source must be UTF-8 and at most 2 MiB')
    row = Search.get_by_search_key(current['key'])
    if current['kind'] == 'theme':
        theme_palette(source)
    elif current['field'] == 'config':
        from pyasm.widget import WidgetConfig, WidgetConfigView
        from tactic_stream.server.interface import describe_composition
        config = WidgetConfig.get(view=current['title'], xml=source, use_cache=False)
        if not config.has_view():
            raise TacticException('Configuration must contain its resource view')
        describe_composition(WidgetConfigView(row.get_value('search_type'), current['title'], [config]), row.get_value('search_type'))
    elif current['kind'] == 'python' and row.get_value('language') in ('python', 'python3'):
        compile('def plugin_action():\n' + textwrap.indent(source, '    '), current['title'], 'exec')
    row.set_value(current['field'], source)
    row.commit()


def scaffold(kind, view):
    root = ET.Element('config')
    if kind == 'theme':
        layout = ET.SubElement(root, view)
        theme = ET.SubElement(layout, 'theme', style='md3')
        ET.SubElement(theme, 'light', base='#f6f8fa', accent='#226b8c')
        ET.SubElement(theme, 'dark', base='#20282c', accent='#8bc9e5')
    else:
        layout = ET.SubElement(root, view, layout='sobject-layout', collection='list',
                               columns='12', padding='8 8 8 8', gap='6')
        element = ET.SubElement(layout, 'element', name='title', title='Title', tag='strong')
        ET.SubElement(ET.SubElement(element, 'display', {'class': 'title'}), 'bind').text = 'node.title'
        if kind == 'widget':
            element = ET.SubElement(layout, 'element', name='description', title='Description', row='2')
            ET.SubElement(ET.SubElement(element, 'display', {'class': 'description'}), 'bind').text = 'record.description'
            element = ET.SubElement(layout, 'element', name='notes', title='Notes', row='3')
            display = ET.SubElement(element, 'display', {'class': 'button'})
            ET.SubElement(display, 'action').text = 'notes'
            ET.SubElement(display, 'text').text = 'Notes'
    return ET.tostring(root, encoding='unicode')


def add_resource(manifest, values):
    """Select existing data or create a typed native configuration/script."""
    root = _manifest_xml(manifest).get_root_node()
    kind = values.get('kind')
    name = str(values.get('name') or '').strip()
    if kind not in KINDS or not re.fullmatch(r'[A-Za-z_][\w.-]{0,127}', name):
        raise TacticException('Choose a resource type and a name using letters, digits, dots and underscores')
    if kind == 'data':
        search_type = str(values.get('searchType') or '')
        target = SearchType.get(search_type)
        base = target.get_base_key()
        if (base.startswith(('sthpw/', 'config/')) or target.get_database() != Project.get_project_code()
                or SearchType.breakup_search_type(search_type).get('project') not in (None, '', Project.get_project_code())):
            raise TacticException('Choose a business Search Type in the selected project')
        if values.get('schema'):
            if not any(node.tag == 'search_type' and node.get('code') == base for node in root):
                ET.SubElement(root, 'search_type', code=base)
        attributes = dict(search_type=base, path='data/' + name + '.spt')
        if values.get('code'):
            attributes['code'] = str(values['code'])
        # An empty code explicitly means all records of this selected type.
        ET.SubElement(root, 'sobject', **attributes)
        return ET.tostring(root, encoding='unicode'), ''
    base = 'config/custom_script' if kind == 'python' else 'config/widget_config'
    if kind == 'python':
        search = Search(base)
        search.add_filter('folder', 'plugins/' + root.findtext('data/code', ''))
        search.add_filter('title', name)
    else:
        search = Search(base)
        search.add_filter('view', name)
    if search.get_sobject() is not None:
        raise TacticException('A resource with this name already exists')
    row = SearchType.create(base)
    if kind == 'python':
        row.set_value('folder', 'plugins/' + root.findtext('data/code', ''))
        row.set_value('title', name)
        row.set_value('language', 'python')
        row.set_value('script', "# Trusted server Python; use native server APIs.\nreturn {'input': kwargs.get('input', {})}\n")
    else:
        row.set_value('view', name)
        row.set_value('search_type', 'ALL')
        row.set_value('widget_type', kind)
        row.set_value('category', 'PluginTheme' if kind == 'theme' else 'CustomLayoutWdg')
        row.set_value('config', scaffold(kind, name))
    row.commit()
    ET.SubElement(root, 'sobject', search_type=base, code=row.get_code(),
                  path='config/' + name + '.spt')
    return ET.tostring(root, encoding='unicode'), row.get_search_key()
