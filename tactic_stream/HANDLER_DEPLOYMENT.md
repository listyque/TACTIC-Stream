# Готовый Tactic Handler и два комплекта TACTIC Stream

Это обязательное уточнение ТЗ. Handler уже реализован в соседнем `th_codex`;
используем его существующие код, XML-RPC клиент, профили и запуск.
Общая цель совместимости API TACTIC сохраняется: Handler задаёт проверяемые
сценарии, а не ограничивает весь объём переноса.

## Standalone server package — L12 checkpoint, 0.112.192

`python -m tools.server_delivery --output <new-directory>` exports the application,
Apache/Webmin and PostgreSQL images, an image-only Compose file, management scripts,
licenses and SHA-256 inventory. The installed package uses named data volumes and
the Python wheel inside its image; it does not mount checkout sources or a developer
dependency volume. `manage.py load`, `init`, `update` and `check` work from the exported
directory. PostgreSQL bootstrap leaves creation of `sthpw` to the native initializer.
Existing SQLite data/configuration is never switched to PostgreSQL by initialization.
See [server installation](SERVER_DELIVERY.en.md) and
[установка серверного комплекта](SERVER_DELIVERY.ru.md).

The working source-mounted Docker environment remains independent. Windows
EXE/Electron, legacy project migration, backup/restore and complete GUI acceptance
are still L12 requirements; this checkpoint does not close L12.

## Целевая поставка

| Режим | Комплект | Подключение Handler | Управление backend |
| --- | --- | --- | --- |
| Локальный | Windows EXE, Vue/Electron, комплектный Python/headless TACTIC, SQLite и готовый Handler | XML-RPC локального экземпляра | Launcher запускает и останавливает локальный TacticMonitor с воркерами |
| Серверный | Apache, headless TACTIC, PostgreSQL; Vue в браузере или Electron | XML-RPC серверного экземпляра через Apache | Серверное окружение; клиент не управляет удалёнными процессами |

В локальную поставку включается готовый Handler и его зависимости. Запуск —
через существующие `launch.py`/`launch.pyw` или существующую готовую сборку.
Версию Handler и комплект зависимостей нужно закрепить при сборке поставки.

Vue/Electron и Handler обращаются к одному TACTIC. Проекты, пользователи,
группы, права, SObject, задачи, snapshots и файловый repository общие.
Первичная установка создаёт системную БД и определения автоматически;
CreateProjectCmd создаёт проектную БД на настроенном vendor.

Native Repository Sync принят в B12; он использует существующие возможности
Handler. Отдельный браузерный Repository Sync не создаём. Общие файловые
операции и доступ к repository входят в критерий совместимости. Handler и
Stream сохраняют самостоятельные репозитории/поставки; новый web Batch Manager
и встроенный WebEngine для QML в этот комплект не входят.

## Подключение существующим механизмом

Handler уже сохраняет presets в `thlib/environment.py`. Поля:
`server`, `user`, `ticket`, `site`, `proxy`, `timeout`, `config_format`,
`team_local_repository`. Используем их без новой схемы конфигурации.
Пароль передаётся существующему `get_ticket`; последующие запросы используют
тикет. Полная поддержка site/proxy проверяется отдельно.

| Параметр | Локальный профиль | Серверный профиль |
| --- | --- | --- |
| `server` | Например, `127.0.0.1:8081` | Публичный адрес Apache, например `192.168.2.55:8082` |
| `user` / `ticket` | Учётная запись и тикет локального экземпляра | Учётная запись и тикет серверного экземпляра |
| Проект | Выбор проекта текущим UI Handler | Тот же механизм выбора проекта |

Проект выбирается отдельно от server preset: `EnvInstance.current_project`,
`server_start(project=...)` и `server_auth(host, project, ...)`. Не добавляем
поле preset, которое готовый Handler не читает. Серверный адрес задаётся без
`/Api/`: клиент сам добавляет `/tactic/default/Api/` и передаёт проект
в существующей структуре ticket. При смене экземпляра нужен его собственный
действующий тикет.

## Маршруты и файлы

| Маршрут | Обработчик |
| --- | --- |
| `/tactic/{route_project}/Api/` | XML-RPC, включая `/tactic/default/Api/` Handler |
| `/tactic/{route_project}/UploadServer/` | Существующая HTTP загрузка Handler с тикетом |
| `/`, `/projects/<код>/`, `/ui/` | Vue, проектный workspace и ресурсы |
| `/admin/rpc`, `/admin/session/...` | API и сессия Vue того же backend |
| Настроенный `checkin/web_base_dir`, обычно `/assets/...` | Файлы соответствующего `asset_base_dir` |

Apache проксирует запросы к тем же backend-воркерам. Vue fallback не
перехватывает XML-RPC, upload и repository. Electron использует те же маршруты.

Handler скачивает repository обычным HTTP без API-тикета — как при стандартном
asset alias оригинального TACTIC. Чтение опубликованных файлов сохраняет этот
контракт; API операции и загрузка требуют авторизации. Локальные URL обслуживает
StaticFiles с отключённым переходом за корень через symlinks, доступны HEAD/Range.
Внешний `web_base_dir` обслуживается внешним файловым сервером. Путь repository
не может перекрывать маршруты приложения; alias должен иметь asset root.

## Поверхность API и воспроизводимая проверка

