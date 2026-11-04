import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  extent,
  describe,
  focusScene
} from '../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';

const short = {
  loaded: true,
  columns: [{ name: 'name' }],
  rows: [{ key: 'A', record: {}, cells: {} }]
};
assert.equal(extent(short, 600), 177);
assert.equal(
  extent({ busy: true, loaded: false, text: '2 assets', rows: [] }, 600),
  235
);
assert.equal(
  extent(
    {
      ...short,
      rows: Array.from({ length: 4 }, (_, i) => ({ key: String(i) }))
    },
    600,
    600
  ),
  351
);
const scene = describe(short, 600, 177, 'en');
const body = scene.nodes.find((node) => node.id === 'nestedTableBody');
assert.deepEqual([body.x, body.y, body.width, body.height], [0, 42, 600, 95]);
assert.equal(
  scene.nodes.find((node) => node.id === 'nestedFooterSurface').y,
  137
);
assert(!JSON.stringify(scene).includes('nestedDrag'));

const compact = describe(
  { ...short, search: false, insert: true },
  320,
  extent({ ...short, search: false }, 320),
  'en'
);
assert(
  !compact.nodes.some((node) =>
    ['nestedFilter', 'nestedToolbarSurface'].includes(node.id)
  )
);
assert.equal(compact.nodes.find((node) => node.id === 'nestedTableBody').y, 0);
const footer = compact.nodes.find((node) => node.id === 'nestedFooterSurface');
for (const id of ['nestedReload', 'nestedCreate', 'nestedClose'])
  assert.equal(compact.nodes.find((node) => node.id === id).y, footer.y + 4);
