"""Read a configured child table with its own query and selection scope."""


def nested_cell(search_key, options, column='', layout_reader=None):
    from pyasm.search import Search

    allowed = {
        'dynamic_class', 'dynamic', 'search_type', 'view', 'expression',
        'icon', 'title_icon', 'icon_tip', 'label', 'mode', 'init_load_num',
        'show_search_limit', 'show_insert', 'show_row_select', 'show_select',
        'show_gear', 'show_search', 'show_shelf', 'show_resize_scroll', 'related_types', 'include_mako', 'html',
    }
    if set(options) - allowed:
        raise ValueError('Unsupported nested table options: ' + ', '.join(sorted(set(options) - allowed)))
    for flag in ('show_search_limit', 'show_insert', 'show_row_select', 'show_select',
                 'show_gear', 'show_search', 'show_shelf', 'show_resize_scroll'):
        if options.get(flag, '') not in ('', True, False, 'true', 'false'):
            raise ValueError('Invalid nested table display option: ' + flag)
    # Nested column authoring opens the scoped Columns editor when show_gear is enabled.
    if False:
        raise ValueError('Nested column authoring is not available yet')
    if options.get('init_load_num') not in (None, '', 'null'):
        if str(options['init_load_num']) != '-1' and not str(options['init_load_num']).isdecimal():
            raise ValueError('Invalid initial row rendering limit')
    handler = options.get('dynamic_class') or options.get('dynamic') or 'tactic.ui.panel.TableLayoutWdg'
    if handler == 'tactic.ui.widget.SObjectCheckinHistoryWdg':
        options = dict(options, search_type='sthpw/snapshot', view='checkin_history', show_insert=False)
        handler = 'tactic.ui.panel.TableLayoutWdg'
    if handler == 'tactic.ui.checkin.SnapshotFilesWdg':
        options = dict(options, search_type='sthpw/file', view='snapshot_files',
                       show_insert=False, show_select=False, show_gear=False)
        handler = 'tactic.ui.panel.TableLayoutWdg'
    if handler in ('tactic.ui.table.CustomLayoutElementWdg', 'tactic.ui.panel.CustomLayoutWdg'):
        if layout_reader is None:
            from tactic.ui.table.custom_layout_element_wdg import read_custom_layout
            layout_reader = read_custom_layout
        layout = layout_reader(search_key, view=options.get('view') or '', html=options.get('html') or '',
                               include_mako=options.get('include_mako', True))
        nodes = layout['layoutNodes']
        if len(nodes) == 1 and nodes[0]['kind'] == 'table':
            return dict(text='', targetSearchKey=search_key, columnName=column,
                nestedTable=nodes[0]['table'], actions=[dict(name='nested-table', label='Show related table', icon='chevron-right')])
        if nodes:
            return dict(layout, columnName=column)
        raise ValueError('A hidden CustomLayout must contain one migrated table')
    if handler not in ('tactic.ui.panel.TableLayoutWdg', 'tactic.ui.panel.FastTableLayoutWdg',
                       'tactic.ui.panel.ViewPanelWdg'):
        raise ValueError('Nested widget is not a migrated table: ' + str(handler))
    obj = Search.get_by_search_key(search_key)
    if obj is None:
        raise LookupError('Object is no longer available')
    view = options.get('view') or 'table'
    label = Search.eval(options['label'], sobjects=obj, single=True) if options.get('label') else ''
    return dict(text=str(label or ''), targetSearchKey=search_key, columnName=column,
                nestedTable=dict(searchType=options.get('search_type') or obj.get_base_search_type(),
                    view=view, parentKey=search_key,
                    selection=options.get('show_row_select', options.get('show_select')) not in (False, 'false'),
                    insert=options.get('show_insert') not in (False, 'false'),
                    shelf=options.get('show_shelf') not in (False, 'false'),
                    gear=options.get('show_gear') not in (False, 'false'),
                    search=options.get('show_search') not in (False, 'false'),
                    searchLimit=options.get('show_search_limit') not in (False, 'false'),
                    expression=options.get('expression') or ''),
                actions=[dict(name='nested-table', label='Show related table', icon='chevron-right')])


