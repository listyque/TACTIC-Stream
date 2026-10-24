# Tactic Frame B07: Table View checkpoint

B07 is **reopened for general legacy compatibility** after the
[2026-10-24 audit](../LEGACY_MIGRATION_AUDIT_2026-10-24.md). Earlier completion
statements below describe selected scenarios and a bounded configuration census;
they do not certify all original templates, custom plugins or public Python calls.
The shared table host and adapted cells remain verified within that scope.
Definition authoring has a confirmed visual-editor regression, and an importable
custom cell is not accepted by the built-in adapter registry. A registered adapter
does not prove every old display option, editor or embedded action works.

| Portable module | Responsibility |
| --- | --- |
| `features/table/columns.mjs` | Width priority, hide order and auto-fit |
| `features/table/host.ui.mjs` | Row/header/selection/action geometry, paint and drag targets |
| `features/table/menus.ui.mjs` | Column and saved-view actions and availability |
| `features/table/cells.ui.mjs` | Typed labels, safe links, task-card geometry and compact summary/field scenes |
| `features/table/nested.ui.mjs` | Scoped expanded-table presentation; requests and mutations stay with each host |
| `features/table/time.ui.mjs` | Table schedule and daily-hours projections; current Gantt/Timesheet owners retain writes |
| `features/table/inline.ui.mjs` | Typed value editor body, explicit-save and uncertain-write states |
| `features/table/widgets.json` | 75 server classes, 183 registered aliases, editor choices and native adapter categories |
| `features/table/dependencies.state.mjs` / `dependencies.ui.mjs` | Concrete snapshot tree, cached expansion, cycle guards, page state and presentation |

Stream ships these under `src/tactic_stream/shared_ui`; Handler ships its own
copy under `thlib/ui/qml/tactic_frame`. The server still imports an explicit
allowlist of Python classes. Catalogue data cannot import arbitrary code.

## Parent groups: Stream .180 / Handler .127

`ParentGroupTableElementWdg` groups by canonical parent search key rather than
visible code. Identically named objects from different types remain separate;
missing references remain visible and can be repaired. The 64px shared header
shows disclosure, preview, code/name/type/description, count and Add Another Item.
The add action uses each product's existing configured insert form and passes
the captured parent and source project; it does not invent a second editor.

`ParentGroupAction` enables an anchored, nonmodal shared picker. This includes
Expression display cells: their computed text is preserved while the relationship
is edited. Search is literal and paged at 50; Save is explicit. Dirty Cancel/Refresh
requires discard confirmation. Save captures source physical ID and full revision,
configuration revision and target revision, locks/rereads the source, rejects
retired/cyclic/foreign-project targets and uses the native relationship API.
A lost response requires Check saved changes, never automatic write replay.
Global rows resolve bare parent types in their own project. Only safe parent
fields are exported; account credentials/private-message/ticket targets are excluded.

The independently shipped Handler procedure retains the same relationship rules.
Actual Qt drag sequences exercise both parent and existing instance-link drops;
the adapter reads `action.value`, not the event's source control. Browser retained
card state now preserves table state; collapsing a group cannot erase the chosen
table view. System-note result trees skip the wildcard `*` as a concrete Search Type.

Known scope: current table/mutation admission is administrator-only. Ordinary-user
ACL, all inherited group summaries/options and arbitrary legacy DOM behavior are
not certified here; they remain L07b. The removed Custom Layout Editor stays out.

Validation for this checkpoint: the 155-step Frame platform gate passed on the
final sources, including 124 native table tests, 106 table API tests and seven
native-source XML-RPC scenarios. Real browser input covers parent changes,
dirty cancellation, resize, a lost save response followed by verification,
collapse/reopen and the captured parent/project in the existing creation form.
The source ledger is 463 QML + 307 Vue = 770 surfaces. Fresh capture contains
1056 native states (36 historical) and 1020 current QML/Vue pairs; Parent picker
and group examples ship in both Help bundles. The disabled Frame Action wrapper
no longer adds an AppButton background underneath its ItemSurface.

