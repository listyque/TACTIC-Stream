import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/projects.ui.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_admin/output/projects/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8'));
const samples = native.captures;
for (const [path, expected] of Object.entries(native.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(root + 'src/tactic_stream/shared_ui/' + path))
      .digest('hex'),
    expected,
    'Stale capture: ' + path
  );
for (const [path, expected] of Object.entries(native.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + path))
      .digest('hex'),
    expected,
    'Stale native source: ' + path
  );
const fixture = JSON.parse(
  await readFile(root + 'tools/frame_admin/project_picker.json', 'utf8')
);
assert.deepEqual(
  UI.projects(fixture, 'TRACKER').map((p) => p.value),
  ['ai_tracker']
);
assert.deepEqual(
  UI.projects(fixture, 'трекер').map((p) => p.value),
  ['ai_tracker']
);
assert.equal(UI.projects(fixture, 'city template').length, 1);
assert.equal(UI.projects(fixture, 'not present').length, 0);
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
  server: { host: '127.0.0.1', port: 0 }
});
await server.listen();
const browser = await chromium.launch({
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars'],
  headless: true
});
const url =
  'http://127.0.0.1:' +
  server.httpServer.address().port +
  '/tools/frame_admin/project_picker.html';
let pairs = 0,
  rectangles = 0;
try {
  for (const dark of [true, false])
    for (const language of ['en', 'ru'])
      for (const [width, height] of [
        [1100, 760],
        [360, 640]
      ]) {
        const context = await browser.newContext({
            viewport: { width, height },
            hasTouch: true
          }),
          page = await context.newPage(),
          errors = [];
        page.on('pageerror', (e) => errors.push(e.message));
        await page.goto(
          url + '?language=' + language + '&mode=' + (dark ? 'dark' : 'light')
        );
        await page.evaluate(() => document.fonts.ready);
        const control = (id) => page.locator('[data-frame="' + id + '"]');
        await control('administrationProjectSelector').click();
        const search = control('administrationProjectSearch');
        await search.waitFor();
        const host = search.locator('..');
        for (const phase of ['open', 'filtered', 'empty']) {
          if (phase !== 'open')
            await search.fill(phase === 'filtered' ? 'city' : 'no_match');
          await page.waitForTimeout(30);
          const sample = await host.evaluate((el) => {
            const origin = el.getBoundingClientRect(),
              boxes = {},
              styles = {};
            for (const node of el.querySelectorAll('[data-frame]')) {
              const box = node.getBoundingClientRect();
              let visible = box.width > 0 && box.height > 0;
              for (
                let p = node.parentElement;
                p && p !== el;
                p = p.parentElement
              ) {
                if (
                  /auto|scroll|hidden/.test(
                    getComputedStyle(p).overflow + getComputedStyle(p).overflowY
                  )
                ) {
                  const clip = p.getBoundingClientRect();
                  if (box.bottom <= clip.top || box.top >= clip.bottom)
                    visible = false;
                }
              }
              if (!visible) continue;
              boxes[node.dataset.frame] = {
                x: box.x - origin.x,
                y: box.y - origin.y,
                width: box.width,
                height: box.height
              };
              const css = getComputedStyle(node);
              styles[node.dataset.frame] = {
                fontSize: parseFloat(css.fontSize),
                weight: Number(css.fontWeight)
              };
            }
            return { boxes, styles };
          });
          const ref = samples.find(
            (s) =>
              s.dark === dark &&
              s.language === language &&
              s.width === width &&
              s.phase === phase
          );
          assert(ref);
          for (const [id, box] of Object.entries(sample.boxes)) {
            const expected = ref.boxes[id];
            assert(expected, 'Missing native ' + id);
            for (const key of ['x', 'y', 'width', 'height'])
              assert(
                Math.abs(expected[key] - box[key]) < 1.1,
                JSON.stringify({
                  id,
                  key,
                  expected: expected[key],
                  actual: box[key],
                  width,
                  language,
                  phase
                })
              );
            rectangles++;
          }
          await host.screenshot({
            path:
              out +
              'vue-' +
              dark +
              '-' +
              language +
              '-' +
              width +
              '-' +
              phase +
              '.png'
          });
          pairs++;
        }
        await search.fill('city_template');
        await search.press('ArrowDown');
        await page.keyboard.press('Enter');
        await page.waitForFunction(
          () =>
            window.projectPickerHarness.model.value.project === 'city_template'
        );
        await control('administrationProjectSelector').tap();
        await search.waitFor();
        await page.keyboard.press('Escape');
        await search.waitFor({ state: 'hidden' });
        await control('administrationProjectSelector').tap();
        await search.fill('ai_tracker');
        await control('administrationProjectOption_ai_tracker').tap();
        assert.equal(
          await page.evaluate(
            () => window.projectPickerHarness.model.value.project
          ),
          'ai_tracker'
        );
        await control('administrationProjectSelector').click();
        await page.evaluate(
          () => (window.projectPickerHarness.model.value.locked = true)
        );
        assert(await control('administrationProjectSelector').isDisabled());
        await search.waitFor({ state: 'hidden' });
        assert.deepEqual(errors, []);
        await context.close();
      }
  await writeFile(
    out + 'vue.json',
    JSON.stringify({ pairs, rectangles }, null, 2)
  );
  console.log(
    JSON.stringify({
      pairs,
      rectangles,
      keyboard: true,
      touch: true,
      locked: true
    })
  );
} finally {
  await browser.close();
  await server.close();
}
