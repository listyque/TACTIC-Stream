import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/tasks/gantt.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/tasks/gantt.ui.mjs';
import * as Calendar from '../../src/tactic_stream/shared_ui/features/tasks/calendar.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/tasks/schedule.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const record = {
  taskCode: 'A',
  taskId: '1',
  ganttScheduled: true,
  ganttStartDay: 5,
  ganttDurationDays: 4,
  progress: 30,
  groupKey: 'g',
  groupFirst: true,
  ganttSection: 'scheduled',
  ganttSectionFirst: true
};
const geometry = State.layout(1200, 600, 60, 1, 12);
const quarter = State.zoomAt(
  geometry,
  150,
  State.scaleZoom('quarters', geometry.baseDay),
  300
);
assert.equal(
  quarter.day,
  2,
  'Named quarter scale must reach its actual two-pixel day width'
);
assert.equal(State.dateForDay('2024-02-28', 1), '2024-02-29');
assert.equal(State.dateForDay('2024-02-28', 2), '2024-03-01');
assert.equal(State.progressKey(99, 'ArrowRight'), 100);
assert.equal(State.progressKey(100, 'ArrowRight'), 100);
assert.equal(State.progressKey(30, 'Escape'), null);
for (const mode of [
  'move',
  'start',
  'end',
  'resize-start',
  'resize-end',
  'create',
  'progress'
]) {
  const origin = State.begin(record, mode, 60, 12),
    untouched = JSON.stringify(origin);
  const moved = State.pointer(origin, 84, 12);
  assert.equal(
    JSON.stringify(origin),
    untouched,
    'Pointer preview never mutates its captured origin'
  );
  assert(State.changed(moved), mode);
  assert(moved.duration >= 1 && moved.duration <= 3650, mode);
  assert(moved.progress >= 0 && moved.progress <= 100, mode);
}
const created = State.pointer(State.begin(record, 'create', 120, 12), 84, 12);
const issuePress = State.begin(record, 'create', 120, 12, true);
assert.equal(
  State.changed(issuePress),
  false,
  'Warning click opens the editor without a new draft'
);
assert.equal(
  State.changed(State.pointer(issuePress, 121, 12)),
  false,
  'Pointer jitter is not a drag'
);
assert.equal(
  State.changed(State.pointer(issuePress, 124, 12)),
  true,
  'Warning drag creates a schedule'
);
assert.deepEqual(
  [created.start, created.duration],
  [7, 4],
  'Unscheduled drag works in either direction'
);
const target = {
  ...record,
  taskCode: 'B',
  taskId: '2',
  dependencyId: '1',
  ganttStartDay: 12,
  groupFirst: false,
  ganttSectionFirst: false
};
assert.equal(UI.dependencies([record, target], [], 12).nodes.length, 4);
assert.equal(UI.dependencies([record, target], ['g'], 12).nodes.length, 0);
assert.equal(
  UI.dependencies([{ ...record, taskId: '' }, target], [], 12).nodes.length,
  0,
  'Never infer a missing predecessor'
);
for (const width of [320, 360, 520, 1200]) {
  const layout = Calendar.layout(width, 500);
  assert(layout.cellWidth * 7 + layout.cellGap * 6 <= layout.inner + 0.001);
  const footer = UI.footer(
    {
      zoom: 1,
      canUndo: true,
      canRedo: true,
      todayDay: 1,
      hostWidth: width >= 380 ? 112 : 0
    },
    width,
    'en'
  );
  assert(
    footer.nodes
      .filter((node) => node.kind === 'Button')
      .every((node) => node.x >= 0 && node.x + node.width <= width)
  );
  validateScene(footer, {}, {});
  const editor = Editor.describe(
    { start: '2030-01-01', duration: '0', dates: true },
    width,
    'en'
  );
  assert.equal(
    editor.nodes.find((node) => node.id === 'ganttEditorApply').enabled,
    false
  );
}
assert.notEqual(
  UI.heading({}, 300, 'en').nodes[1].text,
  UI.heading({}, 300, 'ru').nodes[1].text
);
assert.equal(
  Editor.describe(
    { start: '2030-02-31', duration: 1, dates: true },
    360,
    'en'
  ).nodes.find((node) => node.id === 'ganttEditorApply').enabled,
  false
);
assert.deepEqual(
  Editor.describe(
    { start: '2030-02-31', duration: 1, dates: true },
    360,
    'en'
  ).nodes.find((node) => node.id === 'ganttEditorDuration').keys,
  {}
);
assert.deepEqual(
  Editor.describe(
    { start: '2030-02-20', duration: 1, dates: true },
    360,
    'en'
  ).nodes.find((node) => node.id === 'ganttEditorDuration').keys.Enter,
  { type: 'apply' }
);
console.log(
  'PASS production schedule state: immutable previews, bidirectional create, exact quarter scale, leap days, real dependency identities, collapsed rows, bounded progress, phone geometry and form validation'
);
