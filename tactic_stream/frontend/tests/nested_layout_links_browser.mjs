import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.setDefaultTimeout(20000);
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const errors = [],
  writes = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (
    request.method() === 'POST' &&
    /\/admin\/widget-configuration\/save$/.test(request.url())
  )
    writes.push(request.url());
});
async function view(name, type) {
  await page.waitForFunction(
    ({ name, type }) => {
      const editor = document.querySelector('.layout-editor');
      return (
        editor?.getAttribute('aria-busy') === 'false' &&
        editor.querySelector('[data-frame="layoutView"]')?.value === name &&
        editor.querySelector('[data-frame="layoutSearchType"]')?.value === type
      );
    },
    { name, type }
  );
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
  await view('nested_parent', 'contract/entity');
  await control('layoutElement_nested').click();
  await control('layoutPages_configuration').click();
  const parentSource = await control('layoutSource').inputValue();
  await control('layoutPages_design').click();
  await control('layoutProperty_option_viewOpen').click();
  await view('nested_child', 'contract/collection');
  assert.match(
    await control('adminReturnToLayout').getAttribute('aria-label'),
    /nested_parent/
  );
  await control('layoutElement_inner').click();
  await control('layoutProperty_option_viewOpen').click();
  await view('nested_leaf', 'contract/collection');
  await control('layoutElement_leaf').click();
  await control('layoutProperty_title').fill('Unsaved leaf');
  await control('layoutProperty_title').blur();
  await control('adminReturnToLayout').click();
  await view('nested_leaf', 'contract/collection');
  assert.equal(
    await control('layoutProperty_title').inputValue(),
    'Unsaved leaf'
  );
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  await control('adminReturnToLayout').click();
  await view('nested_child', 'contract/collection');
  assert.equal(
    await control('layoutElement_inner').getAttribute('aria-pressed'),
    'true'
  );
  await control('adminReturnToLayout').click();
  await view('nested_parent', 'contract/entity');
  await control('layoutPages_configuration').click();
  assert.equal(await control('layoutSource').inputValue(), parentSource);
  await control('layoutPages_design').click();
  assert.equal(
    await control('layoutElement_nested').getAttribute('aria-pressed'),
    'true'
  );
  await page.screenshot({ path: process.argv[3] + '/browser-parent.png' });
  await control('layoutProperty_title').fill('Unsaved parent');
  await control('layoutProperty_title').blur();
  await control('layoutProperty_option_viewOpen').click();
  await view('nested_parent', 'contract/entity');
  assert.equal(
    await control('layoutProperty_title').inputValue(),
    'Unsaved parent'
  );
  await control('adminDiscardDocument').click();
  await control('adminConfirmSave').click();
  await control('layoutView').selectOption('broken_parent');
  await view('broken_parent', 'contract/entity');
  await control('layoutElement_broken').click();
  await control('layoutProperty_option_viewOpen').click();
  await view('absent_view', 'contract/entity');
  await control('adminDocumentError').waitFor();
  assert.match(
    await control('adminDocumentError').inputValue(),
    /Referenced item layout is unavailable/
  );
  await control('adminReturnToLayout').click();
  await view('broken_parent', 'contract/entity');
  assert.equal(
    await control('layoutElement_broken').getAttribute('aria-pressed'),
    'true'
  );
  await control('adminReturnToLayout').click();
  await page.locator('.page-layout-editor:visible').waitFor();
  assert.equal(
    await control('pageBlock_0').getAttribute('aria-pressed'),
    'true'
  );
  assert.deepEqual(errors, []);
  assert.equal(writes.length, 0, 'Navigation never saves any layout');
  console.log(
    'Nested layouts: cross-type three-level links, exact return/source/selection, dirty guards, missing-view recovery and outer page return pass'
  );
} finally {
  await browser.close();
}