def read_nested_scope(parent_key, search_type, view='table', expression='', offset=0,
                      limit=50, filters=None, order_by=None):
    """Self-contained original-server procedure; never return an unscoped table."""
    import re
    from pyasm.biz import Project, Snapshot
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey, SearchType

    if not Environment.get_security().is_admin() and (not Environment.get_security().is_logged_in() or Environment.get_security().get_user_name() == 'admin' or not (Project.get_project_code() in ('admin', 'sthpw') or Environment.get_security().check_access('project', [{'code': '*'}, {'code': Project.get_project_code()}], 'allow', default='deny'))):
        raise PermissionError('Administration requires administrator access')
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Invalid nested table page')
    if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view):
        raise ValueError('Invalid view name')
    if SearchKey.extract_project(parent_key) not in (None, '', Project.get_project_code(), 'sthpw', 'admin'):
        raise ValueError('The configured table target belongs to another project')
    requested = SearchType.breakup_search_type(search_type)
    if requested.get('project') not in (None, '', Project.get_project_code(), 'sthpw', 'admin'):
        raise ValueError('The nested table belongs to another project')
    base = SearchType.get(search_type).get_base_key()
    if base in ('sthpw/message', 'sthpw/message_log'):
        raise ValueError('Open private messages from Messages')
    if base.startswith(('prod/', 'flash/')):
        raise ValueError('The legacy production subsystem is excluded')
    parent = Search.get_by_search_key(parent_key)
    if parent is None:
        raise LookupError('Object is no longer available')
    if parent.get_base_search_type() in ('sthpw/message', 'sthpw/message_log'):
        raise ValueError('Open private messages from Messages')
    search = Search(search_type)
    if base == 'sthpw/file' and view == 'snapshot_files' and not expression:
        # shortcut: directory packages remain file records; recursive disk browsing stays in File Workspace.
        snapshots = [parent] if parent.get_base_search_type() == 'sthpw/snapshot' else Snapshot.get_by_sobject(parent, 'publish')
        files = [file for snapshot in snapshots for file in snapshot.get_all_file_objects()]
        search.add_filters('id', [file.get_id() for file in files] or [-1])
    elif parent.get_base_search_type() == 'sthpw/project' and base in (
            'sthpw/task', 'sthpw/snapshot', 'sthpw/note', 'sthpw/work_hour') and not expression:
        search.add_filter('project_code', parent.get_code())
    elif base == parent.get_base_search_type() and not expression:
        search.add_id_filter(parent.get_id())
    elif expression:
        # Only reads enter a nested table. Mutating expressions belong to actions.
        if not isinstance(expression, str) or not re.fullmatch(r'\s*@SOBJECT\([^@;{}]*\)\s*', expression, re.I):
            raise ValueError('A nested table requires an @SOBJECT expression')
        records = Search.eval(expression, sobjects=parent)
        if not isinstance(records, (list, tuple)):
            records = [records] if records else []
        if len(records) > 10000 or any(item.get_base_search_type() != base for item in records):
            raise ValueError('The nested expression returned an invalid scope')
        search.add_filters('id', [item.get_id() for item in records] or [-1])
    else:
        owner = parent.get_parent()
        if owner is not None and owner.get_base_search_type() == base:
            search.add_id_filter(owner.get_id())
        else:
            search.add_parent_filter(parent)
    columns = SearchType.get_column_info(base)
    if not isinstance(filters or [], list) or len(filters or []) > 20:
        raise ValueError('Invalid nested table filters')
    for item in filters or []:
        if not isinstance(item, (tuple, list)) or len(item) != 3 or item[0] not in columns or item[1] not in ('=', '!=', '<', '<=', '>', '>=', 'like'):
            raise ValueError('Invalid nested table filter')
        search.add_filter(item[0], item[2], op=item[1])
    if not isinstance(order_by or [], list) or len(order_by or []) > 4:
        raise ValueError('Invalid nested table ordering')
    for item in order_by or []:
        parts = str(item).split()
        if not parts or len(parts) > 2 or parts[0] not in columns or (len(parts) == 2 and parts[1].lower() not in ('asc', 'desc')):
            raise ValueError('Invalid nested table ordering')
        search.add_order_by(parts[0], parts[1] if len(parts) == 2 else 'asc')
    search.add_order_by('id')
    search.set_limit(limit + 1)
    search.set_offset(offset)
    records = search.get_sobjects()
    values = [item.get_sobject_dict() for item in records[:limit]]
    if base == 'sthpw/login':
        for record in values:
            record.pop('password', None)
    return dict(searchType=base, view=view, parentKey=parent_key, offset=offset,
                hasNext=len(records) > limit,
                records=values)
