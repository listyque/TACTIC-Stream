"""Handler skey_previews descriptors on the shared protected native link resolver.

Layout and projections follow thlib/ui/skey_previews.py and SKeyPreviewCard.qml.
Qt scheduling and Repository Sync are replaced by the authenticated web request.
"""
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

from pyasm.biz import Snapshot
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchKey, SearchType
from pyasm.widget import ThumbWdg
from .navigation_links import navigation_link_request, check_type
from .security_groups import user_identities
from .table_cells import safe_link
from .file_presentation import file_display, repository_display

SKEY_PATTERN = re.compile(r'skey://[^\s<>\"]+')


def extract_skeys(value):
    return list(dict.fromkeys(match.group().rstrip('.,;:!?)]}') for match in SKEY_PATTERN.finditer(str(value or ''))))


def pretty_size(value):
    size = float(value or 0)
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    return ('{:.0f} {}' if unit == 0 else '{:.1f} {}').format(size, units[unit])


def thumbnail(obj):
    try:
        check_type('sthpw/snapshot', obj.get_value('project_code', no_exception=True) or SearchKey.extract_project(obj.get_search_key()))
        check_type('sthpw/file', obj.get_value('project_code', no_exception=True) or SearchKey.extract_project(obj.get_search_key()))
    except SecurityException:
        return ''
    widget = ThumbWdg(name='snapshot')
    widget.set_options({'protocol': 'http'})
    widget.set_sobjects([obj]); widget.preprocess(); widget.set_current_index(0)
    return safe_link(widget.get_cell_value()['image'])


def author_identity(author):
    from .messages import _access
    if not author or not _access('sthpw/login', 'view', 'edit'):
        return {}
    login = Search('sthpw/login'); login.add_filter('login', author)
    identity = user_identities(login.get_sobjects())
    return identity[0] if identity else {}


