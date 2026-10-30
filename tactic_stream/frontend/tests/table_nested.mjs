import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  columns,
  extent,
  rows,
  describe,
  row
} from '../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';

for (const value of ['reference.txt', 0, false, '']) {
  const scene = row(
    { columns: [{ name: 'filename', field: 'file_name' }] },
    { key: 'F', record: { file_name: value }, cells: {} },
    'en'
  );
  assert.equal(
    scene.nodes.find((node) => node.id === 'nestedCell_filename').cell.text,
    value
  );
}

const legacyColumns = columns({
  columns: [
    { name: 'code', title: 'Code', width: '36px', cell: { kind: 'text' } },
    {
      name: 'history',
      title: 'History',
      width: '100px',
      cell: { kind: 'commands' }
    }
  ]
});
assert.equal(legacyColumns[0].width, 160);
assert.equal(legacyColumns[1].width, 100);
assert.ok(legacyColumns[1].width >= 'History'.length * 8 + 20);
assert.equal(legacyColumns[1].x, legacyColumns[0].x + legacyColumns[0].width);

const short = {
  loaded: true,
  columns: [{ name: 'name', title: 'Name', cell: { kind: 'text' } }],
  rows: [{ key: 'A', record: {}, cells: {} }]
};
assert.equal(extent(short, 600), 206);
assert.equal(
  extent({ ...short, rows: [{ key: 'A' }, { key: 'B' }] }, 600),
  274
);
assert.equal(
  extent(
    {
      ...short,
      rows: Array.from({ length: 50 }, (_, i) => ({ key: String(i) }))
    },
    600
  ),
  320
);
const nested = { ...short, children: { A: { open: true, model: short } } };
const expanded = rows(nested, 600)[0];
assert.equal(expanded.extent, 68 + extent(short, 600));
assert.equal(
  row(nested, expanded, 'en', 600).nodes.find((n) => n.id === 'nestedDetail')
    .height,
  extent(short, 600)
);
const compact = columns({
  columns: [
    { name: 'rendered', title: 'Rendered', cell: { kind: 'boolean' } },
    { name: 'preview', title: 'Preview', cell: { kind: 'thumbnail' } }
  ]
});
assert.deepEqual(
  compact.map((c) => c.width),
  [84, 84]
);
assert.equal(
  columns({
    columns: [{ name: 'preview', width: 200, cell: { kind: 'thumbnail' } }]
  })[0].width,
  200
);
const fitted = describe(
  { ...short, rows: [{ key: 'A' }, { key: 'B' }] },
  600,
  274,
  'en'
);
const viewportNode = fitted.nodes.find((n) => n.id === 'nestedHorizontal');
const list = viewportNode.children.find((n) => n.id === 'nestedRows');
const footer = fitted.nodes.find((n) => n.id === 'nestedFooterSurface');
assert.equal(viewportNode.y + list.y + list.height, footer.y);

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  publicDir: root + 'frontend/public',
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  ignoreDefaultArgs: ['--hide-scrollbars'],
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 500, height: 300 },
  deviceScaleFactor: 1.5
});
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
let reads = 0;
let fileColumns = false;
const queries = [];
const suggestions = [];
await page.route('**/admin/search-configuration/suggestions', async (route) => {
  const payload = route.request().postDataJSON();
  suggestions.push(payload);
  await route.fulfill({
    json: {
      result: {
        records: [{ title: 'B', description: 'Robot reference', code: 'B' }]
      }
    }
  });
});
await page.route('**/admin/rpc', async (route) => {
  const request = route.request().postDataJSON();
  assert.equal(request.args[1], 'tactic.ui.table.NestedTableReadCmd');
  assert.ok(['child', 'table'].includes(request.args[2].view));
  reads++;
  const query = request.args[2];
  queries.push(query);
  const secondPage = query.offset > 0;
  const recordKey = secondPage ? 'demo/asset?code=C' : 'demo/asset?code=B';
  const recordCode = secondPage ? 'C' : 'B';
  await route.fulfill({
    json: {
      result: {
        info: {
          definition: {
            operations: { create: true },
            columns: fileColumns ? { file_name: {}, code: {} } : { code: {} },
            table: {
              elements: [
                {
                  name: 'code',
                  title: 'Code',
                  attributes: { width: '160' },
                  cell: {
                    kind: 'text',
                    supported: true,
                    sortable: true,
                    field: 'code'
                  }
                },
                {
                  name: 'expand',
                  title: 'Details',
                  attributes: { width: '100' },
                  cell: { kind: 'commands', supported: true }
                }
              ]
            }
          },
          records: [{ code: recordCode, __search_key__: recordKey }],
          hasNext: !secondPage,
          cells: {
            [recordKey]: {
              expand: {
                nestedTable: {
                  searchType: 'demo/asset',
                  view: 'parent',
                  parentKey: 'demo/asset?code=A'
                },
                actions: [
                  {
                    name: 'nested-table',
                    label: 'Show related table',
                    icon: 'chevron-right'
                  }
                ]
              }
            }
          }
        }
      }
    }
  });
});
try {
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html'
  );
  const root = page.locator('#app > .nested-table');
  assert(
    (await root.boundingBox()).height < 240,
    'A one-row table must fit its content'
  );
  const captures = [];
  for (const width of [320, 1000]) {
    await page.setViewportSize({ width: width + 32, height: 400 });
    await page.evaluate((width) => window.nestedFixture.resize(width), width);
    await page.waitForFunction((width) => {
      const header = document.querySelector(
        '#app > .nested-table [data-frame="nestedToolbarSurface"]'
      );
      return Math.abs(header.getBoundingClientRect().width - (width - 16)) < 1;
    }, width);
    const bounds = await root.evaluate((element) => {
      const outer = element.getBoundingClientRect();
      return Object.fromEntries(
        [
          'nestedFilter',
          'nestedReload',
          'nestedClose',
          'nestedHorizontal',
          'nestedFooterSurface'
        ].map((name) => {
          const rectangle = element
            .querySelector('[data-frame="' + name + '"]')
            .getBoundingClientRect();
          return [
            name,
            {
              x: rectangle.x - outer.x,
              y: rectangle.y - outer.y,
              width: rectangle.width,
              height: rectangle.height
            }
          ];
        })
      );
    });
    for (const [name, rectangle] of Object.entries(bounds)) {
      assert.ok(rectangle.x >= 8 && rectangle.y >= 8, name);
      assert.ok(rectangle.x + rectangle.width <= width - 8, name);
      assert.ok(rectangle.y + rectangle.height <= 312, name);
    }
    captures.push({ width, bounds });
    if (process.env.TABLE_NESTED_OUTPUT) {
      mkdirSync(process.env.TABLE_NESTED_OUTPUT, { recursive: true });
      await root.screenshot({
        path: process.env.TABLE_NESTED_OUTPUT + '/browser-' + width + '.png'
      });
    }
  }
  if (process.env.TABLE_NESTED_OUTPUT)
    writeFileSync(
      process.env.TABLE_NESTED_OUTPUT + '/browser.json',
      JSON.stringify(captures, null, 2)
    );
  await page.evaluate(() => window.nestedFixture.resize(0));
  await page.setViewportSize({ width: 500, height: 300 });

  await root.locator('[data-frame="tableServiceAction_0"]').click();
  const child = root.locator('.nested-table');
  await child.locator('[data-frame="nestedSelect"]').click();
  assert.deepEqual(
    await page.evaluate(() => window.nestedFixture.state.selected),
    []
  );
  assert.deepEqual(
    await page.evaluate(
      () => window.nestedFixture.state.children['demo/asset?code=A'].selected
    ),
    ['demo/asset?code=B']
  );
  await child.locator('[data-frame="tableServiceAction_0"]').click();
  assert.equal(
    await child.locator('[data-frame="nestedState"]').innerText(),
    'This nested table would repeat an ancestor scope'
  );
  await child.locator('[data-frame="nestedClose"]').click();
  await page.waitForFunction(
    () => !document.querySelector('#app > .nested-table .nested-table')
  );
  await root.locator('[data-frame="tableServiceAction_0"]').click();
  await child.locator('[data-frame="nestedSelect"]').waitFor();
  assert.equal(reads, 1, 'Reopening a loaded branch must not fetch again');
  assert.deepEqual(
    await page.evaluate(
      () => window.nestedFixture.state.children['demo/asset?code=A'].selected
    ),
    ['demo/asset?code=B']
  );
  await child.locator('[data-frame="nestedNext"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].rows[0]?.key ===
      'demo/asset?code=C'
  );
  assert.deepEqual(
    await page.evaluate(() => ({
      selected:
        window.nestedFixture.state.children['demo/asset?code=A'].selected,
      records:
        window.nestedFixture.state.children['demo/asset?code=A']
          .selectionRecords
    })),
    {
      selected: ['demo/asset?code=B'],
      records: { 'demo/asset?code=B': { code: 'B' } }
    }
  );
  await child.locator('[data-frame="nestedHeader_code"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].order ===
      'code asc'
  );
  assert.equal(queries.at(-1).offset, 0);
  assert.deepEqual(queries.at(-1).order_by, ['code asc']);
  const filterReads = reads;
  const search = child.locator('[data-frame="nestedFilter"] input');
  await search.fill('B');
  await page.locator('.search-suggestions:popover-open').waitFor();
  assert.equal(suggestions.at(-1).nested_scope.parent_key, 'demo/asset?code=A');
  await search.press('ArrowDown');
  assert.ok(
    await search.getAttribute('aria-activedescendant'),
    'ArrowDown highlights the native suggestion'
  );
  await search.press('Enter');
  await page.waitForFunction(
    ([prev]) =>
      !window.nestedFixture.state.children['demo/asset?code=A'].busy &&
      window.nestedFixture.state.children['demo/asset?code=A'].filter === 'B',
    [filterReads]
  );
  assert.equal(reads, filterReads + 1);
  assert.deepEqual(queries.at(-1).filters, []);
  assert.equal(queries.at(-1).keyword, 'B');
  assert.equal(queries.at(-1).keyword_relation, '=');
  await child.locator('[data-frame="nestedCreate"]').click();
  assert.deepEqual(
    await page.evaluate(() => window.nestedFixture.edits.at(-1)),
    {
      record: null,
      parentKey: 'demo/asset?code=A',
      searchType: 'demo/asset',
      projectCode: 'demo'
    }
  );
  fileColumns = true;
  await child.locator('[data-frame="nestedReload"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].filterField ===
      'file_name'
  );
  await search.fill('reference.txt');
  const fileReads = reads;
  await search.press('Enter');
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.equal(reads, fileReads + 1);
  assert.equal(queries.at(-1).keyword, 'reference.txt');
  assert.equal(queries.at(-1).keyword_relation, 'EQI');
  await search.fill('');
  await search.press('Enter');
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.equal(queries.at(-1).keyword, '');
  await child.locator('[data-frame="nestedClose"]').click();
  await page.evaluate(() => window.nestedFixture.summary());
  await root.locator('[data-frame="tableSummary_0"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].scope
        .searchType === 'sthpw/task'
  );
  await root.locator('[data-frame="tableSummary_1"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].scope
        .searchType === 'sthpw/snapshot'
  );
  await child.locator('[data-frame="nestedSelect"]').waitFor();
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html?parent'
  );
  const panel = page.locator('.nested-table');
  await panel.waitFor();
  await page.waitForFunction(() => {
    const e = document.querySelector('.nested-table');
    return (
      e &&
      Math.abs(
        e.getBoundingClientRect().height -
          e
            .closest('.handler-table-detail')
            .parentElement.getBoundingClientRect().height
      ) < 1
    );
  });
  const readsBeforeResize = reads;
  for (const width of [800, 500, 1000]) {
    await page.setViewportSize({ width, height: 660 });
    await page.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r))
        )
    );
    const bounds = await panel.boundingBox();
    assert(bounds.height < 240);
    assert(
      Math.abs(
        (await panel.evaluate(
          (e) =>
            e
              .closest('.handler-table-detail')
              .parentElement.getBoundingClientRect().height
        )) - bounds.height
      ) < 1
    );
  }
  assert.equal(
    reads,
    readsBeforeResize,
    'Resizing must not reload nested data'
  );
  await panel.locator('[data-frame=nestedClose]').click();
  await panel.waitFor({ state: 'detached' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: nested table actual first-click expansion, independent selection, cycle guard and cached reopening'
  );
} finally {
  await browser.close();
  await server.close();
}
