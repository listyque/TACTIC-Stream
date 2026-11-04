"""Handler tactic_query chat procedures, EPL-1.0; see LICENSE.HANDLER.

Native SDK binding, read-only repair guards, preserved conversation owner and
NULL-status forward fix and native compressed metadata reads are the web adaptations. Storage remains TACTIC.
"""
from pyasm.common import Environment
from pyasm.search import Search, SearchKey


def _can_edit(search_type):
    return Environment.get_security().check_access('search_type',
        [{'code': search_type}, {'code': search_type, 'project': 'sthpw'},
         {'code': '*'}, {'code': '*', 'project': 'sthpw'}], 'edit', default='deny')


def _log_chat_message(server, message_code, *args, **kwargs):
    # log_message tracks the latest actor; a conversation must retain its creator.
    conversation = Search.get_by_code('sthpw/message', message_code)
    owner = {field: conversation.get_value(field) for field in ('login', 'timestamp')}
    server.log_message(message_code, *args, **kwargs)
    server.update(SearchKey.get_by_sobject(conversation, use_id=False), owner, triggers=False)


def query_chat_conversations():
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    import re
    from pyasm.biz import Snapshot
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey, SearchType

    current_login = str(server.get_login() or '')
    administrator = bool(Environment.get_security().is_admin())
    required_schema = (
        ('sthpw/message', 'metadata'),
        ('sthpw/message_log', 'metadata'),
    )

    def available_columns(search_type):
        try:
            sql_factory = getattr(
                SearchType, 'get_sql_by_search_type', None
            )
            if callable(sql_factory):
                sql = sql_factory(search_type)
                table_exists = getattr(sql, 'table_exists', None)
                table = str(search_type).rsplit('/', 1)[-1]
                if callable(table_exists) and not table_exists(table):
                    return set()
            return set(SearchType.get_columns(search_type) or [])
        except AttributeError as error:
            if 'undefined' not in str(error).lower():
                raise
            return set()

    missing_columns = []
    for search_type, column in required_schema:
        if column not in available_columns(search_type):
            missing_columns.append({
                'searchType': search_type,
                'column': column,
                'dataType': 'text',
            })
    if missing_columns:
        return json.dumps({
            'initialized': False,
            'canInitialize': administrator,
            'missingColumns': missing_columns,
            'conversations': [],
            'canCreateGroup': False,
            'canDeleteMessages': False,
        }, separators=(',', ':'))
    if administrator or str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    subscription_search = Search('sthpw/subscription')
    subscription_search.add_filter('login', current_login)
    subscription_search.add_filter('category', 'chat')
    own_subscriptions = subscription_search.get_sobjects()
    message_codes = list(set(
        subscription.get_value('message_code')
        for subscription in own_subscriptions
        if subscription.get_value('message_code')
    ))
    if not message_codes:
        return json.dumps({
            'initialized': True,
            'canInitialize': administrator,
            'conversations': [],
            'canCreateGroup': bool(privileged),
            'canDeleteMessages': bool(privileged),
        }, separators=(',', ':'))

    message_search = Search('sthpw/message')
    message_search.add_filters('code', message_codes)
    message_search.add_filter('category', 'chat')
    messages = dict(
        (message.get_code(), message)
        for message in message_search.get_sobjects()
    )
    active_codes = [
        code for code, message in messages.items()
        if message.get_value('status', no_exception=True) != 'deleted'
    ]
    if not active_codes:
        return json.dumps({
            'initialized': True,
            'canInitialize': administrator,
            'conversations': [],
            'canCreateGroup': bool(privileged),
            'canDeleteMessages': bool(privileged),
        }, separators=(',', ':'))

    members_search = Search('sthpw/subscription')
    members_search.add_filters('message_code', active_codes)
    members_search.add_filter('category', 'chat')
    members = members_search.get_sobjects()
    members_by_code = {}
    login_codes = set()
    for member in members:
        code = member.get_value('message_code')
        login = member.get_value('login')
        members_by_code.setdefault(code, []).append(member)
        if login:
            login_codes.add(login)

    display_names = {}
    if login_codes:
        login_search = Search('sthpw/login')
        login_search.add_filters('login', list(login_codes))
        for login in login_search.get_sobjects():
            code = login.get_value('login')
            display_names[code] = (
                login.get_value('display_name', no_exception=True) or code
            )

    metadata_by_code = {}
    for code, message in messages.items():
        raw_metadata = message.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            value = dict(raw_metadata)
        else:
            try:
                value = json.loads(raw_metadata)
            except (TypeError, ValueError):
                value = {}
        metadata_by_code[code] = value

    own_by_code = dict(
        (subscription.get_value('message_code'), subscription)
        for subscription in own_subscriptions
    )

    summaries_by_code = {}
    missing_summary_codes = []
    for code in active_codes:
        summary = dict((metadata_by_code.get(code) or {}).get('summary') or {})
        if summary:
            summaries_by_code[code] = summary
        else:
            missing_summary_codes.append(code)

    missing_logs_by_code = {}
    if missing_summary_codes:
        log_search = Search('sthpw/message_log')
        log_search.add_filters('message_code', missing_summary_codes)
        log_search.add_filter('status', 'deleted', op='!=')
        log_search.add_order_by('timestamp', direction='desc')
        log_search.add_order_by('id', direction='desc')
        for message_log in log_search.get_sobjects():
            missing_logs_by_code.setdefault(
                message_log.get_value('message_code'), []
            ).append(message_log)

    attachments_by_code = {}
    missing_log_ids = [
        item.get_id()
        for values in missing_logs_by_code.values()
        for item in values if item.get_id()
    ]
    if missing_log_ids:
        connection_search = Search('sthpw/connection')
        connection_search.add_filter('context', 'chat_attachment')
        connection_search.add_filter('dst_search_type', 'sthpw/message_log')
        connection_search.add_filters('dst_search_id', missing_log_ids)
        log_to_chat = dict(
            (item.get_id(), item.get_value('message_code'))
            for values in missing_logs_by_code.values() for item in values
        )
        for connection in connection_search.get_sobjects():
            chat_code = log_to_chat.get(connection.get_value('dst_search_id'))
            if chat_code:
                attachments_by_code[chat_code] = (
                    attachments_by_code.get(chat_code, 0) + 1
                )

    for code in missing_summary_codes:
        values = missing_logs_by_code.get(code, [])
        latest = values[0] if values else None
        latest_metadata = {}
        if latest:
            raw_metadata = latest.get_json_value('metadata', default={}) or {}
            if isinstance(raw_metadata, dict):
                latest_metadata = dict(raw_metadata)
            else:
                try:
                    latest_metadata = json.loads(raw_metadata)
                except (TypeError, ValueError):
                    latest_metadata = {}
        summary = {
            'latestCode': str(latest.get_code() or '') if latest else '',
            'latestBody': str(latest.get_value('message') or '') if latest else '',
            'latestTimestamp': str(latest.get_value('timestamp') or '') if latest else '',
            'latestSender': str(latest.get_value('login') or '') if latest else '',
            'latestForwarded': bool(latest_metadata.get('forwardedFrom')),
            'messageCount': len(values),
            'attachmentCount': attachments_by_code.get(code, 0),
        }
        summaries_by_code[code] = summary
        message = messages.get(code)
        if message and _can_edit('sthpw/message'):
            metadata = dict(metadata_by_code.get(code) or {})
            metadata['summary'] = summary
            server.update(
                SearchKey.get_by_sobject(message, use_id=False),
                {'metadata': metadata}, triggers=False,
            )
            metadata_by_code[code] = metadata

    unread_by_code = {}
    mentions_by_code = {}
    members_count = dict(
        (code, len(members_by_code.get(code, []))) for code in active_codes
    )
    unread_candidate_codes = []
    candidate_cleared = []
    unread_logs = []
    for code in active_codes:
        own = own_by_code.get(code)
        if not own or members_count.get(code, 0) <= 1:
            continue
        summary = summaries_by_code.get(code) or {}
        if int(summary.get('messageCount') or 0) <= 0:
            continue
        cleared = str(
            own.get_value('last_cleared', no_exception=True) or ''
        )[:19]
        latest_ts = str(summary.get('latestTimestamp') or '')[:19]
        if cleared and latest_ts and latest_ts <= cleared:
            continue
        if code in missing_logs_by_code:
            unread_logs.extend(missing_logs_by_code[code])
        else:
            unread_candidate_codes.append(code)
            candidate_cleared.append(cleared)
    if unread_candidate_codes:
        unread_search = Search('sthpw/message_log')
        unread_search.add_filters('message_code', unread_candidate_codes)
        unread_search.add_filter('status', 'deleted', op='!=')
        unread_search.add_filter('login', current_login, op='!=')
        if candidate_cleared and all(candidate_cleared):
            unread_search.add_filter('timestamp', min(candidate_cleared), op='>')
        unread_logs.extend(unread_search.get_sobjects())
    mention_pattern = re.compile(
        r'(^|[^A-Za-z0-9_.@-])@{0}($|[^A-Za-z0-9_.-])'.format(
            re.escape(str(current_login or ''))
        ), re.IGNORECASE,
    )
    for message_log in unread_logs:
        code = message_log.get_value('message_code')
        own = own_by_code.get(code)
        if not own or message_log.get_value('login') == current_login:
            continue
        timestamp = str(message_log.get_value('timestamp') or '')[:19]
        cleared = str(own.get_value(
            'last_cleared', no_exception=True
        ) or '')[:19]
        if cleared and timestamp <= cleared:
            continue
        unread_by_code[code] = unread_by_code.get(code, 0) + 1
        if members_count.get(code, 0) > 2 and mention_pattern.search(
                str(message_log.get_value('message') or '')):
            mentions_by_code[code] = mentions_by_code.get(code, 0) + 1

    previews_by_code = {}
    snapshot_search = Search('sthpw/snapshot')
    snapshot_search.add_filter('search_type', 'sthpw/message')
    snapshot_search.add_filters('search_code', active_codes)
    snapshot_search.add_filter('process', 'icon')
    snapshot_search.add_order_by('timestamp', direction='desc')
    preview_snapshots = snapshot_search.get_sobjects()
    preview_files = Snapshot.get_files_dict_by_snapshots(preview_snapshots)
    for snapshot in preview_snapshots:
        code = snapshot.get_value('search_code')
        if code in previews_by_code:
            continue
        snapshot_data = snapshot.get_data()
        snapshot_data['__files__'] = [
            file_object.get_data()
            for file_object in (preview_files.get(snapshot.get_code()) or [])
        ]
        previews_by_code[code] = snapshot_data

    conversations = []
    for code in active_codes:
        own = own_by_code.get(code)
        if not own:
            continue
        recipients = sorted(set(
            member.get_value('login')
            for member in members_by_code.get(code, [])
            if member.get_value('login') not in (None, '', current_login)
        ))
        recipient_names = [
            display_names.get(login, login) for login in recipients
        ]
        generated_title = ', '.join(recipient_names) or display_names.get(
            current_login, current_login
        )
        last_cleared = own.get_value('last_cleared', no_exception=True)
        unread = unread_by_code.get(code, 0)
        mention_count = mentions_by_code.get(code, 0)
        summary = summaries_by_code.get(code) or {}
        participants = len(recipients) + 1
        message = messages[code]
        custom_title = (
            (metadata_by_code.get(code) or {}).get('title') or ''
        )
        owner = message.get_value('login', no_exception=True) or ''
        personal_notes = participants == 1
        conversations.append({
            'conversationId': code,
            'title': 'Notes' if personal_notes else custom_title or generated_title,
            'customTitle': bool(custom_title) and not personal_notes,
            'recipients': recipients,
            'recipientNames': recipient_names,
            'status': message.get_value('status', no_exception=True) or '',
            'lastCleared': str(last_cleared or ''),
            'unread': unread,
            'mentionCount': mention_count,
            'lastMessage': (
                'Forwarded message'
                if summary.get('latestForwarded')
                else str(summary.get('latestBody') or '')
            ),
            'lastTimestamp': str(summary.get('latestTimestamp') or ''),
            'lastSender': str(summary.get('latestSender') or ''),
            'participantCount': participants,
            'messageCount': int(summary.get('messageCount') or 0),
            'attachmentCount': int(summary.get('attachmentCount') or 0),
            'createdBy': owner,
            'createdAt': str(message.get_value('timestamp', no_exception=True) or ''),
            'canManage': bool(privileged or owner == current_login),
            'canRename': bool(not personal_notes and (privileged or owner == current_login)),
            'canDelete': bool(privileged and not personal_notes),
            'canAddMembers': bool(privileged and not personal_notes),
            'canClearPersonal': bool(personal_notes),
            'isPersonalNotes': bool(personal_notes),
            'preview': previews_by_code.get(code) or {},
        })
    conversations.sort(
        key=lambda record: (record['lastTimestamp'], record['title']),
        reverse=True,
    )
    return json.dumps(
        {
            'initialized': True,
            'canInitialize': administrator,
            'conversations': conversations,
            'canCreateGroup': bool(privileged),
            'canDeleteMessages': bool(privileged),
        }, separators=(',', ':')
    )


