# Tactic Frame: architecture review and complete UI migration plan

Started 2026-10-15. This replaces the previous screen-first migration order.

## Architecture review, 2026-10-15

Decision: retain Frame as shared UI composition and presentation-state modules.
Do not start the large screen rollout until the preparation gate below passes.
This review changes the plan, not application code. Findings are against Stream
96396a8 and Handler 0db42ab2; their worktrees contain unrelated SDK/help changes.

The useful boundary already exists: ordinary `.mjs` modules run in both engines,
describe the same controls, and return state plus explicit commands. Renderers
use each product's house controls. Existing controllers own requests, ACL,
transactions and persistence. Two independent product copies remain appropriate;
no runtime sibling checkout, WebEngine, automatic QML translator or new parser
is needed.

The current source inventory is 47 portable modules (20,469 lines, including
translations), 345 native QML files, 178 Vue components and 48 registered native
window-content kinds. These are file/registry counts, not migration work units:
docks, menus, popovers and script-created UI also exist, and some window kinds
share a component. Administration is implemented in Frame but still requires
comparison against the original Handler, not just against the other Frame host.

### Findings that block expansion

1. **Array-backed native lists perform quadratic reconciliation.**
   `thlib/ui/qml/tactic_frame/core/FrameView.qml:681` scans the remaining
   ListModel for every record, moves records and computes JSON signatures.
   Rendering virtualization does not avoid this work. The existing `fields`
   path can consume native role models directly; Groups/Users already use it.
   Reuse that path and existing controller models for large collections rather
   than build a second general-purpose diff engine. Small array catalogs may
   retain a bounded fallback, with explicit focus/selection preservation tests.
   Without this change, migrating search/results into the array path can freeze
   the GUI during sort/filter updates.

   A local probe instantiated the actual current FrameView in Qt 6.11.2 /
   PySide6 6.11.2 / Python 3.14.7, offscreen software backend. List height was
   300 logical pixels, row height 32, unique keys, empty row scenes, `fields: []`.
   It assigned ordered rows, an unchanged copy, then a reversed copy. Three
   samples per size measured synchronous assignment/reconciliation with QML
   `Date.now()`. Median reverse times were:

   | Records | Reverse update | Unchanged-copy update |
   | ---: | ---: | ---: |
   | 100 | 3 ms | 0 ms |
   | 1,000 | 313 ms | 2 ms |
   | 2,000 | 1,268 ms | 6 ms |
   | 4,000 | 5,163 ms | 10 ms |

   These are synthetic reconciliation timings, not FPS, full screen load times,
   browser measurements or a comparison of Qt and Vue speed. The probe and raw
   results are local ignored artifacts under `.tmp/frame_review_2026_10_15/`.

2. **Typography has two competing unit contracts.**
   `core/foundation.mjs` defines point-based roles; `core/frame.mjs:98` defaults
   nodes to pixel `fontSize: 13`. FrameView applies `font.pixelSize` to controls
   whose base component sets `font.pointSize` (for example Button.qml:26).
   The previous actual smoke run recorded 50 warnings in four Frame windows.
   Choose named typography roles from foundation, resolve them once per host,
   and keep explicit units only where a specialized control needs them. Preserve
   original sizes through measured conversions; do not just hide the warnings.
   Otherwise this ambiguity spreads to every migrated screen and DPI test.

3. **Resize deliveries can discard another target's new geometry.**
   Ten Administration Vue adapters observe body and toolbar but cancel a pending
   animation frame and keep only the newest callback's entries. In the actual
   Groups callback (SecurityGroups.vue:119), a body delivery followed by a
   toolbar-only delivery before the frame leaves the old body size in place.
   A deterministic probe of that source callback reproduced a viewport left at
   1x1 while toolbarSize changed to 900. This tests the delivery sequence, not its
   frequency in a live browser. `graphFrame.js:125` already contains the correct
   pending Map keyed by target. Reuse that batching/lifecycle behavior in these
   adapters with one focused test, rather than maintain eleven variations.

