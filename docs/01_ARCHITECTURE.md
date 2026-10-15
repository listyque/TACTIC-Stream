# Архитектура TACTIC Vue 0.20 — передача разработки

## 0. Что именно описывается

Документ относится к **фактически выпущенному архиву 0.20**, не к первоначальному плану миграции. SHA-256 архива: `e867f7466e830175f9290655c6a7fcb958bccafffb1db117fb8cffc02d2139dd`. Ядро: `5.0.0.a02`, исходная линия `17c78e0dfb20a6fef16d70df6aa7b0c9bf20a596`. Номер native UI — отдельный `NATIVE_UI_VERSION=0.20`.

При передаче заново проверены CRC архива, хеши 7692 файлов его манифеста, build-manifest и выполнена статическая индексация. Приложение и функциональные тесты в рамках этой передачи **заново не запускались**. Отчёты предыдущего выпуска — исторические свидетельства, а не новый прогон.

Точная форма реализации: **форк Python-сервера TACTIC с нативным Vue-представлением и конечным JSON API в том же CherryPy-процессе**. Это не порт Python в JavaScript, не новая ORM, не отдельная SPA с фиктивной БД, не iframe над старым сайтом. Однако отделение сервера от legacy UI не закончено: старые пакеты всё ещё нужны.

## 1. Общая схема

```text
START_TACTIC.bat / MANAGE_TACTIC.bat / SETUP_ENV.bat
        │
        └─ tools/local/tactic_bootstrap.ps1
               └─ tools/local/control.py
                    ├─ launch.py                      standalone / legacy
                    └─ cluster.py                     supervisor + Cheroot gateway
                         ├─ cluster_worker.py #1       primary, reads + writes
                         ├─ cluster_worker.py #2       selected reads
                         └─ cluster_worker.py #3       selected reads
                                  │
                             CherryPyStartup
                                  │
         ┌────────────────────────┼─────────────────────────────────┐
         │                        │                                 │
 /tactic/<project>/        /api/ui/v2/*                       original RPC / legacy
 native HTML shell        mount.ApiRoot → Api               Api / XMLRPC / UploadServer
         │                        │                                 │
 /tactic-ui/*             ExtendedBackend                           │
 compiled Vue + Ace       mixin services                             │
         │                        │                                 │
         └──── metadata / rows / command results ──┐                │
                                                   │                │
                  WidgetConfigView / Search / SObject / Command / Trigger
                                                   │
                           original sthpw + project DBs + file repository
```

Кластер не обязателен для архитектуры Vue: тот же mount работает в одиночном сервере. Gateway — транспорт и контроль локальных процессов, не отдельный предметный backend.

## 2. Где именно встроена Vue

### 2.1 Серверная точка подключения

В `src/pyasm/web/cherrypy30_startup.py`, в `CherryPyStartup.execute()`, до `cherrypy.engine.start()` вызывается `tactic.ui_api.mount.install()`.

`src/tactic/ui_api/mount.py:install`:

- читает source `config.json` и переопределения `<data-dir>/config/native-ui.json` через `tactic.core.native_settings`;
- создаёт `Api(ExtendedBackend(settings), session_store)`;
- монтирует JSON API по `/api/ui/v2`;
- монтирует локальные static resources по `/tactic-ui`;
- устанавливает CherryPy `before_handler` tool, который отдаёт shell для подходящих HTML-страниц.

`src/tactic/ui_api/routing.py:native_page` проверяет HTTP method, `Accept: text/html`, проектный путь и reserved/service paths. Native shell не должен подменять XML-RPC, загрузчик, произвольные custom URL и служебные маршруты. Новый проект может открыть HTML shell без регистрации новой отдельной SPA.

`TACTIC_UI=legacy` отключает native mount. В 0.20 пользовательский вход для такого режима — `START_TACTIC.bat --legacy`. Это переключение представления, а не откат уже записанной БД или общих исправлений Python.

### 2.2 Реальный frontend-стек — не исходный план