def create_chat_conversation(recipients, title=''):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    import uuid
    from pyasm.search import Search

    current_login = server.get_login()
    if str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    participants = set(
        str(login).strip() for login in (recipients or []) if str(login).strip()
    )
    participants.add(current_login)
    if len(participants) > 2 and not privileged:
        raise RuntimeError(
            'Only administrators and supervisors can create group chats'
        )
    if isinstance(title, dict):
        title = title.get('value')
    title = (title or '').strip()
    if len(participants) > 2 and not title:
        raise ValueError('Group chat title is required')
    login_search = Search('sthpw/login')
    login_search.add_filters('login', list(participants))
    existing_logins = set(
        login.get_value('login') for login in login_search.get_sobjects()
    )
    missing = sorted(participants - existing_logins)
    if missing:
        raise ValueError('Unknown TACTIC login: {0}'.format(', '.join(missing)))

    own_search = Search('sthpw/subscription')
    own_search.add_filter('login', current_login)
    own_search.add_filter('category', 'chat')
    own_codes = list(set(
        subscription.get_value('message_code')
        for subscription in own_search.get_sobjects()
        if subscription.get_value('message_code')
    ))
    if own_codes:
        message_search = Search('sthpw/message')
        message_search.add_filters('code', own_codes)
        message_search.add_filter('category', 'chat')
        valid_codes = set(
            message.get_code() for message in message_search.get_sobjects()
            if message.get_value('status', no_exception=True) != 'deleted'
        )
        member_search = Search('sthpw/subscription')
        member_search.add_filters('message_code', list(valid_codes))
        member_search.add_filter('category', 'chat')
        grouped = {}
        for subscription in member_search.get_sobjects():
            grouped.setdefault(
                subscription.get_value('message_code'), set()
            ).add(subscription.get_value('login'))
        for code, members in grouped.items():
            if members == participants:
                return json.dumps(
                    {'conversationId': code, 'created': False},
                    separators=(',', ':'),
                )

    code = 'CHAT_{0}'.format(uuid.uuid4().hex.upper())
    metadata = {
        'summary': {
            'latestCode': '',
            'latestBody': '',
            'latestTimestamp': '',
            'latestSender': '',
            'latestForwarded': False,
            'messageCount': 0,
            'attachmentCount': 0,
        },
    }
    if title:
        metadata['title'] = title
    server.insert('sthpw/message', {
        'code': code,
        'category': 'chat',
        'login': current_login,
        'project_code': 'sthpw',
        'message': '',
        'metadata': metadata,
    }, triggers=True)
    for login in sorted(participants):
        server.insert('sthpw/subscription', {
            'message_code': code,
            'login': login,
            'project_code': 'sthpw',
            'category': 'chat',
        }, triggers=True)
    return json.dumps(
        {'conversationId': code, 'created': True}, separators=(',', ':')
    )


