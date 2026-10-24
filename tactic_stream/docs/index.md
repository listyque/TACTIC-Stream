# TACTIC Stream documentation

This is the entry point for maintained TS documentation. Stream owns the server,
core data model, transports and browser UI. Handler is an independent desktop
client; its Python objects and local execution are not server APIs.

| Need | Start here |
| --- | --- |
| Install and run Stream | [Application README](../README.md) |
| Understand source ownership | [Architecture](architecture.md) |
| Configure projects through an external administrator agent | [Agent start](admin_agent/START.md), then task-specific [source references](admin_agent/SOURCES.md) |
| Server API and core structures | [TS API map](admin_agent/SOURCES.md#ts-server-api), [core model](../frontend/public/help/core_model.en.md) |
| Compatibility with original TACTIC | [Compatibility and verification](compatibility.md) |
| Shared QML/Vue descriptions and controls | [Frame contracts](frame/index.md) |
| Install, package, upgrade or restore | [Delivery guides](delivery/index.md) |
| Use the web application | [Product Help catalogue](../frontend/public/help/index.json) |
| Work with Handler's native API | [TH API](../../../TH/docs/handler_api.md), [TH documentation](../../../TH/docs/index.md) |

## Source and generated files

- `src/pyasm`, `src/tactic`: native TACTIC core, domain operations and compatibility.
- `src/tactic_stream/server`: server transports, application services and lifecycle.
- `frontend/src`: editable web UI; `frontend/public/help`: web Help sources.
- `src/tactic_stream/web`: versioned built resources shipped in wheels. Rebuild them
  through the frontend build; they are not an expendable cache.
- `src/tactic_stream/shared_ui`: Stream's portable Frame source. Handler ships its
  own checked copy; neither installation imports the other checkout.
- `tests`, `tools`, `benchmarks`: maintained checks and drivers. Checked-in fixtures
  belong beside their consumer; generated `tools/*/output` and temporary results
  are ignored.
- `data`, `.venv`, frontend dependencies and installed browser caches are local
  runtime/development state. Do not sweep them up as unused source.

Write engineering documentation in English. Keep EN/RU product Help and localization
with their owning product. A new document must have a clear audience and a link from
this index or its domain index. Update an existing contract before adding another.
Keep engineering rules in AGENTS and administrator instructions in `admin_agent`.
Backlog, handoffs, dated audits and acceptance results belong in the workspace's
local `agent-work/` archive, outside both Git repositories and release bundles.
