import assert from 'node:assert/strict';
import * as Services from '../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';

for (const width of [64, 120, 160, 320]) {
  for (const count of [1, 2, 5]) {
    const actions = Array.from({ length: count }, (_, index) => ({
      name: 'gallery',
      icon: 'image',
      label: 'Gallery ' + index
    }));
    const scene = Services.describe({ actions }, width, 100, 'en');
    const scroll = scene.nodes[0];
    const rows = new Map();
    for (const action of scroll.children) {
      if (!rows.has(action.y)) rows.set(action.y, []);
      rows.get(action.y).push(action);
    }
    for (const row of rows.values()) {
      const first = row[0],
        last = row.at(-1);
      assert.equal((first.x + last.x + last.width) / 2, width / 2);
    }
    if (count === 1) assert.equal(scroll.y + scroll.children[0].height / 2, 50);
  }
}
const mixed = Services.describe(
  {
    text: 'Script name',
    actions: [{ name: 'edit', label: 'Edit', icon: 'edit' }]
  },
  160,
  58,
  'en'
);
assert.equal(mixed.nodes[0].children[0].x, 6, 'Text remains left aligned');
console.log(
  'PASS: centered action rows, wrapped groups and unchanged text layout'
);
