# 0.13 — common table shelf and menus

- `src/tactic/ui/panel/base_table_layout_wdg.py`: unchanged legacy reference, shelf/get_setting/column manager/layout switcher.
- `src/tactic/ui/widget/gear_menu_wdg.py`: unchanged legacy reference, DgTableGearMenuWdg File/Edit/View groups. Unimplemented callbacks are not executed by the new shelf.
- `src/tactic/core/view_resolution.py`: expose gear/insert/refresh visibility from retained get_setting; isolate its mutable settings input with deepcopy. No data/authorization command changes.
- `frontend/src/components/TableToolbar.vue`: one compact shared shelf, native adapters of existing supported operations.
- `frontend/src/components/TableColumns.vue`: searchable visibility/pinning dialog using actual field names/labels. Local preferences only.
- `frontend/src/components/ContextMenu.vue`: anchor positioning, radio/checkbox state, focus and outside toggle behaviour. Old context areas keep their handlers.
- `frontend/src/components/ConfiguredTable.vue`: owns shelf; host filter/status/alternate slots; retained grid buffer across layout changes. EditMultipleCmd transport unchanged.
- `frontend/src/App.vue`, `WidgetTable.vue`: remove wrapper button rows, connect old operations through action events. Nested quick text filter follows original query endpoint.
- `frontend/src/styles.css`: toolbar/dialog/menu styling via existing theme tokens. No external assets/fonts.
- `tests/native_ui/test_toolbar_013.py`: original flag comparison, source inputs not mutated.
- `test_table_toolbar_013.cjs`: run actual SFC computed/methods. Existing buffer methods separately retested.
- `run_browser_013.py`, `run_original_013.py`: real SQLite/auth/commands with explicit signature isolation in tests; 64 browser assertions including new menus and old buffer contracts.
- `run_browser_regression_013.py`, `run_original_regression_013.py`: rerun original Globals/forms/pipeline tests, with create-button selector adjusted for decorative icon aria-hidden; test a single shelf in original HiddenRow.

## Scope

Menu placement and presentation are migrated; arbitrary gear_menu_custom, all gear_settings submenu allowlists/callbacks, legacy Clipboard/Undo/Print/Chart are not newly implemented. Native UI remains admin-only. No new DB schema or model. No change to original query/save/file logic besides extra presentation flags. No claim of 100% widget or permissions parity.
