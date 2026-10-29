import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1800, height: 1100 }
});
const page = await context.newPage();
page.setDefaultTimeout(20000);
const errors = [],
  writes = [];
const previews = [];
page.on('response', async (response) => {
  if (!response.url().endsWith('/admin/rpc')) return;
  const args = response.request().postDataJSON()?.args;
  if (!args?.[1]?.endsWith('DashboardCmd') || args[2]?.action !== 'preview')
    return;
  const value = await response.json();
  previews.push({
    blocks: args[2]?.document?.blocks?.[0]?.children?.map((item) => item.kind),
    error: value.error,
    model: value.result?.info?.model?.layoutNodes?.[0]?.children?.map(
      (item) => item.kind
    )
  });
});
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/rpc') && request.method() === 'POST') {
    const args = request.postDataJSON()?.args;
    if (args?.[1]?.endsWith('DashboardCmd') && args[2]?.action === 'apply')
      writes.push(args[2]);
  }
});
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const box = (key) => page.locator('[data-canvas-key="' + key + '"]:visible');
const idle = () =>
  page.locator('.workspace-page[aria-busy="false"]:visible').waitFor();
async function property(name, value) {
  await control('pageProperty_' + name).fill(String(value));
  await control('pageProperty_' + name).blur();
}
async function editorMenu(command) {
  await control('pageEditorToolsButton').click();
  await page
    .locator('[data-menu-command="' + command + '"]:visible button')
    .click();
}
try {
  await page.goto(process.argv[2] + '/projects/admin/dashboard/kit_test');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await control('signInSubmit').click();
  await idle();
  await control('workspacePageEdit').click();
  await control('pageAddWidget').selectOption('grid');
  await box('0').waitFor();
  await property('columns', 2);
  await property('min_cell_width', 180);
  await control('pageAddWidget').selectOption('heading');
  await property('text', 'Project dashboard');
  await property('column_span', 2);
  await control('pageSizing_height_mode').selectOption('content');
  await control('pageAddWidget').selectOption('icon');
  await control('pageProperty_icon_size').fill('40');
  await control('pageProperty_icon_size').blur();
  await control('pageAddWidget').selectOption('button');
  await property('title', 'Open target');
  await property(
    'href',
    process.argv[2] + '/projects/admin/dashboard/kit_target'
  );
  await control('pageProperty_button_style').selectOption('primary');
  await control('pageSizing_width_mode').selectOption('content');
  await control('pageSizing_height_mode').selectOption('content');
  await control('pageAddWidget').selectOption('image');
  await control('pageProperty_image_fit').selectOption('contain');
  await control('pageAddWidget').selectOption('divider');
  await control('pageAddWidget').selectOption('spacer');
  await box('0.5').waitFor();
  await control('pageBlock_0.0').click();
  await control('pageProperty_text_align').selectOption('center');
  await control('pagePreviewToggle').click();
  assert.equal(await page.locator('[data-canvas-key]').count(), 0);
  await control('customLayout_0_0')
    .getByText('Project dashboard', { exact: true })
    .waitFor();
  assert.equal(writes.length, 0);
  await page.screenshot({ path: process.argv[3] + '/clean-preview.png' });
  await control('pagePreviewToggle').click();
  await page.waitForFunction(
    () => !document.querySelector('[data-frame="adminSaveDocument"]')?.disabled
  );
  await control('adminSaveDocument').click();
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON()?.args?.[2]?.action === 'apply'
  );
  await control('adminConfirmSave').click();
  await saved;
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="adminDocumentError"]')?.value ===
      'Layout saved'
  );
  assert.equal(writes.length, 1);
  await control('administrationCloseButton').click();
  await page.reload();
  await idle();
  const heading = control('customLayout_0_0_block');
  await heading.waitFor();
  const first = await heading.boundingBox(),
    next = await control('customLayout_0_1_block').boundingBox();
  assert.ok(first.width > next.width * 1.8, 'Heading spans both columns');
  await page.setViewportSize({ width: 360, height: 900 });
  await page.waitForFunction(() => {
    const a = document
      .querySelector('[data-frame="customLayout_0_1_block"]')
      ?.getBoundingClientRect();
    const b = document
      .querySelector('[data-frame="customLayout_0_2_block"]')
      ?.getBoundingClientRect();
    return a && b && Math.abs(a.x - b.x) < 1 && b.y > a.y;
  });
  await page.screenshot({ path: process.argv[3] + '/phone.png' });
  await page.setViewportSize({ width: 1800, height: 1100 });
  await control('customLayout_0_2').click();
  await page.waitForURL('**/dashboard/kit_target');
  assert.equal(
    context.pages().length,
    1,
    'Internal dashboard links use the existing workspace'
  );
  assert.deepEqual(errors, []);
  assert.equal(writes.length, 1);
  console.log(
    'Layout kit: create from blank, grid spans, native blocks, fit sizing, clean preview, Save/reload, responsive flow and real link pass'
  );
} catch (error) {
  console.log(JSON.stringify({ errors, previews }, null, 2));
  await page.screenshot({ path: process.argv[3] + '/failure.png' });
  throw error;
} finally {
  await browser.close();
}
