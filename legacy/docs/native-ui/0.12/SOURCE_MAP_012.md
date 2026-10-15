# 0.12 — источник → нативная реализация

| Исходный механизм | Реализация / изменение | Проверка |
|---|---|---|
| `tactic/ui/panel/layout_wdg.py:CellEditWdg.init` | `tactic/core/cell_edit_config.py`, `CellConfigModel`, `/cell-editor` | Исполненный original init-prefix vs native layers; original DB edit_item |
| `tactic/core/edit_commands.py:EditCmd._get_action_handlers` | Отдельный save_config, тот же actual NativeEditCmd action lookup | Original NonEmptyAction, defaults, action_options |
| `tactic/core/edit_commands.py:EditMultipleCmd.execute` | Минимальная фабрика child command; NativeTableEditMultipleCmd | Пакет 2 rows/3 cells, реальный event update_multi; ошибка второй строки откатывает первую |
| `pyasm/search/search.py:SObject.set_value` | Опциональный allow_none; default поведения не меняется | Права/prevalidation/nullable boolean/NOT NULL и actual SQLite NULL |
| `tactic/ui/input/process_group_select_wdg.py:LoginTableElementWdg` | `cell_value_service.py`, пакет login→display_name | Сохранение сырого login |
| `tactic/ui/widget/misc_input_wdg.py:TaskStatusElementWdg.handle_td` | Исходный порядок task/process pipeline colors | Явный handler, безопасный CSS, нет guessing по названию |
| `pyasm/widget/input_wdg.py:ColorWdg` | Цветовой образец + сырой код | Отдельное значение для сохранения |
| `pyasm/widget/file_wdg.py:ThumbWdg.preprocess` | `thumbnail_service.py`, каскад actual snapshots/files | Прямые selection tests; original PNG check-in, HTTP file auth и browser naturalWidth |
| `TableLayoutWdg`/table client | `ConfiguredTable.vue`, разные raw/display/draft, explicit batch save | 15 JS + HTTP + browser; нет immediate PATCH |
| Исходная метамодель sidebar/Table/Edit/Tab | Не заменяется новым меню или таблицами | 80 XML/487 views; old Globals/forms/graphs actual regression |

Пределы: обычные existing rows в буфере; inline insert/пастинг/fill/custom complex save hooks пока отдельно; geometry локальная; ThumbWdg не генерирует новые превью/не исполняет custom callbacks. Новая тема меняет CSS, не configuration definitions. Нет универсального eval/get_widget endpoint.
