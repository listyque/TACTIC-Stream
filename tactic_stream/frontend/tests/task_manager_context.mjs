import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  colorScheme: 'dark'
});
page.setDefaultTimeout(10000);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const base = process.argv[2],
  readCommand = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd';
let auth;
page.on('request', (request) => {
  if (
    request.url().endsWith('/admin/rpc') &&
    request.postDataJSON()?.args?.[1] === readCommand
  )
    auth = request.postDataJSON().args[0];
});
async function command(name, values) {
  const response = await page.request.post(base + '/admin/rpc', {
    data: { method: 'execute_cmd', args: [auth, name, values], kwargs: {} }
  });
  assert.equal(response.status(), 200);
  return (await response.json()).result.info;
}
const manager = page.getByRole('region', { name: 'Task Manager', exact: true });
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.task-manager-results')
        ?.getAttribute('aria-busy') === 'false'
  );
const managerTab = async () => {
  const tab = page.getByRole('tab', { name: 'Task Manager', exact: true });
  if (await tab.isVisible()) await tab.click();
};
async function scope(value) {
  const trigger = (await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .isVisible())
    ? manager.getByRole('button', { name: 'Choose task scope', exact: true })
    : manager.getByRole('button', { name: 'Task view options', exact: true });
  await trigger.click();
  const labels = {
    user: 'My tasks',
    team: 'Teams',
    project: 'Project tasks',
    selected: 'Selected',
    search_type: 'Search Type'
  };
  await manager
    .getByRole('checkbox', { name: labels[value], exact: true })
    .click();
  await ready();
  if ((await trigger.getAttribute('aria-expanded')) === 'true')
    await trigger.click();
}
async function parent(name) {
  const results = page.getByRole('tab', { name: 'Search', exact: true });
  if (await results.isVisible()) await results.click();
  const area = page.locator('.workspace-results');
  for (const checkbox of await area.getByRole('checkbox').all())
    if (await checkbox.isChecked()) await checkbox.uncheck();
  if (name)
    await area
      .getByRole('checkbox', { name: 'Select record: ' + name, exact: true })
      .check();
  await ready();
  await managerTab();
}
async function open() {
  await page.getByLabel('More options', { exact: true }).click();
  await page.getByRole('button', { name: 'Task Manager', exact: true }).click();
  await ready();
}
let releaseDelayed;
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
      new URLSearchParams({ search_type: 'contract/entity', view: 'table' })
  );
  await page.locator('.workspace-results[aria-busy="false"]').waitFor();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await open();
  const scopeTrigger = manager.getByRole('button', {
    name: 'Choose task scope',
    exact: true
  });
  await scopeTrigger.click();
  await manager
    .getByRole('group', { name: 'Task scope', exact: true })
    .waitFor();
  await scopeTrigger.click();
  await manager
    .getByRole('group', { name: 'Task scope', exact: true })
    .waitFor({ state: 'hidden' });
  await scope('selected');
  assert.equal(
    await manager.locator('tr[data-task-key]').count(),
    0,
    'Empty Selected does not expose project tasks'
  );
  await parent('Первый');
  assert.equal(await manager.locator('tr[data-task-key]').count(), 1);
  assert.match(
    await manager.locator('tr[data-task-key]').innerText(),
    /Первый/
  );
  await parent("O'Reilly");
  assert.match(
    await manager.locator('tr[data-task-key]').innerText(),
    /O'Reilly/
  );

  let signalDelayed;
  const delayed = new Promise((resolve) => {
    signalDelayed = resolve;
  });
  const release = new Promise((resolve) => {
    releaseDelayed = resolve;
  });
  let held = false;
  await page.route('**/admin/rpc', async (route) => {
    const request = route.request().postDataJSON();
    if (
      !held &&
      request?.args?.[1] === readCommand &&
      request.args[2]?.scope === 'object' &&
      request.args[2].identity.endsWith('code=A')
    ) {
      held = true;
      const response = await route.fetch();
      signalDelayed();
      await release;
      await route.fulfill({ response });
    } else await route.continue();
  });
  const results = page.getByRole('tab', { name: 'Search', exact: true });
  if (await results.isVisible()) await results.click();
  const area = page.locator('.workspace-results');
  await area
    .getByRole('checkbox', { name: "Select record: O'Reilly", exact: true })
    .uncheck();
  await area
    .getByRole('checkbox', { name: 'Select record: Первый', exact: true })
    .check();
  await delayed;
  await area
    .getByRole('checkbox', { name: 'Select record: Первый', exact: true })
    .uncheck();
  await area
    .getByRole('checkbox', { name: "Select record: O'Reilly", exact: true })
    .check();
  await ready();
  await managerTab();
  releaseDelayed();
  await page.unrouteAll({ behavior: 'wait' });
  assert.match(
    await manager.locator('tr[data-task-key]').innerText(),
    /O'Reilly/,
    'A late response cannot restore the previous Selected parent'
  );
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await manager
    .getByRole('button', { name: 'Edit selected tasks', exact: true })
    .click();
  const editor = page.getByRole('group', { name: 'Bulk fields', exact: true });
  await editor
    .getByRole('checkbox', { name: 'Description', exact: true })
    .check();
  await editor
    .locator('[data-task-field="description"] textarea')
    .fill('Retained Selected draft');
  await editor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .click();
  await scope('project');
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  assert.equal(
    await manager
      .getByRole('checkbox', { name: 'Selected', exact: true })
      .getAttribute('aria-checked'),
    'true',
    'A draft prevents changing the scope before the read guard'
  );
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  await parent('Первый');
  await manager
    .getByRole('region', { name: 'Pending task changes', exact: true })
    .waitFor();
  await parent("O'Reilly");
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await manager
    .getByRole('button', { name: 'Edit selected tasks', exact: true })
    .click();
  assert.equal(
    await editor
      .locator('[data-task-field="description"] textarea')
      .inputValue(),
    'Retained Selected draft'
  );
  await editor.getByRole('button', { name: 'Done', exact: true }).click();
  page.once('dialog', (dialog) => dialog.accept());
  await manager
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .click();
  await ready();

  await scope('project');
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .click();
  await manager.getByLabel('Group', { exact: true }).selectOption('status');
  await ready();
  await manager
    .getByLabel('Records per page', { exact: true })
    .selectOption('20');
  await ready();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .click();
  const editCommand =
    'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd';
  const { plans } = await command(editCommand, {
    action: 'prepare',
    plans: Array.from({ length: 21 }, (_, index) => ({
      operation: 'create',
      draft_id: 'context-page-' + index,
      search_key: 'contract/entity?project=one&code=A',
      process: 'publish'
    }))
  });
  await command(editCommand, {
    action: 'save',
    plans: plans.map((plan, index) => ({
      ...plan,
      data: {
        context: 'publish/context-page-' + index,
        assigned: 'admin',
        status: plan.statuses[0],
        description: 'Pagination fixture ' + index
      }
    }))
  });
  await manager.getByRole('button', { name: 'Refresh', exact: true }).click();
  await ready();
  assert.equal(await manager.locator('tr[data-task-key]').count(), 20);
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await manager
    .getByRole('button', { name: 'Load more tasks', exact: true })
    .click();
  await ready();
  const keys = await manager
    .locator('tr[data-task-key]')
    .evaluateAll((rows) => rows.map((row) => row.dataset.taskKey));
  assert.equal(keys.length, 23);
  assert.equal(new Set(keys).size, 23, 'Load more appends unique tasks');
  assert.equal(
    await manager.locator('tr.task-selected').count(),
    20,
    'Load more retains the previous selection'
  );
  assert.equal(
    await manager
      .getByRole('button', { name: 'Load more tasks', exact: true })
      .count(),
    0
  );
  await manager.getByRole('radio', { name: 'Gantt', exact: true }).click();
  await selectProject(page, 'two');
  await open();
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  assert.equal(
    await manager
      .getByRole('checkbox', { name: 'My tasks', exact: true })
      .getAttribute('aria-checked'),
    'true',
    'Another project starts with its own state'
  );
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  await scope('selected');
  await selectProject(page, 'one');
  await open();
  assert.equal(
    await manager
      .getByRole('radio', { name: 'Gantt', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  assert.equal(
    await manager
      .getByRole('checkbox', { name: 'Project tasks', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .click();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .click();
  assert.equal(
    await manager.getByLabel('Group', { exact: true }).inputValue(),
    'status'
  );
  assert.equal(
    await manager.getByLabel('Records per page', { exact: true }).inputValue(),
    '20'
  );
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .click();
  assert.deepEqual(errors, []);
  console.log(
    'Task Manager context: live Selected, stale read, draft retention, unique pagination and per-project restoration OK'
  );
} catch (error) {
  if (process.argv[3])
    await page.screenshot({ path: process.argv[3], animations: 'disabled' });
  throw error;
} finally {
  releaseDelayed?.();
  await browser.close();
}
