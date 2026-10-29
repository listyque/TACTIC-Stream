import {
  cssRoles,
  cssVariables,
  cssColor,
  palette
} from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as Numbers from '../../src/tactic_stream/shared_ui/controls/forms/number.mjs';
import * as Segments from '../../src/tactic_stream/shared_ui/controls/forms/segmented.mjs';
import { fraction } from '../../src/tactic_stream/shared_ui/controls/display/progress.mjs';
import assert from 'node:assert/strict';

for (const style of ['md3', 'material5', 'fluent'])
  for (const dark of [true, false])
    assert.equal(
      cssVariables(style, dark, [48, 53, 56], [120, 166, 188])[
        '--error-container'
      ],
      cssColor(
        palette(style, dark, [48, 53, 56], [120, 166, 188]).errorContainer
      )
    );

for (const language of ['en', 'ru']) {
  const decimal = language === 'ru' ? ',' : '.';
  assert.equal(Numbers.parse('1' + decimal + '25', 2, language), 1.25);
  assert.equal(Numbers.format(-1.25, 2, language), '-1' + decimal + '25');
  const grouped = language === 'ru' ? '1\u00a0234,5' : '1,234.5';
  assert.equal(Numbers.format(1234.5, 2, language), grouped);
  assert.equal(Numbers.parse(grouped, 2, language), 1234.5);
  const tiny = '0' + decimal + '00000001';
  assert.equal(Numbers.format(0.00000001, 8, language), tiny);
  assert.equal(Numbers.parse(tiny, 8, language), 0.00000001);
  assert.equal(
    Numbers.parse(language === 'ru' ? '12 34,5' : '12,34.5', 2, language),
    null
  );
  for (const invalid of [
    '',
    '+',
    '1e3',
    'NaN',
    'Infinity',
    '1' + decimal + '234',
    'one',
    ' 1 '
  ])
    assert.equal(Numbers.parse(invalid, 2, language), null);
}
assert.equal(Numbers.clamp(null, 0, 10), null);
assert.equal(Numbers.step(9, 1, 0, 10, 5), 10);
assert.equal(Numbers.step(-1.25, -1, -2, 3, 0.25, 2), -1.5);
assert.equal(
  Numbers.clamp(Number.MAX_VALUE, -Number.MAX_VALUE, Number.MAX_VALUE, 8),
  Number.MAX_VALUE
);
const segmented = [
  { value: 'a' },
  { value: 'b', enabled: false },
  { value: 'c' }
];
assert.equal(Segments.target(segmented, 'a', 'ArrowRight'), 2);
assert.equal(Segments.target(segmented, 'a', 'ArrowLeft'), 2);
assert.equal(Segments.target(segmented, 'c', 'Home'), 0);
assert.equal(Segments.target(segmented, 'a', 'End'), 2);
assert.equal(Segments.entry([{ value: 'a', disabled: true }], 'a'), -1);
assert.equal(Segments.target([], 'a', 'ArrowRight'), -1);
assert.equal(fraction(undefined), null);
assert.equal(fraction(Infinity), null);
assert.equal(fraction(5, 0, 10), 0.5);
assert.equal(fraction(10, 10, 10), 0);
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
  navigate,
  row as treeRow
} from '../../src/tactic_stream/shared_ui/controls/lists/tree.ui.mjs';

for (const width of [240, 320, 480])
  for (const depth of [0, 1, 5])
    for (const subtitle of ['', 'cg/scenes']) {
      const scene = treeRow('entry', width, {
        title: 'Ready to Sound',
        subtitle,
        depth,
        hasChildren: true
      });
      const [icon, ...labels] = scene.nodes[0].children;
      const toggle = scene.nodes[1];
      for (const label of labels) {
        assert(
          label.x - (icon.x + icon.width) >= 12,
          'Tree text needs an icon gap'
        );
        assert(
          label.x + label.width <= toggle.x - 8,
          'Tree text must leave the folder toggle clear'
        );
      }
    }

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
