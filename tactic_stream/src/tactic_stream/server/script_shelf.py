"""Handler script_shelf.py XML and scope rules, using native TACTIC Commands (EPL-1.0)."""
import json
import uuid
from xml.etree import ElementTree as ET

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from tactic_stream.server.search_configuration import configuration_records, parse_xml, revision
from tactic_stream.server.widget_configuration import WidgetConfigConflict

CATEGORY = 'script_shelf'
PREFIX = 'script_shelf@'
GLOBAL = PREFIX + 'global'
LANGUAGES = ('javascript', 'python', 'server_js')


def validate_configuration(value):
    if not isinstance(value, dict) or set(value) - {'scope', 'entryKey', 'buttons'}:
        raise ValueError('Invalid script shelf configuration')
    scope, entry, buttons = value.get('scope'), value.get('entryKey', ''), value.get('buttons')
    if scope not in ('global', 'tab', 'preset') or not isinstance(entry, str) or len(entry) > 1024:
        raise ValueError('Invalid script shelf scope')
    if scope == 'tab' and (not entry.rpartition('@')[0] or not entry.rpartition('@')[2]):
        raise ValueError('Select a sidebar tab first')
    if not isinstance(buttons, list) or len(buttons) > 256:
        raise ValueError('Invalid script shelf buttons')
    seen = set()
    result = []
    for button in buttons:
        if not isinstance(button, dict) or set(button) - {'id', 'title', 'description', 'icon', 'script'}:
            raise ValueError('Invalid script shelf button')
        for field, limit in (('id', 128), ('title', 256), ('description', 4096), ('icon', 128), ('script', 1024)):
            if not isinstance(button.get(field, ''), str) or len(button.get(field, '')) > limit or '\x00' in button.get(field, ''):
                raise ValueError('Invalid script shelf button')
        identity, path = button.get('id', ''), button.get('script', '').replace('\\', '/').strip('/')
        if not identity or identity in seen or not path or any(part in ('', '.', '..') for part in path.split('/')):
            raise ValueError('Choose a saved script and a unique button identity')
        seen.add(identity)
        result.append(dict(id=identity, title=button.get('title') or path.rsplit('/', 1)[-1],
            description=button.get('description', ''), icon=button.get('icon') or 'play-arrow', script=path))
    return dict(scope=scope, entryKey=entry, buttons=result)


def shelf_configuration_from_xml(xml, view):
    root = parse_xml(xml)
    node = next((node for node in root.findall('view') if node.get('name') == view), None)
    values = node.find('values') if node is not None else None
    if values is None or not (values.text or '').strip():
        raise ValueError('Script shelf configuration values are missing')
    return validate_configuration(json.loads(values.text))


def shelf_configuration_xml(configuration, view):
    root = ET.Element('config')
    node = ET.SubElement(root, 'view', name=view)
    ET.SubElement(node, 'values', type='json').text = json.dumps(validate_configuration(configuration), ensure_ascii=False, separators=(',', ':'))
    return ET.tostring(root, encoding='unicode')


def can_manage():
    security = Environment.get_security()
    return security.is_admin() or any(group.get_code().lower() == 'admin' or 'supervisor' in group.get_code().lower() for group in security.get_groups())


def shelf_records(records):
    login = Environment.get_user_name()
    return [item for item in records if item.get_value('category') == CATEGORY
        and (item.get_value('view') or '').startswith(PREFIX) and item.get_value('login') in ('', None, login)]


