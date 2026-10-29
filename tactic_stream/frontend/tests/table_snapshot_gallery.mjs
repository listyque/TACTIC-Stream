import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  rows,
  row,
  identity
} from '../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';

const scope = {
  parentKey: 'cg/scenes?code=EP01',
  searchType: 'sthpw/snapshot',
  filters: [['process', '=', 'storyboard']]
};
assert.notEqual(
  identity(scope),
  identity({ ...scope, filters: [['process', '=', 'publish']] })
);
for (const width of [80, 360, 800]) {
  const model = {
    gallery: { scale: 150 },
    rows: Array.from({ length: 30 }, (_, index) => ({
      key: String(index),
      record: { context: 'storyboard' },
      cells: {}
    }))
  };
  const grouped = rows(model, width);
  assert.equal(grouped.flatMap((record) => record.items).length, 30);
  for (const record of grouped)
    for (const card of row(model, record, 'en', width - 16).nodes)
      assert.ok(card.x + card.width <= width - 16, JSON.stringify(card));
}

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = process.env.TABLE_GALLERY_OUTPUT;
if (output) mkdirSync(output, { recursive: true });
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
const context = await browser.newContext({
  viewport: { width: 800, height: 320 },
  deviceScaleFactor: Number(process.env.FRAME_CAPTURE_DPR || 1),
  hasTouch: true
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const captures = [];
try {
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html'
  );
  for (const language of ['en', 'ru'])
    for (const width of [360, 800]) {
      await page.setViewportSize({ width, height: 320 });
      await page.evaluate(
        (language) => window.nestedFixture.gallery(language),
        language
      );
      await page.locator('[data-frame="nestedGallery"]').waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.waitForFunction(() =>
        Array.from(
          document.querySelectorAll(
            '[data-frame^="nestedSnapshotPreview_"] img'
          )
        ).some((image) => image.complete && image.naturalWidth > 0)
      );
      const card = page.locator(
        '[data-frame="nestedSnapshot_sthpw/snapshot?code=SNAP0000"]'
      );
      assert.ok(
        (await page.locator('[data-frame^="nestedSnapshot_"]').count()) < 30
      );
      assert.equal(
        await page.locator('[data-frame="nestedHeaderSurface"]').count(),
        0
      );
      assert.equal(
        await page.locator('[data-frame="nestedReload"]').count(),
        0
      );
      await capture(language, width, 'populated');
      const count = await page.evaluate(
        () => window.nestedFixture.actions.length
      );
      await card.click();
      await card.press('Space');
      await card.tap();
      const actions = await page.evaluate(
        (count) => window.nestedFixture.actions.slice(count),
        count
      );
      assert.equal(actions.length, 3);
      assert.ok(
        actions.every(
          (action) =>
            action.kind === 'file-checkout' &&
            action.cell.targetSearchKey === 'sthpw/snapshot?code=SNAP0000'
        )
      );
      const list = page.locator('[data-frame="nestedGallery"]');
      await list.hover();
      await page.mouse.wheel(0, 1000);
      await page.waitForFunction(
        () =>
          document.querySelector('[data-frame="nestedGallery"]').scrollTop > 0
      );
      await page.evaluate(() => {
        document.activeElement?.blur();
        window.nestedFixture.state.rows = [];
        window.nestedFixture.state.hasNext = false;
      });
      assert.equal(
        await page.locator('[data-frame="nestedGalleryEmpty"]').innerText(),
        language === 'ru' ? 'Снапшоты не найдены' : 'No snapshots found'
      );
      await capture(language, width, 'empty');
    }
  assert.deepEqual(errors, []);
  if (output)
    writeFileSync(
      output + '/browser.json',
      JSON.stringify({ captures, errors }, null, 2)
    );
  console.log(
    'PASS: gallery mouse, keyboard, touch, virtualization, scrolling, empty state and 8 EN/RU captures'
  );
} finally {
  await context.close();
  await browser.close();
  await server.close();
}

async function capture(language, width, state) {
  if (!output) return;
  await page.mouse.move(width - 2, 1);
  await page.waitForTimeout(40);
  const geometry = await page.evaluate(() => {
    const result = {};
    for (const element of document.querySelectorAll('[data-frame]')) {
      const name = element.dataset.frame;
      if (!(name.startsWith('nested') && !name.includes('Bar'))) continue;
      const bounds = element.getBoundingClientRect();
      if (
        bounds.y < 0 ||
        bounds.y + bounds.height > 320 ||
        bounds.x < 0 ||
        bounds.x + bounds.width > innerWidth
      )
        continue;
      const style = getComputedStyle(element);
      result[name] = {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        fontSize: parseFloat(style.fontSize),
        weight: Number(style.fontWeight),
        color: style.color
      };
    }
    return result;
  });
  const name = `${language}-${width}-${state}`;
  await page.screenshot({ path: output + '/browser-' + name + '.png' });
  captures.push({ name, geometry });
}
