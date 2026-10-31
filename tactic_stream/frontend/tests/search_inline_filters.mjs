import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as Header from '../../src/tactic_stream/shared_ui/features/search/header.ui.mjs';

assert.equal(Header.quickBudget({ compact: true }, 1600), 0);
assert.equal(Header.quickBudget({}, 900), 0);
assert.equal(
  Header.quickStrip([{ key: 'long', textWidth: 600 }], 200, 'en').width,
  38
);
const groups = [
  {
    key: 'status',
    title: 'STATUSES',
    source: 'task',
    options: [{ key: 'Review', title: 'Review' }]
  },
  { key: 'assigned', title: 'ASSIGNED TO', source: 'task', options: [] },
  {
    key: 'column:category',
    title: 'Category',
    source: 'column',
    options: [{ key: 'Props', title: 'Props' }]
  },
  { key: 'column:hidden', title: 'Hidden', source: 'column', options: [] }
];
const catalog = {
  groups,
  configuration: {
    groups: [{ key: 'column:hidden', enabled: false }],
    defaultSelections: {}
  }
};
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
    viewport: { width: 1500, height: 600 },
    hasTouch: true
  });
  page.setDefaultTimeout(10000);
  const errors = [],
    reads = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/search-configuration/read', (route) => {
    reads.push(route.request().postDataJSON());
    return route.fulfill({ json: { result: catalog } });
  });
  await page.route('**/admin/user-profile/read', (route) =>
    route.fulfill({
      json: { result: { users: [{ login: 'artist', displayName: 'Artist' }] } }
    })
  );
  await page.route('**/inline-fixture', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<div id="app"></div>' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'inline-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h } = await import(vueUrl);
      const { default: App } = await import('/frontend/src/App.vue');
      const { default: Header } = await import(
        '/frontend/src/features/workspace/SearchHeader.vue'
      );
      const { default: Quick } = await import(
        '/frontend/src/features/workspace/SearchQuickFilters.vue'
      );
      const { default: Menu } = await import(
        '/frontend/src/controls/AppMenu.vue'
      );
      const { appearance, initializeAppearance } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      initializeAppearance();
      Object.assign(appearance, { mode: 'dark', language: 'en', theme: 'md3' });
      window.appearance = appearance;
      createApp({
        data: () => ({
          width: 1460,
          tab: 'one',
          busy: false,
          quickSelections: {},
          quickLayout: null,
          page: 4,
          searchText: 'hero',
          selectedTags: ['cg'],
          filterRecords: [],
          queries: [],
          blocked: false
        }),
        mounted() {
          window.host = this;
        },
        methods: {
          applyQuickFilters: App.methods.applyQuickFilters,
          loadRows() {
            this.queries.push(JSON.stringify(this.quickSelections));
          },
          confirmTaskChanges() {
            return !this.blocked;
          }
        },
        render() {
          return h(
            'main',
            {
              class: 'workspace-browser',
              style: `width:${this.width}px;height:560px;position:relative`
            },
            [
              h(
                Header,
                { model: { busy: this.busy } },
                {
                  field: () =>
                    h('input', {
                      value: this.searchText,
                      placeholder: 'Search',
                      style: 'width:100%;height:38px'
                    }),
                  tags: () => h(Menu, { label: 'Tags', icon: 'tags' }),
                  panels: () =>
                    h(
                      'div',
                      { id: 'workspace-dock-actions' },
                      h(Menu, { label: 'Workspace panels' })
                    ),
                  quick: ({ budget, resize }) =>
                    h(Quick, {
                      ref: 'quick',
                      budget,
                      onResize: resize,
                      ticket: 'fixture',
                      project: 'demo',
                      searchType: 'demo/asset',
                      tabId: this.tab,
                      selections: this.quickSelections,
                      layout: this.quickLayout,
                      disabled: this.busy,
                      onApply: this.applyQuickFilters
                    })
                }
              )
            ]
          );
        }
      }).mount('#app');
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  const button = (key) =>
    page.locator(`[data-frame="searchQuickGroup_${key}"]`);
  await button('status').waitFor();
  assert.equal(reads.length, 1, 'one cached catalog read');
  assert.equal(await button('column:hidden').count(), 0);
  await button('status').click();
  const menu = page.locator('.search-quick-filters');
  await menu.getByRole('button', { name: 'Review', exact: true }).waitFor();
  assert.equal(await menu.getByRole('region').count(), 1);
  await menu.getByRole('button', { name: 'Review', exact: true }).click();
  await page.waitForFunction(
    () => window.host.quickSelections.status?.[0] === 'Review'
  );
  assert.equal(await button('status').getAttribute('aria-label'), 'Status · 1');
  assert.deepEqual(
    await page.evaluate(() => [
      window.host.searchText,
      window.host.selectedTags,
      window.host.page,
      window.host.queries.length
    ]),
    ['hero', ['cg'], 0, 1]
  );
  await button('assigned').locator('.app-icon').tap();
  assert.equal(await menu.getByRole('region').count(), 1);
  await menu.getByRole('button', { name: 'MY TASKS', exact: true }).click();
  await page.waitForFunction(
    () => window.host.quickSelections.assigned?.[0] === '__current_login__'
  );
  await page.keyboard.press('Escape');
  await page.locator('.search-quick-filters > summary').click();
  await menu.getByRole('region', { name: 'Category', exact: true }).waitFor();
  assert.equal(
    await menu.getByRole('region').count(),
    3,
    'full popup retains every enabled group'
  );
  await page.keyboard.press('Escape');
  await page.evaluate(() => (window.host.busy = true));
  assert.equal(await button('status').isDisabled(), true);
  await page.evaluate(() => {
    window.host.busy = false;
    window.host.width = 900;
  });
  await page.waitForFunction(
    () => !document.querySelector('[data-frame="searchQuickGroup_status"]')
  );
  await page.evaluate(() => (window.host.width = 1460));
  await button('status').waitFor();
  assert.equal(reads.length, 1, 'resizing reuses catalog without querying');
  await button('status').focus();
  await page.keyboard.press('Enter');
  await menu.getByRole('button', { name: 'Review', exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page.evaluate(() => (window.host.tab = 'two'));
  await page.waitForFunction(
    () => !window.host.$refs.quick.busy && window.host.$refs.quick.catalog
  );
  assert.equal(reads.length, 2, 'new tab owns its catalog lifecycle');
  const field = await page
    .getByPlaceholder('Search', { exact: true })
    .boundingBox();
  assert.ok(field.width >= 600, 'search retains comfortable width');
  if (process.env.SEARCH_INLINE_OUTPUT) {
    await mkdir(process.env.SEARCH_INLINE_OUTPUT, { recursive: true });
    for (const lang of ['en', 'ru'])
      for (const mode of ['dark', 'light']) {
        await page.evaluate(
          ({ lang, mode }) =>
            Object.assign(window.appearance, { language: lang, mode }),
          { lang, mode }
        );
        await page.waitForTimeout(150);
        await page.locator('.frame-search-header').screenshot({
          path: `${process.env.SEARCH_INLINE_OUTPUT}/browser-${lang}-${mode}.png`
        });
      }
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: responsive configured quick groups, actual apply owner, scoped/full menu, mouse/key/touch, disabled, lifecycle and cached resize'
  );
} finally {
  await browser?.close();
  await server.close();
}
