import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { openViewActions } from './project_selection.mjs';
const base = process.argv[2],
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || undefined
  });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } }),
  errors = [];
page.setDefaultTimeout(8000);
page.on('pageerror', (error) => errors.push(error.message));
const rpc = async (method, args, kwargs = {}) => {
  const response = await page.request.post(base + '/admin/rpc', {
      data: { method, args, kwargs }
    }),
    value = await response.json();
  assert(response.ok(), JSON.stringify(value));
  return value.result;
};
try {
  const ticket = await rpc('get_ticket', ['admin', 'private-test-password']),
    auth = { ticket, project: 'one' };
  await rpc('insert', [
    auth,
    'config/widget_config',
    {
      search_type: 'contract/entity',
      view: 'insert',
      priority: 100,
      config:
        '<config><insert><element name="name" title="Name"><display class="pyasm.widget.TextWdg"><required>true</required></display></element><element name="description" title="Description"><display class="pyasm.widget.TextAreaWdg"/></element></insert></config>'
    }
  ]);
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    )
  );
  await page.goto(base + '/projects/one/?search_type=contract%2Fentity');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await openViewActions(page);
  await page
    .getByRole('button', { name: 'Create record', exact: true })
    .click();
  const form = page.getByRole('dialog', { name: 'Record form', exact: true });
  await form.getByRole('radio', { name: 'Multiple', exact: true }).click();
  await form
    .getByRole('spinbutton', { name: 'Number of objects', exact: true })
    .fill('3');
  await form
    .getByRole('spinbutton', { name: 'Number of objects', exact: true })
    .press('Tab');
  const name = form.getByLabel('Name', { exact: true });
  await name.fill('Batch ');
  await name.press('End');
  await form.getByRole('button', { name: '{n:03}', exact: true }).click();
  assert.equal(await name.inputValue(), 'Batch {n:03}');
  await form
    .getByRole('button', { name: 'Preview 3 objects', exact: true })
    .click();
  assert.equal(await name.inputValue(), 'Batch 001');
  await form
    .getByLabel('Description', { exact: true })
    .fill('First individual draft');
  await form.getByRole('button', { name: 'Next object', exact: true }).click();
  assert.equal(await name.inputValue(), 'Batch 002');
  await form
    .getByRole('button', { name: 'Previous object', exact: true })
    .click();
  assert.equal(
    await form.getByLabel('Description', { exact: true }).inputValue(),
    'First individual draft'
  );
  await page.setViewportSize({ width: 390, height: 800 });
  assert(
    await form.evaluate((element) => element.scrollWidth <= element.clientWidth)
  );
  await page.setViewportSize({ width: 1280, height: 900 });
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith('/admin/rpc') &&
      response.request().postDataJSON()?.method === 'insert_multiple'
  );
  await form
    .getByRole('button', { name: 'Create 3 objects', exact: true })
    .click();
  const saved = await response;
  assert.equal(saved.status(), 200, await saved.text());
  await form.waitFor({ state: 'hidden' });
  const rows = await rpc('query', [auth, 'contract/entity'], {
    filters: [['name', 'like', 'Batch %']],
    order_bys: ['name']
  });
  assert.deepEqual(
    rows.map((row) => row.name),
    ['Batch 001', 'Batch 002', 'Batch 003']
  );
  assert.equal(rows[0].description, 'First individual draft');
  assert.deepEqual(errors, []);
  console.log(
    'PASS: real batch count/token/preview/individual drafts/resize and one atomic insert_multiple'
  );
} catch (error) {
  console.error(error);
  await page
    .screenshot({
      path: '../.screenshots/object-batch-failure.png',
      timeout: 3000
    })
    .catch(() => {});
  throw error;
} finally {
  await browser.close();
}