def update_chat_conversation(message_code, title):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')
    message_search = Search('sthpw/message')
    message_search.add_filter('code', message_code)
    message_search.add_filter('category', 'chat')
    message = message_search.get_sobject()
    if not message or message.get_value('status', no_exception=True) == 'deleted':
        raise RuntimeError('Chat does not exist')
    if str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    owner = message.get_value('login', no_exception=True) or ''
    if owner != current_login and not privileged:
        raise RuntimeError('Only the chat owner or a supervisor can rename it')
    members = Search('sthpw/subscription')
    members.add_filter('message_code', message_code)
    members.add_filter('category', 'chat')
    if len(members.get_sobjects()) == 1:
        raise RuntimeError('The personal notes chat has a fixed title')
    if isinstance(title, dict):
        title = title.get('value')
    title = (title or '').strip()
    if not title:
        raise ValueError('Chat title cannot be empty')
    raw_metadata = message.get_json_value('metadata', default={}) or {}
    if isinstance(raw_metadata, dict):
        values = dict(raw_metadata)
    else:
        try:
            values = json.loads(raw_metadata)
        except (TypeError, ValueError):
            values = {}
    values['title'] = title
    server.update(
        SearchKey.get_by_sobject(message, use_id=False),
        {'metadata': values},
        triggers=True,
    )
    return json.dumps({'title': title}, separators=(',', ':'))


def add_chat_members(message_code, recipients, replace=False):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    member_access = Search('sthpw/subscription')
    member_access.add_filter('message_code', message_code)
    member_access.add_filter('login', current_login)
    member_access.add_filter('category', 'chat')
    if not member_access.get_sobject():
        raise RuntimeError('The current login is not a chat participant')
    message_search = Search('sthpw/message')
    message_search.add_filter('code', message_code)
    message_search.add_filter('category', 'chat')
    message = message_search.get_sobject()
    if not message or message.get_value('status', no_exception=True) == 'deleted':
        raise RuntimeError('Chat does not exist')
    all_members = Search('sthpw/subscription')
    all_members.add_filter('message_code', message_code)
    all_members.add_filter('category', 'chat')
    if len(all_members.get_sobjects()) == 1:
        raise RuntimeError('Members cannot be added to the personal notes chat')
    if str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    if not privileged:
        raise RuntimeError(
            'Only administrators and supervisors can add chat members'
        )
    recipients = set(
        str(login).strip() for login in (recipients or []) if str(login).strip()
    )
    recipients.discard(current_login)
    if replace and not recipients:
        raise ValueError('A group chat must have at least one other member')
    if not recipients:
        return json.dumps({'added': []}, separators=(',', ':'))
    login_search = Search('sthpw/login')
    login_search.add_filters('login', list(recipients))
    existing_logins = set(
        login.get_value('login') for login in login_search.get_sobjects()
    )
    missing = sorted(recipients - existing_logins)
    if missing:
        raise ValueError('Unknown TACTIC login: {0}'.format(', '.join(missing)))
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('category', 'chat')
    existing = set(
        item.get_value('login') for item in member_search.get_sobjects()
    )
    added = sorted(recipients - existing)
    for login in added:
        server.insert('sthpw/subscription', {
            'message_code': message_code,
            'login': login,
            'project_code': 'sthpw',
            'category': 'chat',
        }, triggers=True)
    removed = []
    if replace:
        removed = sorted(existing - recipients - set([current_login]))
        for subscription in member_search.get_sobjects():
            if subscription.get_value('login') in removed:
                server.delete_sobject(
                    SearchKey.get_by_sobject(subscription, use_id=False)
                )
    return json.dumps(
        {'added': added, 'removed': removed}, separators=(',', ':')
    )


def delete_chat_conversation(message_code):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    if str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    if not privileged:
        raise RuntimeError('Only administrators and supervisors can delete chats')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')
    message_search = Search('sthpw/message')
    message_search.add_filter('code', message_code)
    message_search.add_filter('category', 'chat')
    message = message_search.get_sobject()
    if not message or message.get_value('status', no_exception=True) == 'deleted':
        raise RuntimeError('Chat does not exist')
    all_members = Search('sthpw/subscription')
    all_members.add_filter('message_code', message_code)
    all_members.add_filter('category', 'chat')
    if len(all_members.get_sobjects()) == 1:
        raise RuntimeError('The personal notes chat cannot be deleted')
    server.update(
        SearchKey.get_by_sobject(message, use_id=False),
        {'status': 'deleted'},
        triggers=True,
    )
    return json.dumps({'deleted': True}, separators=(',', ':'))


def clear_personal_chat(message_code):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('category', 'chat')
    members = member_search.get_sobjects()
    member_logins = set(item.get_value('login') for item in members)
    if member_logins != set([current_login]):
        raise RuntimeError('Only a personal notes chat can be cleared')
    log_search = Search('sthpw/message_log')
    log_search.add_filter('message_code', message_code)
    cleared = 0
    for message_log in log_search.get_sobjects():
        if message_log.get_value('status', no_exception=True) == 'deleted':
            continue
        server.update(
            SearchKey.get_by_sobject(message_log, use_id=False),
            {'status': 'deleted'},
            triggers=True,
        )
        cleared += 1
    message_search = Search('sthpw/message')
    message_search.add_filter('code', message_code)
    message_search.add_filter('category', 'chat')
    conversation = message_search.get_sobject()
    if conversation:
        raw_metadata = conversation.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            metadata = dict(raw_metadata)
        else:
            try:
                metadata = json.loads(raw_metadata)
            except (TypeError, ValueError):
                metadata = {}
        metadata['summary'] = {
            'latestCode': '',
            'latestBody': '',
            'latestTimestamp': '',
            'latestSender': '',
            'latestForwarded': False,
            'messageCount': 0,
            'attachmentCount': 0,
        }
        server.update(
            SearchKey.get_by_sobject(conversation, use_id=False),
            {'metadata': metadata}, triggers=False,
        )
    return json.dumps({'cleared': cleared}, separators=(',', ':'))