Фактически используется **Vue 3.5.13**, JavaScript и Options API в обычных SFC. Всего в build-manifest **50 SFC вместе с App**. Ace 1.4.7 взят из TACTIC и обслуживается локально.

В текущем build-пути **нет Vite, TypeScript, PrimeVue, Pinia или Vue Router**. Не устанавливать эти технологии как будто они уже являются обязательной частью проекта. Ранее они обсуждались как план, но не стали фактической сборкой.

`tools/native_ui/build.cjs` — небольшой специальный сборщик:

1. Читает `NATIVE_UI_VERSION` и поставляемый `vue.global.prod.js`.
2. Выполняет официальный Vue compiler в Node VM для предварительной компиляции template.
3. Извлекает обычные `<script>\n…\n</script>` и `<template>\n…\n</template>`.
4. Обрабатывает `api.js` и `uiState.js`, затем SFC в **явном массиве `names`**.
5. Удаляет обычные import-строки, заменяет Vue imports доступом к глобальному Vue, оборачивает компоненты в IIFE.
6. Регистрирует их глобально и выполняет `Vue.createApp(App).mount('#app')`.
7. Проверяет синтаксис итогового classic script, пишет `app.js`, `styles.css`, `index.html`, `build-manifest.json`.

**Это не универсальный сборщик SFC.** `<script setup>`, TypeScript, произвольный граф импортов и новые внешние зависимости автоматически не поддерживаются. Для нового компонента нужно обновить `names`; одного нового файла недостаточно. Нельзя править только скомпилированный `web/app.js`: следующая сборка затрёт такую правку.

`frontend/src/main.js` не определяет этот фактический production build. Источник правды — `build.cjs`. Собранные resources находятся в `src/tactic/ui_api/web`; Node для ежедневного запуска не нужен.

Миграция на Vite возможна как отдельное последующее решение, но сначала нужны тесты поведения, контроль generated assets и сохранение запуска без Node у пользователя.

## 3. Реальные слои Python и их обязанности

### Старое ядро

`src/pyasm/search`, `biz`, `command`, `security`, `checkin`, `prod/service` и `src/tactic/command` остаются источником предметного поведения. `SearchType` — реестр типов, `SObject` — объект, `Schema` — отношения, `Pipeline` — определения процессов. UI не создаёт альтернативных Project/Task/Asset-моделей.

### Выделенный `tactic.core`

Содержит два разных вида кода:

**Перенесённые алгоритмы и команды:** `widget_config.py`, `edit_commands.py`, `schema_commands.py`, `pipeline_commands.py`, `process_commands.py`, `admin_commands_017.py`, `collection_commands.py`, `message_commands.py`, `work_hours.py`, `bootstrap.py` и другие.

**Новые проекции/адаптеры:** `config_model.py`, `view_resolution.py`, `cell_edit_config.py`, `widget_containers.py`, `query_model.py`, `native_edit.py`, `design_document.py`, `sidebar_edits.py`, `field_policy.py`.

Название core **не означает полную независимость от web/UI**. В отдельных командах остаются WebContainer и legacy handlers. Старые пути классов часто реэкспортируют перенесённые классы: конфигурационные class paths и сторонние скрипты нельзя ломать перемещением файла.

### `tactic.ui_api`

`Api` — транспортный dispatcher, session/CSRF, ограничение тела и error envelope. `ExtendedBackend` объединяет сервисы через множественное наследование. `ConfigBackend` содержит базовое разрешение sidebar/view/query/form; `TacticBackend` — контекст оригинального сервера и транзакционную границу.

Предметные сервисы: `table_edit_service`, `graph_service`, `security_service`, `search_type_service`, `sidebar_service`, `design_service`, `script_service`, `task_service`, `work_hour_service`, `message_service`, `record_service`, `upload_service`, `version_service`, `collection_service`, `ui_state_service` и другие.

