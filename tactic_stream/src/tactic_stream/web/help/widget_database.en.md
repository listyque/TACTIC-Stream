---
group: Guide
icon: table
order: 94
---
# Table View widget database

[Table View / Columns Editor](table_view.en.md) · [B07](table_widgets_b07.en.md)

Current as of 2026-10-19: the portable catalogue has **41 classes / 98 aliases**.
A scan of 239 shipped XML/CG entries without working databases finds 38 referenced
adapted classes, **36 pending**, 27 excluded `pyasm.prod` classes and 3 explicitly
unfinished originals. An adapter does not certify all original options/actions.

Next: relationships/nested rows → embedded notes/messages/tasks → configured
actions/layout → file operations → status/assignment → table Gantt/hours →
service cells and full B07 acceptance. Each group requires XML examples,
captures, permission checks and actual operations.

**The October 13–14 audit below is historical. Its counts/statuses are not the
current working checklist.** See B07 Help above for the current checkpoint.

> Widgets grouped by purpose, readiness and source condition. Migration starts with a reproducible scenario.

L02 adapters reuse existing panels; see B07 above for XML and explicit limits.

## Migration rule

Read the source, inheritance and callers first. Prepare test XML and data. Capture legacy/TH and Stream with the same theme, language, scale and size. Document options, actions, permissions and limitations, then verify and migrate. Clearly unfinished classes are excluded. A TODO, known bug or pass in an alias is not enough to declare a widget unfinished.

## Historical statuses — October 13–14

14 classes have a working basic scenario; HiddenRow only supports transaction details. 134 classes are not connected. Complete class parity is not claimed. TextWdg is one compatible input alias. 43 pyasm.prod classes were already excluded; SnapshotServerElementWdg is now excluded as an explicit stub. PlaceHolderElementWdg is an intentionally empty infrastructure cell.

[ XML examples and screenshots ](table_widget_examples.en.md)

## First verifiable steps

The Array/XML/JSON/SnapshotVersion display block is now implemented; inline XML/JSON editing remains unfinished. Every mention in widget configs enters a separate working checklist. The TaskCompletionWdg bar follows the current TH TacticCompletionCell for 0/25/75/100%. Next: Format alignment, files/metadata/details, relationships and nested tables, then complex actions/layout. Every next task needs its own reference and example; all classes mentioned in configs are in scope, except agreed exclusions and clearly unfinished source.

## Source review

`tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` (lines 177–178) contains only pass and directly inherits the generic BaseTableElementWdg: excluded. ExplorerTableElementWdg also contains pass, but inherits ExplorerElementWdg implementation: it is an alias, not an unfinished widget. The source explorer catalog uses the nonexistent name ExploreElementWdg. SpreadsheetElementWdg calculates a running total from column/format; it is not a full spreadsheet editor.

Unreviewed classes remain at the source-reproduction stage. This inventory does not prove that the original works. Form/Input/CellEdit and commands are separate contracts; general inline editing and legacy bottom/group_bottom/total_summary remain unavailable.

## Values and formatting (37)

