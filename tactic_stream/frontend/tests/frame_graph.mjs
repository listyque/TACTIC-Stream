import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_graph/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8')),
  cases = JSON.parse(await readFile(out + 'cases.json', 'utf8'));
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
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
let rectangles = 0,
  styles = 0,
  interiors = 0;
const samples = [];
// QV4 and V8 differ in the last floating-point bits after camera division.
const normalized = (value) =>
  JSON.parse(
    JSON.stringify(value, (_key, item) =>
      typeof item === 'number' ? Math.round(item * 1e6) / 1e6 : item
    )
  );
try {
  for (const { mode, language, width, height } of [
    ...new Map(
      native.captures.map((s) => [
        [s.mode, s.language, s.width, s.height].join(':'),
        s
      ])
    ).values()
  ]) {
    const page = await browser.newPage({ viewport: { width, height } }),
      errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(
      'http://127.0.0.1:' +
        server.httpServer.address().port +
        '/tools/frame_graph/index.html?mode=' +
        mode +
        '&language=' +
        language
    );
    await page.waitForFunction(() => window.frameGraph?.canvas.value);
    await page.evaluate(() => document.fonts.ready);
    for (const c of cases) {
      for (const action of c.actions) {
        if (action.type === 'clickControl')
          await page.locator('[data-frame="' + action.id + '"]').click();
        else if (action.type === 'key') {
          await page.locator('.graph-camera').focus();
          await page.keyboard.press(
            action.key === 'Right' ? 'ArrowRight' : action.key
          );
        } else if (action.type === 'click')
          await page.mouse.click(action.x, action.y);
        else {
          await page.mouse.move(action.x, action.y);
          await page.mouse.down();
          await page.mouse.move(action.toX, action.toY);
          await page.mouse.up();
        }
      }
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(35);
      const actual = await page.evaluate(() => {
        const s = window.frameGraph;
        return {
          scene: { body: JSON.parse(JSON.stringify(s.node.value)) },
          state: JSON.parse(
            JSON.stringify({
              ui: s.canvas.value.ui,
              graph: s.graph.value,
              commands: s.commands.value
            })
          )
        };
      });
      const label = [mode, language, width, c.phase].join(' '),
        reference = native.captures.find(
          (s) =>
            s.mode === mode &&
            s.language === language &&
            s.width === width &&
            s.phase === c.phase
        );
      assert.deepEqual(errors, [], label + ' runtime errors');
      assert.deepEqual(
        normalized(actual.state),
        normalized(reference.state),
        label + ' state'
      );
      assert.deepEqual(
        normalized(actual.scene),
        normalized(reference.scene),
        label + ' graph'
      );
      const counts = await compareSurface(
        page,
        '#app',
        await surface(page, '#app'),
        reference,
        label
      );
      rectangles += counts.rectangles;
      styles += counts.styles;
      interiors += counts.interiors;
      const image =
        'graph-vue-' +
        mode +
        '-' +
        language +
        '-' +
        width +
        '-' +
        c.phase +
        '.png';
      await page.screenshot({ path: out + image, animations: 'disabled' });
      samples.push({ mode, language, width, height, phase: c.phase, image });
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
