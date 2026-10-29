import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const key = 'cg/assets?project=column_fixture&code=DEMO_ARM';
const rows = [
  {
    __search_key__: key,
    code: 'DEMO_ARM',
    name: 'Robot Arm',
    description: 'Robot component'
  }
];
const elements = ['code', 'name', 'description'].map((name) => ({
  name,
  title: name === 'name' ? 'Name' : name,
  attributes: { width: '160' },
  cell: { kind: 'text', field: name, supported: true, sortable: true }
}));
const definition = (configured, view = 'table', columns = elements) => ({
  search_type: 'cg/assets',
  administration: true,
  operations: {},
  columns: Object.fromEntries(
    elements.map(({ name }) => [name, { data_type: 'varchar' }])
  ),
  table: {
    view,
    configured,
    layout: 'TableLayoutWdg',
    attributes: {},
    elements: columns
  }
});
let configuration, current, writes, readFailure, saveFailure;
function reset(mode) {
  const view = mode.includes('named') ? 'table@preset' : 'table';
  const xml =
    mode === 'named'
      ? '<config><!--keep--><view name="table@preset"><element name="code" width="160"/></view></config>'
      : '<config><!--keep--><table><element name="' +
        (mode === 'partial-late' ? 'description' : 'code') +
        '" width="160"/></table></config>';
  const generated = mode.startsWith('generated');
  current = definition(!generated, view, generated ? [] : elements);
  configuration = {
    view,
    sources: generated ? [] : [{ id: 7, xml }],
    layers: [],
    revision: 'r0',
    resolved: { elements: generated ? [] : elements }
  };
  writes = [];
  readFailure = false;
  saveFailure = false;
}
const server = await createServer({
  root,
  configFile: false,
  publicDir: root + 'frontend/public',
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [
    vue(),
    {
      name: 'column-resize-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (
            req.url !== '/column-resize-scene' &&
            !req.url.startsWith('/admin/')
          )
            return next();
          res.setHeader('Content-Type', 'application/json');
          if (req.url === '/column-resize-scene') {
            res.end(JSON.stringify({ definition: current, rows }));
            return;
          }
          let raw = '';
          for await (const chunk of req) raw += chunk;
          const data = JSON.parse(raw);
          let result;
          if (req.url === '/admin/widget-configuration/read') {
            if (readFailure) {
              res.statusCode = 503;
              res.end(JSON.stringify({ error: 'Read failed' }));
              return;
            }
            result = configuration;
          } else if (req.url === '/admin/widget-configuration/save') {
            writes.push(data);
            assert.equal(data.revision, configuration.revision);
            configuration = {
              ...configuration,
              revision: 'r' + writes.length,
              sources: [{ id: 7, xml: data.xml }]
            };
            const columns = [...data.xml.matchAll(/<element\b[^>]*>/g)].map(
              ([tag]) => {
                const name = /\bname="([^"]+)"/.exec(tag)[1];
                return {
                  ...elements.find((column) => column.name === name),
                  attributes: {
                    width: /\bwidth="([^"]+)"/.exec(tag)?.[1] || '160'
                  }
                };
              }
            );
            current = definition(true, data.view, columns);
            if (saveFailure) {
              res.statusCode = 502;
              res.end(JSON.stringify({ error: 'Save response lost' }));
              return;
            }
            result = configuration;
          } else if (req.url === '/admin/interface') result = current;
          else if (req.url === '/admin/table-cells')
            result = {
              [key]: Object.fromEntries(
                elements.map(({ name }) => [name, { text: rows[0][name] }])
              )
            };
          else {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: 'Unexpected fixture endpoint' }));
            return;
          }
          res.end(JSON.stringify({ result }));
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
const page = await browser.newPage({ viewport: { width: 1000, height: 600 } }),
  errors = [];
