import assert from 'node:assert/strict';
import { describe } from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs';
import { initial } from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs';

const entry = (name, kind, row, options, extra = {}) => ({
  name,
  kind,
  row,
  options,
  parent: '',
  when: [],
  variant: 'all',
  column: 1,
  span: 12,
  rows: 1,
  height: 22,
  ...extra
});
const sample = {
  kind: 'object',
  record: { status: 'Review', due: '2026-11-12 00:00:00', progress: 45 },
  task_count: 5
};
const layout = {
  flow: 'grid',
  collection: 'tree',
  columns: 12,
  gap: 4,
  elements: [
    entry('state', 'field', 1, {
      bind: 'record.status',
      format: 'badge',
      colors: '{"Review":"yellow"}'
    }),
    entry('date', 'field', 2, {
      bind: 'record.due',
      text: 'Due date',
      format: 'date'
    }),
    entry('progress', 'field', 3, {
      bind: 'record.progress',
      format: 'progress',
      color: 'green'
    }),
    entry('tasks', 'button', 4, {
      action: 'tasks',
      icon: 'task',
      badge: 'node.task_count'
    }),
    entry('notes', 'button', 5, {
      action: 'notes',
      text: 'Notes',
      badge: 'node.task_count'
    }),
    entry('body', 'group', 6, {
      fill: 'panel',
      stroke: 'outlineVariant',
      radius: '6'
    })
  ]
};
const flatten = (rows) =>
  rows.flatMap((row) => [row, ...flatten(row.children || [])]);
for (const width of [240, 320, 600]) {
  const scene = describe(
      layout,
      sample,
      width,
      '',
      'en',
      1000,
      '',
      'card',
      0,
      false
    ),
    nodes = flatten(scene.nodes);
  assert.equal(nodes.find((row) => row.kind === 'StatusChip').accent, 'yellow');
  assert.equal(
    nodes.find((row) => row.id === 'card_dateValue').text,
    '2026-11-12'
  );
  assert.equal(
    nodes.find((row) => row.id === 'card_progressValue').text,
    '45%'
  );
  const bar = nodes.find((row) => row.id === 'card_progressValue_progress');
  assert.equal(bar.background, 'green');
  assert.ok(bar.width > 0 && bar.width < width);
  const button = nodes.find((row) => row.id === 'card_tasksButton');
  assert.equal(button.width, button.height);
  assert.ok(button.width >= 30);
  assert.equal(button.badgeCount, 5);
  assert.equal(button.iconAction, true);
  assert.equal(button.badgeColor, 'contentAccent');
  const notes = nodes.find((row) => row.id === 'card_notesButton');
  assert.equal(notes.text, 'Notes · 5');
  assert.equal(notes.badgeCount, 0, 'A text action shows its count only once');
  assert.equal(
    nodes.find((row) => row.id === 'card_bodyGroup').background,
    'panel'
  );
  for (const row of scene.nodes) {
    for (const child of row.children || [])
      assert.ok(child.y + child.height <= row.height + 1, row.id);
  }
}
const compact = flatten(
  describe(
    {
      ...layout,
      elements: [
        { ...layout.elements.find((item) => item.name === 'notes'), span: 6 }
      ]
    },
    sample,
    240,
    '',
    'ru',
    1000,
    '',
    'card',
    0,
    false
  ).nodes
).find((item) => item.kind === 'Button');
assert.equal(compact.text, '5');
assert.equal(compact.label, 'Notes · 5');
assert.equal(compact.badgeCount, 0);
const element = (name, attributes = [], children = []) => ({
  type: 1,
  name,
  attributes,
  children
});
const tree = element(
  'config',
  [],
  [
    element(
      'cards',
      [['layout', 'sobject-layout']],
      [
        element(
          'element',
          [['name', 'state']],
          [element('display', [['class', 'field']])]
        )
      ]
    )
  ]
);
const colored = Document.edit(
  tree,
  'cards',
  'state',
  'valueColor:Review',
  'yellow'
);
assert.equal(
  Document.describe(colored, 'cards').elements[0].options.colors,
  '{"Review":"yellow"}'
);
assert.equal(
  Document.describe(tree, 'cards').elements[0].options.colors,
  undefined
);
assert.equal(
  Document.describe(
    Document.edit(colored, 'cards', 'state', 'valueColor:Review', ''),
    'cards'
  ).elements[0].options.colors,
  undefined
);
assert.throws(() =>
  Document.edit(tree, 'cards', 'state', 'valueColor:__proto__', 'red')
);
const ui = { ...initial(), selected: 'state', panel: 'settings' };
const invalidColors = Document.edit(
  tree,
  'cards',
  'state',
  'option:colors',
  '{'
);
assert.equal(
  Editor.model({ tree: invalidColors, view: 'cards' }, ui).layoutError,
  'Invalid field value colors',
  'An unfinished color map is an editable document error, not an editor crash'
);
const model = {
  ready: true,
  canWrite: true,
  canLoad: true,
  layout,
  view: 'cards',
  sampleItems: [sample],
  bindings: ['record.status'],
  searchTypes: [],
  configuration: { sources: [] }
};
const settings = flatten(Editor.describe(model, ui, 1500, 1000, 'ru').nodes);
assert.ok(
  settings
    .find((item) => item.id === 'layoutProperty_option_format')
    .options.some((option) => option.value === 'badge')
);
assert.ok(
  settings
    .find((item) => item.id === 'layoutProperty_valueColor_Review')
    .options.some((option) => option.value === 'yellow')
);
assert.equal(
  settings.find((item) => item.id === 'layoutProperty_valueColor_Review').action
    .field,
  'valueColor:Review'
);
console.log(
  'Item fields, value colors, card surfaces and accessible counted action geometry PASS'
);
