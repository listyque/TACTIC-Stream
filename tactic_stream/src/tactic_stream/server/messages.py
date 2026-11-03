"""Fixed web operations over Handler's native TACTIC conversations."""
import json
from datetime import datetime

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchKey, SearchType
from pyasm.security.security import _require_admin
from . import messages_query as query


# These are arguments to known procedures, never executable client code.
OPERATIONS = {
    'list': ('query_chat_conversations', {}),
    'create': ('create_chat_conversation', {'recipients': [], 'title': ''}),
    'rename': ('update_chat_conversation', {'message_code': None, 'title': None}),
    'members': ('add_chat_members', {'message_code': None, 'recipients': [], 'replace': False}),
    'delete': ('delete_chat_conversation', {'message_code': None}),
    'clear': ('clear_personal_chat', {'message_code': None}),
    'history': ('query_chat_history', {'message_code': None, 'limit': 31, 'offset': 0, 'search_text': ''}),
    'read': ('mark_chat_read', {'message_code': None, 'timestamp': None}),
    'send': ('send_chat_message', {'message_code': None, 'message': '', 'attachment_keys': [], 'reply_to': None}),
    'edit': ('edit_chat_message', {'message_log_code': None, 'message': None}),
    'delete-message': ('delete_chat_message', {'message_log_code': None}),
    'reaction': ('toggle_chat_message_reaction', {'message_log_code': None, 'emoji': None}),
    'pin': ('pin_chat_message', {'message_log_code': None, 'unpin': False}),
    'forward': ('forward_chat_messages', {'message_log_keys': [], 'target_message_codes': []}),
    'authorize-attachment': ('authorize_chat_attachment', {'message_code': None, 'snapshot_code': None}),
    'initialize': (None, {}),
    'people': (None, {}),
    'upload': (None, {'message_code': None, 'token': None, 'purpose': 'attachment'}),
    'file': (None, {'message_code': None, 'snapshot_code': None, 'file_code': None}),
    'file-info': (None, {'message_code': None, 'snapshot_code': None, 'file_code': None}),
    'files': (None, {'message_code': None, 'limit': 50, 'offset': 0}),
}
FIELDS = {action: set(defaults) for action, (_, defaults) in OPERATIONS.items()}
CHAT_TYPES = ('sthpw/message', 'sthpw/message_log', 'sthpw/subscription', 'sthpw/connection')
WRITE_TYPES = {
    'create': ('sthpw/message', 'sthpw/subscription'), 'rename': CHAT_TYPES[:1], 'members': CHAT_TYPES[2:3],
    'delete': CHAT_TYPES[:1], 'clear': CHAT_TYPES[:2], 'read': CHAT_TYPES[1:3],
    'send': CHAT_TYPES[:2], 'edit': CHAT_TYPES[:2], 'delete-message': CHAT_TYPES[:2],
    'reaction': CHAT_TYPES[1:2], 'pin': CHAT_TYPES[:1], 'forward': CHAT_TYPES[:2],
    'upload': ('sthpw/message', 'sthpw/connection', 'sthpw/snapshot', 'sthpw/file'),
}


def _access(search_type, level, default):
    keys = [{'code': search_type}, {'code': search_type, 'project': 'sthpw'},
            {'code': '*'}, {'code': '*', 'project': 'sthpw'}]
    return Environment.get_security().check_access('search_type', keys, level, default=default)


def _require_access(search_type, level, default='deny'):
    if not _access(search_type, level, default):
        raise SecurityException('Messages access denied')


def _arguments(action, payload):
    defaults = OPERATIONS[action][1]
    if set(payload) - {'ticket', 'project'} - FIELDS[action]:
        raise ValueError('Unknown Messages argument')
    arguments = dict(defaults)
    arguments.update({key: value for key, value in payload.items() if key in defaults})
    for key, value in arguments.items():
        if key in ('replace', 'unpin'):
            valid = type(value) is bool
        elif key in ('limit', 'offset'):
            valid = type(value) is int and (1 <= value <= 100 if key == 'limit' else 0 <= value <= 100000)
        elif key in ('recipients', 'attachment_keys', 'message_log_keys', 'target_message_codes'):
            valid = isinstance(value, list) and len(value) <= 100 and all(
                isinstance(item, str) and item.strip() and len(item) <= (256 if key == 'recipients' else 4096)
                for item in value)
        elif key == 'reply_to' and value is None:
            valid = True
        else:
            maximum = {'message': 500000, 'title': 512, 'search_text': 1024, 'emoji': 16}.get(key, 4096)
            valid = isinstance(value, str) and len(value) <= maximum and '\x00' not in value
            if key in ('message_code', 'message_log_code', 'snapshot_code', 'file_code', 'timestamp', 'emoji', 'reply_to', 'token'):
                valid = valid and bool(value.strip())
        if not valid:
            raise ValueError('Invalid Messages argument: ' + key)
    if action == 'read':
        # Handler receipt cursors are UTC timestamps, not arbitrary lexical values.
        value = arguments['timestamp']
        if len(value) != 19:
            raise ValueError('Invalid receipt timestamp')
        datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return arguments


def _record(reference, search_type):
    if '?' in reference:
        if (SearchKey.extract_base_search_type(reference) != search_type or
                SearchKey.extract_project(reference) not in (None, 'sthpw') or
                SearchKey.extract_database(reference) not in (None, 'sthpw')):
            raise ValueError('Unexpected Messages object type')
        return SearchKey.get_by_search_key(reference)
    return Search.get_by_code(search_type, reference)


