# План продолжения — предложения после 0.20

Этот документ — **план**, не перечень уже реализованных функций. Основание: выпущенные исходники 0.20, текущая матрица UI и ограничения проверки. Приоритеты не означают календарных сроков; сначала нужно измерить работу на настоящей целевой установке.

## 1. Порядок, который не разрушает уже работающий перенос

```text
Зафиксировать baseline и реальную среду
              ↓
Проверить ядро пользовательских сценариев / роли
              ↓
Закрыть Table + CellEdit + Edit + Tab и типовые display-ячейки
              ↓
Завершать административные инструменты по их исходным контрактам
              ↓
Workflow / runtime Custom Layout / расширенные файлы
              ↓
Review / dashboards / plugins и остаток по usage inventory
              ↓
Структурная модернизация build/API и окончательное удаление legacy UI
```

Не начинать с переписывания ORM, database layout, XML-формата и всего frontend tooling одновременно. Рабочий screenshot, alias в registry или количество прошедших unit-тестов не являются feature parity.

## 2. P0 — проверяемая отправная точка

### P0-01. Git baseline, конфигурации и эталонные сценарии

**Вход:** полный архив 0.20 с SHA-256 из `SNAPSHOT_FACTS.json`, исходный upstream при наличии и отдельная тестовая копия пользовательской установки.

**Сделать:** создать отдельную ветку и первый commit неизменённой 0.20; перенести этот handoff в `docs/handoff-0.20`; зафиксировать хеш исходного архива. Не коммитить `.runtime`, `local_data`, активные `tactic-conf.xml`, `native-ui.json`, profiles, sessions, private backups, worker logs или реальные пользовательские данные.

Экспортировать в обезличенные fixtures выбранные `widget_config`, определения SearchType, Schema, Pipeline и access rules, необходимые для сценариев. Удалять секреты, а не просто менять расширение файла. Версию конфигураций связать с каждым результатом теста.

**Готово, когда:** можно восстановить исходники и тестовую базу, повторить одинаковые действия в native и legacy, видеть различия в данных/командах/UI. Приложение продолжает работать с прежними данными без повторного INIT.

### P0-02. Настоящие Windows и browser boundary

**Файлы:** `tools/local/tactic_bootstrap.ps1`, `control.py`, `launch.py`, `cluster.py`, `cluster_worker.py`, `src/tactic/ui_api/mount.py`, `routing.py`, `api.py`.

**Проверить на Windows:** три BAT, PowerShell 5.1, embedded Python, пробелы/кириллица/`& ! %` в путях, приоритет явного Python, код ошибки дочернего процесса, Ctrl+C и остановка всех workers, shared/exclusive locks, offline upgrade при активном кластере должен отказать.

**Проверить в обычном браузере без `--bridge`:** вход/выход, session cookies, CSRF/Origin, reload прямой ссылки, открытие нового проекта, Ace resources, WebCrypto, resumable upload, protected image/media, восстановление DB-state, отсутствие ошибок CSP. HTTP-мост не закрывает эти задачи.

**Готово, когда:** сохранён отдельный отчёт реального браузера и Windows, без фиктивных claims на основании Linux controller tests. Успешное открытие главной страницы недостаточно.

### P0-03. PostgreSQL и лицензионная граница

Проверить исходную БД PostgreSQL на копии: создание проекта/SearchType, обычный Edit и EditMultiple, rollback второй строки, отношения, snapshots, pipeline/process context, state и три workers. SQLite-specific repair не должен запускаться на PostgreSQL.

Исполнить реальный вход и штатное получение лицензии без тестовой изоляции подписи. Проверка Renew License требует подходящего настоящего подписанного тестового файла и отдельного сценария; отсутствие такого файла — незавершённая проверка, а не повод выключить `verify=True`.

**Готово, когда:** конкретные СУБД/версии/сценарии обозначены в отчёте. Не объявлять MySQL поддержанным только потому, что не изменена его исходная ветка.

### P0-04. Матрица обычных ролей

**Файлы:** `src/tactic/ui_api/tactic_backend.py:TacticBackend.context/login`, `field_policy.py`, `config_backend.py`, `security_service.py`, `native_edit.py` и все service endpoints.

