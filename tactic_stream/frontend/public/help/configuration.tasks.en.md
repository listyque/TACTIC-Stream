---
group: Configuration
icon: settings
order: 37
---
# Tasks configuration

> Defaults initialize a task workspace only where that account/project has no saved task state.

Initial task surface selects Quick Tasks or Task Browser. Browser default remains Task Browser; Quick Tasks is a visible optional surface. Quick Tasks presentation selects cards/compact list. Initial view selects Table/Gantt; sorting selects deadline/recent/process/user/status/object/type/project/priority/milestone/supervisor; grouping selects none/process/user/status/object. Fresh defaults are table, deadline and process grouping.

Expand task details initializes Task Inspector expansion only without a saved account choice. Task Browser columns define order, visibility and width 40–480 pixels. Object remains required; duplicate/unknown keys are removed and newly introduced native columns are appended. Up/down controls change the same column definitions used by the table and its context menu.

Saved per-account/project scope, filters, columns, group expansion, calendar and selection take priority over defaults. Checked tasks and unsaved edits are not restored. Apply updates future initialization; it does not replace an already edited task workspace or its pending edits.

Administrators also see Task scheduling from native server XML. Project schedule/mode overrides the server mode; empty retains pipeline dates. Modes even/even_day/from_end_date use native scheduling commands. These defaults do not turn calendar UI settings into a scheduling algorithm.

Owners: preferences.tasks, taskColumns.js, TaskManager/NotesPanel, native task_workspace/task_schedule and ServerConfiguration. Reset/Apply for Tasks preserves unrelated repository/server XML drafts.
