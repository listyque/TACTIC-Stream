import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
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
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/windows.html'
  );
  await page.waitForFunction(() => !!window.host);
  for (let index = 0; index < 5; index++) {
    await page.evaluate(() => {
      window.host.a.show();
      window.host.b.show();
    });
    await page.locator('#action').click();
    assert.equal(
      await page.locator('#a output').textContent(),
      String(index + 1),
      'First click on a background window must perform its action'
    );
  }
  const title = page.locator('#a > header');
  const before = await page.locator('#a').boundingBox();
  const titleBox = await title.boundingBox();
  await page.mouse.move(titleBox.x + 45, titleBox.y + 8);
  await page.mouse.down();
  await page.mouse.move(titleBox.x + 75, titleBox.y + 28);
  assert((await page.locator('#a').boundingBox()).x > before.x);
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.equal(
    await page.locator('#a').evaluate((node) => node.open),
    true,
    'Escape cancels a move before it can close the window'
  );
  assert(Math.abs((await page.locator('#a').boundingBox()).x - before.x) < 1);
  await page.mouse.move(titleBox.x + 45, titleBox.y + 8);
  await page.mouse.down();
  await page.mouse.move(titleBox.x + 75, titleBox.y + 28);
  await title.evaluate((node) => node.releasePointerCapture(1));
  await page.mouse.up();
  assert(
    Math.abs((await page.locator('#a').boundingBox()).x - before.x) < 1,
    'Lost pointer capture cancels the unfinished move'
  );
  await page.locator('#a input').fill('retained');
  await page.evaluate(() => window.host.b.show());
  await page.locator('#action').tap();
  assert.equal(await page.locator('#a output').textContent(), '6');
  await page
    .locator('#a')
    .getByRole('button', { name: 'Close A', exact: true })
    .click();
  assert.equal(await page.locator('#a').evaluate((node) => node.open), false);
  await page.evaluate(() => {
    window.host.b.close();
    window.host.owner.showModal();
  });
  await page.locator('#launcher').click();
  await page.locator('#child input').fill('child draft');
  await page
    .locator('#child')
    .getByRole('button', { name: 'Close child', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => document.activeElement.id),
    'launcher'
  );
  await page.locator('#launcher').click();
  assert.equal(await page.locator('#child input').inputValue(), 'child draft');
  await page.evaluate(() => window.host.owner.close());
  await page.waitForFunction(() => !window.host.child.open);
  await page.evaluate(() => {
    window.host.a.show();
    window.host.a.style.borderRadius = '20px';
  });
  const windowA = page.locator('#a');
  assert.equal(
    await windowA.evaluate((el) => getComputedStyle(el).borderTopLeftRadius),
    '8px'
  );
  assert.notEqual(
    await windowA.evaluate((el) => getComputedStyle(el).boxShadow),
    'none'
  );
  await windowA
    .getByRole('button', { name: 'Maximize window', exact: true })
    .click();
  assert.equal(
    await windowA.evaluate((el) => getComputedStyle(el).borderTopLeftRadius),
    '0px'
  );
  await windowA
    .getByRole('button', { name: 'Restore window', exact: true })
    .click();
  assert.equal(
    await windowA.evaluate((el) => getComputedStyle(el).borderTopLeftRadius),
    '8px'
  );
  const normalRect = await windowA.boundingBox();
  for (const maximized of [true, false]) {
    if (maximized)
      await windowA
        .getByRole('button', { name: 'Maximize window', exact: true })
        .click();
    await page.evaluate(() => {
      window.host.a.close();
      window.host.setHeader(false);
    });
    await page.waitForFunction(() => !document.querySelector('#a > header'));
    await page.evaluate(() => window.host.setHeader(true));
    await windowA.locator('header').waitFor({ state: 'attached' });
    await page.evaluate(() => window.host.a.show());
    await windowA
      .getByRole('button', {
        name: maximized ? 'Restore window' : 'Maximize window',
        exact: true
      })
      .waitFor();
    assert.equal(
      await windowA.evaluate((el) =>
        el.classList.contains('app-window-maximized')
      ),
      maximized
    );
    if (maximized)
      await windowA
        .getByRole('button', { name: 'Restore window', exact: true })
        .click();
    const restoredRect = await windowA.boundingBox();
    for (const key of ['x', 'y', 'width', 'height'])
      assert(Math.abs(restoredRect[key] - normalRect[key]) < 1, key);
  }
  const configuration = page.locator('#configuration');
  await page.evaluate(() => window.host.configuration.show());
  await configuration
    .getByRole('button', { name: 'Restore window', exact: true })
    .waitFor();
  for (const maximized of [true, false]) {
    await page.evaluate(() => {
      window.host.configuration.close();
      window.host.setHeader(false);
    });
    await page.waitForFunction(
      () => !document.querySelector('#configuration > header')
    );
    await page.evaluate(() => window.host.setHeader(true));
    await configuration.locator('header').waitFor({ state: 'attached' });
    await page.evaluate(() => window.host.configuration.show());
    await configuration
      .getByRole('button', {
        name: maximized ? 'Restore window' : 'Maximize window',
        exact: true
      })
      .waitFor();
    assert.equal(
      await configuration.evaluate((el) =>
        el.classList.contains('app-window-maximized')
      ),
      maximized
    );
    if (maximized)
      await configuration
        .getByRole('button', { name: 'Restore window', exact: true })
        .click();
  }
  assert.deepEqual(errors, []);
  console.log(
    'Window lifecycle: first click/tap, focus return, child owner close and retained draft passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
