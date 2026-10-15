"""Publish the reviewed inventory and checked examples in the existing Help."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
STREAM = HERE.parents[1]
sys.path.insert(0, str(STREAM / 'src'))
from pyasm.search.search import RequestContext, request_context
from pyasm.widget import WidgetConfig
from tactic_stream.server.table_cells import describe_cell, WIDGETS
from pyasm.common import Config

audit = json.loads((HERE / 'table-view-audit.json').read_text(encoding='utf-8'))
groups = {
    'Значения и форматирование': 'Values and formatting',
    'Вычисления и итоги': 'Calculations and totals',
    'Задачи и показатели': 'Tasks and metrics',
    'Календарь и сроки': 'Calendar and schedules',
    'Файлы и версии': 'Files and versions',
    'Заметки и общение': 'Notes and communication',
    'Связи и вложенные объекты': 'Relationships and nested objects',
    'Компоновка и действия': 'Composition and actions',
    'Администрирование и настройки': 'Administration and settings',
    'Исключённый production': 'Excluded production',
}
statuses = {'Частично': 'Partial', 'Не подключён': 'Not connected', 'Исключён ранее': 'Excluded', 'Совместимый alias': 'Input alias', 'Недописан в legacy': 'Unfinished in legacy'}
examples = [
    ('simple', 'name', 'tactic.ui.common.SimpleTableElementWdg', {}, 'Text / Текст',
     'A physical field. The basic renderer supports column; generic inline editing, empty and totals are still missing.',
     'Физическое поле. Базовый renderer поддерживает column; общего inline edit, empty и итогов пока нет.', {'text': 'Lighting review'}),
    ('raw', 'description', 'tactic.ui.common.RawTableElementWdg', {}, 'Raw value / Сырое значение',
     'Displays the stored value. It does not apply the old get_display timestamp conversion or generic inline editing.',
     'Показывает сохранённое значение. Старое преобразование timestamp из get_display и общий inline edit не подключены.', {'text': '2026-10-13 10:30:00'}),
    ('format', 'amount', 'tactic.ui.table.FormatElementWdg', {'type': 'float', 'format': '-1234.12'}, 'Formatted number / Форматированное число',
     'Native number/date/timecode formats; type, format, fps, timezone, constraint. Checkbox is read-only; no total_summary.',
     'Нативные форматы чисел, дат и timecode; type, format, fps, timezone, constraint. Checkbox только для чтения; total_summary нет.', {'text': '1250.50'}),
    ('link', 'website', 'tactic.ui.table.LinkElementWdg', {}, 'Link / Ссылка',
     'Text link to HTTP(S), mailto or a root-relative URL. The icon option is not rendered. Executable/file URLs are rejected.',
     'Текстовая ссылка на HTTP(S), mailto или URL от корня. Опция icon не отображается. Исполняемые/file URL отвергаются.', {'text': 'https://example.com/review', 'href': 'https://example.com/review'}),
    ('expression', 'computed_name', 'tactic.ui.table.ExpressionElementWdg', {'expression': '@GET(.name)'}, 'Expression / Выражение',
     'Computes a virtual field with the native parser. Also supports value/boolean/check, alternate/display expressions and cache. No bottom/group_bottom, link/icon modes or general recalculate button.',
     'Вычисляет виртуальную колонку штатным parser. Есть value/boolean/check, alternate/display expression и cache. Нет bottom/group_bottom, link/icon режимов и общей кнопки пересчёта.', {'text': 'Lighting review'}),
    ('expression_value', 'formula', 'tactic.ui.table.ExpressionValueElementWdg', {}, 'Expression stored in a field / Выражение из поля',
     'The formula field must contain a native expression, e.g. @GET(.name). Its result is displayed; this is not an inline expression editor.',
     'Поле formula должно содержать нативное выражение, например @GET(.name). Выводится результат; inline редактора выражения нет.', {'text': 'Lighting review'}),
    ('thumb', 'preview', 'pyasm.widget.ThumbWdg', {'filename': 'true', 'icon_context': 'icon'}, 'File preview / Превью файла',
     'Uses existing Snapshot/File records and opens FilePreview. Supports context/cascade/latest/original, filename/file_type, HTTP. No legacy detail/redirect/size/JS options.',
     'Использует существующие Snapshot/File и открывает FilePreview. Есть context/cascade/latest/original, filename/file_type, HTTP. Старые detail/redirect/size/JS опции не подключены.', {'text': '/tests/fixtures/messages-attachment.png', 'image': '/tests/fixtures/messages-attachment.png', 'filename': 'lighting.png', 'files': []}),
    ('discussion', 'notes', 'tactic.ui.widget.DiscussionElementWdg', {'process': 'publish', 'allow_email': 'false'}, 'Notes / Заметки',
     'Process counters open the configured notes inspector. process/context/use_parent and default/icon modes are supported. Email is not implemented.',
     'Счётчики процессов открывают настроенный инспектор заметок. Есть process/context/use_parent и default/icon. Email не реализован.', {'search_key': 'cg/demo?project=cg&code=DEMO001', 'count': 2, 'process': 'publish', 'processes': [{'process': 'publish', 'count': 2}]}),
    ('task', 'tasks', 'tactic.ui.table.TaskElementWdg', {'process': 'lighting'}, 'Tasks / Задачи',
     'Uses existing related tasks and their process/pipeline rules. Opens inspection and the task editor. Legacy CGI child-task filters and the full old presentation options are not migrated.',
     'Использует существующие связанные задачи и правила process/pipeline. Открывает инспектор и редактор задач. Старые CGI child-task filters и полный набор presentation опций не перенесены.', {'tasks': [{'taskSearchKey': 'sthpw/task?code=DEMO_TASK', 'process': 'lighting', 'context': 'lighting', 'status': 'In Progress', 'statusColor': '#78a6c4', 'assigned': 'artist', 'assignedIdentity': {'displayName': 'Demo artist', 'initials': 'DA', 'avatarColor': '#43796c'}, 'bidStart': '2026-10-13', 'bidEnd': '2026-10-15'}]}),
    ('completion', 'completion', 'tactic.ui.table.TaskCompletionWdg', {}, 'Completion / Готовность',
     'Reads the native completion average for related tasks. The current row now uses the TH progress bar: 18px, 10px margins, 0–100%, text and accessible values. task_expr can select a subset. Group/footer totals remain missing.',
     'Читает нативный средний процент связанных задач. Строка теперь использует полосу ТХ: 18px, отступы 10px, 0–100%, текст и доступное значение. task_expr выбирает подмножество. Итоги группы/таблицы пока отсутствуют.', {'text': '25.0%', 'completion': 25, 'count': 4}),
    ('array', 'tags', 'ArrayTableElementWdg', {}, 'Array / Массив',
     'The used legacy array cell strips edge pipes and replaces internal || with comma-space. It is read-only and does not change the stored value.',
     'Используемая legacy-ячейка массива убирает крайние | и заменяет внутренние || на запятую с пробелом. Только отображение; исходное значение не изменяется.', {'raw_value': '||Assets||Shots||Textures||'}),
    ('xml', 'snapshot', 'XmlWdg', {}, 'XML / XML',
     'Shows raw XML or decompresses the native zlib: form. Invalid XML keeps its text and shows a diagnostic; no HTML/script execution. Raw SDK/CSV values stay unchanged. General inline editing remains a separate table contract.',
     'Показывает XML или распаковывает нативный zlib: формат. Некорректный XML сохраняет текст и показывает ошибку; HTML/скрипты не исполняются. Raw SDK/CSV не изменяется. Общий inline edit остаётся отдельным контрактом таблицы.', {'raw_value': '<snapshot>\n  <file name="lighting.exr" type="main" />\n</snapshot>'}),
    ('json', 'metadata', 'tactic.ui.table.JsonElementWdg', {'height': '72px'}, 'JSON / JSON',
     'Original sorted keys, two-space indentation and an empty display for false/empty JSON; maximum height is a pixel value up to 600. Read/copy/scroll support is implemented. General inline editing remains separate.',
     'Исходная сортировка ключей, отступ в два пробела и пустое отображение для false/пустого JSON; максимальная высота — до 600px. Есть чтение/копирование/прокрутка. Общий inline edit остаётся отдельным контрактом.', {'raw_value': {'a': {'ready': True}, 'b': [1, 2], 'label': 'Lighting'}}),
    ('snapshot_version', 'version', 'tactic.ui.table.SnapshotVersionElementWdg', {}, 'Snapshot version / Версия снапшота',
     'Empty means No version, -1 Latest, 0 Current; positive versions use the field initial and checkin/version_padding (default 3). Only display; NULL now shows No version instead of raising a formatting error.',
     'Пустое значение — Нет версии, -1 — Последняя, 0 — Текущий; положительная версия использует первую букву поля и checkin/version_padding (по умолчанию 3). Только отображение; NULL теперь показывает Нет версии вместо ошибки форматирования.', {'raw_value': 3}),
]
columns = {name: {'data_type': 'text'} for name in ['name', 'description', 'amount', 'website', 'formula', 'tags', 'snapshot', 'metadata', 'version']}
fixture = []
with request_context(RequestContext(None, 'admin')):
    for key, name, handler, options, title, en, ru, cell in examples:
        root = ET.Element('config')
        view = ET.SubElement(root, 'table', {'layout': 'tactic.ui.panel.TableLayoutWdg'})
        attrs = {'name': name}
        if key == 'completion':
            attrs['width'] = '240'
        node = ET.SubElement(view, 'element', attrs)
        display = ET.SubElement(node, 'display', {'class': handler})
        for option, value in options.items():
            ET.SubElement(display, option).text = value
        ET.indent(root)
        xml = ET.tostring(root, encoding='unicode')
        config = WidgetConfig.get(view='table', xml=xml, use_cache=False)
        assert config.get_display_handler(name) == handler
        opts = config.get_display_options(name)
        element = {'name': name, 'title': title.split(' / ')[0], 'display': {'handler': handler, 'options': opts}, 'action': {'handler': ''}}
        descriptor = describe_cell(element, columns)
        assert descriptor['supported'], (key, descriptor)
        if 'raw_value' in cell:
            raw = cell['raw_value']
            widget = WIDGETS[handler](name=name)
            widget.set_sobjects([SimpleNamespace(get_value=lambda key, **kwargs: raw, get_json_value=lambda key: raw, is_insert=lambda: False)])
            with patch.object(Config, 'get_value', return_value='3'):
                cell = widget.get_cell_value()
        fixture.append({'key': key, 'element': {**element, **descriptor, 'cell': descriptor}, 'record': {}, 'value': cell, 'xml': xml})
assert len(fixture) == 14 and next(s for s in fixture if s['key'] == 'completion')['element']['cell']['kind'] == 'completion'
(STREAM / 'frontend/tests/fixtures/table-widget-catalog.json').write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding='utf-8')

for language in ['en', 'ru']:
    ru = language == 'ru'
    catalog = [f'---\ngroup: {"Guide"}\nicon: table\norder: 94\n---\n# '+('Каталог виджетов Table View' if ru else 'Table View widget database'),
        '> '+('Виджеты сгруппированы по назначению, готовности и состоянию исходника. Перенос начинается с воспроизводимого сценария.' if ru else 'Widgets grouped by purpose, readiness and source condition. Migration starts with a reproducible scenario.'),
        '## '+('Правило переноса' if ru else 'Migration rule'),
        ('Сначала изучаем исходник, наследование и вызывающие места; готовим тестовый XML и данные; снимаем legacy/ТХ и ТС при одинаковой теме, языке, масштабе и размере; описываем параметры, действия, права и ограничения; проверяем и переносим. Явно недописанные классы не переносим. TODO, известный баг или pass у alias сами по себе не делают виджет недописанным.' if ru else 'Read the source, inheritance and callers first. Prepare test XML and data. Capture legacy/TH and Stream with the same theme, language, scale and size. Document options, actions, permissions and limitations, then verify and migrate. Clearly unfinished classes are excluded. A TODO, known bug or pass in an alias is not enough to declare a widget unfinished.'),
        '## '+('Статусы' if ru else 'Statuses'),
        ('14 классов имеют рабочий базовый сценарий; HiddenRow работает только в журнале транзакций. 134 класса пока не подключены. Полная готовность этих классов не заявляется. TextWdg — один совместимый input alias. 43 pyasm.prod уже исключены; SnapshotServerElementWdg теперь исключён как явная заглушка. PlaceHolderElementWdg — намеренно пустая служебная ячейка.' if ru else '14 classes have a working basic scenario; HiddenRow only supports transaction details. 134 classes are not connected. Complete class parity is not claimed. TextWdg is one compatible input alias. 43 pyasm.prod classes were already excluded; SnapshotServerElementWdg is now excluded as an explicit stub. PlaceHolderElementWdg is an intentionally empty infrastructure cell.'),
        '[ '+('Примеры XML и скриншоты' if ru else 'XML examples and screenshots')+' ](table_widget_examples.'+language+'.md)',
        '## '+('Первые проверяемые шаги' if ru else 'First verifiable steps'),
        ('Теперь закрыт блок отображения Array/XML/JSON/SnapshotVersion; inline XML/JSON edit ещё не готов. Все упоминания в widget configs входят в отдельный рабочий чеклист. Полоса TaskCompletionWdg соответствует текущему TacticCompletionCell ТХ на примере 0/25/75/100%. Далее: выравнивание Format, сценарии файлов/metadata/details, связи и вложенные таблицы, затем более сложные actions/layout. Каждая следующая задача требует своего эталона и примера; реализуем все упомянутые в конфигах классы, кроме согласованных исключений и явно недописанных исходников.' if ru else 'The Array/XML/JSON/SnapshotVersion display block is now implemented; inline XML/JSON editing remains unfinished. Every mention in widget configs enters a separate working checklist. The TaskCompletionWdg bar follows the current TH TacticCompletionCell for 0/25/75/100%. Next: Format alignment, files/metadata/details, relationships and nested tables, then complex actions/layout. Every next task needs its own reference and example; all classes mentioned in configs are in scope, except agreed exclusions and clearly unfinished source.'),
        '## '+('Проверка исходника' if ru else 'Source review'),
        ('`tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` (строки 177–178) содержит только pass и наследует общий BaseTableElementWdg: не переносим. `ExplorerTableElementWdg` тоже содержит pass, но наследует реализацию ExplorerElementWdg: это alias, его не исключаем по этому признаку. В исходном каталоге explorer указан как ExploreElementWdg — такого класса нет. `SpreadsheetElementWdg` считает накопительный итог по column/format; это не полноценный spreadsheet editor.' if ru else '`tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` (lines 177–178) contains only pass and directly inherits the generic BaseTableElementWdg: excluded. ExplorerTableElementWdg also contains pass, but inherits ExplorerElementWdg implementation: it is an alias, not an unfinished widget. The source explorer catalog uses the nonexistent name ExploreElementWdg. SpreadsheetElementWdg calculates a running total from column/format; it is not a full spreadsheet editor.'),
        ('Все непроверенные классы остаются на этапе «нужен прогон исходника». Список не подтверждает, что оригинал работает. Form/Input/CellEdit и команды — отдельные контракты; общий inline edit и legacy bottom/group_bottom/total_summary пока не готовы.' if ru else 'Unreviewed classes remain at the source-reproduction stage. This inventory does not prove that the original works. Form/Input/CellEdit and commands are separate contracts; general inline editing and legacy bottom/group_bottom/total_summary remain unavailable.'),
    ]
    for group, english in groups.items():
        rows = [r for r in audit['widgets'] if r['group'] == group]
        catalog += ['## '+(group if ru else english)+f' ({len(rows)})',
                    '\n'.join(['| '+('Класс | Статус' if ru else 'Class | Status')+' |', '| --- | --- |'] +
                              ['| `'+r['qualified_class']+'` | '+(r['status'] if ru else statuses[r['status']])+' |' for r in rows])]
    catalog += ['## '+('Права и границы проверки' if ru else 'Permissions and verification limits'),
                ('Configured Table View доступен admin. Сервер проверяет проект/тип объектов и разрешённые опции. Неизвестные классы/options/actions не исполняются и не становятся «готовыми» от наличия Python файла. Примеры проверены native XML parser и describe_cell без БД; скриншоты Vue сняты с тестовыми типизированными значениями. Native ТХ снимался отдельно для Completion. Полный старый CGI runtime и остальные классы пока не запускались.' if ru else 'Configured Table View requires admin. The server checks record project/type and allowed options. Unknown classes/options/actions are not executed or declared ready merely because a Python file exists. Examples are checked with the native XML parser and describe_cell without a database. Vue screenshots use typed fixture values. Native TH is captured separately for Completion. The full old CGI runtime and the remaining classes have not been run.')]

    guide = [f'---\ngroup: Guide\nicon: table\norder: 95\n---\n# '+('Table View: примеры виджетов' if ru else 'Table View: widget examples'),
             '> '+('Рабочие базовые сценарии, XML и реальные снимки компонентов Vue на тестовых значениях.' if ru else 'Working basic scenarios, XML and real Vue component captures with fixture values.'),
             ('[Каталог и очередь исследования](widget_database.ru.md)' if ru else '[Database and investigation queue](widget_database.en.md)'),
             '## '+('Как использовать примеры' if ru else 'Using the examples'),
             ('В Columns Editor / Widget Configuration текущего SearchType возьмите элемент display из примера и добавьте в нужный table view. Полный config показывает структуру, но не предназначен для замены всех существующих колонок. Имена name/description/amount/website/formula замените реальными физическими полями. Для превью нужны Snapshot/File; для notes/tasks/completion — реальные связи и ACL. Эти снимки показывают renderer с подготовленными значениями, не результат запуска всех примеров в вашей БД.' if ru else 'In Columns Editor / Widget Configuration for the current SearchType, copy the display element into the intended table view. The full config illustrates structure; do not replace all existing columns with it. Replace name/description/amount/website/formula with real physical fields. Preview needs Snapshot/File; notes/tasks/completion need relationships and ACL. These captures show the renderer with prepared values, not every example executed against your database.'),
             ('Имя класса указывайте точно: старые pyasm.widget.TaskCompletionWdg и SimpleTableElementWdg не являются alias современных tactic.ui классов. Display action должен быть пуст; неподдержанные options приводят к Widget unavailable. Width колонки задаётся attribute элемента, не display option.' if ru else 'Use the exact class path: old pyasm.widget.TaskCompletionWdg and SimpleTableElementWdg are not aliases of the modern tactic.ui classes. The action handler must be empty; unsupported display options produce Widget unavailable. Column width is an element attribute, not a display option.')]
    for example, sample in zip(examples, fixture):
        key, name, handler, options, title, en, russian, cell = example
        guide += ['## '+title.split(' / ')[1 if ru else 0], '`'+handler+'`', russian if ru else en,
                  '![ '+title.split(' / ')[1 if ru else 0]+' ](media/table-widget-'+key+'.png)', '```xml\n'+sample['xml']+'\n```']
        if key in {'array', 'xml', 'json', 'snapshot_version'}:
            guide += [('Пара ТХ/ТС на одинаковых значениях, теме, языке и размере 320×128px:' if ru else 'TH/Stream pair with the same values, theme, language and 320×128px size:'),
                      '![TH](media/table-widget-'+key+'-th.png)', '![Stream](media/table-widget-'+key+'-stream.png)']
    guide += ['## '+('Эталон Completion в ТХ' if ru else 'Completion reference in TH'),
              ('Текущий TacticCompletionCell.qml, тёмная тема, 240×52px на ячейку, масштаб 100%, английский, 0/25/75/100%. Сравниваются высота/отступы полосы, ширина заполнения, текст и цвета. Это проверка данного presenter; групповые итоги старого виджета остаются отдельной задачей.' if ru else 'Current TacticCompletionCell.qml, dark theme, 240×52px per cell, 100% scale, English, 0/25/75/100%. Track height/margins, fill width, text and colors are compared. This verifies this presenter; old grouped totals remain a separate task.'),
              '![TH](media/table-widget-completion-th.png)', '![Stream](media/table-widget-completion-stream.png)']
    for folder in [STREAM / 'frontend/public/help', STREAM / 'src/tactic_stream/web/help']:
        for name, body in [('widget_database', catalog), ('table_widget_examples', guide)]:
            (folder / f'{name}.{language}.md').write_text('\n\n'.join(body)+'\n', encoding='utf-8')

for folder in [STREAM / 'frontend/public/help', STREAM / 'src/tactic_stream/web/help']:
    index_path = folder / 'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    for name in ['widget_database', 'table_widget_examples']:
        if not any(row['id'] == name for row in index):
            index.append({'id': name, 'languages': ['en', 'ru']})
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for language in ['en', 'ru']:
        overview = folder / f'overview.{language}.md'
        source = overview.read_text(encoding='utf-8')
        if 'widget_database.' not in source:
            link = '\n\n## '+('Виджеты Table View' if language == 'ru' else 'Table View widgets')+'\n\n'
            link += ('[Каталог по группам и статусам](widget_database.ru.md) · [XML-примеры со скриншотами](table_widget_examples.ru.md)\n' if language == 'ru' else '[Database by group and status](widget_database.en.md) · [XML examples with screenshots](table_widget_examples.en.md)\n')
            overview.write_text(source.rstrip()+link, encoding='utf-8')
print('Help catalog + bilingual grouped inventory + 14 native XML examples PASS')
