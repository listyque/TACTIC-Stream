# Shared UI: foundation → controls → hosts → shell → screens

Started 2026-10-15. This replaces the previous screen-first migration order.

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
| Invisible uncolored graph connections | Fixed in common calculation; render checks pending | Default, source color, explicit color; real pixels in Qt and browser |
| Frame directory structure | In progress | Imports, recursive sync, packaged QML and modules, real screen load |
| 1. Theme/type/metrics/motion | Pending | Compare original TH across supplied styles/palettes; both clients consume same definitions |
| 2. Controls and interaction | Pending | Actual input and all reachable states, glyph hit areas, scrolling and clipping |
| 3. Windows and docks | Pending | Modal/nonmodal, title/grip drag, focus, resize, stacking, persistence |
| 4. Main window | Pending | Common shell layout/actions, explicit platform capabilities and mobile layout |
| 5. Screen contents | Pending | Original TH reference, complete operations and per-screen inventory; never infer readiness from a common wrapper |

Each screen requires two comparisons: original Handler → Frame Handler, then
Frame Handler → Frame Stream. A matching pair of redesigned screens does not
establish fidelity to the original. Existing reports establish only what their
fixtures actually measured; the Administration-wide visual parity claim is
withdrawn pending comparison to the independent original.

The first original comparison confirms a substantial workflow layout drift:
the Frame inspector places generic position fields before process settings,
uses a different panel composition and lacks the original top-level Pipeline
settings action. These regressions must be repaired, preserving existing
workflow-library and server operations rather than deleting functionality.
