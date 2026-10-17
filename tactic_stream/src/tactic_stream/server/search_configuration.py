"""Handler Search Views and quick_filters contracts, using native TACTIC storage."""
from copy import deepcopy
from collections import Counter
import hashlib
import json
import math
import re
from xml.etree import ElementTree as ET

from pyasm.biz import Project, Pipeline
from pyasm.command import Command
from pyasm.common import Environment, Container
from pyasm.search import Search, SearchType, SObject
from pyasm.security.security import _require_admin
from pyasm.common.errors import SecurityException, UnsupportedContract
from tactic_stream.server.api import check_record_access
from tactic_stream.server.widget_configuration import WidgetConfigConflict


RELATIONS = [('Is', '='), ('Is not', '!='), ('Contains', 'EQI'), ('Does not contain', 'NEQI'),
             ('Is empty', 'is empty'), ('Is not empty', 'is not empty'), ('Starts with', 'starts with'),
             ('Ends with', 'ends with'), ('Does not start with', 'does not start with'),
             ('Does not end with', 'does not end with'), ('In', 'in'), ('Not in', 'not in'),
             ('Is greater than', '>'), ('Is less than', '<'), ('Is newer than', 'is after'),
             ('Is older than', 'is before'), ('Is on', 'is on')]
EXCLUDED = {'id', 'code', 'name', 'title', 'description', 'keywords', 'tags', 'tag', 'search_code',
            'search_id', 'search_type', 'project_code', 'login', 'timestamp', 'last_updated', 'created',
            'updated', 'relative_dir', 'file_name', 'file_path', 'web_path', 'lib_path', 'sandbox_path',
            'repo', 'repository', 'metadata', 'data', 'xml', 'config', 'password', 'password_hash',
            'secret', 'token', 'ticket', 'api_key', 'credentials'}


def parse_xml(text):
    if not isinstance(text, str) or len(text.encode()) > 512 * 1024 or re.search(r'<!\s*(DOCTYPE|ENTITY)', text, re.I):
        raise ValueError('Invalid search configuration XML')
    root = ET.fromstring(text)
    if root.tag != 'config':
        raise ValueError('Search configuration must have a config root')
    return root


def unpack_filters(xml):
    # Handler search_presets.records_from_packed, with the original parallel ops.
    root = parse_xml(xml)
    packed = json.loads(root.findtext('./filter/values') or '[]')
    if not isinstance(packed, list) or any(not isinstance(row, dict) for row in packed):
        raise ValueError('Invalid saved search values')
    ops = next((row for row in packed if row.get('prefix') == 'search_ops'), {})
    if any(int(level) != 0 for level in ops.get('levels', [])):
        raise ValueError('Nested legacy filter groups cannot be edited as flat conditions')
    result = []
    for index, row in enumerate(row for row in packed if row.get('prefix') == 'main_body'):
        relation = row.get('main_body_op') if row.get('main_body_relation') == 'expression' else row.get('main_body_relation', '=')
        aliases = {label.lower(): value for label, value in RELATIONS}
        relation = aliases.get(str(relation).lower(), relation)
        result.append(dict(column=row.get('main_body_column', ''), relation=relation,
                           value=row.get('main_body_value', ''), rowEnabled=row.get('main_body_enabled') == 'on',
                           operator='begin' if index == 0 else (ops.get('ops') or [])[index-1] if index <= len(ops.get('ops') or []) else 'and'))
    return result, packed


