---
reference: Handler
group: Docks
icon: tasks
order: 28
---
# Tasks dock

> Tasks follows the selected sObject and edits its workflow tasks. The same header switches between
> compact cards, list and the full Task Manager without moving the primary controls.

Sort and Group show the Handler icons beside each choice and beside the selected value. The compact toolbar keeps the same choices in Task view options.

Choose task scope opens direct checked choices with icons. The toolbar button shows a short scope label and its icon; user and team scopes retain their identity selector. Choosing project, selected objects or search-type tasks closes the scope popup.

## Scope and views

For a selected sObject, the dock loads configured workflow processes and their tasks. The three fixed
view segments are:

| View | Best for |
| --- | --- |
| Cards | Quick status, assignee, dates and progress changes per process. |
| List | A denser overview of many processes. |
| Full Task Manager | Server filtering, table, Gantt, Calendar, bulk editing and wider task details. |

Switching views keeps the same target and unsaved edits. Table, Gantt and Calendar controls belong to
the full workspace footer.

## Process rows

Each process row can reset or save edits, create a missing task, open related notes and expose edit or
delete actions. When a process has several tasks, select the intended task before editing.

Common editable fields include status, assignee, start and end dates, progress, priority and bid. The
available fields and values come from the project workflow. Status and assignee catalogs load on demand.

## Saving

- **Save** on a row commits that task.
- **Save all** commits every changed row owned by the current target.
- **Discard** restores server values for the chosen row.
- **Discard all** removes every unsaved task edit in the dock.
- Creating a task uses the process defaults; the full Task Editor exposes additional fields before creation.

Unsaved rows stay visibly marked. Selection changes do not silently commit them.

## Notes and work hours

Open Notes to make Task Inspector follow the exact parent, process and selected task. Work-hour actions
use that task identity; a process with no task must be created before time can be logged.

## Dates and loading

Date fields show the stored date/time in a compact ISO representation. Focus opens the browser's
date/time editor; picker appearance depends on the platform. In long lists, scroll first and let
the view settle before relying on hover actions.

## Errors and permissions

- Missing processes indicate that the selected object has no configured workflow or no accessible process.
- A save conflict leaves the local edit visible so it can be reviewed or discarded.
- Delete is shown only when the current account and task state permit it.
- An unavailable user, status or field is server configuration data and is never invented by the UI.

## Native catalog and exact task branches (0.112.34)

Cards, compact rows and the full workspace share the native process catalog, user identities and
configured fields. Additional tasks in one process keep distinct context, assignee and draft values.
Switching branches or surfaces preserves unsaved changes; opening notes carries the exact task key.
Full create/edit forms remain available alongside quick fields. Quiet refresh preserves original
revisions, and conflicts or uncertain save results require review/reload before another save.

The full workspace provides Table, Gantt and Calendar. Schedule moves, duration edits, progress,
assignee workload and milestone planning use native TaskScheduleCmd; undo/redo operates on the
local schedule draft until Save. API filters and limits remain separate from the rendered view.
Configured editor commands currently require an administrator; ordinary SDK task permissions
are verified separately. Browser date picking, moving/resizing windows and touch layout are
platform adaptations. The phone composition and workspace restoration are described in Mobile application and Windows help.


## Phone presentation

The project task table becomes cards showing object, process/context, status, assignee,
deadline and progress. Tap or swipe left to open a separate task fields page. Back, a right swipe
and browser Back/Forward return to the list with its previous scroll position; unsaved edits stay
in the shared draft. Save applies the prepared native plan; Discard removes pending edits.
Open notes from the card or Task actions after saving or discarding changes to that task. Checkboxes
select tasks for bulk actions; Select all tasks is in Task view options. Search opens with its button
and keeps the query when hidden. Group headings collapse by tap. Background refresh keeps the
loaded cards, selection and prepared fields stable and applies actual changes without a loading flash.
Scrolling down hides the toolbar; scrolling up restores it. Gantt remains a desktop view; Task Calendar is a separate mobile
panel. Desktop view preferences and drafts survive resizing. Quick process cards/list remain
available from Task view options and adapt to one column.

## Project tasks without object selection

In full Task Manager, + also works when no object is selected. It creates a task owned only by the current project; no asset, shot or other work object is needed. The task uses the standard task status workflow and initially assigns the current user, so it appears in My tasks. Edit and save it using the existing task controls, then open Task Inspector as usual. In a Perforce-like file project, select it under Link tasks to changelist in the submit dialog. With an object selected, + keeps creating a task for that object.

Task Manager's shared table/field editors, virtual creation and opt-in bulk workflow are described in [Tasks and planning](tasks.en.md). Existing configuration and permission owners remain unchanged.

The calendar month fills its dock as seven columns and six week rows. Resizing or maximizing the dock keeps every day inside the panel; the agenda remains a separate scrolling view.

Status cell editing keeps the same caption, color marker and size as its idle value. Status menus show the pipeline colors for every option and keep disabled or removed choices unavailable. Choose with the mouse, touch or keyboard; Escape dismisses the menu without staging a value.

Opening a user picker keeps the task cell corners and text size. Its original button contributes no extra filled background; keyboard focus is drawn inside the existing cell surface.
