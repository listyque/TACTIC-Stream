import assert from 'node:assert/strict';
import * as Editor from '../../src/tactic_stream/shared_ui/features/scripts/editor.ui.mjs';
import * as Shelf from '../../src/tactic_stream/shared_ui/features/scripts/shelf.ui.mjs';
import * as Bar from '../../src/tactic_stream/shared_ui/features/scripts/bar.ui.mjs';
import * as Source from '../../src/tactic_stream/shared_ui/features/scripts/source.ui.mjs';
import { changedFields } from '../../src/tactic_stream/shared_ui/features/tools/database.ui.mjs';
import { translate } from '../../src/tactic_stream/shared_ui/core/strings.mjs';

const editor = {
  canEdit: true,
  editable: true,
  source: 'print(1)',
  native: true,
  tabCount: 1
};
const picker = Shelf.scriptPicker(
  {
    id: 'shelfScript',
    width: 240,
    height: 32,
    record: { script: 'tools/save' },
    enabled: false
  },
  'ru'
).nodes[0];
assert.equal(picker.id, 'shelfScript_trigger');
assert.equal(picker.text, 'tools/save');
assert.equal(picker.icon, 'account-tree');
assert.equal(picker.enabled, false);
assert.equal(picker.width, 240);
assert.equal(
  Shelf.scriptPicker(
    { id: 'empty', width: 240, height: 32, record: {}, enabled: true },
    'ru'
  ).nodes[0].text,
  'Выберите скрипт'
);
assert.equal(Source.toolbarHeight(529), 42);
assert.equal(Source.toolbarHeight(530), 30);
assert(Editor.commands(editor).run);
for (const state of [
  { busy: true },
  { running: true },
  { editable: false },
  { source: '   ' }
])
  assert.equal(Editor.commands({ ...editor, ...state }).run, false);
assert.equal(Editor.commands({ ...editor, uncertain: true }).save, false);
assert.equal(Editor.commands({ ...editor, native: false }).triggers, false);
for (const width of [320, 360, 720, 1100]) {
  const bounds = Editor.layout(editor, width, 600);
  assert(bounds.main.x >= 0 && bounds.main.width > 0);
  assert(bounds.main.x + bounds.main.width <= width);
  assert(bounds.source.height >= 90);
}
const shelf = { canWrite: true, ready: true, existing: true, dirty: true };
assert(Shelf.permissions(shelf).save);
for (const state of [
  { busy: true },
  { running: true },
  { contextChanged: true },
  { uncertain: true },
  { canWrite: false }
]) {
  assert.equal(Shelf.permissions({ ...shelf, ...state }).save, false);
  assert.equal(Shelf.permissions({ ...shelf, ...state }).edit, false);
}
assert.equal(
  Shelf.permissions({ ...shelf, dirty: false, assignmentPending: true }).assign,
  true
);
assert.equal(
  Shelf.permissions({ ...shelf, assignmentPending: true }).assign,
  false
);
assert.equal(Bar.actionHeight(10, 200), 36);
assert.equal(Bar.actionHeight(2, 200), 40);
for (const language of [
  'local_python',
  'dcc_python',
  'python',
  'server_js',
  'javascript'
]) {
  const runtime = Bar.scriptRuntime(language, 'en');
  const action = Bar.action(
    {
      buttonId: language,
      title: 'Run',
      script: 'tools/run',
      language,
      available: language !== 'local_python'
    },
    false,
    'en'
  ).nodes[0];
  const marker = action.children.find(
    (child) => child.id === 'scriptShelfRuntime'
  );
  assert.equal(
    marker.visible,
    language === 'local_python' || language === 'dcc_python'
  );
  assert(action.toolTip.startsWith(runtime.label + '\n'));
  const icon = action.children.find(
    (child) => child.id === 'scriptShelfActionIcon'
  );
  if (marker.visible) assert(icon.x + icon.width <= marker.x);
}
assert.equal(Bar.scriptRuntime('local_python', 'ru').label, 'Только в ТХ');
assert.equal(Bar.scriptRuntime('python', 'ru').label, 'Серверный Python');
assert.deepEqual(Bar.scriptRuntime(undefined, 'en'), {
  label: '',
  handlerOnly: false
});
const absent = Bar.describe({ dcc: false, count: 0 }, 500, 48, 'en').nodes.find(
  (node) => node.id === 'exportDccShelfButton'
);
assert.equal(absent.visible, false);
assert.equal(
  Bar.action({ buttonId: 'old', title: 'Old', available: false }, false, 'en')
    .nodes[0].enabled,
  false
);
const draft = { description: 'draft' };
assert.deepEqual(changedFields(draft, 'name', 'A', 'B'), {
  description: 'draft',
  name: 'B'
});
assert.deepEqual(
  changedFields({ ...draft, name: 'B' }, 'name', 'A', 'A'),
  draft
);
assert.deepEqual(draft, { description: 'draft' });
assert.equal(
  translate('Edit script shelf', 'ru'),
  'Редактировать шелф скриптов'
);
console.log(
  'PASS scripts: execution guards, desktop/phone bounds, shelf ownership/uncertain state, disabled actions and field draft reversion'
);
