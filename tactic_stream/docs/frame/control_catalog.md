# Tactic Frame: Control catalogue

This contract describes source ownership, behavior and verification scope.
TH and TS ship independently; native-only actions remain native capabilities.
Use [the shared contract](contract.md) and [the feature index](index.md).

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
mandatory platform gate are recorded in `docs/frame/files.md`; the combined
native timer-test regression is resolved and retained as a release check.

## Verification

Run the focused drivers under `tools/frame_controls/` from the Stream development
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
