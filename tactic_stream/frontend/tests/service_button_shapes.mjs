import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import records from '../../tests/fixtures/frame_service_buttons.json' with { type: 'json' };
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
  browser = await chromium.launch({
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 800, height: 700 },
    hasTouch: true
  });
  const errors = [],
    results = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_controls/service-buttons.html'
  );
  await page.waitForFunction(() => window.serviceButtons);
  const ids = [
    'mainClose',
    'mainSave',
    ...records.map((record) => record.id),
    'serviceCount',
    'serviceFilter',
    'serviceSummary',
    'serviceReaction'
  ];
  for (const style of ['md3', 'material5', 'fluent'])
    for (const dark of [true, false])
      for (const width of [320, 800]) {
        await page.setViewportSize({ width, height: 700 });
        await page.evaluate(
          (options) => window.serviceButtons.configure(options),
          { style, dark, width }
        );
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))
            )
        );
        for (const id of ids) {
          const control = page.locator(
            `[data-frame="${id}"],[data-shape="${id}"]`
          );
          const radius = await control.evaluate((el) =>
            Math.min(
              el.offsetHeight / 2,
              parseFloat(
                getComputedStyle(
                  el,
                  el.classList.contains('filled-action') ? '::before' : null
                ).borderTopLeftRadius
              )
            )
          );
          const box = await control.boundingBox();
          assert.equal(
            radius,
            id.startsWith('main') ? box.height / 2 : 4,
            style + ' ' + id
          );
          let before = (
            await page.evaluate(() => window.serviceButtons.events())
          ).length;
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.mouse.down();
          assert.equal(
            await control.evaluate((el) =>
              Math.min(
                el.offsetHeight / 2,
                parseFloat(
                  getComputedStyle(
                    el,
                    el.classList.contains('filled-action') ? '::before' : null
                  ).borderTopLeftRadius
                )
              )
            ),
            radius
          );
          await page.mouse.up();
          assert.equal(
            (await page.evaluate(() => window.serviceButtons.events())).length,
            before + (id !== 'serviceDisabled')
          );
          if (id !== 'serviceDisabled') {
            await control.focus();
            await page.keyboard.press('Space');
            await control.tap();
            assert.equal(
              (await page.evaluate(() => window.serviceButtons.events()))
                .length,
              before + 3,
              id
            );
          }
          results.push({
            style,
            dark,
            width,
            id,
            x: box.x,
            y: box.y,
            controlWidth: box.width,
            height: box.height,
            radius
          });
        }
        if (process.env.SERVICE_BUTTON_CAPTURE) {
          await mkdir(process.env.SERVICE_BUTTON_CAPTURE, { recursive: true });
          await page.screenshot({
            path:
              process.env.SERVICE_BUTTON_CAPTURE +
              `/browser-${style}-${dark}-${width}.png`
          });
        }
      }
  assert.deepEqual(errors, []);
  if (process.env.SERVICE_BUTTON_CAPTURE) {
    await writeFile(
      process.env.SERVICE_BUTTON_CAPTURE + '/browser.json',
      JSON.stringify(results)
    );
    const native = JSON.parse(
      await readFile(
        process.env.SERVICE_BUTTON_CAPTURE + '/native.json',
        'utf8'
      )
    );
    assert.equal(results.length, native.length);
    results.forEach((row, index) =>
      assert.deepEqual(row, native[index], row.style + ' ' + row.id)
    );
  }
  console.log(
    'Service squares/main chrome: three themes, both palettes, 320/800, hover/press/keyboard/touch pass.'
  );
} finally {
  await browser?.close();
  await server.close();
}
