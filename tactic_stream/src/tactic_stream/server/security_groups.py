"""Handler security_store group operations on native TACTIC account objects."""
import colorsys
import hashlib
import json
import re
import zlib

from pyasm.biz import Snapshot
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.widget_configuration import WidgetConfigConflict


def group_revision(group, marker=None):
    if marker is None:
        log = Search('sthpw/sobject_log')
        log.add_filter('search_type', 'sthpw/login_group')
        log.add_filter('search_code', group.get_code())
        log.add_order_by('id desc'); log.add_limit(1)
        latest = log.get_sobject(); marker = latest.get_id() if latest else 0
    return hashlib.sha256(json.dumps([group.get_data(), marker],
                                     sort_keys=True, default=str).encode()).hexdigest()


def user_identities(logins):
    """Shared Handler identity projection, without account data or credentials."""
    from tactic_stream.server.table_cells import safe_link
    from pyasm.common import Environment
    security = Environment.get_security()
    can_read_avatars = security and all(security.check_access('search_type', [
        {'code':base}, {'code':base, 'project':'sthpw'}, {'code':'*'}, {'code':'*', 'project':'sthpw'}
    ], 'view', default='allow') for base in ('sthpw/snapshot', 'sthpw/file'))
    snapshots = Snapshot.get_by_sobjects(logins) if logins and can_read_avatars else []
    snapshots = sorted((item for item in snapshots if item.get_value('process') in ('icon', 'publish')),
                       key=lambda item: (item.get_value('process') != 'icon', item.get_value('version') not in (-1, 0), -int(item.get_value('version') or 0)))
    avatars = {}
    for snapshot in snapshots:
        key = str(snapshot.get_value('search_code') or snapshot.get_value('search_id'))
        if key in avatars:
            continue
        for file_type in ('web', 'preview', 'image', 'main', 'icon'):
            path = snapshot.get_web_path_by_type(file_type)
            if path:
                avatars[key] = safe_link(path.replace('\\', '/'))
                break
    users = []
    for item in logins:
        login = str(item.get_value('login') or '')
        name = str(item.get_value('display_name', no_exception=True) or
                   ' '.join(str(item.get_value(field) or '') for field in ('first_name', 'last_name')).strip() or login)
        # Handler user_identity.user_initials and color_hash.color_hash.
        initials = ''.join(part[0] for part in name.split()[:2]).upper() or '?'
        hue = (zlib.crc32(login.encode('utf-8')) & 0xffffffff) % 359
        color = '#{:02x}{:02x}{:02x}'.format(*(round(value * 255) for value in colorsys.hls_to_rgb(hue / 360, 0.5, 0.3)))
        users.append(dict(login=login, displayName=name, retired=item.get_value('s_status', no_exception=True) == 'retired',
                          initials=initials, avatarColor=color, avatarUrl=avatars.get(item.get_code(), avatars.get(str(item.get_id()), ''))))
    return sorted(users, key=lambda row: row['displayName'].casefold())


def user_directory(logins):
    """Handler UserPicker/UserDirectory projection; group ranking grants no rights."""
    from pyasm.biz import Project
    from pyasm.common import Environment
    from .group_authority import ranked_groups
    users = user_identities(logins)
    security = Environment.get_security()
    can_read_groups = security and all(security.check_access('search_type', [
        {'code': base}, {'code': base, 'project': 'sthpw'}, {'code': '*'}, {'code': '*', 'project': 'sthpw'}
    ], 'view', default='deny') for base in ('sthpw/login_group', 'sthpw/login_in_group'))
    groups, memberships = [], {}
    if can_read_groups:
        groups = ranked_groups([dict(code=row.get_value('login_group'),
            label=(row.get_value('name', no_exception=True) or row.get_value('login_group').replace('_', ' ')).title(),
            accessLevel=row.get_value('access_level') or '', accessRules=row.get_value('access_rules') or '',
            projectCode=row.get_value('project_code') or '', isDefault=bool(row.get_value('is_default')))
            for row in Search('sthpw/login_group').get_sobjects()], Project.get_project_code())
        for row in Search('sthpw/login_in_group').get_sobjects():
            memberships.setdefault(row.get_value('login'), set()).add(row.get_value('login_group'))
    records = {row.get_value('login'): row for row in logins}
    for user in users:
        labels = [group['label'] for group in groups if group['code'] in memberships.get(user['login'], set())]
        user.update(groups=labels, primaryGroup=labels[0] if labels else 'Ungrouped',
                    current=user['login'] == Environment.get_user_name(), email=records[user['login']].get_value('email') or '')
    return sorted(users, key=lambda row: (row['primaryGroup'].casefold(), row['displayName'].casefold()))


