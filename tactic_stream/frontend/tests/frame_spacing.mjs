import assert from 'node:assert/strict';
import {
  spacing,
  controls,
  cssVariables
} from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { sections } from '../../src/tactic_stream/shared_ui/controls/forms/sections.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import { arrange } from '../../src/tactic_stream/shared_ui/features/objects/fields.ui.mjs';
import * as Configuration from '../../src/tactic_stream/shared_ui/features/configuration/configuration.ui.mjs';

const fields = [
  { kind: 'Heading', id: 'general', title: 'General' },
  {
    kind: 'Field',
    id: 'name',
    title: 'Name',
    description:
      'A long explanation that must wrap without overlapping the editor. '.repeat(
        3
      ),
    props: { text: 'Robot Arm' }
  },
  { kind: 'Switch', id: 'enabled', title: 'Enabled', props: { checked: true } },
  {
    kind: 'Choice',
    id: 'view',
    title: 'View',
    options: [{ value: 'table', label: 'Table' }],
    trailingAction: {
      title: 'Open',
      icon: 'open-in-new',
      action: { type: 'open' }
    }
  },
  {
    kind: 'ChoiceGrid',
    id: 'choices',
    options: [
      { value: 'one', label: 'One' },
      { value: 'two', label: 'Two' },
      { value: 'three', label: 'Three' }
    ]
  },
  {
    kind: 'Area',
    id: 'description',
    title: 'Description',
    height: 96,
    fullWidth: true
  },
  { kind: 'Button', id: 'apply', title: 'Apply' }
];
let count = 0;
for (const style of ['md3', 'material5', 'fluent']) {
  const variables = cssVariables(style, true, [41, 45, 48], [120, 166, 196]);
  for (const [name, value] of Object.entries(spacing))
    assert.equal(variables['--space-' + name], value + 'px');
  assert.equal(
    variables['--dialog-spacing'],
    '0px',
    'No second inset below the dialog header'
  );
  assert.equal(controls.editorPanel.padding, controls.formField.padding);
  for (const width of [200, 320, 620, 1000])
    for (const language of ['en', 'ru']) {
      const shell = Configuration.describe(
        { page: 'server', product: 'Fixture' },
        width,
        740,
        language
      );
      const header = shell.nodes.find(
        (node) => node.id === 'configurationHeader'
      );
      assert.equal(
        header.children.find((node) => node.id === 'configurationPageTitle').x,
        shell.pageBounds.x + spacing.content,
        'Page title aligns with the content section edge'
      );
      const scene = sections(fields, width, language, true, style);
      validateScene(scene);
      const card = scene.nodes.find((node) => node.id === 'section_general');
      const content = card.children.filter(
        (node) => !node.id.endsWith('Divider')
      );
      for (const item of content) {
        assert.ok(item.x >= spacing.content, item.id + ' left inset');
        assert.ok(
          item.x + item.width <= width - spacing.content + 0.001,
          item.id + ' right inset'
        );
        assert.ok(item.y >= spacing.content, item.id + ' top inset');
        assert.ok(
          item.y + item.height <= card.height - spacing.content + 0.001,
          item.id + ' bottom inset'
        );
      }
      for (const id of [
        'nameLabel',
        'enabledLabel',
        'viewLabel',
        'choices',
        'description',
        'apply'
      ])
        assert.equal(
          content.find((node) => node.id === id).x,
          spacing.content,
          id + ' shares the same left edge'
        );
      const last = content.at(-1);
      assert.equal(
        card.height - last.y - last.height,
        spacing.content,
        'No trailing row gap'
      );
      assert.equal(
        scene.height,
        card.y + card.height,
        'Scroll extent ends at the last surface'
      );
      const inputs = content.filter((node) =>
        ['Field', 'Switch', 'Choice', 'Area', 'Button', 'Box'].includes(
          node.kind
        )
      );
      for (let index = 0; index < inputs.length - 1; index++) {
        const item = inputs[index],
          next = inputs[index + 1];
        if (item.id === 'view') continue; // Its adjacent Open action shares this row.
        assert.ok(
          item.y + item.height <= next.y,
          item.id + ' does not overlap ' + next.id
        );
      }
      count++;
    }
}
const masonry = arrange(1000, [80, 120, 60]);
assert.equal(masonry.cells[1].x - masonry.cells[0].width, spacing.content);
assert.equal(masonry.cells[2].y - masonry.cells[0].height, spacing.content);
assert.ok(
  sections([{ kind: 'Heading', id: 'only', title: 'Heading' }], 320, 'en', true)
    .height >= 20
);
console.log(
  count +
    ' form layouts: aligned edges, wrapping, trailing action, no overlap or double padding; shared CSS roles pass.'
);
