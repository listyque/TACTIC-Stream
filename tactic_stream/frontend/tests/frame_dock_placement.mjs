import assert from 'node:assert/strict';
import {
  finishDrop,
  rootZone,
  targetZone,
  preview
} from '../../src/tactic_stream/shared_ui/shell/dock.placement.mjs';
const rect = { x: 100, y: 70, width: 600, height: 400 };
assert.equal(rootZone(12, 12, 1200, 800), 'left');
assert.equal(rootZone(600, 12, 1200, 800), 'top');
assert.equal(rootZone(600, 790, 1200, 800), 'bottom');
assert.equal(rootZone(1190, 300, 1200, 800), 'right');
assert.equal(rootZone(600, 400, 1200, 800), '');
assert.equal(targetZone(400, 80, rect, 38, true), 'swap');
assert.equal(targetZone(400, 80, rect, 38, false), 'top');
assert.equal(targetZone(400, 270, rect, 38, true), 'center');
assert.equal(
  targetZone(108, 71, rect, 38, true),
  'top',
  'Corners choose the nearest normalized edge'
);
assert.equal(targetZone(101, 90, rect, 38, true), 'left');
assert.equal(targetZone(699, 200, rect, 38, true), 'right');
assert.equal(targetZone(400, 469, rect, 38, true), 'bottom');
assert.deepEqual(preview('right', rect, false), {
  x: 400,
  y: 70,
  width: 300,
  height: 400
});
assert.deepEqual(
  preview('right', { x: 0, y: 0, width: 1000, height: 700 }, true),
  { x: 660, y: 0, width: 340, height: 700 }
);
assert.deepEqual(preview('swap', rect, false), rect);
console.log(
  'Shared dock zones: root edges, nearest corner, header swap, center capability and previews passed.'
);

assert.deepEqual(finishDrop('center', 'tasks', false), {
  type: 'place',
  zone: 'center',
  target: 'tasks'
});
assert.deepEqual(finishDrop('left', '', false), {
  type: 'snap',
  zone: 'left',
  target: ''
});
assert.deepEqual(finishDrop('', '', false), { type: 'cancel' });
assert.deepEqual(finishDrop('', '', true), { type: 'move' });