| Class | Status |
| --- | --- |
| `pyasm.widget.custom_info_wdg.CustomInfoWdg` | Not connected |
| `pyasm.widget.dependency_wdg.DependencyLink` | Not connected |
| `pyasm.widget.input_wdg.TextWdg` | Input alias |
| `pyasm.widget.tab_wdg.CustomXmlWdg` | Not connected |
| `pyasm.widget.table_element_wdg.ArrayTableElementWdg` | Partial |
| `pyasm.widget.table_element_wdg.AuxDataWdg` | Not connected |
| `pyasm.widget.table_element_wdg.CheckTableElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.CheckboxColWdg` | Not connected |
| `pyasm.widget.table_element_wdg.DateTimeWdg` | Not connected |
| `pyasm.widget.table_element_wdg.DateWdg` | Not connected |
| `pyasm.widget.table_element_wdg.DateYearTimeWdg` | Not connected |
| `pyasm.widget.table_element_wdg.DynamicTableElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.EditCheckboxWdg` | Not connected |
| `pyasm.widget.table_element_wdg.ExpandableTextWdg` | Not connected |
| `pyasm.widget.table_element_wdg.NameWdg` | Not connected |
| `pyasm.widget.table_element_wdg.SearchTypeElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.SimpleInfoWdg` | Not connected |
| `pyasm.widget.table_element_wdg.SimpleTableElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.SubmissionLinkTableElement` | Not connected |
| `pyasm.widget.table_element_wdg.UpdateWdg` | Not connected |
| `pyasm.widget.table_element_wdg.WikiElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.XmlWdg` | Partial |
| `tactic.ui.common.base_table_element_wdg.RawTableElementWdg` | Partial |
| `tactic.ui.common.base_table_element_wdg.SimpleTableElementWdg` | Partial |
| `tactic.ui.common.base_table_element_wdg.WidgetTableElementWdg` | Not connected |
| `tactic.ui.panel.freeform_layout_wdg.FreeFormElementWdg` | Not connected |
| `tactic.ui.report.yearly_report_wdg.YearlyReportWdg` | Not connected |
| `tactic.ui.table.format_element_wdg.FormatElementWdg` | Partial |
| `tactic.ui.table.html_element_wdg.HtmlElementWdg` | Not connected |
| `tactic.ui.table.json_element_wdg.JsonElementWdg` | Partial |
| `tactic.ui.table.link_element_wdg.LinkElementWdg` | Partial |
| `tactic.ui.table.metadata_element_wdg.MetadataElementWdg` | Not connected |
| `tactic.ui.table.sobject_detail_wdg.SObjectDetailElementWdg` | Not connected |
| `tactic.ui.table.subcontext_wdg.ProcessElementWdg` | Not connected |
| `tactic.ui.table.subcontext_wdg.SubContextElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.TemplateElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.TypeTableElementWdg` | Not connected |

## Calculations and totals (8)

| Class | Status |
| --- | --- |
| `tactic.ui.table.expression_element_wdg.ExpressionElementWdg` | Partial |
| `tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg` | Partial |
| `tactic.ui.table.python_element_wdg.PythonElementWdg` | Not connected |
| `tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg` | Not connected |
| `tactic.ui.table.spreadsheet_element_wdg.SpreadsheetElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.ExpressionIsCountZeroElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.ExpressionIsZeroElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.IndirectMappedDisplayLabelWdg` | Not connected |

## Tasks and metrics (26)

| Class | Status |
| --- | --- |
| `pyasm.widget.parallel_status.ParallelStatusEditWdg` | Not connected |
| `pyasm.widget.parallel_status.ParallelStatusWdg` | Not connected |
| `pyasm.widget.serial_status.SerialStatusWdg` | Not connected |
| `pyasm.widget.serial_status.SimpleStatusWdg` | Not connected |
| `pyasm.widget.statistic_wdg.CalendarBarWdg` | Not connected |
| `pyasm.widget.statistic_wdg.TaskCompletionWdg` | Not connected |
| `pyasm.widget.statistic_wdg.TaskGroupCompletionWdg` | Not connected |
| `pyasm.widget.task_wdg.SObjectTaskTableElement` | Not connected |
| `pyasm.widget.task_wdg.TaskParentSpacingTableElement` | Not connected |
| `pyasm.widget.task_wdg.TaskWarningTableElement` | Not connected |
| `tactic.ui.report.task_status_report_wdg.ValueBarReportWdg` | Not connected |
| `tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg` | Not connected |
| `tactic.ui.table.sobject_detail_wdg.TaskDetailPanelElementWdg` | Not connected |
| `tactic.ui.table.statistic_wdg.MilestoneCompletionWdg` | Not connected |
| `tactic.ui.table.statistic_wdg.TaskCompletionWdg` | Partial |
| `tactic.ui.table.statistic_wdg.TaskDaysDueElementWdg` | Not connected |
| `tactic.ui.table.statistic_wdg.TaskGroupCompletionWdg` | Not connected |
| `tactic.ui.table.task_element_wdg.RelatedTaskWdg` | Not connected |
| `tactic.ui.table.task_element_wdg.TaskElementWdg` | Partial |
| `tactic.ui.table.task_element_wdg.TaskSummaryElementWdg` | Not connected |
| `tactic.ui.table.task_element_wdg.WorkElementWdg` | Not connected |
| `tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg` | Not connected |
| `tactic.ui.tools.review_wdg.ReviewTaskElementWdg` | Not connected |
| `tactic.ui.widget.misc_input_wdg.SObjectStatusElementWdg` | Not connected |
| `tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg` | Not connected |
| `tactic.ui.widget.overlay_stats_wdg.OverlayStatsWdg` | Not connected |

