import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const base = process.argv[2];
async function request(path, data) {
  const response = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const result = await response.json();
  assert(response.ok, JSON.stringify(result));
  return result.result;
}
const ticket = await request('/admin/rpc', {
  method: 'get_ticket',
  args: ['admin', 'private-test-password']
});
const auth = { ticket, project: 'mobile_forms' },
  type = 'mobile_forms/objects';
const rpc = (method, args, kwargs = {}) =>
  request('/admin/rpc', { method, args: [auth, ...args], kwargs });
await request('/admin/rpc', {
  method: 'execute_cmd',
  args: [
    { ticket, project: 'admin' },
    'tactic.command.CreateProjectCmd',
    { project_code: 'mobile_forms', project_title: 'Mobile forms' }
  ]
});
const fields = Array.from({ length: 12 }, (_, index) => 'detail_' + index);
await rpc('execute_cmd', [
  'tactic.core.schema_commands.SearchTypeCreatorCmd',
  {
    search_type_name: type,
    asset_title: 'Mobile objects',
    column_name: fields,
    data_type: fields.map(() => 'text')
  }
]);
for (const view of ['insert', 'edit'])
  await rpc('insert', [
    'config/widget_config',
    {
      search_type: type,
      view,
      priority: 100,
      config: `<config><${view}><element name="name" title="Name"/><element name="description" title="Description"><display class="pyasm.widget.TextAreaWdg"/></element>${fields.map((name, index) => `<element name="${name}" title="Detail ${index}"/>`).join('')}</${view}></config>`
    }
  ]);
