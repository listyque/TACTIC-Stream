# Tactic Frame B07: Table View checkpoint

B07 is **in progress**. The table host and adapted cells use shared Frame rules;
the widget-config census still contains 40 usable classes without a complete
native/browser implementation. A registered adapter is not proof that every old
display option or embedded action works.

| Portable module | Responsibility |
| --- | --- |
| `features/table/columns.mjs` | Width priority, hide order and auto-fit |
| `features/table/host.ui.mjs` | Row/header/selection/action geometry, paint and drag targets |
| `features/table/menus.ui.mjs` | Column and saved-view actions and availability |
| `features/table/cells.ui.mjs` | Typed labels, safe links, task-card geometry and compact summary/field scenes |
| `features/table/inline.ui.mjs` | Typed value editor body, explicit-save and uncertain-write states |
| `features/table/widgets.json` | 37 server classes, 87 named aliases, editor choices and native adapter categories |

Stream ships these under `src/tactic_stream/shared_ui`; Handler ships its own
copy under `thlib/ui/qml/tactic_frame`. The server still imports an explicit
allowlist of Python classes. Catalogue data cannot import arbitrary code.

## Owners

Qt ListView and the existing browser row virtualization retain delegates,
scrolling and real input. Application search sessions/ConfiguredView retain
queries and selection. ColumnsEditorController and widget-configuration API
retain definitions, revisions and saved views. Existing EditSObject/TableCellEditCmd
and task controllers retain writes, permissions, rollback and unknown outcomes.
No second database, query engine, script runtime or embedded browser is added.

Native `features/table/ValueEditor.qml` and Vue `TableInlineEditor` render the
same editor scene. Enter commits a single-line value; multiline Enter adds a
newline, and Save commits. Date/datetime/color/multiple values require explicit
Save. Escape cancels. The existing native keyword/tag editor remains specialized;
it has not yet been moved into the shared value scene.

Ordinary cell values are plain text in both hosts, including strings containing
markup. Body text uses the shared resolved pixel size, without point rounding
differences. Tiny fallback avatars stay centered and do not crop their glyph.
Explicit-save inputs keep their draft on an outside click. Progress
groups share their content width and scrollbar reserve; the comparison checks
the actual individual track rectangles as well as the containing table.

## Evidence and reproduction

Run from the Stream checkout using its Python environment:

```powershell
.venv/Scripts/python.exe tools/sync_tactic_frame.py --handler-root D:/code/th_codex --check
.venv/Scripts/python.exe tools/frame_table/inventory.py
.venv/Scripts/python.exe tools/frame_table/capture.py
$env:STREAM_BROWSER_CHANNEL = 'msedge'
node frontend/tests/frame_table.mjs
.venv/Scripts/python.exe tools/frame_table/report.py
```

`capture.py` requires the saved pre-B07 archive and commit identifier under
`.tmp/b07`, created from the tracked B06 Handler checkpoint. It never substitutes
current sources for a missing original. The output is ignored test evidence,
not a shipped application dependency. The report validates source fingerprints.
The archived checkpoint already includes previous Frame migrations; it is not
the original application before Frame.

The matrix contains three themes, light/dark, EN/RU, table widths 360/800/1496,
seven inline input modes and eleven typed/error cell examples. GUI fixtures
exercise production presenters; disposable HTTP/XML-RPC tests separately verify
queries and actual mutation effects. Qt/Chromium font rasterization can differ.

The old `handler_table.mjs` workflow now writes into
`tools/frame_table/output/legacy-driver`, preserving historical reports.

## Remaining B07 work

The executable inventory scans every shipped widget XML and CG template entry;
optional local databases use SQLite read-only mode. It records exact references,
deduplicates aliases and does not execute scripts. Current shipped/template
census: 239 entries, 34 referenced adapted classes, 40 pending classes,
27 previously excluded `pyasm.prod` classes and 3 explicitly unfinished originals.
The catalogue also includes three adapted classes not mentioned by this census.
An older optional local-database census covered 449 entries with the same
class counts; it is historical evidence, not required input for the current plan.
No working databases were read for this revision.

