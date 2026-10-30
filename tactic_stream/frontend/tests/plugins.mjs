import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
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
    for (const tab of ['info', 'details', 'manifest', 'files', 'docs']) {
      const model = {
          ...structuredClone(loaded),
          dirty: false,
          busy: false,
          uncertain: false,
          catalog: [row]
        },
        ui = { ...UI.initial(), tab };
      const scene = UI.describe(model, ui, width, 780, language);
      validateScene(
        scene,
        { plugins: [row], files: loaded.metadata.files },
        { pluginTools: {} }
      );
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
const staged = UI.transition(
  {
    ...UI.initial(),
    operation: 'install',
    source: 'url',
    url: 'https://example.org/plugin.zip'
  },
  { metadata: {} },
  { type: 'confirm' }
);
assert.equal(
  staged.ui.operation,
  'install',
  'Retain the installation instructions until the server responds'
);
assert.equal(staged.commands[0].action, 'download_url');
assert.equal(
  UI.transition(
    staged.ui,
    { metadata: {} },
    { type: 'completed', action: 'install' }
  ).ui.operation,
  ''
);
assert.equal(
  UI.transition(
    UI.initial(),
    { metadata: { new: true }, document: { code: '' } },
    { type: 'save' }
  ).commands.length,
  0
);
assert.deepEqual(
  UI.actions(
    { ...loaded, metadata: { ...loaded.metadata, active: true } },
    'en'
  ).map((row) => row.command),
  ['reload', 'deactivate', 'clear_spt', 'delete']
);
assert.deepEqual(
  UI.actions(
    { ...loaded, metadata: { ...loaded.metadata, builtin: true } },
    'en'
  ).map((row) => row.command),
  ['clean']
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
    fail = false,
    empty = false;
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
      result = { catalog: empty ? [] : [row], canWrite: true, metadata: {} };
    else if (args.action === 'new')
      result = {
        identity: '',
        revision: '',
        document: { code: '', title: '', description: '', type: '' },
        metadata: { new: true, project: 'one' },
        canWrite: true
      };
    else {
      if (['install', 'download_url', 'create'].includes(args.action)) {
        empty = false;
        result.catalog = [row];
      }
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
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginAction_deactivate]').click();
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginAction_activate]').waitFor();
  await page.evaluate(() =>
    window.pluginsHarness.editor().dispatch({ type: 'tab', value: 'details' })
  );
  await page.locator('[data-frame=pluginField_title]').fill('Edited plugin');
  assert.ok(await page.locator('[data-frame=pluginSave]').isEnabled());
  await page.locator('[data-frame=pluginSave]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).document.title, 'Edited plugin');
  await page.evaluate(() =>
    window.pluginsHarness.editor().dispatch({ type: 'tab', value: 'info' })
  );
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
        return title && title.x + title.width <= width;
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
  assert.ok(await page.locator('[data-frame=pluginCreate]').isDisabled());
  await page.locator('[data-frame=pluginField_title]').fill('Brand new');
  await page.locator('[data-frame=pluginField_code]').fill('brand_new');
  await page.locator('[data-frame=pluginEditorScroll]').evaluate((element) => {
    element.scrollTop = 100;
  });
  await page.locator('[data-frame=pluginCreate]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(calls.at(-1).action, 'create');
  assert.equal(
    await page
      .locator('[data-frame=pluginEditorScroll]')
      .evaluate((element) => element.scrollTop),
    0
  );
  fail = true;
  await page.locator('[data-frame=pluginAction_activate]').click();
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginError]').waitFor();
  assert.ok(
    await page.locator('[data-frame=pluginAction_activate]').isDisabled()
  );
  fail = false;
  await page.locator('[data-frame=pluginReload]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(await page.locator('[data-frame=pluginError]').count(), 0);
  async function capture(state, names) {
    if (!process.env.PLUGINS_OUTPUT) return;
    await mkdir(process.env.PLUGINS_OUTPUT, { recursive: true });
    for (const language of ['en', 'ru'])
      for (const width of [620, 1000]) {
        await page.setViewportSize({ width, height: 780 });
        await page.evaluate(
          (value) => window.pluginsHarness.language(value),
          language
        );
        await page.waitForFunction(
          (width) =>
            document.querySelector('.frame-host-body').clientWidth === width,
          width
        );
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))
            )
        );
        const boxes = {};
        for (const name of names) {
          const locator = page.locator('[data-frame="' + name + '"]');
          boxes[name] = await locator.boundingBox();
          assert.ok(boxes[name].x + boxes[name].width <= width + 0.5, name);
        }
        const stem = 'guided-' + state + '-' + width + '-' + language;
        if (process.env.PLUGINS_NATIVE) {
          const reference = JSON.parse(
            await readFile(
              process.env.PLUGINS_NATIVE + '/' + stem + '.json',
              'utf8'
            )
          );
          for (const name of names)
            for (const key of ['x', 'y', 'width', 'height'])
              assert.ok(
                Math.abs(boxes[name][key] - reference[name][key]) < 1,
                stem +
                  ': ' +
                  name +
                  '.' +
                  key +
                  ' ' +
                  boxes[name][key] +
                  ' != ' +
                  reference[name][key]
              );
        }
        await writeFile(
          process.env.PLUGINS_OUTPUT + '/' + stem + '.json',
          JSON.stringify(boxes)
        );
        await page.screenshot({
          path: process.env.PLUGINS_OUTPUT + '/' + stem + '.png'
        });
      }
    await page.setViewportSize({ width: 1000, height: 780 });
    await page.evaluate(() => window.pluginsHarness.language('en'));
  }
  empty = true;
  active = false;
  await page.locator('[data-frame=pluginReload]').click();
  await page.locator('[data-frame=pluginEmptyInstall]').waitFor();
  assert.equal(
    await page.locator('[data-frame=pluginCatalogue]').count(),
    0,
    'No empty catalogue column'
  );
  assert.equal(
    await page.locator('[data-frame=pluginSave]').count(),
    0,
    'No idle save/discard clutter'
  );
  await capture('start', [
    'pluginWelcomeTitle',
    'pluginWelcomeIntro',
    'pluginEmptyInstall',
    'pluginEmptyNew'
  ]);
  await page.locator('[data-frame=pluginEmptyNew]').click();
  await page.locator('[data-frame=pluginField_code]').waitFor();
  assert.ok(await page.locator('[data-frame=pluginCreate]').isDisabled());
  await capture('create', [
    'pluginTitle',
    'pluginCreateIntro',
    'pluginField_title',
    'pluginField_code',
    'pluginCreate',
    'pluginCancelCreate'
  ]);
  await page.locator('[data-frame=pluginCancelCreate]').click();
  await page.locator('[data-frame=pluginEmptyInstall]').click();
  await capture('zip', [
    'pluginOperationTitle',
    'pluginInstallSource',
    'pluginZipInstructions',
    'pluginBrowseZip',
    'pluginCancel'
  ]);
  await page
    .locator('[data-frame=pluginInstallSource]')
    .getByRole('radio')
    .nth(1)
    .click();
  assert.ok(await page.locator('[data-frame=pluginConfirm]').isDisabled());
  await page
    .locator('[data-frame=pluginInstall_url]')
    .fill('https://example.org/plugin.zip');
  await capture('url', [
    'pluginOperationTitle',
    'pluginInstallSource',
    'pluginInstall_url',
    'pluginConfirm',
    'pluginCancel'
  ]);
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginResult]').waitFor();
  assert.equal(calls.at(-1).action, 'download_url');
  assert.equal(active, false);
  await page.locator('[data-frame=pluginAction_activate]').click();
  assert.equal(active, false, 'Review alone must not activate');
  await capture('activation', [
    'pluginOperationTitle',
    'pluginOperationContext',
    'pluginConfirm',
    'pluginCancel'
  ]);
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.locator('[data-frame=pluginAction_deactivate]').waitFor();
  assert.equal(active, true);
  await page
    .locator('[data-frame=pluginToolsMenu]')
    .getByRole('button')
    .click();
  await page
    .getByRole('button', { name: 'Reload plugin', exact: true })
    .click();
  await page.locator('[data-frame=pluginOperationTitle]').waitFor();
  await page.locator('[data-frame=pluginCancel]').click();
  await page.locator('[data-frame=pluginInstall]').click();
  const [packageChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.locator('[data-frame=pluginBrowseZip]').click()
  ]);
  await packageChooser.setFiles({
    name: 'package.zip',
    mimeType: 'application/zip',
    buffer: Buffer.from('fixture only; the command is mocked')
  });
  await page.locator('[data-frame=pluginResult]').waitFor();
  assert.equal(calls.at(-1).action, 'install');
  empty = true;
  await page.locator('[data-frame=pluginInstall]').click();
  await page.evaluate(() => window.pluginsHarness.project('two'));
  await page.locator('[data-frame=pluginEmptyInstall]').waitFor();
  assert.equal(
    (await page.evaluate(() => window.pluginsHarness.editor().ui)).operation,
    ''
  );
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
