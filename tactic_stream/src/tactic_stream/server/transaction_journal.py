"""Read-only projection of native TransactionLog / transaction_log-conf.xml.

See LICENSE.TACTIC and compatibility/source_manifest.json. Replay stays in Command.
"""
import re
import json
import xml.etree.ElementTree as ET

from pyasm.biz import Project
from pyasm.common import Common, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, SearchKey
from pyasm.security.security import _require_admin

SEARCH_TYPE = 'sthpw/transaction_log'
FIELDS = ('id', 'code', 'login', 'timestamp', 'title', 'description', 'namespace', 'type', 'command', 'state')
SECRET = re.compile(r'password|passwd|secret|token|ticket|api[_-]?key|private[_-]?key', re.I)


def mask_json(value):
    if isinstance(value, dict):
        result = {key: '[redacted]' if SECRET.search(key) else mask_json(item) for key, item in value.items()}
        # Native schema backups store positional rows alongside their column metadata.
        if isinstance(value.get('columns'), list) and isinstance(result.get('rows'), list):
            indexes = [index for index, column in enumerate(value['columns']) if isinstance(column, dict) and SECRET.search(str(column.get('name') or ''))]
            for row in result['rows']:
                if isinstance(row, list):
                    for index in indexes:
                        if index < len(row):
                            row[index] = '[redacted]'
        return result
    if isinstance(value, list):
        return [mask_json(item) for item in value]
    return value


def mask_json_text(text):
    if not text or text.lstrip()[:1] not in ('{', '['):
        return text
    try:
        return json.dumps(mask_json(json.loads(text)), ensure_ascii=False)
    except RecursionError:
        return '[redacted]'
    except ValueError:
        return text


def check_access():
    _require_admin()
    from .navigation_links import check_project
    check_project(Project.get_project_code())
    if not Environment.get_security().check_access('search_type', SEARCH_TYPE, 'view'):
        raise SecurityException('Transaction journal is not accessible')


def columns():
    check_access()
    info = SearchType.get_column_info(SEARCH_TYPE)
    return {name: info[name] for name in FIELDS if name in info}


def record(obj):
    from .api import ApiXMLRPC
    return ApiXMLRPC._get_sobjects_dict([obj], columns=list(columns()), check_security=False)[0]


def query(payload):
    from .search_configuration import validate_filters, apply_filters
    check_access()
    info = columns()
    search = Search(SEARCH_TYPE)
    records, filters = payload.get('records', []), payload.get('filters') or []
    validate_filters(records, info)
    if any(row.get('column') not in info for row in records):
        raise ValueError('Journal filters require a visible column')
    if not isinstance(filters, list) or any(not (row in ('begin', 'and', 'or') if isinstance(row, str)
            else isinstance(row, (list, tuple)) and len(row) == 3 and row[0] in info) for row in filters):
        raise ValueError('Journal filters require a visible column')
    if payload.get('tags') or payload.get('selections'):
        raise ValueError('This journal has no tags or task filters')
    selected = payload.get('columns') or list(info)
    if not isinstance(selected, list) or any(name not in info for name in selected):
        raise ValueError('Invalid journal columns')
    apply_filters(search, records)
    search.add_op_filters(filters)
    search.add_filter('namespace', Project.get_project_code())
    for name in info:
        search.add_column(name)
    limit, offset = payload.get('limit', 51), payload.get('offset', 0)
    if type(limit) is not int or not 1 <= limit <= 501 or type(offset) is not int or offset < 0:
        raise ValueError('Invalid search page')
    search.set_limit(limit); search.set_offset(offset)
    orders = payload.get('order_bys') or ['timestamp desc', 'id desc']
    if not isinstance(orders, list) or any(not isinstance(order, str) or not re.fullmatch(r'(?:' + '|'.join(info) + r')(?: (?:asc|desc))?', order, re.I) for order in orders):
        raise ValueError('Invalid journal order')
    for order in orders:
        search.add_order_by(order)
    from .api import ApiXMLRPC
    result = ApiXMLRPC._get_sobjects_dict(search.get_sobjects(), columns=selected, check_security=False)
    return dict(records=result, total=search.get_count()) if payload.get('include_total') is True else result


