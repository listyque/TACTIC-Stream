# Готовность UI относительно legacy — 0.20

Это оценка **границ реализации**, а не проценты и не новая приёмка рабочего сервера.
**BASE** — основные перечисленные сценарии реализованы и имеют свидетельства в тестах/отчётах. **PARTIAL** — значимая часть есть, но полной замены нет. **NO_NATIVE_SCREEN** — отдельный эквивалент не найден, наличие generic-таблицы не засчитывается. **UNREVIEWED** — индивидуальной проверки нет.
Ни одна строка не означает полного совпадения всех kwargs, callbacks, прав и пользовательских конфигураций.

## Сводная матрица

| Область | Статус | Что есть | Что осталось | Приоритет |
|---|---|---|---|---|
| Resolver widget_config / definitions | BASE | Исходные DB/file/personal/default layers, независимые handler/options, inline/config_code, пустой view, provenance. | Все runtime DB-overrides/внешние плагины; полное поведение каждого обработчика не следует из metadata parity. | P1 |
| Рабочее пространство / основные вкладки | BASE | Проекты, конфигурационный sidebar, tabs, root/nested dispatch, DB-состояние, компактный shell, dirty guards. | Полный legacy URL/custom routing, tear-off и все callbacks; единый dispatcher вместо дублирования App/WidgetHost. | P1 |
| Sidebar и Schema Views | BASE | Original SidebarConfig; folder/link/title/separator, project/admin/my roots, исходный генератор Schema Views. | Все произвольные callbacks/персональные DB configurations и effective access для non-admin. | P1 |
| TableLayout / обычная таблица | PARTIAL | Metadata, серверные страницы/поиск/сортировка, геометрия, range selection, cells, меню, состояние БД. | Полная server Group By и totals всей выборки, unlimited/chunk-render, все table options, virtual insert-rows, custom layout hooks. | P1 |
| Display-виджеты ячеек | PARTIAL | Plain/format/link/XML, login display-name, task-status color, color, registered thumbnail, несколько global widget buttons. | Полный ExpressionElement/Task/Snapshot/Thumb/custom cells и handle_td/handle_tr семантика; generic raw display не равен widget parity. | P1 |
| CellEditWdg и edit_item | BASE | Отдельный lookup edit + inline + DB edit_item, options, зависимые choices, field/config revisions. | Не все input/actions/extra hooks, complex WorkHours/Gantt не входят в generic cell editor. | P1 |
| EditMultipleCmd / Save Changes | BASE | Буфер существующих строк, 100 rows/1000 cells; один исходный batch, update_multi, rollback и сохранение черновика. | Inline insert, полный Save All произвольных custom handlers; distributed exactly-once и rollback внешних effects не обеспечены. | P1 |
| Fill / Paste / Clipboard | PARTIAL | Заполнение выбранного поля по выбранным строкам с серверным preview, затем staging в общий буфер. | Excel TSV paste, прямоугольные диапазоны, Fill Down/series, полный legacy clipboard/undo-redo. | P1 |
| EditWdg / popup / embedded forms | PARTIAL | Самостоятельные insert/edit/view, original defaults/validation, bindings, hidden/disables, NULL/0, sibling form values, single, dirty guards. | parent/connect workflow, layout_view, custom edit_cmd/save callbacks, все оригинальные input/action types. | P1 |
| TabWdg / вложенные контейнеры | PARTIAL | Дочерние native widgets, include/saved/category semantics, preload, hidden, selected, retain mounted state, DB preference keys. | Динамические счетчики, load modes/callbacks, tear-off; native state не переписывает все legacy XML save_state. | P1 |
| Контекстные меню и table shelf | PARTIAL | Row/column/sidebar/tab/field/widget contexts; compact toolbar; File/Edit/View groups; доступность действий и клавиатура. | Все gear_menu_custom/gear_settings/SmartMenu callbacks, cascade Delete, Print/Chart, old Clipboard, Undo/Redo. | P1 |
| Поиск и сохранённые поиски | PARTIAL | Typed AND/OR, исходные supported saved filters/scopes, server sort/paging, named views widget_config, последний query WidgetSettings. | Весь GeneralFilter/custom filter/expression vocabulary, все legacy serialized last_search; свободный SQL не принимается. | P1 |
| Персональные UI-настройки | BASE | Original WidgetSettings/sthpw/wdg_settings, project/login/scope, geometry/query/workspace/tabs/timeline/stype-editor, debounce/revision. | Полный импорт всех старых XML/last_search и multi-host CAS; unsaved SObjects намеренно не persistence. | P1 |
| TileLayout / карточки | PARTIAL | Режим карточек той же выборки и отображаемых cells, сохранение буфера при переключении. | Полная TileLayoutWdg tile actions/geometry/template/collection behaviors; не считать режим cards точной копией всего класса. | P2 |
| Дерево и отношения | PARTIAL | Lazy relationships исходной Schema, циклы, кандидаты и поддержанные add_instance/remove_instance; link не равен объект. | Все relation/parent/connection types, deep bulk/drag-drop и нестандартные instance schemas. | P2 |
| Collections | PARTIAL | Исходные _is_collection и *_in_*; каталог/вложенность/add/remove/delete, cycles, original commands. | Все expression/parent-scoped layouts и shelf callbacks, комплексные пакетные операции. | P2 |
| Карточка SObject / notes / history | PARTIAL | RecordInspector с related/tasks/files/notes/history/subscription; Note.create, исходные журналы, retire/reactivate. | Все legacy tab/detail widgets, полный note sheet и cascade delete; HTML/custom body не эмулируется. | P2 |
| Задачи и task board | PARTIAL | Original task pipelines/choices, разделение статусов разных pipelines, Task.add_initial_tasks с preview, inline/popup edits. | Весь TaskElementWdg, все advanced assignment/automation/planning branches, шаблоны досок. | P2 |
| WorkHoursElement | PARTIAL | Исходный WorkHoursElementAction и привязки; плановый период/единицы/overtime/ноль по конфигурации. | Комплексные категории, start/end и дубли не агрегируются с перезаписью; полный timesheet UI. | P2 |
| Gantt и Calendar | PARTIAL | Отдельный server date-window, several bars, page loading, move dates через исходную форму, DB preference. | Resize, зависимости, resource load, auto-scheduling, holidays/calendars и полный original Gantt. | P2 |
| Project Workflow / Pipeline editor | PARTIAL | GraphEditor: CRUD узлов/связей/параметров, owner project, исходные PipelineSaveCbk/ProcessInfoCmd; reopen. | Все advanced process panels, nested pipelines, conditions/manual/approval/dependency semantics, rename с историей и все callbacks. | P2 |
| Project Schema editor | PARTIAL | Original Schema.get, read XML, graph existing types/relations, save project schema; встроенные schema readonly. | DDL whole schema designer, миграции связанных физических полей/отношений, полный drag-drop palette. | P2 |
| ProjectCreateWdg / мастер | PARTIAL | default/simple preflight/create/original CreateProjectCmd/new SQLite setup; переход и новый sidebar без restart. | Любые template-project imports, theme/preview в мастере, безопасное восстановление частичного create и durable result. | P2 |
| Manage sTypes | PARTIAL | Каталог, metadata, original column info/definitions; create type/add columns; переходы к table/form/views/workflow/schema; DB state. | DROP/RENAME/ALTER TYPE, полный triggers/notifications editor, все multi-db branches; dependencies не доказательство безопасного удаления. | P2 |
| CSV Import | PARTIAL | До 1 MiB/100 rows/30 cols UTF-8, mapping/preview, original CsvImportCmd create-only и triggers. | Update существующих по ключу, notes/system/special actions, автоколонки и весь legacy wizard. | P2 |
| CSV Export | PARTIAL | Та же query/scope; selection/all, raw/display, выбор columns/delimiter, защита spreadsheet formulas. | Все formats/Excel и сложные widget-specific exports; limit 10000 rows/32 MiB. | P2 |
| ViewDesigner / определения | PARTIAL | Порядок/параметры колонок, display/edit/action, XML sources, shared/personal save, revisions. | Все визуальные типы колонок/форм, полный auto-refactoring refs/JS callbacks. | P1 |
| Manage Views | PARTIAL | Отдельный каталог DB/file views, create/copy/override delete, open по layout-handler, XML preserving. | Rename c обновлением зависимостей, все custom layout classes, пакетное сравнение и импорт legacy settings. | P2 |
| Manage Side Bar | PARTIAL | Общие/свои разделы, вложенные папки, links/title/separator, order/options/visibility, targeted XML patches. | Полный drag-drop между несколькими sections, все callbacks/definition types, сложные перемещения и shared ownership. | P2 |
| Custom Layout Editor | PARTIAL | Секции HTML/CSS/Mako/kwargs/behavior/callback; create/copy/save/override removal, XML preserving. | Не путать хранение Mako/JS с исполняемым preview; полный визуальный legacy layout builder. | P2 |
| CustomLayoutWdg runtime | PARTIAL | Sanitized static HTML/CSS Shadow DOM; server-defined children / reference/inline, native WidgetHost. | Mako, expr, behavior JS/callbacks, async/manual/sequence/load_once, arbitrary HTML forms и внешние plugins. | P2 |
| Script Editor / Ace | PARTIAL | Original custom_script, local Ace, CRUD/copy/diff, syntax checks, сохранённый Python с отдельным gate и original command. | JS/server_js/expression execution, breakpoints/debugger, полная история, безопасные фоновые jobs/отмена. | P2 |
| Manage Users | PARTIAL | Original UserConfig composition, manage_user table/filter, LoginAction/PasswordAction, группы и detailed memberships. | Полные identity provider/email/invites, массовые destructive operations, проверка всех полей и non-admin access. | P2 |
| Manage Security | PARTIAL | Шесть исходных матриц и callbacks, buffers/revisions, wildcard/access-level; условные/deny ambiguous readonly + XML. | Полный effective-access evaluator по всем группам, non-admin coverage, немедленная ревокация кэшей всех sessions. | P0 |
| Global — 13 штатных ссылок | PARTIAL | Projects/templates/users/groups/membership/translations/logs/settings/license/system info/config/DB resource имеют native routes. | Открытие таблицы не закрывает специальную ячейку. ProjectTemplateUpdate, preview и другие инструменты остаются неполными. | P2 |
| System Config | PARTIAL | 7 исходных групп, active tactic-conf.xml, secret write-only, backup/revision, preserve unrelated XML. | Original bootstrap/create dirs/restart automation, все custom fields; restart вручную. | P2 |
| License Manager | PARTIAL | Original metadata и gated XML v2 renew через проверку лицензии и исходную команду. | Успешная подпись и renew не доказаны изолированными tests; legacy v1/pickle не принимается. | P0 |
| System Info / диагностические журналы | BASE | Исходные сведения, schema health, cluster PID/roles/status; request START/RUNNING/END; raw worker logs отдельно. | Это не full monitoring/SQL profiler и не проверка целостности каждой business record. | P2 |
| Messages / subscriptions / chat | PARTIAL | Original message/message_log/subscription, pagination, exact participants, send/mark/unsubscribe, safe structured event display. | WebSocket/presence/read receipts/attachments/global full-text history; multi-worker durable idempotency. | P2 |
| My Notifications | PARTIAL | Original recipient/project scope notification_log/notification_login, safe table display. | Не SMTP delivery и не новое inbox; editing routing/templates/resend не перенесено. | P2 |
| Triggers / Notifications полный редактор | NO_NATIVE_SCREEN | Есть отдельные исходные generic tables и dependency reads. | Специализированный редактор всех правил/handlers/templates, валидация, subscriptions/actions и их legacy runtime behavior. | P2 |
| Files / Snapshots / current | PARTIAL | Пагинация версий/контекст, protected file delivery/preview, current через original API и revision, thumbnails. | Весь snapshot browser/check-out/load dependency UI, sequence/revision/versionless workflows. | P2 |
| Uploads / CheckinWdg | PARTIAL | Chunked resumable staging, fingerprint/quota/locks, original simple_checkin, uncertain result, обязательные unsupported guards. | Многофайловая snapshot, sequences/revisions, custom validators/options/callbacks, админское reconciliation uncertain. | P2 |
| Review / annotations | NO_NATIVE_SCREEN | Есть обычный protected media preview в FilePanel. | Специализированное review, annotations, sessions, сравнение версий не перенесены простым video/img. | P3 |
| Dashboards / Reports / Charts | NO_NATIVE_SCREEN | Общие таблицы и статический custom layout можно использовать отдельно. | Штатные DashboardsWdg/ReportsWdg и специализированные report/chart screens не имеют equivalent native screen. | P3 |
| Plugins / Ingestion | NO_NATIVE_SCREEN | Legacy runtime и исходники остаются; generic config не доказывает полный manager. | UI installation/uninstall/import/ingestion/validation/progress и callbacks. | P3 |
| Sync Dashboard / tools | NO_NATIVE_SCREEN | Legacy source сохранён. | Специализированные sync policies/import/security/recovery screens и multi-site transport. | P3 |
| Undo/Redo / cascade Delete / rename tools | NO_NATIVE_SCREEN | Retire/reactivate не равно delete; общий DB transaction есть. | Original operation history/Undo UI, cascade impacts, rename migration, exact menus. | P2 |
| Прочие Wdg, DCC/web utilities, examples | UNREVIEWED | Исходники сохранены; полный перечень кандидатов и методов в inventory. | Каждый не сопоставленный класс требует actual call/config analysis; отсутствие registry не доказывает unused. | P3 |

