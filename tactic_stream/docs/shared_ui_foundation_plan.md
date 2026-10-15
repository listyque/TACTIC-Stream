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
