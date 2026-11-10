# TACTIC Stream: platform and tools

[Visual presentation](../../../README.md)

[Русский](product-tour.ru.md) · [Workflow](#workflow-graph-and-execution) · [Tasks & Gantt](#planning) · [Files & naming](#check-in-and-check-out) · [Tactic Frame](#tactic-frame) · [Administration](#project-administration) · [Get started](#installation-and-integrations)

[Docks](#docks-and-layouts) · [Sidebar Editor](#sidebar-editor) · [Object overview](#object-overview) · [Server history](#activity-feed-and-project-history) · [Users & access](#users-and-permissions)

| Explore the assistant | Build your own workspace |
| --- | --- |
| [**The built-in project assistant →**](assistant.en.md) — Query project data, prepare changes and inspect the operation log. | [**Custom dashboards →**](dashboards.en.md) — Combine metrics, charts, Item View and selection-driven tools into a project page. |

![TACTIC Stream — Item View with six Orbit Studio production assets](../assets/product-tour/item-view.png)

*Current application screenshots. Orbit Studio, its people and materials are demonstration data.*

> **Development prototype**, including the Perforce-like File Workspace.

## What Stream changes

[Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC) already brought together workflow, configurable data and asset management. Stream preserves that foundation: Search Types, `Search`/`SObject`, schemas, pipelines, commands, permissions and file publications.

Stream develops the TACTIC server on Python 3.14 and replaces its browser application with a Vue interface. Schema, workflow, view and page editors are part of that interface. Handler provides the desktop client; both use shared Tactic Frame descriptions. The name Stream refers to work moving through stages, from a task to a file publication.

| Foundation retained from TACTIC | Stream's approach | Practical result |
| --- | --- | --- |
| Configurable entities and relationships | Native core on Python 3.14, visual schema and field editors | Build the studio's model and work with it through current tools. |
| Workflow and command execution | Modern graph authoring, process inspectors and native server operations | Configure the route and inspect the rules that execute it. |
| Configurable views | Vue workspace, native Qt Handler and shared Tactic Frame descriptions | Use the browser or a desktop workflow with a common UI vocabulary. |
| Snapshots and naming | Publication tools, naming preview and explicit queues | Keep versions and file destinations attached to their production context. |
| Scriptable platform | Current editor, provider-independent assistant and visual page authoring | Extend the project through code, configuration or scoped assistant tools. |
| Server deployment | SQLite local edition and PostgreSQL server deployment | Evaluate locally, then deploy a dedicated service with an appropriate database. |

```mermaid
flowchart LR
    Model["Project schema\nObjects and relationships"] --> Work["Workflow\nProcesses and rules"]
    Work --> Team["Tasks and review\nPeople, dates, decisions"]
    Team --> Publish["Check-in\nNaming, versions, files"]
    Publish --> Delivery["Delivery and reuse\nRepository and clients"]
    Publish --> Team
```

## Item View and search

**Item View** displays project objects with previews, fields and actions. Its tree expands related records, processes and publications. Table mode supports comparing and editing fields, with sorting, filters and selection.

Search tabs retain their state. Filters define the server query; tags and quick filters provide frequently used selections. Tasks, notes, snapshots, details and a calendar can sit beside the results.

### Item Layouts

**Item Layouts** configures cards and rows: text, images, fields and actions. The editor binds elements to object data and previews project records. A saved layout can be assigned to a view.

![Item Layouts — structure, live object preview and editable properties](../assets/product-tour/item-layouts.png)

**Page layouts, item layouts and columns have distinct jobs:** a page composes a workspace, an item layout composes one object, and a table view chooses its fields and widgets. The sidebar connects these definitions to project navigation. [Item Layouts Help](../../frontend/public/help/item_layouts.en.md)

## Docks and layouts

**Docks** are the panels that make up the workspace. Place them side by side, combine them into tabs or hide them. A review layout can give most of the space to a preview and notes; planning can put objects beside tasks.

![Review arrangement — visual objects with a following context panel](../assets/product-tour/docks-review.png)

### Panel arrangement

Drag a panel's grip toward an edge to split the target, toward its center to create a tab stack, or toward the title to exchange positions. Resize the dividers, reorder stack tabs, maximize a panel temporarily or hide it and recover its space. A cancelled drag restores the previous arrangement.

Stream floats panels inside the browser workspace. It does not detach a dock into a native operating-system window. Narrow/phone presentation uses a compact active panel without rewriting the desktop split layout.

![Planning arrangement — object browsing and tasks share the workspace](../assets/product-tour/docks-planning.png)

| Workspace | A useful composition |
| --- | --- |
| **Review** | Item View + Snapshot Browser + Description/Notes: choose a record, inspect the publication, keep its discussion visible. |
| **Planning** | Results + Task Manager/Gantt + task details or calendar where supported: connect assignments and dates to production objects. |
| **Publishing** | Results + Drop Plate + Commit Queue: identify the destination, prepare files and inspect the pending publication. |
| **Documentation** | Results + Knowledge Base: keep project records beside the team's reference material. |

Panels can follow the object, process or snapshot selected in Search. Opening a task selects its record in Inspector. Rearranging panels leaves that connection intact.

### Personal and project layouts

Personal layouts are kept in tab state. **Layout presets** are named project layouts stored on the server; apply, save, replace or delete them as needed. A sidebar entry can use a preset as its starting layout, which users can then rearrange.

A preset stores panels and their arrangement. Saved searches and editor drafts are separate, and credentials are not part of a preset. Reset restores geometry while retaining records and queries. Docks work alongside Item Layouts, Columns Editor, pages and script shelves. [Docks and windows](../../frontend/public/help/windows.en.md)

## Sidebar Editor

Sidebar Editor assigns a Search Type, initial search, view, dock preset and script shelf to each navigation entry. Asset review might open cards and review panels; Asset planning might open a search and tasks. Entry visibility is configured by group.

![Sidebar Editor — an asset-review entry and its workspace settings](../assets/product-tour/sidebar.png)

| Editor area | What you build |
| --- | --- |
| **Navigation tree** | Links, sections and separators; order, nesting and visible entries. |
| **Item** | Display title, icon, Search Type, predefined search, initial item presentation, assigned dock preset and shelf. |
| **Configure search** | Prepare the actual search workspace, including saved search, quick filters, process visibility, sorting and grouping. |
| **Access** | Groups allowed to see an item; preview the draft for a selected group. Hidden entries remain editable. |
| **Technical / XML** | Stable internal identity, child views and the supported widget/view configuration. |

Handler's `tactic_handler` sidebar and TACTIC's `project_view` are independent definitions. The editor chooses the target explicitly. Its project selector controls the authoring scope, even if another project is open in the main workspace.

Rename the display title to change the label while retaining the internal identity. A configured Saved Search initializes the entry's first tab; reopening retains its working state instead of adding a duplicate tab. XML Apply updates the draft, and Save publishes the sidebar. Group preview changes what the editor shows; it does not impersonate that group or replace server data permissions. [Sidebar Editor Help](../../frontend/public/help/sidebar_editor.en.md)

## Object overview

**Details / SObject Report** collects an object’s description, participants, tasks, notes, files and history. Its header shows the preview and summary figures; sections below link to the underlying records.

![SObject Report — identity, work summary and participants for Survey Drone](../assets/product-tour/object-overview.png)

| Section | Contents |
| --- | --- |
| **Tasks and participants** | Statuses, processes and logged time. Participants come from tasks, notes, publications and time entries. |
| **Notes** | Object and process notes with links to their discussions. |
| **Children and relations** | Related production records. |
| **Snapshots and files** | Publications by process, versions, previews, file counts and total size. |
| **Activity** | Changes to the object, tasks, notes, publications, time entries and supported relationships, with their authors. |

From the overview, a task opens in Task Manager and Inspector, a note in its process discussion, and a publication in its source project. Cost figures require the corresponding permission. [SObject Report Help](../../frontend/public/help/sobject_info.en.md)

## Workflow: graph and execution

Workflow executes pipeline rules on the server: updating tasks, handling dependencies, calling scripts and sending notifications. A graph can contain parallel branches and approvals. The object’s production pipeline and a task’s status pipeline are configured separately.

![Workflow canvas — Concept, Model, Look development, Rig, Review and Publish](../assets/product-tour/workflow.png)

*Pipeline with parallel look development and rigging, an approval and an automatic action.*

| Node or rule | What it contributes |
| --- | --- |
| Manual and approval | Work assigned to people; review and sign-off stages. |
| Action and condition | Run configured server behavior or choose a route from a condition. |
| Hierarchy, input and output | Organize nested pipelines and their entry/exit points. |
| Dependency and progress | Coordinate related work and process completion. |
| Status and process events | React to pending, action, complete, revise, reject or error transitions. |
| Process rules | Update task or parent status, create downstream tasks, record actual dates, invoke a saved script or class, and configure notifications. |

In **Administration → Workflow**, select a pipeline and edit its graph and node settings. Options depend on the process type; technical views expose XML and advanced configuration. Triggers, notifications, dependencies and naming have separate settings. Saving the graph does not run its actions.

![Workflow inspector — selected process and its type-specific settings](../assets/product-tour/workflow-process.png)

## Planning

### Task Manager

**Task Manager** works with selected objects, a Search Type, personal tasks or team tasks. Table and compact views show assignees, supervisors, statuses, dates, progress and effort. Search, filters, grouping and sorting are available.

Edits remain explicit drafts until saved. Bulk changes apply to the selected tasks; the inspector keeps a task's object and discussion accessible. Server permissions determine the readable fields and available edits.

![Task Manager with project tasks, assignments, progress and dates](../assets/product-tour/tasks.png)

### Gantt, calendar and time tracking

Gantt places tasks on a timeline. Move or resize bars, edit progress, change scale or group the rows. Dependencies, overlapping assignments and scheduling warnings are displayed; undated tasks remain accessible.

![Gantt view with overlapping assignments, progress and scheduling warnings](../assets/product-tour/gantt.png)

*Gantt displays dependencies but does not automatically reschedule related tasks.*

The task calendar and agenda provide a date-oriented view; milestones represent project checkpoints. Work-hour entries and cost reports connect effort to people and work where the account has access. [Task Manager Help](../../frontend/public/help/dock.tasks.en.md) · [Calendar Help](../../frontend/public/help/dock.task_calendar.en.md)

## Messages and Notes

**Messages** supports direct and group conversations, including people from different projects. It has Favorites, replies, mentions, reactions, pins, forwarding, search and member management. Files can be picked, dragged in or pasted; unfinished messages remain in drafts.

![Messages — a production review conversation with four project participants](../assets/product-tour/messages.png)

**Notes** belong to an object, process or task and store feedback and review decisions. **Knowledge Base** holds articles and instructions with attachments and revision history. Notifications and activity entries link to changed records.

[Built-in Help: search and contextual instructions →](help.en.md) · [Knowledge Base: articles, editor and history →](knowledge-base.en.md)

## Activity Feed and project history

**Activity Feed** shows project events: notes, publications, tasks, field changes and time entries. Each event includes its author, time, details and a link to the object or task. An object’s Activity section shows its history and available events from related records.

![Activity Feed — server-backed project events and their actors](../assets/product-tour/activity-feed.png)

Filter by people and activity category, exclude your own actions, search loaded events or choose a day from the calendar. Older events load while scrolling; calendar counts cover accessible history beyond the currently loaded list. Dates follow the user's local timezone, while relative ages use synchronized server time.

**Notifications** stores notices from the current client session; **System Activity / Debug Log** covers application work and diagnostics. Clearing notifications leaves project history intact. Activity Feed coverage depends on the events recorded by operations and extensions.

## Check-in and check-out

Browser check-in uploads files and records a snapshot against the selected object and process:

1. Select the record and publication context; add files in the browser's supported upload/check-in flow.
2. Review the target, description and naming settings before submitting.
3. The server validates permissions and naming, stores the files and records a snapshot.
4. Use Snapshot Browser to inspect versions, previews and file lists, or download the required publication.

![Snapshot Browser — Survey Drone publications](../assets/product-tour/snapshot-browser.png)

The browser handles uploads and downloads. Handler adds workstation paths, local repository mappings and DCC scene operations when the workflow requires desktop access. The shared server remains the owner of publication metadata, naming and permissions.

A snapshot ties a version to its object, process/context, author, description and files. New versions and revisions are different operations. `latest` and `current` naming rules are separate from versioned storage. File sequences retain their range information so checkout can resolve the published frames.

### Naming Editor

**Naming Editor** defines rule conditions, contexts, filename and directory patterns, sandbox paths and repository aliases. Patterns use object, snapshot and file data, with TSQL conditions and trusted saved scripts where needed. The editor previews the rule’s result.

![Naming editor — context matching, path patterns and native preview](../assets/product-tour/naming.png)

For example, a rule can derive a filename from the object's name, version and extension: `{sobject.name}_v{version}.{ext}`. The native naming engine resolves the actual paths at publication time. A preview is not a reservation: the final check-in still validates the version and collisions. Script-based naming executes trusted project code.

### Local file access through Handler

Handler's **Repository Sync** can discover and download the selected objects, processes and versions into a mapped local repository. Its queue and presets belong to the desktop client. Stream supplies the records and files; Repository Sync is not a browser feature. The same boundary applies to desktop Watch Folders and native Maya operations.

## Tactic Frame

**Tactic Frame** is the shared interface description language used by Handler and Stream. A module defines elements, geometry, state and actions. Qt Quick and Vue render it with their own controls, so the window’s structure can be changed in one place.

Frame consists of JavaScript modules (`.mjs`). The `describe(model, width, height, language)` function builds the visible structure from state. Actions are handled by the client’s controllers.

```mermaid
flowchart TB
    Description["Tactic Frame\nShared descriptions, controls and state rules"] --> Qt["Qt Quick\nNative Handler UI"]
    Description --> Vue["Vue\nStream browser UI"]
    Qt --> Client["Desktop controllers\nLocal files and DCC routing"]
    Vue --> Web["Web controllers\nBrowser interaction"]
    Client --> Server["TACTIC Stream commands and permissions"]
    Web --> Server
```

A small description module saved beside this document illustrates the contract. The host supplies `model` and handles the `name` action; production modules also use the shared translation helpers.

```javascript
import { label, node, rect } from "../../src/tactic_stream/shared_ui/core/frame.mjs";

export function describe(model, width, height, language) {
    return { nodes: [
        label("title", rect(16, 12, width - 32, 28), "Review"),
        node("Field", "assetName", rect(16, 48, width - 32, 38), {
            label: "Asset", text: model.name, action: { type: "name" }
        })
    ] };
}
```

Shared building blocks cover fields, buttons, selectors, virtualized lists, tables, graphs, editors and window structure. Themes, translations, focus and input behavior belong to the contract as well as geometry. **Component showcase** makes those building blocks inspectable inside the application.

![Component showcase — shared controls rendered in the application](../assets/product-tour/frame-showcase.png)

XML views and visual editor documents store project configuration. Frame modules define interface components. Stream and Handler ship separately, each with a copy of the shared descriptions. [Frame contracts](../frame/index.md)

## Script Editor and automation

**Script Editor** runs a script or a selection, displays results and errors and saves scripts to the project library. It has tabs, drafts, undo, highlighting, completion, search and replace, and an outline. Folders organize the library.

![Script Editor — saved project script and production record query](../assets/product-tour/script-editor.png)

| Runtime | Where it runs and what it can use |
| --- | --- |
| **Server Python** | The TACTIC server, its project context, native objects and commands. |
| **Browser JavaScript** | The browser with its supported context, project/selection values, `rpc` and refresh helpers. |
| **Server JavaScript** | QuickJS-NG on the server with the synchronous `server` API; no browser DOM or desktop DCC context. |

Execution location matters. A returned server result appears in the editor; server Python process stdout remains in the server log. Administrator/supervisor capabilities govern editing and running scripts.

**Script shelves** put saved actions beside the work: shared studio tools, personal tools and tools attached to a search tab. Server workflow events and saved scripts provide project automation. Handler additionally owns its Before/After hooks around desktop and DCC actions. Code execution is a trusted capability, separate from merely viewing a script.

[Script Editor Help](../../frontend/public/help/script_editor.en.md) · [Script Shelf Help](../../frontend/public/help/script_shelf.en.md)

## Project administration

**Administration** defines the project model: Search Types, fields, relationships, views and actions. Asset and Shot are example types; studios can create their own. The schema graph shows the relationships between them.

![Project schema — entities and relationships in Orbit Studio](../assets/product-tour/schema.png)

| Section | What you configure |
| --- | --- |
| **Search Types** | Entity definitions, fields and their naming rules. |
| **Project schema** | Relationships between entities and the project graph. |
| **Workflow** | Pipelines, process properties, dependencies and automation. |
| **Columns Editor** | Table views, columns and native field widgets. |
| **Raw database** | Direct authorized table inspection/editing and CSV work, with protected-table restrictions. |
| **Page layouts** | Whole dashboard pages, their blocks, data sources and navigation. |
| **Item layouts** | Reusable cards, rows and object presentations. |
| **Sidebar Editor** | Navigation groups, entries, views and workspace entry points. |
| **Plugins** | Packages, versions and project activation. |
| **Component showcase** | The control vocabulary used by the interfaces. |
| **Users** | Accounts and their project access. |
| **Groups** | Membership and shared access configuration. |
| **Access rules** | Inherited and explicit allow/deny rules; effective access checks for a user. |

![Access rules — group permissions and explicit allow/deny configuration](../assets/product-tour/access-rules.png)

Editors keep drafts until Save or Discard. Saving checks the revision and server permissions. [Administration Help](../../frontend/public/help/administration.en.md)

## Users and permissions

A server account is shared across projects. It holds the profile, contact details, settings and group memberships. Tasks, messages, publications and activity records refer to that account as their author.

![Users — directory, profile, account and group editing](../assets/product-tour/users.png)

### Accounts

New accounts receive an initial password, profile and groups. Stored passwords are not displayed. Retire disables the account and Reactivate enables it again; existing project history retains the author’s identity.

### Groups and access checks

Groups manage membership and descriptions. Access rules manage the policy: access level, project scope, supported object/process/status/action rules, inheritance and explicit allow/deny. Sidebar visibility is a separate part of the interface policy; hiding a link is not the same as denying access to its records.

![Groups — membership and server group configuration](../assets/product-tour/groups.png)

Effective access combines all of the user’s groups, inheritance and explicit rules. Check the result for a specific account after configuration. A single group’s matrix shows only that part of the policy.

Onboarding includes the account, group membership, project permissions and sidebar visibility, followed by an effective-access check. The project selected in Administration limits project settings; accounts remain shared across the server.

## Configuration

**Configuration** contains connection, storage and client settings. Each page keeps a draft: Apply affects the current page, while Save handles pending changes. Leaving unsaved settings prompts a warning. Appearance changes can be previewed and reverted.

![Configuration — appearance, theme and workspace preferences](../assets/product-tour/configuration.png)

| Area | Purpose |
| --- | --- |
| **AI providers** | Provider profiles, model discovery and executor selection for the assistant. |
| **Server** | Connection and supported server options, live service information and explicit lifecycle actions. |
| **Database resources** | Configure/test resources and bind existing schemas; this does not migrate data. |
| **Repositories** | Repository names, colors, mappings and supported server storage settings. Saving a path does not move files. |
| **Projects** | Project creation, templates and project-level setup. |
| **Check-in Options** | Defaults for file preparation, naming and publishing behavior. |
| **Global** | General interaction and update preferences applicable to the current client. |
| **Appearance** | Light/dark themes, palettes, icon choices and English/Russian interface language. |
| **Cache** | Cache policy, visibility and maintenance. |
| **Tasks** | Task defaults and effort/time preferences. |

Supported server XML settings expose service, network, security, directory and scheduling controls with validation and restart requirements. Changing configuration and restarting a service are separate actions. Repository and database migration require their own procedure. [Configuration Help](../../frontend/public/help/configuration.en.md)

## Project assistant

**External agent** reads tasks, notes and publications for selected objects. Conversation context includes the project, page, Search Type and selection. Writing requires separate permission.

![Assistant — Survey Drone tasks, notes and file versions](../assets/product-tour/assistant.png)

In this request, the assistant found a completed modeling task without a model publication. The separate presentation covers conversations, providers, attachments, changes and scripts.

**[Explore the built-in assistant →](assistant.en.md)**

## Dashboards

A dashboard combines metrics, reports, charts, Item View, forms and actions. Detail blocks can follow the selected object. Pages are saved in the project and opened from the sidebar; user permissions determine data access.

![Production overview — live task metrics, status distribution, workload and Item View](../assets/product-tour/dashboard-overview.png)

**[Explore custom dashboards and their visual editor →](dashboards.en.md)**

## Installation and integrations

### Run Stream from source

Use Python 3.14 on Windows and a fresh data directory for the first installation.

```powershell
Set-Location tactic_stream
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
..\START_TACTIC_STREAM.bat
```

The launcher initializes SQLite when needed, requests an administrator password on first setup and opens the configured address. Built web assets are included in the checkout. [CLI and development setup](../../README.md#local-development)

| Delivery | Components | Guide |
| --- | --- | --- |
| Portable Windows | Launcher, bundled Python/web application, SQLite and optional Handler workflow | [Windows delivery](../delivery/WINDOWS_DELIVERY.en.md) |
| Dedicated Linux server | Stream behind Apache with PostgreSQL, delivered through Docker Compose | [Server delivery](../delivery/SERVER_DELIVERY.en.md) |

Back up database, repository and configuration together. An application rollback needs its matching data backup. [Recovery](../delivery/RECOVERY_ACCEPTANCE.md)

### Server API

On a running instance, `/api/documentation` exposes the method catalogue and `/api/compatibility` describes the original contract. XML-RPC remains an integration entrance for existing clients. The native core retains familiar `pyasm`/`tactic` modules and command semantics; integration code must use the appropriate server API rather than Handler's in-memory client objects.

[Server API source map](../admin_agent/SOURCES.md#ts-server-api) · [Core model](../../frontend/public/help/core_model.en.md) · [Architecture](../architecture.md) · [Workspace Pulse example](../../../examples/workspace_pulse/README.md) · [Studio Review example](../../../examples/studio_review/README.md)

## Compatibility, limitations and licenses

Stream and Handler are independent repositories and bundles. Stream does not import Handler or the legacy source tree at runtime. Original TACTIC compatibility is an explicit verification effort, not a blanket guarantee that every historical plugin or script works unchanged.

The old `pyasm.prod` production layer and Drupal are outside this port; MySQL support is deferred, and S3 is excluded. Check the [compatibility scope](../compatibility.md) before planning a migration. [Documentation index](../index.md)

Screenshots use a small demonstration project. Production deployment requires checks of the studio’s schema, scripts, integrations and permissions against the deployed version.

[Original TACTIC license](../../LICENSE.TACTIC) · [QuickJS-NG](../../LICENSE.QUICKJS-NG) · [Vue](../../frontend/public/LICENSE.VUE.txt) · [Icon-font notices](../../frontend/public/licenses/icon-fonts/SOURCES.md)
