import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = fileURLToPath(
  new URL('../../.screenshots/result-disclosure/', import.meta.url)
);
const key = 'demo/episode?project=demo&code=E1';
const item = {
  record: { __search_key__: key, code: 'E1', name: 'Episode 01 — Arrival' },
  title: 'Episode 01 — Arrival',
  subtitle: 'Sample episode',
  accent: '#728acc',
  preview: {},
  info_items: [],
  progress_items: [],
  branches: [
    {
      kind: 'relation',
      key: 'relation:demo/shot:',
      search_type: 'demo/shot',
      path: '',
      title: 'Shot',
      count: 1
    }
  ]
};
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,reactive,h} from 'vue';
import '/src/App.vue';
import ResultPresentation from '/src/features/workspace/ResultPresentation.vue';
import {initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
initializeAppearance();
const state=reactive({active:true,layout:null,rows:[${JSON.stringify(item.record)}],saved:{}});
window.fixture=state;
createApp({setup(){return()=>h('main',{class:'table-container',style:'width:900px;height:650px;overflow:auto'},[
  h(ResultPresentation,{ref:value=>window.presentation=value,rows:state.rows,selectedKeys:[],state:state.saved,
    active:state.active,itemLayout:state.layout,ticket:'fixture',project:'demo',searchType:'demo/episode',
    mode:'continious',groupMode:'none'})])}}).mount('#app');
</script></body></html>`;
let server, browser, release;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'result-disclosure-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/result-disclosure-test') return next();
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await owner.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0, watch: null },
    logLevel: 'error'
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
      viewport: { width: 1000, height: 750 }
    }),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const requests = [],
    metrics = {};
  let hold = '',
    fail = false,
    arrived;
  function pause(kind) {
    hold = kind;
    return new Promise((resolve) => {
      arrived = resolve;
    });
  }
  function resume() {
    hold = '';
    release();
    release = null;
  }
  await page.route('**/admin/result-items', async (route) => {
    const body = route.request().postDataJSON(),
      kind = body.branch?.kind || 'root';
    requests.push(kind);
    if (kind === hold)
      await new Promise((resolve) => {
        release = resolve;
        arrived();
      });
    if (fail && kind === 'relation') {
      fail = false;
      await route.fulfill({
        status: 500,
        json: { error: 'Fixture branch unavailable' }
      });
      return;
    }
    const result =
      kind === 'relation'
        ? {
            items: [
              {
                ...item,
                record: {
                  ...item.record,
                  __search_key__: 'demo/shot?project=demo&code=S1',
                  name: 'Shot 01'
                },
                title: 'Shot 01',
                branches: []
              }
            ],
            has_next: false
          }
        : {
            items: [item],
            organization: { processes: [], statuses: {} },
            has_next: false
          };
    await route.fulfill({ json: { result } });
  });
  page.setDefaultTimeout(10000);
  await page.goto(server.resolvedUrls.local[0] + 'result-disclosure-test');
  const surface = page.locator('.result-presentation'),
    owner = page.locator('article[data-result-key="' + key + '"]');
  const arrow = owner.locator('.result-expand');
  await arrow.waitFor();
  const origin = await owner.boundingBox();
  let heldRequest = pause('children');
  await arrow.click();
  await heldRequest;
  await arrow.locator('.busy-indicator.running').waitFor();
  assert.equal(
    await arrow.locator('.app-icon').count(),
    0,
    'Arrow becomes the spinner'
  );
  assert.equal(await arrow.getAttribute('aria-busy'), 'true');
  assert.equal(
    (await arrow.locator('.busy-indicator').boundingBox()).width,
    24,
    'Same full-card indicator size as Handler'
  );
  assert(
    !(await surface.innerText()).includes('Loading data'),
    'No loading text in the tree'
  );
  assert.equal(
    (await owner.boundingBox()).y,
    origin.y,
    'Loading does not insert a row above the owner'
  );
  await owner.screenshot({ path: output + '/stream-owner-loading.png' });
  await arrow.screenshot({ path: output + '/stream-owner-arrow.png' });
  metrics.owner = {
    button: await arrow.boundingBox(),
    spinner: await arrow.locator('.busy-indicator').boundingBox()
  };
  resume();
  const branch = surface.locator('.result-item-branch'),
    branchArrow = branch.locator('.result-expand');
  await branchArrow.waitFor();
  heldRequest = pause('relation');
  await branchArrow.click();
  await heldRequest;
  await branchArrow.locator('.busy-indicator.running').waitFor();
  assert.equal(
    (await branchArrow.locator('.busy-indicator').boundingBox()).width,
    18,
    'Same branch indicator size as Handler'
  );
  assert.equal(
    await arrow.locator('.busy-indicator').count(),
    0,
    'Only the clicked branch spins'
  );
  assert(!(await surface.innerText()).includes('Loading data'));
  await surface.screenshot({ path: output + '/stream-branch-loading.png' });
  await branchArrow.screenshot({ path: output + '/stream-branch-arrow.png' });
  metrics.branch = {
    button: await branchArrow.boundingBox(),
    spinner: await branchArrow.locator('.busy-indicator').boundingBox()
  };
  await writeFile(
    output + '/browser-metrics.json',
    JSON.stringify(metrics, null, 2)
  );
  resume();
  await page.waitForFunction(
    () => window.presentation.nodes[0].children[0].loaded
  );
  const before = requests.length;
  await branchArrow.click();
  await branchArrow.click();
  assert.equal(requests.length, before, 'Cached branch reopens without HTTP');
  await page.evaluate(() => {
    window.fixture.active = false;
  });
  await page.evaluate(() => {
    window.fixture.active = true;
  });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    requests.length,
    before,
    'Returning to a retained search tab does not reload the tree'
  );
  assert.equal(await surface.locator('.busy-indicator').count(), 0);

  const renderTimes = await page.evaluate(async () => {
    const branch = window.presentation.nodes[0].children[0];
    const original = branch.children;
    const frame = () =>
      new Promise((resolve) => requestAnimationFrame(resolve));
    const results = [];
    for (const count of [1, 500, 5000]) {
      branch.expanded = false;
      branch.children = Array.from({ length: count }, (_, index) => ({
        ...original[0],
        id: branch.id + '/probe/' + index,
        title: 'Render probe ' + index,
        record: {
          ...original[0].record,
          __search_key__: 'demo/shot?project=demo&code=PROBE_' + index
        }
      }));
      await frame();
      await frame();
      const control = document.querySelector(
        '[data-node-id="' + branch.id + '"] .result-expand'
      );
      const start = performance.now();
      control.click();
      await frame();
      const child = document.querySelector(
        '[data-result-key="demo/shot?project=demo&code=PROBE_0"]'
      );
      results.push({
        count,
        milliseconds: performance.now() - start,
        firstFrame: !!child && child.getBoundingClientRect().height > 0
      });
    }
    branch.children = original;
    branch.expanded = true;
    await frame();
    await frame();
    return results;
  });
  assert(
    renderTimes.every((result) => result.firstFrame),
    'Cached descendants must render in the next frame, without a timer or request'
  );
  assert.equal(
    requests.length,
    before,
    'Render probes use only records already in memory'
  );
  await writeFile(
    output + '/render-times.json',
    JSON.stringify(renderTimes, null, 2)
  );
  console.log('Cached click-to-frame:', JSON.stringify(renderTimes));

  // Refresh still fetches new data. Root loading ends before restored descendants finish.
  heldRequest = pause('children');
  await page.evaluate(() => {
    window.fixture.rows = window.fixture.rows.map((row) => ({ ...row }));
  });
  await heldRequest;
  await page.waitForFunction(() => window.presentation.nodes[0]?.busy);
  assert.equal(await surface.getAttribute('aria-busy'), 'false');
  assert(!(await surface.innerText()).includes('Loading data'));
  resume();
  await page.waitForFunction(
    () =>
      window.presentation.nodes[0]?.loaded && !window.presentation.nodes[0].busy
  );

  // XML-configured cards use the same control, error handling and first-click behavior.
  await page.evaluate(() => {
    window.fixture.layout = { flow: 'grid', columns: 12, elements: [] };
  });
  await branchArrow.waitFor();
  fail = true;
  heldRequest = pause('relation');
  await branchArrow.click();
  await heldRequest;
  await branchArrow.locator('.busy-indicator.running').waitFor();
  resume();
  await surface.getByRole('alert').waitFor();
  assert.equal(
    await branchArrow.locator('.busy-indicator').count(),
    0,
    'Failure stops the spinner'
  );
  heldRequest = pause('relation');
  await surface.getByRole('button', { name: 'Retry', exact: true }).click();
  await heldRequest;
  await page.waitForFunction(
    () => window.presentation.nodes[0].children[0].busy
  );
  resume();
  await page.waitForFunction(
    () => window.presentation.nodes[0].children[0].loaded
  );
  await branchArrow.click(); // collapse the loaded branch
  await arrow.click(); // collapse owner
  await arrow.click(); // cached owner, no loading flash
  assert.equal(await arrow.locator('.busy-indicator').count(), 0);

  await arrow.press('Space');
  assert.equal(await arrow.getAttribute('aria-expanded'), 'false');
  await page.waitForFunction(
    () =>
      getComputedStyle(document.querySelector('.result-expand .app-icon'))
        .transform === 'matrix(1, 0, 0, 1, 0, 0)'
  );
  await arrow.press('Enter');
  assert.equal(await arrow.getAttribute('aria-expanded'), 'true');
  await page.waitForFunction(
    () =>
      getComputedStyle(document.querySelector('.result-expand .app-icon'))
        .transform === 'matrix(0, 1, -1, 0, 0, 0)'
  );

  // A late reply cannot populate a different search generation.
  heldRequest = pause('children');
  await page.evaluate(() => {
    window.fixture.rows = window.fixture.rows.map((row) => ({ ...row }));
  });
  await heldRequest;
  await page.waitForFunction(() => window.presentation.nodes[0]?.busy);
  await page.evaluate(() => {
    window.fixture.rows = [];
  });
  const lateReply = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/result-items') &&
      response.request().postDataJSON().branch?.kind === 'children'
  );
  resume();
  await lateReply;
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  await page.waitForFunction(
    () => window.presentation.nodes.length === 0 && !window.presentation.busy
  );
  assert.equal(await surface.locator('article').count(), 0);
  assert.deepEqual(errors, []);
  console.log(
    'PASS production result disclosure: local spinners, stable rows, cached expansion/tab return, fresh refresh, configured cards, failure/retry and stale replies'
  );
} finally {
  release?.();
  await browser?.close();
  await server?.close();
}
