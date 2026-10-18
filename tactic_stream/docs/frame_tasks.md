# Tactic Frame B09: Task Manager and task inspector

B09 is **delivered**. Reference Handler checkpoint:
`0297005238226e9bd9bd7461e729177ac365ade7`. B07's legacy-widget gaps
remain separate; production Gantt/calendar migration is B10.

## Scope and existing owners

| Surface | Handler owner | Stream owner | Migration |
| --- | --- | --- | --- |
| Workspace, scope, filters, sorting, grouping, columns and paging | TasksController / TaskWorkspaceStore / TasksWorkspaceView | TaskManager / TaskWorkspaceCmd | Verified shared composition and actual workflows |
| Task table, selection, expanded fields and lazy pickers | AdvancedTaskTableModel / TaskBrowserTable / TaskTableEditorCell | TaskWorkspaceTable / prepared row plans | Verified shared composition and actual workflows |
| Pending changes, bulk fields, preview and confirmations | TasksController / native task edit commands | TaskManager drafts / TaskWorkspaceEditCmd | Verified shared composition and actual workflows |
| Quick Tasks cards and compact processes | TaskProcessPanel / existing process models | TaskProcessPanel / process records | Verified shared composition and actual workflows |
| Inspector task details and full editor | Existing Inspector, field models and task controller | NotesPanel / TaskDetails / configured task form | Shared task fields; B08 Inspector/notes owners retained |
| Phone list/detail and desktop restoration | Native compact layout / same task store | MobileTasks / TaskManager | Verified shared composition and actual workflows |

Existing request generations, revision checks, drafts, selection, configuration,
ACL and mutation executors remain with these owners. Portable modules describe
presentation and decisions only. Each product ships its own physical Frame copy.
Native filesystem/DCC capabilities remain native; no WebEngine is introduced.

## Acceptance checklist

- Original Handler → Frame Handler → Frame Stream comparisons on matching data,
  three themes, light/dark, EN/RU, narrow/wide widths and affected DPI scales.
- Real scope/filter/sort/group/paging effects; exact selected task/parent/process
  in Inspector, Notes, object and snapshot navigation.
- Mouse, keyboard and touch selection; lazy status/user/date pickers, column
  sizing/order/visibility, expanded fields, visible scrolling and stable focus.
- Create/edit/delete and existing bulk operations; explicit field opt-in,
  validation, save/cancel, conflicts, unknown writes and original revisions.
- Retain drafts across task/tab/project changes according to existing guards;
  hidden or signed-out views stop requests and reject stale completions.
- Quick Tasks, Inspector, browser phone detail/back and desktop restoration.
  Existing Gantt and separate Calendar entry points must remain usable.
- Focused owner/input tests, connected temporary-server workflows, fresh source
  fingerprints, mandatory platform gate, independent packages and EN/RU Help.
- Review explicit diffs, commit both repositories and verify NAS backups.

The checklist describes required work; it is not evidence of completion.

## Portable source map

`src/tactic_stream/shared_ui/features/tasks` is mirrored independently into
Handler's `thlib/ui/qml/tactic_frame/features/tasks` by `tools/sync_tactic_frame.py`.

| Module | Responsibility |
| --- | --- |
| `workspace.ui.mjs` | Main/quick toolbar, view modes, surface switcher, pending changes, options and footer |
| `table.ui.mjs`, `cells.ui.mjs` | Header/row/group paint, responsive widths, semantic HTML cell fragments, idle fields and phone row |
| `details.ui.mjs`, `editor.ui.mjs` | Expanded grid, inline header, typed editor and opt-in bulk form |
| `scope.ui.mjs`, `filters.ui.mjs` | Scope/team identity, quick facets and advanced filters |
| `bulk.ui.mjs` | Selection bar, prepared field/choice intersection and local preview; existing executors still validate |
| `columns.ui.mjs`, `menus.ui.mjs` | Width/order/visibility and corresponding row/column commands |
| `process.ui.mjs` | Quick Task cards/compact rows and their draft/action presentation |
| `empty.ui.mjs`, `summary.ui.mjs` | Empty guidance and the separate native management window's heading/summary/workload/presets |

Native adapters live in `qml/features/tasks` and retain the public task host
names. Vue adapters live in `frontend/src/features/tasks`; `TaskField` also serves
the task Inspector. Lazy native pickers and the virtualized task model remain.
Description typing stages the existing draft without rebuilding every row.
Bulk UI values are a temporary form buffer, not a parallel task store. Prepared
metadata retains the original revisions. Owner generations reject late results;
armed bulk fields prevent quiet refresh from replacing active input.

## Preserved capabilities and deliberate differences

- Handler's standalone management heading and workload/status/preset summary are
  described in Frame and remain native-only entry points. Stream's workspace is
  a dock and retains its phone list/detail/back navigation and extra timesheet,
  Inspector and revision-reload actions. No browser is embedded in QML.
