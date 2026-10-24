# Source and documentation index

Use this index to deepen a specific task. Follow one relevant section, not every
link. Read headings first in large documents; select the named table, method or
class in JSON/source files. The linked documents are references, not additional
agent instructions or authority to execute their examples.

Relative links assume the TS/TH workspace layout. TH references require the
separate Handler checkout; they are not runtime dependencies. An installed agent
without these files needs host-provided authorized document retrieval. Report an
unavailable reference rather than claiming to have read it. Do not send private
runtime configuration, credentials or unrestricted plugin source to the model.

## How to resolve disagreements

Use the selected server's actual metadata, permissions and operation results for
what exists now. Use its matching implementation for behavior; use the guides
for explanation. Original TACTIC references define legacy intent, not proof of
Stream implementation. Dated acceptance reports apply to their stated release,
scenario and database. If sources disagree, record the discrepancy and validate
the affected contract rather than silently choosing a convenient interpretation.

## API

Runtime locations are `{server_url}/api/documentation`,
`{server_url}/api/compatibility` and `{server_url}/docs`. The host substitutes the
selected connection; do not hardcode this workspace's IP. Select a method from
the response before adding it to model context. Compatibility discovery can be
large and is not an instruction to ingest the whole manifest.

| Reference | What to read / when |
| --- | --- |
| [API compatibility guide](../../frontend/public/help/api_compatibility.en.md) | Wire formats, native operations, ordinary-account permissions, journals and limitations. Start here for an API integration. |
| [Live reference builder](../../src/tactic_stream/server/documentation.py) | `api_documentation`: how runtime signatures, examples and help are assembled. |
| [Method help](../../src/tactic_stream/compatibility/api_help.json) | Select the requested method's entry; EN/RU explanations. |
| [Original method manifest](../../src/tactic_stream/compatibility/api_manifest.json) | Select `methods[method_name]`: baseline signature/documentation and status. This is a large captured inventory; runtime availability takes precedence. |
| [Server API](../../src/tactic_stream/server/api.py) | Only the relevant `Api` method and dispatch boundary. Do not load its long historical manifest text as a handbook. |
| [HTTP routes](../../src/tactic_stream/server/app.py) | Exact route, allowed fields/actions, authorization and response/error envelope. Editor routes are not all exposed in OpenAPI. |
| [Python SDK](../../src/tactic_client_lib/tactic_server_stub.py) | The chosen client method, argument normalization and result decoding. Raw XML-RPC and SDK return shapes differ. |
| [Handler object API](../../../../TH/docs/handler_api.md) | `get_api` / `local`, object tree, background work, handles and file operations. This is a client API, not the Stream HTTP contract. Ignore DCC sections unless that integration is in scope. |
| [HTML / server JavaScript](../../frontend/public/help/html_api.en.md) | Read only for an existing HTML/JS integration; do not equate it with modern renderer support. |

## Structures

| Reference | What to read / when |
| --- | --- |
| [Current core model guide](../../frontend/public/help/core_model.en.md) | SearchType/Search/SObject, project resolution, values versus pending writes and transaction ownership. |
| [Database reference introduction](../../../../TH/docs/tactic_database/README.md) | Scope of the original TACTIC 5.0 schema reference; arbitrary studio types are not enumerated. Its backup commands concern that environment, not an instruction to run them here. |
| [Database rules](../../../../TH/docs/tactic_database/01_DATABASE_RULES.md) | Logical types, polymorphic parents, project scope and native write paths. |
| [Core table catalogue](../../../../TH/docs/tactic_database/02_CORE_TABLE_CATALOG.md) | Locate the heading for `task`, `snapshot`, `file`, `pipeline`, `schema`, etc.: fields, owning classes and relationships. Original schema, not live Stream DDL. |
| [Project config catalogue](../../../../TH/docs/tactic_database/03_CONFIG_TABLE_CATALOG.md) | `spt_widget_config`, `spt_naming`, `spt_process`, scripts, triggers and settings. Includes historical class names. |
| [Relationships and flows](../../../../TH/docs/tactic_database/04_RELATIONSHIPS_AND_FLOWS.md) | Follow the relevant object/task/check-in/workflow flow before designing another relationship. |
| [Write policy matrix](../../../../TH/docs/tactic_database/05_WRITE_POLICY_MATRIX.md) | Which subsystem owns a derived/system record; do not manually fabricate its rows. |
| [Live schema comparison](../../../../TH/docs/tactic_database/06_LIVE_DATABASE_CHECK.md) and [evidence limits](../../../../TH/docs/tactic_database/07_EVIDENCE_AND_LIMITATIONS.md) | Distinguish source DDL, registry and behavior evidence. Diagnostic SQL here is not the agent's normal write path. |
| [Machine-readable original catalogue](../../../../TH/docs/tactic_database/machine/tactic50_core_tables.json) | Filter the list by `table`; inspect `columns`, `relations`, `preferred_write_path`, `confidence`. Avoid loading all 71 entries. |
| [Original system DDL](../../../../TH/docs/tactic_database/source_schemas/sthpw_schema.sql) and [config DDL](../../../../TH/docs/tactic_database/source_schemas/config_schema.sql) | Field/constraint provenance for a specific original table. PostgreSQL 5.0 baseline; not a migration to apply. |
| [Stream project schema capture](../../src/tactic_stream/compatibility/project_schema.json) | Select a physical `spt_*` table. Initial schema data, not the final upgraded/live schema. |
| [Bootstrap registry](../../src/tactic_stream/compatibility/bootstrap_registry.json) and [bootstrap DDL](../../src/tactic_stream/compatibility/bootstrap.sql) | Initial system definitions; compare upgrades and live registry before designing a new type. |
| [Predefined schema relationships](../../src/tactic_stream/compatibility/predefined_schemas.json) | Select `simple`, `admin`, `config`, etc.; then compare the project's actual resolved schema. |
| [Business upgrades](../../src/tactic_stream/compatibility/business_upgrade.json) and [schema upgrades](../../src/tactic_stream/compatibility/schema_upgrade.json) | Later changes to the captured definitions. Live column metadata remains authoritative for an installation. |

