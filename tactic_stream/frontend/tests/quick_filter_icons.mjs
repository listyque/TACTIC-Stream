import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as Header from '../../src/tactic_stream/shared_ui/features/search/header.ui.mjs';

for (const key of [
  'column:duration',
  'column:pipeline_code',
  'process',
  'status',
  'assigned'
]) {
  assert.equal(
    Header.quickIcon({ key }),
    '',
    key + ' must not choose an icon from its name'
  );
  assert.equal(Header.quickIcon({ key, columnIcon: 'FAS_CUBE' }), 'FAS_CUBE');
  assert.equal(
    Header.quickIcon({
      key,
      columnIcon: 'FAS_CUBE',
      icon: 'material-design:rocket'
    }),
    'material-design:rocket'
  );
  assert.equal(
    Header.quickIcon({ key, columnIcon: 'FAS_CUBE', icon: '' }),
    'FAS_CUBE'
  );
  const scene = Header.quickStrip([{ key, textWidth: 80 }], 500, 'en');
  assert.equal(
    scene.nodes[0].children.find((node) => node.id.endsWith('Icon')).visible,
    false
  );
}
const root = fileURLToPath(new URL('../', import.meta.url)),
  output = process.env.QUICK_FILTER_ICON_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const html = `<!doctype html><div id="app"></div><script type="module">
import {createApp,h,ref,reactive} from 'vue';
import Editor from '/src/features/workspace/QuickFilterEditor.vue';
import Quick from '/src/features/workspace/SearchQuickFilters.vue';
import {windowDirective} from '/src/controls/window.js';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
const catalog=reactive({revision:'one',configuration:{groups:[{key:'column:duration',enabled:true}],defaultSelections:{}},groups:[{key:'column:duration',column:'duration',source:'column',title:'Duration',columnIcon:'clock',options:[{key:'2',title:'2 Minutes'}],accent:'#607d8b'}]});
const editor=ref(null),quick=ref(null),layout=ref(null),canManage=ref(true),applied=[];
window.filterIcons={editor,quick,layout,catalog,appearance,canManage,applied};
createApp({render:()=>h('main',{style:{padding:'12px',width:'900px'}},[
 h('button',{id:'open-editor',onClick:()=>editor.value.open()},'Edit quick filters'),
 h(Quick,{ref:quick,ticket:'fixture',project:'demo',searchType:'demo/asset',scope:'demo/asset@one',budget:850,layout:layout.value,selections:{}}),
 h(Editor,{ref:editor,ticket:'fixture',project:'demo',searchType:'demo/asset',scope:'demo/asset@one',layout:layout.value,selections:{},canManage:canManage.value,onApply:value=>{layout.value=value;applied.push(value);},onChanged:()=>quick.value.load(true)})
])}).directive('window',windowDirective).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'filter-icon-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url !== '/filter-icons') return next();
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
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
      viewport: { width: 1200, height: 900 },
      hasTouch: true
    }),
    errors = [],
    writes = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let saved = {
    groups: [{ key: 'column:duration', enabled: true }],
    defaultSelections: {}
  };
  const catalog = () => ({
    revision: 'one',
    configuration: saved,
    groups: [
      {
        key: 'column:duration',
        column: 'duration',
        source: 'column',
        title: 'Duration',
        columnIcon: 'clock',
        accent: '#607d8b',
        options: [{ key: '2', title: '2 Minutes' }]
      }
    ]
  });
  await page.route('**/admin/search-configuration/read', (route) =>
    route.fulfill({ json: { result: catalog() } })
  );
  await page.route('**/admin/search-configuration/quick-save', (route) => {
    saved = route.request().postDataJSON().configuration;
    writes.push(saved);
    return route.fulfill({ json: { result: catalog() } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'filter-icons');
  const header = page.locator(
    '[data-frame="searchQuickGroup_column:durationIcon"]'
  );
  await header.waitFor();
  assert.equal(await header.getAttribute('data-icon'), 'clock');
  await page.locator('#open-editor').click();
  const dialog = page.locator('.quick-filter-editor-dialog[open]');
  if (output) {
    await page.setViewportSize({ width: 620, height: 520 });
    for (const language of ['en', 'ru']) {
      for (const mode of ['dark', 'light']) {
        await page.evaluate(
          ({ language, mode }) =>
            Object.assign(window.filterIcons.appearance, { language, mode }),
          { language, mode }
        );
        await dialog.screenshot({
          path: output + '/browser-' + language + '-' + mode + '.png'
        });
      }
    }
    await page.evaluate(() =>
      Object.assign(window.filterIcons.appearance, {
        language: 'en',
        mode: 'dark'
      })
    );
    await page.setViewportSize({ width: 1200, height: 900 });
  }
  async function choose(name) {
    await dialog.locator('[data-frame="quickFilterIcon_0"] summary').click();
    await dialog
      .getByRole('textbox', { name: 'Search icons', exact: true })
      .fill(name);
    await dialog
      .locator('.icon-library')
      .getByRole('button', { name, exact: true })
      .click();
  }
  await choose('rocket');
  await dialog
    .getByRole('button', { name: 'Save for this tab', exact: true })
    .click();
  assert.equal(
    await header.getAttribute('data-icon'),
    'material-design:rocket'
  );
  assert.equal(
    await page.evaluate(() => window.filterIcons.layout.value.groups[0].icon),
    'material-design:rocket'
  );
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await page.locator('#open-editor').click();
  const current = dialog.locator(
    '[data-frame="quickFilterIcon_0"] summary .app-icon'
  );
  assert.equal(
    await current.getAttribute('data-icon'),
    'material-design:rocket'
  );
  await dialog
    .getByRole('button', { name: 'Use column icon', exact: true })
    .click();
  assert.equal(await current.getAttribute('data-icon'), 'clock');
  await dialog
    .getByRole('button', { name: 'Save for this tab', exact: true })
    .click();
  assert.equal(await header.getAttribute('data-icon'), 'clock');
  await choose('camera');
  await dialog
    .getByRole('button', { name: 'Save as defaults on server', exact: true })
    .click();
  await page.waitForFunction(
    () =>
      window.filterIcons.editor.value.message ===
      'Quick-filter defaults saved on server'
  );
  assert.equal(writes[0].groups[0].icon, 'material-design:camera');
  await page.evaluate(() => {
    window.filterIcons.layout.value = null;
  });
  await page.waitForFunction(
    () =>
      document.querySelector(
        '[data-frame="searchQuickGroup_column:durationIcon"]'
      ).dataset.icon === 'material-design:camera'
  );
  if (output)
    for (const mode of ['dark', 'light']) {
      await page.evaluate((mode) => {
        window.filterIcons.appearance.mode = mode;
      }, mode);
      await dialog.screenshot({ path: output + '/browser-' + mode + '.png' });
    }
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await page.evaluate(() => {
    window.filterIcons.canManage.value = false;
    window.filterIcons.appearance.language = 'ru';
  });
  await page.locator('#open-editor').click();
  assert.equal(
    await dialog
      .locator('[data-frame="saveQuickFilterDefaultsButton"]')
      .isVisible(),
    false
  );
  assert(
    await dialog.locator('[data-frame="quickFilterIcon_0"] summary').isEnabled()
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: no field-name icons; column inheritance; real icon picker/tab save/reopen/reset/shared save; stored qualified icons, supervisor boundary and RU editor'
  );
} finally {
  await browser?.close();
  await server.close();
}