def read_shelves():
    if not Environment.get_security().check_access('search_type', 'config/widget_config', 'view'):
        raise SecurityException('Script shelf configuration is not accessible')
    records = configuration_records('SideBarWdg')
    rows = []
    for item in shelf_records(records):
        row = dict(code=item.get_code(), view=item.get_value('view'), title=item.get_value('title') or 'Untitled shelf',
            personal=bool(item.get_value('login')), valid=True, error='', configuration=None)
        try:
            row['configuration'] = shelf_configuration_from_xml(item.get_value('config'), row['view'])
        except (ValueError, TypeError, ET.ParseError) as error:
            row.update(valid=False, error=str(error))
        rows.append(row)
    scripts = []
    if Environment.get_security().check_access('search_type', 'config/custom_script', 'view'):
        for item in Search('config/custom_script').get_sobjects():
            if item.get_value('s_status', no_exception=True) == 'retired':
                continue
            language = item.get_value('language') or 'local_python'
            folder = (item.get_value('folder') or '').replace('\\', '/').strip('/')
            title = item.get_value('title') or ''
            path = '/'.join(part for part in (folder, title) if part)
            scripts.append(dict(path=path, title=title, language=language, runnable=language in LANGUAGES,
                executable=bool((item.get_value('script') or '').strip()) and (language == 'javascript' or language in ('python', 'server_js') and Environment.get_security().is_admin())))
    return dict(shelves=rows, scripts=sorted(scripts, key=lambda item: item['path'].casefold()),
        revision=revision(records), canManage=can_manage(), canWrite=Environment.get_security().is_admin())


def assign_shelf(records, entry_key, view):
    search_type, _, name = entry_key.rpartition('@')
    if not search_type or not name:
        raise ValueError('Select a sidebar tab first')
    login = Environment.get_user_name()
    for item in sorted(records, key=lambda item: bool(item.get_value('login'))):
        if item.get_value('category') == CATEGORY or item.get_value('login') not in ('', None, login):
            continue
        try:
            root = parse_xml(item.get_value('config'))
        except (ET.ParseError, ValueError, TypeError):
            continue
        for element in root.iter('element'):
            if element.get('name') != name or (element.findtext('./display/search_type') or element.findtext('search_type') or '').strip() != search_type:
                continue
            display = element.find('display')
            if display is None:
                display = ET.SubElement(element, 'display', {'class': 'LinkWdg'})
            node = display.find('script_shelf')
            if node is None:
                node = ET.SubElement(display, 'script_shelf')
            node.text = view
            item.set_value('config', ET.tostring(root, encoding='unicode'))
            item.commit(triggers=False)
            return
    raise ValueError('The sidebar item was not found')


def clear_assignments(records, view):
    for item in records:
        if item.get_value('category') == CATEGORY:
            continue
        try:
            root = parse_xml(item.get_value('config'))
        except (ET.ParseError, ValueError, TypeError):
            continue
        changed = False
        for display in root.iter('display'):
            for node in list(display.findall('script_shelf')):
                if (node.text or '').strip() == view:
                    display.remove(node); changed = True
        if changed:
            item.set_value('config', ET.tostring(root, encoding='unicode'))
            item.commit(triggers=False)


