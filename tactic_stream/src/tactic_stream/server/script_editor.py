"""Handler Script Editor storage/history through native TACTIC (EPL-1.0)."""
import hashlib
import json

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from tactic_stream.server.script_history import script_history_request
from tactic_stream.server.widget_configuration import WidgetConfigConflict

TYPE = 'config/custom_script'
LANGUAGES = ('python', 'javascript', 'server_js')


def records():
    if not Environment.get_security().check_access('search_type', TYPE, 'view'):
        raise SecurityException('Saved scripts are not accessible')
    return Search(TYPE).get_sobjects()


def revision(items):
    log = Search('sthpw/sobject_log')
    log.add_filters('search_type', [TYPE, Search(TYPE).get_search_type()])
    if len(items) == 1:
        log.add_filter('search_id', items[0].get_id())
    log.add_order_by('id desc'); log.set_limit(1)
    latest = log.get_sobject()
    return hashlib.sha256(json.dumps([[item.get_data() for item in items], latest.get_id() if latest else None],
        sort_keys=True, default=str).encode()).hexdigest()


def describe(item):
    return dict(code=item.get_code(), searchKey=item.get_search_key(), revision=revision([item]),
        folder=item.get_value('folder') or '', title=item.get_value('title') or '',
        language=item.get_value('language') or 'local_python', source=item.get_value('script') or '',
        retired=item.get_value('s_status', no_exception=True) == 'retired')


def read_scripts():
    items = records()
    return dict(scripts=[describe(item) for item in items], revision=revision(items),
        canEdit=Environment.get_security().is_admin())


def validate(payload):
    for field, limit in (('folder', 1024), ('title', 256), ('language', 64), ('source', 512 * 1024)):
        if not isinstance(payload.get(field), str) or len(payload[field]) > limit or '\x00' in payload[field]:
            raise ValueError('Invalid script fields')
    # Handler tactic_classes.normalize_custom_script_path, including nested title paths.
    parts = [part.strip() for part in (payload['folder'] + '/' + payload['title']).replace('\\', '/').split('/') if part.strip()]
    if not parts or not payload['folder'].strip().strip('/') or not payload['title'].strip() or any(part in ('.', '..') for part in parts):
        raise ValueError('Folder and title must form a valid script path')
    if payload['language'] not in LANGUAGES:
        raise ValueError('Supported languages: browser JavaScript, server Python and server JavaScript')
    return dict(folder='/'.join(parts[:-1]), title=parts[-1], language=payload['language'], script=payload['source'])


def script_editor_request(action, payload):
    if action == 'analyse':
        if not Environment.get_security().is_admin() or not Environment.get_security().check_access('search_type', TYPE, 'view'):
            raise SecurityException('Script analysis requires administrator access')
        source, cursor, manual = payload.get('source'), payload.get('cursor', 0), payload.get('manual', False)
        if not isinstance(source, str) or len(source) > 512 * 1024 or '\x00' in source or type(cursor) is not int or cursor < 0 or type(manual) is not bool:
            raise ValueError('Invalid script analysis request')
        try:
            encoded = source.encode('utf-16-le')
            if cursor * 2 > len(encoded):
                raise ValueError('Invalid script cursor')
            position = len(encoded[:cursor * 2].decode('utf-16-le'))
        except UnicodeError:
            raise ValueError('Invalid script cursor') from None
        from tactic_stream.server.script_features import completion_items, document_symbols, _imported_display_names
        items = completion_items(source, position, manual)
        for item in items:
            for field in ('start', 'end'):
                item[field] = len(source[:item[field]].encode('utf-16-le')) // 2
        return dict(symbols=document_symbols(source), completions=items, moduleNames=_imported_display_names(source))
    if action == 'read':
        return read_scripts()
    if action not in ('save', 'delete', 'history', 'revision'):
        raise ValueError('Invalid script editor operation')
    code = payload.get('code', '')
    if not isinstance(code, str) or len(code) > 256:
        raise ValueError('Invalid script identity')
    if action in ('history', 'revision'):
        item = next((item for item in records() if item.get_code() == code), None)
        if item is None:
            raise ValueError('The script was not found in this project')
        value = payload.get('revision_id', '')
        if not isinstance(value, str) or len(value) > 256:
            raise ValueError('Invalid script revision')
        from pyasm.biz import Project
        return json.loads(script_history_request(action, Project.get_project_code(), item.get_search_key(), value))
    if not Environment.get_security().is_admin():
        raise SecurityException('Script changes require administrator access')
    saved = None
    def execute():
        nonlocal saved
        sql = Search(TYPE).get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get(TYPE).get_table())
        items = records()
        item = next((item for item in items if item.get_code() == code), None) if code else None
        if code and item is None:
            raise ValueError('The script was not found in this project')
        if payload.get('revision') != revision([item] if item else items):
            raise WidgetConfigConflict('The script changed. Refresh before saving.')
        if action == 'delete':
            if item is None:
                raise ValueError('Select a saved script first')
            item.delete()
        else:
            values = validate(payload)
            if item and item.get_value('language') not in LANGUAGES:
                raise ValueError('This legacy language is read-only in the web editor')
            if any(other.get_code() != code and other.get_value('folder') == values['folder'] and other.get_value('title') == values['title'] for other in items):
                raise ValueError('A script with this path already exists')
            item = item or SearchType.create(TYPE)
            for field, value in values.items():
                item.set_value(field, value)
            item.commit(triggers=True)
            saved = item.get_code()
        command.add_description('Script editor: ' + action)
    command = Command()
    command.execute = execute
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return dict(read_scripts(), savedCode=saved)