## Calendar and schedules (12)

| Class | Status |
| --- | --- |
| `pyasm.widget.gantt_wdg.CheckinHistoryGanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.DynGanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.GanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.ResourceUsageGanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.SObjectTaskGanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.ScheduleGanttWdg` | Not connected |
| `pyasm.widget.gantt_wdg.StatusHistoryGanttWdg` | Not connected |
| `pyasm.widget.timecard_wdg.TimecardInfoTableElement` | Not connected |
| `pyasm.widget.timecard_wdg.WeekTableElement` | Not connected |
| `tactic.ui.gantt.gantt_wdg.GanttTableElementWdg` | Not connected |
| `tactic.ui.table.gantt_element_wdg.GanttElementWdg` | Not connected |
| `tactic.ui.table.projected_schedule_wdg.ProjectedCompletionWdg` | Not connected |

## Files and versions (21)

| Class | Status |
| --- | --- |
| `pyasm.widget.dependency_wdg.DependencyThumbWdg` | Not connected |
| `pyasm.widget.file_wdg.FileInfoWdg` | Not connected |
| `pyasm.widget.file_wdg.ThumbWdg` | Partial |
| `pyasm.widget.naming_wdg.NamingElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.FileAppendLinkTableElement` | Not connected |
| `pyasm.widget.table_element_wdg.PublishTableElement` | Not connected |
| `pyasm.widget.table_element_wdg.RenderLinkTableElement` | Not connected |
| `tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg` | Not connected |
| `tactic.ui.cgapp.publish_element_wdg.PublishElementWdg` | Not connected |
| `tactic.ui.cgapp.version_wdg.CurrentVersionContextWdg` | Not connected |
| `tactic.ui.cgapp.version_wdg.UnknownVersionContextWdg` | Not connected |
| `tactic.ui.table.snapshot_element_wdg.SnapshotFileElementWdg` | Not connected |
| `tactic.ui.table.snapshot_element_wdg.SnapshotLockedElementWdg` | Not connected |
| `tactic.ui.table.snapshot_element_wdg.SnapshotMetadataElementWdg` | Not connected |
| `tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` | Unfinished in legacy |
| `tactic.ui.table.snapshot_element_wdg.SnapshotVersionElementWdg` | Partial |
| `tactic.ui.table.sobject_summary_wdg.SObjectFilesElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.CheckinButtonElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.GeneralPublishElementWdg` | Not connected |
| `tactic.ui.tools.custom_layout_edit_wdg.AddImageElementWdg` | Not connected |

## Notes and communication (7)

| Class | Status |
| --- | --- |
| `pyasm.widget.annotate_wdg.AnnotateLink` | Not connected |
| `pyasm.widget.discussion_wdg.DiscussionWdg` | Not connected |
| `tactic.ui.app.message_wdg.MessageTableElementWdg` | Not connected |
| `tactic.ui.app.note_wdg.NoteTableElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg` | Not connected |
| `tactic.ui.table.table_element_wdg.RecipientElementWdg` | Not connected |
| `tactic.ui.widget.discussion_wdg.DiscussionElementWdg` | Partial |

## Relationships and nested objects (11)