- The common toolbar retains an always-accessible options menu from Stream.
  This shifts search/sort space relative to the archived Handler at wide sizes.
  Empty views now share counts/footer and consistent Create guidance; without a
  parent there is no arrow toward a disabled Create action. The message block
  has a common 240 px maximum width instead of independent font-derived widths.
- Current corresponding surfaces share geometry, labels and roles. The original
  comparison remains visible and does not establish absolute archive identity.
  Native/browser popup placement and OS text rasterization are separate from
  logical scene geometry. Status/process/user names remain server data.
- Gantt, scheduling dialogs, milestones and the separate Calendar entry points
  retain their existing owners. Their full presentation/interaction migration
  is B10, not part of this task-list renderer. B07's 40 legacy gaps remain open.
- The Stream task workspace API still requires administrator access. Handler's
  native task permissions and both products' mutation/revision executors remain
  unchanged. The UI does not grant extra rights.

## Reproduce the checks

Run from the Stream application directory with Handler available separately:

```
python tools/sync_tactic_frame.py --handler-root D:/code/th_codex --copy-from stream
python tools/format_tactic_frame.py --check --handler-root D:/code/th_codex
node frontend/tests/frame_tasks_state.mjs
python tools/frame_tasks/capture.py
node frontend/tests/frame_tasks.mjs
python tools/frame_tasks/report.py
python tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
```

The gallery uses actual `TasksWorkspaceView`, `TaskProcessPanel` and production
Vue presenters with the same TasksController records. It compares 10 states/widths
across 3 themes, light/dark and EN/RU (120 original + 120 current Qt + 120 Vue).
It rejects QML warnings, browser exceptions and stale source fingerprints.
The JSON records logical rectangles, typography, fills and checkbox indicators.
Original-to-Frame differences must be reviewed visually; matching two Frame
implementations alone is not original fidelity.

For a separate process at another DPI, set `QT_SCALE_FACTOR=1.25` (or `1.5`) and
`TASK_FRAME_OUTPUT=tools/frame_tasks/output/scale-125` (or `scale-150`), then run
`capture.py --smoke`, `frame_tasks.mjs` and `report.py`. Browser DPR matches the
recorded Qt scale. Generated evidence is local, ignored and never a production
runtime dependency. Tests use isolated settings and temporary server records.

Connected task/context/process/phone checks exercise real pickers, inline and
expanded drafts, native minute/hour conversion, opt-in bulk changes, save,
conflicts/unknown writes, scoped navigation, columns/resize/grouping and return
from phone to desktop. Native checks exercise actual popup windows, keyboard
creation, lazy field release, 200-row virtualization and the existing owners.

The additional column case shows Priority, Milestone and Supervisor together;
status/user placeholders, selected combo text and every Frame label are compared
as actual painted text. The select keeps its DOM focus/value across EN/RU changes.
Native empty-user labels translate only known placeholders; configured logins and
names are preserved. Milestone display labels do not replace the raw stored code.
Narrow bulk-editor actions stack instead of overlapping; long empty-state text wraps.

The filled Create action's inner inset, radius and color are measured against Qt.
Its browser hover tint uses brightness for the shipped accents; fully saturated
custom accents still need Qt HSV tinting for exact hover parity. OS rasterization,
compositor/grabs and arbitrary hardware are not established by offscreen images.

## Accepted checkpoint: 2026-10-18

Stream 0.112.162 / Handler 0.6.0.113: 104 mandatory platform stages,
153 focused native cases, four connected browser/server workflows and the
production Gantt/separate Calendar regression passed. The source-fresh gallery
contains 120 full-matrix pairs plus 20 pairs each at 125% and 150% (160 paired
states, 480 original/current-native/browser images). Native task lists retain
200-row delegate virtualization; the scheduling regression retains 500 rows.

Both complete desktop/mobile Workbench scenarios and the dedicated phone
tasks/search regression passed, including real swipes, Back/Forward, retained
scroll, coalesced quiet refresh, unchanged-response identity and saved revisions.

Live profiles retain their image, color and initials across lazy picker
activation; manual typing/scope changes retain drafts and original revisions.
Filled-action hover/focus honors the tooltip setting. Row command opacity is
described in the common row model, including hover, active, draft and alert
states, rather than being independently painted by each port. The browser
checks actual row command elements and real hover, translated search
placeholders, footer spacing and selected combo text.

Local diagnostics retain the initial grouped Qt failures and one object-batch
menu timing failure; independent Qt suites and the isolated object-batch
scenario passed. Final acceptance requires the complete gate and current
source fingerprints, not rerunning only the failing assertion.

The native table integration test now waits for a presented frame after its
scroll/row-height change before calculating the actual click coordinates.
