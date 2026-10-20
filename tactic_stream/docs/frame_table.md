# Tactic Frame B07: Table View checkpoint

B07 is **in progress**. The table host and adapted cells use shared Frame rules;
the current widget-config census contains 9 classes without typed adapters. The
first checkpoint added 16 adapters and shared tags; the combined second stage
adds eleven registrations with the explicit limits below. A registered adapter is not proof that every old
display option or embedded action works.

| Portable module | Responsibility |
| --- | --- |
| `features/table/columns.mjs` | Width priority, hide order and auto-fit |
| `features/table/host.ui.mjs` | Row/header/selection/action geometry, paint and drag targets |
| `features/table/menus.ui.mjs` | Column and saved-view actions and availability |
| `features/table/cells.ui.mjs` | Typed labels, safe links, task-card geometry and compact summary/field scenes |
| `features/table/nested.ui.mjs` | Scoped expanded-table presentation; requests and mutations stay with each host |
| `features/table/time.ui.mjs` | Table schedule and daily-hours projections; current Gantt/Timesheet owners retain writes |
| `features/table/inline.ui.mjs` | Typed value editor body, explicit-save and uncertain-write states |
| `features/table/widgets.json` | 68 server classes, 163 named aliases, editor choices and native adapter categories |

Stream ships these under `src/tactic_stream/shared_ui`; Handler ships its own
copy under `thlib/ui/qml/tactic_frame`. The server still imports an explicit
allowlist of Python classes. Catalogue data cannot import arbitrary code.

## Owners

Qt ListView and the existing browser row virtualization retain delegates,
scrolling and real input. Application search sessions/ConfiguredView retain
queries and selection. ColumnsEditorController and widget-configuration API
retain definitions, revisions and saved views. Existing EditSObject/TableCellEditCmd
and task controllers retain writes, permissions, rollback and unknown outcomes.
No second database, query engine or embedded browser is added. Configured JavaScript
uses the original SDK through a bounded host bridge: a browser Worker or an isolated
QJSEngine process, never the native UI thread.

Native `features/table/ValueEditor.qml` and Vue `TableInlineEditor` render the
same editor scene. Enter commits a single-line value; multiline Enter adds a
newline, and Save commits. Date/datetime/color/multiple values require explicit
Save. Escape cancels. Keywords/tags now use the same specialized shared scene:
suggestions, deduplicated tokens, pending draft flush and explicit Save/Cancel.

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
eight inline input modes and twenty-four typed/error cell examples. GUI fixtures
exercise production presenters; disposable HTTP/XML-RPC tests separately verify
queries and actual mutation effects. Qt/Chromium font rasterization can differ.

The L02 checkpoint adds five backend/original-source/XML-RPC tests and three
native input cases (14 tests in `tests.test_frame_table`). Fresh comparisons
cover 312 paired states plus 36 archived-reference captures. EN/RU B07 Help
ships four paired cell examples and their XML definitions in both products.
The native SQLite integration checks note/task writes, stale revisions,
permissions, rollback, empty configured branches and foreign-project isolation.
PostgreSQL production data and physical touch hardware were not exercised here.

The broader Search regression run passed 47 of 48 tests. Its existing
`test_instance_children_reject_ambiguous_self_and_cross_resource_links` failure
expects “Self-instance children” but receives “Unknown column or SQL expression:
entity_code”; the same failure was reproduced using the unchanged HEAD
relationship method. L02 does not change that self-instance contract.

The old `handler_table.mjs` workflow now writes into
`tools/frame_table/output/legacy-driver`, preserving historical reports.

<a id="stage-two-2026-10-20"></a>
## Combined stage 2 checkpoint — 2026-10-20

The user moved the remaining stage-1 acceptance into stage 2. The current order
is L01 → L04 → remaining L03 → L06 → L07b. **Stage 2 and B07 remain open.**

The old `tactic.ui.tools.CustomLayoutEditWdg` is excluded: it edits the legacy
HTML/CSS/JavaScript/Mako browser shell. Frame and the existing layout editor own
new portable UI. This does not remove saved CustomLayout definitions or reinterpret
an unsupported DOM callback as a generic Inspector action.

