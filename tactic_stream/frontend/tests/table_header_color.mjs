import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  palette,
  cssRoles
} from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { paint } from '../../src/tactic_stream/shared_ui/features/table/host.ui.mjs';

const luminance = (rgb) =>
  rgb
    .map((v) => v / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
    .reduce((sum, v, index) => sum + v * [0.2126, 0.7152, 0.0722][index], 0);
const contrast = (a, b) =>
  (Math.max(luminance(a), luminance(b)) + 0.05) /
  (Math.min(luminance(a), luminance(b)) + 0.05);
for (const style of ['md3', 'fluent', 'material5'])
  for (const dark of [true, false]) {
    const colors = palette(
      style,
      dark,
      dark ? [41, 45, 48] : [212, 220, 225],
      dark ? [120, 166, 196] : [61, 117, 153]
    );
    assert.ok(contrast(colors[paint.header], colors[paint.headerText]) >= 4.5);
    for (const role of ['toolBar', paint.row, paint.group])
      assert.ok(
        Math.max(
          ...colors[paint.header].map((channel, index) =>
            Math.abs(channel - colors[role][index])
          )
        ) >= 16,
        style + '/' + dark + '/' + role
      );
  }
assert.notEqual(
  cssRoles[paint.header],
  '--table-header',
  'Avoid a self-referencing table CSS variable'
);
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
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
const page = await browser.newPage({
  viewport: { width: 600, height: 160 },
  deviceScaleFactor: 1
});
const output = process.env.TABLE_HEADER_OUTPUT;
if (output) mkdirSync(output, { recursive: true });
const captures = [],
  errors = [];
page.on('pageerror', (error) => errors.push(error.message));
try {
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/header.html'
  );
  for (const dark of [true, false])
    for (const grouped of [false, true]) {
      await page.evaluate(
        async ({ dark, grouped }) =>
          window.headerFixture.show({ dark, grouped }),
        { dark, grouped }
      );
      const header = page.locator('.handler-table-header');
      await header.waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      const colors = await header.evaluate((element) => ({
        background: getComputedStyle(element).backgroundColor,
        text: getComputedStyle(element.querySelector('.handler-table-heading'))
          .color
      }));
      assert.notEqual(colors.background, 'rgba(0, 0, 0, 0)');
      assert.ok(
        contrast(
          colors.background
            .match(/[\d.]+/g)
            .slice(0, 3)
            .map(Number),
          colors.text
            .match(/[\d.]+/g)
            .slice(0, 3)
            .map(Number)
        ) >= 4.5
      );
      const name = `${dark}-${grouped}`;
      if (output)
        await page.screenshot({ path: output + '/browser-' + name + '.png' });
      captures.push({ name, ...colors });
      await header.locator('[aria-label="Code"]').click({ button: 'right' });
      await page.locator('[data-menu-command="sort:ascending"] button').click();
      assert.equal(
        (await page.evaluate(() => window.headerFixture.events)).at(-1).type,
        'sort'
      );
    }
  assert.deepEqual(errors, []);
  if (output)
    writeFileSync(output + '/browser.json', JSON.stringify(captures, null, 2));
  console.log(
    'PASS: distinct header surface and readable labels across themes; grouped labels and actual sort remain intact'
  );
} finally {
  await browser.close();
  await server.close();
}