Сначала создать сценарии admin / project-admin / artist / read-only / отсутствует доступ к проекту. Проверять direct HTTP, не только скрытые кнопки: sidebar, open, query, value providers, cell editor, create/update, bulk, files, scripts, shared/personal views, graph, settings, exports.

Нельзя просто удалить `is_admin` из двух мест. Нужны исходные project/type/row/field/process права, повторная авторизация write, недоступные значения не должны попадать в response. Отдельно проверить отозванную группу/правило в уже существующей сессии и на каждом worker.

**Готово, когда:** появление non-admin режима имеет собственный acceptance suite. До этого оставить admin-only и не рекомендовать публичное развёртывание.

## 3. P1 — фундамент Table / Edit / Tab, а не очередной внешний экран

### P1-01. Контракт каждой используемой ячейки

**Файлы:** `core/config_model.py`, `view_resolution.py`, `cell_edit_config.py`, `ui_api/column_service.py`, `cell_value_service.py`, `thumbnail_service.py`, `frontend/src/components/WidgetCell.vue`, `FieldInput.vue`.

Для каждого реально встречающегося display-handler подготовить запись: исходный класс/методы, config branches, `preprocess`, данные строки, empty/null поведение, цвет/формат/link, действие на click/doubleclick/rightclick, edit/action handler, права, batch lookup и ошибки.

Начать с Simple/Format, Login, Status/Task, Thumb/Snapshot, HiddenRow/Link/buttons, затем ExpressionElement. Не отождествлять физическую колонку и имя элемента; сохранить aliases и виртуальные поля. Вывод raw-значения с warning — не перенос display-виджета.

**Приёмка:** один и тот же fixture XML и SObject дают сопоставимый смысл отображения, тот же исходный тип для сохранения, те же области доступа. Проверять root/nested/card, 0/false/NULL/пустую строку, emoji/кириллицу, большие числа, отсутствие preview, архивные/удалённые связанные записи.

### P1-02. Полное сохранение обычной таблицы

**Файлы:** `ConfiguredTable.vue`, `table_edit_service.py`, `core/native_edit.py`, `core/edit_commands.py`; legacy `layout_wdg.py:CellEditWdg`, `edit_wdg.py`, `edit_cmd.py` compatibility exports.

Расширять исходный buffer, не переходить обратно к immediate PATCH. Отдельно спроектировать новые временные строки (inline insert), назначение defaults, parent/connect, серверные keys после сохранения и взаимодействие с update_multi.

Сначала закрыть `edit_item` и зависимые editors, потом прямоугольный TSV paste/Fill Down, validation preview и общую запись. Не считать CSV importer эквивалентом формы: он имеет другое преобразование строк и набор actions.

**Приёмка:** одна команда на пакет; неизвестный custom action не пропущен; ошибка в последней строке не оставляет первые изменения в БД; черновики остаются; pre/post actions и итоговое событие соответствуют legacy. Сбой HTTP не вызывает повторного INSERT.

### P1-03. Полная query/table-семантика

**Файлы:** `config_backend.py`, `query_model.py`, `core/search_filters.py`, `column_service.py`, `timeline_service.py`, legacy `BaseTableLayoutWdg/TableLayoutWdg/SearchWdg`.

Server Group By, агрегаты всей выборки против агрегатов страницы, несколько сортировок, исходный search limit/chunk rendering, filtered nested tables, collection scope, persistent search flags. Для выражений сортировки и фильтров сначала перенести конкретные разрешённые ветки, а не принимать SQL от браузера.

**Приёмка:** страницы не меняют смысл totals/group counts; обязательный фильтр view не снимается пользовательским reset; table/cards/tree/export/timeline используют ту же предметную область. Запросы измерены на большом, но воспроизводимом dataset без N+1 на каждую ячейку.

### P1-04. Containers и действия

**Файлы:** `App.vue`, `WidgetHost.vue`, `ConfiguredTabs.vue`, `EmbeddedForm.vue`, `core/widget_containers.py`, `widget_service.py`, `menu_service.py`, `ui_state_service.py`.

Закрыть parent/connect/layout_view у embedded Edit, разрешённые load/callback варианты Tab, shared state. После тестов объединить дублируемую root/nested диспетчеризацию в один host/registry. До refactor проверять обе точки явно.