const focus = focusScene(
  { x: 0, y: 95, width: 800, height: 309 },
  800,
  650,
  'en'
);
assert.equal(
  focus.nodes.filter((node) => node.id.startsWith('nestedFocusScrim')).length,
  2
);
assert(focus.nodes.find((node) => node.id === 'nestedFocusShadow').shadow);
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  publicDir: root + 'frontend/public',
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  ignoreDefaultArgs: ['--hide-scrollbars'],
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
const page = await browser.newPage({
  viewport: { width: 500, height: 300 },
  deviceScaleFactor: 1.5
});
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
await page.route('**/admin/widget-configuration/read', (route) =>
  route.fulfill({
    json: {
      result: {
        views: [{ view: 'parent', title: 'Parent', current: true }],
        revision: 'fixture'
      }
    }
  })
);
await page.route('**/admin/result-items', (route) =>
  route.fulfill({ json: { result: { items: [] } } })
);
const forms = [];
await page.route('**/admin/form', async (route) => {
  const payload = route.request().postDataJSON();
  forms.push(payload);
  await route.fulfill({
    json: {
      result: {
        mode: 'insert',
        search_type: payload.search_type,
        view: payload.view,
        fields: []
      }
    }
  });
});
let reads = 0;
let fileColumns = false;
const queries = [];
const suggestions = [];
await page.route('**/admin/search-configuration/suggestions', async (route) => {
  const payload = route.request().postDataJSON();
  suggestions.push(payload);
  await route.fulfill({
    json: {
      result: {
        records: [{ title: 'B', description: 'Robot reference', code: 'B' }]
      }
    }
  });
});
await page.route('**/admin/rpc', async (route) => {
  const request = route.request().postDataJSON();
  if (request.args?.[1] === 'error') {
    assert.fail('Unexpected logged browser error: ' + request.args[2]);
    await route.fulfill({ json: { result: null } });
    return;
  }
  assert.equal(request.args[1], 'tactic.ui.table.NestedTableReadCmd');
  assert.ok(['child', 'table'].includes(request.args[2].view));
  reads++;
  const query = request.args[2];
  queries.push(query);
  const secondPage = query.offset > 0;
  const recordKey = secondPage ? 'demo/asset?code=C' : 'demo/asset?code=B';
  const recordCode = secondPage ? 'C' : 'B';
  await route.fulfill({
    json: {
      result: {
        info: {
          definition: {
            search_type: 'demo/asset',
            administration: true,
            operations: { create: true, edit: true },
            columns: fileColumns ? { file_name: {}, code: {} } : { code: {} },
            table: {
              layout: 'TableLayoutWdg',
              configured: true,
              elements: [
                {
                  name: 'code',
                  title: 'Code',
                  attributes: { width: '160' },
                  cell: {
                    kind: 'text',
                    supported: true,
                    sortable: true,
                    field: 'code'
                  }
                },
                {
                  name: 'expand',
                  title: 'Details',
                  attributes: { width: '100' },
                  cell: { kind: 'commands', supported: true }
                }
              ]
            }
          },
          records: [{ code: recordCode, __search_key__: recordKey }],
          hasNext: !secondPage,
          cells: {
            [recordKey]: {
              expand: {
                nestedTable: {
                  searchType: 'demo/asset',
                  view: 'parent',
                  parentKey: 'demo/asset?code=A'
                },
                actions: [
                  {
                    name: 'nested-table',
                    label: 'Show related table',
                    icon: 'chevron-right'
                  }
                ]
              }
            }
          }
        }
      }
    }
  });
});
try {
  await page.setViewportSize({ width: 800, height: 682 });
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html?parent'
  );
  await page.waitForFunction(() => window.nestedFixture);
  await page.evaluate(() => {
    const state = window.nestedFixture.state;
    state.scope.search = false;
    state.scope.insert = false;
    state.columns = [
      {
        name: 'code',
        title: 'Code',
        width: 160,
        cell: { kind: 'text', supported: true }
      },
      {
        name: 'expand',
        title: 'Details',
        width: 100,
        cell: { kind: 'text', supported: true }
      }
    ];
    state.definition.table.elements = state.columns.map((column) => ({
      ...column,
      attributes: { width: column.width }
    }));
    state.rows = Array.from({ length: 4 }, (_, i) => ({
      key: String(i),
      record: { code: 'Row ' + i, __search_key__: String(i) },
      cells: { code: { text: 'Row ' + i }, expand: { text: '' } }
    }));
  });
  const parentTable = page.locator('.handler-table').first();
  const raised = parentTable.locator('.nested-table').first();
  await raised.locator('[data-frame="nestedTableBody"]').waitFor();
  assert.equal(
    await raised.locator('[data-frame="nestedToolbarSurface"]').count(),
    0
  );
  assert(
    await raised
      .locator('[data-frame="nestedReload"]')
      .evaluate(
        (el) =>
          parseFloat(getComputedStyle(el).borderTopLeftRadius) <
          el.offsetWidth / 2
      )
  );
  const raisedRect = await raised.boundingBox();
  const bodyRect = await raised
    .locator('[data-frame="nestedTableBody"]')
    .boundingBox();
  assert.equal(bodyRect.y, raisedRect.y);
  await parentTable.locator('[data-frame="nestedFocusShadow"]').waitFor();
  const focusOutput = process.env.TABLE_NESTED_FOCUS_OUTPUT;
  if (focusOutput) {
    mkdirSync(focusOutput, { recursive: true });
    await parentTable.screenshot({ path: focusOutput + '/browser-focus.png' });
    const parentRect = await parentTable.boundingBox();
    const footerRect = await raised
      .locator('[data-frame="nestedFooterSurface"]')
      .boundingBox();
    const geometry = {
      width: parentRect.width,
      height: parentRect.height,
      bounds: {
        x: raisedRect.x - parentRect.x,
        y: raisedRect.y - parentRect.y,
        width: raisedRect.width,
        height: raisedRect.height
      },
      bodyY: bodyRect.y - raisedRect.y,
      footerY: footerRect.y - raisedRect.y
    };
    writeFileSync(
      focusOutput + '/browser-focus.json',
      JSON.stringify(geometry)
    );
    if (existsSync(focusOutput + '/native-focus.json'))
      assert.deepEqual(
        geometry,
        JSON.parse(readFileSync(focusOutput + '/native-focus.json', 'utf8'))
      );
  }
  if (focusOutput) {
    const captures = [];
    for (const width of [800, 320]) {
      await page.setViewportSize({ width, height: 682 });
      for (const dark of [true, false]) {
        await page.evaluate(async (dark) => {
          const { appearance } = await import('/frontend/src/appearance.js');
          appearance.mode = dark ? 'dark' : 'light';
          await new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          );
        }, dark);
        await page.waitForFunction(() => {
          const table = document.querySelector('.handler-table');
          const detail = table.querySelector('.handler-table-detail');
          return detail.offsetWidth === table.clientWidth;
        });
        const parentRect = await parentTable.boundingBox();
        const rect = await raised.boundingBox();
        const footer = await raised
          .locator('[data-frame="nestedFooterSurface"]')
          .boundingBox();
        captures.push({
          width,
          height: parentRect.height,
          dark,
          bounds: {
            x: rect.x - parentRect.x,
            y: rect.y - parentRect.y,
            width: rect.width,
            height: rect.height
          },
          bodyY: 0,
          footerY: footer.y - rect.y
        });
        await parentTable.screenshot({
          path: focusOutput + `/browser-focus-${width}-${dark}.png`
        });
      }
    }
    writeFileSync(
      focusOutput + '/browser-focus-matrix.json',
      JSON.stringify(captures)
    );
    if (existsSync(focusOutput + '/native-focus-matrix.json'))
      assert.deepEqual(
        captures,
        JSON.parse(
          readFileSync(focusOutput + '/native-focus-matrix.json', 'utf8')
        )
      );
    await page.setViewportSize({ width: 800, height: 682 });
  }
  await parentTable
    .locator('[data-frame="nestedFocusScrim_0"]')
    .click({ position: { x: 10, y: 10 } });
  await raised.waitFor({ state: 'detached' });
  assert.equal(
    await page.evaluate(() => window.nestedFixture.state.open),
    false
  );
  await page.setViewportSize({ width: 500, height: 300 });
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html'
  );
  const root = page.locator('#app > .nested-table');
  assert(
    (await root.boundingBox()).height < 240,
    'A one-row table must fit its content'
  );
  await root.locator('.handler-table-header').waitFor();
  const captures = [];
  for (const width of [320, 1000]) {
    await page.setViewportSize({ width: width + 32, height: 400 });
    await page.evaluate((width) => window.nestedFixture.resize(width), width);
    await page.waitForFunction((width) => {
      const header = document.querySelector(
        '#app > .nested-table [data-frame="nestedToolbarSurface"]'
      );
      return Math.abs(header.getBoundingClientRect().width - width) < 1;
    }, width);
    const bounds = await root.evaluate((element) => {
      const outer = element.getBoundingClientRect();
      return Object.fromEntries(
        [
          'nestedFilter',
          'nestedReload',
          'nestedClose',
          'nestedTableBody',
          'nestedFooterSurface'
        ].map((name) => {
          const rectangle = element
            .querySelector('[data-frame="' + name + '"]')
            .getBoundingClientRect();
          return [
            name,
            {
              x: rectangle.x - outer.x,
              y: rectangle.y - outer.y,
              width: rectangle.width,
              height: rectangle.height
            }
          ];
        })
      );
    });
    for (const [name, rectangle] of Object.entries(bounds)) {
      assert.ok(rectangle.x >= 0 && rectangle.y >= 0, name);
      assert.ok(rectangle.x + rectangle.width <= width, name);
      assert.ok(rectangle.y + rectangle.height <= 320, name);
    }
    captures.push({ width, bounds });
    if (process.env.TABLE_NESTED_OUTPUT) {
      mkdirSync(process.env.TABLE_NESTED_OUTPUT, { recursive: true });
      await root.screenshot({
        path: process.env.TABLE_NESTED_OUTPUT + '/browser-' + width + '.png'
      });
    }
  }
  if (process.env.TABLE_NESTED_OUTPUT)
    writeFileSync(
      process.env.TABLE_NESTED_OUTPUT + '/browser.json',
      JSON.stringify(captures, null, 2)
    );
  await page.evaluate(() => window.nestedFixture.resize(0));
  await page.setViewportSize({ width: 500, height: 300 });

  await page.evaluate(() => {
    window.nestedFixture.state.gear = true;
    window.nestedFixture.state.definition.administration = true;
  });
  const headerReads = reads;
  await root
    .locator('.handler-table-heading[aria-label=Details]')
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Edit Column Definition', exact: true })
    .click();
  assert.deepEqual(
    await page.evaluate(() => window.nestedFixture.columnEdits.at(-1)),
    {
      project: 'demo',
      searchType: 'demo/asset',
      view: 'parent',
      column: 'expand',
      target: 'definition'
    }
  );
  assert.equal(reads, headerReads);
  await root
    .locator('.handler-table-heading[aria-label=Details]')
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Column Manager', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => window.nestedFixture.columnEdits.at(-1).column),
    ''
  );
  assert.equal(await root.locator('[data-frame=nestedDrag]').count(), 0);
  await root
    .locator('.handler-table-row[role=row]')
    .click({ position: { x: 110, y: 35 } });
  assert.deepEqual(
    await page.evaluate(() => window.nestedFixture.state.selected),
    []
  );
  await root
    .getByRole('button', { name: 'Object actions', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Edit record', exact: true })
    .waitFor();
  await page.keyboard.press('Escape');

  await root.locator('[data-frame="tableServiceAction_0"]').click();
  const child = root.locator('.nested-table');
  await child
    .locator('.handler-table-row[role=row] input[type=checkbox]')
    .click();
  assert.deepEqual(
    await page.evaluate(() => window.nestedFixture.state.selected),
    []
  );
  assert.deepEqual(
    await page.evaluate(
      () => window.nestedFixture.state.children['demo/asset?code=A'].selected
    ),
    ['demo/asset?code=B']
  );
  await child.locator('[data-frame="tableServiceAction_0"]').click();
  assert.equal(
    await child.locator('.error').innerText(),
    'This nested table would repeat an ancestor scope'
  );
  await child.locator('[data-frame="nestedClose"]').click();
  await page.waitForFunction(
    () => !document.querySelector('#app > .nested-table .nested-table')
  );
  await root.locator('[data-frame="tableServiceAction_0"]').click();
  await child
    .locator('.handler-table-row[role=row] input[type=checkbox]')
    .waitFor();
  assert.equal(reads, 1, 'Reopening a loaded branch must not fetch again');
  assert.deepEqual(
    await page.evaluate(
      () => window.nestedFixture.state.children['demo/asset?code=A'].selected
    ),
    ['demo/asset?code=B']
  );
  await child.locator('[data-frame="nestedNext"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].rows[0]?.key ===
      'demo/asset?code=C'
  );
  assert.deepEqual(
    await page.evaluate(() => ({
      selected:
        window.nestedFixture.state.children['demo/asset?code=A'].selected,
      records:
        window.nestedFixture.state.children['demo/asset?code=A']
          .selectionRecords
    })),
    {
      selected: ['demo/asset?code=B'],
      records: { 'demo/asset?code=B': { code: 'B' } }
    }
  );
  await child
    .locator('.handler-table-heading[aria-label=Code]')
    .click({ button: 'right' });
  await page
    .getByRole('menuitemradio', { name: 'Sort A to Z', exact: true })
    .click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].order ===
      'code asc'
  );
  assert.equal(queries.at(-1).offset, 0);
  assert.deepEqual(queries.at(-1).order_by, ['code asc']);
  const filterReads = reads;
  const search = child.locator('[data-frame="nestedFilter"] input');
  await search.fill('B');
  await page.locator('.search-suggestions:popover-open').waitFor();
  assert.equal(suggestions.at(-1).nested_scope.parent_key, 'demo/asset?code=A');
  await search.press('ArrowDown');
  assert.ok(
    await search.getAttribute('aria-activedescendant'),
    'ArrowDown highlights the native suggestion'
  );
  await search.press('Enter');
  await page.waitForFunction(
    ([prev]) =>
      !window.nestedFixture.state.children['demo/asset?code=A'].busy &&
      window.nestedFixture.state.children['demo/asset?code=A'].filter === 'B',
    [filterReads]
  );
  assert.equal(reads, filterReads + 1);
  assert.deepEqual(queries.at(-1).filters, []);
  assert.equal(queries.at(-1).keyword, 'B');
  assert.equal(queries.at(-1).keyword_relation, '=');
  await child.locator('[data-frame="nestedCreate"]').click();
  await page
    .getByRole('dialog', { name: 'Record form', exact: true })
    .waitFor();
  await page.waitForFunction(() =>
    document
      .querySelector('dialog[open]')
      ?.textContent.includes('Create record')
  );
  assert.equal(forms.at(-1).project, 'demo');
  assert.equal(forms.at(-1).search_type, 'demo/asset');
  assert.equal(forms.at(-1).view, 'insert');
  await page
    .getByRole('dialog', { name: 'Record form', exact: true })
    .getByRole('button', { name: 'Close', exact: true })
    .click();
  fileColumns = true;
  await child.locator('[data-frame="nestedReload"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].filterField ===
      'file_name'
  );
  await search.fill('reference.txt');
  const fileReads = reads;
  await search.press('Enter');
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.equal(reads, fileReads + 1);
  assert.equal(queries.at(-1).keyword, 'reference.txt');
  assert.equal(queries.at(-1).keyword_relation, 'EQI');
  await search.fill('');
  await search.press('Enter');
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.equal(queries.at(-1).keyword, '');
  await child.locator('[data-frame="nestedClose"]').click();
  await page.evaluate(() => window.nestedFixture.summary());
  await root.locator('[data-frame="tableSummary_0"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].scope
        .searchType === 'sthpw/task'
  );
  await root
    .locator('.nested-table [data-frame="nestedClose"]')
    .first()
    .click();
  await root.locator('[data-frame="tableSummary_1"]').click();
  await page.waitForFunction(
    () =>
      window.nestedFixture.state.children['demo/asset?code=A'].scope
        .searchType === 'sthpw/snapshot'
  );
  await child
    .locator('.handler-table-row[role=row] input[type=checkbox]')
    .waitFor();
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html?parent'
  );
  const panel = page.locator('.nested-table');
  await panel.waitFor();
  await page.waitForFunction(() => {
    const e = document.querySelector('.nested-table');
    return (
      e &&
      Math.abs(
        e.getBoundingClientRect().height -
          e
            .closest('.handler-table-detail')
            .parentElement.getBoundingClientRect().height
      ) < 1
    );
  });
  const readsBeforeResize = reads;
  for (const width of [800, 500, 1000]) {
    await page.setViewportSize({ width, height: 660 });
    await page.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r))
        )
    );
    const bounds = await panel.boundingBox();
    assert(bounds.height < 240);
    assert(
      Math.abs(
        (await panel.evaluate(
          (e) =>
            e
              .closest('.handler-table-detail')
              .parentElement.getBoundingClientRect().height
        )) - bounds.height
      ) < 1
    );
  }
  assert.equal(
    reads,
    readsBeforeResize,
    'Resizing must not reload nested data'
  );
  await page.evaluate(() => {
    const state = window.nestedFixture.state;
    state.rows = Array.from({ length: 4 }, (_, i) => ({
      ...state.rows[0],
      key: 'row-' + i,
      record: { ...state.rows[0].record, __search_key__: 'row-' + i }
    }));
    state.selected = ['row-1'];
  });
  for (const height of [660, 350, 660]) {
    await page.setViewportSize({ width: 1000, height });
    const expected = Math.min(387, height - 32 - 37 - 58);
    await page.waitForFunction((expected) => {
      const e = document.querySelector('.nested-table');
      return Math.abs(e.getBoundingClientRect().height - expected) < 1;
    }, expected);
    const actual = await panel.evaluate((e) => ({
      height: e.getBoundingClientRect().height,
      parent: e
        .closest('.handler-table-detail')
        .parentElement.getBoundingClientRect().height,
      list: e.querySelector('.handler-table').getBoundingClientRect().height
    }));
    assert.equal(actual.height, actual.parent);
    if (height === 660) assert(actual.list >= 4 * 58);
    assert.deepEqual(
      await page.evaluate(() => window.nestedFixture.state.selected),
      ['row-1']
    );
  }
  assert.equal(reads, readsBeforeResize);
  await panel.locator('[data-frame=nestedClose]').click();
  await panel.waitFor({ state: 'detached' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: nested table actual first-click expansion, independent selection, cycle guard and cached reopening'
  );
} finally {
  await browser.close();
  await server.close();
}
