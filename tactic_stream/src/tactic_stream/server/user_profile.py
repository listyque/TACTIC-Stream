"""Handler UserController projections and native profile mutations (EPL-1.0)."""
import hashlib
import json
import math
import re
import uuid
from pathlib import Path

from pyasm.biz import Project, Pipeline, IconCreator
from pyasm.command import Command
from pyasm.common import Environment, Container
from pyasm.security.access_manager import Sudo
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType, FileUndo
from .security_groups import user_identities, user_directory
from .security_users import FIELDS
from .messages import _require_access
from .widget_configuration import WidgetConfigConflict
from . import user_profile_query as native
from .group_authority import ranked_groups

SELF_FIELDS = FIELDS[:7]


def authority():
    # Keep the established account policy: a group name cannot grant admin rights.
    return Environment.get_security().is_admin()


def selected_user(login):
    _require_access('sthpw/login', 'view', 'allow')
    if not isinstance(login, str) or not login or len(login) > 256:
        raise ValueError('Choose an existing user')
    search = Search('sthpw/login'); search.set_show_retired(authority()); search.add_filter('login', login)
    user = search.get_sobject()
    if not user:
        raise ValueError('The selected user does not exist')
    return user


def group_catalog(group_objects=None):
    rows = group_objects if group_objects is not None else Search('sthpw/login_group').get_sobjects()
    return sorted([dict(code=row.get_value('login_group'), label=(row.get_value('name', no_exception=True) or row.get_value('login_group').replace('_', ' ')).title(),
                 description=row.get_value('description') or '', accessLevel=row.get_value('access_level') or '',
                 projectCode=row.get_value('project_code') or '', isDefault=bool(row.get_value('is_default')))
            for row in rows], key=lambda row: row['code'])


def membership(login):
    search = Search('sthpw/login_in_group'); search.add_filter('login', login)
    return sorted({row.get_value('login_group') for row in search.get_sobjects()})


def revision(user, assigned=None, groups=None):
    avatars = Search('sthpw/snapshot'); avatars.add_sobject_filter(user); avatars.add_filter('context', 'icon')
    value = [user.get_data(), assigned if assigned is not None else membership(user.get_value('login')),
             groups if groups is not None else group_catalog(), [row.get_data() for row in avatars.get_sobjects()]]
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def read_profile(login):
    user = selected_user(login); privileged = authority(); current = login == Environment.get_user_name()
    identity = user_identities([user])[0]
    group_objects = Search('sthpw/login_group').get_sobjects()
    groups = group_catalog(group_objects); assigned = membership(login)
    columns = set(SearchType.get_columns('sthpw/login'))
    profile = {name: user.get_value(name) or '' for name in SELF_FIELDS if name in columns}
    profile['phone_number'] = next((user.get_value(name, no_exception=True) for name in ('phone_number', 'phone', 'telephone', 'mobile') if user.get_value(name, no_exception=True)), '')
    roles = user.get_value('roles', no_exception=True) or user.get_value('role', no_exception=True) or []
    if not isinstance(roles, (list, tuple, set)): roles = str(roles).replace('|', ',').split(',')
    roles = [str(part).strip() for part in roles if str(part).strip()]
    rules_by_code = {item.get_value('login_group'): item.get_value('access_rules') for item in group_objects}
    ranked = ranked_groups([dict(row, accessRules=rules_by_code.get(row['code'], '')) for row in groups], Project.get_project_code())
    profile.update(identity, current=current, searchKey=user.get_search_key(), groups=[row for row in ranked if row['code'] in assigned],
                   roles=list(roles), project=Project.get().get_value('title') or Project.get_project_code())
    for row in profile['groups']: row.pop('accessRules', None)
    document = None
    if current or privileged:
        fields = [field for field in (FIELDS if privileged else SELF_FIELDS) if field in columns]
        document = {field: str(user.get_value(field)) if user.get_value(field) is not None else '' for field in fields}
        document.update(login=login, password='', groups=assigned)
    identities = user_directory(Search('sthpw/login').get_sobjects())
    return dict(profile=profile, users=identities,
                groups=groups if privileged else [], document=document,
                revision=revision(user, assigned=assigned, groups=groups) if document is not None else '',
                permissions=dict(edit=current or privileged, manage=privileged))


