import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = fileURLToPath(
  new URL('../../.screenshots/mobile-table/', import.meta.url)
);
const rows = Array.from({ length: 5 }, (_, i) => ({
  __search_key__: 'demo/asset?code=A' + i,
  name: 'Robot arm ' + i,
  description: 'Mechanical arm for the main character',
  owner: 'Artist ' + i,
  status: 'In progress',
  category: 'Characters',
  code: 'A' + i
}));
const definition = {
  search_type: 'demo/asset',
  operations: {},
  columns: {},
  table: {
    configured: true,
    view: 'table',
    layout: 'TableLayoutWdg',
    attributes: {},
    elements: [
      'name',
      'description',
      'owner',
      'status',
      'category',
      'code'
    ].map((name) => ({
      name,
      title: name,
      attributes: { width: '160' },
      cell: { kind: 'text', field: name, supported: true }
    }))
  }
};
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,reactive,h} from 'vue';import '/src/App.vue';
import ConfiguredView from '/src/features/interface/ConfiguredView.vue';
import {initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';initializeAppearance();
const state=reactive({mode:'continious',selected:[],result:{table:{autoFit:true,scrollColumns:false}}});window.fixture=state;
createApp({setup(){return()=>h('main',{class:'workspace-results table-container',style:'height:100dvh;margin:0'},[
 h(ConfiguredView,{definition:${JSON.stringify(definition)},rows:${JSON.stringify(rows)},workspaceId:'phone',project:'demo',ticket:'fixture',readOnly:false,
 resultMode:'compact',mobileResultMode:state.mode,resultState:state.result,selectedKeys:state.selected,
 'onResult-state':value=>state.result=value,onSelect:(rows,selected)=>state.selected=selected?rows.map(r=>r.__search_key__):[]})])}}).mount('#app');
</script></body></html>`;
let server, browser;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'mobile-table-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/mobile-table-test') return next();
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
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 360, height: 740 },
    hasTouch: true,
    isMobile: true
  });
  page.setDefaultTimeout(8000);
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.route('**/admin/result-items', (route) =>
    route.fulfill({
      json: {
        result: {
          items: rows.map((record) => ({
            record,
            title: record.name,
            subtitle: record.description,
            preview: {},
            branches: [],
            info_items: [],
            progress_items: []
          })),
          organization: { processes: [], statuses: {} },
          has_next: false
        }
      }
    })
  );
  const cdp = await page.context().newCDPSession(page);
  for (const language of ['en', 'ru']) {
    await page.addInitScript(
      (language) =>
        localStorage.setItem(
          'tactic_stream.appearance',
          JSON.stringify({ mode: 'dark', language })
        ),
      language
    );
    await page.goto(server.resolvedUrls.local[0] + 'mobile-table-test');
    await page.locator('.mobile-result-list article').first().waitFor();
    await page.evaluate(() => (window.fixture.mode = 'table'));
    const table = page.locator('.handler-table');
    await table.waitFor();
    for (const width of [320, 360, 390, 600, 700]) {
      await page.setViewportSize({ width, height: 740 });
      await page.waitForFunction(() => {
        const t = document.querySelector('.handler-table');
        return (
          t &&
          t.scrollWidth > t.clientWidth + 100 &&
          t.getBoundingClientRect().right <= innerWidth
        );
      });
      assert.equal(
        await table.locator('.handler-table-heading').count(),
        6,
        'All configured columns survive at phone width'
      );
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth
        ),
        'Page stays inside viewport'
      );
      assert.equal(
        await table.evaluate((t) => getComputedStyle(t).overflowX),
        'auto'
      );
      assert(
        !(await table.getAttribute('class')).includes('no-horizontal-overflow'),
        'Horizontal scrollbar remains available'
      );
      await table.evaluate((t) => (t.scrollLeft = 0));
      const box = await table.boundingBox(),
        y = box.y + 95;
      await cdp.send('Input.dispatchTouchEvent', {
        type: 'touchStart',
        touchPoints: [{ x: width - 45, y }]
      });
      for (let step = 1; step <= 8; step++)
        await cdp.send('Input.dispatchTouchEvent', {
          type: 'touchMove',
          touchPoints: [{ x: width - 45 - step * 25, y }]
        });
      await cdp.send('Input.dispatchTouchEvent', {
        type: 'touchEnd',
        touchPoints: []
      });
      await page.waitForFunction(
        () => document.querySelector('.handler-table').scrollLeft > 30
      );
      assert.equal(await page.evaluate(() => window.scrollX), 0);
      await table.evaluate((t) => (t.scrollLeft = t.scrollWidth));
      await page.screenshot({ path: output + language + '-' + width + '.png' });
      assert(await table.locator('.handler-table-heading').last().isVisible());
    }
    await table.evaluate((t) => (t.scrollLeft = 0));
    await table.locator('.handler-table-row .app-checkbox').first().tap();
    assert.equal(await page.evaluate(() => window.fixture.selected.length), 1);
    await page.evaluate(() => (window.fixture.mode = 'continious'));
    await page
      .locator('.mobile-result-list article')
      .first()
      .waitFor({ state: 'visible' });
    assert.equal(
      await page.evaluate(() => window.fixture.selected.length),
      1,
      'Switching view preserves selection'
    );
    assert(
      await page.evaluate(() => window.fixture.result.table.autoFit),
      'Phone does not overwrite desktop fitting'
    );
    assert.equal(
      await page.evaluate(() => window.fixture.result.table.scrollColumns),
      false
    );
    await page.setViewportSize({ width: 1300, height: 850 });
    await page
      .locator('.result-item-tree.result-item-compact')
      .first()
      .waitFor();
    assert.equal(await table.count(), 0, 'Desktop compact mode is retained');
    await page.setViewportSize({ width: 360, height: 740 });
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS mobile cards/table, 320–700px EN/RU, all columns, internal touch scroll, selection and desktop preferences'
  );
} finally {
  await browser?.close();
  await server?.close();
}