await rpc('insert', [
  'config/widget_config',
  {
    search_type: 'SideBarWdg',
    view: 'project_view',
    priority: 100,
    config: `<config><project_view><element name="mobile" title="Mobile objects"><display class="LinkWdg"><search_type>${type}</search_type></display></element></project_view></config>`
  }
]);
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || undefined
});
let page;
try {
  page = await browser.newPage({
    viewport: { width: 320, height: 740 },
    hasTouch: true,
    isMobile: true,
    colorScheme: 'dark'
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const fits = async (dialog) =>
    assert(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)
    );
  await page.goto(
    base + '/projects/admin/?search_type=sthpw/project&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await selectProject(page, 'mobile_forms');
  await page.locator('.navigation-toggle').tap();
  await page.locator(`.type-list [data-search-type="${type}"]`).tap();
  await page.getByLabel('Result actions', { exact: true }).tap();
  await page
    .locator('.workspace-menu[open]')
    .getByRole('button', { name: 'Create record', exact: true })
    .tap();
  const form = page.getByRole('dialog', { name: 'Record form', exact: true });
  const name = form.getByLabel('Name', { exact: true });
  await name.waitFor();
  assert.equal(
    await name.evaluate((node) => document.activeElement === node),
    false,
    'Opening a phone form must not automatically summon the keyboard'
  );
  await name.fill('Phone object');
  const description = form.getByLabel('Description', { exact: true });
  await description.fill('Phone description');
  await description.press('End');
  await description.press('Enter');
  assert.equal(await description.inputValue(), 'Phone description\n');
  const submit = form.getByRole('button', {
    name: /^(?:Create|Save changes)$/,
    exact: true
  });
  for (const width of [320, 360]) {
    await page.setViewportSize({ width, height: 740 });
    await fits(form);
    const footer = await form.locator('footer').boundingBox();
    assert(footer.y + footer.height <= 740);
    assert(await submit.isVisible());
    assert(
      await form
        .locator('.record-form > fieldset')
        .evaluate((node) => node.scrollHeight > node.clientHeight)
    );
  }
  await form.getByLabel('Detail 11', { exact: true }).fill('Last field');
  await form.screenshot({ path: '../.screenshots/mobile-object-form.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  assert.equal(await name.inputValue(), 'Phone object');
  await page.setViewportSize({ width: 320, height: 740 });
  await form.getByRole('button', { name: 'Close', exact: true }).tap();
  await form.getByRole('button', { name: 'Keep editing', exact: true }).tap();
  await submit.tap();
  await form.waitFor({ state: 'hidden' });
  const rows = await rpc('query', [type], {
    filters: [['name', 'Phone object']]
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].detail_11, 'Last field');
  assert.equal(rows[0].description, 'Phone description\n');
  await page
    .locator('.workspace-results')
    .getByText('Phone object', { exact: true })
    .waitFor();
  await page
    .locator('.workspace-results .result-item:visible')
    .getByLabel('Item actions', { exact: true })
    .first()
    .tap();
  await page
    .getByRole('menuitem', { name: 'Object actions', exact: true })
    .tap();
  const actions = page.getByRole('dialog', {
    name: 'Object actions',
    exact: true
  });
  await actions.waitFor();
  await fits(actions);
  assert.equal(await actions.locator('button:not(.app-button)').count(), 0);
  await actions.getByRole('button', { name: 'Edit record', exact: true }).tap();
  await name.waitFor();
  await name.fill('Unknown result');
  await page.route('**/admin/rpc', async (route) => {
    if (
      !route.request().postDataJSON().args?.includes('tactic.ui.panel.EditCmd')
    )
      return route.continue();
    await route.fetch();
    await route.abort('failed');
  });
  await submit.tap();
  await form
    .getByRole('alert')
    .filter({ hasText: 'The save result is unknown' })
    .waitFor();
  assert.equal(await submit.isDisabled(), true);
  assert.equal(
    (await rpc('query', [type], { filters: [['name', 'Unknown result']] }))
      .length,
    1
  );
  await form.getByRole('button', { name: 'Close', exact: true }).tap();
  await form
    .getByRole('button', { name: 'Discard changes', exact: true })
    .tap();
  await page.unroute('**/admin/rpc');
  // Exercise the shared viewer contract with controlled async files; repository ACLs are outside this UI fixture.
  await page.evaluate(() => {
    window.previewWaiters = {};
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    app.$refs.linkPreview.open(
      {
        title: 'Phone attachment',
        __search_key__: 'mobile_forms/objects?project=mobile_forms&code=FILE'
      },
      {
        context: 'publish',
        version: 1,
        files: [
          {
            code: 'first',
            type: 'main',
            filename: 'First.txt',
            size: 20,
            path: 'data/First.txt'
          },
          {
            code: 'second',
            type: 'main',
            filename:
              'work_hours_implementation_plan_with_a_very_long_filename.txt',
            size: 10000,
            path: 'data/Second.txt'
          },
          ...Array.from({ length: 10 }, (_, index) => ({
            code: 'extra-' + index,
            type: 'main',
            filename: 'additional_file_' + index + '.md',
            size: 512,
            path: 'data/additional_file_' + index + '.md'
          }))
        ],
        loadFile: (file) =>
          new Promise((resolve) => {
            window.previewWaiters[file.code] = resolve;
          })
      }
    );
  });
  const preview = page.getByRole('dialog', {
    name: 'File preview',
    exact: true
  });
  await preview.getByLabel('Preview file', { exact: true }).tap();
  const fileChoice = preview.getByRole('menuitemradio', {
    name: 'work_hours_implementation_plan_with_a_very_long_filename.txt',
    exact: true
  });
  await fileChoice.tap();
  await page.evaluate(() =>
    window.previewWaiters.second(
      new Blob(['Current file\n'.repeat(1000)], { type: 'text/plain' })
    )
  );
  await preview.locator('pre').filter({ hasText: 'Current file' }).waitFor();
  await page.evaluate(() =>
    window.previewWaiters.first(
      new Blob(['Stale file'], { type: 'text/plain' })
    )
  );
  assert(!(await preview.locator('pre').innerText()).includes('Stale file'));
  for (const width of [320, 360]) {
    await page.setViewportSize({ width, height: 740 });
    await fits(preview);
    await preview.getByLabel('Preview file', { exact: true }).tap();
    assert.equal(await fileChoice.getAttribute('aria-checked'), 'true');
    assert.equal(
      await fileChoice.locator('.image-picker-preview .app-icon').count(),
      1
    );
    assert.match(await fileChoice.locator('small').innerText(), /TXT.*9.8 KB/);
    assert.equal(
      await preview
        .locator('.file-preview-picker .account-panel')
        .evaluate((node) => node.scrollWidth > node.clientWidth),
      false
    );
    assert.equal(
      await preview
        .locator('.file-preview-picker .account-panel')
        .evaluate((node) => node.scrollHeight > node.clientHeight),
      true,
      'Long file lists scroll vertically inside the menu'
    );
    await page.screenshot({
      path: `../.screenshots/mobile-file-picker-${width}.png`,
      animations: 'disabled'
    });
    await page.keyboard.press('Escape');
    assert(
      (await preview.locator('.file-preview-content').boundingBox()).height >
        550
    );
    assert(
      await preview
        .locator('.file-preview-content')
        .evaluate((node) => node.scrollHeight > node.clientHeight)
    );
    await preview.screenshot({
      path: `../.screenshots/mobile-file-preview-${width}.png`
    });
  }
  await preview.getByLabel('File details', { exact: true }).tap();
  await preview.getByText('data/Second.txt', { exact: true }).waitFor();
  await preview.getByLabel('File details', { exact: true }).tap();
  await page.setViewportSize({ width: 1280, height: 900 });
  await preview
    .getByLabel('Preview file', { exact: true })
    .waitFor({ state: 'detached' });
  await preview.getByText('data/Second.txt', { exact: true }).waitFor();
  assert.equal(
    await preview.getByLabel('Preview file', { exact: true }).count(),
    0
  );
  await preview
    .getByRole('button', { name: 'Close preview', exact: true })
    .click();
  await preview.locator('pre').waitFor({ state: 'detached' });
  assert.equal(await preview.locator('pre').count(), 0);
  await page.setViewportSize({ width: 320, height: 740 });
  await selectProject(page, 'one');
  await page.locator('.navigation-toggle').tap();
  await page
    .locator('.type-list [data-search-type="contract/collection"]')
    .tap();
  const collection = page
    .locator('.workspace-results .result-item:visible')
    .filter({
      has: page.getByText('First', { exact: true })
    })
    .first();
  await collection.getByLabel('Item actions', { exact: true }).tap();
  await page
    .getByRole('menuitem', { name: 'Object actions', exact: true })
    .tap();
  await actions
    .getByRole('button', { name: 'Advanced menu', exact: true })
    .tap();
  await actions
    .getByRole('button', { name: 'Related objects', exact: true })
    .tap();
  const related = page.getByRole('dialog', {
    name: 'Related objects',
    exact: true
  });
  await related
    .getByRole('combobox', { name: 'Related type', exact: true })
    .waitFor();
  await related.locator('.handler-table-row').first().waitFor();
  await fits(related);
  assert.equal(
    await related.getByLabel('Edit Column Definition', { exact: true }).count(),
    0
  );
  await related.getByLabel('View search options', { exact: true }).tap();
  await related
    .getByRole('combobox', { name: 'Filter field', exact: true })
    .selectOption('code');
  await related
    .getByRole('combobox', { name: 'Records per page', exact: true })
    .selectOption('25');
  await related.getByLabel('View search options', { exact: true }).tap();
  await related.getByLabel('Filter value', { exact: true }).fill('J1');
  const filtered = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON().method === 'query'
  );
  await related.getByRole('button', { name: 'Find', exact: true }).tap();
  await filtered;
  await page.waitForFunction(
    () =>
      document
        .querySelector('.related-objects .configured-view')
        ?.getAttribute('aria-busy') === 'false'
  );
  assert.equal(await related.locator('.handler-table-row').count(), 1);
  await related.getByLabel('Filter value', { exact: true }).fill('');
  const restored = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON().method === 'query'
  );
  await related.getByRole('button', { name: 'Find', exact: true }).tap();
  await restored;
  await related.locator('.handler-table-row').nth(1).waitFor();
  assert(
    (await related.locator('.table-container').boundingBox()).height > 400
  );
  for (
    let i = 0;
    i < 10 && (await page.locator('.notification-dismiss:visible').count());
    i++
  )
    await page.locator('.notification-dismiss:visible').first().tap();
  await related.screenshot({
    path: '../.screenshots/mobile-related-objects.png'
  });
  await related
    .getByRole('button', { name: 'Close related objects', exact: true })
    .tap();
  await page.locator('.navigation-toggle').tap();
  await page.locator('.type-list [data-search-type="contract/entity"]').tap();
  const parent = (
    await request('/admin/rpc', {
      method: 'query',
      args: [{ ticket, project: 'one' }, 'contract/entity'],
      kwargs: { filters: [['code', 'A']] }
    })
  )[0];
  const result = await request('/admin/result-items', {
    ticket,
    project: 'one',
    search_type: 'contract/entity',
    search_keys: [parent.__search_key__]
  });
  const branch = result.items[0].branches.find(
    (row) => row.search_type === 'contract/collection'
  );
  assert(branch);
  const mappings = async () =>
    request('/admin/rpc', {
      method: 'query',
      args: [{ ticket, project: 'one' }, 'contract/entity_in_collection'],
      kwargs: { filters: [['entity_code', 'A']] }
    });
  const beforeLinks = await mappings();
  await page.evaluate(
    ({ parent, branch }) => {
      const app =
        document.querySelector('#app').__vue_app__._container._vnode.component
          .subTree.component.subTree.component.proxy;
      app.$refs.relatedObjects.open(parent, 'contract/collection', branch);
    },
    { parent, branch }
  );
  const linking = page.getByRole('dialog', {
    name: 'Link existing objects',
    exact: true
  });
  const linkedPane = linking.locator('[data-frame="linkedLinkList"]');
  await linkedPane.locator('[data-frame^="linkRow_"]').first().waitFor();
  await fits(linking);
  await linkedPane.locator('[data-frame^="linkRow_"]').first().tap();
  await linking
    .getByRole('button', { name: 'Remove selected links', exact: true })
    .tap();
  await linking.getByRole('button', { name: 'Close', exact: true }).tap();
  await linking
    .getByRole('button', { name: 'Continue editing', exact: true })
    .tap();
  await linking.getByRole('button', { name: 'Save', exact: true }).tap();
  await linking.waitFor({ state: 'hidden' });
  assert(
    (await mappings()).length < beforeLinks.length,
    'Unlink must change native instance mappings'
  );
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log(
    'PASS mobile native record create/edit, long form/save footer, dirty draft/resize/lost-response guard, common object actions, related browse/link save and async file selection/details/scroll'
  );
} catch (error) {
  if (page)
    await page.screenshot({
      path: '../.screenshots/mobile-objects-failure.png'
    });
  throw error;
} finally {
  await browser.close();
}
