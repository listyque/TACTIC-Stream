# Продолжение 0.3

Новые изменения: [SOURCE_MAP_03.md](0.3/SOURCE_MAP_03.md). Ниже сохранена карта базового переноса 0.2.

# Карта фактических изменений

| Исходная точка | Новый файл | Совместимость |
|---|---|---|
| `pyasm/widget/widget_config.py` | `tactic/core/widget_config.py` | Исходный публичный модуль реэкспортирует resolver и test command |
| `tactic/ui/panel/panel_wdg.py` roots / loader / schema XML | `tactic/core/sidebar_config.py` | Старые виджеты делегируют этим методам, не используют вторую копию resolver |
| `pyasm/web/web_init.py` бизнес-регистрации | `tactic/core/bootstrap.py` | WebInit сохраняет sidebar-invalidation, вызывает CoreInit; старые trigger class paths доступны |
| `tactic/ui/panel/edit_cmd.py` | `tactic/core/edit_commands.py` | Реэкспорт EditCmd/EditMultipleCmd |
| DatabaseAction для нового JSON-входа | `tactic/core/native_edit.py` | Legacy DatabaseAction не изменён; только явно заданные plain values адаптируются |
| `tactic/ui/app/search_type_creator_wdg.py` SearchTypeCreatorCmd | `tactic/core/schema_commands.py` | Старый модуль реэкспортирует; core API/create_project_cmd импортируют новую точку |
| `tactic/ui/tools/pipeline_wdg.py` PipelineSaveCbk | `tactic/core/pipeline_commands.py` | Старый модуль реэкспортирует; свойства процессов частично остаются legacy-зависимостью |
| `tactic/ui/startup/security_wdg.py` UserAssignCbk | `tactic/core/security_commands.py` | Старый модуль реэкспортирует |
| Новый формат метаданных без HTML | `tactic/core/config_model.py` | Источник истины — прежние XML/DB configs |
| Проверки link/element | `tactic/core/field_policy.py` | Сохранены категории/формы ключей; только admin runtime в этом форке |
| Native JSON entry | `tactic/ui_api/` | Строгие конечные операции; нет клиентского произвольного execute_cmd |
| CherryPyStartup.execute | `tactic/ui_api/mount.py` | Переключает обычные HTML pages; не перехватывает Api/REST/UploadServer |
| Новое отображение | `frontend/src/*.vue` | Предкомпилированная сборка `src/tactic/ui_api/web/` |

## Дифференциальные тесты и их границы

`test_original_resolver.py` использует реальный перемещённый resolver и реальные XML-файлы из поставки, не заменяет их тестовой реализацией. `test_source_commands.py` проверяет настоящий SidebarConfig и классы команд с заменёнными DB/Web collaborators. Unit tests не подтверждают побочные эффекты PostgreSQL, triggers, DDL и файлового репозитория.

`run_http.py` делает реальные HTTP-запросы к bundled CherryPy. `run_browser.py` проверяет production Vue bundle, но в данной среде работал с `--bridge`: навигация в Chromium заблокирована политикой. База обеих проверок — изолированная test fixture.

## Намеренно не удалено

Legacy UI и его JS остаются в source fork для непренесённых серверных зависимостей и возврата к старому интерфейсу. Новый браузерный путь их не загружает. Удаление всего каталога `tactic/ui` сейчас сломает часть серверных операций и не является допустимым завершающим действием.

Список native renderer kinds в `admin-targets.json` не равен полному покрытию виджетов: `table` означает наличие общего рендера, но специальные ячейки/action handlers могут быть непренесены. `pipeline`, `schema`, `config-editor` — частичные редакторы, а не доказанная полная замена одноимённых старых инструментов.
