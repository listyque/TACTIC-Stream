import assert from 'node:assert/strict';
import {
  matching,
  trigger,
  panel
} from '../../src/tactic_stream/shared_ui/features/search/branch_filter.ui.mjs';
const rows = [
  { id: 'a', text: 'Робот\nAST001' },
  { id: 'b', text: 'Vehicle [final].png\nAST002' }
];
assert.deepEqual(matching(rows, ' рОБот '), ['a']);
assert.deepEqual(matching(rows, 'AST002'), ['b']);
assert.deepEqual(matching(rows, '[final].'), ['b']);
assert.deepEqual(matching(rows, '.*'), []);
assert.deepEqual(matching(rows, ''), ['a', 'b']);
const button = trigger('', 'en').nodes[0];
assert.equal(button.width, 24);
assert.equal(button.height, 24);
assert.equal(button.text, 'Search in this branch');
const scene = panel({ query: 'absent', count: 0 }, 280, 'ru');
assert.equal(
  scene.nodes.find((node) => node.id === 'branchSearchCount').text,
  'Ничего не найдено'
);
for (const node of scene.nodes)
  assert.ok(node.x >= 0 && node.x + node.width <= 280);
console.log(
  'Branch matching, literal search, compact geometry and translation pass'
);
