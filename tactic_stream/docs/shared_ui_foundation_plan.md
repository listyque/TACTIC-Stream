# Tactic Frame: architecture review and complete UI migration plan

Started 2026-10-15. This replaces the previous screen-first migration order.

## Execution plan: full-day batches, revised 2026-10-16

This is the current execution order. The phase IDs and release checkpoints below
remain the coverage map and evidence history, not separate user-sized tasks.
Preparation is delivered; verified parts of controls and shell stay delivered.
Start with **B01** and close its remaining workflows before moving to B02.

Each batch targets roughly **eight hours of complete engineering work**: inspect
the original and dependencies, implement both hosts, exercise real workflows,
compare appearance, fix regressions, update documentation and commit/backup.
This is a work-sizing target, not a measured delivery promise or an eight-hour
stop condition. Graphs, tables, queues and platform defects may take longer.
Re-estimate from actual completed batches; do not manufacture work to fill time.

| Batch | Complete deliverable | Acceptance specific to the batch |
| --- | --- | --- |
| B01. Main workspace and host lifecycle | Finish the remaining phase-2 window/dock/session work as one integrated shell: menus, navigation, projects, search/section tabs, floating/stacked docks, layout save/restore, ownership/focus and desktop/phone transitions | Change project/tab, edit a draft, move/stack/float/close/reopen docks, restart/restore, resize, logout/expire/login and repeat. Preserve drafts, active section and layout; stale callbacks and hidden/signed-out views must not keep requesting. Reuse the already migrated paint and input; repair remaining integration gaps rather than redo it |
| B02. Control kit and usable catalog | Close the remaining reusable-control families in the source atlas: all button variants, fields/search/text areas, checks/radios/switches, date/time/calendar, selects/user/icon/color pickers, tabs/badges/avatars, menus/popovers/tooltips, list/tree/table/graph/code/document control contracts, scrolling and splitters | Distinguish primitives, neutral composites, infrastructure and domain forms; provide executable examples and state coverage for every family. Align text/background, typography, icons, geometry and interaction; keep rendering/platform limits explicit. Domain screen migration remains in its own batch |
| B03. Administration original-reference closure | Review and correct the entire existing Frame Administration against original Handler: Groups, Users, Access, Search Types, Schema, Workflow/process rules, Columns, Raw database, Layouts, Sidebar and Naming, including child editors | Real create/edit/save/cancel/error/dirty-close and cross-editor journeys. Verify graph connections, process/pipeline settings, XML/JSON, ACL and unknown-write handling. Complete original-to-Frame comparisons, not just Frame-to-Frame comparisons |
| B04. Support, identity and connection lifecycle | Complete the shared composition of Help, errors/confirmations, Debug Log, UI performance view, profile, sign-in/presets/connection status and update shell; retain already verified Help behavior | Contextual Help launch/reopen/positions, log search/filter/export, profile validation, connection errors, session expiry/relogin and update reopen/close. Native updater/local operations and server/browser operations keep explicit capabilities and their existing owners |
| B05. Configuration and projects | Configuration navigation and every existing settings page, project creation/editing/templates and related child forms; common layout with declared client-specific settings | Apply/Save/Reset/Close, unsaved guards, validation, reconnect/restart, secrets, project/template changes and return to the workspace. Preserve persistence and useful product-specific options; both standalone packages remain usable |
| B06. Search workflow and card results | Complete the search workspace: query cards, quick/process/advanced filters, tag cloud, saved searches, paging/continuous loading, sorting/grouping, selection, result cards and their menus | Compose and save a query, restore tabs, change filters/tags/view, load more, select/open objects and return without lost context. Verify actual request/filter effects, long labels, empty/error/offline states and phone input |
| B07. Table View, active widgets and editor | Complete the table host and column/view editor; migrate adapted Handler cells and every usable widget referenced by the widget-config inventory, including related pickers/popovers | Exercise real rows, selection, column sizing/order/visibility, sort/group/paging, inline/batch edit, validation/save conflicts and editor persistence. Document each supported widget with a working example. Clearly unfinished legacy implementations remain explicitly excluded; never count an unsupported placeholder as delivery |
| B08. Objects and inspector docks | Object report, description/notes, previews/snapshots/files, process/task fragments, links, create/edit/delete/duplicate and watch-folder editor, including all child surfaces | Selection/tab/project changes preserve drafts and context; same actions, confirmation/ACL/error behavior and native file adapters. Inspector remains a dock with correct float/stack/reopen behavior; test an end-to-end object journey |
| B09. Task Manager and task inspector | Complete task list/table, scope/filters, status/assignment/date editing, task inspector, bulk actions, layouts and desktop/phone composition | Filter and select tasks, edit through real pickers, perform existing bulk operations, save/cancel and reopen across task/project changes. Keep permissions, request generations and mutation owners; do not substitute a visual fixture for production operations |
| B10. Production Gantt and calendar | Integrate the existing shared Gantt proof into production: dependencies, scheduling, drag/resize/zoom, milestones, undo and save/conflict behavior; calendar remains its separate dock | Compare original and both production hosts on the same schedule; verify actual saved changes, drag cancellation, undo, conflicts, range/selection/scroll retention, realistic data sizes and touch/phone interaction |
| B11. Messaging and activity | Conversations, retained message views, composer, attachments, members, emoji/search popovers, notification history and activity feed as one communication block | Immediate cached conversation switching, independent drafts/read/scroll positions, send/newline rules, anchored popovers, uploads/failures and reopen. Repeated hide/logout/expiry must stop requests; real server effects and desktop/touch paths are required |
| B12. Files, check-in and repository queues | File workspace/changelist, ingest/check-in, Commit Queue, Repository Sync queue/editor, matching templates, repository editor and screenshot tools | Complete an actual file-to-check-in workflow plus queue cancel/retry/reopen and synchronization. Preserve file identity, progress, repository rules and large-queue virtualization. Native filesystem/DCC and available browser integrations use their declared capabilities, never fake parity |
| B13. Scripts and standalone tools | Script Editor, shelf/triggers, Batch/Database tools, Handler Server, DCC options and standalone entry points; share corresponding shells/commands without replacing the execution system | Open/run/cancel/save scripts, launch standalone Batch Manager with native QML UI, target the selected DCC client and recover from failures. Preserve Python/QML execution and script-created menus/UI; no embedded browser or forced rewrite of user scripts |
| B14. Remaining surfaces and release closure | Knowledge base/journal/API documentation, remaining client-specific surfaces and inventory gaps; remove superseded layouts and perform the integrated release audit | Every inventoried surface is accepted, intentionally client-specific or explicitly excluded. Exercise long sessions, repeated reopen/project changes, larger collections, independent packages and restore points. Record remaining platform/debt limits; no competing old/new runtime layouts or blanket parity claims |

