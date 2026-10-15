# Source map — native UI 0.5

Основа — весь source fork 0.4, не демонстрационный проект. Штатные меню и views остаются конфигурационными. Новые schema tables, новое хранилище чата и иной workflow-engine не создавались.

## Соответствие

| Исходник / контракт | Сервер 0.5 | Native Vue | Сохранённый смысл / граница |
|---|---|---|---|
| `tactic/ui/app/message_wdg.py: SubscriptionWdg`, `SubscriptionBarWdg` | `core/messaging.py`, `ui_api/message_service.py` | `MessageCenter.vue` | Собственные subscription, message join, category, last_cleared; show_unsubscribe default false для SubscriptionWdg |
| `ChatWdg`, `ChatSessionWdg` | finite `/chats`, `/message-history`, `/message-send` | `MessageCenter.vue`, `MessageContent.vue` | Исходные key/options, message_log история; никаких `get_widget` |
| `ChatCmd` | `core/message_commands.py` + старый reexport | Picker / compose в MessageCenter | Оригинальные tables/welcome; точный participant set вместо ошибочного overlap; новые строки project-scoped |
| `ApiXMLRPC.log_message` | Исходный метод через TacticServerStub и `_write` | Compose | SQLite history commit bugfix; category в логе; key как данные Search |
| `SObject._add_message` + subscribe API | `object_message_key`, `/record-subscription` | `SubscriptionPanel.vue` в RecordInspector | Task/note/snapshot используют parent message key; включение message_event остаётся настройкой TACTIC |
| `FormatMessageWdg` | `message_content` | `MessageContent.vue` | Text / SObject changes / progress как данные; HTML/JS не исполняются |
| `MyNotificationLogWdg` | target_spec + mandatory notification scope | `ConfiguredTable` | Исходная log-таблица с hidden recipient/project фильтром, не unrestricted alias |
| `NotificationLogFilterWdg.alter_search` | `core/notification_filters.py:NotificationLogScope` + alias | — | Тело метода неизменно; portable AST hash из baseline 0.4 |
| `RecipientElementWdg` / `WikiElementWdg` email view | batch recipient provider, safe read-only text | `ConfiguredTable` | Только исходные notification_login, safe plain-text email, не SMTP engine |
| Исходный Search + GanttElement config | выделенный `ConfigBackend._query_search`; `TimelineService`; `core/timeline_model.py` | `TaskTimeline.vue` | Original view/user/relationship/project filters + date window; не новый ORM |
| Original form / NativeEditCmd | Прежний `/record` | App `dates` | Server form разрешения, expected revision, оба поля в одной операции; устаревший Gantt-row не перезаписывает новую строку |

## Явные отличия от старого UI

1. `last_cleared` подписан как отметка показанного, не «прочитал»/«доставлено». Это соответствует возможностям исходного хранения.
2. В переписке identical text не заменяет log ID: одинаковые сообщения не теряются.
3. Global legacy chats без project_code оставлены их членам; новые чаты имеют project. Существующие записи не переписываются массово.
4. `ChatCmd` проверяет всех выбранных получателей и exact membership, не первый чат с пересекающимся получателем. Ограничения не обходятся при возврате retry cache.
5. `Subscription.get_by_message_code` использует current login, а не неопределённую переменную. `unsubscribe` исправляет опечатку и отсутствие guard.
6. Gantt загружает отдельные страницы **периода**, не ограничивается таблицей; NULL end интерпретируется однодневным marker и это явно показано. Это дневной viewer, не scheduler.
7. Дневные границы в original Select не проходят timestamp/TZLOCAL-rebasing: строго проверенные identifier/date и Sql.quote. Existing saved filters продолжают original normalization.
8. «Мои уведомления» нельзя превратить в общий log через override search_type/view или прямой record key. Фильтр остаётся server-only.

## Проверки

- `test_messages_05.py`: 68 unit tests, включая production message service, exact ChatCmd, actual extracted SQLite API body, настоящий Select и notification filtering; DB/environment/transaction collaborators изолированы.
- `test_timeline_05.py`: 26 tests — boundary/NULL, множество интервалов, фильтры, closed fields, paging 320 rows, calendar literals + TZLOCAL.
- `run_http_05.py`: 45 scenarios, real bundled CherryPy с test backend.
- `run_browser_05.py`: 27 scenarios, production Vue; explicit bridge limitation записана.
- Старые 384 unit, 91 HTTP и 61 browser повторяются; новый validation runner создаёт чистый fixture-процесс на каждый HTTP/browser-набор.
- AST provenance относится **к одному перенесённому методу**, не к полной эквивалентности TACTIC. Intentional ChatCmd/log_message исправления не объявляются побайтно одинаковыми со старым алгоритмом.

## Файлы продолжения

Production:
`src/tactic/core/{messaging,message_commands,notification_filters,timeline_model}.py`,
`src/tactic/ui_api/{message_service,timeline_service,extended_backend,config_backend,api}.py`,
`frontend/src/components/{MessageCenter,MessageContent,SubscriptionPanel,TaskTimeline}.vue`,
`frontend/src/App.vue`, `RecordInspector.vue` и styles.

Fixtures и validation находятся только в `tests/native_ui`; `serve_fixture.py` не является launcher сервера TACTIC. Production mount использует ExtendedBackend и не импортирует fixture_05. Windows launcher / dependency manifests в этом этапе не изменены.

## Открытая работа

Прежний список specialised handlers остаётся открытым. Следующие значимые области: runtime-проверка полного backend на обновлённой реальной тестовой БД, обычные роли и межпроцессные конфликты, widget/action families с произвольными expressions, plugin/script/admin panels, review, resumable check-in, resource/dependency Gantt. Не удалять legacy UI packages, пока замыкание серверных импортов и сценариев не проверено.
