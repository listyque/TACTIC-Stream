import assert from 'node:assert/strict';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/showcase.ui.mjs';
import {
  controlKinds,
  validateScene,
  node,
  rect
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Examples from '../../src/tactic_stream/shared_ui/controls/showcase.examples.mjs';
import * as Chart from '../../src/tactic_stream/shared_ui/controls/charts/chart.ui.mjs';
import * as Extended from '../../src/tactic_stream/shared_ui/features/administration/showcase.examples.mjs';
assert.equal(UI.catalogue.families.length, 29);
assert.equal(new Set(UI.catalogue.families.map((f) => f.id)).size, 29);
assert.equal(UI.catalogue.categories.length, 6);
for (const family of UI.live) {
  const model = { ...UI.initial(), family };
  const sample = (
    Extended.families.includes(family) ? Extended : Examples
  ).describe(model, family, 600, 'en');
  assert(sample.code, family + ' must have a usable code example');
  const expression = sample.code
    .replace(/^\/\/.*\n/gm, '')
    .replace(/^import .*;\n/m, '')
    .trim()
    .replace(/;$/, '');
  // Execute only this repository's generated examples, never user-provided code.
  const result = new Function(
    'node',
    'rect',
    'describe',
    'return (' + expression + ')'
  )(node, rect, Chart.describe);
  validateScene(
    result.nodes ? result : { nodes: [result] },
    result.models || {},
    { showcaseMenu: true, showcaseDialog: true }
  );
}
function walk(nodes, check) {
  for (const n of nodes) {
    check(n);
    walk(n.children || [], check);
  }
}
for (const language of ['en', 'ru'])
  for (const width of [320, 620, 1000])
    for (const state of UI.states)
      for (const family of UI.live)
        for (const code of [false, true]) {
          const model = { ...UI.initial(), family, state, code };
          const scene = UI.describe(model, UI.catalogue, width, 720, language);
          validateScene(
            scene,
            {
              ...UI.models(model),
              families: UI.families(UI.catalogue, model, language)
            },
            { showcaseMenu: true, showcaseDialog: true }
          );
          const ids = new Set();
          walk(scene.nodes, (n) => {
            assert(controlKinds.includes(n.kind));
            assert(!ids.has(n.id), n.id);
            ids.add(n.id);
            for (const key of ['x', 'y', 'width', 'height'])
              assert(Number.isFinite(n[key]), n.id + '.' + key);
            assert(n.width >= 0 && n.height >= 0, n.id);
          });
          const content = scene.nodes.find((n) => n.id === 'showcaseContent');
          assert.equal(content.x + content.width <= width, true);
          const title = content.children.find((n) => n.id === 'showcaseTitle');
          const scope = content.children.find((n) => n.id === 'showcaseScope');
          if (width < 740)
            assert(title.height >= 64, 'Two full heading lines fit');
          assert(
            scope.y >= title.y + title.height,
            'Subtitle follows the whole heading'
          );
        }
const initial = UI.initial(),
  changed = UI.transition(
    initial,
    { type: 'text', value: 'Updated' },
    UI.catalogue
  );
assert.equal(initial.text, 'Robot Arm');
assert.equal(changed.text, 'Updated');
assert.equal(
  UI.transition(initial, { type: 'family', value: 'bogus' }, UI.catalogue)
    .family,
  initial.family
);
assert.equal(
  UI.transition(initial, { type: 'state', value: 'bogus' }, UI.catalogue).state,
  'default'
);
assert(
  UI.families(UI.catalogue, { ...initial, query: 'StatusChip' }, 'en').some(
    (f) => f.id === 'badges'
  )
);
assert.equal(
  UI.families(UI.catalogue, { ...initial, query: 'nothingmatches42' }, 'ru')
    .length,
  0
);
assert(
  UI.families(
    UI.catalogue,
    { ...initial, category: 'foundations' },
    'en'
  ).every(
    (f) =>
      UI.catalogue.families.find((r) => r.id === f.id).category ===
      'foundations'
  )
);
console.log(
  'Showcase: 29 live families, executable source, EN/RU and narrow bounds pass.'
);
assert.equal(UI.live.length, 29);
assert.deepEqual(
  UI.fileLabels([
    { name: 'local.txt' },
    'file:///tmp/preview%20one.png',
    'https://example.com/file'
  ]),
  [{ name: 'local.txt' }, { name: 'preview one.png' }]
);
const locked = { ...UI.initial(), state: 'readonly' };
assert.equal(
  UI.transition(
    locked,
    { type: 'sampleCell', row: 0, column: 1, value: 'blocked' },
    UI.catalogue
  ),
  locked
);
let graph = UI.transition(
  UI.initial(),
  {
    type: 'sampleGraph',
    value: {
      type: 'moveNodes',
      positions: [{ identity: 'a', nodeX: 10, nodeY: 20 }]
    }
  },
  UI.catalogue
);
graph = UI.transition(
  graph,
  {
    type: 'sampleGraph',
    value: {
      type: 'moveNodes',
      positions: [{ identity: 'b', nodeX: 30, nodeY: 40 }]
    }
  },
  UI.catalogue
);
assert.equal(graph.graphPositions.length, 2);
assert.deepEqual(
  UI.transition(
    { ...graph, graphSelected: ['a'] },
    { type: 'sampleGraph', value: { type: 'clear' } },
    UI.catalogue
  ).graphSelected,
  []
);
assert.equal(graph.graphPositions[0].nodeX, 10);
assert.throws(
  () =>
    validateScene({
      nodes: [
        node('Progress', 'badProgress', rect(0, 0, 100, 4), { value: NaN })
      ]
    }),
  /finite/
);
assert.throws(
  () =>
    validateScene({
      nodes: [
        node('Search', 'badSearch', rect(0, 0, 100, 36), { suggestions: 'bad' })
      ]
    }),
  /suggestions/
);