### Batch working rule

- A request to continue the plan means completing the next whole batch. A button,
  picker, menu, screenshot report or individual subsection is an internal
  checklist item, not a separate delivery or a reason to request another prompt.
- Keep one batch active. Resolve routine dependencies and regressions within it;
  if an external blocker genuinely prevents completion, record exactly what is
  blocked and continue independent work in that batch. Never silently rename a
  partial batch complete or move its unfinished features to a later batch.
- Every batch includes original Handler → Frame Handler → Frame Stream evidence
  on matching data/theme/language/size, actual mouse/touch/keyboard where relevant,
  focus/scroll/drag/IME, loading/empty/error/disabled, EN/RU, light/dark, three
  themes and affected DPI/phone layouts. Check mutations and persistence through
  existing owners separately from screenshots. Recheck source fingerprints.
- Run focused tests while iterating, then the required platform gate and affected
  integrated journeys on the final sources. A screenshot count alone does not
  establish completion. Update the atlas/examples and EN/RU Help, review both
  diffs, commit each changed product separately and verify NAS backup.
- Common control fixes belong to the common owner and both renderers when
  applicable. B02 owns complete family coverage; later batches extend the same
  kit when a real workflow reveals a missing state, rather than fork local styles.
- Runtime controllers, ACL, configuration and persistence keep their existing
  owners. Products ship separate physical Frame copies. No WebEngine, automatic
  QML translator, second store or forced conversion of native-only tools.

The user-facing checkpoint reports the **whole batch**, its remaining gaps and
evidence. This revision changes planning only; it does not mark any additional UI
implemented or rerun the previous release's acceptance.

## Phase 2C: section rail and color evidence, 2026-10-16

Handler **0.6.0.104** / Stream **0.112.153**. The independent products now ship
64 `.mjs` modules and one menu catalog. `controls/tabs/section.ui.mjs` supplies
panel and row geometry/paint, badge contrast, label and close positions, context
action records and vertical drag target decisions. The existing section models,
commands, loaded workspaces, ACLs and saved formats remain their owners.

