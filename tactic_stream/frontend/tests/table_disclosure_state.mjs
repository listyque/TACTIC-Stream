import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as UI from '../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';

const scope = {
  searchType: 'demo/asset',
  view: 'history',
  parentKey: 'demo/asset?code=A'
};
const cell = {
  columnName: 'history',
  nestedTable: scope,
  actions: [{ name: 'nested-table', icon: 'chevron-right' }]
};
function icon(value, state) {
  return UI.describe(value, 100, 58, 'en', true, { __nested: state }).nodes[0]
    .children[0].icon;
}
const state = { column: 'history', scope, open: true, busy: false };
assert.equal(icon(cell, state), 'expand-more');
assert.equal(icon({ ...cell, columnName: 'copy' }, state), 'chevron-right');
assert.equal(
  icon({ ...cell, nestedTable: { ...scope, view: 'other' } }, state),
  'chevron-right'
);
assert.equal(
  icon(cell, { ...state, open: false, busy: true }),
  'chevron-right'
);
assert.equal(icon(cell, { ...state, busy: true }), 'loading');

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  publicDir: root + 'frontend/public',
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
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1000, height: 900 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/rpc', (route) =>
    route.fulfill({
      json: {
        result: { info: { layout: { columns: [], rows: {} }, records: [] } }
      }
    })
  );
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html?disclosures'
  );
  const buttons = page.locator(
    '#app > .nested-table [data-frame^="nestedCell_"] [data-frame="tableServiceAction_0"]'
  );
  await buttons.nth(5).waitFor();
  const captures = [];
  const icons = async () => {
    const values = await buttons
      .locator('[data-icon]')
      .evaluateAll((items) => items.map((item) => item.dataset.icon));
    captures.push(values);
    return values;
  };
  assert.deepEqual(await icons(), Array(6).fill('chevron-right'));
  await buttons.nth(0).click();
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await page.evaluate(() => {
    window.nestedFixture.state.children['demo/asset?code=A'].busy = true;
  });
  assert.deepEqual(await icons(), [
    'loading',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await page.evaluate(() => {
    window.nestedFixture.state.children['demo/asset?code=A'].busy = false;
  });
  await buttons.nth(1).click();
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await buttons.nth(1).click();
  assert.deepEqual(await icons(), Array(6).fill('chevron-right'));
  await buttons.nth(2).click();
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'chevron-right',
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await buttons.nth(3).click();
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=B'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'chevron-right',
    'expand-more',
    'expand-more',
    'chevron-right',
    'chevron-right'
  ]);
  assert.deepEqual(errors, []);
  if (process.env.TABLE_DISCLOSURE_OUTPUT) {
    mkdirSync(process.env.TABLE_DISCLOSURE_OUTPUT, { recursive: true });
    writeFileSync(
      process.env.TABLE_DISCLOSURE_OUTPUT + '/browser.json',
      JSON.stringify(captures)
    );
  }
  console.log(
    'PASS: disclosure and loading icons follow only the active row, column and nested scope'
  );
} finally {
  await browser.close();
  await server.close();
}