Stream 0.112.175 / Handler 0.6.0.122 add `HiddenRowElementWdg`,
`HiddenRowToggleWdg`, `RowAddElementWdg`, `AuxDataWdg`, `GanttWdg`,
`GanttElementWdg`, `WeekTableElement`, `TimecardInfoTableElement` and
`WorkHoursElementWdg` registrations. The catalogue now contains **66 classes /
157 named aliases**; the shipped/CG census has **63 referenced adapted, 11 pending,
27 excluded-production and 3 excluded-unfinished classes**, across 239 sources.
An adapted census entry is a registered projection, not full original-option acceptance.

Expanded tables use `features/table/nested.ui.mjs` and existing cell presenters.
Each scope owns its records, selection, filter and page; the parent search selection
is unchanged. A collapsed loaded branch reuses its data and selection. Native
delegates create the expanded surface only when needed; server reads stay off the
GUI thread and repeated notifications coalesce. Session/project teardown discards
requests and contexts. The login record projection omits password material.

Same-type hidden views show the current record; child views use its relationship;
reverse task → parent reads resolve the actual parent. The real CG
`columns/tasks_parent` Mako binds only its JSON search key and opens its configured
parent table. A hidden portable CustomLayout currently requires one embedded table.
The initial surface has a 50-record page and a 320-pixel viewport. Legacy
`init_load_num`, shelf/gear and complete search-limit option behavior remain
unaccepted; their XML is retained, not a claim of matching original behavior.
Other dynamic widgets, recursive child surfaces, instance auxiliary transport and
full grouping/summary acceptance remain L01/L03 work. Do not silently substitute
an Inspector for those missing paths.

`features/table/time.ui.mjs` draws configured date ranges and daily hours in both
engines. A schedule bar opens the existing Task Manager Gantt; a daily-hours action
opens the existing Timesheet for its task/week. Read-only all-user hours have no
edit action. Overtime is counted once, minute display converts hours explicitly,
and page dates share one range. **This does not implement the original inline
`GanttCbk` default/cascade writes, full timecard lifecycle or bottom totals.**
Those options, file ingest/publish/append/checkout and the complete B07 matrix
remain required in this stage. Registered time classes stay unchecked below.

Validation at this checkpoint: all **146 platform-gate steps** passed;
**69 native table tests**, **50 table API tests**, browser table workflows and
**468 fresh paired states** passed. The paired driver now compares the embedded
nested-cell text position, size and weight, in addition to Frame container bounds.
The native set includes 504 captures, of which 36 are the archived B06 reference.
One initial integrated Task Inspector menu timeout did not reproduce in its
unchanged isolated scenario or the repeated complete gate; no retry was added to
the test. Retain that observation when investigating intermittent menu activation.

`tools/frame_table/output/index.html` contains the current paired evidence. Local
reports do not certify a production database, actual file transfers or a frozen
Windows package.

## Remaining B07 work

<a id="stage-one-2026-10-20"></a>
### Stage 1 checkpoint — 2026-10-20

Stream 0.112.174 / Handler 0.6.0.121 deliver U01 and sixteen additional class
adapters. This is a checkpoint of the requested five-subblock stage, **not its
completion**. Supported configured paths reuse the existing owners:

| Subblock | Delivered and checked | Still outside acceptance |
| --- | --- | --- |
| U01 | Shared tags, suggestions, pending input, explicit Save/Cancel; real native IME and browser keyboard/pointer input | Old standalone forms remain for their other callers |
| L02 | Existing note/task/message cells, original-source comparison and native XML-RPC regression checks retained | Excluded Submission; old CGI state/slash setting choices and raw message HTML |
| L07a | Seven service cells, custom insert/edit views, user/group identity, per-login preference revision/check, record retire/reactivate revision, template command and forced notification trigger path | Notification delivery and template lifecycle certification remain L09/L10 |
| L03 | Original JS SDK and captured row/selection; browser Worker and isolated native Qt JS process; confirmations and context cancellation; instance-link editor with rollback; real CG script CustomLayout | Nested FastTable/HiddenRow (L01), file-ingest DOM callback (L04), unrestricted Mako/DOM and complex development layouts |
| L05 | Six task/process/work adapters, original parallel 33/66/100 steps, exact task identity, status pipeline and assigned-scope validation; existing Task Manager/check-in | Local transfer modes are native capabilities; complete bottom/group reports remain L07b |

