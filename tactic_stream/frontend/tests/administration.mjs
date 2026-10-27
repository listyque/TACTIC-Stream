import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
const page = await browser.newPage({
  viewport: { width: 1400, height: 940 },
  colorScheme: 'dark'
});
page.setDefaultTimeout(15000);
const errors = [],
  requests = [];
page.on('pageerror', (error) => {
  errors.push(error.message);
  console.error(error.message);
});
page.on('console', (message) => {
  if (message.type() === 'error') console.error(message.text());
});
page.on('request', (request) => {
  if (request.url().endsWith('/admin/rpc'))
    requests.push(request.postDataJSON());
});
const admin = page.getByRole('dialog', { name: 'Administration', exact: true }),
  control = (id) => admin.locator('[data-frame="' + id + '"]:visible');
const selectors = {
  types: '.search-types-editor',
  schema: '.schema-editor',
  workflow: '.workflow-editor',
  columns: '.columns-editor',
  raw: '.raw-database',
  layouts: '.layout-editor',
  sidebar: '.sidebar-editor',
  users: '.security-users',
  groups: '.security-groups',
  rules: '.security-rules'
};
async function select(id) {
  await page.waitForFunction(() => {
    const shell = document.querySelector('.administration-frame-shell'),
      header = shell?.querySelector('[data-frame="administrationHeader"]');
    return (
      header &&
      Math.abs(
        header.getBoundingClientRect().width -
          shell.getBoundingClientRect().width
      ) < 0.5
    );
  });
  const picker = control('administrationSectionSelector');
  if (await picker.isVisible()) await picker.selectOption(id);
  else await control('adminSection_' + id).click();
  await admin.locator(selectors[id] + ':visible').waitFor();
  await page.waitForFunction(
    (selector) =>
      document.querySelector(selector)?.getAttribute('aria-busy') !== 'true',
    selectors[id]
  );
}
async function section(prefix, value) {
  const button = control(prefix + '_' + value);
  if (await button.count()) await button.click();
  else await control(prefix).selectOption(value);
}
async function shot(name) {
  if (process.argv[3]) {
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: process.argv[3] + '/' + name + '.png',
      animations: 'disabled'
    });
  }
}
const loads = () =>
  requests.filter(
    (body) =>
      body.method === 'execute_cmd' &&
      String(body.args[1]).includes('WorkflowCmd') &&
      body.args[2].action === 'load' &&
      body.args[2].identity === 'capture/admin_capture'
  ).length;