- Preserve archived collapsed/revealed/current/pressed composition, scrolling,
  delayed hover collapse and section identity. Native buttons and pointer grabs
  remain native; browser overlays keep real buttons and touch handling. Keyboard
  activation stays manual on the vertical rail. Close never also selects a row.
- Both hosts use the same row-Y drag target and threshold. Native drag no longer
  misses collapsed neighbors by hit-testing at the wide panel's X midpoint.
  Escape, focus loss and model removal/reset cancel native drag without committing
  a reorder; browser input retains Escape/capture-loss/resize/model-change cleanup.
- Right click / Shift+F10 and a 500 ms touch hold open the same action records and
  shared menu rows. Disabled boundaries are preserved. Native actions resolve the
  current section index from its stable ID at dispatch. A browser long touch
  reopens after native light-dismiss settles; pending callbacks are cancelled on
  new input/disposal. First tap activates exactly once without a hover layer
  appearing between press and release. The native hit area only reserves the close
  target when its control is visible, preserving an immediate first mouse click
  throughout the opening animation.
- Frame preview fallback text now uses contrast against the darkened actual
  preview accent, matching native ItemPreview. Unknown nonempty browser icon names
  now show the native warning fallback. Actual color properties are captured and
  compared alongside bounds; captures align focus/hover rather than comparing an
  automatically focused Qt card with an idle browser card. Chromium screenshots
  use grayscale text, separating LCD antialiasing from the actual color role.
  Box corner overrides retain the other radii: browser badges remain circular.
  Captures compare all four actual badge corners as well as their colors.

Acceptance: `tools/frame_projects/capture_qml.py`,
`frontend/tests/frame_projects.mjs --capture`, and `tools/frame_projects/report.py`
compare 60 archived/current/browser states in three themes and EN dark/RU light.
The mandatory platform gate includes native section input at scales 1/1.5/2,
actual browser touch/drag/menu input, retained search/dock workflows and independent
packaging. Related disposable-server navigation/session and real main-window
scenarios remain required for release. This closes section-rail composition,
not the remaining workspace session/layout closure or all of phase 2C.

## Phase 2C: project chooser and search tabs, 2026-10-16

Handler **0.6.0.103** / Stream **0.112.152**. `shell/projects.ui.mjs` now owns
popup/header/category-grid and expanded-card composition. The independent shipped
copies contain 63 `.mjs` modules and one menu catalog. No embedded browser,
shared runtime bundle, new store or dependency was introduced.

- Existing project discovery/ACLs, preview cache, availability filters, category
  order, selection commands and session owners remain in place. Empty category
  fallback is translated in the view; actual server category names remain data.
- Expanded cards preserve archived geometry, preview, lifecycle chip, title,
  two-line description and metadata. The chooser reserves a 12 px scrollbar
  gutter instead of placing cards beneath it; full desktop cards are therefore
  4 px narrower than the archive. Active project selection is passed in native
  QML too. Compact configuration cards retain their original implementation.
- Stream uses two/one columns on phones and a taller filter header for Russian
  wrapping. Configuration's inline chooser shares the same grid. Native and
  browser filters, mouse/touch selection, Escape and bounded project arrow/Home/
  End navigation use real house controls; availability is never a client ACL.
- `controls/tabs/workspace.ui.mjs` owns search-tab paint and tab-key decisions.
  Existing animation timing preferences and real close targets remain present.
  Native search adapters keep activation, close and reorder in workspaceState;
  browser adapters emit to their existing owner. Focus follows surviving tabs.
  Section rails share dimensions and manual-activation keyboard decisions, but
  their full paint/gestures are still pending. This does **not** close phase 2C.

Acceptance is reproduced by `tools/frame_projects/capture_qml.py`,
`frontend/tests/frame_projects.mjs --capture`, `tools/frame_projects/report.py`,
`tools/frame_navigation/check_workflows.py` and the mandatory platform gate.
The report compares 36 archived/current/browser states (md3/material5/fluent,
EN dark/RU light, chooser/card/search-tab variants) and rejects stale source
fingerprints. Related workflows cover project navigation, saved workspace restore
and expired-session request suspension on a disposable server. The platform gate
includes project/tab input at scales 1/1.5/2. Full section-rail composition,
Windows compositor fidelity and physical phone input remain outside this block.

## Phase 2C: navigation container, 2026-10-16

