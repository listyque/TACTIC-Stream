import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { readFile, mkdir } from 'node:fs/promises';
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
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true
  });
  const errors = [],
    requests = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/ui/help/**', async (route) => {
    const file = new URL(route.request().url()).pathname.slice(
      '/ui/help/'.length
    );
    requests.push(file);
    await route.fulfill({
      body: await readFile(root + 'frontend/public/help/' + file),
      contentType: file.endsWith('.json')
        ? 'application/json'
        : 'text/plain; charset=utf-8'
    });
  });
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_help/index.html'
  );
  await page.waitForFunction(() => !!window.help?.value);
  await page.evaluate(() => window.help.value.open('windows'));
  const help = page.getByRole('dialog', { name: 'Help', exact: true });
  await help
    .getByRole('heading', { name: 'Windows and modal editors', exact: true })
    .waitFor();
  const search = help.getByRole('textbox', {
    name: 'Search help',
    exact: true
  });
  await search.fill('nothing matches this topic');
  await help
    .getByText('No help topics match your search', { exact: true })
    .waitFor();
  await search.fill('');
  const article = help.locator('.document-pane');
  await article.evaluate((node) => {
    node.scrollTop = 300;
  });
  const offset = await article.evaluate((node) => node.scrollTop);
  assert(offset > 0);
  const before = requests.length;
  await help.getByRole('button', { name: 'Close help', exact: true }).click();
  await page.evaluate(() => window.help.value.open());
  await help
    .getByRole('heading', { name: 'Windows and modal editors', exact: true })
    .waitFor();
  assert.equal(
    requests.length,
    before,
    'Cached reopen must not reload all articles'
  );
  assert(
    Math.abs((await article.evaluate((node) => node.scrollTop)) - offset) <= 1,
    'Reopen restores the document position'
  );
  for (let round = 1; round <= 5; round++) {
    const expected = offset + round * 20;
    await article.evaluate((node, value) => {
      node.scrollTop = value;
    }, expected);
    await help.getByRole('button', { name: 'Close help', exact: true }).click();
    await page.evaluate(() => window.help.value.open());
    assert(
      Math.abs((await article.evaluate((node) => node.scrollTop)) - expected) <=
        1,
      'Immediate scroll/close/reopen keeps the latest position'
    );
  }
  await page.evaluate(() => window.help.value.open('overview'));
  await help
    .getByRole('link', { name: 'Notes and messages', exact: true })
    .click();
  await help
    .getByRole('heading', { name: 'Notes and messages', exact: true })
    .waitFor();
  const download = page.waitForEvent('download');
  await help
    .getByRole('button', { name: 'Download article', exact: true })
    .click();
  assert.equal((await download).suggestedFilename(), 'communication.en.md');
  await page.setViewportSize({ width: 320, height: 740 });
  await help.getByRole('button', { name: 'Help topics', exact: true }).click();
  await search.fill('Windows and modal editors');
  await help
    .getByRole('button', { name: 'Windows and modal editors', exact: true })
    .click();
  await help
    .getByRole('heading', { name: 'Windows and modal editors', exact: true })
    .waitFor();
  assert(
    await article.evaluate((node) => node.scrollWidth <= node.clientWidth)
  );
  const box = await help.boundingBox();
  assert(box.x >= 0 && box.x + box.width <= 321);
  await help.getByRole('button', { name: 'Close help', exact: true }).click();
  const hiddenRequests = requests.length;
  await page.evaluate(() => {
    window.appearance.language = 'ru';
  });
  assert.equal(
    requests.length,
    hiddenRequests,
    'A hidden reader does not load on language changes'
  );
  await page.evaluate(() => window.help.value.open('overview'));
  const russian = page.locator('dialog.help-view');
  await russian.getByRole('heading', { name: 'Обзор', exact: true }).waitFor();
  await mkdir(root + 'tools/frame_help/output', { recursive: true });
  await russian.screenshot({
    path: root + 'tools/frame_help/output/help-mobile.png'
  });
  assert.deepEqual(errors, []);
  console.log(
    'Help: real search, links, download, cached reopen/scroll, hidden language change and 320px passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