def pack_filters(records, original='', keyword='', order_bys=()):
    # Handler tactic_classes.pack_tactic_search_view; retain other filter prefixes.
    packed = [dict(prefix='filter_mode', filter_mode='and')]
    ops = dict(prefix='search_ops', levels=[], ops=[], modes=[])
    for index, record in enumerate(records):
        row = dict(prefix='main_body', filter_type='_column', main_body_enabled='on' if record['rowEnabled'] else '',
                   main_body_column=record['column'], main_body_relation=record['relation'], main_body_value=record['value'])
        if record['column'] == '_expression':
            row.update(main_body_relation='expression', main_body_op=record['relation'])
        packed.append(row)
        if index:
            ops['levels'].append(0); ops['ops'].append(record['operator']); ops['modes'].append('child')
    packed.append(ops)
    root = parse_xml(original) if original else ET.Element('config')
    node = root.find('filter')
    if node is None:
        node = ET.SubElement(root, 'filter')
    values = node.find('values')
    if values is None:
        values = ET.SubElement(node, 'values', type='json')
    else:
        previous = json.loads(values.text or '[]')
        packed.extend(row for row in previous if row.get('prefix') not in ('main_body', 'search_ops', 'filter_mode'))
    for prefix, field, value in [('keyword', 'value', keyword), ('group', 'order', ', '.join(order_bys))]:
        extra = next((row for row in packed if row.get('prefix') == prefix), None)
        if extra is None:
            extra = dict(prefix=prefix); packed.append(extra)
        extra[field] = value
    values.text = json.dumps(packed, ensure_ascii=False)
    return ET.tostring(root, encoding='unicode')


def validate_filters(records, columns):
    if not isinstance(records, list) or len(records) > 128:
        raise ValueError('Invalid filter conditions')
    allowed = {value for _, value in RELATIONS} | {'match', 'do not match'}
    for row in records:
        if (not isinstance(row, dict) or set(row) - {'column', 'relation', 'value', 'rowEnabled', 'operator', 'isDefault', 'dataType'}
                or row.get('column') not in {*columns, '_expression'} or row.get('relation') not in allowed
                or type(row.get('rowEnabled')) is not bool or row.get('operator') not in ('begin', 'and', 'or')
                or not isinstance(row.get('value'), (str, int, float, bool)) or len(str(row['value'])) > 16384):
            raise ValueError('Invalid filter condition')
    return records


def apply_filters(search, records):
    enabled = [row for row in records if row['rowEnabled'] and (str(row['value']).strip() or row['relation'] in ('is empty', 'is not empty'))]
    for index, row in enumerate(enabled):
        if index:
            search.add_op('begin', 0)
        column, relation, value = row['column'], row['relation'], row['value']
        if column == '_expression':
            if relation in ('in', 'not in'):
                result = Search.eval(value)
                if isinstance(result, Search):
                    search.add_relationship_search_filter(result, op=relation)
                elif isinstance(result, list) and all(isinstance(item, SObject) for item in result):
                    search.add_relationship_filters(result, op=relation)
                else:
                    raise ValueError('Expression must return a Search or SObjects')
            elif relation in ('match', 'do not match'):
                candidates = Search(search.get_search_type()).get_sobjects()
                ids = [item.get_id() for item in candidates if bool(Search.eval(value, item)) == (relation == 'match')]
                search.add_filters('id', ids)
            else:
                raise ValueError('Invalid expression operator')
        elif relation in ('is empty', 'is not empty'):
            search.add_filter(column, 'NULL', op='is' if relation == 'is empty' else 'is not', quoted=False)
        else:
            search.add_op_filters([[column, relation, value]])
        if index:
            search.add_op(row['operator'] if row['operator'] != 'begin' else 'and')


def deny_expression_write(*args, **kwargs):
    raise SecurityException('Search expressions are read-only')


def configuration_records(search_type):
    search = Search('config/widget_config')
    search.add_filter('search_type', search_type)
    search.add_order_by('id')
    return search.get_sobjects()


def revision(records):
    log = Search('sthpw/sobject_log')
    log.add_filters('search_type', list(dict.fromkeys([Search('config/widget_config').get_search_type(),
        Project.get_full_search_type('config/widget_config'), 'config/widget_config?project=' + Project.get_project_code()])))
    log.add_order_by('id desc'); log.add_limit(1)
    latest = log.get_sobject()
    return hashlib.sha256(json.dumps([Project.get_project_code(), [item.get_data() for item in records],
        latest.get_id() if latest else None], sort_keys=True, default=str).encode()).hexdigest()


