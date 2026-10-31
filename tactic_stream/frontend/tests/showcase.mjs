import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
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
let browser, page;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  page = await browser.newPage({
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
  const requests = [];
  await page.route('**/ui/help/**', async (route) => {
    const name = new URL(route.request().url()).pathname.split('/ui/help/')[1];
    assert(/^[a-zA-Z0-9_.-]+\.(json|md)$/.test(name));
    await route.fulfill({
      body: await readFile(root + 'frontend/public/help/' + name),
      contentType: name.endsWith('.json') ? 'application/json' : 'text/markdown'
    });
  });
  await page.route('**/admin/rpc', (route) => {
    requests.push(route.request().postDataJSON());
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
    const { initializeAppearance } = await import(
      '/frontend/src/appearance.js'
    );
    initializeAppearance();
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
  const output =
    process.env.STREAM_SHOWCASE_OUTPUT || root + 'tools/frame_showcase/output';
  await mkdir(output, { recursive: true });
  await page.evaluate(async () => {
    const { appearance } = await import('/frontend/src/appearance.js');
    Object.assign(appearance, {
      language: 'en',
      mode: 'dark',
      clickAnimations: false,
      hoverAnimations: false,
      fadeAnimations: false,
      popupAnimations: false
    });
    window.adminFixture.showAdministration('showcase');
  });
  const dialog = page.locator('dialog.administration-dialog');
  await page.locator('[data-frame=showcaseTitle]').waitFor();
  await page.evaluate(() => document.fonts.ready);
  const help = await page.evaluate(async () => {
    const { loadArticles } = await import(
      '/frontend/src/features/help/help.js'
    );
    return (await loadArticles('ru')).find(
      (article) => article.id === 'frame_showcase'
    );
  });
  assert.equal(help.title, 'Каталог компонентов');
  await page.evaluate(async () =>
    (
      await import('/frontend/src/features/activity/notifications.js')
    ).resetNotifications()
  );
  async function choose(id) {
    await page.locator('input[data-frame=showcaseSearch]').fill(id);
    await page.locator('[data-frame=showcaseFamily_' + id + ']').click();
    await page.locator('input[data-frame=showcaseSearch]').fill('');
  }
  for (const id of [
    'typography',
    'headers',
    'colors',
    'icons',
    'buttons',
    'toggles',
    'text-fields',
    'choices',
    'numbers',
    'dates',
    'user-choice',
    'pickers',
    'tabs',
    'badges',
    'lists',
    'charts'
  ]) {
    await choose(id);
    await page.locator('[data-frame=showcasePreview]').waitFor();
    if (
      ['typography', 'colors', 'buttons', 'badges', 'lists', 'charts'].includes(
        id
      )
    )
      await dialog.screenshot({ path: output + '/' + id + '-ts-dark.png' });
  }
  await choose('text-fields');
  await page.locator('input[data-frame=sampleField]').fill('Edited locally');
  assert.equal(
    await page.locator('input[data-frame=sampleField]').inputValue(),
    'Edited locally'
  );
  await page.locator('[data-frame=showcaseReset]').click();
  assert.equal(
    await page.locator('input[data-frame=sampleField]').inputValue(),
    'Robot Arm'
  );
  await page.locator('[data-frame=showcaseState]').selectOption('disabled');
  assert.equal(
    await page.locator('input[data-frame=sampleField]').isEnabled(),
    false
  );
  await page.locator('[data-frame=showcaseState]').selectOption('default');
  await choose('toggles');
  const checked = page.locator('[data-frame=sampleCheckbox] input');
  assert.equal(await checked.isChecked(), true);
  await page.locator('[data-frame=sampleCheckbox]').click();
  assert.equal(await checked.isChecked(), false);
  await choose('badges');
  await page.locator('[data-frame=showcaseCode]').click();
  await page.locator('[data-frame=showcaseCodeSource]').waitFor();
  assert.equal(
    await page.getByText('Widget unavailable', { exact: true }).count(),
    0
  );
  await page.locator('[data-frame=showcaseCode]').click();
  await page.evaluate(async () => {
    (await import('/frontend/src/appearance.js')).appearance.mode = 'light';
  });
  await dialog.screenshot({ path: output + '/badges-ts-light.png' });
  await page.evaluate(async () => {
    (await import('/frontend/src/appearance.js')).appearance.language = 'ru';
  });
  assert.equal(
    await page
      .locator('input[data-frame=showcaseSearch]')
      .getAttribute('placeholder'),
    'Найти компонент'
  );
  assert.match(
    await page.locator('[data-frame=showcaseTitle]').innerText(),
    /Бейджи/
  );
  await dialog.screenshot({ path: output + '/badges-ts-ru.png' });
  for (const width of [900, 620, 360]) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(80);
    await dialog.screenshot({ path: output + '/narrow-' + width + '-ts.png' });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth
      ),
      false
    );
  }
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => !window.adminFixture.administrationOpen);
  assert.equal(
    requests.filter((r) => r.method === 'execute_cmd').length,
    0,
    'Showcase makes no server commands'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Actual Administration showcase: 16 families, local input, code, both palettes, narrow layouts, no server commands and close pass.'
  );
} catch (error) {
  await page?.screenshot({
    path:
      (process.env.STREAM_SHOWCASE_OUTPUT ||
        root + 'tools/frame_showcase/output') + '/failure.png'
  });
  console.error((await page?.locator('body').innerText())?.slice(-1600));
  throw error;
} finally {
  await browser?.close();
  await server.close();
}
