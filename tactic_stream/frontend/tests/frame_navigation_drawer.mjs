import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import {
  describe,
  move,
  shouldClose
} from '../../src/tactic_stream/shared_ui/shell/navigation.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_navigation/output/';
for (const width of [0, 100, 240, 320, 900]) {
  const scene = describe({ width, height: 640, editable: true });
  validateScene(scene, {}, { edit: true, close: true, content: true });
  assert(scene.width <= width);
}
assert.equal(shouldClose(false, 'mouse', 700, 360), false);
assert.equal(shouldClose(true, 'touch', 700, 360), false);
assert.equal(shouldClose(true, 'mouse', 480, 360), false);
assert.equal(shouldClose(true, 'mouse', 481, 360), true);
const records = [
  { id: 'group', kind: 'section', hasChildren: true, expanded: true, depth: 0 },
  { id: 'hidden', visible: false, depth: 1 },
  { id: 'disabled', enabled: false, depth: 1 },
  { id: 'separator', kind: 'separator' },
  { id: 'child', depth: 1 }
];
assert.deepEqual(move(records, 'group', 'ArrowDown'), {
  type: 'select',
  id: 'child'
});
assert.deepEqual(move(records, 'child', 'ArrowLeft'), {
  type: 'select',
  id: 'group'
});
assert.equal(move(records, 'child', 'ArrowDown'), null);
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 900, height: 640 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_navigation/index.html'
  );
  await page.waitForFunction(() => !!window.drawerHarness);
  await page.evaluate(() => document.fonts.ready);
  const drawer = page.locator('#workspace-sidebar'),
    opener = page.getByRole('button', { name: 'Open navigation', exact: true });
  const captures = [];
  if (process.argv.includes('--capture')) {
    await mkdir(out, { recursive: true });
    for (const width of [900, 320])
      for (const style of ['md3', 'material5', 'fluent'])
        for (const language of ['en', 'ru']) {
          await page.setViewportSize({ width, height: 640 });
          await page.evaluate(
            ([style, language, width]) =>
              window.drawerHarness.configure(style, language, width),
            [style, language, width]
          );
          await page.waitForFunction(
            () =>
              Math.abs(
                document
                  .querySelector('#workspace-sidebar')
                  .getBoundingClientRect().width -
                  (innerWidth === 900 ? 360 : 280)
              ) < 0.1
          );
          const boxes = await drawer.evaluate((node) => {
            const result = {},
              origin = node.getBoundingClientRect();
            for (const id of [
              'navigationSurface',
              'navigationTitle',
              'navigationSubtitle',
              'navigationDivider'
            ]) {
              const item = node.querySelector('[data-frame="' + id + '"]'),
                box = item.getBoundingClientRect();
              result[id] = {
                x: box.x - origin.x,
                y: box.y - origin.y,
                width: box.width,
                height: box.height,
                fontSize: parseFloat(getComputedStyle(item).fontSize)
              };
            }
            for (const [id, selector] of [
              ['navigationEdit', '.navigation-drawer-action:first-of-type'],
              ['navigationClose', '.navigation-drawer-action:last-of-type'],
              ['navigationList', '.type-list']
            ]) {
              const box = node.querySelector(selector).getBoundingClientRect();
              result[id] = {
                x: box.x - origin.x,
                y: box.y - origin.y,
                width: box.width,
                height: box.height
              };
            }
            return result;
          });
          const id = `${width}-${style}-${language}`,
            image = 'browser-' + id + '.png';
          await page.screenshot({ path: out + image, animations: 'disabled' });
          const rows = await drawer
            .locator('.navigation-row')
            .evaluateAll((items) => {
              const result = {},
                origin = document
                  .querySelector('#workspace-sidebar')
                  .getBoundingClientRect();
              for (const item of items.slice(0, 3)) {
                const box = item.getBoundingClientRect(),
                  title = item.querySelector(
                    '[data-frame="sidebarRowTitle"]'
                  ).textContent;
                result[title] = {
                  x: box.x - origin.x,
                  y: box.y - origin.y,
                  width: box.width,
                  height: box.height
                };
              }
              return result;
            });
          const captions = {};
          for (const key of ['navigationTitle', 'navigationSubtitle'])
            captions[key] = await drawer
              .locator('[data-frame="' + key + '"]')
              .innerText();
          assert.equal(
            captions.navigationTitle,
            language === 'ru' ? 'Навигация' : 'Navigation'
          );
          assert.equal(
            captions.navigationSubtitle,
            language === 'ru'
              ? 'Рабочее пространство проекта'
              : 'Project workspace'
          );
          captures.push({ id, image, boxes, rows, captions });
          await page.evaluate(() => window.drawerHarness.close());
        }
    const paths = [
      'frontend/src/features/workspace/NavigationDrawer.vue',
      'frontend/src/features/workspace/NavigationTree.vue',
      'frontend/src/controls/NavigationRow.vue',
      'frontend/src/App.vue',
      'frontend/src/style.css',
      'frontend/src/theme.css',
      'frontend/src/appearance.js',
      'frontend/src/i18n.js',
      'frontend/src/locales/en.json',
      'frontend/src/locales/ru.json',
      'frontend/src/icons.js',
      'frontend/src/icons.css',
      'frontend/src/controls/AppButton.vue',
      'frontend/src/controls/AppIcon.vue',
      'frontend/src/controls/activation.js',
      'frontend/src/controls/controlAppearance.js',
      'frontend/src/controls/panelChrome.css',
      'frontend/src/controls/ripple.js',
      'frontend/src/controls/tooltip.js',
      'frontend/src/frame/FrameView.vue',
      'frontend/src/frame/frame.css',
      'frontend/src/frame/resize.js',
      'frontend/tests/frame_navigation_drawer.mjs',
      'tools/frame_navigation/DrawerHarness.vue',
      'tools/frame_navigation/drawer.entry.js'
    ];
    const sources = {};
    for (const path of paths)
      sources[path] = createHash('sha256')
        .update(await readFile(root + path))
        .digest('hex');
    await writeFile(
      out + 'browser.json',
      JSON.stringify({ captures, sources }, null, 2)
    );
  }
  await page.setViewportSize({ width: 900, height: 640 });
  await page.evaluate(async () => {
    await window.drawerHarness.configure('md3', 'en', 900);
    window.drawerHarness.close();
    window.drawerHarness.inputRecords();
  });
  await opener.click();
  assert(await drawer.isVisible());
  await page.mouse.move(800, 600);
  assert(
    await drawer.isVisible(),
    'Unarmed auto-close allows approaching from the central opener'
  );
  await page.mouse.move(180, 300);
  await page.mouse.move(480, 300);
  assert(await drawer.isVisible());
  await page.mouse.move(481, 300);
  await drawer.waitFor({ state: 'hidden' });
  assert(await opener.evaluate((node) => node === document.activeElement));
  await opener.click();
  await drawer.focus();
  await page.keyboard.press('End');
  assert.equal(
    await page.evaluate(() => document.activeElement.textContent.trim()),
    ''
  );
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.entryKey),
    'last'
  );
  const savedScroll = await drawer
    .locator('.type-list')
    .evaluate((node) => node.scrollTop);
  assert(savedScroll > 300);
  await page.evaluate(() => window.drawerHarness.configure('md3', 'ru', 900));
  assert.equal(
    await drawer.locator('[data-frame="navigationTitle"]').innerText(),
    'Навигация'
  );
  assert.equal(
    await drawer.getByRole('button', { name: 'Assets', exact: true }).count(),
    1
  );
  assert.equal(
    await drawer.locator('.type-list').evaluate((node) => node.scrollTop),
    savedScroll
  );
  await page.evaluate(() => window.drawerHarness.configure('md3', 'en', 900));
  await page.keyboard.press('Escape');
  await opener.click();
  assert.equal(
    await drawer.locator('.type-list').evaluate((node) => node.scrollTop),
    savedScroll
  );
  await page.keyboard.press('Home');
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.entryKey),
    'group'
  );
  await page.keyboard.press('ArrowLeft');
  assert.equal(
    await drawer.getByRole('button', { name: 'Asset 0', exact: true }).count(),
    0
  );
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.entryKey),
    'last'
  );
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.entryKey),
    'entry0'
  );
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.entryKey),
    'entry1'
  );
  await page.keyboard.press('Space');
  assert.equal(await page.evaluate(() => window.drawerHarness.activated), 1);
  await drawer.waitFor({ state: 'hidden' });
  await opener.tap();
  await page.keyboard.press('Escape');
  assert(await opener.evaluate((node) => node === document.activeElement));
  await page.setViewportSize({ width: 320, height: 760 });
  await opener.tap();
  await drawer.getByRole('button', { name: 'Asset 0', exact: true }).tap();
  assert.equal(await page.evaluate(() => window.drawerHarness.activated), 2);
  await opener.tap();
  await page.evaluate(() => {
    window.drawerHarness.extras = true;
    window.drawerHarness.editable = false;
  });
  await page.waitForFunction(
    () => document.querySelector('.type-list').style.top === '185px'
  );
  assert.equal(
    await drawer
      .getByRole('button', { name: 'Edit navigation', exact: true })
      .count(),
    0
  );
  await drawer
    .getByRole('button', { name: 'Close navigation', exact: true })
    .tap();
  assert.deepEqual(errors, []);
  console.log(
    'Drawer: shared layout, armed exit, first mouse/touch, focus, keyboard/hidden/disabled/recycled rows and mobile slots passed.'
  );
} finally {
  await browser?.close();
  await server.close();
}
