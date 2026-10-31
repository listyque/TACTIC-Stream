import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 1100 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin-mode-fixture', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<div id="app"></div>'
    })
  );
  await page.goto(server.resolvedUrls.local[0] + 'admin-mode-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h, reactive } = await import(vueUrl);
      const { default: Shell } = await import(
        '/frontend/src/features/administration/AdministrationShell.vue'
      );
      const { appearance, initializeAppearance } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      initializeAppearance();
      Object.assign(appearance, { mode: 'dark', language: 'en', theme: 'md3' });
      window.model = reactive({
        section: 'groups',
        project: 'demo',
        projects: [],
        locked: false,
        busy: false,
        drafts: [],
        streamApi: false
      });
      createApp({
        render: () =>
          h(
            'div',
            { style: 'height:100dvh' },
            h(Shell, {
              ref: (shell) => {
                window.shell = shell;
              },
              model: window.model,
              onCommand: (command) => {
                if (command.type === 'section') window.selected = command.value;
              }
            })
          )
      }).mount('#app');
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  const section = (id) => page.locator(`[data-frame="adminSection_${id}"]`);
  for (const stream of [false, true]) {
    await page.evaluate((value) => {
      window.model.streamApi = value;
    }, stream);
    for (const collapsed of [false, true]) {
      await page.evaluate((value) => {
        window.shell.ui.collapsed = value;
      }, collapsed);
      await section('groups').waitFor();
      assert.equal(await section('dashboards').count(), stream ? 1 : 0);
      assert.equal(await section('layouts').count(), stream ? 1 : 0);
      await section('groups').click();
      assert.equal(await page.evaluate(() => window.selected), 'groups');
    }
  }
  await page.setViewportSize({ width: 700, height: 1100 });
  await page.evaluate(() => {
    window.model.streamApi = false;
  });
  const selector = page.locator('[data-frame="administrationSectionSelector"]');
  await selector.waitFor();
  assert(
    !(await selector.evaluate((el) =>
      /Page layouts|Item layouts/.test(el.textContent)
    ))
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: actual administration browser navigation retains Stream sections and filters Legacy layouts'
  );
} finally {
  await browser?.close();
  await server.close();
}
