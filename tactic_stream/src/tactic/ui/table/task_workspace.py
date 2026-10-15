"""Handler task workspace scope/page operations on native TACTIC objects.

Source: thlib/ui/task_workspace/store.py and thlib/tactic_query.py (EPL-1.0).
The page algorithm below is copied without its client/Mako transport.
"""
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.api import Api
from tactic.ui.widget.discussion_wdg import discussion_target
from .task_element_wdg import TaskElementWdg


def task_workspace_filters(scope, identity='', search_keys=None, process=''):
    project = Project.get_project_code()
    filters = [('project_code', project)]
    parents = []
    if scope in ('object', 'multiple'):
        keys = [identity] if scope == 'object' and identity else search_keys or []
        if not isinstance(keys, list) or len(keys) > 500:
            raise ValueError('Choose at most 500 task parents')
        for key in dict.fromkeys(keys):
            parent = discussion_target(key)
            if not parent.get_code():
                raise ValueError('The task workspace requires a parent code')
            parents.append(parent)
        if not parents:
            return filters, parents, False
        filters.append('begin')
        for parent in parents:
            filters.extend(['begin', ('search_type', parent.get_search_type()),
                            ('search_code', parent.get_code()), 'and'])
        filters.append('or')
        if scope == 'object' and process:
            filters.append(('process', process))
    elif scope == 'search_type':
        if not identity or SearchType.breakup_search_type(identity).get('project') not in (None, '', project):
            raise ValueError('Choose a Search Type in the current project')
        SearchType.get(identity)
        filters.append(('search_type', SearchType.build_search_type(identity.split('?', 1)[0], project)))
    elif scope == 'user':
        identity = identity or Environment.get_user_name()
        if not Search.get_by_code('sthpw/login', identity):
            raise ValueError('Choose an existing user')
        filters.append(('assigned', identity))
    elif scope == 'team':
        group = Search.get_by_code('sthpw/login_group', identity) if identity else None
        if not group:
            raise ValueError('Choose an existing group')
        members = Search('sthpw/login_in_group'); members.add_filter('login_group', group.get_code())
        logins = sorted({row.get_value('login') for row in members.get_sobjects() if row.get_value('login')})
        if not logins:
            return filters, parents, False
        filters.append(('assigned', 'in', logins))
    elif scope != 'project':
        raise ValueError('Unsupported task workspace scope')
    # Process permissions apply to both rows and scope-wide facets/counts.
    search = Search('sthpw/task'); search.add_op_filters(filters); search.add_column('process', distinct=True)
    allowed = [row.get_value('process') or '' for row in search.get_sobjects()
               if TaskElementWdg.can_view_process(row.get_value('process') or 'publish')]
    if not allowed:
        return filters, parents, False
    filters.append('begin')
    if any(allowed):
        filters.append(('process', 'in', [name for name in allowed if name]))
    if '' in allowed:
        filters.extend(['begin', ('process', 'is', 'NULL'), ('process', ''), 'or'])
    filters.append('or')
    return filters, parents, True