Largest pending groups are nested/hidden-row table scopes, Gantt/timecard/work-hour
cells, loader/publish/checkout operations, configurable buttons/custom layouts,
legacy task/status/assignment editors and their child forms. These must preserve
the original workflow through existing owners. Opening a generic inspector does
not implement a configured nested table; drawing a button does not implement its
script. Unknown classes/options stay explicitly unsupported.

Notification recipient tables are bootstrapped through the existing schema
upgrade. This checkpoint adds read projection, not a public notification insert
or email-delivery implementation. PostgreSQL production data, physical touch
hardware and all historical widget options have not been certified.

<a id="legacy-checklist"></a>
## Active legacy checklist — 2026-10-19

The current delivery order is [L01–L12](../UI_ARCHITECTURE.md#legacy-plan).
L01–L07 below partition all **40 pending canonical classes exactly once** from
239 shipped/CG entries. Every box is still open. These are required config
references, including definitions under `config/.../prod`; excluding `pyasm.prod`
does not exclude other namespaces in that directory. Full source paths, options
and use sites are reproducible with `inventory.py`; generated output stays ignored.

The scan also reports `cg:sthpw/pipeline/document` as an XML parse issue: its
content is a JSON document, not a widget XML. Follow dynamic/script references
when inspecting each group; the static count is not proof that every runtime
reference was discovered. Add newly confirmed usable dependencies to this ledger.

<a id="l01"></a>
### L01 — Связи и вложенные строки (8)

- [ ] `pyasm.widget.dependency_wdg.DependencyLink`
- [ ] `pyasm.widget.sobject_browser_wdg.SObjectConnectionElement`
- [ ] `pyasm.widget.table_element_wdg.HiddenRowToggleWdg`
- [ ] `tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg`
- [ ] `tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg`
- [ ] `tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg`
- [ ] `pyasm.widget.table_element_wdg.AuxDataWdg`
- [ ] `tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg`

Раскрыть настроенную дочернюю таблицу, добавить/связать объект, свернуть и восстановить состояние; проверить фильтры, направление связи, права, пустой результат, группировку и итог. Вложенная область имеет собственный query/selection scope; переход в общий Inspector не заменяет её.

<a id="l02"></a>
### L02 — Встроенные заметки, сообщения и задачи (4)

- [ ] `pyasm.widget.discussion_wdg.DiscussionWdg`
- [ ] `tactic.ui.app.message_wdg.MessageTableElementWdg`
- [ ] `pyasm.widget.task_wdg.SObjectTaskTableElement`
- [ ] `pyasm.widget.task_wdg.TaskParentSpacingTableElement`

Открыть ветку из ячейки, прочитать/добавить заметку или сообщение, изменить связанную задачу и увидеть обновлённые счётчики без потери положения таблицы. Проверить родителя, процесс, приватность и вложенные формы; использовать существующие Messages/Inspector/task owners.

<a id="l03"></a>
### L03 — Настраиваемые действия и layout (3)

- [ ] `tactic.ui.table.button_wdg.ButtonElementWdg`
- [ ] `tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg`
- [ ] `tactic.ui.table.drop_element_wdg.DropElementWdg`

Из исходного XML вызвать реальное действие с контекстом строки/выделения, выполнить разрешённый script/layout и проверить результат, ошибки, отмену и откат. Для drop дать явную альтернативу выбора. Общий редактор колонок/ячеек должен сохранять исходные options и revisions; неподдержанный параметр не игнорируется.

<a id="l04"></a>
### L04 — Файловые действия в таблице (7)

- [ ] `pyasm.widget.table_element_wdg.FileAppendLinkTableElement`
- [ ] `pyasm.widget.table_element_wdg.PublishTableElement`
- [ ] `pyasm.widget.table_element_wdg.RenderLinkTableElement`
- [ ] `pyasm.widget.table_element_wdg.SubmissionLinkTableElement`
- [ ] `tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg`
- [ ] `tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg`
- [ ] `tactic.ui.table.table_element_wdg.GeneralPublishElementWdg`

Из ячейки выполнить append/publish/checkout/load/submission по исходным параметрам через текущие file/Commit Queue owners; проверить snapshot/version, naming, файлы, повтор, права и FileUndo. RenderLink не объявляет готовым отдельный render farm. Local/DCC операции остаются native capabilities, браузер показывает доступные ему действия и понятное ограничение.

<a id="l05"></a>
### L05 — Статусы, процессы и назначение (6)

- [ ] `pyasm.widget.parallel_status.ParallelStatusEditWdg`
- [ ] `pyasm.widget.parallel_status.ParallelStatusWdg`
- [ ] `tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg`
- [ ] `tactic.ui.table.subcontext_wdg.ProcessElementWdg`
- [ ] `tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg`
- [ ] `tactic.ui.table.task_element_wdg.WorkElementWdg`

Из таблицы изменить процесс/статус/исполнителя, включая parallel status; проверить пустое значение, родительский scope, допустимые переходы, ревизию, ACL и конфликт. Внешний вид и первый пункт picker совпадают с текущим Handler; существующий Task Manager не реализуется заново.

<a id="l06"></a>
### L06 — Gantt и учёт времени внутри таблицы (5)

- [ ] `pyasm.widget.gantt_wdg.GanttWdg`
- [ ] `tactic.ui.table.gantt_element_wdg.GanttElementWdg`
- [ ] `pyasm.widget.timecard_wdg.TimecardInfoTableElement`
- [ ] `pyasm.widget.timecard_wdg.WeekTableElement`
- [ ] `tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg`

Проверить исходную временную шкалу, неделю, границы дат, часы и редактирование из ячейки с сохранением/отменой и пересчётом итогов. Переиспользовать B10/B14 schedule/time owners; отдельный Calendar dock остаётся отдельным. Наличие готового большого Gantt не закрывает его legacy table options.

<a id="l07"></a>
### L07 — Служебные ячейки и итоговая приёмка B07 (7)

- [ ] `pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg`
- [ ] `pyasm.widget.table_element_wdg.UpdateWdg`
- [ ] `tactic.ui.input.process_group_select_wdg.LoginTableElementWdg`
- [ ] `tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg`
- [ ] `tactic.ui.table.preference_wdg.PreferenceEditWdg`
- [ ] `tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg`
- [ ] `tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg`

Из конфигов login/group/project/preferences/naming/notification выполнить штатные переходы и изменения: пользователь, Security, preference, update/template, summary, recipient/trigger. Проверить обычного пользователя, admin, revisions и отмену. NotificationTrigger cell не означает готовую отправку email. После этого прогнать весь B07, включая ранее адаптированные 37 классов и их реально используемые options, inline/forms, keywords/tags и bottom/group_bottom/total_summary; закрыть только подтверждённые сценарии.

### Excluded unfinished originals

| Canonical class | Source evidence / decision |
| --- | --- |
| `pyasm.widget.table_element_wdg.WikiElementWdg` | Original explicitly says its wiki implementation is unfinished. |
| `tactic.ui.cgapp.publish_element_wdg.PublishElementWdg` | Returns only an unbound textarea; it is not the working GeneralPublish/Table publish operation. |
| `tactic.ui.table.snapshot_element_wdg.SnapshotServerElementWdg` | Empty direct BaseTableElementWdg placeholder. |

`ExplorerTableElementWdg` inherits a working ExplorerElementWdg; an alias with
`pass` is not unfinished. PlaceHolderElementWdg is intentionally empty infrastructure.
The 27 referenced `pyasm.prod` classes remain excluded separately.

### Acceptance applies to old adapters too

A checked class needs its original config/options, inherited behavior and real
read/write/action scenario, a reproducible XML/data example, unchanged scripts,
ACL/revision/failure/rollback checks and fresh matching native/browser captures
where the capability exists. Record the entry point, screenshots, parameters
and limits in EN/RU Widget Database Help. Reuse the existing object, task, file,
schedule and communication owners; opening a generic panel is not implementation
of the configured embedded scope. Unsupported options stay explicit.

Before closing B07 in L07, exercise the already adapted 37-class catalogue,
configured forms/inline editors, native keywords/tags and the used legacy
bottom/group_bottom/total_summary contracts too. A 40-class checklist alone
cannot certify all historical options. Current working controls remain delivered.
The rest of API/native/workflow/database/deployment compatibility is L08–L12,
not a reason to invent a second UI engine or to declare full TACTIC parity.
