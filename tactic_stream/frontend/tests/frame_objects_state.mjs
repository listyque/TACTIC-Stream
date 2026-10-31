import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Description from '../../src/tactic_stream/shared_ui/features/objects/description.ui.mjs';
import * as Snapshot from '../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';
import * as Watch from '../../src/tactic_stream/shared_ui/features/objects/watch.ui.mjs';
import * as Fields from '../../src/tactic_stream/shared_ui/features/objects/fields.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/objects/editor.ui.mjs';
import * as Duplicate from '../../src/tactic_stream/shared_ui/features/objects/duplicate.ui.mjs';
import * as Links from '../../src/tactic_stream/shared_ui/features/objects/links.ui.mjs';
import * as Inspector from '../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
import * as Report from '../../src/tactic_stream/shared_ui/features/objects/report.ui.mjs';
import { cssVariables } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';

for (const language of ['en', 'ru']) {
  const model = {
    mode: 'publish',
    recordKey: 'demo/asset?project=demo&code=A',
    searchType: 'demo/asset',
    valid: true,
    canSave: true
  };
  const scene = Editor.header(model, 320, language);
  validateScene(scene);
  assert.equal(
    scene.nodes.find((node) => node.id === 'sobjectEditorParent').toolTip,
    model.recordKey
  );
  assert(!scene.nodes.some((node) => node.id === 'sobjectCreateMode'));
}

for (const width of [0, 320, 880])
  for (const editing of [false, true]) {
    const scene = Description.describe(
      { editing, enabled: true, canSave: false, dirty: true, header: false },
      width,
      320,
      'en'
    );
    validateScene(scene, {}, { value: {} });
    if (editing)
      assert.equal(
        scene.nodes.find((row) => row.id === 'description_save').enabled,
        false
      );
  }
assert.equal(
  Description.presentation({ saving: true, editing: true }, 'en').status,
  'Saving…'
);
assert.equal(Description.presentation({ managed: false }, 'en').editable, true);
const colors = cssVariables('md3', true, [41, 45, 48], [120, 166, 196], {});
assert.equal(
  colors['--tertiary'],
  colors['--violet'],
  'Pinned description shares the tertiary role'
);
for (const width of [0, 320, 699, 700, 880, 1400]) {
  const model = {
    name: 'name',
    title: 'Object name',
    description: 'Caption',
    required: true,
    error: 'Invalid name'
  };
  const columns = Fields.columns(model, width);
  for (const height of [0, 36, 112]) {
    const scene = Fields.field(model, width, height, 'ru');
    validateScene(scene);
    assert.equal(
      scene.editor.width,
      columns.inputWidth,
      'Input width must not depend on its measured height'
    );
    assert(scene.height >= scene.editor.y + scene.editor.height);
  }
  const grid = Fields.arrange(width, [130, 240, 120, 160]);
  assert(grid.cells.every((box) => box.width >= 0 && box.height >= 0));
  assert.equal(
    grid.height,
    Math.max(...grid.cells.map((box) => box.y + box.height))
  );
}
for (const vertical of [false, true])
  for (const extent of [0, 40, 300, 1000])
    for (const candidate of [-10, 0.5, 10, NaN]) {
      const ratio = Snapshot.clampRatio(candidate, extent, vertical);
      assert(Number.isFinite(ratio) && ratio >= 0 && ratio <= 1);
      const result = Snapshot.layout(
        {
          contentMode: 'both',
          orientation: vertical ? 'vertical' : 'horizontal',
          ratio: candidate
        },
        extent,
        extent
      );
      for (const box of [result.preview, result.files, result.splitter])
        assert(box.width >= 0 && box.height >= 0);
    }
assert.deepEqual(Snapshot.optionChange({ showAll: false }, 'show_all'), {
  key: 'showAll',
  value: true
});
assert.throws(() => Snapshot.optionChange({}, 'unknown'));
assert.equal(Snapshot.fileIcon('file', 'image', 'file', 'image.png'), 'image');
assert.equal(Snapshot.fileIcon('file', '', '', 'FOLDER.ZIP'), 'archive');
assert.equal(Snapshot.fileColumns(true, 649).path, false);
assert.equal(Snapshot.fileColumns(true, 650).path, true);
assert.deepEqual(
  Watch.available([{ value: 'a' }, { value: 'b' }], ['a'], 'en').map(
    (row) => row.value
  ),
  ['b', '__all__']
);
const watch = Watch.describe(
  { available: [], choice: '', busy: true, canSave: true, selectedCount: 0 },
  320,
  420,
  'en'
);
validateScene(watch, { repositories: [] });
assert.equal(
  watch.nodes.find((row) => row.id === 'watchEditorSave').enabled,
  false
);
console.log(
  'PASS: object description actions, snapshot sizing/options and watch-folder selection'
);

