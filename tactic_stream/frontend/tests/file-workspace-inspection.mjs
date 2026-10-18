import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
const browser = await chromium.launch({
  headless: true,
  channel: 'msedge',
  ignoreDefaultArgs: ['--hide-scrollbars']
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }),
  errors = [],
  actions = [];
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.url().includes('/file-project/command'))
    actions.push(request.postDataJSON().action);
});
const ui = page.locator('.file-workspace');
const idle = async () => {
  await page.waitForFunction(
    () =>
      document.querySelector('.file-workspace')?.getAttribute('aria-busy') ===
      'false'
  );
  assert.deepEqual(await ui.getByRole('alert').allTextContents(), []);
};
const open = async (title) => {
  await ui.getByLabel('View', { exact: true }).click();
  await ui.getByRole('menuitem', { name: title, exact: true }).click();
  await idle();
};
try {
  await mkdir(process.argv[3], { recursive: true });
  await page.goto(process.argv[2] + '/projects/files/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('file-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await ui.waitFor();
  await idle();
  assert.ok(
    actions.includes('read_batch'),
    'Inspection bootstrap must use the native read batch'
  );
  assert.equal(
    await ui.locator('.file-tree-row.drop').count(),
    0,
    'Rows without a drop target must not paint a drop outline'
  );
  assert.equal(
    await ui.getByRole('button', { name: 'Submit', exact: true }).count(),
    0
  );
  assert.equal(
    await ui
      .getByRole('button', { name: 'New changelist', exact: true })
      .count(),
    0
  );
  await open('Submitted');
  const changes = ui.getByRole('tree', { name: 'Changelist tree' });
  await changes
    .getByRole('button', { name: /^Expand Changelist.*Stream baseline/ })
    .click();
  await idle();
  assert.equal(
    await changes
      .getByRole('button', { name: '0000.txt', exact: true })
      .count(),
    0
  );
  await changes
    .getByRole('button', { name: /^Expand Changelist/ })
    .first()
    .click();
  await idle();
  assert.ok(
    await changes.getByRole('button', { name: '0000.txt', exact: true }).count()
  );
  await open('Files');
  assert.equal(await ui.locator('tbody tr').count(), 200);
  await ui.getByRole('button', { name: 'Next page', exact: true }).click();
  await idle();
  assert.equal(await ui.locator('tbody tr').count(), 200);
  await ui.locator('tbody tr').first().click();
  await ui.getByRole('button', { name: 'Preview', exact: true }).click();
  await ui.getByLabel('File preview', { exact: true }).waitFor();
  assert.match(
    await ui.getByLabel('File preview', { exact: true }).inputValue(),
    /base published/
  );
  assert.ok(actions.includes('file_info'));
  assert.ok(
    !actions.includes('file_preview'),
    'Preview must share the file_info request'
  );
  await open('Workspaces');
  await ui.getByRole('option', { name: 'work', exact: true }).click();
  assert.match(
    await ui.getByLabel('Selected server record', { exact: true }).inputValue(),
    /"code": "work"/
  );
  for (const view of [
    'Streams',
    'Stream Graph',
    'Transfers',
    'Storage administration'
  ])
    await open(view);
  const tabs = ui.locator('.workspace-tabs[data-kind="view"]'),
    tabList = tabs.getByRole('tablist');
  await page.waitForFunction(() => {
    const list = document.querySelector(
      '.file-workspace .workspace-tabs[data-kind="view"] .workspace-tab-list'
    );
    return list && list.scrollWidth > list.clientWidth;
  });
  const rail = await tabList.evaluate((list) => ({
    outer: list.offsetHeight,
    tab: list.firstElementChild.getBoundingClientRect().height,
    width: list.clientWidth,
    content: list.scrollWidth,
    scrollbar: getComputedStyle(list, '::-webkit-scrollbar').height,
    thumb: getComputedStyle(list, '::-webkit-scrollbar-thumb').backgroundColor
  }));
  assert.ok(
    rail.outer - rail.tab >= 12,
    'Work views reserve a scrollbar gutter below tab content: ' +
      JSON.stringify(rail)
  );
  assert.equal(rail.scrollbar, '12px');
  assert.notEqual(rail.thumb, 'rgba(0, 0, 0, 0)');
  await tabList.evaluate((list) => (list.scrollLeft = 0));
  await tabList.hover();
  await page.mouse.wheel(180, 0);
  await page.waitForFunction(
    () =>
      document.querySelector(
        '.file-workspace .workspace-tabs[data-kind="view"] .workspace-tab-list'
      ).scrollLeft > 0
  );
  const widths = await tabs
    .locator('.workspace-tab')
    .evaluateAll((items) =>
      items.map((item) => item.getBoundingClientRect().width)
    );
  assert.ok(
    widths.every((width) => width >= 140),
    'Work tabs keep the same natural minimum as native tabs'
  );
  await tabs
    .getByRole('button', { name: 'Close view tab: Transfers', exact: true })
    .click();
  assert.equal(
    await tabs.getByRole('tab', { name: 'Transfers', exact: true }).count(),
    0
  );
  await ui
    .getByRole('button', { name: 'Save storage policy', exact: true })
    .click();
  await idle();
  await open('Files');
  for (const width of [1440, 700, 360]) {
    await page.setViewportSize({ width, height: 800 });
    await page.screenshot({
      path: process.argv[3] + '/inspection-' + width + '.png'
    });
    assert.ok(await ui.isVisible());
  }
  await page.reload();
  await ui.waitFor();
  await idle();
  assert.equal(await ui.locator('tbody tr').count(), 200);
  assert.ok(
    !actions.some((action) =>
      [
        'checkout',
        'submit',
        'create_change',
        'edit',
        'shelve',
        'transfer_begin'
      ].includes(action)
    ),
    actions.join(',')
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      checks:
        'inspection, no file mutations, paging, preview, catalog, storage ACL, layout, restart',
      actions: actions.length,
      rowsPerPage: 200
    })
  );
} catch (error) {
  console.error(errors);
  await page.screenshot({ path: process.argv[3] + '/inspection-failure.png' });
  throw error;
} finally {
  await browser.close();
}
