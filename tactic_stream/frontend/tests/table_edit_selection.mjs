import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = root + '../tools/frame_table/output/edit-selection/';
await mkdir(output, { recursive: true });
const html = `<html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue';
import Table from '/src/features/interface/TableView.vue';
import Configured from '/src/features/interface/ConfiguredView.vue';
import Editor from '/src/features/interface/TableInlineEditor.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';import '/src/icons.css';
Object.assign(appearance,{theme:'md3',mode:'dark',language:'en',popupAnimations:false});initializeAppearance();
createApp({
 data(){return {localSelection:[],focused:null,ownQuery:true,columnEditable:true,editBusy:false,editUncertain:false,
 editRequest:0,cellEditor:null,editError:'',columnError:'',ticket:'fixture',project:'demo',
 definition:{search_type:'demo/asset'},table:{view:'table'},scopes:[],saved:[],
 records:[{__search_key__:'A',name:'Oak'},{__search_key__:'B',name:'Pine'}]}},
 computed:{tableSelection(){return this.localSelection}},
 mounted(){window.fixture=this},
 methods:{
  openCellEditor:Configured.methods.openCellEditor,tableSelect:Configured.methods.tableSelect,
  async cellEditCommand(scope){this.scopes.push({...scope,search_keys:[...scope.search_keys]});return {plans:scope.search_keys.map(key=>({key})),
   field:{name:'name',title:'Name',class_name:'pyasm.widget.input_wdg.TextWdg',values:['Oak'],options:{},action:{handler:'pyasm.command.DatabaseAction',options:{}},input:{type:'text'}}}},
  cancel(){this.cellEditor=null;this.$refs.inlineEditor.close()}
 },
 render(){return h('main',{style:'height:100%;display:flex;flex-direction:column'},[
  this.localSelection.length?h('div',{'data-selection-bar':''},'Deselect '+this.localSelection.length+' items'):null,
  h(Table,{columns:[{name:'name',title:'Name',width:260,editable:true,kind:'text',hideOrder:0}],
   groups:[{key:'all',records:this.records}],closedGroups:{},selectedKeys:this.localSelection,selectable:true,editable:true,
   onSelect:this.tableSelect,onFocus:record=>this.focused=record.__search_key__,onEdit:this.openCellEditor},
   {cell:({record})=>h('span',record.name)}),
  h(Editor,{ref:'inlineEditor',editor:this.cellEditor,error:this.editError,onCancel:this.cancel,
   onSave:value=>{this.saved.push(value);this.cancel()}})
 ])}
}).mount('#app');
</script><style>html,body,#app{height:100%;width:100%;margin:0}</style></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'table-selection-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url !== '/selection-fixture') return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await server.transformIndexHtml(request.url, html));
          } catch (error) {
            next(error);
          }
        });
      }
    }
  ],
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({ viewport: { width: 800, height: 300 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.setDefaultTimeout(6000);
  await page.goto(server.resolvedUrls.local[0] + 'selection-fixture');
  await page.waitForFunction(() => window.fixture);
  const rows = page.locator('.handler-table-row');
  for (const selected of [[], ['B'], ['A', 'B']]) {
    await page.evaluate((selected) => {
      window.fixture.localSelection = selected;
    }, selected);
    await rows.nth(0).locator('.handler-table-cell').dblclick();
    const editor = page.locator('.table-inline-editor:popover-open');
    await page.waitForFunction(
      () => window.fixture.cellEditor || window.fixture.columnError
    );
    assert.equal(await page.evaluate(() => window.fixture.columnError), '');
    await editor.waitFor();
    assert.deepEqual(
      await page.evaluate(() => [...window.fixture.localSelection]),
      selected
    );
    assert.equal(await page.evaluate(() => window.fixture.focused), 'A');
    assert.equal(
      await rows.nth(0).getByRole('checkbox').isChecked(),
      selected.includes('A')
    );
    assert.equal(
      await rows.nth(1).getByRole('checkbox').isChecked(),
      selected.includes('B')
    );
    assert.equal(
      await page.locator('[data-selection-bar]').count(),
      Number(selected.length > 0)
    );
    assert.deepEqual(
      await page.evaluate(() => window.fixture.scopes.at(-1).search_keys),
      selected.includes('A') ? selected : ['A']
    );
    if (selected.length === 0)
      await page.screenshot({ path: output + 'double-click.png' });
    await editor.locator('input').press('Escape');
    await editor.waitFor({ state: 'hidden' });
    assert.deepEqual(
      await page.evaluate(() => [...window.fixture.localSelection]),
      selected
    );
  }
  await page.evaluate(() => {
    window.fixture.localSelection = [];
  });
  await rows.nth(0).getByRole('checkbox').click();
  assert.deepEqual(
    await page.evaluate(() => [...window.fixture.localSelection]),
    ['A']
  );
  await rows
    .nth(1)
    .locator('.handler-table-cell')
    .click({ modifiers: ['Shift'] });
  assert.deepEqual(
    await page.evaluate(() => [...window.fixture.localSelection]),
    ['A', 'B']
  );
  await page.screenshot({ path: output + 'selection.png' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: double-click edit/focus preserves checkboxes and bulk targets; checkbox and Shift selection remain available'
  );
} finally {
  await browser?.close();
  await server.close();
}
