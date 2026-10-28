import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.setDefaultTimeout(20000);
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const editor = page.locator('.page-layout-editor:visible');
const errors = [],
  writes = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  if (request.url().endsWith('/admin/rpc')) {
    const args = request.postDataJSON()?.args;
    if (args?.[1]?.endsWith('DashboardCmd') && args[2]?.action === 'apply')
      writes.push(request.url());
  }
  if (
    /\/admin\/(widget-configuration|columns-editor)\/save$/.test(request.url())
  )
    writes.push(request.url());
});
try {
  await page.goto(process.argv[2] + '/projects/one/dashboard/work');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await control('workspacePageEdit').click();
  await editor.waitFor();
  await editor.locator('[data-canvas-key="0.3"]').waitFor();
  await control('pageTreeToggle_0').click();
  assert.equal(await control('pageBlock_0.3').count(), 0);
  await editor.locator('[data-canvas-key="0.3"]').click();
  await control('pageBlock_0.3').waitFor();
  assert.equal(
    await control('pageBlock_0.3').getAttribute('aria-pressed'),
    'true'
  );
  assert(
    await page.evaluate(
      () =>
        document.activeElement?.closest(
          '[data-canvas-key],.canvas-selection'
        ) !== null
    )
  );
  await control('pageBlock_0.0').click();
  await control('pageProperty_title').fill('Unsaved source');
  await control('pageProperty_title').blur();
  await control('pageProperty_viewOpen').click();
  await page.locator('.layout-editor:visible').waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="layoutView"]')?.value === 'hub_items'
  );
  assert.equal(
    await control('layoutSearchType').inputValue(),
    'contract/entity'
  );
  await control('adminReturnToLayout').click();
  await editor.waitFor();
  assert.equal(
    await control('pageProperty_title').inputValue(),
    'Unsaved source'
  );
  assert.equal(
    await control('pageBlock_0.0').getAttribute('aria-pressed'),
    'true'
  );
  await control('pageBlock_0.1').click();
  await control('pageProperty_viewOpen').click();
  await control('definitionViewTitle').waitFor();
  assert.equal(
    await control('definitionCatalogSearchTypeFilter').inputValue(),
    'contract/entity'
  );
  assert.match(
    await control('definitionViewTitle').textContent(),
    /production/
  );
  await control('adminReturnToLayout').click();
  await editor.waitFor();
  assert.equal(
    await control('pageBlock_0.1').getAttribute('aria-pressed'),
    'true'
  );
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  await control('pageBlock_0.2').click();
  await control('pageProperty_hrefOpen').click();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageLayoutChoice"]')?.value ===
      'report'
  );
  await control('pageBlock_0').click();
  await control('pageProperty_title').fill('Unsaved report');
  await control('pageProperty_title').blur();
  await control('adminReturnToLayout').click();
  assert.equal(await control('pageLayoutChoice').inputValue(), 'report');
  assert.equal(
    await control('pageProperty_title').inputValue(),
    'Unsaved report'
  );
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  await control('adminReturnToLayout').click();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="pageLayoutChoice"]')?.value ===
      'work'
  );
  assert.equal(
    await control('pageBlock_0.2').getAttribute('aria-pressed'),
    'true'
  );
  assert.equal(await control('adminReturnToLayout').count(), 0);
  await editor.locator('[data-canvas-key="0.2"]').waitFor();
  assert.equal(writes.length, 0, 'Following links never saves a document');
  assert.deepEqual(errors, []);
  await page.screenshot({ path: process.argv[3] + '/browser-links.png' });
  console.log(
    'Actual editor links: exact card/table/page, draft guards, return selection and canvas tree reveal pass'
  );
} finally {
  await browser.close();
}
