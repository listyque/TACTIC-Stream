"""Native XML authoring over original WidgetDbConfig, Command and journal."""
import difflib
import hashlib
import json
import re
from xml.etree import ElementTree

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import TacticException, Container
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.security.security import _require_admin
from pyasm.widget import WidgetConfigView
from tactic_stream.server.interface import describe_view, read_interface
from tactic_stream.server.item_layout import LAYOUT, EXAMPLE_VIEWS, describe_item_layout, layout_templates, layout_view_names


class WidgetConfigConflict(TacticException):
    pass


def read_layout_catalog() -> dict:
    _require_admin()
    project = Project.get()
    system = Project.get_project_code() in ('admin', 'sthpw')
    types = project.get_search_types(include_multi_project=True,
                                    include_sthpw=system, include_config=system)
    rows = []
    for item in types:
        if system and not project.has_table(item):
            continue
        options = item.get_record_read_options()
        if options.get('available') is not False:
            rows.append(dict(code=item.get_code(), title=item.get_value('title'),
                             __record_read__=options))
    return dict(stypes=sorted(rows, key=lambda row: (row['title'] or row['code']).lower()))


def read_widget_configuration(search_type, view='table'):
    _require_admin()
    if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
        raise ValueError('Invalid view name')
    data = SearchType.breakup_search_type(search_type)
    if data.get('project') and data['project'] != Project.get_project_code():
        raise ValueError('Select the target project before reading its configuration')
    base = 'SideBarWdg' if search_type == 'SideBarWdg' else SearchType.get(search_type).get_base_key()
    search = Search('config/widget_config')
    search.add_filters('search_type', [base, 'ALL'])
    search.add_order_by('id')
    records = search.get_sobjects()
    raw = [item.get_data() for item in records]
    if base == 'SideBarWdg':
        from tactic.core.sidebar_config import SidebarConfig
        resolved = SidebarConfig.get_config(base, view, personal=True)
    else:
        resolved = WidgetConfigView.get_by_search_type(base, view, use_cache=False)
    layers = [dict(view=item.get_view(), xml=item.get_xml().to_string()) for item in resolved.get_configs()]
    # Original journal changes for every native/XML-RPC commit, including A -> B -> A.
    changes = Search('sthpw/sobject_log')
    # Native API update logs retain an explicit project, even for the admin alias.
    changes.add_filters('search_type', list(dict.fromkeys([search.get_search_type(), Project.get_full_search_type('config/widget_config'),
        'config/widget_config?project=' + Project.get_project_code()])))
    changes.add_order_by('id desc')
    changes.add_limit(1)
    latest = changes.get_sobject()
    revision = hashlib.sha256(json.dumps([Project.get_project_code(), base, view, raw, layers,
        latest.get_id() if latest else None], sort_keys=True, default=str).encode('utf-8')).hexdigest()
    sources = [dict(id=item.get_id(), xml=item.get_value('config'), priority=item.get_value('priority', no_exception=True))
               for item in records if item.get_value('search_type') == base and item.get_value('view') == view]
    sources.sort(key=lambda item: (item['priority'] is not None, item['priority'] or 0, item['id']), reverse=True)
    table_views = {view: dict(view=view, title=view, current=True), 'table': dict(view='table', title='table', current=view == 'table')}
    for item in records:
        if item.get_value('search_type') != base:
            continue
        name = item.get_value('view')
        try:
            root = ElementTree.fromstring(item.get_value('config'))
        except (ElementTree.ParseError, TypeError):
            continue
        node = None
        if isinstance(name, str) and re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', name):
            node = root if root.tag == name or root.tag == 'view' and root.get('name') == name else next(
                (child for child in root if child.tag == name or child.tag == 'view' and child.get('name') == name), None)
        if node is not None and (name == 'table' or name.startswith('th_table_') or node.get('layout') in ('TableLayoutWdg', 'tactic.ui.panel.TableLayoutWdg') or node.find('element') is not None):
            table_views[name] = dict(view=name, title=root.get('th_table_view_title') or name, current=name == view)
    return dict(schema_version=1, project=Project.get_project_code(), search_type=base, view=view,
                table_views=sorted(table_views.values(), key=lambda row: (row['view'] != 'table', row['title'].casefold())),
                views=list(dict.fromkeys(([view, 'tactic_handler', 'project_view', 'definition'] if base == 'SideBarWdg' else [view, *EXAMPLE_VIEWS, 'table', 'edit', 'insert', 'definition', 'edit_definition']) +
                    [item.get_value('view') for item in records if isinstance(item.get_value('view'), str)
                     and re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', item.get_value('view'))])),
                layout_views=[] if base == 'SideBarWdg' else layout_view_names(base, records),
                revision=revision, sources=sources, layers=layers, resolved=describe_view(resolved),
                layout_templates=layout_templates())


def check_widget_configuration(search_type, view, source_id, xml, revision):
    current = read_widget_configuration(search_type, view)
    if not isinstance(revision, str) or revision != current['revision']:
        raise WidgetConfigConflict('Interface configuration changed. Reload before saving.')
    if source_id is not None and (type(source_id) is not int or source_id not in [item['id'] for item in current['sources']]):
        raise ValueError('Configuration source does not belong to this view')
    if not isinstance(xml, str) or not xml.strip() or len(xml.encode('utf-8')) > 512 * 1024:
        raise ValueError('Invalid configuration XML')
    candidate = SearchType.create('config/widget_config')
    candidate.set_value('search_type', current['search_type'])
    candidate.set_value('view', view)
    candidate.set_value('config', xml)
    candidate.validate()
    before = next((item['xml'] for item in current['sources'] if item['id'] == source_id), '')
    diff = '\n'.join(difflib.unified_diff(before.splitlines(), xml.splitlines(), fromfile='stored.xml', tofile='draft.xml', lineterm=''))
    checked = dict(valid=True, revision=current['revision'], diff=diff)
    from pyasm.widget import WidgetConfig
    draft = WidgetConfig.get(view=view, xml=xml, use_cache=False)
    if not draft.has_view():
        raise ValueError('Configuration does not contain its view')
    if draft.get_view_attributes().get('layout') == LAYOUT:
        describe_item_layout(describe_view(WidgetConfigView(search_type, view, [draft])))
    if current['search_type'] == 'SideBarWdg' or draft.get_view_attributes().get('layout') == LAYOUT or current['resolved']['layout'] == LAYOUT:
        # Check the entire resolved tree before publishing any sidebar XML.
        checked['interface'] = _preview_interface(current['search_type'], view, source_id, xml)
    return checked


def save_widget_configuration(search_type, view, source_id, xml, revision):
    _require_admin()
    command = Command()
    def save():
        search = Search('config/widget_config')
        sql = search.get_sql()
        # ponytail: table-wide lock; use row locks if config editing throughput requires it.
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        check_widget_configuration(search_type, view, source_id, xml, revision)
        if source_id is None:
            item = SearchType.create('config/widget_config')
            item.set_value('search_type', 'SideBarWdg' if search_type == 'SideBarWdg' else SearchType.get(search_type).get_base_key())
            item.set_value('view', view)
        else:
            target = Search('config/widget_config')
            target.add_filter('id', source_id)
            item = target.get_sobject()
        item.set_value('config', xml)
        item.commit()
        command.add_description('Save widget config [%s] view [%s]' % (search_type, view))
    command.execute = save
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return read_widget_configuration(search_type, view)


def preview_widget_configuration(search_type, view, source_id, xml, revision):
    checked = check_widget_configuration(search_type, view, source_id, xml, revision)
    if 'interface' not in checked:
        checked['interface'] = _preview_interface(search_type, view, source_id, xml)
    return checked


def _preview_interface(search_type, view, source_id, xml):
    base = 'SideBarWdg' if search_type == 'SideBarWdg' else SearchType.get(search_type).get_base_key()
    search = Search('config/widget_config')
    search.add_filter('search_type', base)
    search.add_filter('view', view)
    search.add_order_by('priority desc')
    records = []
    for item in search.get_sobjects():
        data = item.get_data().copy()
        if item.get_id() == source_id:
            data['config'] = xml
        records.append(SearchType.create('config/widget_config', list(data), tuple(data.values())))
    if source_id is None:
        candidate = SearchType.create('config/widget_config')
        candidate.set_value('search_type', base)
        candidate.set_value('view', view)
        candidate.set_value('config', xml)
        candidate.validate()
        records.append(candidate)
    key = 'WidgetDbConfig:preview'
    previous = Container.get(key)
    cache_key = 'WidgetConfigView:config_cache'
    cache = Container.get(cache_key)
    try:
        Container.put(key, {(search.get_db_resource().get_key(), base, view): records})
        Container.put(cache_key, {})
        if base == 'SideBarWdg':
            from tactic_stream.server.navigation import read_navigation
            interface = dict(navigation=read_navigation())
        else:
            interface = read_interface(base, view)
    finally:
        if previous is None:
            Container.remove(key)
        else:
            Container.put(key, previous)
        if cache is None:
            Container.remove(cache_key)
        else:
            Container.put(cache_key, cache)
    return interface
