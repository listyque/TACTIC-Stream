"""Handler search_links / parce_skey / SkeyPreviewController on native TACTIC reads."""
from urllib.parse import urlsplit, parse_qsl

from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType, SearchKey
from pyasm.widget import ThumbWdg
from .api import ApiXMLRPC, check_record_access
from .search_configuration import search_configuration_request
from .table_cells import safe_link
from .security_groups import user_identities


def check_article_visibility(obj):
    if not obj.get_base_search_type().endswith('/th_knowledge_article'):
        return
    owner = obj.get_value('login', no_exception=True) or obj.get_value('updated_by', no_exception=True)
    if str(obj.get_value('s_status', no_exception=True) or '').strip().casefold() == 'draft' and owner != Environment.get_login().get_login():
        raise LookupError('TACTIC item was not found')


def check_project(project):
    security = Environment.get_security()
    if not Project.get_by_code(project):
        raise LookupError('Project is not available')
    if project not in ('admin', 'sthpw') and not (security.check_access('project', {'code': '*'}, 'allow', default='deny')
            or security.check_access('project', {'code': project}, 'allow', default='deny')):
        raise SecurityException('Project is not available')


def check_type(search_type, project):
    base = search_type.split('?')[0]
    if base == 'sthpw/transaction_log':
        from .transaction_journal import check_access
        check_access()
    else:
        check_record_access(base)
    keys = [{'code': base}, {'code': base, 'project': project}, {'code': '*'}, {'code': '*', 'project': project}]
    if not Environment.get_security().check_access('search_type', keys, 'view', default='allow' if base.startswith('sthpw/') else 'deny'):
        raise SecurityException('Search Type is not available')


