import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_deletion/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8'));
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
const fixture = JSON.parse(await readFile(out + 'fixture.json', 'utf8'));
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
    page.setDefaultTimeout(15000);
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/admin/rpc', (route) => {
      const body = route.request().postDataJSON();
      assert.equal(body.args[2].action, 'load', 'paired capture cannot write');
      return route.fulfill({
        json: { result: { info: structuredClone(fixture) } }
      });
    });
    await page.goto(
      'http://127.0.0.1:' +
        server.httpServer.address().port +
        '/tools/frame_deletion/index.html?mode=' +
        mode +
        '&language=' +
        language
    );
    await page.waitForFunction(
      () =>
        window.frameAdmin?.screen.value?.metadata &&
        !window.frameAdmin.screen.value.busy
    );
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(
      () => window.frameAdmin.screen.value.viewport.width > 100
    );
    for (const phase of ['review', 'typed', 'blocked', 'stale', 'unknown']) {
      await page.evaluate(async (phase) => {
        const s = window.frameAdmin.screen.value;
        if (phase === 'typed')
          await s.dispatch({ type: 'confirmation', value: 'demo/asset' });
        if (phase === 'blocked') {
          s.canWrite = false;
          s.metadata = {
            ...s.metadata,
            objects: 3,
            references: [{ type: 'demo/shot', count: 2 }]
          };
        }
        if (phase === 'stale') s.schemaRevision = 'R2';
        if (phase === 'unknown') s.uncertain = true;
      }, phase);
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(50);
      const actual = await page.evaluate(() => {
        const s = window.frameAdmin.screen.value;
        return JSON.parse(
          JSON.stringify({ scene: s.frameScene, state: s.frameModel })
        );
      });
      const label = [mode, language, width, phase].join(' '),
        reference = native.captures.find(
          (s) =>
            s.mode === mode &&
            s.language === language &&
            s.width === width &&
            s.phase === phase
        );
      assert.deepEqual(errors, [], label + ' runtime errors');
      assert.deepEqual(actual.state, reference.state, label + ' state');
      assert.deepEqual(actual.scene, reference.scene, label + ' scene');
      const root = '.frame-schema-delete > .frame-host-body',
        counts = await compareSurface(
          page,
          root,
          await surface(page, root),
          reference,
          label
        );
      rectangles += counts.rectangles;
      styles += counts.styles;
      interiors += counts.interiors;
      const image =
        'vue-' + mode + '-' + language + '-' + width + '-' + phase + '.png';
      await page.screenshot({ path: out + image, animations: 'disabled' });
      samples.push({ mode, language, width, height, phase, image });
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
