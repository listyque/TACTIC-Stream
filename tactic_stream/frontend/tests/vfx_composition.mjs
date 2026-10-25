import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const auth = {
  ticket: process.env.VFX_TICKET,
  project: process.env.VFX_PROJECT,
  language: 'python'
};
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,reactive,nextTick} from 'vue';
import CustomLayoutView from '/src/features/interface/CustomLayoutView.vue';
import TableDocument from '/src/features/interface/TableDocument.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
window.fixture=reactive({model:null,document:{},closed:0,saved:0,events:[],width:1000,height:600});
window.mountLayout=(model)=>{window.fixture.model=model;};
window.vueNextTick=nextTick;
createApp({render(){const s=window.fixture;return [s.model ? h(CustomLayoutView,{key:s.model.layoutView,ref:view=>window.layout=view,
model:s.model,ticket:window.auth.ticket,project:window.auth.project,width:s.width,height:s.height,
onClose:()=>s.closed++,onSaved:()=>s.saved++,onAction:(...args)=>s.events.push(args)}) : null,
h(TableDocument,{ref:view=>window.documentHost=view,model:s.document,ticket:window.auth.ticket,project:window.auth.project})];}}).mount('#app');
</script><style>body{margin:0;background:var(--background)}#app{position:relative;width:1000px;height:600px}</style></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'vfx-layout-fixture',
      configureServer(server) {
        server.middlewares.use('/vfx-layout', async (_req, res) => {
          res.setHeader('Content-Type', 'text/html');
          res.end(await server.transformIndexHtml('/vfx-layout', html));
        });
      }
    }
  ],
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: null,
    proxy: {
      '/admin': {
        target: process.env.VFX_URL,
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (request) =>
            request.setHeader('origin', process.env.VFX_URL)
          );
        }
      }
    }
  },
  logLevel: 'error'
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 760 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript((value) => (window.auth = value), auth);
  await page.goto(server.resolvedUrls.local[0] + 'vfx-layout');
  await page.waitForFunction(() => window.mountLayout);
  const call = async (method, ...args) =>
    page.evaluate(
      async ({ method, args }) => {
        const response = await fetch('/admin/rpc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ method, args: [window.auth, ...args] })
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        return data.result;
      },
      { method, args }
    );
  const layout = async (view, key = process.env.VFX_SHOT) => {
    const result = await call(
      'execute_cmd',
      'tactic.ui.table.CustomLayoutReadCmd',
      { view, search_key: key }
    );
    await page.evaluate((model) => window.mountLayout(model), result.info);
    return result.info;
  };
  await layout('shot_planner_wdg');
  await page.waitForFunction(() =>
    Object.values(window.layout.tables).every(
      (table) => table.loaded && !table.busy
    )
  );
  assert.equal(await page.locator('.nested-table').count(), 2);
  assert.equal(
    await page.locator('[data-frame="nestedQuick_shot"]').count(),
    1
  );
  await page.locator('[data-frame="nestedSelect"]').first().click();
  const selected = await page.evaluate(() =>
    Object.values(window.layout.tables).map((table) => table.selected.length)
  );
  assert.deepEqual(selected, [1, 0]);
  const drag = await page
    .locator('[data-frame="nestedDrag"]')
    .first()
    .getAttribute('draggable');
  assert.equal(drag, 'true');
  await page
    .locator('[data-frame="nestedDrag"]')
    .first()
    .dragTo(page.locator('[data-frame="dropSurface"]').first());
  await page.waitForFunction(() =>
    window.fixture.events.some((event) => event[1] === 'drop-links')
  );
  const dropped = await page.evaluate(() =>
    window.fixture.events.find((event) => event[1] === 'drop-links')
  );
  assert.equal(dropped[0].__search_key__, process.env.VFX_SHOT);
  assert.equal(dropped[2].dropKeys.length, 1);
  await page.evaluate(() => (window.fixture.width = 400));
  const panels = await page.locator('.nested-table').evaluateAll((items) =>
    items.map((item) => ({
      x: item.getBoundingClientRect().x,
      y: item.getBoundingClientRect().y
    }))
  );
  assert.equal(panels[0].x, panels[1].x);
  assert.ok(panels[1].y > panels[0].y);
  if (process.env.VFX_CAPTURE_DIR)
    await page.locator('[data-frame="customLayoutScroll"]').screenshot({
      path: process.env.VFX_CAPTURE_DIR + '/planner-stream-narrow.png'
    });
  await page.evaluate(() => (window.fixture.width = 1000));
  if (process.env.VFX_CAPTURE_DIR) {
    await mkdir(process.env.VFX_CAPTURE_DIR, { recursive: true });
    await page.locator('#app').screenshot({
      path: process.env.VFX_CAPTURE_DIR + '/planner-stream.png'
    });
  }
  await layout('shot_sheet_wdg');
  await page.waitForFunction(() =>
    Object.values(window.layout.tables).every((table) => table.loaded)
  );
  assert.ok(await page.getByText('1001', { exact: true }).count());
  assert.equal(await page.locator('.nested-table').count(), 2);
  if (process.env.VFX_CAPTURE_DIR)
    await page
      .locator('#app')
      .screenshot({ path: process.env.VFX_CAPTURE_DIR + '/sheet-stream.png' });
  const report = await call(
    'execute_cmd',
    'tactic.ui.table.CustomLayoutReportCmd',
    { search_key: process.env.VFX_SHOT, view: 'shot_sheet_wdg' }
  );
  assert.equal(
    report.info.blocks.filter((block) => block.kind === 'table').length,
    2
  );
  await page.evaluate(() => {
    window.printCount = 0;
    window.printObserver = new MutationObserver(() => {
      for (const frame of document.querySelectorAll('iframe'))
        frame.contentWindow.print = () => window.printCount++;
    });
    window.printObserver.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
  await page.getByRole('button', { name: 'PRINT', exact: true }).click();
  await page.waitForFunction(() => window.printCount === 1);
  await layout('add_snapshot_to_review_wdg', process.env.VFX_SNAPSHOT);
  await page.waitForFunction(
    () => window.layout.state.root.snapshot && !window.layout.state.layoutBusy
  );
  assert.ok((await page.locator('#app').innerText()).includes('SH010'));
  assert.deepEqual(
    await page.evaluate(() =>
      window.layout.state.controls
        .find((control) => control.kind === 'choice')
        .options.map((option) => option.value)
    ),
    ['DAILY']
  );
  assert.deepEqual(
    await page
      .locator('[data-frame="customLayout_2"] option')
      .evaluateAll((options) => options.map((option) => option.value)),
    ['DAILY']
  );
  await page.locator('[data-frame="customLayout_2"]').selectOption('DAILY');
  if (process.env.VFX_CAPTURE_DIR)
    await page
      .locator('#app')
      .screenshot({ path: process.env.VFX_CAPTURE_DIR + '/review-stream.png' });
  await page.getByRole('button', { name: 'Submit', exact: true }).tap();
  await page.waitForFunction(() => window.fixture.closed === 1);
  assert.equal(await page.evaluate(() => window.fixture.saved), 1);
  const planner = (
    await call('execute_cmd', 'tactic.ui.table.CustomLayoutReadCmd', {
      view: 'single_shot_planner_wdg',
      search_key: process.env.VFX_SHOT
    })
  ).info;
  async function openTab(key, title) {
    await page.evaluate(
      async ({ model, key, title }) => {
        window.fixture.document = { ...model, tabKey: key, title };
        await window.vueNextTick();
        window.documentHost.open();
      },
      { model: planner, key, title }
    );
  }
  await openTab('one', 'First Planner');
  const first = page
    .locator('dialog[open] [data-frame="nestedSelect"]')
    .first();
  await first.click();
  assert.ok(await first.isChecked());
  await openTab('two', 'Second Planner');
  await page.locator('dialog[open] [data-frame="layoutTab_0"]').last().click();
  assert.ok(
    await page
      .locator('dialog[open] [data-frame="nestedSelect"]:visible')
      .first()
      .isChecked()
  );
  await page
    .locator('dialog[open] [data-frame="layoutCloseTab_1"]:visible')
    .click();
  assert.equal(
    await page
      .locator('dialog[open] [data-frame="layoutTab_1"]:visible')
      .count(),
    0
  );
  await page.evaluate(() => window.documentHost.close());
  assert.deepEqual(errors, []);
  console.log(
    'VFX browser: project Planner, scoped report, original Review load/select/submit passed.'
  );
} finally {
  await browser?.close();
  await server.close();
}
