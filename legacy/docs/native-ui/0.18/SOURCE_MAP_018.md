# Source map 0.18

Baseline: released 0.17, sha256 `7629bd16ecdb164e5129e8ee092b77aa5dc297a0035670c09bda081e3ba5f3cb`.

| Legacy/source | Native implementation | Preserved contract / limits |
|---|---|---|
| `src/tactic/ui/tools/custom_layout_edit_wdg.py` and `panel/custom_layout_wdg.py` | `core/design_document.py`, `ui_api/design_service.py`, `CustomLayoutEditor.vue`, `LayoutPreview.vue` | Original category/view/HTML/style/Mako/behavior/callback data; targeted XML patch; saved child widgets. Static preview explicitly excludes dynamic template execution. |
| `src/tactic/ui/manager/view_manager_wdg.py`, `panel/view_manager_wdg.py` | `ManageViews.vue` and existing `ViewDesigner.vue`; `design_service.py` | Source config layers, explicit snapshots/copies/override removal; original resolved view layout, not forced table. |
| `src/tactic/ui/app/shelf_wdg.py` | existing `script_service.py` extended; `ScriptEditor.vue`, `CodeEditor.vue` | Existing insert/update; new gated saved `execute_python_script` call; text diff. No arbitrary source-code POST execution. |
| Original `src/context/spt_js/ace/` | copied specific assets under `ui_api/web/vendor/ace` | Existing Ace 1.4.7, same license; local served modes/themes/searchbox; no CDN/fonts. |
| `SearchTypeToolWdg`, `SearchTypeManagerWdg`, `CsvImportCmd` | `SearchTypes.vue`, `CsvImportPanel.vue`, `search_type_service.py`, `admin_workspace.py` | Existing schema metadata/creation; configured child views; original bounded create-only CSV. No destructive physical schema editing claimed. |
| `WidgetSettings` and prior .15 state service | `ui_state_service.py` | New validated `stype-editor` scope; no localStorage or persistent SObject drafts. |
| Existing .16 action log / cluster tailer | `action_log.py`, `api.py` | START/RUNNING/END and sanitized exception location; same output files/tailer; no request-value logging. |
| Existing native settings and launcher | `core/native_settings.py`, `tactic_backend.py`, `tools/local/configure_native.py` | Separate default-off `allow_script_execution`; setting persisted with explicit confirmation, no dependency upgrade. |

New endpoint permissions are checked against the resolved original target and active project. Whole original runtime and commands remain present; no legacy UI directory removed.

## Intentional differences

The old Custom Layout engine can execute Mako, expressions and user JS. The native static preview must not claim to execute these; their bytes are retained. Ambiguous equal-priority layouts, another user's personal override, arbitrary include paths and unsupported loading modes fail visibly.

CSV executes the original import command, **not form EditCmd actions**; protected/special action fields are excluded. Column dependency matches are candidates, not proof that DROP/ALTER is safe. Those destructive operations are not provided.

Script execution is administrative server-side Python, not sandboxed. A lost response can follow real side effects. New transport avoids automatic replay; it does not make DDL, filesystem, network or arbitrary scripts exactly-once.

## Source inventory / changes

`changes-from-0.17.json` and patch list actual new/changed files. `release-manifest-0.18.json` lists packaged bytes. New test sources include `test_design_documents_018.py`, `test_design_state_018.cjs`, `run_http_design_018.py`, `run_browser_design_018.py`, `run_cluster_018.py` and disposable developer server helper. Historical reports are not counted as current test executions.