Acceptance logs: `.tmp/stage2/parent-platform4.log`, `parent-capture4.log` and
`parent-paired6.log`. Earlier partial runs were rejected or restarted after
source/driver/translation changes; their results are not the final acceptance.
The deployed original server, PostgreSQL, real-device input and frozen EXE were
not certified here. Browser Parent/instance-drop events, all scoped column/totals
options and ordinary-user ACL still require the final L07b workflow pass.

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
engines. A schedule bar opens the existing Task Manager Gantt (in object, user,
project, or related-objects cascade scope); a daily-hours action opens the
existing Timesheet for its task/week. Read-only all-user hours and non-editable
schedule bars have no edit action. Overtime is counted once, minute display
converts hours explicitly, and page dates share one range. `GanttCbk` supports
both `default` and `cascade` date shifts, `GanttWdg` supports `ResourceUsageGanttWdg`
and `width`/`cal_margin`, `WorkHoursElementAction` supports ST/OT/clock writes
and zero-delete, and `WeekTableElement`/`WorkHoursElementWdg` compute row and
daily totals.

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

## Connections, recursive tables and object summary — .178 / .125

`SObjectConnectionElement` batches page targets and previews. Incoming/outgoing
directions retain original endpoint semantics; retired and deleted targets remain
visible. Removal captures the source before confirmation, rereads after the DB
lock, checks its revision and removes only the connection. Refresh on a lost
response makes replay safe; target objects remain untouched.

`SObjectSummaryElementWdg` counts related tasks, snapshots and notes, and SQL-sums
`straight_time` without adding overtime. A project row scopes by its own code;
Tasks and Checkins open distinct nested tables in that project's context.

Recursive nested tables reuse the same presenter and Frame `List`; variable
array extents preserve the focused header position and virtualize expanded rows.
Ancestor-scope cycles are rejected. Each child retains its own selection and
loaded state. Closing a branch invalidates its pending native/browser result;
reopening a loaded branch needs no read. Hidden native ancestors reject actions.
The explicit `show_shelf`, `show_search`, `show_search_limit` and selection/insert
flags hide their controls. `init_load_num` is a rendering hint, not pagination:
viewport virtualization replaces the original placeholder rows. Pages remain 50
records and child viewports 320px. Explicit `show_gear=true` is rejected until
nested Columns authoring has its own captured scope.

The shared parallel-group label no longer intercepts the disclosure button.
Summary buttons and sortable child headers use ordinary Action/Icon/Label
composition: `iconAction` is an icon-only native control. The paired capture
requires painted summary labels and compares their exact visible text in Vue.
The broader table workflow also reproduced a dropped Enter: a quiet Inspector
poll disabled its active composer. Quiet refresh now has a separate in-flight
flag, preserves input and rejects its stale reply after a send. A held real server
response proves Enter can send before the poll completes. Handler has no matching
periodic all-project-note poll; its explicit context loads retain their guard.

Actual QML and browser input tests cover disclosure, independent selection,
summary switching, cycle rejection and cache reuse; 10k-row tests cover bounded
materialization and focus retention. Transport tests execute the Handler query
source over XML-RPC against disposable Stream data. This does not certify an
original server, PostgreSQL, ordinary-user ACL or physical touch/DPI hardware.

Current catalogue: **70 classes / 168 named aliases**. The 239 shipped/CG source
entries reference 67 adapted, 4 pending, 30 excluded-production and 3 explicitly
unfinished classes. Render/Submission/Loader have mandatory excluded production
dependencies; normal `prod/DEFAULT` definitions remain generic fallback entries.
Registration and these scenarios do not close L01 or stage 2/B07.