Актуальная очередь остатка — [L01–L12](UI_ARCHITECTURE.md#legacy-plan),
в частности L08 (поведение API/native scripts), L11 (СУБД) и L12 (поставка).
На 2026-10-19 `api_manifest.json` содержит 129 методов: 127 доступны частично,
два исключены, отсутствующих входных методов нет; `full_api_parity_verified`
остаётся `false`. Это не подтверждение всех параметров/эффектов или GUI.
Следующий список вызовов и результаты 12-сценарного стенда ниже — исторические
снимки, а не свежая проверка текущего выпуска.

`tools/capture_legacy.py` читает Handler и его SDK. В
`src/tactic_stream/compatibility/api_manifest.json` записаны receiver, строка,
число позиционных аргументов, keyword-аргументы и RPC зависимости SDK.
Сигнатуры исходного сервера хранятся там же. На 2026-10-06 выделены 26 методов
на распознаваемых клиентских receivers:

`get_ticket`, `ping`, `fast_ping`, `query`, `query_snapshots`,
`get_by_search_key`, `get_base_dirs`, `eval`, `execute_cmd`,
`execute_python_script`, `execute_js_script`, `insert`, `insert_multiple`,
`insert_update`, `update`, `update_multiple`, `delete_sobject`,
`retire_sobject`, `reactivate_sobject`, `connect_sobjects`,
`create_search_type`, `add_column_to_search_type`, `log_message`,
`start`, `finish`, `abort`.

Прежние 41 совпадение остаются кандидатами, включая посторонние методы.
Статический анализ не покрывает динамические receivers, все custom scripts,
нативные `pyasm` вызовы в процедурах и HTTP upload. В частности,
`thlib/ui/script_triggers.py` вызывает `execute_js_script`: вход теперь доступен,
но нужные варианты исполнения и эффекты требуют поведенческой проверки.
Инвентаризация не доказывает готовность всех функций.

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/handler_deployment_check.py --handler D:/code/th_codex
# Только SQLite, без Docker:
.venv/Scripts/python.exe -B -X utf8 tools/handler_deployment_check.py --handler D:/code/th_codex --local-only
```

Полный запуск требует поднятых postgres и apache существующего
`tactic-stream-linux` Compose стенда. Проверка использует неизменённый SDK
Handler, его `prepare_serverside_script`, `get_projects_and_logins`,
`query_search_types_extended`, `query_sobjects`. Создаёт собственные временные
БД, контейнеры и конфиг, использует текущие исходники без rebuild, останавливает
свои процессы и удаляет собственные фикстуры. Рабочие БД и профили не меняются.
Результат — `.test-tmp/handler-deployment.json`; адреса относятся к уже
остановленным тестовым экземплярам.

На обоих комплектах прошли по 12 сценариев: login/ticket/ping, Vue рядом
с XML-RPC, отказ неверному тикету, создание проекта и CRUD с Unicode,
задачи/заметки, три процедуры Handler, start/finish/abort, server naming,
HTTP upload/check-in/download/Range и границы файловых путей. Это проверка
клиента и backend, без запуска GUI Handler.

## Оставшиеся условия готовности

- Windows EXE/Electron, комплектный Python и включённый готовый Handler ещё
  не собраны. Нужна проверка установки и штатного запуска на чистой Windows.
- Полный GUI Handler должен пройти основные операции в обоих режимах с
  изменением только подключения. Проверить права обычных пользователей:
  текущие сценарии используют admin, ряд операций записи пока доступен только ему.
- Поведение `execute_js_script`, EditWdg metadata и других используемых веток API
  проверяется по исходным параметрам, контексту, ошибкам и эффектам. Наличие входа
  больше не считается отсутствующей реализацией и не означает полного паритета.
- Рабочий Docker экземпляр по-прежнему на SQLite. PostgreSQL комплект проверен
  на отдельной фикстуре через Apache; рабочая система не мигрировала.

Критерий завершения ТЗ — готовый Handler выполняет основные операции с обоими
поставляемыми комплектами, меняется только конфигурация подключения.
Успешные интеграционные проверки — выполненная часть этого критерия.

Исправление чекина 2026-10-07: восстановлены локальный `_get_sobjects`, объект
`Environment` при авторизации и чтение колонок через `SObject.get_attr_value`.
Append-checkin обновляет исходный `Snapshot`, сохраняя его идентичность для
последующего построения versionless. Адресная проверка
`test_transport.Transport.test_handler_extended_checkin_through_xmlrpc`
исполняет неизменённые процедуры `get_virtual_snapshot_extended` и
`create_snapshot_extended` из Handler: две загрузки, версии 1/2, latest-versionless
и содержимое файлов. Используется обычный временный проект с правилами naming;
это проверка процедуры через XML-RPC, а не всего GUI и всех режимов чекина.


## Perforce-like projects: source delivery and acceptance

The project-selected file mode uses Handler for local workflows and Stream for
inspection/administration. The builtin template creates new projects through the
native API; Classic projects remain separate. See
[installation/recovery](FILE_PROJECT_DELIVERY.en.md) and
[установка/восстановление](FILE_PROJECT_DELIVERY.ru.md).
The source delivery includes a server wheel, Handler sources and SHA-256 manifest.
EXE/Electron, physical million-file/TB transfer and target-environment/manual
acceptance remain required before production delivery is declared ready.
