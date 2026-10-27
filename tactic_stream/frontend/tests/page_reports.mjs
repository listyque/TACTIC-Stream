import assert from 'node:assert/strict';
import * as Reports from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.reports.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as Filters from '../../src/tactic_stream/shared_ui/features/table/page.filters.mjs';
import * as Plot from '../../src/tactic_stream/shared_ui/features/table/report.ui.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
const source = {
  searchType: 'demo/entry',
  fields: [
    { value: 'code', label: 'Code', dataType: 'varchar' },
    { value: 'amount', label: 'Amount', dataType: 'numeric' },
    { value: 'created', label: 'Created', dataType: 'timestamp' }
  ]
};
const ui = State.initial(),
  model = {
    document: { name: 'report', title: 'Report', blocks: [] },
    searchTypes: [{ value: 'demo/entry', label: 'Entries' }],
    dataSource: source,
    canWrite: true,
    catalog: []
  };
const original = JSON.stringify(model);
let edit = Reports.edit(model, ui, { type: 'pageFilterAdd' });
assert.equal(JSON.stringify(model), original);
model.document = edit.document;
assert.equal(Reports.scope(model.document, edit.ui).searchType, 'demo/entry');
edit = Reports.edit(model, edit.ui, {
  type: 'pageCondition',
  index: 0,
  field: 'column',
  value: 'amount'
});
assert.equal(edit.document.filters[0].value, 0);
model.document = edit.document;
const chart = Document.add(model.document, '', 'chart', 'demo/entry');
model.document = chart.document;
ui.selected = chart.key;
edit = Reports.edit(model, ui, {
  type: 'report',
  section: 'group',
  action: 'add'
});
model.document = edit.document;
edit = Reports.edit(model, ui, {
  type: 'report',
  section: 'group',
  index: 0,
  field: 'column',
  value: 'created'
});
model.document = edit.document;
edit = Reports.edit(model, ui, {
  type: 'report',
  section: 'group',
  index: 0,
  field: 'period',
  value: 'month'
});
model.document = edit.document;
assert.equal(model.document.blocks[0].group_by[0].period, 'month');
assert(
  Reports.fields(model, ui, 280, 'ru', true).some(
    (field) => field.id === 'pageGroup_0_period'
  )
);
const blocked = State.transition(
  ui,
  { ...model, canWrite: false },
  { type: 'report', field: 'group_limit', value: 100 }
);
assert.equal(blocked.commands.length, 0);
const definitions = [
  {
    name: 'amount',
    title: 'Amount',
    dataType: 'numeric',
    value: 0,
    enabled: true
  },
  {
    name: 'active',
    title: 'Active',
    dataType: 'boolean',
    value: false,
    enabled: true
  }
];
let draft = Filters.initial(definitions);
draft = Filters.change(draft, {
  name: 'amount',
  field: 'value',
  value: '12.5'
});
assert.equal(Filters.values(definitions, draft).amount.value, 12.5);
assert.equal(Filters.values(definitions, draft).active.value, false);
assert.equal(definitions[0].value, 0);
assert.throws(
  () =>
    Filters.values(definitions, {
      ...draft,
      amount: { value: 'nope', enabled: true }
    }),
  /number/
);
const data = {
  columns: [
    { key: 'group_0', title: 'Group', kind: 'group' },
    { key: 'total', title: 'Total', kind: 'measure' }
  ],
  measure: 'total',
  rows: [
    { group_0: 'Negative', total: -5 },
    { group_0: 'Zero', total: 0 },
    { group_0: null, total: null }
  ],
  truncated: true
};
const scene = Plot.describe(
  { kind: 'chart', text: 'Chart', report: data },
  'plot',
  600,
  300,
  'en'
);
const bar = scene.nodes
  .find((node) => node.id === 'plot_bars')
  .children.find((node) => node.id === 'plot_bar_0');
assert(bar.width > 0 && bar.x >= 0);
const grid = Plot.describe(
  { kind: 'summary', text: 'Report', report: data },
  'summary',
  600,
  300,
  'en'
).nodes.find((node) => node.kind === 'Grid');
assert.equal(Plot.cell(grid, {}, 2, 1).nodes[0].text, '—');
assert.equal(Plot.cell(grid, {}, 1, 1).nodes[0].text, '0');
assert(Filters.describe(definitions, draft, 320, 'ru').height > 0);
assert.equal(
  Reports.fields({ ...model, dataBusy: true }, ui, 280, 'en', true).find(
    (field) => field.id === 'pageGroupAdd'
  ).props.enabled,
  false
);
console.log(
  'Page reports: immutable shared filters, typed runtime values, dimensions, read-only guards and negative/NULL chart/report rendering pass'
);
