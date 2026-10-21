import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

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
await page.route('**/admin/rpc', async (route) => {
  const request = route.request().postDataJSON();
  assert.equal(request.args[1], 'tactic.ui.table.NestedTableReadCmd');
  assert.ok(['child', 'table'].includes(request.args[2].view));
  reads++;
  await route.fulfill({
    json: {
      result: {
        info: {
          definition: {
            operations: { create: true },
            columns: { code: {} },
            table: {
              elements: [
                {
                  name: 'code',
                  title: 'Code',
                  attributes: { width: '160' },
                  cell: { kind: 'text', supported: true }
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
          records: [{ code: 'B', __search_key__: 'demo/asset?code=B' }],
          hasNext: false,
          cells: {
            'demo/asset?code=B': {
              code: { text: 'B' },
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