Handler **0.6.0.102** / Stream **0.112.151**. The complete navigation drawer now
uses `shell/navigation.ui.mjs`: panel width, header positions/typography,
divider/list insets, exit threshold and keyboard decisions. Both products ship
61 `.mjs` modules and their own menu catalog; there is no runtime sibling import.

- The archived Handler remains the geometry reference. Native buttons, list
  recycling and scrollbar remain house controls; Vue uses the same positions,
  its real buttons and a stable scrollbar gutter. Stream's phone slots for open
  sections and dock selection remain available without a desktop rail.
- Opening retains the scroll position and focuses the panel. Arrow keys enter
  the available rows; Home/End also work before a row is focused and include
  recycled off-screen rows and skip hidden/disabled/separator records. Right/Left
  expand/collapse and enter/leave groups; Escape/close/selection restore focus.
  Qt's built-in ListView navigation no longer overrides these decisions.
- Hover dismissal is armed only after entering the panel in that opening, then
  requires moving more than 120 px beyond its edge. Touch never uses this rule.
  This also fixes the archived native drawer closing while approaching it from
  a central opener. The native selected row now follows the controller's section.
- Script/sidebar definitions, availability/ACLs, existing asynchronous loaders,
  project/session stores, loaded content and saved formats retain their owners.
  This closes the drawer container only: project chooser, section/search-tab
  composition and the rest of phase 2C still remain to migrate.

Acceptance: paired real components and translated captions pass all 12 cases.
Mouse/touch/keyboard, retained scroll through close/reopen and live language
changes, temporary-server project/history/session restore and expired-session
request suspension have passed. The platform gate runs 29 steps, including
36 native checks at each of scales 1/1.5/2. The final run is recorded by its
source fingerprints in `tools/frame_foundation/output/platform/gate.json`.
Reproduce with `tools/frame_navigation/capture_qml.py`,
`frontend/tests/frame_navigation_drawer.mjs --capture`,
`tools/frame_navigation/report.py`, `tools/frame_navigation/check_workflows.py`
and the mandatory platform gate. The report compares 12 archived/current/browser
states (md3/material5/fluent, EN dark/RU light, 900 and 320 px), with 864 real
container/header/list/row measurements. Native/browser rasterization and the
Windows system compositor are not claimed identical.

## Dock focus/footers and main menus, 2026-10-16

Handler **0.6.0.101** / Stream **0.112.150**. The requested next two bounded
blocks are implemented: dock keyboard focus/footer composition, then the main
user/configuration/connection menus. This does not close all of phases 1 or 2.
The products ship 60 `.mjs` modules and one data catalog independently.

- `shell/dock.keys.mjs` owns Left/Right, Home/End, Enter/Space, Delete for
  closable panels and Ctrl+Shift+Left/Right reordering. Each host transfers
  focus to the visible delegate after model updates; closing the final tab
  returns it to the surviving panel/header. Hidden slots and persisted layouts
  retain their existing owner. `dock.surface.mjs` owns footer height, divider
  and corners; a native dialog's outer frame remains an explicit capability.
- `shell/main.menus.json` is the default action catalog. `main.menus.mjs`
  selects platform, privilege, phone/desktop and update-mode actions without
  executing them. `controls/menus/action.ui.mjs` paints the same row geometry,
  icons, titles, badges, checks, status, hover/press/focus in both renderers.
  Existing popup, input, command, settings, errors and authentication owners
  remain in place. No embedded browser or new dependency was introduced.
- Native `MenuRegistry.replace/extend` and arbitrary script command records
  remain supported, including nested menus, accent/avatar records and
  secondary actions. Handler's repository sync/watch/server/update/exit and
  Stream's shelf/queue/tasks/timesheet/project/API/mobile actions are explicit
  catalog capabilities. UI visibility never substitutes for server ACLs.
- Native/button painting no longer masks Frame's row text and icons; the
  same correction applies to the previously extracted navigation row. Accessible
  names and real house-control input remain present without a duplicate label.

Reproduction: `tools/frame_menus/capture_qml.py`,
`frontend/tests/frame_menus.mjs --capture`, `tools/frame_menus/report.py`,
`tools/frame_menus/check_workflows.py`, plus the platform gate and existing dock
capture drivers. The menu report contains 18 original/current/browser cases
(md3/material5/fluent, EN dark/RU light), footer corner measurements, matching
common action rows and visible platform-only differences. These are real
ActionMenu/AppMenu components on fixed records, not an assertion that native
popup windows and DOM popups use the same OS compositor. Real input tests
exercise native popup ownership separately; full-application browser tests
use a disposable local server/database for commands, connection failure/retry,
stale project replies, logout guards, settings persistence and touch at 320 px.

