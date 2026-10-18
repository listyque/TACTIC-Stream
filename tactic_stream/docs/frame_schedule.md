# Tactic Frame B10: production scheduling

B10 migrates production Gantt, the independent Task Calendar dock, milestone
presentation and the explicit schedule editor to the same Frame descriptions.
The pinned pre-migration Handler is `8d18661f1a070b68930eb56afa997c142708b622`.
Acceptance evidence is generated from that Git archive and both production
renderers; the old `tools/shared_ui_demo` remains a historical proof only.

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

## Reproduce evidence

Run from the Stream checkout with the existing sibling Handler checkout:

```powershell
git -C D:/code/th_codex archive 8d18661f1a070b68930eb56afa997c142708b622 -o D:/code/TACTIC_VUE/tactic_stream/.tmp/b10/original-handler.zip
# Extract that archive into .tmp/b10/original (the capture validates its commit
# comment and every extracted QML resource against the archive).
.venv/Scripts/python.exe tools/sync_tactic_frame.py --handler-root D:/code/th_codex --copy-from stream
.venv/Scripts/python.exe tools/format_tactic_frame.py --handler-root D:/code/th_codex --check
.venv/Scripts/python.exe tools/frame_schedule/capture.py
node frontend/tests/frame_schedule.mjs
.venv/Scripts/python.exe tools/frame_schedule/report.py
.venv/Scripts/python.exe tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
```

The gallery is `tools/frame_schedule/output/index.html`. Use
`SCHEDULE_FRAME_OUTPUT` and `QT_SCALE_FACTOR` for separate DPI runs. Native and
browser source fingerprints are checked before and after capture and again by
the report. The source archive is immutable evidence, not a checkout to patch.
Two existing missing `Theme.controlRadius` warnings in the original milestone
manager are recorded explicitly; current native captures reject all warnings.

Real input checks are `tests.test_frame_schedule.FrameScheduleTests` in Handler,
the original native edge/progress tests, `gantt_calendar.mjs`, and the complete
`test_transport.Transport.test_task_manager_in_chromium` server journey. They
cover saved dates/times, pending work, undo, native cancellation, real dependency
identities, independent calendar ownership, milestone conflicts and drafts,
500-row virtualization, desktop restoration and browser touch input. The gate
also retains all earlier platform and task-owner checks.

Pixel geometry, font/color properties and controlled screenshots do not establish
identical font rasterization on every OS. Physical touch hardware, OS IME and
other compositors remain separate acceptance. B07's legacy-widget gaps and B11
messaging are separate batches.

## Accepted checkpoint: 2026-10-18

Stream **0.112.163** / Handler **0.6.0.114**: all **107 mandatory platform
stages** passed with unchanged source fingerprints. The scheduling stage passed
**25 native cases**, including eight production Frame input/owner cases and the
existing edge/progress, scheduling, scrolling and milestone suites. The full
Task Manager server journey passed, including Enter-to-apply, saved dates/times,
undo/redo, milestone revision conflicts and dependency-safe deletion. The three
connected task-context/process/phone journeys also passed.

The fresh gallery contains **156 full-matrix pairs plus 26 pairs at each of 125%
and 150% DPI: 208 paired states, 624 images**. Thirteen states/widths cover Gantt,
hover, empty schedule, Calendar, Agenda, wide/narrow milestones, milestone draft,
error/empty states and the real schedule form. Current geometry is checked to
0.1 px; font sizes/weights/colors and painted surfaces are compared separately.
Original gaps, including the absent explicit form/Agenda and two existing
milestone warnings, stay visible and documented in the report.

Native and browser tests retain 500-row virtualization. Fractional-size
empty/populated scrolling passed at 100/125/150%; the platform gate also passed
native controls at 100/150/200%, the interactive control atlas, complete
desktop/mobile Workbench, window/dock lifecycle and independent packaging.

Migration diagnostics remain in local `.tmp/b10` logs. A missing fixture response
revealed an unguarded loading state, and a retained pan hid a milestone outside
the narrow viewport. The final checks use guarded content, actual overview
navigation, stable pointer capture and the shared keyboard action; they do not
force-click hidden controls or relax comparison thresholds.
