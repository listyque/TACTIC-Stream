import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = fileURLToPath(
  new URL('../../.screenshots/result-density/', import.meta.url)
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
import AppSplitter from '/src/controls/AppSplitter.vue';
import {initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
initializeAppearance();
const state=reactive({width:800,height:650,mode:'continious',active:true,rows:[${JSON.stringify(item.record)}],saved:{}});
window.fixture=state;
createApp({setup(){return()=>h('div',{style:{display:'flex',height:state.height+'px'}},[
 h('main',{class:'workspace-results table-container',style:{width:state.width+'px',flex:'0 0 '+state.width+'px',overflow:'auto'}},[
  h(ResultPresentation,{ref:value=>window.presentation=value,rows:state.rows,selectedKeys:[],state:state.saved,
    active:state.active,ticket:'fixture',project:'demo',searchType:'demo/episode',
    mode:state.mode,groupMode:'none'})]),
 h(AppSplitter,{modelValue:state.width,'onUpdate:modelValue':value=>state.width=value,min:280,max:900,label:'Resize items panel'}),
 h('aside',{style:'flex:1;background:var(--surface)'},'Details')])}}).mount('#app');
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
        name: 'result-density-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/result-density-test') return next();
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
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
      viewport: { width: 1400, height: 750 }
    }),
    errors = [],
    requests = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/result-items', (route) => {
    requests.push(route.request().postDataJSON().branch?.kind || 'root');
    return route.fulfill({
      json: {
        result: {
          items: [item],
          organization: { processes: [], statuses: {} },
          has_next: false
        }
      }
    });
  });
  for (const language of ['en', 'ru']) {
    await page.addInitScript(
      (language) =>
        localStorage.setItem(
          'tactic_stream.appearance',
          JSON.stringify({ mode: 'dark', language })
        ),
      language
    );
    await page.goto(server.resolvedUrls.local[0] + 'result-density-test');
    const owner = page.locator('article[data-result-key="' + key + '"]'),
      splitter = page.getByRole('separator', { name: 'Resize items panel' });
    await owner.waitFor();
    const geometry = () =>
      owner.evaluate((el) => ({
        height: el.getBoundingClientRect().height,
        preview: el
          .querySelector('.image-picker-preview')
          ?.getBoundingClientRect().width,
        compact: el.classList.contains('result-item-compact')
      }));
    assert.deepEqual(await geometry(), {
      height: 100,
      preview: 68,
      compact: false
    });
    await owner.locator('strong').first().click();
    await owner.locator('.result-expand').click();
    await page.locator('.result-item-branch').waitFor();
    await page.evaluate(() => {
      window.retained = window.presentation.nodes[0];
      window.retainedSelection = window.presentation.selectedId;
    });
    const count = requests.length;
    async function drag(width) {
      const box = await splitter.boundingBox();
      const current = await page.evaluate(() => window.fixture.width);
      await page.mouse.move(box.x + box.width / 2, box.y + 30);
      await page.mouse.down();
      await page.mouse.move(
        box.x + box.width / 2 + width - current,
        box.y + 30,
        { steps: 8 }
      );
      await page.mouse.up();
      await page.waitForFunction(
        (compact) => window.presentation.compact === compact,
        width < 445
      );
    }
    await drag(400);
    assert.deepEqual(await geometry(), {
      height: 64,
      preview: 42,
      compact: true
    });
    await page.screenshot({ path: output + `narrow-${language}.png` });
    await drag(800);
    assert.deepEqual(await geometry(), {
      height: 100,
      preview: 68,
      compact: false
    });
    await drag(320);
    assert.deepEqual(await geometry(), {
      height: 64,
      preview: 42,
      compact: true
    });
    await drag(445);
    assert.equal((await geometry()).compact, false);
    await splitter.focus();
    await splitter.press('ArrowLeft');
    await page.waitForFunction(() => window.presentation.compact);
    assert.equal((await geometry()).height, 64);
    assert.equal(requests.length, count, 'Resize must not reload the tree');
    assert.equal(
      await page.evaluate(
        () =>
          window.presentation.nodes[0] === window.retained &&
          window.retained.expanded &&
          window.presentation.selectedId === window.retainedSelection
      ),
      true
    );
    assert.equal(await page.locator('.result-item-branch').count(), 1);
    // The same density governs tile and split presentations, without changing saved mode.
    await page.evaluate(() => (window.fixture.mode = 'tiles'));
    assert.equal((await geometry()).height, 64);
    assert.equal(await page.locator('.result-item-card').count(), 0);
    assert.equal(
      await owner.evaluate((el) => el.classList.contains('result-item-tree')),
      true
    );
    await drag(800);
    await page.locator('.result-item-card').waitFor();
    await page.evaluate(() => (window.fixture.mode = 'splitted_vertical'));
    await page.locator('.result-split-right').waitFor();
    await drag(400);
    assert.equal(await page.locator('.result-split-right').count(), 0);
    assert.equal(await page.locator('.result-versions').count(), 0);
    assert.equal(
      await page.evaluate(() => window.fixture.mode),
      'splitted_vertical'
    );
    await page.evaluate(() => {
      window.fixture.mode = 'continious';
      window.fixture.width = 800;
      window.fixture.height = 200;
    });
    const viewport = page.locator('main.workspace-results');
    await page.waitForFunction(() => !window.presentation.compact);
    const insets = () =>
      viewport.evaluate((el) => {
        const box = el.getBoundingClientRect(),
          card = el.querySelector('.result-surface').getBoundingClientRect();
        return {
          left: card.left - box.left,
          right: box.right - card.right,
          bar: el.offsetWidth - el.clientWidth,
          overflow: el.scrollHeight > el.clientHeight
        };
      });
    const clear = await insets();
    assert.equal(clear.overflow, false);
    assert.equal(clear.bar, 0, 'No empty scrollbar reserve for a short list');
    assert.equal(clear.left, clear.right, 'Equal item insets without overflow');
    assert.equal(
      clear.left,
      10,
      'Native delegate gutter plus full-card elevation inset'
    );
    await page.evaluate(() => (window.fixture.height = 100));
    await page.waitForFunction(() => {
      const el = document.querySelector('main.workspace-results');
      return el.scrollHeight > el.clientHeight;
    });
    await page.waitForFunction(() => {
      const el = document.querySelector('main.workspace-results'),
        box = el.getBoundingClientRect(),
        card = el.querySelector('.result-surface').getBoundingClientRect();
      return (
        Math.abs(
          box.right -
            card.right -
            (card.left - box.left) -
            (el.offsetWidth - el.clientWidth)
        ) < 0.5
      );
    });
    const scrolling = await insets();
    assert.equal(scrolling.left, clear.left);
    assert.equal(scrolling.bar, 12);
    assert.equal(
      scrolling.right,
      clear.right + scrolling.bar,
      'Only the actual scrollbar adds right reserve'
    );
    await page.evaluate(() => (window.fixture.height = 200));
    await page.waitForFunction(() => {
      const el = document.querySelector('main.workspace-results');
      return el.scrollHeight <= el.clientHeight;
    });
    await page.waitForFunction(() => {
      const el = document.querySelector('main.workspace-results'),
        box = el.getBoundingClientRect(),
        card = el.querySelector('.result-surface').getBoundingClientRect();
      return Math.abs(box.right - card.right - (card.left - box.left)) < 0.5;
    });
    assert.deepEqual(
      await insets(),
      clear,
      'Gutter disappears when the viewport fits again'
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: native 445 DIP density, actual splitter drag/key, 320/400/445/800, EN/RU, stable nodes/selection/expansion and no resize requests'
  );
} finally {
  await browser?.close();
  await server?.close();
}
