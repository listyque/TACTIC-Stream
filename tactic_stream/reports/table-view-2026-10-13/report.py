"""Read-only Table View audit. Run after inventory.py using the project venv."""
from pathlib import Path
import ast
import csv
import html
import json
import sys
import tomllib
from collections import Counter

HERE = Path(__file__).resolve().parent
STREAM = HERE.parents[1]
data = json.loads((HERE / 'source_inventory.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(STREAM / 'src'))
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.table_cells import WIDGETS, describe_cell

# A context without a Store ensures these checks cannot read or write records.
columns = {'name': {'data_type': 'text'}}
def element(handler, options=None, action=''):
    return {'name': 'name', 'display': {'handler': handler, 'options': options or {}}, 'action': {'handler': action}}

with request_context(RequestContext(None, 'admin')):
    for handler in WIDGETS:
        options = {'expression': '@GET(.name)', 'order_by': 'name'} if 'ExpressionElementWdg' in handler else {}
        assert describe_cell(element(handler, options), columns)['supported'], handler
    for cls in data['classes']:
        if cls['qualified_class'] not in data['supported']:
            assert not describe_cell(element(cls['qualified_class']), columns)['supported'], cls
    restricted = [
        ('tactic.ui.table.FormatElementWdg', {'total_summary': 'sum'}),
        ('tactic.ui.common.SimpleTableElementWdg', {'empty': 'true'}),
        ('tactic.ui.widget.DiscussionElementWdg', {'allow_email': 'true'}),
        ('pyasm.widget.ThumbWdg', {'redirect': 'name'}),
        ('pyasm.widget.ThumbWdg', {'protocol': 'file'}),
        ('tactic.ui.table.ExpressionElementWdg', {'expression': '@GET(.name)', 'bottom': '@COUNT(.name)'}),
    ]
    for handler, options in restricted:
        assert not describe_cell(element(handler, options), columns)['supported'], (handler, options)
    assert not describe_cell(element('tactic.ui.common.SimpleTableElementWdg', action='example.Action'), columns)['supported']
    journal = {'search_type': 'sthpw/transaction_log', 'view': 'log', 'dynamic_class': 'tactic.ui.panel.FastTableLayoutWdg'}
    hidden = element('tactic.ui.table.HiddenRowElementWdg', journal)
    assert describe_cell(hidden, columns, 'sthpw/transaction_log')['supported']
    assert not describe_cell(hidden, columns, 'cg/assets')['supported']

# "Works" describes the connected scenario, not complete legacy parity.
partial = {
    'pyasm.widget.table_element_wdg.ArrayTableElementWdg': (
        'Исходное strip крайних | и замена || на запятую; короткий и полные class paths; NULL отображается пустым; сравнение source body и typed транспорта ТХ/ТС.',
        'HTML runtime не исполняется; работают нативное текстовое значение и Table View presenter. Ячейка только для чтения.'),
    'pyasm.widget.table_element_wdg.XmlWdg': (
        'Безопасный текст XML, нативный zlib:, ошибка разбора рядом с исходным текстом, прокрутка; raw SDK/CSV не изменён.',
        'Общий inline XML editor ТС пока не подключён; текущий блок закрывает отображение, исходный get_display HTML runtime не вызывается.'),
    'tactic.ui.table.json_element_wdg.JsonElementWdg': (
        'Исходные sorted keys, indent=2, пустой false/empty JSON, ограниченная высота/прокрутка, безопасный текст; raw SDK сохраняет значение.',
        'Общий inline JSON editor ТС пока не подключён; height принимается в px до 600. Исходный HTML runtime не исполняется.'),
    'tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg': (
        'No version / Latest / Current и padding положительных версий из checkin/version_padding; нативный typed вывод и перевод UI меток.',
        'NULL теперь показывает No version вместо исходной ошибки. Raw SDK/CSV не форматируется; HTML runtime исключён.'),
    'tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg': (
        'Текст физической колонки; column, сортировка; boolean отображается общим checkbox.',
        'Нет общего inline edit, empty/total_summary, legacy wiki-разметки и исходного форматирования timestamp в этом presenter. Допустима только display-опция column.'),
    'tactic.ui.common.base_table_element_wdg.RawTableElementWdg': (
        'Сырое значение физической колонки; column и сортировка.',
        'Нет общего inline edit; исходная обработка timestamp/time и now из get_display не вызывается.'),
    'tactic.ui.table.format_element_wdg.FormatElementWdg': (
        'Нативное форматирование чисел, дат, процентов, timecode; type/format/fps/timezone/constraint; Checkbox только для чтения.',
        'Нет общего inline edit и total_summary. justify допускается descriptor, но выравнивание ячейки Vue по этой опции не применяется.'),
    'tactic.ui.table.link_element_wdg.LinkElementWdg': (
        'Ссылка из поля/выражения: HTTP(S), mailto, абсолютный локальный URL.',
        'icon принимается, но TableCell выводит текстовую ссылку; нет общего inline edit. file/JS URL не поддерживаются намеренно.'),
    'tactic.ui.table.expression_element_wdg.ExpressionElementWdg': (
        'Нативные вычисления; value/boolean/check, display/alt expression, format, списки, cache, fast; ошибки по ячейкам.',
        'Не подключены bottom/group_bottom, link_expression/link_view, icon mode, filter_name, JS eval listener; нет общего inline edit и кнопки пересчёта таблицы. group_by/group_by_time metadata не означает исходную группировку и итоги.'),
    'tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg': (
        'Вычисление выражения из значения физической колонки с sobject-контекстом; ошибка показывается в ячейке.',
        'Нет общего inline editor для изменения самого выражения; дополнительные display-опции кроме column отвергаются.'),
    'pyasm.widget.file_wdg.ThumbWdg': (
        'Пакетное превью snapshots/files; context/cascade, original/latest, filename/file_type; открытие общего FilePreview.',
        'Не подключены detail/detail_class_name, redirect/redirect_expr, icon_size/min_icon_size и legacy JS/actions. Доступен HTTP; это не полный старый media/detail widget.'),
    'tactic.ui.widget.discussion_wdg.DiscussionElementWdg': (
        'Процессы и счётчики заметок либо compact icon; process/context/use_parent; открытие NotesPanel.',
        'Нет email-режима (allow_email=true отвергается); только default/icon и ограниченный набор опций. Старый HTML/JS popup не переносится как runtime.'),
    'tactic.ui.table.task_element_wdg.TaskElementWdg': (
        'Задачи по процессам, фильтрам и pipeline; просмотр инспектора; существующий TaskTableEditor для изменений.',
        'Нет полного старого набора presentation/actions/CGI child-task filters. Неподдержанные опции отвергаются; generic CellEdit не заменён редактором задач.'),
    'tactic.ui.table.statistic_wdg.TaskCompletionWdg': (
        'Нативный процент выполнения задач с task_expr и проверкой доступа; 18px полоса как TacticCompletionCell ТХ, процент внутри, ограничение 0–100 и ARIA.',
        'Не подключены исходные групповые/нижние итоги; ширина берётся из XML attribute width, старый display width не управляет layout Vue.'),
}
missing_notes = {
    'GanttElementWdg': 'Диаграмма Task Manager существует отдельно; GanttElementWdg как XML-колонка не подключён.',
    'MetadataElementWdg': 'В ТС есть headless metadata/edit-контракт класса, но нет его table popup и renderer.',
    'SnapshotMetadataElementWdg': 'Metadata backend не заменяет SnapshotMetadataElementWdg в таблице.',
    'DeleteElementWdg': 'Общее меню операций строки умеет удаление; XML-ячейка DeleteElementWdg отсутствует.',
    'SObjectFilesElementWdg': 'Общие Files/FilePreview существуют; список файлов этой XML-ячейки не подключён.',
    'ButtonElementWdg': 'Не подключены кнопка из XML-колонки и её сценарии/action.',
    'CustomLayoutElementWdg': 'Нет встроенной в table cell композиции CustomLayoutElementWdg.',
    'FreeFormLayoutElementWdg': 'Нет встроенного в table cell FreeForm layout.',
    'DropElementWdg': 'Нет XML-ячейки раскрывающегося элемента с исходными действиями.',
    'PythonElementWdg': 'Python в серверном API не означает исполнение PythonElementWdg для ячейки.',
    'ExplorerElementWdg': 'Нет соответствующей explorer-ячейки; в legacy-каталоге также ошибочное имя ExploreElementWdg.',
    'ExplorerTableElementWdg': 'Нет соответствующей explorer-ячейки.',
    'ForeignKeyElementWdg': 'RelatedObjects/pickers не заменяют foreign-key XML-ячейку.',
    'RelatedElementWdg': 'RelatedObjects существует отдельно; этот XML-виджет не подключён.',
    'WorkHoursElementWdg': 'Work Hours и его команды существуют отдельно; XML-ячейка WorkHoursElementWdg не подключена.',
    'CheckinButtonElementWdg': 'Check-in доступен в других сценариях; эту XML-кнопку он не заменяет.',
    'CheckoutButtonElementWdg': 'Открытие/скачивание файлов в других панелях не заменяет эту XML-кнопку.',
    'HtmlElementWdg': 'Нет renderer этой XML-ячейки; произвольный legacy HTML/JS не исполняется в Vue.',
    'JsonElementWdg': 'JSON как обычный текст не заменяет этот виджет.',
    'SpreadsheetElementWdg': 'Исходник считает накопительный итог по column/format; это не полноценный табличный редактор. Этот renderer не подключён.',
}
def group_of(q):
    if q.startswith('pyasm.prod.'):
        return 'Исключённый production'
    name = q.rsplit('.', 1)[-1].lower()
    if any(word in q.lower() for word in ['gantt', 'projected_schedule', 'timecard']):
        return 'Календарь и сроки'
    if any(word in q.lower() for word in ['discussion', 'message_wdg', 'note_wdg', 'annotate', 'notification', 'recipient']):
        return 'Заметки и общение'
    if any(word in name for word in ['snapshot', 'checkin', 'checkout', 'publish', 'thumb', 'file', 'version', 'loader', 'renderlink', 'naming', 'addimage']):
        return 'Файлы и версии'
    if any(word in q.lower() for word in ['task', 'status', 'work_hours', 'statistic', 'overlay_stats']):
        return 'Задачи и показатели'
    if any(word in name for word in ['related', 'foreignkey', 'explorer', 'connection', 'group', 'attach', 'sobjectlink']):
        return 'Связи и вложенные объекты'
    if any(word in q.lower() for word in ['project_wdg', 'preference', 'security', 'process_group_select', 'search_type_element', 'my_tactic', 'clipboard']):
        return 'Администрирование и настройки'
    if any(word in name for word in ['expression', 'python', 'summary', 'spreadsheet', 'indirectmapped']):
        return 'Вычисления и итоги'
    if any(word in name for word in ['button', 'layout', 'hiddenrow', 'rowadd', 'delete', 'drop', 'document', 'wrapper', 'rowselect', 'placeholder', 'tableadd']):
        return 'Компоновка и действия'
    return 'Значения и форматирование'

registered = {}
for item in data['catalog']:
    if item['resolved_class']:
        registered.setdefault(item['resolved_class'], []).append(item['alias'])
rows = []
fixture_path = STREAM / 'frontend/tests/fixtures/table-widget-catalog.json'
samples = json.loads(fixture_path.read_text(encoding='utf-8')) if fixture_path.exists() else []
for cls in data['classes']:
    q = cls['qualified_class']
    item = dict(cls)
    item.update(catalog_aliases=registered.get(q, []), supported_handlers=data['supported'].get(q, []),
                stream_class=data['stream_classes'].get(q, ''), works='', gaps='', base_scenario=False,
                group=group_of(q), legacy_review='Требует прогона исходника', migration='Не начинать без примера и проверки исходника')
    if q.startswith('pyasm.prod.'):
        item.update(status='Исключён ранее', scope='pyasm.prod', gaps='Namespace pyasm.prod целиком исключён предыдущим согласованным решением; не очередь переноса (AGENTS.md).')
        item.update(migration='Не переносить: согласованное исключение')
    elif q == 'tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg':
        node = next(n for n in ast.parse(Path(cls['legacy_file']).read_text(encoding='utf-8')).body if isinstance(n, ast.ClassDef) and n.name == cls['class'])
        assert len(node.body) == 1 and isinstance(node.body[0], ast.Pass), 'Re-review SnapshotServerElementWdg: source changed'
        item.update(status='Недописан в legacy', legacy_review='Проверено: тело класса только pass; непосредственный BaseTableElementWdg не реализует этот виджет.',
                    migration='Не переносить: явная заглушка', gaps='snapshot_element_wdg.py:177–178: class SnapshotServerElementWdg(BaseTableElementWdg): pass. Исключён по правилу пользователя 2026-10-13.')
    elif q == 'pyasm.widget.input_wdg.TextWdg':
        item.update(status='Совместимый alias', scope='Alias input → table', base_scenario=True,
                    works='pyasm.widget.TextWdg в WIDGETS направляется на SimpleTableElementWdg.',
                    gaps='Это input-класс, не отдельный table widget. Ограничения те же, что у SimpleTableElementWdg; в число 193 table-классов не включён.')
    elif q in partial:
        item.update(status='Частично', base_scenario=True, works=partial[q][0], gaps=partial[q][1])
        item.update(legacy_review='Поддержанный сценарий изучен; есть native/server/UI проверки. Полный legacy-контракт не подтверждён.', migration='Продолжать по конкретным сценариям из справки')
    elif cls['class'] == 'HiddenRowElementWdg':
        item.update(status='Частично', works='Только журнал sthpw/transaction_log: view=log, dynamic_class=FastTableLayoutWdg, show-флаги false; JournalDetails.',
                    gaps='Общий HiddenRow с произвольной вложенной таблицей/классом не подключён; принимается только package-path tactic.ui.table.HiddenRowElementWdg.')
    else:
        item.update(status='Не подключён', gaps=missing_notes.get(cls['class'], 'Нет подключения этого класса к describe_cell/WIDGETS и TableCell.vue; при таком display handler показывается Widget unavailable.'))
        if cls['class'] in {'SimpleTableElementWdg', 'TaskCompletionWdg', 'DiscussionWdg', 'GanttWdg', 'DateWdg', 'DateTimeWdg'}:
            item['gaps'] += ' Старый qualified class не является alias нового одноимённого/похожего виджета.'
    if cls['class'] == 'ExplorerTableElementWdg':
        item['legacy_review'] = 'Проверено: pass — alias рабочего ExplorerElementWdg; это не недописанный виджет.'
    if cls['class'] == 'PlaceHolderElementWdg':
        item.update(legacy_review='Проверено: намеренно пустая служебная ячейка, get_display возвращает пустую строку.', migration='Не самостоятельный пользовательский сценарий')
    if 'scope' not in item:
        item['scope'] = 'Каталог Table View' if item['catalog_aliases'] else 'Дополнительные tactic.ui.table' if q.startswith('tactic.ui.table.') else 'Другие table-классы legacy'
    sample = next((s for s in samples if s['element']['display']['handler'] in item['supported_handlers']), None)
    item.update(example_xml=sample['xml'] if sample else '', screenshot='table-widget-'+sample['key']+'.png' if sample else '')
    rows.append(item)

assert len(rows) == len({r['qualified_class'] for r in rows}) == 194
assert len(partial) == 14 and all(any(r['qualified_class'] == q for r in rows) for q in partial)
assert len(data['catalog']) == 19 and len({x['handler'] for x in data['catalog']}) == 18
counts = Counter(r['status'] for r in rows)
assert counts == {'Не подключён': 134, 'Частично': 15, 'Исключён ранее': 43, 'Совместимый alias': 1, 'Недописан в legacy': 1}, counts
version = tomllib.loads((STREAM / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
notes = [
    'Аудит исходников TS ' + version + ' на 2026-10-13. Всего 193 table-класса + 1 совместимый input alias; 19 catalog aliases → 18 class paths (один ошибочный).',
    'Полный перенос означает доступность XML handler, display-опций и действий в Vue Table View. Ни у одного из подключённых классов полный legacy-контракт не подтверждён.',
    'Для 14 классов готов базовый сценарий отображения/открытия панели; это не полная готовность. HiddenRow частично подключён исключительно для журнала.',
    '134 класса не подключены. SnapshotServerElementWdg явно недописан и не переносится. 43 pyasm.prod исключены ранее и не являются долгом переноса. Alias TextWdg учтён отдельно.',
    'Перед переносом: изучить сам виджет и наследование → воспроизводимый пример → скрин legacy/ТХ и ТС на одинаковых данных → документировать опции, действия и права → проверить → переносить. TODO сам по себе не исключение. Непроверенный исходник не считается готовым к переносу.',
    'Сканируются lexical top-level Python-классы и их наследники от двух BaseTableElementWdg; строковые/комментированные deprecated определения не считались. FunctionalTableElement и два base-класса — инфраструктура, не виджеты реестра.',
    'Ошибка исходного каталога: explorer → tactic.ui.table.ExploreElementWdg, но есть ExplorerElementWdg/ExplorerTableElementWdg. Исправление имени само по себе не подключит ячейку в TS.',
    'Наличие класса в TS, headless API, редактора формы или функции в отдельной панели не считается готовностью Table View. Input/Edit/CellEdit виджеты, layout-контейнеры и команды не смешиваются с количеством ячеек.',
    'У всех подключённых обычных ячеек action handler должен быть пуст. Неизвестные display options отвергаются. Configured UI и чтение server cells доступны администратору.',
    f'Проверены все {len(WIDGETS)} handler aliases WIDGETS без Store/БД, отказ остальных 179 class paths, ограниченные опции, action и journal-ветка. Дополнительно четыре value widget проверены по source display bodies и typed транспорту ТХ/ТС. Полный GUI legacy/runtime и пользовательские custom/plugin классы вне checkout не проверялись.',
    'Пять файлов legacy не токенизируются (см. JSON); отдельный просмотр показал, что в них нет table-определений: upgrade dump/reporter, prod queue, AD script, ClientWdg(BaseRefreshWdg).',
]
table_contract = [
    ('TableLayoutWdg / TableWdg', 'Частично', 'Базовая таблица, сортировка поддержанных колонок, выбор строк, width из XML (48–640px), собственные группы, заметки/превью/задачи. Нет общего inline CellEdit, legacy итогов, полного resize/reorder/context menu. Допустимые layout strings проверяются ConfiguredView.supportedLayout.'),
    ('FastTableLayoutWdg / StaticTableLayoutWdg / ToolLayoutWdg', 'Не подключены как общие layout', 'Общая таблица Vue не принимает эти layout names. FastTableLayoutWdg в специальном HiddenRow журнала — отдельный ограниченный контракт.'),
    ('Общий CellEdit / EditMultiple', 'Не подключён общий table UI', 'Формы редактирования и TaskTableEditor существуют, но универсальный редактор значения ячейки и массовое редактирование выбранных ячеек ими не заменены.'),
    ('bottom / group_bottom / total_summary', 'Не подключены', 'Свои rowGroups не заменяют исходные вычисляемые итоги колонок и групп. Эти display options не входят в allowlist.'),
    ('Произвольные action / HTML / JS widgets', 'Не подключены', 'Старые команды и JS-кнопки не запускаются по наличию XML. Требуется отдельное типизированное подключение сценария.'),
]
payload = dict(date='2026-10-13', version=version, counts=dict(counts), fully_ready=0, base_scenario_ready_classes=14,
               notes=notes, table_contract=table_contract, catalog=data['catalog'], widgets=rows, lexing_errors=data['lexing_errors'])
(HERE / 'table-view-audit.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
fields = ['qualified_class', 'group', 'status', 'scope', 'legacy_review', 'migration', 'catalog_aliases', 'base_scenario', 'works', 'gaps', 'example_xml', 'screenshot', 'legacy_file', 'legacy_line', 'stream_class', 'supported_handlers']
with (HERE / 'table-view-audit.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fields, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    for r in rows:
        writer.writerow({**r, 'catalog_aliases': ', '.join(r['catalog_aliases']), 'supported_handlers': ', '.join(r['supported_handlers'])})

def esc(value):
    return html.escape(str(value))
def table(headers, body):
    return '<table><thead><tr>' + ''.join('<th>'+esc(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in body) + '</tbody></table>'
by_class = {r['qualified_class']: r for r in rows}
catalog_rows = []
for c in data['catalog']:
    r = by_class.get(c['resolved_class'])
    catalog_rows.append([esc(c['alias']), '<code>'+esc(c['handler'])+'</code>', esc(r['status'] if r else 'Ошибка legacy-каталога'), esc(r['works'] if r else ''), esc(r['gaps'] if r else 'Ошибка имени ExploreElementWdg вместо ExplorerElementWdg; renderer также не подключён.')])
parts = ['<!doctype html><html lang="ru"><meta charset="utf-8"><title>Table View — аудит 2026-10-13</title><style>body{font:15px/1.5 system-ui;background:#24292e;color:#e5e9ed;margin:24px}h1{font-size:26px}table{border-collapse:collapse;width:100%;margin:18px 0}td,th{padding:10px;text-align:left;border-bottom:1px solid #4b5158;vertical-align:top}th{background:#343a40}code{overflow-wrap:anywhere}a{color:#85c4e5}p{max-width:1100px}.partial{color:#f1cc75}.missing{color:#ff9e9e}</style><h1>Table View — готовность legacy-виджетов</h1>']
parts += ['<p>'+esc(n)+'</p>' for n in notes]
parts += ['<p><a href="table-view-audit.csv">Полный CSV для Excel</a> · <a href="table-view-audit.json">JSON с исходниками и проверками</a></p><h2>Основной каталог Table View (19 aliases)</h2>', table(['Alias','Handler','Статус','Работает','Осталось'], catalog_rows)]
parts += ['<h2>Общий контракт таблицы (не входит в число cell-классов)</h2>', table(['Контракт','Статус','Ограничение'], [[esc(x) for x in r] for r in table_contract])]
parts += ['<h2>Группы по назначению</h2>', table(['Группа', 'Классов'], [[esc(g), str(n)] for g,n in sorted(Counter(r['group'] for r in rows).items())])]
for status in ['Частично', 'Не подключён', 'Недописан в legacy', 'Исключён ранее', 'Совместимый alias']:
    group = [r for r in rows if r['status'] == status]
    parts.append('<h2>'+esc(status)+' — '+str(len(group))+'</h2>')
    parts.append(table(['Класс','Группа / область','Работает','Скрин ТС (тестовые значения)','Осталось / причина','Проверка исходника / перенос','Исходник legacy','Класс TS'], [[
        '<code>'+esc(r['qualified_class'])+'</code>', esc(r['group']+' / '+(', '.join(r['catalog_aliases']) or r['scope'])), esc(r['works']),
        '<img width="240" alt="Пример компонента ТС на тестовых значениях" src="../../src/tactic_stream/web/help/media/'+esc(r['screenshot'])+'">' if r['screenshot'] else 'Не снят',
        esc(r['gaps']), esc(r['legacy_review']+' '+r['migration']),
        '<code>'+esc(r['legacy_file']+':'+str(r['legacy_line']))+'</code>', '<code>'+esc(r['stream_class'] or 'Нет класса с этим полным именем')+'</code>'
    ] for r in group]))
parts.append('</html>')
(HERE / 'table-view-audit.html').write_text(''.join(parts), encoding='utf-8')
with (HERE / 'table-view-audit.csv').open(encoding='utf-8-sig', newline='') as f:
    assert len(list(csv.DictReader(f, delimiter=';'))) == len(rows)
assert len(json.loads((HERE / 'table-view-audit.json').read_text(encoding='utf-8'))['widgets']) == len(rows)
print(json.dumps(dict(version=version, counts=dict(counts), checks='PASS: offline descriptors + unique inventory + CSV/JSON round-trip'), ensure_ascii=False))
