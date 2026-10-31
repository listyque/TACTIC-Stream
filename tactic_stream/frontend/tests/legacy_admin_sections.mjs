import assert from 'node:assert/strict';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs';
import * as Sidebar from '../../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.ui.mjs';
import * as SidebarState from '../../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.state.mjs';

const model = {
  section: 'groups',
  project: 'demo',
  projects: [],
  locked: false,
  busy: false,
  drafts: [],
  streamApi: false
};
const unavailable = ['dashboards', 'layouts', 'plugins'];
const ids = UI.availableSections(model).map((row) => row.id);
for (const id of unavailable) assert(!ids.includes(id));
for (const id of [
  'groups',
  'users',
  'rules',
  'raw',
  'columns',
  'sidebar',
  'workflow'
])
  assert(ids.includes(id));
for (const streamApi of [true, undefined])
  assert.deepEqual(UI.availableSections({ ...model, streamApi }), UI.sections);

function nodes(scene) {
  return scene.flatMap((item) => [item, ...nodes(item.children || [])]);
}
for (const width of [700, 1400])
  for (const collapsed of [false, true]) {
    const scene = UI.describe(model, { collapsed }, width, 900, 'en');
    const all = nodes(scene.nodes);
    assert(all.length > 0);
    for (const id of unavailable)
      assert(!all.some((node) => node.id === 'adminSection_' + id));
    const picker = all.find(
      (node) => node.id === 'administrationSectionSelector'
    );
    if (width < 1000) {
      assert(picker);
      assert.deepEqual(
        picker.options.map((row) => row.value),
        ids
      );
    }
  }
for (const streamApi of [true, false]) {
  const scene = Sidebar.describe(
    {
      ready: true,
      canWrite: true,
      canLoad: true,
      selected: 0,
      entries: [{ index: 0 }],
      groups: [],
      streamApi,
      typeOptions: [],
      presetOptions: [],
      resultOptions: [],
      layoutOptions: [],
      shelfOptions: [],
      entry: {
        name: 'review',
        entryType: 'link',
        widgetType: 'custom_layout',
        displayView: 'dashboard.review'
      }
    },
    SidebarState.initial(),
    1400,
    1100,
    'en'
  );
  assert.equal(JSON.stringify(scene).includes('sidebarEditPage'), streamApi);
}
console.log(
  'PASS: Legacy administration keeps native sections and excludes Stream layouts in both engines'
);
