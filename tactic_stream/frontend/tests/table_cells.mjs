import { closeInspector } from './inspector_helpers.mjs';
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  hasTouch: true,
  colorScheme: 'dark'
});
await page.addInitScript(() =>
  localStorage.setItem(
    'tactic_stream.network',
    JSON.stringify({ updateMode: 'poll', pollInterval: 5, batchDelay: 200 })
  )
);
page.setDefaultTimeout(10000);
const errors = [],
  requests = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/table-cells'))
    requests.push(request.postDataJSON());
});
const table = page.locator(
  '.workspace-results .configured-view:visible .handler-table'
);
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false' &&
      [...document.querySelectorAll('.workspace-results .configured-view')]
        .filter((el) => el.offsetParent)
        .every((el) => el.getAttribute('aria-busy') === 'false')
  );
async function attachNote(notes, file) {
  const chooser = page.waitForEvent('filechooser');
  await notes
    .getByRole('button', { name: 'Attach files', exact: true })
    .click();
  await (await chooser).setFiles(file);
}
async function choice(inspector, name, value) {
  await inspector
    .getByRole('button', {
      name: name === 'Task' ? 'Switch task for this process' : name,
      exact: true
    })
    .click();
  await inspector
    .locator('[data-' + name.toLowerCase() + '-choice="' + value + '"]')
    .click();
}
async function taskAction(inspector, name) {
  const menu = inspector.locator('.inspector-task-actions');
  await inspector
    .getByRole('button', { name: 'Task actions', exact: true })
    .click();
  await menu.getByRole('button', { name, exact: true }).click();
}
async function captureInspector(inspector, name, height) {
  mkdirSync('../.screenshots/collaboration-current', { recursive: true });
  await page.locator('[data-dock="notes"] .dock-titlebar').focus();
  await page.mouse.move(5, 5);
  await page.waitForTimeout(400);
  await page.evaluate(() => document.fonts.ready);
  const box = await inspector.boundingBox(),
    context = await inspector.locator('.inspector-context').boundingBox();
  await page.screenshot({
    path:
      '../.screenshots/collaboration-current/stream-inspector-' + name + '.png',
    clip: { x: box.x, y: context.y - 5, width: box.width, height },
    animations: 'disabled'
  });
}
async function tableView() {
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
}
async function discussionMode(value) {
  await page.getByLabel('More options', { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Configuration', exact: true })
    .click();
  const configuration = page.locator('.configuration-dialog:visible');
  await configuration
    .locator('[data-frame="configurationNavigation"]')
    .getByRole('button', { name: 'Appearance', exact: true })
    .click();
  await configuration
    .getByLabel('Object notes', { exact: true })
    .selectOption(value);
  await configuration.locator('[data-frame="configurationSave"]').click();
  await configuration.locator('[data-frame="configurationClose"]').click();
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
  await ready();
  assert.equal(
    requests.length,
    0,
    'Plain database rows must not load server cells'
  );
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.navigation-tree')
    .getByRole('button', { name: 'Native cells', exact: true })
    .tap();
  await ready();
  await tableView();
  const first = table.getByRole('row').filter({ hasText: 'CELL_A' }),
    second = table.getByRole('row').filter({ hasText: 'CELL_B' });
  await first.waitFor();
  assert.equal(requests.length, 1, 'One batched cell request per page');
  assert.match(await first.innerText(), /\d+\.00/);
  assert.equal(
    await first.getByRole('link').getAttribute('href'),
    'https://example.com/a'
  );
  assert.equal(await second.getByRole('link').count(), 0);
  assert.equal(
    await page.locator('a[href^="javascript:"], a[href^="data:"]').count(),
    0
  );
  assert.equal(
    await first
      .getByRole('checkbox', { name: 'Default', exact: true })
      .isChecked(),
    true
  );
  assert.equal(
    await second
      .getByRole('checkbox', { name: 'Default', exact: true })
      .isChecked(),
    false
  );
  assert.equal(
    await first
      .getByRole('checkbox', { name: 'Default', exact: true })
      .isDisabled(),
    true
  );
  assert.match(await first.innerText(), /group CELL_A/);
  assert.match(await second.innerText(), /group CELL_B/);
  assert.match(await first.innerText(), /\d+, \d+/);
  assert.equal(
    await first
      .getByRole('checkbox', { name: 'Computed boolean', exact: true })
      .isChecked(),
    true
  );
  assert.equal(
    await second
      .getByRole('checkbox', { name: 'Computed boolean', exact: true })
      .isChecked(),
    false
  );
  assert.equal(await first.locator('[data-icon="check"]').count(), 3);
  assert.equal(await second.locator('[data-icon="check"]').count(), 0);
  const preview = page.getByRole('dialog', {
    name: 'File preview',
    exact: true
  });
  await first.getByRole('button', { name: 'File preview', exact: true }).tap();
  await preview.waitFor({ state: 'visible' });
  await page.waitForFunction(() => {
    const img = document.querySelector('.file-preview[open] img');
    return img?.complete && img.naturalWidth > 0;
  });
  assert.equal(
    await preview.getByRole('link', { name: 'Open file', exact: true }).count(),
    1
  );
  const download = page.waitForEvent('download');
  await preview.getByRole('link', { name: 'Download', exact: true }).tap();
  assert.match((await download).suggestedFilename(), /\.png$/);
  await page.keyboard.press('Escape');
  await preview.waitFor({ state: 'hidden' });
  await second.getByRole('button', { name: 'File preview', exact: true }).tap();
  await preview.waitFor({ state: 'visible' });
  assert.equal(
    await preview.getByRole('link', { name: 'Download', exact: true }).count(),
    0
  );
  await preview.getByText('No files', { exact: true }).waitFor();
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .tap();
  await first.getByRole('button', { name: 'publish (1)', exact: true }).tap();
  const notes = page.getByRole('region', {
    name: 'Task Inspector',
    exact: true
  });
  await notes.getByText('Browser discussion', { exact: true }).waitFor();
  await notes.locator('.inspector-object').waitFor();
  await notes
    .getByRole('button', { name: 'Expand Task Inspector', exact: true })
    .click();
  await notes.getByText('No task for publish', { exact: true }).waitFor();
  await captureInspector(notes, 'empty', 214);
  await notes
    .getByRole('button', { name: 'Collapse Task Inspector', exact: true })
    .click();
  const frame = await notes.boundingBox();
  const bubble = await notes.locator('.note-entry').boundingBox(),
    composer = await notes.locator('.note-composer').boundingBox();
  assert.ok(
    Math.abs(composer.y - bubble.y - bubble.height) < 20,
    'Short note history is anchored to the composer'
  );
  await page.screenshot({
    path: '../.screenshots/collaboration-current/stream-notes.png',
    clip: frame,
    animations: 'disabled'
  });
  await notes
    .getByRole('button', { name: 'Expand Task Inspector', exact: true })
    .click();
  assert.equal(
    await notes.locator('.task-detail-fields').count(),
    0,
    'No empty task field grid without a task'
  );
  await notes
    .getByLabel('Note text', { exact: true })
    .fill('Draft remains with this object');
  await closeInspector(page);
  await discussionMode('notes');
  assert.equal(
    await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem('tactic_stream.appearance'))
          .discussionView
    ),
    'notes'
  );
  await second.getByRole('button', { name: 'Add note', exact: true }).tap();
  const standalone = page.getByRole('dialog', { name: 'Notes', exact: true });
  await standalone.getByText('No notes yet', { exact: true }).waitFor();
  assert.equal(
    await standalone.locator('.task-details').count(),
    0,
    'Standalone notes remain available as a visible preference'
  );
  assert.equal(
    await standalone.getByLabel('Note text', { exact: true }).inputValue(),
    ''
  );
  await standalone
    .getByRole('button', { name: 'Close notes', exact: true })
    .tap();
  await discussionMode('inspector');
  await first.getByRole('button', { name: 'publish (1)', exact: true }).tap();
  await notes.getByText('Browser discussion', { exact: true }).waitFor();
  assert.equal(
    await notes.getByLabel('Note text', { exact: true }).inputValue(),
    'Draft remains with this object'
  );
  await notes
    .getByLabel('Note text', { exact: true })
    .fill('Sent from browser');
  await attachNote(notes, {
    name: 'browser note.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Native note attachment')
  });
  await notes.getByRole('button', { name: 'Send note', exact: true }).tap();
  await notes.getByText('Sent from browser', { exact: true }).waitFor();
  const sent = notes
    .locator('.note-entry')
    .filter({ hasText: 'Sent from browser' });
  assert.equal(await sent.locator('.attachment-card').count(), 1);
  await sent.getByRole('button', { name: 'File preview', exact: true }).tap();
  const noteFileDownload = page.waitForEvent('download');
  await preview.getByRole('link', { name: 'Download', exact: true }).tap();
  const downloadedNote = await noteFileDownload;
  assert.match(downloadedNote.suggestedFilename(), /^browser note.*\.txt$/);
  assert.equal(
    await readFile(await downloadedNote.path(), 'utf8'),
    'Native note attachment'
  );
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .tap();

  await sent.getByRole('button', { name: 'Reply', exact: true }).tap();
  await notes.getByLabel('Note text', { exact: true }).fill('Thread reply');
  await notes.getByLabel('Note text', { exact: true }).press('Enter');
  await notes
    .locator('.note-reply')
    .getByText('Thread reply', { exact: true })
    .waitFor();
  const reply = notes.locator('.note-reply');
  await reply
    .getByRole('button', { name: 'Note actions', exact: true })
    .click();
  await page.getByRole('button', { name: 'Edit note', exact: true }).tap();
  const noteEditor = page.getByRole('dialog', {
    name: 'Edit note',
    exact: true
  });
  await noteEditor
    .getByLabel('Note text', { exact: true })
    .fill('Edited reply');
  await noteEditor.getByRole('button', { name: 'Save', exact: true }).tap();
  await reply.getByText('Edited reply', { exact: true }).waitFor();
  await reply.getByText('Edit history', { exact: true }).tap();
  await reply.getByText('Thread reply', { exact: true }).waitFor();
  await reply
    .getByRole('button', { name: 'Note actions', exact: true })
    .click();
  await page.getByRole('button', { name: 'Delete note', exact: true }).tap();
  const noteDelete = page.getByRole('dialog', {
    name: 'Delete note?',
    exact: true
  });
  assert(await noteDelete.evaluate((node) => node.matches(':modal')));
  await noteDelete.getByRole('button', { name: 'Delete', exact: true }).tap();
  await reply.waitFor({ state: 'detached' });
  await closeInspector(page);
  assert.equal(
    requests.length,
    5,
    'One table refresh per saved note/reply/edit/delete'
  );
  await first
    .getByRole('checkbox', { name: 'Select record:', exact: false })
    .check();
  assert.equal(
    await table
      .getByRole('checkbox', { name: 'Select all rows', exact: true })
      .evaluate((el) => el.indeterminate),
    true
  );
  await table
    .getByRole('checkbox', { name: 'Select all rows', exact: true })
    .check();
  assert.equal(
    await second
      .getByRole('checkbox', { name: 'Select record:', exact: false })
      .isChecked(),
    true
  );
  assert.equal(requests.length, 5, 'Selection must not re-fetch cells');
  await first.getByRole('button', { name: 'Check-in', exact: true }).click();
  const plate = page.locator('[data-dock="drop_plate"] .drop-plate');
  await plate.getByLabel('Process', { exact: true }).waitFor();
  assert.equal(
    await plate.getByLabel('Process', { exact: true }).inputValue(),
    'publish'
  );
  assert.equal(
    await plate.getByLabel('Context', { exact: true }).inputValue(),
    'publish'
  );
  await page
    .locator('[data-dock="drop_plate"]')
    .getByRole('button', { name: 'Close panel: Drop Plate', exact: true })
    .click();
  if (process.argv[3])
    await page.screenshot({ path: process.argv[3], animations: 'disabled' });
  await table
    .getByRole('columnheader', { name: 'Number', exact: true })
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Column Manager', exact: true })
    .click();
  const editor = page.locator('.columns-editor'),
    admin = page.locator('.administration-dialog');
  await page.waitForFunction(
    () =>
      document.querySelector('.columns-editor')?.getAttribute('aria-busy') ===
      'false'
  );
  await editor.getByRole('button', { name: 'id', exact: true }).click();
  assert.equal(
    await editor.getByLabel('Title', { exact: true }).inputValue(),
    'Number'
  );
  await admin.locator('[data-frame=administrationCloseButton]').tap();
  await ready();
  await table
    .getByRole('columnheader', { name: 'Number', exact: false })
    .click({ button: 'right' });
  await page
    .getByRole('button', { name: 'Edit Column Definition', exact: true })
    .click();
  await page.waitForFunction(
    () =>
      document.querySelector('.columns-editor')?.getAttribute('aria-busy') ===
      'false'
  );
  await editor.getByText('Select a definition', { exact: true }).waitFor();
  await admin.locator('[data-frame=administrationCloseButton]').tap();
  await ready();
  await page.setViewportSize({ width: 320, height: 740 });
  await page.waitForFunction(
    () =>
      !document.querySelector('.workspace-results .handler-table')?.offsetParent
  );
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  assert.equal(
    await page.evaluate(() =>
      getComputedStyle(document.documentElement)
        .getPropertyValue('--control-height')
        .trim()
    ),
    '36px',
    'Mobile retains the Handler control height'
  );
  assert.equal(
    await table.count(),
    0,
    'Phone uses compact results instead of the desktop configured table'
  );
  const phone = page
    .locator('.workspace-results .result-item:visible')
    .filter({ hasText: 'CELL_A' })
    .first();
  await phone.waitFor();
  await phone.getByLabel('Item actions', { exact: true }).tap();
  await page
    .getByRole('checkbox', { name: 'Select record', exact: true })
    .check();
  await page
    .getByRole('checkbox', { name: 'Select record', exact: true })
    .evaluate((node) =>
      Promise.all(
        node
          .closest('.account-panel')
          .getAnimations()
          .map((animation) => animation.finished)
      )
    );
  const box = await page
    .getByRole('checkbox', { name: 'Select record', exact: true })
    .locator('..')
    .boundingBox();
  assert.equal(box.height, 19, 'Shared checkbox indicator size');
  assert.equal(box.width, 19, 'Do not inflate the Handler checkbox for touch');
  await page.keyboard.press('Escape');
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-mobile.png'),
      animations: 'disabled'
    });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.navigation-tree')
    .getByRole('button', { name: 'Task cells', exact: true })
    .tap();
  await ready();
  await tableView();
  const taskRow = table.getByRole('row').filter({ hasText: 'INSPECTOR_A' });
  await taskRow
    .locator('.table-tasks button')
    .filter({ hasText: /^model/ })
    .first()
    .tap();
  const inspector = page.getByRole('region', {
    name: 'Task Inspector',
    exact: true
  });
  await inspector
    .getByText('Primary task discussion', { exact: true })
    .waitFor();
  const taskOptions = await inspector.locator('[data-task-choice]').all();
  await captureInspector(inspector, 'task', 300);
  assert.equal(taskOptions.length, 2);
  const primaryTask = await taskOptions[0].getAttribute('data-task-choice'),
    secondaryTask = await taskOptions[1].getAttribute('data-task-choice');
  await inspector
    .getByRole('button', { name: 'Object preview', exact: true })
    .tap();
  const objectPreview = page.locator('.file-preview[open]');
  await objectPreview
    .getByText('contract/browser_task', { exact: true })
    .waitFor();
  assert.equal(await objectPreview.locator('img').count(), 1);
  assert.equal(
    await objectPreview
      .locator('img')
      .evaluate((image) => image.complete && image.naturalWidth > 0),
    true
  );
  await objectPreview
    .getByRole('button', { name: 'Close preview', exact: true })
    .tap();
  await inspector.getByRole('button', { name: 'Log time', exact: true }).tap();
  const timesheet = page.getByRole('dialog', {
    name: 'Task timesheet',
    exact: true
  });
  const timeForm = timesheet.locator('.work-hour-form'),
    entries = timesheet.locator('.time-entry-list .timesheet-entry');
  await timesheet.getByLabel('Duration, hours', { exact: true }).fill('1.25');
  await timesheet
    .getByLabel('Category', { exact: true })
    .getByRole('radio', { name: 'Overtime', exact: true })
    .tap();
  await timesheet
    .getByLabel('Description', { exact: true })
    .fill('Browser time entry');
  await timeForm.getByRole('button', { name: 'Save', exact: true }).tap();
  await entries.getByText(/Browser time entry/).waitFor();
  assert.match(await entries.innerText(), /1.25 h.*Pending.*OT 1.25 h/s);
  await entries
    .getByRole('button', { name: 'Approve entry', exact: true })
    .tap();
  await entries
    .getByRole('button', { name: 'Return to pending', exact: true })
    .waitFor();
  await entries.getByRole('button', { name: 'Edit entry', exact: true }).tap();
  await timesheet.getByLabel('Duration, hours', { exact: true }).fill('2.5');
  await timeForm
    .getByRole('button', { name: 'Save & Approve', exact: true })
    .tap();
  await entries.getByText('2.5 h', { exact: true }).waitFor();
  await timesheet.getByRole('button', { name: 'Log time', exact: true }).tap();
  await timesheet.getByLabel('Duration, hours', { exact: true }).fill('23');
  await timeForm.getByRole('button', { name: 'Save', exact: true }).tap();
  await timesheet
    .locator('p[role="alert"]')
    .filter({ hasText: 'Daily work hours cannot exceed 24' })
    .waitFor();
  assert.equal(await entries.count(), 1);
  await timeForm.getByRole('button', { name: 'Cancel', exact: true }).tap();
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(
    await timesheet.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-work-hours-mobile.png'),
      animations: 'disabled'
    });
  await entries
    .getByRole('button', { name: 'Delete entry', exact: true })
    .tap();
  await entries
    .locator('.notice')
    .getByRole('button', { name: 'Delete time entry', exact: true })
    .tap();
  await timesheet.getByText('No time entries yet', { exact: true }).waitFor();
  await timesheet.getByRole('button', { name: 'Close', exact: true }).tap();
  await page.setViewportSize({ width: 1280, height: 900 });
  await inspector
    .getByRole('button', { name: 'Collapse Task Inspector', exact: true })
    .tap();
  await captureInspector(inspector, 'collapsed', 96);
  assert.equal(await inspector.locator('.task-detail-fields').count(), 0);
  await choice(inspector, 'Task', secondaryTask);
  await inspector
    .getByText('Secondary task discussion', { exact: true })
    .waitFor();
  assert.equal(
    await inspector
      .getByText('Primary task discussion', { exact: true })
      .count(),
    0
  );
  await taskAction(inspector, 'Edit task');
  await inspector.getByLabel('Description', { exact: true }).fill('Task draft');
  await captureInspector(inspector, 'full-editor', 390);
  await choice(inspector, 'Task', primaryTask);
  await inspector
    .getByText('Primary task discussion', { exact: true })
    .waitFor();
  await choice(inspector, 'Task', secondaryTask);
  await inspector
    .getByText('Secondary task discussion', { exact: true })
    .waitFor();
  const expandInspector = inspector.getByRole('button', {
    name: 'Expand Task Inspector',
    exact: true
  });
  // Full edit can already expand the retained inspector when its task returns.
  if (await expandInspector.isVisible()) await expandInspector.tap();
  else
    await inspector
      .getByRole('button', {
        name: 'Collapse Task Inspector',
        exact: true
      })
      .waitFor();
  assert.equal(
    await inspector.getByLabel('Description', { exact: true }).inputValue(),
    'Task draft'
  );
  await inspector
    .getByLabel('Status', { exact: true })
    .selectOption('Complete');
  await inspector.getByRole('button', { name: 'Save task', exact: true }).tap();
  await inspector
    .locator('[data-note-kind="status"]')
    .getByText('Complete', { exact: true })
    .waitFor();
  await taskAction(inspector, 'Add task assignee');
  const assignee = inspector.locator('.task-details .notice .user-combo-box');
  await assignee.getByLabel('Assigned to', { exact: true }).click();
  await assignee.getByRole('radio').filter({ hasText: 'admin' }).click();
  await inspector
    .getByRole('button', { name: 'Create task copy', exact: true })
    .tap();
  await page.waitForFunction(
    () =>
      document.querySelectorAll('.notes-panel[open] [data-task-choice]')
        .length === 3
  );
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Protect this draft from task deletion');
  await taskAction(inspector, 'Delete task');
  await inspector
    .getByText('Send or clear the note draft before deleting this task.', {
      exact: true
    })
    .waitFor();
  assert.equal(await inspector.locator('.task-details .notice').count(), 0);
  await inspector.getByLabel('Note text', { exact: true }).fill('');
  await taskAction(inspector, 'Delete task');
  await inspector
    .locator('.task-details .notice')
    .getByRole('button', { name: 'Cancel', exact: true })
    .tap();
  assert.equal(await inspector.locator('[data-task-choice]').count(), 3);
  await taskAction(inspector, 'Delete task');
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-task-actions.png'),
      animations: 'disabled'
    });
  await inspector
    .locator('.task-details .notice')
    .getByRole('button', { name: 'Delete task', exact: true })
    .tap();
  await inspector
    .getByText('Primary task discussion', { exact: true })
    .waitFor();
  assert.equal(await inspector.locator('[data-task-choice]').count(), 2);
  await closeInspector(page);
  await ready();
  await table
    .getByRole('row')
    .filter({ hasText: 'INSPECTOR_EMPTY' })
    .locator('.table-tasks button')
    .filter({ hasText: /^model/ })
    .tap();
  await inspector.getByText('No task for model', { exact: true }).waitFor();
  await taskAction(inspector, 'Create task');
  const fullForm = page.getByRole('dialog', {
    name: 'Record form',
    exact: true
  });
  await fullForm
    .getByRole('button', { name: /^(?:Create|Save changes)$/, exact: true })
    .waitFor();
  assert.equal(
    await fullForm
      .getByRole('button', { name: /^(?:Create|Save changes)$/, exact: true })
      .isEnabled(),
    true
  );
  assert.equal(await fullForm.locator('.error').count(), 0);
  await fullForm.getByRole('button', { name: 'Close', exact: true }).tap();
  await taskAction(inspector, 'Edit task');
  await inspector
    .getByLabel('Description', { exact: true })
    .fill('Created in Task Inspector');
  await inspector.getByRole('button', { name: 'Save task', exact: true }).tap();
  await inspector
    .locator('.inspector-task-surface[data-has-task="true"]')
    .waitFor();
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  await taskAction(inspector, 'Expand Task Inspector');
  const statusBox = await inspector
    .locator('[data-frame="taskInspectorStatusField"]')
    .boundingBox();
  const assignedBox = await inspector
    .locator('[data-frame="taskInspectorAssigneeField"]')
    .boundingBox();
  assert(
    Math.abs(statusBox.y - assignedBox.y) < 1 && assignedBox.x > statusBox.x,
    'Shared quick fields keep two columns at 320px'
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-task-inspector-mobile.png'),
      animations: 'disabled'
    });
  await closeInspector(page);
  await page.setViewportSize({ width: 1280, height: 900 });
  await selectProject(page, 'browser_related');
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.navigation-tree')
    .getByRole('button', { name: 'Progress tasks', exact: true })
    .tap();
  await ready();
  await tableView();
  await table
    .getByRole('row')
    .filter({ hasText: 'BROWSER_PROGRESS' })
    .getByRole('button', { name: 'Task Inspector', exact: true })
    .first()
    .tap();
  await choice(inspector, 'Process', 'linked');
  const related = inspector.getByRole('region', {
    name: 'Related object tasks',
    exact: true
  });
  await related.getByText(/^Related child · /).waitFor();
  await captureInspector(inspector, 'related', 214);
  await related.getByText('1 / 1', { exact: true }).waitFor();
  assert.equal(
    await inspector
      .getByRole('button', { name: 'Create task', exact: true })
      .count(),
    0
  );
  assert.equal(
    await inspector
      .getByRole('button', { name: 'Edit task', exact: true })
      .count(),
    0
  );
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Parent progress draft');
  await related
    .getByRole('button', { name: 'Open related task', exact: true })
    .tap();
  await inspector
    .locator('.inspector-task-surface[data-has-task="true"]')
    .waitFor();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    ''
  );
  await taskAction(inspector, 'Edit task');
  await inspector
    .getByLabel('Description', { exact: true })
    .fill('Related task draft');
  await inspector
    .getByRole('button', { name: 'Back to related tasks', exact: true })
    .tap();
  await related.getByText(/^Related child · /).waitFor();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Parent progress draft'
  );
  await related
    .getByRole('button', { name: 'Open related task', exact: true })
    .tap();
  await inspector.getByLabel('Description', { exact: true }).waitFor();
  assert.equal(
    await inspector.getByLabel('Description', { exact: true }).inputValue(),
    'Related task draft'
  );
  await inspector
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await inspector
    .getByRole('button', { name: 'Back to related tasks', exact: true })
    .tap();
  await related.getByText(/^Related child · /).waitFor();
  await inspector.getByRole('button', { name: 'Send note', exact: true }).tap();
  await inspector.getByText('Parent progress draft', { exact: true }).waitFor();
  await choice(inspector, 'Process', 'empty');
  await related
    .getByText('No related Search Type configured for this progress', {
      exact: true
    })
    .waitFor();
  await choice(inspector, 'Process', 'linked');
  await related.getByText(/^Related child · /).waitFor();
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-related-tasks.png'),
      animations: 'disabled'
    });
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    true
  );
  await taskAction(inspector, 'Expand Task Inspector');
  const relatedButton = await related
    .getByRole('button', { name: 'Open related task', exact: true })
    .boundingBox();
  assert.ok(relatedButton.width >= 24 && relatedButton.height >= 24);
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-related-tasks-mobile.png'),
      animations: 'disabled'
    });
  await related
    .getByRole('button', { name: 'Open related task', exact: true })
    .tap();
  await inspector
    .locator('.inspector-task-surface[data-has-task="true"]')
    .waitFor();
  await inspector
    .getByRole('button', { name: 'Back to related tasks', exact: true })
    .tap();
  await related.getByText(/^Related child · /).waitFor();
  await closeInspector(page);
  await selectProject(page, 'admin');
  await ready();
  await page.getByLabel('More options', { exact: true }).tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Weekly timesheet', exact: true })
    .tap();
  const weekly = page.getByRole('region', {
    name: 'Weekly timesheet',
    exact: true
  });
  await weekly.getByLabel('Week', { exact: true }).fill('2030-01-09');
  await weekly.getByLabel('Week', { exact: true }).blur();
  await weekly.getByText(/Weekly regular/).waitFor();
  assert.equal(
    await weekly.getByLabel('Week', { exact: true }).inputValue(),
    '2030-01-07'
  );
  assert.equal(
    await weekly.locator('.time-entry-list .timesheet-entry').count(),
    1
  );
  await weekly.getByLabel('Team member', { exact: true }).click();
  await weekly.getByRole('radio', { name: 'All users', exact: true }).click();
  await weekly.getByText(/Weekly overtime/).waitFor();
  const weeklyEntries = weekly.locator('.time-entry-list .timesheet-entry');
  for (const checkbox of await weeklyEntries
    .getByRole('checkbox', { name: /^Select time entry:/ })
    .all())
    await checkbox.check();
  await weekly
    .getByRole('button', { name: 'Approve selected entries', exact: true })
    .tap();
  await page.waitForFunction(
    () =>
      [
        ...document.querySelectorAll(
          '.time-entry-panel[aria-label="Weekly timesheet"] .time-entry-list button[aria-label="Return to pending"]'
        )
      ].length === 2
  );
  assert.equal(
    await weeklyEntries.getByRole('checkbox', { checked: true }).count(),
    0
  );
  for (const checkbox of await weeklyEntries
    .getByRole('checkbox', { name: /^Select time entry:/ })
    .all())
    await checkbox.check();
  await weekly
    .getByRole('button', {
      name: 'Return selected entries to pending',
      exact: true
    })
    .tap();
  await page.waitForFunction(
    () =>
      [
        ...document.querySelectorAll(
          '.time-entry-panel[aria-label="Weekly timesheet"] .time-entry-list button[aria-label="Approve entry"]'
        )
      ].length === 2
  );
  await weeklyEntries
    .filter({ hasText: 'Weekly overtime' })
    .getByRole('button', { name: 'Edit entry', exact: true })
    .tap();
  await weekly.getByLabel('Duration, hours', { exact: true }).fill('2.5');
  await weekly
    .locator('.work-hour-form')
    .getByRole('button', { name: 'Save & Approve', exact: true })
    .tap();
  await weeklyEntries
    .filter({ hasText: 'Weekly overtime' })
    .getByText('2.5 h', { exact: true })
    .waitFor();
  await weeklyEntries
    .filter({ hasText: 'Weekly regular' })
    .getByRole('button', { name: 'Edit entry', exact: true })
    .tap();
  await weekly
    .getByLabel('Description', { exact: true })
    .fill('Protected weekly draft');
  await weekly.getByRole('button', { name: 'Close', exact: true }).click();
  await weekly.getByText('Discard unsaved changes?', { exact: true }).waitFor();
  await weekly.getByRole('button', { name: 'Keep editing', exact: true }).tap();
  assert.equal(
    await weekly.getByLabel('Description', { exact: true }).inputValue(),
    'Protected weekly draft'
  );
  await weekly
    .locator('.work-hour-form')
    .getByRole('button', { name: 'Cancel', exact: true })
    .tap();
  await weekly.getByRole('button', { name: 'Next week', exact: true }).tap();
  await weekly
    .getByText('No work hours for this week', { exact: true })
    .waitFor();
  await weekly
    .getByRole('button', { name: 'Previous week', exact: true })
    .tap();
  await weekly.getByText(/Weekly regular/).waitFor();
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(
    await weekly.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  const loggedSummary = await weekly
    .locator('[data-frame="timesheetSummary-logged"]')
    .boundingBox();
  const pendingSummary = await weekly
    .locator('[data-frame="timesheetSummary-pending"]')
    .boundingBox();
  assert.ok(pendingSummary.y >= loggedSummary.y + loggedSummary.height);
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-weekly-mobile.png'),
      animations: 'disabled'
    });
  await weekly
    .getByRole('button', { name: 'Open work reports', exact: true })
    .tap();
  const reports = page.getByRole('region', {
    name: 'Work reports',
    exact: true
  });
  await reports.getByLabel('Week', { exact: true }).fill('2030-01-07');
  await reports.getByLabel('Week', { exact: true }).blur();
  await page.waitForFunction(
    () =>
      document
        .querySelector('.time-entry-panel[aria-label="Work reports"]')
        ?.getAttribute('aria-busy') === 'false'
  );
  await reports.getByLabel('Team member', { exact: true }).selectOption('');
  await page.waitForFunction(
    () =>
      document
        .querySelector('.time-entry-panel[aria-label="Work reports"]')
        ?.getAttribute('aria-busy') === 'false'
  );
  await reports.getByLabel('Report', { exact: true }).selectOption('approval');
  await reports
    .locator('[data-frame="workReportValueLabel"]')
    .getByText('Approved', { exact: true })
    .waitFor();
  assert.equal(
    await reports.locator('[data-frame="workReportValueLabel"]').count(),
    2
  );
  assert.equal(
    await reports.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-reports-mobile.png'),
      animations: 'disabled'
    });
  await reports.getByRole('button', { name: 'Close', exact: true }).tap();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.clock.install();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000));
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.navigation-tree')
    .getByRole('button', { name: 'Task cells', exact: true })
    .tap();
  await ready();
  const taskCell = taskRow.locator('.table-task-cell'),
    cardsPreview = page
      .getByRole('dialog', { name: 'Task previews', exact: true })
      .first();
  await taskCell.hover();
  await page.clock.fastForward(300);
  await cardsPreview.waitFor({ state: 'visible' });
  assert.equal(await cardsPreview.locator('.task-card').count(), 3);
  await cardsPreview.locator('.task-cards').click({ position: { x: 2, y: 2 } });
  await page.mouse.move(1000, 40);
  await page.clock.fastForward(300);
  assert.equal(
    await cardsPreview.isVisible(),
    true,
    'Pinned cards remain after the pointer leaves'
  );
  await page.mouse.click(1000, 40);
  await page.clock.fastForward(250);
  await cardsPreview.waitFor({ state: 'hidden' });
  await taskCell.hover();
  await page.clock.fastForward(300);
  await cardsPreview.waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
  await cardsPreview.waitFor({ state: 'hidden' });
  const previewButton = taskCell.getByRole('button', {
    name: 'Task Manager',
    exact: true
  });
  await previewButton.focus();
  await page.keyboard.press('Enter');
  await inspector.waitFor({ state: 'visible' });
  await closeInspector(page, inspector);
  await taskCell.hover();
  await page.clock.fastForward(300);
  await cardsPreview.waitFor({ state: 'visible' });
  await page
    .locator('.workspace-results')
    .evaluate((el) => el.dispatchEvent(new Event('scroll')));
  await cardsPreview.waitFor({ state: 'hidden' });
  // Configured table previews are desktop-only; phone task editing is exercised in mobile_complete.
  // Scroll closes the preview; reopening requires a new pointer movement.
  await page.mouse.move(1000, 40);
  await taskCell.hover();
  await page.clock.runFor(300);
  await cardsPreview.waitFor({ state: 'visible' });
  assert.equal(
    await cardsPreview.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  const cardStrip = await cardsPreview.locator('.task-cards').evaluate((el) => {
    const bounds = el.getBoundingClientRect();
    return {
      width: el.clientWidth,
      scrollWidth: el.scrollWidth,
      height: el.clientHeight,
      scrollHeight: el.scrollHeight,
      top: bounds.top,
      bottom: bounds.bottom,
      cards: [...el.children].map((card) =>
        card.getBoundingClientRect().toJSON()
      )
    };
  });
  assert.equal(
    cardStrip.scrollWidth,
    cardStrip.width,
    'Three task cards fit without an inner horizontal scrollbar'
  );
  assert.equal(
    cardStrip.scrollHeight,
    cardStrip.height,
    'No inner vertical scrollbar clips task fields'
  );
  assert.equal(
    await cardsPreview.evaluate((el) => el.scrollHeight <= el.clientHeight),
    true
  );
  for (const card of cardStrip.cards)
    assert(
      card.top >= cardStrip.top && card.bottom <= cardStrip.bottom,
      'Full task card height stays inside the preview'
    );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-task-preview-table.png'),
      animations: 'disabled'
    });
  await cardsPreview
    .getByRole('button', { name: 'Edit task status', exact: true })
    .first()
    .tap();
  const tableEditor = page.getByRole('dialog', {
    name: 'Edit table tasks',
    exact: true
  });
  const pending = page.getByRole('region', {
    name: 'Pending task changes',
    exact: true
  });
  await tableEditor.getByLabel('Status', { exact: true }).waitFor();
  assert.equal(
    await tableEditor
      .getByLabel('Status', { exact: true })
      .locator('option')
      .first()
      .textContent(),
    'Select status'
  );
  assert.equal(
    await tableEditor
      .getByLabel('Status', { exact: true })
      .locator('option')
      .first()
      .evaluate((el) => el.disabled),
    true
  );
  assert.equal(
    await tableEditor
      .getByLabel('Status', { exact: true })
      .evaluate(
        (el) =>
          el === document.activeElement || el.contains(document.activeElement)
      ),
    true
  );
  await tableEditor
    .getByLabel('Status', { exact: true })
    .selectOption('Waiting');
  await pending.getByText('1 unsaved tasks', { exact: true }).waitFor();
  assert.equal(
    await inspector.isVisible(),
    false,
    'Table fields edit without opening Inspector'
  );
  await page.getByLabel('More options', { exact: true }).tap();
  await page.getByRole('button', { name: 'Reload Cache', exact: true }).tap();
  await page
    .getByRole('status')
    .filter({ hasText: 'Cache reloaded' })
    .waitFor();
  await ready();
  await pending.getByText('1 unsaved tasks', { exact: true }).waitFor();
  await taskCell
    .getByRole('button', { name: 'Edit task status', exact: true })
    .tap();
  assert.equal(
    await tableEditor.getByLabel('Status', { exact: true }).inputValue(),
    'Waiting',
    'Cache reload retains the task draft and revision'
  );
  await page.keyboard.press('Escape');
  await tableEditor.waitFor({ state: 'hidden' });
  await page
    .locator('.notification-card')
    .filter({ hasText: 'Cache reloaded' })
    .getByRole('button', { name: 'Dismiss notification', exact: true })
    .tap();
  await pending
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await ready();
  await pending.waitFor({ state: 'hidden' });
  await taskCell
    .getByRole('button', { name: 'Edit task assignee', exact: true })
    .tap();
  await tableEditor
    .locator('.user-combo-box')
    .getByRole('radio')
    .filter({ hasText: 'admin' })
    .click();
  await pending
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await pending.waitFor({ state: 'hidden' });
  await ready();
  await taskCell.locator('.task-card-assignee img').waitFor();
  await table
    .getByRole('columnheader', { name: 'Tasks', exact: true })
    .click({ button: 'right' });
  await page
    .getByRole('menuitemradio', { name: 'Large rows', exact: true })
    .click();
  await taskCell
    .getByRole('button', { name: 'Edit task dates', exact: true })
    .tap();
  await tableEditor.getByLabel('Start date', { exact: true }).waitFor();
  assert.equal(
    await tableEditor
      .getByLabel('Start date', { exact: true })
      .evaluate((el) => el === document.activeElement),
    true
  );
  await tableEditor
    .getByLabel('Start date', { exact: true })
    .fill('2030-01-07T09:00');
  await tableEditor
    .getByLabel('End date', { exact: true })
    .fill('2030-01-07T17:00');
  assert.equal(
    await tableEditor.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-task-drafts-mobile.png'),
      animations: 'disabled'
    });
  const actionBounds = await pending.evaluate((el) => {
    const bounds = el.getBoundingClientRect();
    return {
      left: bounds.left,
      right: bounds.right,
      viewport: innerWidth,
      buttons: [...el.querySelectorAll('button')].map((button) => {
        const rect = button.getBoundingClientRect();
        return { left: rect.left, right: rect.right };
      })
    };
  });
  assert.ok(
    actionBounds.left >= 0 &&
      actionBounds.right <= actionBounds.viewport &&
      actionBounds.buttons.every(
        (rect) => rect.left >= 0 && rect.right <= actionBounds.viewport
      ),
    JSON.stringify(actionBounds)
  );
  await page.keyboard.press('Escape');
  await tableEditor.waitFor({ state: 'hidden' });
  const initialTab = await page
    .getByRole('tablist', { name: 'Search tabs', exact: true })
    .getByRole('tab')
    .first()
    .getAttribute('id');
  await page
    .getByRole('button', { name: 'Add new search tab', exact: true })
    .tap();
  await ready();
  await pending.waitFor({ state: 'hidden' });
  await page.locator('#' + initialTab).tap();
  await ready();
  await pending.getByText('1 unsaved tasks', { exact: true }).waitFor();
  await pending
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await pending.waitFor({ state: 'hidden' });
  await ready();
  await taskCell
    .getByText('2030-01-07 – 2030-01-07', { exact: true })
    .waitFor();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.clock.runFor(50);
  await taskRow
    .getByLabel('Select record: INSPECTOR_A', { exact: true })
    .check();
  await table
    .getByRole('row')
    .filter({ hasText: 'INSPECTOR_EMPTY' })
    .getByLabel('Select record: INSPECTOR_EMPTY', { exact: true })
    .check();
  // Finish selected-row layout on the mocked frame clock before anchoring the editor.
  await page.clock.runFor(300);
  await ready();
  await page.mouse.move(1000, 40);
  await taskCell.hover();
  await page.clock.runFor(300);
  await cardsPreview.waitFor({ state: 'visible' });
  await cardsPreview
    .locator('.task-card')
    .filter({
      has: page
        .getByRole('button', { name: 'Task Inspector', exact: true })
        .filter({ hasText: /^review$/ })
    })
    .getByRole('button', { name: 'Edit task status', exact: true })
    .click();
  assert.equal(
    await tableEditor.getAttribute('aria-description'),
    'Apply to 2 rows'
  );
  await tableEditor
    .getByLabel('Status', { exact: true })
    .selectOption('Waiting');
  await pending.getByText('2 unsaved tasks', { exact: true }).waitFor();
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (
      body.method === 'execute_cmd' &&
      body.args[1].endsWith('TaskTableEditCmd') &&
      body.args[2].action === 'save'
    ) {
      await route.fetch();
      await route.abort('connectionreset');
    } else await route.continue();
  });
  await pending
    .getByRole('button', { name: 'Save task changes', exact: true })
    .tap();
  await pending
    .getByRole('button', { name: 'Check saved task changes', exact: true })
    .waitFor();
  assert.equal(
    await pending
      .getByRole('button', { name: 'Save task changes', exact: true })
      .isEnabled(),
    false
  );
  await page.unroute('**/admin/rpc');
  await pending
    .getByRole('button', { name: 'Check saved task changes', exact: true })
    .tap();
  await pending.waitFor({ state: 'hidden' });
  await ready();
  await taskRow
    .getByLabel('Select record: INSPECTOR_A', { exact: true })
    .uncheck();
  await table
    .getByRole('row')
    .filter({ hasText: 'INSPECTOR_EMPTY' })
    .getByLabel('Select record: INSPECTOR_EMPTY', { exact: true })
    .uncheck();
  await page.clock.resume();
  await taskRow
    .locator('.table-tasks button')
    .filter({ hasText: /^model/ })
    .first()
    .tap();
  await inspector
    .getByText('Primary task discussion', { exact: true })
    .waitFor();
  assert.ok(
    (await inspector
      .locator('[data-note-kind="note"] [data-frame="noteAuthorAvatar"] img')
      .count()) > 0
  );
  assert.equal(
    await inspector
      .locator('[data-note-kind="note"] [data-frame="noteAuthorAvatar"] img')
      .first()
      .evaluate((image) => image.complete && image.naturalWidth > 0),
    true
  );
  const remote = (method, args) =>
    page.evaluate(
      async ({ method, args }) => {
        const session = JSON.parse(
          localStorage.getItem('tactic_stream.session')
        );
        const response = await fetch('/admin/rpc', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            method,
            args: [
              { ticket: session.ticket, project: 'admin', language: 'python' },
              ...args
            ]
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        return result.result;
      },
      { method, args }
    );
  const selected = await inspector
    .locator('[data-task-choice][aria-checked="true"]')
    .getAttribute('data-task-choice');
  await taskAction(inspector, 'Edit task');
  await inspector
    .getByLabel('Description', { exact: true })
    .fill('Keep this local task draft');
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Keep this local note draft');
  await remote('update', [
    selected,
    { description: 'Changed in another client' }
  ]);
  await remote('execute_cmd', [
    'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
    {
      search_key: 'contract/browser_task?project=admin&code=INSPECTOR_A',
      process: 'model',
      note: 'Live note from another client',
      files: []
    }
  ]);
  await page.clock.runFor(30000);
  await inspector
    .getByText('Live note from another client', { exact: true })
    .waitFor();
  assert.equal(
    await inspector.getByLabel('Description', { exact: true }).inputValue(),
    'Keep this local task draft'
  );
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Keep this local note draft'
  );
  await inspector.getByRole('button', { name: 'Save task', exact: true }).tap();
  await inspector
    .locator('.error')
    .filter({ hasText: 'Tasks changed. Reload before saving.' })
    .waitFor();
  assert.equal(
    await inspector.getByLabel('Description', { exact: true }).inputValue(),
    'Keep this local task draft'
  );
  await inspector
    .getByRole('button', { name: 'Discard task changes', exact: true })
    .tap();
  await inspector
    .getByRole('button', { name: 'Refresh notes and task', exact: true })
    .tap();
  await taskAction(inspector, 'Edit task');
  assert.equal(
    await inspector.getByLabel('Description', { exact: true }).inputValue(),
    'Changed in another client'
  );
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Keep this local note draft'
  );
  await page.setViewportSize({ width: 320, height: 740 });
  await page.clock.runFor(50);
  assert.equal(
    await inspector.evaluate((el) => el.scrollWidth <= el.clientWidth),
    true
  );
  if (process.argv[3])
    await page.screenshot({
      path: process.argv[3].replace('.png', '-inspector-live-mobile.png'),
      animations: 'disabled'
    });
  let automaticReads = 0;
  const observe = (request) => {
    if (!request.url().endsWith('/admin/rpc')) return;
    const payload = request.postDataJSON();
    if (
      payload?.args?.[1] === 'tactic.ui.table.task_inspector.TaskInspectorCmd'
    )
      automaticReads++;
  };
  page.on('request', observe);
  await closeInspector(page);
  await ready();
  await page.clock.fastForward(60000);
  assert.equal(
    automaticReads,
    0,
    'Closing the inspector stops its periodic requests'
  );
  page.off('request', observe);
  await remote('insert_multiple', [
    'sthpw/login_group',
    Array.from({ length: 21 }, (_, index) => ({
      login_group: 'CELL_MORE_' + String(index).padStart(2, '0'),
      description: 'Extra native cell row'
    }))
  ]);
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.navigation-tree')
    .getByRole('button', { name: 'Native cells', exact: true })
    .tap();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.clock.runFor(50);
  await ready();
  await page
    .locator('.search-header')
    .getByRole('button', { name: 'Refresh', exact: true })
    .tap();
  await ready();
  const footer = page.locator('.workspace-footer');
  await footer.getByLabel('Items per page', { exact: true }).tap();
  await footer
    .getByRole('menuitemradio', { name: '20 items', exact: true })
    .tap();
  await ready();
  await footer.getByLabel('Result loading', { exact: true }).tap();
  await footer
    .getByRole('menuitemradio', { name: 'Continuous', exact: true })
    .tap();
  await ready();
  const loadedKeys = new Set(requests.at(-1).search_keys);
  assert.equal(loadedKeys.size, 20);
  const reads = requests.length;
  await page.getByRole('button', { name: 'Load more', exact: true }).tap();
  await ready();
  assert.equal(requests.length, reads + 1, 'Append uses one native cell batch');
  assert(
    requests.at(-1).search_keys.every((key) => !loadedKeys.has(key)),
    'Existing server cells are retained during append'
  );
  assert.equal(
    await first.getByRole('link').getAttribute('href'),
    'https://example.com/a'
  );
  assert.equal(
    await table.getAttribute('aria-rowcount'),
    String(loadedKeys.size + requests.at(-1).search_keys.length + 1)
  );
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.clock.resume();
  await first.getByRole('button', { name: 'publish (2)', exact: true }).click();
  await notes.getByLabel('Note text', { exact: true }).fill('');
  await page.evaluate(() =>
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        read: async () => [
          {
            types: ['image/png'],
            getType: async () =>
              new Blob(['clipboard image'], { type: 'image/png' })
          }
        ]
      }
    })
  );
  await notes
    .getByRole('button', { name: 'Attach image from clipboard', exact: true })
    .click();
  await notes
    .locator('.note-attachment')
    .getByText('clipboard.png', { exact: true })
    .waitFor();
  await notes
    .getByRole('button', { name: 'Remove attachment', exact: true })
    .click();
  await attachNote(notes, {
    name: 'attachment-only.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7u0AAAAASUVORK5CYII=',
      'base64'
    )
  });
  await notes.getByRole('button', { name: 'Send note', exact: true }).click();
  const imageNote = notes
    .locator('.note-entry')
    .filter({ hasText: 'attachment-only' });
  await imageNote.locator('.attachment-card').waitFor();
  assert.equal(
    await imageNote.locator('.attachment-card').count(),
    1,
    'One card per attachment, without web/icon duplicates'
  );
  await imageNote
    .getByRole('button', { name: 'File preview', exact: true })
    .click();
  await preview.waitFor();
  await page.waitForFunction(
    () => document.querySelector('.file-preview[open] img')?.naturalWidth > 0
  );
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .click();
  if (process.argv[3])
    await notes.screenshot({
      path: process.argv[3].replace('.png', '-attachment-only.png'),
      animations: 'disabled'
    });
  await closeInspector(page);
  // Each Inspector context retains its reading position, including a close/reopen.
  await remote('execute_cmd', [
    'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
    {
      search_key: 'sthpw/login_group?code=CELL_A',
      process: 'publish',
      note:
        'Scroll marker\n' +
        Array.from({ length: 70 }, (_, index) => 'Line ' + index).join('\n'),
      files: []
    }
  ]);
  await first.getByRole('button', { name: /^publish \(/ }).click();
  // The external write must be loaded before testing the retained reading position.
  await notes
    .getByRole('button', { name: 'Refresh notes and task', exact: true })
    .click();
  await notes.getByText(/Scroll marker/).waitFor();
  const timeline = notes.locator('.notes-timeline');
  await timeline.evaluate((node) => {
    node.scrollTop = 120;
  });
  assert.equal(await timeline.evaluate((node) => node.scrollTop), 120);
  await closeInspector(page);
  await second.getByRole('button', { name: 'Add note', exact: true }).click();
  await notes.getByText('No notes for this process', { exact: true }).waitFor();
  await closeInspector(page);
  await first.getByRole('button', { name: /^publish \(/ }).click();
  await notes.getByText(/Scroll marker/).waitFor();
  assert.equal(
    await timeline.evaluate((node) => node.scrollTop),
    120,
    'Closing and reopening restores the reading position'
  );
  await notes
    .getByLabel('Note text', { exact: true })
    .fill('Persistent Inspector text');
  await page.waitForFunction(() =>
    Object.keys(localStorage).some(
      (key) =>
        key.startsWith('tactic_stream.notes.admin.') &&
        localStorage.getItem(key) === 'Persistent Inspector text'
    )
  );
  await closeInspector(page);
  page.once('dialog', (dialog) => dialog.accept());
  await page.reload();
  await ready();
  await first.getByRole('button', { name: /^publish \(/ }).click();
  await notes.getByText(/Scroll marker/).waitFor();
  assert.equal(
    await notes.getByLabel('Note text', { exact: true }).inputValue(),
    'Persistent Inspector text',
    'Text draft survives reload under the same authenticated account'
  );
  await closeInspector(page);
  await second.getByRole('button', { name: 'Add note', exact: true }).click();
  await notes.getByText('No notes for this process', { exact: true }).waitFor();
  assert.equal(
    await notes.getByLabel('Note text', { exact: true }).inputValue(),
    '',
    'Another object does not receive the stored draft'
  );
  await closeInspector(page);
  assert.deepEqual(errors, []);
  console.log(
    'Native cells: expressions/format/link/boolean/batched reads/selection/mixed state/column focus/touch320 OK'
  );
} catch (error) {
  await page.screenshot({ path: '../.screenshots/table-cells-failure.png' });
  throw error;
} finally {
  await browser.close();
}
