import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const document = {
  layoutView: 'dashboard.lifecycle',
  targetSearchKey: 'sthpw/project?code=shell_fixture',
  layoutRecord: {},
  layoutNodes: [{ kind: 'heading', text: 'Lifecycle dashboard' }]
};
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import SectionTabRail from '/src/controls/SectionTabRail.vue';
import WorkspacePage from '/src/features/workspace/WorkspacePage.vue';
import {windowDirective} from '/src/controls/window.js';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',mode:'dark'});initializeAppearance();
createApp({provide:{openHelp(){}},data(){return{section:'dashboard'}},render(){return h('div',{style:'display:flex;position:absolute;inset:0'},[
 h(SectionTabRail,{tabs:[{id:'dashboard',title:'Overview',glyph:'dashboard'},{id:'other',title:'Other',glyph:'search'}],selected:this.section,onSelect:id=>this.section=id}),
 h('main',{style:'flex:1;position:relative;min-width:0'},[this.section==='dashboard'?h(WorkspacePage,{ticket:'fixture',project:'shell_fixture',view:'dashboard.lifecycle',title:'Overview',workspaceId:'dashboard',selectedKeys:[]}):h('div',{class:'other'},'Other workspace')])
])}}).directive('window',windowDirective).mount('#app');
</script></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  cacheDir: root + '/node_modules/.vite/workspace-shell',
  plugins: [
    vue(),
    {
      name: 'workspace-shell-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url === '/') {
            res.setHeader('Content-Type', 'text/html');
            res.end(await server.transformIndexHtml(req.url, html));
            return;
          }
          if (req.url === '/admin/rpc') {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ result: { info: document } }));
            return;
          }
          next();
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1400, height: 900 }
  });
  page.setDefaultTimeout(6000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0]);
  await page
    .getByText('Lifecycle dashboard', { exact: true })
    .waitFor()
    .catch(async (error) => {
      throw new Error(
        error.message +
          '\n' +
          errors.join('\n') +
          '\n' +
          (await page.locator('body').innerText())
      );
    });
  for (let index = 0; index < 3; index++) {
    for (const name of ['Other', 'Overview']) {
      const bounds = await page
        .getByRole('tab', { name, exact: true })
        .boundingBox();
      await page.mouse.move(
        bounds.x + bounds.width / 2,
        bounds.y + bounds.height / 2
      );
      await page.waitForFunction(() =>
        document.querySelector('.section-tab-reveal')?.matches(':popover-open')
      );
      await page.locator('.section-tab-expanded').click();
      await page.mouse.move(1300, 800);
      await page.waitForFunction(
        () =>
          !document
            .querySelector('.section-tab-reveal')
            ?.matches(':popover-open')
      );
      if (name === 'Overview') {
        await page.getByText('Lifecycle dashboard', { exact: true }).waitFor();
        assert.equal(
          await page.locator('.workspace-page').getAttribute('aria-busy'),
          'false'
        );
        assert.equal(
          await page
            .locator('.workspace-page [data-dock-control="dockGrip"]')
            .count(),
          0
        );
      } else await page.getByText('Other workspace', { exact: true }).waitFor();
    }
  }
  assert.deepEqual(errors, []);
  console.log(
    'Browser counterpart: custom pages reopen, pointer-selected sections collapse, no search grip in page content.'
  );
} finally {
  await browser.close();
  await server.close();
}