### Simplifications before adding more surface area

- Keep Table/Grid, Tree, Graph/Gantt, Code and rich text as meaningful specialized
  bricks. Share their model, column definitions, operations and state; implement
  native input, IME, painting and platform integration in the corresponding
  control. The current virtualized Grid and specialized Graph/Code establish
  this direction. Do not describe thousands of offscreen cells as generic boxes.
- Remove equivalent local builders when the owner already exists. Eight local
  `button` constructors occupy 120 lines despite `core/frame.mjs` exporting the
  same builder. This is a small deletion, not a reason to introduce another DSL.
- Reuse `controls/forms/fields.mjs`, `sections.ui.mjs` and the Administration form
  builder. Screen files should read as named sections and actions. Preserve
  domain-specific decisions; avoid replacing them with a giant universal schema.
- Add concise JSDoc for node kinds, bounds/units, record identity and event/command
  shapes. Extend the current validation to catch duplicate sibling IDs, missing
  required sources and missing named child Views in development/tests. Today a
  missing `View` target resolves to null in Qt and an undefined dynamic component
  in Vue. Explicitly optional platform slots must be declared as optional.
- Keep transient editor state (caret, IME composition, native hover/focus) inside
  the brick; keep saved selection, drafts and document transitions outside the
  virtualized delegate. Recycled rows must not own persistent edits.
- Share capability decisions explicitly, extending existing host capability
  objects only when a real feature needs them. Viewport/input mode, client
  availability and server permissions are distinct inputs. Do not scatter
  `if browser` conditions through layouts or treat hidden UI as authorization.
- Keep one explicit maintenance copy direction for portable module edits and
  verify both independent artifacts. Prefer editing the Stream copy then copying
  to Handler for a shared change; native renderer changes stay in Handler.
  Preserve the explicit reverse-copy tool for work deliberately started there.
- Mirror only the actual shared subset. A product-only Frame screen description
  belongs under that product's feature directory and imports its local Frame
  core. It does not force an unused browser-only page into Handler's runtime or
  a native DCC page into Stream. The existing shared-module manifest continues
  to compare the common subset byte for byte.
- Keep existing pure-state tests and real Qt/browser input drivers. Share their
  data and expected operations, rather than build another UI-testing framework.
  Run affected scenarios while developing; run the full paired suite at release
  checkpoints. Current capture hashes include all portable modules and native
  controls, so an unrelated edit invalidates every capture. Dependency-scoped
  hashes may reduce this cost later; until then do not call stale evidence fresh.