class TaskWorkspaceCmd(Command):
    """Read a bounded task page, its parents and scope-wide filter counts."""
    def check_security(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()
        if self.kwargs.get('action') == 'catalog':
            from .task_workspace_edits import task_field_catalog
            return task_field_catalog(self.kwargs.get('search_key', ''))
        if self.kwargs.get('action') == 'processes':
            return task_process_workspace(self.kwargs.get('search_key', ''))
        if self.kwargs.get('action', 'read') != 'read':
            raise ValueError('Unsupported task workspace operation')
        scope = self.kwargs.get('scope', 'object')
        identity = self.kwargs.get('identity', '')
        limit, offset = self.kwargs.get('limit', 100), self.kwargs.get('offset', 0)
        if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or offset < 0:
            raise ValueError('Task pages require a limit of 1..500 and a non-negative offset')
        query = self.kwargs.get('query') or {}
        if not isinstance(scope, str) or not isinstance(identity, str) or not isinstance(query, dict):
            raise ValueError('Invalid task workspace request')
        if set(query) - {'filters', 'quickFilters', 'sort', 'group', 'descending', 'today', 'scopeProcess'}:
            raise ValueError('Unsupported task workspace query options')
        query = dict(query)
        process = query.get('scopeProcess', '')
        keys = self.kwargs.get('search_keys', [])
        if not isinstance(process, str) or not isinstance(keys, list) or not all(isinstance(key, str) and key for key in keys):
            raise ValueError('Invalid task workspace selection')
        filters, targets, available = task_workspace_filters(scope, identity, keys, process)
        if available:
            query['currentLogin'] = Environment.get_user_name()
            users = Search('sthpw/login')
            labels = [dict(value=user.get_code(), label=user.get_value('display_name') or user.get_code()) for user in users.get_sobjects()]
            query['labels'] = dict(assigned=labels, supervisor=labels)
            result = query_task_workspace_page(filters, [], Project.get_project_code(), limit, offset, query)
        else:
            result = dict(tasks=[], parents=[], total=0, facets={}, offset=offset, limit=limit)
        if targets:
            result['parents'] = Api._get_sobjects_dict(targets)
        task_table_metadata(result)
        result.update(scope=scope, identity=identity, loaded=len(result['tasks']),
                      hasMore=offset + len(result['tasks']) < result['total'])
        return result


def task_table_metadata(result):
    """Handler table roles, from native pipelines, previews and WorkHour totals."""
    from pyasm.biz import Pipeline, WorkHour
    from .task_inspector import inspector_object
    if not result['tasks']:
        return
    tasks = Search('sthpw/task')
    tasks.add_filter('project_code', Project.get_project_code())
    tasks.add_filters('code', [row['code'] for row in result['tasks']])
    tasks = {task.get_code(): task for task in tasks.get_sobjects()}
    hours = Search('sthpw/work_hour')
    hours.add_filter('project_code', Project.get_project_code())
    hours.add_filters('task_code', list(tasks))
    entries = {}
    for entry in hours.get_sobjects():
        entries.setdefault(entry.get_value('task_code'), []).append(entry)
    parents = {}
    for row in result['parents']:
        parent = discussion_target(row['__search_key__'])
        row['__preview__'] = inspector_object(parent)['preview']
        pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True))
        parents[(parent.get_base_search_type(), parent.get_code())] = pipeline
    for row in result['tasks']:
        task = tasks.get(row['code'])
        if not task:
            continue
        pipeline = parents.get((str(row.get('search_type') or '').split('?', 1)[0], row.get('search_code')))
        process = pipeline.get_process(row.get('process') or '') if pipeline else None
        row['__process__'] = dict(label=process.get_label() or row['process'], color=process.get_color() or '#607d8b') if process else dict(label=row.get('process') or 'Task', color='#607d8b')
        pipeline = task.get_pipeline()
        status = pipeline.get_process(row.get('status') or '') if pipeline else None
        row['__status__'] = dict(label=status.get_label() or row['status'], color=status.get_color()) if status else {}
        row['__hours__'] = WorkHour.get_summary(task, entries.get(task.get_code(), []))