def delete_chat_message(message_log_code):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import datetime
    import json
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    message_log_ref = str(message_log_code or '')
    message_log = None
    if message_log_ref.startswith('sthpw/message_log'):
        search_type = server.split_search_key(message_log_ref)[0]
        if search_type == 'sthpw/message_log':
            message_log = Search.get_by_search_key(message_log_ref)
    else:
        log_search = Search('sthpw/message_log')
        log_search.add_filter('code', message_log_ref)
        message_log = log_search.get_sobject()
    if not message_log:
        raise RuntimeError('Message does not exist')
    if not message_log.get_code():
        raise RuntimeError('TACTIC message log has no code')
    message_code = message_log.get_value('message_code')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('category', 'chat')
    member_logins = set(
        item.get_value('login') for item in member_search.get_sobjects()
    )
    if current_login not in member_logins:
        raise RuntimeError('The current login is not a chat participant')
    if Environment.get_security().is_admin() or str(current_login or '').lower() == 'admin':
        privileged = True
    else:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        group_codes = [
            str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        ]
        privileged = any(
            group == 'admin' or 'supervisor' in group
            for group in group_codes
        )
    author = str(message_log.get_value('login') or '')
    if author == current_login:
        created = message_log.get_value('timestamp')
        if not isinstance(created, datetime.datetime):
            try:
                created = datetime.datetime.fromisoformat(
                    str(created).replace('Z', '+00:00')
                )
            except (TypeError, ValueError):
                created = None
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - created).total_seconds() if created else -1
        if not 0 <= age < 3600:
            raise RuntimeError('Own messages can only be deleted within one hour')
    elif not privileged:
        raise RuntimeError('Only administrators and supervisors can delete other messages')
    server.update(
        SearchKey.get_by_sobject(message_log, use_id=False),
        {'status': 'deleted'},
        triggers=True,
    )
    attachment_search = Search('sthpw/connection')
    attachment_search.add_filter('context', 'chat_attachment')
    attachment_search.add_filter('dst_search_type', 'sthpw/message_log')
    attachment_search.add_filter('dst_search_id', message_log.get_id())
    deleted_attachment_count = len(attachment_search.get_sobjects())
    conversation_search = Search('sthpw/message')
    conversation_search.add_filter('code', message_code)
    conversation_search.add_filter('category', 'chat')
    conversation = conversation_search.get_sobject()
    if conversation:
        raw_metadata = conversation.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            conversation_metadata = dict(raw_metadata)
        else:
            try:
                conversation_metadata = json.loads(raw_metadata)
            except (TypeError, ValueError):
                conversation_metadata = {}
        summary = dict(conversation_metadata.get('summary') or {})
        summary['messageCount'] = max(
            0, int(summary.get('messageCount') or 0) - 1
        )
        summary['attachmentCount'] = max(
            0,
            int(summary.get('attachmentCount') or 0)
            - deleted_attachment_count,
        )
        if str(summary.get('latestCode') or '') == str(message_log.get_code() or ''):
            latest_search = Search('sthpw/message_log')
            latest_search.add_filter('message_code', message_code)
            latest_search.add_filter('status', 'deleted', op='!=')
            latest_search.add_order_by('timestamp', direction='desc')
            latest_search.add_order_by('id', direction='desc')
            latest_search.set_limit(1)
            latest = latest_search.get_sobject()
            latest_metadata = {}
            if latest:
                raw_latest_metadata = latest.get_json_value('metadata', default={}) or {}
                if isinstance(raw_latest_metadata, dict):
                    latest_metadata = dict(raw_latest_metadata)
                else:
                    try:
                        latest_metadata = json.loads(raw_latest_metadata)
                    except (TypeError, ValueError):
                        latest_metadata = {}
            summary.update({
                'latestCode': str(latest.get_code() or '') if latest else '',
                'latestBody': str(latest.get_value('message') or '') if latest else '',
                'latestTimestamp': str(
                    latest.get_value('timestamp') or ''
                ) if latest else '',
                'latestSender': str(
                    latest.get_value('login') or ''
                ) if latest else '',
                'latestForwarded': bool(
                    latest_metadata.get('forwardedFrom')
                ),
            })
        conversation_metadata['summary'] = summary
        server.update(
            SearchKey.get_by_sobject(conversation, use_id=False),
            {
                'metadata': conversation_metadata,
                'project_code': 'sthpw',
            }, triggers=False,
        )
    return json.dumps({
        'deleted': True,
        'messageCode': message_code,
    }, separators=(',', ':'))


def edit_chat_message(message_log_code, message):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import datetime
    import json
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    message_log_ref = str(message_log_code or '')
    message_log = None
    if message_log_ref.startswith('sthpw/message_log'):
        search_type = server.split_search_key(message_log_ref)[0]
        if search_type == 'sthpw/message_log':
            message_log = Search.get_by_search_key(message_log_ref)
    else:
        log_search = Search('sthpw/message_log')
        log_search.add_filter('code', message_log_ref)
        message_log = log_search.get_sobject()
    if not message_log:
        raise RuntimeError('Message does not exist')
    if not message_log.get_code():
        raise RuntimeError('TACTIC message log has no code')
    message_code = message_log.get_value('message_code')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')
    author = message_log.get_value('login')
    privileged = Environment.get_security().is_admin() or str(current_login or '').lower() == 'admin'
    if not privileged:
        group_search = Search('sthpw/login_in_group')
        group_search.add_filter('login', current_login)
        privileged = any(
            str(item.get_value('login_group') or '').lower() == 'admin'
            or 'supervisor' in str(item.get_value('login_group') or '').lower()
            for item in group_search.get_sobjects()
        )
    if current_login == author:
        created = message_log.get_value('timestamp')
        if not isinstance(created, datetime.datetime):
            try:
                created = datetime.datetime.fromisoformat(
                    str(created).replace('Z', '+00:00')
                )
            except (TypeError, ValueError):
                created = None
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - created).total_seconds() if created else -1
        if not 0 <= age < 3600:
            raise RuntimeError('Own messages can only be edited within one hour')
    elif not privileged:
        raise RuntimeError('Only administrators and supervisors can edit other messages')
    value = str(message or '').strip()
    if not value:
        raise ValueError('Message text cannot be empty')
    if value == str(message_log.get_value('message') or ''):
        return json.dumps({'edited': False}, separators=(',', ':'))

    message_log_key = SearchKey.get_by_sobject(message_log, use_id=False)
    raw_metadata = message_log.get_json_value('metadata', default={}) or {}
    if isinstance(raw_metadata, dict):
        metadata_values = dict(raw_metadata)
    else:
        try:
            metadata_values = json.loads(raw_metadata)
        except (TypeError, ValueError):
            metadata_values = {}
    history = list(metadata_values.get('editHistory') or [])
    edited_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    history.append({
        'body': str(message_log.get_value('message') or ''),
        'editedBy': current_login,
        'editedAt': edited_at,
    })
    metadata_values['editHistory'] = history
    server.update(
        message_log_key,
        {
            'message': value,
            'metadata': metadata_values,
        },
        triggers=True,
    )
    conversation_search = Search('sthpw/message')
    conversation_search.add_filter('code', message_code)
    conversation_search.add_filter('category', 'chat')
    conversation = conversation_search.get_sobject()
    if conversation:
        raw_conversation_metadata = conversation.get_json_value('metadata', default={}) or {}
        if isinstance(raw_conversation_metadata, dict):
            conversation_metadata = dict(raw_conversation_metadata)
        else:
            try:
                conversation_metadata = json.loads(raw_conversation_metadata)
            except (TypeError, ValueError):
                conversation_metadata = {}
        summary = dict(conversation_metadata.get('summary') or {})
        if str(summary.get('latestCode') or '') == str(message_log.get_code() or ''):
            summary['latestBody'] = value
            conversation_metadata['summary'] = summary
            server.update(
                SearchKey.get_by_sobject(conversation, use_id=False),
                {
                    'metadata': conversation_metadata,
                    'project_code': 'sthpw',
                }, triggers=False,
            )
    return json.dumps({
        'edited': True,
        'editedBy': current_login,
        'editedAt': edited_at,
        'editHistory': history,
    }, separators=(',', ':'))


