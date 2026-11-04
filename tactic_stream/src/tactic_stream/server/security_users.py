"""Handler users_api / create_user_profile / mutate_user_profile on native Login."""
import hashlib
import json
import math
import re

from pyasm.common import Environment
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security import Login
from pyasm.security.security import _require_admin
from tactic_stream.server.security_groups import query_security_groups
from tactic_stream.server.widget_configuration import WidgetConfigConflict

FIELDS = ('first_name', 'last_name', 'display_name', 'email', 'phone_number',
          'address', 'department', 'upn', 'namespace', 's_status', 'project_code', 'hourly_wage')


def user_revision(user, groups):
    # Hashes never leave the server; a password change also invalidates a draft.
    data = [user.get_data(), sorted(groups)]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def query_security_users():
    _require_admin()
    directory = query_security_groups()
    identities = {row['login']: row for row in directory['users']}
    fields = [field for field in FIELDS if field in SearchType.get_columns('sthpw/login')]
    memberships = {}
    for row in directory['memberships']:
        memberships.setdefault(row['login'], set()).add(row['login_group'])
    search = Search('sthpw/login'); search.set_show_retired(True)
    users = []
    for user in search.get_sobjects():
        login = user.get_login()
        groups = sorted(memberships.get(login, ()))
        # Explicit projection keeps credentials, failures and arbitrary metadata out of UI.
        document = {field: user.get_value(field) if user.get_value(field) is not None else '' for field in fields}
        document.update(login=login, groups=groups, password='')
        users.append(dict(**identities[login], document=document, revision=user_revision(user, groups)))
    users.sort(key=lambda row: (row['displayName'].casefold(), row['login']))
    return dict(users=users, groups=directory['groups'], fields=fields)


def save_security_user(identity, document, expected_revision):
    _require_admin()
    if not isinstance(identity, str) or not isinstance(expected_revision, str) or not isinstance(document, dict):
        raise ValueError('Invalid user document')
    if set(document) - set((*FIELDS, 'login', 'password', 'groups')):
        raise ValueError('Invalid user document')
    login = document.get('login')
    if not isinstance(login, str) or not login.strip() or len(login) > 256 or re.search(r'[\s/\\<>\x00-\x1f]', login):
        raise ValueError('Enter a login without spaces or slashes')
    if identity and identity != login:
        raise ValueError('An existing login cannot be changed')
    password, groups = document.get('password', ''), document.get('groups', [])
    if not isinstance(password, str) or len(password) > 4096 or not isinstance(groups, list) or len(groups) > 10000 or any(not isinstance(group, str) or not group or len(group) > 256 for group in groups):
        raise ValueError('Invalid password or user groups')
    columns = set(SearchType.get_columns('sthpw/login'))
    values = {field: value for field, value in document.items() if field in FIELDS}
    for field, value in values.items():
        if field not in columns or not isinstance(value, (str, int, float) if field == 'hourly_wage' else str) or isinstance(value, bool) or len(str(value).encode()) > 65536:
            raise ValueError('Invalid user profile field')
        if field == 'hourly_wage' and value != '':
            try:
                values[field] = float(value)
            except ValueError:
                raise ValueError('Hourly wage must be a non-negative number') from None
            if not math.isfinite(values[field]) or values[field] < 0:
                raise ValueError('Hourly wage must be a non-negative number')
    if values.get('s_status', '') not in ('', 'retired'):
        raise ValueError('Invalid account status')
    if login == Environment.get_security().get_user_name() and values.get('s_status') == 'retired':
        raise ValueError('You cannot retire the account you are signed in with')
    for search_type in ('sthpw/login_group', 'sthpw/login_in_group', 'sthpw/login'):
        search = Search(search_type); sql = search.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(search_type).get_table())
    search = Search('sthpw/login'); search.set_show_retired(True); search.add_filter('login', login)
    user = search.get_sobject()
    memberships = Search('sthpw/login_in_group'); memberships.add_filter('login', login)
    existing = {row.get_value('login_group') for row in memberships.get_sobjects()}
    if identity:
        if user is None:
            raise ValueError('The selected user no longer exists. Refresh the list.')
        if expected_revision != user_revision(user, existing):
            raise WidgetConfigConflict('User details or memberships changed. Reload before saving.')
    elif user is not None:
        raise ValueError('A user with this login already exists')
    desired = set(groups)
    if desired:
        search = Search('sthpw/login_group'); search.add_filters('login_group', sorted(desired))
        if desired - {row.get_value('login_group') for row in search.get_sobjects()}:
            raise ValueError('The selected user group no longer exists. Refresh the list.')
    # Avoid signing the current administrator out halfway through the atomic write.
    if identity == Environment.get_security().get_user_name() and identity != 'admin' and 'admin' in existing and 'admin' not in desired:
        raise ValueError('You cannot remove your own administrator membership')
    if user is None:
        values = {field: value for field, value in values.items() if value not in (None, '')}
        user = Login.create(login, password, groups=sorted(desired), project_code=values.get('project_code'))
    for field, value in values.items():
        if field != 's_status':
            user.set_value(field, value)
    user.commit()
    if 's_status' in values and values['s_status'] != (user.get_value('s_status') or ''):
        user.retire() if values['s_status'] == 'retired' else user.reactivate()
    if identity and password:
        user.set_password(password)
    # Read again after Login.create: native creation may have assigned a default group.
    memberships = Search('sthpw/login_in_group'); memberships.add_filter('login', login)
    existing = {row.get_value('login_group') for row in memberships.get_sobjects()}
    if not identity and not groups:
        desired = existing  # Login.create's native default group, as in Handler.
    for group in sorted(desired - existing):
        user.add_to_group(group)
    for group in sorted(existing - desired):
        user.remove_from_group(group)
    return login


def security_users_request(action, payload):
    _require_admin()
    if action == 'read':
        return query_security_users()
    command = Command()
    command.execute = lambda: save_security_user(payload.get('identity', ''), payload.get('document'), payload.get('expected_revision', ''))
    command.get_transaction().set_sync(False)
    selected = Command.execute_cmd(command)
    return dict(**query_security_users(), selected=selected)