def task_process_workspace(search_key):
    """Handler TaskProcessPanel: all permitted pipeline processes and task branches."""
    import hashlib
    from pyasm.biz import Pipeline
    from .task_inspector import task_scope, task_processes, process_configuration
    from .task_workspace_edits import workspace_edit_plan
    if not isinstance(search_key, str) or not search_key:
        raise ValueError('Choose a task parent')
    parent = discussion_target(search_key)
    pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True))
    catalogs, records = {}, []
    for choice in task_processes(parent, pipeline, ''):
        process = choice['value']
        if not pipeline or not pipeline.get_process(process):
            continue
        values, _workflow = process_configuration(pipeline, process)
        if (values.get('type') or choice['type']) == 'progress':
            continue
        _parent, _process, tasks, selected, _defaults, _revision, _pipeline = task_scope(search_key, process)
        branches = []
        for task in tasks or [None]:
            request = dict(operation='update' if task else 'create', search_key=search_key,
                           process=process, task_key=task.get_search_key() if task else '',
                           draft_id='process:'+hashlib.sha256((search_key+':'+process).encode()).hexdigest())
            _parent, _selected, editable, plan = workspace_edit_plan(request, catalogs)
            # Handler shows workflow defaults, not Task.create's automatic first status.
            if task is None:
                for name in ('status', 'assigned'):
                    if name in plan['task']:
                        plan['task'][name] = plan['defaults'].get(name) or ''
            task_pipeline = editable.get_pipeline()
            statuses = [dict(value=name, label=name,
                             color=task_pipeline.get_process(name).get_color() or '#607d8b')
                        for name in plan['statuses']]
            users = plan['users']
            group = values.get('assigned_login_group') or values.get('assigned_group')
            if group:
                members = Search('sthpw/login_in_group'); members.add_filter('login_group', group)
                logins = {row.get_value('login') for row in members.get_sobjects()}
                if logins:
                    users = [user for user in users if user['value'] in logins or user['value'] == plan['task'].get('assigned')]
            notes = Search('sthpw/note')
            primary = not task or task == tasks[0] or len(tasks) <= 1
            notes.add_filter('project_code', Project.get_project_code())
            notes.add_filter('process', process)
            notes.add_filter('search_type', parent.get_search_type() if primary else task.get_search_type())
            notes.add_filter('search_code', parent.get_code() if primary else task.get_code())
            branches.append(dict(plan=plan, statuses=statuses, users=users, notes=notes.get_count()))
        records.append(dict(choice, color=values.get('color') or '#607d8b', branches=branches,
                            selected=selected.get_search_key() if selected else ''))
    return dict(parent=Api._get_sobjects_dict([parent])[0], processes=records)


