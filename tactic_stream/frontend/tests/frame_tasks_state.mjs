import assert from 'node:assert/strict';
import {
  pending,
  surfaces,
  toolbar,
  options
} from '../../src/tactic_stream/shared_ui/features/tasks/workspace.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Table from '../../src/tactic_stream/shared_ui/features/tasks/table.ui.mjs';
import * as Process from '../../src/tactic_stream/shared_ui/features/tasks/process.ui.mjs';
import * as Cells from '../../src/tactic_stream/shared_ui/features/tasks/cells.ui.mjs';
import * as Summary from '../../src/tactic_stream/shared_ui/features/tasks/summary.ui.mjs';
import * as Empty from '../../src/tactic_stream/shared_ui/features/tasks/empty.ui.mjs';
import * as Menus from '../../src/tactic_stream/shared_ui/features/tasks/menus.ui.mjs';

for (const language of ['en', 'ru']) {
  for (const width of [320, 520, 880, 1440]) {
    for (const saving of [false, true]) {
      const scene = pending(
        { count: 3, saving, blocked: saving, preview: true, rebase: true },
        width,
        language
      );
      validateScene(scene);
      const save = scene.nodes.find((node) => node.id === 'taskSave');
      const discard = scene.nodes.find((node) => node.id === 'taskDiscard');
      assert.equal(save.enabled, !saving);
      assert.equal(discard.enabled, !saving);
      assert(discard.x + discard.width <= save.x);
      for (const node of scene.nodes) {
        assert(node.x >= 0 && node.x + node.width <= width, node.id);
      }
      const switcher = surfaces(
        { value: 'compact', disabled: saving },
        108,
        language
      );
      validateScene(switcher);
      assert.deepEqual(
        switcher.nodes[0].options.map((option) => option.value),
        ['cards', 'compact', 'workspace']
      );
      assert.equal(switcher.nodes[0].enabled, !saving);
    }
  }
}
const blocked = pending({ count: 1, saving: false, blocked: true }, 320, 'en');
assert.equal(
  blocked.nodes.find((node) => node.id === 'taskSave').enabled,
  false
);
assert.equal(
  blocked.nodes.find((node) => node.id === 'taskDiscard').enabled,
  true
);
assert(
  blocked.nodes
    .find((node) => node.id === 'taskPendingCount')
    .text.includes('1 task has')
);
console.log(
  'PASS task pending/surface states: EN/RU, narrow/wide, saving and unknown-write guards'
);

const columns = [
  { key: 'object', width: 210, visible: true },
  { key: 'status', width: 138, visible: true },
  { key: 'assigned', width: 154, visible: true },
  { key: 'dates', width: 112, visible: true },
  { key: 'bid_duration', width: 86, visible: true },
  { key: 'milestone_code', width: 132, visible: true }
];
for (const width of [320, 600, 880, 1440]) {
  const web = Table.layout(columns, width);
  const native = Table.layout(
    columns.map((column) => ({ ...column, key: Table.key(column.key) })),
    width
  );
  const geometry = (layout) =>
    layout.cells.map(({ key, x, width }) => ({ key, x, width }));
  assert.deepEqual(geometry(web), geometry(native));
  assert.equal(
    web.cells.some((cell) => cell.key === 'assignee'),
    width >= 520
  );
  assert.equal(
    web.cells.some((cell) => cell.key === 'hours'),
    width >= 900
  );
  for (let index = 1; index < web.cells.length; index++) {
    assert(
      web.cells[index - 1].x + web.cells[index - 1].width <= web.cells[index].x
    );
  }
  assert(
    web.cells.at(-1).x + web.cells.at(-1).width + Table.metrics.actions <=
      web.width
  );
}
const reordered = Table.layout(
  [columns[2], { ...columns[1], visible: false }, columns[0]],
  880
);
assert.deepEqual(
  reordered.cells.map((cell) => cell.key),
  ['assignee', 'object']
);
for (const avatar of [false, true]) {
  const scene = Cells.choice(
    { text: 'Artist', avatar, enabled: true },
    140,
    29
  );
  validateScene(scene, {}, avatar ? { avatar: true } : {});
  const text = scene.nodes.find(
    (node) => node.id === 'taskTableCellDisplayLabel'
  );
  assert.equal(text.x, avatar ? 40 : 11);
}
console.log(
  'PASS task table aliases, responsive columns, order, bounds and idle cell alignment'
);

