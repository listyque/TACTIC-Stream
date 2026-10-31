import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
const root = fileURLToPath(new URL('../../', import.meta.url));
const fields = [
  { kind: 'Heading', id: 'general', title: 'General' },
  {
    kind: 'Field',
    id: 'name',
    title: 'Name',
    description: 'Object name',
    props: { text: 'Robot Arm' }
  },
  { kind: 'Switch', id: 'enabled', title: 'Enabled', props: { checked: true } },
  {
    kind: 'Area',
    id: 'description',
    title: 'Description',
    height: 96,
    fullWidth: true
  },
  {
    kind: 'Button',
    id: 'apply',
    title: 'Apply',
    props: { action: { type: 'apply' } }
  }
];
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
await server.listen();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    channel: 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } }),
    errors = [],
    measurements = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_spacing/'
  );
  await page.waitForFunction(() => window.spacingFixture);
  for (const style of ['md3', 'material5', 'fluent'])
    for (const dark of [true, false])
      for (const width of [320, 800]) {
        await page.setViewportSize({ width, height: 600 });
        await page.evaluate(
          (options) => window.spacingFixture.configure(options),
          { fields, width, style, dark }
        );
        await page.evaluate(() => document.fonts.ready);
        const button = page.locator('[data-frame=apply]');
        await button.click();
        assert.equal(
          await page.evaluate(() => window.spacingFixture.lastEvent().type),
          'apply'
        );
        const card = await page
          .locator('[data-frame=section_general]')
          .boundingBox();
        for (const id of [
          'nameLabel',
          'enabledLabel',
          'description',
          'apply'
        ]) {
          const box = await page
            .locator('[data-frame=' + id + ']')
            .boundingBox();
          assert.equal(box.x - card.x, 12, id + ' left edge');
        }
        const last = await button.boundingBox();
        assert.equal(card.height - (last.y - card.y) - last.height, 12);
        const output = process.env.FRAME_SPACING_CAPTURE;
        if (output && style === 'md3') {
          await mkdir(output, { recursive: true });
          await page.screenshot({
            path: output + '/form-ts-' + width + '-' + dark + '.png'
          });
        }
        await page.evaluate(
          (options) => window.spacingFixture.configure(options),
          { fields, width, style, dark, mode: 'panel' }
        );
        const panel = await page.locator('.spacing-panel').evaluate((el) => {
          const s = getComputedStyle(el);
          return parseFloat(s.paddingLeft) + parseFloat(s.borderLeftWidth);
        });
        assert.equal(panel, 12);
        const row = await page.locator('.editor-list-item').evaluate((el) => ({
          height: el.getBoundingClientRect().height,
          content: el
            .querySelector('.editor-list-item-text')
            .getBoundingClientRect().height
        }));
        assert.ok(
          row.height >= row.content + 24,
          'Two-line rows keep both vertical insets'
        );
        await page.evaluate(() => window.spacingFixture.openDialog());
        const dialog = page.locator('dialog[open]'),
          body = dialog.locator('.spacing-dialog-body');
        const outer = await dialog.boundingBox(),
          inner = await body.boundingBox();
        assert.equal(
          inner.x - outer.x,
          12,
          'Dialog left content inset matches native'
        );
        assert.equal(inner.y - outer.y, 52, 'Header and one content inset');
        measurements.push({
          style,
          dark,
          width,
          panelPadding: panel,
          dialogX: inner.x - outer.x,
          dialogY: inner.y - outer.y
        });
        await body.getByRole('button', { name: 'Apply', exact: true }).click();
      }
  assert.deepEqual(errors, []);
  if (process.env.FRAME_SPACING_CAPTURE)
    await writeFile(
      process.env.FRAME_SPACING_CAPTURE + '/browser-bounds.json',
      JSON.stringify(measurements, null, 2)
    );
  console.log(
    'Real browser: 12 paired form/panel/dialog layouts, aligned insets and Apply pass without JS errors.'
  );
} finally {
  await browser?.close();
  await server.close();
}