Acceptance: the final Frame gate passed all 28 steps, including 34 native
checks at scales 1/1.5/2. Seven additional native menu/access/submenu checks,
the two shipped-application browser workflows and the six-size main-window
comparison passed. The menu report checks 846 archived-native values and
1,848 actual Qt/Vue values; the refreshed dock report checks 504 rectangle
values across 24 layouts. The quality comparison introduces no new failure or
warning category: structure failures decreased from 11 to 9 and unqualified
warnings from 6,615 to 6,526; the 114 missing-property warnings remain legacy
debt. Native smoke has no runtime/font warnings. The catalog classifies
ActionRow as a primitive, ActionRows as a composite and the footer as a layout
control; this does not turn all menu/scroll variants into verified families.

Full navigation-container and project/tab/session composition remain next.
The original archive is preserved. Older Help/control/Admin reports remain
historical until their own fingerprints are refreshed; a current focused gate
is not full legacy UI acceptance.

## Phase 2B: dock trees and gesture acceptance, 2026-10-16

Handler **0.6.0.100** / Stream **0.112.149**. This completes the next bounded
part of 2B: recursive projection/minimums, resize/restore, visible-tab ordering
and all floating edges. The current release has 56 portable modules.

- `shell/dock.layout.mjs` is the single geometry implementation. Native Python
  dataclasses/settings remain the state owner; a small application-owned Qt JS
  evaluator runs the shared module. Vue invokes it directly. No browser, runtime
  sibling import, new dependency or replacement settings store is introduced.
- The old browser 240×160 per-divider limit and duplicated native geometry are
  removed. Both products use `window.sizing.mjs`, recursive subtree minimums and
  proportional projection when space cannot fit all panels. Host shrink/grow
  preserves preferred ratios. Native OS minimum-window constraints and Stream's
  phone presentation remain product capabilities rather than fake equivalence.
- Visible-tab reorder preserves hidden slots. Mouse and touch use the same
  threshold. Escape cancels a reorder without saving. Native release no longer
  accesses a deleted delegate, and a cancelled grab cannot commit its preview.
- All four floating edges and four corners use one sizing rule. Native handles
  are above the panel body; the title no longer steals the top-left resize.
- Real Qt/browser input covers nested split limits, keyboard divider resizing,
  mouse/touch tab reorder, cancellation, save/reload and floating minimums.
  58 related native checks include retained loaded content across layout changes.
  The platform gate includes four new native input tests at scales 1/1.5/2,
  the full tree regressions and five content-retention scenarios.
- `tools/frame_docks/output/index.html` records 24 archived/current/browser
  layouts and 504 rectangle comparisons at 1800×1000, 1100×800 and 760×640.
  The oracle is the independently archived Handler Python algorithm and minimum
  map. Real DockPanel/DockWorkspace shells have deliberately empty feature
  contents: this report establishes dock geometry, not whole-screen fidelity.
  Source fingerprints are verified. Reproduce with `tools/frame_docks/capture_qml.py`,
  `frontend/tests/frame_dock_capture.mjs` and `tools/frame_docks/report.py`.

**Still open before closing all of phase 2:** complete dock-tab keyboard/focus
paths and remaining footer/chrome states, then main menus, navigation containers
and project/tab/session composition. Keep procedural `MenuRegistry.replace/extend`.
Native Windows compositor, popup grabs and separate OS windows still need their
real-backend acceptance. Prior reports below are historical checkpoints and must
be regenerated before being used as evidence for this release.

## Phase-2 acceptance breakdown: historical checkpoint, 2026-10-16

The dependency order remains valid. Phase 1 stays open: a complete source census
and a verified control sample are different deliverables. Phase 2 consumes and
verifies the controls its real workflows need; it does not silently mark the
remaining atlas gaps complete. The previous phase-2 row was too broad for one
acceptance decision and is now split into these checks:

| Part | Deliverable | Required evidence |
| --- | --- | --- |
| 2A. Window hosts and Help pilot | Shared Help composition/state, neutral document reader, matching file/link actions, cached reopen and per-document positions; owner/modality/focus and close lifecycle | Original/current native and Vue captures; actual search, keyboard, links, file export, language, phone reflow and reopen; hidden views do not reload |
| 2B. Dock interaction | Shared snap/target/gesture rules, stacks/tabs, floating drag/resize, cancellation, footer/corners and saved layout | Real first click/tap, tab activation/reorder, close/maximize/restore, cancel/blur, detached native capability and browser floating capability |
| 2C. Main workspace closure | Main menus/navigation, search-tab presentation and layout restore use the checked host controls | Project/tab changes preserve drafts, selection and layout; no hidden/signed-out polling; affected original/native/browser workflows |