## Где продолжать по каждой области

### foundation-config — Resolver widget_config / definitions

Статус: **BASE**. Приоритет: **P1**.

Текущее: Исходные DB/file/personal/default layers, независимые handler/options, inline/config_code, пустой view, provenance.

Незакрытое: Все runtime DB-overrides/внешние плагины; полное поведение каждого обработчика не следует из metadata parity.

Native: `src/tactic/core/widget_config.py`, `src/tactic/core/config_model.py`, `src/tactic/core/view_resolution.py`
Legacy: `src/pyasm/widget/widget_config.py`, `src/tactic/ui/panel/base_table_layout_wdg.py`

### workspace — Рабочее пространство / основные вкладки

Статус: **BASE**. Приоритет: **P1**.

Текущее: Проекты, конфигурационный sidebar, tabs, root/nested dispatch, DB-состояние, компактный shell, dirty guards.

Незакрытое: Полный legacy URL/custom routing, tear-off и все callbacks; единый dispatcher вместо дублирования App/WidgetHost.

Native: `frontend/src/App.vue`, `frontend/src/components/WidgetHost.vue`, `frontend/src/uiState.js`
Legacy: `src/tactic/ui/app/top_wdg.py`, `src/tactic/ui/panel/panel_wdg.py`

### sidebar-runtime — Sidebar и Schema Views

