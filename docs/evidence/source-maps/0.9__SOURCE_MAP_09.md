# Source map 0.9 — startup + configured saved-script editor

Baseline: uploaded `TACTIC_5_Vue_Source_Fork_0.8.zip`. Original core VERSION stays 5.0.0.a02. This map describes concrete source changes, not a percentage of migrated UI.

## Startup / Python 3.13

| Original source / path | New responsibility | Verification |
|---|---|---|
| `pyasm/web/cherrypy30_startup.py::register_project` two implicit exec calls | `context_registry.py` imports original context modules/classes; original method attaches instances using attributes | Exact 0.8 method reproduced `Api NameError` on Python 3.13.5; actual fixed method registers all 11 stock default contexts |
| Same method, path-local XML-RPC settings | Merge late context settings into the actual mounted CherryPy app; include site prefix | Actual bundled CherryPy app config inspected, no synthetic XML-RPC class |
| `error_page` eval route lookup | `get_project` explicit attribute resolution | Unit route/validation tests |
| Mutable default `need_upgrade=[False]` | Per-call list, caller-supplied list still used | Source audit/unit tests |
| `pyasm/common/common.py` import-based class metadata resolution | New `Common.resolve_class`; trusted configs only, no instance side effects, original plugin loader | Mocked imported modules plus actual resolver tests |
| `tactic/core/widget_config.py` has_config/default display/edit/default widget calls | Explicit class lookup instead of separate exec/eval namespaces | Actual WidgetConfigView fallback methods; 11,370 existing metadata parity comparisons |
| `tactic/core/edit_commands.py::_get_action_handlers` default-action lookup | Explicit class getter so a lost import does not silently fall back to DatabaseAction | Resolver/import tests; rest of original command algorithms retained |
| `tools/local/launch.py` only import/environment check | `--check-startup` + `startup_probe.py`; actual constructor/mount/service inspection before listener | Report/schema/probe tested in source-context harness. Full original constructor with real user DB not run here |

No package named Api was installed; no dummy Api controller was substituted. No blanket monkey-patch to exec/locals. No arbitrary client-selected class execution endpoint introduced. Python version and environment downloader are unchanged.

## Original script editor

Reference: `src/tactic/ui/app/shelf_wdg.py`, `ScriptEditorWdg.init`, `get_display`, `get_manage_wdg`, `save_script_cbk`, and `ShelfEditWdg`; stock script_editor sidebar link in DEFAULT configuration.

| Original rule | Native implementation |
|---|---|
| Config handler `ShelfEditWdg` / `ScriptEditorWdg` | Register semantic kind `script-editor` in `tactic/core/config_model.py`; App.vue renders ScriptEditor.vue for resolved target |
| Original permission `builtin/view_script_editor` | `script_permission()` on every script request and generic object/target read |
| Original table `config/custom_script` | Real Search and original insert/update; no second persistence model |
| Folder/title/script_path | DB virtual paths; no filesystem read/overwrite based on them |
| Original language menu | javascript, server_js, python, expression, xml; unknown existing language retained only if unchanged |
| save_script_cbk normalizes empty folder/title prefix, then API insert/update | `script_service.clean_script_values` + `_write` + `_stub().insert/update`; no direct SQL write |
| Manage view: table + folder,title,description,language + show_shelf false | Authorized derived `~scripts-table` target routed to existing configuration table mechanism |
| Initial script_path or search_key | Read initial options from real target, look up original script row |
| Editing Python/JS source | Textarea, not v-html/runtime Vue template/JavaScript evaluation |
| Save current script | Revision + duplicate virtual path checks; draft retained on conflict |

New helper features: server-side bounded pagination/literal search; save copy; description; source download; source text search; dirty/discard/close prompts; Python AST and restricted XML syntax checks. These do not constitute a port of original Run/debugger/server_js/expression evaluation.

Limits: 256 KiB source, API directory page100/UI40, 200-character directory search. Current-page folder grouping, no full tree dump. No hidden DDL to enforce script path uniqueness. Unknown custom script consumers and cross-worker races remain integration concerns.

## Adjacent production defect

`view_service.py::view_operation(PATCH)` contained an unrelated copied block referring to undefined `opts`. That block was removed only in this method. The correct `opts` handling in `saved_view()` remains. Five regression tests call the actual view-save method with test storage: save success, unrelated XML/unknown attributes, validation, revision, own/personal override.

## Tests and actual scope

`test_startup_09.py` (17), `test_script_editor_09.py` (36), `test_view_save_09.py` (5): 58 new unit tests. Full final collection: 826 tests. `check_startup_contexts_09.py` also produces a separate 19-scenario report but is already covered as a subprocess scenario within unit tests; do not double count.

`fixture_09.py` and `script_test_store_09.py` are **test-only**. They supply request/auth/storage collaborators while using production ScriptService and original query builder. Full source API insert/update decorators, licensing and authentication on a complete database are not proven by those collaborators.

`run_http_09.py`: 29 new scenarios. Full HTTP total282. `run_browser_09.py`: 20 new scenarios. Full browser total177. Every suite gets fresh synthetic data. Original admin roots and configured Manage table verified. Browser uses an explicitly enabled HTTP bridge after actual native navigation failed; cookies/CSP/navigation/WebCrypto are not declared covered.

## No DB migration in this stage

No source changes to managed SQLite upgrade, original seed, environment downloader, runtime manifest or requirements. User reported these steps successful. CHECK_STARTUP retains real initialization and can cause original startup writes; it is not a read-only DB check.

## Deliverables / rollback

`changes-from-0.8.patch` and JSON compare new non-report files to exact base ZIP. Historical docs retain their own report status. Separate `TACTIC_0.8_Startup_Fix.zip` has only the two startup source payloads, hash checks/backups/restore and 12 installer tests; not a 0.9 updater. Full0.9 already includes it.

Legacy renderer remains available; old UI directories still contain required server handlers. Rollback of source does not rollback saved scripts, configuration or other data.
