import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import TableServiceCell from '/src/features/interface/TableServiceCell.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',theme:'md3',mode:'dark'});initializeAppearance();
createApp({data(){return {count:1,events:[]}},mounted(){window.host=this},render(){return h(TableServiceCell,{cell:{actions:Array.from({length:this.count},()=>({name:'gallery',label:'Gallery',icon:'image'}))},height:58,editable:true,onAction:name=>this.events.push(name)})}}).mount('#app');
</script><style>body{margin:0}#app{width:160px;height:58px}</style></body></html>`;
let server, browser;
const errors = [];
try {
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/table-action-alignment',
    plugins: [
      vue(),
      {
        name: 'table-action-alignment',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/alignment-fixture') return next();
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await server.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0 }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || undefined
  });
  const page = await browser.newPage();
  page.on('pageerror', (error) => errors.push(error.stack));
  await page.goto(server.resolvedUrls.local[0] + 'alignment-fixture');
  for (const width of [160, 64, 320]) {
    await page
      .locator('#app')
      .evaluate((el, width) => (el.style.width = width + 'px'), width);
    for (const count of [1, 2, 5]) {
      await page.evaluate((count) => (window.host.count = count), count);
      await page.waitForFunction(
        ({ width, count }) => {
          const host = document
            .querySelector('.table-service-cell')
            .getBoundingClientRect();
          const buttons = [
            ...document.querySelectorAll('[data-frame^="tableServiceAction_"]')
          ];
          if (buttons.length !== count || host.width !== width) return false;
          const rows = new Map();
          for (const button of buttons) {
            const r = button.getBoundingClientRect();
            if (!rows.has(r.top)) rows.set(r.top, []);
            rows.get(r.top).push(r);
          }
          return [...rows.values()].every(
            (row) =>
              Math.abs(
                (row[0].left + row.at(-1).right) / 2 - (host.left + width / 2)
              ) < 1
          );
        },
        { width, count }
      );
    }
  }
  await page.evaluate(() => (window.host.count = 1));
  const action = page.locator('[data-frame="tableServiceAction_0"]');
  await action.click();
  await action.focus();
  await action.press('Enter');
  assert.deepEqual(await page.evaluate(() => window.host.events), [
    'gallery',
    'gallery'
  ]);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: action cells centered on resize and wrapping; mouse and keyboard still invoke actions'
  );
} finally {
  await browser?.close();
  await server?.close();
}
