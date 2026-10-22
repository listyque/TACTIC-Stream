import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = root + 'tools/frame_docks/output/';
const reference = JSON.parse(await readFile(output + 'native.json', 'utf8'));
for (const [name, value] of Object.entries(reference.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(root + 'src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    value,
    name
  );
for (const [name, value] of Object.entries(reference.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    value,
    name
  );
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage(),
    errors = [],
    captures = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/docks.html'
  );
  await page.waitForFunction(() => !!window.dockHarness?.docks.value);
  let comparisons = 0;
  for (const sample of reference.samples) {
    await page.setViewportSize({ width: sample.width, height: sample.height });
    assert.equal(
      await page.evaluate(
        (configuration) => window.dockHarness.docks.value.apply(configuration),
        sample.configuration
      ),
      true
    );
    await page.waitForFunction(
      (width) =>
        Math.abs(
          document.querySelector('.dock-workspace').clientWidth - width
        ) < 1,
      sample.width
    );
    // The ResizeObserver owns the new projection; wait for its actual geometry.
    const native = reference.captures.find(
      (row) => row.id === sample.id && !row.original
    );
    await page
      .waitForFunction(
        (expected) =>
          Object.entries(expected).every(([id, rect]) => {
            const item = document.querySelector(`[data-dock="${id}"]`),
              box = item.getBoundingClientRect();
            return (
              item.getClientRects().length &&
              Math.abs(box.x - rect[0]) <= 1 &&
              Math.abs(box.y - rect[1]) <= 1 &&
              Math.abs(box.width - rect[2]) <= 1 &&
              Math.abs(box.height - rect[3]) <= 1
            );
          }),
        native.geometry,
        { timeout: 8000 }
      )
      .catch(async (error) => {
        console.error(
          sample.id,
          native.geometry,
          await page.evaluate(() =>
            [...document.querySelectorAll('[data-dock]')]
              .filter((item) => item.getClientRects().length)
              .map((item) => ({
                id: item.dataset.dock,
                rect: item.getBoundingClientRect().toJSON()
              }))
          )
        );
        throw error;
      });
    const geometry = await page.evaluate(() =>
      Object.fromEntries(
        [...document.querySelectorAll('[data-dock]')]
          .filter((item) => item.getClientRects().length)
          .map((item) => {
            const box = item.getBoundingClientRect();
            return [item.dataset.dock, [box.x, box.y, box.width, box.height]];
          })
      )
    );
    const original = reference.captures.find(
      (row) => row.id === sample.id && row.original
    );
    assert.deepEqual(
      Object.keys(geometry).sort(),
      Object.keys(native.geometry).sort()
    );
    for (const [id, rect] of Object.entries(geometry))
      for (let axis = 0; axis < 4; axis++) {
        assert.ok(
          Math.abs(rect[axis] - native.geometry[id][axis]) <= 1,
          sample.id + '/' + id
        );
        assert.ok(
          Math.abs(native.geometry[id][axis] - original.geometry[id][axis]) <=
            1,
          'Original/' + sample.id + '/' + id
        );
        comparisons += 2;
      }
    const image = 'browser-' + sample.id + '.png';
    await page.screenshot({ path: output + image });
    captures.push({ id: sample.id, geometry, image });
  }
  assert.deepEqual(errors, []);
  const sources = {};
  for (const name of [
    'frontend/src/features/workspace/DockWorkspace.vue',
    'frontend/src/features/workspace/docks.js',
    'frontend/src/controls/WorkspaceTabs.vue',
    'frontend/tests/frame_dock_capture.mjs',
    'tools/frame_foundation/DockHarness.vue',
    'tools/frame_foundation/docks.html'
  ])
    sources[name] = createHash('sha256')
      .update(await readFile(root + name))
      .digest('hex');
  await writeFile(
    output + 'browser.json',
    JSON.stringify({ captures, comparisons, sources }, null, 2)
  );
  console.log(
    `${captures.length} original/native/browser dock layouts, ${comparisons} rectangle values passed.`
  );
} finally {
  await browser.close();
  await server.close();
}
