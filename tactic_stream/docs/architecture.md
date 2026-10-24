# TACTIC Stream architecture

This is the maintained architecture map. Product contracts and implementation
references are linked below; development backlog and superseded checkpoints live
outside the repositories in the workspace's `agent-work/` directory.

## Separate products and execution environments

| Owner | Responsibilities | Interfaces |
| --- | --- | --- |
| TS server | TACTIC objects, Search, permissions, commands/transactions, project databases, repository and plugin/template operations | Native `pyasm`/`tactic`, XML-RPC, HTTP API and editor routes |
| TS web client | Browser interaction, view rendering, drafts and request lifecycle | Vue and its server transport; no direct database writes |
| TH desktop client | Native QML interaction, client objects, local files, queues and desktop integrations | `tactic_handler_api`, `thlib`, existing TACTIC SDK and native controllers |
| Shared Tactic Frame | Portable UI descriptions and state rules | Independent copies of ordinary JavaScript modules, rendered by each product's house controls |

Handler Server is TH's local integration/router service. It is not the Stream
TACTIC database server. Likewise, Handler's Python SObject wrappers are not the
server's `pyasm.search.SObject` objects. Sharing search keys does not make method
signatures, return shapes, thread ownership or lifecycle interchangeable.

## Server core and storage

`src/pyasm/common`, `search`, `biz`, `security` and `command` retain the original
core responsibilities. `src/tactic_stream/server` owns HTTP/API dispatch, startup
and process monitoring. The server must not import the legacy reference checkout
or Handler. Runtime resources live under `config`, `compatibility` and `web`.

Project code, SearchType namespace and database are distinct identities.
SearchType/SObject/Schema/Pipeline and the native registry define the model;
there is no parallel application-specific Asset/Task model. Database differences
belong to Sql/DbResource/DatabaseImpl and vendor implementations. Commands own
permissions, transactions, hooks and effects; direct SQL is not a substitute.

Use the [core model](../frontend/public/help/core_model.en.md),
[agent model](admin_agent/MODEL.md) and
[current schema references](admin_agent/SOURCES.md#ts-server-structures).
Original TACTIC schema catalogues explain provenance; live metadata determines
what is installed. Excluded `pyasm.prod` imports must not be restored from old
examples; project settings use `pyasm.biz.ProjectSetting`.

## Configuration-driven UI

WidgetConfig/WidgetConfigView resolve original XML definitions and layers at
runtime. Keep raw stored values, display cells and unsaved drafts distinct.
Preserve unknown XML, comments, repeated elements, explicit empties and revisions.
Support for declarative options does not imply execution of arbitrary legacy
Python/JavaScript widgets. Reject unsupported contracts explicitly.

The modern UI description is independent of Vue's version. Existing legacy HTML
contracts remain a separate compatibility boundary; do not silently return JSON
where a client expects HTML. Read [configuration and UI references](admin_agent/SOURCES.md#ts-configuration-and-ui)
and the [table contract](frame/table.md) for the relevant operation.

## Shared descriptions, native adapters

Follow the [shared UI contract](frame/contract.md). Shared modules own
structure, layout and state rules; native QML and Vue controls own rendering and
input. Domain controllers and server commands keep their current responsibilities.
TH and TS ship separate copies and build independently; neither imports the
other checkout at runtime. Compare copies with
`tools/sync_tactic_frame.py --handler-root <handler-checkout> --check`.

Shared controls live in `frontend/src/controls`; domain features live together in
`frontend/src/features`. `App.vue` hosts the web application. Controls do not own
API requests or know project/type identities. One screen owns its drafts and
request lifecycle; asynchronous results must not overwrite a newer selection.
Use shared themes, translations, icons, modal-window behavior and scrollbars.
Product help and localization remain EN/RU; server-defined labels remain data.

## API and administrator agents

[OPERATIONS.md](admin_agent/OPERATIONS.md) describes Stream server calls.
[TH references](admin_agent/SOURCES.md#th-client-api-and-structures) describe
Handler's object API, background execution and native object/file semantics.
Select the intended execution environment before choosing an operation.

The administrator-agent entry point is [START.md](admin_agent/START.md),
followed by the domain model and task-specific operations/recipes. This is a
compact knowledge pack, not an installed AI/MCP service. The host supplies tools,
authentication and authorization. Common durable draft/apply orchestration and
an isolated generated-code runner are not implemented by those documents.
Required security/execution boundaries are recorded in [AGENTS.md](../AGENTS.md).

## Verification boundaries

Verify actual calls, permissions, errors, revision conflicts and transaction/file
effects, not just registrations or matching signatures. Shared UI verification
requires real Qt/browser input and paired geometry/appearance at the same data,
theme, language, scale and size. Frame reports must match current source hashes.

Use the relevant `tools/frame_*` harness and frontend scenario, then the
[platform gate](../tools/frame_foundation/check_platform.py). Backend changes need
the relevant isolated integration checks; delivery requires independent bundles
and its own installation/upgrade/recovery qualification. A historical report or
passing unit test is not a claim of full UI, Windows or PostgreSQL acceptance.
