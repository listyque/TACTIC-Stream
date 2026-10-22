import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const out = root + 'tools/frame_support/output/';
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
    server.resolvedUrls.local[0] + 'tools/frame_support/index.html'
  );
  await page.waitForFunction(() => window.support);
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
    await page.evaluate((record) => window.support.configure(record), record);
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await page.evaluate(() => document.fonts.ready);
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
    const actual = await surface(page, '#support');
    const label = [
      record.screen,
      record.style,
      record.dark,
      record.language,
      record.viewportWidth,
      record.case
    ].join(':');
    const count = await compareSurface(page, '#support', actual, record, label);
    rectangles += count.rectangles;
    styles += count.styles;
    interiors += count.interiors;
    const image = record.image.replace('-native-', '-browser-');
    await page
      .locator('#support')
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
