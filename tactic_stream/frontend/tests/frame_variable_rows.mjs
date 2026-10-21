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
const rows = (expanded = false) =>
  ['a', 'b', 'c', 'd'].map((key) => ({
    key,
    text: key.toUpperCase(),
    extent: expanded && key === 'b' ? 260 : 40
  }));
try {
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/variable_rows.html'
  );
  await page.waitForFunction(() => !!window.variableRows);
  await page.evaluate((values) => window.variableRows.set(values), rows());
  assert.equal(
    await page.evaluate(() => window.variableRows.focus(2, 'c')),
    true
  );
  const control = page.locator('[data-frame="item-c"]');
  const before = await control.boundingBox();
  await page.evaluate((values) => window.variableRows.set(values), rows(true));
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="variableRows"]').scrollTop === 260
  );
  assert.equal((await control.boundingBox()).y, before.y);
  assert.equal(
    await control.evaluate((node) => document.activeElement === node),
    true
  );
  await page.keyboard.press('Enter');
  await control.click();
  assert.equal(
    await page.evaluate(() => window.variableRows.events.value.at(-1).key),
    'c'
  );
  await page.evaluate((values) => window.variableRows.set(values), rows());
  await page.waitForFunction(
    () => document.querySelector('[data-frame="variableRows"]').scrollTop === 40
  );
  const large = Array.from({ length: 10000 }, (_, index) => ({
    key: String(index),
    text: String(index),
    extent: index % 10 ? 40 : 260
  }));
  await page.evaluate((values) => window.variableRows.set(values), large);
  assert.equal(
    await page.evaluate(() => window.variableRows.focus(8000, '8000')),
    true
  );
  assert.ok((await page.locator('[data-frame-row]').count()) < 20);
  assert.equal(
    await page
      .locator('[data-frame="item-8000"]')
      .evaluate((node) => document.activeElement === node),
    true
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: variable List actual keyboard/mouse/focus retention/10k rows in Chromium'
  );
} finally {
  await browser.close();
  await server.close();
}