CG layouts were **not missing**: slash references resolve to dotted saved names.
`episodes.columns.script` is exercised from the actual template, with and without
a document URL. It renders links and the saved edit callback without embedding
HTML into QML. `columns.tasks_parent` embeds a FastTable and remains open in L01;
`episodes.columns.assets` contains only `No html` and is preserved as unfinished.
The one removed CG line was `spt.dg_table.add_filter(bvr.src_el)` in `take_episode`:
it supplies no filter definition; the surrounding assignment and refresh are retained.
All other CG scripts/layout definitions remain unchanged.

Portable layout Mako is limited to reading supplied JSON data and formatting it.
Table projection can repeat; it never runs imports, server writes or file/network
I/O. General Python/Mako compatibility is not claimed. The original SDK is a
byte-identical resource in both products; API permissions remain server-owned.
Unknown DOM/popup routes fail explicitly rather than silently opening a generic form.

New shared descriptions live in `features/table/services.ui.mjs`,
`parallel.ui.mjs`, `drop.ui.mjs`, `layout.ui.mjs`, `document.ui.mjs` and
`actions.state.mjs`. Native orchestration is grouped under `thlib/ui/table`;
QML presenters are under `qml/features/table`. Vue adapters remain under
`features/interface`. Neither checkout is required by the other's runtime.

Reproduce focused checks with:

```powershell
# Stream product directory; use temporary fixture databases only.
.venv/Scripts/python.exe -B -m unittest discover -s tests -p 'test_table_*.py' -q
node frontend/tests/table_script_runtime.mjs
node frontend/tests/table_script_worker.mjs
.venv/Scripts/python.exe tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
# Handler checkout, using the same development Python:
# -m unittest -q tests.test_frame_table tests.test_table_scripts tests.test_table_service_workflows tests.test_sobject_link
```

Final checkpoint validation passed: the complete Frame platform gate, **63 native
table tests**, **38 table API tests**, actual browser HTTP/XML-RPC workflows,
ordinary QML smoke and an independent wheel containing all **217 Frame modules**
and exact SDK/bridge resources. The original 250-visual-item table budget remains
unchanged; Insert controls are created only for configured Update columns.

The current capture matrix has **420 paired current states plus 36 archived
references**. New input scenarios cover custom actions, external links, parallel
task targets, the link editor button, custom header insert view, confirmations,
and a modeless readonly document with group switching and common Help. The actual
CG JavaScript scripts run against a fake SDK; sixteen shipped inline callback
bodies are checked through their typed routes. No production scripts or real
SMTP/Telegram delivery run during these tests. PostgreSQL, frozen Windows
packaging and physical touch hardware remain unverified for this checkpoint.

The next dependency work is L01/L04, followed by acceptance of the remaining L03
paths. Do not close stage 1 or B07 using the adapter count alone. EN/RU Help →
Table View: B07 includes XML examples and paired screenshots of supported cells.

The executable inventory scans every shipped widget XML and CG template entry;
optional local databases use SQLite read-only mode. It records exact references,
deduplicates aliases and does not execute scripts. At the stage-1 checkpoint (0.112.174), the shipped/template
census was 239 entries, 54 referenced adapted classes, 20 pending classes,
27 previously excluded `pyasm.prod` classes and 3 explicitly unfinished originals.
The catalogue also includes three adapted classes not mentioned by this census.
An older optional local-database census covered 449 entries with the same
class counts; it is historical evidence, not required input for the current plan.
No working databases were read for this revision.

Largest pending groups are nested/hidden-row table scopes, Gantt/timecard/work-hour
cells and loader/publish/checkout operations. Configurable actions/layouts and
task/status/assignment adapters have the stage-1 limits below. These must preserve
the original workflow through existing owners. Opening a generic inspector does
not implement a configured nested table; drawing a button does not implement its
script. Unknown classes/options stay explicitly unsupported.

