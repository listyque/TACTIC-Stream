"""Handler workspace_layout_presets.py named views, backed by native Commands (EPL-1.0)."""
import json
import math
import re
import uuid
from xml.etree import ElementTree as ET

from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.search_configuration import configuration_records, parse_xml, revision
from tactic_stream.server.widget_configuration import WidgetConfigConflict

CATEGORY = 'workspace_layout'
PREFIX = 'workspace_layout@'


def validate_layout(value):
    if not isinstance(value, dict) or set(value) != {'panels', 'layout'}:
        raise ValueError('Workspace layout configuration has an invalid shape')
    panels = value['panels']
    if not isinstance(panels, list) or not 1 <= len(panels) <= 128:
        raise ValueError('Workspace layout panels or layout tree are invalid')
    known = set()
    for panel in panels:
        if not isinstance(panel, dict) or not isinstance(panel.get('panel_id'), str) or not re.fullmatch(r'[a-z_][a-z0-9_]{0,63}', panel['panel_id']) or panel['panel_id'] in known:
            raise ValueError('Invalid workspace panel identity')
        known.add(panel['panel_id'])
        for field in ('x', 'y', 'width', 'height', 'z'):
            number = panel.get(field)
            if type(number) not in (int, float) or not math.isfinite(number) or abs(number) > (1000000 if field == 'z' else 3):
                raise ValueError('Invalid workspace panel geometry')
        if panel['width'] <= 0 or panel['height'] <= 0 or type(panel.get('visible')) is not bool or type(panel.get('detached', False)) is not bool:
            raise ValueError('Invalid workspace panel geometry')
        if panel.get('dock_area') not in ('left', 'right', 'top', 'bottom', 'center', 'docked', 'floating'):
            raise ValueError('Invalid workspace panel position')
    seen = set()
    def tree(node, depth=0):
        if not isinstance(node, dict) or depth > 32:
            raise ValueError('Invalid workspace layout tree')
        if node.get('type') == 'stack':
            items = node.get('panels')
            if not isinstance(items, list) or not items or any(not isinstance(item, str) or item not in known or item in seen for item in items) or len(set(items)) != len(items) or node.get('active') not in items:
                raise ValueError('Invalid workspace layout stack')
            seen.update(items)
        elif node.get('type') == 'split':
            ratio = node.get('ratio')
            if node.get('orientation') not in ('horizontal', 'vertical') or type(ratio) not in (int, float) or not math.isfinite(ratio) or not 0 < ratio < 1:
                raise ValueError('Invalid workspace layout split')
            tree(node.get('first'), depth + 1); tree(node.get('second'), depth + 1)
        else:
            raise ValueError('Invalid workspace layout tree')
    tree(value['layout'])
    if 'results' not in known:
        raise ValueError('Workspace layout requires results')
    if len(json.dumps(value).encode()) > 128 * 1024:
        raise ValueError('Workspace layout configuration is too large')
    return value


def layout_configuration_from_xml(xml, view):
    root = parse_xml(xml)
    node = next((node for node in root.findall('view') if node.get('name') == view), None)
    values = node.find('values') if node is not None else None
    if values is None or not (values.text or '').strip():
        raise ValueError('Workspace layout configuration values are missing')
    return validate_layout(json.loads(values.text))


def layout_configuration_xml(configuration, view):
    root = ET.Element('config')
    node = ET.SubElement(root, 'view', name=view)
    ET.SubElement(node, 'values', type='json').text = json.dumps(validate_layout(configuration), ensure_ascii=False, separators=(',', ':'))
    return ET.tostring(root, encoding='unicode')


def assignments(records):
    result = {}
    for item in records:
        if item.get_value('category', no_exception=True) == CATEGORY:
            continue
        try:
            root = parse_xml(item.get_value('config'))
        except (ET.ParseError, ValueError, TypeError):
            continue
        for element in root.iter('element'):
            view = (element.findtext('./display/layout_preset') or '').strip()
            if view:
                result.setdefault(view, []).append(element.get('title') or element.get('name') or view)
    return result


def preset_records(records):
    return [item for item in records if item.get_value('category', no_exception=True) == CATEGORY
            and (item.get_value('view') or '').startswith(PREFIX) and not item.get_value('login')]


def read_layouts():
    records = configuration_records('SideBarWdg')
    used = assignments(records)
    rows = []
    for item in preset_records(records):
        view = item.get_value('view')
        row = dict(code=item.get_code(), view=view, title=item.get_value('title') or 'Untitled layout',
                   assignedCount=len(used.get(view, [])), panelCount=0, valid=True, error='', configuration=None)
        try:
            row['configuration'] = layout_configuration_from_xml(item.get_value('config'), view)
            row['panelCount'] = len(row['configuration']['panels'])
        except (ET.ParseError, ValueError, TypeError) as error:
            row.update(valid=False, error=str(error))
        rows.append(row)
    return dict(presets=sorted(rows, key=lambda row: row['title'].casefold()), revision=revision(records))


def workspace_layout_request(action, payload):
    if action not in ('read', 'save', 'delete'):
        raise ValueError('Invalid workspace layout operation')
    if action == 'read':
        return read_layouts()
    _require_admin()
    command = Command()
    def execute():
        sql = Search('config/widget_config').get_sql()
        # ponytail: collection lock, row locks if simultaneous config editing becomes costly.
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        records = configuration_records('SideBarWdg')
        if payload.get('revision') != revision(records):
            raise WidgetConfigConflict('Interface configuration changed. Reload before saving.')
        code = payload.get('code')
        matches = preset_records(records)
        item = next((item for item in matches if item.get_code() == code), None) if code else None
        if code and item is None:
            raise ValueError('Select a layout preset first')
        if action == 'delete':
            if item is None:
                raise ValueError('Select a layout preset first')
            if assignments(records).get(item.get_value('view')):
                raise ValueError('Remove this preset from sidebar items before deleting it')
            item.delete()
        else:
            title = payload.get('title')
            if not isinstance(title, str) or not title.strip() or len(title) > 256:
                raise ValueError('Enter a layout preset name')
            if any(record.get_code() != code and (record.get_value('title') or '').casefold() == title.strip().casefold() for record in matches):
                raise ValueError('A layout preset with this name already exists')
            view = item.get_value('view') if item else PREFIX + uuid.uuid4().hex
            xml = layout_configuration_xml(payload.get('configuration'), view)
            item = item or SearchType.create('config/widget_config')
            for field, value in dict(view=view, login='', category=CATEGORY, search_type='SideBarWdg', title=title.strip(), config=xml).items():
                item.set_value(field, value)
            item.commit(triggers=True)
            if layout_configuration_from_xml(item.get_value('config'), view) != payload['configuration']:
                raise ValueError('The server changed the workspace layout preset payload')
        command.add_description('Save project workspace layout' if action == 'save' else 'Delete project workspace layout')
    command.execute = execute
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return read_layouts()