def profile_summary(login):
    selected_user(login)
    _require_access('sthpw/task', 'view', 'allow')
    data = json.loads(native.query_user_profile_data(login, Project.get_project_code()))
    if data.get('permissions', {}).get('viewWorkHours'): _require_access('sthpw/work_hour', 'view', 'allow')
    for key in ('statusSummary', 'processSummary'):
        for row in data.get(key, []):
            pipeline = Pipeline.get_by_code(row.get('pipeline_code') or 'task')
            node = pipeline.get_process(row.get('status')) if pipeline else None
            if key == 'processSummary':
                pipelines = Pipeline.get_by_search_type(row.get('search_type'), Project.get_project_code()) if row.get('search_type') else []
                node = next((pipe.get_process(row.get('process')) for pipe in pipelines if pipe.get_process(row.get('process'))), None)
            row.update(value=row.get('status' if key == 'statusSummary' else 'process') or '',
                       color=node.get_attribute('color') or '' if node else '')
    return data


def validate_document(document, privileged):
    if not isinstance(document, dict) or set(document) - set((*FIELDS, 'login', 'password', 'groups', 'accessLevels')):
        raise ValueError('Invalid user document')
    values = {key: value for key, value in document.items() if key in FIELDS}
    if not privileged and (set(values) - set(SELF_FIELDS) or 'accessLevels' in document):
        raise SecurityException('You may only edit your own profile fields')
    columns = set(SearchType.get_columns('sthpw/login'))
    for key, value in values.items():
        if key not in columns or not isinstance(value, str) or len(value.encode()) > 65536 or '\x00' in value:
            raise ValueError('Invalid user profile field')
    if values.get('s_status', '') not in ('', 'retired'):
        raise ValueError('Invalid account status')
    if values.get('hourly_wage'):
        value = float(values['hourly_wage'])
        if not math.isfinite(value) or value < 0: raise ValueError('Hourly wage must be a non-negative number')
    password = document.get('password', '')
    groups = document.get('groups')
    if not isinstance(password, str) or len(password) > 4096:
        raise ValueError('Invalid password')
    if groups is not None:
        if not isinstance(groups, list) or len(groups) > 10000 or any(not isinstance(row, str) or len(row) > 256 for row in groups):
            raise ValueError('Invalid user groups')
        if set(groups) - {row['code'] for row in group_catalog()}:
            raise ValueError('The selected user group no longer exists. Refresh the list.')
    levels = document.get('accessLevels')
    if levels is not None and (not isinstance(levels, dict) or len(levels) > 10000 or any(
            not isinstance(key, str) or value not in ('', 'high', 'medium', 'low', 'min', 'none') for key, value in levels.items())):
        raise ValueError('Invalid group access levels')
    return values, password, groups, levels


def write_profile(action, payload, uploads):
    login = payload.get('login'); privileged = authority()
    if action == 'create':
        if not privileged: raise SecurityException('Only an administrator or supervisor can create users')
        if not isinstance(login, str) or not login or len(login) > 256 or re.search(r'[\s/\\<>\x00-\x1f]', login):
            raise ValueError('Enter a login without spaces or slashes')
    elif login != Environment.get_user_name() and not privileged:
        raise SecurityException('You may only edit your own profile')
    for search_type in ('sthpw/login', 'sthpw/login_group', 'sthpw/login_in_group'):
        search = Search(search_type); sql = search.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(search_type).get_table())
    user = None if action == 'create' else selected_user(login)
    if user and action != 'avatar' and payload.get('revision') != revision(user):
        raise WidgetConfigConflict('User details or memberships changed. Reload before saving.')
    if action == 'avatar':
        Container.get('UserProfile:writing')['code'] = user.get_code()
        upload_avatar(user, uploads, payload.get('token'), payload.get('revision'))
    else:
        values, password, groups, levels = validate_document(payload.get('document'), privileged)
        if not privileged and groups is not None and sorted(set(groups)) != membership(login):
            raise SecurityException('Only a supervisor can change user groups')
        if login == Environment.get_user_name() and privileged and login != 'admin' and groups is not None:
            own = membership(login)
            if 'admin' in own and 'admin' not in groups: raise ValueError('You cannot remove your own administrator membership')
        # Native Login.commit requires Sudo even for the validated self fields.
        sudo = Sudo()
        try:
            if action == 'create': native.create_user_profile(login, values=values, password=password, groups=groups)
            else: native.mutate_user_profile(login, values=values, password=password, groups=groups if privileged else None, group_access_levels=levels)
        except PermissionError as error:
            raise SecurityException(str(error)) from error
        finally:
            if sudo: sudo.exit()
    return read_profile(login)


