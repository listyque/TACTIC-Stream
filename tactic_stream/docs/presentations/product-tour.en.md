# TACTIC Stream — Full product tour

[Visual presentation](../../../README.md)

**A configurable production platform built from TACTIC:** a modern Python server, a Vue workspace and a workflow engine connecting project data, people and files.

**Objects, people, processes and published files — one production context.**

[Русский](product-tour.ru.md) · [Workflow](#workflow-is-an-execution-engine) · [Tasks & Gantt](#plan-the-work-then-follow-it-through) · [Files & naming](#from-working-file-to-traceable-publication) · [Tactic Frame](#tactic-frame-one-ui-description-two-native-renderers) · [Administration](#administration-shape-the-project-itself) · [Get started](#run-it-and-extend-it)

[Docks](#docks-assemble-the-interface-around-a-job) · [Sidebar Editor](#sidebar-editor-turn-navigation-into-a-workflow) · [Object overview](#object-overview-the-complete-production-record) · [Server history](#server-activity-understand-what-happened) · [Users & access](#users-groups-and-effective-access)

| Explore the assistant | Build your own workspace |
| --- | --- |
| [**The built-in project assistant →**](assistant.en.md) — Ask about real records, prepare changes and inspect the operations behind an answer. | [**Custom dashboards →**](dashboards.en.md) — Combine metrics, charts, Item View and selection-driven tools into a project page. |

![TACTIC Stream — Item View with six Orbit Studio production assets](../assets/product-tour/item-view.png)

*Fresh captures of the current application in Orbit Studio, a disposable demonstration project with fictional people and concept artwork. The interfaces and records are real; the artwork is illustrative.*

> **Development prototype.** The product is under active development. The Perforce-like File Workspace is also a prototype. Evaluate your actual schema, permissions, scripts and file workflows on isolated data before production use.

## Why this project exists

[Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC) already brought together workflow, configurable data and asset management. Stream preserves that foundation: Search Types, `Search`/`SObject`, schemas, pipelines, commands, permissions and file publications.

**The purpose of the fork is to carry that model into a modern, configurable production workspace.** Stream develops the server core and its browser application together, supports native Handler alongside the browser, and makes project authoring accessible through visual editors. “Stream” describes the continuous route from incoming work to review and delivery: changes, tasks and files stay connected throughout it.

| Foundation retained from TACTIC | Stream's approach | Practical result |
| --- | --- | --- |
| Configurable entities and relationships | Native core on Python 3.14, visual schema and field editors | Build the studio's model and work with it through current tools. |
| Workflow and command execution | Modern graph authoring, process inspectors and native server operations | Configure the route and inspect the rules that execute it. |
| Configurable views | Vue workspace, native Qt Handler and shared Tactic Frame descriptions | Use the browser or a desktop workflow with a common UI vocabulary. |
| Snapshots and naming | Publication tools, naming preview and explicit queues | Keep versions and file destinations attached to their production context. |
| Scriptable platform | Current editor, provider-independent assistant and visual page authoring | Extend the project through code, configuration or scoped assistant tools. |
| Server deployment | SQLite local edition and PostgreSQL server deployment | Evaluate locally, then deploy a dedicated service with an appropriate database. |

These are concrete changes in the product approach, not a claim that Stream invented TACTIC's workflow engine or is faster in every workload.

The practical focus is the handoff: a record describes the work, a pipeline describes its route, tasks identify who does it, discussions preserve decisions, and snapshots identify exactly what was delivered. A status, a chat message and a filename can then be understood in the context of the same object.

```mermaid
flowchart LR
    Model["Project schema\nObjects and relationships"] --> Work["Workflow\nProcesses and rules"]
    Work --> Team["Tasks and review\nPeople, dates, decisions"]
    Team --> Publish["Check-in\nNaming, versions, files"]
    Publish --> Delivery["Delivery and reuse\nRepository and clients"]
    Publish --> Team
```

## A workspace built around the item

An asset, shot, document or custom entity is the entry point. **Item View** gives it a visual identity, useful fields and direct actions. The continuous tree reveals related objects, processes and publications. The table exposes structured fields for sorting, filtering, selection and editing. These are different ways to work with the same project records.

Search tabs retain their context. Filters narrow the server query; tags and quick filters make recurring selections accessible. Docks place tasks, notes, snapshots, details or a calendar next to the working selection. Saved workspace arrangements let departments start with a useful set of panels.

### Design the cards your team needs

The **Item Layouts** editor binds images and text to object data and places supported native actions inside the card. Build a compact production row, a large review card or a reusable detail layout. Preview with actual project records and save the view as project configuration.

![Item Layouts — structure, live object preview and editable properties](../assets/product-tour/item-layouts.png)

**Page layouts, item layouts and columns have distinct jobs:** a page composes a workspace, an item layout composes one object, and a table view chooses its fields and widgets. The sidebar connects these definitions to project navigation. [Item Layouts Help](../../frontend/public/help/item_layouts.en.md)


## Docks: assemble the interface around a job

The workspace is a **composition of functional panels**. Put search results next to a large file preview, stack reference panels into tabs, reserve the lower half for tasks, or move a utility out of the way. The same project can have a review workspace, a planning workspace and a publishing workspace assembled from the available docks.

![Review arrangement — visual objects with a following context panel](../assets/product-tour/docks-review.png)

### Split, stack, float and restore

Drag a panel's grip toward an edge to split the target, toward its center to create a tab stack, or toward the title to exchange positions. Resize the dividers, reorder stack tabs, maximize a panel temporarily or hide it and recover its space. A cancelled drag restores the previous arrangement.

Stream floats panels inside the browser workspace. It does not detach a dock into a native operating-system window. Narrow/phone presentation uses a compact active panel without rewriting the desktop split layout.

![Planning arrangement — object browsing and tasks share the workspace](../assets/product-tour/docks-planning.png)

| Workspace | A useful composition |
| --- | --- |
| **Review** | Item View + Snapshot Browser + Description/Notes: choose a record, inspect the publication, keep its discussion visible. |
| **Planning** | Results + Task Manager/Gantt + task details or calendar where supported: connect assignments and dates to production objects. |
| **Publishing** | Results + Drop Plate + Commit Queue: identify the destination, prepare files and inspect the pending publication. |
| **Documentation** | Results + Knowledge Base: keep project records beside the team's reference material. |

The selection connects the panels. An object, process or snapshot chosen in Search becomes the context of following panels; opening a task keeps its exact identity. A layout changes where tools live without changing their data ownership or permissions.

### Personal arrangement and shared starting point

Personal workspace state retains placement, sizes, visibility and stacks in its owning client/tab. **Layout presets** save named project arrangements on the server: apply, refresh, save, replace and delete are separate operations. Assign a preset to a sidebar entry so a department opens into a useful default; later personal tab state can retain that user's arrangement.

A preset describes panels and their layout. It does not save credentials, commit an editor draft or become a saved search. Reset restores workspace geometry without deleting project records or saved searches. In combination with Item Layouts, Columns Editor, page layouts and script shelves, docks let a studio compose a wide range of working interfaces from implemented tools. [Docks and windows](../../frontend/public/help/windows.en.md)


## Sidebar Editor: turn navigation into a workflow

A sidebar item can define much more than a label. It connects a Search Type, initial search, presentation, workspace layout and script shelf. “Asset review” and “Asset planning” can open the same underlying records with different starting filters and tools.

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


## Object overview: the complete production record

Open **Details / SObject Report** for a record to move from a result card to its production overview. The profile-style header combines preview, identity, description and metrics; the section switcher leads into work associated with that exact object.

![SObject Report — identity, work summary and participants for Survey Drone](../assets/product-tour/object-overview.png)

| Section | What it answers |
| --- | --- |
| **Tasks and participants** | Who is involved, what statuses/processes exist, and how much work has been logged? Participants are gathered from tasks, notes, publications and work entries. |
| **Notes** | Which decisions and comments belong to the object or its processes? Open a note in its original context. |
| **Children and relations** | What related production objects sit underneath or alongside this record? |
| **Snapshots and files** | Which processes have publications, how many files do they contain, and what is their total size? Expand the process tree for versions and previews. |
| **Activity** | Who created or changed the object, tasks, notes, publications, work entries and supported relationships? |

A task opens the matching Task Manager scope and selects the exact task in Inspector. A note returns to its process discussion. Publications retain their source project. Cost information is shown only with the corresponding permission. This report provides the context behind a status rather than forcing a user to reconstruct it from unrelated screens. [SObject Report Help](../../frontend/public/help/sobject_info.en.md)


## Workflow is an execution engine

The pipeline graph is backed by server operations. Each object can follow a configured pipeline; process events drive task state, dependencies, scripts and notifications. The object pipeline and a task's status pipeline serve different purposes, so an asset's production route need not be reduced to the task's Pending / In Progress / Complete statuses.

![Workflow canvas — Concept, Model, Look development, Rig, Review and Publish](../assets/product-tour/workflow.png)

*A configured production graph with parallel look development and rigging, an approval stage and an automatic action. The screenshot demonstrates the definition; it is not evidence that every branch has executed.*

| Node or rule | What it contributes |
| --- | --- |
| Manual and approval | Work assigned to people; review and sign-off stages. |
| Action and condition | Run configured server behavior or choose a route from a condition. |
| Hierarchy, input and output | Organize nested pipelines and their entry/exit points. |
| Dependency and progress | Coordinate related work and process completion. |
| Status and process events | React to pending, action, complete, revise, reject or error transitions. |
| Process rules | Update task or parent status, create downstream tasks, record actual dates, invoke a saved script or class, and configure notifications. |

Author in **Administration → Workflow**: choose a pipeline, arrange its graph, inspect the selected process, edit its type-specific settings, and save the draft. Technical views expose XML and advanced configuration when a studio needs precise control. Dependencies, triggers, notification rules and naming are related configuration, not interchangeable concepts. Saving a graph does not execute its actions or send mail.

![Workflow inspector — selected process and its type-specific settings](../assets/product-tour/workflow-process.png)

## Plan the work, then follow it through

### Task Manager

Move between selected-object work, a Search Type, the project, personal work and team scopes. Table and compact presentations expose status, assignee, supervisor, dates, progress and effort. Search, filters, grouping and sorting make the same workspace useful to an artist checking today's work and a supervisor preparing the next handoff.

Edits remain explicit drafts until saved. Bulk changes apply to the selected tasks; the inspector keeps a task's object and discussion accessible. Server permissions determine the readable fields and available edits.

![Task Manager with project tasks, assignments, progress and dates](../assets/product-tour/tasks.png)

### Gantt, calendar and effort

The Gantt view adds a time axis to the task set. Move or resize task bars, adjust progress, change scale and group by assignee. Existing dependencies and scheduling warnings help expose conflicts. Unscheduled work remains visible rather than being lost outside the date range.

![Gantt view with overlapping assignments, progress and scheduling warnings](../assets/product-tour/gantt.png)

*Orbit's sample schedule deliberately contains overlaps. The warnings are part of the real interface. Dependency visualization does not imply automatic cascading rescheduling.*

The task calendar and agenda provide a date-oriented view; milestones represent project checkpoints. Work-hour entries and cost reports connect effort to people and work where the account has access. [Task Manager Help](../../frontend/public/help/dock.tasks.en.md) · [Calendar Help](../../frontend/public/help/dock.task_calendar.en.md)

## Conversations that retain production context

**Messages** handles direct conversations, group discussions and Favorites across projects. Replies, mentions, reactions, pins, forwarding, member management and conversation search support ongoing coordination. Attach files through the picker, drag and drop or the clipboard; drafts preserve unfinished messages.

![Messages — a production review conversation with four project participants](../assets/product-tour/messages.png)

Use **Notes** for decisions that belong to an object, process or task. Use notifications and the activity journal to follow changes and return to the affected records. The **Knowledge Base** gives longer-lived documentation a tree of Markdown articles, attachments and revision history. A chat can organize a review; the resulting decision can stay attached to the thing being reviewed.


## Server activity: understand what happened

The **Activity Feed** is a project journal of supported record changes: notes, publications, tasks, status changes, object edits and work hours. Entries identify the actor and time, show readable change details and link back to the affected object or task. The object's Activity section provides the narrower history for one production record, including supported child and relation events.

![Activity Feed — server-backed project events and their actors](../assets/product-tour/activity-feed.png)

Filter by people and activity category, exclude your own actions, search loaded events or choose a day from the calendar. Older events load while scrolling; calendar counts cover accessible history beyond the currently loaded list. Dates follow the user's local timezone, while relative ages use synchronized server time.

Three histories serve different purposes. **Activity Feed** explains project changes. **Notifications** records notices from the current client session and links to their sources. **System Activity / Debug Log** exposes runtime work and diagnostics. Clearing a notification list does not erase the server journal, messages or file versions. The journal is not a promise of unrestricted, immutable audit coverage for every legacy extension.


## From working file to traceable publication

1. Select the record and publication context; add files in the browser's supported upload/check-in flow.
2. Review the target, description and naming settings before submitting.
3. The server validates permissions and naming, stores the files and records a snapshot.
4. Use Snapshot Browser to inspect versions, previews and file lists, or download the required publication.

![Snapshot Browser — actual Survey Drone publication history](../assets/product-tour/snapshot-browser.png)

The browser handles uploads and downloads. Handler adds workstation paths, local repository mappings and DCC scene operations when the workflow requires desktop access. The shared server remains the owner of publication metadata, naming and permissions.

A snapshot ties a version to its object, process/context, author, description and files. New versions and revisions are different operations. `latest` and `current` naming rules are separate from versioned storage. File sequences retain their range information so checkout can resolve the published frames.

### Naming is a configurable production rule

The naming editor brings matching rules, paths and examples into one place. Choose context patterns, directory and filename expressions, sandbox locations and repository aliases. Combine object/snapshot/file tokens with TSQL conditions or a trusted saved script when a project needs more than a template. Preview a rule against sample data before saving it.

![Naming editor — context matching, path patterns and native preview](../assets/product-tour/naming.png)

For example, a rule can derive a filename from the object's name, version and extension: `{sobject.name}_v{version}.{ext}`. The native naming engine resolves the actual paths at publication time. A preview is not a reservation: the final check-in still validates the version and collisions. Script-based naming executes trusted project code.

### Deliver to desktop workflows

Handler's **Repository Sync** can discover and download the selected objects, processes and versions into a mapped local repository. Its queue and presets belong to the desktop client. Stream supplies the records and files; Repository Sync is not a browser feature. The same boundary applies to desktop Watch Folders and native Maya operations.

## Tactic Frame: one UI description, two native renderers

**Tactic Frame is the shared language for describing interfaces in Handler and Stream.** A Frame module describes nodes, geometry, state and actions; Qt Quick and Vue render that description with their respective house controls. Handler's interface remains native Qt rather than an embedded web page.

Frame uses standard JavaScript modules (`.mjs`) and ordinary data structures. A feature's `describe(model, width, height, language)` builds its visible structure from state. Controllers handle actions and domain operations; the description does not become a second server API.

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

Project XML views and visual layout documents configure content above this layer. They are not a replacement file syntax for Frame modules. Both products ship independently and carry their own shared-description copy; supported behavior must be checked in both renderers. [Frame contracts](../frame/index.md)

## Script Editor, shelves and production automation

The Script Editor combines a project script library with tabs, drafts, undo, syntax highlighting, completion, search/replace and outline navigation. Run the current script or selected text, then inspect its result and errors in the output area. Named folders turn one-off tools into a discoverable studio library.

![Script Editor — saved project script and production record query](../assets/product-tour/script-editor.png)

| Runtime | Where it runs and what it can use |
| --- | --- |
| **Server Python** | The TACTIC server, its project context, native objects and commands. |
| **Browser JavaScript** | The browser with its supported context, project/selection values, `rpc` and refresh helpers. |
| **Server JavaScript** | QuickJS-NG on the server with the synchronous `server` API; no browser DOM or desktop DCC context. |

Execution location matters. A returned server result appears in the editor; server Python process stdout remains in the server log. Administrator/supervisor capabilities govern editing and running scripts.

**Script shelves** put saved actions beside the work: shared studio tools, personal tools and tools attached to a search tab. Server workflow events and saved scripts provide project automation. Handler additionally owns its Before/After hooks around desktop and DCC actions. Code execution is a trusted capability, separate from merely viewing a script.

[Script Editor Help](../../frontend/public/help/script_editor.en.md) · [Script Shelf Help](../../frontend/public/help/script_shelf.en.md)

## Administration: shape the project itself

Create the entities and relationships the studio actually uses, then define how people see and act on them. Search Types are configurable data types, not a fixed Asset/Shot-only product model. Schema diagrams make their relationships visible.

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

Authoring sections keep their own drafts. Save/discard controls and revision checks make changes explicit; permissions remain enforced by server operations. A visual editor does not grant its user unrestricted database access. [Administration Help](../../frontend/public/help/administration.en.md)


## Users, groups and effective access

User management is a server-wide directory, not a list of assignee names copied into a project. Accounts have identity, profile/contact fields, account settings and group memberships. The same identities appear in assignments, conversations, activity and participant lists.

![Users — directory, profile, account and group editing](../assets/product-tour/users.png)

### Account lifecycle

Create an account, set its initial password and profile, and assign the required groups. Edit existing profile/account fields without reading back a password. Retire an account when access should stop and reactivate it when appropriate; the existing production history retains its author identity. A retired account and a deleted project object are different operations.

### Group membership and permission policy

Groups manage membership and descriptions. Access rules manage the policy: access level, project scope, supported object/process/status/action rules, inheritance and explicit allow/deny. Sidebar visibility is a separate part of the interface policy; hiding a link is not the same as denying access to its records.

![Groups — membership and server group configuration](../assets/product-tour/groups.png)

Use effective-access checks for a particular user to inspect the outcome of membership and inheritance. A group matrix explains configured rules; it does not by itself prove what a user can read or edit after all rules are combined.

A practical onboarding sequence is **account → groups → project/data permissions → sidebar visibility → check the resulting user access**. Administration's selected project scopes project definitions; it does not turn server-wide users into project-local accounts. Drafts, confirmation and native server checks remain in force throughout.

## Configuration: connection, storage and daily behavior

Configuration separates deployment and personal preferences from project authoring. Each page owns its draft: Apply affects the current page, Save handles pending changes, and leaving dirty settings is guarded. Appearance can be previewed and reverted.

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

## A project assistant with actual context

Ask what is ready for review, which version is published or what is missing from a handoff. The built-in **External agent** window captures the project, page, Search Type and selected objects. Its executor reads or changes data through scoped native tools.

![Built-in assistant — a real handoff generated from Survey Drone tasks, notes and file versions](../assets/product-tour/assistant.png)

In this demonstration it found a useful discrepancy: modeling was marked Complete, but no model publication existed. It distinguished review comments from proof of approval. The full presentation covers conversations, attachments, provider choices, project configuration, task changes, script trials and the limits of undo.

**[Explore the built-in assistant →](assistant.en.md)**

## Custom dashboards that are working pages

Compose metrics, reports, charts, Item View, forms and native actions around a team's job. A production overview can lead directly into an asset; a review desk can keep selected-object details next to its tree. The page remains connected to project data and permissions.

![Production overview — live task metrics, status distribution, workload and Item View](../assets/product-tour/dashboard-overview.png)

**[Explore custom dashboards and their visual editor →](dashboards.en.md)**

## Run it and extend it

### Local source checkout

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

### Server APIs and extensions

On a running instance, `/api/documentation` exposes the method catalogue and `/api/compatibility` describes the original contract. XML-RPC remains an integration entrance for existing clients. The native core retains familiar `pyasm`/`tactic` modules and command semantics; integration code must use the appropriate server API rather than Handler's in-memory client objects.

[Server API source map](../admin_agent/SOURCES.md#ts-server-api) · [Core model](../../frontend/public/help/core_model.en.md) · [Architecture](../architecture.md) · [Workspace Pulse example](../../../examples/workspace_pulse/README.md) · [Studio Review example](../../../examples/studio_review/README.md)

## Scope and provenance

Stream and Handler are independent repositories and bundles. Stream does not import Handler or the legacy source tree at runtime. Original TACTIC compatibility is an explicit verification effort, not a blanket guarantee that every historical plugin or script works unchanged.

The old `pyasm.prod` production layer and Drupal are outside this port; MySQL support is deferred, and S3 is excluded. Check the [compatibility scope](../compatibility.md) before planning a migration. [Documentation index](../index.md)

The screenshots illustrate configured workflows on a small demo project. They are not a performance benchmark or a claim of release acceptance. Studio-specific scripts, schemas, integrations and permissions need validation against the deployed version.

[Original TACTIC license](../../LICENSE.TACTIC) · [QuickJS-NG](../../LICENSE.QUICKJS-NG) · [Vue](../../frontend/public/LICENSE.VUE.txt) · [Icon-font notices](../../frontend/public/licenses/icon-fonts/SOURCES.md)
