# Tactic Frame: Task Manager and task inspector

This contract describes source ownership, behavior and verification scope.
TH and TS ship independently; native-only actions remain native capabilities.
Use [the shared contract](contract.md) and [the feature index](index.md).

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

## Verification

Run the focused drivers under `tools/frame_tasks/` from the Stream development
checkout, with the actual Handler checkout supplied using `--handler-root`
where supported. The complete shared gate is:

```powershell
python tools/frame_foundation/check_platform.py --handler-root "../../TH"
```

Adjust that path relative to the working directory; in the two-repository
workspace, Stream commands run from `TS/tactic_stream` and Handler is `../../TH`.
Use isolated data, actual input, fresh source fingerprints and independent-package
checks. Generated reports belong in the ignored tool `output/` directories.
Historical release counts and captures are local archive material, not current
acceptance. Offscreen checks do not establish physical touch/IME, compositor,
DCC or deployment readiness; exercise those when the feature requires them.
