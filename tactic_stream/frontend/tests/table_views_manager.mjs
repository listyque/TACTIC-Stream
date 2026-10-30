import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const output =
  process.env.TABLE_VIEWS_OUTPUT || root + '/../tools/frame_table/output/views';
const ticket = process.env.TABLE_VIEWS_TICKET || 'fixture';
const project = process.env.TABLE_VIEWS_PROJECT || 'demo';
const type = process.env.TABLE_VIEWS_TYPE || 'demo/asset';
const html = `<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import Manager from '/src/features/interface/TableViewsManager.vue';
import TableView from '/src/features/interface/TableView.vue';import {appearance,initializeAppearance} from '/src/appearance.js';
import {windowDirective} from '/src/controls/window.js';import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',theme:'md3',mode:'dark',popupAnimations:false});initializeAppearance();
createApp({data(){return{events:[]}},mounted(){window.host=this},render(){return h('main',{style:'height:100%;display:flex'},[
h(TableView,{columns:[{name:'code',title:'Code',width:160}],groups:[],closedGroups:{},selectedKeys:[],editable:true,views:[{view:'table',current:true},{view:'definition'},{view:'edit'}],onManageViews:()=>this.$refs.manager.open()}),
h(Manager,{ref:'manager',ticket:${JSON.stringify(ticket)},project:${JSON.stringify(project)},searchType:${JSON.stringify(type)},current:'table',onUse:view=>this.events.push({type:'use',view}),onChanged:info=>this.events.push({type:'changed',info})})])}}).directive('window',windowDirective).mount('#app');
</script><style>html,body,#app{height:100%;width:100%;overflow:hidden}body{margin:0}</style></body></html>`;
let state = {
  project,
  searchType: type,
  current: 'table',
  views: [
    {
      view: 'table',
      title: 'Default table',
      protected: true,
      columns: 2,
      sources: 0
    }
  ],
  revision: 'r1'
};
const requests = [],
  errors = [];
let server, browser;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/table-views-manager',
    plugins: [
      vue(),
      {
        name: 'view-manager-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            try {
              if (req.url === '/manager-fixture') {
                res.setHeader('Content-Type', 'text/html');
                res.end(await server.transformIndexHtml(req.url, html));
                return;
              }
              if (req.url !== '/admin/rpc') return next();
              let raw = '';
              for await (const chunk of req) raw += chunk;
              const payload = JSON.parse(raw);
              requests.push(payload);
              res.setHeader('Content-Type', 'application/json');
              if (process.env.TABLE_VIEWS_SERVER) {
                const response = await fetch(
                  process.env.TABLE_VIEWS_SERVER + '/admin/rpc',
                  {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: raw
                  }
                );
                res.statusCode = response.status;
                res.end(await response.text());
                return;
              }
              const [context, command, args] = payload.args;
              assert.equal(command, 'tactic.ui.table.views.TableViewsCmd');
              assert.equal(context.project, project);
              assert.equal(args.search_type, type);
              let info;
              if (args.action === 'read') info = state;
              else {
                assert.equal(args.revision, state.revision);
                const selected =
                  args.action === 'create' || args.action === 'copy'
                    ? 'th_table_' +
                      args.title.toLowerCase().replaceAll(' ', '_')
                    : args.view;
                if (args.action === 'create' || args.action === 'copy')
                  state.views.push({
                    view: selected,
                    title: args.title,
                    columns: 2,
                    sources: 1,
                    protected: false
                  });
                else if (args.action === 'rename')
                  state.views.find((row) => row.view === selected).title =
                    args.title;
                else if (args.action === 'delete')
                  state.views = state.views.filter(
                    (row) => row.view !== selected
                  );
                state.revision += 'x';
                info = {
                  current: 'table',
                  selected: args.action === 'delete' ? 'table' : selected
                };
              }
              res.end(JSON.stringify({ result: { status: 'OK', info } }));
            } catch (error) {
              errors.push(error.stack);
              res.statusCode = 500;
              res.end(JSON.stringify({ message: error.message }));
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
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 }
  });
  page.on('pageerror', (error) => errors.push(error.stack));
  await page.goto(server.resolvedUrls.local[0] + 'manager-fixture');
  await page.getByLabel('Table views and columns', { exact: true }).click();
  assert.equal(
    await page.getByRole('button', { name: 'definition', exact: true }).count(),
    0
  );
  await page
    .getByRole('button', { name: 'Manage table views…', exact: true })
    .click();
  const manager = page.locator('.table-views-manager[open]');
  await manager.waitFor();
  const byId = (id) => manager.locator('[data-frame="' + id + '"]');
  await byId('tableViewsUse').waitFor();
  await byId('tableViews_copy').click();
  await manager
    .getByRole('textbox', { name: 'View name', exact: true })
    .fill('Artist review');
  await byId('tableViewsApply').click();
  await page.waitForFunction(() =>
    window.host.events.some(
      (event) =>
        event.type === 'changed' &&
        event.info.views.some((row) => row.title === 'Artist review')
    )
  );
  await manager
    .getByRole('textbox', { name: 'Find a table view', exact: true })
    .fill('Artist');
  assert.equal(await manager.locator('[data-frame^="tableView_"]').count(), 1);
  await byId('tableViews_rename').click();
  await manager
    .getByRole('textbox', { name: 'View name', exact: true })
    .fill('Lighting review');
  await byId('tableViewsApply').click();
  await page.waitForFunction(() =>
    window.host.events.some(
      (event) =>
        event.type === 'changed' &&
        event.info.views.some((row) => row.title === 'Lighting review')
    )
  );
  await manager
    .getByRole('textbox', { name: 'Find a table view', exact: true })
    .fill('');
  await page.screenshot({ path: output + '/manager.png' });
  await byId('tableViews_create').click();
  await manager
    .getByRole('textbox', { name: 'View name', exact: true })
    .fill('Fresh table');
  await byId('tableViewsApply').click();
  await page.waitForFunction(() =>
    window.host.events.some(
      (event) =>
        event.type === 'changed' &&
        event.info.views.some((row) => row.title === 'Fresh table')
    )
  );
  await byId('tableViews_delete').click();
  assert(await byId('tableViewsDeleteWarning').isVisible());
  await byId('tableViewsApply').click();
  await page.waitForFunction(
    () =>
      window.host.events.filter((event) => event.type === 'changed').length ===
      4
  );
  await byId('tableViewsUse').click();
  await manager.waitFor({ state: 'hidden' });
  assert.equal(
    (await page.evaluate(() => window.host.events)).at(-1).type,
    'use'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: table menu -> manager, create/copy/rename/delete, search, revision payloads and use selection'
  );
} finally {
  await browser?.close();
  await server?.close();
}
