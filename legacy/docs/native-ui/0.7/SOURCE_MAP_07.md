# Source map 0.7 — original metadata, cells and CSV

Baseline: `TACTIC_5_Vue_Source_Fork_0.6.zip`, SHA-256
`a15e0a16f566fb0c843c863331d8d859788278ef04b2be12c146866320265cc4`.

This iteration introduces **no database schema/table changes**. Original TACTIC Search, XML metadata, permissions and command paths remain. It is not complete UI parity.

| Original source / semantics | New shared/server code | Native UI / verification |
|---|---|---|
| `BaseTableLayoutWdg.__init__` config_xml/config_code/element_names branches | `core/view_resolution.py`, `ConfigBackend._view_model` | actual options choose column order/definitions; branch tests |
| `WidgetConfig.get_options` / duplicate XPath definitions | `core/config_options.py`, `core/config_model.py` | nested dicts, stock embedded configs, whitespace, duplicate definitions |
| `BaseTableLayoutWdg.get_setting` | `core/table_settings.py`, old class delegates | exact unchanged AST; shelf/layout/search/pager controls |
| `FormatElementWdg.get_format_value`, numeric helpers | `core/format_value.py`; legacy mixin | `WidgetCell.vue`/`ColumnService`: typed data, raw values separate |
| `BaseTableElementWdg.get_timezone_value` | shared formatter mixin; old class delegates | original timezone preparation/day-column behavior |
| `SimpleTableElementWdg.get_display`, plain/column alias branch | `column_service.simple_cell` / `_column_spec` | source column ACL checked, no Wiki HTML execution |
| `SimpleTableElementWdg.get_bottom_display` total/avg/count | `_page_summaries` calls original `Search.eval` | current-page footer, not global aggregate |
| `LinkElementWdg` | safe static typed links | arbitrary expressions/javascript intentionally unsupported |
| Effective widget configuration | `ColumnService.resolved_view`, GET `/resolved-view` | `ConfigAudit.vue`, original layers/options/handlers/provenance |
| `CsvExportCmd` configured fields/query (not its HTML/Excel-formula path) | `CsvService.export_csv`, POST `/export-csv`, same `_query_search` | `CsvExport.vue`: raw/display, columns/selection; no formula generation |
| Existing saved view serialization | `append_option`, `ViewService.saved_view` | preserves nested state/settings as XML, not Python dict repr |

## What is preserved exactly vs adapted

`convert_to_float`, `number_format`, `currency_format`, and `get_setting` retain source AST hashes. Original copies are retained under test `reference_07`. `get_format_value` delegates visual checkbox/red-currency output to hooks; its broken `real_value` duration reference is intentionally fixed. Legacy visual hooks recreate its prior HTML; native hooks emit data only. Import placement changes do not claim removal of every UI dependency.

The metadata audit covers 80 shipped XML files / 487 views / 2911 element visits / 11370 property checks against real extracted WidgetConfig/WidgetConfigView. Reference aliases come from the source WidgetClassHandler. Live DB priorities, installed plugin methods, dynamic fallback and rendered feature parity are **outside this audit**.

Sources of found differences: generic nested `<state>`/options projected as strings in 0.6; stock inline config serialization; duplicate display declarations and original whitespace semantics. Fixes are regression-tested rather than removing failing comparisons.

`config_code` deliberately resolves only its stored view. `config_xml` deliberately does not append the global column layers. Plain `element_names` prepends an order layer while inheriting source definitions. These branches must not be collapsed into one arbitrary merged XML model.

## Explicit behavior differences / boundaries

* Server-only trusted target options; the browser cannot inject config_xml, class paths or SQL via `/query` or CSV.
* Unknown virtual columns stay visible as unsupported; no claim to reproduce arbitrary `get_display/get_text_value`.
* Native static text is inert, not executable Wiki/HTML. Unsafe/dynamic links return diagnostic cells.
* Custom per-field SQL order_by/order_by_where has no native sorting implementation: reject rather than sort incorrectly.
* Format/Link column overrides are not guessed from SimpleTableElementWdg; unsupported combinations are explicit.
* Native table page max200; no old unlimited/chunk renderer. Supported controls do not imply all shelf/settings modes.
* CSV deliberately does not generate legacy Excel formulas. Leading-risk values receive apostrophes, including negative strings. Raw CSV is storage-value mode, not unsafe byte-for-byte legacy export.
* Page summaries use displayed SObjects. CSV scans matching Search pages; neither is a cross-client transactional snapshot.
* Currency/size formatting needs server locale; unavailable locale produces diagnostics. C-host reference tests share a locale collaborator where needed; production helpers remain source-derived.

## Reproduction

`run_validation_07.py` builds, audits metadata, runs all unit tests and starts a fresh fixture server per HTTP/browser suite. Default native browser navigation is not silently replaced; explicit `--bridge` records limitations. Reference photos/reports are TEST FIXTURE, not a working PostgreSQL server.

Source/schema/auth collaborators in new tests are documented in `column_test_store_07.py` and `fixture_07.py`. Actual query, field resolution, formatting, CSV and OS response handling use production code; fixture persistence never becomes a production backend.

Reports: `validation/summary.json`, `config-parity.json`, individual unit/HTTP/browser logs. All previous tests are rerun, not inferred from historical numbers. Original UI packages must remain for yet-unmigrated handlers and server imports.
