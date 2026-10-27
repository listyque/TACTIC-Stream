import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1700, height: 950 },
  colorScheme: 'dark'
});
page.setDefaultTimeout(15000);
const errors = [],
  writes = [],
  itemReads = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/rpc')) {
    const body = request.postDataJSON();
    if (body?.args?.[1] === 'tactic.ui.table.NestedTableReadCmd')
      itemReads.push(body.args[2]);
    if (
      body?.method === 'execute_cmd' &&
      body.args[1].endsWith('DashboardCmd') &&
      body.args[2].action === 'apply'
    )
      writes.push(body.args[2]);
  }
});
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const editor = page.locator('.page-layout-editor');
async function resize(cancel) {
  const hit = editor.locator('[data-canvas-key="0.0"]');
  await hit.click();
  const handle = editor.locator('[data-canvas-handle="se"]');
  const box = await handle.boundingBox();
  await page.mouse.move(box.x + 7, box.y + 7);
  await page.mouse.down();
  await page.mouse.move(box.x + 47, box.y + 37, { steps: 4 });
  if (cancel) await page.keyboard.press('Escape');
  await page.mouse.up();
}
try {
  await page.goto(process.argv[2] + '/projects/admin/dashboard/review');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.workspace-page[aria-busy="false"]').waitFor();
  await control('workspacePageEdit').click();
  await editor.waitFor();
  await editor.locator('[data-canvas-key="0.0"]').waitFor();
  assert.equal(await control('pageLayoutChoice').inputValue(), 'review');
  const childHit = editor.locator('[data-canvas-key="0.0"]');
  await childHit.click();
  await childHit.click({ modifiers: ['Alt'] });
  await control('pageProperty_gap').waitFor();
  const editCanvasWidth = (await control('pageCanvasPanel').boundingBox())
    .width;
  await control('pagePreviewMode').click();
  assert.equal(
    await editor.locator('[data-canvas-key]').count(),
    0,
    'Clean preview has no editor overlays'
  );
  assert.equal(await control('pageLayersPanel').count(), 0);
  assert(
    (await control('pageCanvasPanel').boundingBox()).width > editCanvasWidth
  );
  assert.equal(writes.length, 0);
  await control('pagePreviewMode').click();
  await resize(true);
  assert.equal(await control('pageProperty_height').inputValue(), '60');
  assert.equal(writes.length, 0);
  await resize(false);
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageProperty_height"]')?.value ===
      '90'
  );
  await control('pagepadding0').fill('12');
  await control('pagepadding0').blur();
  const second = await editor.locator('[data-canvas-key="0.1"]').boundingBox();
  const first = await editor.locator('[data-canvas-key="0.0"]').boundingBox();
  await page.mouse.move(
    second.x + second.width / 2,
    second.y + second.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(first.x + first.width / 2, first.y + 4, { steps: 5 });
  await page.mouse.up();
  await control('adminSaveDocument').waitFor();
  await page.waitForFunction(
    () => !document.querySelector('[data-frame="adminSaveDocument"]')?.disabled
  );
  await control('adminSaveDocument').click();
  assert.equal(writes.length, 0, 'Confirmation precedes any write');
  const saving = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON()?.args?.[2]?.action === 'apply'
  );
  await control('adminConfirmSave').click();
  const saved = await (await saving).json();
  assert.equal(saved.error, undefined, JSON.stringify(saved));
  await page.waitForFunction(
    () =>
      document
        .querySelector('.page-layout-editor')
        ?.getAttribute('aria-busy') === 'false'
  );
  assert.equal(
    await control('adminDocumentError').inputValue(),
    'Layout saved'
  );
  assert.equal(writes.length, 1);
  assert.deepEqual(
    writes[0].document.blocks[0].children.map((row) => row.text),
    ['Next step', 'Project status']
  );
  assert.equal(writes[0].document.blocks[0].children[1].height, 90);
  await control('pageProperty_title').fill('Unsaved');
  await control('pageProperty_title').blur();
  await control('pageLayoutChoice').selectOption('review_two');
  await control('adminConfirmSave').waitFor();
  assert.equal(
    await control('pageLayoutChoice').inputValue(),
    'review',
    'Dirty page stays until confirmation'
  );
  await control('adminConfirmSave').click();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageLayoutChoice"]')?.value ===
      'review_two'
  );
  await editor.locator('[data-canvas-key="0.0"]').waitFor();
  assert.equal(writes.length, 1);
  assert.deepEqual(errors, []);
  await page.screenshot({
    path: process.argv[3] + '/page-editor.png',
    animations: 'disabled'
  });
  await control('administrationCloseButton').click();
  await page
    .getByRole('dialog', { name: 'Administration', exact: true })
    .waitFor({ state: 'hidden' });
  await page.goto(process.argv[2] + '/projects/one/dashboard/detail_preview');
  await page.locator('.workspace-page[aria-busy="false"]').waitFor();
  const treeItem = page.locator('.dashboard-items .result-item').first();
  await treeItem.waitFor();
  await page.evaluate(() => {
    window.originalDashboardItem = document.querySelector(
      '.dashboard-items .result-item'
    );
  });
  const loadedReads = itemReads.length;
  await page.setViewportSize({ width: 1500, height: 850 });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert.equal(
    itemReads.length,
    loadedReads,
    'Resizing does not reread the tree'
  );
  await treeItem.click({ position: { x: 180, y: 30 } });
  await page
    .locator('.workspace-page')
    .getByText('Code: A', { exact: true })
    .waitFor();
  assert.equal(
    itemReads.length,
    loadedReads,
    'Selection only loads the details pane'
  );
  assert(
    await page.evaluate(
      () =>
        window.originalDashboardItem ===
        document.querySelector('.dashboard-items .result-item')
    ),
    'Existing result item stays mounted'
  );
  const refreshed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON()?.args?.[1] ===
        'tactic.ui.table.NestedTableReadCmd'
  );
  await control('workspacePageRefresh').click();
  await refreshed;
  await treeItem.waitFor();
  assert.equal(
    itemReads.length,
    loadedReads + 1,
    'Explicit refresh still reloads the tree once'
  );
  await control('workspacePageEdit').click();
  await editor.getByText('Code: A', { exact: true }).waitFor();
  await control('pageBlock_0.1.0.0').click();
  await control('pageProperty_title').fill('Draft code');
  await control('pageProperty_title').blur();
  await editor.getByText('Draft code: A', { exact: true }).waitFor();
  await control('pageBinding').selectOption('record');
  await control('pageProperty_search_type').selectOption('contract/entity');
  await control('pageRecordQuery').fill('Перв');
  await control('pageRecordFind').click();
  await page.waitForFunction(() =>
    [...document.querySelector('[data-frame="pageRecord"]').options].some(
      (option) => option.value.includes('contract/entity?')
    )
  );
  const recordKey = await control('pageRecord')
    .locator('option')
    .evaluateAll(
      (options) =>
        options.find((option) => option.value.includes('contract/entity?'))
          .value
    );
  await control('pageRecord').selectOption(recordKey);
  await control('pageBindingField').selectOption('name');
  await editor.getByText('Draft code: Первый', { exact: true }).waitFor();
  await control('pageBinding').selectOption('project');
  await control('pageBindingField').selectOption('title');
  await editor.getByText('Draft code: One', { exact: true }).waitFor();
  await control('pageBinding').selectOption('selection');
  await control('pageBindingField').selectOption('amount');
  await editor.getByText('Draft code: 0', { exact: true }).waitFor();
  await control('pageBlock_0.0').click();
  await control('pageFilter_0_remove').click();
  await control('pageFilterAdd').click();
  await control('pageFilter_0_column').selectOption('amount');
  assert.equal(await control('pageFilter_0_value').inputValue(), '0');
  await page.waitForFunction(
    () => !document.querySelector('[data-frame="adminSaveDocument"]').disabled
  );
  await control('adminSaveDocument').click();
  await control('adminConfirmSave').click();
  await page.waitForFunction(
    () =>
      document
        .querySelector('.page-layout-editor')
        .getAttribute('aria-busy') === 'false'
  );
  assert.equal(writes.length, 2);
  const dataDraft = writes[1].document;
  assert.deepEqual(dataDraft.blocks[0].children[0].filters, [
    { column: 'amount', relation: '=', value: 0 }
  ]);
  const bound = dataDraft.blocks[0].children[1].children[0].children[0];
  assert.equal(bound.binding, 'selection');
  assert.equal(bound.field, 'amount');
  await page.screenshot({
    path: process.argv[3] + '/page-data-editor.png',
    animations: 'disabled'
  });
  assert.equal(
    writes.length,
    2,
    'Data changes publish only after explicit save'
  );
  await control('administrationCloseButton').click();
  await page
    .getByRole('dialog', { name: 'Administration', exact: true })
    .waitFor({ state: 'hidden' });
  console.log(
    'Page editor: navigation target, real pointer resize/Escape, spacing, explicit save, dirty switch and independent close pass'
  );
} catch (error) {
  await page.screenshot({ path: process.argv[3] + '/failure.png' });
  throw error;
} finally {
  await browser.close();
}
