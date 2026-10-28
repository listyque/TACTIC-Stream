import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  columns,
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
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({ viewport: { width: 500, height: 300 } });
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
  assert.deepEqual(errors, []);
  console.log(
    'PASS: nested table actual first-click expansion, independent selection, cycle guard and cached reopening'
  );
} finally {
  await browser.close();
  await server.close();
}