page.on('pageerror', (error) => errors.push(error.message));
page.setDefaultTimeout(10000);
async function open(mode) {
  reset(mode);
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/column_resize.html'
  );
  await page.waitForFunction(
    () => !!window.columnResizeFixture?.editor?.tableConfig
  );
}
const ready = () =>
  page.waitForFunction(() => !window.columnResizeFixture.editor.columnBusy);
try {
  for (const mode of [
    'generated',
    'partial',
    'partial-late',
    'named',
    'generated-named'
  ]) {
    await open(mode);
    const handle = page.getByRole('slider', {
      name: 'Resize column ' + (mode.startsWith('generated') ? 'name' : 'Name'),
      exact: true
    });
    const before = Number(await handle.getAttribute('aria-valuenow'));
    const box = await handle.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 48, box.y + box.height / 2);
    await page.mouse.up();
    await ready();
    assert.equal(
      writes.length,
      1,
      mode +
        ' ' +
        (await page.locator('[role="alert"]').allTextContents()).join('; ')
    );
    assert.match(
      writes[0].xml,
      new RegExp('name="name"[^>]*width="' + (before + 48) + '"')
    );
    assert.equal(await page.locator('[role="alert"]').count(), 0, mode);
    assert.equal(
      await page.evaluate(
        () => window.columnResizeFixture.editor.columnUncertain
      ),
      false
    );
    assert.deepEqual(
      current.table.elements.map((column) => column.name),
      ['code', 'name', 'description']
    );
    if (!mode.startsWith('generated'))
      assert.match(writes[0].xml, /<!--keep-->/);
    if (mode.includes('named'))
      assert.equal(
        (writes[0].xml.match(/name="table@preset"/g) || []).length,
        1
      );
    if (process.env.TABLE_DEFINITION_CAPTURE && mode === 'generated')
      await page.screenshot({ path: process.env.TABLE_DEFINITION_CAPTURE });
    await page.reload();
    await page.waitForFunction(
      () => !!window.columnResizeFixture?.editor?.tableConfig
    );
    assert.equal(
      Number(
        await page
          .getByRole('slider', { name: 'Resize column Name', exact: true })
          .getAttribute('aria-valuenow')
      ),
      before + 48,
      'Width survives reopening the table'
    );
  }
  await open('generated');
  await page.evaluate(() =>
    window.columnResizeFixture.editor.changeColumns(
      'width',
      'removed-column',
      240
    )
  );
  assert.equal(writes.length, 0);
  assert.equal(
    await page.evaluate(
      () => window.columnResizeFixture.editor.columnUncertain
    ),
    false
  );
  assert.equal(
    await page
      .getByText('Check the server result before saving again.', {
        exact: true
      })
      .count(),
    0
  );
  const handle = page.getByRole('slider', {
    name: 'Resize column name',
    exact: true
  });
  await handle.focus();
  await page.keyboard.press('ArrowRight');
  await ready();
  assert.equal(
    writes.length,
    1,
    'A local XML error must allow the next valid resize'
  );
  await open('generated');
  readFailure = true;
  await page.evaluate(() => {
    window.columnResizeFixture.editor.tableConfig = null;
  });
  await page
    .getByRole('slider', { name: 'Resize column name', exact: true })
    .focus();
  await page.keyboard.press('ArrowRight');
  await ready();
  assert.equal(writes.length, 0);
  assert.equal(
    await page.evaluate(
      () => window.columnResizeFixture.editor.columnUncertain
    ),
    false
  );
  readFailure = false;
  saveFailure = true;
  await page
    .getByRole('slider', { name: 'Resize column name', exact: true })
    .focus();
  await page.keyboard.press('ArrowRight');
  await ready();
  assert.equal(writes.length, 1);
  assert.equal(
    await page.evaluate(
      () => window.columnResizeFixture.editor.columnUncertain
    ),
    true
  );
  await page
    .getByText('Check the server result before saving again.', { exact: true })
    .waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'PASS: actual Name resize materializes schema/inherited/named columns; read/local errors stay retryable; uncertain writes stay guarded'
  );
} finally {
  await browser.close();
  await server.close();
}
