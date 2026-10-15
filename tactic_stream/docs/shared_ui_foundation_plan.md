# Tactic Frame: architecture review and complete UI migration plan

Started 2026-10-15. This replaces the previous screen-first migration order.

## Phase 1: verified foundation subset; control inventory in progress, 2026-10-15

Handler 0.6.0.98 / Stream 0.112.147. The products retain independent copies:
52 portable modules and 22 registered Frame kinds. No embedded browser, new
runtime dependency or general-purpose UI parser was introduced.

This is not the complete controls library. The executable gallery has sixteen
cards plus tree, splitter and Grid examples; 372 counts state combinations,
not control types. The source-linked atlas at
`tools/frame_controls/output/ui-elements.html` inventories all QML/Vue sources,
inline uses, styles, reusable families and unresolved classifications. Rebuild
it with `python tools/frame_controls/elements.py --handler-root <handler>`.
Its explicit gaps include full tabs, badges/chips, avatars, headers, search,
segmented groups, spinbox, emoji/image pickers and all open menu variants.
Neither static presence nor a nested use is standalone acceptance.

The base kit includes primitives and neutral composite controls. Infrastructure
and business forms/fragments remain separate. Responsibility, not directory or
file size, defines that boundary; see `shared_ui_contract.md`.

- `core/interaction.mjs` owns button, field, checkbox and switch state paint;
  `foundation.mjs` owns dimensions, typography and CSS role resolution. The
  native controls and Vue controls consume those values. Native hover is
  explicit. Full native font values preserve existing point-size overrides
  without mixing point/pixel subproperties. The normal window smoke has no
  font or runtime warnings.
- `core/icons.mjs` owns semantic aliases and font-family fallback in both
  renderers. The font bytes are checked; the release icon driver compares
  305 actual native/browser glyph resolutions across all five supplied sets.
  Qt uses vertical font hinting to retain fractional glyph advances. Controls
  captures check text origins, baselines, advances, glyphs and icon geometry,
  rather than treating a matching outer rectangle as sufficient. Content
  positions allow 0.6 logical pixels; rasterization remains engine-specific.
- Strict local calendar arithmetic is shared, including leap years, early
  years, invalid dates and valid server precision/zone suffixes. Untouched wire
  values remain untouched. DateChoice separates edit and acceptance events;
  UserChoice receives existing records without requests. Disabling a picker
  owner closes its popup, including the color dialog. Browser pickers prepare
  data before showing; keyboard focus returns on cancellation.
- The icon library is anchored and virtualized in both engines, with matching
  keyboard entry, arrows, Home/End and acceptance. User selection, mixed marks,
  field errors, menu/tooltip behavior, scrollbars and splitters use the actual
  house controls. The shared tree row/navigation now drives Sidebar Editor,
  retaining stable IDs, dirty guards and the native role-model list path.
  Grid remains the specialized, virtualized table base.
- `controls/catalog.ui.mjs` supplies executable examples. The Qt and Vue
  harnesses paint production controls. The gallery covers 372 paired states:
  three styles, dark/light, EN/RU, 900/360 logical pixels, normal, disabled,
  read-only, error, loading and long labels; actual hover/press/keyboard focus.
  Comparison checks 11,724 rectangles, 6,696 typography/color values and
  228 indicators, 5,436 text origins/baselines/advances and 2,292 icon
  glyph/geometry checks. Actual input runs at scales 1/1.5/2. Native IME uses Qt input
  events; browser composition remains simulated DOM input.

Reproduction:

```
python tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
python tools/frame_controls/capture_qml.py
node frontend/tests/frame_controls.mjs
python tools/frame_controls/report.py
```

The platform gate now has 16 steps and runs 20 actual native tests at each of
three scales, browser platform/control input, two normal smoke tests and a
clean independent wheel. Update-archive validation separately checks recursive
modules and rollback. Release reports must verify source fingerprints again
following any source change. The controls gallery is
`tools/frame_controls/output/index.html`; the broader Administration comparison
remains `tools/frame_admin/output/index.html`.

Explicit boundaries: two offscreen menu cases fail identically against the
archived and current Handler. `tools/frame_controls/check_menu_baseline.py`
records that comparison; it does not mark either case passed. Native popup
mouse grabs/compositor behavior still require a real Windows backend. The old
`sidebar_editor.mjs` end-to-end journey still expects pre-Frame child dialogs
and immediate save; its remaining port belongs to phase 3, and it is not a
passed release check. Current Frame acceptance uses `administration.mjs`, the
paired Sidebar driver and native/controller regressions. Original-wide screen
fidelity, window ownership and the complete Help pilot remain later phases.

## Phase 0 delivered, 2026-10-15

Handler 0.6.0.97 / Stream 0.112.146. The findings below describe the review
baseline; the preparation blockers have now been resolved. Later phases remain
open. Both products still ship independent local modules and native controls.