def validate_quick(configuration):
    # QuickFilterCatalog.validate_configuration, plus bounded, typed input.
    if not isinstance(configuration, dict) or set(configuration) != {'groups', 'defaultSelections'}:
        raise ValueError('Invalid quick-filter configuration')
    groups, defaults = configuration['groups'], configuration['defaultSelections']
    if not isinstance(groups, list) or len(groups) > 128 or not isinstance(defaults, dict) or len(defaults) > 128:
        raise ValueError('Invalid quick-filter groups or defaults')
    seen = set()
    for group in groups:
        if (not isinstance(group, dict) or set(group) - {'key', 'enabled', 'options'} or not isinstance(group.get('key'), str)
                or not group['key'] or group['key'] in seen or type(group.get('enabled', True)) is not bool):
            raise ValueError('Invalid quick-filter group')
        seen.add(group['key'])
        if 'options' in group and (not isinstance(group['options'], list) or len(group['options']) > 512 or any(not isinstance(value, str) for value in group['options'])):
            raise ValueError('Invalid quick-filter options')
    for key, values in defaults.items():
        if not isinstance(key, str) or not key or not isinstance(values, list) or len(values) > 512 or any(not isinstance(value, str) for value in values):
            raise ValueError('Invalid quick-filter selections')
    if len(json.dumps(configuration).encode()) > 128 * 1024:
        raise ValueError('Quick-filter configuration is too large')
    return deepcopy(configuration)


def quick_from_xml(xml, scope):
    root = parse_xml(xml)
    node = next((view for view in root.findall('view') if view.get('name') == 'quick_filters@' + scope), None)
    if node is None or node.find('values') is None:
        raise ValueError('Quick-filter configuration values are missing')
    return validate_quick(json.loads(node.findtext('values')))


def metadata_options(info):
    # Handler QuickFilterCatalog._metadata_options, without its Qt owner.
    source = info.get('values') or info.get('choices') or info.get('options')
    if isinstance(source, dict):
        iterable = source.items()
    elif isinstance(source, (list, tuple, set)):
        iterable = enumerate(source)
    elif isinstance(source, str):
        iterable = enumerate(source.split('|' if '|' in source else ','))
    else:
        iterable = ()
    records = {}
    for source_key, source_value in iterable:
        if isinstance(source_value, dict):
            value = source_value.get('value')
            if value is None:
                value = source_value.get('code', source_key)
            key = str(value if value is not None else '').strip()
            title = str(source_value.get('title') or source_value.get('label') or source_value.get('name') or key).strip()
            accent = str(source_value.get('color') or '')
        elif isinstance(source, dict):
            key = str(source_key if source_key is not None else '').strip()
            title, accent = str(source_value or key).strip(), ''
        else:
            key = str(source_value if source_value is not None else '').strip()
            title, accent = key, ''
        if key:
            records[key] = dict(key=key, title=title or key, count=0, accent=accent)
    return list(records.values())


