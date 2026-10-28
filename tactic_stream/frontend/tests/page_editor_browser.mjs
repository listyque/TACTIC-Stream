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
  await control('pageBlock_0.0').click();
  await page.keyboard.press('Control+d');
  await control('pageBlock_0.2').waitFor();
  await page.keyboard.press('Control+z');
  assert.equal(await control('pageBlock_0.2').count(), 0);
  await page.keyboard.press('Control+Shift+z');
  await control('pageBlock_0.2').waitFor();
  await control('pageParent').selectOption('');
  await control('pageBlock_1').waitFor();
  await control('pageParent').selectOption('0');
  await control('pageBlock_0.2').waitFor();
  await control('pageAction_reorder-1').click();
  for (let i = 0; i < 4; i++) await control('pageAction_undo').click();
  assert.equal(await control('pageBlock_0.2').count(), 0);
  assert.equal(await control('pageBlock_1').count(), 0);
  await control('pageAncestor_0').click();
  await control('pageProperty_gap').waitFor();
  await control('pageAncestor_page').click();
  assert.equal(await control('pageParent').count(), 0);
  await control('pageBlock_0.0').click();
  await control('pageAction_duplicate').click();
  await control('pageProperty_title').fill('Typing');
  await page.keyboard.press('Control+z');
  assert.equal(
    await control('pageBlock_0.2').count(),
    1,
    'Text Undo does not undo a widget'
  );
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  assert.equal(await control('pageBlock_0.2').count(), 0);
  assert.ok(await control('pageAction_undo').isDisabled());
  await control('pageCanvasPixels').fill('800');
  await control('pageCanvasPixels').blur();
  await control('pageCanvasZoom').selectOption('50');
  assert.ok(
    Math.abs((await control('pageViewportPaper').boundingBox()).width - 400) < 1
  );
  assert.ok(
    await control('adminSaveDocument').isDisabled(),
    'Viewport settings are not document edits'
  );
  await resize(false);
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageProperty_height"]')?.value ===
      '120'
  );
  assert.ok(
    Math.abs(
      (await editor.locator('[data-canvas-handle="se"]').boundingBox()).width -
        14
    ) < 1
  );
  await control('pageAction_undo').click();
  assert.equal(await control('pageProperty_height').inputValue(), '60');
  await control('pageAncestor_0').click();
  const tallPreview = page.waitForResponse((response) => {
    if (!response.url().endsWith('/admin/rpc')) return false;
    const values = response.request().postDataJSON()?.args?.[2];
    return (
      values?.action === 'preview' && values.document?.blocks?.length === 5
    );
  });
  for (let i = 0; i < 4; i++) await control('pageAction_duplicate').click();
  await tallPreview;
  await page.waitForFunction(() => {
    const scroll = document.querySelector('[data-frame="pageViewportScroll"]');
    return (
      parseFloat(scroll.firstElementChild.style.height) > scroll.clientHeight
    );
  });
  const scrollRange = await control('pageViewportScroll').evaluate((e) => ({
    actual: e.scrollHeight,
    declared: parseFloat(e.firstElementChild.style.height)
  }));
  assert.ok(
    scrollRange.actual <= scrollRange.declared + 1,
    'Scaled pages must not create phantom scroll space: ' +
      JSON.stringify(scrollRange)
  );
  for (let i = 0; i < 4; i++) await control('pageAction_undo').click();
  await control('pageCanvasSize').selectOption('1280');
  await control('pageCanvasZoom').selectOption('200');
  await control('pageViewportScroll').hover();
  await page.mouse.wheel(0, 300);
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageViewportScroll"]').scrollTop > 0
  );
  await page.keyboard.down('Shift');
  await page.mouse.wheel(0, 300);
  await page.keyboard.up('Shift');
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageViewportScroll"]').scrollLeft > 0
  );
  await control('pageCanvasSize').selectOption('auto');
  await control('pageCanvasZoom').selectOption('fit');
  assert.ok(await control('pageAction_undo').isDisabled());
  assert.equal(
    writes.length,
    0,
    'Structure and history only edit the local draft'
  );
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
  const previewReads = itemReads.length;
  const previewItem = await editor
    .locator('.dashboard-items .result-item')
    .first()
    .elementHandle();
  for (const zoom of ['50', '150', 'fit'])
    await control('pageCanvasZoom').selectOption(zoom);
  await control('pageCanvasSize').selectOption('768');
  await control('pageCanvasSize').selectOption('auto');
  assert.equal(
    itemReads.length,
    previewReads,
    'Viewport changes do not reread the item tree'
  );
  assert.ok(
    await previewItem.evaluate((e) => e.isConnected),
    'The existing tree stays mounted'
  );
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
  await control('pageBlock_page').click();
  await control('pageSharedAdd').click();
  await control('pageProperty_search_type').selectOption('contract/entity');
  await control('pageFilter_0_column').selectOption('amount');
  await control('pageFilter_0_relation').selectOption('>=');
  await control('pageSharedEnabled').click();
  await control('pageSharedTitle').fill('Minimum amount');
  await control('pageSharedTitle').blur();
  for (const kind of ['chart', 'summary']) {
    await control('pageAddWidget').selectOption(kind);
    await control('pageProperty_search_type').selectOption('contract/entity');
    await control('pageGroupAdd').click();
    await control('pageGroup_0_column').selectOption('amount');
    await control('pageMeasure_0_function').selectOption('sum');
    await control('pageMeasure_0_column').selectOption('amount');
  }
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
  assert.equal(writes.length, 3);
  await control('administrationCloseButton').click();
  await page
    .getByRole('dialog', { name: 'Administration', exact: true })
    .waitFor({ state: 'hidden' });
  await control('pageRuntime_filter_1_value').fill('1');
  await control('pageRuntimeApply').click();
  await page.locator('.workspace-page[aria-busy="false"]').waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayout_1_number_0"]')
        ?.textContent === '7'
  );
  assert.equal(
    await control('customLayout_2_grid_cell_0_1').textContent(),
    '7'
  );
  await page.setViewportSize({ width: 1350, height: 850 });
  assert.equal(await control('pageRuntime_filter_1_value').inputValue(), '1');
  await control('pageRuntimeReset').click();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayout_1_number_0"]')
        ?.textContent === '0'
  );
  assert.equal(writes.length, 3, 'Runtime filters never save configuration');
  await page.screenshot({
    path: process.argv[3] + '/page-reports-runtime.png',
    animations: 'disabled'
  });
  console.log(
    'Page editor: navigation target, real pointer resize/Escape, spacing, explicit save, dirty switch and independent close pass'
  );
} catch (error) {
  await page.screenshot({ path: process.argv[3] + '/failure.png' });
  throw error;
} finally {
  await browser.close();
}
