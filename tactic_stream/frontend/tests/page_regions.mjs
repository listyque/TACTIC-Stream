import assert from 'node:assert/strict';
import { describe } from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/page.document.mjs';
import * as Page from '../../src/tactic_stream/shared_ui/features/table/page.ui.mjs';
import * as Nested from '../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';
import { spacing } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';

const definitions = Array.from({ length: 4 }, (_, index) => ({
  name: 'field' + index,
  title: 'Filter ' + index,
  dataType: 'text',
  relation: '=',
  value: 'value',
  enabled: true
}));
const table = {
  kind: 'table',
  text: 'Tasks',
  editorPath: [1],
  region: 'content',
  table: { searchType: 'demo/task', view: 'table' },
  sizing: { height_mode: 'fill' }
};
const model = {
  layoutFilters: definitions,
  layoutNodes: [
    { kind: 'text', text: 'Instructions', region: 'header', editorPath: [0] },
    table,
    {
      kind: 'button',
      text: 'Open project',
      href: '/projects/demo/',
      region: 'footer',
      editorPath: [2]
    }
  ]
};
const flatten = (rows, x = 0, y = 0) =>
  rows.flatMap((row) => [
    { ...row, absoluteX: x + row.x, absoluteY: y + row.y },
    ...flatten(row.children || [], x + row.x, y + row.y)
  ]);
for (const [width, height] of [
  [1800, 900],
  [800, 700],
  [360, 500]
]) {
  const scene = describe(model, width, height, 'en'),
    rows = flatten(scene.nodes);
  const header = rows.find((row) => row.id === 'customLayoutHeader'),
    body = rows.find((row) => row.id === 'customLayoutScroll'),
    footer = rows.find((row) => row.id === 'customLayoutFooter');
  assert.equal(header.background, 'panel');
  assert.equal(header.radius, 0);
  assert.equal(footer.background, 'panel');
  assert.equal(body.y, header.y + header.height);
  assert.equal(body.y + body.height, footer.y);
  assert.equal(footer.y + footer.height, height);
  assert.equal(header.x, 0, 'The panel surface remains edge-to-edge');
  assert.equal(header.width, width);
  for (const id of [
    'customLayout_0_block',
    'customLayout_1_block',
    'customLayout_2_block'
  ]) {
    const block = rows.find((row) => row.id === id);
    assert.ok(block.absoluteX >= spacing.content, id + ' left interior');
    assert.ok(
      block.absoluteX + block.width <= width - spacing.content,
      id + ' right interior'
    );
  }
  for (const item of rows.filter((row) => row.id.startsWith('pageRuntime'))) {
    assert.ok(item.absoluteX >= spacing.content, item.id + ' left interior');
    assert.ok(
      item.absoluteX + item.width <= width - spacing.content,
      item.id + ' right interior (including the scrollbar reserve)'
    );
  }
  assert.ok(body.height >= Math.min(180, height * 0.45) - 1);
  assert.equal(
    rows.find((row) => row.id === 'customLayout_1' && row.kind === 'View').key,
    'customLayout_1',
    'Moving regions preserves the table identity'
  );
  assert.ok(
    rows.find((row) => row.id === 'customLayout_2').absoluteY >= footer.y
  );
  assert.ok(
    rows.find((row) => row.id === 'customLayout_1_block').absoluteY >= body.y
  );
  assert.ok(
    rows.find((row) => row.id === 'customLayout_1_block').height <= body.height
  );
  if (width === 1800) {
    const last = rows.find((row) => row.id === 'pageRuntimeReset');
    assert.ok(
      last.absoluteX + last.width > width - 32,
      'The filter row uses the available interior width, including its actions'
    );
  }
  if (width === 800) {
    assert.equal(
      rows.find((row) => row.id === 'pageRuntime_field0_enabled').absoluteY,
      rows.find((row) => row.id === 'pageRuntime_field1_enabled').absoluteY
    );
    assert.ok(
      rows.find((row) => row.id === 'pageRuntime_field2_enabled').absoluteY >
        rows.find((row) => row.id === 'pageRuntime_field0_enabled').absoluteY,
      'Four filters form balanced two-by-two rows'
    );
  }
  if (width === 360) {
    const scroll = rows.find((row) => row.id === 'customLayoutHeaderScroll');
    assert.ok(scroll.contentHeight > scroll.height);
    assert.ok(scroll.scrollbarId);
  }
}
const short = describe(
  {
    layoutNodes: [{ ...table, sizing: {}, height: 1000 }, model.layoutNodes[2]]
  },
  800,
  500,
  'en'
);
const shortRows = flatten(short.nodes),
  scroll = shortRows.find((row) => row.id === 'customLayoutScroll');
assert.ok(scroll.contentHeight > scroll.height);
assert.equal(
  shortRows.find((row) => row.id === 'customLayoutFooter').y +
    shortRows.find((row) => row.id === 'customLayoutFooter').height,
  500
);
const doc = {
  name: 'sample',
  title: 'Sample',
  blocks: [
    { kind: 'column', children: [{ kind: 'text', text: 'Nested' }] },
    { kind: 'button', href: '/projects/demo/', region: 'footer' }
  ]
};
assert.equal(
  Document.change(doc, '1', 'region', 'header').blocks[1].region,
  'header'
);
assert.throws(() => Document.change(doc, '0.0', 'region', 'footer'));
assert.throws(() => Document.change(doc, '1', 'region', 'unknown'));
assert.equal(
  Document.reparent(doc, '1', '0').document.blocks[0].children[1].region,
  'content'
);
assert.equal(doc.blocks[1].region, 'footer');
const chrome = Page.describe({ title: 'Tasks', canEdit: true }, 800, 600, 'en');
assert.equal(
  chrome.nodes.find((row) => row.id === 'workspacePageHeader').background,
  'panel'
);
const nested = Nested.describe({ rows: [], embedded: true }, 800, 500, 'en');
assert.ok(nested.nodes.some((row) => row.id === 'nestedToolbarSurface'));
assert.ok(nested.nodes.some((row) => row.id === 'nestedFooterSurface'));
console.log(
  'Page header/content/footer flow, bounded region scrolling, stable table IDs and editor placement PASS'
);
