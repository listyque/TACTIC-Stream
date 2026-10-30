// Real disposable backend supplied by PLUGIN_FIXTURE_URL; no user preset/ticket.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as Resources from '../../src/tactic_stream/shared_ui/features/administration/plugins/plugins.resources.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Layout from '../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/plugins/plugins.ui.mjs';
import { listRowHeight } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const endpoint = process.env.PLUGIN_FIXTURE_URL;
for (const [id, rowHeight, record] of [
  [
    'pluginResources',
    48,
    { key: 'a', title: 'Widget', kind: 'widget', field: 'config' }
  ],
  [
    'pluginCatalogue',
    76,
    { identity: 'plugins:a', title: 'Package', path: 'a' }
  ],
  [
    'pluginFiles',
    40,
    { name: 'README.md', path: 'README.md', directory: false }
  ]
]) {
  const list = { id, width: 250, rowHeight },
    model = { document: { resource: { key: 'a' } }, identity: 'plugins:a' };
  for (const node of UI.row(list, record, model, 'en').nodes)
    assert.ok(
      node.y + node.height <= listRowHeight(list),
      `${id}/${node.id} exceeds its row`
    );
}
const widget = JSON.parse(
  await readFile(new URL('./fixtures/plugin_widget.json', import.meta.url))
);
const widgetScene = Layout.describe(widget, 600, 500, 'en');
validateScene(widgetScene, {}, {});
function flatten(nodes) {
  return nodes.flatMap((node) => [node, ...flatten(node.children || [])]);
}
const notes = flatten(widgetScene.nodes).find(
  (node) => node.id === 'customLayout_0_notesButton'
);
assert.equal(notes.action.name, 'notes');
assert.equal(notes.action.targetSearchKey, widget.targetSearchKey);
assert.equal(notes.action.record.progress, 65);
const source =
  "<config><sample><theme style = 'md3'><light accent = '#123456' base='#ffffff'/><dark base='#202020' accent='#abcdef'/></theme></sample></config>";
