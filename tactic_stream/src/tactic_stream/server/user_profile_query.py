"""Native Handler profile procedures from thlib/tactic_query.py (EPL-1.0).

Local SDK binding; excluded licensing and process-read guard are adaptations.
"""

def mutate_user_profile(login, values=None, password=None, groups=None,
                        group_access_levels=None, require_admin=False):
    """Update a TACTIC login through its native security object API."""
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.common import Environment
    from pyasm.search import Search

    current_login = str(server.get_login() or '')
    target_login = str(login or '').strip()
    if not target_login:
        raise ValueError('A login is required')

    if require_admin and not Environment.get_security().is_admin():
        raise PermissionError('Only a TACTIC administrator can manage users')

    privileged = bool(Environment.get_security().is_admin())
    if target_login != current_login and not privileged:
        raise PermissionError('You may only edit your own profile')

    search = Search('sthpw/login')
    search.set_show_retired(privileged)
    search.add_filter('login', target_login)
    login_object = search.get_sobject()
    if not login_object:
        raise ValueError('The selected user does not exist')

    requested_status = dict(values or {}).get('s_status')
    if target_login == current_login and requested_status == 'retired':
        raise ValueError('You cannot retire the account you are signed in with')

    self_fields = {
        'first_name', 'last_name', 'display_name', 'email',
        'phone_number', 'address', 'department',
    }
    supervisor_fields = {
        'upn', 'namespace', 's_status', 'project_code',
        'hourly_wage',
    }
    allowed = self_fields | (supervisor_fields if privileged else set())
    changed = False
    for name, value in dict(values or {}).items():
        name = str(name or '')
        if name not in allowed or name == 's_status':
            continue
        login_object.set_value(name, value if value is not None else '')
        changed = True
    if changed:
        login_object.commit()

    if privileged and 's_status' in dict(values or {}):
        old_status = login_object.get_value('s_status', no_exception=True)
        if requested_status != old_status:
            if requested_status == 'retired':
                login_object.retire()
            elif old_status == 'retired' and not requested_status:
                login_object.reactivate()
            else:
                login_object.set_value('s_status', requested_status or '')
                login_object.commit()

    password = str(password or '')
    if password:
        setter = getattr(login_object, 'set_password', None)
        if not callable(setter):
            raise RuntimeError('This TACTIC server cannot change passwords')
        setter(password)

    if groups is not None:
        if not privileged:
            raise PermissionError('Only a supervisor can change user groups')
        desired = set(str(value or '') for value in groups if value)
        membership_search = Search('sthpw/login_in_group')
        membership_search.add_filter('login', target_login)
        existing = set(
            str(item.get_value('login_group') or '')
            for item in membership_search.get_sobjects()
        )
        add_to_group = getattr(login_object, 'add_to_group', None)
        remove_from_group = getattr(login_object, 'remove_from_group', None)
        if not callable(add_to_group) or not callable(remove_from_group):
            raise RuntimeError('This TACTIC server has no group membership API')
        for group in sorted(desired - existing):
            add_to_group(group)
        for group in sorted(existing - desired):
            remove_from_group(group)

    changed_access_levels = {}
    if group_access_levels is not None:
        if not privileged:
            raise PermissionError(
                'Only a supervisor can change group access levels'
            )
        requested = dict(group_access_levels or {})
        if len(requested) != len(set(str(key or '') for key in requested)):
            raise ValueError('Each login group may only be updated once')
        normalized_access_levels = {}
        for group_code, access_level in requested.items():
            group_code = str(group_code or '').strip()
            access_level = str(access_level or '').strip()
            if not group_code:
                raise ValueError('A login group code is required')
            if len(access_level) > 32 or any(
                    ord(character) < 32 for character in access_level):
                raise ValueError('Access level must be at most 32 characters')
            if access_level not in ('', 'high', 'medium', 'low', 'min', 'none'):
                raise ValueError(
                    'Access level must be high, medium, low, min, none, or empty'
                )
            normalized_access_levels[group_code] = access_level
        group_objects = {}
        if normalized_access_levels:
            group_search = Search('sthpw/login_group')
            group_search.add_filters(
                'login_group', list(normalized_access_levels)
            )
            group_objects = {
                str(item.get_value('login_group') or ''): item
                for item in group_search.get_sobjects()
            }
        for group_code, access_level in normalized_access_levels.items():
            group_object = group_objects.get(group_code)
            if not group_object:
                raise ValueError('Login group does not exist: %s' % group_code)
            current_level = str(
                group_object.get_value('access_level', no_exception=True) or ''
            )
            if current_level == access_level:
                continue
            group_object.set_value('access_level', access_level)
            group_object.commit()
            changed_access_levels[group_code] = access_level

    data = dict(login_object.get_data())
    data.pop('password', None)
    data['groups'] = sorted(
        set(str(value or '') for value in groups if value)
        if groups is not None else set()
    )
    data['group_access_levels'] = changed_access_levels
    return json.dumps(data, separators=(',', ':'), default=str)


