import assert from 'node:assert/strict';
import * as Raw from '../../src/tactic_stream/shared_ui/features/administration/database/raw.state.mjs';
import { cellText } from '../../src/tactic_stream/shared_ui/features/administration/database/raw.ui.mjs';
import * as Sidebar from '../../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.state.mjs';
import * as Columns from '../../src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs';

const table = {
  ready: true,
  canWrite: true,
  canLoad: true,
  identity: 'table:A',
  rows: [{ key: [1] }],
  columns: [{ name: 'id' }],
  metadata: { label: 'project / table', offset: 0, total: 120 }
};
let ui = Raw.transition(Raw.initial(), table, { type: 'drop' }).ui;
assert.equal(ui.confirmation, 'drop');
assert.deepEqual(Raw.transition(ui, table, { type: 'confirm' }).commands, []);
ui = Raw.transition(ui, table, {
  type: 'dropName',
  value: table.metadata.label
}).ui;
assert.deepEqual(
  Raw.transition(ui, { ...table, identity: 'table:B' }, { type: 'confirm' })
    .commands,
  []
);
assert.deepEqual(Raw.transition(ui, table, { type: 'confirm' }).commands, [
  { type: 'drop', name: table.metadata.label }
]);
assert.deepEqual(
  Raw.transition(Raw.initial(), { ...table, dirty: true }, { type: 'next' })
    .commands,
  []
);
assert.deepEqual(
  Raw.transition(Raw.initial(), { ...table, uncertain: true }, { type: 'save' })
    .commands,
  []
);
const save = Raw.transition(
  Raw.initial(),
  { ...table, dirty: true },
  { type: 'save' }
);
assert.equal(save.ui.confirmation, 'save');
assert.deepEqual(save.commands, []);
assert.deepEqual(
  Raw.transition(save.ui, { ...table, dirty: true }, { type: 'confirm' })
    .commands,
  [{ type: 'save' }]
);
assert.equal(cellText({ key: null }, 'id'), 'DEFAULT');
assert.equal(cellText({ key: undefined }, 'id'), 'DEFAULT');
assert.equal(
  Raw.cellTransition(Raw.cellInitial({}), { readonly: true }, { type: 'apply' })
    .commands.length,
  0
);
assert.equal(
  Raw.cellTransition(
    Raw.cellInitial({}),
    { newRow: false },
    { type: 'mode', value: 'default' }
  ).ui.mode,
  'value'
);
const sidebar = {
  ready: true,
  canWrite: true,
  canLoad: true,
  entry: { title: 'Original' },
  selected: 0,
  entries: [{ index: 0 }],
  xml: '<element/>'
};
ui = Sidebar.transition(Sidebar.initial(), sidebar, {
  type: 'text',
  field: 'title',
  value: 'Draft'
}).ui;
assert(Sidebar.pending(ui));
assert.equal(sidebar.entry.title, 'Original');
ui = Sidebar.transition(ui, sidebar, {
  type: 'text',
  field: 'title',
  value: 'Original'
}).ui;
assert(!Sidebar.pending(ui));
ui = Sidebar.transition(ui, sidebar, {
  type: 'xml',
  value: '<element broken'
}).ui;
assert(Sidebar.pending(ui));
assert.equal(
  Sidebar.transition(ui, sidebar, { type: 'mode', value: 'simple' }).commands[0]
    .type,
  'mode'
);
assert(
  !Sidebar.pending(Sidebar.transition(ui, sidebar, { type: 'applied' }).ui)
);
assert.deepEqual(
  Sidebar.transition(
    ui,
    { ...sidebar, uncertain: true },
    { type: 'field', field: 'name', value: 'retry' }
  ).commands,
  []
);
ui = Sidebar.transition(Sidebar.initial(), sidebar, { type: 'delete' }).ui;
assert.equal(ui.confirmation, 'delete');
assert.deepEqual(
  Sidebar.transition(ui, sidebar, { type: 'confirm' }).commands,
  [{ type: 'delete' }]
);
assert.throws(
  () => Sidebar.transition(Sidebar.initial(), sidebar, { type: 'unknown' }),
  /Unsupported/
);
assert.equal(
  Sidebar.completed(ui, { type: 'help' }).confirmation,
  ui.confirmation
);
const buffered = {
  ...Sidebar.initial(),
  xml: '<element broken',
  treeWidth: 430
};
assert.equal(Sidebar.completed(buffered, { type: 'help' }).xml, buffered.xml);
assert.equal(Sidebar.completed(buffered, { type: 'reload' }).treeWidth, 430);
const columnModel = {
  ...sidebar,
  elements: [
    { name: 'code', path: '0/0' },
    { name: 'title', path: '0/1' }
  ],
  element: { name: 'title', path: '0/1', title: 'Title', width: 160 }
};
assert.equal(
  Columns.selected(Columns.initial(), columnModel.elements, 'title').path,
  '0/1'
);
assert.equal(
  Columns.completed(Columns.initial(), { type: 'filter' }, columnModel).path,
  '0/1'
);
assert.equal(
  Columns.transition(Columns.initial(), columnModel, {
    type: 'step',
    value: -999
  }).commands[0].value,
  48
);
assert.equal(
  Columns.transition(Columns.initial(), columnModel, {
    type: 'step',
    value: 999
  }).commands[0].value,
  640
);
assert.deepEqual(
  Columns.transition(Columns.initial(), columnModel, {
    type: 'move',
    value: -1
  }).commands,
  [{ type: 'change', field: 'move', value: -1, name: 'title' }]
);
assert.deepEqual(
  Columns.transition(Columns.initial(), columnModel, { type: 'move', value: 1 })
    .commands,
  []
);
assert.deepEqual(
  Columns.transition(
    { ...Columns.initial(), text: { title: 'Draft' } },
    columnModel,
    { type: 'move', value: -1 }
  ).commands,
  []
);
assert.deepEqual(
  Columns.transition(
    Columns.initial(),
    { ...columnModel, uncertain: true },
    { type: 'move', value: -1 }
  ).commands,
  []
);
assert.equal(
  Columns.completed(
    Columns.initial(),
    { type: 'change', field: 'move', name: 'title' },
    {
      ...columnModel,
      elements: [
        { name: 'title', path: '0/0' },
        { name: 'code', path: '0/1' }
      ]
    }
  ).path,
  '0/0'
);
console.log(
  'Shared Administration state: save/drop identity guards, readonly/default cells, Sidebar buffers and unknown-write lock passed.'
);