for (const language of ['en', 'ru'])
  for (const width of [272, 320, 380, 520, 720, 800, 1180, 1360, 1600]) {
    for (const phone of [false, true]) {
      const scene = toolbar(
        {
          phone,
          scopeLabel: 'PROJECT',
          scope: 'project',
          scopeChoices: [],
          sortOptions: [],
          groupOptions: [],
          filtersActive: true
        },
        width,
        language
      );
      validateScene(scene, {}, { search: true, surfaces: true });
      const controls = scene.nodes
        .filter(
          (node) =>
            ['View', 'Button', 'Choice', 'Segmented'].includes(node.kind) &&
            node.visible !== false
        )
        .sort((a, b) => a.x - b.x);
      for (const control of controls) {
        assert(
          control.x >= 0 && control.x + control.width <= width,
          width + ':' + control.id
        );
        assert(
          control.y >= 0 && control.y + control.height <= scene.height,
          control.id
        );
      }
      for (let i = 1; i < controls.length; i++)
        assert(
          controls[i - 1].x + controls[i - 1].width <= controls[i].x + 0.01,
          width + ':' + controls[i].id
        );
    }
    const geometry = Table.layout(columns, width),
      segments = Table.segments(geometry, false);
    assert.equal(
      segments.reduce((sum, cell) => sum + cell.width, 0),
      geometry.width
    );
    const model = {
      code: 'T1',
      title: 'Robot',
      process: 'model',
      processLabel: 'Model',
      notes: 3,
      progress: 43,
      start: '2030-01-01',
      end: '2030-01-04',
      hoursLabel: '1 / 2 h'
    };
    for (const expanded of [false, true]) {
      const scene = Table.row({ ...model, expanded }, geometry, language);
      assert.equal(
        scene.nodes.find((node) => node.id === 'taskRowAction').opacity,
        0.35
      );
      for (const flag of ['hovered', 'active', 'dirty', 'busy', 'actionAlert'])
        assert.equal(
          Table.row(
            { ...model, expanded, [flag]: true },
            geometry,
            language
          ).nodes.find((node) => node.id === 'taskRowAction').opacity,
          1,
          flag + ' keeps the task row action visible'
        );
      const views = Object.fromEntries(
        scene.nodes
          .filter((node) => node.kind === 'View')
          .map((node) => [node.view, true])
      );
      validateScene(scene, {}, views);
      const segmented = Table.segments(geometry, expanded).flatMap(
        (segment) => Table.slice(scene, segment).nodes
      );
      for (const node of scene.nodes.filter(
        (node) =>
          !node.id.startsWith('taskRowSurface_') &&
          node.id !== 'taskRowSeparator'
      ))
        assert.equal(
          segmented.filter((item) => item.id === node.id).length,
          1,
          'cell slicing preserves ' + node.id
        );
    }
  }
console.log(
  'PASS task toolbar bounds, table row actions and semantic HTML cell slicing in EN/RU'
);

const grouped = Table.layout(
  [
    {
      key: 'object',
      label: 'Object',
      width: 210,
      group: 'object',
      sort: 'object'
    }
  ],
  900
);
assert.equal(
  grouped.cells[0].group,
  'object',
  'Header context retains the source column grouping action'
);

for (const mode of ['cards', 'compact'])
  for (const dirty of [false, true])
    for (const deleting of [false, true]) {
      const model = {
        label: 'Model',
        count: 2,
        dirty,
        deleting,
        hasTask: true,
        hasTarget: true,
        notes: 3
      };
      const scene = Process.describe(
        model,
        mode === 'cards' ? 217 : Process.minimumWidth(model),
        mode,
        'ru'
      );
      validateScene(scene, {}, { status: true, assigned: true });
      if (dirty)
        assert.equal(
          scene.nodes.find((node) => node.id === 'taskProcess_save').enabled,
          true,
          'A staged deletion can still be saved'
        );
      assert.equal(
        scene.nodes.find((node) => node.id === 'taskProcess_notes').enabled,
        !deleting
      );
      for (const node of scene.nodes)
        assert(
          node.x >= 0 &&
            node.y >= 0 &&
            node.x + node.width <=
              (mode === 'cards' ? 217 : Process.minimumWidth(model)) &&
            node.y + node.height <= scene.height,
          node.id
        );
    }