Контекстное меню должно определяться виджетом и контекстом. Cascade DeleteWdg не заменять retire; сначала preview зависимостей и точный original command. Не добавлять 20 постоянных кнопок в table shelf.

**Приёмка:** root, вложенный Tab, Custom Layout, HiddenRow и восстановленная DB-вкладка открывают один renderer с тем же target. Dirty state живёт при переключении, ошибка refresh не уничтожает форму, child с `display=false` не раскрывается прямым HTTP.

## 4. P2 — админские возможности и предметные сценарии

### P2-01. Manage sTypes / schema DDL

**Файлы:** `search_type_service.py`, `design_service.py`, `SearchTypes.vue`, `CsvImportPanel.vue`, `core/admin_commands_017.py`, исходные SearchTypeTool/ColumnEdit/ColumnAdd/ColumnDrop/Schema commands (найти точный путь в inventory).

Составить перечень всех legacy пунктов редактора, а не только column CRUD. Полный Triggers/Notifications editor отделить от generic таблиц этих записей. Для DROP/RENAME/TYPE: dry-run, backup, явное имя для подтверждения, зависимости DB/Schema/views/scripts, сохранность данных и отказ при неоднозначной миграции. Проверка текстовых ссылок не доказывает отсутствие внешних зависимостей.

Не обещать автоматический rewrite произвольного Python/JS/expressions. При невозможности доказать корректность возвращать конкретные зависимости для ручной миграции. Каждую поддержанную СУБД тестировать отдельно.

### P2-02. Workflow и задачи

**Файлы:** `graph_service.py`, `graph_model.py`, `pipeline_commands.py`, `process_commands.py`, `task_service.py`, `GraphEditor.vue`, `TaskPanel.vue`; legacy `pipeline_wdg.py`, `pipeline_canvas_wdg.py`, `pyasm/command/workflow.py`.

Каждый тип процесса и его property panel переносить с исходными trigger/state effects. Добавить вложенные pipelines, условия/approval/manual/dependencies именно там, где исходники их определяют. Чтение и запись `config/process` всегда в проекте-владельце; граф из admin и граф из проекта — обязательная пара сценариев.

**Приёмка:** изменение координат не меняет semantics; rename использованного процесса не ломает задачи/историю; unknown XML round-trip сохраняется; переключение task status приводит к тем же workflow событиям. Canvas на Vue сам по себе не означает готовый workflow editor.

### P2-03. Custom Layout и Manage Views

**Файлы:** `design_service.py`, `design_document.py`, `CustomLayoutEditor.vue`, `LayoutPreview.vue`, `ManageViews.vue`, `WidgetHost.vue`; legacy CustomLayoutWdg/CustomLayoutEditWdg.

Сначала точные режимы вложенных widgets (manual/async/sequence/load_once), выбор источника/include и kwargs. Динамический Mako/expr и JavaScript behaviors — отдельное решение о доверии и контрактах. Сохранённый произвольный код администратора нельзя исполнять через новый публичный universal eval endpoint.

Выбор: контролируемые server-side providers и декларативные actions либо отдельно изолированная compatibility-среда с явными ограничениями. Такое решение документировать как новое, не как уже существующее в 0.20. Не размазывать `v-html`/`eval` по общему интерфейсу.

Manage Views rename должен учитывать ссылки, owners, definition и users. Пока нет полного рефакторинга ссылок, оставить явную copy/delete semantics.

### P2-04. Файлы, импорт и сообщения

**Файлы:** `upload_service.py`, `upload_store.py`, `src/tactic/core/checkin_policy.py`, `version_service.py`, `FilePanel.vue`, `UploadQueue.vue`, исходные Snapshot/Checkin commands.

Многофайловая snapshot, sequences/revisions, options panels и custom validators; не пропускать их, вызывая simple_checkin. Добавить административное разрешение `uncertain` с сопоставлением результата по фактическим snapshot/files, без слепого повторения. Проверять disk quota, restart, отмену staging и retention.

CSV: расширять original importer, явно различать create/update и form actions. Сообщения: receipts, presence и polling/WebSocket обсуждать после transport/security, не выдавать `last_cleared` за прочтение собеседником.

## 5. P3 — специализированный остаток и очистка архитектуры

