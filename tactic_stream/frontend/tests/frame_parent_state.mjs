import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/table/parent.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/table/parent.ui.mjs';

const seed = {
  targetSearchKey: 'sthpw/note?code=N1',
  sourceId: '10',
  projectCode: 'one',
  tableView: 'table',
  columnName: 'parent',
  sourceRevision: 'source'
};
let change = State.begin(State.create(seed), 'prepare');
assert.equal(change.request.source_revision, 'source');
change = State.accept(change.state, 'prepare', {
  expectedRevision: 'captured',
  sourceId: '10',
  currentParentKey: 'contract/entity?project=one&code=A',
  parentTypes: [{ value: 'contract/entity', label: 'Entities' }],
  parentType: 'contract/entity',
  currentParent: {
    searchKey: 'contract/entity?project=one&code=A',
    title: 'First',
    revision: 'a'
  }
});
assert.equal(change.request.action, 'candidates');
change = State.accept(change.state, 'candidates', {
  rows: [
    {
      searchKey: 'contract/entity?project=one&code=B',
      title: 'Second',
      code: 'B',
      revision: 'b'
    }
  ],
  hasNext: true
});
let state = State.dispatch(change.state, {
  type: 'select',
  searchKey: change.state.rows[0].searchKey
}).state;
assert(State.canSave(state));
assert(State.rows(state)[0].selected);
change = State.begin(state, 'save');
assert.equal(change.request.parent_revision, 'b');
assert(!State.dispatch(change.state, { type: 'cancel' }).close);
change = State.accept(
  change.state,
  'save',
  null,
  'Unable to reach the server.',
  true
);
assert(change.state.uncertain);
assert(!State.canSave(change.state));
assert(!State.dispatch(change.state, { type: 'save' }).request);
const checking = State.dispatch(change.state, { type: 'check' });
assert.equal(checking.request.expected_revision, 'captured');
assert(State.accept(checking.state, 'check', { state: 'saved' }).saved);
state = State.accept(checking.state, 'check', { state: 'unchanged' }).state;
assert(State.canSave(state));
const confirmation = State.dispatch(state, { type: 'cancel' });
assert.equal(confirmation.state.confirmAction, 'close');
assert(!State.dispatch(confirmation.state, { type: 'reject' }).close);
assert(State.dispatch(confirmation.state, { type: 'accept' }).close);
const refresh = State.dispatch(
  State.dispatch(state, { type: 'refresh' }).state,
  { type: 'accept' }
);
assert.equal(refresh.request.source_revision, '');
assert.equal(
  refresh.request.source_id,
  '10',
  'Refresh cannot retarget a recreated record with the same code'
);
assert.equal(refresh.state.rows.length, 0);
const more = State.begin(state, 'candidates', true);
assert.equal(more.request.offset, 1);
const failed = State.accept(
  more.state,
  'candidates',
  null,
  'File Offline'
).state;
assert.equal(failed.rows.length, 1);
assert.equal(State.begin(failed, 'candidates', true).request.offset, 1);
assert.equal(
  State.accept(state, 'prepare', {}).state,
  state,
  'Late response cannot replace the current phase'
);
assert.equal(
  State.dispatch(state, { type: 'query-text', value: 'Родитель' }).state
    .draftQuery,
  'Родитель'
);
assert.equal(
  State.dropParentKey({
    searchType: 'contract/entity',
    searchKeys: ['contract/entity?project=one&code=B']
  }),
  'contract/entity?project=one&code=B'
);
for (const payload of [
  null,
  { searchType: 'contract/entity', searchKeys: [] },
  { searchType: 'contract/entity', searchKeys: ['other/entity?code=A'] }
])
  assert.throws(() => State.dropParentKey(payload), /Drop one parent object/);
const qtPrepare = State.accept(
  State.begin(State.create(seed), 'prepare').state,
  'prepare',
  {
    expectedRevision: 'captured',
    sourceId: '10',
    parentType: 'contract/entity',
    parentTypes: {
      0: { value: 'contract/entity', label: 'Entities' },
      length: 1
    }
  }
);
assert.equal(
  qtPrepare.state.parentTypes.length,
  1,
  'QVariantList array-like values must retain their options'
);
for (const width of [284, 380, 800])
  for (const height of [308, 440])
    for (const language of ['en', 'ru']) {
      for (const model of [state, failed, confirmation.state, change.state]) {
        const scene = UI.describe(model, width, height, language);
        for (const item of scene.nodes) {
          assert(
            item.x >= 0 && item.y >= 0 && item.width >= 0 && item.height >= 0,
            item.id
          );
          assert(item.x + item.width <= width + 0.01, item.id);
          assert(item.y + item.height <= height + 0.01, item.id);
        }
      }
    }
console.log(
  'PASS: parent draft, captured revisions, pagination, uncertain writes, discard and narrow geometry'
);
