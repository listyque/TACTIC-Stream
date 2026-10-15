---
group: Guide
icon: table
order: 94
---
# Каталог виджетов Table View

[Table View / Columns Editor](table_view.ru.md) — Обновление 14 октября: текущие 45 имён/21 адаптированный класс ТХ, действия и общий редактор перенесены. Ниже — исходный аудит legacy и прежние примеры; полная legacy-готовность не заявляется.


> Виджеты сгруппированы по назначению, готовности и состоянию исходника. Перенос начинается с воспроизводимого сценария.

## Правило переноса

Сначала изучаем исходник, наследование и вызывающие места; готовим тестовый XML и данные; снимаем legacy/ТХ и ТС при одинаковой теме, языке, масштабе и размере; описываем параметры, действия, права и ограничения; проверяем и переносим. Явно недописанные классы не переносим. TODO, известный баг или pass у alias сами по себе не делают виджет недописанным.

## Статусы

14 классов имеют рабочий базовый сценарий; HiddenRow работает только в журнале транзакций. 134 класса пока не подключены. Полная готовность этих классов не заявляется. TextWdg — один совместимый input alias. 43 pyasm.prod уже исключены; SnapshotServerElementWdg теперь исключён как явная заглушка. PlaceHolderElementWdg — намеренно пустая служебная ячейка.

[ Примеры XML и скриншоты ](table_widget_examples.ru.md)

## Первые проверяемые шаги

Теперь закрыт блок отображения Array/XML/JSON/SnapshotVersion; inline XML/JSON edit ещё не готов. Все упоминания в widget configs входят в отдельный рабочий чеклист. Полоса TaskCompletionWdg соответствует текущему TacticCompletionCell ТХ на примере 0/25/75/100%. Далее: выравнивание Format, сценарии файлов/metadata/details, связи и вложенные таблицы, затем более сложные actions/layout. Каждая следующая задача требует своего эталона и примера; реализуем все упомянутые в конфигах классы, кроме согласованных исключений и явно недописанных исходников.

## Проверка исходника

`tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` (строки 177–178) содержит только pass и наследует общий BaseTableElementWdg: не переносим. `ExplorerTableElementWdg` тоже содержит pass, но наследует реализацию ExplorerElementWdg: это alias, его не исключаем по этому признаку. В исходном каталоге explorer указан как ExploreElementWdg — такого класса нет. `SpreadsheetElementWdg` считает накопительный итог по column/format; это не полноценный spreadsheet editor.

Все непроверенные классы остаются на этапе «нужен прогон исходника». Список не подтверждает, что оригинал работает. Form/Input/CellEdit и команды — отдельные контракты; общий inline edit и legacy bottom/group_bottom/total_summary пока не готовы.

## Значения и форматирование (37)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.custom_info_wdg.CustomInfoWdg` | Не подключён |
| `pyasm.widget.dependency_wdg.DependencyLink` | Не подключён |
| `pyasm.widget.input_wdg.TextWdg` | Совместимый alias |
| `pyasm.widget.tab_wdg.CustomXmlWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.ArrayTableElementWdg` | Частично |
| `pyasm.widget.table_element_wdg.AuxDataWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.CheckTableElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.CheckboxColWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.DateTimeWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.DateWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.DateYearTimeWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.DynamicTableElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.EditCheckboxWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.ExpandableTextWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.NameWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.SearchTypeElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.SimpleInfoWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.SimpleTableElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.SubmissionLinkTableElement` | Не подключён |
| `pyasm.widget.table_element_wdg.UpdateWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.WikiElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.XmlWdg` | Частично |
| `tactic.ui.common.base_table_element_wdg.RawTableElementWdg` | Частично |
| `tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg` | Частично |
| `tactic.ui.common.base_table_element_wdg.WidgetTableElementWdg` | Не подключён |
| `tactic.ui.panel.freeform_layout_wdg.FreeFormElementWdg` | Не подключён |
| `tactic.ui.report.yearly_report_wdg.YearlyReportWdg` | Не подключён |
| `tactic.ui.table.format_element_wdg.FormatElementWdg` | Частично |
| `tactic.ui.table.html_element_wdg.HtmlElementWdg` | Не подключён |
| `tactic.ui.table.json_element_wdg.JsonElementWdg` | Частично |
| `tactic.ui.table.link_element_wdg.LinkElementWdg` | Частично |
| `tactic.ui.table.metadata_element_wdg.MetadataElementWdg` | Не подключён |
| `tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg` | Не подключён |
| `tactic.ui.table.subcontext_wdg.ProcessElementWdg` | Не подключён |
| `tactic.ui.table.subcontext_wdg.SubContextElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.TemplateElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.TypeTableElementWdg` | Не подключён |