**Review/аннотации, Dashboards/Reports/Charts, Plugins/Ingestion, Sync tools**: сначала пройти actual entry paths из DEFAULT и пользовательских конфигов; открыть legacy, записать сценарии, затем нативный renderer и исходные команды. `FilePanel` с video не заменяет review; таблица plugin records не заменяет plugin manager.

Далее разобрать остальные классы из inventory. Сначала используемые на данной установке, затем штатные core-screen families, затем production/DCC-specific и examples. Vendor JS не нужно «переписывать по файлу» ради счётчика.

### Отдельная модернизация после baseline tests

- Единый список route → HTTP methods → access → service → read/write → revision policy; не независимые таблицы маршрутов API/gateway/frontend.
- Явный request context вместо скрытого mutable backend state; небольшие композиционные services вместо бесконтрольного роста MRO. Менять постепенно, один контракт за PR.
- Единый native renderer registry root/nested/restore.
- Нормальный SFC build (возможный Vite) + постепенные типизированные контракты, без обязательного Node runtime на пользовательском сервере. Сначала повторить production output/resources/CSP и обновить tests.
- Повторная проверка текущих библиотек и lockfile как самостоятельная задача сопровождения; данный handoff не является аудитом их актуальных уязвимостей.
- Headless bootstrap: переносить оставшиеся бизнес-команды и строковые class paths из legacy, затем import guards и API/DCC-regression. Удаление старых UI directories допустимо только после закрытия реальных зависимостей.

## 6. Definition of Done для одного legacy-виджета

Один пункт считается закрытым **для конкретно указанной области**, только когда:

1. Найдены исходный класс, его вызовы и способы определения через XML/DB, включая короткие exports.
2. Составлена таблица options/kwargs и их наследования: поддержано / намеренно отличается / не поддержано.
3. Проверены данные, отображение, пользовательские действия, команды/триггеры, права, state и ошибки; single screenshot недостаточен.
4. Есть source-grounded fixtures и дифференциальные тесты legacy/native. Одинаковый результат проверки resolver не заменяет тест действий.
5. Root, nested, restored, read-only и unauthorized direct request проходят релевантные проверки.
6. Неизвестные данные/атрибуты сохраняются; нет нового hardcoded schema или незаметного raw fallback.
7. Actual тесты, конфигурация, commit и платформа указаны; Windows/DB/browser, которые не запускались, не объявлены проверенными.
8. Изменены текущие readiness matrix и код, а не только README. Незакрытые options сохраняются в backlog.

## 7. Что дать первым заданием

Первое задание для новой сессии — **не очередной большой переписанный модуль**, а P0-01/P0-02 и фиксация отличий трёх реальных сложных таблиц. После этого один узкий P1 контракт довести полностью. Готовый текст находится в `05_FIRST_TASK_FOR_CODEX.md`.


### Backend: шаг 0.90 — parent_key / коллекции

Перенесены исходные SObject collection methods, общий recursive CTE, CRUD parent_key
и insert(collection_key), creator _is_collection флаг. Исправлены keyword-триггеры
вложенных коллекций/rename/удаления нескольких путей. Проверки и ограничения —
в tactic_stream/README.md, раздел 0.90; полная API parity не объявляется.
Следующий связанный блок: исходные CollectionAddCmd/RemoveCmd/DeleteCmd и полный
жизненный цикл удаления коллекции; затем остающиеся schema creator команды.


### Backend: шаг 0.91 — команды коллекций

Перенесены CollectionAddCmd/RemoveCmd/DeleteCmd с исходными import paths и execute_cmd.
Удаление очищает связи членства и сохраняет участников; keyword/journal rollback
проверен. Массовое добавление проверяется до записи, исправлен source partial success.
Проверены реальный легаси, исходный XML-RPC SDK, SQLite/PostgreSQL и параллельное
добавление через временный SQLite HTTP-сервер. Подробности/границы — README 0.91.
Следующий блок: оставшиеся schema creator/edit_connection команды и их зависимости;
HTML collections/renderer actions относятся к будущему UI, не к готовому backend.


### Backend: шаг 0.92 — команды схемы