Статус: **BASE**. Приоритет: **P1**.

Текущее: Original SidebarConfig; folder/link/title/separator, project/admin/my roots, исходный генератор Schema Views.

Незакрытое: Все произвольные callbacks/персональные DB configurations и effective access для non-admin.

Native: `src/tactic/core/sidebar_config.py`, `src/tactic/core/config_model.py`, `frontend/src/components/SidebarNode.vue`
Legacy: `src/tactic/ui/panel/panel_wdg.py`

### table — TableLayout / обычная таблица

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Metadata, серверные страницы/поиск/сортировка, геометрия, range selection, cells, меню, состояние БД.

Незакрытое: Полная server Group By и totals всей выборки, unlimited/chunk-render, все table options, virtual insert-rows, custom layout hooks.

Native: `frontend/src/components/ConfiguredTable.vue`, `frontend/src/components/WidgetTable.vue`, `src/tactic/ui_api/config_backend.py`
Legacy: `src/tactic/ui/panel/table_layout_wdg.py`, `src/tactic/ui/panel/base_table_layout_wdg.py`

### cells — Display-виджеты ячеек

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Plain/format/link/XML, login display-name, task-status color, color, registered thumbnail, несколько global widget buttons.

Незакрытое: Полный ExpressionElement/Task/Snapshot/Thumb/custom cells и handle_td/handle_tr семантика; generic raw display не равен widget parity.

