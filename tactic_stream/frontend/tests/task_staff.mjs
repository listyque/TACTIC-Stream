import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  hasTouch: true
});
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
page.setDefaultTimeout(15000);
try {
  await page.goto(
    process.argv[2] + '/projects/one/?search_type=contract/entity&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('project_writer');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STAFF_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).tap();
  await page.locator('.settings-menu > summary').tap();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: 'Task Manager', exact: true })
    .tap();
  const manager = page.getByRole('region', {
    name: 'Task Manager',
    exact: true
  });
  await manager.waitFor();
  await page.waitForFunction(
    () =>
      document
        .querySelector('.task-manager-results')
        ?.getAttribute('aria-busy') === 'false'
  );
  assert.equal(await manager.locator('tr[data-task-key]').count(), 2);
  const status = manager
    .locator('tr[data-task-key]')
    .first()
    .locator('[data-task-cell="status"] button');
  assert.equal(await status.isEnabled(), process.argv[3] === 'edit');
  if (process.argv[3] === 'edit') {
    await status.tap();
    await page
      .getByRole('dialog', { name: 'Edit task cell', exact: true })
      .waitFor();
    await page.keyboard.press('Escape');
  }
  mkdirSync('../.screenshots/product-staff', { recursive: true });
  await page.screenshot({
    path: `../.screenshots/product-staff/${process.argv[3]}-wide.png`
  });
  await page.setViewportSize({ width: 360, height: 800 });
  await manager.waitFor();
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    ),
    'No page overflow'
  );
  await page.screenshot({
    path: `../.screenshots/product-staff/${process.argv[3]}-narrow.png`
  });
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