def query_task_workspace_page(filters, order_bys, project_code,
                              limit=500, offset=0, query=None):
    """Load a task page and all of its parents in one XML-RPC call."""
    from pyasm.search import Search

    if project_code != Project.get_project_code():
        raise ValueError('Task page belongs to another project')
    task_search = Search('sthpw/task')
    facets = {}
    if filters:
        task_search.add_op_filters(filters)
    if query:
        import re
        from datetime import date, timedelta
        from pyasm.search import SearchType, Sql

        query = dict(query)
        if not 1 <= int(limit) <= 500 or int(offset) < 0:
            raise ValueError('Task pages require a limit of 1..500 and a non-negative offset')
        panel = dict(query.get('filters') or {})
        quick = dict(query.get('quickFilters') or {})
        labels = dict(query.get('labels') or {})
        columns = {
            'process': 'process', 'status': 'status', 'assigned': 'assigned',
            'supervisor': 'supervisor', 'priority': 'priority',
            'milestone': 'milestone_code',
        }
        for name, values in quick.items():
            if name not in columns and name != 'preset':
                raise ValueError('Unknown task quick filter: %s' % name)
            if not isinstance(values, (list, tuple)):
                raise ValueError('Task quick filter %s requires a list of values' % name)
        if set(panel) - (set(columns) | {'text', 'due', 'day', 'hasNotes'}):
            raise ValueError('Unknown task filter fields')
        today = date.fromisoformat(str(query['today'])) if query.get('today') else date.today()

        def exact(column, values, search=None):
            search = search if search is not None else task_search
            values = list(values)
            search.add_op('begin')
            nonempty = [value for value in values if value != '']
            if nonempty:
                search.add_filters(column, nonempty)
            if '' in values:
                search.add_empty_filter(column)
            search.add_op('or')

        def due(value, search=None):
            search = search if search is not None else task_search
            if value == 'unscheduled':
                search.add_null_filter('bid_end_date')
                return
            boundaries = {
                'overdue': (None, today),
                'today': (today, today + timedelta(days=1)),
                'soon': (today + timedelta(days=1), today + timedelta(days=4)),
                'scheduled': (today + timedelta(days=4), None),
            }
            if value not in boundaries:
                raise ValueError('Unknown task deadline filter: %s' % value)
            start, end = boundaries[value]
            if start:
                search.add_filter('bid_end_date', start.isoformat(), op='>=')
            if end:
                search.add_filter('bid_end_date', end.isoformat(), op='<')

        def apply_preset(search, preset):
            search.add_op('begin')
            if preset == 'mine':
                if query.get('currentLogin'):
                    exact('assigned', [str(query['currentLogin'])], search)
                else:
                    search.add_where('1 = 0')
            elif preset == 'unassigned':
                search.add_empty_filter('assigned')
            elif preset in ('overdue', 'today'):
                due(preset, search)
            elif preset == 'recent':
                search.add_filter('timestamp', (today - timedelta(days=7)).isoformat(), op='>=')
                search.add_filter('timestamp', (today + timedelta(days=1)).isoformat(), op='<')
            elif preset == 'review':
                search.add_op('begin')
                for column in ('status', 'process', 'context', 'pipeline_code'):
                    search.add_regex_filter(column, 'approval|review')
                review_processes = [
                    item['value'] for item in labels.get('process', [])
                    if re.search('approval|review', str(item.get('type') or ''), re.I)
                ]
                if review_processes:
                    search.add_filters('process', review_processes)
                search.add_op('or')
            else:
                raise ValueError('Unknown task preset: %s' % preset)
            search.add_op('and')

        # Scope-wide aggregates keep choices available after filtering. Only
        # grouped values/counts cross the RPC boundary, not the task inventory.
        facets = {}
        for name, column in columns.items():
            facet_search = Search('sthpw/task')
            facet_search.order_by = False  # TACTIC adds sort columns to GROUP BY.
            facet_search.add_op_filters(filters or [])
            facet_search.add_column(column)
            # TACTIC 4.9 quotes expressions as identifiers unless this Select
            # uses raw mode. All projection/table names here are fixed above.
            facet_search.get_select().set_quoted_mode('none')
            facet_search.add_column('count(*)', as_column='task_count')
            facet_search.add_group_by(column)
            label_map = {str(item['value']): item for item in labels.get(name, [])}
            options = []
            for item in facet_search.get_sobjects():
                raw_value = item.get_value(column)
                value = str(raw_value if raw_value is not None else '')
                label = label_map.get(value) or {}
                options.append({
                    'key': value, 'title': str(label.get('label') or value),
                    'count': int(item.get_value('task_count') or 0),
                    'accent': str(label.get('color') or ''),
                })
            facets[name] = sorted(options, key=lambda item: item['title'].casefold())
        facets['preset'] = {}
        for preset in ('mine', 'unassigned', 'overdue', 'today', 'recent', 'review'):
            preset_search = Search('sthpw/task')
            preset_search.add_op_filters(filters or [])
            apply_preset(preset_search, preset)
            facets['preset'][preset] = preset_search.get_count()

        for name, column in columns.items():
            if panel.get(name) not in (None, ''):
                exact(column, [str(panel[name])])
            if quick.get(name):
                exact(column, [str(value) for value in quick[name]])
        if panel.get('due'):
            due(panel['due'])
        if panel.get('day'):
            day = date.fromisoformat(str(panel['day']))
            task_search.add_filter('bid_end_date', day.isoformat(), op='>=')
            task_search.add_filter('bid_end_date', (day + timedelta(days=1)).isoformat(), op='<')
        presets = list(quick.get('preset') or [])
        if presets:
            task_search.add_op('begin')
            for preset in presets:
                apply_preset(task_search, preset)
            task_search.add_op('or')

        text = str(panel.get('text') or '').strip()
        sort_mode = str(query.get('sort') or 'due')
        group_mode = str(query.get('group') or 'none')
        parent_labels = []
        if text or sort_mode == 'object' or group_mode == 'object':
            # Discover only distinct parent types, never the task inventory.
            types_search = Search('sthpw/task')
            types_search.add_op_filters(filters or [])
            types_search.add_column('search_type', distinct=True)
            parent_types = {str(item.get_value('search_type') or '').split('?', 1)[0]
                            for item in types_search.get_sobjects()}
            if text:
                task_search.add_op('begin')
                for column in ('description', 'process', 'context', 'status', 'assigned', 'supervisor', 'search_code'):
                    task_search.add_regex_filter(column, re.escape(text))
                for name, column in columns.items():
                    matches = [str(item['value']) for item in labels.get(name, [])
                               if text.casefold() in str(item.get('label') or item['value']).casefold()]
                    if matches:
                        exact(column, matches)
            for parent_type in sorted(parent_types):
                if not parent_type:
                    continue
                parent_search = Search(parent_type)
                title_column = next((column for column in ('name', 'title', 'code')
                                     if SearchType.column_exists(parent_type, column)), 'code')
                parent_search.add_column('code')
                if text:
                    parent_search.add_regex_filter(title_column, re.escape(text))
                    task_search.add_op('begin')
                    task_search.add_regex_filter('search_type', '^' + re.escape(parent_type) + r'(\?|$)')
                    task_search.add_search_filter('search_code', parent_search)
                    task_search.add_op('and')
                if sort_mode == 'object' or group_mode == 'object':
                    parent_codes = Search('sthpw/task')
                    parent_codes.add_op_filters(filters or [])
                    parent_codes.add_regex_filter('search_type', '^' + re.escape(parent_type) + r'(\?|$)')
                    parent_codes.add_column('search_code', distinct=True)
                    ordering_search = Search(parent_type)
                    ordering_search.add_search_filter('code', parent_codes)
                    ordering_search.add_column('code')
                    ordering_search.add_column(title_column)
                    parent_labels.extend((parent_type, str(item.get_value('code')), str(item.get_value(title_column) or item.get_value('code')))
                                         for item in ordering_search.get_sobjects())
            if text:
                task_search.add_op('or')

        if panel.get('hasNotes'):
            # Match the same contextual branch used by the returned note count.
            # All tables here belong to sthpw; values are correlated, not user SQL.
            table = task_search.search_type_obj.get_table()
            task = '"%s"' % table.replace('"', '""')
            task_type = "split_part(%s.search_type, '?', 1)" % task
            primary_order = "(CASE WHEN {a}.context IS NULL OR {a}.context = '' OR {a}.context = COALESCE(NULLIF({a}.process, ''), 'publish') THEN 0 ELSE 1 END, COALESCE(CAST({a}.timestamp AS TEXT), ''), {a}.code)"
            primary = "NOT EXISTS (SELECT 1 FROM {table} sibling WHERE sibling.project_code = {task}.project_code AND split_part(sibling.search_type, '?', 1) = split_part({task}.search_type, '?', 1) AND sibling.search_code = {task}.search_code AND COALESCE(NULLIF(sibling.process, ''), 'publish') = COALESCE(NULLIF({task}.process, ''), 'publish') AND {left} < {right})".format(
                table=task, task=task, left=primary_order.format(a='sibling'), right=primary_order.format(a=task))
            task_search.add_where("""EXISTS (SELECT 1 FROM note n WHERE n.project_code = {task}.project_code AND (
                (n.search_code = {task}.search_code AND COALESCE(NULLIF(n.process, ''), 'publish') = COALESCE(NULLIF({task}.process, ''), 'publish')
                 AND (n.search_type IS NULL OR n.search_type = '' OR split_part(n.search_type, '?', 1) = {parent_type}) AND {primary})
                OR (n.search_code = {task}.code AND (n.search_type IS NULL OR n.search_type = '' OR split_part(n.search_type, '?', 1) = 'sthpw/task') AND NOT ({primary}))
            ))""".format(task=task, parent_type=task_type, primary=primary))

        def label_order(mode, descending=False):
            # Select preserves its native "( CASE ... END )" orders verbatim;
            # bare CASE/LOWER expressions are quoted as column identifiers.
            column = {'due': 'bid_end_date', 'recent': 'timestamp', 'user': 'assigned',
                      'object': 'search_code', 'search_type': 'search_type',
                      'project': 'project_code'}.get(mode, columns.get(mode))
            if not column:
                raise ValueError('Unknown task ordering: %s' % mode)
            direction = 'DESC' if descending else 'ASC'
            if mode == 'object' and parent_labels:
                branches = ["WHEN split_part(search_type, '?', 1) = %s AND search_code = %s THEN %s" %
                            (Sql.quote(kind), Sql.quote(code), Sql.quote(label.casefold()))
                            for kind, code, label in parent_labels]
                expression = '( CASE ' + ' '.join(branches) + ' ELSE LOWER(search_code) END )'
            elif mode in ('due', 'recent'):
                expression = '"%s"' % column
                if mode == 'due':
                    task_search.get_select().add_order_by('( CASE WHEN "bid_end_date" IS NULL THEN 1 ELSE 0 END )')
                else:
                    direction = 'ASC' if descending else 'DESC'
            else:
                choices = labels.get('assigned' if mode == 'user' else mode) or []
                branches = ['WHEN %s THEN %s' % (Sql.quote(str(item['value'])), Sql.quote(str(item.get('label') or item['value']).casefold()))
                            for item in choices]
                expression = 'LOWER(CAST("%s" AS TEXT))' % column
                if branches:
                    expression = '( CASE CAST("%s" AS TEXT) %s ELSE %s END )' % (column, ' '.join(branches), expression)
                else:
                    expression = '( CASE WHEN "%s" IS NOT NULL THEN %s END )' % (column, expression)
            task_search.get_select().add_order_by(expression, direction=direction)

        if group_mode != 'none':
            label_order(group_mode, bool(query.get('descending')) and group_mode == sort_mode)
            group_column = {'user': 'assigned', 'object': 'search_code',
                            'search_type': 'search_type', 'project': 'project_code'}.get(
                                group_mode, columns.get(group_mode))
            if group_mode == 'object':
                task_search.add_order_by('search_type')
            task_search.add_order_by(group_column)
        label_order(sort_mode, bool(query.get('descending')))
        if sort_mode == 'object':
            label_order('process', bool(query.get('descending')))
        if sort_mode != 'due':
            label_order('due')
        task_search.add_order_by('code')
        order_bys = []
    for order_by in order_bys or []:
        task_search.add_order_by(order_by)
    total = task_search.get_count()
    if limit:
        task_search.set_limit(int(limit))
    if offset:
        task_search.set_offset(int(offset))
    task_objects = task_search.get_sobjects()
    tasks = Api._get_sobjects_dict(task_objects)

    page_groups = {}
    for info in tasks:
        parent_type = str(info.get('search_type') or '').split('?', 1)[0]
        parent_code = str(info.get('search_code') or '')
        process = str(info.get('process') or 'publish')
        if parent_code:
            page_groups.setdefault(
                (parent_type, parent_code, process), []
            ).append(info)

    all_group_tasks = dict((key, []) for key in page_groups)
    sibling_group_keys = {
        key for key, page_tasks in page_groups.items()
        if len(page_tasks) > 1 or any(
            task.get('context')
            and task.get('context') != key[2] for task in page_tasks
        )
    }
    sibling_search_codes = list(set(
        key[1] for key in sibling_group_keys
    ))
    sibling_processes = list(set(key[2] for key in sibling_group_keys))
    if sibling_search_codes and sibling_processes:
        sibling_search = Search('sthpw/task')
        sibling_search.add_filters('search_code', sibling_search_codes)
        sibling_search.add_filters('process', sibling_processes)
        sibling_search.add_filter('project_code', project_code)
        for task in sibling_search.get_sobjects():
            task_data = task.get_data()
            key = (
                str(task_data.get('search_type') or '').split('?', 1)[0],
                str(task_data.get('search_code') or ''),
                str(task_data.get('process') or 'publish'),
            )
            if key in all_group_tasks:
                all_group_tasks[key].append(task_data)

    for key, page_tasks in page_groups.items():
        group_tasks = all_group_tasks.get(key) or []
        known_codes = set(
            str(task.get('code') or '') for task in group_tasks
        )
        group_tasks.extend(
            task for task in page_tasks
            if str(task.get('code') or '') not in known_codes
        )
        all_group_tasks[key] = group_tasks

    search_codes = list(set(key[1] for key in page_groups))
    processes = list(set(key[2] for key in page_groups))
    root_note_counts = dict((key, 0) for key in page_groups)
    if search_codes and processes:
        note_search = Search('sthpw/note')
        note_search.add_filters('search_code', search_codes)
        note_search.add_filters('process', processes)
        note_search.add_filter('project_code', project_code)
        for note in note_search.get_sobjects():
            parent_type = str(
                note.get_value('search_type') or ''
            ).split('?', 1)[0]
            parent_code = str(note.get_value('search_code') or '')
            process = str(note.get_value('process') or 'publish')
            candidates = [
                key for key in root_note_counts
                if key[1] == parent_code and key[2] == process
                and (not parent_type or key[0] == parent_type)
            ]
            for key in candidates:
                root_note_counts[key] += 1

    task_parent_by_code = {}
    task_note_counts = {}
    primary_by_group = {}
    for key, group_tasks in all_group_tasks.items():
        group_tasks.sort(key=lambda item: (
            0 if not item.get('context')
            or item.get('context') == key[2] else 1,
            item.get('timestamp') or '', item.get('code') or '',
        ))
        primary_by_group[key] = (
            group_tasks[0].get('code') if group_tasks else None
        )
        if len(group_tasks) <= 1:
            continue
        for task in group_tasks:
            task_code = str(task.get('code') or '')
            if task_code:
                task_parent_by_code[task_code] = key

    if task_parent_by_code:
        task_note_search = Search('sthpw/note')
        task_note_search.add_filters(
            'search_code', list(task_parent_by_code)
        )
        task_note_search.add_filter('project_code', project_code)
        for note in task_note_search.get_sobjects():
            parent_type = str(
                note.get_value('search_type') or ''
            ).split('?', 1)[0]
            if parent_type not in ('', 'sthpw/task'):
                continue
            task_code = str(note.get_value('search_code') or '')
            if task_code in task_parent_by_code:
                task_note_counts[task_code] = (
                    task_note_counts.get(task_code, 0) + 1
                )

    for key, page_tasks in page_groups.items():
        primary_code = primary_by_group.get(key)
        for info in page_tasks:
            task_code = str(info.get('code') or '')
            is_primary = task_code == primary_code
            info['__primary_note_branch__'] = is_primary
            info['__notes_count__'] = (
                root_note_counts.get(key, 0) if is_primary
                else task_note_counts.get(task_code, 0)
            )
            info['__tasks_count__'] = 0

    parent_groups = {}
    for info in tasks:
        raw_type = str(info.get('search_type') or '')
        search_type = raw_type.split('?', 1)[0]
        code = str(info.get('search_code') or '')
        if search_type and code:
            parent_groups.setdefault(search_type, set()).add(code)
    parents = []
    for search_type, codes in parent_groups.items():
        parent_search = Search(search_type)
        parent_search.add_filters('code', list(codes))
        parents.extend(
            Api._get_sobjects_dict(parent_search.get_sobjects())
        )
    return {
        'tasks': tasks,
        'parents': parents,
        'total': total,
        'facets': facets,
        'offset': int(offset or 0),
        'limit': int(limit or 0),
    }
