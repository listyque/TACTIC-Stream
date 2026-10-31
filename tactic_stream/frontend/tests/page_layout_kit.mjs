import assert from 'node:assert/strict';
import * as Geometry from '../../src/tactic_stream/shared_ui/features/table/page.layout.mjs';
import * as Layout from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as Data from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.data.mjs';
const measure = (text, size) => text.length * size * 0.5;
const items = [{ columnSpan: 2, rowSpan: 2 }, {}, {}, { columnSpan: 3 }];
const wide = Geometry.grid(
  items,
  920,
  { columns: 3, min_cell_width: 200, row_height: 100 },
  10
);
assert.equal(wide.columns, 3);
assert.equal(wide.placements[0].width, 610);
assert.equal(wide.placements[0].height, 210);
assert.equal(wide.placements[1].x, 620);
assert.equal(wide.placements[2].y, 110);
assert.equal(wide.placements[3].y, 220);
const small = Geometry.grid(
  items,
  360,
  { columns: 3, min_cell_width: 200, row_height: 100 },
  10
);
assert.equal(small.columns, 1);
assert.ok(small.placements.every((item) => item.x === 0 && item.width === 360));
assert.deepEqual(
  Geometry.rowWidths(
    [
      { width: '100px' },
      { sizing: { min_width: 40, max_width: 80 } },
      { weight: 2 }
    ],
    500,
    measure
  ),
  [100, 80, 320]
);
assert.deepEqual(
  Geometry.rowWidths([{ width: '400px' }, { width: '400px' }], 400, measure),
  [200, 200]
);
assert.equal(
  Geometry.width(
    {
      kind: 'text',
      text: 'Hello',
      sizing: { width_mode: 'content' },
      padding: [0, 12, 0, 12]
    },
    500,
    measure
  ),
  59
);
assert.equal(Geometry.width({ sizing: { min_width: 500 } }, 320, measure), 320);
assert.equal(
  Geometry.height(
    { sizing: { height_mode: 'content', max_height: 100 } },
    200,
    null
  ),
  100
);
const doc = {
  name: 'kit',
  title: 'Kit',
  blocks: [{ kind: 'grid', children: [] }]
};
const original = Document.fingerprint(doc);
assert.equal(
  Document.add({ name: 'blank', title: 'Blank', blocks: [] }, '', 'grid')
    .document.blocks[0].height,
  null
);
let add = Document.add(doc, '0', 'heading');
assert.equal(add.key, '0.0');
assert.equal(add.document.blocks[0].children[0].kind, 'heading');
let changed = Document.sizing(add.document, '0.0', 'width_mode', 'fixed');
assert.equal(changed.blocks[0].children[0].width, 240);
changed = Document.sizing(changed, '0.0', 'max_width', '300');
assert.throws(() => Document.sizing(changed, '0.0', 'min_width', '301'));
changed = Document.change(changed, '0.0', 'width', '180');
assert.equal(changed.blocks[0].children[0].sizing.width_mode, 'fixed');
assert.equal(Document.fingerprint(doc), original);
const image = Document.add(doc, '0', 'image');
assert.equal(Data.mode(image.document, '0.0'), 'project');
assert.equal(
  Data.change(image.document, '0.0', 'binding', 'record').blocks[0].children[0]
    .binding,
  'record'
);
let ui = State.initial();
ui.selected = '0';
ui.selection = ['0'];
const event = { type: 'sizing', field: 'width_mode', value: 'content' },
  model = { document: doc, canWrite: true };
const result = State.transition(ui, model, event);
assert.equal(result.commands.length, 1);
assert.equal(result.ui.past.length, 1);
assert.equal(
  State.transition(ui, { ...model, canWrite: false }, event).commands.length,
  0
);
const nodes = [
  {
    kind: 'grid',
    editorPath: [0],
    columns: 3,
    min_cell_width: 200,
    row_height: 100,
    gap: 10,
    children: [
      {
        kind: 'text',
        editorPath: [0, 0],
        text: 'A',
        columnSpan: 2,
        rowSpan: 2
      },
      { kind: 'icon', editorPath: [0, 1], icon: 'folder', iconSize: 32 },
      {
        kind: 'button',
        editorPath: [0, 2],
        text: 'Open',
        href: 'skey://sthpw/project?code=one',
        buttonStyle: 'primary'
      },
      { kind: 'spacer', editorPath: [0, 3] }
    ]
  }
];
const scene = Layout.describe(
  { layoutNodes: nodes },
  944,
  600,
  'en',
  true,
  '',
  measure
);
const grid = scene.nodes
  .find((node) => node.id === 'customLayoutScroll')
  .children.find((node) => node.editorPath);
const children = grid.children.filter((node) => node.editorPath);
assert.equal(children[0].width, 610);
assert.equal(children[0].height, 210);
assert.equal(children[1].x, 620);
assert.equal(children[2].y, 110);
const button = children[2].children[0];
assert.equal(button.action.name, 'layout-link');
assert.equal(button.highlighted, true);
assert.equal(button.enabled, true);
assert.ok(children[3], 'An empty spacer stays selectable on the canvas');
assert.equal(
  grid.width,
  920,
  'A fitted page uses the interior width without an unused scrollbar gutter'
);
const overflowing = Layout.describe(
  { layoutNodes: [{ ...nodes[0], height: 1000 }] },
  944,
  600,
  'en',
  true,
  '',
  measure
).nodes.find((node) => node.id === 'customLayoutScroll');
assert.ok(overflowing.contentHeight > overflowing.height);
assert.equal(
  overflowing.children[0].width,
  904,
  'Overflowing pages retain both interior padding and scrollbar room'
);
console.log(
  'Page layout kit: adaptive spans, sizing, measured content, primitives, bindings and atomic history pass'
);
