---
reference: Handler
group: Workflows
icon: tasks
order: 16
---
# Tasks and planning

> Task tools provide object-level task editing and project-wide table, Gantt, calendar, timesheet, and
> reporting views.

## Main controls

Switching between the table and Gantt keeps the loaded task page and unsaved
changes. Returning to the table recalculates its layout for the current width.

Click an editable task cell once to open its user/status picker directly. Progress uses a slider with a percentage readout. Planned hours use increase/decrease buttons in 15-minute steps, with a visible hour unit; project values stored in minutes are converted automatically. Start and deadline retain a combined two-field editor. Cell changes remain staged until Save task changes.

Use scope, team filters, quick filters, columns, sorting, grouping, bulk selection, status and
assignee editors, dates, progress, notes, and delete actions. A Tasks badge on an sObject or process
opens Task Manager in Selected scope.
Opening an object or process through its Tasks badge clears filters from the previous scope;
a process badge then applies only that process filter. An active filter colors the filter button
green (or the overflow button at narrow widths). If filters hide every task, the empty state
offers to clear them instead of suggesting task creation.

Selecting a task row updates Task Inspector for that exact task without changing the Inspector's
saved expanded or collapsed state. When one process has multiple tasks, its badge menu shows each
task's context, assignee, and status; the process row opens the task list from already loaded data.
Switching Search tabs that show the same object and process keeps the Inspector's loaded task and
notes; selecting a different context refreshes them.

A workflow **progress** process remains in the Task Inspector process menu, marked with the same
completion icon and approved/total count as the object's completion badge. Selecting it shows the
tasks of objects linked through the project schema and switches Task Manager's selected-object scope
to those objects; it does not create or edit a task on the parent.
Progress processes are not snapshot check-in destinations. If the workflow names a Search Type that
has no schema relationship to the selected object, the Inspector reports the missing relationship
instead of guessing which objects belong to it.

## Usage notes

- Only Selected scope follows sObject selection; project, Search Type, user, and team scopes stay
  unchanged while compact task editors continue to follow the selected result.
- Task note badges use the native per-process TACTIC counts.
- Edit sObject opens the schema-driven editor and always reloads the explicitly requested object,
  including when its window is already open.
- Delete opens the shared dependency editor, where TACTIC dependency defaults can be reviewed before
  removal.
- When deleting a Task, Notes from the same parent sObject and process appear as a checked
  dependency group; clear that group to keep them.
- Task links from Activity Feed, Object Info, and user profiles accept both native TACTIC search-key
  formats.
- Refreshing Selected scope without an sObject keeps the normal empty state and sends no server
  request.
- Selected scope follows the active Search tab and its selected objects, including multiple
  selection.
- The All Search Type action uses that tab's type even when its result list is empty.
- Hidden task views catch up when shown again; unsaved task edits are kept.
- Search Type task groups show the configured title while retaining the server code as their stable
  identity.
- Task filters and sorting run on the server before pagination. Loaded pages are merged into one
  group per stable key, so Load More does not repeat a group header.
- Quick-filter choices show each process, status, or other value once, with the task count for the
  current scope.
- Load More fetches the next matching page; unsaved task edits remain available when a filter
  changes.
- Hover editors are created only when needed. Task-row highlighting appears immediately, and status and assignee content stays in place when its editor appears.
- An empty status uses the same localized “No status” label in the table and hover editor; configured status names remain unchanged.
- Pressing a status or user editor keeps it active while its menu opens, so the pointer can move
  directly into the menu.
- Right-click a table column header to sort, group, or hide it. Any user can use
  **Configure columns** to open personal task-column settings in Configuration → Tasks.
- The table header's right-hand column button chooses visible task columns; the same action remains
  in the overflow menu when the table header is unavailable, such as in Gantt view.
- A draft Gantt schedule remains under Unscheduled Tasks until it is saved successfully.
- In Gantt, drag the protruding left or right grip to change a task's dates; drag the striped grip inside the bar to change completion.
- An empty Task Manager keeps its footer and shows a centered creation cue pointing toward +.
- The arrow remains anchored to the Create button while the dock is resized.
- The table is created asynchronously only when the active scope contains tasks; Gantt is created on
  first request and retained for smooth switching.
- The loading indicator remains until the first Task Manager table and its visible rows are ready;
  quick task rows are also laid out before presentation, so neither view cascades into place.
- User selectors combine task-specific choices with shared profile details, keep group sections and
  search aligned, and preserve the original choice when filtering.
- User choices are prepared when the selector is pressed, so its separate popup window never opens
  with an empty first frame.
- The Task Manager header keeps view switching, overflow, and refresh actions pinned to the right
  edge while secondary actions move into overflow at narrow widths.
- After restart, Task Manager resumes the last scope, filters, collapsed groups, calendar position
  and selected task separately for each project.
- Clearing task filters also leaves a specific user's scope opened from a profile badge and returns
  to Selected. Manually selectable scopes, including My Tasks, stay selected.
- Checked rows and unsaved edits are intentionally cleared.
- Task search remains visible in narrow layouts.
- The compact scope button stays beside Create instead of occupying the search field's flexible
  space; at the minimum width, scope selection remains available from overflow.

## Own journals (0.112.21)

Task detail edits and own note changes can be undone/redone from the user's saved
transaction journals. Notes preserve their IDs and reply links; delete replies before
their parent. Current parent/type/record/column rights are checked again. Status changes
with Workflow/history effects are not yet replayable. See Help: Internal structure,
“Task/note writes and undo/redo” for the tested scope and remaining limits.

## Status/Workflow replay (0.112.22)

