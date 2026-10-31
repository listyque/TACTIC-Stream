import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('../../', import.meta.url));
const fixture = {
  name: 'table-alignment-fixture',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      if (req.url !== '/__alignment.html') return next();
      server.transformIndexHtml(req.url, html).then((body) => {
        res.setHeader('Content-Type', 'text/html');
        res.end(body);
      });
    });
  }
};
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue(), fixture],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
const html = `<!doctype html><html><body style="margin:0"><div id="app"></div><script type="module">
import {createApp,h,reactive} from 'vue';
import TableView from '/frontend/src/features/interface/TableView.vue';
import TableCell from '/frontend/src/features/interface/TableCell.vue';
import {initializeAppearance,appearance} from '/frontend/src/appearance.js';
import '/frontend/src/theme.css';import '/frontend/src/style.css';initializeAppearance();appearance.mode='dark';appearance.language='en';appearance.theme='md3';
const column=reactive({name:'status',title:'Status',width:160,hideOrder:0,kind:'text',supported:true,field:'status',cell:{kind:'text'},displayOptions:{}});
window.alignmentFixture=column;
createApp({render:()=>h(TableView,{columns:[column],groups:[{key:'',label:'',records:[{__search_key__:'task',status:'Оплачен'}]}],selectedKeys:[],state:{}},
{cell:({record,column})=>h(TableCell,{element:column,record,cell:{text:'Оплачен',statusColor:'#008000'}})})}).mount('#app');
</script><style>#app,.handler-table{height:200px;width:100%}</style></body></html>`;
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 800, height: 300 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(server.resolvedUrls.local[0] + '__alignment.html');
  const badge = page.locator('.table-status-badge'),
    header = page.getByRole('columnheader', { name: 'Status', exact: true });
  await badge.waitFor();
  await page.evaluate(() => document.fonts.ready);
  for (const width of [800, 320]) {
    await page.setViewportSize({ width, height: 300 });
    const h = await header.boundingBox(),
      b = await badge.boundingBox();
    assert.ok(Math.abs(h.x + h.width / 2 - b.x - b.width / 2) < 0.5);
    assert.equal(
      await header.evaluate((el) => getComputedStyle(el).justifyContent),
      'center'
    );
    if (process.env.TABLE_ALIGNMENT_CAPTURE) {
      const folder = process.env.TABLE_ALIGNMENT_CAPTURE;
      const native = JSON.parse(
        fs.readFileSync(folder + '/native-bounds.json')
      )[width];
      assert.ok(Math.abs(native.headingCenter - h.x - h.width / 2) < 0.5);
      assert.ok(Math.abs(native.badgeCenter - b.x - b.width / 2) < 0.5);
      await page.screenshot({ path: folder + '/browser-' + width + '.png' });
    }
  }
  for (const justify of ['left', 'right']) {
    await page.evaluate(
      (value) => (window.alignmentFixture.displayOptions = { justify: value }),
      justify
    );
    await page.waitForFunction(
      (value) =>
        document.querySelector('.handler-table-heading').dataset.align ===
        value,
      justify
    );
    const cell = badge.locator('..'),
      c = await cell.boundingBox(),
      b = await badge.boundingBox();
    assert.ok(
      Math.abs(
        (justify === 'left' ? b.x - c.x : c.x + c.width - b.x - b.width) - 14
      ) < 0.5
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'Table heading/status centering, narrow resize and explicit left/right alignment pass'
  );
} finally {
  await browser?.close();
  await server.close();
}
