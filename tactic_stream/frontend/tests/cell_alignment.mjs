import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import * as Cells from '../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import * as Services from '../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';

assert.equal(Cells.alignment({ justify: 'right', value_align: '' }), 'right');
assert.equal(
  Cells.alignment({ justify: 'right', value_align: 'left' }),
  'left'
);
assert.equal(
  Cells.alignment({ justify: 'right', value_align: 'left' }, false),
  'right'
);
assert.equal(
  Cells.alignment({ justify: 'right', value_align: 'left' }, true, ''),
  'right'
);
assert.equal(
  Cells.presentationOptions({}, { value_align: 'left' }).value_align,
  'left'
);
for (const width of [80, 240])
  for (const align of ['left', 'center', 'right']) {
    const scene = Services.describe(
      {
        text: '4 assets',
        displayOptions: { value_align: align },
        actions: [{ name: 'nested-table', icon: 'chevron-right' }]
      },
      width,
      58,
      'en'
    );
    const action = scene.nodes[0].children[0];
    assert.equal(action.x, Cells.contentX(width, action.width, align, 12));
    assert.ok(action.x >= 0 && action.x + action.width <= width);
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
let browser;
try {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({
    viewport: { width: 1050, height: 900 },
    hasTouch: true
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/align-fixture', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<div id="app"></div>' })
  );
  await page.goto(server.resolvedUrls.local[0] + 'align-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async (vueUrl) => {
      const { createApp, h, reactive } = await import(vueUrl);
      const { default: Table } = await import(
        '/frontend/src/features/interface/TableView.vue'
      );
      const { default: Cell } = await import(
        '/frontend/src/features/interface/TableCell.vue'
      );
      const { default: Frame } = await import(
        '/frontend/src/frame/FrameView.vue'
      );
      const Columns = await import(
        '/src/tactic_stream/shared_ui/features/administration/columns/columns.ui.mjs'
      );
      const State = await import(
        '/src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs'
      );
      const Editor = await import(
        '/frontend/src/features/administration/columnsEditor.js'
      );
      const { appearance, initializeAppearance } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      initializeAppearance();
      Object.assign(appearance, { theme: 'md3', mode: 'dark', language: 'en' });
      window.appearance = appearance;
      const source =
        '<config><!--keep--><table><element name="description" custom="keep"><display widget="format"><justify>right</justify></display></element></table></config>';
      const row = Editor.definitionWizard(source).elements[0];
      for (const value of ['left', 'center', 'right', '']) {
        const xml = Editor.changeDefinition(
          source,
          row.path,
          'valueAlign',
          value
        );
        if (
          !xml.includes('<!--keep-->') ||
          !xml.includes('custom="keep"') ||
          !xml.includes('<justify>right</justify>')
        )
          throw Error('Lost custom XML');
        if (Editor.definitionWizard(xml).elements[0].valueAlign !== value)
          throw Error('Lost alignment');
      }
      for (const value of ['justify', 'LEFT', 'left; color:red']) {
        let rejected = false;
        try {
          Editor.changeDefinition(source, row.path, 'valueAlign', value);
        } catch {
          rejected = true;
        }
        if (!rejected) throw Error('Invalid alignment accepted');
      }
      if (!row.xml.includes('<justify>right</justify>'))
        throw Error('Missing element XML');
      const editedXml = Editor.changeDefinition(
        source,
        row.path,
        'xml',
        '<element name="description" title="Custom Desc" width="220"><display class="tactic.ui.table.ExpressionElementWdg"><expression>@GET(.description)</expression></display></element>'
      );
      const editedRow = Editor.definitionWizard(editedXml).elements[0];
      if (
        editedRow.title !== 'Custom Desc' ||
        editedRow.width !== 220 ||
        editedRow.widget !== 'tactic.ui.table.ExpressionElementWdg' ||
        !editedRow.xml.includes('<expression>@GET(.description)</expression>')
      )
        throw Error('Element XML update failed');
      const exprOptions = Editor.widgetOptionsFor(editedRow.widget);
      if (
        exprOptions.length !== 21 ||
        !exprOptions.some(
          (item) =>
            item.value === 'tactic.ui.table.ExpressionElementWdg' &&
            item.label === 'Expression'
        ) ||
        exprOptions.some((item) => item.value === 'expression')
      )
        throw Error('Widget alias dedup failed');
      for (const badXml of [
        '',
        '<element/>',
        '<other name="x"/>',
        '<element name="x">broken'
      ]) {
        let rejected = false;
        try {
          Editor.changeDefinition(source, row.path, 'xml', badXml);
        } catch {
          rejected = true;
        }
        if (!rejected) throw Error('Invalid element XML accepted');
      }
      const columns = reactive(
        ['left', 'center', 'right'].map((align, i) => ({
          name: 'd' + i,
          field: 'd' + i,
          title: 'Description',
          width: 240,
          supported: true,
          attributes: { value_align: align },
          cell: { kind: 'text', field: 'd' + i }
        }))
      );
      const text =
        'Mechanical robot arm — an episode asset with a long description.';
      const records = [{ __search_key__: 'A', d0: text, d1: text, d2: text }];
      const state = reactive({
        align: 'center',
        events: [],
        xml: source,
        element: row
      });
      window.fixture = state;
      const ui = { ...State.initial(), editing: true, path: row.path };
      const model = {
        ready: true,
        canWrite: true,
        selected: { view: 'table', searchType: 'demo/asset' },
        typeOptions: [],
        definitions: [],
        records: [],
        elements: [state.element],
        element: state.element,
        wizard: { supported: true },
        widgetOptions: []
      };
      createApp({
        render: () =>
          h('main', [
            h(
              'div',
              {
                id: 'table',
                class: 'table-container',
                style: 'width:820px;height:170px;display:flex'
              },
              h(
                Table,
                {
                  columns,
                  groups: [{ key: 'records', records }],
                  selectedKeys: [],
                  selectable: false,
                  readOnly: true,
                  focusedKey: 'A',
                  state: {
                    table: {
                      rowHeight: 100,
                      automaticRowHeight: false,
                      autoFit: false,
                      scrollColumns: true
                    }
                  }
                },
                {
                  cell: ({ record, column, height }) =>
                    h(Cell, { element: column, record, height })
                }
              )
            ),
            h(
              'div',
              {
                id: 'decorated',
                class: 'handler-table',
                style: 'display:flex;width:720px;height:100px'
              },
              [
                ...['duration', 'related', 'preview'].map((name) =>
                  h(
                    'div',
                    {
                      id: name,
                      class: 'handler-table-cell',
                      'data-align': state.align,
                      style: 'width:240px;height:100px;padding:0'
                    },
                    h(Cell, {
                      element: {
                        name,
                        supported: true,
                        width: 240,
                        attributes: { value_align: state.align },
                        cell: {
                          kind:
                            name === 'related'
                              ? 'commands'
                              : name === 'preview'
                                ? 'thumbnail'
                                : 'text',
                          field: name
                        }
                      },
                      record: { name: 'Robot Arm' },
                      height: 100,
                      editable: true,
                      cell:
                        name === 'duration'
                          ? { text: '2 Minutes' }
                          : name === 'related'
                            ? {
                                text: '4 assets',
                                actions: [
                                  {
                                    name: 'nested-table',
                                    icon: 'chevron-right',
                                    label: 'Show related table'
                                  }
                                ]
                              }
                            : {},
                      onAction: (...args) => state.events.push(args),
                      onPreview: () => state.events.push(['preview'])
                    })
                  )
                )
              ]
            ),
            h(
              'div',
              {
                class: 'handler-table',
                style: 'width:240px;height:100px;background:var(--page)'
              },
              h(
                'div',
                {
                  id: 'plain-cell',
                  class: 'handler-table-cell',
                  'data-align': state.align,
                  style: 'width:240px;height:100px'
                },
                h(Cell, {
                  element: {
                    name: 'description',
                    field: 'description',
                    supported: true,
                    attributes: { value_align: state.align },
                    cell: { kind: 'text', field: 'description' }
                  },
                  record: { description: text },
                  height: 100
                })
              )
            ),
            h(Frame, {
              style: 'width:1000px;height:700px',
              models: { definitions: [], columns: [] },
              scene: Columns.describe(
                model,
                ui,
                1000,
                700,
                appearance.language
              ),
              onEvent: (action) => {
                if (action.type === 'field' && action.field === 'valueAlign') {
                  state.xml = Editor.changeDefinition(
                    state.xml,
                    row.path,
                    'valueAlign',
                    action.value
                  );
                  state.element.valueAlign = action.value;
                }
              }
            })
          ])
      }).mount('#app');
    },
    entry.code.match(/from "([^"]+)"/)[1]
  );
  const cells = page.locator('#table .handler-table-row .handler-table-cell');
  await cells.nth(2).waitFor();
  for (const [index, align] of ['left', 'center', 'right'].entries()) {
    assert.equal(
      await cells.nth(index).evaluate((el) => getComputedStyle(el).textAlign),
      align
    );
    assert.equal(
      await cells
        .nth(index)
        .locator('.table-cell-text')
        .evaluate((el) => getComputedStyle(el).textAlign),
      align
    );
  }
  assert.deepEqual(
    await page
      .locator('#table .handler-table-heading')
      .evaluateAll((nodes) => nodes.map((n) => getComputedStyle(n).textAlign)),
    ['center', 'center', 'center']
  );
  const positions = [];
  for (const align of ['left', 'center', 'right']) {
    await page.evaluate((align) => (window.fixture.align = align), align);
    await page.waitForTimeout(30);
    positions.push(
      await page
        .locator('#duration [data-frame=tableValueBadge]')
        .evaluate(
          (el) =>
            el.getBoundingClientRect().left -
            el.closest('#duration').getBoundingClientRect().left
        )
    );
    const action = page.locator('#related [data-frame=tableServiceAction_0]');
    await action.locator('[data-frame=tableServiceDisclosure]').tap();
  }
  assert.ok(positions[0] < positions[1] && positions[1] < positions[2]);
  assert.equal(await page.evaluate(() => window.fixture.events.length), 3);
  await page.locator('#preview button').click();
  assert.equal(
    await page.evaluate(() => window.fixture.events.at(-1)[0]),
    'preview'
  );
  const choice = page.locator('[data-frame=definitionCatalogValueAlign]');
  await choice.click();
  await page.getByRole('option', { name: 'Right', exact: true }).click();
  await page.waitForFunction(
    () => window.fixture.element.valueAlign === 'right'
  );
  assert.match(
    await page.evaluate(() => window.fixture.xml),
    /value_align="right"/
  );
  assert.match(
    await page
      .locator('[data-frame=definitionCatalogElementXml]')
      .inputValue(),
    /<justify>right<\/justify>/
  );
  if (process.env.CELL_ALIGNMENT_OUTPUT) {
    await mkdir(process.env.CELL_ALIGNMENT_OUTPUT, { recursive: true });
    for (const mode of ['dark', 'light']) {
      await page.evaluate((mode) => (window.appearance.mode = mode), mode);
      await page.waitForTimeout(150);
      await page.locator('#table').screenshot({
        path:
          process.env.CELL_ALIGNMENT_OUTPUT + '/browser-table-' + mode + '.png'
      });
      for (const align of ['left', 'center', 'right']) {
        await page.evaluate((align) => (window.fixture.align = align), align);
        await page.locator('#plain-cell').screenshot({
          path:
            process.env.CELL_ALIGNMENT_OUTPUT +
            '/browser-text-' +
            align +
            '-' +
            mode +
            '.png'
        });
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: actual content alignment, independent headings, badges/related actions, pointer/touch, XML validation and column setting'
  );
} finally {
  await browser?.close();
  await server.close();
}
