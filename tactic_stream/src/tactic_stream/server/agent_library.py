"""User/project chat organization; native requests and WidgetSettings own storage."""
import hashlib
import json
from uuid import uuid4

from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.web import WidgetSettings

KEY = 'external_agent.library'


def revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def metadata(row):
    value = dict(title='', group='', pinned=False, archived=False)
    value.update(row.get('library', {}))
    return value


def groups():
    value = WidgetSettings.get_value_by_key(KEY, default=dict(groups=[]), is_json=True)
    return dict(groups=value.get('groups', []))


def summary(row):
    meta = metadata(row)
    prompt = row['document']['prompt'] or 'Attachments'
    return dict(request_id=row['request_id'], prompt=prompt[:120],
        title=meta['title'] or ('New conversation' if row['status']=='draft' else prompt[:120]),
        default_title=not meta['title'] and (row['status']=='draft' or not row['document']['prompt']),
        status=row['status'], outcome=row.get('outcome', ''),
        activity=row.get('activity', row['created']), search_type=row['document']['context']['search_type'],
        **{key:meta[key] for key in ('group','pinned','archived')}, library_revision=revision(meta))


def state(cmd):
    from tactic.ui.panel.agent_request_cmd import HOST_TTL, ACTIVE, text
    query = text(cmd.kwargs.get('query', ''), 200, empty=True).casefold()
    archived = cmd.kwargs.get('archived', False)
    offset = cmd.kwargs.get('offset', 0)
    if type(archived) is not bool or type(offset) is not int or not 0 <= offset <= 100000:
        raise ValueError('Invalid conversation history filter')
    document = groups()
    # shortcut: search scans owned JSON records; index when real history volume warrants it.
    records = cmd.records('spt_agent_request')
    active = []
    for row in records:
        cmd.expire(row)
        if row['status'] in ACTIVE:
            active.append(dict(request_id=row['request_id'], status=row['status']))
    matching = {row['request_id'] for row in records if not query or query in
        ' '.join(message.get('text', '') for message in row.get('messages', [])).casefold()}
    items = [summary(row) for row in records]
    items = [row for row in items if row['archived']==archived and
        (row['request_id'] in matching or query in (row['title']+' '+row['prompt']+' '+row['search_type']).casefold())]
    items.sort(key=lambda row:(row['pinned'], row['activity'], row['request_id']), reverse=True)
    page = items[offset:offset+100]
    titles = {}
    for row in page:
        name = row['search_type']
        if name not in titles:
            kind = SearchType.get(name, no_exception=True) if name else None
            titles[name] = (kind.get_value('title', no_exception=True) if kind else '') or name
        row['type_title'] = titles[name]
    return dict(hosts=[row for row in cmd.records('spt_agent_host') if cmd.now-row['seen']<=HOST_TTL],
        requests=page, groups=document['groups'], groups_revision=revision(document), total=len(items),
        next_offset=offset+100 if offset+100<len(items) else None, active_requests=active)


def apply(cmd, action):
    from tactic.ui.panel.agent_request_cmd import identity, text, context_document, ACTIVE
    # Match the request command's lock order before locking native settings.
    settings_sql = Search(WidgetSettings.SEARCH_TYPE).get_sql()
    settings_sql.get_database_impl().lock_collection_table(settings_sql, 'wdg_settings')
    document = groups()
    if action == 'draft':
        code = identity(cmd.kwargs.get('request_id'))
        context = context_document(cmd.kwargs.get('context'))
        old = cmd.load('spt_agent_request', code, missing=True)
        if old:
            if old['document']['context'] != context:
                raise ValueError('Conversation ID already belongs to another context')
            return old
        row = dict(request_id=code, document=dict(prompt='', context=context, allow_changes=False, allow_web=False),
            host_id='', status='draft', created=cmd.now, seen=cmd.now, activity=cmd.now,
            messages=[], events=[], answer='', error='', model='', effort='', provider='codex', turn=0)
        cmd.save('spt_agent_request', code, row)
        return row
    if action == 'organize':
        code = identity(cmd.kwargs.get('request_id'))
        row = cmd.load('spt_agent_request', code)
        if cmd.kwargs.get('expected_revision') != revision(metadata(row)):
            raise ValueError('Conversation settings changed. Reload before saving.')
        values = cmd.kwargs.get('document')
        if (not isinstance(values, dict) or set(values)!={'title','group','pinned','archived'}
                or type(values['pinned']) is not bool or type(values['archived']) is not bool):
            raise ValueError('Invalid conversation settings')
        text(values['title'], 160, empty=True)
        text(values['group'], 64, empty=True)
        if values['group'] and not any(group['id']==values['group'] for group in document['groups']):
            raise ValueError('Choose an existing conversation folder')
        if values['archived'] and row['status'] in ACTIVE:
            raise ValueError('Wait for the current turn before archiving this conversation')
        row['library'] = dict(values, title=values['title'].strip())
        cmd.save('spt_agent_request', code, row)
        return row
    if cmd.kwargs.get('expected_revision') != revision(document):
        raise ValueError('Conversation folders changed. Reload before saving.')
    code = cmd.kwargs.get('group', '')
    selected = next((group for group in document['groups'] if group['id']==code), None)
    if code and selected is None:
        raise ValueError('Conversation folder is unavailable')
    if action == 'group_save':
        name = text(cmd.kwargs.get('name'), 120).strip()
        if any(group['id']!=code and group['name'].casefold()==name.casefold() for group in document['groups']):
            raise ValueError('A conversation folder with this name already exists')
        if selected:
            selected['name'] = name
        else:
            if len(document['groups'])>=100:
                raise ValueError('Use at most 100 conversation folders')
            document['groups'].append(dict(id=str(uuid4()), name=name))
    elif action == 'group_remove' and selected:
        document['groups'].remove(selected)
        for row in cmd.records('spt_agent_request'):
            value = metadata(row)
            if value['group']==code:
                row['library'] = dict(value, group='')
                cmd.save('spt_agent_request', row['request_id'], row)
    else:
        raise ValueError('Unknown conversation folder operation')
    WidgetSettings.set_value_by_key(KEY, document)
    return dict(groups=document['groups'], groups_revision=revision(document))