Keep the existing controllers and product-specific persistence/OS operations.
The common layer owns layout and presentation transitions. Do not add a second
window manager, a second document loader, runtime sibling imports or a browser
inside QML. A generic document reader is a control; Help is the feature composed
from that reader, search, topic rows and toolbar actions.

Delivered in Handler **0.6.0.99** / Stream **0.112.148**:

- **2A is implemented and checked as the first complete workflow pilot.** One
  `features/support/help` composition/state module pair drives both adapters.
  `DocumentPane` is a neutral composite, not a second Help screen. Search,
  contextual navigation, source/download, per-article positions, retained reopen,
  owner close, language and phone topics use the checked paths. Early scroll
  is retained even before a browser animation frame; `open()` waits for restore.
- The Help comparison records **24 current Qt/browser pairs**, **48 original/current
  native captures** and **2,460** actual geometry, typography and article-text
  comparisons on one corpus. It covers md3/material5/fluent, light/dark, EN/RU,
  1100/320 px. Source and article fingerprints are enforced. The original's
  missing glyph and lack of phone reflow are recorded separately. Native
  QTextDocument and browser Markdown retain different painting/layout internals;
  the article body is not declared pixel-identical.
- **2B has a checked interaction foundation, not full dock-tree acceptance.**
  Shared placement owns edge/header/center decisions, previews, drag threshold
  and release/cancel outcome. Float keeps its structural slot; Dock restores
  it. Native cancellation no longer commits previews; floating title movement
  stays separate from docking. Real mouse/touch cover first activation,
  close/maximize/restore, stacking, cancellation and saved active tab. The
  original/current native header comparison and browser cases remain required.
- **2C has the neutral navigation row migrated.** Its shared control description
  preserves section/link/separator layout, icons, badges, depth and selection;
  routing, filtering and availability remain with the existing feature owners.
  Eight original/current/browser cases check 448 inner geometry values.
  Existing main-toolbar and typed-window scenarios remain release checks.

Reports: `tools/frame_help/output/index.html`,
`tools/frame_foundation/output/navigation/index.html`, and the existing control
atlas/gallery and Administration index. Reproduction adds
`tools/frame_help/capture_qml.py`, `frontend/tests/frame_help_capture.mjs`,
`tools/frame_help/report.py`, `tools/frame_foundation/navigation_qml.py`, and
`frontend/tests/frame_navigation_capture.mjs` to the phase-1 commands below.
The platform gate now includes these actual input workflows at three native
scales, the 19 window-kind mappings, eight Help launchers and dock rollback.

The built application's static JavaScript dependency graph remains 27 files.
Summed gzip size changed from 784,046 to 793,704 bytes against the preceding
checkpoint (+9,658 bytes, 1.23%). Chunk movement alone is not a payload regression;
do not add asynchronous renderer ownership without a measured need and readiness
checks for first focus/action. The phase-1 and original checkpoint sections below
retain their historical counts; they are not the current release totals.

**Next acceptance block at this checkpoint was 2B/2C:** complete projected dock-tree/minimum-size
parity, all tab reorder/focus paths and corners, then the complete main-menu,
navigation-container and project/tab/session composition. Keep the native
`MenuRegistry.replace/extend` runtime contract; a static replacement menu would
silently remove script capabilities. Do not close phase 2 from a matching toolbar,
neutral row, self-comparison or source inventory. Phase 1's unverified families
also remain open. Real Windows compositor/native file-picker interaction still
requires the Windows backend, separately from offscreen Qt and headless Edge.

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

## Domain coverage map (phase IDs; not execution batches)

The full-day batches at the top of this document define the current execution
order and delivery size. This table retains the domain coverage and original
phase IDs referenced by earlier checkpoints; it is not a second active plan.

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

File counts do not justify a delivery estimate. The eight-hour batch target above
sets the intended working scope; recalibrate it using actual completion time and
remaining defects. Workspace lifecycle, table editing, messaging, file queues,
graphs and standalone scripts have the greatest uncertainty. Do not reduce their
acceptance or claim completion merely to fit one day.

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
