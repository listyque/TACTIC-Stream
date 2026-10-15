# Карта переноса 0.4

Одна исходная TACTIC база и сервер, config-driven представления. Новый UI не является самостоятельным task manager.

| Исходник/семантика | Сервер 0.4 | Vue |
|---|---|---|
| GeneralFilterWdg, FilterData, Search/Select | core/search_filters.py, filter_data.py, query_model.py; config_backend/view_service | AdvancedFilter, FilterGroup |
| Schema + SObject.get_related* | RecordService и проверенные related targets | RelationTree, RelationTreeRow |
| Schema instance + add_instance/remove_instance | RelationshipService | RelationshipEditor |
| Task.add_initial_tasks/TaskGenerator | TaskService; Task.resolve_initial_pipeline | TaskPanel |
| TaskStatusSelectWdg/ProcessInput/ProcessGroupSelect | core/task_choices.py, ExtendedBackend.form/prepare_form | ConfiguredForm/TaskPanel |
| SubContextAction + TaskDateAction | core/context_actions.py, NativeEditCmd | FieldInput/ConfiguredForm |
| WorkHoursElementAction + WorkHoursElementWdg config | WorkHourService/core/work_hours | WorkHoursPanel + configured table virtual field |
| SObject.retire/reactivate; original logs | HistoryService | HistoryPanel/record-state selector |

## Изменения алгоритмов не скрыты

Пять извлечённых методов сохраняют AST относительно входного 0.3 с двумя переименованиями class-symbol. В остальных местах новые validators/adapter отличия перечислены в README: типизированный буквальный поиск, guards SQL NULL/IN, безопасный FilterData, пустой SubContext, task pipeline resolution helper. Нельзя считать всё дерево автоматически эквивалентным по этой локальной проверке.

## Источники тестов

Тесты actual providers читают `src/config2/search_type/widget/sthpw/task-conf.xml`. `src/config/sthpw/sobject/task-conf.xml` — другой уровень схемы, не источник формы. SQL-builder тесты используют реальные Search/Select/SqliteImpl, но временную таблицу и подменённую metadata/DB-связь. Все HTTP mutations работают на явно помеченном fixture; доменные границы проверяются отдельно с production services и DB collaborators.

## Границы следующего этапа

Не закрыты general expression/related-search execution, arbitrary views/custom handlers, все роли, рабочие базы, полный DCC/check-in и асинхронные файловые операции. Требуется реальный DB прогон bootstrap/auth/form/write/trigger/workflow/check-in и Windows BAT. Не удалять legacy UI зависимостей до runtime-аудита. Старые отчёты сохранены по версиям.