Перенесены SchemaSaveCmd/SchemaConnectorCbk, edit_connection и creator sobject_parent.
Сохранены отдельные этапы регистрации, XML графа, колонок и декларативных widget configs.
Исправлены source missing import, stale/negative schema cache, duplicate view и текстовый id.
Проверки/границы — tactic_stream/README.md 0.92. Исходные HTML/canvas не возвращались.
Следующий связанный блок: template copy в SearchTypeCreatorCmd и его backend зависимости;
автоматические view/sidebar defaults согласовывать с общим динамическим renderer.

### Backend: шаг 0.93 — шаблоны таблиц и pipeline

SearchTypeCreatorCmd поддерживает copy_from_template и создание pipeline/process
через прежний execute_cmd. SQLite/PostgreSQL копируют структуру с независимым id,
constraints/defaults/indexes и транзакционным откатом. Исправлены TableUndo.log,
потеря определений и XML escaping; версии pipeline сохраняют собственные скрипты.
Реальный исходник, неизменённый XML-RPC SDK и временный PostgreSQL проверены;
границы и команды — tactic_stream/README.md 0.93. Следующий блок — декларативные
creator views/sidebar и их использование динамическим Vue; preview отдельно.

### Backend/UI: шаг 0.94 — creator configs и динамические представления

Перенесены create_config/add_sidebar_views и исправлен общий WidgetDbConfig.append.
Новый admin-only JSON descriptor использует исходные конфиги/priority merge;
XML-RPC не менялся. Vue открывает плоские проектные ссылки, читает порядок и
заголовки колонок, обновляется после правок XML без сборки. Пустой view сохранён,
неподдержанные widgets/layouts явно недоступны; браузер полей с прежними правами
сохраняется. Исходник/SDK/SQLite/PostgreSQL и Chromium проверены; границы — README 0.94.
Следующий блок — исходные EditWdg метаданные, команды полей/форм и их Vue UI;
config editor, вложенный sidebar, preview, arbitrary widgets/actions остаются в плане.

### 2026-10-07 — 0.95: исходные серверные формы и команды

Перенесены EditWdg init/get_config/do_search, базовые inputs/Select options и
EditCmd/EditMultipleCmd с DatabaseAction/DefaultValue/Multi/NonEmpty/Regex/Null/
UniqueValue/XmlAction. execute_cmd принимает исходные form values, сохраняет
request-local scope и использует общий транзакционный путь. Восстановлены
SearchType.get_tactic_type(s), database impl accessor и Common.get_next_code.
Добавлен admin-only /admin/form; XML-RPC/HTML сигнатуры не заменены descriptor.
Проверены исходник, неизменённые SDK и query_EditWdg Handler, SQLite/PostgreSQL,
insert/edit/bulk, rollback, defaults и адресные исправления. Границы — README 0.95.
Следующий блок — подключить эти серверные формы к Vue и расширять исходные
input/action зависимости; календарь/upload/task/pipeline и полная GUI parity
ещё не готовы. Renderer/config editor/preview остаются в плане.

### 2026-10-07 — 0.96: Vue создание и редактирование объектов

RecordForm использует /admin/form и исходный execute_cmd/EditCmd: базовые
Text/TextArea/Checkbox/Select, серверные defaults/choices, raw sibling values,
readonly, сообщения действий и сохранение черновика при ошибке. XML формы
перечитывается при открытии; неизвестные inputs/options блокируются явно.
Dirty close подтверждается; запись не повторяется при потерянном ответе.
Исправлены числовой zero в DatabaseAction и XML options конструктора Checkbox.
Built Chromium/SQLite и адресные проверки описаны в README 0.96; рабочие БД и
Handler не менялись. PostgreSQL проверки 0.95 не повторялись ради frontend.
Следующий блок — исходные date/calendar inputs, затем специализированные
upload/task/process/pipeline зависимости. Config editor, nested layouts,
revision/preview/AI authoring остаются незавершёнными.

### 2026-10-07 — 0.97: календарные поля и timezone

Перенесён современный CalendarInputWdg metadata/get_value, исходный timezone
helper и SPTDate зависимости. Vue date/datetime-local работает через прежние
EditWdg/EditCmd/DatabaseAction, сохраняет raw timestamps без сдвига и потери
микросекунд при изменении соседей. Исправлены source day/locale/invalid-date
дефекты, потеря точности commit и JSON command response с datetime.
Исходный runtime/SDK/Handler procedure, Chromium и отдельные SQLite/PostgreSQL
базы проверены; команды и точные ограничения — tactic_stream/README.md 0.97.
Рабочие базы и Handler не менялись. Старый pyasm календарь/inline/JS/Time/Interval
не перенесены. Следующий блок — upload/task/process/pipeline inputs/actions;
config editor, nested layouts, preview/revisions и AI authoring остаются в плане.