def create_user_profile(login, values=None, password=None, groups=None, require_admin=False):
    """Create a TACTIC login through the native login sObject API."""
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.common import Environment
    from pyasm.search import Search
    from pyasm.security import Login

    if require_admin and not Environment.get_security().is_admin():
        raise PermissionError('Only a TACTIC administrator can manage users')

    privileged = bool(Environment.get_security().is_admin())
    if not privileged:
        raise PermissionError('Only a TACTIC administrator can create users')

    target_login = str(login or '').strip()
    if not target_login:
        raise ValueError('A login is required')
    if any(character.isspace() for character in target_login):
        raise ValueError('A login cannot contain spaces')

    duplicate_search = Search('sthpw/login')
    duplicate_search.set_show_retired(True)
    duplicate_search.add_filter('login', target_login)
    if duplicate_search.get_sobject():
        raise ValueError('A user with this login already exists')

    allowed = {
        'first_name', 'last_name', 'display_name', 'email',
        'phone_number', 'address', 'department', 'upn', 'namespace', 's_status',
        'project_code', 'hourly_wage',
    }
    desired_groups = sorted(set(str(value) for value in (groups or []) if value))
    payload = {str(key): value for key, value in dict(values or {}).items()
               if key in allowed and value not in (None, '')}
    login_object = Login.create(target_login, str(password or ''), groups=desired_groups,
                                project_code=payload.get('project_code'))
    for name, value in payload.items():
        login_object.set_value(name, value)
    if payload:
        login_object.commit()

    data = dict(login_object.get_data())
    data.pop('password', None)
    data['groups'] = desired_groups
    return json.dumps(data, separators=(',', ':'), default=str)


