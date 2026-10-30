import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const output =
  process.env.TABLE_SCROLLING_OUTPUT ||
  root + '/../tools/frame_table/output/scrolling';
const html = `<!doctype html><html><head><link rel="icon" href="data:,"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import TableView from '/src/features/interface/TableView.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import {windowDirective} from '/src/controls/window.js';
import '/src/theme.css';import '/src/style.css';import '/src/controls/panelChrome.css';
Object.assign(appearance,{language:'en',theme:'md3',mode:'dark',popupAnimations:false});initializeAppearance();window.appearance=appearance;
createApp({data(){return {state:{},readOnly:false,columns:[{name:'code',title:'Code',width:160,hideOrder:0},{name:'notes',title:'Notes',width:160,hideOrder:2},{name:'category',title:'Category',width:160,hideOrder:1}]}},mounted(){window.host=this},render(){return h(TableView,{columns:this.columns,groups:[{key:'all',records:[{__search_key__:'asset',code:'A',notes:'Asset notes',category:'Character'}]}],closedGroups:{},selectedKeys:[],readOnly:this.readOnly,editable:!this.readOnly,state:this.state,onState:state=>this.state=state},{cell:({record,column})=>record[column.name]})}}).directive('window',windowDirective).mount('#app');
</script><style>html,body,#app{height:100%;width:100%;overflow:hidden}#app{display:flex;background:var(--page)}</style></body></html>`;
let browser, server;
const errors = [];
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/table-scrolling',
    plugins: [
      vue(),
      {
        name: 'table-scrolling-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/scrolling-fixture') return next();
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
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || undefined
  });
  for (const touch of [false, true]) {
    const page = await browser.newPage({
      viewport: { width: 430, height: 380 },
      hasTouch: touch
    });
    page.on('pageerror', (error) => errors.push(error.stack));
    page.on('console', (message) => {
      if (['warning', 'error'].includes(message.type()))
        errors.push(message.text());
    });
    await page.goto(server.resolvedUrls.local[0] + 'scrolling-fixture');
    const table = page.locator('.handler-table');
    const headings = table.locator('.handler-table-heading');
    await page.waitForFunction(
      () => document.querySelectorAll('.handler-table-heading').length === 2
    );
    assert.equal(await headings.count(), 2);
    async function toggle(keyboard = false, russian = false) {
      const button = table.getByLabel(
        russian ? 'Варианты таблицы и колонки' : 'Table views and columns',
        { exact: true }
      );
      if (touch) await button.tap();
      else await button.click();
      const action = page.getByRole('menuitemcheckbox', {
        name: russian ? 'Горизонтальная прокрутка' : 'Horizontal scrolling',
        exact: true
      });
      if (keyboard) {
        await action.focus();
        await action.press('Enter');
      } else if (touch) await action.tap();
      else await action.click();
    }
    await toggle();
    await page.waitForFunction(() => window.host.state.table.scrollColumns);
    assert.equal(await headings.count(), 3);
    assert.equal(await table.evaluate((el) => el.scrollWidth), 584);
    await table.hover();
    await page.mouse.wheel(180, 0);
    await page.waitForFunction(
      () => document.querySelector('.handler-table').scrollLeft > 0
    );
    assert(
      await table.evaluate((el) => {
        const header = el
          .querySelector('.handler-table-heading')
          .getBoundingClientRect();
        const cell = el
          .querySelector('.handler-table-cell')
          .getBoundingClientRect();
        return Math.abs(header.x - cell.x) < 1;
      })
    );
    for (const width of [900, 360, 430]) {
      await page.setViewportSize({ width, height: 380 });
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      await page.waitForFunction(
        (width) =>
          document.querySelector('.handler-table').clientWidth === width,
        width
      );
      await page.waitForFunction(
        (width) =>
          document.querySelector('.handler-table').scrollWidth ===
          Math.max(width, 584),
        width
      );
      assert.equal(await headings.count(), 3);
      assert.equal(
        await table.evaluate((el) => el.scrollWidth),
        Math.max(width, 584)
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth),
        width
      );
    }
    await table.evaluate((el) => (el.scrollLeft = 0));
    assert(
      await table.evaluate((el) => el.offsetHeight - el.clientHeight > 0),
      'Horizontal scrollbar reserves its gutter'
    );
    await page.screenshot({
      path: output + (touch ? '/touch.png' : '/browser.png')
    });
    await toggle(true);
    await page.waitForFunction(() => !window.host.state.table.scrollColumns);
    assert.equal(await headings.count(), 2);
    await page.evaluate(() => {
      window.host.readOnly = true;
      window.appearance.language = 'ru';
    });
    await toggle(false, true);
    await page.waitForFunction(() => window.host.state.table.scrollColumns);
    assert.equal(await headings.count(), 3);
    await table.getByLabel('Подогнать ширину колонок', { exact: true }).click();
    await page.waitForFunction(
      () =>
        !window.host.state.table.scrollColumns &&
        window.host.state.table.autoFit
    );
    assert.equal(await headings.count(), 2);
    await page.close();
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: optional table scrolling via mouse, keyboard and touch; EN/RU, read-only, resize and header alignment'
  );
} finally {
  await browser?.close();
  await server?.close();
}