Native: `frontend/src/components/WidgetCell.vue`, `src/tactic/ui_api/column_service.py`, `src/tactic/ui_api/cell_value_service.py`, `src/tactic/ui_api/thumbnail_service.py`
Legacy: `src/tactic/ui/table/expression_element_wdg.py`, `src/pyasm/widget/file_wdg.py`, `src/pyasm/widget/table_element_wdg.py`

### cell-editor — CellEditWdg и edit_item

Статус: **BASE**. Приоритет: **P1**.

Текущее: Отдельный lookup edit + inline + DB edit_item, options, зависимые choices, field/config revisions.

Незакрытое: Не все input/actions/extra hooks, complex WorkHours/Gantt не входят в generic cell editor.

Native: `src/tactic/core/cell_edit_config.py`, `src/tactic/ui_api/table_edit_service.py`, `frontend/src/components/FieldInput.vue`
Legacy: `src/tactic/ui/panel/layout_wdg.py`

### save-buffer — EditMultipleCmd / Save Changes

Статус: **BASE**. Приоритет: **P1**.

Текущее: Буфер существующих строк, 100 rows/1000 cells; один исходный batch, update_multi, rollback и сохранение черновика.

Незакрытое: Inline insert, полный Save All произвольных custom handlers; distributed exactly-once и rollback внешних effects не обеспечены.

Native: `src/tactic/core/edit_commands.py`, `src/tactic/core/native_edit.py`, `src/tactic/ui_api/table_edit_service.py`, `frontend/src/components/ConfiguredTable.vue`
Legacy: `src/tactic/ui/panel/edit_cmd.py`

### fill-clipboard — Fill / Paste / Clipboard

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Заполнение выбранного поля по выбранным строкам с серверным preview, затем staging в общий буфер.

Незакрытое: Excel TSV paste, прямоугольные диапазоны, Fill Down/series, полный legacy clipboard/undo-redo.

Native: `frontend/src/components/ConfiguredTable.vue`, `src/tactic/ui_api/table_edit_service.py`
Legacy: `src/tactic/ui/panel/table_layout_wdg.py`

### forms — EditWdg / popup / embedded forms

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Самостоятельные insert/edit/view, original defaults/validation, bindings, hidden/disables, NULL/0, sibling form values, single, dirty guards.

Незакрытое: parent/connect workflow, layout_view, custom edit_cmd/save callbacks, все оригинальные input/action types.

Native: `frontend/src/components/ConfiguredForm.vue`, `frontend/src/components/EmbeddedForm.vue`, `src/tactic/ui_api/widget_service.py`, `src/tactic/core/native_edit.py`
Legacy: `src/tactic/ui/panel/edit_wdg.py`

### tabs — TabWdg / вложенные контейнеры

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Дочерние native widgets, include/saved/category semantics, preload, hidden, selected, retain mounted state, DB preference keys.

Незакрытое: Динамические счетчики, load modes/callbacks, tear-off; native state не переписывает все legacy XML save_state.

Native: `frontend/src/components/ConfiguredTabs.vue`, `src/tactic/core/widget_containers.py`, `src/tactic/ui_api/widget_service.py`
Legacy: `src/tactic/ui/container/tab_wdg.py`

### menus — Контекстные меню и table shelf

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Row/column/sidebar/tab/field/widget contexts; compact toolbar; File/Edit/View groups; доступность действий и клавиатура.

Незакрытое: Все gear_menu_custom/gear_settings/SmartMenu callbacks, cascade Delete, Print/Chart, old Clipboard, Undo/Redo.

Native: `frontend/src/components/ContextMenu.vue`, `frontend/src/components/TableToolbar.vue`, `src/tactic/core/context_menus.py`, `src/tactic/ui_api/menu_service.py`
Legacy: `src/tactic/ui/panel/base_table_layout_wdg.py`, `src/tactic/ui/container/smart_menu_wdg.py`

