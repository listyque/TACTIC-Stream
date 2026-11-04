import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

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
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 1000 }
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/plugins-close-fixture', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<html><body><div id="app"></div></body></html>'
    })
  );
  await page.route('**/admin/rpc', (route) => {
    const body = route.request().postDataJSON();
    if (
      body.method === 'execute_cmd' &&
      body.args[1].endsWith('.PluginManagerCmd')
    ) {
      const args = body.args[2];
      const row = {
        identity: 'plugins:example',
        title: 'Example',
        code: 'example',
        active: true
      };
      const info =
        args.action === 'list'
          ? { catalog: [row], metadata: {}, canWrite: true }
          : {
              identity: row.identity,
              revision: 'one',
              canWrite: true,
              document: {
                title: 'Example',
                code: 'example',
                description: '',
                file: null
              },
              metadata: { active: true, files: [], project: 'one' }
            };
      return route.fulfill({ json: { result: { info } } });
    }
    return route.fulfill({ json: { result: [] } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'plugins-close-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  const vueUrl = entry.code.match(/from "([^"]+)"/)[1];
  await page.evaluate(async (vueUrl) => {
    const { createApp } = await import(vueUrl);
    const { default: App } = await import('/frontend/src/App.vue');
    const { windowDirective } = await import(
      '/frontend/src/controls/window.js'
    );
    await import('/frontend/src/theme.css');
    await import('/frontend/src/style.css');
    const { initializeAppearance, appearance } = await import(
      '/frontend/src/appearance.js'
    );
    initializeAppearance();
    Object.assign(appearance, { mode: 'dark', language: 'en' });
    // Replace authentication only; retain the real App template, refs and close handlers.
    window.adminFixture = createApp({
      ...App,
      created() {
        this.session = { ticket: 'fixture', login: 'admin' };
        this.project = this.workspaceProject = 'one';
        this.projects = [{ code: 'one', title: 'One' }];
        this.canAdminister = true;
        this.ready = true;
        this.restoringSession = false;
      }
    })
      .directive('window', windowDirective)
      .mount('#app');
  }, vueUrl);
  const dialog = page.locator('dialog.administration-dialog');
  async function open() {
    await page.waitForFunction(() => window.adminFixture.$refs.settingsMenu);
    await page.evaluate(() =>
      window.adminFixture.showAdministration('plugins')
    );
    await page.locator('[data-frame=pluginTitle]').waitFor();
    await page.waitForFunction(
      () => !window.adminFixture.administrationInstances.plugins?.busy
    );
  }
  await open();
  const reloadBounds = await dialog
    .locator('[data-frame="pluginReload"]')
    .boundingBox();
  const helpBounds = await dialog
    .locator('[data-frame="administrationHelpButton"]')
    .boundingBox();
  assert.equal(
    reloadBounds.y,
    helpBounds.y,
    'Header controls share a baseline'
  );
  for (const id of [
    'adminToggleNavigation',
    'administrationHelpButton',
    'pluginReload',
    'pluginCollapse'
  ]) {
    const control = dialog.locator(`[data-frame="${id}"]:visible`);
    for (const hover of [false, true]) {
      if (hover) await control.hover();
      const style = await control.evaluate((el) => ({
        width: el.offsetWidth,
        height: el.offsetHeight,
        radius: getComputedStyle(el).borderTopLeftRadius
      }));
      assert.equal(style.width, 34, id);
      assert.equal(style.height, 34, id);
      if (id === 'pluginCollapse') assert.equal(style.radius, '4px', id);
      else
        assert.ok(style.radius === '50%' || parseFloat(style.radius) >= 17, id);
    }
  }
  for (const button of await dialog
    .locator('.app-window-controls button:visible')
    .all()) {
    const shape = await button.evaluate((el) => ({
      height: el.offsetHeight,
      radius: getComputedStyle(el).borderTopLeftRadius
    }));
    assert.ok(
      shape.radius === '50%' || parseFloat(shape.radius) >= shape.height / 2,
      'Outer window chrome remains round'
    );
  }
  if (process.env.ADMIN_BUTTON_CAPTURE)
    await page.screenshot({ path: process.env.ADMIN_BUTTON_CAPTURE });
  assert.equal(
    await page.evaluate(
      () => typeof window.adminFixture.administrationInstances.plugins.canLeave
    ),
    'function'
  );
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => !window.adminFixture.administrationOpen);
  assert.deepEqual(errors, [], 'Clean visit closes without an exception');
  await open();
  await page.evaluate(() =>
    window.adminFixture.administrationInstances.plugins.dispatch({
      type: 'tab',
      value: 'details'
    })
  );
  await page.locator('[data-frame=pluginField_title]').fill('Unsaved title');
  await page.keyboard.press('Escape');
  assert.ok(await dialog.isVisible(), 'Unsaved changes keep the window open');
  assert.match(
    await page.locator('[data-frame=pluginOperationTitle]').innerText(),
    /Discard changes/
  );
  await page.locator('[data-frame=pluginConfirm]').click();
  await dialog
    .locator('.app-window-controls')
    .getByRole('button', { name: 'Close', exact: true })
    .click();
  await dialog.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'Plugins administration closes after a clean visit and discard; drafts stay protected.'
  );
} finally {
  await browser?.close();
  await server.close();
}