Validation for this checkpoint: 151 platform stages passed with fresh source
fingerprints and independent packaging; 102 native table tests and 80 table API
tests passed. The current paired driver accepted 732 states after 768 native
captures (36 are historical references). Summary labels are checked as painted
text, not inferred from button rectangles. Browser table, connection, held-refresh,
10k variable-row and native-fallback XML-RPC scenarios passed.


## Snapshot dependency viewer — .179 / .126

`DependencyLink` opens the existing modeless `table_document` window. Both hosts
use the same state and presenter, including per-path row identities, branch-local
loading/error/retry, cached reopening and ancestor cycle detection. Tree projection
uses iterative traversal, including a tested 1,000-level chain without a depth cap.
Root selection
resolves current/latest once; every later read captures the concrete version,
source project and revision. Contextual level references retain their original
resolution instead of falling back to an unscoped snapshot code.
Global snapshot/project tables open the record's own project; an expanded scope
without an explicit project inherits its captured application project.

Files, upstream/input/downstream links, file-local references, instance/node
metadata, retired snapshots and missing owners/references remain visible.
Sequence members are paged in batches of 50 without eagerly expanding the full
range. This viewer does not claim sequence/UDIM transfers: those remain L04.
An ordinary registered file opens through the existing native file owner or
browser preview, validating its captured snapshot/file code and revision first.
The browser file selector contains only the requested file.

The thumbnail projection now expands only the first sequence frame. Its original
path expanded the complete range just to keep index zero; a 10-million-frame
regression guard fails on that behavior and accepts the bounded read. A real
registered million-frame sequence is exercised through the browser/XML-RPC fixture.

Close, refresh, project change and sign-out invalidate outstanding reads; native
reads run in workers. Actual native input/lifetime tests, exact native procedure
source over XML-RPC and the production Edge workflow cover expansion/cache,
cycles, sequence pagination and concrete file bytes. The viewer currently requires
administrator access; ordinary-user ACL and stage 2/B07 acceptance remain open.

The generic document host also invalidates pending custom-layout/security reads
when another document opens or the window closes. A late successful response must
not replace Dependencies or reopen its closed window. Both functional-window
captions use the current language.

Current registration census: **72 classes / 174 named aliases**; 239 shipped/CG
sources reference **69 adapted, 2 pending, 30 excluded-production and 3 unfinished**
classes. The two publish classes still lack their adapted workflow.
Older checkpoint counts above describe those releases, not the current census.

Previous dependency checkpoint validation (.179/.126): 108 native table tests, 90 table API tests and six native-source
XML-RPC cases passed. Fresh capture produced 864 native states (36 historical
references); the paired driver accepted all 828 current states. The production
browser flow additionally checks actual registered file bytes, page/cache
behavior, captured projects and responses arriving after document closure.
All 153 platform stages passed on the final source fingerprints, including
format, independent copies, input, DPI and independent packaging. Earlier runs
observed intermittent bold-action and Batch submenu input failures; both
unchanged suites passed independently and in the final complete gate. This
checkpoint does not claim to fix those intermittent tests or certify the
deployed original server, PostgreSQL, ordinary-user ACL or physical hardware.

<a id="l01"></a>
### L01 — Связи и вложенные строки (8)

- [x] `pyasm.widget.dependency_wdg.DependencyLink` — administrator base viewer; ordinary-user ACL remains in L07b.
- [x] `pyasm.widget.sobject_browser_wdg.SObjectConnectionElement` — administrator direction/read/remove workflows; ordinary-user ACL remains open.
- [x] `pyasm.widget.table_element_wdg.HiddenRowToggleWdg`
- [x] `tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg`
- [x] `tactic.ui.table.hidden_row_element_wdg.RowAddElementWdg`
- [x] `tactic.ui.table.group_element_wdg.ParentGroupTableElementWdg` — identity grouping/header, parent action and existing child insert form; full option/ACL acceptance remains L07b.
- [x] `pyasm.widget.table_element_wdg.AuxDataWdg`
- [x] `tactic.ui.table.sobject_summary_wdg.SObjectSummaryElementWdg` — object/project counts and separate task/snapshot scopes.

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
- [x] `tactic.ui.table.custom_layout_element_wdg.CustomLayoutElementWdg` — portable saved layouts (`episodes/columns/script`, `columns/tasks_parent`, `columns.thumb_view` → `custom_col`), including `HiddenRowElementWdg` custom-layout cells and explicit unresolved references (`asset_panel_wdg`, `asset_cost_breakdown`, `inline_add_item`, bare `custom_col`); ordinary-user ACL remains L07b.
- [x] `tactic.ui.table.drop_element_wdg.DropElementWdg` — portable instance links and `folder_drop` / `FileIngestCmd` callback delivered; ordinary-user ACL remains L07b.

