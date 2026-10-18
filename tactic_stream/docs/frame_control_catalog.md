# Tactic Frame control kit (B02)

The B06 search migration adds the house `VirtualCollection` adapter to the list
family. Its shared geometry packs variable-height rows/tiles; the Vue adapter
owns measured delegates and offscreen keyboard focus, while Qt retains native
ListView/GridView. Search forms and record operations remain feature composition;
see `docs/frame_search.md` for the owner map and the 100/1,000/10,000-entry checks.

The kit is the vocabulary for shared screens, not a collection of independent
QML and Vue forms. A primitive handles one value/action; a neutral composite
accepts ordinary records and emits intent. Infrastructure handles input,
positioning and lifetime. Domain forms retain requests, permissions, drafts,
validation and writes.

The reviewed registry is `tools/frame_controls/element_catalog.json`. Its 27
families include infrastructure and domain boundaries; they are not 27 primitive
types. `controls/catalog/variants.mjs` supplies 144 executable examples. Each
example has an ID, family, named house control and neutral values. Both hosts
consume the same example, layout and transition functions. There is no server,
project, ticket, runtime translator or browser embedded in QML.

## Use the catalog

From the Stream checkout, build the self-contained browser artifact:

```powershell
node frontend/tests/frame_control_catalog.mjs
```

Open `tools/frame_controls/output/catalog.html` directly from disk. Choose a
family/example and use the control. Theme, language and width changes retain the
value; choosing another example or Reset restores that example. The event trace
shows intent. Fonts are embedded; the artifact makes no HTTP requests.

The native catalog uses the actual independent Handler checkout:

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/capture_variants.py --interactive --example packed-choices
```

It opens a QML window with example/state/style selectors and palette/language
buttons. Resize it normally. It uses the production Windows/OpenGL backend and
the normal native file chooser; close the window to exit. No application session
or user settings are loaded. It does not run Python/JavaScript from a server.

## Where changes belong

| Responsibility | Shared source / house controls |
| --- | --- |
| Numeric clamp, localized parse/format | `controls/forms/number.mjs`; SpinBox / `controls/forms/AppSpinBox.vue` |
| Segmented selection and keyboard targets | `controls/forms/segmented.mjs`; SegmentedButton / AppSegmentedButton |
| Calendar parsing and day slots | `controls/forms/calendar.mjs`; DateField / AppDateField |
| Chip geometry, packing and visible rows | `controls/display/chips.mjs`, `controls/lists/chips.mjs`; QuickFilterChip and QuickFilterOptions |
| Surface composition and examples | `controls/display/surfaces.ui.mjs`, `controls/catalog/variants.mjs` |
| Theme roles, pixel fonts and control metrics | `core/foundation.mjs` |
| Actual native controls | Handler `thlib/ui/qml/controls`, public names exported through `qmldir` |
| Actual browser controls | Stream `frontend/src/controls`, new parts grouped into actions, forms, display, layout, lists and typography |
| Host-only catalog adapters | Stream `tools/frame_controls/ControlsExample.vue`; Handler `tests/fixtures/frame_controls/ControlExample.qml` |

The adapters only connect house props/events and neutral local models. They do
not implement another picker, painter, editor or reducer. Legacy named controls
keep their public imports and APIs. The products ship separate physical copies
of the portable modules; synchronize explicitly with `tools/sync_tactic_frame.py`.

Examples cover buttons/counts/disclosure, mixed/compact/prominent checks,
segmented groups, fields/search/areas, selects/users, numeric/date/time controls,
icons/color/emoji/image selection, tabs/chips/identity, previews, headers/field
frames, list rows, menus, feedback, drag-target presentation, scrolling, splitters
and neutral tree/Grid/Graph/Code/Document contracts. A 1000-record choice flow
exercises virtualization without fetching data.

`UserAvatar` is a profile lookup adapter; ItemPreview is the neutral avatar.
ActivityCalendar is a feed filter, not the DateField calendar. CompletionStrip,
attachments, process trees, script outlines and NodeGraph know their domain.
Their complete screens remain in their assigned batches. Original presence-dot,
skeleton, emoji-recents and generic range/multiselect/vertical-slider wishlist
names have no finished neutral implementation to copy; exclusions are recorded
with reasons rather than filled with invented controls.

## Reproduce acceptance

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/capture_variants.py --native
node frontend/tests/frame_control_variants.mjs
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/report_variants.py
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/capture_qml.py
node frontend/tests/frame_controls.mjs
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/report.py
.venv/Scripts/python.exe -B -X utf8 tools/frame_controls/elements.py --handler-root D:/code/th_codex
.venv/Scripts/python.exe -B -X utf8 tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
```

