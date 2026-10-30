import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/plugins/plugins.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const row = {
    identity: 'plugins:example',
    title: 'Example plugin',
    code: 'example',
    version: '',
    builtin: false,
    active: false,
    path: 'example'
  },
  loaded = {
    identity: row.identity,
    revision: 'revision-1',
    canWrite: true,
    document: {
      title: row.title,
      code: row.code,
      description: 'A plugin package',
      version: '',
      manifest: '<manifest><data><code>example</code></data></manifest>',
      file: null
    },
    metadata: {
      folder: '',
      files: [
        { name: 'README.md', path: 'README.md', directory: false, size: 12 }
      ],
      builtin: false,
      active: false,
      project: 'one',
      docs: 'README.md',
      docsExist: true
    }
  };
for (const width of [620, 1000, 1400])
  for (const language of ['en', 'ru'])
    for (const tab of ['info', 'manifest', 'files', 'docs']) {
      const model = {
          ...structuredClone(loaded),
          dirty: false,
          busy: false,
          uncertain: false,
          catalog: [row]
        },
        ui = { ...UI.initial(), tab };
      const scene = UI.describe(model, ui, width, 780, language);
      validateScene(scene, { plugins: [row], files: loaded.metadata.files });
      assert.ok(
        scene.nodes.every((node) => node.x >= 0 && node.x + node.width <= width)
      );
    }
assert.equal(
  UI.transition(
    UI.initial(),
    { dirty: true },
    { type: 'select', identity: 'x' }
  ).commands[0].type,
  'error'
);
assert.equal(
  UI.transition(UI.initial(), { busy: true }, { type: 'save' }).commands.length,
  0
);
assert.equal(
  UI.transition(
    { ...UI.initial(), operation: 'deactivate' },
    { metadata: {} },
    { type: 'confirm' }
  ).commands[0].values.confirmation,
  true
);
const root = fileURLToPath(new URL('../../', import.meta.url)),
  server = await createServer({
    root,
    configFile: false,
    publicDir: root + 'frontend/public',
    plugins: [vue()],
    resolve: {
      alias: {
        vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
      }
    },
    server: { host: '127.0.0.1', port: 0, watch: null },
    logLevel: 'error'
  });
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
      viewport: { width: 1000, height: 780 },
      deviceScaleFactor: 1.5
    }),
    errors = [],
    calls = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  let active = false,
    fail = false;
  await page.route('**/UploadServer/', (route) =>
    route.fulfill({ json: ['replacement.txt'] })
  );
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (body.method === 'log') return route.fulfill({ json: { result: null } });
    assert.equal(body.method, 'execute_cmd');
    assert.equal(body.args[1], 'tactic.ui.app.plugin_wdg.PluginManagerCmd');
    const args = body.args[2];
    calls.push(structuredClone(args));
    if (fail)
      return route.fulfill({
        status: 403,
        json: { error: 'Fixture access denied' }
      });
    let result = structuredClone(loaded);
    if (args.action === 'list')
      result = { catalog: [row], canWrite: true, metadata: {} };
    else if (args.action === 'new')
      result = {
        identity: '',
        revision: '',
        document: { code: '', title: '', description: '', type: '' },
        metadata: { new: true, project: 'one' },
        canWrite: true
      };
    else {
      if (args.action === 'activate') active = true;
      if (args.action === 'deactivate') {
        assert.equal(args.confirmation, true);
        active = false;
      }
      if (args.action === 'open_file')
        result.document.file = {
          path: 'README.md',
          content: '# Example',
          revision: 'file-1'
        };
      if (args.action === 'save') result.document = args.document;
      result.metadata.active = active;
    }
    return route.fulfill({ json: { result: { info: result } } });
  });
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_foundation/plugins.html'
  );
  await page.locator('[data-frame=pluginTitle]').waitFor();
  await page.locator('[data-frame=pluginAction_activate]').click();
  await page.locator('[data-frame=pluginAction_deactivate]').click();
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginAction_activate]').waitFor();
  await page.locator('[data-frame=pluginField_title]').fill('Edited plugin');
  assert.ok(await page.locator('[data-frame=pluginSave]').isEnabled());
  await page.locator('[data-frame=pluginSave]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).document.title, 'Edited plugin');
  for (const language of ['en', 'ru'])
    for (const width of [620, 1000]) {
      await page.setViewportSize({ width, height: 780 });
      await page.evaluate(
        (value) => window.pluginsHarness.language(value),
        language
      );
      await page.waitForFunction((width) => {
        const title = window.pluginsHarness
          .editor()
          .scene.nodes.find((node) => node.id === 'pluginTitle');
        return title && Math.abs(title.x + title.width - width) < 1;
      }, width);
      const outside = await page
        .locator(
          '.plugins-frame > .frame-host-body > .frame-view > [data-frame]'
        )
        .evaluateAll((elements) =>
          elements
            .filter(
              (element) =>
                element.getBoundingClientRect().right > window.innerWidth + 1
            )
            .map((element) => element.dataset.frame)
        );
      assert.deepEqual(outside, []);
      if (process.env.PLUGINS_OUTPUT) {
        await mkdir(process.env.PLUGINS_OUTPUT, { recursive: true });
        await page.screenshot({
          path:
            process.env.PLUGINS_OUTPUT +
            '/plugins-' +
            width +
            '-' +
            language +
            '.png'
        });
      }
    }
  await page.setViewportSize({ width: 1000, height: 780 });
  await page.evaluate(() => {
    window.pluginsHarness.language('en');
    window.pluginsHarness.editor().dispatch({ type: 'tab', value: 'files' });
  });
  await page.locator('[data-frame="pluginFile_README.md"]').click();
  await page
    .locator('[data-frame=pluginFileEditor] textarea')
    .fill('# Documentation changed');
  await page.locator('[data-frame=pluginSave]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).document.file.content, '# Documentation changed');
  await page.locator('[data-frame=pluginFileReplace]').click();
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.locator('[data-frame=pluginConfirm]').click()
  ]);
  await chooser.setFiles({
    name: 'replacement.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('replacement')
  });
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).action, 'upload');
  assert.equal(calls.at(-1).path, 'README.md');
  assert.equal(calls.at(-1).confirmation, true);
  await page.locator('[data-frame=pluginNew]').click();
  await page.locator('[data-frame=pluginField_code]').fill('brand_new');
  await page.locator('[data-frame=pluginSave]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).action, 'create');
  fail = true;
  await page.locator('[data-frame=pluginAction_activate]').click();
  await page.locator('[data-frame=pluginError]').waitFor();
  assert.ok(
    await page.locator('[data-frame=pluginAction_activate]').isDisabled()
  );
  fail = false;
  await page.locator('[data-frame=pluginReload]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(await page.locator('[data-frame=pluginError]').count(), 0);
  const before = calls.length;
  await page.waitForTimeout(120);
  assert.equal(calls.length, before, 'No idle polling');
  assert.deepEqual(errors, []);
  console.log(
    'Plugin browser: real pointer, keyboard/editing, confirmations, error recovery, EN/RU geometry and no idle polling passed'
  );
} finally {
  await browser?.close();
  await server.close();
}
