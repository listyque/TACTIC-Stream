# External administrator connection

Audience: the person configuring an external agent host. For TACTIC domain
knowledge start with [START](START.md) and [MODEL](MODEL.md). This document
describes implemented tools, not a promised future API.

## What runs where

The external host runs its chosen model and launches a separate MCP stdio
process. That process calls the configured TS HTTP API. It never imports
`pyasm`, opens a database or imports Handler. TS owns authentication, access,
project context and native naming evaluation. No model/provider dependency
or API key is installed in either TACTIC product.

The adapter uses the official [MCP Python SDK 2.3.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0)
for negotiation, schemas and stdio. It supports current and legacy protocol
clients through that SDK; no custom JSON-RPC implementation is maintained.
This first adapter is for a host capable of launching a local process. It is
not a public HTTP MCP endpoint or an installed client-specific configuration.

## Install and launch

Use Python 3.14 and the Stream source checkout. From `TS/tactic_stream`:

```text
python -m pip install -e ".[agent]"
python -m tactic_stream.admin_agent --help
```

`tactic-admin-agent` is also installed as a console command. The `agent` extra
is optional; normal server startup does not load MCP or its dependencies.

Configure the MCP host's stdio server with these fields (replace placeholders):

```json
{
  "command": "<absolute Python 3.14 executable>",
  "args": [
    "-m", "tactic_stream.admin_agent",
    "--server", "http://<TACTIC host>:8081",
    "--project", "<existing project code>",
    "--stream-root", "<absolute TS/tactic_stream checkout>",
    "--handler-root", "<absolute independent TH checkout>"
  ]
}
```

The host injects `TACTIC_AGENT_TICKET` into the child environment using its
private secret facility. Use an existing valid TACTIC session ticket. Never
paste credentials into a prompt or commit them to this example. Ticket renewal
is currently host-owned: on expiration renew the session and restart the adapter.
The adapter does not read browser sessions, configuration secrets or passwords.
Editor reads go through `execute_cmd`, which currently requires administrator
access. A tool's read-only annotation does not bypass server authorization.

`--server` is an origin, with no path/query/embedded credentials. Each process
is bound to one project. The model cannot select a destination, ticket, arbitrary
RPC method or command class. Redirects and environment HTTP proxies are disabled;
TLS certificate verification uses Python's normal trust configuration. Plain
HTTP is only appropriate on a trusted local network; use HTTPS across untrusted
networks. HTTP socket operations have a 30-second timeout; requests are never
retried automatically.

The reference roots are documentation checkouts, not runtime data directories.
`--handler-root` is optional and only enables TH reference reading; it does not
connect to or start Handler. This checkout-based reference mode does not claim
that a standalone server delivery includes engineering docs. Missing references
are reported explicitly in the catalogue.

## Implemented tools

| Tool | Result / owner |
| --- | --- |
| `agent_capabilities` | Adapter version, running TS health, bound project, limits and explicit unavailable actions. |
| `reference_catalog` | Curated reference IDs with TS/TH ownership and availability. |
| `reference_read` | At most 50 lines / 12,000 characters, zero-based offset, next offset and source identity. No arbitrary file paths. |
| `ts_types` | Project SearchType catalogue, paginated after the native list operation. |
| `ts_type_read` | One type's native columns, relations, pipeline metadata and revision. |
| `ts_schema_read` | Current project schema and revision. |
| `ts_naming_read` | Native rules/revision and a page of at most 50 sample objects. |
| `ts_naming_preview` | Native matching rule, versioned/versionless paths and known collisions for one sample. Does not save. |

Native HTTP responses are capped at 2 MiB before decoding. Large catalogues can
therefore exceed the transport limit even when a small tool page was requested;
the current native catalogue API is not server-paginated. Naming rule collections
and schema documents are returned whole within that limit. Narrower server reads
are needed for exceptionally large projects; the adapter fails explicitly rather
than silently cutting XML or rules.

Knowledge is retrieved on demand from the existing administrator pack and TS/TH
Help, without loading repository AGENTS, backlog or all source files. `ts.sources`
links the deeper owner-specific API/structure references. The curated MCP catalogue
is not yet a reader for every linked document. Local document text and project
data are reference material, never instructions granting extra authority.

## Naming from a description

1. Read `ts.start` and `ts.model`, then the naming section of `ts.operations`.
2. Discover the real type with `ts_types` / `ts_type_read`; inspect schema for
   parent relationships. Never infer a column from the user's display label.
3. Load `ts_naming_read`. Retain the original full document, rule identity and
   collection revision. Select returned sample keys from the bound project.
4. Compose native patterns using actual object, parent, snapshot and file fields.
   For editing, preserve every original field, including false and empty values.
5. Pass `search_type` separately; `document` contains the remaining native fields.
   Call preview for representative objects, versions, filenames and contexts.
   Inspect `matches`, `selectedRule`, missing parent values and collisions.
6. Present the exact draft and concrete resulting paths. State that it has not
   been saved. The current MCP tool set deliberately has no apply operation.

For example, after discovering the corresponding fields, native file naming can
use `{sobject.code}_{snapshot.context[1]}_v{version}.{ext}`. It is a pattern for
the real engine, not a second naming formatter implemented in the agent.

Preview always sends `allow_execution:false`. Script/class overrides and
expression-triggered custom execution are rejected by the existing NamingCmd
guard. This restriction is not an OS sandbox. Existing authorized server
configuration and extensions remain part of the trusted runtime. Preview creates
no naming/file/snapshot records; normal server authentication/command bookkeeping
may still occur. Preview does not reserve a path or guarantee future uniqueness;
actual check-in must evaluate naming and collisions again.

## Verification

With the `agent` extra installed, run:

```text
python -B -X utf8 -m unittest discover -s tests -p test_admin_agent.py -v
```

The tests start an owned temporary SQLite HTTP fixture and a real MCP stdio
subprocess, negotiate current and legacy clients, exercise metadata and native
naming preview, reject invalid tickets/cross-project samples/custom execution,
check unchanged naming/file/snapshot records, and close both test processes.
Boundary checks cover reference paging, strict fields, redirects, secret
redaction, invalid JSON and response limits. Without the optional dependency
the suite skips explicitly. This is not evidence for PostgreSQL, live account
setup, TH hook execution or an external model's reasoning quality.
