---
reference: Handler
group: Docks
icon: calendar-month
order: 32
---
# Task Calendar dock

> Task Calendar summarizes scheduled tasks by day and turns a selected date into a server-side task
> filter for the active task scope.

## Calendar navigation

Use previous and next month to move through time, **Today** to return to the current month, and the
clear action to remove the selected day. A day cell shows matching loaded tasks and a compact
`+ more` indicator when they exceed the visible limit.

Selecting a day applies its date boundary to Task Manager on the server. It is not merely a visual
highlight. Clearing the date restores the previous non-date task scope.

## What is counted

Calendar and Gantt operate on matching task data available to the current workspace. If the task
browser has more server pages, load them when the view needs the complete matching set. The selected
day message states which date is currently filtering tasks.

## Typical workflow

1. Open the required task scope or Search selection.
2. Navigate to the required month.
3. Select a day to filter matching deadlines or scheduled work.
4. Open a task in Tasks or Task Inspector for editing.
5. Clear the date to return to the wider task result.

## States and errors

- An empty day means no accessible task matches the active scope and date.
- Tasks without usable start or end dates cannot be positioned reliably in the calendar.
- Server filtering keeps the selected day while loading; an error does not silently switch dates.
- Date labels follow the interface locale, while stored task dates remain project data.

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

## Shared scheduling

Gantt and the separate Task Calendar dock use the same Frame layout in Handler
and Stream. Use the pencil on a task to edit its schedule without dragging.
Apply to draft stages dates and progress together; Save task changes performs
the existing server write. Undo/Redo affect pending schedule edits and preserve
other task drafts. Escape cancels an unfinished pointer gesture.

Calendar month navigation and Agenda keep the current task owner. Select a day
to filter Task Browser; clear it to return. Calendar does not replace Gantt.
Dependency connectors show actual links between loaded, visible scheduled tasks;
they do not infer missing tasks or cascade schedule changes automatically.
Project milestones retain their linked-task plan and existing save/conflict
controls. Native milestone SObject storage and browser revision review remain
separate client capabilities.
