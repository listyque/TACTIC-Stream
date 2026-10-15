# 1.1 — происхождение изменений и проверка Global

Основа: TACTIC Vue source fork 1.0. Не новый продукт и не новая схема приложения. Настройки sidebar по-прежнему разрешает исходный WidgetConfig/SidebarConfig; новые Global handlers дополняют target registry, а не заменяют список пунктов меню.

| Исходная область | Новая граница / файлы | Проверка |
|---|---|---|
| `_global_admin`, 13 штатных ссылок, DEFAULT-conf.xml | `config_model.target_spec`, `App.vue`, `WidgetHost.vue` | 13 открытий и содержимое через original server HTTP и браузер |
| `DbConfigWdg` / `DbConfigContentWdg` | `core/system_config_model.py`, `ui_api/global_admin_service.py`, `GlobalSettings.vue` | Оригинальные секции/ключи; XML/backup/conflict/secret tests; настоящая файловая запись по HTTP |
| `LicenseManagerWdg` / `RenewLicenseCbk` | `core/license_commands.py`, legacy reexport, dedicated API/Vue | execute AST совпадает с 1.0; метаданные и отказ v1 проверены. Успешная cryptographic replace не проверена |
| `login`, `login_group`, `db_resource` insert/edit definitions | `config_backend`, `global_admin_service`, `core/native_edit.py`, `ConfiguredForm`, `FieldInput` | Оригинальные значения, defaults и actions на full seed; password confirmation, write-only secrets, conflict |
| `NonEmptyAction`, `LoginAction`, `PasswordAction`, `SecurityAddGroupToProjectAction` | Валидированные временные form values, original handlers | Реальный NativeEditCmd; не прямой SQL и не замена всех handlers DatabaseAction |
| Group DropElementWdg / User Assign / Global Rules / HiddenRow | `global_cells/global_cell_target`, `WidgetCell`, `ConfiguredTable`, `GroupMembership`, `AdminPanel` | Реальная membership/rules запись; отказ подмены связанной группы; раскрытие настроенной таблицы |
| Database Resource `projects` и `add_project` | Исходная Schema + EditWdg `sthpw/project/db_resource` | Реальная регистрация ссылки на базу и повторное чтение по связи; не создание самой БД |
| `ProjectWdg` | Ячейка database exists/version, исходный Project.database_exists и сравнение версии | Оригинальная выборка проектов; не замена ячейки одним title |
| `GraphEditor` / `PipelineToolWdg` / `SchemaToolWdg` | Target с root App, initial selection, source schema, owner context, pending property state | Создать pipeline/процессы/связь→сохранить→перечитать; admin-owner; встроенная и сохранённая схема |
| `PipelineSaveCbk`, `ProcessInfoCmd` | Тот же command path, правильный project context | Настоящий config/process в full SQLite; подпись лицензии отдельно изолирована тестом |
| SQLite upgrade `id serial PRIMARY KEY` | `sqlite_upgrade.repair_identity_columns`, staged worker, CHECK metadata | 6 старых таблиц, значения/storage/rowid/index/trigger, backup, 0 старых методов при repair/repeat |
| Source allow_writes reset при распаковке | `core/native_settings`, `CONFIGURE_NATIVE.bat`, `configure_native.py`, mount | Явная локальная операция, хранение в data/config/native-ui.json, defaults остаются false |

## Различия, которые не следует считать перенесёнными

System Config требует ручного перезапуска; оригинальный bootstrap/restart и автоматическое создание директорий не выполняются. Preview/template update, все custom виджеты и меню, произвольные expression/SQL providers не заменены фиктивной поддержкой. Default Group table показывает именно выбранный конфигурацией `login_group` (внутренний код), а не подменяет его human `name`: это разные поля исходного TACTIC.

Source Schema для admin/sthpw/unittest остаётся read-only — оригинал принудительно читает эти схемы из конфигурации исходников. Редактировать нужно рабочий проект. Schema editor не выполняет миграции колонок и данных. Параметр pipeline задаёт исходный выбранный граф и больше не считается ограничением доступа.

## Области доказательств

- `validation/final/summary.json`: полная повторная регрессия 921 unit / 322 fixture HTTP / 212 fixture browser. Каждый старый набор использует чистое тестовое хранилище.
- `validation/original-verified/summary.json`: настоящий сервер и полные SQLite seed-копии, оригинальная аутентификация/модели/команды. 83 HTTP + 42 browser, последовательный сценарий на одной отдельной временной установке.
- `validation/identity-verified/summary.json`: 11 проверок полной миграции и ремонта старого SERIAL-результата. Оригинальные SQL-методы не подменены.
- `source-provenance.json`: сравнение AST исходного RenewLicenseCbk.execute.
- `validation/native-navigation.log`: попытка реальной Chromium-навигации была отклонена средой. Последующие browser-наборы имеют явный HTTP bridge.

Cryptodome/подпись лицензии не были доступны для full-server теста: используется явный тестовый --isolate-license. В рабочем коде License verify остаётся включённым. Windows BAT/PowerShell, PostgreSQL/MySQL, все пользовательские плагины и реальные сетевые файловые репозитории этими тестами не доказываются.
