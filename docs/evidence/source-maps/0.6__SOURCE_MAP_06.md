# Карта исходников — native UI 0.6

Основа — полный source fork 0.5 (SHA-256 `1002aa537f0bf7e37af696dc1a5ae08a346028b67cb68952aed08a79e8534322`), не новый демонстрационный проект. Все пути ниже относительно корня TACTIC-5.0. JSON-проекции и конечные endpoints не заменяют widget_config/Schema/Command.

| Исходный контракт | Изменение 0.6 | Нативный компонент | Сохранённый смысл / предел |
|---|---|---|---|
| `src/tactic/ui/panel/collection_wdg.py: CollectionAddCmd/RemoveCmd/DeleteCmd` | `src/tactic/core/collection_commands.py`, старый import alias | `CollectionPanel.vue` | Три исходных execute без изменения AST; настоящие junction-операции/триггеры |
| `CollectionAddCmd.get_parent_codes` | Search BFS, ограниченный обход | Ошибка при попытке цикла | Намеренная замена PostgreSQL ARRAY/depth-10, переносимый поиск родителей |
| `_is_collection`, `<type>_in_<type>` | `ui_api/collection_service.py`, проверка исходной схемы | Каталог/состав/кандидаты/вложенность | Не новый тип данных, не копирование объектов |
| `edit_collection` + `NativeEditCmd` | Серверная проекция исходной формы; маркер фиксирован сервером | `ConfiguredForm.vue` из CollectionPanel | Custom actions без поддержки не подменяются записью обычного поля |
| Исходные collection handler/options | `core/config_model.py`, `ExtendedBackend` | Тот же sidebar и mount в App | collection_key/show_collection_shelf соблюдаются; неизвестные scope не игнорируются |
| `Snapshot` + `get_files_by_snapshots` | `ui_api/version_service.py:/file-versions` | `FilePanel.vue` | Серверные страницы/контекст/архив, регистрация файлов пакетно |
| `TacticServerStub.set_current_snapshot`, `Snapshot.set_current` | `/snapshot-current` preview/confirmation + original `_write` | Подтверждение current | Не direct SQL update, не set_latest; original triggers/versionless |
| `UploadServerWdg` / исходный single-file check-in | Новый ограниченный staging transport; `UploadStore` + `UploadService` | `UploadQueue.vue` | Не общий перевод UploadServerWdg; финал только simple_checkin |
| `CheckinWdg.get_checkin_script_path` / process overrides | `core/checkin_policy.py` + guard обоих upload paths | Диагностика unsupported check-in | Custom callbacks не исполняются и не пропускаются молча |
| `simple_checkin` | `_finish_staged_upload` через `_write` | Отдельная финализация | Существующая команда, mode=copy/create_icon=False, один файл/одна операция |
| `RecordService.file` | Сохранён исходный secured download | Ссылки/предпросмотр FilePanel | Принадлежность object/snapshot/file и допустимые пути проверяются сервером |

Обработчик kind=collections уже распознавался в предыдущем target registry, но не имел полной нативной реализации. Новая итерация заполняет этот контракт сервисом и CollectionPanel; пункты sidebar остаются конфигурационными.

## Конечные API-проекции

Все — `/api/ui/v2` в прежнем процессе CherryPy. Request context/cookie/Origin/CSRF и `_write` не заменены.

- GET/POST `/collections`, GET `/collection-members`, POST `/collection-change`.
- GET `/file-versions`, GET/POST `/snapshot-current`.
- GET/POST/DELETE `/uploads`, GET `/upload-status`, PATCH `/upload-chunk`, POST `/upload-finish`.

PATCH передаёт raw octet-stream не более 4 МиБ; JSON других маршрутов ограничен отдельно. Названия классов, SQL и пути с клиента не исполняются. `/~collection-items` — серверно-проверенное производное представление общей таблицы только для соответствующего collection target, не универсальный stype override.

## Изменённые общие исходники

`src/tactic/ui/panel/collection_wdg.py` заменяет определения трёх серверных классов reexports. Старые виджеты не удалены. `api.py/mount.py` регистрируют конечные маршруты и bounded binary body. `tactic_backend.py` хранит серверные настройки staging; `extended_backend.py` подключает новые mixins. В `RecordInspector` заменён старый file tab, удалён его прежний неиспользуемый upload/preview код. Прежний небольшой endpoint остаётся для совместимых клиентов, с новым policy guard.

Build — существующий локальный предкомпилятор `tools/native_ui/build.cjs`, 27 SFC, Vue 3.5.13. Это не утверждение о Vite или обновлении Vue. BAT/окружение сохранены побайтно относительно 0.5 (проверка в packaging manifest).

## Источник алгоритмов / проверка

`tests/native_ui/source-provenance-06.json` содержит SHA-256 нормализованного AST методов `execute` из исходного архива 0.5. `test_collections_06.py` сверяет новые методы с этими значениями. Добавленная проверка предков преднамеренно вынесена отдельно. Это доказательство сохранения этих тел методов, не доказательство полного runtime-соответствия всей системы.

Реальные OS/file-lock тесты — `test_uploads_06.py`. Реальный production UploadService с дисковым Store и подставной DB-командой — `StagedPolicyIntegrationTests`. Коллекции/версии — настоящий Search/Select/SqliteImpl с изолированными таблицами, не установленный TACTIC. HTTP/browser use `fixture_06.py`; production-код fixture не импортирует.

`run_validation_06.py` пересобирает браузерный bundle и запускает unit + все предыдущие HTTP/browser suites и новые. Для каждого HTTP/browser suite — отдельное чистое test-хранилище. Результаты — в `validation/summary.json`, а не суммирование прежних заявлений.

В новом browser bridge криптографический адаптер hashlib используется только из-за insecure about:blank; production WebCrypto не подменён. Полноценные PostgreSQL/check-in/versionless/Windows/multiworker интеграционные проверки не выполнены.
