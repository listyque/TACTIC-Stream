import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 850, height: 650 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let old;
  await page.route('**/admin/rpc', async (route) => {
    const data = route.request().postDataJSON();
    assert.equal(data.args[1], 'tactic.ui.table.CustomLayoutReadCmd');
    const query = data.args[2].filter_query;
    assert.ok(query);
    if (query.text === 'old') await new Promise((resolve) => (old = resolve));
    const value =
      query.text === 'new'
        ? 'New'
        : query.text === 'old'
          ? 'Old'
          : 'In Progress';
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        result: { info: { filterSuggestions: [{ name: 'status', value }] } }
      })
    });
  });
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_layout/page-search.html'
  );
  const input = page.getByRole('combobox', { name: 'Search this page…' });
  await input.waitFor();
  const original = await input.elementHandle();
  assert.equal(await page.locator('input[type=checkbox]').count(), 0);
  assert.equal(await page.locator('[data-frame=pageRuntimeApply]').count(), 0);
  await input.fill('sta');
  await input.press('ArrowDown');
  await input.press('Enter');
  await page.waitForFunction(
    () => document.querySelector('input[type=search]')?.value === 'Status: '
  );
  await input.fill('Status: Pro');
  await page
    .locator('.search-suggestions:popover-open u')
    .filter({ hasText: 'Pro' })
    .waitFor();
  await input.press('ArrowDown');
  await input.press('Enter');
  await page.waitForFunction(() => window.applied.length === 1);
  assert.deepEqual(await page.evaluate(() => window.applied[0].status), {
    enabled: true,
    value: 'In Progress'
  });
  assert.equal(
    await original.evaluate((node) => node.isConnected),
    true,
    'Applying a condition keeps the search input mounted'
  );
  assert.ok(
    (
      await page.locator('[data-frame=customLayout_0_value]').innerText()
    ).includes('4')
  );
  await page.locator('[data-frame=pageRuntimeRemove_status]').click();
  await page.waitForFunction(() => window.applied.length === 2);
  assert.equal(
    await page.evaluate(() => window.applied[1].status.enabled),
    false
  );
  await input.fill('Amount: 0');
  await input.press('Enter');
  await page.waitForFunction(() => window.applied.length === 3);
  assert.deepEqual(await page.evaluate(() => window.applied[2].amount), {
    enabled: true,
    value: 0
  });
  await input.fill('old');
  await page.waitForTimeout(220);
  assert.ok(old, 'The first suggestion request was dispatched');
  await input.fill('new');
  await page
    .locator('.search-suggestions:popover-open')
    .getByRole('button', { name: /New/ })
    .waitFor();
  old();
  await page.waitForTimeout(100);
  assert.equal(
    await page
      .locator('.search-suggestions:popover-open')
      .getByRole('button', { name: /Old/ })
      .count(),
    0
  );
  assert.deepEqual(errors, []);
  console.log(
    'Browser page search: house suggestions, matched text, keyboard selection, immediate metric refresh, removal, typed zero, retained input and stale responses pass'
  );
} finally {
  await browser?.close();
  await server.close();
}
