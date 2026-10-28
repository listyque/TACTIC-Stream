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
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1200, height: 900 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_search/');
  await page.waitForFunction(() => !!window.searchFixture);
  // A configured item can be taller than the default-card estimate.
  await page.addStyleTag({
    content:
      '#search-fixture .result-item {height:320px!important;min-height:320px!important}'
  });
  for (const tile of [false, true]) {
    await page.evaluate(
      (tile) => window.searchFixture.collection(1000, tile),
      tile
    );
    await page.locator('.virtual-collection-entry article').first().waitFor();
    await page.evaluate(
      () =>
        new Promise((resolve) => {
          let frames = 8;
          function settle() {
            if (--frames) requestAnimationFrame(settle);
            else resolve();
          }
          requestAnimationFrame(settle);
        })
    );
    const result = await page.evaluate(async () => {
      const host = document.querySelector('#search-fixture');
      const first = document.querySelector('.virtual-collection-entry');
      const overlaps = [];
      for (let step = 0; step < 60; ++step) {
        host.style.width = (step % 2 ? 805 : 780) + 'px';
        for (let frame = 0; frame < 3; ++frame) {
          await new Promise(requestAnimationFrame);
          const groups = new Map();
          for (const entry of document.querySelectorAll(
            '.virtual-collection-entry'
          )) {
            const bounds = entry.getBoundingClientRect();
            groups.set(
              bounds.top,
              Math.max(groups.get(bounds.top) || 0, bounds.bottom)
            );
          }
          const rows = [...groups].sort((a, b) => a[0] - b[0]);
          for (let index = 1; index < rows.length; ++index)
            if (rows[index - 1][1] > rows[index][0] + 1)
              overlaps.push({ step, frame, rows });
        }
      }
      return {
        overlaps: overlaps.slice(0, 1),
        retained: first === document.querySelector('.virtual-collection-entry'),
        mounted: document.querySelectorAll('.virtual-collection-entry').length
      };
    });
    assert.deepEqual(
      result.overlaps,
      [],
      (tile ? 'tiles' : 'list') + ': measured rows overlap during pane resize'
    );
    assert.ok(result.retained, 'Resizing must retain keyed delegates');
    assert.ok(result.mounted < 80, 'Resizing must retain virtualization');
    await page
      .locator('.virtual-collection-entry article')
      .first()
      .evaluate((element) => {
        element.style.setProperty('height', '430px', 'important');
        element.style.setProperty('min-height', '430px', 'important');
      });
    await page.waitForFunction(() => {
      const rows = [
        ...document.querySelectorAll('.virtual-collection-entry')
      ].map((element) => element.getBoundingClientRect());
      const first = rows[0],
        next = rows.find((row) => row.top > first.top + 1);
      return next && next.top >= first.bottom;
    });
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: list and fixed-width tiles retain measured heights through 120 pane resizes, without overlap or delegate recreation'
  );
} finally {
  await browser?.close();
  await server.close();
}