Это **не независимые микросервисы**. Они работают на одном объекте backend, разделяют active_target, helpers и исходный request context. Порядок базовых классов и `super()` влияет на поведение. Перед переименованием или переупорядочиванием миксинов проверить полный MRO, а не только один файл.

Полные классы, методы, диапазоны строк и хеши — `inventory/native_code_index.json`. Объём 104 Python-модулей в новых слоях/tools сам по себе не является мерой готовности UI.

## 4. Как получается настоящий sidebar и страница

### 4.1 `widget_config` остаётся источником истины

`SidebarConfig` в `core/sidebar_config.py` выделен из `SideBarPanelWdg` / `SideBarBookmarkMenuWdg`. Он выбирает `project_view`, `my_view_<login>`, `admin_views` либо `_my_admin` по исходной логике. Читаются DB-записи, файлы типа проекта, персональные/общие definitions и `DEFAULT-conf.xml`. `Schema Views` генерируются исходным механизмом отдельно.

В `ConfigBackend._tree()` исходные конфигурации переходят в `ConfigModel`, затем `SidebarProjection`. Проверяются права ссылки. Папки, заголовки и разделители — структура sidebar, а **не неподдержанные страницы**.

`SidebarProjection` выдаёт стабильный id ссылки и сохраняет server target. Идентификатор не должен зависеть только от визуальной позиции. Вложенные derived targets используют `/~tab/…`, `/~layout/…`, `/~admin/…`, `/~design/…` и другие контролируемые ветки. Глубина ограничена.

### 4.2 Open-поток

```text
App/SidebarNode → GET /sidebar
             → пользователь выбирает target
             → GET /open {project,target}
             → ExtendedBackend.open_target
                  заново разрешает исходный target и его scope
                  определяет kind по явным handler aliases
                  строит нужные metadata/children/spec
             → App или WidgetHost
                  table → ConfiguredTable / WidgetTable
                  form  → EmbeddedForm / ConfiguredForm
                  tabs  → ConfiguredTabs → WidgetHost
                  graph/admin/layout → специализированный компонент
                  unknown → явная диагностика
```

Нельзя заменить неизвестный handler на таблицу только потому, что в options присутствует SearchType. Нельзя определять виджет по заголовку меню. `Project Workflow` — графический редактор, а `Pipelines` — исходная таблица, из ячейки которой открывается выбранный граф: это разные штатные пути.

`core/config_model.py:SCREEN_HANDLERS`, `TABLE_HANDLERS`, `target_spec` — явная семантическая регистрация. `widget_aliases.json` отдельно разрешает краткие имена XML. **Наличие alias не доказывает, что все options этого класса уже работают.**

Диспетчеризация существует и в `App.vue`, и в `WidgetHost.vue`; исторически отсутствие компонента в одной из этих точек ломало основные либо вложенные страницы. При добавлении редактора проверить обе точки, derived target, dirty-state и разрешения.

## 5. Наследование конфигураций: не делать наивный merge

`core/widget_config.py` содержит перенесённые `WidgetConfig/WidgetConfigView`. `ConfigModel.from_tactic` берёт реально разрешённую последовательность слоёв. Проекция хранит источники, но сама не строит legacy HTML.

Критичные особенности `ConfigModel`:

- порядок элементов принадлежит первому подходящему view, в том числе **пустому**;
- атрибуты наследуются по приоритету;
- handler и его options разрешаются **независимо**;
- options — первый непустой блок, не рекурсивный merge всех слоёв;
- повторные имена `<element>` имеют особые правила; нельзя дедуплицировать весь XML;
- `definition`, `edit_definition` и `default_definition` — не обычные страницы;
- provenance и fingerprint должны учитывать ту конфигурацию, которая реально участвует.

`core/view_resolution.py:resolve_table` воспроизводит отдельные ветки TableLayout: inline `config_xml`, `config_code`, `element_names`, глобальные column configs. Эти ветки не эквивалентны.

`widget_containers.py` отдельно реализует разрешение EditWdg и TabWdg. В TabWdg сохранены особенности последнего include, selected, load, hidden elements, use_state, чтения legacy save_state. Переписать эту последовательность «понятнее» без дифференциального теста значит изменить старые проекты.