### 2026-10-07 — 0.98: workflow inputs и context actions

Перенесены восемь исходных workflow inputs: pipeline/process/review/subcontext,
два SearchType selects, назначение по группе и status с проверкой view access.
SubContextAction скопирован целиком. Vue получает серверные choices, сохраняет
через прежний EditCmd; ошибка postprocess откатывает запись. Исправлен source
wrong-name process filter; дефект подтверждён настоящим runtime.
12 адресных проверок, исходный SDK/Handler task-процедура, Chromium и отдельный
SQLite/PostgreSQL сценарий прошли. Scope/команды — tactic_stream/README.md 0.98.
Handler/рабочие данные не менялись. HTML-зависимые special cases Handler,
inline switching и разрешение choices по draft ещё не готовы. Следующий блок —
upload/parent/task inputs/actions; config editor, nested layouts, revisions/
preview и AI authoring остаются в плане.


## 0.99 — task parent, single-file upload и form actions

Перенесены TaskSObjectInputWdg/HiddenWdg/SimpleUploadWdg и пять исходных actions:
UploadAction, DateAction, TimeAction, TaskDateAction, InitialTaskCreateAction.
Vue использует существующие UploadServer и EditCmd; task parent связывается
исходным DatabaseAction. Восстановлены set_sobject_value без лишнего type filter
и uploaded repository mode. Исправлены revision checkbox/prefix и generated
revision naming; чужой ticket/выход из upload root запрещены, cleanup журналируется.
Поздний rollback сохраняет consumed file в исходном undo cache.

Реальный исходный runtime, неизменённый SDK HTTP upload/XML-RPC EditCmd,
Handler query_EditWdg procedure, отдельные SQLite/PostgreSQL и Chromium checks
описаны в tactic_stream/README.md 0.99. ТХ/legacy/рабочие данные не меняются.
Остаются составные TimeAction browser inputs, rich/multi/zip uploads,
lookup popup и HTML-dependent Handler special cases; затем config authoring,
nested layouts и revisions/preview. Полная совместимость ещё не объявляется.

## 0.100 — MultiUploadAction, UploadWdg и MultiSelectWdg

Взяты исходные specified/arbitrary upload, custom icon, context/subcontext,
revision и email trigger; FieldStorage сохранён, handoff прежнего UploadServer
добавлен для XML-RPC/Vue. FileCheckin/Command/FileUndo остаются общим путём
записи и отката. Исправлены source icon-type/prefix/empty/config/regex bugs;
дефект custom icon подтверждён настоящим runtime отдельным ожиданием.
Старый pyasm.widget.UploadWdg и MultiSelectWdg дают headless метаданные;
Vue сохраняет составные controls через EditCmd и MultiDatabaseAction.

11 адресных тестов, исходный runtime, неизменённый XML-RPC SDK/HTTP upload,
Chromium и отдельное SQLite/PostgreSQL сравнение прошли. Exact команды/границы —
tactic_stream/README.md 0.100. Рабочие данные, Handler и legacy не менялись.
0.100 — версия этапа, не 100% готовности. Следующие блоки: modern rich UploadWdg,
ZIP upload/naming, time-only inputs; затем authoring XML, nested layouts,
revisions/preview. Полная API/HTML/GUI совместимость ещё не объявляется.

## 0.101 — MultiZipUploadAction и TimeInputWdg/actions

Исходный ZIP action перенесён в прежние FileUpload/FileCheckin/EditCmd.
Common.unzip_file теперь валидирует архив до IO, ограничивает размер и пишет
через FileUndo. Полный custom naming class path сохраняет исходный метод
get_sobject_by_filename; eval и excluded prod resolvers не возвращаются.
Исправлены исходные cleanup/grouping дефекты; subcontext и revisions работают.
Восстановлены DateDatabaseAction/TimeDatabaseAction и headless TimeInputWdg.
Vue использует native time input, прежние TimeAction hour/minute и обратный
timezone display; SQL time сохраняет clock/precision на SQLite и PostgreSQL.

