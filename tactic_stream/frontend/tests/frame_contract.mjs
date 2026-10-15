import assert from 'node:assert/strict';
import {
  node,
  rect,
  validateScene,
  recordIndex,
  virtualRange
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import { textStyles } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { records as pipelineRecords } from '../../src/tactic_stream/shared_ui/features/administration/workflow/catalog.ui.mjs';

const bounds = rect(0, 0, 100, 40);
const create = (kind, extra = {}) => node(kind, 'control', bounds, extra);
assert.equal(create('Label').fontSize, 13);
assert.equal(create('Label', { text: undefined }).text, '');
assert.equal(create('Label', { text: 0 }).text, '0');
for (const [fontRole, size] of Object.entries(textStyles))
  assert.equal(create('Label', { fontRole }).fontSize, size);
assert.throws(() => create('Label', { fontRole: 'missing' }), /font role/);
assert.throws(() => create('Label', { fontRole: null }), /font role/);
assert.equal(create('Label', { fontRole: undefined }).fontRole, 'body');
assert.throws(() => create('Label', { fontSize: 13 }), /Reserved/);
assert.throws(() => node('Label', '', bounds), /id/);
assert.throws(() => create('Label', { x: NaN }), /Reserved/);
const scene = (...nodes) => ({ nodes });
assert.throws(
  () => validateScene(scene(create('Label'), create('Button'))),
  /Duplicate/
);
assert.throws(
  () => validateScene(scene(create('Button', { action: { type: '' } }))),
  /action/
);
assert.throws(
  () => validateScene(scene(create('View', { view: 'editor' })), {}, {}),
  /Missing Frame View/
);
validateScene(
  scene(create('View', { view: 'editor', optional: true })),
  {},
  {}
);
validateScene(scene(create('View', { view: 'editor' })), {}, { editor: {} });
assert.throws(
  () =>
    validateScene(
      scene(create('View', { view: 'editor' })),
      {},
      { editor: undefined }
    ),
  /Missing Frame View/
);
assert.throws(
  () =>
    validateScene(
      scene(create('List', { source: 'rows', keyField: 'id', rowHeight: 32 })),
      {},
      {}
    ),
  /source/
);
validateScene(
  scene(create('List', { source: 'rows', keyField: 'id', rowHeight: 32 })),
  { rows: [] },
  {}
);
assert.throws(
  () =>
    validateScene(
      scene(create('List', { source: 'rows', rowHeight: 0 })),
      { rows: [] },
      {}
    ),
  /keyField/
);
assert.throws(() => recordIndex([{ id: 'a' }, { id: 'a' }], 'id'), /Duplicate/);
assert.throws(() => recordIndex([{ name: 'a' }], 'id'), /Missing/);
assert.throws(() => recordIndex([{ id: 1 }, { id: '1' }], 'id'), /Duplicate/);
assert.equal(recordIndex([{ id: 0 }, { id: 'a' }], 'id').get('0'), 0);
assert.deepEqual(virtualRange(10000, 32, 300, 3200, 3), {
  first: 97,
  last: 113,
  height: 320000
});
assert.deepEqual(virtualRange(0, 32, 300, 320000, 3), {
  first: 0,
  last: 0,
  height: 0
});
assert.deepEqual(virtualRange(2, 32, 300, 320000, 3), {
  first: 2,
  last: 2,
  height: 64
});
assert.throws(() => virtualRange(10, 0, 300, 0, 3), /Invalid/);
assert.throws(
  () => validateScene(scene({ ...create('Label'), fontSize: 99 })),
  /typography/
);
const pipelines = pipelineRecords(
  {
    catalog: [
      { identity: 'group:demo/asset', searchType: 'demo/asset', label: 'Saved' }
    ],
    ready: true,
    identity: '',
    document: { searchType: 'demo/asset' },
    metadata: {}
  },
  { query: '', collapsed: [] },
  'en'
);
assert.equal(recordIndex(pipelines, 'key').size, pipelines.length);
assert(
  pipelines.some((row) => row.identity === '' && row.key === 'draft:demo/asset')
);


for(const rowGap of [-1,NaN,Infinity,12]) {
  assert.throws(()=>validateScene({nodes:[node('List','invalidGap',rect(0,0,100,100),{keyField:'id',source:'rows',rowHeight:12,rowGap})]},{rows:[]}),/positive rowHeight/);
}

console.log(
  'Frame contract: typography, bounds, action shapes, required bindings and stable record keys passed.'
);
