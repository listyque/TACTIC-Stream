# Карта изменений 0.14

## Основа и сохранённая логика

Основа — фактически опубликованная .13. Незавершённая прежняя .14 не использовалась как реализация. Существующие `Search`, `SObject`, `EditCmd`, `EditMultipleCmd`, `widget_config`, sidebar и формы не заменены. Изменения не включают DDL прикладных баз, миграцию или новый доменный backend.

| Файл | Изменение и исходная граница |
|---|---|
| `tools/local/cluster.py` | Supervisor, запуск оригинального CherryPyStartup в дочерних процессах, контроль, heartbeat, atomic status и localhost Cheroot gateway |
| `tools/local/cluster_worker.py` | Worker поверх прежних configure_paths, FirstRunInit/WebInit/CherryPyStartup; только writer выполняет FirstRun; watchdog и общий lifetime-lock |
| `tools/local/cluster_gateway.py` | Exact native read allowlist + POST/query round-robin; остальные запросы сериализуются на writer; streaming, Host/headers, no retry |
| `tools/local/local_lock.py` | Старое эксклюзивное API сохранено; добавлены shared lease и отдельное имя owner-lock; Windows LockFileEx вместо msvcrt для shared/exclusive |
| `src/tactic/ui_api/shared_sessions.py` | SessionStore-compatible приватный межпроцессный транспортный store с исходными TACTIC tickets, общей CSRF/revocation и лимитами |
| `src/tactic/ui_api/cluster_runtime.py` | Private worker access guard и whitelist-проекция статуса без secrets/путей |
| `src/tactic/ui_api/mount.py` | Выбор SharedSessionStore только при supervisor environment; standalone остаётся in-memory |
| `src/pyasm/web/cherrypy_startup.py` | Только writer запускает периодический scheduler; базовый cache-режим для cluster; startup ticket cleanup не повторяется в группе; standalone прежний |
| `src/pyasm/web/cherrypy30_startup.py` | Исходный lazy REST loopback получает приватный credential в cluster; external redirects запрещены для этого внутреннего запроса |
| `src/tactic/ui_api/admin_service.py` / `AdminPanel.vue` | Штатный System Info получает статусы PID/ролей/запросов; маршрутизация sidebar не меняется |
| `src/tactic/ui_api/table_edit_service.py` | `/table-fill-preview` разрешает каждый исходный CellEdit/edit_item и валидирует draft; не выполняет запись/action |
| `src/tactic/ui_api/api.py` / `extended_backend.py` | Ограниченный маршрут preview, без универсального Python-class/eval API |
| `ConfiguredTable.vue` | Выбор колонки/value, preview, проверка локальной ревизии буфера, атомарное staging всех строк; прежний Save Changes остаётся командой записи |
| `TableToolbar.vue` | Fill в контекстном меню выбранных строк, не россыпь постоянных кнопок |
| `ConfiguredForm.vue` | Synchronous submit latch и снимок values для предотвращения повторного клика; не server durable idempotency |
| `frontend/src/styles.css` | Читаемые вспомогательные таблицы Fill/cluster в светлой и тёмной темах |
| `START_CLUSTER.bat` | Новый grouped launcher; прежние BAT/runtime-manifest без изменений |

## Тесты

`test_cluster_014.py`: реальные sqlite3 session файлы, shared/revocation/expiry/limits, crossprocess file locks, маршрутизация/serial writes/parallel reads/no replay. `test_fill_014.py`: валидация preview и отсутствие вызовов сохранения. `test_fill_state_014.cjs`: настоящие Vue-методы staging/submit.

`run_cluster_014.py` и test-only worker создают disposable исходную установку и запускают три настоящих процесса. Проверяется только оригинальный password/ticket/SQL/Command path; подпись лицензии изолируется явно в тесте, не production. Использует предыдущие run_http_012/run_http_11 плюс новый run_http_fill_014 и run_browser_014. Сырые worker logs в публикацию не входят.

## Не заявляется

Не полный master/replica database-кластер, не load-tested HA, не SQL READ ONLY role и не автоматическая отмена внешних side effects. Не весь Fill/Paste и не новые буферные insert-строки. Исходные UI каталоги остаются; полный headless/callback parity этим этапом не обеспечивается.