| Class | Status |
| --- | --- |
| `pyasm.widget.sobject_browser_wdg.SObjectConnectionDetailElement` | Not connected |
| `pyasm.widget.sobject_browser_wdg.SObjectConnectionElement` | Not connected |
| `pyasm.widget.table_element_wdg.GroupTableElement` | Not connected |
| `pyasm.widget.table_element_wdg.SObjectAttachTableElement` | Not connected |
| `pyasm.widget.table_element_wdg.SObjectExplorerWdg` | Not connected |
| `pyasm.widget.table_element_wdg.SObjectLinkElementWdg` | Not connected |
| `tactic.ui.table.explorer_wdg.ExplorerElementWdg` | Not connected |
| `tactic.ui.table.explorer_wdg.ExplorerTableElementWdg` | Not connected |
| `tactic.ui.table.foreign_key_element_wdg.ForeignKeyElementWdg` | Not connected |
| `tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg` | Not connected |
| `tactic.ui.table.related_element_wdg.RelatedElementWdg` | Not connected |

## Composition and actions (16)

| Class | Status |
| --- | --- |
| `pyasm.widget.table_element_wdg.HiddenRowToggleWdg` | Not connected |
| `pyasm.widget.table_element_wdg.PlaceHolderElementWdg` | Not connected |
| `pyasm.widget.table_element_wdg.TableAddWdg` | Not connected |
| `pyasm.widget.table_element_wdg.WrapperTableElementWdg` | Not connected |
| `tactic.ui.panel.document_wdg.DocumentItemWdg` | Not connected |
| `tactic.ui.panel.layout_wdg.RowSelectWdg` | Not connected |
| `tactic.ui.table.button_wdg.ButtonElementWdg` | Not connected |
| `tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg` | Not connected |
| `tactic.ui.table.custom_layout_element_wdg.FreeFormLayoutElementWdg` | Not connected |
| `tactic.ui.table.custom_layout_element_wdg.LayoutElementWdg` | Not connected |
| `tactic.ui.table.delete_element_wdg.DeleteElementWdg` | Not connected |
| `tactic.ui.table.drop_element_wdg.DropElementWdg` | Not connected |
| `tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg` | Partial |
| `tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg` | Not connected |
| `tactic.ui.tools.pipeline_wdg.PipelineDocumentItemWdg` | Not connected |
| `tactic.ui.widget.button_new_wdg.IconButtonElementWdg` | Not connected |

## Administration and settings (13)

| Class | Status |
| --- | --- |
| `pyasm.widget.clipboard_wdg.ClipboardHistoryElement` | Not connected |
| `pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg` | Not connected |
| `pyasm.widget.project_wdg.ProjectClassWdg` | Not connected |
| `pyasm.widget.project_wdg.ProjectSummaryWdg` | Not connected |
| `pyasm.widget.project_wdg.ProjectWdg` | Not connected |
| `tactic.ui.app.search_type_element_wdg.SearchTypeHasTableElementWdg` | Not connected |
| `tactic.ui.input.process_group_select_wdg.LoginTableElementWdg` | Not connected |
| `tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg` | Not connected |
| `tactic.ui.startup.security_wdg.SecurityCheckboxElementWdg` | Not connected |
| `tactic.ui.table.preference_wdg.PreferenceDescriptionWdg` | Not connected |
| `tactic.ui.table.preference_wdg.PreferenceEditWdg` | Not connected |
| `tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg` | Not connected |
| `tactic.ui.table.project_wdg.ProjectWdg` | Not connected |

## Excluded production (43)

