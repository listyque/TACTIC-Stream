import { chooseStatus } from './status_picker_helpers.mjs';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium, firefox } from 'playwright';

import { translate } from '../../src/tactic_stream/shared_ui/core/strings.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/tasks/editor.ui.mjs';
const single = Editor.describe(
  {
    inline: true,
    immediate: true,
    fields: [{ name: 'progress', editable: true }]
  },
  316,
  'en'
);
assert.equal(
  single.nodes.find((node) => node.id === 'taskInlineTitle').text,
  'Progress'
);
assert.equal(
  single.nodes.some((node) => node.id === 'taskEditorTitle_progress'),
  false
);
assert.equal(single.height, 80);
const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h,nextTick} from 'vue';
import TaskManager from '/src/features/tasks/TaskManager.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import {tooltipDirective} from '/src/controls/tooltip.js';
import {windowDirective} from '/src/controls/window.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{language:'en',theme:'md3',mode:'dark',popupAnimations:false});initializeAppearance();window.appearance=appearance;
const TestManager={...TaskManager,components:{...TaskManager.components,NotesPanel:{render:()=>null},Timesheet:{render:()=>null}}};
const fields=['assigned','supervisor','status','progress','bid_duration','bid_start_date','bid_end_date'].map(name=>({name,editable:true}));
const task={__search_key__:'sthpw/task?code=TASK1',search_code:'ASSET1',search_type:'demo/asset',process:'model',assigned:'admin',status:'Working',progress:20,bid_duration:2,bid_start_date:'2026-10-01',bid_end_date:'2026-11-01'};
const users=[{value:'admin',label:'Admin',primaryGroup:'Admin'},{value:'artist',label:'Alex Artist',primaryGroup:'Artists'}];
const plan={operation:'update',search_key:'demo/asset?code=ASSET1',task_key:task.__search_key__,task,fields,data:{},statuses:['Working','Complete'],users,catalog:{bidDurationUnit:'hour'}};
createApp({mounted(){const manager=this.$refs.manager;window.manager=manager;
manager.parentRecords={asset:{__search_key__:'demo/asset?code=ASSET1',code:'ASSET1',name:'Robot'}};
manager.catalog={users,processes:[],priorityChoices:[],milestoneChoices:[]};manager.result={tasks:[task]};manager.rowPlans={[task.__search_key__]:plan};},
render(){return h('main',[h('nav',['assigned','supervisor','status','progress','bid_duration','dates'].map(key=>h('button',{id:key,onClick:event=>window.manager.editCell(window.manager.tasks[0],{key},Object.assign(event.currentTarget.getBoundingClientRect(),{anchor:event.currentTarget}))},key))),h(TestManager,{ref:'manager',ticket:'fixture',project:'demo',currentUser:'admin',parents:[]})])}})
.provide('openHelp',()=>{}).directive('tooltip',tooltipDirective).directive('window',windowDirective).mount('#app');
</script><style>body{padding:24px}nav{display:flex;flex-wrap:wrap;gap:8px}</style></body></html>`;
let server, browser;
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'inline-editors',
        configureServer(server) {
          server.middlewares.use(async (request, response, next) => {
            if (request.url !== '/inline-fixture') return next();
            response.setHeader('Content-Type', 'text/html');
            response.end(await server.transformIndexHtml(request.url, html));
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0 }
  });
  await server.listen();
  browser = await (
    process.env.STREAM_BROWSER_ENGINE === 'firefox' ? firefox : chromium
  ).launch({
    headless: true,
    ...(process.env.STREAM_BROWSER_ENGINE === 'firefox'
      ? {}
      : { channel: process.env.STREAM_BROWSER_CHANNEL })
  });
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
  page.setDefaultTimeout(5000);
  const errors = [],
    requests = [];
  if (process.env.TASK_EDITOR_CAPTURE)
    await mkdir(process.env.TASK_EDITOR_CAPTURE, { recursive: true });
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {
    if (request.method() === 'POST') requests.push(request.url());
  });
  await page.goto(server.resolvedUrls.local[0] + 'inline-fixture');
  await page.waitForFunction(() => window.manager?.tasks.length === 1);
  await page.evaluate(() => {
    const dialog = window.manager.$refs.dialog;
    dialog.showModal();
    dialog.prepend(document.querySelector('nav'));
  });
  const popup = page.locator('.task-table-editor:popover-open');
  for (const field of ['assigned', 'supervisor']) {
    await page.locator('#' + field).click();
    await page.getByRole('combobox', { name: 'Search users' }).waitFor();
    assert.equal(
      await popup.locator('header').count(),
      0,
      'One click goes straight to the user picker'
    );
    await page.getByRole('combobox', { name: 'Search users' }).fill('Alex');
    await page.getByRole('radio', { name: /Alex Artist/ }).click();
    await page.waitForFunction(
      (field) => window.manager.tasks[0][field + 'Login'] === 'artist',
      field
    );
    assert.equal(await popup.count(), 0);
  }
  await page.locator('#status').click();
  const status = popup.locator('.status-select');
  await status.waitFor();
  assert.equal(
    await status.evaluate((el) => el.open),
    true,
    'Status choices open without a second click'
  );
  await chooseStatus(status, 'Complete');
  await page.waitForFunction(
    () => window.manager.tasks[0].status === 'Complete'
  );
  await page.locator('#progress').click();
  const progress = popup.getByRole('slider', { name: 'Progress' });
  await progress.focus();
  await progress.press('ArrowRight');
  if (process.env.TASK_EDITOR_CAPTURE)
    await popup.screenshot({
      path: process.env.TASK_EDITOR_CAPTURE + '/progress-ts.png'
    });
  await progress.press('End');
  assert.equal(await progress.inputValue(), '100');
  await popup.locator('output').getByText('100%', { exact: true }).waitFor();

  assert.equal(await popup.locator('input[type=number]').count(), 0);
  await page.keyboard.press('Escape');
  await page.locator('#bid_duration').click();
  const hours = popup.getByRole('spinbutton', { name: 'Planned hours' });
  await popup.getByRole('button', { name: 'Increase value' }).click();
  assert.equal(Number(await hours.inputValue()), 2.25);
  if (process.env.TASK_EDITOR_CAPTURE)
    await popup.screenshot({
      path: process.env.TASK_EDITOR_CAPTURE + '/hours-ts.png'
    });
  await popup.getByRole('button', { name: 'Decrease value' }).click();
  assert.equal(Number(await hours.inputValue()), 2);

  await hours.fill('2.5');
  await hours.press('Enter');
  await page.waitForFunction(
    () => window.manager.tasks[0].bid_duration === 2.5
  );
  await page.keyboard.press('Escape');
  await page.evaluate(() => {
    const manager = window.manager,
      key = manager.tasks[0].key;
    manager.rowPlans[key].catalog.bidDurationUnit = 'minute';
  });
  await page.locator('#bid_duration').click();
  await hours.fill('3');
  await hours.press('Enter');
  await page.waitForFunction(
    () => window.manager.tasks[0].bid_duration === 180
  );
  await page.keyboard.press('Escape');
  await page.locator('#dates').click();
  assert.equal(
    await popup.locator('[data-task-field$="_date"]').count(),
    2,
    'Paired dates retain their two-field editor'
  );
  await page.keyboard.press('Escape');
  await page.evaluate(() => {
    window.manager.rowPlans[window.manager.tasks[0].key].fields.find(
      (field) => field.name === 'assigned'
    ).editable = false;
  });
  await page.locator('#assigned').click();
  assert.equal(
    await popup.count(),
    0,
    'Read-only fields do not open an editor'
  );
  assert.equal(
    (
      await page.evaluate(
        () => window.manager.rowPlans[window.manager.tasks[0].key].task
      )
    ).progress,
    20,
    'Editing stages a draft, keeping the original plan'
  );
  assert.deepEqual(
    requests,
    [],
    'Opening and editing cells performs no unrequested save'
  );
  await page.setViewportSize({ width: 320, height: 600 });
  await page.evaluate(() => (window.appearance.language = 'ru'));
  await page.locator('#progress').click();
  await popup
    .getByRole('slider', { name: translate('Progress', 'ru') })
    .waitFor();
  const bounds = await popup.boundingBox();
  assert(bounds.x >= 0 && bounds.x + bounds.width <= 320);
  await page.keyboard.press('Escape');
  assert.deepEqual(errors, []);
  console.log(
    'PASS: Task Manager direct pickers, progress slider, quarter-hour stepper, paired dates and draft ownership'
  );
} finally {
  await browser?.close();
  await server?.close();
}
