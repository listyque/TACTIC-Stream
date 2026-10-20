import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
let server, browser;
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [vue()],
    publicDir: root + 'frontend/public',
    resolve: {
      alias: {
        vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
      }
    },
    logLevel: 'error',
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 900 },
    acceptDownloads: true,
    hasTouch: true
  });
  const errors = [],
    reads = [],
    downloads = [];
  let failure = '',
    preparedFiles = [
      {
        code: 'F1',
        filename: 'scene.ma',
        type: 'main',
        size: 6,
        href: '/assets/scene.ma'
      },
      {
        code: 'F2',
        filename: 'reference #100%.txt',
        type: 'reference',
        size: 6,
        href: '/assets/reference%20%23100%25.txt'
      }
    ];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('download', (item) => downloads.push(item));
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    if (payload.method === 'log')
      return route.fulfill({ json: { result: true } });
    assert.equal(payload.method, 'execute_cmd');
    assert.equal(payload.args[0].project, 'cg');
    assert.equal(payload.args[1], 'tactic.ui.table.TableSnapshotFilesCmd');
    assert.equal(payload.args[2].search_key, 'sthpw/snapshot?code=S7');
    reads.push(payload);
    if (failure)
      return route.fulfill({ status: 400, json: { error: failure } });
    await route.fulfill({
      json: {
        result: {
          info: {
            snapshot: {
              code: 'S7',
              version: 7,
              project_code: 'cg',
              context: 'publish/reference',
              __search_key__: 'sthpw/snapshot?code=S7'
            },
            files: preparedFiles
          }
        }
      }
    });
  });
  await page.route(
    /\/assets\/(?:scene\.ma|reference%20%23100%25\.txt)$/,
    (route) =>
      route.fulfill({ body: 'remote', contentType: 'application/octet-stream' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_files/');
  await page
    .waitForFunction(() => window.filesFixture)
    .catch((error) => {
      assert.deepEqual(errors, []);
      throw error;
    });
  const dialog = page.locator('.snapshot-checkout[open]');
  const field = (id) => dialog.locator('[data-frame=' + id + ']');
  async function show(width = 760, language = 'en') {
    await page.evaluate(
      ({ width, language }) =>
        window.filesFixture.show({
          screen: 'snapshot-checkout',
          width,
          height: 700,
          style: 'md3',
          dark: true,
          language,
          model: {}
        }),
      { width, language }
    );
    await dialog
      .locator('.snapshot-checkout-workspace[aria-busy=false]')
      .waitFor();
  }
  for (const [code, filename] of [
    ['F3', '\ue000.txt'],
    ['F4', '\u{10000}.txt']
  ])
    preparedFiles.push({ ...preparedFiles[1], code, filename });
  Object.assign(preparedFiles[2], { size: null, type: null });
  preparedFiles.reverse();
  await show();
  await field('snapshotCheckoutFile_F1').waitFor();
  assert.deepEqual(
    await dialog
      .locator('[data-frame^=snapshotCheckoutFile_]')
      .evaluateAll((nodes) => nodes.map((node) => node.dataset.frame)),
    [
      'snapshotCheckoutFile_F1',
      'snapshotCheckoutFile_F2',
      'snapshotCheckoutFile_F4',
      'snapshotCheckoutFile_F3'
    ]
  );
  const body = await dialog
    .locator('.snapshot-checkout-workspace')
    .boundingBox();
  assert.equal(await field('snapshotCheckoutSize_F3').innerText(), '0 B');
  assert.equal(body.width, 760);
  assert.equal(
    body.height,
    560,
    'Browser titlebar leaves the native client viewport intact'
  );
  await field('snapshotCheckoutFile_F2').tap();
  assert.equal(
    await field('snapshotCheckoutFile_F2').getAttribute('aria-selected'),
    'true'
  );
  assert.equal(
    await field('snapshotCheckoutFile_F2')
      .locator('.item-surface')
      .evaluate(
        (node) =>
          getComputedStyle(node).getPropertyValue('--item-base').trim() ===
          getComputedStyle(node).getPropertyValue('--content-selection').trim()
      ),
    true
  );
  const nextDownload = page.waitForEvent('download');
  await field('snapshotCheckoutDownload').tap();
  const downloaded = await nextDownload;
  assert.equal(downloaded.suggestedFilename(), 'reference #100%.txt');
  assert.equal((await readFile(await downloaded.path())).toString(), 'remote');
  await field('snapshotCheckout_message')
    .filter({ hasText: 'Download completed' })
    .waitFor();
  await field('snapshotCheckoutClose').tap();
  await dialog.waitFor({ state: 'hidden' });
  preparedFiles = [];
  await show();
  await field('snapshotCheckoutEmpty').waitFor();
  assert.equal(await field('snapshotCheckoutDownload').isEnabled(), false);
  await field('snapshotCheckoutClose').tap();
  failure = 'Snapshot is no longer available';
  await show();
  await field('snapshotCheckout_error').filter({ hasText: failure }).waitFor();
  assert.equal(await field('snapshotCheckoutDownload').isEnabled(), false);
  await field('snapshotCheckoutClose').tap();
  failure = '';
  preparedFiles = [
    {
      code: 'SLOW',
      filename: 'slow.dat',
      type: 'main',
      size: 6,
      href: '/assets/slow.dat'
    }
  ];
  let held;
  await page.route('**/assets/slow.dat', (route) => {
    held = route;
  });
  await show();
  const pending = page.waitForRequest('**/assets/slow.dat');
  await field('snapshotCheckoutDownload').tap();
  await pending;
  await field('snapshotCheckoutDownload')
    .filter({ hasText: 'Cancel transfer' })
    .tap();
  await field('snapshotCheckout_message')
    .filter({ hasText: 'Download cancelled' })
    .waitFor();
  assert.equal(
    downloads.length,
    1,
    'Cancelled HTTP does not publish a browser download'
  );
  await held.abort().catch(() => {});
  await field('snapshotCheckoutClose').tap();
  await show();
  const pendingSignout = page.waitForRequest('**/assets/slow.dat');
  await field('snapshotCheckoutDownload').tap();
  await pendingSignout;
  await page.evaluate(() =>
    window.filesFixture.session({ ticket: 'changed-session' })
  );
  await dialog.waitFor({ state: 'hidden' });
  await held.abort().catch(() => {});
  assert.equal(
    downloads.length,
    1,
    'A new session cannot receive a stale download'
  );
  preparedFiles = Array.from({ length: 30 }, (_, index) => ({
    code: 'FILE' + index,
    filename: 'Long reference file ' + index + '.txt',
    type: 'reference',
    size: 6,
    href: '/assets/reference.txt'
  }));
  await page.setViewportSize({ width: 320, height: 740 });
  await show(320, 'ru');
  for (const [id, text] of [
    ['snapshotCheckoutClose', 'Закрыть'],
    ['snapshotCheckoutDownload', 'Получить файлы']
  ]) {
    assert.equal(await field(id).getAttribute('aria-label'), text);
    assert(
      await field(id).evaluate((node, text) => {
        const labels = [
          ...node.querySelectorAll(':scope > span:not(.app-icon)')
        ];
        return (
          labels.some((label) => label.textContent.trim() === text) &&
          labels.every((label) => label.scrollWidth <= label.clientWidth)
        );
      }, text)
    );
  }
  await field('snapshotCheckoutFiles').evaluate((node) => {
    node.scrollTop = 500;
  });
  assert(
    (await field('snapshotCheckoutFiles').evaluate((node) => node.scrollTop)) >
      0
  );
  const geometry = await field('snapshotCheckoutDownload').boundingBox();
  assert(geometry.x >= 0 && geometry.x + geometry.width <= 320);
  assert.equal(
    await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth),
    true
  );
  await field('snapshotCheckoutClose').tap();
  assert.deepEqual(errors, []);
  console.log(
    'Snapshot checkout actual input: selected bytes/name, native viewport, empty/error, HTTP cancel, session disposal and scroll at 320px passed.'
  );
} finally {
  await browser?.close();
  await server?.close();
}
