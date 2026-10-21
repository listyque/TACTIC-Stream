import assert from 'node:assert/strict';
import {
  node,
  rect,
  listOffsets,
  listBounds,
  listRange,
  revealListOffset,
  validateScene
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const definition = node('List', 'rows', rect(0, 0, 300, 80), {
  source: 'rows',
  keyField: 'key',
  fields: ['key', 'extent'],
  rowHeight: 40,
  rowGap: 0,
  rowHeightField: 'extent'
});
const rows = [40, 260, 40, 40].map((extent, key) => ({
  key: String(key),
  extent
}));
validateScene({ nodes: [definition] }, { rows });
const offsets = listOffsets(definition, rows);
assert.deepEqual(offsets, [0, 40, 300, 340, 380]);
assert.deepEqual(listBounds(definition, offsets, 2), { y: 300, height: 40 });
assert.deepEqual(listRange(4, 40, 80, 0, 0, offsets), {
  first: 0,
  last: 2,
  height: 380
});
assert.deepEqual(listRange(4, 40, 80, 220, 0, offsets), {
  first: 1,
  last: 2,
  height: 380
});
assert.deepEqual(listRange(4, 40, 80, 300, 0, offsets), {
  first: 2,
  last: 4,
  height: 380
});
assert.deepEqual(listRange(0, 40, 80, 0, 3, [0]), {
  first: 0,
  last: 0,
  height: 0
});
assert.equal(revealListOffset(0, 2, 80, 4, 40, 0, offsets), 260);
assert.equal(
  listOffsets({ ...definition, rowHeightField: undefined }, rows),
  null
);
assert.throws(() => listOffsets(definition, [{ key: 'bad', extent: -1 }]));
assert.throws(() => listOffsets(definition, [{ key: 'bad', extent: NaN }]));
assert.throws(() => listOffsets(definition, [{ key: 'bad', extent: '40' }]));
assert.throws(() =>
  validateScene({ nodes: [{ ...definition, fields: ['key'] }] }, { rows })
);
assert.throws(() =>
  validateScene({ nodes: [definition] }, { rows: { count: 4 } })
);
const large = Array.from({ length: 100000 }, (_, key) => ({
  key,
  extent: key % 10 ? 40 : 260
}));
const largeOffsets = listOffsets(definition, large);
const range = listRange(
  large.length,
  40,
  400,
  largeOffsets[80000],
  3,
  largeOffsets
);
assert.equal(range.first, 79997);
assert.ok(range.last - range.first < 20);
console.log(
  'PASS: variable row geometry, boundaries, focused header visibility and bounded virtualization'
);