def quick_groups(search_type, columns):
    # Handler facet discovery exclusions and 64-value ceiling; SQL aggregation
    # counts the complete dataset rather than only the current result page.
    available = {}
    for column, info in columns.items():
        datatype = info.get('data_type', '').lower()
        if (column in EXCLUDED or column.startswith('__') or column.endswith(('_date', '_time', '_timestamp', '_path', '_url', '_size'))
                or not metadata_options(info) and any(token in datatype for token in ('blob', 'binary', 'bytea', 'json', 'xml', 'date', 'time', 'serial'))):
            continue
        available[column] = info
    admin = Environment.get_security().is_admin()
    user_rows = []
    if available and not admin:
        # ponytail: ordinary users cannot execute raw SQL; one native read is
        # O(rows × facet fields). Replace with a trusted aggregate API if needed.
        search = Search(search_type)
        for column in available:
            search.add_column(column)
        statement, parameters = search._statement()
        with search.store.connection(search.get_db_resource()) as db:
            user_rows = db.execute(statement, parameters).fetchall()
    result = []
    for column, info in available.items():
        if admin:
            search = Search(search_type)
            search.add_column(column)
            search.add_column('COUNT(*)', as_column='facet_count', quoted=False)
            search.add_group_by(column); search.add_order_by(column); search.add_limit(66)
            # Aggregate rows are not complete SObjects: SearchType constructors
            # need identity fields that a GROUP BY result deliberately omits.
            statement, parameters = search._statement()
            with search.store.connection(search.get_db_resource()) as db:
                rows = db.execute(statement, parameters).fetchall()
            options = [dict(key=str(item[column]), title=str(item[column]), count=item['facet_count'])
                       for item in rows if item[column] not in ('', None)]
        else:
            counts = Counter(str(item[column]) for item in user_rows if item[column] not in ('', None))
            if len(counts) > 64:
                continue
            options = [dict(key=value, title=value, count=count) for value, count in sorted(counts.items())]
        merged = {option['key']: option for option in metadata_options(info)}
        for option in options:
            merged.setdefault(option['key'], option)['count'] = option['count']
        options = sorted(merged.values(), key=lambda option: option['title'].casefold())
        if 0 < len(options) <= 64:
            result.append(dict(key='column:' + column, column=column, source='column', accent='#607d8b', title=info.get('title') or info.get('label') or info.get('display') or column.replace('_', ' ').title(), options=options))
    tasks = Search('sthpw/task')
    tasks.add_filters('search_type', [search_type, SearchType.build_search_type(search_type, Project.get_project_code())])
    tasks.add_filter('project_code', Project.get_project_code())
    task_rows = tasks.get_sobjects()
    pipelines = Pipeline.get_by_search_type(search_type, Project.get_project_code())
    configured_processes, configured_statuses = {}, {}
    configured_accents = {'process': {}, 'status': {}}
    for pipeline in pipelines:
        for name in pipeline.get_process_names(recurse=True):
            attrs = pipeline.get_process_attrs(name)
            if attrs.get('type') in ('action', 'condition', 'dependency', 'progress'):
                continue
            configured_processes[name] = attrs.get('label') or name
            if attrs.get('color'):
                configured_accents['process'][name] = attrs['color']
            process = pipeline.get_process(name)
            code = process.get_task_pipeline() if process else None
            status_pipeline = Pipeline.get_by_code(code) if code else None
            if status_pipeline:
                for status in status_pipeline.get_process_names():
                    configured_statuses[status] = status
                    color = status_pipeline.get_process_attrs(status).get('color')
                    if color:
                        configured_accents['status'][status] = color
    if task_rows or configured_processes or configured_statuses:
        for field, title in [('process', 'PROCESSES'), ('status', 'STATUSES'), ('assigned', 'ASSIGNED TO')]:
            configured = configured_processes if field == 'process' else configured_statuses if field == 'status' else {}
            values = sorted({str(item.get_value(field)) for item in task_rows if item.get_value(field)} | set(configured))
            options = [dict(key=value, title=configured.get(value, value)) for value in values]
            for option in options:
                color = configured_accents.get(field, {}).get(option['key'])
                if color:
                    option.update(accent=color, showAccentMarker=True)
            if field == 'assigned':
                logins = Search('sthpw/login').get_sobjects() if Environment.get_security().is_admin() else []
                names = {item.get_value('login'): item.get_value('display_name') or item.get_value('login') for item in logins}
                names.update({value: names.get(value, value) for value in values})
                options = [dict(key=key, title=value) for key, value in sorted(names.items()) if key != Environment.get_user_name()]
                options.insert(0, dict(key='__current_login__', title='MY TASKS'))
            result.append(dict(key=field, column='', source='task', accent='#607d8b', title=title, options=options))
    return result