## Вычисления и итоги (8)

| Класс | Статус |
| --- | --- |
| `tactic.ui.table.expression_element_wdg.ExpressionElementWdg` | Частично |
| `tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg` | Частично |
| `tactic.ui.table.python_element_wdg.PythonElementWdg` | Не подключён |
| `tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg` | Не подключён |
| `tactic.ui.table.spreadsheet_element_wdg.SpreadsheetElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.ExpressionIsCountZeroElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.ExpressionIsZeroElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.IndirectMappedDisplayLabelWdg` | Не подключён |

## Задачи и показатели (26)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.parallel_status.ParallelStatusEditWdg` | Не подключён |
| `pyasm.widget.parallel_status.ParallelStatusWdg` | Не подключён |
| `pyasm.widget.serial_status.SerialStatusWdg` | Не подключён |
| `pyasm.widget.serial_status.SimpleStatusWdg` | Не подключён |
| `pyasm.widget.statistic_wdg.CalendarBarWdg` | Не подключён |
| `pyasm.widget.statistic_wdg.TaskCompletionWdg` | Не подключён |
| `pyasm.widget.statistic_wdg.TaskGroupCompletionWdg` | Не подключён |
| `pyasm.widget.task_wdg.SObjectTaskTableElement` | Не подключён |
| `pyasm.widget.task_wdg.TaskParentSpacingTableElement` | Не подключён |
| `pyasm.widget.task_wdg.TaskWarningTableElement` | Не подключён |
| `tactic.ui.report.task_status_report_wdg.ValueBarReportWdg` | Не подключён |
| `tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg` | Не подключён |
| `tactic.ui.table.sobject_detail_wdg.TaskDetailPanelElementWdg` | Не подключён |
| `tactic.ui.table.statistic_wdg.MilestoneCompletionWdg` | Не подключён |
| `tactic.ui.table.statistic_wdg.TaskCompletionWdg` | Частично |
| `tactic.ui.table.statistic_wdg.TaskDaysDueElementWdg` | Не подключён |
| `tactic.ui.table.statistic_wdg.TaskGroupCompletionWdg` | Не подключён |
| `tactic.ui.table.task_element_wdg.RelatedTaskWdg` | Не подключён |
| `tactic.ui.table.task_element_wdg.TaskElementWdg` | Частично |
| `tactic.ui.table.task_element_wdg.TaskSummaryElementWdg` | Не подключён |
| `tactic.ui.table.task_element_wdg.WorkElementWdg` | Не подключён |
| `tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg` | Не подключён |
| `tactic.ui.tools.review_wdg.ReviewTaskElementWdg` | Не подключён |
| `tactic.ui.widget.misc_input_wdg.SObjectStatusElementWdg` | Не подключён |
| `tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg` | Не подключён |
| `tactic.ui.widget.overlay_stats_wdg.OverlayStatsWdg` | Не подключён |

## Календарь и сроки (12)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.gantt_wdg.CheckinHistoryGanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.DynGanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.GanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.ResourceUsageGanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.SObjectTaskGanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.ScheduleGanttWdg` | Не подключён |
| `pyasm.widget.gantt_wdg.StatusHistoryGanttWdg` | Не подключён |
| `pyasm.widget.timecard_wdg.TimecardInfoTableElement` | Не подключён |
| `pyasm.widget.timecard_wdg.WeekTableElement` | Не подключён |
| `tactic.ui.gantt.gantt_wdg.GanttTableElementWdg` | Не подключён |
| `tactic.ui.table.gantt_element_wdg.GanttElementWdg` | Не подключён |
| `tactic.ui.table.projected_schedule_wdg.ProjectedCompletionWdg` | Не подключён |

## Файлы и версии (21)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.dependency_wdg.DependencyThumbWdg` | Не подключён |
| `pyasm.widget.file_wdg.FileInfoWdg` | Не подключён |
| `pyasm.widget.file_wdg.ThumbWdg` | Частично |
| `pyasm.widget.naming_wdg.NamingElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.FileAppendLinkTableElement` | Не подключён |
| `pyasm.widget.table_element_wdg.PublishTableElement` | Не подключён |
| `pyasm.widget.table_element_wdg.RenderLinkTableElement` | Не подключён |
| `tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg` | Не подключён |
| `tactic.ui.cgapp.publish_element_wdg.PublishElementWdg` | Не подключён |
| `tactic.ui.cgapp.version_wdg.CurrentVersionContextWdg` | Не подключён |
| `tactic.ui.cgapp.version_wdg.UnknownVersionContextWdg` | Не подключён |
| `tactic.ui.table.snapshot_element_wdg.SnapshotFileElementWdg` | Не подключён |
| `tactic.ui.table.snapshot_element_wdg.SnapshotLockedElementWdg` | Не подключён |
| `tactic.ui.table.snapshot_element_wdg.SnapshotMetadataElementWdg` | Не подключён |
| `tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` | Недописан в legacy |
| `tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg` | Частично |
| `tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.CheckinButtonElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.GeneralPublishElementWdg` | Не подключён |
| `tactic.ui.tools.custom_layout_edit_wdg.AddImageElementWdg` | Не подключён |

