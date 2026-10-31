"""Native dashboard composition; runs on the server during plugin activation only."""
from uuid import uuid4
from xml.etree import ElementTree as ET

from pyasm.biz import Project, Schema
from pyasm.search import Search, SearchType
from tactic.ui.panel.dashboard_cmd import DashboardCmd, dashboard_state
from tactic_stream.server.sidebar_editor import SidebarDraft, read_sidebar, save_sidebar


NAMES = ('workspace_pulse', 'workspace_vfx')
TABLE_VIEW = 'workspace_pulse_table'
PANEL = dict(fill='surfaceContainerLowest', stroke_width=0, radius=8, shadow=True)
VFX_TABLES = ('episode', 'episodes', 'sequence', 'sequences', 'scenes', 'shot', 'shots', 'asset', 'assets')


def panel(title, children, **values):
    return dict(kind='column', title=title, children=children, padding=[16]*4,
                gap=12, appearance=PANEL, **values)


def metric(title, search_type, filters, icon=''):
    return dict(kind='metric', title=title, search_type=search_type,
                filters=filters, icon=icon, appearance=PANEL, height=104)


def overview(project):
    """An editable overview backed by scoped native task aggregates and tables."""
    scope = [dict(column='project_code', relation='=', value=project)]
    task = dict(search_type='sthpw/task', filters=scope)
    due = dict(column='bid_end_date', relation='!=', value=None)
    def card(children, **values):
        return dict(kind='column', children=children, padding=[20]*4, gap=12,
                    appearance=PANEL, **values)
    return dict(name='workspace_overview', title='Project overview', filters=[
        dict(name=name, title=title, search_type='sthpw/task', column=column,
             value='', enabled=False)
        for name, title, column in [('status', 'Status', 'status'),
                                    ('assigned', 'Assignee', 'assigned'),
                                    ('process', 'Process', 'process')]
    ], blocks=[
        dict(kind='grid', region='header', columns=4, min_cell_width=220,
             row_height=104, gap=16, margin=[16,0,8,0], children=[
            metric('Total tasks', 'sthpw/task', scope, 'clipboard-check'),
            metric('Scheduled', 'sthpw/task', scope + [due], 'calendar'),
            metric('Without a due date', 'sthpw/task', scope + [dict(column='bid_end_date', relation='=', value=None)], 'clock'),
            metric('Assigned', 'sthpw/task', scope + [dict(column='assigned', relation='like', value='_%')], 'person')]),
        dict(kind='column', padding=[16,0,24,0], gap=20, children=[
            dict(kind='row', gap=20, collapse_width=880, children=[
                card([dict(kind='chart', title='Delivery schedule', search_type='sthpw/task',
                    filters=scope + [due], chart_type='line', height=264,
                    group_by=[dict(column='bid_end_date', period='day', title='Due date')],
                    group_limit=25)], weight=2),
                card([dict(kind='chart', title='Tasks by status', **task, chart_type='donut',
                    height=264, group_by=[dict(column='status', title='Status')],
                    group_order='value_desc', group_limit=10)], weight=2)]),
            dict(kind='row', gap=20, collapse_width=880, children=[
                card([dict(kind='table', title='Task queue', **task, view=TABLE_VIEW,
                    height=344, controls=['shelf', 'search', 'searchLimit'])], weight=3),
                card([dict(kind='chart', title='Workload by assignee', **task, chart_type='bar',
                    height=344, group_by=[dict(column='assigned', title='Assignee')],
                    group_order='value_desc', group_limit=10)], weight=2)])])])


def documents(project, types):
    """Project code and type identities come from native discovery, never a fixture."""
    scope = [dict(column='project_code', relation='=', value=project)]
    pulse = overview(project)
    pulse.update(name=NAMES[0], title='Pulse')

    # Native templates keep their own namespaces; inspect existing table names only.
    vfx_types = [row for row in types if row['table'] in VFX_TABLES]
    vfx = dict(name=NAMES[1], title='VFX overview', blocks=[])
    if vfx_types:
        vfx['blocks'].append(dict(kind='row', region='header', children=[
            metric(row['title'], row['code'], []) for row in vfx_types]))
        for index in range(0, len(vfx_types), 2):
            vfx['blocks'].append(dict(kind='row', children=[
                panel(row['title'], [dict(kind='table', title=row['title'], search_type=row['code'],
                    view=TABLE_VIEW, height=340, controls=['shelf', 'search', 'searchLimit'])])
                for row in vfx_types[index:index+2]]))
    else:
        vfx['blocks'] = [panel('VFX overview', [dict(kind='text', text=
            'This project has no episode, sequence, shot or asset tables. '
            'Pulse remains available for its native tasks. '
            'After adding VFX types, reload this plugin to discover them.')])]
    return pulse, vfx


