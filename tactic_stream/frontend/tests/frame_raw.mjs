import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_raw/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8')),
  catalog = JSON.parse(await readFile(out + 'catalog.json', 'utf8')),
  cases = JSON.parse(
    await readFile(repo + 'tools/frame_raw/cases.json', 'utf8')
  );
for (const [name, hash] of Object.entries(native.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(repo + 'src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    hash,
    'stale native capture: ' + name
  );
for (const [name, hash] of Object.entries(native.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    hash,
    'stale native renderer: ' + name
  );
const server = await createServer({
  root: repo,
  configFile: false,
  resolve: {
    alias: {
      vue: repo + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: {
      ignored: [
        '**/.tmp/**',
        '**/.venv/**',
        '**/.standalone*/**',
        '**/output/**'
      ]
    }
  }
});
await server.listen();
const url =
  'http://127.0.0.1:' +
  server.httpServer.address().port +
  '/tools/frame_raw/index.html';
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
let rectangles = 0,
  styles = 0,
  interiors = 0;
const samples = [];
try {
  const dimensions = [
    ...new Map(
      native.captures.map((s) => [
        [s.mode, s.language, s.width, s.height].join(':'),
        s
      ])
    ).values()
  ];
  for (const { mode, language, width, height } of dimensions) {
    const page = await browser.newPage({ viewport: { width, height } }),
      errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/admin/raw-database/*', (route) => {
      assert(
        /\/(list|load)$/.test(route.request().url()),
        'paired capture never writes'
      );
      return route.fulfill({ json: { result: catalog } });
    });
    await page.goto(url + '?mode=' + mode + '&language=' + language);
    await page.waitForFunction(
      () =>
        window.frameAdmin?.screen.value?.baseline &&
        !window.frameAdmin.screen.value.busy
    );
    await page.evaluate(() => document.fonts.ready);
    const dialog = page.locator('dialog.raw-cell-editor'),
      control = (id, modal = false) =>
        (modal ? dialog : page.locator('section.raw-database')).locator(
          '[data-frame="' + id + '"]'
        );
    for (const c of cases) {
      for (const event of c.actions) {
        if (event.type === 'state')
          await page.evaluate((value) => {
            const s = window.frameAdmin.screen.value;
            s.canWrite = value !== 'readonly';
            s.uncertain = value === 'uncertain';
            s.error = s.uncertain ? 'Connection failed' : '';
            s.busy = value === 'busy';
          }, event.value);
        else if (event.type === 'reveal')
          await page.locator('.frame-grid-body').evaluate((el, event) => {
            el.scrollLeft = event.column * 230;
            el.scrollTop =
              event.row *
              (parseFloat(
                getComputedStyle(el).getPropertyValue('--control-height')
              ) +
                1);
          }, event);
        else {
          const el = control(event.id, event.window === 'cell');
          if (event.type === 'text') await el.fill(event.value);
          else if (event.type === 'choose') await el.selectOption(event.value);
          else {
            const box = await el.boundingBox();
            assert(box, event.id);
            await page.mouse.click(
              box.x + box.width / 2,
              box.y + box.height / 2
            );
          }
        }
        await page.waitForTimeout(25);
      }
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(30);
      const main = await page.evaluate(() => {
        const s = window.frameAdmin.screen.value;
        return {
          scene: { toolbar: s.toolbarScene, body: s.frameScene },
          state: {
            ui: JSON.parse(JSON.stringify(s.ui)),
            dirty: s.dirty,
            uncertain: s.uncertain,
            identity: s.identity,
            rows: s.rows.map((row) => ({
              key: row.key,
              texts: row.texts,
              modes: row.modes,
              deleted: row.deleted
            }))
          }
        };
      });
      const captures = [];
      if (await dialog.isVisible()) {
        const sample = await page.evaluate(() => {
          const s = window.frameAdmin.screen.value.$refs.cellEditor;
          return {
            scene: s.scene,
            state: {
              ui: JSON.parse(JSON.stringify(s.ui)),
              readonly: s.model.readonly
            }
          };
        });
        sample.parent = main;
        captures.push({
          phase: c.phase + '-cell',
          selector: 'dialog.raw-cell-editor > .frame-view',
          sample
        });
      } else
        captures.push({
          phase: c.phase,
          selector: 'section.raw-database',
          exclude: 'dialog.raw-cell-editor',
          sample: main
        });
      for (const capture of captures) {
        const { phase, selector, exclude, sample } = capture,
          label = [mode, language, width, phase].join(' ');
        const reference = native.captures.find(
          (r) =>
            r.mode === mode &&
            r.language === language &&
            r.width === width &&
            r.phase === phase
        );
        assert(reference, label + ' native capture');
        assert.deepEqual(errors, [], label + ' runtime errors');
        assert.deepEqual(sample.state, reference.state, label + ' state');
        assert.deepEqual(sample.scene, reference.scene, label + ' graph');
        if (sample.parent)
          assert.deepEqual(
            sample.parent,
            reference.parent,
            label + ' parent draft and graph'
          );
        const measured = await surface(page, selector, exclude),
          count = await compareSurface(
            page,
            selector,
            measured,
            reference,
            label
          );
        rectangles += count.rectangles;
        styles += count.styles;
        interiors += count.interiors;
        const image =
          'raw-vue-' +
          mode +
          '-' +
          language +
          '-' +
          width +
          '-' +
          phase +
          '.png';
        if (capture.phase.endsWith('-cell'))
          await page
            .locator(selector)
            .screenshot({ path: out + image, animations: 'disabled' });
        else
          await page.screenshot({ path: out + image, animations: 'disabled' });
        samples.push({
          mode,
          language,
          width,
          height,
          phase,
          image,
          viewport: reference.viewport
        });
      }
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width,
        'no page overflow'
      );
    }
    await page.close();
  }
  await writeFile(
    out + 'vue.json',
    JSON.stringify(
      { rectangles, styles, interiors, captures: samples },
      null,
      2
    )
  );
  console.log(
    JSON.stringify({ pairs: samples.length, rectangles, styles, interiors })
  );
} finally {
  await browser.close();
  await server.close();
}
