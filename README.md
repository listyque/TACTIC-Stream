# ![TACTIC Stream](tactic_stream/docs/assets/readme/wordmark.svg)

**A production platform connecting project data, people, processes and files.**

[Русский](README.ru.md) · **[Get started](#get-started)** · [Why Stream](#why-stream) · [Feature tour](tactic_stream/docs/presentations/product-tour.en.md) · [Documentation](tactic_stream/docs/index.md)

Model your studio's work, define its route through production and bring the team into a shared browser workspace. TACTIC Stream connects configurable objects, an executable workflow engine, planning, review and versioned publications. TACTIC Handler provides the native desktop companion.

![TACTIC Stream Item View: visual assets in a real project workspace](tactic_stream/docs/assets/product-tour/item-view.png)

> **Development prototype.** Stream is under active development. The Perforce-like File Workspace is also a prototype.

## Why Stream

The fork carries TACTIC's configurable data model, workflow, permissions and file publications into a modern Python server and Vue workspace. **Stream** describes the connected path from incoming work through review to delivery.

- **Keep the TACTIC foundation.** Objects, relationships, pipelines and snapshots remain the core production concepts.
- **Make the project editable.** Visual tools expose schemas, workflows, naming, sidebars, layouts and access rules.
- **Connect browser and desktop.** Tactic Frame describes shared interfaces for Vue and native Qt Quick; Handler adds local repositories and Maya integration.

[What comes from TACTIC, what Stream changes, and why →](tactic_stream/docs/presentations/product-tour.en.md#why-this-project-exists)

## Get started

| Run Stream | Start here |
| --- | --- |
| **Windows desktop / SQLite** | [Portable package guide](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md): local application, repository and optional native Handler. |
| **Linux server / PostgreSQL** | [Server deployment guide](tactic_stream/docs/delivery/SERVER_DELIVERY.en.md): Docker Compose, Apache and a dedicated database. |
| **From source** | [Local development](tactic_stream/README.md#local-development): Python 3.14, editable installation and the repository launcher. |

The first setup asks you to create the administrator password. Open or create a project, configure its data and invite the team.

## Inside Stream

### A workflow engine behind the graph

Describe manual work, actions, conditions, approvals and dependencies. The server executes configured transitions; the graph editor and process inspector expose their rules. Tasks and published versions stay attached to the objects moving through that process.

![Workflow editor: connected production stages and review](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow: from definition to execution →](tactic_stream/docs/presentations/product-tour.en.md#workflow-is-an-execution-engine)

### Compose the workspace your team needs

Browse with Item View, continuous trees or tables. Split and stack docks to keep objects, tasks, notes and previews together. Sidebar Editor, Item Layouts and page editors shape navigation and presentation around the department.

![Dock composition: visual objects, tasks and publication previews](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](tactic_stream/docs/presentations/product-tour.en.md#a-workspace-built-around-the-item) · [Docks →](tactic_stream/docs/presentations/product-tour.en.md#docks-assemble-the-interface-around-a-job) · [Sidebar Editor →](tactic_stream/docs/presentations/product-tour.en.md#sidebar-editor-turn-navigation-into-a-workflow)

### Give the plan people and dates

Task Manager, Gantt and the calendar connect assignments, schedules and progress. Notes preserve review decisions on the object; Messages supports the team conversation. Object overview and server history help trace what happened.

![Gantt: production tasks arranged across the team's schedule](tactic_stream/docs/assets/product-tour/gantt.png)

[Planning →](tactic_stream/docs/presentations/product-tour.en.md#plan-the-work-then-follow-it-through) · [Notes and Messages →](tactic_stream/docs/presentations/product-tour.en.md#conversations-that-retain-production-context)

### Deliver files with their context intact

Check-in associates files with an object, process and version. Naming Editor defines names and repository paths; Snapshot Browser returns to the required publication. Native Handler extends this workflow with local Repository Sync and Maya scene operations.

![Snapshot Browser: Survey Drone publications and file previews](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Check-in, versions, naming and delivery →](tactic_stream/docs/presentations/product-tour.en.md#from-working-file-to-traceable-publication)

### Turn project data into a working page

Compose metrics, charts, Item View and actions in Dashboard Editor. Build a production overview, a department page or a review desk that responds to the current selection.

![Custom dashboard: live project metrics, workload and visual records](tactic_stream/docs/assets/product-tour/dashboard-overview.png)

[Dashboards and visual page authoring →](tactic_stream/docs/presentations/dashboards.en.md)

### Ask questions in project context

The built-in assistant can inspect real records, explain results and prepare operations using available tools. Keep the selected object in the conversation and examine the work behind an answer.

![Project assistant examining production records](tactic_stream/docs/assets/product-tour/assistant.png)

[Assistant: providers, tools and capabilities →](tactic_stream/docs/presentations/assistant.en.md)

### Give the team a shared handbook

Knowledge Base connects searchable sections and articles to project objects. Write in Visual or Markdown, attach reference files, save drafts and publish instructions with article history.

![Knowledge Base: a delivery checklist linked to a production asset](tactic_stream/docs/assets/product-tour/knowledge-base.png)

[Knowledge Base: authoring and publishing →](tactic_stream/docs/presentations/knowledge-base.en.md)

Built-in Help explains the application: contextual articles, topic search, English/Russian content and Markdown downloads are available inside the workspace.

![Built-in Help: application documentation with a searchable topic catalog](tactic_stream/docs/assets/product-tour/help.png)

[Explore built-in Help →](tactic_stream/docs/presentations/help.en.md)

## Build on the platform

| Area | Explore |
| --- | --- |
| **Model and administration** | [Schemas and visual editors](tactic_stream/docs/presentations/product-tour.en.md#administration-shape-the-project-itself), [users and access](tactic_stream/docs/presentations/product-tour.en.md#users-groups-and-effective-access), [configuration](tactic_stream/docs/presentations/product-tour.en.md#configuration-connection-storage-and-daily-behavior). |
| **Context and activity** | [Object overview](tactic_stream/docs/presentations/product-tour.en.md#object-overview-the-complete-production-record) and [server history](tactic_stream/docs/presentations/product-tour.en.md#server-activity-understand-what-happened). |
| **Scripts and integrations** | [Script Editor and shelves](tactic_stream/docs/presentations/product-tour.en.md#script-editor-shelves-and-production-automation), [server APIs](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api), [development setup](tactic_stream/README.md). |
| **Interface language** | [Tactic Frame](tactic_stream/docs/presentations/product-tour.en.md#tactic-frame-one-ui-description-two-native-renderers): one shared UI description, native controls in Vue and Qt Quick. |

**[Full product tour →](tactic_stream/docs/presentations/product-tour.en.md)** · [All documentation](tactic_stream/docs/index.md)

Screenshots are current application captures on isolated Orbit Studio data; records and artwork are illustrative. Stream and Handler ship independently. Original TACTIC compatibility is documented by [scope and verification](tactic_stream/docs/compatibility.md).

Built from [Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC). [TACTIC license](tactic_stream/LICENSE.TACTIC) · [Third-party licenses](tactic_stream/docs/presentations/product-tour.en.md#scope-and-provenance).