const fields = [
  { name: 'name', type: 'string' },
  { name: 'description', type: 'multiline' },
  { name: 'code', type: 'string', readOnly: true }
];
const source = {
  name: 'Asset {n:03}',
  description: 'Line {n}\nAgain {n:02}',
  code: 'keep {n}'
};
const drafts = Editor.batchDrafts(source, fields, 3);
assert.deepEqual(
  drafts.map((row) => row.name),
  ['Asset 001', 'Asset 002', 'Asset 003']
);
assert.equal(drafts[1].description, 'Line 2\nAgain 02');
assert.equal(drafts[1].code, 'keep {n}');
assert.equal(source.name, 'Asset {n:03}');
assert.throws(() => Editor.batchDrafts(source, fields, 101));
assert.throws(() => Editor.batchDrafts(source, fields, 2.5));
const records = [{ key: 'a' }, { key: 'b' }, { key: 'c' }];
assert.deepEqual(Links.select(['a'], records, 2, 0, false, true), [
  'a',
  'b',
  'c'
]);
assert.deepEqual(Links.select(['a'], records, 0, 0, true, false), []);
assert.deepEqual(Links.select(['a'], records, 2, 0, true, false), ['a', 'c']);
for (const width of [0, 320, 560, 880, 1200])
  for (const language of ['en', 'ru']) {
    const editor = {
      mode: 'insert',
      title: 'Create record',
      searchType: 'demo/assets',
      fieldCount: 3,
      batchEnabled: true,
      batchCount: 3,
      batchTotal: 3,
      batchIndex: 0
    };
    for (const part of ['header', 'tools', 'footer'])
      for (const batchPreview of [false, true])
        validateScene(
          Editor[part]({ ...editor, batchPreview }, width, language),
          {},
          { batchCount: {} }
        );
    for (const step of [0, 1, 2, 3, 4])
      for (const part of ['header', 'tabs', 'body', 'footer'])
        validateScene(
          Duplicate[part](
            {
              step,
              ready: true,
              relations: [
                {
                  key: 'x',
                  title: 'Assets',
                  kind: 'instance',
                  count: 1,
                  mode: 'none',
                  options: [
                    { value: 'none', label: 'Do not copy' },
                    { value: 'link', label: 'Keep links' }
                  ],
                  items: []
                }
              ],
              processes: [
                {
                  name: 'model',
                  copySnapshots: true,
                  snapshotCount: 1,
                  fileCount: 1
                }
              ],
              totals: {}
            },
            width,
            language
          )
        );
    validateScene(
      Links.describe(
        { direction: 'add', canTransfer: true, dirty: true },
        width,
        640,
        language
      ),
      {},
      {
        availableSearch: {},
        linkedSearch: {},
        availableList: {},
        linkedList: {}
      }
    );
    validateScene(
      Inspector.context(
        { taskCount: 2, hasActions: true, process: 'model' },
        width,
        language
      )
    );
    validateScene(
      Inspector.quick(
        {
          hasTask: true,
          canCreate: true,
          canEdit: true,
          statuses: [{ value: '', label: '' }]
        },
        width,
        language
      ),
      {},
      { progress: {}, status: {} }
    );
    for (const page of ['tasks', 'notes', 'children'])
      validateScene(
        Report.page(
          {
            page,
            metrics: {},
            participants: [],
            tasks: [],
            notes: [],
            children: []
          },
          width,
          language
        )
      );
  }
const hidden = Report.page(
  {
    page: 'tasks',
    metrics: { canViewCosts: false },
    participants: [{ login: 'a', displayName: 'Artist', cost: 900, hours: 3 }]
  },
  440,
  'en'
);
assert(
  !JSON.stringify(hidden).includes('900'),
  'Costs must not reach presentation when the field is hidden'
);
console.log(
  'PASS: object wizard layouts, batch drafts, link range selection and inspector controls'
);

for (const width of [0, 320, 880])
  for (const language of ['en', 'ru']) {
    for (const state of [
      'ready',
      'loading',
      'error',
      'unconfigured',
      'missingType',
      'unrelated'
    ])
      validateScene(
        Inspector.related(
          { state, count: 0, summaryAvailable: false },
          width,
          language
        )
      );
    for (const expanded of [false, true])
      validateScene(
        Inspector.workHours(
          {
            expanded,
            summary: {
              approved: 2,
              planned: 8,
              pending: 1,
              overPlan: 0,
              progress: 25
            }
          },
          width,
          language
        )
      );
  }