def toggle_chat_message_reaction(message_log_code, emoji):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import datetime
    import json
    from pyasm.search import Search, SearchKey

    current_login = str(server.get_login() or '')
    emoji = str(emoji or '').strip()
    if not emoji or len(emoji) > 16 or any(char.isspace() for char in emoji):
        raise ValueError('Invalid message reaction')

    message_log_ref = str(message_log_code or '')
    if message_log_ref.startswith('sthpw/message_log'):
        message_log = Search.get_by_search_key(message_log_ref)
    else:
        log_search = Search('sthpw/message_log')
        log_search.add_filter('code', message_log_ref)
        message_log = log_search.get_sobject()
    if not message_log or message_log.get_value(
            'status', no_exception=True) == 'deleted':
        raise RuntimeError('Message does not exist')

    message_code = str(message_log.get_value('message_code') or '')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')

    raw_metadata = message_log.get_json_value('metadata', default={}) or {}
    if isinstance(raw_metadata, dict):
        metadata = dict(raw_metadata)
    else:
        try:
            metadata = json.loads(raw_metadata)
        except (TypeError, ValueError):
            metadata = {}
    reactions = dict(metadata.get('reactions') or {})
    logins = list(dict.fromkeys(
        str(login) for login in (reactions.get(emoji) or []) if login
    ))
    active = current_login not in logins
    if active:
        logins.append(current_login)
        reactions[emoji] = logins
    else:
        logins.remove(current_login)
        if logins:
            reactions[emoji] = logins
        else:
            reactions.pop(emoji, None)
    updated_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
    metadata['reactions'] = reactions
    metadata['reactionUpdatedAt'] = updated_at
    message_log_key = SearchKey.get_by_sobject(message_log, use_id=False)
    server.update(
        message_log_key, {'metadata': metadata}, triggers=True,
    )
    return json.dumps({
        'messageId': message_log_key,
        'messageCode': message_code,
        'reactions': reactions,
        'reactionUpdatedAt': updated_at,
        'active': active,
    }, separators=(',', ':'))


def pin_chat_message(message_log_code, unpin=False):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import datetime
    import json
    from pyasm.search import Search, SearchKey

    current_login = server.get_login()
    message_log_ref = str(message_log_code or '')
    if message_log_ref.startswith('sthpw/message_log'):
        message_log = Search.get_by_search_key(message_log_ref)
    else:
        log_search = Search('sthpw/message_log')
        log_search.add_filter('code', message_log_ref)
        message_log = log_search.get_sobject()
    if not message_log:
        raise RuntimeError('Message does not exist')
    if not message_log.get_code():
        raise RuntimeError('TACTIC message log has no code')
    message_code = message_log.get_value('message_code')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')

    conversation_search = Search('sthpw/message')
    conversation_search.add_filter('code', message_code)
    conversation_search.add_filter('category', 'chat')
    conversation = conversation_search.get_sobject()
    if not conversation:
        raise RuntimeError('Chat does not exist')
    raw_metadata = conversation.get_json_value('metadata', default={}) or {}
    if isinstance(raw_metadata, dict):
        value = dict(raw_metadata)
    else:
        try:
            value = json.loads(raw_metadata)
        except (TypeError, ValueError):
            value = {}
    if unpin:
        current = dict(value.get('pin') or {})
        current_id = str(current.get('messageId') or '')
        message_id = SearchKey.get_by_sobject(message_log, use_id=False)
        if current_id == message_id:
            value['pin'] = {}
            server.update(
                SearchKey.get_by_sobject(conversation, use_id=False),
                {'metadata': value},
                triggers=True,
            )
        return json.dumps(value, separators=(',', ':'))
    pinned_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    message_id = SearchKey.get_by_sobject(message_log, use_id=False)
    pinned = {
        'messageId': message_id,
        'pinnedBy': str(current_login or ''),
        'pinnedAt': pinned_at,
    }
    history = list(value.get('pinHistory') or [])
    history.append({
        'messageId': message_id,
        'body': str(message_log.get_value('message') or ''),
        'sender': str(message_log.get_value('login') or ''),
        'timestamp': str(message_log.get_value('timestamp') or ''),
        'pinnedBy': str(current_login or ''),
        'pinnedAt': pinned_at,
    })
    value['pin'] = pinned
    value['pinHistory'] = history
    server.update(
        SearchKey.get_by_sobject(conversation, use_id=False),
        {'metadata': value},
        triggers=True,
    )
    return json.dumps(value, separators=(',', ':'))