def read_search_configuration(search_type, scope='', include_groups=True):
    columns = SearchType.get_column_info(search_type)
    records = configuration_records(search_type)
    presets, quick = [], []
    for item in records:
        view = item.get_value('view') or ''
        suffix = view.split(':', 2)[-1]
        if view.startswith('link_search:') and (suffix == search_type or suffix.startswith(search_type + '@')):
            record = dict(code=item.get_code(), view=view, title=item.get_value('title') or view.split(':')[1].replace('_', ' ').title())
            try:
                record['records'], packed = unpack_filters(item.get_value('config'))
                record['keyword'] = next((row.get('value', '') for row in packed if row.get('prefix') == 'keyword'), '')
                order = next((row.get('order', '') for row in packed if row.get('prefix') == 'group'), '')
                record['order_bys'] = [part.strip() for part in order.split(',') if part.strip()]
            except (ValueError, TypeError, ET.ParseError) as error:
                record.update(records=[], error=str(error))
            presets.append(record)
        if view == 'quick_filters@' + scope and item.get_value('category') == 'quick_filters' and not item.get_value('login'):
            quick.append(item)
    if len(quick) > 1:
        raise ValueError('Multiple shared quick-filter standards exist for this sidebar item')
    configuration = quick_from_xml(quick[0].get_value('config'), scope) if quick else dict(groups=[], defaultSelections={})
    return dict(presets=presets, columns=columns, relations=[dict(label=label, value=value) for label, value in RELATIONS],
                revision=revision(records), configuration=configuration, groups=quick_groups(search_type, columns) if include_groups else [])


def generated_quick_records(selections, columns):
    """Handler tel_filters: task facets must match the same related task."""
    if not isinstance(selections, dict) or len(selections) > 128:
        raise ValueError("Invalid quick-filter selections")
    records, conditions, tasks = [], [], {}

    def literal(value):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    for key, source in selections.items():
        if (
            not isinstance(key, str)
            or not isinstance(source, list)
            or len(source) > 512
            or any(not isinstance(value, str) or len(value) > 16384 for value in source)
        ):
            raise ValueError("Invalid quick-filter selections")
        values = sorted(set(value for value in source if value))
        if key.startswith("column:") and key[7:] in columns:
            if values:
                records.append(
                    dict(
                        column=key[7:],
                        relation="=" if len(values) == 1 else "in",
                        value=values[0] if len(values) == 1 else "|".join(values),
                        rowEnabled=True,
                        operator="and",
                        isDefault=False,
                        generatedFilterKind="quick_filters",
                        generatedFilterState=dict(
                            title=key[7:].replace("_", " ").title(),
                            translatable=False,
                            selections={key: values},
                        ),
                    )
                )
        elif key in ("assigned", "process", "status"):
            if values:
                tasks[key] = values
        else:
            raise ValueError("Unknown quick-filter group")
    for field in ("assigned", "process", "status"):
        values = tasks.get(field)
        if not values:
            continue
        if values == ["__current_login__"]:
            conditions.append("['" + field + "', '$LOGIN']")
        else:
            values = sorted(
                set(
                    Environment.get_user_name()
                    if value == "__current_login__"
                    else value
                    for value in values
                )
            )
            conditions.append(
                "['"
                + field
                + "', "
                + ("'in', " if len(values) > 1 else "")
                + literal("|".join(values))
                + "]"
            )
    if conditions:
        records.append(
            dict(
                column="_expression",
                relation="in",
                value="@SOBJECT(sthpw/task" + "".join(conditions) + ")",
                rowEnabled=True,
                operator="and",
                isDefault=False,
                generatedFilterKind="quick_filters",
                generatedFilterState=dict(
                    title="Related task filters", translatable=True, selections=tasks
                ),
            )
        )
    return records