Own task status and single-project Workflow journals now support undo/redo with their
status history, process states, messages/packages and own notes. Current rights are rechecked
and failures roll back. Historical Workflow journals lacking message backups are refused.
See Help: Internal structure, “Task status and complete Workflow replay” for boundaries.

## Workflow across projects (0.112.23)

Own complete dependency journals now replay across project databases with task status,
own notes, process states, history and messages. Each original parent's actual project
requires current rights; IDs and callback results survive replay without rerunning callbacks.
See Help: Internal structure, “Workflow replay across projects” for checks and boundaries.

## Legacy state ownership replay (0.112.24)

Own complete Workflow journals can now undo/redo the normal adoption of a legacy state
with an empty pipeline_code, retaining its original ID and data. The recorded owner must be
the parent's visible primary pipeline with its visible process. Arbitrary owner switching
remains denied. See Help: Internal structure, “Replay of legacy pipeline adoption”.

## Gantt and the calendar dock

Table and Gantt are presentations of Task Manager. Calendar opens a separate Task Calendar dock
from the Calendar button or Workspace panels → Tasks and reports. Position, stack, float or close
it using the shared dock controls; its visibility and geometry are part of saved layouts. Calendar
and Task Manager share the same scope, loaded tasks, selected day and drafts. Selecting a date
applies the server task filter; clearing it restores the wider result. On phones, choose Task
Calendar or Task Manager from the active panel selector. Agenda keeps Stream's task list available.

Gantt keeps task labels fixed while its timeline scrolls. Wheel over the time header zooms around
the pointer; Shift+wheel pans. Drag empty timeline space or use the overview to navigate. Days,
Weeks, Months, Quarters and Fit range are in Schedule options. Center today returns to the current
date. Group summaries, weekends, milestones and warning messages use the same task projection.

Drag a task bar to move it, its two grips to change start/deadline, or its progress handle to change
completion. Empty space on an unscheduled task row creates a schedule. Escape cancels a gesture;
Undo/Redo and Ctrl+Z/Ctrl+Shift+Z operate on the shared draft. Checked tasks can move together and
use batch scheduling. Date changes retain the original time. A draft stays in its original schedule
section until saved. The visible Edit schedule button provides the same changes without dragging,
including on touch screens. Save and Discard remain in Task Manager's pending strip. Row selection
and double-click opening do not save edits. Backend permissions and original revisions are checked
before staging and saving; the calendar is not a second task editor or an independent data copy.


## Mobile Task Manager

The project task table becomes cards showing object, process/context, status, assignee,
deadline and progress. Tap or swipe left to open a separate task fields page. Back, a right swipe
and browser Back/Forward return to the list with its previous scroll position; unsaved edits stay
in the shared draft. Save applies the prepared native plan; Discard removes pending edits.
Open notes with their own button after saving or discarding changes to that task. Checkboxes
select tasks for bulk actions and group headings collapse by tap. Scrolling down hides the search
bar; scrolling up restores it. Gantt remains a desktop view; Task Calendar is a separate mobile
panel. Desktop view preferences and drafts survive resizing. Quick process cards/list remain
available from Task view options and adapt to one column.


Gantt keeps its scroll viewport stable when a dock has fractional dimensions or the display uses 125% or 150% scale. An empty list with a fitting time range needs no canvas scrollbars; an overflowing list or range still scrolls normally. Resizing must not make the bars appear and disappear repeatedly.

## Project tasks without object selection

In full Task Manager, + also works when no object is selected. It creates a task owned only by the current project; no asset, shot or other work object is needed. The task uses the standard task status workflow and initially assigns the current user, so it appears in My tasks. Edit and save it using the existing task controls, then open Task Inspector as usual. In a Perforce-like file project, select it under Link tasks to changelist in the submit dialog. With an object selected, + keeps creating a task for that object.

## Shared Task Manager controls

The table, Quick Tasks cards/compact rows, scope and filter popovers, column
chooser, task fields and selection bar use the same Tactic Frame descriptions
in Handler and Stream. Each product ships its own copy and its own native controls.
The separate Handler management window also retains its scope summary, workload,
status distribution and preset chips. Stream keeps its phone list/detail/back
navigation and its additional Inspector/timesheet commands.

**Create task** adds an expanded virtual row. Choose its process/context and edit
its fields; the task reaches TACTIC only after **Save**. **Discard** removes an
unsaved row. Status, assignee, supervisor and date fields use the existing pickers.
Click a date, progress or hours cell to open its anchored editor. Commit a numeric
hours entry with Enter or by leaving the field; it becomes a pending row change.
Hours retain the configured native hour/minute conversion.

Select tasks with their checkboxes. The selection bar offers status and assignee;
**More fields** opens the remaining fields. Check only the fields to replace.
**Apply** on the selection bar saves the validated bulk operation. **Apply to draft**
in More fields stages row changes for review with the regular Save/Discard bar;
**Done** closes the field panel. Mixed values need an explicit replacement.
The original task revisions stay attached to changes. Conflicts and uncertain
write results require the existing reload/reconciliation path before another save.

Save or discard pending changes before changing scope, team, user or page size.
The Teams chooser does not change scope until a team is selected; an empty list
explains that no team scopes are available. Quiet refresh never replaces an
active field editor or an armed bulk edit. Column visibility, width/order, sort,
group and page size use the existing workspace preferences. Object is required.
Gantt and the separate Calendar remain available; their scheduling UI is a
separate migration block.

Permissions remain those of the existing executors. Stream's current task
workspace API requires an administrator; this UI migration does not grant native
Handler users additional server permissions or change its existing task ACL path.
