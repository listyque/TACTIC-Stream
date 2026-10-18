import { closeInspector } from './inspector_helpers.mjs';
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  hasTouch: true,
  colorScheme: 'dark'
});
page.setDefaultTimeout(10000);
await page.addInitScript(() => {
  Object.defineProperty(Crypto.prototype, 'randomUUID', {
    value: undefined,
    configurable: true
  });
});
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
let auth;
let projectedRecords = [];
page.on('request', (request) => {
  if (
    request.url().endsWith('/admin/rpc') &&
    request.postDataJSON()?.args?.[1] ===
      'tactic.ui.table.task_workspace.TaskWorkspaceCmd'
  )
    auth = request.postDataJSON().args[0];
  if (
    request.url().endsWith('/admin/rpc') &&
    request.postDataJSON()?.args?.[1] ===
      'tactic.ui.table.task_schedule.TaskScheduleCmd' &&
    request.postDataJSON().args[2]?.action === 'projection'
  )
    projectedRecords = request.postDataJSON().args[2].records;
});
const manager = page.getByRole('region', { name: 'Task Manager', exact: true });
const calendar = page.locator('#dock-task_calendar .task-calendar-view');
const editor = page.getByRole('group', { name: 'Bulk fields', exact: true }),
  draftEditor = page.getByRole('dialog', {
    name: 'Edit task draft',
    exact: true
  });
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.task-manager-results')
        ?.getAttribute('aria-busy') === 'false'
  );
