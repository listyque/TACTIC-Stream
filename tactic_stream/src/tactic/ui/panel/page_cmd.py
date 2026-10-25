"""Create a native search page through the existing search, view and sidebar editors."""
import hashlib
import json
import re
from uuid import UUID
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.navigation import read_navigation
from tactic_stream.server.search_configuration import (
    read_search_configuration, search_configuration_request, generated_quick_records, validate_filters)
from tactic_stream.server.sidebar_editor import SidebarDraft, read_sidebar, save_sidebar
from tactic_stream.server.widget_configuration import (
    read_widget_configuration, preview_widget_configuration, save_widget_configuration, WidgetConfigConflict)
from tactic_stream.server.workspace_layout import read_layouts, validate_layout, workspace_layout_request


WIDGETS = {'preview': 'ThumbWdg', 'tasks': 'tactic.ui.table.TaskElementWdg',
           'notes': 'tactic.ui.widget.DiscussionElementWdg'}
PANELS = ('results', 'advanced_search', 'task_calendar', 'tasks', 'notes', 'timesheet',
          'work_reports', 'cost_reports', 'commit_queue', 'description', 'snapshot', 'knowledge', 'drop_plate')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str, allow_nan=False).encode()).hexdigest()


def page_state(search_type):
    if not isinstance(search_type, str) or '?' in search_type:
        raise ValueError('Select a base Search Type in the current project')
    Search(search_type)  # Native type/project routing and access checks.
    sql = Search('config/widget_config').get_sql()
    if not sql.table_exists('spt_widget_config_revision'):
        raise ValueError('Upgrade the project schema before creating pages')
    configuration = Search('config/widget_config')
    configuration.add_order_by('id')
    sidebar = read_sidebar()
    table = read_widget_configuration(search_type, 'table')
    revision = digest([Project.get_project_code(), search_type,
                       sql.get_value("SELECT revision FROM spt_widget_config_revision WHERE code='collection'"),
                       [row.get_data() for row in configuration.get_sobjects()], sidebar['revision'],
                       table['revision'], SearchType.get_column_info(search_type)])
    return dict(revision=revision, search=read_search_configuration(search_type, include_groups=False),
                table=table, sidebar=sidebar, navigation=read_navigation(), workspace=read_layouts(),
                widgets=WIDGETS, workspace_panels=PANELS)