Notification recipient tables are bootstrapped through the existing schema
upgrade. This checkpoint adds read projection, not a public notification insert
or email-delivery implementation. PostgreSQL production data, physical touch
hardware and all historical widget options have not been certified.

<a id="legacy-checklist"></a>
## Active legacy checklist — 2026-10-20

The current delivery plan has [three implementation stages and a separate fourth deployment stage](../UI_ARCHITECTURE.md#legacy-plan). U01 / L01–L12 remain subblock IDs, not stage numbers; the effort-sorted internal order is unchanged.
L01–L07 below partition the original **40 canonical classes exactly once** from
239 shipped/CG entries. L02 has four registered adapters; stage 1 adds another 16. Twenty classes still
need adapters. Checked entries below mean tested supported adapter scenarios;
full original-option acceptance remains a separate L07b gate. These are required config
references, including definitions under `config/.../prod`; excluding `pyasm.prod`
does not exclude other namespaces in that directory. Full source paths, options
and use sites are reproducible with `inventory.py`; generated output stays ignored.

The scan also reports `cg:sthpw/pipeline/document` as an XML parse issue: its
content is a JSON document, not a widget XML. Follow dynamic/script references
when inspecting each group; the static count is not proof that every runtime
reference was discovered. Add newly confirmed usable dependencies to this ledger.

### U01 — active shared-UI gap: inline keywords/tags

Delivered in Stream 0.112.174 / Handler 0.6.0.121: the same specialized Frame
scene renders chips, suggestions and the pending text draft. Save flushes the
pending draft, Escape discards it, outside clicks do not save. Real native
QInputMethodEvent and browser pointer/keyboard tests cover the active path.
The old standalone tag forms remain available to their other callers; the
active table editor no longer selects legacyTagsEditor. This does not close
stage 1 or add another canonical class to the 40-class partition.

L07a implements the seven service/admin classes listed under L07; L07b is the
later integrated acceptance, not a second set of seven classes. Existing L02
adapters remain delivered with the explicit option limits recorded below.

## Snapshot checkout checkpoint — 2026-10-21

Stream 0.112.177 / Handler 0.6.0.124 add `CheckoutButtonElementWdg` for ordinary
individual snapshot files. The catalogue contains 68 classes / 163 named aliases;
the 239-source census is 65 adapted, 9 pending, 27 excluded-production and 3
excluded-unfinished classes. The source ledger has 459 QML + 305 Vue = 764 entries,
with 220 separately shipped Frame modules.

Both products use `features/files/snapshot_checkout.ui.mjs`. Handler opens an
ordinary native modal window and reuses native `File` paths plus the existing
`RepositorySyncController`; the browser downloads the selected file using its
own destination policy. No browser engine or second transfer queue is added.
Opening reads file metadata without a local disk walk; the selected file is
checked off the GUI thread before transfer. Both hosts order main files first,
then by filename, type and identity, including Unicode filenames.
Concrete version, owning project and selected file remain captured. Private
message attachments retain the Messages flow; unsupported sequence/UDIM groups
are rejected explicitly. Their full transfer support remains L04 work.

Real mouse input verifies native overwrite confirmation, cancellation during
local stat/HTTP read, closing, and late-response disposal. Transfer regressions
preserve files created during HTTP reads and prevent duplicate scheduling from
mutating an active request's source/policy. Native file URLs quote literal path
metadata including spaces, `#` and `%`. A real isolated browser/server/database
scenario clicks the table action after append, then verifies the actual downloaded
name, bytes, owning project and unchanged snapshot version. Focused browser input
also covers empty/error, HTTP cancellation, session changes and 320px scrolling.

The house native ProgressBar explicitly uses the Material implementation. Its
accent and track no longer depend on which Qt control module was loaded first.
A regression preloads the generic control before checking actual colors/pixels;
the paired checkout driver also compares track color, thickness and fill value.

Checks for this checkpoint: all 147 Frame platform steps, including independent
packaging; 89 native table tests and 65 server table tests. Fresh comparison
covers 708 current Handler/Stream states, including 120 checkout states; the
744 native captures also retain 36 historical B06 references. The paired form
body is checked separately from operating-system window decorations. Browser
input checks the real table action and downloaded filename/bytes, cancellation,
session changes, selection paint and the narrow translated footer.

This is an L04 checkpoint, not completion of stage 2 or B07. Ordinary-user ACL,
original-server/PostgreSQL execution, physical devices/DPI, groups, publish,
remaining nested/group/time/options and the final B07 matrix remain open.

## Snapshot append checkpoint — 2026-10-20

Stream 0.112.176 / Handler 0.6.0.123 add `FileAppendLinkTableElement`.
The catalogue contains 67 classes / 160 named aliases; the 239-source census is
64 adapted / 10 pending / 27 excluded-production / 3 excluded-unfinished.
The UI source ledger contains 458 QML + 303 Vue = 761 entries.

Both hosts render `features/files/object_checkin.ui.mjs`, including file type,
keep-original-name, pending files, explicit discard, loading/error and uncertain
write states. Handler hosts the body in an ordinary native modal Window, not an
embedded Popup; geometry persists but an old snapshot session never restores.
Browser uses the existing check-in owner, while native uploads/filesystem work
runs in workers with captured server/project and lifecycle cancellation.
Ctrl+V attaches an image even when a native text field has focus; plain text
paste still edits that field. Directories and more than 50 files are rejected.
Each draft uploads into its own ticket-relative directory, so concurrent
same-named files cannot overwrite another draft's upload. Completion refreshes
both the concrete snapshot and the original current/latest row.

`TableSnapshotAppendCmd` and the copied native procedure resolve a versionless
alias to a concrete snapshot, validate its owning project, capture a full
snapshot/files revision and lock/recheck it at save. Every uploaded basename,
file type and duplicate is validated before `FileAppendCheckin`; no new version
is created. `FileUndo` rolls back a late failure. Server uploads are disposable;
original client files and existing repository files remain protected. Unknown
write outcomes disable repeat until the snapshot is refreshed. Only admin scope
is currently accepted, matching the table host. PostgreSQL/original-server
execution and physical hardware/DPI acceptance remain unverified here.

Checks for this checkpoint: all 146 Frame platform steps, including independent
packaging; 80 native table tests and 62 server table tests;
an isolated browser scenario clicks the real table action, uploads through
UploadServer in the snapshot's owning project and reads the repository bytes
back without changing the version. Fresh comparison covers 588 current
Handler/Stream states, including 120 append states (three styles, light/dark,
EN/RU, 360/760 px, ready/loading/error/unknown/discard). Native captures also
retain 36 historical B06 references. The paired images compare form content;
operating-system window decorations are not a pixel-parity claim. The default
760×820 form viewport is checked separately from browser titlebar geometry.

The remaining L04/L01/L03/L06 and L07b work is still open. This checkpoint does
not turn an unsupported action into a generic Inspector link.

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
### L02 — Legacy-ячейки для готовых заметок, сообщений и задач (4 адаптера)

- [x] `pyasm.widget.discussion_wdg.DiscussionWdg`
- [x] `tactic.ui.app.message_wdg.MessageTableElementWdg`
- [x] `pyasm.widget.task_wdg.SObjectTaskTableElement`
- [x] `pyasm.widget.task_wdg.TaskParentSpacingTableElement`

Открыть ветку из ячейки, прочитать/добавить заметку или сообщение, изменить связанную задачу и увидеть обновлённые счётчики без потери положения таблицы. Проверить родителя, процесс, приватность и вложенные формы; использовать существующие Messages/Inspector/task owners.

L02 checkpoint: Stream 0.112.169 / Handler 0.6.0.119. These boxes mean
configured adapters and the tested base workflows, not every original option.
The old Discussion uses existing note counts/Inspector and setting/append_setting
process choices (including zero-count choices); Task uses existing cards, drafts
and editors, with supe/bid_edit controlling inline assignment/dates. simple_date
selects compact month-day dates; the old HTML CalendarBar is replaced by the
current native/Frame date presentation. TaskParentSpacing shows the original
context prefix. Messages format plain/chat/note/task/snapshot/progress payloads
as plain text; the old HTML preview is not recreated.

`include_submission=true` is explicitly rejected because Submission belongs to
the agreed excluded pyasm.prod subsystem. Slash subcontexts in legacy setting
choices and CGI filter state stay explicitly unsupported; use the modern
Discussion context option for that separate scenario. Display flags are not ACL:
server permissions/revisions remain authoritative. No second Messages or Tasks
application is introduced. Reproduce with `test_table_embedded_widgets.py`, the
unchanged native transport checks and the existing Qt/Vue table capture harness;
examples are also in EN/RU Help → Table View: B07.

<a id="l03"></a>
### L03 — Настраиваемые действия и layout (3)

- [x] `tactic.ui.table.button_wdg.ButtonElementWdg`
- [ ] `tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg`
- [ ] `tactic.ui.table.drop_element_wdg.DropElementWdg` — portable instance links delivered; the shipped `folder_drop` / FileIngest callback remains L04 work.

Из исходного XML вызвать реальное действие с контекстом строки/выделения, выполнить разрешённый script/layout и проверить результат, ошибки, отмену и откат. Для drop дать явную альтернативу выбора. Общий редактор колонок/ячеек должен сохранять исходные options и revisions; неподдержанный параметр не игнорируется.

<a id="l04"></a>
### L04 — Файловые действия в таблице (7)

- [x] `pyasm.widget.table_element_wdg.FileAppendLinkTableElement`
- [ ] `pyasm.widget.table_element_wdg.PublishTableElement`
- [ ] `pyasm.widget.table_element_wdg.RenderLinkTableElement`
- [ ] `pyasm.widget.table_element_wdg.SubmissionLinkTableElement`
- [ ] `tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg`
- [ ] `tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg` — ordinary single files delivered in .177/.124; sequence/UDIM and remaining original options are not accepted yet.
- [ ] `tactic.ui.table.table_element_wdg.GeneralPublishElementWdg`

Из ячейки выполнить append/publish/checkout/load/submission по исходным параметрам через текущие file/Commit Queue owners; проверить snapshot/version, naming, файлы, повтор, права и FileUndo. RenderLink не объявляет готовым отдельный render farm. Local/DCC операции остаются native capabilities, браузер показывает доступные ему действия и понятное ограничение.

<a id="l05"></a>
### L05 — Статусы, процессы и назначение (6)

- [x] `pyasm.widget.parallel_status.ParallelStatusEditWdg`
- [x] `pyasm.widget.parallel_status.ParallelStatusWdg`
- [x] `tactic.ui.table.sobject_detail_wdg.SObjectTaskStatusElementWdg`
- [x] `tactic.ui.table.subcontext_wdg.ProcessElementWdg`
- [x] `tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg`
- [x] `tactic.ui.table.task_element_wdg.WorkElementWdg`

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

- [x] `pyasm.widget.my_tactic_summary_wdg.MyTacticSummaryWdg`
- [x] `pyasm.widget.table_element_wdg.UpdateWdg`
- [x] `tactic.ui.input.process_group_select_wdg.LoginTableElementWdg`
- [x] `tactic.ui.panel.security_manager_wdg.SecurityManagerButtonWdg`
- [x] `tactic.ui.table.preference_wdg.PreferenceEditWdg`
- [x] `tactic.ui.table.project_wdg.ProjectTemplateUpdateWdg`
- [x] `tactic.ui.table.table_element_wdg.NotificationTriggerElementWdg`

Из конфигов login/group/project/preferences/naming/notification выполнить штатные переходы и изменения: пользователь, Security, preference, update/template, summary, recipient/trigger. Проверить обычного пользователя, admin, revisions и отмену. NotificationTrigger cell не означает готовую отправку email. После этого прогнать весь B07, включая уже адаптированные классы и их реально используемые options, inline/forms, keywords/tags и bottom/group_bottom/total_summary; закрыть только подтверждённые сценарии.

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

Before closing B07 in L07b, exercise the complete 68-class catalogue,
configured forms/inline editors, native keywords/tags and the used legacy
bottom/group_bottom/total_summary contracts too. A 40-class checklist alone
cannot certify all historical options. Current working controls remain delivered.
The rest of API/native/workflow/database/deployment compatibility is L08–L12,
not a reason to invent a second UI engine or to declare full TACTIC parity.
