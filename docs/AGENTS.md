# TACTIC Vue source fork — правила работы с репозиторием

Это кандидат AGENTS для переноса в репозиторий. Если там уже есть AGENTS, сначала прочитать и объединить правила; не затирать существующие инструкции вслепую. Пути handoff ниже предполагают его размещение в `docs/handoff-0.20/`.

## Источник истины и цель

Продолжается полный TACTIC 5.0 fork, исходная база передачи native 0.20. Сначала читать `docs/handoff-0.20/00_START_HERE.md` и проверять архитектуру по коду. Сохранить оригинальную модель SearchType/SObject/Schema/Pipeline, widget_config и команды. Не создавать параллельные Project/Task/Asset schemas, demo-backend или статический sidebar.

Имена native-версий не равны версии TACTIC. Первоначальный план Vite/TypeScript/PrimeVue не описывает текущий build: используются JavaScript Options API и `tools/native_ui/build.cjs`.

## Данные и изменения

- Работать на ветке и отдельной тестовой базе/репозитории файлов. Не инициализировать и не мигрировать рабочий local_data без прямого задания.
- Не удалять legacy UI directories: серверные команды и строковые class paths ещё от них зависят. Старые import paths сохранять при переносе классов.
- Не отключать авторизацию, CSRF, лицензирование, gates записи или hooks ради теста. Signature isolation допустима только явным тестовым runner; её успех не доказывает подпись.
- .runtime, local_data, profiles, active configs, sessions, tickets, passwords, raw worker logs и реальные payload не коммитить и не упаковывать. Файлы шрифтов не включать в выдачу.

## UI и конфигурации

- Table, CellEdit, EditWdg, TabWdg и CustomLayout — разные контракты. Чтение настроек не означает полный перенос поведения класса.
- Сохранять независимые lookup handler/options, precedence, пустой view, повторные элементы и unknown XML. Использовать targeted changes; не сериализовать исходный XML через неполную ConfigModel проекцию.
- `values` — исходные значения; `cells` — display; draft — несохранённые правки. Не записывать formatted display обратно.
- Apply в ячейке не сохраняет; Save Changes — один original EditMultipleCmd / update_multi, сначала валидация всего пакета. Сохранять defaults, sibling values и custom actions либо явно отказывать неподдержанному контракту.
- Проверять root App, nested WidgetHost, восстановленный state и context menu. Не подменять неизвестный widget случайной таблицей.
- Компактный UI без повторных hero headers. Не возвращать россыпь постоянных кнопок; меню и dirty save-strip сохранять.
- UI preferences — исходный WidgetSettings с отдельными native keys; не localStorage. Unsaved SObject draft не сохранять как preference.

## Backend и кластер

- Использовать исходный request context и Command/Transaction. RLock/Container/stub/active_target нельзя убирать без доказанной изоляции.
- Новый route проверить в API dispatcher, method/CSRF policy, service, traces и cluster read allowlist. POST /query балансируется; название другого endpoint не делает его read-only.
- Читатели не являются SQL read-only ролями. Потеря HTTP-ответа не допускает автоматический повтор write. Gateway не обещает HA/exactly-once.
- Server-defined trusted script/layout — не код произвольного клиента. Run сохранённого Python требует отдельного gate и является привилегированным execution, не sandbox.

## Build, тесты и поставка

- Не править только generated `src/tactic/ui_api/web/app.js`. Изменять SFC/API, обновлять явный build список и пересобирать.
- В корне остаются START_TACTIC.bat, SETUP_ENV.bat, MANAGE_TACTIC.bat. Старые имена в исторических README не восстанавливать как новые wrappers.
- До изменения выполнить релевантный baseline; добавить regression по исходному legacy-поведению. Команды и scope — `04_TESTING_AND_RELEASE.md`.
- Не складывать прошлые test counts как текущие. Отличать unit, mocked fixtures, original TACTIC/SQLite, browser bridge и настоящий браузер/Windows/PostgreSQL.
- Каждый новый отчёт содержит commit/архив, конфигурацию, exact команды, результаты и ограничения. Статический индекс и screenshots не называют full parity.
- Сохранять commit/checkpoint до долгого теста. Релиз: полный diff, built assets, актуальный readiness, manifest/hash/CRC. Не переименовывать предыдущий архив в новую версию при неудаче.