def prepare_page(search_type, document, state):
    allowed = {'name', 'title', 'columns', 'records', 'task_filters', 'order_bys', 'workspace_layout'}
    if not isinstance(document, dict) or set(document) - allowed:
        raise ValueError('Invalid page document')
    name, title = document.get('name'), document.get('title')
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', name):
        raise ValueError('Page name must be a lowercase identifier of at most 48 characters')
    if not isinstance(title, str) or not title.strip() or len(title) > 256:
        raise ValueError('Enter a page title')
    view, scope = 'page_' + name, search_type + '@' + name
    current = read_widget_configuration(search_type, view)
    if current['sources'] or current['resolved']['configured']:
        raise ValueError('The page view already exists; edit it in the native editor')
    if any(row['view'].endswith(':' + scope) for row in state['search']['presets']):
        raise ValueError('Searches already exist in this page namespace')
    columns = document.get('columns')
    if not isinstance(columns, list) or not 1 <= len(columns) <= 64:
        raise ValueError('Select between 1 and 64 table columns')
    root = ET.Element('config')
    table = ET.SubElement(root, view, layout='TableLayoutWdg')
    seen = set()
    for column in columns:
        if not isinstance(column, dict) or set(column) - {'name', 'title', 'width', 'widget'}:
            raise ValueError('Invalid page column')
        field, widget = column.get('name'), column.get('widget', 'field')
        if (not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_]\w{0,63}', field)
                or field in seen or widget not in ('field', *WIDGETS)
                or widget == 'field' and field not in state['search']['columns']):
            raise ValueError('Select a unique native field or supported widget')
        seen.add(field)
        attrs = dict(name=field)
        if 'title' in column:
            if not isinstance(column['title'], str) or len(column['title']) > 256:
                raise ValueError('Invalid column title')
            attrs['title'] = column['title']
        if 'width' in column:
            if type(column['width']) is not int or not 40 <= column['width'] <= 1200:
                raise ValueError('Column width must be between 40 and 1200')
            attrs['width'] = str(column['width'])
        element = ET.SubElement(table, 'element', attrs)
        if widget != 'field':
            ET.SubElement(element, 'display', {'class': WIDGETS[widget]})
    records = document.get('records', [])
    validate_filters(records, state['search']['columns'])
    if any(row['column'] == '_expression' for row in records):
        raise ValueError('Use task_filters for related tasks; arbitrary expressions require the native editor')
    selections = document.get('task_filters', {})
    if not isinstance(selections, dict) or set(selections) - {'assigned', 'process', 'status'}:
        raise ValueError('Invalid related task filters')
    generated = generated_quick_records(selections, state['search']['columns'])
    if '__current_login__' in selections.get('assigned', []) and len(selections['assigned']) != 1:
        raise ValueError('Use current login alone to retain a dynamic assignee filter')
    records = [dict(row) for row in records] + [
        {key: value for key, value in row.items() if key in ('column', 'relation', 'value', 'rowEnabled', 'operator')}
        for row in generated]
    orders = document.get('order_bys', ['code'])
    if not isinstance(orders, list) or len(orders) > 16 or any(not isinstance(order, str) for order in orders):
        raise ValueError('Invalid page ordering')
    for order in orders:
        Search(search_type).add_order_by(order)
    workspace = document.get('workspace_layout')
    if workspace is not None:
        validate_layout(workspace)
        if any(panel['panel_id'] not in PANELS for panel in workspace['panels']):
            raise ValueError('Select a discovered native workspace panel')
        if not next(panel for panel in workspace['panels'] if panel['panel_id'] == 'results')['visible']:
            raise ValueError('A page layout must display results')
        if any(row['title'].casefold() == title.strip().casefold() for row in state['workspace']['presets']):
            raise ValueError('A workspace layout with this title already exists')
    sidebar = state['sidebar']
    source = 'handler' if state['navigation']['view'] == 'tactic_handler' else 'tactic'
    if state['navigation']['configured'] and state['navigation']['view'] not in sidebar['documents']:
        raise ValueError('Materialize inherited navigation in the sidebar editor before adding a page')
    groups = [row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
    draft = SidebarDraft(sidebar['documents'], groups, Project.get_project_code(), source)
    draft.check_name(name, None)
    draft._selected_row = -1  # New pages belong to the root, not the editor's first selected folder.
    draft.add_entry('link')
    for field, value in dict(name=name, title=title.strip(), searchType=search_type,
                             widgetType='view_panel', displayView=view, resultViewMode='table').items():
        draft.update_selected(field, value)
    xml = ET.tostring(root, encoding='unicode')
    preview = preview_widget_configuration(search_type, view, None, xml, current['revision'])
    if any(not element.get('cell', {}).get('supported', True) for element in preview['interface']['table']['elements']):
        raise ValueError('A selected column is unavailable in this interface')
    sample = search_configuration_request('query', dict(search_type=search_type, records=records,
        order_bys=orders, columns=[name for name in seen if name in state['search']['columns']], limit=25, include_total=True))
    return dict(view=view, scope=scope, title=title.strip(), xml=xml, records=records,
                order_bys=orders, interface=preview['interface'], sample=sample,
                workspace_layout=workspace), draft


class PageCmd(Command):
    def execute(self):
        _require_admin()
        action = self.kwargs.get('action')
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Page project does not match the current project')
        if action not in ('read', 'preview', 'apply', 'operation'):
            raise ValueError('Unknown page operation')
        search_type = self.kwargs.get('search_type')
        sql = Search('config/widget_config').get_sql()
        if action == 'apply':
            sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        operation_id = self.kwargs.get('operation_id', '')
        if action in ('apply', 'operation'):
            if not isinstance(operation_id, str) or str(UUID(operation_id)) != operation_id:
                raise ValueError('A canonical UUID operation_id is required')
            key = digest([Environment.get_user_name(), Project.get_project_code(), operation_id])
            receipt = sql.do_query('SELECT request_hash,result FROM spt_page_operation WHERE code=%s' % sql.quote(key))
            fingerprint = digest([search_type, self.kwargs.get('document'), self.kwargs.get('expected_revision')])
            if receipt:
                result = json.loads(receipt[0][1])
                if result['search_type'] != search_type or action == 'apply' and receipt[0][0] != fingerprint:
                    raise ValueError('Operation ID was already used with a different request')
                return result
            if action == 'operation':
                return dict(operation_id=operation_id, status='not_found')
        state = page_state(search_type)
        if action == 'read':
            return state
        if self.kwargs.get('expected_revision') != state['revision']:
            raise WidgetConfigConflict('Page dependencies changed. Reload before saving.')
        prepared, draft = prepare_page(search_type, self.kwargs.get('document'), state)
        if action == 'preview':
            return dict(prepared, revision=state['revision'], sidebar=draft.result(), applied=False)
        view = prepared['view']
        current = read_widget_configuration(search_type, view)
        saved_table = save_widget_configuration(search_type, view, None, prepared['xml'], current['revision'])
        current_search = read_search_configuration(search_type, prepared['scope'], include_groups=False)
        saved_search = search_configuration_request('save', dict(search_type=search_type, scope=prepared['scope'],
            title=prepared['title'], records=prepared['records'], order_bys=prepared['order_bys'], revision=current_search['revision']))
        preset = next(row for row in saved_search['presets'] if row['view'].endswith(':' + prepared['scope']))
        draft.update_selected('searchView', preset['view'])
        layout = None
        if prepared['workspace_layout'] is not None:
            current_layouts = read_layouts()
            saved = workspace_layout_request('save', dict(title=prepared['title'],
                configuration=prepared['workspace_layout'], revision=current_layouts['revision']))
            layout = next(row for row in saved['presets'] if row['title'] == prepared['title'])
            draft.update_selected('layoutPreset', layout['view'])
        save_sidebar(draft, read_sidebar()['revision'])
        result = dict(operation_id=operation_id, status='applied', search_type=search_type,
                      name=self.kwargs['document']['name'], view=view, search=preset,
                      table_source=saved_table['sources'][0]['id'], workspace=layout,
                      navigation=read_navigation(), base_revision=state['revision'])
        parameter = sql.get_database_impl().get_parameter()
        sql._do_update('INSERT INTO spt_page_operation (code,request_hash,result) VALUES (%s)' %
                       ','.join([parameter] * 3), parameters=[key, fingerprint, json.dumps(result)])
        self.add_description('Create search page [%s]' % result['name'])
        return result
