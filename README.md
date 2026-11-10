# ![TACTIC Stream](tactic_stream/docs/assets/readme/wordmark.svg)

**Asset management and production tracking.**

[Русский](README.ru.md) · **[Get started](#setup-and-first-project)** · [Why Stream](#why-fork-tactic) · [Features](#features-at-a-glance) · [Feature tour](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour) · [Documentation](https://github.com/listyque/TACTIC-Stream/wiki/Home)

TACTIC Stream is a **self-hosted platform for managing production, project data and versioned files**. It includes a server and a browser application where a team can organize assets and shots, assign tasks, review work and publish files. It is built on **Python 3.14 and Vue 3** and developed as a fork of **Southpaw TACTIC**.

You define what the project contains and how work moves through it: the objects, their relationships, production stages, permissions and file-naming rules. A shot’s tasks, notes and published scenes stay connected to that shot. Stream can also manage a model library, documents or deliverables using your own record types. It runs on your infrastructure; the separate **TACTIC Handler** desktop client adds local-file workflows and Maya integration.

![TACTIC Stream Item View: project assets](tactic_stream/docs/assets/product-tour/item-view.png)

> **Development prototype**, including the Perforce-like File Workspace.

## Who it is for

- **Animation and VFX teams** — track assets, sequences and shots from assignment through review and publication.
- **Supervisors, coordinators and production managers** — plan dates, see workload and missing deliveries, keep discussions and decisions with the work.
- **Pipeline TDs and administrators** — build the studio’s data model, automate transitions, configure interfaces and connect other tools through scripts and APIs.

The project model is configurable. Production tracking is a natural use case, but Stream’s objects do not have to be assets or shots.

## Why fork TACTIC?

TACTIC already provides much of the difficult foundation: configurable types and relationships, a workflow engine, permissions, transactions, file snapshots, naming and a Python API. Those concepts let a studio describe its own production process and connect tools to it.

The fork preserves that foundation while developing a current Python server, a new browser application and shared interfaces with Handler. The changes reach the core, transports, editors and deployment, so Stream develops them together as an independent product. Existing TACTIC concepts and supported script contracts remain useful when extending a project.

**Stream** refers to work moving through production. An object has tasks, review decisions and published files; workflow connects those stages. This lets the team follow both the assignment and the material handed to the next department.

## What Stream changes

| Area | What Stream brings | Why it helps |
| --- | --- | --- |
| **Server and deployment** | Python 3.14, a FastAPI/Uvicorn HTTP layer, local SQLite and a PostgreSQL server edition. | Start with a local installation or deploy a dedicated service on your own infrastructure. |
| **Everyday workspace** | A Vue application with Item View, cards, editable tables, docks, retained search tabs, light/dark themes and EN/RU localization. | Arrange objects, tasks, notes and publications around the work you are doing. |
| **Project authoring** | Integrated schema, workflow, naming, sidebar, item-layout and page editors. | Configure a project’s data, production rules and working screens in the same application. |
| **Browser and desktop UI** | Tactic Frame descriptions rendered by Vue in Stream and native Qt Quick in Handler. | Shared screens use common layout and interaction rules while each client keeps its own browser or desktop capabilities. |
| **Team-specific pages** | Visual dashboard authoring, reusable widgets and project packages. | Build a department overview or delivery page from the project’s actual records and reuse it elsewhere. |
| **Project assistance** | An integrated assistant with project context and operation history, plus an editable Knowledge Base and searchable Help. | Ask about the current work, inspect proposed changes and keep studio instructions close to the records they describe. |

Stream retains TACTIC’s core model and supported APIs; legacy configurations, scripts and plugins still need checking against the [compatibility scope](https://github.com/listyque/TACTIC-Stream/wiki/TACTIC-compatibility). The old production subsystem and some historical widgets are excluded.

[TACTIC foundations and Stream’s implementation →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#what-stream-changes)

## Features at a glance

| Area | What you can do |
| --- | --- |
| **Project data** | Create your own object types, fields, forms and relationships. Start with an empty project or a template and manage its structure in [Administration](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#project-administration). |
| **Workflow engine** | Build pipelines with manual work, approvals, actions, conditions and nested processes. The server handles configured events, tasks, scripts and notifications; the editor exposes the graph and node settings. |
| **Search and Item View** | Find records by text, tags, fields and related data; save searches; expand objects into relationships, processes and versions. Choose cards, rows or editable tables. |
| **Tasks and scheduling** | Assign work, edit statuses and dates, make bulk changes and plan in [Task Manager, Gantt and calendar](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#planning). Record work hours and inspect task history. |
| **Files and publications** | Prepare uploads in Drop Plate and Commit Queue, check in versioned snapshots, inspect their files and previews, and configure naming and repository paths. |
| **Review and communication** | Keep Notes with an object or process, use Messages for conversations, open an object overview and follow server activity. |
| **Workspace and dashboards** | Arrange docks, save layouts, design object cards and compose [pages](https://github.com/listyque/TACTIC-Stream/wiki/Tour-dashboards) from metrics, charts, Item View and actions. Assign views and access through Sidebar Editor. |
| **Users and administration** | Manage accounts, groups and project permissions; inspect configuration and server information through the application. |
| **Scripts, API and packages** | Write and run server scripts in Script Editor, expose tools on shelves, call Python/XML-RPC/HTTP APIs and distribute project resources as plugins or templates. |
| **Help, knowledge and assistant** | Read built-in EN/RU Help, publish studio articles with attachments and revision history, or ask the [assistant](https://github.com/listyque/TACTIC-Stream/wiki/Tour-assistant) to examine project data and prepare supported changes. |

The browser handles project work and file uploads/downloads. Local repository synchronization, watched workstation folders and Maya scene operations belong to Handler.

## What you can build with it

- **An animation or VFX production project:** episodes, sequences, shots and assets, with assignments, review stages and publications attached to each object.
- **A reusable asset library:** models, textures, references and their variants, searchable by your own fields and tags, with versioned files and usage relationships.
- **A review and delivery process:** records for submissions, responsible people, approval steps, feedback and the exact file version being delivered.
- **A department workspace:** a sidebar entry opening the department’s search, dock arrangement, tools and dashboard; instructions live alongside it in the Knowledge Base.

The repository includes two installable examples:

- **[Studio Review](https://github.com/listyque/TACTIC-Stream/wiki/Studio-Review)** adds a review type, sample records, a sidebar entry, reusable widgets, a theme and a Python approval action. It shows how a project package combines data, UI and behavior.
- **[Workspace Pulse](https://github.com/listyque/TACTIC-Stream/wiki/Workspace-Pulse)** adds task and deadline summaries, charts, a searchable queue and a VFX overview based on the project’s existing types. Its pages remain editable in Page Editor.

Start with project configuration and the visual editors. Add scripts for custom rules, and package the result when another project needs the same setup.

## Technology

| Part | Implementation |
| --- | --- |
| Server core | **Python 3.14+**, retaining TACTIC’s `pyasm` / `tactic`, `Search` / `SObject`, Command, permissions and transactions. |
| HTTP service | **FastAPI and Uvicorn**, with HTTP/editor routes and the compatible **XML-RPC** endpoint used by TACTIC clients. |
| Browser application | **Vue 3**, JavaScript and **Vite**. The server ships built UI assets; normal users do not need Node.js. |
| Shared UI | **Tactic Frame**, portable JavaScript modules describing shared screens and interaction rules for Vue and Qt Quick. |
| Data and files | **SQLite** for local installations or **PostgreSQL** for the server edition; publications use a configured filesystem repository. |
| Desktop package | **Electron** hosts the Stream UI and manages its bundled local Python server. Handler is a separate native **PySide6 / Qt Quick** client. |
| Server deployment | Linux containers with **Docker Compose, Apache and PostgreSQL**. |

[Architecture](https://github.com/listyque/TACTIC-Stream/wiki/Architecture) · [Python dependencies](tactic_stream/pyproject.toml) · [Frontend dependencies](tactic_stream/frontend/package.json) · [Tactic Frame](https://github.com/listyque/TACTIC-Stream/wiki/Frame)

## Setup and first project

**[Download Clean / Demo](https://github.com/listyque/TACTIC-Stream/releases)** — Windows, Docker/PostgreSQL, Synology DSM and combined TH + TS bundles. [Demo projects](examples/demo/README.md) · [Windows guide](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md) · [DSM guide](tactic_stream/docs/delivery/DSM_DELIVERY.en.md).

| Run Stream | Start here |
| --- | --- |
| **Windows desktop / SQLite** | [Portable package guide](https://github.com/listyque/TACTIC-Stream/wiki/Windows): local application, repository and optional native Handler. |
| **Linux server / PostgreSQL** | [Server deployment guide](https://github.com/listyque/TACTIC-Stream/wiki/Server): Docker Compose, Apache and a dedicated database. |
| **From source** | [Local development](https://github.com/listyque/TACTIC-Stream/wiki/Development#local-development): Python 3.14, editable installation and the repository launcher. |

The first setup asks you to create the administrator password. Open or create a project, configure its data, then create accounts and grant the team access.

## Stream tools

### Workflow engine

Workflow defines routes through production, including parallel stages, conditions and approvals. The server handles events according to pipeline rules: creating tasks, running actions and sending notifications. The editor shows the complete graph and each node’s settings.

![Workflow editor: connected production stages and review](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow: from definition to execution →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#workflow-graph-and-execution)

### Workspace configuration

Arrange object lists, tasks, previews and notes side by side, combine them into tabs and save the layout. Sidebar Editor defines department navigation, Item Layouts configures object cards, and the page editor builds dashboards. They use the same project records.

![Dock composition: visual objects, tasks and publication previews](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#item-view-and-search) · [Docks →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#docks-and-layouts) · [Sidebar Editor →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#sidebar-editor)

### Task Manager and Gantt

Task Manager edits assignees, dates and statuses. Gantt shows the schedule and overlapping work. Open a task to reach its object and discussion, or use Messages for team conversations. Project history records changes to plans and statuses.

![Gantt: production tasks arranged across the team's schedule](tactic_stream/docs/assets/product-tour/gantt.png)

[Planning →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#planning) · [Notes and Messages →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#messages-and-notes)

### Publications and file versions

Check-in stores a file against an object and process, assigns a version and applies naming and directory rules. Snapshot Browser shows the publications and their contents. Handler adds local repository synchronization and opening scenes in Maya.

![Snapshot Browser: Survey Drone publications and file previews](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Check-in, versions, naming and delivery →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#check-in-and-check-out)

### Dashboards

Dashboard Editor puts metrics, charts, tables and Item View on one page. Details and actions can follow the selected object. The example below combines task and workload reports with an asset navigator.

![Custom dashboard: live project metrics, workload and visual records](tactic_stream/docs/assets/product-tour/dashboard-overview.png)

[Dashboards and visual page authoring →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-dashboards)

### Project assistant

The assistant reads project records, prepares reports and drafts changes through its available tools. Below, it reviewed Survey Drone: modeling was marked complete, but no model had been published. Operation details are available alongside the answer. Using the assistant requires a separately configured model provider.

![Project assistant examining production records](tactic_stream/docs/assets/product-tour/assistant.png)

[Assistant: providers, tools and capabilities →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-assistant)

### Knowledge Base and Help

Knowledge Base holds instructions, delivery requirements and technical notes. Articles can link to project objects and include files. The editor offers Visual and Markdown modes, with drafts, publication and revision history.

![Knowledge Base: a delivery checklist linked to a production asset](tactic_stream/docs/assets/product-tour/knowledge-base.png)

[Knowledge Base: authoring and publishing →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-knowledge-base)

Built-in Help documents application tools and settings. It opens from working tools and supports search, English and Russian articles, and Markdown export.

![Built-in Help: application documentation with a searchable topic catalog](tactic_stream/docs/assets/product-tour/help.png)

[Explore built-in Help →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-help)

## Configuration and development

| Area | Explore |
| --- | --- |
| **Model and administration** | [Schemas and visual editors](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#project-administration), [users and access](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#users-and-permissions), [configuration](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#configuration). |
| **Context and activity** | [Object overview](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#object-overview) and [server history](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#activity-feed-and-project-history). |
| **Scripts and integrations** | [Script Editor and shelves](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#script-editor-and-automation), [server APIs](https://github.com/listyque/TACTIC-Stream/wiki/Server-API-references#ts-server-api), [development setup](https://github.com/listyque/TACTIC-Stream/wiki/Development). |
| **Interface language** | [Tactic Frame](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#tactic-frame): one shared UI description, native controls in Vue and Qt Quick. |

**[Full product tour →](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour)** · [All documentation](https://github.com/listyque/TACTIC-Stream/wiki/Home)

Screenshots are current application captures on isolated Orbit Studio data; records and artwork are illustrative. Stream and Handler ship independently. Original TACTIC compatibility is documented by [scope and verification](https://github.com/listyque/TACTIC-Stream/wiki/TACTIC-compatibility).

Built from [Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC). [TACTIC license](tactic_stream/LICENSE.TACTIC) · [Third-party licenses](https://github.com/listyque/TACTIC-Stream/wiki/Tour-product-tour#compatibility-limitations-and-licenses).
