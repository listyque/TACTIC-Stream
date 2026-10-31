import { chooseStatus, statusValues } from './status_picker_helpers.mjs';
import { closeInspector } from './inspector_helpers.mjs';
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  colorScheme: 'dark',
  hasTouch: true
});
page.setDefaultTimeout(10000);
const base = process.argv[2],
  output = process.argv[3],
  errors = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('response', async (response) => {
  if (response.status() >= 400)
    console.error(response.url(), await response.text());
});
let auth;
page.on('request', (request) => {
  const args = request.postDataJSON?.()?.args;
  if (
    request.url().endsWith('/admin/rpc') &&
    args?.[1] === 'tactic.ui.table.task_workspace.TaskWorkspaceCmd'
  )
    auth = args[0];
});
const manager = page.getByRole('region', { name: 'Task Manager', exact: true });
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.task-manager-results')
        ?.getAttribute('aria-busy') === 'false'
  );
async function captureSurface(name) {
  mkdirSync('../.screenshots/collaboration-current', { recursive: true });
  for (const notification of await page.locator('.notification-card').all())
    await notification
      .getByRole('button', { name: 'Dismiss notification', exact: true })
      .click();
  const heading = page.locator('[data-dock="tasks"] > header'),
    maximize = heading.getByRole('button', {
      name: 'Maximize panel',
      exact: true
    });
  const restore = await maximize.isVisible();
  if (restore) {
    await maximize.click();
    await page.waitForFunction(
      () => document.querySelector('.task-manager-results')?.clientWidth > 1100
    );
  }
  await page.mouse.move(5, 5);
  await page.evaluate(() => document.fonts.ready);
  const frame = await manager.boundingBox(),
    top = await manager.locator('.task-manager-toolbar').boundingBox(),
    bottom = await manager.locator('.task-manager-footer').boundingBox();
  await page.screenshot({
    path:
      '../.screenshots/collaboration-current/stream-process-' + name + '.png',
    clip: {
      x: frame.x,
      y: top.y,
      width: frame.width,
      height: bottom.y + bottom.height - top.y
    },
    animations: 'disabled'
  });
  if (restore)
    await heading
      .getByRole('button', { name: 'Restore panel', exact: true })
      .click();
}
async function command(command, values) {
  const response = await page.request.post(base + '/admin/rpc', {
    data: { method: 'execute_cmd', args: [auth, command, values], kwargs: {} }
  });
  assert.equal(response.status(), 200, await response.text());
  return (await response.json()).result.info;
}
async function surface(label) {
  if (
    !(await manager
      .getByRole('radio', { name: label, exact: true })
      .isVisible())
  )
    await manager
      .getByRole('button', { name: 'Task view options', exact: true })
      .click();
  await manager.getByRole('radio', { name: label, exact: true }).tap();
  await ready();
}
const model = manager.locator('[data-process="model"]'),
  review = manager.locator('[data-process="review"]');
