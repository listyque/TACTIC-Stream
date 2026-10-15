"""Native message/subscription UI over the original TACTIC tables and commands.

Not a new chat database. Inbox authorization always requires the CURRENT
user's subscription, even for an administrator. notification_log is a separate
recipient-scoped email delivery log, not the in-app message stream.
"""
from __future__ import annotations
import copy
import re
import time
from .contracts import ApiError, json_safe, revision, text
from tactic.core.messaging import (add_project_scope, in_project, is_new,
                                  message_content, object_message_key, subscription_search)

MESSAGE_HANDLERS = {'tactic.ui.app.SubscriptionWdg', 'tactic.ui.app.SubscriptionBarWdg',
                    'tactic.ui.app.ChatWdg', 'tactic.ui.app.ChatSessionWdg',
                    'tactic.ui.app.message_wdg.SubscriptionWdg', 'tactic.ui.app.message_wdg.SubscriptionBarWdg',
                    'tactic.ui.app.message_wdg.ChatWdg', 'tactic.ui.app.message_wdg.ChatSessionWdg'}
CHAT_HANDLERS = {s for s in MESSAGE_HANDLERS if s.endswith(('ChatWdg', 'ChatSessionWdg'))}
RECIPIENT_HANDLERS = {'tactic.ui.table.RecipientElementWdg', 'RecipientElementWdg'}
WIKI_HANDLERS = {'WikiElementWdg', 'pyasm.widget.WikiElementWdg', 'tactic.ui.table.WikiElementWdg'}


def page_number(value, name, maximum, default=0):
    if value is None:
        return default
    if isinstance(value, bool) or not re.fullmatch(r'\d{1,19}', str(value)) or not 0 <= int(value) <= maximum:
        raise ApiError(400, 'pagination', 'Некорректный параметр ' + name)
    return int(value)


def raw(obj):
    return obj.get_sobject_dict() if obj is not None else None


def _get(obj, name):
    return obj.get_value(name, no_exception=True) if obj is not None else None


