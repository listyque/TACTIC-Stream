import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const out = root + 'tools/frame_configuration/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
assert.equal(native.status, 'captured');
for (const [prefix, sources] of [
  [root + 'src/tactic_stream/shared_ui/', native.sha256],
  ['D:/grav/Tactic Stream/TH/', native.nativeSources],
  [root, native.driverSources]
]) {
  for (const [name, digest] of Object.entries(sources))
    assert.equal(
      createHash('sha256')
        .update(await readFile(prefix + name))
        .digest('hex'),
      digest,
      'Stale capture: ' + name
    );
}
await mkdir(out, { recursive: true });
await writeFile(out + 'browser.json', JSON.stringify({ status: 'capturing' }));
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
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_configuration/index.html'
  );
  await page.waitForFunction(() => window.frameConfiguration);
  await page.evaluate(() => document.fonts.ready);
  let rectangles = 0,
    styles = 0,
    interiors = 0;
  const captures = [];
  for (const record of native.captures.filter((row) => !row.original)) {
    await page.setViewportSize({
      width: Math.ceil(record.width),
      height: Math.ceil(record.height)
    });
    await page.evaluate(
      (record) => window.frameConfiguration.set(record),
      record
    );
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.evaluate(() => document.fonts.ready);
    if (record.imageData)
      await page
        .locator('#configuration-fixture .image-picker img')
        .evaluateAll((images) =>
          Promise.all(images.map((image) => image.decode()))
        );
    if (record.activeFocusId) {
      await page.evaluate((id) => {
        const node = document.querySelector(
          '[data-frame="' + CSS.escape(id) + '"]'
        );
        const control = node?.matches('input,textarea,select,button')
          ? node
          : node?.querySelector('input,textarea,select,button');
        control?.focus();
      }, record.activeFocusId);
    }
    await page.mouse.move(record.width - 1, record.height - 1);
    // Qt already names these real house-control parts independently of Frame nodes.
    await page
      .locator('#configuration-fixture [data-image-picker-part]')
      .evaluateAll((parts) => {
        for (const part of parts)
          part.dataset.frame = 'imagePicker' + part.dataset.imagePickerPart;
      });
    const actual = await surface(page, '#configuration-fixture');
    const label = [
      record.screen,
      record.style,
      record.dark,
      record.language,
      record.viewportWidth,
      record.case
    ].join(':');
    const clippedActions = await page
      .locator(
        '#configuration-fixture .app-button >span:not(.app-button-badge)'
      )
      .evaluateAll((labels) =>
        labels
          .filter(
            (item) =>
              item.getBoundingClientRect().width &&
              getComputedStyle(item).overflowX === 'hidden' &&
              item.scrollWidth > item.clientWidth
          )
          .map((item) => item.textContent)
      );
    assert.deepEqual(clippedActions, [], label + ': truncated action captions');
    let count;
    try {
      count = await compareSurface(
        page,
        '#configuration-fixture',
        actual,
        record,
        label
      );
    } catch (failure) {
      console.error(
        await page.locator('#configuration-fixture').evaluate((root) =>
          [
            ...root.querySelectorAll(
              '.image-picker,.image-picker-layout,.image-picker-actions,[data-image-picker-part]'
            )
          ].map((node) => {
            const css = getComputedStyle(node);
            return {
              class: node.className,
              box: node.getBoundingClientRect().toJSON(),
              height: css.height,
              margin: css.margin,
              padding: css.padding,
              rows: css.gridTemplateRows,
              columns: css.gridTemplateColumns,
              align: css.alignItems,
              display: css.display
            };
          })
        )
      );
      throw failure;
    }
    rectangles += count.rectangles;
    styles += count.styles;
    interiors += count.interiors;
    const image = record.image.replace('-native-', '-browser-');
    await page
      .locator('#configuration-fixture')
      .screenshot({ path: out + image, animations: 'disabled' });
    captures.push({
      screen: record.screen,
      style: record.style,
      dark: record.dark,
      language: record.language,
      viewportWidth: record.viewportWidth,
      case: record.case,
      image
    });
  }
  assert.deepEqual(errors, []);
  const { readdir } = await import('node:fs/promises');
  const webSources = {};
  for (const name of await readdir(root + 'frontend/src', {
    recursive: true
  })) {
    if (!/\.(vue|js|css|json)$/.test(name)) continue;
    const relative = 'frontend/src/' + name.replaceAll('\\', '/');
    webSources[relative] = createHash('sha256')
      .update(await readFile(root + relative))
      .digest('hex');
  }
  await writeFile(
    out + 'browser.json',
    JSON.stringify(
      {
        status: 'passed',
        rectangles,
        styles,
        interiors,
        captures,
        webSources,
        sha256: native.sha256,
        nativeSources: native.nativeSources,
        driverSources: native.driverSources
      },
      null,
      2
    )
  );
  console.log(
    JSON.stringify({ pairs: captures.length, rectangles, styles, interiors })
  );
} finally {
  await browser?.close();
  await server.close();
}