def _conversation(code):
    conversation = Search.get_by_code('sthpw/message', code)
    members = Search('sthpw/subscription')
    members.add_filter('message_code', code)
    members.add_filter('login', Environment.get_user_name())
    members.add_filter('category', 'chat')
    if (conversation is None or conversation.get_value('category') != 'chat' or
            conversation.get_value('status') == 'deleted' or members.get_sobject() is None):
        raise SecurityException('Chat is not accessible')
    return conversation


def _message(reference):
    message = _record(reference, 'sthpw/message_log')
    if message is None or message.get_value('status') == 'deleted':
        raise SecurityException('Chat message is not accessible')
    _conversation(message.get_value('message_code'))
    return message


def _execute(action, arguments, uploads=None):
    if action == 'initialize':
        _require_admin()
        from .knowledge_query import knowledge_request
        knowledge_request('initialize', Project.get_project_code())
        return query.query_chat_conversations()
    if action == 'people':
        from .security_groups import user_directory
        return {'users': user_directory(Search('sthpw/login').get_sobjects())}
    for search_type in WRITE_TYPES.get(action, ()):
        _require_access(search_type, 'edit')
    if action == 'send' and arguments['attachment_keys']:
        _require_access('sthpw/connection', 'edit')
        _require_access('sthpw/snapshot', 'view', 'allow')
        for reference in arguments['attachment_keys']:
            _record(reference, 'sthpw/snapshot')
    if arguments.get('message_code'):
        _conversation(arguments['message_code'])
    if action == 'upload':
        from .messages_files import upload_attachment
        return upload_attachment(arguments, uploads)
    if action == 'file':
        from .messages_files import attachment_file
        return attachment_file(arguments)
    if action == 'file-info':
        from .messages_files import attachment_info
        return attachment_info(arguments)
    if action == 'files':
        history = json.loads(query.query_chat_history(arguments['message_code'], limit=arguments['limit'] + 1, offset=arguments['offset']))
        page = history['messages'][:arguments['limit']]
        snapshots = {}
        for message in page:
            forwarded = message.get('__forwarded_from__') or {}
            for row in message.get('__attachments__', []) + (forwarded.get('attachments', []) if forwarded.get('available') else []):
                snapshots[row['code']] = row
        return {'snapshots': list(snapshots.values()), 'hasMore': len(history['messages']) > arguments['limit'], 'nextOffset': arguments['offset'] + len(page)}
    if arguments.get('message_log_code'):
        _message(arguments['message_log_code'])
    if arguments.get('reply_to'):
        reply = _message(arguments['reply_to'])
        if reply.get_value('message_code') != arguments['message_code']:
            raise ValueError('Reply belongs to another chat')
    if action == 'forward':
        for reference in arguments['message_log_keys']:
            _message(reference)
        for code in arguments['target_message_codes']:
            _conversation(code)
    try:
        return getattr(query, OPERATIONS[action][0])(**arguments)
    except RuntimeError as error:
        # Native procedures use RuntimeError for role/participant/age restrictions.
        if str(error).startswith(('Only ', 'Own messages ', 'The current login ', 'Attachment does not belong')):
            raise SecurityException(str(error)) from error
        raise ValueError(str(error)) from error


def messages_request(action, payload, uploads=None):
    if action not in OPERATIONS:
        raise ValueError('Unknown Messages operation')
    arguments = _arguments(action, payload)
    project, security = Project.get_project_code(), Environment.get_security()
    if Project.get_by_code(project) is None:
        raise ValueError('Messages project does not exist')
    if project not in ('admin', 'sthpw') and not security.check_access('project',
            [{'code': project}, {'code': '*'}], 'allow', default='deny'):
        raise SecurityException('Messages project is not accessible')
    previous = Container.get('Chat:writing')
    previous_attachment = Container.get('Chat:attachment')
    try:
        for search_type in CHAT_TYPES:
            _require_access(search_type, 'view', 'allow')
        for search_type in ('sthpw/login', 'sthpw/login_in_group'):
            _require_access(search_type, 'view', 'edit')
        if action in ('list', 'history', 'people', 'authorize-attachment', 'send', 'upload', 'file', 'file-info', 'files'):
            for search_type in ('sthpw/snapshot', 'sthpw/file'):
                _require_access(search_type, 'view', 'allow')
        # Reading can repair summaries/receipts only where the user's edit ACL allows it.
        Container.put('Chat:writing', True)
        command = Command()
        command.get_transaction().set_sync(False)

        def execute():
            if action not in ('people', 'file', 'file-info') and any(_access(kind, 'edit', 'deny') for kind in CHAT_TYPES):
                sql = Search('sthpw/message').get_sql()
                # ponytail: serialize chat metadata in sthpw; replace this coarse lock if chat load warrants it.
                sql.get_database_impl().lock_collection_table(sql, 'message')
            return _execute(action, arguments, uploads)

        command.execute = execute
        result = Command.execute_cmd(command)
        result = json.loads(result) if isinstance(result, str) else result
        if action in ('list', 'initialize'):
            result['permissions'] = {name: all(_access(kind, 'edit', 'deny') for kind in kinds)
                                     for name, kinds in WRITE_TYPES.items()}
        return result
    finally:
        Container.put('Chat:attachment', previous_attachment)
        Container.put('Chat:writing', previous)