## Заметки и общение (7)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.annotate_wdg.AnnotateLink` | Не подключён |
| `pyasm.widget.discussion_wdg.DiscussionWdg` | Не подключён |
| `tactic.ui.app.message_wdg.MessageTableElementWdg` | Не подключён |
| `tactic.ui.app.note_wdg.NoteTableElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg` | Не подключён |
| `tactic.ui.table.table_element_wdg.RecipientElementWdg` | Не подключён |
| `tactic.ui.widget.discussion_wdg.DiscussionElementWdg` | Частично |

## Связи и вложенные объекты (11)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.sobject_browser_wdg.SObjectConnectionDetailElement` | Не подключён |
| `pyasm.widget.sobject_browser_wdg.SObjectConnectionElement` | Не подключён |
| `pyasm.widget.table_element_wdg.GroupTableElement` | Не подключён |
| `pyasm.widget.table_element_wdg.SObjectAttachTableElement` | Не подключён |
| `pyasm.widget.table_element_wdg.SObjectExplorerWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.SObjectLinkElementWdg` | Не подключён |
| `tactic.ui.table.explorer_wdg.ExplorerElementWdg` | Не подключён |
| `tactic.ui.table.explorer_wdg.ExplorerTableElementWdg` | Не подключён |
| `tactic.ui.table.foreign_key_element_wdg.ForeignKeyElementWdg` | Не подключён |
| `tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg` | Не подключён |
| `tactic.ui.table.related_element_wdg.RelatedElementWdg` | Не подключён |

## Компоновка и действия (16)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.table_element_wdg.HiddenRowToggleWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.PlaceHolderElementWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.TableAddWdg` | Не подключён |
| `pyasm.widget.table_element_wdg.WrapperTableElementWdg` | Не подключён |
| `tactic.ui.panel.document_wdg.DocumentItemWdg` | Не подключён |
| `tactic.ui.panel.layout_wdg.RowSelectWdg` | Не подключён |
| `tactic.ui.table.button_wdg.ButtonElementWdg` | Не подключён |
| `tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg` | Не подключён |
| `tactic.ui.table.custom_layout_element_wdg.FreeFormLayoutElementWdg` | Не подключён |
| `tactic.ui.table.custom_layout_element_wdg.LayoutElementWdg` | Не подключён |
| `tactic.ui.table.delete_element_wdg.DeleteElementWdg` | Не подключён |
| `tactic.ui.table.drop_element_wdg.DropElementWdg` | Не подключён |
| `tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg` | Частично |
| `tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg` | Не подключён |
| `tactic.ui.tools.pipeline_wdg.PipelineDocumentItemWdg` | Не подключён |
| `tactic.ui.widget.button_new_wdg.IconButtonElementWdg` | Не подключён |

## Администрирование и настройки (13)

| Класс | Статус |
| --- | --- |
| `pyasm.widget.clipboard_wdg.ClipboardHistoryElement` | Не подключён |
| `pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg` | Не подключён |
| `pyasm.widget.project_wdg.ProjectClassWdg` | Не подключён |
| `pyasm.widget.project_wdg.ProjectSummaryWdg` | Не подключён |
| `pyasm.widget.project_wdg.ProjectWdg` | Не подключён |
| `tactic.ui.app.search_type_element_wdg.SearchTypeHasTableElementWdg` | Не подключён |
| `tactic.ui.input.process_group_select_wdg.LoginTableElementWdg` | Не подключён |
| `tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg` | Не подключён |
| `tactic.ui.startup.security_wdg.SecurityCheckboxElementWdg` | Не подключён |
| `tactic.ui.table.preference_wdg.PreferenceDescriptionWdg` | Не подключён |
| `tactic.ui.table.preference_wdg.PreferenceEditWdg` | Не подключён |
| `tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg` | Не подключён |
| `tactic.ui.table.project_wdg.ProjectWdg` | Не подключён |

## Исключённый production (43)

