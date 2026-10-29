import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const rows = Array.from({ length: 4 }, (_, index) => ({
  __search_key__: 'cg/assets?project=column_fixture&code=A' + index,
  code: 'A' + index,
  name: 'Robot Arm ' + (index + 1)
}));
const definition = {
  search_type: 'cg/assets',
  administration: false,
  operations: {},
  columns: {},
  table: {
    view: 'table',
    configured: true,
    layout: 'TableLayoutWdg',
    attributes: {},
    elements: ['code', 'name'].map((name) => ({
      name,
      title: name,
      attributes: { width: '160' },
      cell: { kind: 'text', field: name, supported: true }
    }))
  }
};
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
      name: 'workspace-width-fixture',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url !== '/column-resize-scene') return next();
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ definition, rows }));
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
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
  ignoreDefaultArgs: ['--hide-scrollbars']
});
const page = await browser.newPage({
    viewport: { width: 900, height: 650 },
    deviceScaleFactor: 1.5,
    colorScheme: 'dark'
  }),
  errors = [];
page.on('pageerror', (error) => errors.push(error.message));
page.setDefaultTimeout(10000);
const captures = [];
try {
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/column_resize.html'
  );
  await page.getByRole('grid', { name: 'Table', exact: true }).waitFor();
  await page.evaluate(() =>
    document
      .getElementById('app')
      .classList.add('workspace-results', 'table-container')
  );
  await page.getByText('Robot Arm 1', { exact: true }).click();
  for (const [name, width, height, vertical, horizontal] of [
    ['no-scroll', 700, 480, false, false],
    ['vertical', 700, 180, true, false],
    ['both', 350, 180, true, true],
    ['horizontal', 350, 480, false, true],
    ['restored', 700, 480, false, false]
  ]) {
    await page.evaluate(
      ({ width, height }) =>
        Object.assign(document.getElementById('app').style, {
          width: width + 'px',
          height: height + 'px'
        }),
      { width, height }
    );
    await page.waitForTimeout(100);
    const metrics = await page.evaluate(() => {
      const owner = document.getElementById('app'),
        grid = owner.querySelector('.handler-table');
      const header = grid.querySelector('.handler-table-header'),
        row = grid.querySelector('.handler-table-row');
      const bounds = grid.getBoundingClientRect();
      return {
        ownerWidth: owner.getBoundingClientRect().width,
        ownerClient: owner.clientWidth,
        gridWidth: bounds.width,
        clientWidth: grid.clientWidth,
        scrollWidth: grid.scrollWidth,
        clientHeight: grid.clientHeight,
        scrollHeight: grid.scrollHeight,
        headerWidth: header.getBoundingClientRect().width,
        rowWidth: row.getBoundingClientRect().width,
        vertical: grid.scrollHeight > grid.clientHeight,
        horizontal: grid.scrollWidth > grid.clientWidth
      };
    });
    captures.push({ name, ...metrics });
    assert.equal(
      metrics.ownerWidth - metrics.ownerClient,
      0,
      'Workspace must not reserve a hidden scrollbar: ' +
        JSON.stringify(metrics)
    );
    assert.equal(metrics.gridWidth, metrics.ownerClient, name);
    assert.equal(metrics.vertical, vertical, name);
    assert.equal(metrics.horizontal, horizontal, name);
    if (!vertical) assert.equal(metrics.gridWidth, metrics.clientWidth, name);
    else assert(metrics.gridWidth > metrics.clientWidth, name);
    assert(Math.abs(metrics.headerWidth - metrics.rowWidth) < 1, name);
    if (!horizontal)
      assert(Math.abs(metrics.headerWidth - metrics.clientWidth) < 1, name);
    if (process.env.TABLE_WORKSPACE_WIDTH_OUTPUT) {
      await mkdir(process.env.TABLE_WORKSPACE_WIDTH_OUTPUT, {
        recursive: true
      });
      await page.locator('#app').screenshot({
        path: process.env.TABLE_WORKSPACE_WIDTH_OUTPUT + '/' + name + '.png'
      });
    }
  }
  if (process.env.TABLE_WORKSPACE_WIDTH_OUTPUT)
    await writeFile(
      process.env.TABLE_WORKSPACE_WIDTH_OUTPUT + '/metrics.json',
      JSON.stringify(captures, null, 2)
    );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: workspace/table/header/rows fill available width; only actual vertical/horizontal scrollbars reserve space across resize transitions'
  );
} finally {
  await browser.close();
  await server.close();
}
