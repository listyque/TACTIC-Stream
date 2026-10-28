import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const xml =
  '<config><continuous_example layout="sobject-layout" flow="grid"><element name="title" height="32"><display class="title"><bind>record.name</bind></display></element></continuous_example></config>';
const layout = {
  flow: 'grid',
  collection: 'tree',
  columns: 12,
  elements: [
    {
      name: 'title',
      kind: 'title',
      parent: '',
      variant: 'all',
      row: 1,
      column: 1,
      span: 12,
      rows: 1,
      height: 32,
      options: { bind: 'record.name' }
    }
  ]
};
const html = `<!doctype html><html><body><div id="app" style="height:100vh;display:flex"></div><script type="module">
import {createApp,h,ref} from 'vue';import Editor from '/src/features/administration/LayoutEditor.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';import '/src/theme.css';import '/src/style.css';
import {windowDirective} from '/src/controls/window.js';
Object.assign(appearance,{language:'en',mode:'dark'});initializeAppearance();
const editor=ref(null),project=ref('one');window.fixtureEditor=editor;window.fixtureProject=value=>project.value=value;
window.fixtureWarnings=[];
const app=createApp({render:()=>h(Editor,{ref:editor,style:'height:100%;flex:1',ticket:'fixture',project:project.value,initialFocus:{searchType:'foreign/activity'}})});
app.config.warnHandler=message=>window.fixtureWarnings.push(message);
app.provide('openHelp',()=>{}).directive('window',windowDirective).mount('#app');
</script></body></html>`;
const reads = [];
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'layout-catalog',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url === '/') {
            res.setHeader('Content-Type', 'text/html');
            res.end(await server.transformIndexHtml(req.url, html));
            return;
          }
          if (!req.url.startsWith('/admin/')) return next();
          let body = '';
          for await (const chunk of req) body += chunk;
          const value = JSON.parse(body);
          res.setHeader('Content-Type', 'application/json');
          if (req.url.endsWith('/catalog'))
            res.end(
              JSON.stringify({
                result: {
                  stypes:
                    value.project === 'two'
                      ? [{ code: 'two/card', title: 'Two card' }]
                      : [
                          { code: 'library/card', title: 'Card' },
                          { code: 'one/broken', title: 'Unavailable' }
                        ]
                }
              })
            );
          else if (req.url.endsWith('/read')) {
            reads.push(value.search_type);
            if (value.search_type === 'one/broken') {
              res.statusCode = 400;
              res.end(
                JSON.stringify({ error: 'Registered table does not exist' })
              );
            } else
              res.end(
                JSON.stringify({
                  result: {
                    revision: 'R1',
                    sources: [{ id: 1, xml }],
                    layers: [],
                    views: ['continuous_example'],
                    layout_views: ['continuous_example'],
                    layout_templates: [],
                    resolved: { configured: true }
                  }
                })
              );
          } else if (req.url.endsWith('/preview'))
            res.end(
              JSON.stringify({
                result: { interface: { table: { item_layout: layout } } }
              })
            );
          else if (req.url === '/admin/rpc')
            res.end(JSON.stringify({ result: [] }));
          else {
            res.statusCode = 404;
            res.end('{}');
          }
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({ headless: true });
let page;
const errors = [];
try {
  page = await browser.newPage({
    viewport: { width: 1400, height: 900 }
  });
  page.on('pageerror', (error) => errors.push(error.message));
  page.setDefaultTimeout(8000);
  await page.goto(server.resolvedUrls.local[0]);
  await page.locator('.layout-live-preview .result-presentation').waitFor();
  const types = page.locator('[data-frame="layoutSearchType"]');
  assert.deepEqual(reads, ['library/card']);
  await types.selectOption('one/broken');
  await page
    .locator('.layout-live-preview [role="alert"]')
    .filter({ hasText: 'Registered table does not exist' })
    .waitFor();
  assert.equal(
    await page.getByText('Loading interface...', { exact: true }).count(),
    0
  );
  assert.deepEqual(
    await types
      .locator('option')
      .evaluateAll((nodes) => nodes.map((node) => node.value)),
    ['library/card', 'one/broken']
  );
  assert.deepEqual(reads, ['library/card', 'one/broken']);
  await types.selectOption('library/card');
  await page.waitForFunction(
    () =>
      document.querySelector('.layout-editor')?.getAttribute('aria-busy') ===
      'false'
  );
  await page.locator('.layout-live-preview .result-presentation').waitFor();
  assert.equal(
    await page.locator('.layout-live-preview [role="alert"]').count(),
    0
  );
  assert.deepEqual(reads, ['library/card', 'one/broken', 'library/card']);
  let capture;
  const pending = new Promise((resolve) => {
    capture = resolve;
  });
  await page.route('**/admin/widget-configuration/catalog', (route) => {
    if (route.request().postDataJSON().project === 'one') capture(route);
    else route.continue();
  });
  await page.evaluate(() => {
    window.fixtureEditor.value.loadCatalog();
  });
  const old = await pending;
  await page.evaluate(() => window.fixtureProject('two'));
  await page.waitForFunction(
    () =>
      window.fixtureEditor.value.searchType === 'two/card' &&
      !window.fixtureEditor.value.busy
  );
  await old.fulfill({
    json: {
      result: {
        stypes: [{ code: 'foreign/activity', title: 'Stale activity' }]
      }
    }
  });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(await types.inputValue(), 'two/card');
  assert.deepEqual(
    await types
      .locator('option')
      .evaluateAll((nodes) => nodes.map((node) => node.value)),
    ['two/card']
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(await page.evaluate(() => window.fixtureWarnings), []);
  console.log(
    'Scoped catalog excludes stale types; failed preview stops loading and recovers with a valid type'
  );
} catch (error) {
  console.error(
    'reads',
    reads,
    'errors',
    errors,
    await page.locator('body').innerText()
  );
  console.error(
    await page.evaluate(() => ({
      error: window.fixtureEditor.value.error,
      busy: window.fixtureEditor.value.busy,
      viewport: window.fixtureEditor.value.viewport,
      frameError: window.fixtureEditor.value.frameModel.error
    }))
  );
  throw error;
} finally {
  await browser.close();
  await server.close();
}
