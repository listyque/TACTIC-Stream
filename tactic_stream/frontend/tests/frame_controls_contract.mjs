import { cssRoles } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import assert from 'node:assert/strict';
import {
  parse,
  monthDays,
  localDate
} from '../../src/tactic_stream/shared_ui/controls/forms/calendar.mjs';
import {
  buttonVisual,
  fieldVisual,
  checkVisual,
  switchVisual
} from '../../src/tactic_stream/shared_ui/core/interaction.mjs';
import {
  visibleRows,
  navigate
} from '../../src/tactic_stream/shared_ui/controls/lists/tree.ui.mjs';

for (const value of [
  '2024-02-29',
  '2024-02-29 13:14:59',
  '2024-02-29T13:14',
  '0099-02-28',
  '2024-02-29T13:14:15.123456+03:00',
  '2024-02-29T13:14Z'
])
  assert(parse(value), value);
for (const value of [
  '2023-02-29',
  '2024-02-30',
  '2024-13-01',
  '2024-00-01',
  '2024-01-00',
  '2024-01-01T24:00',
  '2024-01-01T01:60',
  '2024-01-01T01:00:60',
  '2024-01-01trash',
  '2024-01-01T01:00:00+24:00',
  '2024-01-01T01:00:00+02:60',
  ''
])
  assert.equal(parse(value), null, value);
assert.equal(parse('2024-02-29T13:14', false), null);
assert.equal(monthDays(2024, 1).filter(Boolean).length, 29);
assert.equal(monthDays(2023, 1).filter(Boolean).length, 28);
assert.equal(monthDays(2024, 0)[0], 1);
assert.equal(monthDays(99, 1).filter(Boolean).length, 28);
assert.equal(localDate(99, 1, 28).getFullYear(), 99);
assert.equal(localDate(2024, 1, 30).getMonth(), 2);
assert.equal(parse('0000-01-01'), null);
assert.equal(
  buttonVisual({ highlighted: true, destructive: true }).content,
  'onError'
);
assert.equal(
  buttonVisual({ highlighted: true, destructive: true, pressed: true })
    .pressedMix,
  true
);
assert.equal(
  buttonVisual({ focused: true }).background,
  buttonVisual({ hovered: true }).background
);
assert.equal(
  buttonVisual({ loading: true, pressed: true }).content,
  'disabledText'
);
assert.equal(fieldVisual({ error: true, focused: true }).border, 'error');
assert.equal(fieldVisual({ tableCell: true }).borderWidth, 0);
assert.equal(
  checkVisual({ mixed: true }).background,
  checkVisual({ checked: true }).background
);
assert.equal(checkVisual({ mixed: true, enabled: false }).mark, 'disabledText');
assert.equal(
  switchVisual({ checked: true, enabled: false }).thumb,
  'disabledText'
);
const tree = [
  { id: 'root', depth: 0, expanded: false, hasChildren: true },
  { id: 'child', depth: 1 },
  { id: 'other', depth: 0 }
];
assert.deepEqual(
  visibleRows(tree).map((row) => row.id),
  ['root', 'other']
);
assert.deepEqual(navigate(visibleRows(tree), 'root', 'ArrowRight'), {
  type: 'expand',
  id: 'root'
});
const expanded = [
  Object.assign({}, tree[0], { expanded: true }),
  ...tree.slice(1)
];
assert.deepEqual(navigate(expanded, 'root', 'ArrowRight'), {
  type: 'select',
  id: 'child'
});
assert.deepEqual(navigate(expanded, 'child', 'ArrowLeft'), {
  type: 'select',
  id: 'root'
});
assert.deepEqual(navigate(expanded, 'root', 'End'), {
  type: 'select',
  id: 'other'
});
assert.equal(navigate([], 'none', 'ArrowDown'), null);
console.log('Shared control states and strict local calendar contract passed.');

const flags = [
  'highlighted',
  'destructive',
  'segmented',
  'checked',
  'pressed',
  'hovered',
  'focused',
  'tonal',
  'flat',
  'loading'
];
for (let mask = 0; mask < 1 << flags.length; mask++) {
  const state = {};
  for (let bit = 0; bit < flags.length; bit++)
    state[flags[bit]] = !!(mask & (1 << bit));
  const paint = buttonVisual(state);
  for (const role of [paint.background, paint.content, paint.border])
    assert(
      role === 'transparent' || cssRoles[role],
      'Unmapped browser paint role ' + role
    );
}
