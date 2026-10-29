import assert from 'node:assert/strict';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as Chrome from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.chrome.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
import { geometry as adminGeometry } from '../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs';
const document = {
  name: 'work',
  title: 'Work',
  blocks: [
    {
      kind: 'row',
      children: [
        { kind: 'column', children: [{ kind: 'text', text: 'Nested' }] }
      ]
    },
    { kind: 'text', text: 'Sibling' }
  ]
};
const original = JSON.stringify(document);
const raw = {
  document,
  catalog: [{ identity: 'work', label: 'Work' }],
  canWrite: true,
  canLoad: true,
  checked: true,
  sourceXml: '<config/>',
  busy: false
};
let ui = State.initial();
const model = () => UI.model(raw, ui);
const event = (value) => {
  const result = State.transition(ui, model(), value);
  assert.deepEqual(result.commands, []);
  ui = result.ui;
};
const rows = () => UI.models(model(), ui).pageBlocks.map((row) => row.key);
const flatten = (scene) =>
  scene.nodes.flatMap((node) => [
    node,
    ...flatten({ nodes: node.children || [] })
  ]);
assert.deepEqual(rows(), ['page', '0', '0.0', '0.0.0', '1']);
event({ type: 'treeToggle', key: '0' });
assert.deepEqual(rows(), ['page', '0', '1']);
assert.equal(ui.selected, '');
event({ type: 'select', key: '0.0.0' });
assert.equal(ui.selected, '0.0.0');
assert.deepEqual(rows(), ['page', '0', '0.0', '0.0.0', '1']);
event({ type: 'treeCollapse', key: 'page' });
assert.deepEqual(rows(), ['page']);
event({ type: 'treeExpand', key: 'page' });
assert.equal(rows().length, 5);
for (const kind of ['page', ...Document.kinds]) assert(Chrome.icons[kind]);
for (const language of ['en', 'ru'])
  for (const width of [360, 860, 1000, 1400, 2000]) {
    const nodes = flatten(UI.describe(model(), ui, width, 800, language));
    assert(nodes.every((node) => node.width >= 0 && node.height >= 0));
    if (width >= 1000) {
      const tree = nodes.find((node) => node.id === 'pageLayersPanel'),
        add = nodes.find((node) => node.id === 'pageAddWidget');
      assert.equal(tree.width, 180);
      const toolbar = nodes.find((node) => node.id === 'pageCanvasTools');
      assert.equal(tree.y, toolbar.height + 8);
      assert(add && add.y < 72);
      assert.equal(nodes.filter((node) => node.kind === 'Splitter').length, 2);
      assert(toolbar.height <= 100);
      assert.equal(
        nodes.some((node) => node.id === 'pageAction_duplicate'),
        false
      );
    }
  }
for (const language of ['en', 'ru'])
  for (const width of [320, 360, 760, 850, 1100, 2000]) {
    for (const creating of [false, true]) {
      const empty = UI.model({ ...raw, document: null, catalog: [] }, ui);
      const state = { ...State.initial(), creating };
      const scene = UI.describe(empty, state, width, 800, language);
      const nodes = flatten(scene),
        toolbar = nodes.find((node) => node.id === 'pageEmptyTools');
      const primary = nodes.find((node) => node.id === 'pageNew');
      assert(primary && primary.highlighted && primary.text.length > 0);
      assert.equal(
        nodes.some((node) => node.id === 'pageCanvasSize'),
        false
      );
      for (const item of toolbar.children) {
        assert(
          item.x >= 0 && item.x + item.width <= width,
          language + ' ' + width + ' ' + item.id
        );
        assert(item.y + item.height <= toolbar.height);
      }
      for (let i = 0; i < toolbar.children.length; i++)
        for (const next of toolbar.children.slice(i + 1)) {
          const item = toolbar.children[i];
          assert(
            item.x + item.width <= next.x ||
              next.x + next.width <= item.x ||
              item.y + item.height <= next.y ||
              next.y + next.height <= item.y,
            item.id + ' overlaps ' + next.id
          );
        }
      assert.equal(
        nodes.some((node) => node.id === 'pageLayoutCreate'),
        creating
      );
      assert.equal(
        nodes.some((node) => node.id === 'pageEmptyHint'),
        !creating
      );
    }
    const tools = Chrome.canvasTools(
      model(),
      State.initial(),
      width,
      language,
      true
    );
    assert(tools.nodes.find((node) => node.id === 'pagePreviewToggle'));
    assert(
      tools.nodes.find((node) => node.id === 'pageToolsMenu').label.length > 0
    );
    assert(
      !Chrome.actions(model(), ui, language).some((action) =>
        ['new', 'preview'].includes(action.command)
      )
    );
  }
event({ type: 'panelSize', panel: 'layers', value: 245 });
event({ type: 'panelSize', panel: 'properties', value: 350 });
assert.equal(Chrome.geometry(1400, ui).left, 245);
event({ type: 'togglePanel', panel: 'layers' });
event({ type: 'togglePanel', panel: 'properties' });
assert.equal(Chrome.geometry(1400, ui).canvasWidth, 1316);
event({ type: 'togglePanel', panel: 'layers' });
event({ type: 'togglePanel', panel: 'properties' });
assert.equal(Chrome.geometry(1400, ui).left, 245);
event({ type: 'panelSize', panel: 'layers', value: Infinity });
assert.equal(ui.layersWidth, 245);
event({ type: 'sourceXml' });
const nodes = flatten(UI.describe(model(), ui, 1400, 800, 'en'));
assert(
  !nodes.some(
    (node) => node.id === 'pageLayersPanel' || node.id === 'pagePropertiesPanel'
  )
);
const xml = nodes.find((node) => node.id === 'pageXmlSource');
assert.equal(xml.text, '<config/>');
assert(xml.readOnly && xml.syntax === 'xml');
assert.equal(JSON.stringify(document), original);
assert.equal(adminGeometry(1400, 900, true).nav, 56);
assert.deepEqual(Chrome.toolEvent('moveUp'), { type: 'reorder', delta: -1 });
assert(
  Chrome.actions({ ...model(), busy: true }, ui, 'en')
    .filter((row) =>
      ['new', 'duplicate', 'moveUp', 'moveDown'].includes(row.command)
    )
    .every((row) => !row.enabled)
);
console.log(
  'Page editor chrome: compact geometry, tree, reversible split panels, XML and write guards pass'
);
