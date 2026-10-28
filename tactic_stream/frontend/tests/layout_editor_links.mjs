import assert from 'node:assert/strict';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as Links from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.links.mjs';
import * as Admin from '../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs';
import * as AdminState from '../../src/tactic_stream/shared_ui/features/administration/administration.state.mjs';
const catalog = [
  { identity: 'work', label: 'Work' },
  { identity: 'report', label: 'Report' }
];
const document = {
  name: 'work',
  blocks: [
    {
      kind: 'column',
      search_type: 'demo/asset',
      children: [
        { kind: 'items', search_type: 'demo/asset', view: 'hub_items' },
        { kind: 'table', search_type: 'demo/asset', view: 'production' },
        {
          kind: 'link',
          href: '/projects/demo/dashboard/report',
          text: 'Report'
        }
      ]
    }
  ]
};
let ui = { ...State.initial(), collapsed: ['page', '0'] };
const raw = {
  document,
  project: 'demo',
  origin: 'https://server.test',
  catalog,
  canWrite: true,
  checked: true,
  dataSource: {}
};
const flatten = (scene) =>
  scene.nodes.flatMap((node) => [
    node,
    ...flatten({ nodes: node.children || [] })
  ]);
for (const [key, type, view] of [
  ['0.0', 'card', 'hub_items'],
  ['0.1', 'columns', 'production']
]) {
  ui = State.transition(ui, UI.model(raw, ui), {
    type: 'selection',
    keys: [key]
  }).ui;
  assert.deepEqual(ui.collapsed, []);
  const model = UI.model(raw, ui);
  assert(UI.models(model, ui).pageBlocks.some((row) => row.key === key));
  const row = UI.row(
    { width: 180, source: 'pageBlocks' },
    model.layers.find((row) => row.key === key),
    model,
    ui,
    'en'
  );
  assert(row.nodes[0].selected);
  for (const language of ['en', 'ru'])
    for (const width of [360, 1000, 1400]) {
      const local = { ...ui, panel: 'properties' };
      const nodes = flatten(UI.describe(model, local, width, 800, language));
      const choice = nodes.find((node) => node.id === 'pageProperty_view');
      const action = nodes.find((node) => node.id === 'pageProperty_viewOpen');
      assert(action && choice && action.x >= choice.x + choice.width + 6);
      assert.deepEqual(action.action, { type });
      assert(!nodes.some((node) => node.id === 'pageEditCard'));
    }
  assert.deepEqual(State.transition(ui, model, { type }).commands, [
    { type, searchType: 'demo/asset', view }
  ]);
}
ui = State.transition(ui, UI.model(raw, ui), {
  type: 'selection',
  keys: ['0.2']
}).ui;
assert.deepEqual(
  State.transition(ui, UI.model(raw, ui), { type: 'linkedPage' }).commands,
  [{ type: 'linkedPage', name: 'report' }]
);
assert.deepEqual(
  State.transition(ui, UI.model({ ...raw, dirty: true }, ui), {
    type: 'linkedPage'
  }).commands,
  []
);
for (const value of [
  '/dashboard/report',
  '/projects/demo/dashboard/report?mode=edit',
  'https://server.test/projects/demo/dashboard/report'
])
  assert.equal(
    Links.target(value, 'demo', 'https://server.test', catalog),
    'report'
  );
for (const value of [
  '/projects/other/dashboard/report',
  'https://foreign.test/dashboard/report',
  '//server.test/dashboard/report',
  'javascript:alert(1)',
  '/dashboard/missing',
  '/dashboard/%zz',
  '/dashboard/report\n',
  '/dashboard/%2Freport'
])
  assert.equal(Links.target(value, 'demo', 'https://server.test', catalog), '');
const context = Links.context({
  ...ui,
  text: { secret: 'draft' },
  past: [document]
});
assert(!('text' in context) && !('past' in context));
assert.equal(context.selected, '0.2');
const parent = { name: 'work', title: 'Work' };
const adminModel = { section: 'layouts', layoutParent: parent, projects: [] };
assert(
  flatten(
    Admin.describe(adminModel, AdminState.initial(), 1400, 900, 'ru')
  ).some((node) => node.id === 'adminReturnToLayout')
);
assert.deepEqual(
  AdminState.transition(AdminState.initial(), adminModel, {
    type: 'return-layout'
  }).commands,
  [{ type: 'return-layout' }]
);
assert.deepEqual(
  AdminState.transition(
    AdminState.initial(),
    { section: 'layouts' },
    { type: 'return-layout' }
  ).commands,
  []
);
console.log(
  'Layout references: source scope, adjacent links, page boundary, tree reveal and safe view context pass'
);
