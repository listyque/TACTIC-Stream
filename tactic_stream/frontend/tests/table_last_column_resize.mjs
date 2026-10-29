import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  visibleColumns,
  acknowledgedWidths
} from '../../src/tactic_stream/shared_ui/features/table/columns.mjs';

const columns = [
  { name: 'code', width: 160, hideOrder: 0 },
  { name: 'notes', width: 160, hideOrder: 1 }
];
assert.deepEqual(
  visibleColumns(columns, 320, { notes: 208 }).map((column) => column.name),
  ['code', 'notes']
);
assert.deepEqual(
  visibleColumns(columns, 304, {}).map((column) => column.name),
  ['code']
);
assert.deepEqual(
  acknowledgedWidths([{ name: 'notes', width: 208 }], {
    notes: 208,
    removed: 100
  }),
  { notes: 208 }
);
assert.deepEqual(acknowledgedWidths(columns, { notes: 208 }), {});

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
    viewport: { width: 700, height: 400 },
    deviceScaleFactor: 1.5
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/header.html?last-column'
  );
  const handle = page.getByRole('slider', {
    name: 'Resize column Notes',
    exact: true
  });
  await handle.waitFor();
  await page.evaluate(() =>
    window.headerFixture.show({ dark: true, grouped: false })
  );
  const captures = [];
  async function capture(stage) {
    captures.push({
      stage,
      width: Number(await handle.getAttribute('aria-valuenow'))
    });
    if (process.env.TABLE_RESIZE_OUTPUT) {
      mkdirSync(process.env.TABLE_RESIZE_OUTPUT, { recursive: true });
      await page.locator('#app').screenshot({
        path: process.env.TABLE_RESIZE_OUTPUT + '/browser-' + stage + '.png'
      });
    }
  }
  assert.equal(await handle.getAttribute('aria-valuenow'), '160');
  await capture('initial');
  const bounds = await handle.boundingBox();
  await page.mouse.move(
    bounds.x + bounds.width / 2 + 3,
    bounds.y + bounds.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    bounds.x + bounds.width / 2 + 51,
    bounds.y + bounds.height / 2,
    { steps: 6 }
  );
  await page.mouse.up();
  await page.waitForFunction(() =>
    window.headerFixture.events.some((event) => event.type === 'width')
  );
  assert.deepEqual(
    await page.evaluate(() =>
      window.headerFixture.events.filter((event) => event.type === 'width')
    ),
    [{ type: 'width', name: 'notes', width: 208 }]
  );
  assert.equal(await handle.getAttribute('aria-valuenow'), '208');
  await capture('drag');
  assert.equal(
    await page
      .getByRole('columnheader', { name: 'Notes', exact: true })
      .count(),
    1
  );
  assert.equal(
    await page
      .locator('.handler-table')
      .evaluate((element) => element.scrollWidth > element.clientWidth),
    true
  );
  await handle.scrollIntoViewIfNeeded();
  const again = await handle.boundingBox();
  await page.mouse.move(again.x + again.width / 2, again.y + again.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    again.x + again.width / 2 - 24,
    again.y + again.height / 2
  );
  await handle.dispatchEvent('pointercancel', { pointerId: 1 });
  await page.mouse.up();
  assert.equal(await handle.getAttribute('aria-valuenow'), '208');
  await capture('cancel');
  assert.equal(
    await page.evaluate(
      () =>
        window.headerFixture.events.filter((event) => event.type === 'width')
          .length
    ),
    1
  );
  await handle.focus();
  await handle.press('ArrowLeft');
  assert.equal(await handle.getAttribute('aria-valuenow'), '200');
  await capture('keyboard');
  await page.evaluate(() => {
    const columns = window.headerFixture.columns;
    columns.value = columns.value.map((column) =>
      column.name === 'notes' ? { ...column, width: 120 } : column
    );
  });
  assert.equal(await handle.getAttribute('aria-valuenow'), '120');
  await capture('server');
  const edge = await page
    .getByRole('columnheader', { name: 'Notes', exact: true })
    .boundingBox();
  await page.mouse.move(edge.x + edge.width + 3, edge.y + edge.height / 2);
  assert.equal(
    await handle.evaluate((element) => element.matches(':hover')),
    true
  );
  await page.mouse.down();
  await page.mouse.move(edge.x + edge.width + 35, edge.y + edge.height / 2);
  await page.mouse.up();
  assert.equal(await handle.getAttribute('aria-valuenow'), '152');
  const fit = page.getByRole('button', {
    name: 'Auto Fit columns',
    exact: true
  });
  await fit.click();
  assert.equal(await fit.getAttribute('aria-pressed'), 'true');
  const views = page.locator('summary[aria-label="Table views and columns"]');
  await views.click();
  await page.waitForFunction(
    () =>
      document
        .querySelector('summary[aria-label="Table views and columns"]')
        .getAttribute('aria-expanded') === 'true',
    null,
    { timeout: 5000 }
  );
  await page.keyboard.press('Escape');
  if (process.env.TABLE_RESIZE_OUTPUT)
    writeFileSync(
      process.env.TABLE_RESIZE_OUTPUT + '/browser.json',
      JSON.stringify(captures)
    );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: last adaptive column stays mounted, commits mouse/keyboard widths and exposes overflow after acknowledgement'
  );
} finally {
  await browser.close();
  await server.close();
}
