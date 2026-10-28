import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url)),
  reference = root + '/../tools/frame_table/fixtures',
  report = root + '/../tools/frame_table/output/legacy-driver';
const fixture = JSON.parse(
  await readFile(reference + '/comparison_scene.json', 'utf8')
);
const native = JSON.parse(
  await readFile(reference + '/native_table_metrics.json', 'utf8')
);
let configuration = structuredClone(fixture.configuration),
  definition = structuredClone(fixture.definition),
  cells = structuredClone(fixture.cells);
let catalog = {
  records: [
    {
      identity: '1',
      row: 0,
      id: 1,
      view: 'table',
      searchType: 'cg/assets',
      login: '',
      code: 'TABLE_FIXTURE',
      config: configuration.sources[0].xml
    }
  ],
  searchTypes: [{ value: 'cg/assets', label: 'Assets · cg/assets' }],
  revision: 'catalog-r1'
};
const configurations = new Map([['table', configuration]]);
const requests = [],
  errors = [],
  writes = [];
let stale = false;
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';import ObjectOperations from '/src/features/objects/ObjectOperations.vue';import ConfiguredView from '/src/features/interface/ConfiguredView.vue';import ColumnsEditor from '/src/features/administration/ColumnsEditor.vue';import {windowDirective} from '/src/controls/window.js';import {appearance,initializeAppearance} from '/src/appearance.js';import {tooltipDirective} from '/src/controls/tooltip.js';import '/src/theme.css';import '/src/style.css'
Object.assign(appearance,{language:'en',theme:'md3',mode:'dark',palette:'default',accent:'default',hoverAnimations:false,clickAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance()
const source=${JSON.stringify(fixture)}
createApp({data(){return {page:'table',definition:source.definition,rows:source.records,selected:[source.records[2].__search_key__],state:{},events:[],sortField:'name',sortDirection:'asc',ticket:'fixture',focus:null}},mounted(){window.host=this;window.appearance=appearance},methods:{select(rows,value){const set=new Set(this.selected);for(const r of rows)value?set.add(r.__search_key__):set.delete(r.__search_key__);this.selected=[...set]},saved(result){if(result?.records){const map=new Map(result.records.map(r=>[r.__search_key__,r]));this.rows=this.rows.map(r=>map.get(r.__search_key__)||r)}this.events.push({kind:'saved',result})}},render(){return h('main',{id:'frame',class:this.page==='editor'?'administration-shell':''},[
h(ObjectOperations,{ref:'rowMenu',project:'table_fixture',operations:{edit:true}}),
this.page==='table'?h(ConfiguredView,{ref:'table',definition:this.definition,rows:this.rows,readOnly:false,ticket:this.ticket,project:'table_fixture',resultMode:'table',selectedKeys:this.selected,resultState:this.state,accent:source.accent,sortField:this.sortField,sortDirection:this.sortDirection,onSelect:this.select,onSaved:this.saved,onOperate:(record,event)=>this.$refs.rowMenu.open(record,event,{branch:{kind:'file'}}),onInspect:r=>this.events.push({kind:'inspect',key:r.__search_key__}),onColumn:scope=>this.events.push({kind:'column',scope}),onSort:(field,direction)=>{this.sortField=field;this.sortDirection=direction;this.events.push({kind:'sort',field,direction})},onResultState:s=>this.state=s}):h(ColumnsEditor,{ref:'editor',ticket:this.ticket,project:'table_fixture',presentationVisible:false,initialFocus:this.focus,onSaved:r=>this.events.push({kind:'definition-saved',result:r})})
])}}).provide('openHelp',()=>{}).provide('openTableCheckin',(record,cell,project)=>window.host.events.push({kind:'drop-plate',key:record.__search_key__,process:cell.process,context:cell.context,project})).provide('openTaskInspector',(record,cell,process,key,scope)=>{window.host.events.push({kind:'inspector',record:record.__search_key__,process,key,scope:{project:scope.project,searchType:scope.searchType}});return true}).directive('window',windowDirective).directive('tooltip',tooltipDirective).mount('#app')
</script><style>html,body,#app{width:100%;height:100%;overflow:hidden}#frame{width:100%;height:100%;background:var(--page)}#frame>.configured-view{display:flex;flex-direction:column;height:100%;width:100%;overflow:hidden}#frame>.columns-editor{height:100%;padding:0;gap:0}#frame>.columns-editor>.columns-editor-layout{height:100%;margin:0}#frame .administration-save-bar{display:none}</style></body></html>`;
let server, browser;
const measurements = [];
async function taskPreviewGeometry(popup, height, narrow = false) {
  const result = await popup.evaluate((el) => {
    const cards = el.firstElementChild,
      style = getComputedStyle(cards);
    return {
      width: el.clientWidth,
      scrollWidth: el.scrollWidth,
      height: el.clientHeight,
      scrollHeight: el.scrollHeight,
      box: el.getBoundingClientRect().toJSON(),
      inner: {
        width: cards.clientWidth,
        scrollWidth: cards.scrollWidth,
        height: cards.clientHeight,
        scrollHeight: cards.scrollHeight
      },
      cards: cards.getBoundingClientRect().toJSON(),
      gap: style.gap,
      overflow: style.overflow,
      items: [...cards.children].map((card) =>
        card.getBoundingClientRect().toJSON()
      )
    };
  });
  const details = JSON.stringify(result);
  assert.equal(result.items.length, 4, details);
  assert.equal(result.gap, '4px', details);
  assert.equal(result.overflow, 'visible', details);
  assert.equal(result.inner.width, 440, details);
  assert.equal(result.inner.scrollWidth, result.inner.width, details);
  assert.equal(result.inner.height, height, details);
  assert.equal(result.inner.scrollHeight, height, details);
  assert.equal(result.scrollHeight, result.height, details);
  for (const card of result.items) {
    assert.equal(card.width, 107, details);
    assert.equal(card.height, height - 2, details);
    assert(
      card.top >= result.cards.top && card.bottom <= result.cards.bottom,
      details
    );
  }
  if (narrow) assert(result.scrollWidth > result.width, details);
  else {
    assert.equal(result.scrollWidth, result.width, details);
    assert.equal(result.box.width, 456, details);
    assert.equal(result.box.height, height + 16, details);
  }
  return result;
}
const deadline = setTimeout(() => browser?.close(), 120000);
try {
  server = await createServer({
    root,
    configFile: false,
    cacheDir: root + '/node_modules/.vite/handler-table',
    plugins: [
      vue(),
      {
        name: 'handler-table-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            try {
              if (req.url === '/table-fixture') {
                res.setHeader('Content-Type', 'text/html');
                res.end(await server.transformIndexHtml(req.url, html));
                return;
              }
              if (!req.url?.startsWith('/admin/')) return next();
              let raw = '';
              for await (const chunk of req) raw += chunk;
              const data = JSON.parse(raw || '{}');
              requests.push({ path: req.url, data });
              let result;
              if (req.url === '/admin/table-cells') {
                assert(data.search_keys.length <= 500);
                result = Object.fromEntries(
                  data.search_keys.map((key) => [key, cells[key] || {}])
                );
              } else if (req.url === '/admin/widget-configuration/read')
                result = configurations.get(data.view) || {
                  ...configuration,
                  view: data.view,
                  revision: 'empty-' + data.view,
                  sources: []
                };
              else if (req.url === '/admin/widget-configuration/save') {
                if (stale) {
                  res.statusCode = 409;
                  res.setHeader('Content-Type', 'application/json');
                  res.end(
                    JSON.stringify({
                      error:
                        'Interface configuration changed. Reload before saving.'
                    })
                  );
                  return;
                }
                const previous = configurations.get(data.view);
                assert.equal(
                  data.revision,
                  previous?.revision || 'empty-' + data.view
                );
                writes.push(data);
                configuration = {
                  ...configuration,
                  view: data.view,
                  revision: 'r' + writes.length,
                  sources: [
                    {
                      ...configuration.sources[0],
                      id: previous?.sources[0].id || 2,
                      xml: data.xml
                    }
                  ]
                };
                configurations.set(data.view, configuration);
                configuration.table_views = [...configurations.keys()].map(
                  (view) => ({ view, title: view, current: view === data.view })
                );
                result = configuration;
              } else if (req.url === '/admin/interface') {
                const stored = configurations.get(data.view);
                result = stored
                  ? await page.evaluate(
                      ({ xml, view, source }) => {
                        const document = new DOMParser().parseFromString(
                            xml,
                            'application/xml'
                          ),
                          node =
                            document.documentElement.tagName === view
                              ? document.documentElement
                              : [...document.documentElement.children].find(
                                  (node) => node.tagName === view
                                );
                        if (!node) throw Error('Missing stored view');
                        const elements = [...node.children]
                          .filter((node) => node.tagName === 'element')
                          .map((node) => ({
                            ...structuredClone(
                              source.table.elements.find(
                                (element) =>
                                  element.name === node.getAttribute('name')
                              )
                            ),
                            attributes: Object.fromEntries(
                              [...node.attributes]
                                .filter(
                                  (attr) =>
                                    !['name', 'title'].includes(attr.name)
                                )
                                .map((attr) => [attr.name, attr.value])
                            ),
                            title:
                              node.getAttribute('title') ||
                              source.table.elements.find(
                                (element) =>
                                  element.name === node.getAttribute('name')
                              ).title
                          }));
                        return {
                          ...source,
                          table: { ...source.table, view, elements }
                        };
                      },
                      {
                        xml: stored.sources[0].xml,
                        view: data.view,
                        source: fixture.definition
                      }
                    )
                  : definition;
              } else if (req.url === '/admin/columns-editor/read')
                result = catalog;
              else if (req.url === '/admin/columns-editor/save') {
                assert.equal(data.revision, catalog.revision);
                catalog = {
                  ...catalog,
                  revision: 'catalog-r2',
                  records: [{ ...catalog.records[0], config: data.xml }],
                  selected: '1'
                };
                result = catalog;
                writes.push(data);
              } else if (req.url === '/admin/rpc') {
                if (data.method === 'log') {
                  res.setHeader('Content-Type', 'application/json');
                  res.end(JSON.stringify({ result: null }));
                  return;
                }
                assert.equal(data.method, 'execute_cmd');
                const command = data.args[1],
                  args = data.args[2];
                if (command === 'tactic.ui.table.table_edit.TableCellEditCmd') {
                  const source = structuredClone(fixture.editors[args.column]);
                  assert(source);
                  source.plans = source.plans.filter((plan) =>
                    args.search_keys.includes(plan.search_key)
                  );
                  if (!args.action || args.action === 'prepare')
                    result = { info: source };
                  else if (args.action === 'check')
                    result = { info: { state: 'saved' } };
                  else {
                    assert.equal(args.action, 'save');
                    assert.equal(args.plans.length, source.plans.length);
                    writes.push(args);
                    const field =
                      source.field.action.options.column ||
                      source.field.options.column ||
                      source.field.name;
                    result = {
                      info: {
                        records: fixture.records
                          .filter((r) =>
                            args.search_keys.includes(r.__search_key__)
                          )
                          .map((r) => ({ ...r, [field]: args.value }))
                      }
                    };
                  }
                } else if (
                  command === 'tactic.ui.table.task_inspector.TaskTableEditCmd'
                ) {
                  if (!args.action || args.action === 'prepare') {
                    const plan = structuredClone(fixture.task_editor);
                    plan.plans = plan.plans.filter((p) =>
                      args.search_keys.includes(p.search_key)
                    );
                    result = { info: plan };
                  } else {
                    assert.equal(args.action, 'save');
                    writes.push(args);
                    result = { info: { tasks: [] } };
                  }
                } else if (command === 'tactic.ui.table.NestedTableReadCmd') {
                  assert.equal(args.search_type, 'cg/assets');
                  assert.equal(
                    args.parent_key,
                    fixture.records[0].__search_key__
                  );
                  const childDefinition = structuredClone(fixture.definition);
                  childDefinition.table.elements =
                    childDefinition.table.elements.filter((column) =>
                      ['name', 'description'].includes(column.name)
                    );
                  const records = fixture.records.slice(0, 2);
                  result = {
                    info: {
                      definition: childDefinition,
                      records,
                      hasNext: false,
                      cells: Object.fromEntries(
                        records.map((row) => [
                          row.__search_key__,
                          fixture.cells[row.__search_key__]
                        ])
                      )
                    }
                  };
                } else throw Error('Unexpected command ' + command);
              } else throw Error('Unexpected endpoint ' + req.url);
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ result }));
            } catch (error) {
              errors.push(String(error.stack));
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: error.message }));
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
    channel: process.env.STREAM_BROWSER_CHANNEL,
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1496, height: 660 }
  });
  page.setDefaultTimeout(10000);
  page.on('pageerror', (error) => errors.push(error.stack));
  await page.goto(server.resolvedUrls.local[0] + 'table-fixture');
  await page.waitForFunction(
    () =>
      window.host?.$refs.table &&
      Object.keys(window.host.$refs.table.cells).length === 5
  );
  await page.evaluate(() => document.fonts.ready);
  const table = page.locator('.handler-table'),
    rows = table.locator('.handler-table-row'),
    headings = table.locator('.handler-table-heading');
  assert.equal(await headings.count(), 10);
  assert.equal(await rows.count(), 5);
  assert.equal(
    await page.getByText('Widget unavailable', { exact: true }).count(),
    0
  );
  assert.equal(await table.evaluate(el => getComputedStyle(el).margin), '0px');
  assert.equal(await table.locator('.handler-table-header').evaluate(el => getComputedStyle(el).borderRadius), '0px');
  const header = await table.locator('.handler-table-header').boundingBox(),
    first = await rows.first().boundingBox(),
    preview = await rows.first().locator('.item-preview').first().boundingBox();
  const sample = native.captures.find(
    (c) => c.kind === 'table' && c.mode === 'dark'
  );
  const refHeader = sample.items.find((i) => i.name === 'tableHeaderSurface'),
    refRow = sample.items.find((i) => i.name === 'searchResultTableRow'),
    refPreview = sample.items.find((i) => i.name === 'tableCellPreview');
  assert(
    Math.abs(header.width - await table.evaluate(el => el.clientWidth)) < 0.6,
    JSON.stringify({
      header,
      refHeader,
      table: await table.boundingBox(),
      style: await table.evaluate((el) => ({
        overflow: getComputedStyle(el).overflow,
        clientWidth: el.clientWidth,
        scrollbar: getComputedStyle(el).scrollbarWidth
      }))
    })
  );
  assert.equal(header.height, 37);
  assert.equal(await table.locator('.handler-table-header').evaluate(el => getComputedStyle(el).borderBottomWidth), '0px');
  assert.equal(await table.evaluate(el => getComputedStyle(el).paddingRight), '0px');
  assert.equal(await table.evaluate(el => getComputedStyle(el).scrollbarGutter), 'auto');
  assert.equal(await table.evaluate(el => el.offsetWidth - el.clientWidth), 0);
  await page.setViewportSize({width: 1496, height: 160});
  await page.waitForFunction(() => {const el = document.querySelector('.handler-table'); return el.offsetWidth > el.clientWidth;});
  await page.setViewportSize({width: 1496, height: 660});
  await page.waitForFunction(() => {const el = document.querySelector('.handler-table'); return el.offsetWidth === el.clientWidth;});
  assert.equal(first.height, refRow.height);
  assert.equal(preview.width, refPreview.width);
  const card = await rows.first().locator('.task-card').first().boundingBox();
  assert.equal(card.width, 107);
  assert.equal(card.height, 50);
  for (const mode of ['dark', 'light']) {
    await page.evaluate((mode) => (window.appearance.mode = mode), mode);
    await page.screenshot({ path: report + '/table-stream-' + mode + '.png' });
    measurements.push({ kind: 'table', mode, header, first, preview });
  }
  await page.evaluate(() => (window.appearance.mode = 'dark'));
  // Context and overflow share the real object menu without a dimmed backdrop.
  for (const viewport of [{width:1496,height:660}, {width:320,height:660}]) {
    await page.setViewportSize(viewport);
    for (const method of ['context', 'overflow']) {
      if (method === 'context') await rows.first().click({button:'right', position:{x:100,y:20}});
      else await rows.first().locator('.handler-table-actions button').click();
      const menu = page.locator('.object-operations > dialog[open]');
      await menu.waitFor();
      assert.equal(await menu.evaluate(el => getComputedStyle(el, '::backdrop').backgroundColor), 'rgba(0, 0, 0, 0)');
      await page.keyboard.press('Escape');
      await menu.waitFor({state:'hidden'});
    }
  }
  await page.setViewportSize({width:1496,height:660});
  // Hovering any selected task cell previews every selected row, as in Handler.
  await page.evaluate(
    (keys) => (window.host.selected = keys),
    fixture.records.slice(0, 2).map((row) => row.__search_key__)
  );
  await rows.first().locator('.table-task-cell').hover();
  await page.waitForFunction(
    () => document.querySelectorAll('.task-preview:popover-open').length === 2
  );
  const taskPopup = page.locator('.task-preview:popover-open').first();
  for (const mode of ['dark', 'light']) {
    await page.evaluate((mode) => (window.appearance.mode = mode), mode);
    const geometry = await taskPreviewGeometry(taskPopup, 52),
      source = native.captures.find(
        (c) => c.kind === 'task-preview' && c.mode === mode
      );
    assert.equal(geometry.box.width, source.popups[0].width);
    assert.equal(geometry.box.height, source.popups[0].height);
    await page.screenshot({
      path: report + '/task-preview-stream-' + mode + '.png'
    });
    measurements.push({ kind: 'task-preview', mode, geometry });
  }
  await page.evaluate(() => (window.appearance.mode = 'dark'));
  await page.mouse.move(10, 600);
  await page.waitForFunction(
    () => !document.querySelector('.task-preview:popover-open')
  );
  // Both CSS load orders and scaled pixels must keep the full card row, with one horizontal scroller only when needed.
  for (const sample of [
    { width: 1496, height: 58, scale: 1.25, mode: 'dark', language: 'ru' },
    { width: 1496, height: 84, scale: 1.5, mode: 'light', language: 'ru' },
    {
      width: 320,
      height: 84,
      scale: 1,
      mode: 'dark',
      language: 'ru',
      narrow: true
    }
  ]) {
    const check = await browser.newPage({
      viewport: { width: sample.width, height: 660 },
      deviceScaleFactor: sample.scale
    });
    check.on('pageerror', (error) => errors.push(error.stack));
    await check.goto(server.resolvedUrls.local[0] + 'table-fixture');
    await check.waitForFunction(
      () => Object.keys(window.host?.$refs.table.cells || {}).length === 5
    );
    await check.evaluate((sample) => {
      Object.assign(window.appearance, {
        mode: sample.mode,
        language: sample.language
      });
      window.host.state = { table: { rowHeight: sample.height } };
      for (const element of window.host.definition.table.elements)
        element.attributes.th_hide_order = '0';
      // Production loads feature styles after the application stylesheet.
      for (const style of document.querySelectorAll('style[data-vite-dev-id]'))
        if (
          style.dataset.viteDevId.endsWith(
            'TaskCards.vue?vue&type=style&index=0&lang.css'
          )
        )
          document.head.append(style);
    }, sample);
    const cell = check.locator('.table-task-cell').first();
    await cell.scrollIntoViewIfNeeded();
    await cell.hover();
    const preview = check.locator('.task-preview:popover-open').first();
    await preview.waitFor({ state: 'visible' });
    const geometry = await taskPreviewGeometry(
      preview,
      sample.height - 6,
      sample.narrow
    );
    if (sample.narrow) {
      await preview.evaluate((el) => (el.scrollLeft = el.scrollWidth));
      await check.waitForFunction(
        () =>
          document.querySelector('.task-preview:popover-open')?.scrollLeft > 0
      );
      await preview.locator('.task-card-heading').last().click();
      assert.equal(
        (await check.evaluate(() => window.host.events)).at(-1).kind,
        'inspector'
      );
    } else {
      await check.keyboard.press('Escape');
      await check.waitForFunction(
        () => !document.querySelector('.task-preview:popover-open')
      );
    }
    measurements.push({ kind: 'task-preview', ...sample, geometry });
    await check.close();
  }
  const touch = await browser.newPage({
    viewport: { width: 1496, height: 660 },
    hasTouch: true
  });
  await touch.goto(server.resolvedUrls.local[0] + 'table-fixture');
  await touch.waitForFunction(
    () => Object.keys(window.host?.$refs.table.cells || {}).length === 5
  );
  await touch
    .locator('.table-task-cell')
    .first()
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  assert.equal(
    (await touch.evaluate(() => window.host.events)).at(-1).kind,
    'inspector'
  );
  await touch.close();
  await page.evaluate(
    (keys) => (window.host.selected = keys),
    [fixture.records[2].__search_key__]
  );
  await rows
    .first()
    .getByRole('button', { name: 'Open details', exact: true })
    .click();
  assert.equal(
    (await page.evaluate(() => window.host.events)).at(-1).kind,
    'inspect'
  );
  await rows.first().locator('.table-note-chip').click();
  assert.equal(
    (await page.evaluate(() => window.host.events)).at(-1).kind,
    'inspector'
  );
  await rows
    .first()
    .getByRole('button', { name: 'Check-in', exact: true })
    .click();
  await page.waitForFunction(
    () => window.host.events.at(-1).kind === 'drop-plate'
  );
  assert.equal(
    (await page.evaluate(() => window.host.events)).at(-1).process,
    'publish'
  );
  await headings.nth(1).click({ button: 'right' });
  await page
    .getByRole('menuitemradio', { name: 'Sort Z to A', exact: true })
    .click();
  assert.equal(await page.evaluate(() => window.host.sortDirection), 'desc');
  await headings.nth(8).click({ button: 'right' });
  await page
    .getByRole('menuitemradio', { name: 'Group by this column', exact: true })
    .click();
  assert.equal(await table.locator('.group-row').count(), 3);
  await headings.nth(8).click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Remove grouping', exact: true })
    .click();
  await table.getByLabel('Table views and columns', { exact: true }).click();
  await page
    .getByRole('button', { name: 'Configure columns', exact: true })
    .click();
  assert.equal(
    (await page.evaluate(() => window.host.events)).at(-1).scope.searchType,
    'cg/assets'
  );
  await table.getByLabel('Auto Fit columns', { exact: true }).click();
  assert.equal(
    await page.evaluate(() => window.host.state.table.autoFit),
    true
  );
  await table.getByLabel('Auto Fit columns', { exact: true }).click();
  // Plain clicks focus rows; Shift and checkboxes explicitly select them.
  await page.evaluate(() => window.host.selected = []);
  await rows.first().locator('.handler-table-cell').nth(1).click();
  assert.deepEqual(await page.evaluate(() => window.host.selected), []);
  assert(await rows.first().evaluate(el => el.classList.contains('active')));
  assert.equal(await rows.first().getAttribute('aria-selected'), 'true');
  assert.equal(await rows.first().locator('input[type=checkbox]').isChecked(), false);
  await rows.nth(1).locator('.handler-table-cell').nth(1).click({modifiers: ['Shift']});
  assert.deepEqual(await page.evaluate(() => window.host.selected), fixture.records.slice(0, 2).map(r => r.__search_key__));
  await rows.nth(2).locator('.handler-table-cell').nth(1).click();
  assert.equal((await page.evaluate(() => window.host.selected)).length, 2);
  await table.focus();
  await page.keyboard.press('ArrowDown');
  assert.equal((await page.evaluate(() => window.host.selected)).length, 2);
  await rows.first().locator('.handler-table-cell').nth(1).dblclick();
  const inline = page.locator('.table-inline-editor:popover-open');
  await inline.getByRole('textbox').fill('Edited robot');
  assert.equal(await inline.locator('footer').count(), 0);
  await inline.getByRole('textbox').press('Enter');
  await page.waitForFunction(() => !window.host.$refs.table.cellEditor);
  assert.equal(
    await page.evaluate(() => window.host.rows[0].name),
    'Edited robot'
  );
  assert.equal(writes.at(-1).column, 'name');
  await rows.first().locator('.handler-table-cell').nth(2).dblclick();
  await inline.getByRole('textbox').fill('Full description');
  await inline.getByRole('button', { name: 'Cancel', exact: true }).click();
  assert.equal(
    await page.evaluate(() => window.host.rows[0].description),
    fixture.records[0].description
  );
  await rows.first().locator('.handler-table-cell').nth(8).dblclick();
  await inline.getByRole('combobox').selectOption('PROP');
  await page.waitForFunction(() => !window.host.$refs.table.cellEditor);
  assert.equal(
    await page.evaluate(() => window.host.rows[0].assets_category_code),
    'PROP'
  );
  const taskEditor = page.locator('.task-table-editor:popover-open');
  await rows
    .first()
    .getByRole('button', { name: 'Edit task status', exact: true })
    .first()
    .click();
  const status = taskEditor.locator('select'),
    unsetStatus = status.locator('option').first();
  assert.equal(await unsetStatus.textContent(), 'Select status');
  assert.equal(await unsetStatus.getAttribute('value'), '');
  assert.equal(
    await unsetStatus.evaluate((el) => el.disabled),
    true,
    await unsetStatus.evaluate((el) => el.outerHTML)
  );
  assert.equal(await status.inputValue(), '');
  assert.equal(
    await page.evaluate(() => window.host.$refs.table.dirtyTaskCount),
    0
  );
  await page.evaluate(() => (window.appearance.language = 'ru'));
  assert.equal(await unsetStatus.textContent(), 'Выберите статус');
  assert.equal(await status.inputValue(), '');
  await page.evaluate(() => (window.appearance.language = 'en'));
  await page.keyboard.press('Escape');
  await taskEditor.waitFor({ state: 'hidden' });
  await rows
    .first()
    .getByRole('button', { name: 'Edit task status', exact: true })
    .first()
    .click();
  await status.selectOption('Waiting');
  await page
    .getByRole('region', { name: 'Pending task changes', exact: true })
    .waitFor();
  assert(
    Object.values(
      await page.evaluate(() => window.host.$refs.table.taskDrafts)
    ).every((draft) => draft.data.status === 'Waiting')
  );
  await page.getByLabel('Save task changes', { exact: true }).click();
  await page.waitForFunction(
    () =>
      !window.host.$refs.table.taskBusy &&
      !window.host.$refs.table.dirtyTaskCount
  );
  assert.equal(writes.at(-1).action, 'save');
  await rows
    .first()
    .getByRole('button', { name: 'Edit task assignee', exact: true })
    .first()
    .click();
  await taskEditor
    .locator('.user-combo-option')
    .filter({ hasText: 'Not assigned' })
    .click();
  await page
    .getByRole('region', { name: 'Pending task changes', exact: true })
    .waitFor();
  await page.getByLabel('Save task changes', { exact: true }).click();
  await page.waitForFunction(
    () =>
      !window.host.$refs.table.taskBusy &&
      !window.host.$refs.table.dirtyTaskCount
  );
  // Width/order/hide/view mutations preserve authoritative XML and reload the typed descriptor.
  await table
    .getByRole('slider', { name: 'Resize column Name', exact: true })
    .press('ArrowRight');
  await page.waitForFunction(() => !window.host.$refs.table.columnBusy);
  assert.match(writes.at(-1).xml, /name="name"[^>]*width="153"/);
  await table
    .getByRole('columnheader', { name: 'Name', exact: true })
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Move column right', exact: true })
    .click();
  await page.waitForFunction(() => !window.host.$refs.table.columnBusy);
  assert(
    writes.at(-1).xml.indexOf('name="description"') <
      writes.at(-1).xml.indexOf('name="name"'),
    JSON.stringify({
      write: writes.at(-1),
      errors: await page.locator('[role="alert"]').allTextContents()
    })
  );
  await table
    .getByRole('columnheader', { name: 'Keywords', exact: true })
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Remove Column', exact: true })
    .click();
  await page.waitForFunction(() => !window.host.$refs.table.columnBusy);
  assert.equal(await headings.count(), 9);
  assert.match(writes.at(-1).xml, /name="keywords"[^>]*hidden="true"/);
  await table.getByLabel('Table views and columns', { exact: true }).click();
  await page
    .getByRole('button', { name: 'Save current as new view…', exact: true })
    .click();
  const saveView = page.getByRole('dialog', {
    name: 'Save table view',
    exact: true
  });
  await saveView.getByRole('textbox').fill('Review assets');
  await saveView.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(() => !window.host.$refs.table.columnBusy);
  assert.equal(writes.at(-1).view, 'th_table_review_assets');
  assert.match(writes.at(-1).xml, /th_table_view_title="Review assets"/);
  stale = true;
  await table
    .getByRole('slider', { name: 'Resize column Name', exact: true })
    .press('ArrowRight');
  await page
    .getByText('Interface configuration changed. Reload before saving.', {
      exact: true
    })
    .waitFor();
  stale = false;
  await page
    .getByRole('button', { name: 'Reload from server', exact: true })
    .click();
  await page.waitForFunction(
    () =>
      !window.host.$refs.table.columnBusy &&
      !window.host.$refs.table.columnError
  );
  // A long result set mounts only the visible window and restores its position.
  await page.evaluate((source) => {
    window.host.rows = Array.from({ length: 1000 }, (_, i) => ({
      ...source[0],
      id: i,
      code: 'VIRTUAL_' + i,
      name: 'Virtual ' + i,
      __search_key__: 'cg/assets?project=table_fixture&code=VIRTUAL_' + i
    }));
    window.host.$refs.table.cells = {};
  }, fixture.records);
  assert((await rows.count()) < 25);
  await table.evaluate((el) => (el.scrollTop = 20000));
  await page.waitForFunction(() => window.host.state.table.scrollTop > 10000);
  assert((await rows.count()) < 25);
  await page.evaluate((source) => {
    window.host.rows = source;
    window.host.state = {};
    window.host.page = 'editor';
  }, fixture.records);
  await page.waitForFunction(() => window.host.$refs.editor?.catalog);
  const editor = page.locator('.columns-editor');
  assert.equal(
    await editor.getByLabel('Title', { exact: true }).inputValue(),
    'Preview'
  );
  assert.equal(
    await editor.getByLabel('Show in table', { exact: true }).isChecked(),
    true
  );
  for (const mode of ['dark', 'light']) {
    await page.evaluate((mode) => (window.appearance.mode = mode), mode);
    await page.screenshot({
      path: report + '/columns-editor-stream-' + mode + '.png'
    });
  }
  await editor.getByRole('button', { name: 'name', exact: true }).click();
  await editor.getByLabel('Title', { exact: true }).fill('Object name');
  await editor.getByLabel('Title', { exact: true }).press('Tab');
  assert.equal(await page.evaluate(() => window.host.$refs.editor.dirty), true);
  await page.evaluate(() => window.host.$refs.editor.save());
  await page.waitForFunction(() => !window.host.$refs.editor.busy);
  assert(catalog.records[0].config.includes('title="Object name"'));
  await page.evaluate(
    () =>
      (window.host.focus = {
        project: 'table_fixture',
        searchType: 'cg/assets',
        view: 'table',
        column: 'description'
      })
  );
  await page.evaluate(() => window.host.$refs.editor.focusRequestedColumn());
  assert.equal(
    await page.evaluate(() => window.host.$refs.editor.element.name),
    'description'
  );
  await page.evaluate(() => (window.appearance.language = 'ru'));
  assert.equal(
    await editor.getByLabel('Заголовок', { exact: true }).inputValue(),
    'Description'
  );
  await page.setViewportSize({ width: 320, height: 660 });
  await page.screenshot({ path: report + '/columns-editor-stream-mobile.png' });
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth),
    320
  );
  await page.setViewportSize({ width: 800, height: 660 });
  await page.evaluate(() => {
    window.host.page = 'table';
    window.appearance.language = 'en';
  });
  await page.waitForFunction(
    () => !!window.host.$refs.table && !window.host.$refs.table.cellsBusy
  );
  const rootSelection = await page.evaluate(() => [...window.host.selected]);
  await page.evaluate(() => {
    const record = window.host.rows[0];
    return window.host.$refs.table.tableAction(
      record,
      'nested-table',
      {
        columnName: 'nested',
        nestedTable: {
          searchType: 'cg/assets',
          view: 'table',
          parentKey: record.__search_key__,
          insert: true
        }
      },
      null
    );
  });
  const nested = page.locator('.nested-table');
  await nested.waitFor();
  await page.waitForFunction(
    () =>
      Object.values(window.host.$refs.table.expandedTables)[0]?.rows?.length ===
      2
  );
  await nested.locator('[data-frame="nestedSelect"]').first().click();
  assert.deepEqual(
    await page.evaluate(() => window.host.selected),
    rootSelection,
    'Nested selection must not change the search selection'
  );
  assert.equal(
    await page.evaluate(
      () =>
        Object.values(window.host.$refs.table.expandedTables)[0].selected.length
    ),
    1
  );
  const childCalls = () =>
    requests.filter(
      (row) => row.data.args?.[1] === 'tactic.ui.table.NestedTableReadCmd'
    ).length;
  const beforeReopen = childCalls();
  await nested.locator('[data-frame="nestedClose"]').click();
  await nested.waitFor({ state: 'detached' });
  await page.evaluate(() => {
    const record = window.host.rows[0],
      state = Object.values(window.host.$refs.table.expandedTables)[0];
    return window.host.$refs.table.tableAction(
      record,
      'nested-table',
      { columnName: 'nested', nestedTable: state.scope },
      null
    );
  });
  await nested.waitFor();
  assert.equal(
    childCalls(),
    beforeReopen,
    'Reopening a loaded branch must reuse its rows'
  );
  assert.equal(
    await page.evaluate(
      () =>
        Object.values(window.host.$refs.table.expandedTables)[0].selected.length
    ),
    1
  );
  await nested.locator('[data-frame="nestedFilter"]').fill('Robot');
  await nested.locator('[data-frame="nestedReload"]').click();
  await page.waitForFunction(
    () => !Object.values(window.host.$refs.table.expandedTables)[0].busy
  );
  const lastChild = requests
    .filter(
      (row) => row.data.args?.[1] === 'tactic.ui.table.NestedTableReadCmd'
    )
    .at(-1);
  assert.deepEqual(lastChild.data.args[2].filters, [
    ['name', 'like', '%Robot%']
  ]);
  await nested.screenshot({ path: report + '/nested-table-stream.png' });
  assert.deepEqual(errors, []);
  await writeFile(
    report + '/stream-measurements.json',
    JSON.stringify(
      {
        measurements,
        checks: [
          '10 CG columns',
          'all working cells',
          'header/row/preview/card dimensions',
          'details/notes routing',
          'sorting/grouping',
          'column manager context',
          'auto fit',
          'mouse/keyboard selection',
          'native editor request/save/cancel',
          'virtual window/scroll state',
          'column definition/save/focus/language/mobile'
        ],
        requests: requests.map((r) => r.path),
        writes: writes.length
      },
      null,
      2
    )
  );
  console.log(
    'PASS: Handler Table View and Columns Editor; native dimensions, interactions, editing, virtualization, EN/RU, 320px'
  );
} finally {
  clearTimeout(deadline);
  await browser?.close();
  await server?.close();
}