try {
  await page.goto(
    base + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await selectProject(page, 'one');
  await page.goto(
    base +
      '/projects/one/?' +
      new URLSearchParams({ search_type: 'contract/quick_task', view: 'table' })
  );
  await page.locator('.workspace-results[aria-busy="false"]').waitFor();
  await page.getByLabel('More options', { exact: true }).click();
  await page.getByRole('button', { name: 'Task Manager', exact: true }).click();
  await ready();
  await surface('Task cards');
  await manager
    .getByText('Select an sObject to view its task processes', { exact: true })
    .waitFor();
  const results = page.getByRole('tab', { name: 'Search', exact: true });
  if (await results.isVisible()) await results.click();
  await page
    .locator('.workspace-results')
    .getByText('Asset B', { exact: true })
    .first()
    .click();
  await ready();
  const tab = page.getByRole('tab', { name: 'Task Manager', exact: true });
  if (await tab.isVisible()) await tab.click();
  await model.waitFor();
  assert.equal(await manager.locator('[data-process]').count(), 2);
  assert.ok(
    await review.evaluate((element) => element.classList.contains('missing'))
  );
  const modelStatus = model.locator('.status-select');
  const oldStatus = await modelStatus.getAttribute('data-value');
  const statuses = await statusValues(modelStatus);
  const changedStatus = statuses.find((value) => value !== oldStatus);
  assert.ok(changedStatus);
  await chooseStatus(modelStatus, changedStatus);
  await chooseStatus(review.locator('.status-select'), statuses[0]);
  await review.getByLabel('Assigned to', { exact: true }).tap();
  await review.getByLabel('Search users', { exact: true }).fill('admin');
  await review.getByRole('radio', { name: 'admin', exact: true }).tap();
  await surface('Compact task list');
  assert.equal(
    await model.locator('.status-select').getAttribute('data-value'),
    changedStatus
  );
  assert.equal(
    await model.evaluate((element) => element.getBoundingClientRect().height),
    44
  );
  await page.screenshot({
    path: output.replace('.png', '-compact.png'),
    animations: 'disabled'
  });
  await captureSurface('compact');
  await surface('Open task workspace');
  await manager.getByRole('region', { name: 'Pending task changes' }).waitFor();
  await surface('Task cards');
  await model
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await model
      .getByRole('button', { name: 'Save task changes', exact: true })
      .count(),
    0
  );
  await review
    .getByRole('button', { name: 'Create task', exact: true })
    .waitFor();
  await review.getByRole('button', { name: 'Create task', exact: true }).tap();
  await ready();
  assert.equal(
    await review.evaluate((element) => element.classList.contains('missing')),
    false
  );
  const parent = 'contract/quick_task?project=one&code=QUICK_A';
  const read = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd',
    edit = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd';
  const created = await command(edit, {
    action: 'prepare',
    plans: [
      {
        operation: 'create',
        draft_id: 'browser-quick-secondary',
        search_key: parent,
        process: 'model',
        context: 'model/second'
      }
    ]
  });
  await command(edit, {
    action: 'save',
    plans: created.plans.map((plan) => ({
      ...plan,
      data: { assigned: 'admin', status: plan.statuses[0] }
    }))
  });
  await manager.getByRole('button', { name: 'Refresh', exact: true }).tap();
  await ready();
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await model
    .getByRole('button', { name: 'model/second / admin', exact: true })
    .tap();
  await chooseStatus(model.locator('.status-select'), changedStatus);
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await model.getByRole('button', { name: 'model / admin', exact: true }).tap();
  assert.equal(
    await model
      .getByRole('button', { name: 'Reset task changes', exact: true })
      .count(),
    0
  );
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await model
    .getByRole('button', { name: 'model/second / admin', exact: true })
    .tap();
  await model
    .getByRole('button', { name: 'Reset task changes', exact: true })
    .waitFor();
  assert.equal(
    await model.locator('.status-select').getAttribute('data-value'),
    changedStatus
  );
  await model
    .getByRole('button', { name: 'Reset task changes', exact: true })
    .tap();
  await page.screenshot({ path: output, animations: 'disabled' });
  await captureSurface('cards');
  await page.setViewportSize({ width: 320, height: 740 });
  await page.waitForTimeout(200);
  assert.equal(
    await model.evaluate((element) => element.getBoundingClientRect().height),
    119
  );
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth),
    320
  );
  await review.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await review.getByRole('button', { name: 'Edit task', exact: true }).tap();
  const editor = page.getByRole('dialog', {
    name: 'Edit task draft',
    exact: true
  });
  await editor.waitFor();
  await editor.getByRole('button', { name: 'Cancel', exact: true }).tap();
  await page.screenshot({
    path: output.replace('.png', '-mobile.png'),
    animations: 'disabled'
  });
  await surface('Compact task list');
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth),
    320
  );
  await page.screenshot({
    path: output.replace('.png', '-compact-mobile.png'),
    animations: 'disabled'
  });
  const result = await command(read, {
    action: 'processes',
    search_key: parent
  });
  assert.equal(result.processes[0].branches.length, 2);
  assert.equal(result.processes[1].branches.length, 1);
  await surface('Task cards');
  await review.getByRole('button', { name: 'Task notes', exact: true }).tap();
  const inspector = page.getByRole('region', {
    name: 'Task Inspector',
    exact: true
  });
  await inspector.waitFor();
  await closeInspector(page);
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await model.getByRole('button', { name: 'Add task', exact: true }).tap();
  await editor.waitFor();
  await editor.locator('[data-task-field="context"] input').fill('model/third');
  await chooseStatus(
    editor.locator('[data-task-field="status"] .status-select'),
    statuses[0]
  );
  await editor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await model.getByRole('button', { name: 'Create task', exact: true }).tap();
  await ready();
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  const third = model.getByRole('button', { name: /^model\/third \// });
  await third.tap();
  await model.getByRole('button', { name: 'Task actions', exact: true }).tap();
  await model.getByRole('button', { name: 'Delete task', exact: true }).tap();
  const deletion = page.getByRole('dialog', {
    name: 'Delete selected tasks',
    exact: true
  });
  await deletion
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await model
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    (await command(read, { action: 'processes', search_key: parent }))
      .processes[0].branches.length,
    2
  );
  assert.deepEqual(errors, []);
  console.log(
    'Quick Task Manager: empty selection/process, create/edit/delete/notes, user search, branch drafts, single save, three surfaces and touch320 OK'
  );
} catch (error) {
  console.error(error);
  console.error('PAGE ERRORS', errors);
  await page.screenshot({
    path: output.replace('.png', '-failure.png'),
    animations: 'disabled'
  });
  throw error;
} finally {
  await browser.close();
}