The expanded report requires all 24 theme/palette/language/width combinations,
matching native/browser geometry and text styles/colors, actual PNGs and current
source hashes. `--quick` is iteration evidence only. The original 372-state
gallery retains opened controls, real hover/press/focus and detailed glyph/input
checks. The gate additionally executes expanded real input at 1/1.5/2 scale,
recreation/disabled/readonly lifecycle, file validation, Grid drafts, Code edits,
Graph select/move, two-axis scrolling and chip virtualization. The offline
artifact and source-atlas filters are tested as delivered HTML files.

The report retains Qt/DOM text-origin/baseline/advance diagnostics, including
rounding of fractional text metrics, wrapping and elision. These are not silently
counted as passing pixel comparisons. Bundled icon identities, font sizes,
semantic colors and layout bounds are separate checks. Color emoji are bitmap
glyphs; their unused Text.color is not their painted pixel color. Qt software
does not prove rounded photo masks; Windows/OpenGL evidence does. Browser
fallback select/scrollbar and native system file dialogs keep their platform
appearance. Automated IME/selection and synthetic touch do not replace physical
OS IME, touch hardware, rasterizer and compositor acceptance.

## Files control variants (B12)

The files migration also exercises the existing TabButton variant (`Button.tab`),
editable Choice, multiline checkbox captions and character-wrapped notices.
Graph content can scale its paint around the top-left origin. These are variants
of the same house controls, not new feature-local controls. Both renderers keep
child view/model descriptors inside passive action paint and reveal focused
checkboxes in scrolling forms. `controls/forms/toggle.ui.mjs` composes a switch
and a passive caption without reducing the primitive's hit target;
`controls/buttons/metrics.mjs` lays out measured natural action widths.
Work-view tabs share `viewTabWidth` and the existing workspace-tab painter,
retain close targets and reserve horizontal scrollbar space.

Native Workspace input tests exercise these variants through actual forms,
graph controls, EN/RU dialogs and narrow layouts; the browser queue tests cover
late clipboard/capture/validation results and session changes. The executable catalog includes `choice-editable` and
`checkbox-wrapped`; input checks enter custom text and toggle the wrapped label.
Splitter `action` previews a draft, `commitAction` saves it once and
`cancelAction` restores the previous value. The browser and QML queue drivers
check release, cancellation and keyboard paths. Fresh comparisons and the
mandatory platform gate are recorded in `docs/frame_files.md`; the combined
native timer-test regression is resolved and retained as a release check.

## B02 release evidence, 2026-10-16

Handler 0.6.0.106 / Stream 0.112.155: 3,456 current actual pairs, 24 configurations,
zero external geometry differences and 28,716 strict font/color checks. The
428 separately retained text-metric diagnostics are at most 1.046875 logical px
in this environment; they are not passing pixel assertions. The report also
checks photo crop/contain pixels and nested error-icon backgrounds. Its actual
local images and family filters, and offline catalog input, pass in a browser.

All 42 platform stages pass, with expanded input at three scales and native
recreation/readonly/disabled coverage. The detailed 372-state gallery and fresh
original/native/browser project and main-window comparisons also pass. Project
metadata widths now pass the original strict tolerance. Existing whole-repository
structure/lint debt and physical platform acceptance remain explicit in the plan.