### search — Поиск и сохранённые поиски

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Typed AND/OR, исходные supported saved filters/scopes, server sort/paging, named views widget_config, последний query WidgetSettings.

Незакрытое: Весь GeneralFilter/custom filter/expression vocabulary, все legacy serialized last_search; свободный SQL не принимается.

Native: `src/tactic/core/query_model.py`, `src/tactic/core/search_filters.py`, `frontend/src/components/AdvancedFilter.vue`, `src/tactic/ui_api/view_service.py`
Legacy: `src/tactic/ui/app/search_wdg.py`

### prefs — Персональные UI-настройки

Статус: **BASE**. Приоритет: **P1**.

Текущее: Original WidgetSettings/sthpw/wdg_settings, project/login/scope, geometry/query/workspace/tabs/timeline/stype-editor, debounce/revision.

Незакрытое: Полный импорт всех старых XML/last_search и multi-host CAS; unsaved SObjects намеренно не persistence.

Native: `src/tactic/ui_api/ui_state_service.py`, `frontend/src/uiState.js`
Legacy: `src/pyasm/web/widget.py`

### cards — TileLayout / карточки

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Режим карточек той же выборки и отображаемых cells, сохранение буфера при переключении.

Незакрытое: Полная TileLayoutWdg tile actions/geometry/template/collection behaviors; не считать режим cards точной копией всего класса.

Native: `frontend/src/components/ConfiguredTable.vue`, `src/tactic/ui_api/extended_backend.py`
Legacy: `src/tactic/ui/panel/tile_layout_wdg.py`

### relationships — Дерево и отношения

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Lazy relationships исходной Schema, циклы, кандидаты и поддержанные add_instance/remove_instance; link не равен объект.

Незакрытое: Все relation/parent/connection types, deep bulk/drag-drop и нестандартные instance schemas.

Native: `frontend/src/components/RelationTree.vue`, `frontend/src/components/RelationshipEditor.vue`, `src/tactic/ui_api/relationship_service.py`, `src/tactic/ui_api/record_service.py`
Legacy: `src/pyasm/biz/schema.py`

### collections — Collections

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Исходные _is_collection и *_in_*; каталог/вложенность/add/remove/delete, cycles, original commands.

Незакрытое: Все expression/parent-scoped layouts и shelf callbacks, комплексные пакетные операции.

Native: `frontend/src/components/CollectionPanel.vue`, `src/tactic/ui_api/collection_service.py`, `src/tactic/core/collection_commands.py`
Legacy: `src/tactic/ui/panel/collection_wdg.py`

### record-panel — Карточка SObject / notes / history

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: RecordInspector с related/tasks/files/notes/history/subscription; Note.create, исходные журналы, retire/reactivate.

Незакрытое: Все legacy tab/detail widgets, полный note sheet и cascade delete; HTML/custom body не эмулируется.

Native: `frontend/src/components/RecordInspector.vue`, `frontend/src/components/HistoryPanel.vue`, `src/tactic/ui_api/record_service.py`, `src/tactic/ui_api/history_service.py`
Legacy: `src/tactic/ui/panel/edit_wdg.py`

### tasks — Задачи и task board

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original task pipelines/choices, разделение статусов разных pipelines, Task.add_initial_tasks с preview, inline/popup edits.

Незакрытое: Весь TaskElementWdg, все advanced assignment/automation/planning branches, шаблоны досок.

Native: `frontend/src/components/TaskPanel.vue`, `src/tactic/ui_api/task_service.py`, `src/tactic/core/task_choices.py`
Legacy: `src/tactic/ui/table/task_element_wdg.py`

### hours — WorkHoursElement

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Исходный WorkHoursElementAction и привязки; плановый период/единицы/overtime/ноль по конфигурации.

Незакрытое: Комплексные категории, start/end и дубли не агрегируются с перезаписью; полный timesheet UI.

Native: `frontend/src/components/WorkHoursPanel.vue`, `src/tactic/ui_api/work_hour_service.py`, `src/tactic/core/work_hours.py`
Legacy: `src/pyasm/widget/table_element_wdg.py`

### timeline — Gantt и Calendar

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Отдельный server date-window, several bars, page loading, move dates через исходную форму, DB preference.

Незакрытое: Resize, зависимости, resource load, auto-scheduling, holidays/calendars и полный original Gantt.

Native: `frontend/src/components/TaskTimeline.vue`, `src/tactic/ui_api/timeline_service.py`, `src/tactic/core/timeline_model.py`
Legacy: `src/tactic/ui/table/gantt_element_wdg.py`, `src/pyasm/widget/gantt_wdg.py`

### pipeline — Project Workflow / Pipeline editor

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: GraphEditor: CRUD узлов/связей/параметров, owner project, исходные PipelineSaveCbk/ProcessInfoCmd; reopen.

Незакрытое: Все advanced process panels, nested pipelines, conditions/manual/approval/dependency semantics, rename с историей и все callbacks.

Native: `frontend/src/components/GraphEditor.vue`, `src/tactic/ui_api/graph_service.py`, `src/tactic/core/pipeline_commands.py`, `src/tactic/core/process_commands.py`
Legacy: `src/tactic/ui/tools/pipeline_wdg.py`, `src/tactic/ui/tools/pipeline_canvas_wdg.py`

