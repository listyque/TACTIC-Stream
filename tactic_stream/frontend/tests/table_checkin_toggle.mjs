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
    viewport: { width: 1100, height: 700 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/checkin_toggle.html'
  );
  await page.waitForFunction(() => window.checkinToggle?.$refs.docks);
  const button = page.getByRole('button', { name: 'Check-in', exact: true });
  const plate = page.locator('[data-dock="drop_plate"]');
  assert.equal(await plate.isVisible(), false);
  await button.click();
  await plate.waitFor({ state: 'visible' });
  assert.deepEqual(
    await page.evaluate(() => ({
      key: window.checkinToggle.tableCheckinTarget.searchKey,
      process: window.checkinToggle.tableCheckinTarget.process,
      context: window.checkinToggle.tableCheckinTarget.context
    })),
    { key: 'demo/asset?code=A', process: 'model', context: 'model/review' }
  );
  await page.evaluate(() => {
    window.checkinToggle.draft = ['keep.txt'];
  });
  await button.click();
  await plate.waitFor({ state: 'hidden' });
  assert.deepEqual(
    await page.evaluate(() => ({
      draft: window.checkinToggle.draft,
      clears: window.checkinToggle.clears,
      leaveChecks: window.checkinToggle.leaveChecks
    })),
    { draft: ['keep.txt'], clears: 1, leaveChecks: 1 }
  );
  await button.click();
  await plate.waitFor({ state: 'visible' });
  assert.deepEqual(
    await page.evaluate(() => ({
      draft: window.checkinToggle.draft,
      clears: window.checkinToggle.clears,
      leaveChecks: window.checkinToggle.leaveChecks
    })),
    { draft: ['keep.txt'], clears: 1, leaveChecks: 1 }
  );
  await button.click();
  await plate.waitFor({ state: 'hidden' });
  // Opening another target still uses the existing discard guard.
  await page.evaluate(() => {
    window.checkinToggle.record = {
      __search_key__: 'demo/asset?code=B',
      code: 'B'
    };
  });
  await button.click();
  assert.equal(await plate.isVisible(), false);
  await page.evaluate(() => {
    window.checkinToggle.draft = [];
  });
  await button.click();
  await plate.waitFor({ state: 'visible' });
  await page.evaluate(async () => {
    const docks = window.checkinToggle.$refs.docks;
    docks.show('tasks');
    docks.move('tasks', 'center', 'drop_plate');
  });
  await plate.waitFor({ state: 'hidden' });
  await button.click();
  await plate.waitFor({ state: 'visible' });
  // Non-table callers (Task Work) retain their explicit open behavior.
  await page.evaluate(() => {
    const host = window.checkinToggle;
    return host.openTableCheckin(host.record, host.cell, 'demo');
  });
  assert.equal(await plate.isVisible(), true);
  assert.equal(
    await page.evaluate(() => {
      const docks = window.checkinToggle.$refs.docks;
      const layout = docks.capture();
      layout.panels.find((panel) => panel.panel_id === 'drop_plate').dock_area =
        'floating';
      return docks.apply(layout);
    }),
    true
  );
  await button.click();
  await plate.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: real table check-in input toggles the dock, preserves staged state on hide, raises covered tabs and keeps non-table opening explicit'
  );
} finally {
  await browser.close();
  await server.close();
}
