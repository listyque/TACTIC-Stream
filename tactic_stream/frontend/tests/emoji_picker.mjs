import assert from 'node:assert/strict';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { firefox, chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = process.env.EMOJI_CAPTURE;
const engine = process.env.STREAM_BROWSER_ENGINE || 'firefox';
const catalog = JSON.parse(
  await readFile(root + 'frontend/src/assets/emoji.json', 'utf8')
);
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
let browser;
try {
  await server.listen();
  browser = await (engine === 'firefox' ? firefox : chromium).launch({
    headless: true,
    ...(engine === 'firefox' ? {} : { channel: 'msedge' })
  });
  const page = await browser.newPage({
    viewport: { width: 1000, height: 800 },
    deviceScaleFactor: Number(process.env.EMOJI_SCALE || 1)
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/emoji-fixture', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><div id="app"></div>'
    })
  );
  await page.goto(server.resolvedUrls.local[0] + 'emoji-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  const vueUrl = entry.code.match(/from "([^"]+)"/)[1];
  await page.evaluate(async (vueUrl) => {
    const { createApp, h, ref } = await import(vueUrl);
    const { default: Composer } = await import(
      '/frontend/src/features/messages/MessageComposer.vue'
    );
    const { appearance, initializeAppearance } = await import(
      '/frontend/src/appearance.js'
    );
    await import('/frontend/src/theme.css');
    await import('/frontend/src/style.css');
    initializeAppearance();
    Object.assign(appearance, {
      theme: 'md3',
      mode: 'dark',
      language: 'en',
      clickAnimations: false,
      hoverAnimations: false,
      popupAnimations: false
    });
    const text = ref('');
    createApp({
      render: () =>
        h(
          'div',
          { style: 'position:absolute;bottom:20px;left:20px;width:600px' },
          [
            h(Composer, {
              members: [],
              modelValue: text.value,
              'onUpdate:modelValue': (value) => (text.value = value)
            })
          ]
        )
    }).mount('#app');
  }, vueUrl);
  const picker = page.locator('.emoji-picker');
  await picker.getByLabel('Insert emoji', { exact: true }).click();
  await picker.locator('.emoji-grid button').first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  if (output) await mkdir(output, { recursive: true });
  const records = [];
  for (const index of [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]) {
    await picker
      .locator('[data-frame="emojiCategorySwitcher"] button')
      .nth(index)
      .click();
    if (index === 2) {
      assert.equal(
        await picker.getByText('No matching emoji', { exact: true }).count(),
        1,
        'The catalogue has no standalone Component records'
      );
      continue;
    }
    await picker.locator('.emoji-grid button').first().waitFor();
    records.push(
      await picker.evaluate((element) => ({
        category: element.querySelector('[data-frame=emojiCategorySwitcher]')
          ?.textContent,
        grid: element
          .querySelector('.emoji-grid')
          .getBoundingClientRect()
          .toJSON(),
        scroll: element.querySelector('.emoji-grid').scrollTop,
        buttons: [...element.querySelectorAll('.emoji-grid button')]
          .slice(0, 8)
          .map((button) => ({
            text: button.textContent,
            label: button.getAttribute('aria-label'),
            bounds: button.getBoundingClientRect().toJSON(),
            font: getComputedStyle(button).fontFamily
          }))
      }))
    );
    const painted = await picker
      .locator('.emoji-grid button')
      .first()
      .evaluate((button) => {
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 64;
        const ctx = canvas.getContext('2d'),
          style = getComputedStyle(button);
        ctx.font =
          style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(button.textContent, 32, 32);
        return ctx
          .getImageData(0, 0, 64, 64)
          .data.filter((value, index) => index % 4 === 3 && value).length;
      });
    assert(
      painted > 32,
      'Visible emoji must paint pixels, not only exist in the DOM: ' +
        records.at(-1).buttons[0].text
    );
    const row = records.at(-1);
    assert.equal(row.scroll, 0, 'Changing category resets the virtual scroll');
    for (const button of row.buttons) {
      assert(button.bounds.width >= 38 && button.bounds.height >= 38);
      assert(
        button.bounds.left >= row.grid.left &&
          button.bounds.right <= row.grid.right
      );
      assert.equal(button.bounds.top, row.grid.top);
    }
    if (output)
      await picker.locator('.account-panel').screenshot({
        path: output + '/' + engine + '-' + records.length + '.png'
      });
  }
  if (output)
    await writeFile(
      output + '/' + engine + '.json',
      JSON.stringify(records, null, 2)
    );
  const grid = picker.locator('.emoji-grid');
  assert(
    (await grid.locator('button').count()) <
      catalog.filter((row) => row.category === 'Smileys & Emotion').length,
    'Only visible emoji delegates are created'
  );
  await grid.evaluate((element) => {
    element.scrollTop = 380;
  });
  await page.waitForFunction(
    () =>
      Number(document.querySelector('.emoji-grid button')?.dataset.emojiIndex) >
      0
  );
  await picker.getByLabel('Find emoji', { exact: true }).fill('grinning face');
  await page.waitForFunction(
    () => document.querySelector('.emoji-grid')?.scrollTop === 0
  );
  await grid
    .getByRole('button', { name: 'grinning face', exact: true })
    .waitFor();
  const first = grid.locator('button').first();
  const value = await first.innerText();
  await first.focus();
  await page.keyboard.press('Enter');
  assert.equal(
    await page.getByLabel('Write a reply', { exact: true }).inputValue(),
    value
  );
  await page.setViewportSize({ width: 320, height: 700 });
  await picker.getByLabel('Insert emoji', { exact: true }).click();
  await first.waitFor();
  const popup = await picker.locator('.account-panel').boundingBox();
  assert(
    popup.x >= 0 &&
      popup.x + popup.width <= 321 &&
      popup.y >= 0 &&
      popup.y + popup.height <= 701
  );
  if (output)
    await picker
      .locator('.account-panel')
      .screenshot({ path: output + '/' + engine + '-narrow.png' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS ' +
      engine +
      ': all populated emoji categories paint pixels; empty Component, grid bounds, virtualization, scrolling, search, keyboard insertion and narrow popup'
  );
} finally {
  await browser?.close();
  await server.close();
}