Из исходного XML вызвать реальное действие с контекстом строки/выделения, выполнить разрешённый script/layout и проверить результат, ошибки, отмену и откат. Для drop дать явную альтернативу выбора. Общий редактор колонок/ячеек должен сохранять исходные options и revisions; неподдержанный параметр не игнорируется.

<a id="l04"></a>
### L04 — Файловые действия в таблице (7)

- [x] `pyasm.widget.table_element_wdg.FileAppendLinkTableElement`
- [x] `pyasm.widget.table_element_wdg.PublishTableElement` — configured row form and optional Multi Publish header; configured field actions, not an invented generic check-in.
- Excluded: `pyasm.widget.table_element_wdg.RenderLinkTableElement` — requires the previously excluded production subsystem; see the source inventory.
- Excluded: `pyasm.widget.table_element_wdg.SubmissionLinkTableElement` — requires the previously excluded production subsystem; see the source inventory.
- Excluded: `tactic.ui.cgapp.loader_element_wdg.LoaderElementWdg` — requires the previously excluded production subsystem; see the source inventory.
- [x] `tactic.ui.table.table_element_wdg.CheckoutButtonElementWdg` — ordinary files, sequences and UDIM groups delivered in .183/.130; ordinary-user ACL remains L07b.
- [x] `tactic.ui.table.table_element_wdg.GeneralPublishElementWdg` — configured view and optional bounded preview; excluded Publish Browser is not included.

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

- [x] `pyasm.widget.gantt_wdg.GanttWdg`
- [x] `tactic.ui.table.gantt_element_wdg.GanttElementWdg`
- [x] `pyasm.widget.timecard_wdg.TimecardInfoTableElement`
- [x] `pyasm.widget.timecard_wdg.WeekTableElement`
- [x] `tactic.ui.table.work_hours_element_wdg.WorkHoursElementWdg`

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

Before closing B07 in L07b, exercise the complete current catalogue,
configured forms/inline editors, native keywords/tags and the used legacy
bottom/group_bottom/total_summary contracts too. A 40-class checklist alone
cannot certify all historical options. Current working controls remain delivered.
The rest of API/native/workflow/database/deployment compatibility is L08–L12,
not a reason to invent a second UI engine or to declare full TACTIC parity.


### Configured publication checkpoint (.181/.128)

Both canonical publish classes use the existing configured editor and EditCmd,
with captured publish presentation, a target key, optional preview and explicit
Multi Publish header. They preserve the configured UploadAction and rollback;
NullAction is not substituted with a check-in. Dirty/busy/uncertain/batch editor
sessions survive another row click; clean sessions may retarget. All shipped
native object/task entry points use the same admission helper.

Current registration: **74 classes / 180 named aliases**. The 239-source census
references **71 adapted, 0 without adapters, 30 excluded-production and 3
unfinished** classes. This is registration coverage, not completed acceptance:
L04 sequence/UDIM/ingest, remaining L03/L06 and L07b remain open. The old
HTML/Mako Custom Layout Editor and production Publish Browser stay excluded.
Real original-server deployment, PostgreSQL, frozen EXE and physical devices
remain unverified.