### schema — Project Schema editor

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original Schema.get, read XML, graph existing types/relations, save project schema; встроенные schema readonly.

Незакрытое: DDL whole schema designer, миграции связанных физических полей/отношений, полный drag-drop palette.

Native: `frontend/src/components/GraphEditor.vue`, `src/tactic/ui_api/graph_service.py`, `src/tactic/core/graph_model.py`
Legacy: `src/tactic/ui/tools/schema_wdg.py`

### projects — ProjectCreateWdg / мастер

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: default/simple preflight/create/original CreateProjectCmd/new SQLite setup; переход и новый sidebar без restart.

Незакрытое: Любые template-project imports, theme/preview в мастере, безопасное восстановление частичного create и durable result.

Native: `frontend/src/components/ProjectWizard.vue`, `src/tactic/ui_api/project_service.py`, `src/tactic/core/project_creation.py`
Legacy: `src/tactic/ui/app/page_header_wdg.py`

### stypes — Manage sTypes

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Каталог, metadata, original column info/definitions; create type/add columns; переходы к table/form/views/workflow/schema; DB state.

Незакрытое: DROP/RENAME/ALTER TYPE, полный triggers/notifications editor, все multi-db branches; dependencies не доказательство безопасного удаления.

Native: `frontend/src/components/SearchTypes.vue`, `src/tactic/ui_api/search_type_service.py`, `src/tactic/ui_api/admin_workspace.py`, `src/tactic/core/admin_commands_017.py`
Legacy: `src/tactic/ui/app/search_type_creator_wdg.py`, `src/tactic/ui/startup/column_edit_wdg.py`

### csv-import — CSV Import

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: До 1 MiB/100 rows/30 cols UTF-8, mapping/preview, original CsvImportCmd create-only и triggers.

Незакрытое: Update существующих по ключу, notes/system/special actions, автоколонки и весь legacy wizard.

Native: `frontend/src/components/CsvImportPanel.vue`, `src/tactic/ui_api/search_type_service.py`
Legacy: `src/pyasm/command/csv_import_cmd.py`

### csv-export — CSV Export

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Та же query/scope; selection/all, raw/display, выбор columns/delimiter, защита spreadsheet formulas.

Незакрытое: Все formats/Excel и сложные widget-specific exports; limit 10000 rows/32 MiB.

Native: `frontend/src/components/CsvExport.vue`, `src/tactic/ui_api/csv_service.py`
Legacy: `src/tactic/ui/widget/data_export_wdg.py`

### view-designer — ViewDesigner / определения

Статус: **PARTIAL**. Приоритет: **P1**.

Текущее: Порядок/параметры колонок, display/edit/action, XML sources, shared/personal save, revisions.

Незакрытое: Все визуальные типы колонок/форм, полный auto-refactoring refs/JS callbacks.

Native: `frontend/src/components/ViewDesigner.vue`, `frontend/src/components/ConfigEditor.vue`, `src/tactic/ui_api/view_service.py`, `src/tactic/core/view_edits.py`
Legacy: `src/tactic/ui/panel/view_manager_wdg.py`

### manage-views — Manage Views

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Отдельный каталог DB/file views, create/copy/override delete, open по layout-handler, XML preserving.

Незакрытое: Rename c обновлением зависимостей, все custom layout classes, пакетное сравнение и импорт legacy settings.

Native: `frontend/src/components/ManageViews.vue`, `src/tactic/ui_api/design_service.py`
Legacy: `src/tactic/ui/manager/view_manager_wdg.py`, `src/tactic/ui/panel/view_manager_wdg.py`

### sidebar-editor — Manage Side Bar

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Общие/свои разделы, вложенные папки, links/title/separator, order/options/visibility, targeted XML patches.

Незакрытое: Полный drag-drop между несколькими sections, все callbacks/definition types, сложные перемещения и shared ownership.

Native: `frontend/src/components/SidebarEditor.vue`, `src/tactic/ui_api/sidebar_service.py`, `src/tactic/core/sidebar_edits.py`
Legacy: `src/tactic/ui/panel/manage_view_panel_wdg.py`

### custom-layout-editor — Custom Layout Editor

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Секции HTML/CSS/Mako/kwargs/behavior/callback; create/copy/save/override removal, XML preserving.

Незакрытое: Не путать хранение Mako/JS с исполняемым preview; полный визуальный legacy layout builder.

Native: `frontend/src/components/CustomLayoutEditor.vue`, `src/tactic/ui_api/design_service.py`, `src/tactic/core/design_document.py`
Legacy: `src/tactic/ui/tools/custom_layout_edit_wdg.py`

### custom-layout-runtime — CustomLayoutWdg runtime

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Sanitized static HTML/CSS Shadow DOM; server-defined children / reference/inline, native WidgetHost.

Незакрытое: Mako, expr, behavior JS/callbacks, async/manual/sequence/load_once, arbitrary HTML forms и внешние plugins.

