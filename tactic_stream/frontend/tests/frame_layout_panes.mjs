import assert from 'node:assert/strict';
import * as Layout from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Preview from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';

const model = {
  layoutNodes: [
    {
      kind: 'row',
      editorPath: [0],
      gap: 16,
      children: [
        {
          kind: 'items',
          text: 'Reports',
          editorPath: [0, 0],
          weight: 3,
          height: 700,
          padding: [12, 12, 12, 12],
          items: { searchType: 'demo/report', view: 'card' }
        },
        { kind: 'details', editorPath: [0, 1], weight: 7 }
      ]
    }
  ],
  layoutDetail: {
    title: 'A selected report',
    targetSearchKey: 'demo/report?code=A',
    layoutNodes: Array.from({ length: 20 }, (_, index) => ({
      kind: 'text',
      text: 'Paragraph ' + index
    }))
  }
};
function flatten(nodes) {
  return nodes.flatMap((node) => [node, ...flatten(node.children || [])]);
}
function scene(width, height, state = {}) {
  return flatten(
    Layout.describe({ ...model, layoutState: state }, width, height, 'en').nodes
  );
}
for (const height of [420, 900]) {
  const nodes = scene(1100, height);
  const left = nodes.find((node) => node.id === 'customLayout_0_0_block');
  const right = nodes.find((node) => node.id === 'customLayout_0_1_surface');
  const split = nodes.find((node) => node.kind === 'Splitter');
  assert.ok(split, 'An Items/Details navigator needs the existing splitter');
  assert.equal(left.y, right.y);
  assert.equal(left.height, right.height);
  assert.equal(left.height, height - 24);
  assert.equal(split.height, height - 24);
  assert.equal(
    nodes.find((node) => node.id === 'customLayoutScroll').contentHeight,
    height
  );
  assert.ok(
    nodes.find((node) => node.id === 'customLayout_0_1').contentHeight >=
      height - 24
  );
  if (height === 420)
    assert.ok(
      nodes.find((node) => node.id === 'customLayout_0_1').contentHeight >
        height
    );
  const moved = Layout.resize({}, { ...split.action, value: split.value + 90 });
  const resized = scene(1100, height, moved);
  assert.equal(
    resized.find((node) => node.id === left.id).width,
    left.width + 90
  );
  const smaller = scene(900, height, moved).find(
    (node) => node.kind === 'Splitter'
  );
  assert.ok(smaller.value >= smaller.min && smaller.value <= smaller.max);
}
assert.ok(
  !scene(360, 640).some((node) => node.kind === 'Splitter'),
  'Narrow pages stack normally'
);
assert.deepEqual(
  Layout.resize({ marker: true }, { key: 'x', value: NaN, extent: 0 }),
  { marker: true }
);
const card = {
  flow: 'grid',
  columns: 1,
  elements: [
    {
      name: 'copy',
      kind: 'group',
      parent: '',
      variant: 'all',
      flow: 'grid',
      columns: 1
    },
    {
      name: 'title',
      kind: 'title',
      parent: 'copy',
      variant: 'all',
      height: 48,
      options: { bind: 'node.title' }
    }
  ]
};
for (const width of [240, 380]) {
  const labels = flatten(
    Preview.describe(
      card,
      { kind: 'object', title: 'A readable report title' },
      width,
      '',
      'en',
      width,
      '',
      'item',
      0,
      false
    ).nodes
  );
  const title = labels.find((node) => node.id === 'item_titleText');
  assert.ok(
    title.width > width - 40,
    'An implicit single-column group must keep its available width'
  );
}
console.log(
  'PASS: navigator panes fill together, retain scrollable details and use bounded split state'
);