Native publication supports text/multiline/select/checkbox and explicit
SimpleUpload/UploadAction. Other configured input/action combinations block the
form explicitly. It uses configured EditCmd rather than the ordinary native
editor's direct update; other native forms retain their persistence. Native and
browser FileInput controls share controls/forms/file.ui.mjs and live under their
base-control directories. UploadMultipart closes HTTP connections on both success
and failure. Ordinary-user ACL, form revisions and additional inputs stay L07b.

Step 2.0 acceptance: all 156 Frame platform gate steps passed on the unified
`d:/grav/Tactic Stream/{TS,TH}` workspace after adding `get_action_handler` to
the `test_columns_table_view.py` config stubs, registering `FileInput` /
`AppFileInput` in `element_catalog.json`, and synchronizing programmatic scroll
events in `checkin.mjs`; `tools/frame_table/report.py` validated current source
fingerprints cleanly.


### Stage 1.5 (`L07b`) & Stage 1 (`B07`) final acceptance (.186/.133)

- **Catalogue options & summaries**: `FormatElementWdg` (`total_summary`: `count`, `total`, `average`), `ExpressionElementWdg` (`bottom`, `group_bottom`, `inline_styles`, `rowcss_background-color`), `SearchTypeElementWdg` (`filename`), `SimpleTableElementWdg` (`css_background`, `css_background-color`, `rowcss_background-color`), and `ThumbWdg` (`redirect`, `redirect_expr`) are supported and projected into group and bottom summary rows in both engines (`features/table/host.ui.mjs`, `TableView.vue`, `ConfiguredView.vue`, `SearchResultTable.qml`).
- **Nested column authoring (`show_gear`)**: `nested_scope.py`, `tactic_query.py`, `nested.ui.mjs`, `NestedTable.vue`, `ConfiguredView.vue`, and `TH/thlib/ui/table/nested.py` wire `show_gear` (`nestedColumns`) to open the scoped Columns Editor for administrators.
- **Ordinary-user ACL vs administrator tools**: `_require_table_access` in `interface.py` and the self-contained table procedures (`read_nested_scope`, `read_dependency_node`, `read_connection_cells`, `remove_connection`, `edit_parent_group`, `read_parent_cells`, `append_snapshot_files`, `read_snapshot_files`, `edit_drop_links`, `read_summary_cell`) enforce project, `search_type`, and `element` permissions for authenticated non-admin users while keeping `read_group_summary`, `read_custom_layout`, and `ColumnsEditor` admin-only.
- **Form revisions, retired record guard, and uncertain save recovery**: `read_form`, `EditCmd`, `EditMultipleCmd`, `RecordForm.vue`, `SObjectFieldEditor.qml`, and `sobject_editor.py` enforce `expected_revision` before writing, reject editing retired records (`Retired records cannot be edited. Reactivate the record first.`), and expose `Check saved changes` (`sobjectEditorCheck` / `action='check'`) when a network error leaves the save outcome unknown.
- **Explicit remaining unsupported configs**: Only the 4 unresolved legacy `CustomLayout` references (`asset_panel_wdg`, `asset_cost_breakdown`, `inline_add_item`, bare `custom_col`) and `include_submission=true` remain explicitly rejected; the 30 `pyasm.prod`/3D/Maya/Flash classes and 3 unfinished source widgets (`WikiElementWdg`, `PublishElementWdg`, `SnapshotServerElementWdg`) remain excluded. Stage 1 (`B07`) is closed.


## Snapshot history files: Stream .198 / Handler .144

Legacy HiddenRowElementWdg targeting tactic.ui.checkin.SnapshotFilesWdg now opens the existing nested table host with a read-only snapshot_files file view. Both shipped procedures resolve membership from Snapshot.get_all_file_objects(), including XML references, instead of selecting every file by parent type or project. Columns retain native web links, repository directory, file type, range, size and timestamp. A non-snapshot owner uses its original publish-context snapshots. The browser table-action Worker copies JSON record context before postMessage, including nested Vue proxies, and disposes its resources if serialization or sending fails. Native Qt script execution has no browser Worker boundary.