Native: `frontend/src/components/LayoutPreview.vue`, `src/tactic/ui_api/design_service.py`
Legacy: `src/tactic/ui/panel/custom_layout_wdg.py`

### script-editor — Script Editor / Ace

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original custom_script, local Ace, CRUD/copy/diff, syntax checks, сохранённый Python с отдельным gate и original command.

Незакрытое: JS/server_js/expression execution, breakpoints/debugger, полная история, безопасные фоновые jobs/отмена.

Native: `frontend/src/components/ScriptEditor.vue`, `frontend/src/components/CodeEditor.vue`, `src/tactic/ui_api/script_service.py`
Legacy: `src/tactic/ui/app/shelf_wdg.py`

### users — Manage Users

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original UserConfig composition, manage_user table/filter, LoginAction/PasswordAction, группы и detailed memberships.

Незакрытое: Полные identity provider/email/invites, массовые destructive operations, проверка всех полей и non-admin access.

Native: `frontend/src/components/UserManager.vue`, `frontend/src/components/UserGroups.vue`, `src/tactic/ui_api/admin_workspace.py`, `src/tactic/ui_api/security_service.py`
Legacy: `src/tactic/ui/startup/project_config_wdg.py`

### security — Manage Security

Статус: **PARTIAL**. Приоритет: **P0**.

Текущее: Шесть исходных матриц и callbacks, buffers/revisions, wildcard/access-level; условные/deny ambiguous readonly + XML.

Незакрытое: Полный effective-access evaluator по всем группам, non-admin coverage, немедленная ревокация кэшей всех sessions.

Native: `frontend/src/components/SecurityMatrix.vue`, `src/tactic/ui_api/security_service.py`, `src/tactic/core/admin_commands_017.py`
Legacy: `src/tactic/ui/startup/security_wdg.py`

### globals — Global — 13 штатных ссылок

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Projects/templates/users/groups/membership/translations/logs/settings/license/system info/config/DB resource имеют native routes.

Незакрытое: Открытие таблицы не закрывает специальную ячейку. ProjectTemplateUpdate, preview и другие инструменты остаются неполными.

Native: `frontend/src/components/GlobalSettings.vue`, `src/tactic/ui_api/global_admin_service.py`, `frontend/src/components/GroupMembership.vue`
Legacy: `src/tactic/ui/config/DEFAULT-conf.xml`

### system-config — System Config

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: 7 исходных групп, active tactic-conf.xml, secret write-only, backup/revision, preserve unrelated XML.

Незакрытое: Original bootstrap/create dirs/restart automation, все custom fields; restart вручную.

Native: `frontend/src/components/GlobalSettings.vue`, `src/tactic/core/system_config_model.py`, `src/tactic/ui_api/global_admin_service.py`
Legacy: `src/tactic/ui/startup/db_config_wdg.py`

### license — License Manager

Статус: **PARTIAL**. Приоритет: **P0**.

Текущее: Original metadata и gated XML v2 renew через проверку лицензии и исходную команду.

Незакрытое: Успешная подпись и renew не доказаны изолированными tests; legacy v1/pickle не принимается.

Native: `frontend/src/components/GlobalSettings.vue`, `src/tactic/core/license_commands.py`, `src/tactic/ui_api/global_admin_service.py`
Legacy: `src/tactic/ui/app/license_manager_wdg.py`

### system-info — System Info / диагностические журналы

Статус: **BASE**. Приоритет: **P2**.

Текущее: Исходные сведения, schema health, cluster PID/roles/status; request START/RUNNING/END; raw worker logs отдельно.

Незакрытое: Это не full monitoring/SQL profiler и не проверка целостности каждой business record.

Native: `frontend/src/components/AdminPanel.vue`, `src/tactic/ui_api/system_diagnostics.py`, `src/tactic/ui_api/action_log.py`
Legacy: `src/tactic/ui/app/system_info_wdg.py`

### messages — Messages / subscriptions / chat

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original message/message_log/subscription, pagination, exact participants, send/mark/unsubscribe, safe structured event display.

Незакрытое: WebSocket/presence/read receipts/attachments/global full-text history; multi-worker durable idempotency.

Native: `frontend/src/components/MessageCenter.vue`, `frontend/src/components/SubscriptionPanel.vue`, `src/tactic/ui_api/message_service.py`, `src/tactic/core/message_commands.py`
Legacy: `src/tactic/ui/app/message_wdg.py`

### mail-log — My Notifications

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Original recipient/project scope notification_log/notification_login, safe table display.

Незакрытое: Не SMTP delivery и не новое inbox; editing routing/templates/resend не перенесено.

Native: `src/tactic/ui_api/extended_backend.py`, `src/tactic/core/notification_filters.py`
Legacy: `src/pyasm/prod/site/my_tactic_tab_wdg.py`

### notifications-rules — Triggers / Notifications полный редактор

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P2**.

Текущее: Есть отдельные исходные generic tables и dependency reads.

Незакрытое: Специализированный редактор всех правил/handlers/templates, валидация, subscriptions/actions и их legacy runtime behavior.

Native: `src/tactic/ui_api/search_type_service.py`
Legacy: `src/tactic/ui/app/notify_wdg.py`

