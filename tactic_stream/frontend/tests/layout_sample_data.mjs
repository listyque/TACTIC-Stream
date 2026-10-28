import assert from 'node:assert/strict';
import * as Samples from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.samples.mjs';
import * as Composition from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs';
const element = (name, kind, options = {}, extra = {}) => ({
  name,
  kind,
  options,
  parent: '',
  variant: 'all',
  when: [],
  hidden: false,
  row: 1,
  column: 1,
  span: 12,
  rows: 1,
  columns: 12,
  height: 40,
  role: '',
  tag: 'div',
  flow: 'grid',
  align: 'stretch',
  tone: 'normal',
  ...extra
});
const layout = {
  collection: 'grid',
  flow: 'grid',
  columns: 12,
  elements: [
    element('title', 'title', { bind: 'record.name' }),
    element(
      'state',
      'field',
      { bind: 'record.state', format: 'badge', colors: '{"planned":"cyan"}' },
      { row: 2 }
    ),
    element(
      'progress',
      'field',
      { bind: 'record.percent', format: 'progress' },
      { row: 3 }
    ),
    element('due', 'field', { bind: 'record.due', format: 'date' }, { row: 4 })
  ]
};
const sample = Samples.fallback(layout, [], 'demo/asset', 'title', 'en');
assert.equal(sample.title, 'Example item');
assert.equal(sample.record.state, 'planned');
assert.equal(sample.record.percent, 42);
assert.match(sample.record.due, /^2026-/);
assert(!sample.record.__search_key__ && !sample.record.id);
const real = {
  kind: 'object',
  record: { __search_key__: 'demo/asset?code=A', name: 'Real' }
};
const original = JSON.stringify(real);
assert.equal(
  Samples.fallback(layout, [real], 'demo/asset', 'title', 'en'),
  null
);
assert.equal(JSON.stringify(real), original);
const typed = {
  ...layout,
  elements: [
    element(
      'artifact',
      'view',
      { view: 'card' },
      { search_type: 'demo/artifact', widget_layout: layout }
    )
  ]
};
const artifact = Samples.fallback(
  typed,
  [real],
  'demo/asset',
  'artifact',
  'ru'
);
assert.equal(artifact.search_type, 'demo/artifact');
assert.equal(artifact.title, 'Пример элемента');
assert(Composition.visible(typed.elements[0], artifact, typed, 1400));
assert.equal(
  Samples.fallback(
    typed,
    [{ kind: 'object', search_type: 'demo/artifact', record: {} }],
    'demo/asset',
    'artifact',
    'ru'
  ),
  null
);
for (const variant of [
  'main',
  'children',
  'process',
  'relation',
  'versions',
  'snapshot',
  'file'
]) {
  const one = {
    ...layout,
    elements: [element('one', 'title', {}, { variant })]
  };
  const node = Samples.fallback(one, [], 'demo/asset', 'one', 'en');
  assert(node && Composition.supports(one, node, 1400), variant);
}
const malicious = {
  ...layout,
  elements: [
    element('bad', 'field', { bind: 'record.__proto__.polluted' }),
    element('identity', 'field', { bind: 'record.__search_key__' })
  ]
};
assert.equal(
  Samples.fallback(malicious, [], 'demo/asset', 'bad', 'en').record
    .__search_key__,
  undefined
);
assert.equal({}.polluted, undefined);
const ui = { ...State.initial(), selected: 'title' };
const raw = {
  liveInterface: { table: { item_layout: layout } },
  searchType: 'demo/asset',
  sampleItems: []
};
assert(UI.model(raw, ui).samplePreview);
for (const field of ['busy', 'error', 'sampleError', 'previewError'])
  assert.equal(
    UI.model({ ...raw, [field]: field === 'busy' ? true : 'Read failed' }, ui)
      .samplePreview,
    null
  );
const scene = Samples.scene(
  layout,
  sample,
  640,
  100,
  'title',
  true,
  'en',
  1400,
  ''
);
assert.equal(scene.nodes[0].id, 'layoutSampleScroll');
assert.equal(scene.nodes[0].scrollbarId, 'layoutSampleScrollBar');
assert(scene.nodes[0].contentHeight > 100);
assert(scene.canvasBoxes.some((box) => box.key === 'title'));
console.log(
  'Item samples: empty data, selected type, typed bindings, variants, identity isolation, errors and shared scroll/canvas pass'
);
