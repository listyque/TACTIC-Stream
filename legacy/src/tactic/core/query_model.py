"""Bounded, typed queries and compatibility with TACTIC's saved search format.

No Python/SQL/JavaScript supplied by the browser is executed. Boolean groups
use Search.add_op, i.e. the existing database-specific SQL builder. Legacy
saved searches use the extracted OriginalColumnFilter after input validation;
this preserves its NULL/empty/regex/date semantics rather than approximating
all relations with LIKE. This module never constructs or renders a Wdg.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

MAX_LEAVES = 40
MAX_DEPTH = 4
OPS = frozenset(('eq', 'ne', 'contains', 'not_contains', 'starts', 'ends',
                 'gt', 'gte', 'lt', 'lte', 'null', 'not_null', 'empty',
                 'not_empty', 'in', 'not_in'))
TEXT_KINDS = frozenset(('text', 'textarea', 'select'))
IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
LEGACY_RELATIONS = frozenset(('is', 'is not', 'contains', 'does not contain',
    'starts with', 'ends with', 'does not start with', 'does not end with',
    'is empty', 'is not empty', 'is equal to', 'is greater than', 'is less than',
    'in', 'not in', 'is older than', 'is newer than', 'is before', 'is after',
    'is on', 'is timecode before', 'is timecode after', 'is timecode equal'))


def normalize_tree(value, fields, coerce, *, maximum=MAX_LEAVES):
    """Return an independent validated tree; callback performs field coercion."""
    if value is None:
        return None
    by_name = {f['name']: f for f in fields if f.get('storage', True)}
    count = [0]

    def visit(node, depth):
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise ValueError('Некорректная или слишком глубокая группа фильтров')
        if 'children' in node:
            if set(node) - {'op', 'children'} or node.get('op') not in ('and', 'or'):
                raise ValueError('Группа должна использовать AND или OR')
            children = node['children']
            if not isinstance(children, list) or len(children) > maximum:
                raise ValueError('Слишком много условий в группе')
            if not children and depth:
                raise ValueError('Удалите пустую вложенную группу')
            return {'op': node['op'], 'children': [visit(c, depth + 1) for c in children]}
        if set(node) - {'field', 'op', 'value'}:
            raise ValueError('Неизвестные параметры условия')
        name, op = node.get('field'), node.get('op')
        if not isinstance(name, str) or name not in by_name or op not in OPS:
            raise ValueError('Неизвестное поле или оператор фильтра')
        field = by_name[name]
        count[0] += 1
        if count[0] > maximum:
            raise ValueError('Допустимо не более %s условий' % maximum)
        if op in ('contains', 'not_contains', 'starts', 'ends') and field['kind'] not in TEXT_KINDS:
            raise ValueError('Этот оператор применим только к текстовым полям')
        if op in ('null', 'not_null', 'empty', 'not_empty'):
            result = None
        elif op in ('in', 'not_in'):
            raw = node.get('value')
            if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
                raise ValueError('Оператор IN требует от 1 до 100 значений')
            if any(x is None for x in raw):
                raise ValueError('Для NULL используйте отдельное условие')
            result = [coerce(dict(field, nullable=True, options=[]), x) for x in raw]
        else:
            if node.get('value') is None:
                raise ValueError('Укажите значение либо выберите оператор NULL')
            result = coerce(dict(field, nullable=True, options=[]), node.get('value'))
        if any(isinstance(x, str) and '\x00' in x for x in (result if isinstance(result, list) else [result])):
            raise ValueError('NUL запрещён в значении фильтра')
        if result == '__ALL__' or isinstance(result, list) and '__ALL__' in result:
            raise ValueError('Значение __ALL__ зарезервировано движком TACTIC')
        return {'field': name, 'op': op, 'value': result}
    return visit(value, 0)


def combine(*trees):
    children = []
    for tree in trees:
        if tree is None:
            continue
        if tree.get('op') == 'and' and 'children' in tree:
            children.extend(tree['children'])
        else:
            children.append(tree)
    return {'op': 'and', 'children': children}


def _literal_text(search, name, value, op):
    """Literal matching, with the actual database's escaping semantics.

    TACTIC's SqliteImpl.get_regex_filter is LIKE, not a regex engine. Do not
    pass a regex-escaped string to it. PostgreSQL retains its original EQI
    case handling; SQLite uses its original LIKE case handling.
    """
    if not IDENTIFIER.fullmatch(name):
        raise ValueError('Недопустимое имя столбца')
    vendor = search.get_database_impl().get_database_type()
    if vendor == 'PostgreSQL' and op in ('contains', 'not_contains'):
        search.add_regex_filter(name, re.escape(str(value)), op='NEQI' if op == 'not_contains' else 'EQI')
        return
    if vendor not in ('Sqlite', 'PostgreSQL'):
        raise ValueError('Буквальный текстовый поиск пока поддерживает SQLite и PostgreSQL')
    from pyasm.search import Sql
    # Use an explicit, non-backslash escape so PostgreSQL string settings
    # cannot reinterpret backslashes and SQLite does not treat %/_ as wildcards.
    pattern = str(value).replace('!', '!!').replace('%', '!%').replace('_', '!_')
    if op in ('contains', 'not_contains'):
        pattern = '%' + pattern + '%'
    elif op == 'starts':
        pattern += '%'
    else:
        pattern = '%' + pattern
    operation = 'NOT LIKE' if op == 'not_contains' else 'LIKE'
    search.add_where("\"%s\" %s %s ESCAPE '!'" % (name, operation, Sql.quote(pattern)))


def _not_null(search, name):
    # Select.add_filter(column, None, op='is not') ALWAYS emits IS NULL in
    # this TACTIC revision. Follow the original GeneralFilter's explicit form.
    if not IDENTIFIER.fullmatch(name):
        raise ValueError('Недопустимое имя столбца')
    search.add_where('"%s" IS NOT NULL' % name)


def _scalar(search, name, value, op='='):
    # The core reserves the string NULL as an SQL keyword. In a typed native
    # predicate it is a literal string; an actual null uses the dedicated op.
    if value == 'NULL':
        search.add_filter(name, value, op=op, quoted=True)
    else:
        search.add_filter(name, value, op=op)


def apply_tree(search, tree, fields):
    """Compile to the ORIGINAL Search builder. No interpolated SQL values."""
    if tree is None:
        return
    kinds = {f['name']: f['kind'] for f in fields}
    if 'children' in tree:
        if not tree['children']:
            return
        search.add_op('begin')
        for child in tree['children']:
            apply_tree(search, child, fields)
        search.add_op(tree['op'])
        return
    name, op, value = tree['field'], tree['op'], tree.get('value')
    if op == 'ne':
        # TACTIC's "is not" explicitly includes NULL.
        search.add_op('begin')
        _scalar(search, name, value, op='!=')
        search.add_filter(name, None)
        search.add_op('or')
    elif op in ('null', 'not_null'):
        search.add_filter(name, None) if op == 'null' else _not_null(search, name)
    elif op in ('empty', 'not_empty'):
        is_text = kinds.get(name) in TEXT_KINDS
        if is_text:
            search.add_op('begin')
            search.add_filter(name, '', op='=' if op == 'empty' else '!=')
            search.add_filter(name, None) if op == 'empty' else _not_null(search, name)
            search.add_op('or' if op == 'empty' else 'and')
        else:
            search.add_filter(name, None) if op == 'empty' else _not_null(search, name)
    elif op in ('contains', 'not_contains', 'starts', 'ends'):
        if op == 'not_contains':
            search.add_op('begin')
        _literal_text(search, name, value, op)
        if op == 'not_contains':
            search.add_filter(name, None)
            search.add_op('or')
    elif op in ('in', 'not_in'):
        # Select.add_filters does not coerce booleans and treats [''] as a
        # NULL id filter. Scalar predicates preserve types and SQL NULL rules.
        search.add_op('begin')
        for item in value:
            _scalar(search, name, item, op='=' if op == 'in' else '!=')
        search.add_op('or' if op == 'in' else 'and')
    else:
        _scalar(search, name, value, op={'eq': '=', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}[op])


def _validate_saved(data, search, *, login, project):
    """Validate parameters BEFORE calling legacy methods which interpolate SQL.

    Curly-brace expressions are not sent to Search.eval. Only the two known
    contextual placeholders are resolved. Unknown expression/custom filters
    fail explicitly instead of being omitted from the result set.
    """
    from pyasm.search import SearchType
    if isinstance(data, str):
        if len(data) > 500000:
            raise ValueError('Сохранённый фильтр слишком большой')
        data = json.loads(data)
    if not isinstance(data, list) or len(data) > 200:
        raise ValueError('Ожидается список исходных фильтров TACTIC')
    result = copy.deepcopy(data)
    stype = search.get_base_search_type()
    main = []
    mode = 'and'
    for item in result:
        if not isinstance(item, dict):
            raise ValueError('Некорректный элемент сохранённого поиска')
        prefix = item.get('prefix', 'main_body')
        if prefix == 'filter_mode':
            mode = item.get('filter_mode') or 'and'
            if mode not in ('and', 'or', 'custom'):
                raise ValueError('Неизвестный режим сохранённого поиска')
            continue
        if prefix == 'search_ops':
            for name in ('levels', 'ops', 'modes'):
                if not isinstance(item.get(name), list) or len(item[name]) > 200:
                    raise ValueError('Некорректные операторы составного поиска')
            if len({len(item[n]) for n in ('levels', 'ops', 'modes')}) != 1:
                raise ValueError('Размеры операторов составного поиска не совпадают')
            if any(type(v) is not int or v not in (0, 1) for v in item['levels']):
                raise ValueError('Старый поиск поддерживает уровни 0 и 1')
            if any(v not in ('and', 'or') for v in item['ops']):
                raise ValueError('Недопустимый оператор составного поиска')
            if any(v != 'sobject' for v in item['modes']):
                raise ValueError('Связанные составные фильтры требуют отдельного адаптера')
            continue
        if prefix == 'group':
            if item.get('group_operator') not in (None, '', 'and', 'AND') or item.get('group_begin') or item.get('group_end'):
                raise ValueError('Неизвестный формат группировки поиска')
            continue
        if prefix != 'main_body':
            if item.get(prefix + '_enabled') in ('off', 'false', False):
                continue
            raise ValueError('Ещё не перенесён тип фильтра: ' + str(prefix))
        # Prefix is necessary for FilterData lookup even in old default-less records.
        item['prefix'] = prefix
        enabled = item.get(prefix + '_enabled')
        if enabled is not None and str(enabled).lower() not in ('on', 'true'):
            main.append(item)
            continue
        item[prefix + '_enabled'] = 'on'
        name = item.get(prefix + '_column')
        relation = item.get(prefix + '_relation')
        if relation not in LEGACY_RELATIONS or not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
            raise ValueError('Не перенесён оператор/столбец: ' + str(relation))
        if not SearchType.column_exists(stype, name):
            raise ValueError('В сохранённом поиске нет такого столбца: ' + name)
        target = item.get(prefix + '_search_type')
        if target and target != stype:
            raise ValueError('Связанный фильтр нельзя незаметно превратить в обычный')
        if item.get(prefix + '_key') or item.get(prefix + '_user'):
            raise ValueError('JSON-path/user-фильтр ещё не перенесён')
        value = item.get(prefix + '_value')
        if value is None or value == '':
            value = item.get(prefix + '_select', '')
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        elif not isinstance(value, (str, int, float)):
            raise ValueError('Неожиданный тип значения сохранённого фильтра')
        value = str(value)
        if len(value) > 4000 or '\x00' in value or value == '__ALL__':
            raise ValueError('Недопустимое значение фильтра')
        value = value.replace('{$PROJECT}', project).replace('{$LOGIN}', login)
        if value.startswith('{') and value.endswith('}'):
            raise ValueError('Вычисляемое выражение фильтра требует отдельного провайдера')
        if relation in ('is equal to', 'is greater than', 'is less than'):
            try:
                number = Decimal(value)
                if not number.is_finite():
                    raise ValueError()
                value = str(number)
            except (ValueError, InvalidOperation) as exc:
                raise ValueError('Некорректное число в исходном фильтре') from exc
        if relation in ('is older than', 'is newer than', 'is before', 'is after', 'is on'):
            relative = re.fullmatch(r'[0-9]{1,6} (?:day|week|hour|month)s?', value, re.I)
            if relative and relation != 'is on':
                pass
            else:
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError as exc:
                    raise ValueError('Временной фильтр требует ISO-даты или интервала') from exc
        if relation.startswith('is timecode') and not re.fullmatch(r'[0-9:;.]{1,40}', value):
            raise ValueError('Некорректный timecode')
        item[prefix + '_value'] = value
        item[prefix + '_select'] = ''
        main.append(item)
    return result, main, mode


def apply_saved(search, raw, *, login='', project=''):
    if not raw:
        return
    from pyasm.common import Container
    from tactic.core.filter_data import FilterData
    from tactic.core.search_filters import OriginalColumnFilter
    data, main, mode = _validate_saved(raw, search, login=login, project=project)
    previous = Container.get('FilterData')
    Container.put('FilterData', FilterData(data))
    try:
        if mode != 'custom':
            search.add_op('begin')
        OriginalColumnFilter.alter_sobject_search(search, main, 'main_body')
        if mode != 'custom':
            search.add_op(mode)
    finally:
        Container.put('FilterData', previous)


def _as_legacy_leaf(node, fields, database_type='PostgreSQL'):
    """A leaf representable with the original UI's column relation operators."""
    by_name = {f['name']: f for f in fields}
    op, value = node['op'], node.get('value')
    name = node['field']
    if value == 'NULL' or isinstance(value, list) and 'NULL' in value:
        raise ValueError('Литерал NULL зарезервирован старым движком. Временный типизированный поиск поддерживается.')
    rel = {'eq': 'is', 'ne': 'is not', 'contains': 'contains', 'not_contains': 'does not contain',
           'starts': 'starts with', 'ends': 'ends with', 'gt': 'is greater than', 'lt': 'is less than',
           'empty': 'is empty', 'not_empty': 'is not empty', 'in': 'in', 'not_in': 'not in'}.get(op)
    if op in ('null', 'not_null'):
        if by_name[name]['kind'] in TEXT_KINDS:
            raise ValueError('NULL без пустой строки нельзя сохранить как старый «is empty». Используйте «Пусто» или оставьте условие временным.')
        rel = 'is empty' if op == 'null' else 'is not empty'
    if rel is None:
        raise ValueError('Оператор %s не имеет точного соответствия в старом формате. Поиск не сохранён.' % op)
    if op in ('gt', 'lt') and by_name[name]['kind'] not in ('integer', 'number'):
        raise ValueError('Старый числовой оператор нельзя применить к тексту/датам')
    if op in ('contains', 'not_contains', 'starts', 'ends'):
        if database_type == 'Sqlite':
            # Legacy SQLite filters have no ESCAPE clause. Wildcard literals
            # cannot be encoded without changing the old UI's meaning.
            if '%' in str(value) or '_' in str(value):
                raise ValueError('SQLite: буквальные %/_ нельзя точно сохранить в старом формате. Временный поиск поддерживается.')
            value = str(value)
        elif database_type == 'PostgreSQL':
            if op in ('contains', 'not_contains'):
                value = re.escape(str(value))
            else:
                value = str(value).replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
        else:
            raise ValueError('Сохранение буквального поиска для этой СУБД ещё не перенесено')
    if op in ('in', 'not_in'):
        if any('|' in str(x) for x in value):
            raise ValueError('Значения IN с | нельзя без потери записать в старый формат')
        if by_name[name]['kind'] == 'boolean':
            value = [('1' if x else '0') if database_type == 'Sqlite' else ('true' if x else 'false') for x in value]
        value = '|'.join(str(x) for x in value)
    if value is None:
        value = ''
    elif isinstance(value, bool):
        value = 'true' if value else 'false'
    else:
        value = str(value)
    if value == '' and op not in ('empty', 'not_empty', 'null', 'not_null'):
        raise ValueError('Пустое сравнение пропускается старым движком. Выберите «Пусто».')
    return {'prefix': 'main_body', 'main_body_enabled': 'on', 'main_body_column': name,
            'main_body_relation': rel, 'main_body_value': value}


