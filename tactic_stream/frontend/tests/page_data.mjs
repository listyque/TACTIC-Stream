import assert from 'node:assert/strict';
import * as Data from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.data.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
const document = {
  name: 'work',
  title: 'Work',
  blocks: [
    { kind: 'items', search_type: 'demo/asset', view: 'cards', filters: [] },
    { kind: 'details', children: [{ kind: 'text', field: 'name' }] },
    { kind: 'text', field: 'title' }
  ]
};
const metadata = {
  searchType: 'demo/asset',
  fields: [
    { value: 'code', label: 'Code', dataType: 'varchar' },
    { value: 'amount', label: 'Amount', dataType: 'integer' },
    { value: 'enabled', label: 'Enabled', dataType: 'boolean' },
    { value: 'created', label: 'Created', dataType: 'timestamp' },
    { value: 'name', label: 'Name', dataType: 'text' }
  ],
  itemViews: [{ value: 'cards', label: 'Cards' }],
  tableViews: [{ value: 'table', label: 'Table' }]
};
const original = JSON.stringify(document);
let draft = Data.filter(document, '0', { action: 'add' }, metadata);
draft = Data.filter(
  draft,
  '0',
  { index: 0, field: 'column', value: 'amount' },
  metadata
);
assert.equal(draft.blocks[0].filters[0].value, 0);
draft = Data.filter(draft, '0', { action: 'add' }, metadata);
draft = Data.filter(
  draft,
  '0',
  { index: 1, field: 'column', value: 'enabled' },
  metadata
);
draft = Data.filter(
  draft,
  '0',
  { index: 1, field: 'value', value: 'false' },
  metadata
);
assert.equal(draft.blocks[0].filters[1].value, false);
draft = Data.filter(
  draft,
  '0',
  { index: 0, field: 'relation', value: 'notEmpty' },
  metadata
);
assert.deepEqual(draft.blocks[0].filters[0], {
  column: 'amount',
  relation: '!=',
  value: null
});
assert.equal(Data.relation({ relation: '!=', value: undefined }), 'notEmpty');
const nativeNull = Document.copy(draft);
nativeNull.blocks[0].filters[0].value = undefined;
assert.equal(
  Document.change(nativeNull, '0', 'height', 200).blocks[0].filters[0].value,
  null
);
assert.throws(
  () =>
    Data.filter(
      draft,
      '0',
      { index: 0, field: 'value', value: 'bad' },
      metadata
    ),
  /number/
);
const switched = Data.change(draft, '0', 'search_type', 'demo/shot');
assert.deepEqual(
  switched.blocks[0].filters,
  draft.blocks[0].filters,
  'source change must not silently drop filters'
);
assert.equal(switched.blocks[0].view, 'cards');
assert.equal(
  JSON.stringify(document),
  original,
  'data editing cannot mutate the baseline'
);
assert.equal(Data.mode(document, '1.0'), 'selection');
assert.equal(Data.mode(document, '2'), 'project');
let bound = Data.change(document, '1.0', 'binding', 'selection');
assert.equal(bound.blocks[1].children[0].search_type, 'demo/asset');
assert.equal(Data.scope(bound, '1.0').searchType, 'demo/asset');
assert.throws(
  () => Data.change(document, '2', 'binding', 'selection'),
  /Details/
);
bound = Data.change(document, '2', 'binding', 'record');
bound = Data.change(bound, '2', 'search_type', 'demo/asset');
bound = Data.change(bound, '2', 'source_key', 'demo/asset?code=A');
assert.equal(Data.scope(bound, '2').recordKey, 'demo/asset?code=A');
assert.equal(
  Data.change(bound, '2', 'search_type', 'demo/shot').blocks[2].source_key,
  ''
);
const ui = Object.assign(State.initial(), { selected: '0' }),
  raw = {
    document: draft,
    canWrite: true,
    checked: true,
    dirty: false,
    dataSource: metadata,
    searchTypes: [],
    catalog: []
  };
let state = State.transition(ui, raw, {
  type: 'filter',
  action: 'remove',
  index: 0
});
assert.equal(state.commands[0].document.blocks[0].filters.length, 1);
assert.equal(
  State.transition(
    ui,
    { ...raw, canWrite: false },
    { type: 'filter', action: 'add' }
  ).commands.length,
  0
);
assert.equal(
  State.transition(ui, { ...raw, canWrite: false }, { type: 'source' })
    .commands[0].type,
  'source'
);
const fields = Data.fields(raw, ui, 286, 'en', true),
  rows = fields.filter((row) => row.id?.startsWith('pageFilter_'));
const loading = Data.fields({ ...raw, dataBusy: true }, ui, 286, 'en', true);
assert.equal(
  loading
    .find((row) => row.id === 'pageFilter_0')
    .props.children.find((row) => row.id.endsWith('_relation')).enabled,
  false
);
assert.equal(
  rows[1].props.children.find((row) => row.id.endsWith('_value')).kind,
  'Choice'
);
const date = Data.filter(
  Data.filter(document, '0', { action: 'add' }, metadata),
  '0',
  { index: 0, field: 'column', value: 'created' },
  metadata
);
const dateFields = Data.fields({ ...raw, document: date }, ui, 286, 'en', true);
assert.equal(
  dateFields.find((row) => row.id === 'pageFilter_0').props.children.at(-1)
    .kind,
  'DateChoice'
);
const model = UI.model(raw, ui);
assert(UI.describe(model, ui, 1400, 800, 'en').nodes.length);
console.log(
  'Page data: typed/null filters, real bindings, immutable source changes, write guards and native control projections pass'
);
