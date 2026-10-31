import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as UI from '../../src/tactic_stream/shared_ui/features/search/menus.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

assert.equal(UI.inlineViews(700, 100), false);
assert.equal(UI.inlineViews(800, 150), true);
assert.equal(UI.inlineViews(1000, 800), false);
assert.equal(UI.inlineViews(800, 430), true);
assert.equal(UI.inlineViews(800, 430, 42), false);
assert.equal(UI.viewActions('table', false).length, 6);
validateScene(UI.describeViewPicker({ mode: 'table', busy: false }, 'en'));
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  publicDir: root + 'frontend/public',
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 400 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/view-fixture', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<div id="app"></div>' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'view-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h, reactive } = await import(vueUrl);
      const { default: Tabs } = await import(
        '/frontend/src/controls/WorkspaceTabs.vue'
      );
      const { default: Menu } = await import(
        '/frontend/src/features/workspace/SearchResultMenu.vue'
      );
      const { default: Actions } = await import(
        '/frontend/src/controls/AppMenu.vue'
      );
      const { default: App } = await import('/frontend/src/App.vue');
      const { appearance, initializeAppearance, hostedPalette } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      hostedPalette.value = {
        dark: '#78a6c4',
        darkBase: '#292d30',
        light: '#3d7599',
        lightBase: '#d4dce1'
      };
      initializeAppearance();
      Object.assign(appearance, {
        theme: 'md3',
        mode: 'dark',
        language: 'en',
        clickAnimations: false,
        hoverAnimations: false,
        fadeAnimations: false,
        popupAnimations: false
      });
      const state = (window.viewFixture = reactive({
        width: 1100,
        mode: 'continious',
        busy: false,
        tabs: [{ id: 'one', title: 'Assets', current: true }],
        writes: 0,
        guard: true
      }));
      const owner = {
        canCloseTaskViews: () => state.guard,
        persistWorkspace: () => state.writes++,
        workspaceProject: 'demo'
      };
      function choose(mode) {
        App.methods.changeResultView.call(owner, mode);
        if (owner.resultMode) state.mode = owner.resultMode;
      }
      createApp({
        render: () =>
          h('div', { style: { width: state.width + 'px' } }, [
            h(
              Tabs,
              { tabs: state.tabs, selected: 'one' },
              {
                actions: ({ compact, width, natural, history }) =>
                  h(
                    Actions,
                    {
                      label: 'Result actions',
                      inline: !compact,
                      closeOnSelect: false
                    },
                    {
                      default: () =>
                        h(Menu, {
                          kind: 'view',
                          label: 'Change search results view',
                          icon: 'MDI_TABLE',
                          model: { mode: state.mode, busy: state.busy },
                          toolbarWidth: compact ? 0 : width,
                          tabsWidth: natural,
                          historyWidth: history,
                          onCommand: choose
                        })
                    }
                  )
              }
            )
          ])
      }).mount('#app');
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  const picker = page.getByRole('radiogroup', {
    name: 'Result view',
    exact: true
  });
  await picker.waitFor();
  const bounds = await picker.boundingBox();
  assert.equal(bounds.width, 114);
  assert.equal(bounds.height, 40);
  for (const [label, mode] of [
    ['Table', 'table'],
    ['Cards', 'tiles'],
    ['Continuous tree', 'continious']
  ]) {
    await picker.getByRole('radio', { name: label, exact: true }).click();
    assert.equal(await page.evaluate(() => window.viewFixture.mode), mode);
  }
  await picker
    .getByRole('radio', { name: 'Continuous tree', exact: true })
    .focus();
  await page.keyboard.press('End');
  assert.equal(await page.evaluate(() => window.viewFixture.mode), 'table');
  await picker.getByRole('radio', { name: 'Cards', exact: true }).tap();
  assert.equal(await page.evaluate(() => window.viewFixture.mode), 'tiles');
  await page.evaluate(() => (window.viewFixture.busy = true));
  assert.equal(
    await picker
      .getByRole('radio', { name: 'Table', exact: true })
      .isDisabled(),
    true
  );
  await page.evaluate(() => {
    window.viewFixture.busy = false;
    window.viewFixture.guard = false;
  });
  await picker.getByRole('radio', { name: 'Table', exact: true }).click();
  assert.equal(await page.evaluate(() => window.viewFixture.mode), 'tiles');
  await page.evaluate(() => (window.viewFixture.guard = true));
  for (const [label, mode] of [
    ['Compact rows', 'compact'],
    ['Versions on the right', 'splitted_vertical'],
    ['Versions at the bottom', 'splitted_horizontal'],
    ['Table', 'table']
  ]) {
    await page
      .getByLabel('Change search results view', { exact: true })
      .click();
    await page.getByRole('menuitemradio', { name: label, exact: true }).click();
    assert.equal(await page.evaluate(() => window.viewFixture.mode), mode);
  }
  if (process.env.RESULT_VIEW_OUTPUT) {
    mkdirSync(process.env.RESULT_VIEW_OUTPUT, { recursive: true });
    await page.mouse.move(0, 200);
    await picker.screenshot({
      path: process.env.RESULT_VIEW_OUTPUT + '/browser-picker.png'
    });
    const dark = await picker.evaluate(
      (el) => getComputedStyle(el).backgroundColor
    );
    await page.evaluate(async () => {
      const { appearance } = await import('/frontend/src/appearance.js');
      appearance.mode = 'light';
    });
    await page.waitForFunction(
      (dark) =>
        getComputedStyle(
          document.querySelector('[data-frame="searchResultViewPicker"]')
        ).backgroundColor !== dark,
      dark
    );
    await picker.screenshot({
      path: process.env.RESULT_VIEW_OUTPUT + '/browser-picker-light.png'
    });
  }
  const writes = await page.evaluate(() => window.viewFixture.writes);
  await page.evaluate(
    () =>
      (window.viewFixture.tabs = Array.from({ length: 8 }, (_, i) => ({
        id: i ? 'tab' + i : 'one',
        title: 'A long search tab ' + i
      })))
  );
  await picker.waitFor({ state: 'hidden' });
  await page.evaluate(() => {
    window.viewFixture.tabs = [{ id: 'one', title: 'Assets' }];
    window.viewFixture.width = 700;
  });
  await picker.waitFor({ state: 'hidden' });
  await page.getByLabel('Result actions', { exact: true }).click();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Cards', exact: true }).click();
  assert.equal(await page.evaluate(() => window.viewFixture.mode), 'tiles');
  assert.equal(
    await page.evaluate(() => window.viewFixture.writes),
    writes + 1
  );
  await page.evaluate(() => (window.viewFixture.width = 1100));
  await picker.waitFor();
  assert.equal(
    await picker
      .getByRole('radio', { name: 'Cards', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: real view selection, task guard, persistence, keyboard/touch, busy, tab crowding and resize'
  );
} finally {
  await browser.close();
  await server.close();
}
