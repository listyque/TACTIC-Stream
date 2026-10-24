# TACTIC Stream

TACTIC Stream provides a Python TACTIC server and a Vue web client. It preserves
TACTIC's project, SearchType, SObject, schema, pipeline and command model.
Compatibility is assessed against original TACTIC contracts; TACTIC Handler is
one independent client, not the definition of the entire server API.

| Location | Purpose |
| --- | --- |
| [tactic_stream](tactic_stream/README.md) | Current server, web client, setup and documentation. |
| [legacy](legacy/README.md) | Original source used to trace behavior and verify compatibility; not a runtime dependency. |
| `cg/` | Example project/template package. |
| [AGENTS.md](AGENTS.md) | Engineering agent rules, separate from administrator-agent instructions. |

Start an existing local installation with `START_TACTIC_STREAM.bat`.
See the [installation instructions](tactic_stream/README.md#local-development)
for a new environment. SQLite and PostgreSQL are the supported database paths;
API discovery and focused integration tests describe the actual compatibility
boundary. Do not interpret a method inventory as complete behavioral parity.

TACTIC Handler lives in its own repository and ships independently. Its Python
object API, native QML UI and local file operations differ from Stream's HTTP
API, web client and server-side core. The [agent source map](tactic_stream/docs/admin_agent/SOURCES.md)
separates those interfaces, shared contracts and original TACTIC references.

Developer documentation is in English. Product help remains available in English
and Russian. Agent backlog, handoffs and work journals are local workspace
material outside the product repositories; they are not release documentation.