def describe(key, *, nested=True):
    resolved = navigation_link_request({'link': key}, preview=True)
    info = resolved['object']
    base, kind = resolved['searchType'], resolved['kind']
    kind = 'user' if base == 'sthpw/login' else 'knowledge' if base.endswith('/th_knowledge_article') else 'sobject' if kind == 'object' else kind
    if kind == 'chat-attachment':
        kind = 'snapshot' if base == 'sthpw/snapshot' else 'file'
    code, project = str(info.get('code') or info.get('id') or ''), resolved['project']
    parent = resolved.get('parent') or {}
    parent_key = 'skey://' + parent['__search_key__'] if parent else ''
    definition = SearchType.get(base)
    item = dict(searchKey=key, status='ready', kind=kind, title=resolved['title'] or code or 'TACTIC item',
                subtitle=definition.get_title(), detail=' · '.join(value for value in (code, project) if value),
                description=info.get('description') or '', previewUrl='', itemCode=code,
                icon={'sobject': 'inventory_2', 'task': 'task_alt', 'snapshot': 'photo_library', 'file': 'description', 'note': 'sticky_note_2', 'message': 'chat', 'user': 'person', 'project': 'folder_special', 'knowledge': 'article'}[kind],
                parentKey=parent_key, openKey=parent_key or key, process=resolved['process'])
    if kind == 'task':
        item.update(title=str(info.get('process') or 'Task').replace('_', ' ').title(),
                    subtitle=' · '.join([info.get('assigned') or info.get('login') or 'Unassigned', info.get('status') or 'No status']),
                    detail=' · '.join(str(value) for value in (parent.get('title') or parent.get('name') or info.get('search_code'), info.get('bid_end_date') or info.get('end_date')) if value))
    elif kind in ('note', 'message'):
        author = str(info.get('login') or 'Unknown user')
        identity = author_identity(author)
        body = str(info.get('note' if kind == 'note' else 'message') or '')
        item.update(author=author, authorDisplay=identity.get('displayName') or author,
                    avatarUrl=identity.get('avatarUrl') or '',
                    initials=identity.get('initials') or author[:2].upper(),
                    authorColor=identity.get('avatarColor') or '', timestamp=info.get('timestamp') or '',
                    body=SKEY_PATTERN.sub('', body).strip() if kind == 'note' else body, detail=info.get('timestamp') or '',
                    title=('Note by ' if kind == 'note' else 'Message by ') + author)
        if kind == 'message':
            item.update(conversationId=resolved['conversationId'], itemCode=info['__search_key__'], canOpen=True)
        else:
            keys = extract_skeys(body) if nested else []
            item.update(nestedPreviewCount=len(keys), nestedPreviews=[preview(key, nested=False) for key in keys[:4]])
            check_type('sthpw/snapshot', project); check_type('sthpw/file', project)
            note = SearchKey.get_by_search_key(info['__search_key__'])
            attachments = []
            for snapshot in Snapshot.get_by_sobjects([note], process='attachment'):
                for file in snapshot.get_all_file_objects():
                    if file.get_value('type') in ('icon', 'web'):
                        continue
                    name = file.get_value('file_name') or 'File'
                    attachments.append(dict(title=name, extension=Path(name).suffix.lstrip('.').upper(), size=pretty_size(file.get_value('st_size')),
                                            searchKey='skey://' + snapshot.get_search_key(), previewUrl=thumbnail(snapshot)))
            item.update(attachments=attachments[:6], attachmentCount=len(attachments))
    elif kind == 'snapshot':
        snapshot = resolved.get('snapshot')
        obj = SearchKey.get_by_search_key(info['__search_key__'])
        if snapshot:
            files = snapshot['__files__']
        else:
            check_type('sthpw/file', project)
            files = [file.get_data() for file in obj.get_all_file_objects()]
        main = [file for file in files if file.get('type') not in ('web', 'icon', 'playblast')]
        group = [file for file in main if file.get('type') == main[0].get('type')] if main else []
        primary = group[0] if group else {}
        version, revision = int(info.get('version') or 0), int(info.get('revision') or 0)
        metadata = obj.get_json_value('metadata', default={})
        file_obj = Search.get_by_code('sthpw/file', primary['code']) if primary else None
        display = file_display(file_obj, info.get('context') or '')
        title = ('Multiple files | ' + str(len(group))) if len(group) > 1 else metadata.get('chatAttachment', {}).get('name') or display['title'] or info.get('context') or code
        item.update(title=title, openKey=key, context=info.get('context') or '',
                    version='latest' if version in (-1, 0) else 'v{:03d}'.format(version), revision='r{:03d}'.format(revision) if revision else '',
                    author=author_identity(info.get('login')).get('displayName') or info.get('login') or '', timestamp=str(info.get('timestamp') or '').split('.')[0],
                    fileSize=pretty_size(primary.get('st_size')) if primary else '',
                    fileExtension=Path(primary.get('file_name') or '').suffix.lstrip('.').upper(),
                    fileExists=bool(file_obj and Path(file_obj.get_lib_path()).is_file()), isLatest=bool(info.get('is_latest')),
                    isVersionless=version in (-1, 0), isMultiple=len(group) > 1,
                    infoChips=display['infoChips'], **repository_display(info.get('repo') or ''))
        if snapshot:
            item['privateAttachment'] = dict(chat=resolved['conversationId'], snapshot=snapshot, fileCode=resolved['fileCode'])
        else:
            item['previewUrl'] = resolved.get('preview', {}).get('image') or ''
    elif kind == 'file':
        filename = info.get('file_name') or code
        item.update(title=filename, subtitle='{} file · {}'.format(Path(filename).suffix.lstrip('.').upper() or 'FILE', info.get('type') or 'main'),
                    detail=' · '.join(value for value in (pretty_size(info.get('st_size')), info.get('snapshot_code'), parent.get('title') or parent.get('name')) if value),
                    openKey='skey://sthpw/snapshot?code=' + info['snapshot_code'] if info.get('snapshot_code') else parent_key or key)
    elif kind == 'user':
        item.update(title=info.get('displayName') or code, subtitle='TACTIC user', previewUrl=info.get('avatarUrl') or '', openKey=key)
    elif kind == 'project':
        item.update(subtitle='TACTIC project', openKey=key)
    elif kind == 'knowledge':
        article_kind = info.get('kind') if info.get('kind') in ('article', 'section') else 'article'
        item.update(articleKind=article_kind, excerpt=' '.join(str(info.get('content_text') or '').split())[:180], openKey=key)
    if kind in ('sobject', 'project', 'knowledge'):
        item['previewUrl'] = thumbnail(SearchKey.get_by_search_key(info['__search_key__']))
    return item


def unavailable(key):
    try:
        parsed = urlsplit(key)
        values = dict(parse_qsl(parsed.query))
        base = parsed.netloc + parsed.path
    except ValueError:
        values, base = {}, ''
    kind = {'sthpw/task': 'task', 'sthpw/snapshot': 'snapshot', 'sthpw/file': 'file', 'sthpw/note': 'note', 'sthpw/message_log': 'message', 'sthpw/login': 'user', 'sthpw/project': 'project'}.get(base, 'knowledge' if base.endswith('/th_knowledge_article') else 'sobject')
    return dict(searchKey=key, status='error', kind=kind, title=values.get('code') or values.get('id') or 'TACTIC item', error='Link preview is unavailable')


def preview(key, *, nested=True):
    try:
        return describe(key, nested=nested)
    except (ValueError, LookupError, PermissionError, SecurityException):
        return unavailable(key)
    except Exception:
        # Per-card failures reveal no object metadata or server traceback.
        import logging
        logging.getLogger(__name__).exception('Link preview failed')
        return unavailable(key)


def preview_links_request(keys):
    if (not isinstance(keys, list) or not 1 <= len(keys) <= 50 or
            any(not isinstance(key, str) or not key.startswith('skey://') or len(key) > 16384 or any(char in key for char in '\r\n\x00') for key in keys)):
        raise ValueError('Choose between 1 and 50 valid sKeys')
    return {'previews': [preview(key) for key in dict.fromkeys(keys)]}
