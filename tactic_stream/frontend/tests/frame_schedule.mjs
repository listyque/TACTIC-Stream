import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url));
const out =
  root +
  (process.env.SCHEDULE_FRAME_OUTPUT || 'tools/frame_schedule/output') +
  '/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
const digest = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
async function fresh() {
  for (const [prefix, files] of [
    [root + 'src/tactic_stream/shared_ui/', native.shared],
    ['D:/code/th_codex/', native.nativeSources],
    [root, native.driverSources]
  ])
    for (const [name, hash] of Object.entries(files))
      assert.equal(
        await digest(prefix + name),
        hash,
        'Stale schedule source ' + name
      );
}
async function fingerprints() {
  const sources = {};
  for (const name of await readdir(root + 'frontend/src', { recursive: true }))
    if (/\.(vue|css|js|mjs|json)$/.test(name))
      sources['frontend/src/' + name.replaceAll('\\', '/')] = await digest(
        root + 'frontend/src/' + name
      );
  for (const name of [
    'frontend/tests/frame_schedule.mjs',
    'frontend/tests/frame_capture.mjs',
    ...(await readdir(root + 'tools/frame_schedule'))
      .filter((name) => /\.(vue|html|mjs|py)$/.test(name))
      .map((name) => 'tools/frame_schedule/' + name)
  ])
    sources[name] = await digest(root + name);
  return sources;
}
await fresh();
const browserSources = await fingerprints();
let server, browser;
const errors = [],
  captures = [];
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [vue()],
    publicDir: root + 'frontend/public',
    resolve: {
      alias: {
        vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
      }
    },
    logLevel: 'error',
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: native.scale || 1
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_schedule/');
  await page.waitForFunction(() => !!window.scheduleFixture);
  for (const record of native.captures.filter((row) => !row.original)) {
    await page.evaluate(
      (fixture) => window.scheduleFixture.show(fixture),
      record.fixture
    );
    await page.mouse.move(1590, 990);
    if (record.fixture.screen === 'agenda') {
      await page.locator('[data-frame="calendarAgenda"]').click();
      await page.evaluate(() => new Promise(requestAnimationFrame));
    }
    if (record.fixture.screen === 'hover') {
      await page.mouse.move(480, 130);
      await page.evaluate(() => new Promise(requestAnimationFrame));
    }
    const actual = await surface(page, '#schedule-fixture');
    const expected = {
      ...record,
      frameIds: record.frameIds.filter((id) => !id.startsWith('materialIcon'))
    };
    const checked = await compareSurface(
      page,
      '#schedule-fixture',
      actual,
      expected,
      record.image
    );
    const image = record.image.replace('-native-', '-stream-');
    await page
      .locator('#schedule-fixture')
      .screenshot({ path: out + image, animations: 'disabled' });
    captures.push({ image, fixture: record.fixture, ...checked });
    console.log('Compared', image, checked.rectangles);
  }
  assert.deepEqual(errors, []);
  await fresh();
  assert.deepEqual(
    await fingerprints(),
    browserSources,
    'Sources changed during browser captures'
  );
  await writeFile(
    out + 'browser.json',
    JSON.stringify({ status: 'passed', captures, browserSources }, null, 2)
  );
  console.log('PASS production schedule pairs:', captures.length);
} finally {
  if (browser) await browser.close();
  if (server) await server.close();
}