- Array-backed native lists now index immutable records once and materialize
  only visible keyed rows plus overscan. The existing native role-model path
  remains direct. Reordering preserves the actual editor, draft, caret,
  selection and IME preedit; removing a row cannot transfer its edit to the
  successor. Persistent drafts remain the feature owner's responsibility.
- Frame text uses named logical-pixel roles and complete native font values.
  Deployed Frame sizes are preserved. The ordinary window smoke now passes
  with zero font warnings; the archived baseline produces 50. Other native
  controls retain their existing typography contract until their migration.
- Browser size deliveries merge per observed target and release pending work
  on disposal. Model updates use the actual DOM scroll position, including
  when a scroll event has not yet reached reactive state. IME Enter does not
  invoke commands; unusual control IDs are escaped during lookup.
- Scene contracts validate kinds, sibling IDs, finite geometry, text roles,
  required models/views and record keys. Missing required slots fail early;
  platform-optional slots must be explicit. Eight duplicate button builders
  were removed. No parser, runtime dependency or embedded browser was added.
- A reproducible source inventory records native/Vue surfaces, registered
  windows, docks, entry owners and hashes. Runtime script/plugin/configuration
  inputs must still be supplied for their own acceptance; source discovery is
  not a claim that every window was exercised.

Measured with the same real Qt list fixture, three reverse updates per size:

| Records | Before: median update + frame | After |
| ---: | ---: | ---: |
| 1,000 | 376.90 ms | 11.47 ms |
| 4,000 | 5,816.32 ms | 52.85 ms |

These local software-rendered measurements establish the removed quadratic
path; they do not certify full-application FPS, GPU behavior or production data.
The 10,000-record regression separately checks bounded delegate creation.

The focused gate is one command, with isolated settings, per-step timeouts,
owned-process cleanup and source fingerprints:

```
python tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
```

All 13 steps passed: format, module/guide sync, scene contracts, 20 renderer
registrations, resize lifecycle, eight discovery/sync tests, five actual native
input tests at scales 1/1.5/2, browser input at those three device scales, two
ordinary window smoke tests, a clean independent wheel and source inventory.
Native IME uses actual Qt input-method events; browser composition is simulated
with DOM events, not a physical OS IME session.

Release regression also passed 249 native tests and all 14 browser suites:
2,340 paired Administration states, 98,414 geometry checks, 60,798 style checks
and 4,622 internal-indicator checks. Captures were refreshed and their source
hashes checked. This verifies current Frame-to-Frame behavior; the remaining
original-Handler visual closure is still phase 3.

Current evidence: `tools/frame_foundation/output/index.html`, source inventory
`output/inventory.html`, machine-readable gate `output/platform/gate.json` and
full paired gallery `tools/frame_admin/output/index.html`. Regenerate reports
after source changes. Existing whole-repository structure/lint debt remains
visible; no warning budget was raised. Next is phase 1 plus the complete Help
vertical pilot, not another wholesale screen rollout.

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
| 0. Preparation — complete | Fixed findings, source/entry inventory, executable brick contracts and original reference | Focused 13-step gate and full current Administration regression passed; runtime-generated surfaces still require their real inputs |
| 1. Controls — in progress, verified subset | Inventory all reusable families and inline variants, then finish their shared contracts and paired standalone scenarios; the current gallery is a subset | Real normal/hover/pressed/focused/disabled/loading/error states in both engines; EN/RU, themes, narrow/wide and DPI; same semantic events; family-specific gaps remain explicit in the atlas |
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
| Frame directory structure/readability | Complete for migrated code | 47 recursive modules, 73 formatted native renderers/adapters; separated Administration domains and shell/windows, shell/docks; public QML type index; independent clean wheel and native update archive checked |
| 1. Theme/type/metrics/motion | Implemented and checked | 12,708 archived/current TH checks; 3,178 browser checks; styles, custom palettes, independent motion preferences and reduced motion |
| 2. Controls and interaction | In progress; verified subset | Shared state paint and metrics; 372 paired states of the current sample, actual mouse/touch/keyboard at three scales, shared Sidebar tree and specialized Grid. The full source atlas distinguishes primitives/composites/infrastructure/forms and lists unverified families. Windows compositor/popup-grab cases and original-wide screen parity remain explicit above |
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
were raised. The archived offline smoke emits 50 point/pixel font warnings;
the current run loads/reopens/closes the same registered windows with exit code
0 and no warnings. Both ordinary smoke regression tests now pass. Structure
and lint debt remain separate from the resolved Frame typography defect.

Current Administration reports were refreshed with source hashes after the final
changes. They compare Frame implementations; original-wide parity is not implied.
No live database or user configuration is part of these fixtures. The local
evidence entry point is `tools/frame_foundation/output/index.html`.