Для **редактирования XML** проекции недостаточно. `design_document.py`/`sidebar_edits.py` и соответствующие сервисы используют targeted XML changes с сохранением нетронутых частей. Не сохранять исходный документ через `ConfigModel.elements()` как через полную сериализацию: неизвестные узлы, комментарии, CDATA и соседние views можно потерять. Копирование разрешённого view в Manage Views — отдельно обозначенная операция snapshot.

## 6. Таблица: четыре самостоятельных уровня

### 6.1 Metadata

`ConfigBackend.view` создаёт фактический словарь `spec`: `type`, `view`, `resolved_view`, `fields`, `revision`, `table_options`, `capabilities`, `diagnostics`. Это не Python-класс `ViewSpec`, обещанный первоначальным планом. `ExtendedBackend.view` добавляет известные semantic providers и специальные поля.

Поле содержит имя, label, kind, storage, read_only, supported, handler, action, options, nullable, sources, display/edit/action metadata. Часть существующих физических колонок с неизвестным display-handler может читаться как raw value **с диагностикой**, но не объявляется перенесённым виджетом и не становится автоматически редактируемой.

### 6.2 Query и display

`Api` получает `project,target`, а не произвольную SQL-таблицу для обхода прав. Сервер заново разрешает target, исходные фильтры view, parent/scope, архивный режим, пользовательский составной запрос, сортировку и страницы через настоящий `Search`.

`query_model.py` — ограниченная структура AND/OR и адаптация известных legacy filters. Это не универсальный интерпретатор любых выражений. `Search.eval` разрешён в конкретных доверенных server-defined местах; свободный код браузер не выбирает.

Строка отделяет:

- `key` — полноценный search key;
- `values` — исходные значения для данных и ревизий;
- `cells` — отображение разрешённого виджета;
- черновик — отдельно в памяти ConfiguredTable.

`column_service`, `cell_value_service`, `thumbnail_service`, `global_admin_service` готовят известные renderers. `WidgetCell.vue` показывает format/link/XML/status/login/color/thumbnail/widget buttons. Цвет pipeline и display_name не подменяют код статуса или login в записи.

### 6.3 CellEdit не равен полной форме

`/cell-editor` → `TableEditService` → `core/cell_edit_config.py` воспроизводит исходную ветку `CellEditWdg`: edit, inline edit, DB edit_item. Для сохранения отдельно разрешаются actions через save-config. Не открывать вместо этого обычный EditWdg и не сохранять formatted string обратно в raw поле.

`FieldInput.vue` пока реализует ограниченные стандартные контролы. Отдельные WorkHours, граф, файлы и сложные действия не должны молча становиться обычным TextWdg.

### 6.4 Save Changes

Применение редактора меняет только локальный буфер. Несколько строк/полей отправляются одним `/table-changes`. До первого write проверяются все keys, scope, row revisions, table/editor config revisions, fields и known actions.

`NativeTableEditMultipleCmd` наследует оригинальный `EditMultipleCmd`, меняя фабрику дочернего edit-command. `_write` оборачивает выполнение в оригинальный `Command` и сохраняет `update_multi`. Не заменять пакет последовательными PATCH.

`NativeEditCmd` адаптирует транспорт JSON, в том числе `None`, 0, sibling form fields и password confirmation. В `native_edit.py` есть последовательное переопределение одноимённого класса через `_OriginalNativeEditCmd`; учитывать обе части. `validated_form_values` временно предоставляет валидированные значения через WebContainer и восстанавливает прежнее состояние.

В оригинальный `SObject.set_value` добавлен opt-in `allow_none=True`; старые вызовы без флага сохраняют прежнее поведение. Отдельно проверяются NULL/empty/false/zero и большие numeric.