def query_chat_history(message_code, limit=31, offset=0, search_text=''):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from datetime import datetime, timezone
    from pyasm.biz import Snapshot
    from pyasm.search import Search, SearchKey

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

    current_login = str(server.get_login() or '')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        raise RuntimeError('The current login is not a chat participant')

    history_search = Search('sthpw/message_log')
    history_search.add_filter('message_code', message_code)
    history_search.add_filter('status', 'deleted', op='!=')
    search_text = str(search_text or '').strip()
    if search_text:
        history_search.add_filter('message', '%{0}%'.format(search_text), op='like')
    history_search.add_order_by('timestamp', direction='desc')
    history_search.add_order_by('id', direction='desc')
    history_search.set_limit(int(limit))
    if offset:
        history_search.set_offset(int(offset))
    history = history_search.get_sobjects()
    for message_log in history:
        if message_log.get_code():
            continue
        if not _can_edit('sthpw/message_log'):
            continue
        record_id = message_log.get_id()
        if not record_id:
            raise RuntimeError('TACTIC message log has no code or id')
        code = 'MESSAGE_LOG{0:05d}'.format(int(record_id))
        server.update(
            SearchKey.get_by_sobject(message_log, use_id=True),
            {'code': code, 'project_code': 'sthpw'}, triggers=False,
        )
        message_log.set_value('code', code)
    metadata_by_log = {}
    delivery_updates = {}
    delivered_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    target_refs = set()
    for message_log in history:
        raw_metadata = message_log.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            value = dict(raw_metadata)
        else:
            try:
                value = json.loads(raw_metadata)
            except (TypeError, ValueError):
                value = {}
        delivery = dict(value.get('delivery') or {})
        recipients = dict(delivery.get('recipients') or {})
        receipt = dict(recipients.get(str(current_login or '')) or {})
        sender = str(
            delivery.get('sender') or message_log.get_value('login') or ''
        )
        if (
                _can_edit('sthpw/message_log') and sender != current_login and receipt
                and not receipt.get('deliveredAt')):
            receipt['deliveredAt'] = delivered_at
            recipients[current_login] = receipt
            delivery['recipients'] = recipients
            value['delivery'] = delivery
            delivery_updates[SearchKey.get_by_sobject(
                message_log, use_id=False
            )] = {
                'metadata': value,
                'status': aggregate_delivery(delivery),
                'project_code': 'sthpw',
            }
        metadata_by_log[str(message_log.get_code() or '')] = value
        for field in ('replyTo', 'forwardedFrom'):
            target_ref = str(value.get(field) or '')
            if target_ref:
                target_refs.add(target_ref)
    if delivery_updates:
        # Receipt changes must create a change timestamp so the sender can
        # update the visible ticks without reloading the conversation.
        server.update_multiple(data=delivery_updates, triggers=True)

    reply_targets = {}
    target_codes = []
    for target_ref in target_refs:
        search_type, target_code = server.split_search_key(target_ref)
        if search_type == 'sthpw/message_log' and target_code:
            target_codes.append(target_code)
    if target_codes:
        target_search = Search('sthpw/message_log')
        target_search.add_filters('code', list(set(target_codes)))
        for target in target_search.get_sobjects():
            reply_targets[str(target.get_code())] = target

    attachments_by_log = {}
    attachment_logs = history + list(reply_targets.values())
    log_codes_by_id = {
        item.get_id(): item.get_code() for item in attachment_logs
        if item.get_id() and item.get_code()
    }
    if log_codes_by_id:
        connection_search = Search('sthpw/connection')
        connection_search.add_filter('context', 'chat_attachment')
        connection_search.add_filter('dst_search_type', 'sthpw/message_log')
        connection_search.add_filters(
            'dst_search_id', list(log_codes_by_id)
        )
        connections = connection_search.get_sobjects()
        snapshot_ids = []
        snapshot_to_logs = {}
        for connection in connections:
            if connection.get_value('src_search_type') != 'sthpw/snapshot':
                continue
            snapshot_id = connection.get_value('src_search_id')
            log_code = log_codes_by_id.get(
                connection.get_value('dst_search_id')
            )
            if snapshot_id and log_code:
                snapshot_ids.append(snapshot_id)
                snapshot_to_logs.setdefault(snapshot_id, []).append(log_code)
        if snapshot_ids:
            snapshot_search = Search('sthpw/snapshot')
            snapshot_search.add_filters('id', list(set(snapshot_ids)))
            snapshots = snapshot_search.get_sobjects()
            files = Snapshot.get_files_dict_by_snapshots(snapshots)
            snapshot_keys = SearchKey.get_by_sobjects(snapshots, use_id=False)
            for snapshot, snapshot_key in zip(snapshots, snapshot_keys):
                snapshot_data = snapshot.get_data()
                snapshot_data['__search_key__'] = snapshot_key
                snapshot_data['__files__'] = [
                    file_object.get_data()
                    for file_object in (files.get(snapshot.get_code()) or [])
                ]
                snapshot_data['snapshot'] = {}
                for log_code in snapshot_to_logs.get(snapshot.get_id(), []):
                    attachments_by_log.setdefault(log_code, []).append(
                        snapshot_data
                    )

    conversation_metadata = {}
    pin_search = Search('sthpw/message')
    pin_search.add_filter('code', message_code)
    pin_search.add_filter('category', 'chat')
    conversation = pin_search.get_sobject()
    if conversation:
        raw_metadata = conversation.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            conversation_metadata = dict(raw_metadata)
        else:
            try:
                conversation_metadata = json.loads(raw_metadata)
            except (TypeError, ValueError):
                conversation_metadata = {}
    pin_value = dict(conversation_metadata.get('pin') or {})
    pin_message_id = str(pin_value.get('messageId') or '')
    if pin_message_id:
        pin_target = Search.get_by_search_key(pin_message_id)
        if pin_target and pin_target.get_value(
                'status', no_exception=True) != 'deleted':
            pin_value.update({
                'body': str(pin_target.get_value('message') or ''),
                'sender': str(pin_target.get_value('login') or ''),
                'timestamp': str(pin_target.get_value('timestamp') or ''),
            })
        else:
            pin_value = {}

    records = []
    for message_log in history:
        data = message_log.get_data()
        data['__search_key__'] = SearchKey.get_by_sobject(
            message_log, use_id=False
        )
        log_code = str(message_log.get_code() or '')
        data['__attachments__'] = attachments_by_log.get(log_code, [])
        message_metadata = metadata_by_log.get(
            log_code, {}
        )
        data['__edit_history__'] = list(
            message_metadata.get('editHistory') or []
        )
        data['__reactions__'] = dict(
            message_metadata.get('reactions') or {}
        )
        data['__delivery__'] = delivery_record(
            message_metadata.get('delivery') or {}
        )
        reply_ref = str(message_metadata.get('replyTo') or '')
        if reply_ref:
            target_code = server.split_search_key(reply_ref)[1]
            target = reply_targets.get(str(target_code))
            if target:
                data['__reply__'] = {
                    'messageId': SearchKey.get_by_sobject(target, use_id=False),
                    'sender': str(target.get_value('login') or ''),
                    'body': str(target.get_value('message') or ''),
                    'timestamp': str(target.get_value('timestamp') or ''),
                    'available': target.get_value(
                        'status', no_exception=True
                    ) != 'deleted',
                }
            else:
                data['__reply__'] = {
                    'messageId': reply_ref,
                    'sender': '',
                    'body': '',
                    'timestamp': '',
                    'available': False,
                }
        forward_ref = str(message_metadata.get('forwardedFrom') or '')
        if forward_ref:
            target_code = server.split_search_key(forward_ref)[1]
            target = reply_targets.get(str(target_code))
            if target:
                data['__forwarded_from__'] = {
                    'messageId': SearchKey.get_by_sobject(target, use_id=False),
                    'conversationId': str(target.get_value('message_code') or ''),
                    'sender': str(target.get_value('login') or ''),
                    'body': str(target.get_value('message') or ''),
                    'timestamp': str(target.get_value('timestamp') or ''),
                    'available': target.get_value(
                        'status', no_exception=True
                    ) != 'deleted',
                    'attachments': attachments_by_log.get(
                        str(target.get_code() or ''), []
                    ),
                }
            else:
                data['__forwarded_from__'] = {
                    'messageId': forward_ref,
                    'conversationId': '',
                    'sender': '',
                    'body': '',
                    'timestamp': '',
                    'available': False,
                    'attachments': [],
                }
        records.append(data)
    return json.dumps({
        'messages': records,
        'pinnedMessage': pin_value,
        'pinHistory': conversation_metadata.get('pinHistory') or [],
    }, separators=(',', ':'))


def mark_chat_read(message_code, timestamp):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from datetime import datetime, timezone
    from pyasm.search import Search, SearchKey

    def aggregate_delivery(delivery):
        recipients = dict((delivery or {}).get('recipients') or {})
        receipts = list(recipients.values())
        if receipts and all(item.get('readAt') for item in receipts):
            return 'read'
        if receipts and all(item.get('deliveredAt') for item in receipts):
            return 'delivered'
        return 'sent'

    current_login = str(server.get_login() or '')
    search = Search('sthpw/subscription')
    search.add_filter('message_code', message_code)
    search.add_filter('login', current_login)
    search.add_filter('category', 'chat')
    subscription = search.get_sobject()
    if not subscription:
        raise RuntimeError('The current login is not a chat participant')
    current_value = subscription.get_value('last_cleared', no_exception=True)
    timestamp_second = str(timestamp or '')[:19]
    current_second = str(current_value or '')[:19]
    if timestamp_second and (
            not current_second or timestamp_second > current_second):
        server.update(
            SearchKey.get_by_sobject(subscription, use_id=False),
            {'last_cleared': timestamp_second},
            triggers=True,
        )
    receipt_updates = {}
    if timestamp_second:
        log_search = Search('sthpw/message_log')
        log_search.add_filter('message_code', message_code)
        log_search.add_filter('login', current_login, op='!=')
        log_search.add_filter('status', 'deleted', op='!=')
        log_search.add_filter('status', 'read', op='!=')
        log_search.add_filter('timestamp', timestamp_second, op='<=')
        read_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        for message_log in log_search.get_sobjects():
            raw_metadata = message_log.get_json_value('metadata', default={}) or {}
            if isinstance(raw_metadata, dict):
                metadata = dict(raw_metadata)
            else:
                try:
                    metadata = json.loads(raw_metadata)
                except (TypeError, ValueError):
                    metadata = {}
            delivery = dict(metadata.get('delivery') or {})
            recipients = dict(delivery.get('recipients') or {})
            receipt = dict(recipients.get(current_login) or {})
            if not receipt or receipt.get('readAt'):
                continue
            receipt['deliveredAt'] = str(
                receipt.get('deliveredAt') or read_at
            )
            receipt['readAt'] = read_at
            recipients[current_login] = receipt
            delivery['recipients'] = recipients
            metadata['delivery'] = delivery
            receipt_updates[SearchKey.get_by_sobject(
                message_log, use_id=False
            )] = {
                'metadata': metadata,
                'status': aggregate_delivery(delivery),
                'project_code': 'sthpw',
            }
    if receipt_updates:
        server.update_multiple(data=receipt_updates, triggers=True)
    return {
        'lastCleared': str(timestamp_second or current_value or ''),
        'receiptsUpdated': len(receipt_updates),
    }