console.log(
  'PASS quick task cards/compact, dirty state and staged-deletion Save guard'
);

const Scope = await import(
  '../../src/tactic_stream/shared_ui/features/tasks/scope.ui.mjs'
);
const Filters = await import(
  '../../src/tactic_stream/shared_ui/features/tasks/filters.ui.mjs'
);
const Editor = await import(
  '../../src/tactic_stream/shared_ui/features/tasks/editor.ui.mjs'
);
assert.equal(
  Scope.actions({ scope: 'user', personal: false }, 'en').find(
    (row) => row.value === 'user'
  ).checked,
  false
);
assert.equal(
  Scope.actions(
    {
      scope: 'search_type',
      searchTypeTitle: 'Assets',
      searchTypeAvailable: false
    },
    'ru'
  ).find((row) => row.value === 'search_type').enabled,
  false
);
assert.equal(
  Scope.describe(
    { scope: 'team', teams: [{ value: 'team', label: 'Team' }], radius: 8 },
    270,
    'en'
  ).nodes.find((row) => row.id === 'taskScopeIdentity').kind,
  'Choice'
);
const filterGroups = Filters.fromFacets(
  {
    process: [{ key: 'model', title: 'MODEL', count: 4 }],
    preset: { mine: 4 }
  },
  { process: ['model', 'archived'] },
  'project'
);
assert.equal(
  filterGroups
    .find((row) => row.key === 'process')
    .options.find((row) => row.key === 'archived').count,
  0
);
for (const language of ['en', 'ru'])
  for (const width of [220, 280, 416, 540]) {
    const scene = Filters.describe(
      { groups: filterGroups, filters: { hasNotes: true }, advanced: true },
      width,
      language,
      (text) => text.length * 7
    );
    assert.equal(
      scene.nodes.find((row) => row.id === 'taskFilterNotes').checked,
      true
    );
    for (const item of scene.nodes)
      assert.ok(item.x >= 0 && item.x + item.width <= width, item.id);
    const fields = [
      'status',
      'assigned',
      'bid_start_date',
      'bid_end_date',
      'description'
    ].map((name) => ({ name, editable: true }));
    const editor = Editor.describe(
      { fields, bulk: true, enabled: ['status'] },
      width,
      language
    );
    assert.equal(
      editor.nodes.find((row) => row.id === 'taskEditorValue_status').enabled,
      true
    );
    assert.equal(
      editor.nodes.find((row) => row.id === 'taskEditorValue_assigned').enabled,
      false
    );
    for (const item of editor.nodes)
      assert.ok(item.x >= 0 && item.x + item.width <= width, item.id);
  }

const Bulk = await import(
  '../../src/tactic_stream/shared_ui/features/tasks/bulk.ui.mjs'
);
for (const width of [220, 272, 320, 380, 520, 760, 1400]) {
  const scene = Bulk.bar(
    { count: 2, enabled: ['status'], canApply: true },
    width,
    'en'
  );
  for (const node of scene.nodes)
    assert.ok(
      node.x >= 0 && node.x + node.width <= width,
      node.id + ' ' + width
    );
}
const plan = {
  task: { status: 'Ready', assigned: 'a', description: 'before' },
  fields: [
    { name: 'status', editable: true },
    { name: 'description', editable: true }
  ],
  statusChoices: [{ value: 'Ready' }],
  users: [{ value: 'a' }],
  catalog: { priorityChoices: [], milestoneChoices: [] }
};
const form = Bulk.prepare([
  plan,
  { ...plan, task: { ...plan.task, status: 'Other' } }
]);
form.enabled = ['status'];
assert.equal(
  Bulk.preview(form).invalid,
  2,
  'Mixed input requires an explicit value'
);
form.set = ['status'];
assert.equal(Bulk.preview(form).eligible, 1);
form.values.status = 'Removed';
assert.equal(
  Bulk.preview(form).invalid,
  2,
  'Removed statuses cannot be applied'
);
console.log(
  'PASS scope, quick/advanced filters, opt-in editors and bulk geometry/validation'
);

