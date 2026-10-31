import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
const root = fileURLToPath(new URL('../../', import.meta.url));
let native;
if (process.env.TASK_HOVER_CAPTURE) {
  try {
    native = JSON.parse(
      await readFile(process.env.TASK_HOVER_CAPTURE + '/native.json', 'utf8')
    );
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}
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
  browser = await chromium.launch({
    headless: true,
    channel: 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
      viewport: { width: 800, height: 600 },
      hasTouch: true
    }),
    errors = [],
    measurements = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/task-hover.html'
  );
  await page.waitForFunction(() => window.taskHover);
  for (const style of ['md3', 'material5', 'fluent'])
    for (const dark of [true, false]) {
      await page.evaluate((options) => window.taskHover.configure(options), {
        style,
        dark,
        tasks: native?.records
      });
      const badge = page.locator('.table-task-cell .task-preview-trigger');
      await badge.hover();
      await page.waitForTimeout(400); // Must exceed the production 260ms hover timer.
      assert.equal(
        await page.locator('.task-preview:popover-open').count(),
        0,
        'Badge hover must not replace the button with cards'
      );
      await badge.click();
      assert.equal(
        (await page.evaluate(() => window.taskHover.events())).at(-1).type,
        'inspect'
      );
      await page.locator('.table-task-cell .task-card-heading').hover();
      const popup = page.locator('.task-preview:popover-open');
      await popup.waitFor();
      const card = popup.locator('.task-card').first(),
        dates = card.locator('.task-card-dates');
      assert.equal((await card.boundingBox()).width, 220);
      assert(await dates.isVisible());
      const status = card.locator('.task-card-status'),
        assignee = card.locator('.task-card-assignee');
      const controls = await page.evaluate(() =>
        parseFloat(
          getComputedStyle(document.documentElement).getPropertyValue(
            '--control-height'
          )
        )
      );
      assert.equal((await status.boundingBox()).height, controls);
      assert.equal((await assignee.boundingBox()).height, controls);
      await dates.click();
      assert.equal(
        (await page.evaluate(() => window.taskHover.events())).at(-1).field,
        'bid_start_date'
      );
      const rect = await card.boundingBox();
      measurements.push({
        style,
        dark,
        width: rect.width,
        height: rect.height,
        editorHeight: controls,
        dates: true
      });
      if (process.env.TASK_HOVER_CAPTURE) {
        await mkdir(process.env.TASK_HOVER_CAPTURE, { recursive: true });
        await popup.screenshot({
          path:
            process.env.TASK_HOVER_CAPTURE +
            '/preview-ts-' +
            style +
            '-' +
            dark +
            '.png'
        });
      }
      await popup
        .getByRole('button', { name: 'Task Manager', exact: true })
        .click();
      assert.equal(await page.locator('.task-preview:popover-open').count(), 0);
    }
  await page.setViewportSize({ width: 320, height: 180 });
  await page.evaluate(() => window.taskHover.configure({ width: 180 }));
  await page.locator('.table-task-cell .task-card-heading').hover();
  const narrow = page.locator('.task-preview:popover-open');
  await narrow.waitFor();
  const scroller = narrow.locator('.task-preview-content');
  assert(
    await scroller.evaluate(
      (el) =>
        el.scrollWidth > el.clientWidth && el.scrollHeight > el.clientHeight
    )
  );
  await scroller.evaluate((el) => {
    el.scrollLeft = el.scrollWidth;
    el.scrollTop = el.scrollHeight;
  });
  await narrow.locator('.task-card').last().locator('.task-card-dates').click();
  assert.equal(
    (await page.evaluate(() => window.taskHover.events())).at(-1).process,
    'rig'
  );
  await narrow
    .getByRole('button', { name: 'Task Manager', exact: true })
    .click();
  await page.setViewportSize({ width: 800, height: 600 });
  await page.evaluate(() => window.taskHover.configure({ width: 100 }));
  const badge = page.locator('.table-task-cell .task-preview-trigger');
  await badge.hover();
  await page.waitForTimeout(400);
  assert.equal(await page.locator('.task-preview:popover-open').count(), 0);
  await badge.tap();
  await badge.focus();
  await page.keyboard.press('Enter');
  assert.equal(
    (await page.evaluate(() => window.taskHover.events())).at(-1).type,
    'inspect'
  );
  assert.deepEqual(errors, []);
  if (native)
    assert.deepEqual(
      measurements,
      native.measurements,
      'Actual expanded card dimensions match native'
    );
  if (process.env.TASK_HOVER_CAPTURE)
    await writeFile(
      process.env.TASK_HOVER_CAPTURE + '/browser.json',
      JSON.stringify({ measurements, errors }, null, 2)
    );
  console.log(
    'Task badge hover/click/tap/Enter; full-size dated previews and controls pass in three themes and both palettes.'
  );
} finally {
  await browser?.close();
  await server.close();
}