def search_suggestions(search_type, text, column=''):
    # Handler search_suggestion_data.py and search_helpers.get_suggestion_filter.
    if not isinstance(text, str) or len(text) > 4096:
        raise ValueError('Invalid search text')
    text = text.strip()
    info = SearchType.get_column_info(search_type)
    if not isinstance(column,str) or column and column not in info:
        raise ValueError('Invalid suggestion column')
    column = column or ('code' if search_type == 'sthpw/transaction_log' else next((name for name in ('name', 'title', 'code', 'login') if name in info), ''))
    if not text or not column or text.startswith(('skey://', 'tactic-search://')):
        return dict(column=column, records=[])
    columns = [column] + [name for name in ('keywords', 'code', 'description') if name in info and name != column]
    filters = ['begin', (column, 'EQI', text)]
    filters.extend((name, 'EQI', text) for name in ('keywords', 'description') if name in columns)
    filters.append('or')
    search = Search(search_type)
    journal = search_type == 'sthpw/transaction_log'
    if journal:
        from .transaction_journal import check_access
        check_access()
        search.add_filter('namespace', Project.get_project_code())
    for name in dict.fromkeys(columns + ['id', 's_status']):
        if name in info:
            search.add_column(name)
    search.add_op_filters(filters)
    search.set_limit(50)
    from tactic_stream.server.api import ApiXMLRPC
    records = ApiXMLRPC._get_sobjects_dict(search.get_sobjects(), check_security=not journal)
    suggestions, seen = [], set()
    folded_key = text.casefold()
    for record in records:
        title = record.get(column)
        if title in (None, ''):
            continue
        title = str(title)
        description = ' '.join(str(record.get('description') or '').splitlines())
        keyword = next((part for part in str(record.get('keywords') or '').replace(',', ' ').split()
                        if folded_key in part.casefold()), '')
        identity = (title, description, keyword)
        if identity in seen:
            continue
        seen.add(identity)
        values = {column: title}
        values.update((name, record[name]) for name in ('keywords', 'description') if record.get(name) not in (None, ''))
        suggestions.append(dict(title=title, description=description, keyword=keyword,
            code=str(record.get('code') or ''), id=record.get('id'), values=values, selected=False))
        if len(suggestions) >= 20:
            break
    return dict(column=column, records=suggestions)


def tag_catalog(search_type):
    # Handler view_state.py:_query_tag_catalog, using native Search in one request.
    column = next((name for name in ('keywords', 'tags', 'tag') if name in SearchType.get_column_info(search_type)), '')
    if not column:
        return dict(column='', records=[])
    counts, labels = Counter(), {}
    offset, page_size = 0, 2000
    while True:
        search = Search(search_type)
        for name in (column, 'id', 's_status'):
            if name in search.columns:
                search.add_column(name)
        search.add_order_by('id')
        search.set_limit(page_size); search.set_offset(offset)
        batch = search.get_sobjects()
        for record in batch:
            for tag in re.split(r'[,;\s]+', str(record.get_value(column) or '')):
                tag = tag.strip()
                if tag:
                    key = tag.casefold()
                    counts[key] += 1
                    labels.setdefault(key, tag)
        if len(batch) < page_size:
            break
        offset += page_size
    maximum = max(counts.values(), default=1)
    return dict(column=column, records=[dict(tag=labels[key], count=count,
        weight=math.log1p(count) / math.log1p(maximum), column=column)
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], labels[item[0]].casefold()))])


def process_visibility_catalog(search_type):
    """Metadata for the local visibility tree; the result query remains unchanged."""
    from pyasm.biz import Schema
    from .result_items import schema_relations
    from .navigation_links import check_type

    project = Project.get_project_code()
    schema = Schema.get()
    rows = []
    expanded = set()

    def append(node_id, parent_id, key, title, kind, group, depth, accent=''):
        if len(rows) >= 4096:
            raise ValueError('Process visibility tree is too large')
        rows.append(dict(nodeId=node_id, parentId=parent_id, key=key, title=title,
                         kind=kind, group=group, depth=depth, accent=accent,
                         checked=True, checkable=kind != 'pipeline', expanded=True,
                         selected=False, rowVisible=True, hasChildren=False))

    def visit(current, parent='', depth=0, ancestors=()):
        if current in expanded:
            return
        expanded.add(current)
        if depth > 32:
            raise ValueError('Process visibility tree is too deep')
        for builtin in ('publish', 'attachment', 'icon'):
            append(f'{parent or "root"}:builtin:{builtin}', parent, builtin,
                   builtin.title(), 'builtin', '', depth)
        for index, pipeline in enumerate(Pipeline.get_by_search_type(current, project)):
            code = pipeline.get_code()
            identity = f'{parent or "root"}:pipeline:{index}:{code}'
            append(identity, parent, code, pipeline.get_value('name') or code,
                   'pipeline', code, depth)
            for process_index, name in enumerate(pipeline.get_process_names(recurse=True)):
                attrs = pipeline.get_process_attrs(name)
                append(f'{identity}:process:{process_index}:{name}', identity, name,
                       name.capitalize(), 'process', code, depth + 1,
                       attrs.get('color') or '')
        for index, relation in enumerate(schema_relations(current, schema)):
            child = relation['search_type']
            if child in ancestors[:-1]:
                continue
            try:
                check_type(child, project)
            except (SecurityException, UnsupportedContract):
                continue
            identity = f'{parent or "root"}:child:{index}:{child}'
            append(identity, parent, child, relation['title'], 'child', '', depth,
                   relation.get('accent') or '')
            visit(child, identity, depth + 1, (*ancestors, child))

    visit(search_type)
    parents = {row['parentId'] for row in rows if row['parentId']}
    for row in rows:
        row['hasChildren'] = row['nodeId'] in parents
    return dict(title=SearchType.get(search_type).get_title(), records=rows)


