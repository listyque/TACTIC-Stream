# ![TACTIC Stream](tactic_stream/docs/assets/readme/wordmark.svg)

**Asset management and production tracking.**

[Русский](README.ru.md) · **[Get started](#setup-and-first-project)** · [Why Stream](#what-stream-changes) · [Feature tour](tactic_stream/docs/presentations/product-tour.en.md) · [Documentation](tactic_stream/docs/index.md)

TACTIC Stream combines the project model, tasks, workflow and versioned file storage. A studio defines its own objects—assets, shots, documents—and configures how people work with them. The main interface runs in a browser; TACTIC Handler provides desktop access to local files and Maya.

![TACTIC Stream Item View: project assets](tactic_stream/docs/assets/product-tour/item-view.png)

> **Development prototype**, including the Perforce-like File Workspace.

## What Stream changes

Stream builds on TACTIC’s configurable objects, relationships, pipelines and publication rules. The fork develops that system on Python 3.14, with a new Vue browser application and visual editors. Server and interface evolve together: schema, process and view configuration are part of the application itself.

The name Stream refers to work moving through production stages. An asset has tasks and review decisions; snapshots record the delivered files. Those connections matter during a handoff: a completed task and a usable file are different things. Shared Tactic Frame descriptions supply interfaces for Stream and native Handler.

[What comes from TACTIC, what Stream changes, and why →](tactic_stream/docs/presentations/product-tour.en.md#what-stream-changes)

## Setup and first project

| Run Stream | Start here |
| --- | --- |
| **Windows desktop / SQLite** | [Portable package guide](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md): local application, repository and optional native Handler. |
| **Linux server / PostgreSQL** | [Server deployment guide](tactic_stream/docs/delivery/SERVER_DELIVERY.en.md): Docker Compose, Apache and a dedicated database. |
| **From source** | [Local development](tactic_stream/README.md#local-development): Python 3.14, editable installation and the repository launcher. |

The first setup asks you to create the administrator password. Open or create a project, configure its data, then create accounts and grant the team access.

## Stream tools

### Workflow engine

Workflow defines routes through production, including parallel stages, conditions and approvals. The server handles events according to pipeline rules: creating tasks, running actions and sending notifications. The editor shows the complete graph and each node’s settings.

![Workflow editor: connected production stages and review](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow: from definition to execution →](tactic_stream/docs/presentations/product-tour.en.md#workflow-graph-and-execution)

### Workspace configuration

Arrange object lists, tasks, previews and notes side by side, combine them into tabs and save the layout. Sidebar Editor defines department navigation, Item Layouts configures object cards, and the page editor builds dashboards. They use the same project records.

![Dock composition: visual objects, tasks and publication previews](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](tactic_stream/docs/presentations/product-tour.en.md#item-view-and-search) · [Docks →](tactic_stream/docs/presentations/product-tour.en.md#docks-and-layouts) · [Sidebar Editor →](tactic_stream/docs/presentations/product-tour.en.md#sidebar-editor)

### Task Manager and Gantt

Task Manager edits assignees, dates and statuses. Gantt shows the schedule and overlapping work. Open a task to reach its object and discussion, or use Messages for team conversations. Project history records changes to plans and statuses.

![Gantt: production tasks arranged across the team's schedule](tactic_stream/docs/assets/product-tour/gantt.png)

[Planning →](tactic_stream/docs/presentations/product-tour.en.md#planning) · [Notes and Messages →](tactic_stream/docs/presentations/product-tour.en.md#messages-and-notes)

### Publications and file versions

Check-in stores a file against an object and process, assigns a version and applies naming and directory rules. Snapshot Browser shows the publications and their contents. Handler adds local repository synchronization and opening scenes in Maya.

![Snapshot Browser: Survey Drone publications and file previews](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Check-in, versions, naming and delivery →](tactic_stream/docs/presentations/product-tour.en.md#check-in-and-check-out)

### Dashboards

Dashboard Editor puts metrics, charts, tables and Item View on one page. Details and actions can follow the selected object. The example below combines task and workload reports with an asset navigator.

![Custom dashboard: live project metrics, workload and visual records](tactic_stream/docs/assets/product-tour/dashboard-overview.png)

[Dashboards and visual page authoring →](tactic_stream/docs/presentations/dashboards.en.md)

### Project assistant

The assistant reads project records, prepares reports and drafts changes through its available tools. Below, it reviewed Survey Drone: modeling was marked complete, but no model had been published. Operation details are available alongside the answer.

![Project assistant examining production records](tactic_stream/docs/assets/product-tour/assistant.png)

[Assistant: providers, tools and capabilities →](tactic_stream/docs/presentations/assistant.en.md)

### Knowledge Base and Help

Knowledge Base holds instructions, delivery requirements and technical notes. Articles can link to project objects and include files. The editor offers Visual and Markdown modes, with drafts, publication and revision history.

![Knowledge Base: a delivery checklist linked to a production asset](tactic_stream/docs/assets/product-tour/knowledge-base.png)

[Knowledge Base: authoring and publishing →](tactic_stream/docs/presentations/knowledge-base.en.md)

Built-in Help documents application tools and settings. It opens from working tools and supports search, English and Russian articles, and Markdown export.

![Built-in Help: application documentation with a searchable topic catalog](tactic_stream/docs/assets/product-tour/help.png)

[Explore built-in Help →](tactic_stream/docs/presentations/help.en.md)

## Configuration and development

| Area | Explore |
| --- | --- |
| **Model and administration** | [Schemas and visual editors](tactic_stream/docs/presentations/product-tour.en.md#project-administration), [users and access](tactic_stream/docs/presentations/product-tour.en.md#users-and-permissions), [configuration](tactic_stream/docs/presentations/product-tour.en.md#configuration). |
| **Context and activity** | [Object overview](tactic_stream/docs/presentations/product-tour.en.md#object-overview) and [server history](tactic_stream/docs/presentations/product-tour.en.md#activity-feed-and-project-history). |
| **Scripts and integrations** | [Script Editor and shelves](tactic_stream/docs/presentations/product-tour.en.md#script-editor-and-automation), [server APIs](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api), [development setup](tactic_stream/README.md). |
| **Interface language** | [Tactic Frame](tactic_stream/docs/presentations/product-tour.en.md#tactic-frame): one shared UI description, native controls in Vue and Qt Quick. |

**[Full product tour →](tactic_stream/docs/presentations/product-tour.en.md)** · [All documentation](tactic_stream/docs/index.md)

Screenshots are current application captures on isolated Orbit Studio data; records and artwork are illustrative. Stream and Handler ship independently. Original TACTIC compatibility is documented by [scope and verification](tactic_stream/docs/compatibility.md).

Built from [Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC). [TACTIC license](tactic_stream/LICENSE.TACTIC) · [Third-party licenses](tactic_stream/docs/presentations/product-tour.en.md#compatibility-limitations-and-licenses).
