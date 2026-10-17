import { closeInspector } from './inspector_helpers.mjs';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const base = process.argv[2],
  output = '../.screenshots/mobile-current';
await mkdir(output, { recursive: true });
async function request(path, data) {
  const response = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const value = await response.json();
  assert(response.ok, JSON.stringify(value));
  return value.result;
}
const ticket = await request('/admin/rpc', {
  method: 'get_ticket',
  args: ['admin', 'private-test-password']
});
const auth = { ticket, project: 'one' },
  rpc = (method, args, kwargs = {}) =>
    request('/admin/rpc', { method, args: [auth, ...args], kwargs });
for (let i = 0; i < 18; i++) {
  const parent = await rpc('insert', [
    'contract/quick_task',
    {
      code: 'PHONE_' + i,
      name: `Phone asset ${i} with a complete readable title`,
      pipeline_code: 'one/quick_task'
    }
  ]);
  const command = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd';
  const plan = (
    await rpc('execute_cmd', [
      command,
      {
        action: 'prepare',
        plans: [
          {
            operation: 'create',
            draft_id: 'phone-task-' + i,
            search_key: parent.__search_key__,
            process: 'model'
          }
        ]
      }
    ])
  ).info.plans[0];
  await rpc('execute_cmd', [
    command,
    {
      action: 'save',
      plans: [
        { ...plan, data: { status: plan.statuses[0], assigned: 'admin' } }
      ]
    }
  ]);
}
await request('/admin/messages/initialize', auth);
const chat = (await request('/admin/messages/create', auth)).conversationId;
for (let i = 0; i < 16; i++)
  await request('/admin/messages/send', {
    ...auth,
    message_code: chat,
    message: 'Phone history ' + i
  });
