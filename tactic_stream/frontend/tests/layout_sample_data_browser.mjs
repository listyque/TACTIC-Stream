import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.setDefaultTimeout(20000);
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const errors = [],
  writes = [],
  itemReads = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  if (request.url().endsWith('/admin/widget-configuration/save'))
    writes.push(request.postDataJSON());
  if (request.url().endsWith('/admin/result-items'))
    itemReads.push(request.postDataJSON());
});
async function ready(view) {
  await page.waitForFunction((view) => {
    const editor = document.querySelector('.layout-editor');
    return (
      editor?.getAttribute('aria-busy') === 'false' &&
      editor.querySelector('[data-frame="layoutView"]')?.value === view
    );
  }, view);
}
try {
  await page.goto(process.argv[2] + '/projects/one/dashboard/work');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await control('workspacePageEdit').click();
  await control('pageBlock_0').click();
  await control('pageProperty_viewOpen').click();
  await ready('mixed_cards');
  const real = page.locator('.layout-editor .result-presentation').first();
  await real.locator('.result-item').first().waitFor();
  const realElement = await real.elementHandle();
  const reads = itemReads.length;
  await control('layoutElement_collection').click();
  await page.locator('.layout-sample-preview').waitFor();
  await control('layoutSampleScroll').waitFor();
  assert.match(
    await control('layoutPreviewHeading').textContent(),
    /Sample data/
  );
  await control('layoutSampleScroll')
    .getByText('Example item', { exact: true })
    .first()
    .waitFor();
  assert(
    await realElement.evaluate((node) => node.isConnected),
    'Real preview remains mounted'
  );
  await control('layoutElement_title').click();
  await real.waitFor();
  assert(await realElement.evaluate((node) => node.isConnected));
  assert.equal(
    itemReads.length,
    reads,
    'Preview selection does not reload real records'
  );
  await control('layoutElement_collection').click();
  await control('layoutProperty_option_viewOpen').click();
  await ready('empty_card');
  await control('layoutSampleScroll').waitFor();
  const readCount = itemReads.length;
  const sample = page.locator('.layout-sample-preview');
  await sample.locator('[data-canvas-key="title"]').click();
  const handle = sample.locator('[data-canvas-handle="se"]');
  const box = await handle.boundingBox();
  await page.mouse.move(box.x + 7, box.y + 7);
  await page.mouse.down();
  await page.mouse.move(box.x + 7, box.y + 27, { steps: 4 });
  await page.mouse.up();
  assert.equal(await control('adminDiscardDocument').isDisabled(), false, 'Resize changes the layout');
  await control('layoutCheck').click();
  await ready('empty_card');
  await page.waitForFunction(
    () => [...document.querySelectorAll('[data-frame="adminSaveDocument"]')].some(node => node.getClientRects().length && !node.disabled)
  );
  await control('adminSaveDocument').click();
  await control('adminConfirmSave').click();
  await ready('empty_card');
  assert.equal(writes.length, 1);
  assert(
    !writes[0].xml.includes('Example item') &&
      !writes[0].xml.includes('Example value')
  );
  assert.equal(
    itemReads.length,
    readCount,
    'Synthetic data never requests record enrichment'
  );
  await control('layoutSampleScroll')
    .getByText('Example item', { exact: true })
    .first()
    .waitFor();
  await page.screenshot({ path: process.argv[3] + '/browser-sample.png' });
  await control('adminReturnToLayout').click();
  await ready('mixed_cards');
  assert.equal(
    await control('layoutElement_collection').getAttribute('aria-pressed'),
    'true'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Sample preview: missing selected type, empty nested view, retained real renderer, geometry/save, no fake record requests or data writes pass'
  );
} finally {
  await browser.close();
}
