import assert from 'node:assert/strict';
import * as Host from '../../src/tactic_stream/shared_ui/features/table/host.ui.mjs';
import * as Columns from '../../src/tactic_stream/shared_ui/features/table/columns.mjs';
import * as Menus from '../../src/tactic_stream/shared_ui/features/table/menus.ui.mjs';
import * as Cells from '../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import * as Inline from '../../src/tactic_stream/shared_ui/features/table/inline.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const columns = [
  { name: 'name', title: 'Name', width: 160, hideOrder: 0, sortable: true },
  { name: 'notes', width: 160, hideOrder: 2 },
  { name: 'thumbnail', kind: 'thumbnail', width: 100, hideOrder: 1 }
];
for (const width of [0, 240, 800, 1600]) {
  for (const autoFit of [false, true]) {
    const scene = Host.describe(
      { columns, autoFit, automaticRowHeight: true },
      width
    );
    assert(scene.cells.every((cell) => cell.width >= 48 && cell.width <= 640));
    assert(scene.width >= width);
    assert(scene.rowHeight >= 58);
    assert.equal(Host.dropIndex(scene.cells, -1), 0);
    assert.equal(Host.dropIndex(scene.cells, 10000), scene.cells.length - 1);
    assert.equal(scene.columns[0].name, 'name');
  }
}
assert.equal(Host.boundedWidth(1000), 640);
assert.equal(Host.boundedWidth(0), 48);
for (const connection of [
  {
    name: 'connections',
    resolvedClass: 'pyasm.widget.sobject_browser_wdg.SObjectConnectionElement',
    displayOptions: { icon_size: '72' }
  },
  {
    name: 'connections',
    display: {
      handler: 'SObjectConnectionElement',
      options: { icon_size: '72' }
    }
  }
]) {
  assert.equal(
    Host.describe({ columns: [connection], automaticRowHeight: true }, 800)
      .rowHeight,
    104
  );
  assert.equal(
    Host.describe(
      { columns: [connection], automaticRowHeight: false, rowHeight: 52 },
      800
    ).rowHeight,
    52
  );
}
assert.equal(Columns.visibleColumns(columns, 200, {}).length, 1);
assert.equal(Cells.taskLayout(4, 220, 52).visible, 1);
assert.equal(Cells.taskLayout(4, 440, 52).visible, 4);
assert.equal(Cells.taskLayout(4, 440, 52).previewWidth, 440);
assert.equal(Cells.taskLayout(4, 220, 78).dates, true);
assert.equal(Cells.taskLayout(4, 220, 77).dates, false);
assert.equal(Cells.previewSize(40, 60), 32);
assert.equal(Cells.checked({ checked: false }, 'true'), false);
assert.equal(Cells.checked({}, 'yes'), true);
for (const value of [
  'javascript:alert(1)',
  'file:///secret',
  '//server',
  '/\\server',
  'https://a\n/'
]) {
  assert.equal(Cells.link(value), '', value);
}
assert.equal(
  Cells.link('/assets/file', 'https://example.com/tactic'),
  'https://example.com/assets/file'
);
assert.equal(Cells.link('/assets/file'), '/assets/file');
assert.equal(Cells.link('/assets/file', ''), '');
assert.equal(
  Cells.link('/assets/file', '127.0.0.1:9123/tactic'),
  'http://127.0.0.1:9123/assets/file'
);
assert.equal(Cells.link('/assets/file', 'file:///secret'), '');
assert.equal(Cells.link('/assets/file', 'https://user:secret@example.com'), '');
assert.deepEqual(Cells.completionGroups(4, 280, 58), {
  rowHeight: 18,
  gap: 4,
  contentHeight: 84,
  gutter: 16,
  width: 264
});
assert.equal(Cells.completionGroups(1, 280, 58).gutter, 0);
assert.equal(Cells.link('https://example.com/a'), 'https://example.com/a');
for (const language of ['en', 'ru']) {
  const actions = Menus.columnActions(
    { column: columns[0], count: 1, index: 0, group: 'none' },
    language
  );
  assert.equal(actions.find((row) => row.command === 'remove').enabled, false);
  assert.equal(actions.find((row) => row.command === 'left').enabled, false);
  assert.equal(actions.find((row) => row.command === 'right').enabled, false);
  const disabled = Menus.columnActions(
    { column: columns[0], count: 4, busy: true },
    language
  );
  assert.equal(
    disabled.find((row) => row.command === 'sort:ascending').enabled,
    false
  );
  assert.equal(
    disabled.find((row) => row.command === 'edit_definition').enabled,
    false
  );
  for (const width of [180, 300, 600]) {
    for (const mode of [
      'text',
      'multiline',
      'select',
      'user',
      'bool',
      'date',
      'datetime',
      'color',
      'multi',
      'time'
    ]) {
      for (const uncertain of [false, true]) {
        const scene = Inline.describe(
          {
            mode,
            title: 'Field',
            value: mode === 'multi' ? ['a'] : '',
            options: [
              { value: 'a', label: 'A' },
              { value: 'b', label: 'B' }
            ],
            count: 2,
            uncertain
          },
          width,
          language
        );
        validateScene(scene);
        assert(scene.height >= 36);
        assert.equal(
          scene.nodes.some((node) => node.id === 'tableInlineSave'),
          Inline.explicitSave(mode) || uncertain
        );
        if (uncertain)
          assert.equal(
            scene.nodes.find((node) => node.id === 'tableInlineSave').enabled,
            false
          );
        if (mode === 'multiline')
          assert.deepEqual(
            scene.nodes.find((node) => node.id === 'tableInlineValue').keys,
            {}
          );
      }
    }
  }
}
assert.deepEqual(Inline.change(['a'], { type: 'toggle', value: 'a' }), []);
assert.deepEqual(Inline.change(['a'], { type: 'toggle', value: 'b' }), [
  'a',
  'b'
]);
for (const width of [48, 100, 280]) {
  for (const height of [36, 52, 84]) {
    const tasks = Array.from({ length: 12 }, (_, index) => ({
      process: 'process' + index,
      status: 'Review'
    }));
    const scene = Cells.taskSummary(tasks, width, height);
    validateScene(scene);
    assert.equal(
      scene.nodes[0].children.filter((node) => node.kind === 'Action').length,
      12
    );
    assert.deepEqual(scene.nodes[0].children[11].action, {
      type: 'inspect',
      index: 11
    });
    validateScene(
      Cells.keyValues([{ title: 'Owner', value: 'admin' }], width, height, 'en')
    );
  }
}
assert.equal(
  Cells.text({ error: 'bad' }, '', 'en'),
  'Cell calculation failed: bad'
);
assert.equal(Cells.text({ text: { a: 1 } }, '', 'en'), '{"a":1}');
assert.equal(Cells.textRole({ urgency: 'critical' }), 'error');
assert.equal(Cells.text({ label: 'Exists' }, '', 'ru'), 'Есть');
assert.equal(Cells.text({ label: 'Does not exist' }, '', 'ru'), 'Отсутствует');
assert.equal(
  Cells.text({ label: 'Project does not exist' }, '', 'ru'),
  'Проект не существует'
);
assert.equal(Cells.textRole({ urgency: 'warning_1' }), 'yellow');
assert.equal(
  Cells.assigneeLabel({ assigned: '', assignedLabel: 'Not assigned' }, 'ru'),
  'Не назначено'
);
assert.equal(
  Cells.assigneeLabel({ assigned: 'admin', assignedLabel: 'Admin Name' }, 'ru'),
  'Admin Name'
);
console.log(
  'PASS: table layout, bounds, menus, workflow cards, safe links and typed inline scenes'
);

