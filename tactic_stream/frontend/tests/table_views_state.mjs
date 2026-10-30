import assert from 'node:assert/strict';
import * as UI from '../../src/tactic_stream/shared_ui/features/table/views.ui.mjs';
import * as Menus from '../../src/tactic_stream/shared_ui/features/table/menus.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const model = {
  project: 'demo',
  searchType: 'demo/asset',
  current: 'table',
  revision: 'r1',
  views: [
    { view: 'table', title: 'Default table', protected: true, columns: 4 },
    { view: 'artists', title: 'Artist workspace', protected: false, columns: 3 }
  ]
};
const ui = UI.loaded(UI.initial(), model);
assert.equal(UI.choices([{ view: 'th_table_light_filter' }]).length, 1);
assert.equal(
  UI.choices([
    { view: 'definition' },
    { view: 'edit' },
    { view: 'simple_filter' },
    { view: 'artists' }
  ]).length,
  1
);
assert.equal(
  Menus.viewActions(
    [{ view: 'definition' }, { view: 'table' }],
    true,
    'en'
  ).some((row) => row.command === 'select:0'),
  false
);
assert.equal(UI.transition(ui, model, { type: 'delete' }).ui.mode, '');
assert.equal(UI.rows(model, { ...ui, query: 'workspace' })[0].view, 'artists');
let next = UI.transition({ ...ui, selected: 'artists' }, model, {
  type: 'rename'
}).ui;
next = UI.transition(next, model, {
  type: 'title',
  value: 'Lighting review'
}).ui;
assert.deepEqual(UI.transition(next, model, { type: 'apply' }).command, {
  action: 'rename',
  view: 'artists',
  title: 'Lighting review',
  revision: 'r1'
});
for (const width of [320, 640, 960])
  for (const height of [360, 540, 650])
    for (const mode of ['', 'create', 'copy', 'rename', 'delete']) {
      validateScene(
        UI.describe(
          model,
          { ...ui, selected: 'artists', mode, title: 'Review' },
          width,
          height,
          'ru'
        ),
        { views: model.views }
      );
    }
console.log(
  'PASS: saved-view filtering, protected defaults, revisions and responsive manager scenes'
);