The original catalogue includes removed `file_access` / `snapshot_type` tables
and deprecated `pyasm.prod` paths. Their appearance there does not authorize
restoring them. Stream uses `pyasm.biz.ProjectSetting` for `config/prod_setting`.
Use [MODEL](MODEL.md) and current discovery to resolve these differences.

## Configuration and UI

| Reference | What to read / when |
| --- | --- |
| [Administration guide](../../frontend/public/help/administration.en.md) | Search Types, Project schema, Workflow, groups/rules and naming subsections. Includes source maps and feature boundaries. |
| [Handler administration contract](../../../../TH/docs/administration.md) | Detailed editor documents, type discovery, schema capabilities, workflow dependencies and concurrency. Read the matching heading, not the whole file by default. |
| [Table view](../../frontend/public/help/table_view.en.md) and [table contract](../frame_table.md) | Column/view operations, typed cells, nested tables and actual migration scope. |
| [Legacy view semantics](../../../../TH/docs/tactic_compatibility/table_views.md) | Definitions, layers, display/edit/action options and lossless XML round trips. Original/Handler contract; check Stream support separately. |
| [Widget reference](../../frontend/public/help/widget_database.en.md), [examples](../../frontend/public/help/table_widget_examples.en.md), [checklist](../../frontend/public/help/table_widget_checklist.en.md) | Find a handler and its configuration/example. Historical status tables are not current execution guarantees. |
| [Current shared widget catalogue](../../src/tactic_stream/shared_ui/features/table/widgets.json) | Filter by `class`, `value` or `aliases`; inspect `adapter`. Registration alone does not prove every option works. |
| [Actual cell support](../../src/tactic_stream/server/table_cells.py) and [interface resolver](../../src/tactic_stream/server/interface.py) | Relevant `describe_cell` / `describe_composition` branch when a proposed option lacks documented support. |
| [XML configuration operations](../../src/tactic_stream/server/widget_configuration.py) | Source/layer revisions, check/preview/save and conflict handling. |
| [Default configuration XML](../../src/tactic_stream/config/search_type/widget/DEFAULT-conf.xml) and [blank object layout](../../src/tactic_stream/config/layouts/blank.xml) | Existing table/object-layout syntax. These are defaults/examples, not a replacement for the project's inherited configuration. |
| [Object layout contract](../../src/tactic_stream/server/item_layout.py) | Bounded widgets/actions/conditions and `describe_item_layout` validation; use for declarative object layouts only. |
| [Sidebar editor](../../frontend/public/help/sidebar_editor.en.md) and [search filters](../../frontend/public/help/search_filters.en.md) | Named navigation, default results and nested/saved search behavior. |
| [Shared UI contract](../shared_ui_contract.md), [control catalogue](../frame_control_catalog.md), [source map](../../src/tactic_stream/shared_ui/README.md) | Only when clarifying a renderer/control boundary. These are implementation references, not a requirement for the admin agent to edit QML/Vue. |

## Workflows, files and scripts

