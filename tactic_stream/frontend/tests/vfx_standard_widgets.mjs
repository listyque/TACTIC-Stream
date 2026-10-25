import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  fieldKind,
  unsupportedField
} from '../src/features/objects/recordFields.js';

const field = {
  name: 'name',
  title: 'Name',
  class_name: 'tactic.ui.input.text_input_wdg.TextInputWdg',
  values: ['Original'],
  options: { required: 'true' },
  attributes: {},
  action: { handler: '', options: {} }
};
assert.equal(fieldKind(field), 'TextWdg');
assert.equal(unsupportedField(field), false);
assert.equal(
  unsupportedField({ ...field, options: { validation_js: 'custom()' } }),
  true
);
const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import TableCell from '/src/features/interface/TableCell.vue';
import RecordForm from '/src/features/objects/RecordForm.vue';
import {windowDirective} from '/src/controls/window.js';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,fadeAnimations:false,popupAnimations:false});
initializeAppearance();
const app=createApp({mounted(){window.host=this},render(){return [
h('div',{id:'wiki',class:'handler-table-cell'},[h(TableCell,{
element:{name:'description',field:'description',supported:true,cell:{kind:'text'}},
record:{description:'User <b>value</b>\\nSecond line'},cell:{text:'User <b>value</b>\\nSecond line',multiline:true},height:58})]),
h(RecordForm,{ref:'form',ticket:'fixture-ticket',project:'vfx_test',searchType:'vfx/layer'})]}});
app.directive('window',windowDirective);app.mount('#app');
</script><style>#wiki{box-sizing:border-box;width:360px;height:58px;display:flex;align-items:center;background:var(--surface);padding:0 10px;font-weight:400}body{margin:0}</style></body></html>`;
let browser;
const errors = [],
  requests = [];
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'vfx-standard-fixture',
      configureServer(server) {
        server.middlewares.use('/vfx-standard', async (_request, response) => {
          response.setHeader('Content-Type', 'text/html');
          response.end(await server.transformIndexHtml('/vfx-standard', html));
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 800 },
    hasTouch: true
  });
  page.setDefaultTimeout(8000);
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/form', (route) =>
    route.fulfill({
      json: {
        result: {
          mode: 'edit',
          search_type: 'vfx/layer',
          input_prefix: 'edit',
          search_key: 'vfx/layer?project=vfx_test&id=1',
          view: 'edit',
          fields: [field],
          expected_revision: 'fixture-revision'
        }
      }
    })
  );
  await page.route('**/admin/rpc', (route) => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({ json: { result: { info: { state: 'saved' } } } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'vfx-standard');
  await page
    .waitForFunction(() => !!window.host)
    .catch((error) => {
      throw new Error(errors.join('\n') || error.message);
    });
  await page.evaluate(() => document.fonts.ready);
  const wiki = page.locator('#wiki .table-cell-text');
  assert.equal(await wiki.innerText(), 'User <b>value</b>\nSecond line');
  assert.equal(await wiki.locator('b').count(), 0);
  assert.equal(
    await wiki.evaluate((el) => getComputedStyle(el).whiteSpace),
    'pre-line'
  );
  const output = process.argv[2];
  if (output) {
    await mkdir(output, { recursive: true });
    await page
      .locator('#wiki')
      .screenshot({ path: output + '/wiki-stream.png' });
  }
  await page.evaluate(() =>
    window.host.$refs.form.open('vfx/layer?project=vfx_test&id=1')
  );
  const dialog = page.locator('dialog:visible');
  const input = dialog.locator('input[name="edit|name"]');
  assert.equal(await input.inputValue(), 'Original');
  assert.equal(await input.getAttribute('required'), '');
  await input.fill('Changed through native text input');
  if (output)
    await dialog.screenshot({ path: output + '/text-input-stream.png' });
  await dialog.getByRole('button', { name: 'Save changes', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('dialog[open]'));
  assert.equal(requests.length, 1);
  assert.equal(requests[0].args[1], 'tactic.ui.panel.EditCmd');
  assert.equal(
    requests[0].args[3]['edit|name'],
    'Changed through native text input'
  );
  await page.setViewportSize({ width: 360, height: 640 });
  await page.evaluate(() =>
    window.host.$refs.form.open('vfx/layer?project=vfx_test&id=1')
  );
  await input.tap();
  await input.fill('Touch edit');
  await dialog.getByRole('button', { name: 'Save changes', exact: true }).tap();
  await page.waitForFunction(() => !document.querySelector('dialog[open]'));
  assert.equal(requests[1].args[3]['edit|name'], 'Touch edit');
  assert.deepEqual(errors, []);
  console.log(
    'VFX standard Wiki display and TextInput form mouse/touch save passed'
  );
} finally {
  await browser?.close();
  await server.close();
}