def table_config(search_type, fields):
    root = ET.Element('config')
    view = ET.SubElement(root, TABLE_VIEW)
    widths = dict(name=200, description=280, process=120, status=140, assigned=160, bid_end_date=140, code=180)
    if search_type == 'sthpw/task':
        widths.update(description=200, process=72, status=96, assigned=100, bid_end_date=100)
    for column, title in fields:
        element = ET.SubElement(view, 'element', name=column, title=title, width=str(widths[column]))
        if search_type == 'sthpw/task' and column == 'assigned':
            display = ET.SubElement(element, 'display', {'class': 'tactic.ui.table.ExpressionElementWdg'})
            ET.SubElement(display, 'expression').text = '@GET(.assigned)'
        elif search_type == 'sthpw/task' and column == 'bid_end_date':
            display = ET.SubElement(element, 'display', {'class': 'tactic.ui.table.FormatElementWdg'})
            ET.SubElement(display, 'type').text = 'date'
            ET.SubElement(display, 'format').text = '1999-12-31'
    ET.indent(root, space='  ')
    row = SearchType.create('config/widget_config')
    for key, value in dict(search_type=search_type, view=TABLE_VIEW,
                           config=ET.tostring(root, encoding='unicode')).items():
        row.set_value(key, value)
    row.commit()


def navigation():
    state = read_sidebar()
    groups = [row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
    source = 'handler' if dashboard_state()['navigation']['view'] == 'tactic_handler' else 'tactic'
    return state, SidebarDraft(state['documents'], groups, Project.get_project_code(), source)


def install():
    project = Project.get()
    if project.get_code() in ('admin', 'sthpw'):
        raise ValueError('Activate Workspace Pulse in a business project')
    query = Search('config/widget_config')
    if any(row.get_value('view') in [TABLE_VIEW, *('dashboard.' + name for name in NAMES)]
           for row in query.get_sobjects()):
        raise ValueError('Workspace Pulse views already exist; inspect them before activation')
    schema_types = set(Schema.get().get_search_types())
    types = [dict(code=row.get_code(), title=row.get_title(), table=row.get_table())
             for row in project.get_search_types(include_multi_project=True)
             if row.get_database() == project.get_code() and row.get_code() in schema_types]
    task_fields = [('description', 'Task'), ('process', 'Process'), ('status', 'Status'),
                   ('assigned', 'Assignee'), ('bid_end_date', 'Due')]
    table_config('sthpw/task', task_fields)
    for row in types:
        if row['table'] not in VFX_TABLES:
            continue
        columns = SearchType.get_column_info(row['code'])
        fields = [(key, title) for key, title in [('name', 'Name'), ('description', 'Description')]
                  if key in columns]
        table_config(row['code'], fields or [('code', 'Code')])
    for document in documents(project.get_code(), types):
        DashboardCmd(action='apply', project_code=project.get_code(), document=document,
                     expected_revision=dashboard_state()['revision'], operation_id=str(uuid4())).execute()
    state, draft = navigation()
    for name, icon in zip(NAMES, ('chart-bar', 'film')):
        draft._selected_row = next(i for i, row in enumerate(draft.entries)
                                   if row['name'] == 'dashboard_' + name)
        draft.update_selected('icon', icon)
        for root in draft._documents.values():
            for element in root.iter('element'):
                if element.get('name') == 'dashboard_' + name:
                    element.set('icon', 'FAS_' + icon.replace('-', '_').upper())
    save_sidebar(draft, state['revision'])


def remove_navigation():
    state, draft = navigation()
    names = {'dashboard_' + name for name in NAMES}
    # Remove definitions as well as references, so native Reload can reuse the names.
    for root in draft._documents.values():
        for parent in root.iter():
            for child in list(parent):
                if child.tag == 'element' and child.get('name') in names:
                    parent.remove(child)
    draft._rebuild_entries()
    save_sidebar(draft, state['revision'])
