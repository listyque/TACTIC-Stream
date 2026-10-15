"""Typed cell presentation over original field configs; raw data stays separate."""
import re
import threading
from urllib.parse import urlsplit
from tactic.core.format_value import FormatValueMixin
from tactic.core.field_policy import field_access
from .contracts import ApiError, safe_field, json_safe

FORMAT = {'FormatElementWdg', 'tactic.ui.table.FormatElementWdg', 'tactic.ui.table.format_element_wdg.FormatElementWdg'}
SIMPLE = {'', 'SimpleTableElementWdg', 'tactic.ui.common.SimpleTableElementWdg', 'tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg'}
LINK = {'LinkElementWdg', 'tactic.ui.table.LinkElementWdg', 'tactic.ui.table.link_element_wdg.LinkElementWdg'}
TITLES = {'EditTitleWdg', 'tactic.ui.panel.EditTitleWdg', 'tactic.ui.panel.edit_wdg.EditTitleWdg'}
EXPRESSION = {'ExpressionElementWdg', 'tactic.ui.table.ExpressionElementWdg', 'tactic.ui.table.expression_element_wdg.ExpressionElementWdg'}
FORMAT_LOCK = threading.RLock()  # The original locale helpers change process locale.


class NativeFormat(FormatValueMixin):
    def __init__(self, options=None): self.options = options or {}
    def get_option(self, name): return self.options.get(name)


def safe_link(value):
    """Do not reproduce the old widget's executable URL / dynamic eval behavior."""
    if not value: return {'kind': 'text', 'text': ''}
    if not isinstance(value, str) or len(value) > 4096:
        return {'kind': 'error', 'text': 'Некорректная ссылка'}
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value:
        return {'kind': 'error', 'text': 'Небезопасная ссылка отключена'}
    if value.startswith('{') and value.endswith('}'):
        return {'kind': 'error', 'text': 'Выражение в ссылке ещё не перенесено'}
    try: parsed = urlsplit(value)
    except ValueError: return {'kind': 'error', 'text': 'Некорректная ссылка'}
    if (value.startswith('/') and not value.startswith('//')) or (parsed.scheme in ('http', 'https') and parsed.netloc) or (parsed.scheme == 'mailto' and parsed.path):
        return {'kind': 'link', 'text': value, 'href': value, 'external': not value.startswith('/')}
    return {'kind': 'error', 'text': 'Разрешены относительные /, HTTP(S) и mailto-ссылки'}


def format_cell(value, options, name, day_column=False):
    formatter = NativeFormat(options)
    try:
        # Match FormatElementWdg's date preparation BEFORE get_format_value.
        if value and options.get('type') in ('date', 'time'):
            if not day_column:
                value = formatter.get_timezone_value(value)
            value = str(value)
        with FORMAT_LOCK:
            result = formatter.get_format_value(value, options.get('format'))
        if isinstance(result, dict) and result.get('kind') in ('boolean', 'text'):
            return result
        return {'kind': 'text', 'text': '' if result is None else str(result)}
    except Exception as exc:
        # A bad date/unsupported host locale is not a fabricated zero or success.
        return {'kind': 'error', 'text': 'Ошибка форматирования', 'error_type': type(exc).__name__}


def simple_cell(value, options, name, data_type, day_column=False):
    """Plain-value/date branch of SimpleTableElementWdg, without Wiki/HTML eval."""
    if options.get('empty') and not value:
        return {'kind': 'text', 'text': '--Select--' if options['empty'] in (True, 'true') else ''}
    if (name == 'id' and value == -1) or value is None or value == {}:
        return {'kind': 'text', 'text': ''}
    if data_type in ('timestamp','timestamp without time zone','timestamp with time zone','time','datetime') or name == 'timestamp':
        if not value or value == 'now': return {'kind': 'text', 'text': ''}
        try:
            from dateutil import parser
            dt = parser.parse(str(value))
            if not day_column: dt = NativeFormat(options).get_timezone_value(dt)
            return {'kind': 'text', 'text': dt.strftime('%b %d, %Y - %H:%M')}
        except Exception as exc:
            return {'kind': 'error', 'text': 'Ошибка даты', 'error_type': type(exc).__name__}
    return {'kind': 'text', 'text': str(value)}


