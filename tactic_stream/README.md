# TACTIC Stream

TACTIC Stream is a Python 3.14+ TACTIC server with a Vue web client. The Python
package and CLI are `tactic-stream`; the source namespace is `tactic_stream`.
See `pyproject.toml` for the source version and pinned runtime dependencies.

The core retains TACTIC's `Search`/`SObject`, project/schema/pipeline model,
command transactions, permissions and client contracts. SQLite supports local
installation; PostgreSQL supports server deployment. Compatibility with original
TACTIC is an ongoing behavioral contract, not a claim that every legacy option
works. Use live discovery and the relevant integration checks.

## Local development

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Use Python 3.14 or newer. Start through the repository's
`../START_TACTIC_STREAM.bat` (or the workspace launcher of the same name).
It initializes only when needed, upgrades the installation and runs the monitor.
Follow its prompts for the initial administrator password; there is no default
password. Never initialize over an existing installation to fix a connection.
The normal local installation uses `data/config/tactic-conf.xml` and port 8081;
use the configured bind address rather than assuming localhost.

For explicit CLI control:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 run.py --data-dir .\data init
.\.venv\Scripts\python.exe -B -X utf8 run.py --data-dir .\data upgrade
.\.venv\Scripts\python.exe -B -X utf8 run.py --data-dir .\data serve
```

`init` is for a new installation. Back up the database, repository and configuration
before upgrading an existing installation. The server monitor owns its workers;
use the normal launcher/CLI lifecycle. Node.js is needed to rebuild the frontend,
not to serve already bundled web resources.

## Documentation by product and task

| Task | Reference |
| --- | --- |
| Stream architecture and ownership | [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md) |
| Server API, core structures and guides | [TS source map](docs/admin_agent/SOURCES.md#ts-server-api) |
| Handler client API, native objects and guides | [TH source map](docs/admin_agent/SOURCES.md#th-client-api-and-structures) |
| Administrator agent: create projects/templates | [START.md](docs/admin_agent/START.md) |
| Shared QML/Vue descriptions | [Tactic Frame contract](docs/shared_ui_contract.md) and [source map](src/tactic_stream/shared_ui/README.md) |
| Windows deployment | [English](WINDOWS_DELIVERY.en.md) / [Russian](WINDOWS_DELIVERY.ru.md) |
| Server deployment | [English](SERVER_DELIVERY.en.md) / [Russian](SERVER_DELIVERY.ru.md) |
| Native Handler connection and bundle ownership | [HANDLER_DEPLOYMENT.md](HANDLER_DEPLOYMENT.md) |
| Backup, restore and acceptance limits | [RECOVERY_ACCEPTANCE.md](RECOVERY_ACCEPTANCE.md) |
| Built-in product help | [Topic index](frontend/public/help/index.json), also available in the application |

The web workspace is `/`, project workspaces are `/projects/<code>/`, and bundled
resources are `/ui/`. Live server references are `/api/documentation`,
`/api/compatibility` and `/docs`; XML-RPC retains `/tactic/default/Api/`.
Discovery describes the selected server. An available method/class does not
certify every argument combination or old plugin dependency.

## Checks

Run focused tests for the changed contract. The complete core suite is:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -v
```

Shared UI checks use `tools/frame_foundation/check_platform.py --handler-root`
with the actual independent Handler checkout. Tests must use isolated data and
clean up their own processes. Do not treat historical reports as fresh results.

Development backlog and work journals are kept outside both product repositories
in the workspace's `agent-work/` directory. They are not package resources or
administrator-agent startup context. Product documentation records contracts and
reproducible procedures rather than a sequence of assistant turns.
