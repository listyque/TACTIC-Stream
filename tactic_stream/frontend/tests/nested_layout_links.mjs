import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs';
const source = {
  ready: true,
  project: 'demo',
  searchType: 'demo/asset',
  view: 'parent',
  source: 7,
  searchTypes: [
    { value: 'demo/asset', label: 'Assets' },
    { value: 'demo/shot', label: 'Shots' }
  ],
  layout: {
    elements: [
      { name: 'title', kind: 'title', options: {} },
      {
        name: 'nested',
        kind: 'view',
        options: { view: 'child' },
        search_type: ''
      }
    ]
  }
};
let ui = {
  ...State.initial(),
  selected: 'nested',
  page: 'design',
  panel: 'settings',
  catalogWidth: 245,
  propertiesWidth: 310
};
assert.deepEqual(State.reference(source, ui), {
  searchType: 'demo/asset',
  view: 'child'
});
let result = State.transition(ui, source, { type: 'openLayout' });
assert.deepEqual(result.commands, [
  { type: 'reference', searchType: 'demo/asset', view: 'child', source: null }
]);
ui = State.synchronize(result.ui, {
  ...source,
  view: 'child',
  source: 8,
  layout: { elements: [{ name: 'leaf' }] }
});
assert.equal(ui.selected, 'leaf');
assert.equal(State.navigationParent(ui).name, 'parent');
assert.deepEqual(
  State.transition(ui, { ...source, dirty: true }, { type: 'backLayout' })
    .commands,
  []
);
result = State.transition(
  ui,
  { ...source, view: 'child' },
  { type: 'backLayout' }
);
assert.deepEqual(result.commands, [
  { type: 'reference', searchType: 'demo/asset', view: 'parent', source: 7 }
]);
ui = State.synchronize(result.ui, source);
assert.equal(ui.selected, 'nested');
assert.equal(ui.catalogWidth, 245);
assert.equal(ui.propertiesWidth, 310);
assert.equal(State.navigationParent(ui), null);
for (const raw of [
  { ...source, dirty: true },
  { ...source, uncertain: true }
])
  assert.equal(
    State.transition(ui, raw, { type: 'openLayout' }).commands.length,
    0
  );
assert.equal(
  State.transition({ ...ui, text: { pending: 'draft' } }, source, {
    type: 'openLayout'
  }).commands.length,
  0
);
const cross = {
  ...source,
  layout: {
    elements: [{ ...source.layout.elements[1], search_type: 'demo/shot' }]
  }
};
assert.deepEqual(State.reference(cross, ui), {
  searchType: 'demo/shot',
  view: 'child'
});
for (const item of [
  { kind: 'text', options: { view: 'child' } },
  { kind: 'view', options: { view: '../invalid' } },
  { kind: 'view', options: { view: 'parent' } },
  { kind: 'view', options: { view: 'child' }, search_type: 'other/private' }
])
  assert.equal(
    State.reference(
      { ...source, layout: { elements: [{ name: 'nested', ...item }] } },
      ui
    ),
    null
  );
const pending = State.transition(ui, source, { type: 'openLayout' }).ui;
assert.equal(
  State.navigationParent(
    State.synchronize(pending, { ...source, project: 'other', ready: false })
  ),
  null
);
assert.equal(
  State.navigationParent(
    State.synchronize(pending, { ...source, view: 'manual' })
  ),
  null
);
const capped = { ...ui, navigation: Array(32).fill({ view: 'parent' }) };
assert.equal(
  State.transition(capped, source, { type: 'openLayout' }).commands.length,
  0
);
console.log(
  'Nested item links: exact/inherited type, source and selection return, dirty guards, scope changes and bounded history pass'
);
