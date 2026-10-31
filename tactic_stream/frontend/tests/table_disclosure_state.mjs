import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as UI from '../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';

const scope = {
  searchType: 'demo/asset',
  view: 'history',
  parentKey: 'demo/asset?code=A'
};
const cell = {
  columnName: 'history',
  nestedTable: scope,
  actions: [{ name: 'nested-table', icon: 'chevron-right' }]
};
function icon(value, state) {
  return UI.describe(value, 100, 58, 'en', true, { __nested: state }).nodes[0]
    .children[0].icon;
}
const state = { column: 'history', scope, open: true, busy: false };
assert.equal(icon(cell, state), 'expand-more');
assert.equal(icon({ ...cell, columnName: 'copy' }, state), 'chevron-right');
assert.equal(
  icon({ ...cell, nestedTable: { ...scope, view: 'other' } }, state),
  'chevron-right'
);
assert.equal(
  icon(cell, { ...state, open: false, busy: true }),
  'chevron-right'
);
assert.equal(icon(cell, { ...state, busy: true }), 'loading');
for (const width of [80, 180, 320])
  for (const text of [
    '0 assets',
    '4 assets',
    '112 объектов',
    'A very long related object label'
  ]) {
    const scene = UI.describe({ ...cell, text }, width, 58, 'en');
    const action = scene.nodes[0].children[0];
    assert.equal(scene.nodes[0].children.length, 1);
    assert.equal(action.kind, 'Action');
    assert.equal(action.text, text);
    assert.ok(action.width <= width - 24);
    assert.equal(
      action.children.find((node) => node.kind === 'Icon').icon,
      'chevron-right'
    );
  }

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  publicDir: root + 'frontend/public',
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
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1000, height: 900 },
    hasTouch: true
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/rpc', (route) =>
    route.fulfill({
      json: {
        result: { info: { layout: { columns: [], rows: {} }, records: [] } }
      }
    })
  );
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_table/nested_recursive.html?disclosures'
  );
  const buttons = page.locator(
    '#app > .nested-table [data-frame="tableServiceAction_0"]'
  );
  await buttons
    .nth(5)
    .waitFor({ timeout: 5000 })
    .catch(async (error) => {
      console.error(errors, await page.locator('#app').innerText());
      throw error;
    });
  // Scope switching is a state check; the raised child intentionally blocks parent pointer input.
  const captures = [];
  const icons = async () => {
    const values = await buttons
      .locator('[data-icon]')
      .evaluateAll((items) => items.map((item) => item.dataset.icon));
    captures.push(values);
    return values;
  };
  assert.deepEqual(await icons(), Array(6).fill('chevron-right'));
  await buttons.nth(0).click();
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await page.evaluate(() => {
    window.nestedFixture.state.children['demo/asset?code=A'].busy = true;
  });
  assert.deepEqual(await icons(), [
    'loading',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await page.evaluate(() => {
    window.nestedFixture.state.children['demo/asset?code=A'].busy = false;
  });
  await buttons.nth(1).evaluate((el) => el.click());
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await buttons.nth(1).evaluate((el) => el.click());
  assert.deepEqual(await icons(), Array(6).fill('chevron-right'));
  await buttons.nth(2).evaluate((el) => el.click());
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=A'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'chevron-right',
    'expand-more',
    'chevron-right',
    'chevron-right',
    'chevron-right'
  ]);
  await buttons.nth(3).evaluate((el) => el.click());
  await page.waitForFunction(
    () => !window.nestedFixture.state.children['demo/asset?code=B'].busy
  );
  assert.deepEqual(await icons(), [
    'chevron-right',
    'chevron-right',
    'expand-more',
    'expand-more',
    'chevron-right',
    'chevron-right'
  ]);
  assert.deepEqual(errors, []);
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h, reactive, ref } = await import(vueUrl);
      const { default: Cell } = await import(
        '/frontend/src/features/interface/TableServiceCell.vue'
      );
      const host = document.createElement('div');
      document.body.append(host);
      host.id = 'combined-count';
      Object.assign(host.style, {
        position: 'fixed',
        zIndex: '10000',
        top: '100px',
        left: '100px',
        width: '180px',
        height: '58px',
        background: 'var(--page)'
      });
      const cell = {
        text: '4 assets',
        displayOptions: {
          icon: 'FAS_CUBE',
          label: '{@COUNT(demo/asset)} assets'
        },
        columnName: 'assets',
        nestedTable: {
          searchType: 'demo/asset',
          view: 'related',
          parentKey: 'A'
        },
        actions: [
          {
            name: 'nested-table',
            label: 'Show related table',
            icon: 'chevron-right'
          }
        ]
      };
      const fixture = (window.combinedCount = {
        events: [],
        editable: ref(true),
        nested: reactive({
          open: false,
          busy: false,
          column: 'assets',
          scope: cell.nestedTable
        })
      });
      createApp({
        render: () =>
          h(Cell, {
            cell,
            editable: fixture.editable.value,
            height: 58,
            nestedState: fixture.nested,
            onAction: (name, value) => {
              fixture.events.push([name, value.nestedTable]);
              fixture.nested.open = !fixture.nested.open;
            }
          })
      }).mount(host);
      const { default: ValueCell } = await import(
        '/frontend/src/features/interface/TableCell.vue'
      );
      const durationHost = document.createElement('div');
      document.body.append(durationHost);
      durationHost.id = 'duration-value';
      Object.assign(durationHost.style, {
        position: 'fixed',
        zIndex: '10000',
        top: '180px',
        left: '100px',
        width: '180px',
        height: '58px',
        background: 'var(--page)'
      });
      window.durationFixture = reactive({
        name: 'duration',
        attributes: {},
        cell: { kind: 'text', field: 'duration' },
        supported: true
      });
      createApp({
        render: () =>
          h(ValueCell, {
            element: window.durationFixture,
            record: {},
            cell: { text: '2 Minutes' },
            height: 64
          })
      }).mount(durationHost);
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  const combined = page.locator(
    '#combined-count [data-frame="tableServiceAction_0"]'
  );
  await combined.waitFor();
  assert.equal(await page.locator('#combined-count button').count(), 1);
  assert.equal(
    await combined.locator('[data-frame="tableServiceValue"]').innerText(),
    'Assets 4'
  );
  for (const id of [
    'tableServiceLeadingIcon',
    'tableServiceValue',
    'tableServiceDisclosure'
  ]) {
    const box = await page
      .locator('#combined-count [data-frame="' + id + '"]')
      .boundingBox();
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  }
  assert.equal(
    (await page.evaluate(() => window.combinedCount.events)).length,
    3
  );
  assert.deepEqual(await page.evaluate(() => window.combinedCount.events[0]), [
    'nested-table',
    { searchType: 'demo/asset', view: 'related', parentKey: 'A' }
  ]);
  await combined.focus();
  await page.keyboard.press('Space');
  await page.keyboard.press('Enter');
  await combined.tap();
  assert.equal(
    (await page.evaluate(() => window.combinedCount.events)).length,
    6
  );
  await page.evaluate(() => {
    window.combinedCount.nested.open = true;
    window.combinedCount.nested.busy = true;
  });
  await page.locator('#combined-count [data-icon="loading"]').waitFor();
  await page.evaluate(() => {
    window.combinedCount.editable.value = false;
  });
  await page.waitForFunction(
    () => document.querySelector('#combined-count button').disabled
  );
  const box = await combined.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  assert.equal(
    (await page.evaluate(() => window.combinedCount.events)).length,
    6
  );
  assert.deepEqual(errors, []);
  const duration = page.locator('#duration-value');
  await duration.locator('[data-frame="tableValueLabel"]').waitFor();
  assert.equal(
    await duration.locator('[data-frame="tableValueLabel"]').innerText(),
    '2 Minutes'
  );
  assert.equal(await duration.locator('[data-icon="clock"]').count(), 1);
  assert.equal(await duration.locator('button').count(), 0);
  await duration.evaluate((el) => {
    el.style.width = '80px';
  });
  await page.waitForFunction(
    () =>
      document
        .querySelector('#duration-value [data-frame="tableValueBadge"]')
        .getBoundingClientRect().width <= 80
  );
  const bounds = await duration.boundingBox(),
    badge = await duration
      .locator('[data-frame="tableValueBadge"]')
      .boundingBox();
  assert.ok(
    badge.x >= bounds.x && badge.x + badge.width <= bounds.x + bounds.width
  );
  await duration.evaluate((el) => {
    el.style.width = '180px';
  });
  const xmlProof = await page.evaluate(async () => {
    const { definitionWizard, changeDefinition } = await import(
      '/frontend/src/features/administration/columnsEditor.js'
    );
    let source =
      '<config><!--keep--><table><element name="duration" custom="keep"><display widget="hidden_row"><icon>FAS_CUBE</icon><option>keep</option></display></element></table></config>';
    let row = definitionWizard(source).elements[0];
    const inherited = row.valueIcon;
    for (const [field, value] of [
      ['valueIcon', 'FAS_CLOCK'],
      ['valueStyle', 'badge']
    ])
      source = changeDefinition(source, row.path, field, value);
    row = definitionWizard(source).elements[0];
    let rejected = 0;
    for (const [field, value] of [
      ['valueIcon', '<script>'],
      ['valueStyle', 'unknown']
    ]) {
      try {
        changeDefinition(source, row.path, field, value);
      } catch {
        rejected++;
      }
    }
    return {
      inherited,
      icon: row.valueIcon,
      style: row.valueStyle,
      source,
      rejected
    };
  });
  assert.equal(xmlProof.inherited, 'FAS_CUBE');
  assert.equal(xmlProof.icon, 'FAS_CLOCK');
  assert.equal(xmlProof.style, 'badge');
  assert.equal(xmlProof.rejected, 2);
  assert.ok(
    xmlProof.source.includes('<!--keep-->') &&
      xmlProof.source.includes('custom="keep"') &&
      xmlProof.source.includes('<option>keep</option>')
  );
  if (process.env.TABLE_DISCLOSURE_OUTPUT) {
    mkdirSync(process.env.TABLE_DISCLOSURE_OUTPUT, { recursive: true });
    await page.evaluate(() => {
      window.combinedCount.editable.value = true;
      window.combinedCount.nested.open = false;
      window.combinedCount.nested.busy = false;
    });
    await page.mouse.move(0, 0);
    await page.locator('#combined-count').screenshot({
      path: process.env.TABLE_DISCLOSURE_OUTPUT + '/browser-count-button.png'
    });
    await duration.screenshot({
      path: process.env.TABLE_DISCLOSURE_OUTPUT + '/browser-duration.png'
    });
    writeFileSync(
      process.env.TABLE_DISCLOSURE_OUTPUT + '/browser.json',
      JSON.stringify(captures)
    );
  }
  console.log(
    'PASS: disclosure and loading icons follow only the active row, column and nested scope'
  );
} finally {
  await browser.close();
  await server.close();
}