assert.deepEqual(
  Host.headerAction({
    resolvedClass: 'pyasm.widget.table_element_wdg.UpdateWdg',
    displayOptions: { insert_view: 'insert_review' }
  }),
  { type: 'insert', view: 'insert_review' }
);
assert.equal(
  Host.headerAction({
    resolvedClass: 'UpdateWdg',
    displayOptions: { insert: 'false' }
  }),
  null
);

const Nested = await import(
  '../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs'
);
const nestedModel = {
  selection: false,
  shelf: false,
  searchLimit: false,
  columns: [{ name: 'code', width: 160 }],
  rows: [{ key: 'A', cells: {}, record: {} }],
  children: { A: { open: true } }
};
const nestedRows = Nested.rows(nestedModel);
assert.equal(nestedRows[0].extent, Nested.rowHeight + Nested.height);
assert.equal(Nested.columns(nestedModel)[0].x, 0);
const nestedScene = Nested.describe(nestedModel, 320, 320, 'en');
assert.ok(
  !nestedScene.nodes.some((node) =>
    [
      'nestedFilter',
      'nestedReload',
      'nestedCreate',
      'nestedPrevious',
      'nestedNext',
      'nestedClearSelection'
    ].includes(node.id)
  )
);
validateScene(nestedScene, { rows: nestedRows });
assert.equal(
  Nested.identity({ searchType: 'x', parentKey: 'A' }),
  Nested.identity({ searchType: 'x', view: 'table', parentKey: 'A' })
);

const Connections = await import(
  '../../src/tactic_stream/shared_ui/features/table/connections.ui.mjs'
);
for (const iconSize of [16, 32, 60, 256]) {
  const cell = {
    iconSize,
    connectionRows: [
      {
        connectionKey: 'C',
        available: true,
        code: 'A',
        preview: {
          filename: 'asset.png',
          text: 'https://example.com/asset.png'
        }
      }
    ]
  };
  const list = Connections.describe(cell, 280, 300, 'en').nodes[0];
  const row = Connections.row(
    cell.connectionRows[0],
    cell,
    264,
    'en',
    true,
    ''
  );
  assert.ok(list.rowHeight >= 96);
  for (const node of row.nodes)
    assert.ok(
      node.y >= 0 && node.y + node.height <= list.rowHeight,
      JSON.stringify(node)
    );
  const filename = row.nodes.find((node) => node.id === 'tableConnectionFile');
  assert.ok(filename.y >= 64);
}

assert.equal(
  Nested.identity({ searchType: 'x', parentKey: 'A' }, 'demo'),
  Nested.identity({ projectCode: 'demo', searchType: 'x', parentKey: 'A' })
);