Actual source runtime, неизменённый SDK ZIP/XML-RPC, Chromium и отдельные
SQLite/PostgreSQL checks описаны в tactic_stream/README.md 0.101.
Handler/legacy/рабочие данные не менялись. Next: modern rich UploadWdg,
authoring XML, nested layouts и revisions/preview; full API/HTML/GUI parity
остаётся незавершённой. Номер этапа не является процентом готовности.

## 0.102 — modern UploadWdg и implicit icon context

Из оригинала восстановлены modern UploadWdg context_expr/context/setting/
pipeline branches; Vue переиспользует file-group с одним файлом и прежние
UploadAction field names. Перенесён отсутствовавший SObject.get_icon_context.
Исправлен source subcontext omission в общем UploadAction; edit/revision,
metadata priority, пустой context guard и прежние rollback contracts проверены.
Actual source, stock SDK, Chromium и real SQLite/PostgreSQL результаты/команды
описаны в tactic_stream/README.md 0.102. Handler/legacy/рабочие данные не меняются.
Next: authoring исходного XML, nested layouts и revisions/preview.
HTML/JS progress/immediate callbacks и full API/GUI parity остаются незавершёнными.

## 0.103 — исходный XML authoring и защита параллельной записи

Vue editor выбирает view/DB source, показывает exact XML и resolved layers,
проверяет исходным WidgetDbConfig.validate и сохраняет Command/SObject.commit.
Comments/CDATA/unknown XML/sibling views не теряются. Native read/check/save
не меняет XML-RPC; diff/revision guard и database lock защищают от stale create,
параллельных процессов и обычных XML-RPC/script A→B→A изменений.
Actual WidgetConfig contracts, SQLite/PostgreSQL с двумя spawn processes и
Chromium validation/save/conflict/view-switch описаны в README 0.103.
Рабочие данные/Handler/legacy не менялись. Следующие блоки — nested layouts и
preview тем же renderer; затем history/AI API. Полная история/idempotency,
filesystem dependency locking и распределённая атомарность пока не готовы.


### 0.104 — XML preview и композиция интерфейсов

Внедрён read-only preview тем же Vue ConfiguredView, без сохранения draft.
Штатный WidgetConfigView разрешает transient source с сохранением priority и
слоёв; исправлена потеря merged display при повторном чтении сырого XML.
Декларативные TabWdg/ViewPanelWdg дают вложенные view, с ограничениями дерева,
проверкой циклов/проекта и явными неподдержанными виджетами. Проверки на SQLite,
PostgreSQL и Chromium; исходный merge дефект подтверждён legacy probe.
Дальше: полноценные независимые controls дочерних ViewPanel, расширение widget
каталога и контракта validation/preview до операций AI, сохраняя общий headless
слой и исходные XML конфиги.


### 0.105 — дочерние ViewPanel controls

Native дочерние таблицы используют существующий query с независимыми filters,
order_bys, limit/offset. Поддержаны исходные XML options search_limit/order_by/
do_initial_search/show_refresh/show_search_limit, KeepAlive state при смене
вкладок и manual search. Preview и runtime используют один компонент.
Source option probe, SQLite/PostgreSQL query и Chromium выполнены на временных
данных. Дальше — контекстные read/edit/create формы дочерних представлений
через штатные EditWdg/EditCmd и права, затем расширение widget каталога.

### 0.106 — серверная конфигурация и пути

По уточнению пользователя: единые `/` в путевых настройках, API и startup,
UNC `//` сохранён. Редактор 38 поддержанных настроек работает через Config,
общую ревизию/блокировку/атомарную запись; UI с разделами и черновиками по ТХ.
HTTP/Chromium и запуск двух временных XML-настроенных workers с recovery
проверены. Миграция БД/корней остаётся отдельной задачей; Handler не изменён.
Следующий этап ядра/UI — дочерние EditWdg/EditCmd формы, как в плане 0.105.
Сквозной UI контракт уточнён: 320–360 px, touch без обязательной мыши/правой
кнопки/hover/drag, основной жест tap, максимум long press для контекстных
действий. Общая сворачиваемая навигация и зоны 44 px проверены в hasTouch Chromium.
