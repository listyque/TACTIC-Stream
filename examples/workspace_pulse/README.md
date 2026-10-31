# Workspace Pulse 1.1.0

A reusable example TACTIC plugin for **TACTIC Stream and TACTIC Handler**.
The same native dashboard documents render in both clients. No extra frontend,
desktop renderer, external service, model call or dependency is installed.

## Install

Build from the workspace checkout:

```powershell
TS/tactic_stream/.venv/Scripts/python.exe TS/tactic_stream/tools/build_workspace_pulse.py
```

Open **Administration → Plugins** in either client, select a business project,
install `TS/releases/workspace-pulse-1.1.0.zip`, review its contents and activate.
Refresh project navigation. **Pulse** and **VFX overview** appear in the existing
sidebar. The same ZIP can be activated independently in other projects.

- **Pulse:** four compact task/deadline counters, shared status/assignee/process filters,
  a delivery line chart, status donut, assignee bars and a searchable native task table.
  Cards use one spacing grid, theme-aware surfaces and cached soft shadows.
  The task table fits all configured columns and shares its height with the adjacent chart.
  Task descriptions, rather than internal task codes, lead the table.
- **VFX overview:** discovers existing episode, sequence, scenes, shot and asset
  tables in the target project, including types from template namespaces. Shows
  counts and native searchable tables; creates no types or business records.
  Projects without these types get an explicit explanation. Reload after adding
  types. Custom semantic names require editing `workspace.py` before activation.

There are no guessed terminal statuses, fixed project codes, decorative placeholder
previews or sample business data. Counters show tasks with/without a due date;
the report groups by actual assignee values. A type without a `name` field uses its code.
Status/assignee inputs use the existing dashboard filter controls; table search
uses the ordinary smart search and suggestions. Common filters affect task bricks.
Chart tooltips show the full label and value. A single scheduled date produces
one real point, not an invented trend. No-value groups remain visible.

Upgrade both clients to TS 0.112.345 / TH 0.6.0.306 or newer before installing.
For an existing 1.0.0 activation, export customized pages first, remove the old
version from that project, then install and activate 1.1.0. Installation does not
silently replace an active project's customized pages.

## Customize and remove

Open the pages in the native **Page Editor** to change data sources, columns,
layout and appearance. Their saved documents are ordinary `CustomLayoutWdg`
configurations and are available to the internal agent's `ts_dashboard_read`,
`ts_dashboard_preview` and `ts_dashboard_save` tools, subject to current permissions.
The plugin does not install new AI instructions, credentials or MCP access.

**Remove from project** removes only its two pages, custom URLs, table views and
sidebar entries. It preserves tasks, files, workflows and other navigation.
Reload removes/recreates these plugin-owned configurations, so export customized
pages before reloading/removing. Activation rejects colliding view names instead
of overwriting an unrelated layout; all writes use the native Command journal.

## Package structure

- `manifest.xml`: native package metadata and narrowly selected owned records.
- `install.py` / `uninstall.py`: native manifest hooks.
- `workspace.py`: discover the current schema, compose documents with existing
  bricks and publish through `DashboardCmd`; remove only owned navigation.
- `empty.spt`: intentionally empty; configurations are generated at activation.

TS owns these server commands and config tables; TH consumes them over its native
transport. The two products keep separate renderers and distributions.
Requires the current TS dashboard/PluginManager contract, not unmodified legacy
TACTIC. See `TS/tactic_stream/docs/admin_agent/DASHBOARDS_MCP.md` and
`TS/tactic_stream/docs/admin_agent/SOURCES.md` in the workspace for ownership/API
details. No legacy production module or optional database adapter is required.