This checkpoint does not implement recursive directory-package browsing in this hidden row, downloading a whole frame sequence from its pattern link, or Maya/applet actions. Existing Submit/RV adapters and other legacy gaps are not certified by this fix. Source changes need a BAT server restart and browser reload; no new packaged EXE is qualified here.


The nested shared renderer now falls back to the configured record field when no computed cell is returned, preserving zero, false and deliberately empty computed cells. Both file-table filters prefer file_name over internal code. Validation includes 37 file/nested/value regressions, the browser Worker regression (including disposal after serialization failure), real browser/QML input on three AST001 files from the main SQLite fixture, and direct source reads of all 180 VFX snapshots / 516 files. Three live repository URLs returned byte-identical files. These renderer checks use extracted main-data responses in isolated test hosts; they do not claim that the running server has reloaded Python modules. The offscreen QML comparison uses MD3 dark, EN, Segoe UI, scale 1 at 600 x 320.

Final acceptance: all 156 Frame platform stages passed on unchanged final source fingerprints; native-file-workspace-journey passed its recorded serial retry. Gate: .test-tmp/snapshot-files-platform-verified.log and tools/frame_foundation/output/platform/gate.json (SHA-256 e21385aa7d7ac2b526038834c45dbefaf1a1d03f0807039ac0e2e7f12e6a5c14). Earlier incomplete/failed runs are not acceptance.


## Checkin Log owner captions: Stream .199 / Handler .145

The actual Checkin Log sidebar link uses sthpw/snapshot view log; it is distinct from checkin_history. Its Code cell still named pyasm.prod.web.SnapshotInfoWdg after the namespace exclusion. The original generic owner-caption behavior from legacy/src/pyasm/prod/web/prod_wdg.py now lives in tactic.ui.table.snapshot_element_wdg.SnapshotInfoWdg, with modern public imports only. Parent reads are batched by qualified type and code/id references are retained. Ordinary names/codes follow the original name-code format; missing or excluded owners display n/a. The excluded ShotInstance specialization is not restored. Handler uses its existing value adapter and native get_text_value projection. The built-in log no longer offers RenderLinkTableElement, whose original target is pyasm.prod.web.RenderSubmissionWdg.

The previous .198 checkpoint checked Files in table/checkin_history, but did not certify Code or the other columns of log. The new regression explicitly reads both log and checkin_history through Stream and Handler's query_table_layout and requires every remaining log column to be supported. Fresh HTTP reads of Files before this change already succeeded; the screenshot alone does not establish whether its Files error came from retained browser state or an earlier worker.


Checkin Log live verification for .199/.145: 40 targeted file/widget regressions pass. All 180 main VFX snapshots read through log without unsupported columns or cell errors. The shipped native procedure executed through the running main HTTP server agrees with Stream on 20 owner captions and file descriptors. A fresh browser opened the real Checkin Log twice with an intervening Assets navigation: 20 rows, zero unavailable widgets, zero cell errors, and three links after expanding Files. The main BAT server was gracefully restarted to load the new Python catalogue and left running at 0.112.199. Browser evidence is .test-tmp/checkin-log-browser.json/png; native projection is .test-tmp/checkin-native-live.json. These are test data/profile artifacts and are not packaged EXE acceptance.

Final Checkin Log Frame gate: all 156 stages passed on final source fingerprints, with recorded serial retries of native-file-workspace-journey and native-table. Report: tools/frame_foundation/output/platform/gate.json (SHA-256 a48b0fc52a3ffdb384ad91dcaaefc82defc2a0666c66dd2fd0b40478053e36b7); log: .test-tmp/checkin-log-platform-final.log. The earlier run with a JSON formatting failure is not the final acceptance.
