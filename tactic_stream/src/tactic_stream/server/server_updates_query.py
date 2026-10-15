"""Handler tactic_query.query_server_updates, EPL-1.0; native local TACTIC runtime."""
def query_server_updates(message_after='', activity_after='', project_code='',
                         limit=101, reaction_after='', include_activity=True,
                         include_reactions=True, include_presence=False,
                         presence_ttl=360, cache_after='',
                         include_cache_changes=False, include_messages=True,
                         heartbeat_presence=True):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import hashlib
    import json
    from datetime import datetime, timezone
    from json import loads
    from pyasm.search import Search, SearchKey

    security = Environment.get_security()

    def can_view(search_type):
        base = str(search_type or '').split('?', 1)[0]
        if not base:
            return True
        if not security.is_admin() and base in (
                'sthpw/login', 'sthpw/ticket', 'sthpw/login_group',
                'sthpw/login_in_group', 'sthpw/db_resource'):
            return False
        keys = [{'code': base}, {'code': base, 'project': project_code},
                {'code': '*'}, {'code': '*', 'project': project_code}]
        return security.check_access('search_type', keys, 'view',
            default='allow' if base.startswith('sthpw/') else 'deny')

    def visible(item):
        if not can_view(item.get_base_search_type()):
            return False
        parent_type = item.get_value('search_type', no_exception=True)
        if not can_view(parent_type):
            return False
        if str(parent_type or '').split('?', 1)[0] == 'sthpw/task':
            task = item.get_parent()
            if not task or not can_view(task.get_value('search_type')):
                return False
        if item.get_base_search_type() == 'sthpw/work_hour':
            task = Search.get_by_code('sthpw/task', item.get_value('task_code', no_exception=True))
            if not task or not can_view(task.get_value('search_type')):
                return False
        return True

    clock_started_utc = datetime.now(timezone.utc)
    chat_requested = bool(
        include_messages or include_reactions or include_presence
    )
    if chat_requested:
        from pyasm.search import SearchType

    def chat_search_type_available(search_type):
        try:
            sql_factory = getattr(
                SearchType, 'get_sql_by_search_type', None
            )
            if security.is_admin() and callable(sql_factory):
                sql = sql_factory(search_type)
                table_exists = getattr(sql, 'table_exists', None)
                table = str(search_type).rsplit('/', 1)[-1]
                if callable(table_exists) and not table_exists(table):
                    return False
            columns = set(SearchType.get_columns(search_type) or [])
        except AttributeError as error:
            if 'undefined' not in str(error).lower():
                raise
            return False
        return 'metadata' in columns

    messages_initialized = (
        all(
            chat_search_type_available(search_type)
            for search_type in ('sthpw/message', 'sthpw/message_log')
        )
        if chat_requested else True
    )
    if not messages_initialized:
        # First-run servers do not have Handler's structured chat metadata.
        # Keep activity/cache polling alive, but do not read or write chat and
        # presence records until an administrator confirms schema bootstrap.
        include_messages = False
        include_reactions = False
        include_presence = False
        heartbeat_presence = False

    include_messages = include_messages and can_view('sthpw/subscription') and can_view('sthpw/message_log')
    include_reactions = include_reactions and can_view('sthpw/change_timestamp') and can_view('sthpw/message_log')
    include_presence = include_presence and can_view('sthpw/message')

    def refresh_presence(ttl_seconds, publish_current):
        category = 'online_status'
        login = str(server.get_login() or '').strip()
        if not login:
            return []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        now_value = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        metadata = {
            'schemaVersion': 1,
            'login': login,
            'state': 'online',
            'lastSeen': now_value,
        }
        if publish_current:
            search = Search('sthpw/message')
            search.add_filter('category', category)
            search.add_filter('login', login)
            search.add_order_by('timestamp', direction='desc')
            search.set_limit(1)
            presence = search.get_sobject()
            if presence:
                server.update(
                    SearchKey.get_by_sobject(presence, use_id=False),
                    {
                        'message': now_value,
                        'status': 'online',
                        'metadata': metadata,
                    },
                    triggers=False,
                )
            else:
                digest = hashlib.sha1(login.encode('utf-8')).hexdigest()[:24]
                server.insert('sthpw/message', {
                    'code': 'ONLINE_STATUS_{0}'.format(digest.upper()),
                    'category': category,
                    'message': now_value,
                    'status': 'online',
                    'login': login,
                    'project_code': 'sthpw',
                }, metadata=metadata)
        all_search = Search('sthpw/message')
        all_search.add_filter('category', category)
        all_search.add_order_by('timestamp', direction='desc')
        records = []
        seen_logins = set()
        ttl_seconds = max(30, int(ttl_seconds or 360))
        for item in all_search.get_sobjects():
            item_login = str(item.get_value('login') or '').strip()
            if not item_login or item_login in seen_logins:
                continue
            seen_logins.add(item_login)
            raw_metadata = item.get_value('metadata') or {}
            if isinstance(raw_metadata, dict):
                item_metadata = dict(raw_metadata)
            else:
                try:
                    item_metadata = json.loads(raw_metadata)
                except (TypeError, ValueError):
                    item_metadata = {}
            last_seen = str(
                item_metadata.get('lastSeen')
                or item.get_value('message') or ''
            )
            try:
                parsed = datetime.strptime(last_seen, '%Y-%m-%dT%H:%M:%SZ')
                age = max(0, int((now - parsed).total_seconds()))
            except (TypeError, ValueError):
                age = ttl_seconds + 1
            records.append({
                'login': item_login,
                'lastSeen': last_seen,
                'online': age <= ttl_seconds,
            })
        return records

    def event_timestamp(value):
        try:
            parsed = loads(value)
        except (TypeError, ValueError):
            parsed = value
        if isinstance(parsed, dict):
            parsed = parsed.get('view') or parsed.get('value') or ''
        return str(parsed or '')

    def metadata_value(item):
        raw_metadata = item.get_value('metadata') or {}
        if isinstance(raw_metadata, dict):
            return dict(raw_metadata)
        try:
            return json.loads(raw_metadata)
        except (TypeError, ValueError):
            return {}

    def aggregate_delivery(delivery):
        recipients = dict((delivery or {}).get('recipients') or {})
        receipts = list(recipients.values())
        if receipts and all(item.get('readAt') for item in receipts):
            return 'read'
        if receipts and all(item.get('deliveredAt') for item in receipts):
            return 'delivered'
        return 'sent'

    def delivery_record(delivery):
        value = dict(delivery or {})
        recipients = dict(value.get('recipients') or {})
        receipts = list(recipients.values())
        return {
            'status': aggregate_delivery(value),
            'sentAt': str(value.get('sentAt') or ''),
            'recipientCount': len(receipts),
            'deliveredCount': len([
                item for item in receipts if item.get('deliveredAt')
            ]),
            'readCount': len([
                item for item in receipts if item.get('readAt')
            ]),
        }

    def cache_change_records():
        """Return compact invalidation records for the persistent cache."""
        cursor = str(cache_after or '')
        cursor_timestamp = cursor.split('|', 1)[0]
        records = []
        retired = []
        newest = cursor
        scopes = list(dict.fromkeys(
            value for value in (project_code, 'sthpw') if value
        ))

        def search_type_project(search_type):
            value = str(search_type or '')
            base, separator, query = value.partition('?')
            if separator:
                for field in query.split('&'):
                    key, equals, field_value = field.partition('=')
                    if equals and key == 'project':
                        return field_value
            if base.startswith('sthpw/'):
                return 'sthpw'
            return ''

        def append_rows(search_type, target, kind, newest_value):
            if not can_view(search_type):
                return newest_value
            for scope in scopes:
                search = Search(search_type)
                if kind == 'retire':
                    # retire_log has no project_code column. Project Search
                    # Types retain their project in ``?project=...`` while
                    # core records use the sthpw namespace. Filtering by the
                    # nonexistent column aborts the PostgreSQL transaction in
                    # TACTIC 4.9, so every later Search reports a misleading
                    # schema error for an unrelated table.
                    search.add_filter(
                        'search_type',
                        (
                            'sthpw/%' if scope == 'sthpw'
                            else '%project={0}%'.format(scope)
                        ),
                        op='like',
                    )
                else:
                    search.add_filter('project_code', scope)
                if cursor_timestamp:
                    search.add_filter(
                        'timestamp', cursor_timestamp, op='>='
                    )
                    search.add_order_by('timestamp')
                else:
                    search.add_order_by('timestamp', direction='desc')
                search.set_limit(limit)
                rows = search.get_sobjects()
                for item in rows:
                    data = item.get_data()
                    timestamp = event_timestamp(data.get('timestamp'))
                    raw_search_type = str(
                        data.get('search_type')
                        or data.get('search_type_code') or ''
                    )
                    changed_type = raw_search_type.split('?', 1)[0]
                    if not can_view(changed_type):
                        continue
                    if kind == 'retire' and changed_type in ('sthpw/note', 'sthpw/task', 'sthpw/work_hour') and not security.is_admin():
                        continue
                    record_project = str(
                        data.get('project_code')
                        or search_type_project(raw_search_type)
                    )
                    if kind == 'retire' and record_project != scope:
                        continue
                    changed_code = str(
                        data.get('search_code')
                        or data.get('code') or data.get('id') or ''
                    )
                    if kind != 'retire' and changed_type in ('sthpw/task', 'sthpw/note', 'sthpw/work_hour'):
                        changed = Search.get_by_code(changed_type, changed_code)
                        if not changed or not visible(changed):
                            continue
                    token = '|'.join((
                        timestamp, changed_type, changed_code, kind,
                    ))
                    if cursor and token <= cursor:
                        continue
                    newest_value = max(newest_value, token)
                    target.append({
                        'searchType': changed_type,
                        'searchCode': changed_code,
                        'projectCode': record_project or scope,
                        'timestamp': timestamp,
                    })
            return newest_value

        newest = append_rows(
            'sthpw/change_timestamp', records, 'change', newest
        )
        newest = append_rows(
            'sthpw/retire_log', retired, 'retire', newest
        )
        if not cursor:
            records = []
            retired = []
        return records, retired, newest

    current_login = str(server.get_login() or '')
    limit = int(limit or 101)
    if include_cache_changes:
        cache_changes, cache_retired, cache_cursor = cache_change_records()
    else:
        cache_changes, cache_retired, cache_cursor = [], [], str(
            cache_after or ''
        )
    message_poll_attempted = bool(include_messages)
    message_codes = []
    if message_poll_attempted:
        own_search = Search('sthpw/subscription')
        own_search.add_filter('login', current_login)
        own_search.add_filter('category', 'chat')
        message_codes = list(set(
            subscription.get_value('message_code')
            for subscription in own_search.get_sobjects()
            if subscription.get_value('message_code')
        ))
    messages = []
    if message_codes:
        search = Search('sthpw/message_log')
        search.add_filters('message_code', message_codes)
        search.add_filter('status', 'deleted', op='!=')
        if message_after:
            search.add_filter('timestamp', message_after, op='>')
            search.add_order_by('timestamp')
        else:
            search.add_order_by('timestamp', direction='desc')
        search.set_limit(limit)
        message_logs = search.get_sobjects()
        message_logs = [item for item in message_logs if item.get_code()]
        delivery_by_code = {}
        delivery_updates = {}
        delivered_at = datetime.now(timezone.utc).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        for item in message_logs:
            metadata = metadata_value(item)
            delivery = dict(metadata.get('delivery') or {})
            recipients = dict(delivery.get('recipients') or {})
            receipt = dict(recipients.get(str(current_login or '')) or {})
            sender = str(
                delivery.get('sender') or item.get_value('login') or ''
            )
            if (
                    security.is_admin() and sender != current_login and receipt
                    and not receipt.get('deliveredAt')):
                receipt['deliveredAt'] = delivered_at
                recipients[current_login] = receipt
                delivery['recipients'] = recipients
                metadata['delivery'] = delivery
                delivery_updates[SearchKey.get_by_sobject(
                    item, use_id=False
                )] = {
                    'metadata': metadata,
                    'status': aggregate_delivery(delivery),
                    'project_code': 'sthpw',
                }
            delivery_by_code[str(item.get_code() or '')] = delivery_record(
                delivery
            )
        if delivery_updates and security.is_admin():
            server.update_multiple(data=delivery_updates, triggers=True)
        attachment_counts = {}
        message_log_ids = {
            item.get_id(): item.get_code() for item in message_logs
            if item.get_id() and item.get_code()
        }
        if message_log_ids:
            connection_search = Search('sthpw/connection')
            connection_search.add_filter('context', 'chat_attachment')
            connection_search.add_filter(
                'dst_search_type', 'sthpw/message_log'
            )
            connection_search.add_filters(
                'dst_search_id', list(message_log_ids)
            )
            for connection in connection_search.get_sobjects():
                code = message_log_ids.get(
                    connection.get_value('dst_search_id')
                )
                if code:
                    attachment_counts[code] = attachment_counts.get(code, 0) + 1
        for item in message_logs:
            data = item.get_data()
            data['__search_key__'] = SearchKey.get_by_sobject(
                item, use_id=False
            )
            data['__event_timestamp__'] = event_timestamp(
                data.get('timestamp')
            )
            data['__attachment_count__'] = attachment_counts.get(
                item.get_code(), 0
            )
            data['__delivery__'] = delivery_by_code.get(
                str(item.get_code() or ''), {}
            )
            if data['__delivery__']:
                data['status'] = data['__delivery__'].get('status') or 'sent'
            messages.append(data)

    reactions = []
    reaction_cursor = str(reaction_after or '')
    if message_codes and include_reactions:
        change_search = Search('sthpw/change_timestamp')
        change_search.add_filter('search_type', 'sthpw/message_log')
        if reaction_after:
            change_search.add_filter(
                'timestamp', str(reaction_after)[:19], op='>='
            )
            change_search.add_order_by('timestamp')
        else:
            change_search.add_order_by('timestamp', direction='desc')
        change_search.set_limit(limit)
        changes = change_search.get_sobjects()
        changed_codes = []
        event_by_code = {}
        for change in changes:
            code = str(change.get_value('search_code') or '')
            if not code:
                continue
            timestamp = event_timestamp(change.get_value('timestamp'))
            changed_codes.append(code)
            if timestamp > event_by_code.get(code, ''):
                event_by_code[code] = timestamp
            if timestamp > reaction_cursor:
                reaction_cursor = timestamp
        if changed_codes:
            changed_search = Search('sthpw/message_log')
            changed_search.add_filters('code', list(set(changed_codes)))
            for message_log in changed_search.get_sobjects():
                message_code = str(message_log.get_value('message_code') or '')
                if (
                    message_code not in message_codes
                    or message_log.get_value('status', no_exception=True) == 'deleted'
                ):
                    continue
                raw_metadata = message_log.get_value('metadata') or {}
                if isinstance(raw_metadata, dict):
                    metadata = dict(raw_metadata)
                else:
                    try:
                        metadata = loads(raw_metadata)
                    except (TypeError, ValueError):
                        metadata = {}
                reactions.append({
                    'messageId': SearchKey.get_by_sobject(
                        message_log, use_id=False
                    ),
                    'messageCode': message_code,
                    'reactions': dict(metadata.get('reactions') or {}),
                    'delivery': delivery_record(
                        metadata.get('delivery') or {}
                    ),
                    'status': aggregate_delivery(
                        metadata.get('delivery') or {}
                    ),
                    'reactionUpdatedAt': str(
                        metadata.get('reactionUpdatedAt') or ''
                    ),
                    '__event_timestamp__': event_by_code.get(
                        str(message_log.get_code() or ''), ''
                    ),
                })

    activity = []
    if project_code and include_activity:
        sources = (
            ('sthpw/status_log', 'status'),
            ('sthpw/snapshot', 'publication'),
            ('sthpw/note', 'note'),
            ('sthpw/task', 'task'),
            ('sthpw/change_timestamp', 'change'),
        )
        for search_type, kind in sources:
            if not can_view(search_type):
                continue
            search = Search(search_type)
            search.add_filter('project_code', project_code)
            timestamp_column = 'timestamp'
            if activity_after:
                search.add_filter(timestamp_column, activity_after, op='>')
                search.add_order_by(timestamp_column)
            else:
                search.add_order_by(timestamp_column, direction='desc')
            search.set_limit(limit)
            source_items = search.get_sobjects()
            for item in source_items:
                if not visible(item):
                    continue
                data = item.get_data()
                if (
                    kind == 'change'
                    and str(data.get('search_type') or '').split('?')[0]
                    == 'sthpw/task'
                ):
                    continue
                data['__search_key__'] = SearchKey.get_by_sobject(
                    item, use_id=False
                )
                data['__kind__'] = kind
                data['__event_timestamp__'] = event_timestamp(
                    data.get(timestamp_column)
                    or item.get_value(timestamp_column, no_exception=True)
                )
                activity.append(data)
        work_hour_changes = [
            item for item in activity
            if item.get('__kind__') == 'change'
            and str(item.get('search_type') or '').split('?', 1)[0]
            == 'sthpw/work_hour'
            and item.get('search_code')
        ]
        if work_hour_changes:
            work_hour_codes = list(set(
                str(item.get('search_code') or '')
                for item in work_hour_changes
            ))
            work_hour_search = Search('sthpw/work_hour')
            work_hour_search.add_filters('code', work_hour_codes)
            work_hours_by_code = {
                str(item.get_code() or ''): item
                for item in work_hour_search.get_sobjects()
            }
            task_codes = list(set(
                str(item.get_value('task_code') or '')
                for item in work_hours_by_code.values()
                if item.get_value('task_code')
            ))
            task_contexts = {}
            if task_codes:
                work_task_search = Search('sthpw/task')
                work_task_search.add_filters('code', task_codes)
                for task in work_task_search.get_sobjects():
                    task_data = task.get_data()
                    parent = task.get_parent()
                    task_contexts[str(task.get_code() or '')] = {
                        'process': str(task_data.get('process') or ''),
                        'context': str(
                            task_data.get('context')
                            or task_data.get('process') or ''
                        ),
                        'targetSearchKey': str(
                            SearchKey.get_by_sobject(parent, use_id=False)
                            if parent else ''
                        ),
                        'targetTitle': str((
                            parent.get_name()
                            or parent.get_value('name', no_exception=True)
                            or parent.get_value('title', no_exception=True)
                            or parent.get_code() or ''
                        ) if parent else ''),
                        'targetType': str(
                            task_data.get('search_type') or ''
                        ).split('?', 1)[0],
                    }
            retained_activity = []
            for info in activity:
                if info not in work_hour_changes:
                    retained_activity.append(info)
                    continue
                code = str(info.get('search_code') or '')
                work_hour = work_hours_by_code.get(code)
                if not work_hour:
                    continue
                event_time = str(info.get('__event_timestamp__') or '')
                changed_by = info.get('changed_by') or {}
                if not isinstance(changed_by, dict):
                    try:
                        changed_by = loads(changed_by)
                    except (TypeError, ValueError):
                        changed_by = {}
                actor = next((
                    str(value) for value in changed_by.values() if value
                ), '') if isinstance(changed_by, dict) else ''
                data = work_hour.get_data()
                task_code = str(data.get('task_code') or '')
                data.update(task_contexts.get(task_code, {}))
                data['__search_key__'] = str(
                    SearchKey.get_by_sobject(work_hour, use_id=False) or ''
                )
                data['__kind__'] = 'work_hour'
                data['__event_timestamp__'] = event_time
                data['__actor__'] = actor
                data['__work_hour_action__'] = 'change'
                retained_activity.append(data)
            activity = retained_activity
        publication_rows = [
            item for item in activity
            if item.get('__kind__') == 'publication' and item.get('code')
        ]
        if publication_rows:
            publication_by_code = dict(
                (str(item.get('code')), item) for item in publication_rows
            )
            file_search = Search('sthpw/file')
            file_search.add_filters(
                'snapshot_code', list(publication_by_code.keys())
            )
            file_search.add_filter('type', 'main')
            for file_item in file_search.get_sobjects():
                file_data = file_item.get_data()
                publication = publication_by_code.get(
                    str(file_data.get('snapshot_code') or '')
                )
                file_name = str(file_data.get('file_name') or '')
                if publication is not None and file_name:
                    publication.setdefault('__main_files__', []).append(
                        file_name
                    )
    activity.sort(key=lambda item: item.get('__event_timestamp__') or '')
    activity_page = activity[:limit] if activity_after else activity[-limit:]
    presence = refresh_presence(
        presence_ttl, bool(heartbeat_presence)
    ) if include_presence else []
    clock_ended_utc = datetime.now(timezone.utc)
    return {
        'messages': messages,
        'reactions': reactions,
        'reactionCursor': reaction_cursor,
        'activity': activity_page,
        'presence': presence,
        'cacheChanges': cache_changes,
        'cacheRetired': cache_retired,
        'cacheCursor': cache_cursor,
        'messagePollAttempted': message_poll_attempted,
        'messagesInitialized': messages_initialized,
        'serverClock': {
            'utcStarted': clock_started_utc.strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ'
            ),
            'utcEnded': clock_ended_utc.strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ'
            ),
        },
    }
