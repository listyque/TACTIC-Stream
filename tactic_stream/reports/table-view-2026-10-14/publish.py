"""Publish the current Handler table port and its reproducible paired evidence."""
import ast
import html
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tactic_stream.server.table_cells import WIDGETS

tree = ast.parse(Path('D:/code/th_codex/thlib/tactic_table_widgets.py').read_text(encoding='utf-8'))
registry = next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'table_classes' for target in node.targets))
names = ast.literal_eval(registry.values[0])
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'extend' and isinstance(node.func.value, ast.Subscript) and node.func.value.slice.value == 'tactic':
        names += ast.literal_eval(node.args[0])
assert len(names) == 45 and not set(names) - WIDGETS.keys()
classes = sorted({WIDGETS[name].__name__ for name in names})
assert len(classes) == 21
groups = {
    'Values / Значения': ['SimpleTableElementWdg','RawTableElementWdg','FormatElementWdg','ArrayTableElementWdg','XmlWdg','JsonElementWdg','SnapshotVersionElementWdg'],
    'Expressions and links / Вычисления и ссылки': ['ExpressionElementWdg','ExpressionValueElementWdg','LinkElementWdg'],
    'Preview and collaboration / Превью и общение': ['ThumbWdg','DiscussionElementWdg','TaskElementWdg','TaskCompletionWdg'],
    'Actions / Действия': ['SObjectDetailElementWdg','CheckinButtonElementWdg','ExplorerElementWdg','ExplorerTableElementWdg','SObjectFilesElementWdg','MetadataElementWdg','DeleteElementWdg'],
}
assert sorted(sum(groups.values(), [])) == classes
aliases = [{'alias':name,'class':WIDGETS[name].__name__,'scope':'Current adapted Handler scenario'} for name in names]
(HERE/'handler-widget-checklist.json').write_text(json.dumps({'handler_aliases':len(names),'classes':len(classes),'groups':groups,'aliases':aliases},ensure_ascii=False,indent=2),encoding='utf-8')

