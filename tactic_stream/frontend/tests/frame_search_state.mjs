import assert from 'node:assert/strict';
import * as Visibility from '../../src/tactic_stream/shared_ui/features/search/visibility.ui.mjs';
import * as Card from '../../src/tactic_stream/shared_ui/features/search/card.ui.mjs';
import * as Menus from '../../src/tactic_stream/shared_ui/features/search/menus.ui.mjs';
import { taskGroup } from '../../src/tactic_stream/shared_ui/features/search/organization.mjs';
import { groupRecords } from '../src/features/workspace/resultViews.js';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Collection from '../../src/tactic_stream/shared_ui/controls/lists/collection.mjs';
import { normalizeRecords } from '../../src/tactic_stream/shared_ui/features/search/conditions.ui.mjs';

const defaults = normalizeRecords([], [{ value: 'code' }, { value: 'name' }]);
assert.equal(defaults[0].column, 'name');
assert.equal(defaults[0].relation, 'EQI');
assert.equal(defaults[0].isDefault, true);
const normalized = normalizeRecords([
  { column: 'code', operator: 'or' },
  { column: 'name', operator: 'or', isDefault: true }
]);
assert.deepEqual(
  normalized.map((row) => [row.operator, row.isDefault]),
  [
    ['begin', true],
    ['or', false]
  ]
);
for (const count of [100, 1000, 10000]) {
  const collection = Collection.layout(
    Array.from({ length: count }, (_, index) => ({
      key: String(index),
      height: index % 3 ? 100 : 64
    })),
    800,
    { rowGap: 3 }
  );
  const [first, last] = Collection.range(
    collection.rows,
    collection.height / 2,
    700
  );
  assert(last - first < 25);
  assert(collection.rows[first].top <= collection.height / 2);
  assert(
    collection.rows[last - 1].top + collection.rows[last - 1].height >=
      collection.height / 2 + 700
  );
  assert.deepEqual(Collection.range([], 0, 700), [0, 0]);
}
const tiles = Collection.layout(
  [
    { key: 'a', height: 244 },
    { key: 'b', height: 160 },
    { key: 'c', height: 164 }
  ],
  442,
  { cellWidth: 212, columnGap: 18, rowGap: 14 }
);
assert.deepEqual(
  tiles.rows.map((row) => [row.top, row.height]),
  [
    [0, 244],
    [258, 164]
  ]
);
assert.equal(tiles.rows[0].entries[1].left, 230);

const records = [
  { kind: 'pipeline', nodeId: 'p', expanded: true },
  {
    nodeId: 'a',
    parentId: 'p',
    kind: 'process',
    key: 'model',
    group: '__proto__',
    checkable: true,
    checked: true
  },
  {
    nodeId: 'b',
    parentId: 'p',
    kind: 'process',
    key: 'model',
    group: '__proto__',
    checkable: true,
    checked: true
  }
];
Visibility.change(records, { type: 'check', index: 1, value: false });
assert.equal(
  records[2].checked,
  false,
  'Repeated schema edges share a logical visibility setting'
);
const ignore = JSON.parse(JSON.stringify(Visibility.ignoreFrom(records)));
assert.deepEqual(ignore.processes.__proto__, ['model']);
assert.equal(
  Visibility.branchVisible(
    { kind: 'process', process: 'model' },
    { pipeline_code: '__proto__' },
    ignore
  ),
  false
);
assert(Visibility.applyIgnore(records, {}).every((record) => record.checked));
Visibility.change(records, { type: 'expand', index: 0, shift: true });
assert(records.slice(1).every((record) => !record.rowVisible));

const compare = (left, right) =>
    left.localeCompare(right, undefined, { numeric: true }),
  statuses = [{ key: 'Ready', accent: '#123456' }, { key: 'Done' }];
assert.equal(
  taskGroup(
    [
      { process: 'model', status: 'Done' },
      { process: 'model', status: 'Ready' }
    ],
    'model',
    statuses,
    '#555555',
    compare
  ).label,
  'Ready'
);
assert.equal(taskGroup([], 'model', statuses, '', compare).label, 'No task');
assert.equal(
  taskGroup([{ process: 'model', status: '' }], 'model', statuses, '', compare)
    .label,
  'No status'
);
assert.equal(
  taskGroup(
    [
      { process: 'model', status: 'Step10' },
      { process: 'model', status: 'Step2' }
    ],
    'model',
    [],
    '',
    compare
  ).label,
  'Step2'
);
assert.equal(
  taskGroup(
    [{ process: 'model', status: '__proto__' }],
    'model',
    [{ key: '__proto__' }],
    '',
    compare
  ).rank,
  0
);
const rows = [1, 2, 3].map((id) => ({ __search_key__: 'cg/asset?code=' + id }));
const nodes = rows.map((record, index) => ({
  record,
  tasks:
    index === 0
      ? [{ process: 'model', status: 'Done' }]
      : index === 1
        ? [{ process: 'model', status: 'Ready' }]
        : []
}));
assert.deepEqual(
  groupRecords(rows, 'task_status:model', nodes, {
    statuses: { model: statuses }
  }).map((group) => group.label),
  ['Ready', 'Done', 'No task']
);

for (const language of ['en', 'ru'])
  for (const width of [320, 360, 800, 1440])
    for (const kind of ['object', 'snapshot', 'process', 'relation', 'file'])
      for (const tile of [false, true])
        for (const compact of [false, true]) {
          const model = {
            kind,
            tile,
            compact,
            mobile: width < 700,
            subtitle: 'Description',
            hasMetadata: true,
            technical: 'v001 · model',
            typeWidth: 80,
            typeTitle: 'Asset',
            typeIcon: 'sobject',
            typeColor: '#607d8b',
            foreground: '#ffffff'
          };
          const geometry = Card.layout(model, width);
          const body = Card.body(
            model,
            geometry.content.width,
            geometry.content.height
          );
          const views = {
            title: {},
            metadata: {},
            technical: {},
            description: {}
          };
          validateScene(body, {}, views);
          if (tile) validateScene(Card.tileHeader(model, width, language));
          validateScene(
            Visibility.footer({ valid: true, dirty: true }, width, language)
          );
          validateScene(
            Menus.sortColumn(
              {
                column: 'name',
                direction: 'asc',
                columns: [{ value: 'name', label: 'Name' }]
              },
              Math.min(256, width),
              language
            )
          );
        }
assert.equal(
  Menus.filterActions({
    presets: [
      { title: 'A', view: 'stable:a' },
      { title: 'B', view: 'stable:b' }
    ],
    selected: 'stable:b'
  }).find((action) => action.checked).command,
  'preset:stable:b'
);
assert.equal(
  Menus.sortActions({ defaultOrder: true }).filter(
    (action) => action.command === 'default'
  ).length,
  1
);
console.log(
  'Search state: visibility identities, repeated edges, task grouping/order, stable preset commands and bounded card/editor scenes passed'
);
