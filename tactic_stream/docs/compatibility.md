# TACTIC compatibility and verification

Compatibility is behavioral: original scripts, configurations, plugins and SDK
calls must preserve their supported meaning. A method name, class registration or
successful modern-client screen is not proof of complete legacy compatibility.
Use live API discovery for the selected installation and check actual arguments,
results, authorization, revisions, transaction effects and failure paths.

Transported Handler procedures use public `pyasm.common` exception exports.
Legacy TACTIC re-exports `SecurityException` from `common_exception.py` and lacks
Stream's `pyasm.common.errors` module. Physical-table tests execute both products'
procedure sources without that import and verify administrator enforcement;
the native Python procedure transport also exercises the actual Handler source.

Handler security-group catalog procedures and Stream's native counterpart use
the legacy `Search.add_column` signature. Fixed aggregate expressions such as
`MAX(id)` use `Search.get_select().set_quoted_mode('none')` instead of a `quoted`
keyword. SQL-backed tests check both implementations with the old signature and
compare grouped journal markers with each group's latest revision; administrator
checks, stale-write protection and safe user projections remain required.

| Boundary | Reference |
| --- | --- |
| Supported and excluded server contracts | [API compatibility Help](../frontend/public/help/api_compatibility.en.md) |
| Native object/query semantics | [Core model](../frontend/public/help/core_model.en.md) |
| Original project page URLs | [Custom URL contract and limits](custom_urls.md) |
| Original table configurations | [Table contract](frame/table.md), [widget catalogue](../frontend/public/help/widget_database.en.md) |
| TS APIs and original server references | [Source index](admin_agent/SOURCES.md) |
| TH client interpretation of TACTIC | [Handler compatibility map](../../../TH/docs/tactic_compatibility/README.md) |

Use the unchanged client/script against disposable data. Compare stored values
and side effects, not only presentation. Check both SQLite and PostgreSQL when a
database contract changes; inspect TH and TS separately for shared UI workflows.
Existing test and tool sources are the reproducible evidence owners. Record
package/source fingerprints and the precise tested scope with each new run.

The excluded old `pyasm.prod` subsystem is distinct from ordinary configurable
VFX projects. Maya/applets are excluded from the current acceptance scope.
Unsupported behavior must be reported explicitly. Historical migration audits
are retained in the local workspace archive; their counts are not current status.
