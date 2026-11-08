import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
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
  const context = await browser.newContext({
    viewport: { width: 1200, height: 800 }
  });
  const errors = [];
  let batch = '',
    submits = 0;
  await context.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    if (payload.method === 'get_base_dirs')
      return route.fulfill({ json: { result: {} } });
    const values = payload.args[2];
    assert.equal(values.action, 'plan');
    return route.fulfill({
      json: { result: { info: { plan: { version: 1, files: [] } } } }
    });
  });
  await context.route('**/admin/checkin-queue/submit', async (route) => {
    const body = route.request().postData();
    batch = body.match(/name="batch_id"\r\n\r\n([a-z0-9-]+)/)[1];
    submits++;
    await route.abort('failed');
  });
  await context.route('**/admin/checkin-queue/updates', async (route) => {
    const { batches } = route.request().postDataJSON();
    const checkins = batches.some((item) => item.batch_id === batch)
      ? [
          {
            batch_id: batch,
            operation_id: 'publish',
            state: 'complete',
            snapshot: { code: 'SNAP1', version: 1 }
          }
        ]
      : [];
    await route.fulfill({ json: { result: { checkins } } });
  });
  const first = await context.newPage(),
    second = await context.newPage();
  const configure = async (page) => {
    await page.waitForFunction(() => window.filesFixture);
    await page.evaluate(() =>
      window.filesFixture.show({
        screen: 'queue',
        width: 1100,
        height: 740,
        style: 'md3',
        dark: true,
        language: 'en',
        model: { queue: [] },
        restoreQueue: true
      })
    );
  };
  for (const page of [first, second]) {
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(server.resolvedUrls.local[0] + 'tools/frame_files/');
    await configure(page);
  }
  const enqueue = (page, name) =>
    page.evaluate(
      (name) =>
        window.filesFixture.queue().enqueue({
          name,
          title: name,
          ticket: 'fixture',
          project: 'cg',
          searchKey: 'cg/asset?code=ONE',
          files: [new File(['source'], name)],
          process: 'publish',
          context: `publish/${name}`
        }),
      name
    );
  await Promise.all([
    enqueue(first, 'first.txt'),
    enqueue(second, 'second.txt')
  ]);
  await first.getByText('second.txt', { exact: true }).first().waitFor();
  await second.getByText('first.txt', { exact: true }).first().waitFor();
  await first.getByRole('button', { name: 'Commit all', exact: true }).click();
  await first
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Completed' })
    .waitFor();
  await second.reload();
  await configure(second);
  await second
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Completed' })
    .waitFor();
  await second
    .locator('[data-frame^=commitQueueState_]')
    .filter({ hasText: 'Missing files' })
    .waitFor();
  assert.equal(submits, 1);
  assert.deepEqual(errors, []);
} finally {
  await browser?.close();
  await server.close();
}
