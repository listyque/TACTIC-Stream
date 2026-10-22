import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_scripts/output/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
async function webFingerprint() {
  const sources = {};
  for (const name of await readdir(root + 'frontend/src', {
    recursive: true
  })) {
    if (!/\.(vue|js|css|json)$/.test(name)) continue;
    const path = 'frontend/src/' + name.replaceAll('\\', '/');
    sources[path] = createHash('sha256')
      .update(await readFile(root + path))
      .digest('hex');
  }
  return sources;
}
const webSources = await webFingerprint();
assert.equal(native.status, 'captured');
for (const [prefix, sources] of [
  [root + 'src/tactic_stream/shared_ui/', native.sha256],
  [
    (process.env.HANDLER_ROOT || 'D:/grav/Tactic Stream/TH') + '/',
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
      'Stale native capture: ' + name
    );
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
    server.resolvedUrls.local[0] + 'tools/frame_scripts/index.html'
  );
  await page.waitForFunction(() => window.scriptFrame);
  for (const record of native.captures.filter(
    (row) => !row.original && ['shelf', 'bar', 'editor'].includes(row.screen)
  )) {
    await page.setViewportSize({ width: record.width, height: record.height });
    const model =
      record.screen === 'bar'
        ? {
            mode: 'shared',
            busy: record.case === 'locked',
            running: false,
            error: ''
          }
        : record.model;
    await page.evaluate((value) => window.scriptFrame.configure(value), {
      ...record,
      model
    });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    if (record.screen === 'editor')
      await page.waitForFunction((expected) => {
        const host = document.querySelector('.script-source > .code-editor');
        const box = host?.getBoundingClientRect();
        return (
          box &&
          ['x', 'y', 'width', 'height'].every(
            (key) => Math.abs(box[key] - expected[key]) <= 0.1
          ) &&
          document.querySelector('.script-source-toolbar').clientHeight >= 30
        );
      }, record.measured.boxes.scriptEditorCodeEditor);
    const actual = await surface(page, '#script-frame');
    if (record.screen === 'editor') {
      const toolbar = page.locator('.script-source-toolbar');
      assert(
        await toolbar.evaluate((node) => node.clientHeight >= 30),
        'Source commands must fit above their reserved scrollbar'
      );
      const host = await page
        .locator('.script-source > .code-editor')
        .boundingBox();
      const expectedHost = record.measured.boxes.scriptEditorCodeEditor;
      for (const key of ['x', 'y', 'width', 'height'])
        assert(
          Math.abs(host[key] - expectedHost[key]) <= 0.1,
          JSON.stringify({
            file: record.file,
            key,
            vue: host[key],
            qml: expectedHost[key]
          })
        );
    }
    const file = record.file.replace('-native-', '-browser-');
    await page
      .locator('#script-frame')
      .screenshot({ path: out + file, animations: 'disabled' });
    // Compare corresponding Frame controls; native-only triggers/history hosting and
    // the existing typed tree/tabs/source presenters retain their platform owners.
    const corresponding = Object.keys(actual.boxes).filter(
      (id) =>
        record.measured.boxes[id] &&
        !['script_triggers', 'scriptSource_saved'].includes(id)
    );
    assert(
      corresponding.length >= 5,
      'Missing shared composition: ' + record.screen
    );
    const pick = (object) =>
      Object.fromEntries(
        corresponding.filter((id) => object?.[id]).map((id) => [id, object[id]])
      );
    const expected = {
      ...record.measured,
      frameIds: corresponding,
      boxes: pick(record.measured.boxes),
      styles: pick(record.measured.styles),
      fills: pick(record.measured.fills),
      interiors: pick(record.measured.interiors)
    };
    const count = await compareSurface(
      page,
      '#script-frame',
      {
        ...actual,
        boxes: pick(actual.boxes),
        styles: pick(actual.styles),
        fills: pick(actual.fills),
        interiors: pick(actual.interiors)
      },
      expected,
      record.file
    );
    captures.push({
      screen: record.screen,
      style: record.style,
      dark: record.dark,
      language: record.language,
      width: record.width,
      height: record.height,
      case: record.case,
      file,
      count
    });
  }
  const shelf = native.captures.find(
    (row) =>
      !row.original &&
      row.screen === 'shelf' &&
      row.case === 'initial' &&
      row.width === 900 &&
      row.language === 'en'
  );
  assert.equal(shelf.buttons.length, 2);
  await page.setViewportSize({ width: shelf.width, height: shelf.height });
  await page.evaluate((value) => window.scriptFrame.configure(value), shelf);
  const pickerTrigger = page.locator(
    '[data-frame="scriptShelfPicker_0_trigger"]'
  );
  await pickerTrigger.click();
  await page.locator('.script-picker[open] .account-panel').waitFor();
  // Removing a row must also remove its pending popup before another row takes index 0.
  const remaining = {
    ...shelf,
    buttons: shelf.buttons.slice(1),
    model: { ...shelf.model, count: 1 }
  };
  await page.evaluate(
    (value) => window.scriptFrame.configure(value),
    remaining
  );
  await page.waitForFunction(
    () => !document.querySelector('.script-picker[open]')
  );
  assert.equal(await page.evaluate(() => window.scriptFrame.events.length), 0);
  await pickerTrigger.click();
  const popup = page.locator('.script-picker[open] .account-panel');
  await popup.getByLabel('Search scripts', { exact: true }).fill('publish');
  await popup.locator('[data-entry-key="tools/publish"]').click();
  const chosen = await page.evaluate(() => window.scriptFrame.events.at(-1));
  assert.equal(chosen.buttonId, shelf.buttons[1].buttonId);
  assert.equal(chosen.field, 'script');
  assert.equal(chosen.value, 'tools/publish');
  await page.evaluate((value) => window.scriptFrame.configure(value), {
    ...remaining,
    model: { ...remaining.model, uncertain: true }
  });
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="scriptShelfButtonTitle_0"]')
        ?.disabled
  );
  assert(await pickerTrigger.isDisabled());
  assert.deepEqual(errors, []);
  assert.deepEqual(
    await webFingerprint(),
    webSources,
    'Web sources changed during capture'
  );
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
  console.log(
    'PASS',
    captures.length,
    'current native/Vue compositions; full workflows are exercised separately'
  );
} finally {
  await browser?.close();
  await server.close();
}