assert.ok(
  Resources.themeSource(source, 'light_accent', '#987654').includes(
    "accent = '#987654'"
  )
);
assert.ok(
  Resources.themeSource(source, 'light_accent', '#987654').includes(
    "accent='#abcdef'"
  )
);
assert.ok(
  Resources.themeSource(source, 'style', 'fluent').includes("style = 'fluent'")
);
assert.match(endpoint || '', /^http:\/\/127\.0\.0\.1:\d+\/fixture$/);
const root = fileURLToPath(new URL('../../', import.meta.url));
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
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
      viewport: { width: 1000, height: 900 },
      deviceScaleFactor: 1.5
    }),
    errors = [],
    calls = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.route('**/admin/rpc', async (route) => {
    const request = route.request().postDataJSON();
    if (request.method === 'log')
      return route.fulfill({ json: { result: null } });
    assert.equal(request.method, 'execute_cmd');
    assert.equal(request.args[1], 'tactic.ui.app.plugin_wdg.PluginManagerCmd');
    const args = request.args[2];
    calls.push(args.action);
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method: 'execute_cmd', args })
    });
    const body = await response.json();
    return route.fulfill({ status: response.status, json: body });
  });
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_foundation/plugins.html'
  );
  await page.locator('[data-frame=pluginTitle]').waitFor();
  const dispatch = async (action) => {
    await page.evaluate(
      (value) => window.pluginsHarness.editor().dispatch(value),
      action
    );
    await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
    assert.equal(
      await page.evaluate(() => window.pluginsHarness.editor().error),
      ''
    );
  };
  await dispatch({ type: 'tab', value: 'resources' });
  const model = await page.evaluate(() => window.pluginsHarness.editor().model);
  assert.ok(model.metadata.resources.some((r) => r.kind === 'column'));
  for (const width of [620, 1000])
    for (const language of ['en', 'ru']) {
      await page.setViewportSize({ width, height: 900 });
      await page.evaluate(
        (value) => window.pluginsHarness.language(value),
        language
      );
      await page.waitForTimeout(60);
      if (process.env.PLUGINS_OUTPUT) {
        await mkdir(process.env.PLUGINS_OUTPUT, { recursive: true });
        const stem =
          process.env.PLUGINS_OUTPUT + '/resources-' + width + '-' + language;
        await page.screenshot({ path: stem + '-browser.png' });
        const names = [
          'pluginTitle',
          'pluginTabs',
          'pluginAddResource',
          'pluginResources',
          'pluginResourceSelected',
          'pluginResourceMode'
        ];
        const boxes = {};
        for (const name of names) {
          const box = await page
            .locator('[data-frame="' + name + '"]')
            .boundingBox();
          assert.ok(box, name);
          boxes[name] = box;
        }
        await writeFile(stem + '-browser.json', JSON.stringify(boxes));
        if (process.env.PLUGINS_NATIVE) {
          const native = JSON.parse(
            await readFile(
              process.env.PLUGINS_NATIVE +
                '/resources-' +
                width +
                '-' +
                language +
                '-native.json'
            )
          );
          for (const [name, box] of Object.entries(boxes))
            for (const axis of ['x', 'y', 'width', 'height'])
              assert.ok(
                Math.abs(box[axis] - native[name][axis]) <= 1.5,
                `${name}.${axis}: ${box[axis]} vs ${native[name][axis]}`
              );
        }
      }
    }
  await page.setViewportSize({ width: 1000, height: 900 });
  await page.evaluate(() => window.pluginsHarness.language('en'));
  await page.locator('[data-frame=pluginAddResource]').click();
  await page
    .locator('[data-frame=pluginResourceInput_resourceName]')
    .fill('browser_extra_' + Date.now());
  await page.locator('[data-frame=pluginResourceCreate]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.match(
    await page.evaluate(
      () => window.pluginsHarness.editor().model.document.resource.title
    ),
    /^browser_extra_/
  );
  let current = await page.evaluate(() => window.pluginsHarness.editor().model);
  const theme = current.metadata.resources.find((r) => r.kind === 'theme');
  await dispatch({ type: 'resource', key: theme.key });
  await dispatch({
    type: 'resource-theme',
    field: 'light_accent',
    value: '#246b7b'
  });
  await page.locator('[data-frame=pluginSave]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(
    await page.evaluate(
      () =>
        window.pluginsHarness.editor().model.document.resource.palette.light
          .accent
    ),
    '#246b7b'
  );
  await page.locator('[data-frame=pluginApplyTheme]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  await page.locator('[data-frame=pluginResetTheme]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(
    await page.evaluate(
      () => window.pluginsHarness.editor().model.metadata.pluginTheme
    ),
    null
  );
  current = await page.evaluate(() => window.pluginsHarness.editor().model);
  const script = current.metadata.resources.find((r) => r.kind === 'python');
  await dispatch({ type: 'resource', key: script.key });
  await page
    .locator('[data-frame=pluginPythonInputs]')
    .fill('{"review_code":"STUDIO_REVIEW_003"}');
  await page.locator('[data-frame=pluginPythonRun]').click();
  await page.locator('[data-frame=pluginConfirm]').click();
  await page.waitForFunction(() => !window.pluginsHarness.editor().busy);
  assert.equal(
    await page.evaluate(
      () => window.pluginsHarness.editor().model.metadata.runResult.status
    ),
    'Approved'
  );
  assert.deepEqual(errors, []);
  const before = calls.length;
  await page.waitForTimeout(150);
  assert.equal(calls.length, before);
  console.log(
    'Browser real plugin: EN/RU narrow/wide, typed creation, theme source/apply/reset, confirmed Python action and no polling passed'
  );
} finally {
  if (browser) await browser.close();
  await server.close();
}
