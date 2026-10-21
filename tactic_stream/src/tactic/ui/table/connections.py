"""Connection cells and revision-guarded removal using original TACTIC records."""
# Copyright (c) 2005-2008 Southpaw Technology. MIT; see LICENSE.TACTIC.
from pyasm.command import Command


def read_connection_cells(search_keys, direction='dst', icon_size=60):
    import hashlib
    import json
    from pyasm.biz import Project, SObjectConnection
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey
    from pyasm.widget import ThumbWdg

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if direction not in ('src', 'dst'):
        raise ValueError('Invalid connection direction')
    if type(icon_size) is not int or not 16 <= icon_size <= 256:
        raise ValueError('Invalid connection icon size')
    if not isinstance(search_keys, list) or len(search_keys) > 500:
        raise ValueError('Invalid connection table scope')
    project = Project.get_project_code()
    for key in search_keys:
        if not isinstance(key, str) or SearchKey.extract_project(key) not in (None, '', 'sthpw', 'admin', project):
            raise ValueError('The configured table target belongs to another project')
    parents = Search.get_by_search_keys(search_keys, keep_order=True)
    if len(parents) != len(search_keys) or any(parent is None for parent in parents):
        raise LookupError('Object is no longer available')
    private_types = ('sthpw/message', 'sthpw/message_log')
    if any(parent.get_base_search_type() in private_types for parent in parents):
        raise ValueError('Open private messages from Messages')
    grouped = {}
    connections = {}
    result = {}
    for parent in parents:
        key = parent.get_search_key()
        result[key] = dict(text='', targetSearchKey=key, direction=direction, iconSize=icon_size, connectionRows=[])
        if parent.get_base_search_type() == 'sthpw/connection':
            if parent.get_value('project_code') == project:
                connections[key] = [(parent, direction)]
        else:
            grouped.setdefault(parent.get_search_type(), []).append(parent)
    for search_type, group in grouped.items():
        query = Search(SObjectConnection)
        query.add_filter('project_code', project)
        query.add_filter(direction + '_search_type', search_type)
        query.add_filters(direction + '_search_id', [parent.get_id() for parent in group])
        by_id = {parent.get_id(): parent.get_search_key() for parent in group}
        for connection in query.get_sobjects():
            key = by_id[connection.get_value(direction + '_search_id')]
            connections.setdefault(key, []).append((connection, 'src' if direction == 'dst' else 'dst'))
    target_groups = {}
    for group in connections.values():
        for connection, endpoint in group:
            search_type = connection.get_value(endpoint + '_search_type')
            if SearchKey.extract_base_search_type(search_type) in private_types:
                raise ValueError('Open private messages from Messages')
            target_groups.setdefault(search_type, set()).add(connection.get_value(endpoint + '_search_id'))
    targets = {}
    for search_type, identities in target_groups.items():
        for target in Search.get_by_id(search_type, list(identities)):
            targets[(search_type, target.get_id())] = target
    thumbs = list({target.get_search_key(): target for target in targets.values()}.values())
    thumb = ThumbWdg(name='preview')
    thumb.set_sobjects(thumbs)
    thumb.preprocess()
    previews = {}
    for index, target in enumerate(thumbs):
        thumb.set_current_index(index)
        if hasattr(thumb, 'get_cell_value'):
            previews[target.get_search_key()] = thumb.get_cell_value()
        else:
            from urllib.parse import unquote, urlsplit
            link = thumb.get_data(target) or ''
            image = thumb.info.get('icon') or thumb.info.get('web') or link
            if urlsplit(image).path.lower().rsplit('.', 1)[-1] not in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'avif'):
                image = ''
            previews[target.get_search_key()] = dict(image=image, text=link,
                filename=unquote(urlsplit(link).path.rsplit('/', 1)[-1]))
    for parent_key, group in connections.items():
        for connection, endpoint in group:
            target = targets.get((connection.get_value(endpoint + '_search_type'), connection.get_value(endpoint + '_search_id')))
            revision = hashlib.sha256(json.dumps(connection.get_data(), sort_keys=True, default=str).encode()).hexdigest()
            row = dict(connectionKey=connection.get_search_key(), expectedRevision=revision, available=target is not None)
            if target is not None:
                target_key = target.get_search_key()
                row.update(searchKey=target_key, code=target.get_code(),
                    name=target.get_value('name', no_exception=True) or target.get_display_value(),
                    description=target.get_value('title', no_exception=True) or target.get_value('description', no_exception=True) or '',
                    keywords=target.get_value('keywords', no_exception=True) or '',
                    retired=target.is_retired(), preview=previews[target_key])
            result[parent_key]['connectionRows'].append(row)
    return result


def remove_connection(parent_key, connection_key, expected_revision, direction='dst'):
    import hashlib
    import json
    from pyasm.biz import Project
    from pyasm.common import Environment, UserException
    from pyasm.search import Search, SearchKey

    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if direction not in ('src', 'dst'):
        raise ValueError('Invalid connection direction')
    if not isinstance(parent_key, str) or SearchKey.extract_project(parent_key) not in (None, '', 'sthpw', 'admin', Project.get_project_code()):
        raise ValueError('The configured table target belongs to another project')
    if not isinstance(connection_key, str) or SearchKey.extract_base_search_type(connection_key) != 'sthpw/connection':
        raise ValueError('Select a connection before removing it')
    if not isinstance(expected_revision, str) or not expected_revision or len(expected_revision) > 128:
        raise ValueError('Reload the connection before removing it')
    selected = Search.get_by_search_key(connection_key)
    parent = Search.get_by_search_key(parent_key)
    if parent is None and not (selected is None and SearchKey.extract_base_search_type(parent_key) == 'sthpw/connection'):
        raise LookupError('Object is no longer available')
    private_types = ('sthpw/message', 'sthpw/message_log')
    if parent is not None and parent.get_base_search_type() in private_types:
        raise ValueError('Open private messages from Messages')
    removed = dict(state='removed', parentKey=parent_key, connectionKey=connection_key)
    if selected is None:
        return removed
    if selected.get_value('project_code') != Project.get_project_code():
        raise ValueError('The connection belongs to another project')
    sql = selected.get_sql()
    lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
    if lock:
        lock(sql, 'connection')
    elif sql.get_database_type() == 'PostgreSQL':
        sql.do_update('LOCK TABLE "connection" IN EXCLUSIVE MODE')
    else:
        raise ValueError('Connection revisions require a transactional database lock')
    # Identity reads can retain the pre-lock object in the request cache.
    fresh = Search('sthpw/connection')
    fresh.add_id_filter(selected.get_id())
    selected = fresh.get_sobject()
    if selected is None:
        return removed
    if selected.get_value('project_code') != Project.get_project_code():
        raise ValueError('The connection belongs to another project')
    if any(SearchKey.extract_base_search_type(selected.get_value(endpoint + '_search_type')) in private_types for endpoint in ('src', 'dst')):
        raise ValueError('Open private messages from Messages')
    if parent.get_base_search_type() == 'sthpw/connection':
        belongs = parent.get_id() == selected.get_id()
    else:
        belongs = (selected.get_value(direction + '_search_type') == parent.get_search_type()
            and selected.get_value(direction + '_search_id') == parent.get_id())
    revision = hashlib.sha256(json.dumps(selected.get_data(), sort_keys=True, default=str).encode()).hexdigest()
    if not belongs or revision != expected_revision:
        raise UserException('Connection changed. Reload before removing it.')
    selected.delete()
    return removed


class TableConnectionRemoveCmd(Command):
    def execute(self):
        self.info = remove_connection(**self.kwargs)
        return self.info
