// Produce a self-contained, file://-usable catalog and exercise the delivered artifact.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = root + 'tools/frame_controls/output/';
await mkdir(output, { recursive: true });
const result = await build({
  root,
  configFile: false,
  publicDir: false,
  define: { 'process.env.NODE_ENV': '"production"' },
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'error',
  build: {
    write: false,
    minify: true,
    lib: {
      entry: root + 'tools/frame_controls/variants.entry.js',
      name: 'FrameControlsCatalog',
      cssFileName: 'catalog',
      formats: ['iife']
    }
  }
});
const bundle = Array.isArray(result) ? result[0] : result;
let css = bundle.output
  .filter((asset) => asset.type === 'asset' && asset.fileName.endsWith('.css'))
  .map((asset) => asset.source)
  .join('\n');
const emoji = await readFile(
  root + 'frontend/public/assets/NotoColorEmoji.ttf'
);
css = css.replaceAll(
  '/assets/NotoColorEmoji.ttf',
  'data:font/ttf;base64,' + emoji.toString('base64')
);
const js = bundle.output
  .filter((asset) => asset.type === 'chunk')
  .map((chunk) => chunk.code)
  .join('\n');
const template = await readFile(
  root + 'tools/frame_controls/catalog.html',
  'utf8'
);
await writeFile(
  output + 'catalog.html',
  template
    .replace('__STYLES__', () => css)
    .replace('__APPLICATION__', () => js.replaceAll('</script', '<\\/script'))
);
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 }
    }),
    errors = [],
    requests = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  await page.goto(pathToFileURL(output + 'catalog.html').href);
  await page.waitForFunction(() => window.controlVariants);
  await page.locator('#family').selectOption('numbers');
  await page.locator('#example').selectOption('decimal');
  const number = page.getByRole('spinbutton');
  await number.fill('2.5');
  await number.press('Enter');
  assert.equal(
    await page.evaluate(() => window.controlVariants.model.value),
    2.5
  );
  await page.locator('#language').selectOption('ru');
  await page.locator('#mode').selectOption('light');
  await page.locator('#width').selectOption('900');
  assert.equal(await number.inputValue(), '2,5');
  assert.equal(
    await page.evaluate(() => window.controlVariants.model.value),
    2.5
  );
  await page.locator('#state').selectOption('readonly');
  assert((await number.isEditable()) === false);
  await page.locator('#reset').click();
  assert.equal(
    await page.evaluate(() => window.controlVariants.model.value),
    1.25
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, [], 'Offline catalog makes no network requests');
  console.log(
    'Offline executable catalog: examples, input, retained values across language/theme/resize, readonly and reset PASS'
  );
} finally {
  await browser.close();
}
