import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 1920, height: 1400 },
  hasTouch: true
});
page.setDefaultTimeout(10000);
const errors = [],
  forms = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/form')) {
    const { ticket, ...scope } = request.postDataJSON();
    forms.push(scope);
  }
});
const form = page.locator('.record-form-dialog:visible');
try {
  await page.goto(
    process.argv[2] +
      '/projects/one/?search_type=contract/entity&view=publish_test'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  const rows = page.locator('.workspace-results .handler-table [role="row"]');
  const first = rows.filter({ hasText: 'Первый' }).first();
  const second = rows.filter({ hasText: "O'Reilly" }).first();
  await first.locator('[data-frame="tablePublish"]').last().tap();
  await form.getByLabel('Name', { exact: true }).fill('Published in browser');
  assert.equal(forms.at(-1).view, 'review_publish');
  assert.equal(forms.at(-1).search_key, 'contract/entity?project=one&code=A');
  assert.equal(forms.at(-1).operation, undefined);
  assert(
    (
      await form.locator('[data-frame="sobjectEditorParent"]').innerText()
    ).includes('code=A')
  );
  const chooser = page.waitForEvent('filechooser');
  await form.locator('[data-frame="fileInputChoose"]').click();
  await (
    await chooser
  ).setFiles({
    name: 'published.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Configured browser publication')
  });
  const count = forms.length;
  const header = await form.locator(':scope > header').boundingBox();
  await page.mouse.move(header.x + 24, header.y + 12);
  await page.mouse.down();
  await page.mouse.move(header.x + 24, header.y + 430, { steps: 12 });
  await page.mouse.up();
  assert(await form.evaluate((node) => node.matches(':modal')));
  const otherTarget = await second
    .locator('[data-frame="tablePublish"]')
    .last()
    .boundingBox();
  await page.touchscreen.tap(
    otherTarget.x + otherTarget.width / 2,
    otherTarget.y + otherTarget.height / 2
  );
  assert.equal(
    await form.getByLabel('Name', { exact: true }).inputValue(),
    'Published in browser'
  );
  assert.equal(
    forms.length,
    count,
    'A second row cannot overwrite an unsaved publication'
  );
  await form.locator('[data-frame="sobjectEditorSubmit"]').click();
  await form.waitFor({ state: 'hidden' });
  await page
    .getByRole('button', { name: 'Multi Publish', exact: true })
    .click();
  await form.getByLabel('Name', { exact: true }).waitFor();
  assert.equal(forms.at(-1).view, 'multi_publish');
  assert.equal(forms.at(-1).search_key, null);
  assert.equal(
    await form.locator('[data-frame="sobjectCreateMode"]').count(),
    0
  );
  await form.locator('[data-frame="sobjectEditorCancel"]').click();
  await form.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'PASS: configured Publish upload, target, draft admission and Multi Publish header on real browser input'
  );
} finally {
  await browser.close();
}
