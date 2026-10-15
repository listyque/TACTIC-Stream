import assert from 'node:assert/strict';
import * as Dock from '../../src/tactic_stream/shared_ui/shell/dock.layout.mjs';
import {
  stack,
  place,
  projectTree,
  resizeTree
} from '../src/features/workspace/docks.js';

let tree = place(place(stack('results'), 'tasks', 'right'), 'notes', 'right');
tree = place(tree, 'snapshot', 'center', 'notes');
const available = Dock.panelIds(tree),
  original = structuredClone(tree);
const sizes = Dock.normalizedSizes(
  Object.fromEntries(available.map((id) => [id, id])),
  1600,
  900
);
assert.deepEqual(
  Dock.minimumSize(
    tree,
    available,
    Object.fromEntries(available.map((id) => [id, Dock.minimum(id)]))
  ),
  [1080, 300]
);
const small = projectTree(tree, available, 760, 640);
assert.deepEqual(
  tree,
  original,
  'Resize projection must preserve preferred ratios'
);
assert.ok(Math.abs(small.rectangles.results[2] - 360 / 1080) < 1e-9);
assert.ok(Math.abs(small.rectangles.tasks[2] - 320 / 1080) < 1e-9);
assert.ok(Math.abs(small.rectangles.notes[2] - 400 / 1080) < 1e-9);
const resized = resizeTree(tree, available, 1600, 900, '', 0.1);
const actual = Dock.project(resized, available, sizes);
assert.ok(actual.rectangles.results[2] >= 360 / 1600 - 1e-9);
assert.ok(actual.rectangles.tasks[2] >= 320 / 1600 - 1e-9);
assert.deepEqual(
  projectTree(tree, ['results'], 760, 640).rectangles.results,
  [0, 0, 1, 1]
);
assert.deepEqual(projectTree(tree, available, 1800, 1000).tree, original);
const tabs = {
  type: 'stack',
  panels: ['notes', 'description', 'snapshot'],
  active: 'notes'
};
assert.deepEqual(Dock.reorder(tabs, 'notes', ['snapshot', 'notes']).panels, [
  'snapshot',
  'description',
  'notes'
]);
assert.deepEqual(Dock.reorder(tabs, 'notes', ['notes', 'notes']), tabs);
assert.equal(Dock.normalizeActive(tabs, ['snapshot']).active, 'snapshot');
assert.equal(Dock.tabTarget([50, 150, 250], 1, -1), 1);
assert.equal(Dock.tabTarget([50, 150, 250], 1, -101), 0);
assert.equal(Dock.tabTarget([50, 150, 250], 0, 201), 2);
for (const edge of [
  'left',
  'right',
  'top',
  'bottom',
  'top-left',
  'top-right',
  'bottom-left',
  'bottom-right'
]) {
  const rect = Dock.floatingResize(
    [100, 100, 600, 400],
    edge,
    edge.includes('left') ? 550 : -550,
    edge.includes('top') ? 350 : -350,
    'notes',
    1200,
    900
  );
  assert.ok(rect[2] >= 400 && rect[3] >= 300, edge);
  if (edge.includes('left')) assert.equal(rect[0] + rect[2], 700);
  if (edge.includes('top')) assert.equal(rect[1] + rect[3], 500);
}
console.log(
  'Dock layout: recursive minimums, proportional undersize, resize/restore, hidden tabs and eight floating edges passed.'
);
