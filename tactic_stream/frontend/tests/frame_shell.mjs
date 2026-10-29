import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_shell/output/';
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
        '/tools/frame_shell/index.html?mode=' +
        mode +
        '&language=' +
        language
    );
    await page.waitForFunction(
      () => window.frameAdmin?.screen.value?.scene.nodes.length > 0
    );
    await page.evaluate(() => document.fonts.ready);
    const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
    for (const phase of [
      'default',
      'workflow',
      'collapse',
      'groups',
      'locked'
    ]) {
      if (phase === 'workflow') {
        if (width >= 1000) await control('adminSection_workflow').click();
        else
          await control('administrationSectionSelector').selectOption(
            'workflow'
          );
      }
      if (phase === 'collapse') {
        if (width >= 1000) await control('adminToggleNavigation').click();
        else
          await page.evaluate(() =>
            window.frameAdmin.screen.value.dispatch({ type: 'collapse' })
          );
      }
      if (phase === 'groups') {
        if (width >= 1000) await control('adminSection_groups').click();
        else
          await control('administrationSectionSelector').selectOption('groups');
      }
      if (phase === 'locked') {
        await page.evaluate(() => {
          const f = window.frameAdmin;
          f.model.value = {
            ...f.model.value,
            locked: true,
            drafts: ['schema']
          };
        });
        await page.evaluate(() =>
          window.frameAdmin.screen.value.dispatch({ type: 'close' })
        );
      }
      await page.evaluate(() => document.activeElement.blur());
      await page.mouse.move(width - 1, height - 1);
      await page.waitForTimeout(50);
      const actual = await page.evaluate(() => {
        const f = window.frameAdmin;
        return JSON.parse(
          JSON.stringify({
            scene: f.screen.value.scene,
            state: { model: f.model.value, ui: f.screen.value.ui }
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
      const counts = await compareSurface(
        page,
        'section.administration-frame-shell',
        await surface(page, 'section.administration-frame-shell'),
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
  const inputPage = await browser.newPage({
    viewport: { width: 1400, height: 940 },
    hasTouch: true
  });
  await inputPage.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_shell/index.html?mode=dark&language=en'
  );
  const control = (id) => inputPage.locator('[data-frame="' + id + '"]');
  await control('adminToggleNavigation').click();
  await control('adminSection_rules').click();
  const bounds = await control('administrationSidebar').boundingBox();
  const action = await control('adminSection_rules').boundingBox();
  assert(
    Math.abs(action.x + action.width / 2 - bounds.x - bounds.width / 2) < 0.5
  );
  assert.equal(action.width, action.height);
  await inputPage.setViewportSize({ width: 1400, height: 500 });
  await inputPage.waitForFunction(() => {
    const el = document.querySelector(
      '[data-frame="administrationNavigation"]'
    );
    return el && el.scrollHeight > el.clientHeight;
  });
  assert(
    await control('administrationNavigation').evaluate(
      (el) => el.scrollHeight > el.clientHeight
    )
  );
  await control('adminSection_types').tap();
  await control('adminSection_rules').tap();
  assert.equal(
    await inputPage.evaluate(() => window.frameAdmin.model.value.section),
    'rules'
  );
  await control('adminToggleNavigation').click();
  await control('administrationNavigation').evaluate((el) => {
    el.scrollTop = el.scrollHeight;
  });
  await control('adminSectionTitle_rules').waitFor();
  await inputPage.close();
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