class MessageService:
    def _message_login(self):
        from pyasm.common import Environment
        return Environment.get_user_name()

    def _message_options(self, data):
        """Header bar is global UI; configured widgets additionally restrict options."""
        if not data.get('target'):
            return {}
        screen = self.open_target(data['target'])
        if screen['kind'] != 'message-center' or screen['handler'] not in MESSAGE_HANDLERS:
            raise ApiError(403, 'message_view', 'Этот handler не является экраном сообщений')
        options = dict(screen.get('options') or {})
        if screen['handler'].endswith('SubscriptionWdg'):
            options.setdefault('show_unsubscribe', 'false')
        if screen['handler'] in CHAT_HANDLERS:
            options['category'] = 'chat'
        return options

    def _message_once(self, data, operation, callback):
        """Bounded in-process retry protection, NOT a durable multiworker guarantee."""
        token = data.get('request_id')
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', token):
            raise ApiError(400, 'request_id', 'Нужен уникальный request_id отправки')
        now = time.monotonic()
        cache = getattr(self, '_message_request_cache', {})
        cache = {k: v for k, v in cache.items() if now - v[0] < 900}
        self._message_request_cache = cache
        key = (self.site, self._project(), self._message_login(), operation, token)
        signature = revision({k: v for k, v in data.items() if k not in ('request_id', 'target')})
        if key in cache:
            if cache[key][1] != signature:
                raise ApiError(409, 'request_reused', 'Этот request_id уже использован для другой операции')
            return copy.deepcopy(cache[key][2])
        if len(cache) >= 2000:
            raise ApiError(429, 'retry_cache_full', 'Слишком много отправок; повторите позднее')
        result = callback()
        cache[key] = (now, signature, copy.deepcopy(result))
        return result

    def _channel(self, code, *, allow_missing_message=False):
        from pyasm.search import Search
        code = text(code, 'message_code', 256)
        search = Search('sthpw/subscription')
        search.add_filter('login', self._message_login())
        search.add_filter('message_code', code)
        add_project_scope(search, self._project())
        search.set_limit(3)
        own = search.get_sobjects()
        if not own:
            raise ApiError(403, 'subscription_required', 'У вас нет подписки на эту переписку или событие')
        if len(own) != 1:
            raise ApiError(409, 'duplicate_subscription', 'Есть дубли подписки; требуется устранить их без потери данных')
        search = Search('sthpw/message'); search.add_filter('code', code)
        message = search.get_sobject()
        if message is not None and not in_project(_get(message, 'project_code'), self._project()):
            raise ApiError(403, 'message_project', 'Сообщение относится к другому проекту')
        if message is None and not allow_missing_message:
            raise ApiError(404, 'message_missing', 'По этой подписке ещё нет сообщений')
        return own[0], message

    def _logs(self, code, message):
        from pyasm.search import Search
        search = Search('sthpw/message_log'); search.add_filter('message_code', code)
        # Original chats could be projectless. Their history is global for
        # members only; never mix histories of new project-scoped chats.
        if not (_get(message, 'category') == 'chat' and not _get(message, 'project_code')):
            add_project_scope(search, self._project())
        return search

    def _channel_revision(self, sub, message):
        logs = self._logs(_get(sub, 'message_code'), message)
        logs.add_order_by('id', direction='desc'); logs.set_limit(1)
        last = logs.get_sobject()
        return revision({'subscription': raw(sub), 'message': raw(message), 'latest_log': raw(last)})

    def _message_item(self, obj, category='default'):
        return {'id': str(obj.get_id()), 'code': _get(obj, 'code'),
                'login': _get(obj, 'login'), 'timestamp': json_safe(_get(obj, 'timestamp')),
                'status': _get(obj, 'status'), 'project': _get(obj, 'project_code'),
                'content': message_content(_get(obj, 'message'), _get(obj, 'category') or category)}

    def _subscriptions(self, data, options):
        from pyasm.search import Search
        category = text(options.get('category') or data.get('category') or '', 'category', 256, empty=True)
        mode = data.get('mode', 'all')
        if mode not in ('all', 'new'):
            raise ApiError(400, 'mode', 'Выберите все или новые события')
        offset = page_number(data.get('offset'), 'offset', 1000000)
        limit = page_number(data.get('limit'), 'limit', 100, 40)
        if not limit:
            raise ApiError(400, 'limit', 'Страница не может быть пустой')
        q = subscription_search(self._message_login(), self._project(), category, mode == 'new')
        if options.get('key'):
            q.add_filter('message_code', text(options['key'], 'key', 256))
        total = q.get_count(); q.set_limit(limit); q.set_offset(offset)
        subscriptions = q.get_sobjects()
        codes = sorted({_get(s, 'message_code') for s in subscriptions if _get(s, 'message_code')})
        messages = {}
        if codes:
            qm = Search('sthpw/message'); qm.add_filters('code', codes)
            messages = {m.get_code(): m for m in qm.get_sobjects()}
        items = []
        for sub in subscriptions:
            message = messages.get(_get(sub, 'message_code'))
            # Defense-in-depth in case a custom Schema changed the join.
            if _get(sub, 'login') != self._message_login() or not in_project(_get(sub, 'project_code'), self._project()):
                continue
            if message and not in_project(_get(message, 'project_code'), self._project()):
                continue
            items.append({'subscription': sub.get_search_key(), 'message_code': _get(sub, 'message_code'),
                          'category': _get(sub, 'category') or _get(message, 'category') or 'default',
                          'new': is_new(_get(message, 'timestamp'), _get(sub, 'last_cleared')),
                          'last_cleared': json_safe(_get(sub, 'last_cleared')),
                          'latest': self._message_item(message) if message else None,
                          'legacy_global': message is not None and not _get(message, 'project_code')})
        return {'items': items, 'offset': offset, 'limit': limit, 'total': total,
                'has_more': offset + len(subscriptions) < total, 'can_write': self.allow_writes,
                'category': category, 'source': 'sthpw/subscription + sthpw/message',
                'acknowledgement': 'last_cleared, not a read receipt'}

    def _history(self, data, options):
        from pyasm.search import Search
        code = options.get('key') or data.get('message_code')
        sub, message = self._channel(code, allow_missing_message=True)
        if options.get('category') and _get(sub, 'category') != options['category']:
            raise ApiError(403, 'message_category', 'Сообщение не принадлежит категории виджета')
        category = _get(message, 'category') or _get(sub, 'category') or 'default'
        before = page_number(data.get('before'), 'before', 2**63-1)
        limit = page_number(data.get('limit'), 'limit', 100, 50)
        if not limit:
            raise ApiError(400, 'limit', 'Страница не может быть пустой')
        query = self._logs(_get(sub, 'message_code'), message)
        if before:
            query.add_filter('id', before, op='<')
        query.add_order_by('id', direction='desc'); query.set_limit(limit+1)
        rows = query.get_sobjects(); more = len(rows) > limit; rows = rows[:limit]
        participants = []
        if category == 'chat':
            peers = Search('sthpw/subscription'); peers.add_filter('message_code', _get(sub, 'message_code'))
            peers.add_filter('category', 'chat'); peers.set_limit(101)
            peer_rows = peers.get_sobjects()
            if len(peer_rows) > 100:
                raise ApiError(400, 'participant_limit', 'Более 100 участников: требуется отдельная пагинация')
            participants = [{'login': _get(p, 'login'), 'last_cleared': json_safe(_get(p, 'last_cleared'))} for p in peer_rows]
        # The original ChatCmd welcome need not be in message_log. Always show
        # latest separately; do not fabricate a historical log record for it.
        return {'message_code': _get(sub, 'message_code'), 'category': category,
                'items': [self._message_item(x, category) for x in reversed(rows)],
                'next_before': str(rows[-1].get_id()) if more and rows else None,
                'has_more': more, 'latest': self._message_item(message, category) if message else None,
                'participants': participants, 'revision': self._channel_revision(sub, message),
                'last_cleared': json_safe(_get(sub, 'last_cleared')),
                'new': is_new(_get(message, 'timestamp'), _get(sub, 'last_cleared')),
                'can_send': self.allow_writes and category == 'chat' and _get(sub, 'category') == 'chat',
                'can_ack': self.allow_writes and message is not None,
                'can_unsubscribe': self.allow_writes and options.get('show_unsubscribe', 'true') not in ('false', False),
                'legacy_global': message is not None and not _get(message, 'project_code')}

    def message_operation(self, method, path, data):
        from pyasm.search import Search
        if path == '/record-subscription':
            return self.record_subscription(method, data)
        options = self._message_options(data)
        if path == '/messages' and method == 'GET':
            return self._subscriptions(data, options)
        if path == '/message-history' and method == 'GET':
            return self._history(data, options)
        if path == '/chat-users' and method == 'GET':
            term = text(data.get('query') or '', 'query', 100, empty=True)
            search = Search('sthpw/login')
            # Native user picker exposes login/display_name only, never secrets.
            if term:
                from tactic.core.query_model import _literal_text
                search.add_op('begin'); _literal_text(search, 'login', term, 'contains')
                _literal_text(search, 'display_name', term, 'contains'); search.add_op('or')
            search.add_filter('login', self._message_login(), op='!=')
            search.add_order_by('login'); search.set_limit(51)
            rows = search.get_sobjects()
            return {'items':[{'login':_get(u,'login'), 'name':_get(u,'display_name') or _get(u,'login')} for u in rows[:50]],
                    'has_more':len(rows)>50}
        if path == '/chats' and method == 'POST':
            if options.get('category') not in (None, '', 'chat') or options.get('key'):
                raise ApiError(403, 'chat_view', 'Этот виджет не разрешает создание переписки')
            def start():
                from tactic.core.message_commands import ChatCmd
                def create():
                    cmd = ChatCmd(users=data.get('users')); cmd.execute()
                    return {'message_code':cmd.info['message_code'], 'created':cmd.info['created']}
                return self._write(create)
            return self._message_once(data, path, start)
        if path == '/message-send' and method == 'POST':
            code = text(data.get('message_code'), 'message_code', 256)
            if options.get('key') and options['key'] != code:
                raise ApiError(403, 'message_key', 'Сообщение другого виджета')
            value = data.get('message')
            if not isinstance(value, str) or not value.strip() or len(value) > 16000 or any(ord(c)<32 and c not in '\n\t\r' for c in value):
                raise ApiError(400, 'message_text', 'Сообщение должно содержать от 1 до 16000 символов без NUL')
            def send():
                def write():
                    sub, message = self._channel(code)
                    if _get(sub,'category') != 'chat' or _get(message,'category') != 'chat' or options.get('category') not in (None,'','chat'):
                        raise ApiError(403, 'chat_only', 'Системные события нельзя переписывать как чат')
                    self._stub().log_message(code, value, status='in_progress', category='chat', log_history=True)
                    return {'sent':True, 'message_code':code, 'retry_scope':'single native process, 15 minutes'}
                return self._write(write)
            # Membership is checked even for a cached retry, not just on write.
            sub, message = self._channel(code)
            if _get(sub,'category') != 'chat' or _get(message,'category') != 'chat' or options.get('category') not in (None,'','chat'):
                raise ApiError(403, 'chat_only', 'Этот виджет не разрешает отправку в выбранную переписку')
            return self._message_once(data, path, send)
        if path == '/subscriptions' and method in ('PATCH', 'DELETE'):
            code = options.get('key') or data.get('message_code')
            def change():
                sub, message = self._channel(code, allow_missing_message=True)
                if options.get('category') and _get(sub, 'category') != options['category']:
                    raise ApiError(403, 'message_category', 'Сообщение другой категории')
                if self._channel_revision(sub, message) != data.get('revision'):
                    raise ApiError(409, 'conflict', 'Появились новые события или изменилась подписка; перечитайте её')
                if method == 'PATCH':
                    if data.get('action') != 'acknowledge' or message is None:
                        raise ApiError(400, 'acknowledge', 'Нельзя отметить отсутствующее сообщение')
                    # Set observed message timestamp, NOT NOW: never mark unseen
                    # future events cleared after a concurrent read/send.
                    sub.set_value('last_cleared', _get(message, 'timestamp')); sub.commit()
                    return {'acknowledged':True, 'last_cleared':json_safe(_get(message,'timestamp')), 'read_receipt':False}
                if options.get('show_unsubscribe', 'true') in ('false', False):
                    raise ApiError(403, 'unsubscribe_disabled', 'Отписка выключена конфигурацией виджета')
                if data.get('confirm') != 'UNSUBSCRIBE':
                    raise ApiError(400, 'confirmation', 'Подтвердите отписку')
                # Original SubscriptionWdg deletes only the current user's
                # subscription row. Keep message and message_log untouched.
                sub.delete()
                return {'unsubscribed':True, 'deleted_messages':False}
            return self._write(change)
        raise ApiError(405, 'method', 'Операция сообщений не поддерживается')

    def record_subscription(self, method, data):
        from pyasm.search import Search
        screen = self.open_target(data.get('target'))
        if screen['kind'] not in ('table','form'):
            raise ApiError(400, 'record_view', 'Откройте объект из конфигурационного представления')
        obj = self._object(screen['search_type'], data.get('key'))
        try:
            code = object_message_key(obj)
        except ValueError as exc:
            raise ApiError(400, 'subscription_source', str(exc)) from exc
        def state():
            search = Search('sthpw/subscription'); search.add_filter('login', self._message_login())
            search.add_filter('message_code', code); search.set_limit(3)
            rows = search.get_sobjects()
            if len(rows)>1:
                raise ApiError(409, 'duplicate_subscription', 'Найдены дубли подписки')
            sub = rows[0] if rows else None
            if sub and not in_project(_get(sub,'project_code'),self._project()):
                raise ApiError(409,'subscription_project','Ключ подписки уже используется в другом проекте')
            fresh = self._object(screen['search_type'], data.get('key'))
            if object_message_key(fresh) != code:
                raise ApiError(409, 'subscription_source_changed', 'Родитель объекта изменился; откройте подписку заново')
            return sub, revision({'object':raw(fresh), 'subscription':raw(sub)})
        sub, rev = state()
        if method == 'GET':
            return {'message_code':code, 'subscribed':sub is not None, 'revision':rev,
                    'can_write':self.allow_writes,
                    'notice':'События публикует исходный SObject._add_message согласно message_event SearchType. Подписка не включает генерацию событий автоматически.'}
        if method not in ('POST', 'DELETE'):
            raise ApiError(405, 'method', 'Метод не поддерживается')
        def change():
            current, current_rev = state()
            if current_rev != data.get('revision'):
                raise ApiError(409, 'conflict', 'Объект или подписка изменились')
            if method == 'POST':
                if current:
                    raise ApiError(409, 'already_subscribed', 'Вы уже подписаны')
                self._stub().subscribe(code, category='sobject')
                return {'subscribed':True, 'message_code':code}
            if data.get('confirm')!='UNSUBSCRIBE':
                raise ApiError(400,'confirmation','Подтвердите отписку')
            if current:
                current.delete()
            return {'subscribed':False, 'message_code':code, 'deleted_messages':False}
        return self._write(change)

    def _notification_recipients(self, ids):
        from pyasm.search import Search
        if not ids:
            return {}
        q = Search('sthpw/notification_login'); q.add_filters('notification_log_id', ids)
        q.add_filter('project_code', self._project()); q.set_limit(10001)
        recipients = q.get_sobjects()
        if len(recipients)>10000:
            raise ApiError(400, 'recipient_limit', 'Слишком много получателей на странице')
        result = {}
        for rec in recipients:
            result.setdefault(str(_get(rec,'notification_log_id')), []).append('%s: %s' % (_get(rec,'type') or 'to', _get(rec,'login') or ''))
        return {k:'\n'.join(v) for k,v in result.items()}
