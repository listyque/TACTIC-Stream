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
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
try {
  const page = await browser.newPage({
      viewport: { width: 1200, height: 850 }
    }),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_foundation/chrome.html'
  );
  await page.waitForFunction(() => window.chromeFixture);
  for (const kind of ['legacy', 'framed']) {
    await page.evaluate((kind) => window.chromeFixture[kind].show(), kind);
    const dialog = page.locator('#' + kind),
      header = dialog.locator('> .app-window-titlebar');
    await header.waitFor();
    const restore = dialog.getByRole('button', {
      name: 'Restore window',
      exact: true
    });
    if (await restore.count()) await restore.click();
    const bounds = await dialog.boundingBox(),
      title = await header.boundingBox();
    assert.equal(title.height, 40);
    assert(
      Math.abs(title.x - bounds.x - 1) < 1,
      'Title must meet the left window border ' +
        JSON.stringify({
          kind,
          bounds,
          title,
          style: await header.evaluate((el) => ({
            padding: el.parentElement.style.cssText,
            margin: getComputedStyle(el).margin,
            vars: el.style.cssText
          }))
        })
    );
    assert(
      Math.abs(title.y - bounds.y - 1) < 1,
      'Title must meet the top window border'
    );
    assert.equal(
      await dialog.evaluate((el) => getComputedStyle(el).borderRadius),
      '8px'
    );
    const close = header.getByRole('button', {
      name: kind === 'legacy' ? 'Close editor' : 'Close',
      exact: true
    });
    const button = await close.boundingBox();
    assert.equal(button.width, 34);
    assert.equal(button.height, 34);
    await page.evaluate(() => window.chromeFixture.busy(true));
    await close.waitFor();
    assert(await close.isDisabled());
    await page.evaluate(() => window.chromeFixture.busy(false));
    const input = dialog.getByRole('textbox');
    await input.fill('retained');
    await dialog
      .getByRole('button', { name: 'Maximize window', exact: true })
      .click();
    assert.equal(
      await dialog.evaluate((el) => getComputedStyle(el).borderRadius),
      '0px'
    );
    await dialog
      .getByRole('button', { name: 'Restore window', exact: true })
      .click();
    await page.evaluate(() => window.chromeFixture.dirty(true));
    await close.click();
    await dialog.getByRole('alert').waitFor();
    assert.equal(await input.inputValue(), 'retained');
    await page.keyboard.press('Escape');
    assert(await dialog.isVisible());
    await page.evaluate(() => window.chromeFixture.dirty(false));
    await close.click();
    assert(!(await dialog.isVisible()));
  }
  for (const theme of ['md3', 'material5', 'fluent']) {
    await page.evaluate((theme) => {
      window.chromeAppearance.theme = theme;
      window.chromeFixture.confirmation.show();
    }, theme);
    const dialog = page.getByRole('dialog', {
      name: 'Discard changes?',
      exact: true
    });
    assert.equal(
      await dialog.evaluate((el) => getComputedStyle(el).borderRadius),
      '8px'
    );
    assert.equal((await dialog.locator('header').boundingBox()).height, 40);
    await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  }
  for (const [top, side] of [
    [20, 20],
    [0, 20],
    [0, 0]
  ]) {
    await page.evaluate(
      ({ top, side }) => {
        const element = document.createElement('dialog');
        element.id = 'compact';
        element.className = 'record-dialog';
        element.style.cssText = `padding:${top}px ${side}px;--dialog-content-top:${top}px;--dialog-content-side:${side}px;width:400px`;
        element.innerHTML =
          '<header><h2>Confirmation</h2></header><p>Keep draft?</p>';
        document.body.append(element);
        element.showModal();
      },
      { top, side }
    );
    const dialog = page.locator('#compact'),
      bounds = await dialog.boundingBox(),
      header = await dialog.locator('header').boundingBox();
    assert.equal(header.height, 40);
    assert(Math.abs(header.x - bounds.x - 1) < 1);
    assert(Math.abs(header.y - bounds.y - 1) < 1);
    await dialog.evaluate((element) => {
      element.close();
      element.remove();
    });
  }
  await page.evaluate(() => {
    const panel = document.createElement('section');
    panel.className = 'record-dialog';
    panel.id = 'inline-panel';
    panel.innerHTML = '<header style="height:75px">Embedded panel</header>';
    document.body.append(panel);
  });
  assert.equal(
    (await page.locator('#inline-panel > header').boundingBox()).height,
    75,
    'Window normalization must not resize embedded panels'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Window chrome: legacy and Frame hosts, close guards, disabled controls, geometry, drafts and three themes passed'
  );
} finally {
  await browser.close();
  await server.close();
}
