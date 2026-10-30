import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import TableView from '/src/features/interface/TableView.vue';import TableCell from '/src/features/interface/TableCell.vue';
import NestedTableCell from '/src/features/interface/NestedTableCell.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';import {windowDirective} from '/src/controls/window.js';
import '/src/theme.css';import '/src/style.css';Object.assign(appearance,{language:'en',theme:'md3',mode:'dark'});initializeAppearance();
createApp({data(){return {nested:false,width:160,kind:'text',text:'robot, hero, character, rig, animation',state:{}}},mounted(){window.host=this},render(){const record={__search_key__:'asset',keywords:this.text};return h(TableView,{columns:[{name:'keywords',title:'Keywords',width:this.width,hideOrder:0}],groups:[{key:'all',records:[record]}],state:{table:{rowHeight:120}},closedGroups:{},selectedKeys:[],readOnly:true},{cell:({record,column})=>this.nested?h(NestedTableCell,{frameNode:{column:{...column,supported:true,field:'keywords',cell:{kind:this.kind}},record,cell:{text:this.text,href:'/docs'},height:120}}):h(TableCell,{element:{...column,supported:true,field:'keywords',cell:{kind:this.kind}},record,cell:{text:this.text,href:'/docs'},height:120})})}}).directive('window',windowDirective).mount('#app');
</script><style>html,body,#app{width:100%;height:100%;overflow:hidden}#app{display:flex}</style></body></html>`;
let server, browser;
const errors = [];
try {
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/table-text-wrap',
    plugins: [
      vue(),
      {
        name: 'table-text-wrap',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/wrap-fixture') return next();
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
  const page = await browser.newPage({ viewport: { width: 800, height: 360 } });
  page.on('pageerror', (error) => errors.push(error.stack));
  await page.goto(server.resolvedUrls.local[0] + 'wrap-fixture');
  const value = page.locator('.handler-table-cell .table-cell-text');
  await value.waitFor();
  for (const kind of ['text', 'link']) {
    for (const width of [160, 600, 120]) {
      await page.evaluate(
        ({ width, kind }) => {
          window.host.width = width;
          window.host.kind = kind;
        },
        { width, kind }
      );
      await page.waitForFunction(
        ({ width, kind }) => {
          const el = document.querySelector(
            '.handler-table-cell .table-cell-text'
          );
          return (
            Math.abs(
              el.closest('.handler-table-cell').getBoundingClientRect().width -
                width
            ) < 1 && el.tagName === (kind === 'link' ? 'A' : 'SPAN')
          );
        },
        { width, kind }
      );
      const geometry = await value.evaluate((el) => {
        const range = document.createRange();
        range.selectNodeContents(el);
        return {
          lines: range.getClientRects().length,
          width: el.clientWidth,
          scrollWidth: el.scrollWidth,
          height: el.clientHeight,
          scrollHeight: el.scrollHeight
        };
      });
      assert.equal(geometry.lines > 1, width < 600, JSON.stringify(geometry));
      assert(
        geometry.scrollWidth <= geometry.width + 1,
        JSON.stringify(geometry)
      );
      assert(
        geometry.scrollHeight <= geometry.height + 1,
        JSON.stringify(geometry)
      );
    }
  }
  await page.evaluate(() => (window.host.text = 'robot'.repeat(8)));
  await page.waitForFunction(
    () =>
      document.querySelector('.handler-table-cell .table-cell-text').textContent
        .length === 40
  );
  assert(await value.evaluate((el) => el.scrollWidth <= el.clientWidth + 1));
  await page.evaluate(() => (window.host.text = 'robot\nhero'));
  await page.waitForFunction(
    () =>
      document.querySelector('.handler-table-cell .table-cell-text')
        .textContent === 'robot\nhero'
  );
  assert.equal(
    await value.evaluate((el) => {
      const r = document.createRange();
      r.selectNodeContents(el);
      return new Set([...r.getClientRects()].map((rect) => rect.top)).size;
    }),
    2
  );
  await page.evaluate(() => {
    window.host.nested = true;
    window.host.kind = 'text';
    window.host.width = 160;
    window.host.text = 'robot, hero, character, rig, animation';
  });
  await page.locator('.nested-table-cell').waitFor();
  assert(
    await value.evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return (
        range.getClientRects().length > 1 &&
        el.scrollWidth <= el.clientWidth + 1 &&
        el.scrollHeight <= el.clientHeight + 1
      );
    }),
    'Nested tables use the same wrapping policy'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: ordinary text and links wrap on resize; keywords, long tokens and newlines remain visible within row bounds'
  );
} finally {
  await browser?.close();
  await server?.close();
}
