import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL
});
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  hasTouch: true
});
page.setDefaultTimeout(10000);
const errors = [],
  calls = [],
  dropCalls = [],
  forms = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().endsWith('/admin/form')) {
    const { ticket, ...scope } = request.postDataJSON();
    forms.push(scope);
  }
  if (!request.url().endsWith('/admin/rpc')) return;
  const body = request.postDataJSON();
  if (body.args?.[1] === 'tactic.ui.table.TableParentGroupCmd')
    calls.push({ ...body.args[2], project: body.args[0].project });
  if (body.args?.[1] === 'tactic.ui.table.DropElementEditCmd')
    dropCalls.push({ ...body.args[2], project: body.args[0].project });
});
const ready = () =>
  page.waitForFunction(() => {
    const views = [
      ...document.querySelectorAll('.workspace-results .configured-view')
    ].filter((node) => node.offsetParent);
    return (
      document
        .querySelector('.workspace-results')
        ?.getAttribute('aria-busy') === 'false' &&
      views.length &&
      views.every((node) => node.getAttribute('aria-busy') === 'false')
    );
  });
try {
  await page.goto(
    process.argv[2] + '/projects/one/?search_type=sthpw/note&view=parent_test'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  const row = page
    .getByRole('row')
    .filter({ hasText: process.argv[3] })
    .first();
  await row.getByRole('button', { name: 'Change parent', exact: true }).tap();
  const picker = page.locator('.table-parent-picker:popover-open');
  const candidate = picker.locator(
    '[data-frame="parentCandidate:contract/entity?project=one&code=B"]'
  );
  await candidate.waitFor();
  assert.equal(calls.length, 2, 'one prepare and one candidate request');
  assert(calls[0].source_id);
  await candidate.click();
  await picker.getByRole('button', { name: 'Cancel', exact: true }).click();
  await picker.locator('[data-frame="confirmationReject"]').click();
  await page.setViewportSize({ width: 900, height: 620 });
  const bounds = await picker.boundingBox();
  assert(
    bounds.x >= 0 &&
      bounds.x + bounds.width <= 901 &&
      bounds.y >= 0 &&
      bounds.y + bounds.height <= 621
  );
  let held = false;
  await page.route('**/admin/rpc', async (route) => {
    const body = route.request().postDataJSON();
    if (
      !held &&
      body.args?.[1] === 'tactic.ui.table.TableParentGroupCmd' &&
      body.args[2].action === 'save'
    ) {
      held = true;
      await route.fetch();
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Test lost response' })
      });
    }
    return route.continue();
  });
  await picker.getByRole('button', { name: 'Save', exact: true }).click();
  await picker
    .getByRole('button', { name: 'Check saved changes', exact: true })
    .click();
  await picker.waitFor({ state: 'hidden' });
  await ready();
  assert.equal(
    calls.filter((call) => call.action === 'save').length,
    1,
    'uncertain writes must never replay automatically'
  );
  assert.equal(calls.at(-1).action, 'check');
  assert.equal(calls.at(-1).project, 'one');
  await page.setViewportSize({ width: 1280, height: 900 });
  await row.locator('[data-frame="parentCell"]').evaluate((el) => {
    const dataTransfer = new DataTransfer();
    dataTransfer.setData(
      'application/x-tactic-frame',
      JSON.stringify({
        searchType: 'contract/entity',
        searchKeys: ['contract/entity?project=one&code=A']
      })
    );
    el.dispatchEvent(
      new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer })
    );
  });
  await picker.waitFor();
  const droppedParent = picker.locator(
    '[data-frame="parentCandidate:contract/entity?project=one&code=A"]'
  );
  await droppedParent.waitFor();
  assert.equal(await droppedParent.getAttribute('aria-selected'), 'true');
  await picker.getByRole('button', { name: 'Save', exact: true }).click();
  await picker.waitFor({ state: 'hidden' });
  await ready();
  await page
    .locator('.handler-table-heading')
    .filter({ hasText: 'PARENT' })
    .click({ button: 'right' });
  await page
    .getByRole('menuitemradio', { name: 'Group by this column', exact: true })
    .click();
  await page.locator('[data-frame="parentGroupTitle"]').first().waitFor();
  assert.equal(
    await page.locator('[data-frame="parentGroupTitle"]').count(),
    1
  );
  const group = page
    .locator('.handler-table-group')
    .filter({ has: page.locator('[data-frame="parentGroupTitle"]') })
    .first();
  await group.locator('[data-frame="parentGroupToggle"]').click();
  await group.locator('[data-frame="parentGroupToggle"]').click();
  await group.locator('[data-frame="parentGroupCreate"]').click();
  await page
    .getByRole('dialog')
    .filter({ has: page.getByRole('button', { name: 'Create', exact: true }) })
    .waitFor();
  assert.equal(forms.at(-1).project, 'one');
  assert.equal(forms.at(-1).search_type, 'sthpw/note');
  assert.equal(forms.at(-1).parent_key, 'contract/entity?project=one&code=A');
  await page.goto(
    process.argv[2] +
      '/projects/one/?search_type=contract/collection&view=drop_test'
  );
  await ready();
  await page.getByLabel('Change search results view', { exact: true }).click();
  await page.getByRole('menuitemradio', { name: 'Table', exact: true }).click();
  await ready();
  const emptyRow = page.getByRole('row').filter({ hasText: 'EMPTY' }).first();
  await emptyRow.locator('[data-frame="dropSurface"]').evaluate((el) => {
    const dataTransfer = new DataTransfer();
    dataTransfer.setData(
      'application/x-tactic-frame',
      JSON.stringify({
        searchType: 'contract/entity',
        searchKeys: ['contract/entity?project=one&code=A']
      })
    );
    el.dispatchEvent(
      new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer })
    );
  });
  const related = page.locator('.related-objects[open]');
  await related.waitFor();
  await related
    .locator(
      '[data-frame="linkedLinkList"] [data-frame="linkRow_contract/entity?project=one&code=A"]'
    )
    .waitFor();
  await related.locator('[data-frame="linkSave"]').click();
  await related.waitFor({ state: 'hidden' });
  await ready();
  assert.equal(dropCalls.length, 1);
  assert.deepEqual(dropCalls[0].target_keys, [
    'contract/entity?project=one&code=A'
  ]);
  await emptyRow.locator('[data-frame="dropEdit"]').click();
  await related
    .locator(
      '[data-frame="linkedLinkList"] [data-frame="linkRow_contract/entity?project=one&code=A"]'
    )
    .waitFor();
  await related
    .locator(
      '[data-frame="linkedLinkList"] [data-frame="linkRow_contract/entity?project=one&code=A"]'
    )
    .click();
  await related.locator('[data-frame="linkTransferButton"]').click();
  await related.locator('[data-frame="linkSave"]').click();
  await related.waitFor({ state: 'hidden' });
  await ready();
  assert.equal(dropCalls.length, 2);
  assert.deepEqual(dropCalls[1].target_keys, []);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: real ParentGroup table, touch, dirty cancel, resize, uncertain save/check, grouping and existing child form'
  );
} finally {
  await browser.close();
}