def details(payload):
    check_access()
    from pyasm.widget import WidgetConfigView
    view = WidgetConfigView.get_by_search_type(SEARCH_TYPE, 'log')
    if view.get_element_names() != ['transaction'] or view.get_display_handler('transaction') not in ('XmlWdg', 'pyasm.widget.XmlWdg'):
        raise UnsupportedContract('Transaction details require the native XML view')
    key = payload.get('search_key')
    if not isinstance(key, str) or len(key) > 2048 or SearchKey.extract_base_search_type(key) != SEARCH_TYPE:
        raise ValueError('Invalid transaction key')
    if SearchType.breakup_search_type(key).get('project') not in (None, '', Project.get_project_code()):
        raise ValueError('Invalid transaction key')
    code, identity = SearchKey.extract_code(key), SearchKey.extract_id(key)
    if not (code or identity):
        raise ValueError('Invalid transaction key')
    search = Search(SEARCH_TYPE)
    search.add_filter('namespace', Project.get_project_code())
    search.add_filter('code' if code else 'id', code or identity)
    obj = search.get_sobject()
    if not obj:
        raise LookupError('Transaction was not found')
    source = obj.get_value('transaction') or '<transaction/>'
    if source.startswith('zlib:'):
        source = Common.decompress_transaction(source)
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise ValueError('Invalid transaction XML') from error
    if root.tag != 'transaction':
        raise ValueError('Invalid transaction XML')
    hidden = 0
    security = Environment.get_security()
    note_codes = [node.get('search_code') for node in root if node.get('search_type', '').split('?')[0] == 'sthpw/note' and node.get('search_code')]
    note_ids = [node.get('search_id') for node in root if node.get('search_type', '').split('?')[0] == 'sthpw/note' and not node.get('search_code') and node.get('search_id')]
    visible_note_codes = set()
    visible_note_ids = set()
    if note_codes:
        note_search = Search('sthpw/note')
        note_search.add_filters('code', note_codes)
        visible_note_codes = {str(item.get_code()) for item in note_search.get_sobjects()}
    if note_ids:
        note_search = Search('sthpw/note')
        note_search.add_filters('id', note_ids)
        visible_note_ids = {str(item.get_id()) for item in note_search.get_sobjects()}
    for node in list(root):
        base = node.get('search_type', '').split('?')[0]
        if base:
            project = SearchType.breakup_search_type(node.get('search_type')).get('project') or Project.get_project_code()
            from .navigation_links import check_project
            try:
                check_project(project)
            except (SecurityException, LookupError):
                root.remove(node); hidden += 1; continue
            keys = [{'code': base}, {'code': base, 'project': project}, {'code': '*'}, {'code': '*', 'project': project}]
            if not security.check_access('search_type', keys, 'view', default='allow' if base.startswith('sthpw/') else 'deny'):
                root.remove(node); hidden += 1; continue
        if base == 'sthpw/note':
            if node.get('search_code'):
                if str(node.get('search_code')) not in visible_note_codes:
                    root.remove(node); hidden += 1; continue
            elif not node.get('search_id') or str(node.get('search_id')) not in visible_note_ids:
                root.remove(node); hidden += 1; continue
        for element in node.iter():
            for name in list(element.attrib):
                if SECRET.search(name):
                    element.set(name, '[redacted]')
                else:
                    element.set(name, mask_json_text(element.get(name)))
            element.text = mask_json_text(element.text)
            field = element.get('name') or element.tag
            if SECRET.search(field):
                for name in element.attrib:
                    if name != 'name':
                        element.set(name, '[redacted]')
                for child in list(element):
                    element.remove(child)
                element.text = '[redacted]'
    ET.indent(root, space='  ')
    return dict(record=record(obj), xml=ET.tostring(root, encoding='unicode'), hidden=hidden)
