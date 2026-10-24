# Tactic Frame: Production scheduling

This contract describes source ownership, behavior and verification scope.
TH and TS ship independently; native-only actions remain native capabilities.
Use [the shared contract](contract.md) and [the feature index](index.md).

## Source and owners

| Shared module under `shared_ui/features/tasks` | Production consumers | Responsibility |
| --- | --- | --- |
| `gantt.state.mjs` | TaskGanttView / TaskGanttRow in Qt; TaskGanttView in Vue | Layout, row projection, bar geometry, tick density, pointer preview, zoom anchoring, progress keys, overview and edge scrolling |
| `gantt.ui.mjs` | Both Gantt presenters | Heading/ticks/markers, section/group bands, task labels, bars/grips, warnings, overview, footer and operation menus |
| `calendar.ui.mjs` | Both TaskCalendarView presenters | Month navigation, weekday/grid geometry, day contents, milestone/task actions, Agenda rows and footer |
| `schedule.ui.mjs` | Native TaskScheduleDialog; Vue TaskScheduleEditor | Form, validation, working days, duration/progress, multi-selection and apply/cancel |
| `milestones.ui.mjs` | Native MilestoneManagerView; Vue MilestoneContent/MilestoneRow inside MilestonePanel | Header, search, responsive editable rows, linked-task statistics, actions and empty state |

Each product ships its own independent copy. Native house controls render Qt;
App controls render Vue. There is no WebEngine, second request store, parallel
undo stack or replacement mutation pipeline in Frame.

Handler keeps TasksController, TaskWorkspaceStore, native scheduling calculations,
task revisions and the existing SObject mutation paths. Stream keeps TaskManager,
TaskScheduleCmd, TaskWorkspaceEditCmd and MilestoneCmd. The schedule projection
accepts bounded display data; task IDs and dependency IDs grant no read/write
access. Existing server authorization, revision checks and unknown-write guards
remain in their original owners.

## Behavior and intentional capabilities

- Gantt retains grouping/collapse, loaded-row selection, preview/object navigation,
  dates/progress, resize/move/create, edge scrolling, zoom/pan, named scales,
  overview, warnings, batch operations and pending changes. Calendar stays its
  own dock; selecting a day filters the task owner and does not replace Gantt.
- The new explicit native schedule form uses the same scene as Vue. Applying
  dates and progress is one undo entry and preserves other drafts and original
  times. Escape cancels a pointer preview before release. A changed task/context
  blocks the native form until it is reopened. Invalid calendar dates cannot be
  normalized silently into a different day. Enter in duration/progress applies
  the valid form through the same action as its button in both engines.
- Group headers toggle across their entire timeline band. The warning chip
  opens the form on click and creates a schedule when dragged; free timeline
  space pans. Wheel over the timeline zooms at the pointer, Shift-wheel pans,
  and wheel over the labels scrolls the list. Switching modes retains the actual
  Gantt presenter, zoom and scroll. No-op schedule operations retain redo history.
- Named Quarters reaches the actual two-pixel day scale even for a short range.
  Month-only DateField presentation uses the same month text in Qt and Vue.
- Connectors show actual `sthpw/task.depend_id` links between loaded, visible,
  scheduled tasks. Missing/hidden predecessors and self-links are not inferred
  from process order. Dependency editing and automatic cascade rescheduling are
  not features of the original Gantt and are not introduced by this migration.
- Frame shares milestone presentation, not a new storage API. Handler retains
  its native SObject commit/delete path; Stream retains revision review and
  unknown-write inspection through MilestoneCmd. Browser-only revision/unknown
  write controls remain explicit capabilities. No equivalent native optimistic
  milestone rebase is claimed.
- The Stream Task Workspace API remains administrator-only. The native task
  permissions are unchanged. Phone uses the existing task-list composition;
  scheduling is available through explicit controls, without requiring drag.

## Verification

Run the focused drivers under `tools/frame_schedule/` from the Stream development
checkout, with the actual Handler checkout supplied using `--handler-root`
where supported. The complete shared gate is:

```powershell
python tools/frame_foundation/check_platform.py --handler-root "../../TH"
```

Adjust that path relative to the working directory; in the two-repository
workspace, Stream commands run from `TS/tactic_stream` and Handler is `../../TH`.
Use isolated data, actual input, fresh source fingerprints and independent-package
checks. Generated reports belong in the ignored tool `output/` directories.
Historical release counts and captures are local archive material, not current
acceptance. Offscreen checks do not establish physical touch/IME, compositor,
DCC or deployment readiness; exercise those when the feature requires them.
