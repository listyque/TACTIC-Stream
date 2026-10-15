"""Bounded native CSV export of the SAME authorized, configured table Search.

Legacy CsvExportCmd renders Wdg.get_text_value(), then inserts Excel formulas
for csv_force_string. The native path uses the corresponding typed cell data,
keeps QUOTE_NONNUMERIC + column-name headers, and deliberately does not create
spreadsheet formulas. Unsupported widget cells fail export rather than vanish.
No upload/import, arbitrary SQL, filesystem path or search type from the client.
"""
import csv
import io
import json
import re
from dataclasses import dataclass
from .contracts import ApiError, clean_query, safe_element

MAX_ROWS = 10000
MAX_BYTES = 32 * 1024 * 1024

@dataclass(frozen=True)
class BytesPayload:
    data: bytes
    filename: str
    content_type: str = 'text/csv; charset=utf-8'


def protected_csv_value(value, force_string=False):
    value = '' if value is None else str(value)
    # Protection is intentionally also applied to leading whitespace. Preserve
    # the original text after the apostrophe. Numeric negatives may be numeric
    # in a DB but a CSV consumer cannot safely distinguish arbitrary strings.
    dangerous = value.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n'))
    return ("'" + value) if value and (dangerous or force_string) else value


def csv_cell(row, field, mode):
    name = field['name']
    if mode == 'raw':
        if not field.get('storage'):
            raise ApiError(400, 'csv_virtual_raw', 'Для виртуальной колонки нужен режим отображаемых значений: ' + name)
        value = row['values'].get(name)
        if isinstance(value, (dict, list)): value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    else:
        if not field.get('supported'):
            raise ApiError(501, 'csv_widget', 'Не перенесён get_text_value для колонки: ' + name)
        cell = row.get('cells', {}).get(name)
        if cell and cell.get('kind') == 'error':
            raise ApiError(422, 'csv_cell', 'Ошибка отображения колонки ' + name + '; файл не сформирован')
        if cell:
            value = cell.get('text', '')
        else:
            value = row['values'].get(name)
            if field.get('renderer') in ('work-hours', 'gantt') or isinstance(value, (dict, list)):
                raise ApiError(501, 'csv_widget', 'Составной виджет нельзя незаметно заменить строкой JSON: ' + name)
            option = next((o for o in field.get('options', []) if str(o['value']) == str(value)), None)
            if option: value = option['label']
    return protected_csv_value(value, field.get('display_options', {}).get('csv_force_string') == 'true')


class CsvService:
    def export_csv(self, stype, spec, data):
        if data.get('config_revision') != spec['revision']:
            raise ApiError(409, 'config_changed', 'Конфигурация изменилась; обновите представление перед экспортом')
        names = data.get('columns')
        if not isinstance(names, list) or not names or len(names) > 200 or any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
            raise ApiError(400, 'csv_columns', 'Выберите от 1 до 200 различных колонок')
        by_name = {f['name']: f for f in spec['fields']}
        if any(n not in by_name or not safe_element(n) for n in names):
            raise ApiError(403, 'csv_columns', 'Колонка отсутствует в разрешённом представлении')
        fields = [by_name[n] for n in names]
        mode = data.get('value_mode', 'display')
        if mode not in ('display', 'raw'):
            raise ApiError(400, 'csv_mode', 'Неверный режим значений')
        delimiter = data.get('delimiter', ',')
        if delimiter not in (',', ';', '\t'):
            raise ApiError(400, 'csv_delimiter', 'Разделитель: запятая, точка с запятой или табуляция')
        selection = data.get('selection', 'matched')
        if selection not in ('matched', 'selected'):
            raise ApiError(400, 'csv_selection', 'Неизвестный режим выборки')
        keys = data.get('keys') or []
        if selection == 'selected' and (not isinstance(keys, list) or not keys or len(keys) > 1000 or any(not isinstance(k,str) for k in keys) or len(set(keys)) != len(keys)):
            raise ApiError(400, 'csv_selection', 'Выберите от 1 до 1000 различных записей')
        if spec.get('sort_error'):
            raise ApiError(501, 'configured_sort', spec['sort_error'])
        query = clean_query(data, spec['fields'], spec.get('default_sort'))
        search = self._query_search(stype, spec, query)
        if selection == 'selected':
            objects = [self._object(stype, key) for key in keys]
            search.add_filters('id', [obj.get_id() for obj in objects])
        total = search.get_count()
        if total > MAX_ROWS:
            raise ApiError(413, 'csv_limit', 'Экспорт ограничен 10000 записями; уточните поиск', {'total': total})
        if selection == 'selected' and total != len(keys):
            raise ApiError(409, 'csv_selection_changed', 'Часть выбранных записей больше не входит в текущую выборку')
        # Repeat stable ordering used by ConfigBackend.query. Selection is
        # exported in table order, not an arbitrary list of keys from a client.
        orders = query.get('sorts') or [query['sort']]
        for order in orders:
            if order['field'] is not None:
                search.add_order_by(order['field'], direction=order['direction'])
        from pyasm.search import SearchType
        if not any(o['field'] == 'id' for o in orders) and SearchType.column_exists(stype, 'id'):
            search.add_order_by('id', direction='asc')
        output = io.BytesIO()
        output.write(b'\xef\xbb\xbf')
        line = io.StringIO(newline='')
        writer = csv.writer(line, quoting=csv.QUOTE_NONNUMERIC, delimiter=delimiter, lineterminator='\r\n')
        def append(values):
            line.seek(0); line.truncate(0); writer.writerow(values)
            part = line.getvalue().encode('utf-8')
            if output.tell() + len(part) > MAX_BYTES:
                raise ApiError(413, 'csv_size', 'CSV больше 32 МиБ; файл не сформирован, уточните поиск')
            output.write(part)
        append(names)
        offset = 0
        seen = set()
        while offset < total:
            search.set_limit(min(200, total-offset)); search.set_offset(offset)
            objects = search.get_sobjects()
            if not objects:
                raise ApiError(409, 'csv_changed', 'Выборка изменилась во время выгрузки; повторите экспорт')
            # Keep the entire authorized spec for server providers, but write
            # exactly the selected columns in the user's selected order.
            for row in self._serialize_many(objects, spec):
                if row['key'] in seen:
                    raise ApiError(409, 'csv_changed', 'Страницы изменились во время выгрузки; повторите экспорт')
                seen.add(row['key'])
                append([csv_cell(row, f, mode) for f in fields])
            offset += len(objects)
        if search.get_count() != total:
            raise ApiError(409, 'csv_changed', 'Количество записей изменилось во время экспорта')
        stem = re.sub(r'[^A-Za-z0-9_.-]', '_', stype + '_' + spec['view'])[:150]
        return BytesPayload(output.getvalue(), stem + '.csv')