const browser = await chromium.launch({ headless: true });
let page;
try {
  page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    hasTouch: true,
    isMobile: true
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  const ready = () =>
    page.waitForFunction(() =>
      document.querySelector('.workspace-results[aria-busy="false"]')
    );
  const root = page.locator('.workspace-results');
  const capture = async (name) => {
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: output + '/' + name + '.png',
      animations: 'disabled'
    });
  };
  const fits = async (node) =>
    assert(
      await node.evaluate(
        (element) => element.scrollWidth <= element.clientWidth
      ),
      'No horizontal overflow'
    );
  const panel = async (id) => {
    await page.locator('.navigation-toggle').tap();
    await page
      .getByRole('combobox', { name: 'Active panel', exact: true })
      .selectOption(id);
    await page
      .locator('#workspace-sidebar')
      .getByRole('button', { name: 'Close navigation', exact: true })
      .tap();
  };
  const dockState = () =>
    page.evaluate(() =>
      JSON.parse(localStorage.getItem('tactic_stream.docks.admin'))
    );
  const dismiss = async () => {
    for (const button of await page
      .locator('.notification-dismiss:visible')
      .all())
      await button.tap();
  };
  await page.goto(
    base + '/projects/one/?search_type=contract/quick_task&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).tap();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).tap();
  await root.getByRole('grid', { name: 'Table', exact: true }).waitFor();
  const panels = page.locator('.dock-menu');
  await panels.getByLabel('Workspace panels', { exact: true }).tap();
  await panels
    .locator('.dock-group-menu > summary[aria-label="Browsing"]')
    .tap();
  await panels
    .getByRole('menuitemradio', { name: 'Description', exact: true })
    .tap();
  const description = page.locator('[data-dock="description"]');
  await description.waitFor({ state: 'visible' });
  await description
    .getByLabel('Panel position: Description', { exact: true })
    .tap();
  await description
    .getByRole('button', { name: 'Dock right', exact: true })
    .tap();
  const desktopLayout = (await dockState()).layout;
  const desktopPanels = (await dockState()).panels;
  await dismiss();
  await capture('desktop-before');
  await page.setViewportSize({ width: 360, height: 780 });
  assert.equal(await page.locator('.workspace-rail').count(), 0);
  assert.equal(
    await page
      .getByRole('separator', { name: 'Resize workspace panels', exact: true })
      .filter({ visible: true })
      .count(),
    0
  );
  await panel('results');
  await root.locator('.result-item:visible').first().waitFor();
  const phone = root
    .locator('.result-item:visible')
    .filter({ hasText: 'Phone asset 0 with a complete readable title' })
    .first();
  assert.equal(await root.locator('table:visible').count(), 0);
  assert.equal(
    await phone
      .locator('.image-picker-preview > span:not(.app-icon)')
      .evaluate((node) => node.clientWidth),
    42
  );
  assert(
    (await phone.boundingBox()).height * 3 <= (await root.boundingBox()).height,
    'Compact results fit at least three rows in the phone viewport'
  );
  assert((await root.boundingBox()).height > 500);
  assert.equal(
    await root
      .getByRole('button', { name: 'Object details', exact: true })
      .count(),
    0
  );
  assert.equal(
    await page
      .getByLabel('Change search results view', { exact: true })
      .count(),
    0
  );
  await phone.getByLabel('Item actions', { exact: true }).tap();
  await page
    .getByRole('checkbox', { name: 'Select record', exact: true })
    .check();
  await page.keyboard.press('Escape');
  await page
    .getByRole('group', { name: 'Selected record actions', exact: true })
    .waitFor();
  await phone.getByLabel('Item actions', { exact: true }).tap();
  await page
    .getByRole('checkbox', { name: 'Select record', exact: true })
    .uncheck();
  await page.keyboard.press('Escape');
  await fits(root);
  await capture('phone-items-360');
  // A synthetic visual viewport models the keyboard without changing desktop geometry.
  await page.evaluate(() => {
    Object.defineProperties(visualViewport, {
      height: { value: 440, configurable: true },
      offsetTop: { value: 24, configurable: true }
    });
    visualViewport.dispatchEvent(new Event('resize'));
  });
  assert.equal(
    Math.round((await page.locator('.workspace').boundingBox()).height),
    440
  );
  await page.evaluate(() => {
    delete visualViewport.height;
    delete visualViewport.offsetTop;
    visualViewport.dispatchEvent(new Event('resize'));
  });
  await phone.getByLabel('Item actions', { exact: true }).tap();
  await page.getByRole('menuitem', { name: 'Notes', exact: true }).tap();
  const inspector = page.getByRole('region', {
    name: 'Task Inspector',
    exact: true,
    includeHidden: true
  });
  await inspector.locator('.inspector-context').waitFor();
  await inspector.getByLabel('Process', { exact: true }).tap();
  await inspector.locator('[data-process-choice="model"]').tap();
  await inspector
    .locator('.inspector-process > summary')
    .filter({ hasText: 'Model' })
    .waitFor();
  assert.equal(
    await inspector
      .getByRole('button', { name: 'Maximize window', exact: true })
      .isVisible(),
    false
  );
  assert(
    (await inspector.locator('.notes-timeline').boundingBox()).height > 500
  );
  const note = inspector.getByLabel('Note text', { exact: true });
  await note.fill('Preserved phone note');
  await note.press('End');
  await note.press('Enter');
  assert.equal(await note.inputValue(), 'Preserved phone note\n');
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.equal(await note.inputValue(), 'Preserved phone note\n');
  await page.setViewportSize({ width: 320, height: 740 });
  await inspector.waitFor({ state: 'visible' });
  assert.equal(
    (await dockState()).compactActive,
    'notes',
    'Returning to phone keeps the chosen inspector even when it is hidden on desktop'
  );
  await fits(inspector);
  await closeInspector(page);
  await phone.getByLabel('Item actions', { exact: true }).tap();
  await page.getByRole('menuitem', { name: 'Notes', exact: true }).tap();
  await inspector.getByLabel('Process', { exact: true }).tap();
  await inspector.locator('[data-process-choice="model"]').tap();
  await note.waitFor();
  assert.equal(await note.inputValue(), 'Preserved phone note\n');
  const chooser = page.waitForEvent('filechooser');
  await inspector
    .getByRole('button', { name: 'Attach files', exact: true })
    .tap();
  await (
    await chooser
  ).setFiles({
    name: 'Phone-note.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Native phone note attachment')
  });
  await inspector.getByRole('button', { name: 'Send note', exact: true }).tap();
  await inspector
    .locator('.note-body')
    .filter({ hasText: 'Preserved phone note' })
    .waitFor();
  await inspector
    .getByRole('link', { name: 'Download', exact: true })
    .waitFor();
  assert.equal(await note.inputValue(), '');
  await dismiss();
  await capture('phone-inspector-320');
  await closeInspector(page);
  await page.getByLabel('More options', { exact: true }).tap();
  await page.getByRole('button', { name: 'Task Manager', exact: true }).tap();
  const manager = page.getByRole('region', {
    name: 'Task Manager',
    exact: true
  });
  const tasksReady = () =>
    page.waitForFunction(() =>
      document.querySelector('.task-manager-results[aria-busy="false"]')
    );
  await tasksReady();
  await manager.getByLabel('Task view options', { exact: true }).tap();
  await manager
    .getByRole('group', { name: 'Task scope', exact: true })
    .getByRole('menuitemradio', { name: 'Project tasks', exact: true })
    .tap();
  await tasksReady();
  await manager.getByLabel('Task view options', { exact: true }).tap();
  await manager.locator('.mobile-task-list [data-task-key]').first().waitFor();
  assert.equal(await manager.locator('table:visible').count(), 0);
  await fits(manager);
  assert(
    (await manager.locator('.task-manager-results').boundingBox()).height > 500
  );
  const row = manager
    .locator('.mobile-task-list [data-task-key]')
    .filter({ hasText: 'Phone asset 0 with a complete readable title' })
    .first();
  await row
    .getByRole('button', {
      name: 'Phone asset 0 with a complete readable title',
      exact: true
    })
    .tap();
  const status = manager.getByRole('combobox', { name: 'Status', exact: true });
  await status.waitFor();
  const choices = await status
    .locator('option:not([disabled])')
    .evaluateAll((options) => options.map((row) => row.value));
  const previous = await status.inputValue(),
    changed = choices.find((value) => value && value !== previous);
  assert(changed);
  await status.selectOption(changed);
  await manager
    .getByRole('region', { name: 'Pending task changes', exact: true })
    .waitFor();
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.equal(
    await page.locator('.task-manager-pending').count(),
    1,
    'Task draft stays mounted while its desktop dock is hidden'
  );
  await page.setViewportSize({ width: 320, height: 740 });
  await manager.locator('.mobile-task-heading').waitFor();
  assert.equal(
    await status.inputValue(),
    changed,
    'Phone keeps the task detail and staged status'
  );
  await manager
    .getByRole('region', { name: 'Pending task changes', exact: true })
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await tasksReady();
  const parents = await rpc('query', ['contract/quick_task'], {
    filters: [['code', 'PHONE_0']]
  });
  const saved = await rpc('query', ['sthpw/task'], {
    filters: [
      ['search_code', parents[0].code],
      ['process', 'model']
    ]
  });
  assert.equal(saved[0].status, changed);
  await dismiss();
  await capture('phone-tasks-320');
  await manager.getByRole('button', { name: 'Back', exact: true }).tap();
  await row.getByRole('button', { name: 'Open notes', exact: true }).tap();
  await inspector.locator('.inspector-context').waitFor();
  assert.match(
    await inspector.locator('.inspector-object-title').innerText(),
    /Phone asset 0/
  );
  await closeInspector(page);
  await page.getByLabel('Account', { exact: true }).tap();
  await page.getByRole('button', { name: 'Messages', exact: true }).tap();
  const messages = page.getByRole('dialog', { name: 'Messages', exact: true });
  await messages.getByRole('button', { name: 'Favorites', exact: true }).tap();
  await messages.locator('.message-row').first().waitFor();
  const composer = messages.getByLabel('Write a reply', { exact: true });
  await composer.fill('Phone chat draft');
  await composer.press('End');
  await composer.press('Enter');
  await messages
    .getByRole('button', { name: 'Conversations', exact: true })
    .tap();
  await messages.getByRole('button', { name: 'Favorites', exact: true }).tap();
  assert.equal(await composer.inputValue(), 'Phone chat draft\n');
  await page.evaluate(() => {
    Object.defineProperties(visualViewport, {
      height: { value: 420, configurable: true },
      offsetTop: { value: 10, configurable: true }
    });
    visualViewport.dispatchEvent(new Event('resize'));
  });
  const composeBox = await messages
    .locator('.messages-compose-row')
    .boundingBox();
  assert(
    composeBox.y + composeBox.height <= 431,
    'Composer stays above the keyboard'
  );
  await fits(messages);
  await page.evaluate(() => {
    delete visualViewport.height;
    delete visualViewport.offsetTop;
    visualViewport.dispatchEvent(new Event('resize'));
  });
  await dismiss();
  await capture('phone-messages-320');
  await messages.getByRole('button', { name: 'Send', exact: true }).tap();
  await page.waitForFunction(
    () => document.querySelector('.message-composer textarea').value === ''
  );
  assert(
    (
      await request('/admin/messages/history', { ...auth, message_code: chat })
    ).messages.some((row) => row.message === 'Phone chat draft\n')
  );
  await messages
    .getByRole('button', { name: 'Close Messages', exact: true })
    .tap();
  await panel('results');
  const resultViewport = root.locator('.mobile-result-screen:visible');
  await resultViewport.evaluate((node) => (node.scrollTop = node.scrollHeight));
  const snapshotOwner = root
    .locator('.result-item-object[aria-label="Asset B"]:visible')
    .first();
  await snapshotOwner.locator('.result-item-copy').tap();
  await panel('snapshot');
  const snapshots = page.locator('.snapshot-browser');
  await snapshots
    .locator('.snapshot-file-row')
    .filter({ hasText: 'phone-preview' })
    .tap();
  await snapshots
    .getByRole('button', { name: 'Snapshot file actions', exact: true })
    .tap();
  await snapshots
    .getByRole('button', { name: 'Copy Web Link', exact: true })
    .waitFor();
  await page.keyboard.press('Escape');
  await snapshots.getByRole('button', { name: 'Open File', exact: true }).tap();
  const file = page.getByRole('dialog', { name: 'File preview', exact: true });
  await file
    .locator('pre')
    .filter({ hasText: 'Native phone snapshot preview' })
    .waitFor();
  await file.getByRole('button', { name: 'Close preview', exact: true }).tap();
  await dismiss();
  await capture('phone-snapshot-320');
  await page.reload();
  await ready();
  await page.locator('[data-dock="snapshot"]').waitFor({ state: 'visible' });
  assert.equal(
    (await dockState()).compactActive,
    'snapshot',
    'Phone restores its own active panel'
  );
  assert.deepEqual((await dockState()).layout, desktopLayout);
  await panel('results');
  for (const size of [
    { width: 390, height: 844 },
    { width: 700, height: 900 },
    { width: 640, height: 360 }
  ]) {
    await page.setViewportSize(size);
    await fits(root);
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      )
    );
    assert((await root.boundingBox()).height > size.height * 0.45);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator('.workspace-rail').waitFor();
  assert.equal(await page.locator('.workspace-rail').count(), 1);
  await root.getByRole('grid', { name: 'Table', exact: true }).waitFor();
  assert.deepEqual(
    (await dockState()).layout,
    desktopLayout,
    'Mobile panel choice does not rewrite desktop geometry or active stack'
  );
  assert.deepEqual(
    (await dockState()).panels,
    desktopPanels,
    'Phone interactions preserve desktop visibility, floating bounds and z-order'
  );
  await dismiss();
  await capture('desktop-after');
  await page.reload();
  await ready();
  await root.getByRole('grid', { name: 'Table', exact: true }).waitFor();
  assert.deepEqual((await dockState()).layout, desktopLayout);
  await panels.getByLabel('Workspace panels', { exact: true }).tap();
  await panels.locator('.dock-group-menu > summary[aria-label="Tools"]').tap();
  await panels
    .getByRole('menuitemradio', { name: 'Drop Plate', exact: true })
    .tap();
  const drop = page.locator('[data-dock="drop_plate"]');
  await drop.getByRole('button', { name: 'Maximize panel', exact: true }).tap();
  await page.setViewportSize({ width: 320, height: 780 });
  await page.locator('.workspace-rail').waitFor({ state: 'detached' });
  assert.equal(
    (await dockState()).maximized,
    'drop_plate',
    'Phone exclusions preserve the desktop maximized pane'
  );
  await page.setViewportSize({ width: 1280, height: 900 });
  await drop.waitFor({ state: 'visible' });
  await drop.getByRole('button', { name: 'Restore panel', exact: true }).tap();
  assert.deepEqual(errors, []);
  await writeFile(
    output + '/acceptance.json',
    JSON.stringify(
      {
        capturedAt: new Date().toISOString(),
        browser: 'Chromium',
        widths: [320, 360, 390, 640, 700, 1280],
        scenarios: [
          'compact objects and touch actions',
          'selection',
          'native task status edit and save',
          'inspector note draft resize/reopen and native attachment',
          'chat back/draft/newline/send',
          'snapshot file actions/preview without right click',
          'visual viewport keyboard',
          'desktop layout/view restore and reload'
        ],
        errors
      },
      null,
      2
    )
  );
  console.log(
    'PASS complete phone workspace: touch items/tasks/notes/files/messages, keyboard viewport and unchanged desktop restoration'
  );
} catch (error) {
  if (page) await page.screenshot({ path: output + '/failure.png' });
  throw error;
} finally {
  await browser.close();
}
