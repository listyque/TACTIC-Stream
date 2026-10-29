import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';
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
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
const context = await browser.newContext({
  viewport: { width: 900, height: 600 },
  hasTouch: true
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const output = process.env.SEARCH_MENU_OUTPUT;
if (output) mkdirSync(output, { recursive: true });
try {
  for (const language of ['en', 'ru'])
    for (const width of [900, 380]) {
      await page.setViewportSize({ width, height: 600 });
      await page.goto(
        'http://127.0.0.1:' +
          server.httpServer.address().port +
          '/tools/frame_search/index.html'
      );
      await page.evaluate(
        async ({ language, width }) =>
          window.searchFixture.show({
            screen: 'result-menu',
            width,
            height: 600,
            language,
            style: 'md3',
            dark: true,
            model: {
              presets: [{ title: 'My Tasks', view: 'my_tasks' }],
              selected: '',
              busy: false
            }
          }),
        { language, width }
      );
      const owner = page
        .locator('.search-fixture-dock .workspace-menu')
        .first();
      const trigger = owner.locator(':scope > summary');
      const panel = owner.locator(':scope > .account-panel');
      await trigger.click();
      await panel.waitFor({ state: 'visible' });
      await page.waitForFunction(
        () =>
          document
            .querySelector('.search-fixture-dock [data-frame="menuTitle"]')
            ?.getBoundingClientRect().width > 100
      );
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      assert.equal(
        await panel.evaluate((element) => element.matches(':popover-open')),
        true,
        'Result menu must escape dock/sidebar stacking and clipping'
      );
      const bounds = await panel.boundingBox();
      const button = await trigger.boundingBox();
      assert.ok(bounds.x >= 4 && bounds.x + bounds.width <= width - 4 + 0.5);
      assert.ok(
        Math.abs(bounds.x - button.x) < 1 ||
          width < button.x + bounds.width + 4,
        'Start alignment follows the native result menu'
      );
      assert.equal(
        await panel.evaluate((element) => {
          const box = element.getBoundingClientRect();
          return element.contains(
            document.elementFromPoint(box.left + 12, box.top + 20)
          );
        }),
        true,
        'Popup content stays above the navigation rail'
      );
      if (output)
        await page.screenshot({ path: output + `/${language}-${width}.png` });
      await owner
        .locator('[data-menu-command="filter_processes"] button')
        .tap();
      assert.deepEqual(
        await page.evaluate(() => window.searchFixture.events()),
        ['filter_processes']
      );
      assert.equal(
        await panel.evaluate((element) => element.matches(':popover-open')),
        false
      );
      assert.equal(
        await trigger.evaluate((element) => element === document.activeElement),
        true
      );
      await trigger.press('ArrowDown');
      await page.keyboard.press('Enter');
      assert.equal(
        (await page.evaluate(() => window.searchFixture.events())).at(-1),
        'advanced_search'
      );
      await trigger.click();
      await page.keyboard.press('Escape');
      assert.equal(
        await trigger.evaluate((element) => element === document.activeElement),
        true
      );
      await trigger.click();
      await page.mouse.click(width - 10, 550);
      assert.equal(
        await panel.evaluate((element) => element.matches(':popover-open')),
        false
      );
    }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: result menu escapes clipped/transformed docks and sidebar; EN/RU narrow/wide mouse, touch, keyboard, dismissal and focus'
  );
} finally {
  await context.close();
  await browser.close();
  await server.close();
}