def script_shelf_request(action, payload):
    if 'entry_key' in payload and (not isinstance(payload['entry_key'], str) or len(payload['entry_key']) > 1024 or '\x00' in payload['entry_key']):
        raise ValueError('Invalid sidebar entry identity')
    if action == 'script':
        path = payload.get('path')
        if not isinstance(path, str) or not path or len(path) > 1024 or '\\' in path or '\x00' in path:
            raise ValueError('Invalid saved script path')
        if not Environment.get_security().check_access('search_type', 'config/custom_script', 'view'):
            raise SecurityException('Saved scripts are not accessible')
        folder, _, title = path.rpartition('/')
        search = Search('config/custom_script')
        search.add_filter('folder', folder); search.add_filter('title', title)
        items = search.get_sobjects()
        if len(items) != 1 or items[0].get_value('s_status', no_exception=True) == 'retired':
            raise ValueError('Choose an existing unambiguous saved script')
        item = items[0]
        if item.get_value('language') != 'javascript':
            raise ValueError('Only JavaScript executes in the browser')
        if not (item.get_value('script') or '').strip():
            raise ValueError('Saved script code is empty')
        return dict(path=path, language='javascript', script=item.get_value('script') or '')
    if action == 'read':
        return read_shelves()
    if action not in ('save', 'delete', 'assign'):
        raise ValueError('Invalid script shelf operation')
    if action == 'save' and payload.get('mode') == 'shared' and not can_manage():
        raise SecurityException('Shared script shelves require administrator or supervisor access')
    command = Command()
    saved_code = ''
    def execute():
        nonlocal saved_code
        sql = Search('config/widget_config').get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        records = configuration_records('SideBarWdg')
        if payload.get('revision') != revision(records):
            raise WidgetConfigConflict('Interface configuration changed. Reload before saving.')
        code = payload.get('code')
        if code is not None and not isinstance(code, str):
            raise ValueError('Invalid script shelf identity')
        visible = shelf_records(records)
        item = next((item for item in visible if item.get_code() == code), None) if code else None
        if code and item is None:
            raise ValueError('Select a script shelf first')
        personal = payload.get('mode') == 'personal' if action == 'save' else bool(item and item.get_value('login'))
        if not personal and not can_manage():
            raise SecurityException('Shared script shelves require administrator or supervisor access')
        if action == 'save':
            if payload.get('mode') not in ('personal', 'shared') or (item and personal != bool(item.get_value('login'))):
                raise ValueError('Invalid script shelf owner')
            configuration = validate_configuration(payload.get('configuration'))
            if personal and configuration['scope'] == 'preset' or not personal and configuration['scope'] == 'tab':
                raise ValueError('Invalid script shelf scope')
            title = payload.get('title')
            if not isinstance(title, str) or not title.strip() or len(title) > 256:
                raise ValueError('Enter a script shelf name')
            view = item.get_value('view') if item else GLOBAL if not personal and configuration['scope'] == 'global' else PREFIX + uuid.uuid4().hex
            if not personal and ((view == GLOBAL) != (configuration['scope'] == 'global')):
                raise ValueError('Invalid shared script shelf scope')
            for record in visible:
                if record.get_code() == code or bool(record.get_value('login')) != personal:
                    continue
                if not personal and (record.get_value('view') == view or (record.get_value('title') or '').casefold() == title.strip().casefold()):
                    raise ValueError('A script shelf with this name already exists')
                if personal:
                    existing = shelf_configuration_from_xml(record.get_value('config'), record.get_value('view'))
                    if existing['scope'] == configuration['scope'] and (configuration['scope'] == 'global' or existing['entryKey'] == configuration['entryKey']):
                        raise ValueError('A personal shelf already exists for this scope')
            item = item or SearchType.create('config/widget_config')
            for field, value in dict(view=view, login=Environment.get_user_name() if personal else '', category=CATEGORY,
                search_type='SideBarWdg', title=title.strip(), config=shelf_configuration_xml(configuration, view)).items():
                item.set_value(field, value)
            item.commit(triggers=True)
            if shelf_configuration_from_xml(item.get_value('config'), view) != configuration:
                raise ValueError('The server changed the script shelf configuration')
            saved_code = item.get_code()
            if not personal and payload.get('entry_key'):
                if view == GLOBAL:
                    raise ValueError('The shared shelf is the project default')
                assign_shelf(records, payload['entry_key'], view)
        else:
            if item is None:
                raise ValueError('Select a script shelf first')
            view = item.get_value('view')
            if not personal and view == GLOBAL:
                raise ValueError('The shared shelf cannot be deleted or assigned')
            if action == 'assign':
                if personal:
                    raise ValueError('Only shared tab shelves can be assigned')
                assign_shelf(records, payload.get('entry_key', ''), view)
            else:
                if not personal:
                    clear_assignments(records, view)
                item.delete()
        command.add_description('Script shelf: ' + action)
    command.execute = execute
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return dict(read_shelves(), savedCode=saved_code)
