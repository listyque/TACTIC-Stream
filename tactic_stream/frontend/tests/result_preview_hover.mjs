import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root, configFile: false, publicDir: root + 'frontend/public', plugins: [vue()],
  resolve: { alias: { vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js' } },
  server: { host: '127.0.0.1', port: 0, watch: null }, logLevel: 'error'
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 760, height: 180 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'warning') errors.push(message.text()); });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_search/index.html');
  await page.waitForFunction(() => !!window.searchFixture);
  if (process.env.PREVIEW_HOVER_OUTPUT) mkdirSync(process.env.PREVIEW_HOVER_OUTPUT, { recursive: true });
  for (const [width, language, dark] of [[360, 'ru', true], [720, 'en', false]]) {
    await page.evaluate(async ({ width, language, dark }) => {
      await window.searchFixture.show({
        screen: 'snapshot', width, height: 150, language, dark, style: 'md3', selected: true,
        node: { id: 'snapshot:hover', kind: 'snapshot', title: 'Baby_Shark.Default', depth: 0,
          hasChildren: true, expanded: true, accent: '#607d8b',
          record: { __search_key__: 'sthpw/snapshot?code=SNAP001' },
          snapshot_display: { title: 'Baby_Shark.Default', exists: true, latest: true },
          branches: [], info_items: [], progress_items: [] }
      });
      const { appearance } = await import('/frontend/src/appearance.js');
      appearance.hoverAnimations = true;
    }, { width, language, dark });
    const row = page.locator('.result-item-snapshot');
    const preview = row.locator('.result-preview');
    await page.mouse.move(750, 170);
    const resting = await preview.boundingBox();
    const geometry = await row.boundingBox();
    if (process.env.PREVIEW_HOVER_OUTPUT) await page.screenshot({ path: `${process.env.PREVIEW_HOVER_OUTPUT}/web-${width}-rest.png` });
    for (let repeat = 0; repeat < 2; repeat++) {
      await page.mouse.move(resting.x + 20, resting.y + 20);
      await page.waitForFunction(() => Math.abs(new DOMMatrix(getComputedStyle(document.querySelector('.result-preview')).transform).m42 + 3) < 0.001);
      const hovered = await preview.boundingBox();
      assert.equal(hovered.width, resting.width);
      assert.equal(hovered.height, resting.height);
      assert.equal(hovered.x, resting.x);
      assert.ok(Math.abs(hovered.y - resting.y + 3) < 0.001);
      assert.deepEqual(await row.boundingBox(), geometry);
      if (repeat === 0 && process.env.PREVIEW_HOVER_OUTPUT) await page.screenshot({ path: `${process.env.PREVIEW_HOVER_OUTPUT}/web-${width}-hover.png` });
      await page.mouse.move(750, 170);
      await page.waitForFunction(() => getComputedStyle(document.querySelector('.result-preview')).transform === 'none');
    }
    await page.evaluate(async () => {
      const { appearance } = await import('/frontend/src/appearance.js');
      appearance.hoverAnimations = false;
    });
    await preview.hover();
    assert.equal(await preview.evaluate(el => getComputedStyle(el).transform), 'none');
    await page.evaluate(async () => {
      const { appearance } = await import('/frontend/src/appearance.js');
      appearance.hoverAnimations = true;
    });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await preview.evaluate(el => getComputedStyle(el).transform), 'none');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await row.evaluate(el => el.classList.add('result-item-compact'));
    assert.equal(await preview.evaluate(el => getComputedStyle(el).transform), 'none');
    await row.evaluate(el => el.classList.remove('result-item-compact'));
  }
  assert.deepEqual(errors, []);
  console.log('Preview hover: fixed size/row, -3px lift, return, compact/disabled/reduced motion passed in RU/EN and narrow/wide layouts.');
} finally {
  await browser?.close();
  await server.close();
}