| Класс | Статус |
| --- | --- |
| `pyasm.prod.render.qube_render_submit.QubeState` | Исключён ранее |
| `pyasm.prod.web.asset_data_wdg.AssetDataLink` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.AssetInfoWdg` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.CondensedAssetInfoWdg` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.CondensedShotInfoWdg` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.GeneralInfoWdg` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.ShotInfoWdg` | Исключён ранее |
| `pyasm.prod.web.asset_info_wdg.SubmissionInfoWdg` | Исключён ранее |
| `pyasm.prod.web.camera_info_wdg.CameraInfoWdg` | Исключён ранее |
| `pyasm.prod.web.composite_wdg.CompLayerTableElementWdg` | Исключён ранее |
| `pyasm.prod.web.composite_wdg.ExploreTableElementWdg` | Исключён ранее |
| `pyasm.prod.web.composite_wdg.LayerTableElementWdg` | Исключён ранее |
| `pyasm.prod.web.frame_info_wdg.FrameRangeWdg` | Исключён ранее |
| `pyasm.prod.web.frame_info_wdg.IFrameLink` | Исключён ранее |
| `pyasm.prod.web.layout_summary_wdg.AssetsInShotWdg` | Исключён ранее |
| `pyasm.prod.web.layout_summary_wdg.AssignedShotWdg` | Исключён ранее |
| `pyasm.prod.web.layout_summary_wdg.TasksInSObjectWdg` | Исключён ранее |
| `pyasm.prod.web.prod_input_wdg.AssetCheckboxWdg` | Исключён ранее |
| `pyasm.prod.web.prod_input_wdg.LayerCheckboxWdg` | Исключён ранее |
| `pyasm.prod.web.prod_input_wdg.LevelCheckboxWdg` | Исключён ранее |
| `pyasm.prod.web.prod_input_wdg.SObjectCheckboxWdg` | Исключён ранее |
| `pyasm.prod.web.prod_input_wdg.ShotCheckboxWdg` | Исключён ранее |
| `pyasm.prod.web.prod_table_element_wdg.BinTableElementWdg` | Исключён ранее |
| `pyasm.prod.web.prod_table_element_wdg.InstancePublishWdg` | Исключён ранее |
| `pyasm.prod.web.prod_table_element_wdg.ThumbPublishWdg` | Исключён ранее |
| `pyasm.prod.web.prod_wdg.SnapshotInfoWdg` | Исключён ранее |
| `pyasm.prod.web.prod_wdg.SnapshotLabelWdg` | Исключён ранее |
| `pyasm.prod.web.render_wdg.RenderTableElementWdg` | Исключён ранее |
| `pyasm.prod.web.shot_instance_adder_wdg.NumSequenceInstanceWdg` | Исключён ранее |
| `pyasm.prod.web.shot_instance_adder_wdg.NumShotInstancesWdg` | Исключён ранее |
| `pyasm.prod.web.shot_instance_adder_wdg.NumTasksWdg` | Исключён ранее |
| `pyasm.prod.web.sobject_checkin_wdg.CheckboxCheckinWdg` | Исключён ранее |
| `pyasm.prod.web.sobject_checkin_wdg.DescriptionCheckinWdg` | Исключён ранее |
| `pyasm.prod.web.sobject_planner_wdg.NumSObjectInstancesWdg` | Исключён ранее |
| `pyasm.prod.web.statistics_wdg.EpisodeCompletionWdg` | Исключён ранее |
| `pyasm.prod.web.statistics_wdg.FrameCompletionWdg` | Исключён ранее |
| `pyasm.prod.web.submission_wdg.DailiesLink` | Исключён ранее |
| `pyasm.prod.web.submission_wdg.SubmissionDataTableElement` | Исключён ранее |
| `pyasm.prod.web.texture_wdg.TextureAddSourceElementWdg` | Исключён ранее |
| `pyasm.prod.web.texture_wdg.TextureSourceElementWdg` | Исключён ранее |
| `pyasm.prod.web.version_wdg.LatestVersionContextWdg` | Исключён ранее |
| `pyasm.prod.web.version_wdg.LatestVersionWdg` | Исключён ранее |
| `pyasm.prod.web.version_wdg.SessionVersionWdg` | Исключён ранее |

## Права и границы проверки

Configured Table View доступен admin. Сервер проверяет проект/тип объектов и разрешённые опции. Неизвестные классы/options/actions не исполняются и не становятся «готовыми» от наличия Python файла. Примеры проверены native XML parser и describe_cell без БД; скриншоты Vue сняты с тестовыми типизированными значениями. Native ТХ снимался отдельно для Completion. Полный старый CGI runtime и остальные классы пока не запускались.