Откат DB-транзакции не отменяет внешние effects скриптов, сети и файлов. Потеря ответа не разрешает автоматически повторять write. Лимит буфера — 100 строк / 1000 ячеек. Новые строки всё ещё создаются popup-формой, а не временными insert-строками буфера.

## 7. Авторизация и request lifecycle

`api.py` нормализует запрос, создаёт request_id/trace, проверяет метод/JSON, cookie, CSRF и Origin для меняющих операций. Cookie native session — HttpOnly, SameSite=Strict, path `/api/ui/v2`; ticket TACTIC остаётся на сервере.

`TacticBackend.context` под process-local RLock создаёт оригинальный контекст TacticInit/WebContainer/CherryPyAdapter, проверяет ticket через XmlRpcInit, устанавливает проект и локальный TacticServerStub. При выходе commit/abort/release SQL и очистка Container выполняются независимо от результата.

**Вход жёстко admin-only в login и request context.** Наличие экрана Manage Security не означает завершение политики обычных пользователей. `field_policy.py` и scope-checks — часть защиты, но снимать admin-only одним удалением if нельзя.

Два in-process lock-а (`Api.lock` и backend lock) защищают shared request state. Они не делают внешние legacy-клиенты участниками той же блокировки. Не переносить это без анализа в асинхронный конкурентный обработчик: active_target, original Container и stub создают риск смешения контекстов.

`allow_writes`, `allow_uploads`, `allow_script_execution` — отдельные gate; uploads/scripts требуют writes. Параметры берутся из `core/native_settings.py`. Production-проверки лицензии не отключаются. Тестовый флаг signature isolation не является способом рабочего запуска.

## 8. Где что сохраняется

| Данные | Реальное хранилище | Не путать |
|---|---|---|
| Схема проекта и реестр SearchType | Исходные Schema/SearchType, sthpw и project DB | Не JS-модели |
| Поля, layouts, sidebar, именованные views/поиски | `config/widget_config` + исходные XML-файлы | Не localStorage |
| Личные настройки рабочего места | `WidgetSettings` → `sthpw/wdg_settings` | Отдельные `native:ui:v1:*` JSON keys, не все legacy keys |
| Черновик формы / таблицы | Память смонтированного Vue-компонента | Не сохранённый SObject |
| Серверный XML | Активный `tactic-conf.xml` | Не preference и не новый config store |
| Разрешения native транспорта | `<data-dir>/config/native-ui.json` | Не правила групп TACTIC |
| Пути и режим до старта сервера | `launcher.local.json` рядом с BAT | Не БД UI-предпочтений |
| HTTP session кластера | Приватный `sessions.sqlite3` run-id | Технический store, не новая предметная БД |
| Файлы до check-in | `<tmp>/native_resumable` | Не окончательный repository |
| Версии и файлы | Исходные Snapshot/File и repository | Не staging uploads |

`frontend/src/uiState.js` ведёт очередь по channel/project/scope/target, debounce 300 ms, revision и flush перед выходом/переходом. Старые ответы проверяются по поколению навигации. Ошибка сохранения предпочтений не должна показаться успехом или стереть чужую запись. Нет автоматического переноса всех форматов legacy state в native JSON.

## 9. Кластер и консоль

`cluster.py` запускает 2–8 workers (по умолчанию 3), держит owner/lifetime locks, проверяет здоровье и перезапускает упавший процесс в прежней роли. Gateway на публичном localhost-порту; workers — соседние loopback-порты с приватным заголовком. Это локальная группа, не TLS/HA/multi-host deployment.

`cluster_gateway.py:is_balanced` распределяет только явные GET routes и **POST /query**. Остальные маршруты — через primary и его последовательную очередь. Например, название timeline в списке не означает балансировку POST /timeline: это отдельный кандидат на анализ. Автоматического replay нет даже для reads.

FirstRun и периодический scheduler — у writer; исходные бизнес-триггеры нужны каждому worker. Базовый cache-mode выбран вместо разошедшихся full process caches. SharedSessionStore хранит исходные tickets, CSRF и revocation; рестарт одного worker сохраняет сессию, полный рестарт группы требует входа заново.