def send_chat_message(message_code, message, attachment_keys=None, reply_to=None):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    def update_message_log(message_log, metadata=None):
        code = message_log.get_code()
        values = {}
        use_id = False
        if not code:
            record_id = message_log.get_id()
            if not record_id:
                raise RuntimeError('TACTIC message log has no code')
            code = 'MESSAGE_LOG{0:05d}'.format(int(record_id))
            values['code'] = code
            use_id = True
        values['project_code'] = 'sthpw'
        if metadata is not None:
            values['metadata'] = metadata
        if values:
            server.update(
                SearchKey.get_by_sobject(message_log, use_id=use_id),
                values,
                triggers=False,
            )
            if 'code' in values:
                message_log.set_value('code', values['code'])
        return code

    current_login = str(server.get_login() or '')
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('category', 'chat')
    members = member_search.get_sobjects()
    member_logins = set(
        str(item.get_value('login') or '') for item in members
        if item.get_value('login')
    )
    if current_login not in member_logins:
        raise RuntimeError('The current login is not a chat participant')

    reply_target = None
    if reply_to:
        reply_ref = str(reply_to)
        if reply_ref.startswith('sthpw/message_log'):
            reply_target = Search.get_by_search_key(reply_ref)
        else:
            reply_search = Search('sthpw/message_log')
            reply_search.add_filter('code', reply_ref)
            reply_target = reply_search.get_sobject()
        if (
            not reply_target
            or reply_target.get_value('message_code') != message_code
            or reply_target.get_value('status', no_exception=True) == 'deleted'
        ):
            raise RuntimeError('The replied message is not available in this chat')
        update_message_log(reply_target)

    valid_attachments = []
    for attachment_key in attachment_keys or []:
        search_type, code = server.split_search_key(attachment_key)
        if search_type != 'sthpw/snapshot':
            raise ValueError('Chat attachment must be a TACTIC snapshot')
        snapshot_search = Search('sthpw/snapshot')
        snapshot_search.add_filter('code', code)
        snapshot = snapshot_search.get_sobject()
        if not snapshot:
            raise ValueError('Chat attachment snapshot was not found')
        if (
            snapshot.get_value('search_type') != 'sthpw/message'
            or snapshot.get_value('search_code') != message_code
        ):
            raise RuntimeError('Attachment does not belong to this chat')
        valid_attachments.append(attachment_key)

    if not str(message or '').strip() and not valid_attachments:
        raise ValueError('Message or attachment is required')
    log_search = Search('sthpw/message_log')
    sqlite = log_search.get_database_impl().get_database_type() == 'Sqlite'
    _log_chat_message(server, 
        message_code, message or '', status='sent',
        category='chat', log_history=not sqlite,
    )
    if sqlite:
        # TACTIC 5.0 does not commit message_log in its SQLite branch.
        from pyasm.search import SearchType
        message_log = SearchType.create('sthpw/message_log')
        message_log.set_value('message_code', message_code)
        message_log.set_value('message', message or '')
        message_log.set_value('status', 'sent')
        message_log.set_value('login', current_login)
        message_log.set_value('project_code', 'sthpw')
        message_log.set_value('timestamp', 'NOW')
        message_log.commit(triggers=False)
    else:
        log_search.add_filter('message_code', message_code)
        log_search.add_filter('login', current_login)
        log_search.add_order_by('id', direction='desc')
        log_search.set_limit(1)
        message_log = log_search.get_sobject()
    if not message_log:
        raise RuntimeError('TACTIC did not create a message log')
    sent_at = str(message_log.get_value('timestamp') or '')
    metadata_values = {
        'delivery': {
            'schemaVersion': 1,
            'sender': str(current_login or ''),
            'sentAt': sent_at,
            'recipients': dict(
                (login, {'deliveredAt': '', 'readAt': ''})
                for login in sorted(member_logins)
                if login != current_login
            ),
        },
    }
    if reply_target:
        metadata_values['replyTo'] = SearchKey.get_by_sobject(
            reply_target, use_id=False
        )
    update_message_log(message_log, metadata_values)
    message_log_key = SearchKey.get_by_sobject(message_log, use_id=False)
    try:
        for attachment_key in valid_attachments:
            connection = server.connect_sobjects(
                attachment_key, message_log_key, context='chat_attachment'
            )
            if not connection:
                raise RuntimeError('Could not attach the file to the chat message')
    except Exception:
        server.update(
            message_log_key, {'status': 'deleted'}, triggers=True,
        )
        raise
    data = message_log.get_data()
    data['__search_key__'] = message_log_key
    data['__delivery__'] = metadata_values['delivery']
    conversation_search = Search('sthpw/message')
    conversation_search.add_filter('code', message_code)
    conversation_search.add_filter('category', 'chat')
    conversation = conversation_search.get_sobject()
    if conversation:
        raw_metadata = conversation.get_json_value('metadata', default={}) or {}
        if isinstance(raw_metadata, dict):
            conversation_metadata = dict(raw_metadata)
        else:
            try:
                conversation_metadata = json.loads(raw_metadata)
            except (TypeError, ValueError):
                conversation_metadata = {}
        summary = dict(conversation_metadata.get('summary') or {})
        summary.update({
            'latestCode': str(message_log.get_code() or ''),
            'latestBody': str(message or ''),
            'latestTimestamp': str(message_log.get_value('timestamp') or ''),
            'latestSender': str(current_login or ''),
            'latestForwarded': False,
            'messageCount': int(summary.get('messageCount') or 0) + 1,
            'attachmentCount': (
                int(summary.get('attachmentCount') or 0)
                + len(valid_attachments)
            ),
        })
        conversation_metadata['summary'] = summary
        server.update(
            SearchKey.get_by_sobject(conversation, use_id=False),
            {
                'metadata': conversation_metadata,
                'project_code': 'sthpw',
            }, triggers=False,
        )
    return json.dumps({'message': data}, separators=(',', ':'))