### files — Files / Snapshots / current

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Пагинация версий/контекст, protected file delivery/preview, current через original API и revision, thumbnails.

Незакрытое: Весь snapshot browser/check-out/load dependency UI, sequence/revision/versionless workflows.

Native: `frontend/src/components/FilePanel.vue`, `src/tactic/ui_api/version_service.py`, `src/tactic/ui_api/record_service.py`
Legacy: `src/tactic/ui/checkin/snapshot_files_wdg.py`, `src/tactic/ui/table/snapshot_element_wdg.py`

### checkin — Uploads / CheckinWdg

Статус: **PARTIAL**. Приоритет: **P2**.

Текущее: Chunked resumable staging, fingerprint/quota/locks, original simple_checkin, uncertain result, обязательные unsupported guards.

Незакрытое: Многофайловая snapshot, sequences/revisions, custom validators/options/callbacks, админское reconciliation uncertain.

Native: `frontend/src/components/UploadQueue.vue`, `src/tactic/ui_api/upload_store.py`, `src/tactic/ui_api/upload_service.py`, `src/tactic/core/checkin_policy.py`
Legacy: `src/tactic/ui/widget/checkin_wdg.py`

### review — Review / annotations

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P3**.

Текущее: Есть обычный protected media preview в FilePanel.

Незакрытое: Специализированное review, annotations, sessions, сравнение версий не перенесены простым video/img.

Native: `frontend/src/components/FilePanel.vue`
Legacy: `src/tactic/ui/tools/review_wdg.py`, `src/tactic/ui/widget/review_wdg.py`

### dashboards-reports — Dashboards / Reports / Charts

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P3**.

Текущее: Общие таблицы и статический custom layout можно использовать отдельно.

Незакрытое: Штатные DashboardsWdg/ReportsWdg и специализированные report/chart screens не имеют equivalent native screen.

Native: отдельная реализация не найдена в пределах этой карты.
Legacy: `src/tactic/ui/startup/dashboards_wdg.py`, `src/tactic/ui/startup/reports_wdg.py`, `src/tactic/ui/chart/chart_builder_wdg.py`

### plugins-ingest — Plugins / Ingestion

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P3**.

Текущее: Legacy runtime и исходники остаются; generic config не доказывает полный manager.

Незакрытое: UI installation/uninstall/import/ingestion/validation/progress и callbacks.

Native: отдельная реализация не найдена в пределах этой карты.
Legacy: `src/tactic/ui/app/plugin_wdg.py`, `src/tactic/ui/tools/ingest_wdg.py`, `src/tactic/ui/tools/ingestion_wdg.py`

### sync — Sync Dashboard / tools

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P3**.

Текущее: Legacy source сохранён.

Незакрытое: Специализированные sync policies/import/security/recovery screens и multi-site transport.

Native: отдельная реализация не найдена в пределах этой карты.
Legacy: `src/tactic/ui/sync/sync_settings_wdg.py`, `src/tactic/ui/sync/sync_import_wdg.py`

### undo-delete — Undo/Redo / cascade Delete / rename tools

Статус: **NO_NATIVE_SCREEN**. Приоритет: **P2**.

Текущее: Retire/reactivate не равно delete; общий DB transaction есть.

Незакрытое: Original operation history/Undo UI, cascade impacts, rename migration, exact menus.

Native: отдельная реализация не найдена в пределах этой карты.
Legacy: `src/tactic/ui/app/undo_log_wdg.py`

### other — Прочие Wdg, DCC/web utilities, examples

Статус: **UNREVIEWED**. Приоритет: **P3**.

Текущее: Исходники сохранены; полный перечень кандидатов и методов в inventory.

Незакрытое: Каждый не сопоставленный класс требует actual call/config analysis; отсутствие registry не доказывает unused.

Native: отдельная реализация не найдена в пределах этой карты.
Legacy: искать по полному индексу классов и фактической конфигурации.

## Полнота списка

Эта матрица покрывает функциональные семейства, а `inventory/ALL_UI_FILES.md` перечисляет **каждый файл-кандидат текущего сканера**. `legacy_ui_inventory.json` добавляет классы, методы, ссылки и native-кандидатов. Такой двухуровневый список не делает вид, что все 1351 файла вручную проверены.

В индекс входят 435 Python, 831 JavaScript, 44 CSS, 28 HTML и 13 XML файлов. Значительная доля JS — поставляемые Ace/CKEditor и другие библиотеки. Их нельзя считать отдельными неперенесёнными прикладными экранами. Автоматический поиск не включает пользовательские DB widget_config, код внешних плагинов и динамические class paths.

Stock sidebar на файлах — `inventory/STOCK_SIDEBAR.md`. Перечень явных 501-ограничений — `inventory/explicit_unsupported_guards.json`; ограничения через read_only/diagnostics в этот перечень автоматически не входят.

Все строки имеют `full_legacy_parity_verified=false`: это честная граница handoff, а не утверждение, что ничего не работает. Полную готовность можно ставить отдельному проверенному сценарию, а не всему классу по наличию компонента.