const Admin = await import(
  '../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs'
);
const Config = await import(
  '../../src/tactic_stream/shared_ui/features/configuration/configuration.ui.mjs'
);
for (const width of [1100, 1400, 1800]) {
  const admin = Admin.describe(
    { section: 'layouts', project: 'demo', projects: [] },
    { collapsed: false },
    width,
    900,
    'en'
  );
  const config = Config.describe(
    { page: 'appearance', product: 'TACTIC STREAM' },
    width,
    900,
    'en'
  );
  const head = admin.nodes.find((node) => node.id === 'administrationHeader');
  const reference = config.nodes.find(
    (node) => node.id === 'configurationHeader'
  );
  for (const field of [
    'x',
    'y',
    'width',
    'height',
    'background',
    'radius',
    'titlebar',
    'chromeRight',
    'chromeTop',
    'chromeHeight'
  ])
    assert.equal(head[field], reference[field], field + ' window header');
  const toolbar = head.children.find(
    (node) => node.id === 'administrationToolbar'
  );
  assert(
    toolbar.x + toolbar.width <= width - head.chromeRight - 80,
    'Commands leave window controls their own space'
  );
  assert(
    head.children.find((node) => node.id === 'administrationSectionTitle')
      .width >= 200,
    'The section title remains readable'
  );
}

const sources = [
  {
    code: 'TABLE',
    searchType: 'vfx/asset',
    view: 'table',
    columns: [{ name: 'submit' }]
  },
  {
    code: 'INPUT',
    searchType: 'vfx/asset',
    view: 'edit_definition',
    columns: [{ name: 'code', widget: 'TextWdg' }]
  },
  {
    code: 'DISPLAY',
    searchType: 'vfx/asset',
    view: 'definition',
    columns: [{ name: 'submit', widget: 'SubmissionLinkTableElement' }]
  },
  {
    code: 'CUSTOM',
    searchType: 'vfx/asset',
    view: 'planner',
    columns: [{ name: 'submit', widget: 'custom.Wdg' }]
  }
];
const focus = { searchType: 'vfx/asset', view: 'table', column: 'submit' };
assert.equal(
  Columns.definitionSource(sources, focus, (row) => row.columns).code,
  'DISPLAY'
);
assert.equal(
  Columns.definitionSource(
    sources,
    { ...focus, view: 'planner' },
    (row) => row.columns
  ).code,
  'CUSTOM'
);
assert.equal(
  Columns.definitionSource(
    sources,
    { ...focus, column: 'missing' },
    (row) => row.columns
  ),
  null
);
assert.equal(
  Columns.definitionSource(
    sources,
    { ...focus, view: 'edit_definition', column: 'code' },
    (row) => row.columns
  ).code,
  'INPUT'
);
assert.equal(
  Columns.definitionSource(
    sources,
    { ...focus, column: '' },
    (row) => row.columns
  ).code,
  'TABLE'
);