def query_user_profile_data(login, project_code='', activity_limit=25):
    """Return profile aggregates; the shared journal owns recent activity."""
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from datetime import datetime, timedelta, timezone
    from pyasm.search import Search, SearchType

    login = str(login or '').strip()
    project_code = str(project_code or '').strip()
    # Retain the deployed procedure signature while activity is now queried
    # through query_user_recent_activity by both profile and feed clients.
    del activity_limit
    if not login or not project_code:
        return json.dumps({}, separators=(',', ':'))

    current_login = str(server.get_login() or '').strip()
    can_manage_work_hours = Environment.get_security().is_admin()
    can_view_work_hours = (
        current_login.casefold() == login.casefold()
        or can_manage_work_hours
    )

    task_search = Search('sthpw/task')
    task_search.add_filter('assigned', login)
    task_search.add_filter('project_code', project_code)
    task_search.add_order_by('bid_end_date')
    task_search.add_order_by('timestamp', direction='desc')
    from tactic.ui.table.task_element_wdg import TaskElementWdg
    task_objects = [task for task in task_search.get_sobjects()
                    if TaskElementWdg.can_view_process(task.get_value('process') or 'publish')]
    task_rows = [(task, task.get_data()) for task in task_objects]
    status_keys = {
        (str(data.get('pipeline_code') or 'task'), str(data['status']))
        for _, data in task_rows if data.get('status')
    }
    project_processes = {}
    if status_keys:
        process_search = Search(SearchType.build_search_type('config/process', project_code))
        process_search.add_filters('pipeline_code', sorted({code for code, _ in status_keys}))
        process_search.add_filters('process', sorted({status for _, status in status_keys}))
        project_processes = {
            (row.get_value('pipeline_code'), row.get_value('process')): row
            for row in process_search.get_sobjects()
        }
    status_counts = {}
    process_counts = {}
    today = datetime.now(timezone.utc).date()
    week_end = today + timedelta(days=6 - today.weekday())
    incomplete = 0
    overdue = 0
    due_this_week = 0
    completed_statuses = {}
    for task, data in task_rows:
        status = str(data.get('status') or '')
        status_key = (data.get('project_code'), data.get('pipeline_code'), status)
        if status_key not in completed_statuses:
            pipeline = task.get_pipeline()
            node = pipeline.get_process(status) if pipeline else None
            mapping = node.get_attribute('mapping') if node else None
            if node and not mapping:
                process = project_processes.get((str(data.get('pipeline_code') or 'task'), status))
                if process is None:
                    process = pipeline.get_process_sobject(status)
                workflow = process.get_json_value('workflow', {}) if process else {}
                mapping = workflow.get('mapping') or (workflow.get('default') or {}).get('mapping')
            # Match native workflow behavior, not completion percentages or
            # translated/custom status names. An explicit mapping takes priority.
            completed_statuses[status_key] = bool(node) and str(
                mapping or status
            ).strip().lower() in ('complete', 'approved')
        completed = completed_statuses[status_key]
        if not completed:
            incomplete += 1
        deadline_text = str(data.get('bid_end_date') or '')[:10]
        deadline = None
        try:
            deadline = datetime.strptime(deadline_text, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            pass
        if deadline and not completed:
            if deadline < today:
                overdue += 1
            if today <= deadline <= week_end:
                due_this_week += 1
        status = str(data.get('status') or '')
        status_entry = status_counts.setdefault(status, {
            'label': status or 'Unspecified', 'count': 0,
            'pipeline_code': str(data.get('pipeline_code') or ''),
            'search_type': str(data.get('search_type') or ''),
            'process': str(data.get('process') or ''),
            'status': status,
        })
        status_entry['count'] += 1
        process = str(data.get('process') or '')
        process_entry = process_counts.setdefault(process, {
            'label': process or 'Unspecified', 'count': 0,
            'pipeline_code': str(data.get('pipeline_code') or ''),
            'search_type': str(data.get('search_type') or ''),
            'process': process,
            'status': status,
        })
        process_entry['count'] += 1
    logged_hours = 0.0
    approved_hours = 0.0
    pending_hours = 0.0
    week_start = today - timedelta(days=today.weekday())
    if can_view_work_hours:
        hour_search = Search('sthpw/work_hour')
        hour_search.add_filter('login', login)
        hour_search.add_filter('project_code', project_code)
        hour_search.add_filter('day', week_start.isoformat(), op='>=')
        hour_search.add_filter('day', week_end.isoformat(), op='<=')
        for entry in hour_search.get_sobjects():
            try:
                regular = float(entry.get_value('straight_time') or 0.0)
            except (TypeError, ValueError):
                regular = 0.0
            try:
                overtime = float(entry.get_value('over_time') or 0.0)
            except (TypeError, ValueError):
                overtime = 0.0
            value = regular + overtime
            logged_hours += value
            if str(entry.get_value('status') or '').lower() == 'approved':
                approved_hours += value
            else:
                pending_hours += value

    return json.dumps({
        'taskSummary': {
            'total': len(task_objects),
            'incomplete': incomplete,
            'overdue': overdue,
            'dueThisWeek': due_this_week,
        },
        'workHourSummary': {
            'loggedHours': round(logged_hours, 2),
            'approvedHours': round(approved_hours, 2),
            'pendingHours': round(pending_hours, 2),
            'periodStart': week_start.isoformat(),
            'periodEnd': week_end.isoformat(),
        },
        'permissions': {
            'viewWorkHours': bool(can_view_work_hours),
            'manageWorkHours': bool(can_manage_work_hours),
        },
        'statusSummary': list(status_counts.values()),
        'processSummary': list(process_counts.values()),
    }, separators=(',', ':'))
