import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_rules/output/';
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
        '/tools/frame_rules/index.html?mode=' +
        mode +
        '&language=' +
        language
    );
    console.log('rules case', mode, language, width);
    await page.waitForFunction(
      () =>
        window.frameAdmin?.screen.value?.active &&
        window.frameAdmin.screen.value.revision === 'R1' &&
        window.frameAdmin.screen.value.document.rules.length === 1 &&
        !window.frameAdmin.screen.value.busy
    );
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(
      () => window.frameAdmin.screen.value.viewport.width > 100
    );
    for (const phase of [
      'catalog',
      'task_status',
      'parent_status',
      'task_create',
      'task_date',
      'custom_script',
      'python_class',
      'notification',
      'naming',
      'objects',
      'readonly',
      'unknown'
    ]) {
      await page.evaluate(async (phase) => {
        const s = window.frameAdmin.screen.value;
        if (phase === 'task_status')
          await s.dispatch({ type: 'select', index: 0 });
        if (
          [
            'task_status',
            'parent_status',
            'task_create',
            'task_date',
            'custom_script',
            'python_class'
          ].includes(phase)
        )
          await s.dispatch({ type: 'field', field: 'action', value: phase });
        if (['notification', 'naming', 'objects'].includes(phase))
          await s.dispatch({ type: 'page', value: phase });
        if (phase === 'notification') await s.dispatch({ type: 'add' });
        if (phase === 'readonly') s.canWrite = false;
        if (phase === 'unknown') {
          s.canWrite = true;
          s.uncertain = true;
        }
      }, phase);
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(50);
      const actual = await page.evaluate(() => {
        const s = window.frameAdmin.screen.value;
        return JSON.parse(
          JSON.stringify({
            scene: { toolbar: s.toolbarScene, body: s.frameScene },
            state: {
              ui: s.ui,
              document: s.document,
              dirty: !!s.dirty,
              uncertain: s.uncertain
            }
          })
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
      const root = 'section.process-dependencies-body',
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