actions = [
    ('detail','SObjectDetailElementWdg','Details opens the object inspector. use_parent selects the native parent.','Details открывает инспектор объекта. use_parent выбирает штатного родителя.'),
    ('general_checkin','CheckinButtonElementWdg','Check-in preserves the native target, process and context and opens the Drop Plate dock. Browser files are uploaded to the server.','Check-in сохраняет штатную цель, процесс и контекст и открывает док Drop Plate. Файлы браузера загружаются на сервер.'),
    ('folder','ExplorerElementWdg','Explorer resolves a native sandbox/repository path and copies it. Opening a client folder requires the separately excluded desktop bridge.','Explorer вычисляет штатный sandbox/repository путь и копирует его. Открытие папки клиента требует отдельно исключённого desktop bridge.'),
    ('files','SObjectFilesElementWdg','Files opens the object inspector with existing file and preview operations.','Files открывает инспектор объекта со штатными файлами и превью.'),
    ('metadata','MetadataElementWdg','Metadata opens the existing inspector; native metadata actions remain authoritative.','Metadata открывает существующий инспектор; изменения выполняются штатными metadata actions.'),
    ('delete','DeleteElementWdg','Delete opens the native object deletion confirmation; it never deletes on the first cell click.','Delete открывает подтверждение штатного удаления объекта; первый клик по ячейке ничего не удаляет.'),
]
for language in ('en','ru'):
    ru = language == 'ru'
    lines = ['---\ngroup: Guide\nicon: table\norder: 93\n---', '# '+('Table View и редактор колонок' if ru else 'Table View and Columns Editor'),
        ('Текущий адаптированный Table View ТХ перенесён в ТС: **45 зарегистрированных имён, 21 класс**. Это готовность действующих сценариев ТХ, а не полного старого HTML/JS runtime. Незавершённые исходники не переносятся.' if ru else 'The current adapted Handler Table View is ported to Stream: **45 registered names, 21 classes**. This covers current Handler scenarios, not the entire old HTML/JS runtime. Unfinished source widgets stay excluded.'),
        '## '+('Таблица' if ru else 'Table'),
        ('Округлый заголовок, высота строки 58, превью 50, карточки задач 107 × 50, process chips заметок, относительные даты, обрезка длинного текста и фон выделения следуют ТХ. Ctrl/Shift и клавиатура выбирают строки. Двойной клик по строке открывает объект; двойной клик по редактируемой ячейке открывает штатный input. Описание редактируется в текстовой панели. Enter или выход из поля сохраняет текст целиком; Escape отменяет.' if ru else 'Rounded header, 58px rows, 50px previews, 107 × 50px task cards, process note chips, relative dates, text elision and selection follow Handler. Ctrl/Shift and keyboard select rows. Double-click a row to inspect it; double-click an editable cell to use its native input. Description uses a text panel. Enter or leaving the field commits the full text; Escape cancels.'),
        '![TH](media/handler-table-th-dark.png)\n\n![Stream](media/handler-table-stream-dark.png)',
        ('Меню заголовка: сортировка, группировка/снятие группировки, настройка display/input definition, скрытие колонки, порядок и высота строки. Границы колонок изменяют ширину мышью или стрелками с шагом 8/16. Auto Fit подгоняет ширины. Кнопка колонок выбирает сохранённый вид и сохраняет текущий как новый. Это тот же config/widget_config, без отдельного хранилища. Большие выдачи виртуализированы; вычисления ячеек идут пакетами не больше 500 объектов.' if ru else 'Header menu: sorting, grouping/ungrouping, display/input definition, hide, order and row height. Drag column boundaries or use arrows in 8/16px steps. Auto Fit fits widths. The columns button selects saved views or saves a new one. All use config/widget_config, without another store. Long results are virtualized; server cells are read in batches of at most 500 objects.'),
        '## '+('Правки и задачи' if ru else 'Edits and tasks'),
        ('Input разрешается через edit/edit_definition и реальную action.column. Поэтому Assets Category редактирует assets_category_code. Групповая правка проверяет все ревизии до первого EditCmd; сбой откатывает весь batch. ID/code/project/timestamp/login и read_only защищены. Конфликт сохраняет черновик; неизвестный исход записи проверяется на сервере до повторной попытки. Смена ticket/project запрещает сохранение старого черновика.' if ru else 'Inputs resolve through edit/edit_definition and the real action.column. Assets Category therefore edits assets_category_code. Batch edits validate every revision before the first EditCmd; failure rolls back the entire batch. ID/code/project/timestamp/login and read_only are protected. Conflicts retain drafts; unknown save outcomes are checked before retrying. A ticket/project change blocks writes from the old draft.'),
        ('Карточки задач используют компактные редакторы статуса и пользователя и отдельную панель дат. Правки выбранных задач остаются pending до Save task changes. Hover раскрывает все карточки; hover выбранной строки раскрывает превью всех выбранных строк. Touch закрепляет превью, Escape/клик снаружи/прокрутка закрывают. Значок с количеством открывает Task Manager/Inspector.' if ru else 'Task cards use compact status/user editors and a separate dates panel. Selected task changes remain pending until Save task changes. Hover reveals all cards; hovering a selected row previews every selected row. Touch pins previews; Escape/outside click/scroll closes them. The count icon opens Task Manager/Inspector.'),
        ('Если статус ещё не выбран, «Выберите статус» служит подсказкой; выберите статус задачи из списка. Переключение языка само по себе не изменяет задачу.' if ru else 'An unset status displays Select status as a hint; choose a task status from the list. Changing language does not itself modify the task.'),
        ('Превью сохраняет полную высоту карточек. Когда все задачи помещаются, полос прокрутки нет; в узком окне доступна только горизонтальная прокрутка. Нажатие внутри открытого превью закрепляет его; прокрутка самой ленты не закрывает превью.' if ru else 'The preview retains the full card height. When all tasks fit, no scrollbars appear; narrow windows use horizontal scrolling only. Press inside an open preview to pin it; scrolling its own card strip keeps it open.'),
        '![TH task preview](media/handler-task-preview-th-dark.png)\n\n![Stream task preview](media/handler-task-preview-stream-dark.png)',
        '## Columns Editor',
        ('Слева каталог сохранённых определений с фильтром Search Type и поиском. Справа Wizard/XML; Wizard меняет title, hidden, width и display widget. Колонка, вызванная из таблицы, выбирается сразу. Splitter работает горизонтально/вертикально по ширине окна. Неизвестные опции, другие элементы и комментарии остаются в XML. Save to server сохраняет исходную запись с проверкой ревизии; Discard возвращает сохранённый XML.' if ru else 'Saved definitions, Search Type filter and search are on the left. Wizard/XML are on the right. Wizard changes title, hidden, width and display widget; the requested table column is selected immediately. Splitters adapt to width. Unknown options, other elements and comments remain in XML. Save to server updates the original record with revision validation; Discard restores stored XML.'),
        '![TH editor](media/handler-columns-editor-th-dark.png)\n\n![Stream editor](media/handler-columns-editor-stream-dark.png)',
        '## '+('Готовые адаптированные классы' if ru else 'Adapted working classes')]
    for group,members in groups.items():
        lines += ['### '+group.split(' / ')[1 if ru else 0], '\n'.join('- `'+name+'`' for name in members)]
    lines += ['## '+('Примеры действий' if ru else 'Action examples'),
        ('Добавляйте element в существующий table, не заменяйте весь конфиг. Остальные примеры значений, XML/JSON, вычислений и completion — [в каталоге](table_widget_examples.ru.md). Все class aliases перечислены в reports/table-view-2026-10-14/handler-widget-checklist.json.' if ru else 'Add each element to an existing table; do not replace the whole config. Value, XML/JSON, expression and completion examples are in the [catalog](table_widget_examples.en.md). All class aliases are listed in reports/table-view-2026-10-14/handler-widget-checklist.json.')]
    for name,widget,en,russian in actions:
        options = '<process>publish</process><mode>upload</mode>' if name == 'general_checkin' else '<mode>repository</mode>' if name == 'folder' else ''
        lines += ['### '+widget, russian if ru else en, f'```xml\n<element name="{name}" width="64">\n  <display class="tactic.ui.table.{widget}">{options}</display>\n</element>\n```']
    lines += ['## '+('Проверка и границы' if ru else 'Validation and limits'),
        ('Парные снимки: текущие QML ТХ и Vue ТС, один временный CG-проект, EN, MD3 dark/light, Segoe UI, 1496 × 660, DPI 96/scale 1. Данные и запись проверены отдельно штатными native командами. Captures используют отдельные display controllers и не доказывают работу пользовательского сервера. HTTP, XML-RPC, ревизии, rollback и admin-only проверяются отдельными тестами. Пиксельное сглаживание шрифтов Qt и Chromium различается. Физические телефоны, другие DPI и другие серверные СУБД в этом прогоне не проверены.' if ru else 'Paired captures use current Handler QML and Stream Vue, one temporary CG project, EN, MD3 dark/light, Segoe UI, 1496 × 660, DPI 96/scale 1. Native commands separately validate data and writes. Captures use isolated display controllers and do not prove a user server session. HTTP, XML-RPC, revisions, rollback and admin-only behavior have separate tests. Qt and Chromium font rasterization differs. Physical phones, other DPI and other database engines were not checked in this run.'),
        ('Browser check-in загружает файлы на сервер; локальные DCC/каталоги и desktop transfer move/link не воспроизводятся браузером. XML/JSON остаются structured display, как в текущем ТХ; произвольные JS/HTML actions и старые totals не включаются в этот перенос.' if ru else 'Browser check-in uploads files to the server. Local DCC/folders and desktop move/link transfers are not available in the browser. XML/JSON remain structured display, as in current Handler. Arbitrary JS/HTML actions and old totals are outside this port.')]
    for folder in (ROOT/'frontend/public/help',ROOT/'src/tactic_stream/web/help'):
        (folder/f'table_view.{language}.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
        index_path=folder/'index.json'; index=json.loads(index_path.read_text(encoding='utf-8'))
        if not any(row['id']=='table_view' for row in index):
            index.append({'id':'table_view','languages':['en','ru']}); index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for article in ('widget_database','table_widget_examples','table_widget_checklist'):
            path=folder/f'{article}.{language}.md'; source=path.read_text(encoding='utf-8')
            marker='[Table View / Columns Editor]'
            if marker not in source:
                note = ('Обновление 14 октября: текущие 45 имён/21 адаптированный класс ТХ, действия и общий редактор перенесены. Ниже — исходный аудит legacy и прежние примеры; полная legacy-готовность не заявляется.' if ru else 'October 14 update: the current 45 names/21 adapted Handler classes, actions and shared editor are ported. The original legacy audit/examples below remain historical; full legacy parity is not claimed.')
                position=source.index('\n',source.index('# '))
                source=source[:position]+f'\n\n{marker}(table_view.{language}.md) — {note}\n'+source[position:]
                path.write_text(source,encoding='utf-8')
        media=folder/'media'; media.mkdir(exist_ok=True)
        for kind in ('table','columns-editor','task-preview'):
            for client in ('th','stream'):
                for mode in ('dark','light'):
                    shutil.copyfile(HERE/f'{kind}-{client}-{mode}.png',media/f'handler-{kind}-{client}-{mode}.png')

escape=html.escape
parts=['''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Table View: ТХ → ТС</title><style>
body{font:15px/1.5 "Segoe UI",sans-serif;margin:24px;background:#24292e;color:#e5e9ed}h1{font-size:26px}a{color:#85c4e5}button,input,select{font:inherit}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:9px;border-bottom:1px solid #50555a}code{overflow-wrap:anywhere}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair img{width:100%;border:1px solid #50555a}figure{margin:0}p{max-width:1100px}.light{display:none}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style>
<h1>Table View ТХ → ТС · 14 октября 2026</h1><p>Перенесены действующие адаптированные сценарии: 45 зарегистрированных имён, 21 класс, таблица и редактор колонок. Полный старый HTML/JS runtime и незавершённые исходники сюда не входят.</p>
<p>Свежие текущие QML/Vue: один временный CG-проект, пять Assets, EN, MD3, Segoe UI, 1496 × 660, 96 DPI / scale 1. Qt и Chromium используют разные растеризаторы шрифтов. Контроллеры снимков изолированы; native операции, HTTP и XML-RPC проверяются отдельно.</p>
<label>Тема <select onchange="document.querySelectorAll('.dark,.light').forEach(el=>el.style.display=el.className===this.value?'grid':'none')"><option>dark</option><option>light</option></select></label>''']
for kind,title in [('table','Таблица'),('task-preview','Превью задач при наведении'),('columns-editor','Редактор колонок')]:
    parts.append('<h2>'+title+'</h2>')
    for mode in ('dark','light'):
        parts.append(f'<div class="{mode}" style="display:{"grid" if mode=="dark" else "none"}"><div class="pair">'+''.join(f'<figure><figcaption>{client.upper()}</figcaption><a href="{kind}-{client}-{mode}.png"><img src="{kind}-{client}-{mode}.png" alt="{client}"></a></figure>' for client in ('th','stream'))+'</div></div>')
parts += ['<h2>Проверено</h2><p>Регистрация всех 45 имён; 10 реальных CG-колонок без unsupported/error; geometry header/row/preview/task card; selection/keyboard, sorting/grouping, auto-fit, resize/order/hide/presets/conflicts; native text and foreign-key edits, batch rollback, rights; inline assignee and task drafts; 1000 rows with virtualized display and bounded batches; Columns Editor Wizard/XML, requested column, EN/RU and width 320. Свежие QML/Vue hover-превью: четыре карточки, 456 × 68, без обрезки и лишних скроллов. Браузерные проверки RU, pixel scale 1.25/1.5, высот строк 58/84 и ширины 320: единственная горизонтальная прокрутка сохраняет доступ к последней задаче.</p>',
    '<h2>Границы</h2><p>Открытие клиентских папок/локальных DCC и move/link требуют desktop bridge. Explorer копирует штатный путь; check-in использует browser upload. XML/JSON, source totals и неподключённые legacy options не объявлены полностью готовыми. Физический телефон, другие DPI и PostgreSQL в этом прогоне не проверены.</p>',
    '<h2>Рабочий реестр ТХ</h2><table><tr><th>Имя в конфигурации</th><th>Адаптированный класс</th></tr>']
parts += [f'<tr><td><code>{escape(row["alias"])}</code></td><td>{escape(row["class"])}</td></tr>' for row in aliases]
parts += ['</table><p><a href="native-measurements.json">Измерения и SHA QML</a> · <a href="stream-measurements.json">Браузерные проверки</a> · <a href="handler-widget-checklist.json">Реестр JSON</a> · <a href="../table-view-2026-10-13/used-table-widget-checklist.html">Общий legacy checklist</a></p></html>']
(HERE/'table-view-parity.html').write_text(''.join(parts),encoding='utf-8')
print(json.dumps({'handler_aliases':len(names),'classes':len(classes),'paired_images':12,'help_languages':2}))