const scheduleReady = async () => {
  await ready();
  await page.waitForFunction(
    () =>
      document
        .querySelector('.task-schedule-view')
        ?.getAttribute('aria-busy') === 'false'
  );
};
async function captureSurface(name) {
  mkdirSync('../.screenshots/collaboration-current', { recursive: true });
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
    bottom = await manager
      .locator('.task-manager-footer, .gantt-footer')
      .last()
      .boundingBox();
  await page.screenshot({
    path:
      '../.screenshots/collaboration-current/stream-manager-' + name + '.png',
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
async function chooseView(view) {
  await manager
    .getByRole(view === 'calendar' ? 'button' : 'radio', {
      name: { table: 'Table', gantt: 'Gantt', calendar: 'Calendar' }[view],
      exact: true
    })
    .tap();
}
async function command(name, values) {
  const response = await page.request.post(process.argv[2] + '/admin/rpc', {
    data: { method: 'execute_cmd', args: [auth, name, values], kwargs: {} }
  });
  const data = await response.json();
  assert.equal(response.status(), 200);
  return data.result.info;
}
const readCommand = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd';
const editCommand = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd';
const taskPage = () => command(readCommand, { scope: 'project', limit: 500 });
const countTasks = async () => (await taskPage()).total;
async function hourUnit(unit) {
  const response = await page.request.post(process.argv[2] + '/admin/rpc', {
    data: {
      method: 'execute_python_script',
      args: [
        auth,
        '',
        {
          code:
            'from pyasm.biz import ProjectSetting\nfrom pyasm.search import SearchType\n' +
            'setting = ProjectSetting.get_by_key("bid_duration_unit") or SearchType.create("config/prod_setting")\n' +
            'setting.set_value("key", "bid_duration_unit")\nsetting.set_value("value", ' +
            JSON.stringify(unit) +
            ')\nsetting.commit()'
        }
      ],
      kwargs: {}
    }
  });
  assert.equal(response.status(), 200, await response.text());
  await manager.getByRole('button', { name: 'Refresh', exact: true }).tap();
  await ready();
}
async function editSelected(value) {
  await manager
    .getByRole('button', { name: 'Edit selected tasks', exact: true })
    .tap();
  await editor.waitFor({ state: 'visible' });
  await editor
    .getByRole('checkbox', { name: 'Description', exact: true })
    .check();
  await editor.locator('[data-task-field="description"] textarea').fill(value);
  await editor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await editor.waitFor({ state: 'hidden' });
}
try {
  await page.goto(
    process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await page.locator('.project-picker').waitFor();
  await selectProject(page, 'one');
  await page.locator('.settings-menu > summary').tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  await manager.waitFor({ state: 'visible' });
  await ready();
  assert.equal(await manager.locator('tr[data-task-key]').count(), 2);
  const initial = await countTasks();
  const table = manager.getByRole('table', {
    name: 'Project task table',
    exact: true
  });
  const rows = () => table.locator('tr[data-task-key]');
  await page
    .locator('[data-dock="tasks"] > header')
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .tap();
  await page.waitForFunction(
    () => document.querySelector('.task-manager-results')?.clientWidth > 1100
  );
  assert.equal(
    Math.round((await rows().first().boundingBox()).height),
    58,
    'Handler task row height'
  );
  assert.equal(
    Math.round((await table.locator('thead').boundingBox()).height),
    34,
    'Handler table header height'
  );
  assert.equal(
    await table.locator('[data-task-column="process"]').count(),
    0,
    'Process is the second line of Object, as in current QML'
  );
  const expanderBounds = await rows()
    .first()
    .getByRole('button', { name: 'Expand task details', exact: true })
    .boundingBox();
  const checkboxBounds = await rows()
    .first()
    .getByRole('checkbox')
    .boundingBox();
  assert.ok(
    Math.abs(
      expanderBounds.y +
        expanderBounds.height / 2 -
        checkboxBounds.y -
        checkboxBounds.height / 2
    ) < 2,
    'Expand and select occupy one row'
  );
  await table.focus();
  await page.keyboard.press('Home');
  await page.keyboard.press('Space');
  assert.equal(
    await rows()
      .filter({ has: page.locator('input:checked') })
      .count(),
    1
  );
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await table.locator('tr.task-active').count(),
    1,
    'Active row is separate from bulk selection'
  );
  assert.equal(await table.locator('tr.task-selected').count(), 1);
  await page.keyboard.press('Shift+Home');
  assert.equal(
    await table.locator('tr.task-selected').count(),
    2,
    'Shift extends the visible row range'
  );
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .uncheck();
  await rows()
    .first()
    .getByRole('button', { name: 'Expand task details', exact: true })
    .tap();
  await ready();
  const details = manager.locator('.task-workspace-details').first();
  if (process.argv[3])
    await manager.locator('.task-manager-results').screenshot({
      path: process.argv[3].replace('.png', '-details-clean.png')
    });
  for (const field of ['priority', 'milestone_code', 'supervisor'])
    assert.equal(
      await details.locator(`[data-task-field="${field}"]`).count(),
      1,
      'Expanded details include hidden columns'
    );
  const oldDescription = (await taskPage()).tasks[0].description || '';
  assert.equal(
    await details.locator('textarea').getAttribute('readonly'),
    '',
    'Existing description starts read-only'
  );
  await details
    .getByRole('button', { name: 'Edit task description', exact: true })
    .tap();
  await details.locator('textarea').fill('Canceled description');
  await details.locator('textarea').press('Escape');
  assert.equal(
    await details.locator('textarea').inputValue(),
    oldDescription,
    'Escape restores the unstaged description'
  );
  await details
    .getByRole('button', { name: 'Edit task description', exact: true })
    .tap();
  await details
    .locator('[data-task-field="description"] textarea')
    .fill('Expanded row draft');
  await details
    .getByRole('button', { name: 'Finish editing description', exact: true })
    .tap();
  assert.equal(
    (await taskPage()).tasks[0].description || '',
    oldDescription,
    'Typing stages no database write'
  );
  const slider = details.getByRole('slider', { name: 'Progress', exact: true });
  await slider.focus();
  await slider.press('End');
  assert.equal(await slider.inputValue(), '100');
  assert.equal(
    Number(
      (await taskPage()).tasks[0].progress ||
        (await taskPage()).tasks[0].completion ||
        0
    ),
    0,
    'Slider stages without writing'
  );
  await slider.press('Home');
  await rows()
    .first()
    .getByRole('button', { name: 'Collapse task details', exact: true })
    .tap();
  await rows().first().locator('[data-task-cell="bid_duration"] button').tap();
  await ready();
  const cellEditor = manager.getByRole('dialog', {
    name: 'Edit task cell',
    exact: true
  });
  await cellEditor.waitFor({ state: 'visible' });
  await cellEditor
    .locator('[data-task-field="bid_duration"] input')
    .fill('13.5');
  await cellEditor.getByRole('button', { name: 'Close', exact: true }).tap();
  await rows()
    .first()
    .getByRole('button', { name: 'Expand task details', exact: true })
    .tap();
  await ready();
  assert.equal(
    await details
      .locator('[data-task-field="description"] textarea')
      .inputValue(),
    'Expanded row draft'
  );
  assert.equal(
    await details
      .locator('[data-task-field="bid_duration"] input')
      .inputValue(),
    '13.5',
    'Both editors use one draft'
  );
  if (process.argv[3])
    await manager.locator('.task-manager-results').screenshot({
      path: process.argv[3].replace('.png', '-details-desktop.png')
    });
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await details
      .locator('[data-task-field="description"] textarea')
      .inputValue(),
    'Expanded row draft',
    'Expanded forms reload their native plan after Save'
  );
  assert.equal(Number((await taskPage()).tasks[0].bid_duration), 13.5);
  await hourUnit('minute');
  assert.equal(
    await details
      .locator('[data-task-field="bid_duration"] input')
      .inputValue(),
    '0.23',
    'Native minutes display as rounded hours'
  );
  await details.locator('[data-task-field="bid_duration"] input').fill('2.5');
  await details
    .locator('[data-task-field="bid_duration"] input')
    .press('Enter');
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    Number((await taskPage()).tasks[0].bid_duration),
    150,
    'Hours edit stores native minutes'
  );
  await hourUnit('hour');
  await details.locator('[data-task-field="bid_duration"] input').fill('13.5');
  await details
    .locator('[data-task-field="bid_duration"] input')
    .press('Enter');
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  await details
    .getByRole('button', { name: 'Edit task description', exact: true })
    .tap();
  await details
    .locator('[data-task-field="description"] textarea')
    .fill('Discard expanded draft');
  await details
    .getByRole('button', { name: 'Finish editing description', exact: true })
    .tap();
  page.once('dialog', (dialog) => dialog.accept());
  await manager
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await details
      .locator('[data-task-field="description"] textarea')
      .inputValue(),
    'Expanded row draft'
  );
  await rows()
    .first()
    .getByRole('button', { name: 'Collapse task details', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Task columns', exact: true })
    .tap();
  await manager
    .getByRole('checkbox', { name: 'Assignee', exact: true })
    .uncheck();
  await manager
    .getByRole('spinbutton', { name: 'Width of Start / Deadline', exact: true })
    .fill('233');
  await page.keyboard.press('Enter');
  for (let index = 0; index < 4; index++)
    await manager
      .getByRole('group', { name: 'Start / Deadline', exact: true })
      .getByRole('button', { name: 'Move column left', exact: true })
      .tap();
  assert.equal(
    await table
      .locator('th[data-task-column]')
      .first()
      .getAttribute('data-task-column'),
    'dates'
  );
  assert.equal(
    await table.locator('th[data-task-column="assigned"]').count(),
    0
  );
  assert.ok(
    Math.abs(
      (await table.locator('th[data-task-column="dates"]').boundingBox())
        .width - 240
    ) < 2
  );
  await page
    .getByRole('button', { name: 'Close panel: Task Manager', exact: true })
    .tap();
  await manager.waitFor({ state: 'hidden' });
  await page.locator('.settings-menu > summary').tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  await ready();
  await page
    .locator('[data-dock="tasks"] > header')
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .tap();
  await page.waitForFunction(
    () => document.querySelector('.task-manager-results')?.clientWidth > 1100
  );
  await page.waitForFunction(
    () =>
      document.querySelector('.task-workspace-table th[data-task-column]')
        ?.dataset.taskColumn === 'dates'
  );
  assert.equal(
    await table
      .locator('th[data-task-column]')
      .first()
      .getAttribute('data-task-column'),
    'dates',
    'Column order survives reopening'
  );
  assert.equal(
    await table.locator('th[data-task-column="assigned"]').count(),
    0
  );
  assert.ok(
    Math.abs(
      (await table.locator('th[data-task-column="dates"]').boundingBox())
        .width - 240
    ) < 2
  );
  await manager
    .getByRole('button', { name: 'Task columns', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await rows()
    .first()
    .getByRole('button', { name: 'Expand task details', exact: true })
    .tap();
  await ready();
  const objectBounds = await rows()
    .first()
    .locator('[data-task-cell="object"]')
    .boundingBox();
  const leadingBounds = await rows()
    .first()
    .locator('.task-row-controls')
    .boundingBox();
  assert.ok(
    Math.abs(objectBounds.x - leadingBounds.x - leadingBounds.width) < 1,
    'Expanded Object stays beside controls after column reorder'
  );
  await rows()
    .first()
    .getByRole('button', { name: 'Collapse task details', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Task columns', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Reset task columns', exact: true })
    .tap();
  await manager.getByLabel('Group', { exact: true }).selectOption('object');
  await ready();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await table.locator('.task-group button').first().tap();
  assert.equal(
    await manager
      .getByRole('checkbox', { name: 'Select all tasks', exact: true })
      .isChecked(),
    true,
    'Header reflects visible rows'
  );
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .uncheck();
  assert.equal(
    await manager.getByRole('region', { name: 'Pending task changes' }).count(),
    0
  );
  assert.match(
    await manager.locator('[data-frame=taskBulkCount]').innerText(),
    /1 task selected/,
    'Collapsed selection is preserved'
  );
  await manager
    .getByRole('button', { name: 'Task columns', exact: true })
    .tap();
  await manager.getByLabel('Group', { exact: true }).selectOption('none');
  await ready();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await editSelected('Workspace staged description');
  assert.equal(
    await manager.getByRole('region', { name: 'Pending task changes' }).count(),
    1
  );
  await page
    .getByRole('button', { name: 'Close panel: Task Manager', exact: true })
    .tap();
  await manager.waitFor({ state: 'hidden' });
  await page.locator('.settings-menu > summary').tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  await manager.getByRole('region', { name: 'Pending task changes' }).waitFor();
  await page.getByLabel('More options', { exact: true }).tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Reset workspace layout', exact: true })
    .tap();
  await manager.waitFor({ state: 'hidden' });
  await page.locator('.settings-menu > summary').tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  await manager.getByRole('region', { name: 'Pending task changes' }).waitFor();
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await manager.getByRole('region', { name: 'Pending task changes' }).count(),
    0
  );
  assert.equal(await countTasks(), initial);
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await editSelected('Local pending values');
  const current = await taskPage(),
    first = current.tasks[0];
  const parent = current.parents.find(
    (parent) => parent.code === first.search_code
  );
  const remote = (
    await command(editCommand, {
      action: 'prepare',
      plans: [
        {
          task_key: first.__search_key__,
          search_key: parent.__search_key__,
          process: first.process
        }
      ]
    })
  ).plans[0];
  await command(editCommand, {
    action: 'save',
    plans: [{ ...remote, data: { description: 'Changed remotely' } }]
  });
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(
    await manager.getByRole('region', { name: 'Pending task changes' }).count(),
    1,
    'A conflict retains local drafts'
  );
  await manager
    .getByRole('button', { name: 'Reload draft revisions', exact: true })
    .tap();
  const conflict = page.getByRole('dialog', {
    name: 'Review task conflicts',
    exact: true
  });
  await conflict.waitFor({ state: 'visible' });
  assert.match(await conflict.innerText(), /Changed remotely/);
  assert.match(await conflict.innerText(), /Local pending values/);
  await conflict
    .getByRole('button', { name: 'Use latest revisions', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.ok(
    (await taskPage()).tasks.every(
      (task) => task.description === 'Local pending values'
    )
  );
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await editSelected('Saved with a lost reply');
  let lost = false;
  const dropReply = async (route) => {
    const payload = route.request().postDataJSON();
    if (
      !lost &&
      payload?.args?.[1] === editCommand &&
      payload.args[2]?.action === 'save'
    ) {
      lost = true;
      await route.fetch();
      await route.abort('failed');
    } else await route.continue();
  };
  await page.route('**/admin/rpc', dropReply);
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(lost, true);
  assert.equal(
    await manager
      .getByRole('button', { name: 'Save task changes', exact: true })
      .isDisabled(),
    true
  );
  assert.ok(
    (await taskPage()).tasks.every(
      (task) => task.description === 'Saved with a lost reply'
    )
  );
  await page.unroute('**/admin/rpc', dropReply);
  page.once('dialog', (dialog) => dialog.accept());
  await manager
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await ready();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await manager.getByRole('button', { name: 'Create task', exact: true }).tap();
  await ready();
  assert.equal(
    await editor.isVisible(),
    false,
    'Create adds an expanded virtual row, as in Handler'
  );
  const creation = manager.locator('.task-workspace-details').first();
  await creation
    .locator('[data-task-field="context"] input')
    .fill('publish/browser-new');
  const assignee = creation.locator(
    '[data-task-field="assigned"] .user-combo-box'
  );
  await assignee.locator('summary').tap();
  await assignee
    .locator('.user-combo-option')
    .filter({ hasText: 'admin' })
    .first()
    .tap();
  await creation
    .locator('[data-task-field="description"] textarea')
    .fill('New staged workspace task');
  assert.equal(await countTasks(), initial, 'A new row is virtual until Save');
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(await countTasks(), initial + 1);
  await manager
    .getByLabel('Search tasks', { exact: true })
    .fill('New staged workspace task');
  await manager.getByLabel('Search tasks', { exact: true }).press('Enter');
  await ready();
  assert.equal(await manager.locator('tr[data-task-key]').count(), 1);
  await manager
    .locator('tbody')
    .getByRole('button', { name: 'Task actions', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Task Inspector', exact: true })
    .tap();
  const inspector = page.locator('.notes-panel[open]');
  await inspector.waitFor({ state: 'visible' });
  await page.waitForFunction(
    () =>
      document
        .querySelector('#dock-notes .notes-panel[open]')
        ?.getAttribute('aria-busy') === 'false'
  );
  await page.setViewportSize({ width: 320, height: 740 });
  const noteField = inspector.getByRole('textbox', {
    name: 'Note text',
    exact: true
  });
  const noteCalls = [],
    noteListener = (request) => {
      if (
        request.url().endsWith('/admin/rpc') &&
        request.postDataJSON()?.args?.[1] ===
          'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd'
      )
        noteCalls.push(request);
    };
  page.on('request', noteListener);
  await noteField.fill('Phone note draft');
  await noteField.press('End');
  await noteField.press('Enter');
  assert.equal(
    await noteField.inputValue(),
    'Phone note draft\n',
    'Phone Enter inserts a line in notes'
  );
  assert.equal(noteCalls.length, 0, 'Enter does not send a phone note');
  assert(
    await inspector.evaluate((node) => node.scrollWidth <= node.clientWidth)
  );
  assert.equal(
    await inspector.locator('.task-detail-fields').count(),
    0,
    'Phone details start collapsed'
  );
  assert(
    (await inspector.locator('.notes-timeline').boundingBox()).height > 200,
    'Notes have usable phone height'
  );
  await inspector
    .getByRole('button', { name: 'Task actions', exact: true })
    .tap();
  await inspector
    .getByRole('button', { name: 'Expand Task Inspector', exact: true })
    .tap();
  await inspector
    .locator('[data-frame=taskInspectorStatusField]')
    .waitFor({ state: 'visible' });
  await inspector
    .getByRole('button', { name: 'Task actions', exact: true })
    .tap();
  await inspector
    .getByRole('button', { name: 'Collapse Task Inspector', exact: true })
    .tap();
  const notices = page.getByRole('button', {
    name: 'Dismiss notification',
    exact: true
  });
  for (let i = 0; i < 10 && (await notices.count()); i++)
    await notices.first().click();
  await inspector.evaluate((node) => {
    node.scrollTop = 0;
  });
  await page.screenshot({ path: '../.screenshots/mobile-task-inspector.png' });
  await noteField.fill('');
  page.off('request', noteListener);
  await page.setViewportSize({ width: 1280, height: 900 });
  await closeInspector(page);
  await manager
    .locator('tbody')
    .getByRole('button', { name: 'Task actions', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Task timesheet', exact: true })
    .tap();
  const timesheet = page.getByRole('dialog', {
    name: 'Task timesheet',
    exact: true
  });
  await timesheet.waitFor({ state: 'visible' });
  await timesheet.getByRole('button', { name: 'Close', exact: true }).tap();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await manager
    .getByRole('button', { name: 'Delete selected tasks', exact: true })
    .tap();
  const deletion = page.getByRole('dialog', {
    name: 'Delete selected tasks',
    exact: true
  });
  await deletion.waitFor({ state: 'visible' });
  await deletion
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  assert.equal(await countTasks(), initial + 1, 'Deletion is staged');
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.equal(await countTasks(), initial);
  await manager.getByLabel('Search tasks', { exact: true }).fill('');
  await manager.getByLabel('Search tasks', { exact: true }).press('Enter');
  await ready();
  const baseline = (await taskPage()).tasks;
  await chooseView('gantt');
  await scheduleReady();
  const gantt = manager.getByRole('region', {
    name: 'Task Gantt',
    exact: true
  });
  assert.equal(await gantt.locator('[data-task-key]').count(), 2);
  for (const box of await gantt.getByRole('checkbox').all()) await box.check();
  await editSelected('Description must survive schedule undo');
  await gantt
    .getByRole('button', { name: 'Schedule options', exact: true })
    .tap();
  await gantt
    .getByRole('checkbox', { name: 'Working days only', exact: true })
    .check();
  await gantt
    .getByRole('button', { name: 'Shift one day later', exact: true })
    .tap();
  await scheduleReady();
  assert.ok(
    projectedRecords
      .find((row) => row.taskCode === baseline[0].__search_key__)
      .start.startsWith('2030-01-07')
  );
  assert.ok(
    (await taskPage()).tasks
      .find((row) => row.code === baseline[0].code)
      .bid_start_date.startsWith('2030-01-04'),
    'Schedule remains pending until Save'
  );
  await gantt
    .getByRole('button', { name: 'Undo schedule change', exact: true })
    .tap();
  await scheduleReady();
  assert.ok(
    projectedRecords
      .find((row) => row.taskCode === baseline[0].__search_key__)
      .start.startsWith('2030-01-04')
  );
  assert.equal(
    await gantt.locator('[data-task-key].pending').count(),
    2,
    'Description drafts survive schedule undo'
  );
  await gantt
    .getByRole('button', { name: 'Redo schedule change', exact: true })
    .tap();
  await scheduleReady();
  await gantt
    .locator('[data-task-key]')
    .first()
    .getByRole('button', { name: 'Edit schedule', exact: true })
    .tap();
  const scheduleEditor = page.getByRole('dialog', {
    name: 'Edit schedule',
    exact: true
  });
  await scheduleEditor.waitFor({ state: 'visible' });
  await scheduleEditor.getByLabel('Progress', { exact: true }).fill('35');
  await scheduleEditor.getByLabel('Progress', { exact: true }).press('Enter');
  await scheduleEditor.waitFor({ state: 'hidden' });
  await scheduleReady();
  assert.equal(
    projectedRecords.find((row) => row.taskCode === baseline[0].__search_key__)
      .progress,
    35
  );
  await gantt
    .getByRole('button', { name: 'Undo schedule change', exact: true })
    .tap();
  await scheduleReady();
  assert.equal(
    projectedRecords.find((row) => row.taskCode === baseline[0].__search_key__)
      .progress,
    0
  );
  await gantt
    .getByRole('button', { name: 'Redo schedule change', exact: true })
    .tap();
  await scheduleReady();
  const beforeDrag = JSON.parse(JSON.stringify(projectedRecords));
  await gantt
    .getByRole('button', { name: 'Schedule options', exact: true })
    .tap();
  await gantt
    .getByRole('combobox', { name: 'Timeline scale', exact: true })
    .selectOption('days');
  await gantt
    .getByRole('button', { name: 'Schedule options', exact: true })
    .tap();
  const bar = gantt.locator('.task-gantt-move').first(),
    rect = await bar.boundingBox();
  await page.mouse.move(rect.x + rect.width / 2, rect.y + rect.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    rect.x + rect.width / 2 + 56,
    rect.y + rect.height / 2,
    { steps: 6 }
  );
  await page.mouse.up();
  await scheduleReady();
  assert.notEqual(
    projectedRecords[0].start,
    beforeDrag[0].start,
    'Mouse moves the native staged schedule'
  );
  assert.notEqual(
    projectedRecords[1].start,
    beforeDrag[1].start,
    'Selected peers move together'
  );
  await page.keyboard.press('Control+z');
  await scheduleReady();
  assert.equal(projectedRecords[0].start, beforeDrag[0].start);
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await scheduleReady();
  const savedSchedule = (await taskPage()).tasks;
  assert.ok(
    savedSchedule.every(
      (row) => row.description === 'Description must survive schedule undo'
    )
  );
  const savedFirst = savedSchedule.find((row) => row.code === baseline[0].code);
  assert.ok(
    savedFirst.bid_start_date.startsWith('2030-01-07 09:13'),
    'Original start time is retained'
  );
  assert.ok(
    savedFirst.bid_end_date.startsWith('2030-01-09 17:20'),
    'Original deadline time is retained'
  );
  assert.equal(Number(savedFirst.progress ?? savedFirst.completion), 35);
  await gantt
    .getByRole('button', { name: 'Schedule options', exact: true })
    .tap();
  await gantt
    .getByRole('checkbox', { name: 'Group workload by assignee', exact: true })
    .check();
  await scheduleReady();
  assert.ok(
    (await gantt.locator('[data-frame="ganttGroupSummary"]').count()) > 0
  );
  await gantt
    .getByRole('checkbox', { name: 'Group workload by assignee', exact: true })
    .uncheck();
  await scheduleReady();
  await gantt
    .getByRole('button', { name: 'Schedule options', exact: true })
    .tap();
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-gantt.png'),
      animations: 'disabled'
    });
  await captureSurface('gantt');
  await chooseView('calendar');
  await scheduleReady();
  await calendar
    .getByLabel('Calendar month', { exact: true })
    .fill('2030-01-01');
  await scheduleReady();
  assert.equal(await calendar.locator('.task-calendar-day').count(), 42);
  await calendar.getByRole('button', { name: 'Agenda', exact: true }).tap();
  assert.equal(
    await calendar.locator('[data-frame="calendarAgendaAction"]').count(),
    2
  );
  await calendar.getByRole('button', { name: 'Agenda', exact: true }).tap();
  await calendar
    .locator('[data-date="2030-01-09"] [data-frame="calendarDayAction"]')
    .tap();
  await scheduleReady();
  assert.equal(
    await manager.locator('[data-task-key]').count(),
    1,
    'Selecting a day uses the native deadline filter'
  );
  await calendar
    .getByRole('button', { name: 'Clear selected day', exact: true })
    .tap();
  await scheduleReady();
  await page.setViewportSize({ width: 320, height: 740 });
  await calendar
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  await manager.locator('.task-manager-scope').waitFor({ state: 'hidden' });
  assert.equal(
    await manager.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  const toolbarBounds = await manager
    .locator('.task-manager-toolbar')
    .boundingBox();
  assert.equal(
    Math.round(toolbarBounds.height),
    40,
    'One compact toolbar on the phone'
  );
  assert.equal(
    await manager.getByLabel('Search tasks', { exact: true }).isVisible(),
    false
  );
  await manager.getByRole('button', { name: 'Open search', exact: true }).tap();
  assert.ok(
    (await manager.getByLabel('Search tasks', { exact: true }).boundingBox())
      .width >= 52,
    'Search stays available at 320px'
  );
  await manager.getByLabel('Search tasks', { exact: true }).press('Escape');
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  const triggerBox = await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .boundingBox();
  const popupBox = await manager
    .locator('.task-manager-options > .account-panel')
    .boundingBox();
  assert.ok(
    popupBox.y >= triggerBox.y + triggerBox.height ||
      popupBox.y + popupBox.height <= triggerBox.y,
    'A scrolling popup keeps its trigger reachable'
  );
  await manager
    .getByRole('button', { name: 'Choose task scope', exact: true })
    .tap();
  const scopeGroup = manager.getByRole('group', {
    name: 'Task scope',
    exact: true
  });
  await scopeGroup.waitFor();
  assert.ok((await scopeGroup.evaluate((el) => el.clientWidth)) > 100);
  await page.keyboard.press('Escape');
  assert.equal(
    await manager
      .getByRole('button', { name: 'Task view options', exact: true })
      .evaluate((el) => el === document.activeElement),
    true
  );
  assert.equal(
    await manager
      .getByRole('button', { name: 'Calendar', exact: true })
      .count(),
    0,
    'Phone uses the task list'
  );
  assert.equal(await manager.locator('.task-schedule-view').count(), 0);
  await page.setViewportSize({ width: 1280, height: 900 });
  await scheduleReady();
  await chooseView('calendar');
  await scheduleReady();
  const calendarBounds = await calendar
    .locator('[data-date="2030-01-06"]')
    .boundingBox();
  assert.ok(
    calendarBounds.x + calendarBounds.width <= 1280,
    'Desktop calendar returns after leaving phone mode'
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-calendar.png'),
      animations: 'disabled'
    });
  await captureSurface('calendar');
  await chooseView('gantt');
  await scheduleReady();
  await gantt
    .locator('[data-task-key]')
    .first()
    .getByRole('button', { name: 'Edit schedule', exact: true })
    .tap();
  await scheduleEditor.waitFor({ state: 'visible' });
  await scheduleEditor.getByLabel('Progress', { exact: true }).fill('55');
  await scheduleEditor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await scheduleReady();
  await gantt
    .getByRole('button', { name: 'Undo schedule change', exact: true })
    .tap();
  await scheduleReady();
  assert.equal(
    projectedRecords.find((row) => row.taskCode === baseline[0].__search_key__)
      .progress,
    35,
    'Touch editing shares schedule undo'
  );
  assert.equal(
    await manager.getByRole('region', { name: 'Pending task changes' }).count(),
    0
  );
  await chooseView('table');
  await page.setViewportSize({ width: 1280, height: 900 });
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-desktop.png'),
      animations: 'disabled'
    });
  await captureSurface('table');
  await page.setViewportSize({ width: 320, height: 740 });
  if (await calendar.isVisible())
    await calendar
      .getByRole('button', { name: 'Task Manager', exact: true })
      .tap();
  assert.equal(
    await manager.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true,
    'No page overflow at 320px'
  );
  assert.ok(
    (await manager
      .locator('.task-manager-results')
      .evaluate((el) => el.clientHeight)) > 280,
    'Results have usable height'
  );
  const horizontal = await manager
    .locator('.task-manager-results')
    .evaluate((el) => {
      el.scrollLeft = el.scrollWidth;
      return el.scrollLeft;
    });
  assert.equal(
    horizontal,
    0,
    'Phone task list requires no horizontal scrolling'
  );
  assert.equal(
    await table.count(),
    0,
    'Desktop table is replaced by compact task rows'
  );
  if (process.argv[3])
    await page.screenshot({ path: process.argv[3], animations: 'disabled' });
  await manager.locator('.task-manager-results').evaluate((el) => {
    el.scrollLeft = 0;
  });
  await manager
    .locator('.mobile-task-list article')
    .first()
    .getByRole('button', { name: 'Task actions', exact: true })
    .tap();
  await manager.getByRole('button', { name: 'Edit task', exact: true }).tap();
  await draftEditor.waitFor({ state: 'visible' });
  await draftEditor
    .locator('[data-task-field="description"] textarea')
    .scrollIntoViewIfNeeded();
  const touchBounds = await draftEditor
    .locator('[data-task-field="description"] textarea')
    .boundingBox();
  assert.ok(
    touchBounds.x >= 0 && touchBounds.x + touchBounds.width <= 320,
    'Task editing fits the phone'
  );
  assert.ok(touchBounds.width > 220);
  await draftEditor
    .locator('[data-task-field="description"] textarea')
    .fill('Touch expanded draft');
  await draftEditor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await draftEditor.waitFor({ state: 'hidden' });
  assert.ok(
    !(await taskPage()).tasks.some(
      (task) => task.description === 'Touch expanded draft'
    )
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-expanded.png'),
      animations: 'disabled'
    });
  page.once('dialog', (dialog) => dialog.accept());
  await manager
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await ready();
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await manager
    .getByRole('button', { name: 'Project milestones', exact: true })
    .tap();
  const milestones = page.getByRole('dialog', {
    name: 'Project milestones',
    exact: true
  });
  const milestonesReady = () =>
    page.waitForFunction(
      () =>
        document
          .querySelector('.milestone-results')
          ?.getAttribute('aria-busy') === 'false'
    );
  await milestones.waitFor({ state: 'visible' });
  await milestonesReady();
  for (const name of ['Release A', 'Release B']) {
    await milestones.locator('[data-frame="milestoneCreate"]').tap();
    const row = milestones.locator('[data-milestone]').first();
    await row.getByLabel('Milestone name', { exact: true }).fill(name);
    await row.getByLabel('Due date', { exact: true }).fill('2030-01-10');
  }
  const milestoneRow = (name) =>
    milestones.getByRole('group', { name, exact: true });
  await milestoneRow('Release A')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  assert.equal(
    await milestoneRow('Release B')
      .getByRole('button', { name: 'Save milestone', exact: true })
      .isEnabled(),
    true,
    'Saving A keeps the independent new B draft'
  );
  await milestoneRow('Release B')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  const milestoneCommand = 'tactic.ui.table.milestones.MilestoneCmd';
  let milestoneData = await command(milestoneCommand, {});
  assert.equal(
    milestoneData.records.length,
    2,
    'New draft codes become native codes without duplicate inserts'
  );
  const releaseA = milestoneData.records.find(
    (row) => row.description === 'Release A'
  );
  await milestoneRow('Release A')
    .getByLabel('Milestone name', { exact: true })
    .fill('Release A local');
  await milestoneRow('Release B')
    .getByLabel('Milestone name', { exact: true })
    .fill('Release B local');
  await milestoneRow('Release A local')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  assert.equal(
    await milestoneRow('Release B local')
      .getByRole('button', { name: 'Save milestone', exact: true })
      .isEnabled(),
    true
  );
  await milestoneRow('Release B local')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  await milestoneRow('Release A local')
    .getByLabel('Milestone name', { exact: true })
    .fill('Pending local release');
  milestoneData = await command(milestoneCommand, {});
  await command(milestoneCommand, {
    action: 'update',
    code: releaseA.code,
    expected_revision: milestoneData.records.find(
      (row) => row.code === releaseA.code
    ).revision,
    data: { description: 'External release', due_date: '2030-01-11' }
  });
  await milestoneRow('Pending local release')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  assert.match(
    await milestoneRow('Pending local release').innerText(),
    /Milestones changed/
  );
  page.once('dialog', (dialog) => dialog.accept());
  await milestoneRow('Pending local release')
    .getByRole('button', {
      name: 'Review current milestone revision',
      exact: true
    })
    .tap();
  await milestonesReady();
  await milestoneRow('Pending local release')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  await milestones
    .getByRole('searchbox', { name: 'Search milestones', exact: true })
    .fill('Release B');
  assert.equal(await milestones.locator('[data-milestone]').count(), 1);
  await milestoneRow('Release B local')
    .getByRole('button', { name: 'Delete milestone', exact: true })
    .tap();
  await milestones
    .locator('.milestone-delete')
    .getByRole('button', { name: 'Delete milestone', exact: true })
    .tap();
  await milestonesReady();
  await milestones
    .getByRole('searchbox', { name: 'Search milestones', exact: true })
    .fill('');
  assert.equal(await milestones.locator('[data-milestone]').count(), 1);
  assert.equal(
    await milestones.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true,
    'Milestones fit touch320'
  );
  assert.ok(
    (await milestones
      .locator('.milestone-results')
      .evaluate((el) => el.clientHeight)) > 280
  );
  assert.ok(
    (await milestones
      .locator('.milestone-frame-search')
      .evaluate((el) => el.clientHeight)) < 70,
    'Search does not consume the scrollable list height'
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-milestones.png'),
      animations: 'disabled'
    });
  await page.setViewportSize({ width: 1280, height: 900 });
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-milestones-desktop.png'),
      animations: 'disabled'
    });
  await page.setViewportSize({ width: 320, height: 740 });
  await milestones.getByRole('button', { name: 'Close', exact: true }).tap();
  await milestones.waitFor({ state: 'hidden' });
  await manager
    .getByRole('button', { name: 'Task view options', exact: true })
    .tap();
  await manager
    .getByRole('checkbox', { name: 'Select all tasks', exact: true })
    .check();
  await page.keyboard.press('Escape');
  await manager
    .getByRole('button', { name: 'Edit selected tasks', exact: true })
    .tap();
  await editor.waitFor({ state: 'visible' });
  await editor
    .getByRole('checkbox', { name: 'Milestone', exact: true })
    .check();
  await editor
    .getByRole('combobox', { name: 'Milestone', exact: true })
    .selectOption(releaseA.code);
  await editor
    .getByRole('button', { name: 'Apply to draft', exact: true })
    .tap();
  await editor.waitFor({ state: 'hidden' });
  await manager
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await ready();
  assert.ok(
    (await taskPage()).tasks.every(
      (row) => row.milestone_code === releaseA.code
    ),
    'Assignment uses native task Save'
  );
  await page.setViewportSize({ width: 1280, height: 900 });
  await chooseView('gantt');
  await scheduleReady();
  const markerOverview = await gantt
    .locator('[data-frame^="ganttOverviewMarker"]')
    .first()
    .boundingBox();
  await page.mouse.click(
    markerOverview.x + markerOverview.width / 2,
    markerOverview.y + markerOverview.height / 2
  );
  await gantt.locator('[data-frame^="ganttMarkerOpen"]').first().tap();
  await milestones.waitFor({ state: 'visible' });
  await milestonesReady();
  assert.match(
    await milestones.locator('[data-frame="milestonePlanTitle"]').innerText(),
    /\/ 2/,
    'Markers and editor share the linked-task plan'
  );
  await milestones
    .locator('[data-milestone]')
    .getByRole('button', { name: 'Delete milestone', exact: true })
    .tap();
  await milestones
    .locator('.milestone-delete')
    .getByRole('button', { name: 'Delete milestone', exact: true })
    .tap();
  await milestonesReady();
  assert.match(
    await milestones.innerText(),
    /assigned to tasks and cannot be deleted/
  );
  await milestones
    .locator('.milestone-delete')
    .getByRole('button', { name: 'Cancel', exact: true })
    .tap();
  await milestones.locator('[data-frame="milestoneCreate"]').tap();
  await milestones
    .locator('[data-milestone]')
    .first()
    .getByLabel('Milestone name', { exact: true })
    .fill('Lost milestone reply');
  let lostMilestone = false;
  const dropMilestoneReply = async (route) => {
    const payload = route.request().postDataJSON();
    if (
      !lostMilestone &&
      payload?.args?.[1] === milestoneCommand &&
      payload.args[2]?.action === 'create'
    ) {
      lostMilestone = true;
      await route.fetch();
      await route.abort('failed');
    } else await route.continue();
  };
  await page.route('**/admin/rpc', dropMilestoneReply);
  await milestoneRow('Lost milestone reply')
    .getByRole('button', { name: 'Save milestone', exact: true })
    .tap();
  await milestonesReady();
  await page.unroute('**/admin/rpc', dropMilestoneReply);
  assert.equal(lostMilestone, true);
  assert.equal(
    await milestoneRow('Lost milestone reply')
      .getByRole('button', { name: 'Save milestone', exact: true })
      .isDisabled(),
    true
  );
  assert.equal(
    (await command(milestoneCommand, {})).records.filter(
      (row) => row.description === 'Lost milestone reply'
    ).length,
    1
  );
  await milestones
    .getByRole('button', { name: 'Inspect current server data', exact: true })
    .tap();
  await milestonesReady();
  page.once('dialog', (dialog) => dialog.accept());
  await milestones
    .locator('aside.notice[role="alert"]')
    .getByRole('button', { name: 'Discard changes', exact: true })
    .tap();
  assert.equal(
    await milestones
      .getByRole('button', { name: 'Inspect current server data', exact: true })
      .count(),
    0
  );
  await milestones.getByRole('button', { name: 'Close', exact: true }).tap();
  await milestones.waitFor({ state: 'hidden' });
  const desktop = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    hasTouch: false,
    colorScheme: 'dark',
    storageState: await page.context().storageState()
  });
  desktop.on('pageerror', (error) => errors.push(error.message));
  await desktop.goto(process.argv[2] + '/');
  await desktop.locator('.project-picker').waitFor();
  await desktop.locator('.settings-menu > summary').click();
  await desktop
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .click();
  const desktopManager = desktop.getByRole('region', {
    name: 'Task Manager',
    exact: true
  });
  await desktopManager
    .locator('.task-manager-results[aria-busy="false"]')
    .waitFor();
  assert.equal(
    await desktopManager
      .getByRole('radio', { name: 'Gantt', exact: true })
      .getAttribute('aria-checked'),
    'true',
    'Workspace view survives a browser reload'
  );
  await desktopManager
    .getByRole('radio', { name: 'Table', exact: true })
    .click();
  await desktop
    .locator('[data-dock="tasks"] > header')
    .getByRole('button', { name: 'Maximize panel', exact: true })
    .click();
  await desktop.waitForFunction(
    () => document.querySelector('.task-manager-results')?.clientWidth > 1100
  );
  const objectHeader = desktopManager.locator('th[data-task-column="object"]'),
    dateHeader = desktopManager.locator('th[data-task-column="dates"]');
  const originalWidth = (await dateHeader.boundingBox()).width;
  const handle = dateHeader.getByRole('separator', {
      name: 'Resize Start / Deadline',
      exact: true
    }),
    bounds = await handle.boundingBox();
  await desktop.mouse.move(
    bounds.x + bounds.width / 2,
    bounds.y + bounds.height / 2
  );
  await desktop.mouse.down();
  await desktop.mouse.move(
    bounds.x + bounds.width / 2 + 35,
    bounds.y + bounds.height / 2,
    { steps: 5 }
  );
  await desktop.mouse.up();
  assert.ok(
    Math.abs((await dateHeader.boundingBox()).width - originalWidth - 35) < 2,
    'Mouse resizes a column'
  );
  await handle.focus();
  await desktop.keyboard.press('ArrowRight');
  assert.ok(
    Math.abs((await dateHeader.boundingBox()).width - originalWidth - 45) < 2,
    'Keyboard resizes the same preference'
  );
  await objectHeader.click({ button: 'right' });
  const columnMenu = desktopManager.locator('[aria-label="Column actions"]');
  await columnMenu
    .getByRole('menuitemradio', { name: 'Group by column', exact: true })
    .click();
  await desktopManager
    .locator('.task-manager-results[aria-busy="false"]')
    .waitFor();
  assert.equal(await desktopManager.locator('.task-group').count(), 2);
  await desktop
    .getByRole('button', { name: 'Close panel: Task Manager', exact: true })
    .click();
  await desktop.context().close();
  await page
    .getByRole('button', { name: 'Close panel: Task Manager', exact: true })
    .tap();
  await manager.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'Task Manager: shared inline/expanded drafts, selection, columns/resize, calendar/Gantt, milestones and touch320 OK'
  );
} catch (error) {
  console.error(error);
  console.error('PAGE ERRORS', errors);
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-failure.png'),
      animations: 'disabled'
    });
  throw error;
} finally {
  await browser.close();
}
