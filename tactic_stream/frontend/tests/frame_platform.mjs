import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const repo = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root: repo,
  configFile: false,
  resolve: {
    alias: {
      vue: repo + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: { ignored: ['**/.tmp/**', '**/.venv/**', '**/output/**'] }
  }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  for (const scale of [1, 1.5, 2]) {
    const page = await browser.newPage({
      viewport: { width: 640, height: 360 },
      deviceScaleFactor: scale
    });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(
      `http://127.0.0.1:${server.httpServer.address().port}/tools/frame_foundation/platform.html`
    );
    await page.waitForFunction(() => window.framePlatform);
    await page.evaluate(() => window.framePlatform.populate(10000));
    await page.locator('[data-frame="edit_0"]').waitFor();
    const editor = page.locator('[data-frame="edit_0"]');
    await editor.fill('Edited draft');
    await editor.evaluate((input) => {
      window.originalFrameEditor = input;
      input.setSelectionRange(2, 5);
    });
    await page.evaluate(() => window.framePlatform.reverse());
    await page.waitForFunction(
      () => window.framePlatform.rows.value[0].id === '9999'
    );
    assert(
      await editor.evaluate((input) => input === window.originalFrameEditor)
    );
    assert.deepEqual(
      await editor.evaluate((input) => ({
        text: input.value,
        start: input.selectionStart,
        end: input.selectionEnd,
        focused: document.activeElement === input
      })),
      { text: 'Edited draft', start: 2, end: 5, focused: true }
    );
    assert.equal(
      await editor.evaluate((input) => getComputedStyle(input).fontSize),
      '13px'
    );
    assert((await page.locator('[data-frame-row]').count()) < 30);
    await page.evaluate(() => window.framePlatform.populate(0));
    await page.waitForFunction(
      () => !document.querySelector('[data-frame-row]')
    );
    assert.equal(
      await page
        .locator('[data-frame="arrayRows"]')
        .evaluate((element) => element.scrollTop),
      0
    );
    await page.evaluate(() => window.framePlatform.populate(20));
    await editor.waitFor();
    await editor.focus();
    await editor.evaluate((input) => {
      input.dispatchEvent(
        new CompositionEvent('compositionstart', { bubbles: true })
      );
      input.value = 'Draft 0Ж';
      input.dispatchEvent(
        new InputEvent('input', { bubbles: true, isComposing: true, data: 'Ж' })
      );
      input.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'Enter',
          bubbles: true,
          isComposing: true
        })
      );
      input.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'Enter',
          bubbles: true,
          keyCode: 229
        })
      );
    });
    assert.equal(
      await page.evaluate(() => window.framePlatform.rows.value[0].text),
      'Draft 0'
    );
    assert.equal(
      await page.evaluate(() => window.framePlatform.commits.value),
      0
    );
    await page.evaluate(() => window.framePlatform.reverse());
    assert.equal(await editor.inputValue(), 'Draft 0Ж');
    await editor.dispatchEvent('compositionend');
    await page.waitForFunction(() =>
      window.framePlatform.rows.value.some(
        (row) => row.id === '0' && row.text === 'Draft 0Ж'
      )
    );
    const unusual = 'id/"[]:ю';
    await page.evaluate((id) => {
      window.framePlatform.rows.value = [{ id, text: 'Named editor' }];
    }, unusual);
    await page.waitForFunction(
      () => document.querySelector('input')?.value === 'Named editor'
    );
    assert(
      await page.evaluate(
        (id) => window.framePlatform.focus('edit_' + id),
        unusual
      )
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.value),
      'Named editor'
    );
    await page.evaluate(() => window.framePlatform.populate(1000));
    await page.waitForFunction(() =>
      document.querySelector('[data-frame="edit_0"]')
    );
    await page.evaluate(() => {
      document.activeElement.blur();
      document.querySelector('[data-frame="arrayRows"]').scrollTop = 4000;
      window.framePlatform.reverse();
    });
    await page.waitForFunction(() =>
      document.querySelector('[data-frame="edit_899"]')
    );
    assert.equal(
      await page
        .locator('[data-frame="arrayRows"]')
        .evaluate((element) => element.scrollTop),
      4000
    );
    await page.evaluate(() => window.framePlatform.populate(10));
    await editor.fill('Pending draft');
    await page.evaluate(() => {
      window.framePlatform.rows.value = window.framePlatform.rows.value.filter(
        (row) => row.id !== '0'
      );
    });
    await page.waitForFunction(
      () => !document.querySelector('[data-frame="edit_0"]')
    );
    assert.deepEqual(
      await page.evaluate(() => window.framePlatform.rows.value[0]),
      { id: '1', text: 'Draft 1' }
    );
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(
    'Frame browser platform: 10k rows, bounded delegates, retained editor/draft/focus/selection, clear/regrow and 1/1.5/2 DPR passed.'
  );
} finally {
  await browser?.close();
  await server.close();
}
