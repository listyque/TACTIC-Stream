import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = `<!doctype html><link rel="icon" href="data:,"><div id="app"></div><script type="module">
import {createApp,h,reactive} from 'vue';
import Table from '/src/features/tasks/TaskWorkspaceTable.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en'});initializeAppearance();
const state=reactive({opened:false,busy:false,active:'',width:520});
window.taskSurface=state;
const task={key:'TASK1',title:'One task',parent:'project/asset?code=ONE',process:'model',description:'Model work'};
createApp({render:()=>h('main',{style:{width:state.width+'px'}},[
 h('button',{id:'toggle',onClick:()=>state.opened=!state.opened},'Toggle table'),
 h('section',{style:{display:state.opened?'block':'none',overflow:'auto'}},[
  h(Table,{groups:[{key:'',tasks:[task]}],columns:[{key:'object',visible:true,width:210},{key:'description',visible:true,width:240}],selected:[],collapsed:[],expanded:[],editors:{},active:state.active,busy:state.busy,blocked:state.busy,onActivate:key=>state.active=key})
 ])
])}).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'task-surface-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url !== '/task-surface') return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await server.transformIndexHtml(request.url, html));
          } catch (error) {
            next(error);
          }
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 700 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (['warning', 'error'].includes(message.type()))
      errors.push(message.text());
  });
  await page.goto(server.resolvedUrls.local[0] + 'task-surface');
  const table = page.locator('.task-workspace-table');
  await table.waitFor({ state: 'attached' });
  await table.evaluate((element) => (window.initialTaskTable = element));
  for (const width of [520, 1280]) {
    await page.evaluate((value) => (window.taskSurface.width = value), width);
    await page.locator('#toggle').click();
    await table.waitFor({ state: 'visible' });
    await page.waitForFunction(() => {
      const table = document.querySelector('.task-workspace-table');
      return table.getBoundingClientRect().width >= window.taskSurface.width;
    });
    await table.locator('tbody tr[data-task-key]').click();
    assert.equal(await page.evaluate(() => window.taskSurface.active), 'TASK1');
    await page.evaluate(() => (window.taskSurface.busy = true));
    await page.evaluate(() => (window.taskSurface.busy = false));
    assert(await table.isVisible());
    assert(
      await table.evaluate((element) => element === window.initialTaskTable)
    );
    await page.locator('#toggle').click();
    await table.waitFor({ state: 'hidden' });
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS task table hidden mount, reveal, input, resize and re-open'
  );
} finally {
  await browser?.close();
  await server.close();
}
