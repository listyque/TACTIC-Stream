import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output =
  process.argv[2] || root + '.screenshots/snapshot-browser-current';
const projection = JSON.parse(
  await readFile(output + '/projection.json', 'utf8')
);
for (const row of projection.previews)
  row.url = row.qualityUrl = '/comparison-image/' + row.file.token + '.png';
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  logLevel: 'error',
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 940, height: 700 },
    hasTouch: true,
    colorScheme: 'dark'
  });
  page.setDefaultTimeout(8000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/result-items', (route) =>
    route.fulfill({ json: { result: projection } })
  );
  await page.route('**/comparison-image/*.png', (route) =>
    route.fulfill({
      path:
        output + '/' + new URL(route.request().url()).pathname.split('/').at(-1)
    })
  );
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_objects/');
  await page.waitForFunction(() => window.objectsFixture);
  for (const [width, height] of [
    [440, 500],
    [880, 650]
  ]) {
    await page.evaluate(
      ({ width, height }) =>
        window.objectsFixture.show({
          screen: 'snapshot-browser',
          width,
          height,
          style: 'md3',
          dark: true,
          language: 'en',
          model: {
            target: {
              project: 'one',
              key: 'one/snapshot_assets?code=SNAPSHOT_A'
            }
          }
        }),
      { width, height }
    );
    const surface = page.locator('.snapshot-browser');
    await page.getByLabel('Snapshot Browser options', { exact: true }).tap();
    await page
      .getByRole('button', { name: 'Compare snapshots', exact: true })
      .tap();
    const panel = page.getByRole('region', {
      name: 'Compare snapshots',
      exact: true
    });
    const a = panel.getByRole('combobox', { name: 'Snapshot A', exact: true });
    const b = panel.getByRole('combobox', { name: 'Snapshot B', exact: true });
    assert.match(
      await a.locator('option:checked').textContent(),
      /v2 · publish/
    );
    assert.match(
      await b.locator('option:checked').textContent(),
      /v1 · publish/
    );
    await a.selectOption({ index: 0 });
    assert.match(
      await a.locator('option:checked').textContent(),
      /v-1 · publish/
    );
    await a.selectOption({ index: 1 });
    await panel.locator('[data-comparison="A"] img').waitFor();
    await panel.locator('[data-comparison="B"] img').waitFor();
    await surface.screenshot({
      path: `${output}/stream-compare-side-${width}.png`,
      animations: 'disabled'
    });
    await panel
      .getByRole('radio', { name: 'Image divider', exact: true })
      .tap();
    const slider = panel.getByRole('slider', {
      name: 'Image divider',
      exact: true
    });
    await slider.press('ArrowRight');
    assert.equal(await slider.inputValue(), '51');
    await surface.screenshot({
      path: `${output}/stream-compare-divider-${width}.png`,
      animations: 'disabled'
    });
    await panel
      .getByRole('button', { name: 'Close comparison', exact: true })
      .tap();
    await panel.waitFor({ state: 'hidden' });
  }
  assert.deepEqual(errors, []);
} finally {
  await browser?.close();
  await server.close();
}
