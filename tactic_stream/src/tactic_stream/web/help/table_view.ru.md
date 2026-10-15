---
group: Guide
icon: table
order: 93
---

# Table View и редактор колонок

Текущий адаптированный Table View ТХ перенесён в ТС: **45 зарегистрированных имён, 21 класс**. Это готовность действующих сценариев ТХ, а не полного старого HTML/JS runtime. Незавершённые исходники не переносятся.

## Таблица

Округлый заголовок, высота строки 58, превью 50, карточки задач 107 × 50, process chips заметок, относительные даты, обрезка длинного текста и фон выделения следуют ТХ. Ctrl/Shift и клавиатура выбирают строки. Двойной клик по строке открывает объект; двойной клик по редактируемой ячейке открывает штатный input. Описание редактируется в текстовой панели. Enter или выход из поля сохраняет текст целиком; Escape отменяет.

![TH](media/handler-table-th-dark.png)

![Stream](media/handler-table-stream-dark.png)

Меню заголовка: сортировка, группировка/снятие группировки, настройка display/input definition, скрытие колонки, порядок и высота строки. Границы колонок изменяют ширину мышью или стрелками с шагом 8/16. Auto Fit подгоняет ширины. Кнопка колонок выбирает сохранённый вид и сохраняет текущий как новый. Это тот же config/widget_config, без отдельного хранилища. Большие выдачи виртуализированы; вычисления ячеек идут пакетами не больше 500 объектов.

## Правки и задачи

Input разрешается через edit/edit_definition и реальную action.column. Поэтому Assets Category редактирует assets_category_code. Групповая правка проверяет все ревизии до первого EditCmd; сбой откатывает весь batch. ID/code/project/timestamp/login и read_only защищены. Конфликт сохраняет черновик; неизвестный исход записи проверяется на сервере до повторной попытки. Смена ticket/project запрещает сохранение старого черновика.

Карточки задач используют компактные редакторы статуса и пользователя и отдельную панель дат. Правки выбранных задач остаются pending до Save task changes. Hover раскрывает все карточки; hover выбранной строки раскрывает превью всех выбранных строк. Touch закрепляет превью, Escape/клик снаружи/прокрутка закрывают. Значок с количеством открывает Task Manager/Inspector.

Если статус ещё не выбран, «Выберите статус» служит подсказкой; выберите статус задачи из списка. Переключение языка само по себе не изменяет задачу.

Превью сохраняет полную высоту карточек. Когда все задачи помещаются, полос прокрутки нет; в узком окне доступна только горизонтальная прокрутка. Нажатие внутри открытого превью закрепляет его; прокрутка самой ленты не закрывает превью.

![TH task preview](media/handler-task-preview-th-dark.png)

![Stream task preview](media/handler-task-preview-stream-dark.png)

## Columns Editor

Слева каталог сохранённых определений с фильтром Search Type и поиском. Справа Wizard/XML; Wizard меняет title, hidden, width и display widget. Колонка, вызванная из таблицы, выбирается сразу. Splitter работает горизонтально/вертикально по ширине окна. Неизвестные опции, другие элементы и комментарии остаются в XML. Save to server сохраняет исходную запись с проверкой ревизии; Discard возвращает сохранённый XML.

![TH editor](media/handler-columns-editor-th-dark.png)

![Stream editor](media/handler-columns-editor-stream-dark.png)

## Готовые адаптированные классы

### Значения

- `SimpleTableElementWdg`
- `RawTableElementWdg`
- `FormatElementWdg`
- `ArrayTableElementWdg`
- `XmlWdg`
- `JsonElementWdg`
- `SnapshotVersionElementWdg`

### Вычисления и ссылки

- `ExpressionElementWdg`
- `ExpressionValueElementWdg`
- `LinkElementWdg`

### Превью и общение

- `ThumbWdg`
- `DiscussionElementWdg`
- `TaskElementWdg`
- `TaskCompletionWdg`

### Действия

- `SObjectDetailElementWdg`
- `CheckinButtonElementWdg`
- `ExplorerElementWdg`
- `ExplorerTableElementWdg`
- `SObjectFilesElementWdg`
- `MetadataElementWdg`
- `DeleteElementWdg`

## Примеры действий

Добавляйте element в существующий table, не заменяйте весь конфиг. Остальные примеры значений, XML/JSON, вычислений и completion — [в каталоге](table_widget_examples.ru.md). Все class aliases перечислены в reports/table-view-2026-10-14/handler-widget-checklist.json.

### SObjectDetailElementWdg

Details открывает инспектор объекта. use_parent выбирает штатного родителя.

```xml
<element name="detail" width="64">
  <display class="tactic.ui.table.SObjectDetailElementWdg"></display>
</element>
```

### CheckinButtonElementWdg

Check-in сохраняет штатную цель, процесс и контекст и открывает док Drop Plate. Файлы браузера загружаются на сервер.

```xml
<element name="general_checkin" width="64">
  <display class="tactic.ui.table.CheckinButtonElementWdg"><process>publish</process><mode>upload</mode></display>
</element>
```

### ExplorerElementWdg

Explorer вычисляет штатный sandbox/repository путь и копирует его. Открытие папки клиента требует отдельно исключённого desktop bridge.

```xml
<element name="folder" width="64">
  <display class="tactic.ui.table.ExplorerElementWdg"><mode>repository</mode></display>
</element>
```

### SObjectFilesElementWdg

Files открывает инспектор объекта со штатными файлами и превью.

```xml
<element name="files" width="64">
  <display class="tactic.ui.table.SObjectFilesElementWdg"></display>
</element>
```

### MetadataElementWdg

Metadata открывает существующий инспектор; изменения выполняются штатными metadata actions.

```xml
<element name="metadata" width="64">
  <display class="tactic.ui.table.MetadataElementWdg"></display>
</element>
```

### DeleteElementWdg

Delete открывает подтверждение штатного удаления объекта; первый клик по ячейке ничего не удаляет.

```xml
<element name="delete" width="64">
  <display class="tactic.ui.table.DeleteElementWdg"></display>
</element>
```

## Проверка и границы

Парные снимки: текущие QML ТХ и Vue ТС, один временный CG-проект, EN, MD3 dark/light, Segoe UI, 1496 × 660, DPI 96/scale 1. Данные и запись проверены отдельно штатными native командами. Captures используют отдельные display controllers и не доказывают работу пользовательского сервера. HTTP, XML-RPC, ревизии, rollback и admin-only проверяются отдельными тестами. Пиксельное сглаживание шрифтов Qt и Chromium различается. Физические телефоны, другие DPI и другие серверные СУБД в этом прогоне не проверены.

Browser check-in загружает файлы на сервер; локальные DCC/каталоги и desktop transfer move/link не воспроизводятся браузером. XML/JSON остаются structured display, как в текущем ТХ; произвольные JS/HTML actions и старые totals не включаются в этот перенос.