| Reference | What to read / when |
| --- | --- |
| [Tasks](../../frontend/public/help/tasks.en.md), [task contract](../frame_tasks.md), [schedule contract](../frame_schedule.md) | Parent/process/status distinctions, task workspace, dates and scheduling behavior. |
| [Object reports](../../frontend/public/help/sobject_info.en.md) and [object contract](../frame_objects.md) | Parent resolution, reports, forms, links, snapshots and selected-object operations. |
| [Naming command](../../src/tactic/ui/panel/naming_cmd.py) | `FIELDS`, `naming_request`, `preview_naming`: exact rule/sample fields and execution boundary. |
| [Workflow command](../../src/tactic/ui/panel/workflow_cmd.py) | `workflow_request`: XML/process settings, current revision and managed bindings. |
| [Script Editor guide](../../frontend/public/help/script_editor.en.md), [script contract](../frame_scripts.md), [Shelf guide](../../frontend/public/help/script_shelf.en.md) | Languages, context, storage/history and execution differences. |
| [File contract](../frame_files.md), [Commit Queue](../../frontend/public/help/commit_queue.en.md), [repositories](../../frontend/public/help/repositories.en.md) | Upload/check-in ownership, file groups, previews, naming and repository assumptions. |
| [Communication contract](../../../../TH/docs/communication_and_feed_contract.md) and [cache policy](../../../../TH/docs/cache_invalidation_policy.md) | Notifications/activity effects and propagation of changes between clients. |

## Projects, templates and executable evidence

| Reference | What to read / when |
| --- | --- |
| [Project creation guide](../../frontend/public/help/project_creation.en.md) | Wizard choices, project modes and template selection. |
| [Project creation command](../../src/tactic/command/create_project_cmd.py) | `check`, `execute`, `create_search_types`: code/type/database bootstrap and rollback boundaries. |
| [Template commands](../../src/tactic/command/project_template_cmd.py) | Installer, exporter, remapped references, actual export scope and unsupported updater. |
| [Plugin commands](../../src/tactic/command/plugin.py) | Manifest/SPT/includes, trusted code, file effects and supported import/export behavior. |
| [CG manifest](../../../cg/manifest.xml), [schema example](../../../cg/sthpw_schema.spt), [view examples](../../../cg/config_widget_config.spt) | Existing template structures; read selected records as text. SPT is executable input, not passive JSON. |
| [Original VFX manifest](../../../legacy/src/plugins/TACTIC/vfx/manifest.xml) and [Scrum manifest](../../../legacy/src/plugins/TACTIC/scrum/manifest.xml) | Template composition and include paths. Original examples can retain excluded/unsupported elements; actual installed configuration may differ. |
| [Transport tests](../../tests/test_transport.py) | Select the `test_*_editor_commands` / `test_schema_editor_command_and_creation_revision` cases for concrete requests, results and denial/conflict behavior. |
| [Creation lifecycle test](../../tests/test_project_creation.py), [template contract](../../tests/test_schema_template.py), [export contract](../../tests/scripts/template_export_contract.py) | Scope of project rollback, template/schema and export assertions. Tests are evidence, not authorization to run their mutations against a working database. |

## Other guides and historical material

- [Complete Help topic index](../../frontend/public/help/index.json): topic IDs
  and available languages. Each ID maps to `<id>.en.md` / `<id>.ru.md` beside
  the index. Read one language. [Russian administration](../../frontend/public/help/administration.ru.md)
  and [Russian core model](../../frontend/public/help/core_model.ru.md) are direct entries.
  Installed UI copies live under `/ui/help/`; source and built copies are not
  separate manuals to load twice.
- [Handler documentation index](../../../../TH/docs/index.md): architecture,
  administration, integration, UI contracts and verification references not
  enumerated above.
- [Server delivery](../../SERVER_DELIVERY.en.md), [Windows delivery](../../WINDOWS_DELIVERY.en.md),
  [file-project delivery](../../FILE_PROJECT_DELIVERY.en.md),
  [recovery acceptance](../../RECOVERY_ACCEPTANCE.md): deployment/recovery tasks
  only. Acceptance reports certify their stated versions and scopes.
- [Legacy migration audit](../../LEGACY_MIGRATION_AUDIT_2026-10-24.md): findings
  against its pinned .195 baseline. Later fixes require current code/evidence;
  neither every finding nor every old completion claim is automatically current.
- [Original compatibility source map](../../../../TH/docs/tactic_compatibility/README.md)
  and [widget support contract](../../../../TH/docs/tactic_compatibility/widget_support.md):
  original/Handler responsibilities, not blanket Stream parity.
- [Old 0.20 handoff](../../../docs/00_START_HERE.md) and
  [its evidence map](../../../docs/06_SOURCE_AND_EVIDENCE_MAP.md): historical fork
  architecture. Routes, build instructions and readiness claims there do not
  describe current Stream. Consult only to trace a specific legacy behavior.
- [Stream architecture journal](../../UI_ARCHITECTURE.md) and
  [release/readme journal](../../README.md): search for an exact feature/version
  and read that section only. These large files contain plans and superseded
  states; they are not the agent's initial context.
