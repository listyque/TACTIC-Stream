import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

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
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1000, height: 900 }
  });
  const errors = [];
  await page.addInitScript(() => {
    Object.defineProperty(crypto, 'randomUUID', { value: undefined });
  });
  page.on('pageerror', (error) => errors.push(error.message));
  let saved = '2',
    running = 2,
    restart = '',
    probes = 0,
    requests = 0;
  let instance = '11111111-1111-4111-8111-111111111111';
  const runtime = () => ({
    available: true,
    state: 'running',
    instance_id: instance,
    restart_id: restart,
    web_workers: running
  });
  const configuration = () => ({
    revision: 'revision-' + saved,
    writable: true,
    undocumented: [],
    event_clients: [],
    runtime: runtime(),
    groups: [
      {
        title: 'Services and workers',
        settings: [
          {
            path: 'services/process_count',
            label: 'Web workers',
            description: 'Worker processes',
            value: saved,
            default: '3',
            editable: true,
            restart: true,
            input_type: 'integer'
          }
        ]
      }
    ]
  });
  await page.route('**/admin/**', (route) =>
    route.fulfill({ json: { result: [] } })
  );
  await page.route('**/admin/configuration{,/**}', async (route) => {
    const body = route.request().postDataJSON();
    assert.equal(body.ticket, 'fixture-ticket');
    const action = new URL(route.request().url()).pathname.split('/').at(-1);
    let result;
    if (action === 'save') {
      assert.deepEqual(body.changes, { 'services/process_count': '3' });
      saved = '3';
      result = configuration();
    } else if (action === 'restart') {
      requests++;
      restart = body.request_id;
      result = runtime();
    } else if (action === 'runtime') {
      if (++probes === 1) return route.abort('connectionrefused');
      running = 3;
      instance = '22222222-2222-4222-8222-222222222222';
      result = runtime();
    } else result = configuration();
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ result })
    });
  });
  await page.route('**/admin/rpc', (route) =>
    route.fulfill({ json: { result: [] } })
  );
  await page.route('**/server-placement-fixture', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<div id="app"></div>' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'server-placement-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  const vueUrl = entry.code.match(/from "([^"]+)"/)[1];
  await page.evaluate(async (vueUrl) => {
    const { createApp } = await import(vueUrl);
    const { default: App } = await import('/frontend/src/App.vue');
    const { windowDirective } = await import(
      '/frontend/src/controls/window.js'
    );
    await import('/frontend/src/theme.css');
    await import('/frontend/src/style.css');
    const { appearance, initializeAppearance } = await import(
      '/frontend/src/appearance.js'
    );
    initializeAppearance();
    Object.assign(appearance, {
      mode: 'dark',
      theme: 'md3',
      clickAnimations: false,
      hoverAnimations: false
    });
    window.placement = createApp({
      ...App,
      created() {
        this.session = { ticket: 'fixture-ticket', login: 'admin' };
        this.project = this.workspaceProject = 'one';
        this.projects = [{ code: 'one', title: 'One' }];
        this.canAdminister = true;
        this.ready = true;
        this.restoringSession = false;
      }
    })
      .directive('window', windowDirective)
      .mount('#app');
    const { sections } = await import(
      '/src/tactic_stream/shared_ui/features/administration/administration.ui.mjs'
    );
    if (sections.some((section) => section.id === 'server'))
      throw Error('Backend server remains in Administration');
    window.placement.showAdministration('showcase');
  }, vueUrl);
  await page
    .locator('dialog.administration-dialog')
    .waitFor({ state: 'visible' });
  assert.equal(
    await page.getByText('Backend server', { exact: true }).count(),
    0
  );
  await page.evaluate(() => window.placement.leaveAdministration());
  await page.evaluate(() => window.placement.showConfiguration());
  await page
    .locator('dialog[data-window-kind="configuration"]')
    .waitFor({ state: 'visible' });
  if (process.env.SERVER_PLACEMENT_CAPTURE) {
    const output = process.env.SERVER_PLACEMENT_CAPTURE;
    await mkdir(output, { recursive: true });
    const surface = page.locator('[data-frame=serverControlSurface]');
    await surface.waitFor();
    const box = await surface.boundingBox();
    const controls = [];
    for (const id of [
      'serverWorkerCount',
      'serverRunningWorkers',
      'serverWorkersSave',
      'serverRestart',
      'serverControlRefresh'
    ]) {
      const bounds = await page
        .locator('[data-frame="' + id + '"]')
        .boundingBox();
      controls.push({
        id,
        x: bounds.x - box.x,
        y: bounds.y - box.y,
        width: bounds.width,
        height: bounds.height
      });
    }
    await surface.screenshot({ path: output + '/browser.png' });
    await writeFile(
      output + '/browser.json',
      JSON.stringify({ width: box.width, height: box.height, controls })
    );
  }
  const count = page.locator('[data-frame=serverWorkerCount]');
  await count.fill('3');
  assert.ok(await page.locator('[data-frame=serverRestart]').isDisabled());
  await page.locator('[data-frame=serverWorkersSave]').click();
  await page.waitForFunction(
    () => !document.querySelector('[data-frame=serverRestart]')?.disabled
  );
  assert.equal(requests, 0);
  await page.locator('[data-frame=serverRestart]').click();
  await page.locator('[data-frame=serverRestartCancel]').click();
  assert.equal(requests, 0);
  await page.locator('[data-frame=serverRestart]').click();
  await page.locator('[data-frame=serverRestartAccept]').click();
  await page.waitForFunction(() =>
    document
      .querySelector('[data-frame=serverControlNotice]')
      ?.textContent.includes('TACTIC Stream restarted')
  );
  assert.equal(requests, 1, 'Never resubmit a restart during reconnect');
  assert.ok(
    (
      await page.locator('[data-frame=serverRunningWorkers]').innerText()
    ).includes('3')
  );
  await page.setViewportSize({ width: 344, height: 900 });
  await page.waitForFunction(
    () =>
      document
        .querySelector('[data-frame=serverRestart]')
        ?.getBoundingClientRect().right <= innerWidth
  );
  const bounds = await page.locator('[data-frame=serverRestart]').boundingBox();
  assert.ok(
    bounds.x >= 0 && bounds.x + bounds.width <= 344,
    JSON.stringify(bounds)
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS server control: save, explicit confirmation/cancel, one restart, lost status response, running count and narrow bounds'
  );
} finally {
  await browser?.close();
  await server.close();
}
