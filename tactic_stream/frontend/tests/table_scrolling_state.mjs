import assert from 'node:assert/strict';
import * as Host from '../../src/tactic_stream/shared_ui/features/table/host.ui.mjs';
import * as Menus from '../../src/tactic_stream/shared_ui/features/table/menus.ui.mjs';

const columns = [
  { name: 'name', width: 160, hideOrder: 0 },
  { name: 'notes', width: 160, hideOrder: 2 },
  { name: 'thumbnail', width: 100, hideOrder: 1 }
];
assert.equal(Host.describe({ columns }, 240).columns.length, 1);
for (const width of [240, 800]) {
  const scrolling = Host.describe(
    { columns, scrollColumns: true, autoFit: true, overrides: { notes: 210 } },
    width
  );
  assert.deepEqual(scrolling.columns, columns);
  assert.deepEqual(
    scrolling.cells.map((cell) => cell.width),
    [160, 210, 100]
  );
  assert.equal(scrolling.width, Math.max(width, 40 + 470 + 64));
}
for (const enabled of [false, true]) {
  const action = Menus.viewActions([], enabled, 'en', true).find(
    (action) => action.command === 'scroll_columns'
  );
  assert.equal(action.checked, true);
  assert.notEqual(
    action.enabled,
    false,
    'Display mode requires no write access'
  );
}
console.log(
  'PASS: optional horizontal scrolling, widths and read-only view menu'
);
