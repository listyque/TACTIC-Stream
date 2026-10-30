"""Saved table views: native commands, revision checks and project-owned XML."""
from copy import deepcopy
import re
import unicodedata
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from pyasm.widget import WidgetConfigView
from tactic_stream.server.columns_editor import _records, _revision
from tactic_stream.server.widget_configuration import WidgetConfigConflict

SERVICE_VIEWS = {'definition', 'default_definition', 'edit_definition', 'edit',
                 'insert', 'search', 'filter', 'custom_filter', 'simple_filter'}
TABLE_LAYOUTS = {'', 'TableLayoutWdg', 'tactic.ui.panel.TableLayoutWdg'}


def table_node(xml, view):
    if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view) or view in SERVICE_VIEWS:
        return None
    try:
        root = ET.fromstring(xml)
    except (ET.ParseError, TypeError):
        return None
    node = next((node for node in root.iter()
                 if node.tag == view or node.tag == 'view' and node.get('name') == view), None)
    if node is None or node.get('layout', '') not in TABLE_LAYOUTS:
        return None
    return node if view == 'table' or node.find('element') is not None or node.get('layout') else None


def catalog(search_type, current='table'):
    _require_admin()
    base = SearchType.get(search_type).get_base_key()
    records = _records()
    candidates = [row for row in records if row.get('search_type') == base
                  and not row.get('login') and table_node(row.get('config'), row.get('view', '')) is not None]
    groups = {}
    for row in candidates:
        groups.setdefault(row['view'], []).append(row)
    views = [dict(view='table', title='Default table', columns=0,
                  sources=0, protected=True)]
    login = Environment.get_security().get_user_name()
    defaults = [row for row in records if row.get('search_type') == base and row.get('view') == 'table'
                and (not row.get('login') or row.get('login') == login)
                and table_node(row.get('config'), 'table') is not None]
    if defaults:
        default = max(defaults, key=lambda row: (row.get('login') == login, row.get('priority') or 0, row['id']))
        views[0].update(columns=len(table_node(default['config'], 'table').findall('element')), sources=len(defaults))
    for view, sources in groups.items():
        source = max(sources, key=lambda row: (row.get('priority') or 0, row['id']))
        root = ET.fromstring(source['config'])
        entry = dict(view=view, title=root.get('th_table_view_title') or view,
                     columns=len(table_node(source['config'], view).findall('element')),
                     sources=len(sources), protected=view == 'table')
        if view == 'table':
            continue
        else:
            views.append(entry)
    views.sort(key=lambda row: (row['view'] != 'table', row['title'].casefold()))
    return dict(project=Project.get_project_code(), searchType=base, current=current,
                projectTitle=Project.get().get_value('title', no_exception=True) or Project.get_project_code(),
                searchTitle=SearchType.get(base).get_value('title', no_exception=True) or base,
                views=views, revision=_revision(records))


class TableViewsCmd(Command):
    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'read')
        search_type = self.kwargs.get('search_type')
        current = self.kwargs.get('current', 'table')
        if action not in ('read', 'create', 'copy', 'rename', 'delete'):
            raise ValueError('Invalid table view operation')
        data = SearchType.breakup_search_type(search_type)
        if data.get('project') and data['project'] != Project.get_project_code():
            raise ValueError('Select the target project before managing its views')
        if action == 'read':
            self.info = catalog(search_type, current)
            return self.info
        search = Search('config/widget_config')
        sql = search.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        state = catalog(search_type, current)
        if self.kwargs.get('revision') != state['revision']:
            raise WidgetConfigConflict('Table views changed. Reload before saving.')
        view = self.kwargs.get('view', '')
        selected = next((row for row in state['views'] if row['view'] == view), None)
        if action != 'create' and selected is None:
            raise ValueError('Choose an existing table view')
        if action in ('rename', 'delete') and selected['protected']:
            raise ValueError('The default table is protected. Create a copy instead.')
        title = unicodedata.normalize('NFKC', str(self.kwargs.get('title') or '')).strip()
        if action != 'delete' and (not title or len(title) > 120):
            raise ValueError('Enter a view name of up to 120 characters')
        if action != 'delete' and any(row['title'].casefold() == title.casefold()
                                     and (action != 'rename' or row['view'] != view)
                                     for row in state['views']):
            raise ValueError('A table view with this name already exists.')
        if action in ('create', 'copy'):
            slug = re.sub(r'[^\w]+', '_', title, flags=re.UNICODE).strip('_').casefold()[:55]
            if not slug:
                raise ValueError('Table view name requires letters or numbers.')
            target = 'th_table_' + slug
            used = {row.get('view') for row in _records() if row.get('search_type') == state['searchType']}
            suffix = 2
            while target in used:
                target = 'th_table_' + slug + '_' + str(suffix)
                suffix += 1
            root = ET.Element('config', th_table_view_title=title)
            node = ET.SubElement(root, target)
            if action == 'copy':
                resolved = WidgetConfigView.get_by_search_type(state['searchType'], view, use_cache=False)
                node.attrib.update(resolved.get_view_attributes())
                for config in resolved.get_configs():
                    source = table_node(config.get_xml().to_string(), view)
                    if source is not None:
                        for child in source:
                            if child.tag != 'element':
                                node.append(deepcopy(child))
                        break
                for name in resolved.get_element_names():
                    xml = resolved.get_element_xml(name)
                    if xml:
                        node.append(ET.fromstring(xml))
            else:
                ET.SubElement(node, 'element', name='code')
            item = SearchType.create('config/widget_config')
            item.set_value('search_type', state['searchType'])
            item.set_value('view', target)
            item.set_value('config', ET.tostring(root, encoding='unicode'))
            item.commit()
            view = target
        else:
            sources = Search('config/widget_config')
            sources.add_filter('search_type', state['searchType'])
            sources.add_filter('view', view)
            for item in sources.get_sobjects():
                if item.get_value('login', no_exception=True):
                    raise ValueError('This view has personal overrides. Manage them in the definition editor first.')
                if action == 'delete':
                    item.delete()
                else:
                    root = ET.fromstring(item.get_value('config'), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
                    root.set('th_table_view_title', title)
                    item.set_value('config', ET.tostring(root, encoding='unicode'))
                    item.commit()
            if action == 'delete' and current == view:
                current = 'table'
        self.add_description('%s table view [%s] [%s]' % (action, state['searchType'], view))
        # The outer API transaction publishes journal entries after execute returns.
        self.info = dict(current=current, selected='table' if action == 'delete' else view)
        return self.info
