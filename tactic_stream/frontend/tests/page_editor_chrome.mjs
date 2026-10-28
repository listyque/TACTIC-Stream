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
      assert.equal(tree.y, 0);
      assert(add && add.y < 72);
      assert.equal(nodes.filter((node) => node.kind === 'Splitter').length, 2);
      assert(nodes.find((node) => node.id === 'pageCanvasTools').height <= 82);
      assert.equal(
        nodes.some((node) => node.id === 'pageAction_duplicate'),
        false
      );
    }
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
