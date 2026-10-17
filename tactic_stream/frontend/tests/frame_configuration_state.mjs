import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Configuration from '../../src/tactic_stream/shared_ui/features/configuration/configuration.ui.mjs';
import * as Settings from '../../src/tactic_stream/shared_ui/features/configuration/settings.ui.mjs';
import * as Projects from '../../src/tactic_stream/shared_ui/features/projects/project.ui.mjs';
import * as Templates from '../../src/tactic_stream/shared_ui/features/projects/templates.ui.mjs';
import * as Repositories from '../../src/tactic_stream/shared_ui/features/configuration/repository.ui.mjs';
import * as Catalog from '../../src/tactic_stream/shared_ui/features/projects/catalog.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/projects/editor.ui.mjs';
import * as Server from '../../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs';

const views = { lightAccent: {}, darkAccent: {}, image: {} };
for (const kind of ['close', 'clear'])
  for (const width of [288, 328, 430])
    for (const language of ['en', 'ru'])
      validateScene(Configuration.confirmation({ kind }, width, 248, language));
let scenes = 0;
for (const width of [360, 800, 1100])
  for (const language of ['en', 'ru'])
    for (const native of [false, true]) {
      for (const page of Configuration.pages) {
        const values = {
          columns: [
            { key: 'object', label: 'Object', width: 180, visible: true },
            { key: 'status', label: 'Status', width: 100, visible: true }
          ]
        };
        const model = { native, values, style: 'md3' };
        const fields = Settings.fieldsFor(page.id, model);
        validateScene(
          Configuration.describe(
            {
              page: page.id,
              product: 'Fixture',
              canReset: true,
              dirtyPages: [page.id]
            },
            width,
            740,
            language
          )
        );
        validateScene(
          Settings.describe(
            {
              ...model,
              fields,
              columns: page.id === 'tasks' ? values.columns : []
            },
            width,
            640,
            language
          ),
          {},
          views
        );
        assert(
          fields.every(
            (field, index) =>
              field.kind !== 'Heading' || fields[index + 1]?.kind !== 'Heading'
          )
        );
        scenes += 2;
      }
      for (const step of [0, 1, 2, 3])
        for (const busy of [false, true])
          for (const discard of [false, true]) {
            validateScene(
              Projects.wizard(
                {
                  product: 'Fixture',
                  step,
                  draft: { source: '_empty' },
                  ready: true,
                  busy,
                  discard
                },
                width,
                740,
                language
              ),
              {},
              views
            );
            scenes++;
          }
      for (const deletion of ['', 'cg']) {
        validateScene(
          Templates.describe(
            {
              packages: [{ code: 'cg', path: 'fixture/cg' }],
              selected: 'cg',
              deletion
            },
            width,
            600,
            language
          )
        );
        scenes++;
      }
      const repo = {
        alias: 'default',
        title: 'Assets',
        code: 'default',
        active: true,
        isDefault: true,
        defaultEligible: true,
        custom: false
      };
      validateScene(
        Repositories.editor(
          { record: repo, native, selected: 'default', editing: true },
          width,
          700,
          language
        ),
        { repositories: [repo] }
      );
      validateScene(
        Repositories.summary({ records: [repo] }, width, 700, language)
      );
      validateScene(
        Catalog.describe(
          { selected: { code: 'cg' }, canManage: true },
          width,
          700,
          language
        ),
        { projects: [] }
      );
      validateScene(
        Editor.describe({ values: {}, dirty: true }, width, 700, language),
        {},
        views
      );
      scenes += 4;
    }
const fields = Settings.fieldsFor('checkin', { native: true, values: {} });
for (const key of [
  'descriptionLimit',
  'sequencePadding',
  'sequenceNaming',
  'minimumFramePadding'
]) {
  if (key !== 'sequenceNaming')
    assert(
      fields.some((field) => field.field === key),
      key
    );
}
assert.equal(
  Settings.change(
    { displayLimit: 20 },
    { type: 'step', field: 'displayLimit', value: 5 },
    fields
  ).displayLimit,
  25
);
assert.equal(
  Settings.change(
    { displayLimit: 20 },
    { type: 'field', field: 'displayLimit', value: '0' },
    fields
  ).displayLimit,
  0,
  'Validation keeps an invalid typed draft available to its owner'
);
assert.equal(Projects.wizardDirty({ source: 'cg' }), true);
assert.equal(Projects.wizardDirty({ source: '_empty' }), false);
const columns = [
  { key: 'object', visible: true },
  { key: 'status', visible: true }
];
assert.equal(
  Settings.editColumn(columns, {
    type: 'columnVisible',
    key: 'object',
    value: false
  })[0].visible,
  true
);
assert.equal(
  Settings.editColumn(columns, {
    type: 'columnMove',
    key: 'status',
    direction: -1
  })[0].key,
  'status'
);
assert.equal(columns[0].key, 'object');
const readonly = Settings.dccFields({
  sections: [
    {
      fields: [
        {
          key: 'locked',
          type: 'integer',
          read_only: true,
          minimum: 0,
          maximum: 10
        }
      ]
    }
  ]
});
const scene = Settings.describe(
  { fields: readonly, values: { locked: 5 } },
  800,
  600,
  'en'
);
function flatten(nodes) {
  return nodes.flatMap((node) => [node, ...flatten(node.children || [])]);
}
for (const id of ['setting_lockedIncrease', 'setting_lockedDecrease'])
  assert.equal(
    flatten(scene.nodes).find((node) => node.id === id).enabled,
    false,
    id
  );
const serverFields = Server.fields(
  {
    groups: [
      {
        title: 'Security',
        settings: [
          {
            path: 'security/token',
            label: 'Token',
            description: 'Secret',
            editable: true,
            secret: true,
            configured: true,
            input_type: 'text',
            value: 'must-not-leak',
            default: null
          }
        ]
      }
    ],
    draft: { 'security/token': '' },
    showDetails: true,
    expanded: ['security/token']
  },
  'en'
);
assert(!JSON.stringify(serverFields).includes('must-not-leak'));
assert(serverFields.some((field) => field.props?.password));
assert(serverFields.some((field) => field.action?.type === 'clear'));
assert.equal(
  Settings.field(
    { kind: 'Switch', field: 'enabled', title: 'Enabled' },
    { enabled: true },
    {},
    'en',
    false
  ).props.text,
  'Enabled'
);
console.log(
  `Configuration/project contracts: ${scenes} valid shared scenes and draft/column decisions passed`
);