Qt documents the cost of dynamic-role ListModels, broad binding updates and
heavy delegates; Vue documents stable props, virtualization, shallow state for
large immutable data and the cost of unnecessary component layers. These support
the direction above, not a claim that a particular optimization is already fast:
[Qt 6.11 performance](https://doc.qt.io/qt-6.11/qtquick-performance.html),
[Vue performance](https://vuejs.org/guide/best-practices/performance).

## Complete rollout order (proposed; not completion claims)

Migration means one definition of corresponding UI and state, with native
renderers. It does not mean rewriting Python controllers, browser transport,
database code or user-authored QML into JavaScript.

| Phase | Scope | Completion gate |
| --- | --- | --- |
| 0. Preparation | Fix the three findings above; record source/host/entry point for every window, dock, menu and popup; define brick contracts and original references | Frame-owned smoke warnings resolved; resize delivery test passes; large-list updates preserve selection/focus without multi-second blocking; existing quality debt remains visible |
| 1. Controls | Finish foundation consumers, typography, buttons, fields, choices, checkbox/switch, tooltips, menus, scrollbars/splitters, user/date/time/color/icon pickers, tree/table base | Real normal/hover/pressed/focused/disabled/loading/error states in both engines; EN/RU, themes, narrow/wide and DPI; same semantic events |
| 2. Windows and main workspace | Complete window kinds, ownership/modality, anchored popovers, native detach/browser panels, dock stacks/tabs, footer/corners, resize/drag, main menus/navigation, search tabs and layout restore | Original TH → Frame TH → Frame TS; first click/tap works; reopening/tab changes preserve drafts and layout; no extra requests from hidden views |
| 3. Administration closure | Finish original-reference comparison for all existing Frame sections and child editors; restore missing source behavior before expanding | Groups, Users, Access, Search Types, Schema, Workflow, Columns, Raw database, Layouts, Sidebar, Naming and process rules pass their actual read/edit/save/error/guard scenarios |
| 4. Support and identity | Help, errors/confirmations, debug log, UI performance, user profile, sign-in/presets and connection status; update UI shell | Shared search/selection/scroll and host behavior; host-specific log/update operations stay explicit; no authentication/polling regression |
| 5. Configuration and projects | Common configuration navigation/forms, project create/edit/templates; network/repository/check-in/cache/appearance/task preferences and client-specific pages | Fields and page composition shared where equivalent; adapters retain current persistence/reconnect/restart/secret rules; differing client settings remain declared sections |
| 6. Search and table infrastructure | Search workspace, query cards, quick/process filters, tags, saved/advanced search, paging/sort/group, selection, result cards/table, column/view editor | Keyboard/touch/inline edit and unknown-write guards; referenced production widget configs covered by documented examples; unfinished legacy widgets remain excluded |
| 7. Objects and inspector docks | Object report, descriptions, notes, previews/snapshots, files, processes/tasks, links, create/edit/delete/duplicate, watch-folder editor | Context and drafts survive selection/tab changes; same actions, ACL errors and confirmations; native file actions remain adapters |
| 8. Tasks | Task manager table/inspector, filters/scope, Gantt, separate calendar dock, milestones | Start with the existing shared Gantt proof, then migrate production operations, dependencies, scheduling, drag/undo, save conflicts and mobile presentation |
| 9. Communication | Conversations, messages/composer, attachments, members/emoji/search popovers, notifications and activity feed | Immediate cached switching; drafts/read positions retained; hidden/signed-out views stop requests; Enter/send rules and desktop/touch behavior verified |
| 10. Files and queues | File workspace/changelist, ingest/check-in, Commit Queue, Repository Sync queue/editor, matching templates, repository editor, screenshot tools | Large queues virtualized; progress/cancel/retry preserved; local filesystem, DCC and browser transfer capabilities tested through existing owners |
| 11. Scripts and standalone tools | Script Editor, shelf/triggers, Batch/Database editor, Handler Server, DCC options and standalone entry points | Shared editor/workspace shell and commands; Python/QML execution and standalone lifecycle retained; no browser inside QML and no forced conversion of user scripts |
| 12. Remaining client surfaces and removal | Knowledge base/journal/API docs, remaining context menus/popovers, product-only pages; remove superseded layouts after acceptance | Every inventory item is migrated, intentionally client-specific or explicitly excluded by the user; no competing old/new runtime implementation |

The order is dependency-based. For example, object task cells may reuse the task
brick before the full Task Manager migrates; they must not wait for or duplicate
that entire page. Support/configuration features that do not share semantics
keep separate data/operations under the same composition rules. Browser-only
server administration and native-only DCC tools remain first-class inventory
items, not fake parity claims. Optional browser local capabilities must be based
on the current working integration, not on a blanket assumption that all local
features are impossible in a browser.

Use Help as the first complete vertical pilot while completing phases 1–2:
navigation, search, rich article body, scrolling, toolbar, window lifecycle and
desktop/phone reflow. This validates the full path on a bounded read-only screen
before committing to the remaining application rollout. Administration remains
the complex editable reference; another small button demo is insufficient.

### One vertical migration batch

1. Capture the original screen and list its actions, child surfaces, states,
   controller dependencies, platform capabilities and stored state. Record known
   original bugs separately; do not preserve a bug merely to match a screenshot.
2. Specify shared data/events/commands and named layout sections. Add a brick
   only if an existing one cannot express the actual interaction correctly.
3. Connect the existing Qt and Vue controllers. Keep request generations,
   uncertain writes, ACL, validation and dirty-close guards in their real owners.
4. Compare original → native Frame → browser Frame on the same fixture. Exercise
   actual click, touch, keyboard, IME, focus, popup anchoring, scrolling and drag
   where relevant; assert backend effects separately from appearance.
5. Include loading/empty/error, offline/logout, long labels, themes, phone reflow,
   repeated open/close, tab/project changes and realistic collection sizes.
6. Update existing EN/RU Help, checklist/examples, native type indexes and
   independent package/update checks. Remove the replaced layout only after
   acceptance. Commit both products and retain a usable rollback point.

Do not migrate a component count as a substitute for a working user scenario.
Do not keep both old and new implementations active behind a permanent toggle.

### Performance and acceptance policy

Proposed targets must be measured on recorded hardware before becoming gates:
cached tab switching/first action feedback within 100 ms; no growing delegate
count while scrolling; no GUI-thread work exceeding the available frame budget
during continuous drag/scroll. Sort/load work may run asynchronously but the
display update must remain responsive. Record scene construction, model update,
delegate creation, memory, request count and frame pacing separately.

Use 100/1,000/10,000 records for collection checks and a viewport-limited large
table/graph fixture; adapt the final sizes to observed production data. A matching
scene JSON or thousands of small visual states is not a load test. A synthetic
QML timing is not a browser or GPU performance guarantee. Retain the original
controller model and brick boundaries until measurement justifies changing them.

No calendar estimate is justified by file counts. Measure completion time and
remaining defects after preparation plus the complete Help pilot, then
estimate the remaining vertical batches. The highest-risk blocks are workspace
lifecycle, table editing, messaging lifecycle, file queues and standalone scripts.

## Restore points and reference

`D:/code/TACTIC_VUE/backups/2026-10-15_103116_before_shared_ui_foundation`
contains verified TH.zip and TS.zip, SHA-256/file manifests and RESTORE.txt.
TH_git_HEAD_reference.zip is the tracked original Handler at
fa3f594c5cd09ce565ea14acb533302e79c9308a, not the uncommitted current state.
Settings and local data are private. Remote databases are outside these archives.

## Ownership and directory rules

Both products ship independent copies. No runtime checkout imports or WebEngine.
Folders express responsibility, not QML versus JavaScript file extensions:

```
shared_ui/                    # TS portable modules; TH has tactic_frame/
  core/                       # node contract, theme, typography, metrics
  controls/                   # graph, code and other reusable controls
  shell/                      # window/dock/workspace composition and state
  features/
    administration/           # shared admin forms/strings and page modules
      groups/ users/ security/ database/ columns/ sidebar/
      search_types/ naming/ workflow/ schema/ layouts/
    search/                   # tags, quick filters, presets
```

Native renderers follow the same boundaries. Feature code may use core and
controls; controls may not depend on Administration or another feature.
Moves must update consumers, capture hashes, package checks and the recursive
sync manifest. Do not leave old implementation copies as runtime fallbacks.
Original reference sources stay separate from the running application.

## Work and acceptance ledger

| Work | Status | Acceptance |
| --- | --- | --- |
| Current TH/TS archives | Complete | ZIP CRC, SHA-256, no files changed while read |
| Independent original graph reference | Captured | Original/Frame schema/workflow, selected node and edge |
| Invisible uncolored graph connections | Fixed; initial render checks passed | Default, source color, explicit color; real pixels in Qt and browser |
| Frame directory structure/readability | Complete for migrated code | 47 recursive modules, 72 formatted native renderers/adapters; separated Administration domains and shell/windows, shell/docks; public QML type index; independent clean wheel and native update archive checked |
| 1. Theme/type/metrics/motion | Implemented and checked | 12,708 archived/current TH checks; 3,178 browser checks; styles, custom palettes, independent motion preferences and reduced motion |
| 2. Controls and interaction | In progress | Common primitive metrics, form sections, tab sizing/displacement; native and browser first-click, touch, scrollbar and splitter checks passed. Complete primitive states still require review |
| 3. Windows and docks | In progress | Common geometry, minimum sizes (240 original values), dock-header composition and tab rules; 24 browser windows have semantic kinds. Existing owners retain persistence/lifecycle. 12 original/Frame native header pairs and 9 browser cases passed; complete dock trees and chrome states remain |
| 4. Main window | In progress | Original TH = Frame TH toolbar geometry at five widths; actual Vue at six widths, real settings/account/project input. Menus, navigation and full workspace composition remain |
| 5. Screen contents | In progress | Workflow parameters/pipeline settings and original left library placement restored; actual full TS/TH input and whole Workflow comparison passed. 2340 paired Administration states passed; original-wide visual parity remains incomplete; search/filter migration has not begun |

Each screen requires two comparisons: original Handler → Frame Handler, then
Frame Handler → Frame Stream. A matching pair of redesigned screens does not
establish fidelity to the original. Existing reports establish only what their
fixtures actually measured; the Administration-wide visual parity claim is
withdrawn pending comparison to the independent original.

The first original comparison confirmed workflow layout drift. Process settings
now precede coordinates, coordinates live under Advanced JSON, original form
sections and node-type choices are restored, and Pipeline settings has its own
top-level action with dirty-buffer guards. The workflow library is back in the
Administration sidebar under compact section icons, using one catalog scene and
state. The complete original and Frame Workflow pages were captured at two widths;
the whole-shell styling and additional toolbar commands still differ. This is
evidence for the corrected placement, not an assertion of pixel-perfect parity.

## Current evidence and limits

- `tools/frame_foundation/check_foundation.py` and
  `frontend/tests/frame_foundation.mjs`: actual native/browser theme values.
- `tools/frame_foundation/check_main.py`: archived pre-task Main, current Main
  and the built Vue application, with private temporary server data. Native
  captures use `grabToImage` and reject blank frames; offscreen window-buffer
  captures were blank and are not accepted as visual evidence.
- `tools/frame_admin/native_regression.py`: 249/249 native Administration
  regressions passed after the module, renderer, adapter and host moves.
- `tools/frame_foundation/reference_administration.py` and
  `frontend/tests/frame_library_browser.mjs`: whole native/browser Workflow,
  including its sidebar host, on the same original controller fixture.
- `tools/check_frame_package.py`: a clean independent wheel contains precisely
  all 47 modules, matches their bytes, and imports them without another checkout.
- `frontend/tests/tab_widths.mjs`: shared tab rules against checked-in historical
  QML declarations, captured before extraction; production contains one rule.
- `frontend/tests/button_activation.mjs`, `panel_chrome.mjs`,
  `checkbox_geometry.mjs`, `window_types.mjs`: actual input and host behavior.

Platform differences remain explicit: Handler has DCC selection and separate
native dock windows; Stream retains its panel-maximize/position controls,
floating Results title and phone presentation. Handler's quick theme toggle
and Stream's quick Appearance menu still have different actions. The shared
toolbar currently owns layout, not those menu operations.

The whole-repository quality gates remain red. The reproducible
`tools/frame_foundation/check_quality_baseline.py` compares the archive with
current sources: structure failures decreased from 11 to 10, missing-property
remains 114, property-override remains 9, and unused-imports remains 21. No limits
were raised. Both identical offline smoke runs load/reopen/close the registered
windows with exit code 0, but both emit 50 existing point/pixel font warnings
in four Frame windows; these still fail the ordinary smoke test. This is an
explicit remaining defect, not a passing global smoke gate.

Current Administration reports were refreshed with source hashes after the final
changes. They compare Frame implementations; original-wide parity is not implied.
No live database or user configuration is part of these fixtures. The local
evidence entry point is `tools/frame_foundation/output/index.html`.
