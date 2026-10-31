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
  const page = await browser.newPage({ viewport: { width: 900, height: 200 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/header-fixture', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<div id="app"></div>' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'header-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h } = await import(vueUrl);
      const { default: Header } = await import(
        '/frontend/src/features/workspace/SearchHeader.vue'
      );
      const { default: Tags } = await import(
        '/frontend/src/features/workspace/TagCloud.vue'
      );
      const { default: Quick } = await import(
        '/frontend/src/features/workspace/SearchQuickFilters.vue'
      );
      const { default: Menu } = await import(
        '/frontend/src/controls/AppMenu.vue'
      );
      const { default: Button } = await import(
        '/frontend/src/controls/AppButton.vue'
      );
      const { appearance, initializeAppearance } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      initializeAppearance();
      Object.assign(appearance, { theme: 'md3', mode: 'dark', language: 'en' });
      window.events = [];
      createApp({
        render: () =>
          h('div', [
            h(
              Header,
              { model: {}, onEvent: (a) => window.events.push(a.type) },
              {
                field: () => h('input', { placeholder: 'Search' }),
                tags: () => h(Tags, { selected: [], disabled: true }),
                quick: () => h(Quick, { selections: {}, disabled: true }),
                panels: () =>
                  h(
                    'div',
                    { id: 'workspace-dock-actions' },
                    h(Menu, { label: 'Workspace panels' })
                  )
              }
            ),
            h(Button, {
              iconOnly: true,
              icon: 'refresh',
              label: 'Local service',
              style: 'margin-top:16px'
            })
          ])
      }).mount('#app');
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  for (const label of [
    'Refresh',
    'Script shelf',
    'Tags',
    'Quick filters',
    'Search help',
    'Workspace panels'
  ]) {
    const button = page
      .getByRole('button', { name: label, exact: true })
      .or(page.locator('summary[aria-label="' + label + '"]'));
    await button.first().waitFor();
    for (const hover of [false, true]) {
      if (hover) await button.first().hover();
      const geometry = await button
        .first()
        .evaluate((el) => ({
          width: el.offsetWidth,
          height: el.offsetHeight,
          radius: getComputedStyle(el).borderTopLeftRadius
        }));
      assert.equal(geometry.width, geometry.height, label);
      assert.ok(
        geometry.radius === '50%' ||
          parseFloat(geometry.radius) >= geometry.height / 2,
        label + ': ' + geometry.radius
      );
    }
  }
  await page.getByRole('button', { name: 'Search help', exact: true }).click();
  await page.getByRole('button', { name: 'Script shelf', exact: true }).click();
  assert.deepEqual(await page.evaluate(() => window.events), ['help', 'shelf']);
  assert.equal(
    await page
      .getByRole('button', { name: 'Local service', exact: true })
      .evaluate((el) => getComputedStyle(el).borderTopLeftRadius),
    '4px'
  );
  assert.deepEqual(errors, []);
  if (process.env.SEARCH_HEADER_CAPTURE)
    await page.screenshot({ path: process.env.SEARCH_HEADER_CAPTURE });
  console.log(
    'PASS: all six main search controls round, ordinary service control square, actions preserved'
  );
} finally {
  await browser?.close();
  await server.close();
}
