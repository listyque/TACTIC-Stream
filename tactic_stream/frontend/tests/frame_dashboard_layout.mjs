import assert from 'node:assert/strict';
import * as Layout from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Page from '../../src/tactic_stream/shared_ui/features/table/page.ui.mjs';

function find(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = find(node.children || [], id);
    if (child) return child;
  }
}
const scene = Layout.describe(
  {
    layoutNodes: [
      {
        kind: 'text',
        text: 'Context',
        region: 'header',
        height: 28,
        editorPath: [0]
      },
      {
        kind: 'table',
        text: 'Queue',
        height: 240,
        editorPath: [1],
        table: { searchType: 'sthpw/task' }
      }
    ]
  },
  720,
  500,
  'en'
);
const table = find(scene.nodes, 'customLayout_1');
const block = find(scene.nodes, 'customLayout_1_block');
assert.equal(block.height, 240, 'Table title is inside its height budget');
assert.equal(table.y + table.height, block.height);
assert.equal(table.x, 0);
assert.equal(table.width, 720);
const header = find(scene.nodes, 'customLayout_0_block');
assert.equal(header.x, 0, 'Header has no implicit side gutter');
assert.equal(header.width, 720);
assert.deepEqual(Page.describe({}, 720, 500, 'en').bodyBounds, {
  x: 0,
  y: 52,
  width: 720,
  height: 448
});
console.log(
  'Dashboard table stays inside its bounds; header and body use the full width.'
);