try {
  if (process.argv[3]) await mkdir(process.argv[3], { recursive: true });
  await page.goto(process.argv[2] + '/projects/capture/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await selectProject(page, 'capture');
  await page.getByLabel('More options', { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Administration', exact: true })
    .click();
  await admin.waitFor();
  assert.equal(
    await admin
      .locator('[data-frame="administrationHeader"] .app-window-controls')
      .count(),
    1,
    'window controls remain attached'
  );
  for (const id of Object.keys(selectors).filter((id) => id !== 'workflow')) {
    await select(id);
    assert.equal(
      await admin.locator('.administration-page:visible').count(),
      1,
      id
    );
    await shot('frame-' + id + '-1400');
    await page.setViewportSize({ width: 900, height: 740 });
    await shot('frame-' + id + '-900');
    await page.setViewportSize({ width: 1400, height: 940 });
  }
  await select('columns');
  await admin
    .locator('[data-frame="definitionRow_' + process.argv[4] + '"]')
    .click();
  await control('definitionCatalogTitle').waitFor();
  assert.equal(await control('definitionCatalogTitle').inputValue(), 'Code');
  await control('definitionColumnDown').click();
  assert.equal(
    await control('definitionCatalogTitle').inputValue(),
    'Code',
    'selection follows the moved column'
  );
  await control('definitionCatalogMode_xml').click();
  const moved = await control('definitionCatalogXml').inputValue();
  assert(
    moved.indexOf('name="name"') < moved.indexOf('name="code"'),
    'native XML element order changes'
  );
  assert(
    moved.includes('<!--keep reorder-->') &&
      moved.includes('custom="kept"') &&
      moved.includes('<extension value="kept"'),
    'unknown XML survives moving a column'
  );
  await control('adminSaveDocument').click();
  await control('adminConfirmSave').click();
  await page.waitForFunction(
    () =>
      document.querySelector('.columns-editor').getAttribute('aria-busy') ===
      'false'
  );
  await control('adminReloadDocument').click();
  await page.waitForFunction(
    () =>
      document.querySelector('.columns-editor').getAttribute('aria-busy') ===
      'false'
  );
  assert(
    (await control('definitionCatalogXml').inputValue()).indexOf(
      'name="name"'
    ) <
      (await control('definitionCatalogXml').inputValue()).indexOf(
        'name="code"'
      ),
    'reordered XML survives server save and readback'
  );
  await select('schema');
  await control('adminCreateSchemaType').click();
  const creator = page.getByRole('dialog', {
    name: 'New Search Type',
    exact: true
  });
  await creator.waitFor();
  await creator
    .locator('[data-frame="adminSearchTypeTitle"]')
    .fill('Cancelled draft');
  await shot('frame-type-creator');
  await creator
    .getByRole('button', { name: 'Close Search Type creator', exact: true })
    .click();
  await creator.waitFor({ state: 'hidden' });
  await select('types');
  await control('adminSearchType_capture/assets').click();
  await section('searchTypePages', 'workflow');
  const before = loads();
  await control('adminSearchTypeWorkflow_capture/admin_capture').click();
  await admin.locator('.workflow-editor:visible').waitFor();
  await control('adminPipelineName').waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('.workflow-editor').getAttribute('aria-busy') ===
      'false'
  );
  await shot('frame-workflow-1400');
  await page.setViewportSize({ width: 900, height: 740 });
  await shot('frame-workflow-900');
  await page.setViewportSize({ width: 1400, height: 940 });
  assert.equal(
    loads() - before,
    1,
    'opening a linked workflow reads that identity once'
  );
  await admin.locator('[data-frame="adminWorkflowSearch"]:visible').waitFor();
  const library = await control('adminWorkflowCatalogPanel').boundingBox(),
    sidebar = await control('administrationSidebar').boundingBox(),
    graph = await control('adminGraphCanvas').boundingBox();
  assert(
    library.x >= sidebar.x + sidebar.width + 12,
    'workflow library belongs inside the editor'
  );
  assert(
    library.x + library.width < graph.x,
    'library and graph remain separate panels'
  );
  await control('adminWorkflowSearch').fill('Assets');
  await control('adminToggleNavigation').click();
  await page.waitForFunction(() => {
    const sidebar = document.querySelector(
      '[data-frame="administrationSidebar"]'
    );
    return sidebar && sidebar.getBoundingClientRect().width < 100;
  });
  const collapsed = await control('adminSection_workflow').boundingBox(),
    collapsedIcon = await control('adminSectionIcon_workflow').boundingBox(),
    expand = await control('adminToggleNavigation').boundingBox();
  assert(collapsed.width >= 40, 'collapsed selection remains usable');
  assert(collapsedIcon.x >= collapsed.x + 8);
  assert(
    collapsedIcon.x + collapsedIcon.width <= collapsed.x + collapsed.width - 8
  );
  assert(
    Math.abs(
      collapsedIcon.x + collapsedIcon.width / 2 - expand.x - expand.width / 2
    ) < 1
  );
  await shot('frame-workflow-collapsed');
  assert.equal(await control('adminWorkflowSearch').count(), 1);
  await control('adminToggleNavigation').click();
  assert.equal(
    await control('adminWorkflowSearch').inputValue(),
    'Assets',
    'catalog state survives collapsing its host'
  );
  await control('adminWorkflowSearch').fill('');
  const split = await control('adminCatalogSplit').boundingBox();
  await page.mouse.move(split.x + split.width / 2, split.y + split.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    split.x + split.width / 2 + 40,
    split.y + split.height / 2
  );
  await page.mouse.up();
  await page.waitForFunction(
    (width) =>
      document
        .querySelector('[data-frame="adminWorkflowCatalogPanel"]')
        .getBoundingClientRect().width >
      width + 30,
    library.width
  );
  await page.setViewportSize({ width: 720, height: 740 });
  await admin
    .locator(
      '[data-frame="adminGraphPanels"]:visible,[data-frame="adminGraphPanels_catalog"]:visible'
    )
    .first()
    .waitFor();
  await section('adminGraphPanels', 'catalog');
  await control('adminWorkflowSearch').waitFor();
  assert.equal(
    await admin.locator('#administration-workflow-library').count(),
    0,
    'phone/tablet catalog stays inside the editor'
  );
  await page.setViewportSize({ width: 1400, height: 940 });
  await admin.locator('[data-frame="adminWorkflowSearch"]:visible').waitFor();
  await control('adminGraphCanvas').waitFor();
  assert.equal(
    await control('adminPipelineName').inputValue(),
    'Assets',
    'existing workflow is loaded, not replaced with a new draft'
  );
  assert.equal(
    await page.locator('dialog[open]').count(),
    1,
    'workflow uses the main Administration section'
  );
  await control('adminPipelineName').fill('Retained workflow draft');
  await select('users');
  await select('workflow');
  assert.equal(
    await control('adminPipelineName').inputValue(),
    'Retained workflow draft'
  );
  assert.equal(loads() - before, 1);
  const saves = () =>
    requests.filter(
      (body) =>
        body.method === 'execute_cmd' &&
        String(body.args[1]).includes('WorkflowCmd') &&
        body.args[2].action === 'save'
    ).length;
  const writes = saves();
  await control('adminSaveDocument').click();
  assert.equal(saves(), writes);
  await control('adminConfirmSave').click();
  await page.waitForFunction(
    () =>
      document.querySelector('.workflow-editor').getAttribute('aria-busy') ===
      'false'
  );
  assert.equal(saves(), writes + 1);
  await select('users');
  await control('adminCreateDocument').click();
  await control('adminUserLogin').fill('retained_draft');
  await control('segmentedButtonSegment_account').click();
  await control('adminUserPassword').fill('private-unsaved-password');
  await select('groups');
  await control('createSecurityGroup').click();
  await control('securityGroupName').fill('retained_group');
  assert.equal(
    await control('administrationProjectSelector').isDisabled(),
    true
  );
  await select('users');
  assert.equal(
    await control('adminUserPassword').inputValue(),
    'private-unsaved-password'
  );
  await select('types');
  await control('administrationCloseButton').click();
  await admin.locator('.security-users:visible').waitFor();
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  await control('administrationCloseButton').click();
  await admin.locator('.security-groups:visible').waitFor();
  await control('adminDiscardDocument').click();
  await control('confirmDiscardSecurityGroup').click();
  await control('administrationCloseButton').click();
  await admin.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'Ten Frame Administration sections, window chrome, linked-workflow identity/read/save, retained drafts and close guards passed'
  );
} finally {
  await browser.close();
}
