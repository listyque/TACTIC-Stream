import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import Header from '/src/features/objects/TaskInspectorHeader.vue';
import Hours from '/src/features/objects/WorkHoursSummary.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';import '/src/features/objects/inspector.css';
Object.assign(appearance,{mode:'dark',language:'en'});initializeAppearance();
const editor={object:{record:{name:'Robot Body'},type_title:'Assets',preview:{image:''}},processes:[{value:'model',label:'model',color:'#ee5358'}],task_choices:[],process_type:'process',selected_task:'task'};
createApp({render:()=>h('section',{class:'record-dialog notes-panel notes-panel-docked'},[h(Header,{editor,process:'model',expanded:false}),h(Hours,{summary:{actual:0,planned:2},expanded:false,hasTask:true})])}).mount('#app');
</script><style>html,body{margin:0;width:100%;height:100%}#app{width:680px;height:100%}</style>`;
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'inspector-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/inspector-fixture') return next();
          res.setHeader('Content-Type', 'text/html');
          res.end(await server.transformIndexHtml(req.url, html));
        });
      }
    }
  ],
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 400 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'inspector-fixture');
  const inspector = page.locator('.notes-panel-docked'),
    context = inspector.locator('.inspector-context'),
    hours = inspector.locator('.shared-work-hours');
  await context.waitFor();
  const outer = await inspector.boundingBox(),
    header = await context.boundingBox(),
    summary = await hours.boundingBox();
  assert.equal(header.x - outer.x, 8);
  assert.equal(header.y - outer.y, 5);
  assert.equal(outer.width - header.width, 16);
  assert.equal(summary.x, header.x);
  assert.equal(summary.width, header.width);
  assert.equal(summary.y - header.y - header.height, 5);
  assert.equal(header.height, 46);
  assert.equal(summary.height, 32);
  assert.deepEqual(errors, []);
  console.log(
    'PASS Task Inspector header and work-hours insets match native geometry'
  );
} finally {
  await browser?.close();
  await server.close();
}