def navigation_link_request(payload, *, preview=False):
    value = payload.get('link')
    if not isinstance(value, str) or not value.strip() or len(value) > 16384 or any(char in value for char in '\r\n\x00'):
        raise ValueError('Invalid TACTIC link')
    parsed = urlsplit(value.strip())
    values = dict(parse_qsl(parsed.query))
    project = values.get('project') or values.get('project_code') or Project.get_project_code()
    if not preview and project != Project.get_project_code():
        raise ValueError('Select the target project before opening its link')
    check_project(project)
    if parsed.scheme.casefold() == 'tactic-search':
        if parsed.netloc not in ('', 'open') or not all(str(values.get(key) or '').strip() for key in ('project', 'search_type', 'view')):
            raise ValueError('Invalid saved search link')
        search_type, view = values['search_type'].strip(), values['view'].strip()
        check_type(search_type, project)
        catalog = search_configuration_request('settings', {'search_type': search_type})
        preset = next((row for row in catalog['presets'] if row['view'] == view), None)
        if not preset:
            raise LookupError('Saved search was not found')
        if preset.get('error'):
            raise ValueError(preset['error'])
        return dict(kind='saved-search', project=project, searchType=search_type.split('?')[0], preset=preset)
    if parsed.scheme.casefold() != 'skey' or not parsed.netloc or not parsed.path.strip('/'):
        raise ValueError('Invalid TACTIC link')
    search_type = parsed.netloc + '/' + parsed.path.lstrip('/')
    identifier = 'code' if values.get('code') else 'id'
    if not values.get(identifier):
        raise ValueError('The link does not identify a TACTIC item')
    check_type(search_type, project)
    search = Search(SearchType.build_search_type(search_type, project))
    if search_type == 'sthpw/transaction_log':
        search.add_filter('namespace', project)
    search.add_filter(identifier, values[identifier]); search.set_limit(1)
    obj = search.get_sobject()
    if not obj:
        raise LookupError('TACTIC item was not found')
    check_article_visibility(obj)
    actual_project = obj.get_value('project_code', no_exception=True) or project
    check_project(actual_project)
    kind = {'sthpw/task': 'task', 'sthpw/note': 'note', 'sthpw/snapshot': 'snapshot', 'sthpw/file': 'file', 'sthpw/project': 'project', 'sthpw/message_log': 'message'}.get(search_type, 'object')
    if kind == 'message':
        from .messages import _message
        _message(obj.get_code())
    if search_type == 'sthpw/message':
        from .messages import _conversation
        _conversation(obj.get_code())
    if search_type == 'sthpw/transaction_log':
        from .transaction_journal import record
        identity = record(obj)
    else:
        identity = ApiXMLRPC._record(obj)
    result = dict(kind=kind, project=actual_project, searchType=search_type, object=identity, title=identity.get('name') or identity.get('title') or identity.get('code') or '', process=values.get('context') or obj.get_value('process', no_exception=True) or '')
    if kind == 'message':
        result['conversationId'] = obj.get_value('message_code')
        result['project'] = project
    if search_type == 'sthpw/login':
        identity = user_identities([obj])[0]
        result['object'] = dict(identity, code=obj.get_code(), __search_key__=obj.get_search_key(), __search_type__=obj.get_search_type())
    if kind == 'project':
        check_project(obj.get_code()); result['project'] = obj.get_code()
    if kind in ('task', 'note', 'snapshot', 'file'):
        snapshot = obj if kind == 'snapshot' else None
        if kind == 'file':
            check_type('sthpw/snapshot', actual_project)
            snapshot = Search.get_by_code('sthpw/snapshot', obj.get_value('snapshot_code'))
            if not snapshot:
                raise LookupError('Snapshot was not found')
            check_project(snapshot.get_value('project_code') or project)
        parent_type = (snapshot or obj).get_value('search_type', no_exception=True)
        if parent_type:
            parent_project = SearchType.breakup_search_type(parent_type).get('project') or actual_project
            check_project(parent_project); check_type(parent_type, parent_project)
            if parent_type.split('?')[0] in ('sthpw/message', 'sthpw/message_log'):
                from .messages import _conversation, _message
                owner = snapshot or obj
                reference = owner.get_value('search_code', no_exception=True) or owner.get_value('search_id', no_exception=True)
                (_conversation if parent_type.split('?')[0] == 'sthpw/message' else _message)(str(reference))
        if snapshot and (parent_type or '').split('?')[0] == 'sthpw/message':
            # Private chat files never receive public repository URLs.
            from .messages_files import attachment_info
            file = obj if kind == 'file' else next((item for item in snapshot.get_all_file_objects() if item.get_value('type') not in ('web', 'icon')), None)
            if file is None:
                raise LookupError('Attachment file was not found')
            info = attachment_info(dict(message_code=snapshot.get_value('search_code'), snapshot_code=snapshot.get_code(), file_code=file.get_code()))
            result.update(kind='chat-attachment', conversationId=snapshot.get_value('search_code'), snapshot=info['snapshot'], fileCode=file.get_code())
            return result
        parent = snapshot.get_sobject() if snapshot else None
        if not snapshot and parent_type:
            # Handler _parent_key follows polymorphic metadata, independently of schema connections.
            code = obj.get_value('search_code', no_exception=True)
            identity = code or obj.get_value('search_id', no_exception=True)
            if identity:
                parent_key = SearchKey.build_search_key(SearchType.build_search_type(parent_type.split('?')[0], parent_project), identity, column='code' if code else 'id')
                parent = Search.get_by_search_key(parent_key)
        if parent:
            check_article_visibility(parent)
            check_project(parent.get_value('project_code', no_exception=True) or actual_project)
            result['parent'] = ApiXMLRPC._record(parent)
        if snapshot:
            result['process'] = snapshot.get_value('context') or result['process']
            widget = ThumbWdg(name='snapshot')
            widget.set_options({'protocol': 'http'}); widget.set_sobjects([snapshot]); widget.preprocess(); widget.set_current_index(0)
            cell = widget.get_cell_value()
            for field in ('image', 'text'):
                cell[field] = safe_link(cell[field])
            for file in cell['files']:
                file['href'] = safe_link(file['href'])
            result['preview'] = cell
            if kind == 'file':
                cell['fileCode'] = obj.get_code()
            if parent:
                cell['object'] = result['parent']
    return result
