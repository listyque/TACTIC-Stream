import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const out = root + 'tools/frame_search/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
async function sourceHashes(directory) {
  const result = {};
  for (const entry of await readdir(root + directory, {
    withFileTypes: true
  })) {
    if (entry.name === 'output') continue;
    const name = directory + '/' + entry.name;
    if (entry.isDirectory()) Object.assign(result, await sourceHashes(name));
    else if (/\.(vue|js|mjs|css|json|html)$/.test(name))
      result[name] = createHash('sha256')
        .update(await readFile(root + name))
        .digest('hex');
  }
  return result;
}
const browserSources = {
  ...(await sourceHashes('frontend/src')),
  ...(await sourceHashes('tools/frame_search'))
};
for (const name of [
  'frontend/tests/frame_search.mjs',
  'frontend/tests/frame_capture.mjs'
])
  browserSources[name] = createHash('sha256')
    .update(await readFile(root + name))
    .digest('hex');
async function fresh() {
  for (const [prefix, sources] of [
    [root + 'src/tactic_stream/shared_ui/', native.sha256],
    ['D:/code/th_codex/', native.nativeSources],
    [root, native.driverSources || {}],
    [root, browserSources]
  ])
    for (const [name, digest] of Object.entries(sources))
      assert.equal(
        createHash('sha256')
          .update(await readFile(prefix + name))
          .digest('hex'),
        digest,
        'Stale capture: ' + name
      );
}
await fresh();
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
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
const cases = [],
  errors = [],
  warnings = [];
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({ viewport: { width: 800, height: 700 } });
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'warning') warnings.push(message.text());
  });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_search/');
  await page.waitForFunction(() => !!window.searchFixture);
  for (const record of native.captures.filter((record) => !record.original)) {
    const fixture = record.fixture;
    await page.setViewportSize({
      width: fixture.viewportWidth,
      height: Math.max(600, fixture.height)
    });
    await page.evaluate((value) => window.searchFixture.show(value), fixture);
    await page.evaluate(() => document.fonts.ready);
    await page.mouse.move(fixture.width - 1, Math.max(500, fixture.height - 1));
    await page.locator('#search-fixture').screenshot({
      path: out + record.image.replace('-native-', '-browser-'),
      animations: 'disabled'
    });
    const actual = await surface(page, '#search-fixture');
    if (fixture.screen === 'snapshot')
      assert.equal(
        await page.locator('.middle-elide').textContent(),
        fixture.node.title,
        'A fitting snapshot filename stays complete'
      );
    if (fixture.screen === 'card') {
      const paint = await page.evaluate(
        async (images) => {
          const samples = [];
          for (const source of images) {
            const image = new Image();
            image.src = source;
            await image.decode();
            const canvas = document.createElement('canvas');
            canvas.width = image.width;
            canvas.height = image.height;
            const context = canvas.getContext('2d', {
              willReadFrequently: true
            });
            context.drawImage(image, 0, 0);
            samples.push(
              [15, 100, 230].map((y) => [
                ...context.getImageData(110, y, 1, 1).data
              ])
            );
          }
          return samples;
        },
        await Promise.all(
          [record.image, record.image.replace('-native-', '-browser-')].map(
            async (name) =>
              'data:image/png;base64,' +
              (await readFile(out + name)).toString('base64')
          )
        )
      );
      paint[0].forEach((pixel, index) =>
        pixel.forEach((channel, component) =>
          assert(
            Math.abs(channel - paint[1][index][component]) <= 2,
            record.image + ' preview/gradient paint mismatch at sample ' + index
          )
        )
      );
      assert.equal(
        await page
          .locator('.result-communication')
          .evaluate((node) => getComputedStyle(node).opacity),
        '1',
        'Nonzero card counts remain visible without hovering'
      );
      assert.equal(
        await page
          .locator('.result-task-button .app-button-badge')
          .textContent(),
        '2'
      );
      assert.equal(
        await page
          .locator('.result-note-button .app-button-badge')
          .textContent(),
        '3'
      );
    }
    let measurements = null;
    if (
      ['advanced', 'footer', 'tags', 'quick', 'visibility'].includes(
        fixture.screen
      )
    )
      measurements = await compareSurface(
        page,
        '#search-fixture',
        actual,
        record,
        record.image
      );
    cases.push({
      image: record.image.replace('-native-', '-browser-'),
      native: record.image,
      fixture,
      measurements
    });
  }
  const collections = [];
  for (const count of [100, 1000, 10000])
    for (const tile of [false, true]) {
      await page.setViewportSize({ width: 800, height: 700 });
      const started = performance.now();
      await page.evaluate(
        ([count, tile]) => window.searchFixture.collection(count, tile),
        [count, tile]
      );
      const list = page.locator('.virtual-collection');
      await list.locator('.virtual-collection-entry').first().waitFor();
      assert(
        (await list.locator('.virtual-collection-entry').count()) < 80,
        'Delegates stay bounded'
      );
      await page
        .locator('.search-fixture-scroll')
        .evaluate((element) => (element.scrollTop = element.scrollHeight));
      await list
        .locator('[data-collection-key="' + (count - 1) + '"]')
        .waitFor();
      await page.waitForFunction(
        (key) => {
          const viewport = document
            .querySelector('.search-fixture-scroll')
            .getBoundingClientRect();
          const last = document
            .querySelector('[data-collection-key="' + key + '"]')
            ?.getBoundingClientRect();
          return (
            last && last.top < viewport.bottom && last.bottom > viewport.top
          );
        },
        String(count - 1)
      );
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      const mounted = await list.locator('.virtual-collection-entry').count();
      assert(
        mounted >= 4,
        'The visible viewport must be populated, not only an offscreen focused entry'
      );
      assert(mounted < 80, 'Scrolling must not accumulate delegates');
      if (count === 100 && !tile) {
        const settled = mounted;
        await page
          .locator('.search-fixture-scroll')
          .evaluate((node) => (node.style.height = '200px'));
        await page.waitForFunction(
          (count) =>
            document.querySelectorAll('.virtual-collection-entry').length <
            count,
          settled
        );
        await page
          .locator('.search-fixture-scroll')
          .evaluate((node) => (node.style.height = '600px'));
        await page.waitForFunction(
          (count) =>
            document.querySelectorAll('.virtual-collection-entry').length >=
            count,
          settled
        );
      }
      const last = list.locator(
        '[data-collection-key="' + (count - 1) + '"] article'
      );
      await last.focus();
      await page.keyboard.press('Home');
      await page.waitForFunction(
        () =>
          document.activeElement?.closest('[data-collection-key]')?.dataset
            .collectionKey === '0'
      );
      await page.keyboard.press('End');
      await page.waitForFunction(
        (count) =>
          document.activeElement?.closest('[data-collection-key]')?.dataset
            .collectionKey === String(count - 1),
        count
      );
      collections.push({
        count,
        tile,
        mounted,
        elapsedMs: Math.round(performance.now() - started)
      });
    }
  assert.deepEqual(errors, []);
  assert.deepEqual(warnings, []);
  await fresh();
  await writeFile(
    out + 'browser.json',
    JSON.stringify(
      { status: 'passed', browserSources, cases, collections },
      null,
      2
    )
  );
  console.log(
    'Search comparison:',
    cases.length,
    'fresh QML/Vue states; actual virtualized input:',
    collections
  );
} finally {
  await browser?.close();
  await server.close();
}
