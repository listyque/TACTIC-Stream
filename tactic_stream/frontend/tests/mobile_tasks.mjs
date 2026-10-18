import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('..', import.meta.url)),
  output = fileURLToPath(
    new URL('../../.screenshots/mobile-tasks-current/', import.meta.url)
  );
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="dock-tasks" style="height:100dvh;display:flex"></div><div id="app"></div><script type="module">
import { createApp,h,ref,provide } from 'vue'
import '/src/App.vue'
import TaskManager from '/src/features/tasks/TaskManager.vue'
import HelpView from '/src/features/help/HelpView.vue'
import MobileResults from '/src/features/workspace/MobileResults.vue'
import { windowDirective } from '/src/controls/window.js'
import { appearance,initializeAppearance } from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{mode:'dark',fadeAnimations:false,popupAnimations:false,clickAnimations:false});initializeAppearance();window.appearance=appearance
window.searchEvents=[]
createApp({setup(){
 const help=ref(null);provide('openHelp',topic=>help.value.open(topic))
 const search=ref(false),parent=ref(null),scroll=ref({})
 window.searchMode=search
 const nodes=Array.from({length:24},(_,i)=>({id:'object-'+i,kind:'object',record:{__search_key__:'cg/assets?id='+i,name:'Search asset '+i},preview:{},children:[]}))
 return()=>[h(HelpView,{ref:help}),h(TaskManager,{ref:v=>window.manager=v,docked:true,ticket:'fixture',project:'cg',currentUser:'alice'}),
 search.value?h('div',{style:'position:fixed;inset:0;display:flex;flex-direction:column;background:var(--page);z-index:40'},[h(MobileResults,{groups:[{key:'',label:'',nodes}],parent:parent.value,path:parent.value?[parent.value.id]:[],direction:parent.value?'forward':'back',scroll:scroll.value,active:true,closedGroups:{},selectedKeys:[],
 onEnter:node=>{window.searchEvents.push(node.id);parent.value=node},onBack:()=>parent.value=null,onScrolled:(key,top)=>scroll.value[key]=top,onSelect:()=>window.searchEvents.push('select')})]):null]
}}).directive('window',windowDirective).mount('#app')
</script></body></html>`;
const parents = Array.from({ length: 24 }, (_, i) => ({
  __search_key__: 'cg/assets?id=' + i,
  code: 'ASSET' + i,
  name:
    i === 0 ? 'Hero asset with a long name that wraps on a phone' : 'Asset ' + i
}));
let tasks = parents.map((p, i) => ({
  __search_key__: 'sthpw/task?id=' + i,
  search_type: 'cg/assets',
  search_code: p.code,
  process: 'model',
  context: 'model/main',
  status: 'In Progress',
  assigned: 'alice',
  supervisor: 'bob',
  bid_start_date: '2026-10-01 09:00:00',
  bid_end_date: '2026-10-20 18:00:00',
  progress: 30,
  description: 'Original description',
  __process__: { label: 'Modeling', color: '#789fd0' },
  __status__: { label: 'In Progress', color: '#e4b865' },
  __notes_count__: 2
}));
const catalog = {
  users: [
    { value: 'alice', label: 'Alice Artist' },
    { value: 'bob', label: 'Bob Supervisor' }
  ],
  processes: [{ value: 'model', label: 'Modeling' }],
  teams: [],
  milestoneChoices: [],
  priorityChoices: [],
  statuses: []
};
const fields = [
  'process',
  'context',
  'status',
  'assigned',
  'supervisor',
  'bid_start_date',
  'bid_end_date',
  'progress',
  'description'
].map((name) => ({ name, editable: name !== 'process' }));
let server,
  browser,
  holdRead = false,
  releaseRead;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    cacheDir: root + '/node_modules/.vite/mobile-tasks',
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'mobile-tasks-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/mobile-tasks-test') return next();
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
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
      viewport: { width: 320, height: 740 },
      hasTouch: true,
      isMobile: true
    }),
    errors = [],
    commands = [];
  page.setDefaultTimeout(10000);
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('dialog', (dialog) => dialog.accept());
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    commands.push(payload);
    const [, command, values] = payload.args;
    let info = {};
    if (holdRead && command.endsWith('TaskWorkspaceCmd') && !values.action) {
      holdRead = false;
      await new Promise((resolve) => (releaseRead = resolve));
    }
    if (command.endsWith('TaskWorkspaceCmd'))
      info =
        values.action === 'catalog'
          ? catalog
          : {
              tasks,
              parents,
              loaded: tasks.length,
              total: tasks.length,
              offset: 0,
              hasMore: false,
              facets: {}
            };
    else if (command.endsWith('TaskWorkspaceEditCmd')) {
      if (values.action === 'prepare')
        info = {
          plans: values.plans.map((request) => ({
            operation: 'update',
            task_key: request.task_key,
            search_key: request.search_key,
            process: 'model',
            revision: 'original-revision',
            fields,
            task: {
              ...tasks.find((task) => task.__search_key__ === request.task_key)
            },
            data: {},
            users: catalog.users,
            statuses: ['In Progress', 'Complete'],
            statusChoices: [],
            catalog
          }))
        };
      else if (values.action === 'save') {
        for (const plan of values.plans)
          tasks = tasks.map((task) =>
            task.__search_key__ === plan.task_key
              ? { ...task, ...plan.data }
              : task
          );
        info = {};
      }
    } else if (command.endsWith('TaskScheduleCmd'))
      info = { calendar: { days: [] }, gantt: { records: [] } };
    else if (command.endsWith('MilestoneCmd'))
      info = { records: [], fields: [], canCreate: false, canDelete: false };
    await route.fulfill({ json: { result: { info } } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'mobile-tasks-test');
  await page.waitForFunction(() => window.manager);
  await page.evaluate(() => window.manager.open());
  const manager = page.locator('#dock-tasks .task-manager'),
    list = manager.locator('.mobile-task-list');
  const ready = () => page.waitForFunction(() => !window.manager.busy);
  await ready();
  assert.equal(await list.locator('article').count(), 24);
  assert(
    await manager.evaluate((node) => node.scrollWidth <= node.clientWidth),
    'No horizontal phone overflow'
  );
  const card = list.locator('article').first(),
    selection = card.locator('input[type=checkbox]');
  assert.equal(
    await manager.getByLabel('Search tasks', { exact: true }).isVisible(),
    false
  );
  assert.equal(await manager.locator('.task-bulk-bar').count(), 0);
  assert.equal(
    await card
      .locator('[data-frame="taskPhoneRail"]')
      .evaluate((node) => getComputedStyle(node).width),
    '1px'
  );
  await manager.getByRole('button', { name: 'Open search', exact: true }).tap();
  await manager
    .getByLabel('Search tasks', { exact: true })
    .fill('Draft search');
  await manager.getByLabel('Search tasks', { exact: true }).press('Escape');
  assert.equal(
    await manager.getByLabel('Search tasks', { exact: true }).isVisible(),
    false
  );
  await page.evaluate(() => {
    clearTimeout(window.manager.searchTimer);
    window.manager.filters.text = '';
    window.manager.storeColumns();
  });
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  assert.equal(await page.evaluate(() => window.manager.selected.length), 24);
  await page.keyboard.press('Escape');
  await manager
    .getByRole('button', {
      name: 'Cancel bulk edit and clear selection',
      exact: true
    })
    .tap();
  await selection.tap();
  assert.equal(await page.evaluate(() => window.manager.selected.length), 1);
  assert.equal(
    await manager.locator('.mobile-task-heading').count(),
    0,
    'Selection does not navigate'
  );
  await page.evaluate(() => {
    window.originalResult = window.manager.result;
    window.originalPlans = window.manager.rowPlans;
    window.originalCard = document.querySelector('.mobile-task-card');
  });
  const stableBox = await card.boundingBox();
  const beforeLive = commands.filter(
    (c) => c.args[1].endsWith('TaskWorkspaceCmd') && !c.args[2].action
  ).length;
  holdRead = true;
  await page.evaluate(() =>
    window.manager.applyServerBatch({
      projectCode: 'cg',
      activity: [{ __kind__: 'task' }]
    })
  );
  await page.waitForFunction(() => window.manager.refreshing);
  await page.evaluate(() =>
    window.manager.applyServerBatch({
      projectCode: 'cg',
      activity: [{ __kind__: 'task' }]
    })
  );
  assert.equal(
    await page.evaluate(() => window.manager.busy || window.manager.loading),
    false,
    'Background reads do not enter the visible loading state'
  );
  assert.equal(await selection.isEnabled(), true);
  assert.equal(
    await manager
      .getByText(
        'Tasks changed on the server. Refresh to review current values; your draft keeps its original revisions.',
        { exact: true }
      )
      .count(),
    0
  );
  assert.deepEqual(
    await card.boundingBox(),
    stableBox,
    'Background reads keep card geometry stable'
  );
  await page.waitForFunction(() => window.manager.refreshing);
  releaseRead();
  await page.waitForFunction(() => !window.manager.refreshing);
  assert.equal(
    commands.filter(
      (c) => c.args[1].endsWith('TaskWorkspaceCmd') && !c.args[2].action
    ).length,
    beforeLive + 2,
    'Changes during one read coalesce into a single follow-up'
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.manager.result === window.originalResult &&
        window.manager.rowPlans === window.originalPlans &&
        window.originalCard === document.querySelector('.mobile-task-card')
    ),
    true,
    'Unchanged responses keep data, prepared fields and DOM'
  );
  assert.equal(
    await page.evaluate(() => window.manager.selected.length),
    1,
    'Background reads preserve selection'
  );
  tasks = tasks.map((task, index) =>
    index ? task : { ...task, __notes_count__: 3 }
  );
  await page.evaluate(() => window.manager.load(true));
  await page.waitForFunction(() => !window.manager.refreshing);
  assert.equal(
    await card.locator('.app-button-badge').innerText(),
    '3',
    'Real server changes update the card in place'
  );
  assert.equal(
    await page.evaluate(
      () => window.originalCard === document.querySelector('.mobile-task-card')
    ),
    true
  );
  await manager
    .getByRole('button', {
      name: 'Cancel bulk edit and clear selection',
      exact: true
    })
    .tap();
  await page.screenshot({ path: output + 'tasks-dark-320.png' });
  const screen = manager.locator(
    '.mobile-result-screen[data-screen-key="root"]'
  );
  await screen.evaluate((node) => (node.scrollTop = 450));
  await page.waitForTimeout(220);
  assert.equal(
    await manager.locator('.task-manager-toolbar').isVisible(),
    false,
    'Scrolling hides root chrome'
  );
  const currentScroll = await screen.evaluate((node) => node.scrollTop);
  const target = list.locator('article').nth(4);
  await target.getByRole('button', { name: 'Asset 4', exact: true }).tap();
  await ready();
  assert.equal(
    await manager.locator('.mobile-task-heading h2').innerText(),
    'Asset 4'
  );
  assert.equal(
    await manager.locator('.task-manager-toolbar').isVisible(),
    false,
    'Details have their own header'
  );
  assert.equal(
    await manager.locator('.task-manager-footer').isVisible(),
    false
  );
  assert.equal(
    await manager.locator('.task-workspace-editor').count(),
    1,
    'Fields are on the page'
  );
  assert.equal(await manager.locator('.mobile-task-links').count(), 0);
  assert.equal(
    await manager
      .getByText('Changes remain pending until Save.', { exact: true })
      .count(),
    0
  );
  const avatars = manager.locator(
    '.user-combo-box > summary > .image-picker-preview:visible'
  );
  assert.equal(
    await avatars.count(),
    2,
    'Both user fields are visible on the detail page'
  );
  for (const avatar of await avatars.all()) {
    const box = await avatar.boundingBox();
    assert.ok(
      Math.abs(box.width - box.height) < 1,
      'Assignee and supervisor avatars stay circular'
    );
  }
  const description = manager.getByRole('textbox', {
    name: 'Description',
    exact: true
  });
  await description.fill('Phone draft');
  assert.equal(
    await page.evaluate(
      () => window.manager.drafts['sthpw/task?id=4'].revision
    ),
    'original-revision'
  );
  assert.equal(
    commands.filter((c) => c.args[2].action === 'save').length,
    0,
    'Fields only stage a draft'
  );
  await page.screenshot({ path: output + 'detail-dark-320.png' });
  await page.evaluate(() =>
    window.manager.applyServerBatch({
      projectCode: 'cg',
      activity: [{ __kind__: 'task' }]
    })
  );
  assert.equal(
    await page.evaluate(() => window.manager.refreshing),
    false,
    'Live updates do not refresh through an active draft'
  );
  await manager.getByRole('button', { name: 'Back', exact: true }).tap();
  await page.waitForFunction(() => !window.manager.mobileTaskKey);
  await manager
    .locator('.mobile-result-screen:not([data-screen-key="root"])')
    .waitFor({ state: 'hidden' });
  assert.equal(
    await screen.evaluate((node) => node.scrollTop),
    currentScroll,
    'Back restores list scroll'
  );
  assert.equal(
    await page.evaluate(
      () => window.manager.drafts['sthpw/task?id=4'].data.description
    ),
    'Phone draft'
  );
  await page.goForward();
  await ready();
  await page.waitForFunction(
    () => window.manager.mobileTaskKey === 'sthpw/task?id=4'
  );
  await page.setViewportSize({ width: 1280, height: 850 });
  await manager.locator('.task-workspace-table').waitFor();
  assert.equal(
    await page.evaluate(
      () => window.manager.drafts['sthpw/task?id=4'].data.description
    ),
    'Phone draft'
  );
  await page.setViewportSize({ width: 320, height: 740 });
  await manager.locator('.mobile-task-heading').waitFor();
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await page.evaluate(() => Object.keys(window.manager.drafts).length),
    0
  );
  assert.equal(
    await manager
      .getByRole('textbox', { name: 'Description', exact: true })
      .inputValue(),
    'Phone draft',
    'Detail re-prepares after Save'
  );
  const saved = commands.find((c) => c.args[2].action === 'save').args[2]
    .plans[0];
  assert.equal(saved.revision, 'original-revision');
  assert.deepEqual(saved.data, { description: 'Phone draft' });
  await manager.locator('[data-task-field="assigned"] summary').tap();
  const userPopup = page.locator('.user-combo-box[open] .account-panel');
  await userPopup.waitFor();
  assert(
    await userPopup.evaluate((node) => {
      const r = node.getBoundingClientRect();
      return r.left >= 0 && r.right <= innerWidth;
    })
  );
  await page.keyboard.press('Escape');
  await manager.locator('[data-task-field="bid_end_date"] summary').tap();
  const datePopup = page.locator('.app-date-menu[open] .account-panel');
  await datePopup.waitFor({ state: 'visible' });
  assert(
    await datePopup.evaluate((node) => {
      const r = node.getBoundingClientRect();
      return r.left >= 0 && r.right <= innerWidth;
    })
  );
  await page.keyboard.press('Escape');
  const swipe = async (locator, dx, gesturePage = page) => {
    const cdp = await gesturePage.context().newCDPSession(gesturePage),
      box = await locator.boundingBox(),
      viewport = gesturePage.viewportSize();
    const left = Math.max(0, box.x),
      right = Math.min(viewport.width, box.x + box.width),
      x = dx > 0 ? left + 6 : right - 64,
      y = box.y + (dx > 0 ? 8 : Math.min(20, box.height / 2));
    assert(
      x >= 0 && x + dx >= 0 && x <= viewport.width && x + dx <= viewport.width,
      'Swipe stays inside the visible viewport'
    );
    const hit = await gesturePage.evaluate(
      ({ x, y }) => {
        const node = document.elementFromPoint(x, y);
        return {
          visible: !!node,
          interactive: !!node?.closest(
            'button,a,input,textarea,select,label,summary,[contenteditable]'
          ),
          row: node?.closest('[data-mobile-item]')?.dataset.mobileItem
        };
      },
      { x, y }
    );
    assert(
      hit.visible && !hit.interactive,
      'Swipe starts on visible, non-editable content: ' +
        JSON.stringify({ hit, box, x, y })
    );
    if (dx < 0) assert(hit.row, 'Entry swipe starts inside a visible item');
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchStart',
      touchPoints: [{ x, y }]
    });
    for (let i = 1; i <= 6; i++)
      await cdp.send('Input.dispatchTouchEvent', {
        type: 'touchMove',
        touchPoints: [{ x: x + (dx * i) / 6, y }]
      });
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchEnd',
      touchPoints: []
    });
    await cdp.detach();
    await page.waitForTimeout(80);
  };
  await swipe(manager.locator('.mobile-result-screen'), 100);
  await page.waitForFunction(() => !window.manager.mobileTaskKey);
  await screen.evaluate((node) => (node.scrollTop = 0));
  await page.waitForTimeout(220);
  await swipe(card.locator('[data-frame="taskPhoneProcess"]'), -100);
  await ready();
  await manager.locator('.mobile-task-heading').waitFor();
  for (const theme of ['md3', 'material5'])
    for (const mode of ['light', 'dark']) {
      await page.evaluate(
        ({ theme, mode }) => Object.assign(window.appearance, { theme, mode }),
        { theme, mode }
      );
      assert(
        await manager.evaluate((node) => node.scrollWidth <= node.clientWidth)
      );
      await page.screenshot({
        path: output + 'detail-' + theme + '-' + mode + '-320.png'
      });
    }
  const searchPage = await browser.newPage({
    viewport: { width: 320, height: 740 },
    hasTouch: true,
    isMobile: true
  });
  searchPage.on('pageerror', (error) => errors.push(error.message));
  await searchPage.goto(server.resolvedUrls.local[0] + 'mobile-tasks-test');
  await searchPage.waitForFunction(() => window.searchMode);
  await searchPage.evaluate(() => (window.searchMode.value = true));
  const search = searchPage.locator('[aria-label="Mobile item browser"]');
  await search.waitFor();
  const searchCard = search.locator('[data-mobile-item="object-0"]');
  await searchCard.locator('.result-item-actions summary').tap();
  await searchCard.locator('input[type=checkbox]').tap();
  assert.deepEqual(
    await searchPage.evaluate(() => window.searchEvents),
    ['select'],
    'Search selection remains independent'
  );
  await searchPage.keyboard.press('Escape');
  await swipe(searchCard.locator('.result-item-copy'), -100, searchPage);
  await search.locator('.mobile-result-header').waitFor();
  assert.deepEqual(
    await searchPage.evaluate(() => window.searchEvents),
    ['select', 'object-0'],
    'Search uses the same entry gesture once'
  );
  await swipe(search.locator('.mobile-result-screen'), 100, searchPage);
  await search.locator('.mobile-result-header').waitFor({ state: 'hidden' });
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log(
    'Mobile tasks: 320px cards/detail, browser Back/Forward, swipe, scroll, drafts/revisions, Save, desktop resize, pickers, themes and search regression OK'
  );
} finally {
  await browser?.close();
  await server?.close();
}
