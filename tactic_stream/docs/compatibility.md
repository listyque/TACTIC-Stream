# TACTIC compatibility and verification

Compatibility is behavioral: original scripts, configurations, plugins and SDK
calls must preserve their supported meaning. A method name, class registration or
successful modern-client screen is not proof of complete legacy compatibility.
Use live API discovery for the selected installation and check actual arguments,
results, authorization, revisions, transaction effects and failure paths.

Handler's maintained Stream-boundary inventory lives in its
`docs/tactic_compatibility/stream_api.md` and `stream_boundaries.json`.
The desktop client enables extensions only for a confirmed server/login/ticket;
Legacy and unknown sessions keep native search, check-in, hooks and HTML/Mako
layouts. Stream table management, typed item metadata, private file transfers,
configured page resolution and server check-in queue requests are gated at their
owners, including deferred work. Shared menus hide the Stream manager while
retaining native view actions. Remote check-in references remain stored and are
never replayed through legacy check-in after a session change.

`tests/test_legacy_stream_boundaries.py` runs both native and transported Handler
sources without the Stream namespace: simple nested filter expressions retain
native evaluation and parent scope, HTML layouts work, and typed Stream layouts
return an explicit marker before imports. Installed Stream dependency failures
remain errors; Stream access callbacks and expression write denial stay active.

`PluginManagerCmd` is a Stream extension even though original TACTIC has plugin
installation commands and widgets. Handler hides the Stream manager for Legacy
and unidentified API sessions, blocking uploads and queued command execution
before server contact. Shared administration navigation applies this same
filter; Stream keeps the manager and legacy plugins remain usable independently.

DashboardCmd and Stream widget-configuration authoring are Stream extensions.
Handler hides page/item layout editors for Legacy and unidentified API sessions;
native and browser administration descriptions use the same section filtering.
Browser Stream sessions retain both editors. Controller guards cover direct,
queued and preview requests, including a change away from a Stream session.

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
