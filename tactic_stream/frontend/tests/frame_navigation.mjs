import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { navigationRow } from '../../src/tactic_stream/shared_ui/controls/lists/tree.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url));
for (const kind of ['section', 'link', 'separator'])
  for (const width of [200, 320]) {
    const scene = navigationRow(
      width,
      { kind, title: 'Sample', badge: 120, depth: 2 },
      { selected: true }
    );
    validateScene(scene);
    for (const node of scene.nodes) assert(node.x + node.width <= width);
  }
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 900, height: 800 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/navigation.html'
  );
  await page.waitForFunction(() => !!window.navigationHarness);
  const nav = page.getByRole('navigation', { name: 'Project views' });
  const first = nav.getByRole('button', { name: 'First asset', exact: true });
  const second = nav.getByRole('button', { name: 'Second asset', exact: true });
  assert.equal((await first.boundingBox()).height, 48);
  assert.equal(await first.getAttribute('aria-pressed'), 'true');
  await second.tap();
  assert.equal(
    await page.evaluate(() => window.navigationHarness.selected),
    'second'
  );
  assert.equal(
    await page.evaluate(() => window.navigationHarness.activated),
    1
  );
  assert(
    await nav
      .getByRole('button', { name: 'Unavailable', exact: true })
      .isDisabled()
  );
  const section = nav.getByRole('button', { name: 'Assets', exact: true });
  await section.click();
  assert.equal(await first.count(), 0);
  await page.keyboard.press('ArrowRight');
  assert.equal(await first.count(), 1);
  await first.focus();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Space');
  assert.equal(
    await page.evaluate(() => window.navigationHarness.activated),
    2
  );
  await page
    .getByRole('textbox', { name: 'Search navigation' })
    .fill('Second asset');
  assert.equal(await first.count(), 0);
  assert.equal(await second.count(), 1);
  const row = second.locator('..'),
    scene = navigationRow(
      320,
      {
        kind: 'link',
        title: 'Second asset',
        icon: 'folder',
        accent: '#bb4488',
        depth: 1
      },
      { selected: true }
    );
  await page.waitForFunction(() => {
    const row = document
      .querySelector('[data-entry-key="second"]')
      .closest('.navigation-row');
    return (
      Math.abs(
        row
          .querySelector('[data-frame="sidebarRowSurface"]')
          .getBoundingClientRect().width -
          row.clientWidth +
          24
      ) < 0.6
    );
  });
  const origin = await row.boundingBox();
  for (const node of scene.nodes) {
    const box = await row
      .locator('[data-frame="' + node.id + '"]')
      .boundingBox();
    for (const key of ['width', 'height'])
      assert(Math.abs(box[key] - node[key]) < 0.6, node.id + '.' + key);
    assert(Math.abs(box.x - origin.x - node.x) < 0.6, node.id + '.x');
    assert(Math.abs(box.y - origin.y - node.y) < 0.6, node.id + '.y');
  }
  assert.deepEqual(errors, []);
  console.log(
    'Navigation: shared row geometry, first tap, selection, disabled, collapse, keyboard and full-text filter passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
