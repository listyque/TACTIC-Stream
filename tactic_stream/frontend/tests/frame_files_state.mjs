import assert from 'node:assert/strict';
import {
  node,
  rect,
  validateScene
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Queue from '../../src/tactic_stream/shared_ui/features/files/queue/queue.ui.mjs';
import * as Ingest from '../../src/tactic_stream/shared_ui/features/files/ingest.ui.mjs';
import * as Plate from '../../src/tactic_stream/shared_ui/features/files/drop_plate.ui.mjs';
import * as Screenshot from '../../src/tactic_stream/shared_ui/features/files/screenshot.ui.mjs';
import * as Sync from '../../src/tactic_stream/shared_ui/features/files/sync/queue.ui.mjs';
import * as SyncEditor from '../../src/tactic_stream/shared_ui/features/files/sync/editor.ui.mjs';
import * as ObjectCheckin from '../../src/tactic_stream/shared_ui/features/files/object_checkin.ui.mjs';
import * as RepositoryPrompts from '../../src/tactic_stream/shared_ui/features/files/repository_prompts.ui.mjs';
import * as WorkspaceRows from '../../src/tactic_stream/shared_ui/features/files/workspace/rows.ui.mjs';
import * as WorkspaceForms from '../../src/tactic_stream/shared_ui/features/files/workspace/forms.ui.mjs';
import * as WorkspacePresentation from '../../src/tactic_stream/shared_ui/features/files/workspace/presentation.mjs';
import * as WorkspaceGraph from '../../src/tactic_stream/shared_ui/features/files/workspace/graph.ui.mjs';
import * as WorkspaceStorage from '../../src/tactic_stream/shared_ui/features/files/workspace/storage.ui.mjs';
import * as WorkspaceDepots from '../../src/tactic_stream/shared_ui/features/files/workspace/depots.ui.mjs';
import * as WorkspaceSubmit from '../../src/tactic_stream/shared_ui/features/files/workspace/submit.ui.mjs';
import * as WorkspaceInspector from '../../src/tactic_stream/shared_ui/features/files/workspace/inspector.ui.mjs';
import * as WorkspaceMappings from '../../src/tactic_stream/shared_ui/features/files/workspace/mappings.ui.mjs';
import * as WorkspaceLog from '../../src/tactic_stream/shared_ui/features/files/workspace/log.ui.mjs';
import * as WorkspaceDialogs from '../../src/tactic_stream/shared_ui/features/files/workspace/dialogs.ui.mjs';
import * as WorkspaceEditors from '../../src/tactic_stream/shared_ui/features/files/workspace/editors.ui.mjs';
import * as WorkspaceChangelist from '../../src/tactic_stream/shared_ui/features/files/workspace/changelist.ui.mjs';
import * as WorkspaceToolbar from '../../src/tactic_stream/shared_ui/features/files/workspace/toolbar.ui.mjs';
import * as WorkspaceNavigation from '../../src/tactic_stream/shared_ui/features/files/workspace/navigation.ui.mjs';
import * as WorkspaceCatalog from '../../src/tactic_stream/shared_ui/features/files/workspace/catalog.ui.mjs';
import * as WorkspaceDetails from '../../src/tactic_stream/shared_ui/features/files/workspace/details.ui.mjs';
import * as WorkspaceFooter from '../../src/tactic_stream/shared_ui/features/files/workspace/footer.ui.mjs';
import * as WorkspaceTree from '../../src/tactic_stream/shared_ui/features/files/workspace/tree.ui.mjs';

const record = {
  operationId: 'one',
  title: 'model.txt',
  objectTitle: 'Hero Robot',
  status: 'Prepared',
  process: 'publish',
  context: 'publish/review',
  contextBranch: 'review',
  checked: true,
  canEdit: true,
  canCommit: true,
  canOptions: true,
  canPreview: true,
  canContext: true,
  canDescription: true,
  canNaming: true,
  versionlessAllowed: true,
  fileCount: 1,
  naming: [
    {
      title: 'model.txt',
      versioned: ['repo/model_v001.txt'],
      versionless: ['repo/model.txt']
    }
  ]
};
const model = {
  count: 2,
  selected: 0,
  record,
  hasReady: true,
  hasCheckedReady: true,
  filesHeight: 142,
  fileCount: 1,
  serverQueueAvailable: true
};
const models = {
  operations: [record],
  files: [],
  naming: Queue.namingRows(record, 'en')
};
const views = { preview: {}, description: {}, progress: {} };
function visit(scene, all = []) {
  validateScene(scene, models, views);
  for (const value of scene.nodes) {
    all.push(value);
    if (value.children?.length) visit({ nodes: value.children }, all);
  }
  return all;
}
for (const width of [320, 390, 640, 700, 1000, 1600]) {
  for (const details of [false, true])
    for (const advanced of [false, true]) {
      const state = { ...model, details, advanced, namingExpanded: true };
      const scene = Queue.describe(state, width, 700, 'en'),
        controls = visit(scene);
      const bounds = Queue.layout(state, width, 700, 'en');
      assert.equal(bounds.compact, width < 700);
      assert.equal(
        controls.some((node) => node.id === 'commitQueueRows'),
        bounds.showQueue
      );
      assert.equal(
        controls.some((node) => node.id === 'commitQueueField_version'),
        bounds.showDetails && advanced
      );
      const left = controls.find((node) => node.id === 'commitQueueFilesDock');
      if (left) assert(left.width >= 0);
    }
}
assert.equal(Queue.versionValue(''), 0);
assert.equal(Queue.versionValue('42'), 42);
for (const invalid of ['1.2', '-1', '10000', 'no', '1e3'])
  assert.equal(Queue.versionValue(invalid), null);
assert.equal(Queue.previewActions({ ...model, busy: true })[0].enabled, false);
assert.equal(
  Queue.operationActions({ ...model, busy: true }, record)[0].enabled,
  false
);
assert.equal(
  Queue.sendActions({
    ...model,
    record: { ...record, status: 'Result unknown', canCommit: false }
  })[0].enabled,
  false
);
assert.equal(Queue.namingRows(record, 'en').length, 3);
for (const width of [280, 320, 440, 700]) {
  const choices = ObjectCheckin.modeChoice({ count: 12 }, width, 'ru');
  validateScene({ nodes: choices.nodes });
  assert.equal(
    choices.nodes.filter((node) => node.kind === 'Button').length,
    3
  );
  validateScene(ObjectCheckin.revision({}, width, 170, 'en'));
  for (const state of [
    {},
    { revision: true },
    { preview: true },
    { append: true, appendUncertain: true },
    { discard: true },
    { busy: true }
  ])
    validateScene(
      ObjectCheckin.describe(
        { ...state, processes: [], repositories: [], count: 3 },
        width,
        700,
        'en'
      ),
      { files: [] }
    );
  const changed = RepositoryPrompts.team(
    {
      code: 'default',
      path: '//share/' + 'folder/'.repeat(100),
      changed: true
    },
    width,
    280,
    'ru'
  );
  const accept = changed.nodes.find(
    (node) => node.id === 'repositoryTeamAccept'
  );
  assert.equal(accept.enabled, false);
  validateScene(changed);
  validateScene(RepositoryPrompts.setup({}, width, 280, 'en'));
}
for (const width of [320, 390, 700, 1000]) {
  const state = {
    ...model,
    details: true,
    busy: true,
    resumeAvailable: true,
    record: { ...record, status: 'Failed', canRetry: true }
  };
  const controls = visit(Queue.describe(state, width, 700, 'en'));
  const cancel = controls.find((node) => node.id === 'commitQueueCancel');
  const retry = controls.find((node) => node.id === 'commitQueueRetry');
  assert(cancel && retry);
  assert(cancel.x >= 0 && retry.x >= 0);
  assert(
    cancel.x >= retry.x + retry.width ||
      cancel.y >= retry.y + retry.height ||
      retry.y >= cancel.y + cancel.height
  );
  validateScene(
    Sync.describe({ count: 0, total: 0, active: 0 }, width, 800, 'en'),
    {},
    { queue: {}, busy: {} }
  );
  validateScene(
    SyncEditor.describe({ presets: [], selected: -1 }, width, 800, 'en'),
    {},
    { processes: {}, chunk: {}, queue: {} }
  );
  for (const language of ['en', 'ru'])
    for (const origin of [
      { x: 0, y: 0 },
      { x: width, y: 700 }
    ]) {
      const region = Screenshot.finish(
        { width: 1, height: 1 },
        origin,
        width,
        700
      );
      const scene = Screenshot.describe(
        { region, ready: true, busy: false },
        width,
        700,
        language
      );
      validateScene(scene, {}, { resize: {} });
      for (const button of scene.nodes.filter(
        (node) => node.kind === 'Button'
      )) {
        assert(button.x >= 0 && button.y >= 0);
        assert(
          button.x + button.width <= width && button.y + button.height <= 700
        );
      }
      const moved = Screenshot.move(region, { x: width, y: 700 }, width, 700);
      assert(moved.x + moved.width <= width && moved.y + moved.height <= 700);
      const resized = Screenshot.resize(
        moved,
        { x: width, y: 700 },
        width,
        700
      );
      assert(
        resized.x + resized.width <= width && resized.y + resized.height <= 700
      );
    }
}
assert.equal(Ingest.optionValue('updateMode', false), 'insert');
assert.equal(Ingest.optionValue('updateMode', true), 'update');
assert.equal(Ingest.fileHeight({ error: '' }), 46);
assert.equal(Ingest.fileHeight({ error: 'Bad file' }), 62);
assert.equal(
  Plate.matches(
    { title: 'diffuse', path: 'textures/diffuse.exr', extension: 'EXR' },
    '.exr',
    'extension'
  ),
  true
);
assert.equal(
  Plate.matches(
    { title: 'diffuse', path: 'textures/diffuse.exr', extension: 'EXR' },
    'beauty',
    'name'
  ),
  false
);
assert.throws(
  () =>
    validateScene({
      nodes: [
        node('Box', 'invalidMenu', rect(0, 0, 10, 10), { contextAction: {} })
      ]
    }),
  /Invalid Frame action/
);
console.log(
  'PASS files/queue presentation: layout matrix, guards, naming, version input and context action validation'
);
for (const language of ['en', 'ru']) {
  for (const width of [260, 320, 480, 700]) {
    for (const [form, data] of [
      ['revert', { caption: 'change/main', deleteNew: true }],
      [
        'revision',
        {
          target: '//main/assets/model.txt',
          selector: 'at_date',
          value: '2026-10-18',
          force: true
        }
      ],
      [
        'target',
        {
          operation: 'apply_reconcile',
          creating: true,
          target: 'pending',
          options: []
        }
      ],
      ['shelf', { code: 'shelf', options: [], after: true }],
      [
        'review',
        {
          review: {
            items: [],
            number: 7,
            editable: true,
            rebase_required: true
          },
          operation: 'merge_begin'
        }
      ],
      [
        'comparison',
        {
          comparison: {
            left: { path: 'a.txt' },
            right: { path: 'b.txt' },
            kind: 'text',
            text: '+ change'
          }
        }
      ]
    ]) {
      const scene = WorkspaceForms[form](data, width, 400, language);
      validateScene(scene, { targetFiles: [], reviewFiles: [] });
      for (const item of scene.nodes) {
        assert.ok(item.x >= 0 && item.y >= 0);
        assert.ok(
          item.x + item.width <= width + 0.01,
          form + ' horizontal bounds'
        );
        assert.ok(
          item.y + item.height <= 400 + 0.01,
          form + ' vertical bounds'
        );
      }
      if (form === 'review')
        assert.equal(
          scene.nodes.find((item) => item.id === 'workspaceReviewAccept')
            .enabled,
          false
        );
      if (form === 'revert')
        assert.equal(
          scene.nodes[0].children.find(
            (item) => item.id === 'workspaceRevertDeleteNew'
          ).checked,
          true
        );
    }
    validateScene(
      WorkspaceRows.treeRow(
        {
          row: { kind: 'change', depth: 3, state: 'pending' },
          caption: 'Change',
          subtitle: 'admin · main'
        },
        width
      )
    );
    validateScene(
      WorkspaceRows.fileRow(
        {
          row: { path: 'a.txt' },
          columns: [{ key: 'path', visible: true, width: 160 }]
        },
        width,
        language
      )
    );
  }
}
assert.equal(
  WorkspaceForms.validRevision({ selector: 'revision', value: '0' }),
  true
);
assert.equal(
  WorkspaceForms.validRevision({ selector: 'file_revision', value: '0' }),
  false
);
assert.equal(
  WorkspaceForms.validRevision({ selector: 'changelist', value: '1.5' }),
  false
);
assert.equal(
  WorkspaceForms.validRevision({ selector: 'at_date', value: '   ' }),
  false
);
assert.equal(
  WorkspacePresentation.badges({
    path: 'a.txt',
    action: 'write',
    local_status: 'modified',
    change_state: 'pending',
    staged_current: false
  })[0].label,
  'Modified after upload'
);
console.log(
  'PASS workspace row status precedence, operation forms, revision validation and narrow/localized bounds'
);
const streamNodes = [
  { code: 'main', depot: 'main', stream_type: 'mainline', revision: 1 },
  {
    code: 'dev',
    parent: 'main',
    depot: 'main',
    stream_type: 'development',
    revision: 2
  }
];
for (const language of ['en', 'ru'])
  for (const width of [260, 390, 700, 1000]) {
    const models = { depots: [], pendingFiles: [], shelfFiles: [], tasks: [] };
    const views = { streamGraphEdges: {}, entries: {}, message: {} };
    const policies = Object.fromEntries(
      WorkspaceStorage.fields.map(([key]) => [key, '0'])
    );
    policies.max_parallel = '4';
    for (const scene of [
      WorkspaceGraph.describe(
        {
          native: true,
          nodes: streamNodes,
          edges: [],
          zoom: 1.5,
          after: true,
          edgesAfter: true
        },
        width,
        500,
        language
      ),
      WorkspaceStorage.describe(
        {
          status: { indexed: true, initialized: true },
          draft: { policy: policies },
          filesService: true
        },
        width,
        500,
        language
      ),
      WorkspaceDepots.describe(
        {
          draft: { creating: true, code: 'main' },
          selected: {},
          repositories: [],
          administrator: true
        },
        width,
        500,
        language
      ),
      WorkspaceSubmit.describe(
        { review: {}, context: {}, selectedTasks: [], exceptions: [] },
        width,
        500,
        language
      ),
      WorkspaceInspector.describe(
        {
          info: { path: 'a.txt', stream: 'main', file: { size: 12 } },
          tab: 'details'
        },
        width,
        500,
        language
      ),
      WorkspaceMappings.describe(
        {
          rows: [
            {
              id: 'one',
              stream: 'main',
              source: '...',
              target: '...',
              writable: true
            }
          ],
          enabled: true
        },
        width,
        language
      ),
      WorkspaceLog.describe({ expanded: true }, width, 140, language),
      WorkspaceLog.entry(
        {
          time: '12:00',
          operation: 'Upload',
          level: 'ERROR',
          message: 'Full message',
          path: 'a.txt'
        },
        width,
        40
      )
    ])
      validateScene(scene, models, views);
    const graph = WorkspaceGraph.describe(
      { nodes: streamNodes, zoom: 2, after: true, edgesAfter: true },
      width,
      500,
      language
    );
    const more = graph.nodes.find((node) => node.id === 'streamGraphMore'),
      edges = graph.nodes.find((node) => node.id === 'streamGraphMoreEdges');
    assert.ok(
      more.x + more.width <= edges.x,
      'Graph page actions do not overlap'
    );
    const submit = WorkspaceSubmit.describe(
      { review: {}, context: {}, selectedTasks: [], exceptions: [] },
      width,
      500,
      language
    );
    assert.equal(
      submit.nodes.find((node) => node.id === 'submitAccept').enabled,
      false
    );
  }
assert.deepEqual(WorkspaceGraph.layout(streamNodes), {
  main: { x: 24, y: 24 },
  dev: { x: 228, y: 24 }
});
assert.deepEqual(
  WorkspaceGraph.layout([
    { code: 'a', parent: 'b' },
    { code: 'b', parent: 'a' }
  ]),
  { a: { x: 24, y: 24 }, b: { x: 24, y: 112 } }
);
assert.throws(
  () =>
    validateScene({
      nodes: [node('Box', 'invalidScale', rect(0, 0, 10, 10), { scale: 0 })]
    }),
  /Invalid Frame scale/
);
assert.equal(
  WorkspaceLog.entryText({
    time: '00:00',
    operation: 'Read',
    message: 'complete\nmessage',
    path: 'path'
  }),
  '00:00 · Read · complete\nmessage\npath'
);
console.log(
  'PASS workspace graph, storage/depot/submit/inspector/mapping/log scenes, cyclic graph, progress guards and paint scale validation'
);

for (const language of ['en', 'ru'])
  for (const width of [200, 360, 800, 1400]) {
    const height = 540;
    const scenes = [
      WorkspaceChangelist.describe(
        { change: {}, details: {} },
        width,
        height,
        language
      ),
      WorkspaceEditors.tab(
        { draft: { preset: 'history' } },
        width,
        height,
        language
      ),
      WorkspaceEditors.setup({ code: 'work' }, width, height, language),
      WorkspaceDialogs.columns(
        { columns: [{ key: 'path', visible: true, width: 300 }] },
        width,
        height,
        language
      ),
      WorkspaceDialogs.editor(
        { kind: 'rename_file', draft: 'folder/file.txt' },
        width,
        height,
        language
      ),
      WorkspaceToolbar.views(
        { canCreate: true, canMaximize: true, narrow: width < 800 },
        width,
        48,
        language
      ),
      WorkspaceNavigation.describe(
        {
          workspaces: [],
          path: '//main/long/path',
          recovery: true,
          connectionState: 'offline'
        },
        width,
        language
      ),
      WorkspaceCatalog.describe(
        { native: true, source: 'workspaces', count: 0 },
        width,
        height,
        language
      ),
      WorkspaceDetails.describe(
        {
          native: true,
          kind: 'tasks',
          taskError: 'Transfer failed',
          after: 'next',
          preview: 'preview'
        },
        width,
        height,
        language
      ),
      WorkspaceDetails.describe(
        { native: true, kind: 'conflicts', showResolved: false },
        width,
        height,
        language
      ),
      WorkspaceTree.describe(
        { native: true, treeView: 'workspace', navigationHeight: 180 },
        width,
        height,
        language
      ),
      WorkspaceFooter.describe(
        {
          busy: true,
          progress: {
            bytes_per_second: 100,
            total_known: true,
            phase: 'verifying',
            files_done: 2,
            files_total: 1
          },
          logVisible: true
        },
        width,
        40,
        language
      )
    ];
    for (const kind of ['blocked', 'drop', 'nonempty', 'switch', 'confirm'])
      scenes.push(
        WorkspaceDialogs.prompt(
          kind,
          {
            action: 'delete_change',
            targets: [{ number: 1 }],
            message: 'Outside workspace',
            count: 2
          },
          width,
          height,
          language
        )
      );
    for (const scene of scenes)
      validateScene(
        scene,
        { catalog: [] },
        {
          files: {},
          shelves: {},
          tasks: {},
          mappings: {},
          tabs: {},
          busy: {},
          progress: {},
          navigation: {},
          depot: {},
          workspace: {},
          rows: {},
          taskFiles: {}
        }
      );
    for (const local of [false, true]) {
      const filters = WorkspaceToolbar.filters(
        {
          kind: 'files',
          local,
          narrow: width < 800,
          selectedCount: 1,
          selectionScope: 'files'
        },
        width,
        language
      );
      for (const node of filters.nodes)
        assert.ok(
          node.x + node.width <= width + 0.5,
          node.id + ' exceeds narrow toolbar'
        );
    }
    const progress = scenes
      .flatMap((scene) => scene.nodes)
      .find((node) => node.id === 'workspaceTransferProgress');
    assert.equal(
      progress.value,
      1,
      'Published progress stays bounded after a smaller total'
    );
  }
for (const value of ['', '47', '901', '100.5', '1e2', '-5', 'abc'])
  assert.equal(WorkspaceDialogs.validColumnWidth(value), false, value);
for (const value of ['48', '900', '150'])
  assert.equal(WorkspaceDialogs.validColumnWidth(value), true, value);
assert.match(
  WorkspaceRows.treeTitle({ kind: 'change', code: 'fallback' }, 'en'),
  /#fallback/
);
assert.ok(
  !WorkspaceToolbar.views({ canActions: false }, 360, 40, 'en').nodes.some(
    (node) =>
      [
        'newChangelistButton',
        'workspaceActionsButton',
        'fileWorkspaceMaximize'
      ].includes(node.id)
  )
);
assert.ok(
  !WorkspaceCatalog.describe(
    { native: false, source: 'workspaces' },
    360,
    500,
    'en'
  ).nodes.some((node) => node.id === 'workspaceCatalogSwitch')
);
console.log(
  'PASS workspace dialogs, editors, navigation, catalog, details, trees and footer: bilingual narrow scenes and capability boundaries'
);
for (const language of ['en', 'ru']) {
  const scene = SyncEditor.describe(
    {
      presets: [],
      validContext: true,
      selected: 0,
      buttonWidths: [90, 300],
      error: 'Server validation failed. '.repeat(200)
    },
    390,
    700,
    language
  );
  const content = scene.nodes[0].children[0];
  const footer = content.children.find(
    (node) => node.id === 'repositorySyncEditorFooter'
  );
  const start = footer.children.find(
    (node) => node.id === 'repositorySyncEditorStart'
  );
  const status = footer.children.find(
    (node) => node.id === 'repositorySyncEditorStatusScroll'
  );
  assert.equal(start.width, 300);
  assert.ok(footer.y + footer.height <= 700);
  assert.ok(status.height <= 140 && status.contentHeight > status.height);
}