for (const width of [220, 280, 416])
  for (const toolbarWidth of [272, 520, 900, 1400]) {
    const scene = options(
      {
        toolbarWidth,
        pageSize: 50,
        view: 'table',
        sortOptions: [],
        groupOptions: []
      },
      width,
      'en'
    );
    const actions = scene.nodes.map((node) => node.action?.type);
    for (const type of [
      'mode',
      'page-size',
      'scope',
      'filters',
      'columns',
      'calendar'
    ])
      assert.ok(actions.includes(type), type);
    for (const node of scene.nodes)
      assert.ok(node.x >= 0 && node.x + node.width <= width, node.id);
  }

for (const language of ['en', 'ru'])
  for (const width of [272, 520, 1000, 1600]) {
    for (const management of [false, true]) {
      const scene = Summary.describe(
        { management, loaded: 24, total: 24, complete: true },
        width,
        language
      );
      validateScene(scene, {}, { presets: {}, workload: {}, statuses: {} });
      assert.equal(
        scene.nodes.some((node) => node.view === 'workload'),
        management
      );
    }
    const empty = Empty.describe({ canCreate: false }, width, 300, language);
    validateScene(empty);
    assert.equal(
      empty.nodes.some((node) => node.id === 'taskWorkspaceEmptyArrow'),
      false
    );
    const creating = Empty.describe(
      { canCreate: true, target: { x: 24, y: -14 } },
      width,
      300,
      language
    );
    validateScene(creating, {}, { arrow: {} });
    assert(
      creating.nodes.some((node) => node.id === 'taskWorkspaceEmptyArrow')
    );
    const filtered = Empty.describe(
      { canCreate: true, filtered: true, target: { x: 24, y: -14 } },
      width,
      300,
      language
    );
    assert(
      !filtered.nodes.some((node) => node.id === 'taskWorkspaceEmptyArrow')
    );
  }
for (const pending of [false, true]) {
  const row = Menus.row({
    dirty: pending,
    pending,
    busy: false,
    hasTask: true,
    inspector: true,
    timesheet: true,
    checked: 2
  });
  assert.equal(row.find((row) => row.command === 'delete').enabled, !pending);
  assert.equal(
    row.some((row) => row.command === 'discard'),
    pending
  );
  assert(row.some((row) => row.command === 'inspect'));
  assert(row.some((row) => row.command === 'timesheet'));
}
const required = Menus.column({
  column: { key: 'object', required: true, sort: 'object', group: 'object' },
  group: 'none'
});
assert.equal(required.find((row) => row.command === 'hide').enabled, false);
assert.equal(required.find((row) => row.command === 'ungroup').enabled, false);
console.log(
  'PASS task summary, empty Create guidance, row mutation guards and required-column menu'
);

const emptyRu = Empty.describe({ canCreate: true }, 900, 400, 'ru');
assert.equal(
  emptyRu.nodes.find((node) => node.id === 'taskWorkspaceEmptyTitle').text,
  'Создайте задачу'
);
assert.equal(
  emptyRu.nodes.find((node) => node.id === 'taskWorkspaceEmptyHint').text,
  'Используйте кнопку + выше'
);

for (const width of [152, 184, 220, 240, 256, 420]) {
  const scene = Editor.describe(
    { fields: [], live: true, staging: true },
    width,
    'ru'
  );
  const close = scene.nodes.find((node) => node.id === 'taskEditorCancel'),
    apply = scene.nodes.find((node) => node.id === 'taskEditorApply');
  for (const node of [close, apply])
    assert(node.x >= 0 && node.x + node.width <= width);
  assert(
    close.x + close.width <= apply.x || close.y + close.height <= apply.y,
    'Narrow draft actions must not overlap'
  );
}
const emptyNarrow = Empty.describe(
  { canCreate: false, filtered: true },
  272,
  300,
  'ru'
);
assert(
  emptyNarrow.nodes.find((node) => node.id === 'taskWorkspaceEmptyTitle').wrap
);

assert.equal(Cells.initials('Not assigned'), 'NA');
assert.equal(Cells.initials('John Michael Doe'), 'JM');
assert.equal(Cells.initials(''), '?');
