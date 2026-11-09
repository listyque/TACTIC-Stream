# TACTIC Stream

**English** · [Русский](README.ru.md) · [Documentation](tactic_stream/docs/index.md)

**Self-hosted TACTIC server and browser workspace.** Build Item Views for
assets, shots, and other project records. Track tasks and publications and
configure project schemas, pipelines, and access rules from the Vue interface.

Stream uses SQLite for local installations and PostgreSQL for server deployments.
**TACTIC-Handler** is a separate native client that can connect to Stream for
desktop file and Maya workflows.

> **Development prototype.** The Perforce-like file workspace and its browser
> inspection tools are an unfinished prototype.

![TACTIC Stream showing a configured Item View for the Orbit Studio demo](tactic_stream/docs/assets/github-item-view.png)

## Item View

Create a named card or row layout for a Search Type. Arrange previews, record
fields, and actions such as opening details or notes. Check the layout against
project data, then save it as a view. Reuse named item layouts in dashboard
blocks. [Item Layouts guide](tactic_stream/frontend/public/help/item_layouts.en.md) · [Table view screenshot](tactic_stream/docs/assets/github-workspace.png)

## What you can do

- **Track production.** Search project records, work with task schedules and
  notes, and review snapshots in the browser.
- **Configure projects.** Edit search types, pipelines, layouts, permissions,
  and project resources through web administration.
- **Manage published files.** Use server-backed publication and repository
  workflows. Depot and changelist inspection belong to the Perforce-like prototype.
- **Integrate tools.** Use live API discovery and the TACTIC project, SearchType,
  SObject, and command model.

## Start locally on Windows

From the root of this checkout, use Python 3.14 and a fresh local data directory.

```powershell
Set-Location tactic_stream
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
..\START_TACTIC_STREAM.bat
```

The launcher initializes SQLite when needed, prompts for a new administrator
password on first setup, and opens the configured local web address. The bundled
web UI runs with Python alone. [Local development and CLI](tactic_stream/README.md#local-development)

Back up existing data before using the launcher with a newer checkout. It runs
the schema upgrade before starting the server. [Backup and recovery](tactic_stream/docs/delivery/RECOVERY_ACCEPTANCE.md)

## Deployment and documentation

| I want to | Start here |
| --- | --- |
| Try the portable desktop bundle | [Windows delivery](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md) |
| Run a dedicated PostgreSQL server | [Server delivery with Docker Compose](tactic_stream/docs/delivery/SERVER_DELIVERY.en.md) |
| Upgrade or restore an installation | [Backup and recovery](tactic_stream/docs/delivery/RECOVERY_ACCEPTANCE.md) |
| Build an integration | [Server API source map](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api) · [Compatibility](tactic_stream/docs/compatibility.md) |
| Explore example plugins | [Workspace Pulse](examples/workspace_pulse/README.md) · [Studio Review](examples/studio_review/README.md) |
| Work on the code | [Application setup](tactic_stream/README.md) · [Architecture](tactic_stream/docs/architecture.md) |

Validate compatibility with the schemas, plugins, and workflows your deployment
uses. The running server provides
API discovery at `/api/documentation` and `/api/compatibility`.

## License notices

[Original TACTIC](tactic_stream/LICENSE.TACTIC) · [QuickJS-NG](tactic_stream/LICENSE.QUICKJS-NG) · [Vue](tactic_stream/frontend/public/LICENSE.VUE.txt) · [Bundled icon fonts](tactic_stream/frontend/public/licenses/icon-fonts/SOURCES.md)