Существуют 503 до отправки при недоступном primary и возможный 502/обрыв уже отправленного запроса. Второй случай может означать выполненную запись с потерянным ответом. Не переключать такой write на другой worker автоматически.

`action_log.py` пишет безопасные START/RUNNING/END и принятые UI intent events. `frontend/src/api.js` присваивает action_id; сервер отдельно создаёт request_id. `execute_traced` связывает реальные команды с trace. Клиентское событие не является свидетельством commit. RUNNING показывает незавершённый запрос, не процент выполнения.

`TACTIC_ACTION_LOG=actions|verbose|off`; safe logs ротируются, supervisor объединяет их в консоль. Сырые worker logs могут содержать секреты исходного TACTIC и не равны безопасному журналу.

## 10. Файлы, скрипты, schema — отдельные опасные границы

Resumable upload сохраняет offset/fingerprint на серверном диске. До финализации нет snapshot. При финализации выполняется оригинальный `simple_checkin`. Durable квитанция снижает риск дубля; состояние `uncertain` после обрыва запрещает автоматический retry. Это не exactly-once транзакция диска, SQL и сторонних hooks.

Checkin policy не должна пропускать неизвестный клиентский validator, revision/sequence или options panel ради «работающего upload». Нужен отдельный перенос такого контракта.

Script Editor выполняет только сохранённый Python с отдельным permission gate и проверкой ревизии. Это выполнение на сервере с его правами, не sandbox; HTTP timeout не гарантирует остановку кода. Mako/JS в Custom Layout пока только сохраняются, не исполняются в native preview.

Manage sTypes умеет add-only columns. Просмотр ссылок на поле — кандидаты, не разрешение безопасно DROP/RENAME/ALTER TYPE. Offline managed SQLite upgrade уже имеет staging/backup/restore и проверку SERIAL identity; не подменять его write-запросом UI.

## 11. Технический долг, который нужно знать до следующего изменения

1. **Большой ExtendedBackend и множественное наследование.** Нет явной отдельной модели request context/dispatcher для каждого сервиса; super-chain хрупок.
2. **Дублирование renderer dispatch в App и WidgetHost.** Исторический источник исчезающих специальных страниц. Рефакторить в общий host после контрактных тестов root/nested/restore.
3. **Специальный build-script.** Он работоспособен для текущих SFC, но хрупок к формату, импортам и новым библиотекам; миграция на нормальный compiler — отдельный PR.
4. **Нет полноценной runtime-валидации всех ответов / общей строго типизированной схемы.** `contracts.py` содержит helpers, не полный OpenAPI. Не считать будущий TS-план уже реализованным.
5. **Неполная политика обычных ролей.** Admin-only остаётся существенной границей продукта.
6. **Некоторые ограничения выражены как 501/guard, другие — diagnostics/read_only/неполный renderer.** Один grep по 501 не показывает всю недостающую функциональность.
7. **Исторические карты устарели.** Старые SOURCE_MAP и REVIEW_MATRIX описывают выпуск, не текущую истину. В исходном inventory_widgets.py словарь REVIEWED всё ещё фиксирован на 1.0.
8. **Много файлов vendor среди UI-кандидатов.** 1351 не означает 1351 собственный экран. Для планирования нужно отделить Ace/CKEditor/MooTools и маленькие виджеты от пользовательских сценариев.
9. **Raw/side effects.** Read-route может выполнять служебную запись исходного ядра. Не объявлять readers SQL read-only и не обещать линейное ускорение.
10. **Нет доказанной Windows/production parity.** Stored tests на Linux/SQLite и bridge не заменяют реальный браузер, Windows wrappers, подпись лицензии, PostgreSQL и рабочие configurations.

Сначала зафиксировать реальную работу на пользовательской тестовой установке и конкретные отличия от legacy, затем улучшать структуру без изменения поведения. Не переписывать одновременно ORM, формат конфигурации, launcher и UI.
