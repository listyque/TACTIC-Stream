import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const base = process.argv[2],
  type = 'visibility_browser/items';
async function request(path, data) {
  const response = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const body = await response.json();
  assert(response.ok, JSON.stringify(body));
  return body.result;
}
const ticket = await request('/admin/rpc', {
  method: 'get_ticket',
  args: ['admin', 'private-test-password']
});
const auth = { ticket, project: 'visibility_browser' };
const rpc = (method, args) =>
  request('/admin/rpc', { method, args: [auth, ...args] });
await request('/admin/rpc', {
  method: 'execute_cmd',
  args: [
    { ticket, project: 'admin' },
    'tactic.command.CreateProjectCmd',
    { project_code: auth.project, project_title: 'Visibility browser' }
  ]
});
await rpc('execute_cmd', [
  'tactic.core.schema_commands.SearchTypeCreatorCmd',
  { search_type_name: type, sobject_pipeline: true, process: ['model', 'rig'] }
]);
await rpc('insert', [
  type,
  { code: 'ONE', name: 'One object', pipeline_code: 'visibility_browser/items' }
]);
await rpc('insert', [
  'config/widget_config',
  {
    search_type: 'SideBarWdg',
    view: 'project_view',
    priority: 100,
    config: `<config><project_view><element name="items" title="Visibility items"><display class="LinkWdg"><search_type>${type}</search_type></display></element></project_view></config>`
  }
]);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  colorScheme: 'dark'
});
page.setDefaultTimeout(12000);
const errors = [],
  queries = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/search-configuration/query'))
    queries.push(request.postDataJSON());
});
const ready = () =>
  page.waitForFunction(
    () =>
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false'
  );
const dialog = page.getByRole('dialog', {
  name: 'Filter Processes',
  exact: true
});
async function open() {
  await page.getByLabel('Search filters and presets', { exact: true }).click();
  await page
    .getByRole('button', { name: 'Filter Processes', exact: true })
    .click();
  await dialog.locator('[data-process-id]').first().waitFor();
}
const row = (key) =>
  dialog.locator('[data-process-id]').filter({
    has: page.locator('[data-frame="processSelectionTitle_process"]', {
      hasText: new RegExp('^' + key + '$', 'i')
    })
  });
try {
  await page.goto(
    base + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ready();
  await selectProject(page, auth.project);
  await page.locator('.navigation-toggle').click();
  await page.locator(`.type-list [data-search-type="${type}"]`).last().click();
  await ready();
  const object = page
    .locator('.workspace-results .result-item-object:visible')
    .first();
  await object.getByRole('button', { name: 'Expand item' }).click();
  await page
    .locator('.workspace-results .result-item-process:visible')
    .filter({ hasText: 'model' })
    .waitFor();
  const before = queries.length;
  await open();
  await row('model').getByRole('checkbox').uncheck();
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  assert(
    await page
      .locator('.workspace-results .result-item-process:visible')
      .filter({ hasText: 'model' })
      .isVisible(),
    'Cancel retains original visibility'
  );
  await open();
  assert(await row('model').getByRole('checkbox').isChecked());
  await row('model').getByRole('checkbox').uncheck();
  await dialog
    .getByRole('button', { name: 'Save and close', exact: true })
    .click();
  await dialog.waitFor({ state: 'hidden' });
  await page
    .locator('.workspace-results .result-item-process:visible')
    .filter({ hasText: 'model' })
    .waitFor({ state: 'hidden' });
  assert.equal(
    queries.length,
    before,
    'Visibility changes do not execute the object query'
  );
  await open();
  assert.equal(
    await row('model').getByRole('checkbox').isChecked(),
    false,
    'Saved tab visibility reopens'
  );
  await row('rig').getByRole('treeitem', { name: 'Rig', exact: true }).click();
  await row('model')
    .getByRole('treeitem', { name: 'Model', exact: true })
    .click({ modifiers: ['Control'] });
  await row('rig').getByRole('checkbox').uncheck();
  assert.equal(await row('model').getByRole('checkbox').isChecked(), false);
  await dialog
    .getByRole('button', { name: 'Show Togglers', exact: true })
    .click();
  await dialog
    .getByRole('button', { name: 'Toggle Process', exact: true })
    .click();
  assert(await row('model').getByRole('checkbox').isChecked());
  assert(await row('rig').getByRole('checkbox').isChecked());
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  assert(await dialog.isVisible(), 'Save keeps the editor open');
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.reload();
  await ready();
  await open();
  assert(await row('model').getByRole('checkbox').isChecked());
  await page.setViewportSize({ width: 360, height: 740 });
  assert(
    await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth),
    'Narrow editor has no horizontal overflow'
  );
  const footer = await dialog
    .locator('[data-frame="processVisibility_cancel"]')
    .boundingBox();
  assert(footer.y + footer.height <= 740);
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  assert.deepEqual(errors, []);
  console.log(
    'Process visibility: actual metadata, cancel/save/reopen, tab persistence, Ctrl selection, togglers, no query reload and narrow layout passed'
  );
} catch (error) {
  await page.screenshot({
    path: '../.screenshots/process-visibility-failure.png'
  });
  throw error;
} finally {
  await browser.close();
}