def search_configuration_request(action, payload):
    policy = SearchType.get(payload['search_type']).get_record_read_options()
    if policy.get('command') and action in ('query', 'settings', 'read', 'suggestions'):
        if Container.get('FileProject:access') != Project.get_project_code():
            from tactic.command.file_project_cmd import FileProjectCmd
            command = FileProjectCmd(action='admin_search', operation=action, payload=payload)
            Command.execute_cmd(command)
            return command.info
    search_type = payload['search_type'].split('?', 1)[0]
    explicit = SearchType.breakup_search_type(payload['search_type']).get('project')
    if explicit and explicit != Project.get_project_code():
        raise ValueError('Select the target project before reading its configuration')
    scope = payload.get('scope') or search_type
    if not isinstance(scope, str) or len(scope) > 256 or scope.partition('@')[0] != search_type or any(character in scope for character in '<>\r\n'):
        raise ValueError('Invalid saved search scope')
    journal = search_type == 'sthpw/transaction_log'
    if journal:
        from .transaction_journal import check_access, query
        check_access()
        if action == 'query':
            return query(payload)
    else:
        check_record_access(search_type)
    if action == 'visibility':
        return process_visibility_catalog(search_type)
    if action == 'suggestions':
        return search_suggestions(search_type, payload.get('keyword', ''), payload.get('column', ''))
    if action == 'tags':
        return tag_catalog(search_type)
    if action == 'query':
        search = Search(search_type)
        validate_filters(payload.get('records', []), search.columns)
        previous_read = Container.get('Expression:check_record_access')
        previous_write = Container.get('Expression:check_method_access')
        Container.put('Expression:check_record_access', check_record_access)
        Container.put('Expression:check_method_access', deny_expression_write)
        try:
            apply_filters(search, payload.get('records', []))
        finally:
            Container.put('Expression:check_record_access', previous_read)
            Container.put('Expression:check_method_access', previous_write)
        search.add_op_filters(payload.get('filters') or [])
        tags = payload.get('tags', [])
        if (not isinstance(tags, list) or len(tags) > 128 or
                any(not isinstance(tag, str) or not tag or len(tag) > 16384 for tag in tags)):
            raise ValueError('Invalid tag selection')
        if tags:
            column = payload.get('tag_column') or next((name for name in ('keywords', 'tags', 'tag') if name in search.columns), '')
            if column not in ('keywords', 'tags', 'tag') or column not in search.columns:
                raise ValueError('This search type has no tag column.')
            # Keep OR tags grouped beneath the existing filter and native Search ACL.
            search.add_op('begin')
            for tag in tags:
                search.add_filter(column, '%' + tag + '%', op='like')
            search.add_op('or')
        selections = payload.get('selections', {})
        if not isinstance(selections, dict):
            raise ValueError('Invalid quick-filter selections')
        task_selections = {}
        for key, values in selections.items():
            if not isinstance(values, list) or len(values) > 512 or any(not isinstance(value, str) for value in values):
                raise ValueError('Invalid quick-filter selections')
            if not values:
                continue
            if key.startswith('column:'):
                search.add_filters(key[7:], values)
            elif key in ('process', 'status', 'assigned'):
                task_selections[key] = values
            else:
                raise ValueError('Unknown quick-filter group')
        if task_selections:
            task = Search('sthpw/task')
            task.add_filter('project_code', Project.get_project_code())
            for field, values in task_selections.items():
                task.add_filters(field, [Environment.get_user_name() if value == '__current_login__' else value for value in values])
            search.add_relationship_search_filter(task)
        limit, offset = payload.get('limit', 51), payload.get('offset', 0)
        if type(limit) is not int or not 1 <= limit <= 501 or type(offset) is not int or offset < 0:
            raise ValueError('Invalid search page')
        search.set_limit(limit); search.set_offset(offset)
        for order in payload.get('order_bys') or []:
            search.add_order_by(order)
        search.set_show_retired(payload.get('show_retired') is True)
        from tactic_stream.server.api import ApiXMLRPC
        columns = payload.get('columns')
        if columns is not None and (not isinstance(columns, list) or any(column not in search.columns for column in columns)):
            raise ValueError('Invalid search columns')
        records = ApiXMLRPC._get_sobjects_dict(search.get_sobjects(), columns=columns)
        if payload.get('include_total') is True:
            return dict(records=records, total=search.get_count())
        return records
    if action == 'settings':
        result = read_search_configuration(search_type, scope, include_groups=False)
        result['generatedRecords'] = generated_quick_records(payload.get('selections', {}), result['columns'])
        if journal:
            from .transaction_journal import columns
            result['columns'] = columns()
        return result
    if action == 'read':
        result = read_search_configuration(search_type, scope)
        if journal:
            from .transaction_journal import columns
            result.update(columns=columns(), groups=[])
        return result
    _require_admin()
    command = Command()
    def execute():
        sql = Search('config/widget_config').get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/widget_config').get_table())
        records = configuration_records(search_type)
        if payload.get('revision') != revision(records):
            raise WidgetConfigConflict('Search configuration changed. Reload before saving.')
        if action == 'quick-save':
            configuration = validate_quick(payload.get('configuration'))
            view = 'quick_filters@' + scope
            matches = [item for item in records if item.get_value('view') == view and item.get_value('category') == 'quick_filters' and not item.get_value('login')]
            if len(matches) > 1:
                raise ValueError('Multiple shared quick-filter standards exist for this sidebar item')
            item = matches[0] if matches else SearchType.create('config/widget_config')
            root = ET.Element('config'); node = ET.SubElement(root, 'view', name=view)
            ET.SubElement(node, 'values', type='json').text = json.dumps(configuration, ensure_ascii=False, separators=(',', ':'))
            data = dict(view=view, login='', category='quick_filters', search_type=search_type, title='Quick filters', config=ET.tostring(root, encoding='unicode'))
        else:
            code = payload.get('code')
            item = next((item for item in records if item.get_code() == code), None) if code else None
            if code and (item is None or not item.get_value('view').startswith('link_search:')):
                raise ValueError('Saved search does not belong to this Search Type')
            if action == 'delete':
                if item is None:
                    raise ValueError('Select a saved search first')
                return item.delete()
            title = payload.get('title')
            if not isinstance(title, str) or not title.strip() or len(title) > 256:
                raise ValueError('Enter a preset name')
            validate_filters(payload.get('records'), SearchType.get_column_info(search_type))
            slug = re.sub(r'[^\w]+', '_', title.strip()).strip('_').lower() or 'preset'
            view = item.get_value('view') if item else 'link_search:' + slug + ':' + scope
            if item is None and any(record.get_value('view') == view for record in records):
                raise ValueError('A saved search with this name already exists')
            original = item.get_value('config') if item else ''
            keyword, orders = payload.get('keyword', ''), payload.get('order_bys', [])
            if not isinstance(keyword, str) or len(keyword) > 4096 or not isinstance(orders, list) or len(orders) > 16:
                raise ValueError('Invalid saved search keyword or ordering')
            check = Search(search_type)
            for order in orders:
                check.add_order_by(order)
            data = dict(view=view, login='', category='search_filter', search_type=search_type, title=title.strip(), config=pack_filters(payload['records'], original, keyword, orders))
            item = item or SearchType.create('config/widget_config')
        for name, value in data.items():
            item.set_value(name, value)
        item.commit(triggers=action == 'quick-save')
        command.add_description('Save search configuration')
    command.execute = execute
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return read_search_configuration(search_type, scope)