const { sameSearchKey } = await import('../src/features/workspace/links.js');
assert(
  sameSearchKey(
    'sthpw/task?project=one&code=T1',
    'skey://sthpw/task?code=T1&project=sthpw',
    'one'
  )
);
assert(sameSearchKey('cg/assets?project=cg&code=A', 'cg/assets?code=A', 'cg'));
assert(
  !sameSearchKey('cg/assets?project=other&code=A', 'cg/assets?code=A', 'cg')
);
assert(!sameSearchKey('cg/assets?code=A', 'cg/shot?code=A', 'cg'));
assert(!sameSearchKey('bad', 'cg/assets?code=A', 'cg'));

assert.equal(
  Editor.numberedValue('Asset {n:2} / {n:02}', 3),
  'Asset {n:2} / 03'
);
assert.equal(Editor.batchExample('Asset {n:03}', 3), 'Asset 001 … Asset 003');

const Note = await import(
  '../../src/tactic_stream/shared_ui/features/objects/note.ui.mjs'
);
for (const width of [0, 140, 320, 880]) {
  const layout = Note.body(
    { text: true, previews: true, attachments: true },
    width,
    { text: 44, previews: 72, attachments: 134 }
  );
  assert.equal(layout.height, 266);
  assert.deepEqual(
    layout.nodes.map((n) => n.y),
    [0, 52, 132]
  );
  assert.equal(
    Note.edit({ text: 'Draft', uncertain: true }, width, 'en').nodes.find(
      (n) => n.id === 'noteEditSave'
    ).enabled,
    false
  );
  assert.equal(
    Note.remove({ uncertain: true }, width, 'en').nodes.find(
      (n) => n.id === 'noteDeleteConfirm'
    ).enabled,
    false
  );
}

const relatedAction = Inspector.relatedRow(
  { clickable: true },
  320,
  'en'
).nodes.find((node) => node.id === 'relatedTaskOpen');
assert(relatedAction.width >= 24 && relatedAction.height >= 24);
for (const height of [0, 26, 192]) {
  const list = Links.list({ scope: 'available', count: 0 }, 380, height, 'en');
  assert(list.viewport.height >= 0);
  assert.equal(list.rowWidth, list.viewport.width - 24);
  assert.equal(
    list.nodes.some((node) => node.id === 'linkEmpty_available'),
    height > 42
  );
}

const ReportHeader = await import(
  '../../src/tactic_stream/shared_ui/features/objects/report.ui.mjs'
);
const restoredHeader = ReportHeader.header(
  {
    summary: {
      title: 'Hero Robot',
      typeTitle: 'Assets',
      description: 'Short description',
      code: 'ASSET001',
      searchType: 'cg/assets',
      project: 'Computer graphics',
      pipeline: 'cg/assets'
    },
    metrics: {}
  },
  880,
  'en'
);
const headerNode = (id) => restoredHeader.nodes.find((node) => node.id === id);
assert.equal(headerNode('objectReportPreview').round, false);
assert(headerNode('objectReportPreview').y > 14);
assert.equal(headerNode('objectReportDescription').kind, 'View');
assert.equal(
  headerNode('objectReportFieldValue_0').y -
    headerNode('objectReportFieldLabel_0').y,
  15
);
assert.equal(
  restoredHeader.nodes.filter((node) =>
    node.id.startsWith('objectReportFieldIcon_')
  ).length,
  4
);
assert(headerNode('objectReportType').width < 100);
assert(
  headerNode('objectReportMetric_0').width >
    headerNode('objectReportMetric_1').width
);

// Original Inspector keeps all four quick fields on one desktop row, with phone reflow.
const desktopQuick = Inspector.quick(
  { hasTask: true, canEdit: true },
  880,
  'en'
);
const phoneQuick = Inspector.quick({ hasTask: true, canEdit: true }, 320, 'en');
const quickNode = (scene, id) => scene.nodes.find((node) => node.id === id);
assert.equal(
  quickNode(desktopQuick, 'taskInspectorStatusField').y,
  quickNode(desktopQuick, 'taskInspectorDate_start').y
);
assert(
  quickNode(phoneQuick, 'taskInspectorDate_start').y >
    quickNode(phoneQuick, 'taskInspectorStatusField').y
);

assert.equal(
  Inspector.quick({ hasTask: false, canEdit: false }, 880, 'en').height,
  148,
  'An empty Inspector retains its original card geometry'
);

for (const language of ['en', 'ru']) {
  const uncertainFooter = Editor.footer(
    { mode: 'edit', uncertain: true, busy: false, canSave: false },
    640,
    language
  );
  validateScene(uncertainFooter);
  assert.ok(
    uncertainFooter.nodes.some((node) => node.id === 'sobjectEditorCheck')
  );
}
