# Карта изменения исходников 0.3

## Оригинальный код, не замена семантики

- `tactic.ui.tools.pipeline_wdg.ProcessInfoCmd` → `tactic.core.process_commands.ProcessInfoCmd`.
- `tactic.ui.tools.pipeline_wdg.NewProcessInfoCmd` → `tactic.core.process_commands.NewProcessInfoCmd`.
- Старые пути реэкспортируют классы. `PipelineSaveCbk` пользуется core-импортом.
- Ограниченные original hierarchy/progress/status handlers: `ui_api/graph_service.py`.
- `Login`, `Note.create`, `CreateProjectCmd`, `NativeEditCmd`, `Schema`, `Snapshot` остаются источником бизнес-операций.

## Новые сервисы и их native-представление

| Сервер | Vue | Что не заявляется |
|---|---|---|
| `graph_model.py`, `graph_service.py` | `GraphEditor.vue` | Все script/custom-node свойства и live workflow parity |
| `view_edits.py`, `view_service.py` | `ViewDesigner.vue` | Полный произвольный layout/JS designer |
| `extended_backend.py` | `ConfiguredTable.vue`, `TaskTimeline.vue` | Общая expression language, resource Gantt, бесконечное дерево |
| `record_service.py`, `file_payload.py` | `RecordInspector.vue` | Полный чат, внешнее storage, resumable upload |
| `admin_service.py` | `AdminPanel.vue` | Полная legacy/system/plugin админка |

Handler registry связывает **типы виджетов** с реализациями; это не hard-coded sidebar.
Sidebar и view order остаются продуктом WidgetConfigView/SidebarConfig исходного TACTIC.

## Локальный запуск

`tools/local/launch.py` настраивает пути и запускает original FirstRunInit/CherryPyStartup.
`setup_env.ps1` ставит приватное окружение. Никаких импортов fixture в production.
Windows/runtime/SQLite-startup не считаются проверенными по HTTP-тестам fixtures.

## Незавершённые области плана

Полное отделение presentation зависимостей, script/plugin/admin, general expression/filter
engine UI, instance-link editing, all original task widgets, notifications/chat, review player,
legacy custom layouts, full Gantt/resource calculations, обычные роли и multiworker.
Каждый неизвестный handler видим как неподдержанный, а не замещается фиктивной таблицей.