| Class | Status |
| --- | --- |
| `pyasm.prod.render.qube_render_submit.QubeState` | Excluded |
| `pyasm.prod.web.asset_data_wdg.AssetDataLink` | Excluded |
| `pyasm.prod.web.asset_info_wdg.AssetInfoWdg` | Excluded |
| `pyasm.prod.web.asset_info_wdg.CondensedAssetInfoWdg` | Excluded |
| `pyasm.prod.web.asset_info_wdg.CondensedShotInfoWdg` | Excluded |
| `pyasm.prod.web.asset_info_wdg.GeneralInfoWdg` | Excluded |
| `pyasm.prod.web.asset_info_wdg.ShotInfoWdg` | Excluded |
| `pyasm.prod.web.asset_info_wdg.SubmissionInfoWdg` | Excluded |
| `pyasm.prod.web.camera_info_wdg.CameraInfoWdg` | Excluded |
| `pyasm.prod.web.composite_wdg.CompLayerTableElementWdg` | Excluded |
| `pyasm.prod.web.composite_wdg.ExploreTableElementWdg` | Excluded |
| `pyasm.prod.web.composite_wdg.LayerTableElementWdg` | Excluded |
| `pyasm.prod.web.frame_info_wdg.FrameRangeWdg` | Excluded |
| `pyasm.prod.web.frame_info_wdg.IFrameLink` | Excluded |
| `pyasm.prod.web.layout_summary_wdg.AssetsInShotWdg` | Excluded |
| `pyasm.prod.web.layout_summary_wdg.AssignedShotWdg` | Excluded |
| `pyasm.prod.web.layout_summary_wdg.TasksInSObjectWdg` | Excluded |
| `pyasm.prod.web.prod_input_wdg.AssetCheckboxWdg` | Excluded |
| `pyasm.prod.web.prod_input_wdg.LayerCheckboxWdg` | Excluded |
| `pyasm.prod.web.prod_input_wdg.LevelCheckboxWdg` | Excluded |
| `pyasm.prod.web.prod_input_wdg.SObjectCheckboxWdg` | Excluded |
| `pyasm.prod.web.prod_input_wdg.ShotCheckboxWdg` | Excluded |
| `pyasm.prod.web.prod_table_element_wdg.BinTableElementWdg` | Excluded |
| `pyasm.prod.web.prod_table_element_wdg.InstancePublishWdg` | Excluded |
| `pyasm.prod.web.prod_table_element_wdg.ThumbPublishWdg` | Excluded |
| `pyasm.prod.web.prod_wdg.SnapshotInfoWdg` | Excluded |
| `pyasm.prod.web.prod_wdg.SnapshotLabelWdg` | Excluded |
| `pyasm.prod.web.render_wdg.RenderTableElementWdg` | Excluded |
| `pyasm.prod.web.shot_instance_adder_wdg.NumSequenceInstanceWdg` | Excluded |
| `pyasm.prod.web.shot_instance_adder_wdg.NumShotInstancesWdg` | Excluded |
| `pyasm.prod.web.shot_instance_adder_wdg.NumTasksWdg` | Excluded |
| `pyasm.prod.web.sobject_checkin_wdg.CheckboxCheckinWdg` | Excluded |
| `pyasm.prod.web.sobject_checkin_wdg.DescriptionCheckinWdg` | Excluded |
| `pyasm.prod.web.sobject_planner_wdg.NumSObjectInstancesWdg` | Excluded |
| `pyasm.prod.web.statistics_wdg.EpisodeCompletionWdg` | Excluded |
| `pyasm.prod.web.statistics_wdg.FrameCompletionWdg` | Excluded |
| `pyasm.prod.web.submission_wdg.DailiesLink` | Excluded |
| `pyasm.prod.web.submission_wdg.SubmissionDataTableElement` | Excluded |
| `pyasm.prod.web.texture_wdg.TextureAddSourceElementWdg` | Excluded |
| `pyasm.prod.web.texture_wdg.TextureSourceElementWdg` | Excluded |
| `pyasm.prod.web.version_wdg.LatestVersionContextWdg` | Excluded |
| `pyasm.prod.web.version_wdg.LatestVersionWdg` | Excluded |
| `pyasm.prod.web.version_wdg.SessionVersionWdg` | Excluded |

## Permissions and verification limits

Configured Table View requires admin. The server checks record project/type and allowed options. Unknown classes/options/actions are not executed or declared ready merely because a Python file exists. Examples are checked with the native XML parser and describe_cell without a database. Vue screenshots use typed fixture values. Native TH is captured separately for Completion. The full old CGI runtime and the remaining classes have not been run.
