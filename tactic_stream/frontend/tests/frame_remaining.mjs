import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Workspace from '../../src/tactic_stream/shared_ui/features/knowledge/workspace.ui.mjs';
import * as Commands from '../../src/tactic_stream/shared_ui/features/knowledge/commands.ui.mjs';
import * as Formatting from '../../src/tactic_stream/shared_ui/features/knowledge/format.ui.mjs';
import * as Navigation from '../../src/tactic_stream/shared_ui/features/knowledge/navigation.ui.mjs';
import * as Reports from '../../src/tactic_stream/shared_ui/features/workhours/reports.ui.mjs';
import * as Sheet from '../../src/tactic_stream/shared_ui/features/workhours/sheet.ui.mjs';
import * as Api from '../../src/tactic_stream/shared_ui/features/support/documentation/api.ui.mjs';
import * as Journal from '../../src/tactic_stream/shared_ui/features/support/documentation/journal.ui.mjs';
import * as Collaboration from '../../src/tactic_stream/shared_ui/features/support/collaboration/initialization.ui.mjs';

for (const language of ['en', 'ru'])
  for (const width of [304, 430, 560, 720, 900, 1280]) {
    for (const busy of [false, true]) {
      for (const canInitialize of [false, true]) {
        const state = { busy, canInitialize, epoch: 3 };
        validateScene(Collaboration.state(state, width, 420, language));
        const confirm = Collaboration.confirmation(state, width, 420, language);
        validateScene(confirm);
        assert.equal(
          confirm.nodes.find(
            (row) => row.id === 'collaborationInitializationConfirm'
          ).enabled,
          !busy
        );
        assert.equal(
          confirm.nodes.find(
            (row) => row.id === 'collaborationInitializationDetails'
          ).resetKey,
          3
        );
      }
      const model = {
        initialized: true,
        canEdit: true,
        busy,
        navigationExpanded: true,
        navigationPage: true
      };
      const scene = Workspace.describe(model, width, 700, language);
      validateScene(
        scene,
        {},
        { navigation: {}, page: {}, initialization: {} }
      );
      assert.equal(scene.bounds.navigationVisible, true);
      assert.equal(scene.bounds.pageVisible, width >= 720);
      for (const kind of ['article', 'section'])
        for (const creating of [true, false]) {
          const entry = {
            kind,
            creating,
            back: width < 720,
            selectionCount: 3,
            step: 1,
            draft: true,
            dirty: true,
            busy,
            canEdit: true,
            title: 'Long page title',
            description: 'Summary',
            tocCount: 3,
            resourceCount: 2,
            tocVisible: true
          };
          const editor = Commands.editor(entry, width, language);
          validateScene(editor);
          const visible = editor.nodes.filter((row) => row.visible !== false);
          for (const row of visible) {
            assert.ok(row.x >= 0 && row.x + row.width <= width + 0.01, row.id);
            if (row.kind === 'Button') assert.equal(row.enabled, !busy, row.id);
          }
          const title = visible.find(
            (row) => row.id === 'knowledgeEditorTitle'
          );
          assert.ok(title.width > 0);
          for (const row of visible.filter((row) => row.kind === 'Button')) {
            if (row.y < title.y + title.height && row.y + row.height > title.y)
              assert.ok(
                row.x + row.width <= title.x || row.x >= title.x + title.width,
                row.id
              );
          }
          const viewer = Commands.viewer(entry, width, language);
          validateScene(viewer);
          assert.ok(
            viewer.nodes.find((row) => row.id === 'knowledgeViewerTitle')
              .width > 0
          );
        }
      const format = Formatting.describe(
        { mode: 'visual', disabled: busy },
        width,
        language
      );
      validateScene(format);
      assert.ok(
        format.nodes.every((row) => row.x >= 0 && row.x + row.width <= width)
      );
      const headings = [{ title: 'Heading', level: 1 }];
      validateScene(Navigation.outline(headings, width, 260, '', language), {
        headings
      });
      validateScene(
        Navigation.row(
          { identity: 'A', title: 'Page', kind: 'article' },
          true,
          '',
          width,
          language
        )
      );
      const report = {
        report: 'my_hours',
        busy,
        options: [{ key: 'my_hours' }],
        count: 1
      };
      validateScene(Reports.describe(report, width, 700, language), {
        reports: [{ key: 'my_hours' }],
        values: [{}]
      });
      validateScene(
        Reports.descriptor(
          { key: 'my_hours', permission: 'user' },
          report,
          width,
          language
        )
      );
      validateScene(
        Reports.valueRow(
          { label: 'Artist', valueLabel: '2 h', share: 3 },
          width,
          language
        )
      );
      validateScene(
        Sheet.toolbar(
          { busy, canManage: true, selectedCount: 2, users: [] },
          width,
          language
        )
      );
      const summary = Sheet.summary({}, width, language);
      validateScene(summary);
      assert.equal(summary.height, width < 480 ? 111 : 52);
      assert.equal(
        summary.nodes.find((row) => row.id === 'timesheetSummary-pending').y,
        width < 480 ? 59 : 0
      );
      validateScene(
        Sheet.entry(
          { id: 'A', canEdit: true, canApprove: true, selectable: true },
          width,
          language
        )
      );
      const edit = Sheet.editor(
        { day: '2026-10-18', hours: '1.25', busy, canManage: true },
        width,
        language
      );
      validateScene(edit);
      assert.equal(
        edit.nodes.find((row) => row.id === 'workHourSave').enabled,
        !busy
      );
      for (const type of ['json', 'text', 'number', 'password', 'boolean'])
        validateScene(
          Api.parameter(
            { name: 'value', label: 'Value', type },
            type === 'boolean' ? false : '2',
            busy,
            width,
            language
          )
        );
      validateScene(
        Api.method(
          { name: 'query', examples: [{ label: 'Read objects' }] },
          'query',
          true,
          width,
          language
        )
      );
      validateScene(
        Journal.describe(
          { busy, xml: '<transaction/>', hidden: 5, error: 'Failure' },
          width,
          language
        )
      );
    }
  }
for (const value of ['0', '-1', '24.01', '1.234', 'NaN', 'Infinity', '1e1', ''])
  assert.equal(Sheet.validHours(value), false, value);
for (const value of ['0.01', '24', '1,5', '1.25'])
  assert.equal(Sheet.validHours(value), true, value);
assert.equal(
  Api.methods(
    [
      {
        name: 'query',
        status: 'available',
        examples: [{}],
        help: { ru: 'Список' }
      }
    ],
    'common',
    'список',
    'ru'
  ).length,
  1
);
assert.equal(
  Api.methods([{ name: 'secret', status: 'excluded' }], 'available', '', 'en')
    .length,
  0
);
console.log('B14 scene, responsive command and input invariants passed');