def query_security_groups():
    _require_admin()
    groups = Search('sthpw/login_group').get_sobjects()
    markers = {}
    if groups:
        log = Search('sthpw/sobject_log'); log.add_filter('search_type', 'sthpw/login_group')
        log.add_filters('search_code', [group.get_code() for group in groups])
        log.add_column('search_code')
        log.get_select().set_quoted_mode('none')
        log.add_column('MAX(id)', as_column='id')
        log.add_group_by('search_code')
        # Journal Search defaults to timestamp sorting; native Select would
        # also group by timestamp and split one group's journal into many rows.
        statement, parameters = log._statement(default_order=False)
        with log.store.connection(log.get_db_resource()) as db:
            markers = {row['search_code']: row['id'] for row in db.execute(statement, parameters).fetchall()}
    memberships = [dict(login=str(item.get_value('login') or ''), login_group=str(item.get_value('login_group') or ''))
                   for item in Search('sthpw/login_in_group').get_sobjects()]
    search = Search('sthpw/login'); search.set_show_retired(True)
    users = user_identities(search.get_sobjects())
    counts = {}
    for row in memberships:
        counts.setdefault(row['login_group'], set()).add(row['login'])
    records = [dict(code=group.get_code(), name=group.get_value('login_group'), description=group.get_value('description') or '',
                    accessLevel=group.get_value('access_level') or '', projectCode=group.get_value('project_code') or '', isDefault=bool(group.get_value('is_default')),
                    memberCount=len(counts.get(group.get_value('login_group'), ())), revision=group_revision(group, markers.get(group.get_code(), 0))) for group in groups]
    return dict(groups=sorted(records, key=lambda row: row['name'].casefold()), memberships=memberships,
                users=sorted(users, key=lambda row: row['displayName'].casefold()))


def save_security_group(group_code, login_group, description, add_members, remove_members, expected_revision):
    """Handler's membership deltas preserve unrelated concurrent edits."""
    _require_admin()
    if not all(isinstance(value, str) for value in (group_code, login_group, description, expected_revision)):
        raise ValueError('Invalid group details')
    code, name, description = group_code.strip(), login_group.strip(), description.strip()
    if not name or len(name) > 100 or re.search(r'[\s/\\<>]', name):
        raise ValueError('Enter a group identifier without spaces or slashes')
    if len(code) > 256 or len(description.encode()) > 65536:
        raise ValueError('Group details are too large')
    for values in (add_members, remove_members):
        if not isinstance(values, list) or len(values) > 10000 or any(not isinstance(value, str) or not value or len(value) > 256 for value in values):
            raise ValueError('Invalid group members')
    additions, removals = set(add_members), set(remove_members)
    if additions & removals:
        raise ValueError('A user cannot be added and removed at the same time')
    # Serialize membership changes and creation through the existing drivers.
    for search_type in ('sthpw/login_group', 'sthpw/login_in_group', 'sthpw/login'):
        search = Search(search_type); sql = search.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(search_type).get_table())
    search = Search('sthpw/login_group')
    search.add_filter('code' if code else 'login_group', code or name)
    group = search.get_sobject()
    if code and not group:
        raise ValueError('The selected group no longer exists. Refresh the list.')
    if group and group.get_value('login_group') != name:
        raise ValueError('An existing group identifier cannot be changed')
    if group and not code:
        members = Search('sthpw/login_in_group'); members.add_filter('login_group', name)
        existing = {item.get_value('login') for item in members.get_sobjects()}
        if (group.get_value('description') or '') == description and additions <= existing and not removals:
            return dict(code=group.get_code())
        raise ValueError('A group with this identifier already exists')
    if group and expected_revision != group_revision(group):
        raise WidgetConfigConflict('Group details changed. Reload before saving.')
    logins = {}
    if additions or removals:
        search = Search('sthpw/login'); search.set_show_retired(True)
        search.add_filters('login', sorted(additions | removals))
        logins = {item.get_value('login'): item for item in search.get_sobjects()}
        missing = (additions | removals) - set(logins)
        if missing:
            raise ValueError('Users no longer exist: %s' % ', '.join(sorted(missing)))
    if group is None:
        group = SearchType.create('sthpw/login_group'); group.set_value('login_group', name)
    group.set_value('description', description); group.commit()
    search = Search('sthpw/login_in_group'); search.add_filter('login_group', name)
    existing = {item.get_value('login') for item in search.get_sobjects()}
    for login in sorted(additions - existing):
        logins[login].add_to_group(name)
    for login in sorted(removals & existing):
        logins[login].remove_from_group(name)
    return dict(code=group.get_code())


def security_groups_request(action, payload):
    _require_admin()
    if action == 'read':
        return query_security_groups()
    command = Command()
    command.execute = lambda: save_security_group(payload.get('group_code', ''), payload.get('login_group'), payload.get('description', ''),
        payload.get('add_members', []), payload.get('remove_members', []), payload.get('expected_revision', ''))
    command.get_transaction().set_sync(False)
    result = Command.execute_cmd(command)
    return dict(**query_security_groups(), selected=result['code'])
