import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/table/dependencies.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/table/dependencies.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

let change = State.begin(State.create('alias', 'project'), 'root');
let state = change.state;
assert.equal(change.request.search_key, 'alias');
assert.equal(State.begin(state, 'root').request, undefined);
state = State.accept(state, 'root', {
  snapshotKey: 'S1',
  projectCode: 'project',
  revision: 'rev1',
  hasNext: true,
  rows: [
    {
      key: '0',
      kind: 'reference',
      snapshotKey: 'S2',
      projectCode: 'other',
      revision: 'rev2'
    },
    {
      key: '1',
      kind: 'file',
      snapshotKey: 'S1',
      projectCode: 'project',
      fileRange: '1-10',
      fileIndex: 0
    }
  ]
});
change = State.toggle(state, State.rows(state)[0]);
state = change.state;
assert.equal(change.request.projectCode, 'other');
assert.equal(change.request.expected_revision, 'rev2');
state = State.toggle(state, State.rows(state)[0]).state;
state = State.accept(state, 'root/0', {
  rows: [{ key: '0', kind: 'reference', snapshotKey: 'S1' }],
  hasNext: false
});
assert.equal(
  State.rows(state).length,
  3,
  'late read must not reopen collapsed branch'
);
change = State.toggle(state, State.rows(state)[0]);
state = change.state;
assert.equal(
  change.request,
  undefined,
  'reopening cached branch must be immediate'
);
assert.equal(State.rows(state)[1].cycle, true);
assert.equal(State.toggle(state, State.rows(state)[1]).request, undefined);
change = State.toggle(
  state,
  State.rows(state).find((row) => row.kind === 'file')
);
assert.equal(change.request.file_index, 0);
assert.equal(change.request.search_key, 'S1');
state = State.accept(change.state, change.request.path, null, 'offline');
assert(State.rows(state).some((row) => row.error === 'offline'));
change = State.begin(state, 'root', true);
assert.equal(change.request.offset, 2);
assert.equal(change.request.expected_revision, 'rev1');
state = State.accept(change.state, 'root', null, 'offline');
const failure = State.rows(state).find(
  (row) => row.kind === 'status' && row.pagePath === 'root'
);
const retry = UI.row(failure, 400, 'en').nodes.find((node) =>
  node.id.startsWith('dependencyRetry_')
).action;
assert.equal(retry.more, true);
change = State.begin(state, retry.path, retry.more);
assert.equal(
  change.request.offset,
  2,
  'retry of a failed page must preserve existing rows'
);
state = State.accept(change.state, 'root', {
  rows: [{ key: '2', kind: 'missing', title: 'gone' }],
  hasNext: false
});
assert.equal(state.pages.root.rows.length, 3);
const translated = UI.describe(
  { ...state, notice: 'Dependencies changed. Reload this snapshot.' },
  696,
  500,
  'ru'
).nodes.find((node) => node.id === 'dependencyOwner');
assert.equal(translated.text, 'Зависимости изменились. Обновите снапшот.');
for (const width of [296, 696, 1400]) {
  validateScene(UI.describe(state, width, 500, 'ru'), {
    dependencyRows: State.rows(state)
  });
  for (const row of State.rows(state))
    validateScene(UI.row(row, width - 16, 'ru'));
}
const deep = State.create('S0', 'project');
let path = 'root';
for (let depth = 0; depth < 1000; depth++) {
  deep.pages[path] = {
    searchKey: 'S' + depth,
    open: true,
    loaded: true,
    rows: [
      {
        key: '0',
        kind: 'reference',
        group: 'Upstream',
        snapshotKey: 'S' + (depth + 1)
      }
    ]
  };
  path += '/0';
}
assert.equal(
  State.rows(deep).length,
  1000,
  'valid deep graphs must not be truncated'
);
deep.pages[path] = {
  searchKey: 'S1000',
  open: true,
  loaded: true,
  rows: [{ key: '0', kind: 'reference', group: 'Upstream', snapshotKey: 'S0' }]
};
assert.equal(State.rows(deep).at(-1).cycle, true);
console.log(
  'PASS: dependency cached tree, cycles, range pages, errors, captured projects, layouts'
);