def forward_chat_messages(message_log_keys, target_message_codes):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search, SearchKey

    def update_message_log(message_log, metadata=None):
        code = message_log.get_code()
        values = {}
        use_id = False
        if not code:
            record_id = message_log.get_id()
            if not record_id:
                raise RuntimeError('TACTIC message log has no code')
            code = 'MESSAGE_LOG{0:05d}'.format(int(record_id))
            values['code'] = code
            use_id = True
        values['project_code'] = 'sthpw'
        if metadata is not None:
            values['metadata'] = metadata
        if values:
            server.update(
                SearchKey.get_by_sobject(message_log, use_id=use_id),
                values,
                triggers=False,
            )
            if 'code' in values:
                message_log.set_value('code', values['code'])
        return code

    current_login = str(server.get_login() or '')
    source_refs = []
    source_messages = []
    seen_sources = set()
    for message_log_key in message_log_keys or []:
        message_log = Search.get_by_search_key(str(message_log_key or ''))
        if not message_log or server.split_search_key(
                SearchKey.get_by_sobject(message_log, use_id=False)
        )[0] != 'sthpw/message_log':
            raise RuntimeError('A forwarded message does not exist')
        if message_log.get_value('status', no_exception=True) == 'deleted':
            raise RuntimeError('A deleted message cannot be forwarded')
        update_message_log(message_log)
        source_ref = SearchKey.get_by_sobject(message_log, use_id=False)
        if source_ref in seen_sources:
            continue
        seen_sources.add(source_ref)
        source_refs.append(source_ref)
        source_messages.append(message_log)
    if not source_messages:
        raise ValueError('Select at least one message to forward')

    source_chats = set(
        message_log.get_value('message_code') for message_log in source_messages
    )
    access_search = Search('sthpw/subscription')
    access_search.add_filter('login', current_login)
    access_search.add_filter('category', 'chat')
    access_search.add_filters('message_code', list(source_chats))
    accessible_sources = set(
        item.get_value('message_code') for item in access_search.get_sobjects()
    )
    if accessible_sources != source_chats:
        raise RuntimeError('The current login cannot access a forwarded message')

    targets = []
    seen_targets = set()
    for message_code in target_message_codes or []:
        message_code = str(message_code or '').strip()
        if message_code and message_code not in seen_targets:
            seen_targets.add(message_code)
            targets.append(message_code)
    if not targets:
        raise ValueError('Select at least one destination chat')
    target_access = Search('sthpw/subscription')
    target_access.add_filter('category', 'chat')
    target_access.add_filters('message_code', targets)
    target_members = target_access.get_sobjects()
    members_by_target = {}
    for item in target_members:
        members_by_target.setdefault(
            str(item.get_value('message_code') or ''), set()
        ).add(str(item.get_value('login') or ''))
    accessible_targets = set(
        code for code, logins in members_by_target.items()
        if current_login in logins
    )
    if accessible_targets != set(targets):
        raise RuntimeError('The current login cannot access a destination chat')
    target_search = Search('sthpw/message')
    target_search.add_filter('category', 'chat')
    # A new conversation has NULL status and is still active.
    target_search.add_op('begin')
    target_search.add_filter('status', 'deleted', op='!=')
    target_search.add_null_filter('status')
    target_search.add_op('or')
    target_search.add_filters('code', targets)
    target_messages = dict(
        (item.get_code(), item) for item in target_search.get_sobjects()
    )
    active_targets = set(target_messages)
    if active_targets != set(targets):
        raise RuntimeError('A destination chat is not available')

    created = []
    for message_code in targets:
        latest_created = None
        for source_ref in source_refs:
            log_search = Search('sthpw/message_log')
            sqlite = log_search.get_database_impl().get_database_type() == 'Sqlite'
            _log_chat_message(server, 
                message_code, '', status='sent',
                category='chat', log_history=not sqlite,
            )
            if sqlite:
                # TACTIC 5.0 does not commit message_log in its SQLite branch.
                from pyasm.search import SearchType
                message_log = SearchType.create('sthpw/message_log')
                message_log.set_value('message_code', message_code)
                message_log.set_value('message', '')
                message_log.set_value('status', 'sent')
                message_log.set_value('login', current_login)
                message_log.set_value('project_code', 'sthpw')
                message_log.set_value('timestamp', 'NOW')
                message_log.commit(triggers=False)
            else:
                log_search.add_filter('message_code', message_code)
                log_search.add_filter('login', current_login)
                log_search.add_order_by('timestamp', direction='desc')
                log_search.set_limit(len(source_refs) + 1)
                # Keep this explicit: the source minifier corrupts a
                # multiline next(generator, default) expression.
                message_log = None
                for item in log_search.get_sobjects():
                    item_key = SearchKey.get_by_sobject(item, use_id=False)
                    if item_key not in created:
                        message_log = item
                        break
            if not message_log:
                raise RuntimeError('TACTIC did not create a forwarded message log')
            sent_at = str(message_log.get_value('timestamp') or '')
            update_message_log(message_log, {
                'forwardedFrom': source_ref,
                'delivery': {
                    'schemaVersion': 1,
                    'sender': str(current_login or ''),
                    'sentAt': sent_at,
                    'recipients': dict(
                        (login, {'deliveredAt': '', 'readAt': ''})
                        for login in sorted(
                            members_by_target.get(message_code, set())
                        ) if login and login != current_login
                    ),
                },
            })
            message_id = SearchKey.get_by_sobject(message_log, use_id=False)
            created.append(message_id)
            latest_created = message_log
        conversation = target_messages.get(message_code)
        if conversation and latest_created:
            raw_metadata = conversation.get_json_value('metadata', default={}) or {}
            if isinstance(raw_metadata, dict):
                conversation_metadata = dict(raw_metadata)
            else:
                try:
                    conversation_metadata = json.loads(raw_metadata)
                except (TypeError, ValueError):
                    conversation_metadata = {}
            summary = dict(conversation_metadata.get('summary') or {})
            summary.update({
                'latestCode': str(latest_created.get_code() or ''),
                'latestBody': '',
                'latestTimestamp': str(
                    latest_created.get_value('timestamp') or ''
                ),
                'latestSender': str(current_login or ''),
                'latestForwarded': True,
                'messageCount': (
                    int(summary.get('messageCount') or 0)
                    + len(source_refs)
                ),
                'attachmentCount': int(
                    summary.get('attachmentCount') or 0
                ),
            })
            conversation_metadata['summary'] = summary
            server.update(
                SearchKey.get_by_sobject(conversation, use_id=False),
                {
                    'metadata': conversation_metadata,
                    'project_code': 'sthpw',
                }, triggers=False,
            )
    return json.dumps({
        'forwarded': len(created),
        'destinations': len(targets),
        'messages': len(source_refs),
    }, separators=(',', ':'))


def authorize_chat_attachment(message_code, snapshot_code):
    from tactic_client_lib import TacticServerStub
    from pyasm.common import Environment
    server = TacticServerStub.get(protocol='local')
    server.login = Environment.get_user_name()
    import json
    from pyasm.search import Search

    current_login = server.get_login()
    member_search = Search('sthpw/subscription')
    member_search.add_filter('message_code', message_code)
    member_search.add_filter('login', current_login)
    member_search.add_filter('category', 'chat')
    if not member_search.get_sobject():
        return json.dumps({'allowed': False}, separators=(',', ':'))

    snapshot_search = Search('sthpw/snapshot')
    snapshot_search.add_filter('code', snapshot_code)
    snapshot = snapshot_search.get_sobject()
    if not snapshot:
        return json.dumps({'allowed': False}, separators=(',', ':'))
    connection_search = Search('sthpw/connection')
    connection_search.add_filter('context', 'chat_attachment')
    connection_search.add_filter('src_search_type', 'sthpw/snapshot')
    connection_search.add_filter('src_search_id', snapshot.get_id())
    connection_search.add_filter('dst_search_type', 'sthpw/message_log')
    connections = connection_search.get_sobjects()
    log_ids = [
        connection.get_value('dst_search_id')
        for connection in connections if connection.get_value('dst_search_id')
    ]
    allowed = False
    if log_ids:
        log_search = Search('sthpw/message_log')
        log_search.add_filters('id', log_ids)
        log_search.add_filter('message_code', message_code)
        log_search.add_filter('status', 'deleted', op='!=')
        allowed = bool(log_search.get_sobject())
        if not allowed:
            # Handler forwards reference the source log rather than duplicating its file connection.
            from pyasm.search import SearchKey
            sources = Search('sthpw/message_log')
            sources.add_filters('id', log_ids)
            sources.add_filter('status', 'deleted', op='!=')
            references = {SearchKey.get_by_sobject(row, use_id=use_id)
                          for row in sources.get_sobjects() for use_id in (False, True)}
            targets = Search('sthpw/message_log')
            targets.add_filter('message_code', message_code)
            targets.add_filter('status', 'deleted', op='!=')
            allowed = any((row.get_json_value('metadata', default={}) or {}).get('forwardedFrom') in references
                          for row in targets.get_sobjects())
    return json.dumps({'allowed': allowed}, separators=(',', ':'))
