# 0.15 — происхождение изменений

| Исходная логика | Изменение |
|---|---|
| `tactic/ui/app/page_header_wdg.py` / ProjectCreateWdg и `tactic/command/create_project_cmd.py` | `ProjectWizard.vue` — интерфейс шагов; `ProjectService` — ограниченная проверка/создание; `NativeCreateProjectCmd` наследует оригинальный lifecycle, не заменяет его новой моделью |
| `CreateProjectCmd.upgrade`, `import_default_side_bar` | Для новой SQLite согласуются реальные registry table names, используется original Upgrade через SQLite-адаптер, проверяется структура, затем оригинальный sidebar в правильном проекте |
| `pyasm/web/widget.py` / WidgetSettings | Оригинальное `sthpw/wdg_settings`, scoped by user/project; исправлен site/project/login request-cache key; storage/API сохранены |
| `tactic/ui/app/search_wdg.py` / persistent last search | Сохранение query-state в том же WidgetSettings, отдельные namespaced JSON keys; `set_persistent_search=false` соблюдается; не переписывает legacy-формат |
| `tactic/core/widget_containers.py` / исходный TabWdg resolver | Исходные дети/права не менялись; `ConfiguredTabs` сохраняет персональный порядок/закрытие/selected/titles через UiStateService по имёнам детей |
| `config/widget_config` / сохранённые поиски и view designer | Прежний путь сохраняется; UI-предпочтения не записывают туда новый независимый дубль конфигурации |
| `App.vue`, `WidgetTable.vue`, `ConfiguredTable.vue` | Удаление повторного заголовка; query/geometry/workspace вместо localStorage; сохранение перед switch/logout; открытие созданного проекта |
| `SidebarNode.vue`, `TaskTimeline.vue` | DB-параметры раскрытия папок, периода/масштаба; SObject/результаты/черновики не сериализуются |
| `tools/local/cluster_gateway.py` | GET ui-state разрешён в read-balancing; PATCH и create проходят старую ведущую очередь |

Контракт UI-state: строгие scope/target/value/revision; target разрешается через исходный sidebar/config и проверку прав; пользователь/проект не выбираются произвольными полями payload. Несовместимое сохранение даёт предупреждение/конфликт. Ключи native не объявляются идентичными всем legacy WidgetSettings keys.

## Проверенные границы

Два исходных типа проекта default/simple. Структура/настройки/предпросмотр создаются реально; импорт зарегистрированных шаблонов/preview/theme не скрыт за обещанием полной поддержки. DDL и внешний filesystem — не единая атомарная транзакция. Неудачный create автоматически не повторяется и не удаляет остатки.

Модульные тесты валидируют лимиты, типы, protected/hidden дети, поля и отсутствие черновиков; JS-тесты исполняют реальные методы координатора и мастера. Сквозные тесты — настоящая SQLite, исходные команды и три TACTIC-процесса. Статусы всех завершённых наборов берутся из JSON/логов, не из прежних README.
