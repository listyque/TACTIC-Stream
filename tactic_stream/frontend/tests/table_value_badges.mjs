import assert from 'node:assert/strict';
import * as Cells from '../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import * as Services from '../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';
import * as Columns from '../../src/tactic_stream/shared_ui/features/administration/columns/columns.ui.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs';

assert.deepEqual(Cells.valuePresentation('duration'), {
  badge: true,
  icon: 'clock',
  align: 'center',
  value_text_style: ''
});
assert.equal(Cells.valuePresentation('name'), null);
assert.equal(Cells.valueFont({ value_text_style: 'heading' }).size, 16);
assert.equal(Cells.valueFont({ value_text_style: 'heading' }).weight, 600);
assert.equal(Cells.valueFont({ value_text_style: 'small' }).size, 12);
assert.equal(Cells.valueFont({ value_text_style: '' }).size, 13);
assert.equal(Cells.valueFont({ value_text_style: 'constructor' }).size, 13);
assert.equal(
  Cells.valuePresentation('duration', { value_style: 'text' }),
  null
);
assert.deepEqual(Cells.valuePresentation('duration', { value_icon: '' }), {
  badge: true,
  icon: '',
  align: 'center',
  value_text_style: ''
});
assert.deepEqual(Cells.valuePresentation('name', { value_icon: 'FAS_CUBE' }), {
  badge: false,
  icon: 'FAS_CUBE',
  align: 'center',
  value_text_style: ''
});
assert.deepEqual(
  Cells.presentationOptions(
    { icon: 'FAS_CUBE', value_icon: 'old' },
    { value_icon: '', width: 500 }
  ),
  { icon: 'FAS_CUBE', value_icon: '' }
);
for (const width of [80, 180, 320]) {
  const scene = Cells.valueLabel(
    '2 Minutes',
    width,
    58,
    Cells.valuePresentation('duration')
  );
  const badge = scene.nodes[0];
  assert.equal(badge.kind, 'Box');
  assert.ok(badge.x >= 0 && badge.x + badge.width <= width);
  assert.equal(
    badge.children.find((node) => node.id === 'tableValueLabel').text,
    '2 Minutes'
  );
}
const cell = {
  text: '4 assets',
  actions: [{ name: 'nested-table', icon: 'chevron-right' }],
  displayOptions: { icon: 'FAS_CUBE', label: '{@COUNT(demo/asset)} assets' }
};
const action = Services.describe(cell, 180, 58, 'en').nodes[0].children[0];
assert.equal(action.text, 'Assets 4');
assert.equal(
  action.children.find((node) => node.id === 'tableServiceLeadingIcon').icon,
  'FAS_CUBE'
);
assert.equal(
  Cells.relatedLabel('Custom label', cell.displayOptions),
  'Custom label'
);
assert.equal(Cells.relatedLabel('4 assets'), '4 assets');
assert.equal(
  Services.describe(
    { ...cell, displayOptions: { ...cell.displayOptions, value_icon: '' } },
    180,
    58,
    'en'
  ).nodes[0].children[0].children.some(
    (node) => node.id === 'tableServiceLeadingIcon'
  ),
  false
);
console.log(
  'PASS: Duration and configured icons preserve text, units and ordinary labels'
);
const element = { name: 'duration', path: '0/0', visible: true, width: 160 };
const model = {
  ready: true,
  canWrite: true,
  selected: { view: 'table', searchType: 'demo/asset' },
  typeOptions: [],
  definitions: [],
  records: [],
  elements: [element],
  element,
  wizard: { supported: true },
  widgetOptions: []
};
const ui = { ...State.initial(), editing: true };
const nodes = [];
function collect(scene) {
  for (const node of scene.nodes || scene.children || []) {
    nodes.push(node);
    collect(node);
  }
}
collect(Columns.describe(model, ui, 1200, 800, 'en'));
assert.equal(
  nodes.find((node) => node.id === 'definitionCatalogValueIcon').kind,
  'IconChoice'
);
assert.equal(
  nodes.find((node) => node.id === 'definitionCatalogValueStyle').kind,
  'Choice'
);
assert.equal(
  nodes.find((node) => node.id === 'definitionCatalogTextStyle').kind,
  'Choice'
);
assert.deepEqual(
  State.transition(ui, model, {
    type: 'field',
    field: 'valueIcon',
    value: 'FAS_CUBE'
  }).commands,
  [{ type: 'change', field: 'valueIcon', value: 'FAS_CUBE' }]
);
