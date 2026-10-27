import assert from 'node:assert/strict';
import {
  describe,
  supports,
  maximumHeight
} from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';
const item = (name, kind, row, height, options, search_type = '') => ({
  name,
  kind,
  row,
  height,
  options,
  search_type,
  variant: 'all',
  parent: '',
  column: 1,
  span: 12,
  rows: 1
});
const layout = {
  flow: 'grid',
  collection: 'tree',
  columns: 12,
  elements: [
    item('title', 'title', 1, 24, { bind: 'record.name' }, 'demo/project'),
    item(
      'notes',
      'button',
      2,
      40,
      { action: 'notes', text: 'Notes' },
      'demo/project'
    )
  ]
};
const record = {
  kind: 'object',
  record: { __search_key__: 'demo/project?code=P1', name: 'Project title' }
};
assert(supports(layout, record, 1000));
assert(
  !supports(
    layout,
    { ...record, kind: 'branch', branch: { kind: 'relation' } },
    1000
  ),
  'A relation is not its parent record'
);
assert(
  !supports(
    layout,
    { ...record, record: { __search_key__: 'demo/task?code=T1' } },
    1000
  )
);
const scene = describe(layout, record, 600, '', 'en', 1000, '', '', 0, false);
assert.equal(scene.height, 70);
const nodes = (rows) =>
  rows.flatMap((row) => [row, ...nodes(row.children || [])]);
assert(nodes(scene.nodes).some((node) => node.text === 'Project title'));
assert.equal(
  nodes(scene.nodes).find((node) => node.id.endsWith('titleText')).maxLines,
  1
);
const action = nodes(scene.nodes).find((node) =>
  node.id.endsWith('notesButton')
);
assert.equal(action.action.action, 'notes');
assert(action.enabled);
const editor = nodes(
  describe(layout, record, 600, 'title', 'en', 1000, '', '', 0, true).nodes
);
assert.equal(
  editor.find((node) => node.id.endsWith('notesButton')).enabled,
  false
);
assert(
  editor.some(
    (node) => node.action?.type === 'select' && node.action.name === 'title'
  )
);
const picture = {
  ...layout,
  elements: [item('image', 'image', 1, 64, { bind: 'node.preview.image' })]
};
const image = nodes(
  describe(
    picture,
    {
      ...record,
      preview: { image: 'file:///D:/project files/preview.png', local: true }
    },
    300,
    '',
    'en',
    1000,
    '',
    '',
    0,
    false
  ).nodes
).find((node) => node.kind === 'Preview');
assert.equal(image.source, 'file:///D:/project%20files/preview.png');
assert.equal(maximumHeight(layout, [record, record], 600, 'en', 1000), 70);
const aligned = {
  flow: 'grid',
  collection: 'tree',
  columns: 12,
  elements: [
    { ...layout.elements[0], span: 6, height: 24, align: 'start' },
    {
      ...layout.elements[1],
      name: 'tall',
      row: 1,
      column: 7,
      span: 6,
      height: 100
    }
  ]
};
assert.equal(
  describe(aligned, record, 600, '', 'en', 1000, '', '', 0, false).nodes.find(
    (n) => n.layoutElement === 'title'
  ).height,
  24
);
console.log(
  'PASS actual-type targeting, branch fallback, native actions, editor selection, grid size and trusted local preview'
);
