import assert from 'node:assert/strict';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
import * as Canvas from '../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import * as Layout from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';

const document = {
  name: 'review',
  title: 'Review',
  blocks: [
    {
      kind: 'column',
      children: [
        { kind: 'text', text: 'A' },
        { kind: 'text', text: 'B' }
      ]
    },
    { kind: 'column', children: [] }
  ]
};
const original = JSON.stringify(document);
const moved = Document.geometry(
  document,
  {
    key: '0.0',
    handle: 'move',
    after: { x: 420, y: 40, width: 40, height: 30 }
  },
  [
    { key: '0', depth: 0, x: 0, y: 0, width: 300, height: 300 },
    { key: '0.0', depth: 1, x: 0, y: 0, width: 40, height: 30 },
    { key: '1', depth: 0, x: 400, y: 0, width: 300, height: 300 }
  ]
);
assert.equal(moved.key, '1.0');
assert.equal(moved.document.blocks[1].children[0].text, 'A');
assert.equal(document.blocks[0].children.length, 2);
assert.equal(JSON.stringify(document), original);
assert.throws(() => Document.block(document, '9.0'));
assert.throws(() => Document.spacing(document, '0', 'padding', 0, -1));
assert.throws(() => Document.change(document, '0', 'width', '2.5'));
const resized = Document.geometry(
  document,
  {
    key: '0.0',
    handle: 'se',
    before: { width: 80, height: 28 },
    after: { width: 140, height: 64 }
  },
  []
);
assert.equal(resized.document.blocks[0].children[0].width, 140);
assert.equal(resized.document.blocks[0].children[0].height, 64);
const scene = Layout.describe(
  {
    layoutNodes: [
      {
        kind: 'group',
        editorPath: [0],
        padding: [10, 20, 30, 40],
        margin: [2, 3, 4, 5],
        gap: 12,
        children: [{ kind: 'text', text: 'A', editorPath: [0, 0] }]
      }
    ]
  },
  700,
  600,
  'en'
);
const selected = Canvas.decorate(scene, 'editorPath');
assert.notEqual(selected, scene);
assert.equal(
  scene.nodes.some((n) => n.id === 'canvasOverlay'),
  false
);
assert.equal(Canvas.decorate(scene, 'editorPath').canvasBoxes.length, 2);
const bounds = selected.canvasBoxes.find((b) => b.key === '0.0');
assert.equal(bounds.x, 45);
assert.equal(bounds.y, 12);
assert.deepEqual(
  Canvas.transform({ x: 1, y: 2, width: 80, height: 30 }, 'move', 3.4, -8),
  { x: 4, y: -6, width: 80, height: 30 }
);
assert.equal(
  Canvas.transform({ width: 80, height: 30 }, 'se', -900, -900).width,
  40
);
const raw = {
  document,
  catalog: [{ identity: 'review', label: 'Review' }],
  canWrite: true,
  checked: true,
  dirty: false
};
for (const width of [390, 850, 1400])
  for (const panel of ['layers', 'canvas', 'properties']) {
    const ui = Object.assign(State.initial(), { selected: '0.0', panel });
    const model = UI.model(raw, ui),
      result = UI.describe(model, ui, width, 700, 'en');
    assert(result.nodes.length);
    assert(result.nodes.every((n) => n.x >= 0 && n.width <= width));
  }
let ui = State.initial();
ui.selected = '0.0';
assert.equal(
  State.transition(ui, raw, { type: 'add', value: '' }).commands.length,
  0
);
assert.equal(
  State.transition(ui, Object.assign({}, raw, { canWrite: false }), {
    type: 'geometry',
    value: {}
  }).commands.length,
  0
);
ui.text = { '0.0:title': 'pending' };
assert(State.transition(ui, raw, { type: 'geometry', value: {} }).ui.error);
ui = Object.assign(State.initial(), {
  confirmation: 'remove',
  selected: '0.0'
});
assert.equal(
  State.transition(ui, Object.assign({}, raw, { uncertain: true }), {
    type: 'confirm'
  }).commands.length,
  0
);
assert.equal(
  State.transition(ui, raw, { type: 'confirm' }).commands[0].document.blocks[0]
    .children.length,
  1
);
console.log(
  'Page canvas: immutable movement, resize, spacing, responsive panels and write guards pass'
);
const clipped = Canvas.boxes(
  [
    {
      id: 'clip',
      x: 0,
      y: 0,
      width: 100,
      height: 60,
      clip: true,
      children: [
        { id: 'partial', editorPath: [0], x: 0, y: 40, width: 100, height: 40 },
        { id: 'hidden', editorPath: [1], x: 0, y: 80, width: 100, height: 40 }
      ]
    }
  ],
  'editorPath'
);
assert.equal(clipped.length, 1);
assert.equal(clipped[0].height, 40);
assert.equal(clipped[0].hit.height, 20);
const hits = [
  { key: 'parent', x: 0, y: 0, width: 200, height: 100 },
  { key: 'child', x: 20, y: 20, width: 100, height: 50 }
];
assert.equal(Canvas.pick(hits, 30, 30).key, 'child');
assert.equal(Canvas.pick(hits, 30, 30, 'child', true).key, 'parent');
assert.equal(Canvas.pick(hits, 30, 30, 'parent', true).key, 'child');
assert.equal(Canvas.pick(hits, 250, 30), null);
const stacked = Canvas.boxes(
  [
    {
      id: 'front',
      editorPath: [0],
      layer: 4,
      x: 0,
      y: 0,
      width: 100,
      height: 100
    },
    {
      id: 'back',
      editorPath: [1],
      layer: 1,
      x: 0,
      y: 0,
      width: 100,
      height: 100
    }
  ],
  'editorPath'
);
assert.equal(
  Canvas.pick(stacked, 30, 30).key,
  '0',
  'Selection follows visual stacking'
);
assert.equal(
  Canvas.pick(clipped, 10, 70),
  null,
  'clipped areas cannot be selected'
);
const previewUi = State.transition(State.initial(), raw, {
  type: 'preview'
}).ui;
assert(previewUi.preview);
const clean = UI.describe(UI.model(raw, previewUi), previewUi, 1400, 700, 'en');
assert(
  !clean.nodes.some((node) =>
    ['pageLayersPanel', 'pagePropertiesPanel'].includes(node.id)
  )
);
assert.equal(clean.nodes.find((node) => node.id === 'pageCanvasPanel').x, 0);
assert.equal(
  State.transition(previewUi, raw, { type: 'preview' }).commands.length,
  0
);
