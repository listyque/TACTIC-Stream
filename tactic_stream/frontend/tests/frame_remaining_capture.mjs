import assert from 'node:assert/strict';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = new URL('../../', import.meta.url).pathname.replace(
  /^\/(\w:)/,
  '$1'
);
const out = root + 'tools/frame_remaining/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
assert.equal(native.status, 'captured');
for (const [prefix, sources] of [
  [root + 'src/tactic_stream/shared_ui/', native.sha256],
  [
    (process.env.HANDLER_ROOT || 'D:/code/th_codex') + '/',
    native.nativeSources
  ],
  [root, native.driverSources]
])
  for (const [name, digest] of Object.entries(sources))
    assert.equal(
      createHash('sha256')
        .update(await readFile(prefix + name))
        .digest('hex'),
      digest,
      'Stale native source: ' + name
    );
async function fingerprint() {
  const result = {};
  for (const name of await readdir(root + 'frontend/src', {
    recursive: true
  })) {
    if (!/\.(vue|js|css|json)$/.test(name)) continue;
    const path = 'frontend/src/' + name.replaceAll('\\', '/');
    result[path] = createHash('sha256')
      .update(await readFile(root + path))
      .digest('hex');
  }
  return result;
}
const webSources = await fingerprint();
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
const captures = [],
  errors = [];
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage();
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_remaining/index.html'
  );
  await page.waitForFunction(() => window.fixture);
  for (const record of native.captures.filter((row) => row.panel)) {
    await page.setViewportSize({ width: record.width, height: record.height });
    await page.evaluate((value) => window.fixture.load(value), record);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    const actual = await surface(page, 'main');
    const count = await compareSurface(
      page,
      'main',
      actual,
      record.measured,
      record.file
    );
    const file = record.file.replace('-native.png', '-vue.png');
    await page.screenshot({ path: out + file, animations: 'disabled' });
    captures.push({ ...record, file, measured: actual, count });
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(await fingerprint(), webSources);
  await writeFile(
    out + 'browser.json',
    JSON.stringify(
      {
        status: 'passed',
        quick: native.quick,
        captures,
        sha256: native.sha256,
        nativeSources: native.nativeSources,
        webSources
      },
      null,
      2
    )
  );
  console.log('PASS', captures.length, 'current native/Vue compositions');
} finally {
  await browser?.close();
  await server.close();
}