def encode_saved(tree, fields, database_type='PostgreSQL'):
    """Encode the two-level Boolean layout actually understood by GeneralFilter.

    Never silently flatten a deeper expression. Conditions can always be used
    temporarily; only an exactly representable structure is saved for legacy UI.
    """
    if not tree or not tree.get('children'):
        return []
    outer = tree['op']
    groups = []
    for child in tree['children']:
        if 'children' not in child:
            groups.append(('and', [child]))
        elif any('children' in x for x in child['children']):
            raise ValueError('Для сохранения в штатном поиске доступны два уровня групп')
        else:
            groups.append((child['op'], child['children']))
    groups = [(op, children) for op, children in groups if children]
    rules, levels, ops, modes = [], [], [], []
    for group_index, (op, children) in enumerate(groups):
        for i, leaf in enumerate(children):
            rules.append(_as_legacy_leaf(leaf, fields, database_type))
            if i < len(children)-1:
                levels.append(0); ops.append(op); modes.append('sobject')
            elif group_index < len(groups)-1:
                levels.append(1); ops.append(outer); modes.append('sobject')
    if len(groups) == 1:
        return rules + [{'prefix': 'filter_mode', 'filter_mode': groups[0][0]}]
    # The old engine's two-level algorithm expects each subgroup to contain
    # at least two leaves. Duplicate a singleton predicate (p AND p == p) so
    # legacy add_ops can close it without referencing a preceding group's op.
    if any(len(children) == 1 for _, children in groups):
        expanded = {'op': outer, 'children': [
            {'op': op, 'children': children if len(children) > 1 else children * 2}
            for op, children in groups]}
        return encode_saved(expanded, fields, database_type)
    return rules + [{'prefix': 'filter_mode', 'filter_mode': 'custom'},
                    {'prefix': 'search_ops', 'levels': levels, 'ops': ops, 'modes': modes}]