class ColumnService:
    def _column_spec(self, spec, model, columns, form=False):
        from pyasm.common import Environment
        security = Environment.get_security()
        stype = spec['type']
        for field in spec['fields']:
            el = model.describe(field['name'])
            opts = field.get('display_options', el['options'])
            handler = field['handler']
            if form and handler in TITLES:
                level = opts.get('level') or '0'
                field.update(kind='heading', supported=True, read_only=True, reason='', heading_level=int(level) if str(level).isdigit() and int(level) < 6 else 0)
                continue
            if form:
                continue
            if handler in SIMPLE | FORMAT | LINK:
                # The original Simple renderer reads its column override. The
                # Format/Link renderers do not share that get_display branch.
                if opts.get('expression'):
                    field.update(supported=False, read_only=True, reason='Expression этого обработчика ещё не перенесён')
                    continue
                if handler not in SIMPLE and opts.get('column') and opts['column'] != field['name']:
                    field.update(supported=False, read_only=True, reason='column override этого специального обработчика ещё не перенесён')
                    continue
                column = opts.get('column') or field['name']
                source_attrs = model.describe(column)['attributes']
                allowed = safe_field(column) and column in columns and field_access(security, self._project(), stype, column, source_attrs)[0]
                if not allowed:
                    field.update(supported=False, read_only=True, reason='Исходная колонка отсутствует или недоступна')
                    # A preceding provider must not bypass this source-field check.
                    field.pop('provider', None)
                    field.pop('source_field', None)
                    continue
                field['value_column'] = column
                field['value_type'] = str((columns[column] if isinstance(columns[column], dict) else {}).get('data_type', '')).lower()
                if handler in FORMAT and not field.get('width'):
                    field['width'] = 30 if opts.get('type') == 'integer' else 80 if opts.get('type') in ('float','date','timecode','currency') else 100
                field['renderer'] = 'format' if handler in FORMAT else 'link' if handler in LINK else 'text'
                field.update(supported=True, reason='')
                if column != field['name']: field['read_only'] = True
                field['justify'] = opts.get('justify') if opts.get('justify') in ('left', 'right', 'center') else ('right' if opts.get('type') in ('integer', 'float', 'currency', 'timecode') else 'left')
                field['single_line'] = opts.get('single_line') in (True, 'true')
                if opts.get('total_summary') in ('count', 'total', 'average'):
                    if column == field['name']:
                        field['summary'] = opts['total_summary']
                    else:
                        field['summary_notice'] = 'Summary для column alias пока не поддержан'
        spec['diagnostics'] = [{'field': f['name'], 'handler': f['handler'], 'reason': f.get('reason')} for f in spec['fields'] if f.get('reason')]
        for f in spec['fields']:
            f['display_support'] = 'native' if f.get('supported') else 'raw' if f.get('storage') else 'unsupported'
        return spec

    def _column_cells(self, obj, row, spec):
        from pyasm.search import SObject
        cells = row.setdefault('cells', {})
        for field in spec['fields']:
            column = field.get('value_column')
            if not column or not field.get('supported'):
                continue
            value = obj.get_value(column, no_exception=True)
            # Values remain unformatted; this is essential for editing/revisions.
            row['values'][field['name']] = json_safe(obj.get_value(column, no_exception=True, auto_convert=False))
            if field.get('renderer') == 'format':
                cells[field['name']] = format_cell(value, field.get('display_options', {}), column, SObject.is_day_column(column))
            elif field.get('renderer') == 'link':
                cells[field['name']] = safe_link(value)
            elif field.get('renderer') == 'text':
                cells[field['name']] = simple_cell(value, field.get('display_options', {}), column, field.get('value_type'), SObject.is_day_column(column))
        return row

    def _page_summaries(self, objects, spec):
        """Original SimpleTableElementWdg totals are over the displayed objects."""
        from pyasm.search import Search
        result = []
        if not objects: return result
        for field in spec['fields']:
            mode = field.get('summary')
            if not mode: continue
            name = field['name']
            expression = '@SUM(.%s)' % name if mode == 'total' else '@AVG(.%s)' % name if mode == 'average' else '@COUNT()'
            try:
                value = Search.eval(expression, sobjects=objects, vars={'ELEMENT_NAME': name})
                cell = format_cell(value, field.get('display_options', {}), name) if field.get('renderer') == 'format' else {'kind': 'text', 'text': str(value)}
            except Exception as exc:
                value, cell = None, {'kind': 'error', 'text': 'Ошибка вычисления итога', 'error_type': type(exc).__name__}
            result.append({'field': name, 'mode': mode, 'value': json_safe(value), 'cell': cell,
                           'label': {'total': 'Total: ', 'average': 'Avg: ', 'count': 'Count: '}[mode], 'scope': 'page'})
        return result

    def resolved_view(self, data):
        opened = self.open_target(data.get('target'))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'not_a_table', 'Нужно конфигурационное представление')
        spec = opened['spec']
        model = self._view_model(opened['search_type'], opened['view'], opened['options'])
        by_name = {f['name']: f for f in spec['fields']}
        order_owner = next((i for i, s in enumerate(model.sources) if s.view not in ('definition','edit_definition','default_definition') and s.node is not None), None)
        return {'search_type': opened['search_type'], 'view': opened['view'], 'resolved_view': model.view,
                'revision': spec['revision'], 'handler': opened['handler'], 'options': opened['options'],
                'table_options': spec.get('table_options', {}), 'default_sort': spec.get('default_sort', []),
                'sort_error': spec.get('sort_error'), 'diagnostics': spec.get('diagnostics', []),
                'layers': [{'index': i, 'view': s.view, 'origin': s.origin, 'owns_order': i == order_owner} for i,s in enumerate(model.sources)],
                'fields': [dict(name=n, label=by_name[n]['label'], handler=by_name[n]['handler'],
                                display_handler=model.describe(n)['handler'], edit_handler=model.describe(n)['edit_handler'],
                                options=by_name[n].get('display_options', {}), attributes=model.describe(n)['attributes'],
                                action=by_name[n].get('action',''), sortable=by_name[n].get('sortable',False), sort_reason=by_name[n].get('sort_reason',''), sources=by_name[n].get('sources',[]),
                                support=by_name[n].get('display_support','native' if by_name[n].get('supported') else 'raw' if by_name[n].get('storage') else 'unsupported'),
                                reason=by_name[n].get('reason','')) for n in model.names() if n in by_name],
                'notice': 'Отчёт о разрешённой конфигурации, не сертификат полного совпадения всех custom handlers с legacy UI.'}
