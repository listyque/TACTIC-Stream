import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import RecordForm from '/src/features/objects/RecordForm.vue';
import {windowDirective} from '/src/controls/window.js';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',mode:'dark',fadeAnimations:false,popupAnimations:false});initializeAppearance();
window.setLanguage=value=>appearance.language=value;
createApp({mounted(){window.form=this.$refs.form},render(){return h(RecordForm,{ref:'form',ticket:'fixture',project:'demo',searchType:'demo/asset'})}}).directive('window',windowDirective).mount('#app');
</script></body></html>`;
const field = {
  name: 'preview',
  title: 'Preview',
  class_name: 'tactic.ui.widget.upload_wdg.SimpleUploadWdg',
  values: [],
  options: { icon_size: '100%' },
  attributes: {},
  action: { handler: 'pyasm.command.UploadAction', options: {} },
  input: { type: 'file', context: 'icon', column: 'preview' }
};
const definition = {
  mode: 'edit',
  search_type: 'demo/asset',
  view: 'edit',
  search_key: 'demo/asset?project=demo&code=ASSET',
  input_prefix: 'edit',
  expected_revision: 'fixture-revision',
  fields: [field]
};
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==',
  'base64'
);
let server, browser;
try {
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/record-preview',
    plugins: [
      vue(),
      {
        name: 'record-preview-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/preview-test') return next();
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
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 800 }
  });
  page.setDefaultTimeout(10000);
  const errors = [],
    writes = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/form', (route) =>
    route.fulfill({ json: { result: definition } })
  );
  await page.route('**/tactic/demo/UploadServer/', async (route) => {
    assert.match(route.request().postDataBuffer().toString(), /selected\.png/);
    writes.push('upload');
    await route.fulfill({ json: ['/temp/selected.png'] });
  });
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    assert.equal(payload.method, 'execute_cmd');
    assert.equal(payload.args[1], 'tactic.ui.panel.EditCmd');
    assert.equal(payload.args[2].expected_revision, 'fixture-revision');
    assert.deepEqual(payload.args[2].element_names, ['preview']);
    assert.equal(payload.args[3]['edit|preview|path'], 'selected.png');
    assert.equal(payload.args[3]['edit|preview|ticket'], 'fixture');
    assert.equal(payload.args[3]['edit|preview|context'], 'icon');
    assert.equal(payload.args[3]['edit|preview|column'], 'preview');
    writes.push('save');
    await route.fulfill({ json: { result: {} } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'preview-test');
  await page.waitForFunction(() => !!window.form);
  await page.evaluate(() =>
    window.form.open('demo/asset?project=demo&code=ASSET')
  );
  const picker = page.locator('.record-preview-input'),
    input = picker.locator('input[type=file]');
  const save = page.getByRole('button', { name: 'Save changes', exact: true });
  assert.equal(
    await page
      .getByText('This form contains unsupported inputs or options.', {
        exact: false
      })
      .count(),
    0
  );
  assert.equal(
    await picker
      .getByRole('button', { name: 'Choose image', exact: true })
      .isEnabled(),
    true
  );
  assert.equal(await save.isDisabled(), true);
  await page.evaluate(() => {
    const original = FileReader.prototype.readAsDataURL;
    FileReader.prototype.readAsDataURL = function (file) {
      window.finishPreview = () => original.call(this, file);
    };
    window.restoreReader = () =>
      (FileReader.prototype.readAsDataURL = original);
  });
  await input.setInputFiles({
    name: 'selected.png',
    mimeType: 'image/png',
    buffer: png
  });
  assert.equal(await page.evaluate(() => window.form.fileValidating), true);
  assert.equal(await save.isDisabled(), true);
  await page.evaluate(() => window.form.save());
  assert.deepEqual(
    writes,
    [],
    'No save while the image is still being validated'
  );
  await page.evaluate(() => {
    window.finishPreview();
    window.restoreReader();
  });
  await page.waitForFunction(
    () =>
      window.form.files.preview?.name === 'selected.png' &&
      !window.form.fileValidating
  );
  assert.equal(await picker.locator('img').count(), 1);
  assert.equal(await save.isEnabled(), true);
  await input.setInputFiles({
    name: 'broken.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image')
  });
  await picker.getByRole('alert').waitFor();
  assert.equal(
    await page.evaluate(() => window.form.files.preview.name),
    'selected.png'
  );
  await picker
    .getByRole('button', { name: 'Undo image selection', exact: true })
    .click();
  assert.equal(await save.isDisabled(), true);
  assert.equal(await page.evaluate(() => window.form.dirty), false);
  assert.deepEqual(writes, []);
  for (const width of [360, 1100]) {
    await page.setViewportSize({ width, height: 800 });
    for (const language of ['en', 'ru']) {
      await page.evaluate((value) => window.setLanguage(value), language);
      await page.waitForTimeout(100);
      assert.equal(
        await picker.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
        true
      );
    }
  }
  await page.evaluate(() => window.setLanguage('en'));
  await input.setInputFiles({
    name: 'selected.png',
    mimeType: 'image/png',
    buffer: png
  });
  await page.waitForFunction(
    () => !!window.form.files.preview && !window.form.fileValidating
  );
  await save.click();
  await page.waitForFunction(
    () => !window.form.definition && !window.form.saving
  );
  assert.deepEqual(writes, ['upload', 'save']);
  field.options.required = 'true';
  await page.evaluate(() =>
    window.form.open('demo/asset?project=demo&code=ASSET')
  );
  assert.equal(await input.evaluate((el) => el.required), true);
  await input.setInputFiles({
    name: 'selected.png',
    mimeType: 'image/png',
    buffer: png
  });
  await page.waitForFunction(
    () => !!window.form.files.preview && !window.form.fileValidating
  );
  assert.equal(await input.evaluate((el) => el.required), false);
  await page.evaluate(() => window.form.close());
  assert.deepEqual(
    writes,
    ['upload', 'save'],
    'Closing a staged image does not upload it'
  );
  field.options = { icon_size: '100%', read_only: 'true' };
  await page.evaluate(() =>
    window.form.open('demo/asset?project=demo&code=ASSET')
  );
  assert.equal(
    await picker
      .getByRole('button', { name: 'Choose image', exact: true })
      .isDisabled(),
    true
  );
  await page.evaluate(() => window.form.close());
  field.options = { icon_size: '100%' };
  field.input.context = 'publish';
  await page.evaluate(() =>
    window.form.open('demo/asset?project=demo&code=ASSET')
  );
  assert.equal(
    await page.locator('.record-preview-input').count(),
    0,
    'Non-image uploads retain the file picker'
  );
  assert.equal(await page.locator('input[type=file]').count(), 1);
  await page.evaluate(() => window.form.close());
  assert.deepEqual(errors, []);
  console.log(
    'Record preview: stock metadata, image validation, undo, EN/RU sizing and upload/save handoff passed'
  );
} finally {
  await browser?.close();
  await server?.close();
}