def merge_saved(base, tree, fields, database_type='PostgreSQL'):
    """Keep inherited filters AND new predicates in the legacy config format.

    An existing custom operator stream cannot safely be nested without changing
    its disabled-rule semantics; reject that merge, rather than silently flatten.
    Re-saving it unchanged is always possible.
    """
    if isinstance(base, str):
        base = json.loads(base or '[]')
    if not isinstance(base, list):
        raise ValueError('Исходный фильтр должен быть списком')
    base = copy.deepcopy(base)
    if not tree or not tree.get('children'):
        return base
    if not base:
        return encode_saved(tree, fields, database_type)
    mode = next((x.get('filter_mode') or 'and' for x in base if isinstance(x, dict) and x.get('prefix') == 'filter_mode'), 'and')
    if mode not in ('and', 'or') or any(not isinstance(x, dict) or x.get('prefix', 'main_body') not in ('main_body', 'filter_mode') for x in base):
        raise ValueError('Нельзя без потери вложить существующий custom-фильтр в старый двухуровневый формат. Сохраните исходный поиск без дополнительных условий.')
    rules = [x for x in base if x.get('prefix', 'main_body') == 'main_body']
    if any(x.get('main_body_enabled') is not None and str(x['main_body_enabled']).lower() not in ('on','true') for x in rules):
        raise ValueError('Перед объединением сохранённого поиска удалите отключённые условия в исходном редакторе')
    # Encode native groups first. If its top is AND, it can coexist with the
    # inherited group at the same level. OR must stay a single child group.
    children = tree['children'] if tree['op'] == 'and' else [tree]
    native_groups = []
    for child in children:
        if 'children' not in child:
            native_groups.append(('and', [_as_legacy_leaf(child, fields, database_type)]))
        elif any('children' in x for x in child['children']):
            raise ValueError('Объединённый поиск требует более двух уровней старого формата')
        else:
            native_groups.append((child['op'], [_as_legacy_leaf(x, fields, database_type) for x in child['children']]))
    groups = [(mode, rules)] + native_groups
    result, levels, ops = [], [], []
    groups = [(op, r if len(r)>1 else r*2) for op,r in groups if r]
    for gi,(op,rules) in enumerate(groups):
        for i,rule in enumerate(rules):
            rule = dict(rule, prefix='main_body')
            result.append(rule)
            if i < len(rules)-1:
                levels.append(0); ops.append(op)
            elif gi < len(groups)-1:
                levels.append(1); ops.append('and')
    return result + [{'prefix':'filter_mode','filter_mode':'custom'},
                     {'prefix':'search_ops','levels':levels,'ops':ops,'modes':['sobject']*len(ops)}]
