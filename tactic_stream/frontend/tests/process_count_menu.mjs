import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = fileURLToPath(
  new URL('../../.screenshots/process-count-menu/', import.meta.url)
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
  note_counts: { model: 1 },
  comments: 1,
  tasks: [
    { process: 'model', taskSearchKey: 'sthpw/task?project=demo&code=T1' }
  ],
  branches: [
    {
      kind: 'process',
      process: 'publish',
      title: 'Publish',
      accent: '#78909c'
    },
    { kind: 'process', process: 'model', title: 'Model', accent: '#ef5350' },
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
import {createApp,reactive,h,provide} from 'vue';
import '/src/App.vue';
import ResultPresentation from '/src/features/workspace/ResultPresentation.vue';
import {initializeAppearance} from '/src/appearance.js';
import {mobile} from '/src/mobile.js';mobile.value=false;
import '/src/theme.css';import '/src/style.css';
initializeAppearance();
const state=reactive({active:true,layout:null,rows:[${JSON.stringify(item.record)}],saved:{}});
window.fixture=state;
window.calls=[];createApp({setup(){provide('openTaskManager',(...args)=>window.calls.push(args));return()=>h('main',{class:'table-container',style:'width:100%;height:550px;overflow:auto'},[
  h(ResultPresentation,{ref:value=>window.presentation=value,rows:state.rows,selectedKeys:[],state:state.saved,
    active:state.active,itemLayout:state.layout,ticket:'fixture',project:'demo',searchType:'demo/episode',
    mode:'continious',groupMode:'none'})])}}).mount('#app');
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
        name: 'process-count-fixture',
        configureServer(owner) {
          owner.middlewares.use(async (req, res, next) => {
            if (req.url !== '/process-count-test') return next();
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
    viewport: { width: 800, height: 600 },
    hasTouch: true
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/result-items', (route) =>
    route.fulfill({
      json: {
        result: {
          items: [item],
          organization: { processes: [], statuses: {} },
          has_next: false
        }
      }
    })
  );
  for (const language of ['en', 'ru'])
    for (const width of [800, 320]) {
      await page.setViewportSize({ width, height: 600 });
      await page.addInitScript(
        (language) =>
          localStorage.setItem(
            'tactic_stream.appearance',
            JSON.stringify({ mode: 'dark', language })
          ),
        language
      );
      await page.goto(server.resolvedUrls.local[0] + 'process-count-test');
      await page.locator('article[data-result-key]').waitFor();
      // Use the existing item task action, not a test-only popup opener.
      const task = page.locator('.result-communication button').first();
      await task.click();
      const panel = page.locator('.result-process-menu > .account-panel');
      await panel.waitFor({ state: 'visible' });
      await page.evaluate(() => document.fonts.ready);
      const geometry = await panel.evaluate((el) => ({
        width: el.getBoundingClientRect().width,
        x: el.getBoundingClientRect().x,
        radius: getComputedStyle(el).borderRadius,
        overflow: getComputedStyle(el).overflow,
        background: getComputedStyle(el).backgroundColor,
        rows: [...el.querySelectorAll('.app-menu-item')].map((row) => ({
          height: row.getBoundingClientRect().height,
          font: getComputedStyle(row.querySelector('button')).fontSize
        })),
        badges: [...el.querySelectorAll('.app-button-badge')].map((b) => ({
          text: b.textContent.trim(),
          height: b.getBoundingClientRect().height
        }))
      }));
      assert.equal(geometry.width, 212);
      assert.equal(geometry.radius, '8px');
      assert.equal(geometry.overflow, 'visible');
      assert.ok(geometry.x >= 4 && geometry.x + geometry.width <= width - 4);
      assert.ok(
        geometry.rows.every((row) => row.height === 32 && row.font === '11px'),
        JSON.stringify(geometry)
      );
      assert.deepEqual(
        geometry.badges.map((b) => b.text),
        ['0', '1']
      );
      assert.ok(geometry.badges.every((b) => b.height === 20));
      await page.screenshot({ path: output + `menu-${language}-${width}.png` });
      await panel.getByRole('menuitem', { name: 'Model', exact: true }).click();
      await panel.waitFor({ state: 'hidden' });
      assert.deepEqual(
        await page.evaluate(() =>
          window.calls.map((call) => [call[0].code, call[1], call[3]])
        ),
        [['E1', 'model', 'sthpw/task?project=demo&code=T1']]
      );
      // Notes keep their existing action and process/task context.
      await page.evaluate(() => {
        window.noteCalls = [];
        window.presentation.$refs.notes.open = (...args) =>
          window.noteCalls.push(args);
      });
      await page.locator('.result-communication button').last().click();
      await panel.getByRole('menuitem', { name: 'Model', exact: true }).click();
      assert.deepEqual(
        await page.evaluate(() =>
          window.noteCalls.map((call) => [call[0].code, call[2], call[4]])
        ),
        [['E1', 'model', 'sthpw/task?project=demo&code=T1']]
      );
      // Multiple tasks can still drill in, go back and select an exact task.
      await page.evaluate(() =>
        window.presentation.nodes[0].tasks.push({
          process: 'model',
          context: 'Review',
          taskSearchKey: 'sthpw/task?project=demo&code=T2'
        })
      );
      await task.click();
      await panel
        .getByRole('menuitem', {
          name: language === 'ru' ? 'Выбрать задачу' : 'Choose task',
          exact: true
        })
        .click();
      await panel
        .getByRole('menuitem', {
          name: language === 'ru' ? 'Все процессы' : 'All processes',
          exact: true
        })
        .click();
      await panel
        .getByRole('menuitem', {
          name: language === 'ru' ? 'Выбрать задачу' : 'Choose task',
          exact: true
        })
        .click();
      await panel
        .getByRole('menuitem', { name: 'Review', exact: true })
        .click();
      assert.equal(
        await page.evaluate(() => window.calls.at(-1)[3]),
        'sthpw/task?project=demo&code=T2'
      );
      await task.click();
      await page.keyboard.press('Escape');
      await panel.waitFor({ state: 'hidden' });
      assert.equal(
        await page.evaluate(
          () =>
            document.activeElement ===
            document.querySelector('.result-communication button')
        ),
        true
      );
    }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: native-style process picker, task-manager scope, exact task, notes, back, Escape, EN/RU, 320/800'
  );
} finally {
  await browser?.close();
  await server?.close();
}