def upload_avatar(user, uploads, token, expected_revision):
    from PIL import Image
    import io
    from pyasm.checkin import FileCheckin
    from .api import upload_file_name
    for search_type in ('sthpw/snapshot', 'sthpw/file'):
        _require_access(search_type, 'edit')
    if not uploads or len(uploads) != 1: raise ValueError('Choose one avatar image')
    name, content = uploads[0]; name = upload_file_name(name); token = uuid.UUID(token).hex
    if Path(name).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp') or len(content) > 10 * 1024 * 1024:
        raise ValueError('Choose a JPG, PNG, or WEBP image up to 10 MB')
    try:
        with Image.open(io.BytesIO(content)) as image: image.verify()
    except Exception as error: raise ValueError('Choose a valid avatar image') from error
    search = Search('sthpw/snapshot'); search.add_sobject_filter(user); search.add_filter('context', 'icon')
    identity = dict(token=token, name=name, sha256=hashlib.sha256(content).hexdigest(), login=Environment.get_user_name())
    for snapshot in search.get_sobjects():
        existing = snapshot.get_json_value('metadata', {}).get('profileUpload', {})
        if existing.get('token') == token:
            if existing != identity: raise ValueError('Avatar identity was already used for another file')
            return
    if expected_revision != revision(user):
        raise WidgetConfigConflict('User details or memberships changed. Reload before saving.')
    directory = Path(Environment.get_upload_dir()) / ('avatar_' + token)
    scope = Container.get('UserProfile:writing')
    scope.update(code=user.get_code(), paths={str(directory.resolve()), str((Path(Environment.get_tmp_dir()) / 'undo').resolve())})
    FileUndo.mkdir(str(directory)); path = directory / name
    FileUndo.create(str(path), io_action=False); path.write_bytes(content)
    creator = IconCreator(str(path)); creator.execute()
    paths, types = [str(path)], ['main']
    for kind, value in (('web', creator.get_web_path()), ('icon', creator.get_icon_path())):
        if value: paths.append(value); types.append(kind)
    checkin = FileCheckin(user, paths, file_types=types, context='icon', process='icon', description='User avatar',
                         mode='create', source_paths=paths, keep_file_name=False, do_update_versionless=True)
    checkin.execute(); snapshot = checkin.get_snapshot()
    snapshot.add_metadata({'profileUpload': identity}, replace=False); snapshot.commit(triggers=False)
    if not any(directory.iterdir()): FileUndo.rmdir(str(directory))


def user_profile_request(action, payload, uploads=None):
    project = Project.get_project_code()
    if Project.get() is None: raise ValueError('Profile project does not exist')
    if project not in ('admin', 'sthpw') and not Environment.get_security().check_access(
            'project', [{'code':project}, {'code':'*'}], 'allow', default='deny'):
        raise SecurityException('Profile project is not accessible')
    if action == 'read': return read_profile(payload.get('login'))
    if action == 'summary': return profile_summary(payload.get('login'))
    if action not in ('save', 'create', 'avatar'): raise ValueError('Unknown user profile operation')
    login, privileged = payload.get('login'), authority()
    if not privileged and (action == 'create' or login != Environment.get_user_name()):
        raise SecurityException('You may only edit your own profile')
    previous = Container.get('UserProfile:writing')
    try:
        Container.put('UserProfile:writing', dict(login=login, manage=privileged, avatar=action == 'avatar', project=Project.get_project_code()))
        command = Command(); command.execute = lambda: write_profile(action, payload, uploads)
        command.get_transaction().set_sync(False)
        return Command.execute_cmd(command)
    finally:
        Container.put('UserProfile:writing', previous)
