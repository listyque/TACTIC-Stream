"""Presentation-free semantics of TACTIC subscriptions and message rendering.

Existing tables remain authoritative: message is the latest event,
message_log is history, subscription.last_cleared is an acknowledgement
watermark. It is NOT a delivery/read receipt or presence indicator.
"""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone


def timestamp(value):
    """Comparable database timestamp; no claim about the installation's timezone."""
    if value in (None, ''):
        return None
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def is_new(message_time, cleared_time):
    current, cleared = timestamp(message_time), timestamp(cleared_time)
    return current is not None and (cleared is None or current > cleared)


def in_project(value, project):
    # Original ChatCmd did not write project_code. Preserve those legacy
    # conversations only for their actual subscribers, never as public chats.
    return value in (None, '', project)


def add_project_scope(search, project, table=''):
    search.add_op('begin')
    search.add_filter('project_code', project, table=table)
    search.add_filter('project_code', None, table=table)
    search.add_filter('project_code', '', table=table)
    search.add_op('or')


def subscription_search(login, project, category='', only_new=False):
    """Original SubscriptionWdg join/order, with an effective new/all switch.

    SubscriptionWdg accidentally overwrote mode with 'nnn'. The native
    switch uses the intended last_cleared < message.timestamp predicate.
    """
    from pyasm.search import Search
    search = Search('sthpw/subscription')
    search.add_filter('login', login)
    add_project_scope(search, project)
    # Search resolves this join through the ORIGINAL Schema.
    search.add_order_by('message.timestamp', direction='desc')
    add_project_scope(search, project, table='message')
    if category:
        search.add_filter('category', category)
    if only_new:
        search.add_where('"message"."timestamp" IS NOT NULL')
        search.add_op('begin')
        search.add_filter('last_cleared', '"message"."timestamp"', quoted=False, op='<')
        search.add_filter('last_cleared', None)
        search.add_op('or')
    search.add_order_by('id', direction='desc')
    return search


def message_content(raw, category='default'):
    """Data projection of FormatMessageWdg, never HTML, eval or executable JS."""
    result = {'text': '', 'kind': category or 'default', 'progress': None, 'changes': []}
    value = raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                value = decoded
        except (ValueError, TypeError):
            pass
    if not isinstance(value, dict):
        result['text'] = '' if raw is None else str(raw)
        return result
    if category == 'sobject':
        stype = str(value.get('search_type') or '')
        obj = value.get('sobject') if isinstance(value.get('sobject'), dict) else {}
        updates = value.get('update_data') if isinstance(value.get('update_data'), dict) else {}
        result['object'] = {'search_type': stype, 'code': str(obj.get('code') or '')}
        if stype.split('?')[0] == 'sthpw/note':
            result['text'] = 'Комментарий: ' + str(updates.get('note') or '')
        elif stype.split('?')[0] == 'sthpw/task':
            result['text'] = 'Изменена задача: ' + str(updates.get('process') or obj.get('process') or '')
        elif stype.split('?')[0] == 'sthpw/snapshot':
            result['text'] = 'Check-in: ' + str(obj.get('process') or obj.get('context') or '')
        else:
            result['text'] = 'Архивирование' if value.get('mode') == 'retire' else 'Изменение объекта'
        result['changes'] = [{'field': str(k), 'value': v} for k, v in updates.items()]
    else:
        content = value.get('message')
        if content is None:
            content = value.get('description', '')
        result['text'] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    if category == 'progress':
        try:
            percent = float(value.get('progress', 0))
            result['progress'] = max(0.0, min(100.0, percent)) if math.isfinite(percent) else None
        except (ValueError, TypeError):
            pass
    if not result['text'] and not result['changes']:
        result['text'] = json.dumps(value, ensure_ascii=False, default=str)
    return result


def object_message_key(obj):
    """Same key construction as SObject._add_message; do not invent a topic ID."""
    stype = obj.get_base_search_type()
    if stype in ('sthpw/note', 'sthpw/task', 'sthpw/snapshot'):
        parent_type = obj.get_value('search_type', no_exception=True)
        code = obj.get_value('search_code', no_exception=True)
        if not parent_type or not code:
            raise ValueError('У записи нет родителя для подписки')
        return '%s&code=%s' % (parent_type, code)
    if stype.startswith(('sthpw/', 'config/')):
        raise ValueError('SObject._add_message не публикует события этого системного типа')
    return obj.get_search_key()
