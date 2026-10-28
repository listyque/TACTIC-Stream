"""Handler tactic_query.query_user_recent_activity, EPL-1.0. No client runtime."""
def query_user_recent_activity(
        login='', project_code='', limit=25, offset=0, kinds=None,
        assigned_login='', include_day_counts=False, day='', logins=None,
        counts_only=False, counts_from_day='', instance_relations=None,
        object_scope=None, exclude_login='', time_zone='UTC'):
    """Return one enriched, pageable activity shape for profiles and feeds."""
    import json
    import xml.etree.ElementTree as ElementTree
    from pyasm.search import Search, SearchKey
    from pyasm.common import Environment

    security = Environment.get_security()

    def can_view(search_type):
        base = str(search_type or '').split('?', 1)[0]
        if not base:
            return True
        keys = [{'code': base}, {'code': base, 'project': project_code},
                {'code': '*'}, {'code': '*', 'project': project_code}]
        if not security.check_access('search_type', keys, 'view', default='allow' if base.startswith('sthpw/') else 'deny'):
            return False
        for endpoint in (instance_relations or {}).get(base, ()):
            endpoint_keys = [{'code': endpoint}, {'code': endpoint, 'project': project_code},
                             {'code': '*'}, {'code': '*', 'project': project_code}]
            if not security.check_access('search_type', endpoint_keys, 'view', default='deny'):
                return False
        return True

    login = str(login or '').strip()
    project_code = str(project_code or '').strip()
    limit = max(1, min(int(limit or 25), 100))
    offset = max(0, int(offset or 0))
    assigned_login = str(assigned_login or '').strip()
    exclude_login = str(exclude_login or '').strip().casefold()
    logins = list(dict.fromkeys(
        str(value or '').strip()
        for value in (logins or ())
        if str(value or '').strip()
    ))
    instance_relations = {
        clean_type: tuple(
            str(endpoint or '').split('?', 1)[0]
            for endpoint in endpoints or ()
            if str(endpoint or '').strip()
        )
        for raw_type, endpoints in dict(instance_relations or {}).items()
        for clean_type in (str(raw_type or '').split('?', 1)[0],)
        if clean_type
    }
    object_scope = dict(object_scope or {})
    scope_search_type = str(
        object_scope.get('searchType') or ''
    ).split('?', 1)[0]
    scope_search_code = str(object_scope.get('searchCode') or '')
    scope_search_id = str(object_scope.get('searchId') or '')
    scope_child_types = set(
        str(value or '').split('?', 1)[0]
        for value in object_scope.get('childTypes') or ()
        if str(value or '').strip()
    )
    scope_note_codes = set(
        str(value or '')
        for value in object_scope.get('noteCodes') or ()
        if str(value or '').strip()
    )
    scope_snapshot_codes = set(
        str(value or '')
        for value in object_scope.get('snapshotCodes') or ()
        if str(value or '').strip()
    )
    scope_work_hour_codes = set(
        str(value or '')
        for value in object_scope.get('workHourCodes') or ()
        if str(value or '').strip()
    )
    scope_indexed_objects = []
    for raw_reference in object_scope.get('indexedObjects') or ():
        reference = dict(raw_reference or {})
        reference_type = str(
            reference.get('searchType') or ''
        ).split('?', 1)[0]
        reference_code = str(reference.get('searchCode') or '')
        reference_id = str(reference.get('searchId') or '')
        if reference_type and (reference_code or reference_id):
            scope_indexed_objects.append({
                'searchType': reference_type,
                'searchCode': reference_code,
                'searchId': reference_id,
            })
    scope_task_ids = set(
        str(value or '')
        for value in object_scope.get('taskIds') or ()
        if str(value or '').strip()
    )
    scope_task_code_by_id = {}
    for reference in scope_indexed_objects:
        if reference.get('searchType') != 'sthpw/task':
            continue
        reference_id = str(reference.get('searchId') or '')
        reference_code = str(reference.get('searchCode') or '')
        if reference_id:
            scope_task_ids.add(reference_id)
            if reference_code:
                scope_task_code_by_id[reference_id] = reference_code
    scope_enabled = bool(scope_search_type and scope_search_code)
    scope_identity_values = {
        value for value in (scope_search_code, scope_search_id) if value
    }
    allowed_kinds = set(str(value or '') for value in (kinds or ()))
    counts_only = bool(counts_only)
    include_day_counts = bool(include_day_counts or counts_only)
    counts_from_day = str(counts_from_day or '').strip()
    day = str(day or '').strip()
    import datetime
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(time_zone)

    def utc_midnight(local_day, days=0):
        local = datetime.datetime.strptime(local_day, '%Y-%m-%d')
        local += datetime.timedelta(days=days)
        return local.replace(tzinfo=zone).astimezone(
            datetime.timezone.utc
        ).strftime('%Y-%m-%d %H:%M:%S')

    def local_day_key(timestamp):
        if not timestamp:
            return ''
        instant = datetime.datetime.fromisoformat(str(timestamp))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=datetime.timezone.utc)
        return instant.astimezone(zone).date().isoformat()

    day_start = utc_midnight(day) if day else ''
    day_end = utc_midnight(day, 1) if day else ''
    counts_start = utc_midnight(counts_from_day) if counts_from_day else ''

    records = []
    parent_refs = {}
    relation_refs = {}
    snapshot_codes = set()
    day_counts = {}
    message_codes = None
    sources = (
        ('sthpw/status_log', 'status', True),
        ('sthpw/snapshot', 'publication', True),
        ('sthpw/note', 'note', True),
        ('sthpw/task', 'task', True),
        ('sthpw/message_log', 'message', False),
    )

    technical_columns = {
        'id', 'code', 'search_type', 'search_id', 'search_code',
        'project_code', 'timestamp', 'login', 'transaction_code',
        'pipeline_code', '__search_key__',
    }

    def clean_search_type(value):
        return str(value or '').split('?', 1)[0]

    def actor_is_excluded(value):
        return bool(
            exclude_login
            and str(value or '').strip().casefold() == exclude_login
        )

    def source_actor(data, kind):
        if kind == 'task':
            return str(data.get('login') or data.get('changed_by') or '')
        return str(
            data.get('login') or data.get('assigned')
            or data.get('changed_by') or ''
        )

    def json_mapping(value):
        if isinstance(value, dict):
            return dict(value)
        if not value:
            return {}
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError):
            return {}
        return dict(decoded) if isinstance(decoded, dict) else {}

    def transaction_xml(transaction, data):
        """Read transaction XML through TACTIC so zlib payloads are expanded."""
        getter = getattr(transaction, 'get_xml_value', None)
        if getter:
            try:
                xml_value = getter('transaction')
                serializer = getattr(xml_value, 'to_string', None)
                if serializer:
                    try:
                        value = serializer(pretty=False)
                    except TypeError:
                        value = serializer()
                    if isinstance(value, bytes):
                        return value.decode('utf-8', errors='replace')
                    return str(value or '')
            except (AttributeError, TypeError, ValueError):
                pass
        return str(data.get('transaction') or '')

    def parse_transaction(value):
        """Return the user-facing object mutations from a TACTIC transaction."""
        text = str(value or '').strip()
        if not text or '<' not in text:
            return []
        try:
            root = ElementTree.fromstring(text)
        except (ElementTree.ParseError, TypeError, ValueError):
            return []
        mutations = []
        for node in root.iter('sobject'):
            action = str(node.get('action') or '').strip().lower()
            if action not in ('insert', 'create', 'update', 'delete', 'remove'):
                continue
            changes = []
            field_values = {}
            for column in node.findall('column'):
                name = str(column.get('name') or '').strip()
                if not name:
                    continue
                before = str(column.get('from') or '').strip()
                after = str(column.get('to') or '').strip()
                if before == after:
                    continue
                field_values[name] = {
                    'before': before,
                    'after': after,
                }
                if name.lower() in technical_columns:
                    continue
                changes.append({
                    'field': name.replace('_', ' '),
                    'before': before,
                    'after': after,
                })
            display_title = ''
            for preferred_field in ('name', 'title'):
                title_change = next((
                    change for change in changes
                    if str(change.get('field') or '').lower()
                    == preferred_field
                ), None)
                if not title_change:
                    continue
                if action in ('delete', 'remove'):
                    display_title = str(title_change.get('before') or '')
                else:
                    display_title = str(
                        title_change.get('after')
                        or title_change.get('before') or ''
                    )
                break
            mutations.append({
                'action': action,
                'searchType': clean_search_type(node.get('search_type')),
                'searchCode': str(
                    node.get('search_code') or node.get('search_id') or ''
                ),
                'changes': changes[:4],
                'fieldValues': field_values,
                'displayTitle': display_title,
            })
        return mutations

    def mutation_value(mutation, field):
        change = dict(
            (mutation.get('fieldValues') or {}).get(field) or {}
        )
        if mutation_kind(mutation) == 'delete':
            return str(change.get('before') or change.get('after') or '')
        return str(change.get('after') or change.get('before') or '')

    def mutation_title(mutation):
        return str(mutation.get('displayTitle') or '')

    work_task_access = {}

    def mutation_access(mutation):
        if not can_view(mutation.get('searchType')):
            return False
        if clean_search_type(mutation.get('searchType')) != 'sthpw/work_hour':
            return True
        task_code = mutation_value(mutation, 'task_code')
        if not task_code:
            return security.is_admin()
        if task_code not in work_task_access:
            task = Search.get_by_code('sthpw/task', task_code)
            work_task_access[task_code] = bool(task and can_view(task.get_value('search_type')))
        return work_task_access[task_code]

    def audit_detail(mutation, transaction_data):
        changes = mutation.get('changes') or []
        if changes:
            parts = []
            for change in changes:
                field = change.get('field') or ''
                before = change.get('before') or ''
                after = change.get('after') or ''
                if before and after:
                    parts.append('{0}: {1} -> {2}'.format(
                        field, before, after
                    ))
                elif after:
                    parts.append('{0}: {1}'.format(field, after))
                elif before:
                    parts.append('{0}: {1} -> empty'.format(field, before))
            return '; '.join(parts)[:480]
        return str(
            transaction_data.get('description')
            or transaction_data.get('title') or ''
        )[:480]
    if not allowed_kinds or 'message' in allowed_kinds:
        subscription_search = Search('sthpw/subscription')
        subscription_search.add_filter('login', str(Environment.get_user_name() or ''))
        subscription_search.add_filter('category', 'chat')
        message_codes = list(set(
            item.get_value('message_code')
            for item in subscription_search.get_sobjects()
            if item.get_value('message_code')
        ))

    def apply_source_filters(search, kind, filter_project, filter_day=True):
        if kind == 'task' and assigned_login:
            search.add_filter('assigned', assigned_login)
        elif logins:
            search.add_filters(
                'assigned' if kind == 'task' else 'login', logins
            )
        elif login:
            search.add_filter('login', login)
        if exclude_login:
            search.add_filter('login', exclude_login, op='!=')
        if kind == 'message':
            search.add_filter('category', 'chat')
            search.add_filter('status', 'deleted', op='!=')
            if message_codes:
                search.add_filters('message_code', message_codes)
            else:
                search.add_filter('message_code', '__no_accessible_chat__')
        if project_code and filter_project:
            search.add_filter('project_code', project_code)
        if scope_enabled:
            if kind in ('task', 'publication'):
                search.add_filter('search_type', scope_search_type)
                if scope_search_id:
                    search.add_filter('search_id', scope_search_id)
                else:
                    search.add_filter('search_code', scope_search_code)
            elif kind in ('status', 'note'):
                if scope_search_id or scope_task_ids:
                    parent_ids = list(scope_task_ids)
                    if scope_search_id:
                        parent_ids.append(scope_search_id)
                    search.add_filters(
                        'search_id', list(dict.fromkeys(parent_ids))
                    )
                else:
                    parent_codes = list(scope_task_codes)
                    parent_codes.append(scope_search_code)
                    search.add_filters(
                        'search_code', list(dict.fromkeys(parent_codes))
                    )
        if filter_day and day:
            search.add_filter('timestamp', day_start, op='>=')
            search.add_filter('timestamp', day_end, op='<')
        elif not filter_day and counts_from_day:
            search.add_filter(
                'timestamp', counts_start, op='>='
            )

    scope_task_codes = {
        str(value or '')
        for value in object_scope.get('taskCodes') or ()
        if str(value or '').strip()
    }
    if scope_enabled and not scope_task_codes:
        scope_task_search = Search('sthpw/task')
        scope_task_search.add_filter('search_type', scope_search_type)
        scope_task_search.add_filter('search_code', scope_search_code)
        if project_code:
            scope_task_search.add_filter('project_code', project_code)
        for scope_task in scope_task_search.get_sobjects():
            scope_task_data = scope_task.get_data()
            if (
                    clean_search_type(scope_task_data.get('search_type'))
                    != scope_search_type
                    or str(scope_task_data.get('search_code') or '')
                    != scope_search_code):
                continue
            scope_task_code = str(scope_task.get_code() or '')
            if scope_task_code:
                scope_task_codes.add(scope_task_code)
                scope_task_id = str(
                    scope_task_data.get('id') or scope_task.get_id() or ''
                )
                if scope_task_id:
                    scope_task_ids.add(scope_task_id)
                    scope_task_code_by_id[scope_task_id] = (
                        scope_task_code
                    )

    if scope_enabled and not scope_indexed_objects:
        scope_indexed_objects.append({
            'searchType': scope_search_type,
            'searchCode': scope_search_code,
            'searchId': scope_search_id,
        })

    for search_type, kind, filter_project in sources:
        if not can_view(search_type):
            continue
        if allowed_kinds and kind not in allowed_kinds:
            continue
        if include_day_counts:
            calendar_search = Search(search_type)
            apply_source_filters(
                calendar_search, kind, filter_project, filter_day=False
            )
            for calendar_item in calendar_search.get_sobjects():
                if not can_view(calendar_item.get_value('search_type', no_exception=True)):
                    continue
                if actor_is_excluded(source_actor(
                        calendar_item.get_data(), kind)):
                    continue
                day_key = local_day_key(calendar_item.get_value('timestamp'))
                if len(day_key) == 10:
                    day_counts[day_key] = day_counts.get(day_key, 0) + 1
        if counts_only:
            continue
        search = Search(search_type)
        apply_source_filters(search, kind, filter_project)
        search.add_order_by('timestamp', direction='desc')
        search.set_limit(offset + limit)
        for item in search.get_sobjects():
            data = item.get_data()
            if not can_view(data.get('search_type')):
                continue
            item_code = str(data.get('code') or data.get('id') or '')
            if kind == 'publication' and item_code:
                snapshot_codes.add(item_code)
            process = str(data.get('process') or '')
            context = str(data.get('context') or process)
            version = data.get('version')
            parent_type = str(data.get('search_type') or '').split('?', 1)[0]
            parent_code = str(data.get('search_code') or '')
            parent_id = str(data.get('search_id') or '')
            if scope_enabled and not parent_code:
                if (
                        clean_search_type(parent_type) == scope_search_type
                        and parent_id == scope_search_id):
                    parent_code = scope_search_code
                elif clean_search_type(parent_type) == 'sthpw/task':
                    parent_code = str(
                        scope_task_code_by_id.get(parent_id) or ''
                    )
            if kind == 'message':
                parent_type = 'sthpw/message'
                parent_code = str(data.get('message_code') or '')
            if parent_type and parent_code:
                parent_refs.setdefault(parent_type, set()).add(parent_code)

            if kind == 'status':
                before = str(data.get('from_status') or '')
                after = str(
                    data.get('to_status') or data.get('status') or ''
                )
                title = 'Status changed'
                detail = ' -> '.join(
                    value for value in (before, after) if value
                )
            elif kind == 'publication':
                title = 'Published snapshot'
                detail = str(data.get('description') or '')[:480]
            elif kind == 'note':
                title = 'Added note'
                detail = str(data.get('note') or '')[:240]
            elif kind == 'message':
                title = 'Sent message'
                detail = str(data.get('message') or '')[:240]
            else:
                title = 'Updated task'
                detail = str(
                    data.get('description') or data.get('status') or ''
                )[:240]
            if kind == 'publication':
                item_title = ''
            elif kind == 'task':
                item_title = context or process
            else:
                item_title = str(
                    data.get('name') or data.get('title') or item_code
                )
            actor = source_actor(data, kind)
            records.append({
                'eventId': '{0}:{1}'.format(
                    kind, data.get('code') or data.get('id') or ''
                ),
                'searchKey': str(SearchKey.get_by_sobject(
                    item, use_id=(kind == 'status')
                ) or ''),
                'kind': kind,
                'title': title,
                'detail': detail,
                'actor': actor,
                'timestamp': str(data.get('timestamp') or ''),
                'itemCode': item_code,
                'itemTitle': item_title,
                'project': str(data.get('project_code') or project_code),
                'process': process,
                'context': context,
                'version': str(version if version not in (None, '') else ''),
                'statusBefore': before if kind == 'status' else '',
                'statusAfter': (
                    after if kind == 'status'
                    else str(data.get('status') or '') if kind == 'task'
                    else ''
                ),
                'taskCode': item_code if kind == 'task' else (
                    parent_code if kind == 'status'
                    and parent_type == 'sthpw/task' else ''
                ),
                'serverGenerated': bool(
                    kind == 'status' and not actor.strip()
                ),
                '_parentType': parent_type,
                '_parentCode': parent_code,
                '_taskId': str(data.get('id') or '') if kind == 'task' else '',
            })

    task_activity_records = [
        record for record in records
        if record.get('kind') == 'task' and record.get('taskCode')
    ]
    unresolved_task_codes = {
        str(record.get('taskCode') or ''): record
        for record in task_activity_records
    }
    if unresolved_task_codes and security.check_access('search_type', 'sthpw/transaction_log', 'view') and security.check_access('search_type', 'sthpw/change_timestamp', 'view'):
        task_change_search = Search('sthpw/change_timestamp')
        task_change_search.add_filter('search_type', 'sthpw/task')
        task_change_search.add_filters(
            'search_code', list(unresolved_task_codes)
        )
        if project_code:
            task_change_search.add_filter('project_code', project_code)
        transaction_code_by_task = {}
        for task_change in task_change_search.get_sobjects():
            task_change_data = task_change.get_data()
            task_code = str(task_change_data.get('search_code') or '')
            transaction_code = str(
                task_change_data.get('transaction_code') or ''
            )
            if task_code in unresolved_task_codes and transaction_code:
                transaction_code_by_task[task_code] = transaction_code

        transaction_codes = set(transaction_code_by_task.values())
        transactions_by_code = {}
        if transaction_codes:
            task_transaction_search = Search('sthpw/transaction_log')
            task_transaction_search.add_filters(
                'code', list(transaction_codes)
            )
            for task_transaction in task_transaction_search.get_sobjects():
                task_transaction_data = task_transaction.get_data()
                transaction_code = str(
                    task_transaction_data.get('code') or ''
                )
                if transaction_code in transaction_codes:
                    transactions_by_code[transaction_code] = (
                        task_transaction_data
                    )

        resolved_task_codes = set()
        for task_code, transaction_code in transaction_code_by_task.items():
            transaction_data = transactions_by_code.get(transaction_code)
            if transaction_data is None:
                continue
            record = unresolved_task_codes[task_code]
            actor = str(transaction_data.get('login') or '')
            record['actor'] = actor
            record['serverGenerated'] = not bool(actor.strip())
            resolved_task_codes.add(task_code)

        unresolved_task_ids = {
            str(record.get('_taskId') or ''): record
            for task_code, record in unresolved_task_codes.items()
            if task_code not in resolved_task_codes
            and record.get('_taskId')
        }
        if unresolved_task_ids:
            task_log_search = Search('sthpw/sobject_log')
            task_log_search.add_filter('search_type', 'sthpw/task')
            task_log_search.add_filters(
                'search_id', list(unresolved_task_ids)
            )
            task_log_search.add_order_by('timestamp', direction='desc')
            for task_log in task_log_search.get_sobjects():
                task_log_data = task_log.get_data()
                if clean_search_type(
                        task_log_data.get('search_type')) != 'sthpw/task':
                    continue
                task_id = str(task_log_data.get('search_id') or '')
                record = unresolved_task_ids.pop(task_id, None)
                if record is None:
                    continue
                actor = str(task_log_data.get('login') or '')
                record['actor'] = actor
                record['serverGenerated'] = not bool(actor.strip())

    task_parent_records = [
        record for record in records
        if record.get('_parentType') == 'sthpw/task'
        and record.get('_parentCode')
    ]
    if task_parent_records:
        task_codes = list(set(
            record.get('_parentCode') for record in task_parent_records
        ))
        task_search = Search('sthpw/task')
        task_search.add_filters('code', task_codes)
        tasks_by_code = {
            str(item.get_code() or ''): item.get_data()
            for item in task_search.get_sobjects()
        }
        for record in task_parent_records:
            task_code = str(record.get('_parentCode') or '')
            task_data = tasks_by_code.get(task_code, {})
            root_type = clean_search_type(task_data.get('search_type'))
            root_code = str(task_data.get('search_code') or '')
            root_id = str(task_data.get('search_id') or '')
            if (
                    scope_enabled and not root_code
                    and root_type == scope_search_type
                    and root_id == scope_search_id):
                root_code = scope_search_code
            if not root_type or not root_code:
                continue
            record['_parentType'] = root_type
            record['_parentCode'] = root_code
            record['taskCode'] = task_code
            record['process'] = str(
                task_data.get('process') or record.get('process') or ''
            )
            record['context'] = str(
                task_data.get('context') or record.get('context')
                or record.get('process') or ''
            )
            record['itemTitle'] = str(
                record.get('context') or record.get('process') or ''
            )
            if record.get('kind') == 'status':
                record['serverGenerated'] = bool(
                    not str(record.get('actor') or '').strip()
                )
            parent_refs.setdefault(root_type, set()).add(root_code)

    page_cutoff = ''
    page_candidate_count = offset + limit
    page_timestamps = sorted(
        (
            str(record.get('timestamp') or '')
            for record in records
            if record.get('timestamp')
        ),
        reverse=True,
    )
    if len(page_timestamps) >= page_candidate_count:
        page_cutoff = page_timestamps[page_candidate_count - 1]

    audit_kinds = {'create', 'change', 'delete', 'work_hour'}
    audit_enabled = not allowed_kinds or bool(allowed_kinds & audit_kinds)
    if counts_only and not audit_enabled:
        return {
            'records': [],
            'countsFromDay': counts_from_day,
            'dayCounts': [
                {'dateKey': day_key, 'count': day_counts[day_key]}
                for day_key in sorted(day_counts, reverse=True)
            ],
        }
    audited_targets = set()
    if audit_enabled:
        def apply_transaction_filters(search, filter_day):
            if project_code:
                search.add_filter('namespace', project_code)
            if logins:
                search.add_filters('login', logins)
            elif login:
                search.add_filter('login', login)
            if exclude_login:
                search.add_filter('login', exclude_login, op='!=')
            if filter_day and day:
                search.add_filter(
                    'timestamp', day_start, op='>='
                )
                search.add_filter(
                    'timestamp', day_end, op='<'
                )
            elif not filter_day and counts_from_day:
                search.add_filter(
                    'timestamp', counts_start, op='>='
                )
            if filter_day and page_cutoff:
                search.add_filter('timestamp', page_cutoff, op='>=')

        def mutation_kind(mutation):
            action = mutation.get('action') or 'update'
            if action in ('insert', 'create'):
                return 'create'
            if action in ('delete', 'remove'):
                return 'delete'
            return 'change'

        instance_type_cache = {}

        def instance_relation_refs(mutation):
            """Resolve both semantic endpoints of an instance mutation."""
            instance_type = str(mutation.get('searchType') or '')
            if not instance_type:
                return None
            field_values = dict(mutation.get('fieldValues') or {})
            candidate_columns = [
                str(column) for column in field_values
                if str(column).endswith('_code')
            ]
            if len(field_values) < 2:
                return None
            endpoint_types = instance_type_cache.get(instance_type)
            if endpoint_types is None:
                endpoint_types = instance_relations.get(instance_type, ())
                instance_type_cache[instance_type] = endpoint_types
            if len(endpoint_types or ()) != 2:
                return None

            try:
                from pyasm.biz import Schema
                schema = Schema.get(project_code=project_code)
            except (AttributeError, ImportError, TypeError):
                schema = None

            used_columns = set()
            endpoint_refs = []
            for endpoint_type in endpoint_types:
                try:
                    foreign_keys = tuple(
                        schema.get_foreign_keys(
                            instance_type, endpoint_type
                        ) or ()
                    ) if schema is not None else ()
                except (AttributeError, KeyError, TypeError, ValueError):
                    foreign_keys = ()

                instance_column = next((
                    column for column in foreign_keys
                    if column in field_values and column not in used_columns
                ), '')
                if not instance_column:
                    conventional = '{0}_code'.format(
                        str(endpoint_type).split('/')[-1]
                    )
                    if (
                            conventional in field_values
                            and conventional not in used_columns):
                        instance_column = conventional
                if not instance_column:
                    instance_column = next((
                        column for column in candidate_columns
                        if column not in used_columns
                    ), '')
                if not instance_column:
                    return None

                endpoint_column = next((
                    column for column in foreign_keys
                    if column != instance_column
                    and column not in field_values
                ), 'code')
                change = dict(field_values.get(instance_column) or {})
                endpoint_value = str(
                    change.get('before')
                    if mutation_kind(mutation) == 'delete'
                    else change.get('after') or change.get('before') or ''
                )
                if not endpoint_value:
                    return None
                used_columns.add(instance_column)
                endpoint_refs.append((
                    str(endpoint_type), str(endpoint_column), endpoint_value
                ))
            return tuple(endpoint_refs)

        def scope_endpoint_matches(endpoint_ref):
            if not scope_enabled or not endpoint_ref:
                return False
            endpoint_type, _endpoint_column, endpoint_value = endpoint_ref
            return (
                clean_search_type(endpoint_type) == scope_search_type
                and str(endpoint_value or '') in scope_identity_values
            )

        def scoped_mutation_role(mutation, instance_refs=None):
            """Classify how one audit mutation belongs to the object scope."""
            if not scope_enabled:
                return 'object'
            parent_type = clean_search_type(mutation.get('searchType'))
            parent_code = str(mutation.get('searchCode') or '')
            if (
                    parent_type == scope_search_type
                    and parent_code == scope_search_code):
                return 'root'
            if instance_refs and any(
                    scope_endpoint_matches(endpoint)
                    for endpoint in instance_refs):
                return 'relation'

            field_values = dict(mutation.get('fieldValues') or {})
            relationship_values = {
                str(value or '')
                for field, change in field_values.items()
                if (
                    str(field or '').lower()
                    not in technical_columns
                    and str(field or '').lower().endswith(('_code', '_id'))
                )
                for value in (
                    dict(change or {}).get('before'),
                    dict(change or {}).get('after'),
                )
                if str(value or '')
            }
            parent_reference = bool(
                relationship_values.intersection(scope_identity_values)
            )
            generic_parent_reference = (
                mutation_value(mutation, 'search_code')
                in scope_identity_values
                or mutation_value(mutation, 'search_id')
                in scope_identity_values
            )
            if parent_type == 'sthpw/task':
                if (
                        parent_code in scope_task_codes
                        or mutation_value(mutation, 'search_code')
                        == scope_search_code):
                    return 'system'
                return ''
            if parent_type in ('sthpw/note', 'sthpw/snapshot'):
                parent_code_value = mutation_value(
                    mutation, 'search_code'
                )
                if (
                        parent_code in (
                            scope_note_codes
                            if parent_type == 'sthpw/note'
                            else scope_snapshot_codes
                        )
                        or
                        parent_code_value == scope_search_code
                        or parent_code_value in scope_task_codes):
                    return 'system'
                return ''
            if parent_type == 'sthpw/work_hour':
                if (
                        parent_code in scope_work_hour_codes
                        or mutation_value(
                            mutation, 'task_code'
                        ) in scope_task_codes):
                    return 'work_hour'
                return ''
            if (
                    parent_type in scope_child_types
                    and (parent_reference or generic_parent_reference)):
                return 'child'
            return ''

        if include_day_counts:
            calendar_audit_search = Search('sthpw/transaction_log')
            apply_transaction_filters(calendar_audit_search, False)
            for calendar_transaction in calendar_audit_search.get_sobjects():
                calendar_data = calendar_transaction.get_data()
                if actor_is_excluded(calendar_data.get('login')):
                    continue
                day_key = local_day_key(calendar_data.get('timestamp'))
                if len(day_key) != 10:
                    continue
                for mutation in parse_transaction(transaction_xml(
                        calendar_transaction, calendar_data)):
                    parent_type = mutation.get('searchType') or ''
                    if not mutation_access(mutation):
                        continue
                    instance_refs = (
                        instance_relation_refs(mutation)
                        if mutation_kind(mutation) in ('create', 'delete')
                        else None
                    )
                    if (
                            scope_enabled
                            and not scoped_mutation_role(
                                mutation, instance_refs
                            )):
                        continue
                    kind = (
                        'work_hour'
                        if parent_type == 'sthpw/work_hour'
                        else mutation_kind(mutation)
                    )
                    if (
                            not parent_type
                            or parent_type.startswith('sthpw/')
                            and parent_type != 'sthpw/work_hour'
                            and not (
                                scope_enabled
                                and scoped_mutation_role(
                                    mutation, instance_refs
                                ) == 'system'
                            )
                            or allowed_kinds and kind not in allowed_kinds):
                        continue
                    day_counts[day_key] = day_counts.get(day_key, 0) + 1

        if counts_only:
            return {
                'records': [],
                'countsFromDay': counts_from_day,
                'dayCounts': [
                    {'dateKey': day_key, 'count': day_counts[day_key]}
                    for day_key in sorted(day_counts, reverse=True)
                ],
            }

        transaction_limit = max((offset + limit) * 4, 100)
        scoped_object_logs = []
        transactions = []
        if scope_enabled:
            # transaction_log is project-wide.  Limiting that table before
            # checking the XML displaced older events of a selected object in
            # any active project.  sobject_log is the native per-object index;
            # query it first for all live records in this report, then fetch
            # the exact transactions it references.
            indexed_ids_by_type = {}
            for reference in scope_indexed_objects:
                reference_type = clean_search_type(
                    reference.get('searchType')
                )
                reference_id = str(reference.get('searchId') or '')
                if reference_type and reference_id:
                    indexed_ids_by_type.setdefault(
                        reference_type, set()
                    ).add(reference_id)

            indexed_transaction_ids = set()
            for reference_type, reference_ids in indexed_ids_by_type.items():
                indexed_log_search = Search('sthpw/sobject_log')
                indexed_log_search.add_filter(
                    'search_type', reference_type
                )
                indexed_log_search.add_filters(
                    'search_id', list(reference_ids)
                )
                indexed_log_search.add_order_by(
                    'timestamp', direction='desc'
                )
                indexed_log_search.set_limit(transaction_limit)
                for indexed_log in indexed_log_search.get_sobjects():
                    indexed_data = indexed_log.get_data()
                    transaction_id = str(
                        indexed_data.get('transaction_log_id') or ''
                    )
                    if not transaction_id:
                        continue
                    indexed_transaction_ids.add(transaction_id)
                    scoped_object_logs.append(indexed_data)

            if len(indexed_transaction_ids) > transaction_limit:
                ordered_index_ids = []
                seen_index_ids = set()
                for indexed_data in sorted(
                        scoped_object_logs,
                        key=lambda item: str(
                            item.get('timestamp') or ''
                        ),
                        reverse=True):
                    transaction_id = str(
                        indexed_data.get('transaction_log_id') or ''
                    )
                    if (
                            not transaction_id
                            or transaction_id in seen_index_ids):
                        continue
                    seen_index_ids.add(transaction_id)
                    ordered_index_ids.append(transaction_id)
                    if len(ordered_index_ids) >= transaction_limit:
                        break
                indexed_transaction_ids = set(ordered_index_ids)
                scoped_object_logs = [
                    indexed_data for indexed_data in scoped_object_logs
                    if str(
                        indexed_data.get('transaction_log_id') or ''
                    ) in indexed_transaction_ids
                ]

            if indexed_transaction_ids:
                indexed_transaction_search = Search(
                    'sthpw/transaction_log'
                )
                apply_transaction_filters(
                    indexed_transaction_search, True
                )
                indexed_transaction_search.add_filters(
                    'id', list(indexed_transaction_ids)
                )
                indexed_transaction_search.add_order_by(
                    'timestamp', direction='desc'
                )
                indexed_transaction_search.set_limit(transaction_limit)
                transactions.extend(
                    indexed_transaction_search.get_sobjects()
                )

            # Delete and unlink operations intentionally have no sobject_log
            # row.  Their uncompressed XML still contains the selected root
            # identity, so query that identity before applying the page limit.
            # Compressed updates are covered by the native index above.
            identity_transaction_search = Search(
                'sthpw/transaction_log'
            )
            apply_transaction_filters(
                identity_transaction_search, True
            )
            identity_transaction_search.add_filter(
                'transaction', '%{0}%'.format(scope_search_code),
                op='like',
            )
            identity_transaction_search.add_order_by(
                'timestamp', direction='desc'
            )
            identity_transaction_search.set_limit(transaction_limit)
            transactions.extend(
                identity_transaction_search.get_sobjects()
            )
        else:
            transaction_search = Search('sthpw/transaction_log')
            apply_transaction_filters(transaction_search, True)
            transaction_search.add_order_by(
                'timestamp', direction='desc'
            )
            transaction_search.set_limit(transaction_limit)
            transactions = transaction_search.get_sobjects()

        transaction_by_id = {}
        for transaction in transactions:
            transaction_data = transaction.get_data()
            transaction_data['_expandedTransaction'] = transaction_xml(
                transaction, transaction_data
            )
            transaction_id = str(
                transaction.get_id() or transaction_data.get('id') or ''
            )
            if transaction_id:
                transaction_by_id[transaction_id] = transaction_data
        if scope_enabled and len(transaction_by_id) > transaction_limit:
            ordered_transactions = sorted(
                transaction_by_id.items(),
                key=lambda item: str(
                    item[1].get('timestamp') or ''
                ),
                reverse=True,
            )[:transaction_limit]
            transaction_by_id = dict(ordered_transactions)
        if transaction_by_id:
            object_logs_by_transaction = {}
            if scope_enabled:
                object_log_values = scoped_object_logs
            else:
                object_log_search = Search('sthpw/sobject_log')
                object_log_search.add_filters(
                    'transaction_log_id', list(transaction_by_id.keys())
                )
                object_log_values = [
                    object_log.get_data()
                    for object_log in object_log_search.get_sobjects()
                ]
            for object_data in object_log_values:
                transaction_id = str(
                    object_data.get('transaction_log_id') or ''
                )
                object_logs_by_transaction.setdefault(
                    transaction_id, []
                ).append(object_data)

            for transaction_id, transaction_data in transaction_by_id.items():
                mutations = parse_transaction(
                    transaction_data.get('_expandedTransaction')
                )
                if not mutations:
                    continue
                indexed = object_logs_by_transaction.get(transaction_id, [])
                indexed_types = set(
                    clean_search_type(row.get('search_type'))
                    for row in indexed
                )
                for mutation_index, mutation in enumerate(mutations):
                    parent_type = mutation.get('searchType') or ''
                    if not mutation_access(mutation):
                        continue
                    parent_code = mutation.get('searchCode') or ''
                    mutation_action = mutation_kind(mutation)
                    instance_refs = (
                        instance_relation_refs(mutation)
                        if mutation_action in ('create', 'delete') else None
                    )
                    scope_role = scoped_mutation_role(
                        mutation, instance_refs
                    )
                    if scope_enabled and not scope_role:
                        continue
                    kind = (
                        'work_hour'
                        if parent_type == 'sthpw/work_hour'
                        else mutation_action
                    )
                    if allowed_kinds and kind not in allowed_kinds:
                        continue
                    if parent_type == 'sthpw/work_hour':
                        values = {}
                        for field, change in dict(
                                mutation.get('fieldValues') or {}).items():
                            value = (
                                change.get('before')
                                if mutation_action == 'delete'
                                else change.get('after')
                                or change.get('before')
                            )
                            if field:
                                values[field] = value
                        records.append({
                            'eventId': 'work_hour:{0}:{1}'.format(
                                transaction_data.get('code') or transaction_id,
                                mutation_index,
                            ),
                            'searchKey': '',
                            'kind': 'work_hour',
                            'title': 'Work hours',
                            'detail': str(values.get('description') or '')[:480],
                            'changes': [],
                            'actor': str(transaction_data.get('login') or ''),
                            'timestamp': str(
                                transaction_data.get('timestamp') or ''
                            ),
                            'itemCode': parent_code,
                            'itemTitle': '',
                            'project': project_code,
                            'process': str(values.get('process') or ''),
                            'context': str(values.get('process') or ''),
                            'version': '',
                            'statusBefore': '',
                            'statusAfter': '',
                            'workHourAction': mutation_action,
                            '_workHourValues': values,
                            '_workHourCode': parent_code,
                            '_parentType': '',
                            '_parentCode': '',
                            '_fallbackTitle': '',
                        })
                        continue
                    # Outside an object scope, dedicated sources provide
                    # richer task, note, snapshot, message and status events.
                    # A scoped history also needs system-record deletions and
                    # the individual non-status changes of its tasks.
                    scoped_system_type = (
                        parent_type
                        if scope_enabled and scope_role == 'system'
                        else ''
                    )
                    if (
                            parent_type.startswith('sthpw/')
                            and not scoped_system_type):
                        continue
                    if (
                            scoped_system_type in ('sthpw/note', 'sthpw/snapshot')
                            and kind == 'create'):
                        continue
                    if (
                            not scope_enabled and kind != 'delete'
                            and indexed_types
                            and parent_type not in indexed_types):
                        continue
                    if not parent_type or not parent_code:
                        continue
                    audited_targets.add((
                        str(transaction_data.get('code') or ''),
                        parent_type,
                        parent_code,
                    ))
                    visible_changes = list(mutation.get('changes') or [])
                    if scoped_system_type == 'sthpw/task':
                        visible_changes = [
                            change for change in visible_changes
                            if str(change.get('field') or '').lower()
                            != 'status'
                        ]
                        if kind == 'change' and not visible_changes:
                            continue
                    item_type = (
                        parent_type
                        if scope_enabled
                        and scope_role in ('child', 'system')
                        else ''
                    )
                    item_title = str(
                        mutation_title(mutation)
                        or mutation_value(mutation, 'process')
                        or mutation_value(mutation, 'context')
                        or mutation_value(mutation, 'description')
                        or mutation_value(mutation, 'note')
                        or parent_code
                    )
                    if instance_refs:
                        for (
                                endpoint_type, endpoint_column, endpoint_value
                        ) in instance_refs:
                            relation_refs.setdefault(
                                (endpoint_type, endpoint_column), set()
                            ).add(endpoint_value)
                    else:
                        resolved_parent_type = (
                            scope_search_type if item_type else parent_type
                        )
                        resolved_parent_code = (
                            scope_search_code if item_type else parent_code
                        )
                        parent_refs.setdefault(
                            resolved_parent_type, set()
                        ).add(resolved_parent_code)
                        if item_type:
                            parent_refs.setdefault(
                                item_type, set()
                            ).add(parent_code)
                    records.append({
                        'eventId': 'audit:{0}:{1}'.format(
                            transaction_data.get('code') or transaction_id,
                            mutation_index,
                        ),
                        'searchKey': '',
                        'kind': kind,
                        'title': (
                            'Created object' if kind == 'create'
                            else 'Deleted object' if kind == 'delete'
                            else 'Updated object'
                        ),
                        'detail': (
                            '' if instance_refs else
                            audit_detail(mutation, transaction_data)
                        ),
                        'changes': [] if instance_refs else visible_changes,
                        'actor': str(transaction_data.get('login') or ''),
                        'timestamp': str(
                            transaction_data.get('timestamp') or ''
                        ),
                        'itemCode': '' if instance_refs else parent_code,
                        'itemTitle': '' if instance_refs else item_title,
                        'itemType': item_type,
                        'project': project_code,
                        'process': (
                            mutation_value(mutation, 'process')
                            if scoped_system_type == 'sthpw/task' else ''
                        ),
                        'context': (
                            mutation_value(mutation, 'context')
                            or mutation_value(mutation, 'process')
                            if scoped_system_type == 'sthpw/task' else ''
                        ),
                        'version': '',
                        'statusBefore': '',
                        'statusAfter': '',
                        'taskCode': (
                            parent_code
                            if scoped_system_type == 'sthpw/task' else ''
                        ),
                        'statusAfter': (
                            mutation_value(mutation, 'status')
                            if scoped_system_type == 'sthpw/task' else ''
                        ),
                        '_parentType': (
                            '' if instance_refs else
                            scope_search_type if item_type else parent_type
                        ),
                        '_parentCode': (
                            '' if instance_refs else
                            scope_search_code if item_type else parent_code
                        ),
                        '_fallbackTitle': (
                            '' if instance_refs else mutation_title(mutation)
                        ),
                        '_relationFrom': (
                            instance_refs[0] if instance_refs else None
                        ),
                        '_relationTo': (
                            instance_refs[1] if instance_refs else None
                        ),
                        '_scopeItemType': item_type,
                        '_scopeItemCode': parent_code if item_type else '',
                        '_scopeItemTitle': item_title if item_type else '',
                        'relationAction': (
                            'unlink' if instance_refs and kind == 'delete'
                            else 'link' if instance_refs else ''
                        ),
                    })

        # change_timestamp is only a latest-change index.  Use it to fill gaps
        # where the transaction index did not yield a readable mutation.
        change_search = Search('sthpw/change_timestamp')
        if project_code:
            change_search.add_filter('project_code', project_code)
        if scope_enabled:
            change_search.add_filter('search_type', scope_search_type)
            change_search.add_filter('search_code', scope_search_code)
        if day:
            change_search.add_filter(
                'timestamp', day_start, op='>='
            )
            change_search.add_filter(
                'timestamp', day_end, op='<'
            )
        if page_cutoff:
            change_search.add_filter('timestamp', page_cutoff, op='>=')
        change_search.add_order_by('timestamp', direction='desc')
        change_search.set_limit(max((offset + limit) * 3, 75))
        requested_actors = set(logins or ([login] if login else []))
        for changed_item in change_search.get_sobjects():
            changed_data = changed_item.get_data()
            parent_type = clean_search_type(changed_data.get('search_type'))
            if not can_view(parent_type):
                continue
            parent_code = str(changed_data.get('search_code') or '')
            transaction_code = str(
                changed_data.get('transaction_code') or ''
            )
            changed_on = json_mapping(changed_data.get('changed_on'))
            changed_by = json_mapping(changed_data.get('changed_by'))
            visible_fields = [
                field for field in changed_on
                if str(field or '').lower() not in technical_columns
            ]
            latest_field = max(
                visible_fields,
                key=lambda field: str(changed_on.get(field) or ''),
                default='',
            )
            actor = str(changed_by.get(latest_field) or '')
            if not actor:
                actor = next((
                    str(value) for value in changed_by.values() if value
                ), '')
            if actor_is_excluded(actor):
                continue
            if requested_actors and actor not in requested_actors:
                continue
            if (
                    not parent_type or not parent_code
                    or parent_type.startswith('sthpw/')
                    or scope_enabled and (
                        parent_type != scope_search_type
                        or parent_code != scope_search_code
                    )
                    or (transaction_code, parent_type, parent_code)
                    in audited_targets):
                continue
            parent_refs.setdefault(parent_type, set()).add(parent_code)
            records.append({
                'eventId': 'change:{0}'.format(
                    changed_data.get('code') or changed_data.get('id') or
                    '{0}:{1}'.format(parent_type, parent_code)
                ),
                'searchKey': '',
                'kind': 'change',
                'title': 'Updated object',
                'detail': '',
                'changes': [{
                    'field': str(field).replace('_', ' '),
                    'before': '',
                    'after': '',
                    'valuesKnown': False,
                } for field in visible_fields[:4]],
                'actor': actor,
                'timestamp': str(
                    changed_data.get('timestamp')
                    or changed_on.get(latest_field) or ''
                ),
                'itemCode': parent_code,
                'itemTitle': parent_code,
                'project': str(
                    changed_data.get('project_code') or project_code
                ),
                'process': '',
                'context': '',
                'version': '',
                'statusBefore': '',
                'statusAfter': '',
                '_parentType': parent_type,
                '_parentCode': parent_code,
                '_fallbackTitle': '',
            })

    if exclude_login:
        records = [
            record for record in records
            if not actor_is_excluded(record.get('actor'))
        ]

    work_hour_records = [
        record for record in records
        if record.get('kind') == 'work_hour'
    ]
    if work_hour_records:
        work_hour_codes = list(set(
            str(record.get('_workHourCode') or '')
            for record in work_hour_records
            if record.get('_workHourCode')
        ))
        current_work_hours = {}
        if work_hour_codes:
            work_hour_search = Search('sthpw/work_hour')
            work_hour_search.add_filters('code', work_hour_codes)
            for work_hour in work_hour_search.get_sobjects():
                work_hour_data = work_hour.get_data()
                work_hour_data['__search_key__'] = str(
                    SearchKey.get_by_sobject(work_hour, use_id=False) or ''
                )
                current_work_hours[str(work_hour.get_code() or '')] = (
                    work_hour_data
                )

        task_codes = set()
        for record in work_hour_records:
            values = dict(record.pop('_workHourValues', {}) or {})
            current = current_work_hours.get(
                str(record.pop('_workHourCode', '') or ''), {}
            )
            # Transaction values describe the state at that event; the
            # current row only fills fields absent from an older mutation.
            values = dict(current, **values)
            category = str(values.get('category') or 'regular').lower()
            try:
                straight_time = float(values.get('straight_time') or 0)
            except (TypeError, ValueError):
                straight_time = 0.0
            try:
                over_time = float(values.get('over_time') or 0)
            except (TypeError, ValueError):
                over_time = 0.0
            hours = (
                over_time
                if category == 'overtime'
                else straight_time + over_time
            )
            task_code = str(values.get('task_code') or '')
            if task_code:
                task_codes.add(task_code)
            record.update({
                'searchKey': str(values.get('__search_key__') or ''),
                'detail': str(values.get('description') or record.get('detail') or '')[:480],
                'itemTitle': '{0:g} h'.format(hours),
                'process': str(values.get('process') or record.get('process') or ''),
                'context': str(values.get('process') or record.get('context') or ''),
                'taskCode': task_code,
                'hours': hours,
                'workDay': str(values.get('day') or ''),
                'workHourCategory': category,
                'workHourStatus': str(values.get('status') or ''),
                'workHourOwner': str(values.get('login') or ''),
            })

        tasks_by_code = {}
        if task_codes:
            work_task_search = Search('sthpw/task')
            work_task_search.add_filters('code', list(task_codes))
            tasks_by_code = {
                str(item.get_code() or ''): item.get_data()
                for item in work_task_search.get_sobjects()
            }
        for record in work_hour_records:
            task_data = tasks_by_code.get(
                str(record.get('taskCode') or ''), {}
            )
            parent_type = clean_search_type(task_data.get('search_type'))
            parent_code = str(task_data.get('search_code') or '')
            parent_id = str(task_data.get('search_id') or '')
            if (
                    scope_enabled and not parent_code
                    and parent_type == scope_search_type
                    and parent_id == scope_search_id):
                parent_code = scope_search_code
            record['process'] = str(
                task_data.get('process') or record.get('process') or ''
            )
            record['context'] = str(
                task_data.get('context') or record.get('context')
                or record.get('process') or ''
            )
            record['_parentType'] = parent_type
            record['_parentCode'] = parent_code
            if parent_type and parent_code:
                parent_refs.setdefault(parent_type, set()).add(parent_code)

    main_files = {}
    if snapshot_codes:
        file_search = Search('sthpw/file')
        file_search.add_filters('snapshot_code', list(snapshot_codes))
        file_search.add_filter('type', 'main')
        for file_item in file_search.get_sobjects():
            file_data = file_item.get_data()
            snapshot_code = str(file_data.get('snapshot_code') or '')
            file_name = str(file_data.get('file_name') or '')
            if snapshot_code and file_name:
                main_files.setdefault(snapshot_code, []).append(file_name)

    parents = {}
    for parent_type, codes in parent_refs.items():
        parent_query_type = parent_type
        if (
            project_code and not parent_type.startswith('sthpw/')
            and '?project=' not in parent_type
        ):
            parent_query_type = '{0}?project={1}'.format(
                parent_type, project_code
            )
        parent_search = Search(parent_query_type)
        parent_column = 'code' if 'code' in parent_search.get_columns() else 'id'
        parent_search.add_filters(parent_column, list(codes))
        for parent in parent_search.get_sobjects():
            parent_data = parent.get_data()
            parent_code = str(parent.get_code() or '')
            try:
                parent_title = str(parent.get_name() or '')
            except (AttributeError, TypeError):
                parent_title = ''
            parent_title = str(
                parent_title
                or parent_data.get('name')
                or parent_data.get('title')
                or parent_data.get('code')
                or parent_code
            )
            if parent_type == 'sthpw/message':
                raw_metadata = parent_data.get('metadata') or {}
                if isinstance(raw_metadata, dict):
                    parent_metadata = dict(raw_metadata)
                else:
                    try:
                        parent_metadata = json.loads(str(raw_metadata))
                    except (TypeError, ValueError):
                        parent_metadata = {}
                parent_title = str(
                    parent_metadata.get('title') or 'Conversation'
                )
            parents[(parent_type, parent_code)] = {
                'searchKey': str(SearchKey.get_by_sobject(
                    parent, use_id=False
                ) or ''),
                'title': parent_title,
                'type': parent_type,
                'pipelineCode': str(
                    parent_data.get('pipeline_code') or ''
                ),
            }

    relation_endpoints = {}
    for (endpoint_type, endpoint_column), values in relation_refs.items():
        endpoint_query_type = endpoint_type
        if (
            project_code and not endpoint_type.startswith('sthpw/')
            and '?project=' not in endpoint_type
        ):
            endpoint_query_type = '{0}?project={1}'.format(
                endpoint_type, project_code
            )
        endpoint_search = Search(endpoint_query_type)
        endpoint_search.add_filters(endpoint_column, list(values))
        for endpoint in endpoint_search.get_sobjects():
            endpoint_data = endpoint.get_data()
            endpoint_value = str(endpoint_data.get(endpoint_column) or '')
            if not endpoint_value and endpoint_column == 'code':
                endpoint_value = str(endpoint.get_code() or '')
            if not endpoint_value:
                continue
            try:
                endpoint_title = str(endpoint.get_name() or '')
            except (AttributeError, TypeError):
                endpoint_title = ''
            endpoint_title = str(
                endpoint_title
                or endpoint_data.get('name')
                or endpoint_data.get('title')
                or endpoint_data.get('code')
                or ''
            )
            relation_endpoints[(
                endpoint_type, endpoint_column, endpoint_value
            )] = {
                'searchKey': str(SearchKey.get_by_sobject(
                    endpoint, use_id=False
                ) or ''),
                'title': endpoint_title,
                'type': endpoint_type,
                'pipelineCode': str(
                    endpoint_data.get('pipeline_code') or ''
                ),
            }

    scoped_audit_task_codes = {
        str(record.get('taskCode') or '')
        for record in records
        if record.get('_scopeItemType') == 'sthpw/task'
        and record.get('taskCode')
    }
    if scoped_audit_task_codes:
        records = [
            record for record in records
            if not (
                record.get('kind') == 'task'
                and str(record.get('taskCode') or '')
                in scoped_audit_task_codes
            )
        ]

    resolved_records = []
    for record in records:
        relation_from_ref = record.pop('_relationFrom', None)
        relation_to_ref = record.pop('_relationTo', None)
        parent_type = record.pop('_parentType', '')
        parent_code = record.pop('_parentCode', '')
        item_type = record.pop('_scopeItemType', '')
        item_code = record.pop('_scopeItemCode', '')
        item_fallback_title = record.pop('_scopeItemTitle', '')
        record.pop('_taskId', None)
        fallback_title = record.pop('_fallbackTitle', '')
        if relation_from_ref and relation_to_ref:
            relation_from = relation_endpoints.get(
                tuple(relation_from_ref), {}
            )
            relation_to = relation_endpoints.get(
                tuple(relation_to_ref), {}
            )
            if scope_enabled and scope_endpoint_matches(relation_from_ref):
                relation_from, relation_to = relation_to, relation_from
                relation_from_ref, relation_to_ref = (
                    relation_to_ref, relation_from_ref
                )
            if scope_enabled and not scope_endpoint_matches(relation_to_ref):
                continue
            record.update({
                'searchKey': str(relation_from.get('searchKey') or ''),
                'itemTitle': str(relation_from.get('title') or ''),
                'itemType': str(
                    relation_from.get('type') or relation_from_ref[0]
                ),
                'targetSearchKey': str(
                    relation_to.get('searchKey') or ''
                ),
                'targetTitle': str(relation_to.get('title') or ''),
                'targetType': str(
                    relation_to.get('type') or relation_to_ref[0]
                ),
                'pipelineCode': str(
                    relation_to.get('pipelineCode') or ''
                ),
            })
            resolved_records.append(record)
            continue
        if scope_enabled and (
                clean_search_type(parent_type) != scope_search_type
                or str(parent_code or '') != scope_search_code):
            continue
        parent = parents.get((parent_type, parent_code), {})
        record['targetSearchKey'] = str(parent.get('searchKey') or '')
        record['targetTitle'] = str(
            parent.get('title') or fallback_title or parent_code
            or 'TACTIC object'
        )
        record['targetType'] = str(parent.get('type') or parent_type)
        record['pipelineCode'] = str(parent.get('pipelineCode') or '')
        if record.get('kind') == 'publication':
            record['itemTitle'] = ', '.join(sorted(
                main_files.get(str(record.get('itemCode') or ''), [])
            ))
        if item_type and item_code:
            item = parents.get((item_type, item_code), {})
            record['searchKey'] = str(item.get('searchKey') or '')
            record['itemTitle'] = str(
                (item_fallback_title or item.get('title') or item_code)
                if item_type.startswith('sthpw/') else
                (item.get('title') or item_fallback_title or item_code)
            )
            record['itemType'] = str(item.get('type') or item_type)
        resolved_records.append(record)

    records = [record for record in resolved_records if can_view(record.get('targetType')) and can_view(record.get('itemType'))]
    records.sort(key=lambda record: record.get('timestamp') or '', reverse=True)
    page = records[offset:offset + limit]
    if include_day_counts:
        return {
            'records': page,
            'dayCounts': [
                {'dateKey': day_key, 'count': day_counts[day_key]}
                for day_key in sorted(day_counts, reverse=True)
            ],
        }
    return page

