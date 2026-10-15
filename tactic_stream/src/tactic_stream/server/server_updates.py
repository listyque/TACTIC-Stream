"""Authenticated Handler update batch over the same native Search/Command API."""
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.command import Command
from pyasm.search.update_events import PROJECT_TYPES
from .server_updates_query import query_server_updates


CHANNELS = {'messages', 'reactions', 'activity', 'cache'}


def update_subscription(payload):
    channels = payload.get('channels', sorted(CHANNELS))
    types = payload.get('search_types', [])
    invalidated = payload.get('invalidated_types', [])
    if not isinstance(channels, list) or len(channels) > 4 or any(not isinstance(value, str) or value not in CHANNELS for value in channels):
        raise ValueError('Invalid update channels')
    for values in (types, invalidated):
        if not isinstance(values, list) or len(values) > 128 or any(not isinstance(value, str) or len(value) > 256
                or not value or '?' in value or value.count('/') != 1 for value in values):
            raise ValueError('Invalid subscribed search types')
    if type(payload.get('heartbeat', True)) is not bool:
        raise ValueError('Invalid presence heartbeat')
    project, security = Project.get_project_code(), Environment.get_security()
    def allowed(search_type):
        if not security.is_admin() and search_type in ('sthpw/login', 'sthpw/ticket', 'sthpw/login_group', 'sthpw/login_in_group', 'sthpw/db_resource'):
            return False
        keys = [{'code': search_type}, {'code': search_type, 'project': project}, {'code': '*'}, {'code': '*', 'project': project}]
        return security.check_access('search_type', keys, 'view', default='allow' if search_type.startswith('sthpw/') else 'deny')
    return dict(login=Environment.get_user_name(), channels=sorted(set(channels)), search_types=sorted({value for value in types if allowed(value)})), {value for value in invalidated if allowed(value)}


def server_updates_request(payload, heartbeat=True, presence_only=False, invalidations=()):
    subscription, invalidated = update_subscription(payload)
    cursors = ('message_after', 'activity_after', 'reaction_after', 'cache_after')
    if any(not isinstance(payload.get(key, ''), str) or len(payload.get(key, '')) > 1024 for key in cursors):
        raise ValueError('Invalid server update cursor')
    ttl = payload.get('presence_ttl', 90)
    if type(ttl) is not int or not 30 <= ttl <= 1080:
        raise ValueError('Invalid presence timeout')
    project, security = Project.get_project_code(), Environment.get_security()
    if Project.get_by_code(project) is None:
        raise ValueError('Server update project does not exist')
    if project not in ('admin', 'sthpw') and not (security.check_access('project', {'code': '*'}, 'allow', default='deny')
            or security.check_access('project', {'code': project}, 'allow', default='deny')):
        raise SecurityException('Server update project is not accessible')
    # Local API writes currently require admin; a reader must still receive its batch.
    heartbeat = heartbeat and payload.get('heartbeat', True) and security.is_admin()
    channels = subscription['channels']
    arguments = dict(project_code=project, limit=101, include_presence=True,
        heartbeat_presence=heartbeat, presence_ttl=ttl, include_cache_changes='cache' in channels and not invalidated,
        include_messages='messages' in channels, include_reactions='reactions' in channels, include_activity='activity' in channels,
        **{key: payload.get(key, '') for key in cursors})
    if presence_only:
        arguments.update(include_messages=False, include_activity=False,
                         include_reactions=False, include_cache_changes=False)
    if not security.is_admin():
        result = query_server_updates(**arguments)
        result['presenceHeartbeatApplied'] = False
    else:
        # Handler executes this procedure in sthpw; heartbeat writes are global.
        Project.set_project('sthpw')
        try:
            command = Command()
            command.get_transaction().set_sync(False)
            command.get_transaction().notify_updates = not presence_only
            # This query writes presence messages; delivery receipts use message_log.
            command.get_transaction().notify_excluded_types = {'sthpw/message'}
            command.execute = lambda: query_server_updates(**arguments)
            result = Command.execute_cmd(command)
        finally:
            Project.set_project(project)
    for scope, search_type in set(invalidations) | {('sthpw' if value.startswith('sthpw/') and value not in PROJECT_TYPES else project, value) for value in invalidated}:
        if not security.is_admin() and search_type in (
                'sthpw/login', 'sthpw/ticket', 'sthpw/login_group', 'sthpw/login_in_group', 'sthpw/db_resource'):
            continue
        keys = [{'code': search_type}, {'code': search_type, 'project': project},
                {'code': '*'}, {'code': '*', 'project': project}]
        if security.check_access('search_type', keys, 'view',
                default='allow' if search_type.startswith('sthpw/') else 'deny'):
            # Type invalidation survives coalesced commits and same-second legacy cursors.
            result['cacheChanges'].append(dict(searchType=search_type, searchCode='', projectCode=scope,
                                               timestamp=result['serverClock']['utcEnded']))
    result['presenceHeartbeatApplied'] = heartbeat and result['messagesInitialized']
    result['subscription'] = subscription
    return result
